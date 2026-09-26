import sqlite3
from pathlib import Path

# current_app allows for the app to be used without passing the app object
# g is used to store temporary data for the current request
from flask import current_app, g

def get_database():

    # Create a connection only if one has not already been created
    if "database" not in g:
        #get database location from app refer to app.py
        database_path = current_app.config["DATABASE"]

        # Connect to the SQLite database and configure it
        g.database = sqlite3.connect(database_path)
        g.database.row_factory = sqlite3.Row
        g.database.execute("PRAGMA foreign_keys = ON")

    return g.database

def close_database(error=None):
    # Remove connection from g 'golbal' connection or return None
    database = g.pop("database", None)

    # Close the connection if it exists
    if database is not None:
        database.close()



def init_database(app):
    # Turns database location into a Path obj
    database_path = Path(app.config["DATABASE"])

    # Creates a databse location backend if it doesn't already exist
    database_path.parent.mkdir(parents=True, exist_ok=True)

    # Create Path obj to sql schema file
    schema_path = Path(__file__).parent / "schema.sql"

    # Open connection to database
    connection = sqlite3.connect(database_path)

    #Enables foreign keys. foreign keys are what links sql tables with another
    connection.execute("PRAGMA foreign_keys = ON")

    # Execute the SQL schema to create the necessary tables in the database
    with schema_path.open('r', encoding="utf-8") as schema_file:
        connection.executescript(schema_file.read())
    
    connection.close()

    # Tells flask to close the database connection when the app
    app.teardown_appcontext(close_database)