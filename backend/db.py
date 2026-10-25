import sqlite3
from pathlib import Path

# current_app allows for the app to be used without passing the app object
# g is used to store temporary data for the current request
from flask import current_app, g


def get_database():
    """Return the SQLite connection for the current Flask request."""

    # Create a connection only if one has not already been created. Flask's g
    # object lasts for the current request, so every task query in that request
    # can safely reuse this connection.
    if "database" not in g:
        # Get the database location configured by create_app() in app.py.
        database_path = current_app.config["DATABASE"]

        # sqlite3.Row lets task code access columns by name, such as
        # row["title"], instead of depending on numeric column positions.
        g.database = sqlite3.connect(database_path)
        g.database.row_factory = sqlite3.Row

        # SQLite requires foreign-key checking to be enabled per connection.
        # The current task table does not use those keys yet, but enabling this
        # now prepares the connection for the project and user tables.
        g.database.execute("PRAGMA foreign_keys = ON")

    return g.database


def close_database(error=None):
    """Close the connection stored for the completed Flask request."""

    # Remove the connection from Flask's request-local g object. pop() returns
    # None when no route opened a connection, so closing remains safe.
    database = g.pop("database", None)

    # Close the connection if a route used the database during this request.
    if database is not None:
        database.close()


def migrate_task_table(connection):
    """Add new task columns to databases created by the original prototype.

    CREATE TABLE IF NOT EXISTS does not update an existing table. This small
    migration keeps an older homefield.db usable by adding any missing columns.
    The original completed column may remain in an older database, but new code
    uses status as the single source of truth.
    """
    existing_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(task)")
    }

    # Each statement adds one column introduced by the expanded task model.
    # SQLite permits these ALTER TABLE operations without deleting saved tasks.
    columns_to_add = {
        "description": "TEXT NOT NULL DEFAULT ''",
        "status": "TEXT NOT NULL DEFAULT 'todo'",
        "deadline": "TEXT",
        "project_id": "INTEGER",
        "created_by": "INTEGER",
        "assigned_to": "INTEGER",
        "is_deleted": "INTEGER NOT NULL DEFAULT 0",
        "deleted_at": "TEXT",
        # These two columns begin nullable during migration because SQLite
        # cannot add a required column using a changing time-based default.
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }

    for column_name, column_definition in columns_to_add.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE task ADD COLUMN {column_name} {column_definition}"
            )

    # Give older task rows timestamps when they did not previously have them.
    # SQLite's CURRENT_TIMESTAMP is UTC and is suitable for this one-time
    # backfill. New tasks receive ISO 8601 UTC timestamps from Python.
    connection.execute(
        """
        UPDATE task
        SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP),
            updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
        WHERE created_at IS NULL OR updated_at IS NULL
        """
    )


def migrate_project_table(connection):
    """Preserve projects created before editing and soft deletion were added."""
    existing_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(project)")
    }
    columns_to_add = {
        "is_deleted": "INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1))",
        "deleted_at": "TEXT",
        "updated_at": "TEXT",
    }
    for column_name, definition in columns_to_add.items():
        if column_name not in existing_columns:
            connection.execute(f"ALTER TABLE project ADD COLUMN {column_name} {definition}")
    connection.execute(
        "UPDATE project SET updated_at = created_at WHERE updated_at IS NULL"
    )


def init_database(app):
    """Create the database, apply its schema, and register cleanup logic."""

    # Turn the configured database location into a Path object.
    database_path = Path(app.config["DATABASE"])

    # Create backend/database or the temporary test directory if it is missing.
    database_path.parent.mkdir(parents=True, exist_ok=True)

    # schema.sql sits beside this Python file and describes fresh databases.
    schema_path = Path(__file__).parent / "schema.sql"

    # Open a short-lived setup connection. Normal API requests use the
    # request-specific connection returned by get_database().
    connection = sqlite3.connect(database_path)

    # Foreign keys link related tables and must be enabled for every connection.
    connection.execute("PRAGMA foreign_keys = ON")

    # Create missing tables, then add expanded fields to an older task table.
    with schema_path.open("r", encoding="utf-8") as schema_file:
        connection.executescript(schema_file.read())

    migrate_task_table(connection)
    migrate_project_table(connection)
    connection.commit()
    connection.close()

    # Tell Flask to close request-specific connections after each request.
    app.teardown_appcontext(close_database)
