from datetime import datetime, timezone

from db import get_database


# Keeping valid values in one set makes request validation easy to understand
# and matches the CHECK constraint declared in schema.sql.
VALID_STATUSES = {"todo", "in_progress", "review", "done"}


def utc_now():
    """Return the current time as an ISO 8601 timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


def validate_optional_id(payload, field_name):
    """Validate a nullable project or user ID from the request body."""
    value = payload.get(field_name)

    # None represents a relationship that has not been selected yet.
    if value is None:
        return None

    # bool is a subclass of int in Python, so reject it explicitly. Database IDs
    # must be positive integers such as 1 or 25, never true, false, zero, or -1.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return f"{field_name} must be a positive integer or null"

    return None


def validate_task_payload(payload):
    """Return an error message when task JSON is invalid, otherwise return None."""
    if not isinstance(payload, dict):
        return "Task data must be a JSON object"

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return "Task title must be a non-empty string"

    description = payload.get("description", "")
    if not isinstance(description, str):
        return "Task description must be a string"

    status = payload.get("status", "todo")
    if status not in VALID_STATUSES:
        return "Task status must be todo, in_progress, review, or done"

    deadline = payload.get("deadline")
    if deadline is not None and not isinstance(deadline, str):
        return "Task deadline must be a string or null"

    # An empty deadline is ambiguous, so require either a useful string or null.
    if isinstance(deadline, str) and not deadline.strip():
        return "Task deadline must be a non-empty string or null"

    for field_name in ("project_id", "created_by", "assigned_to"):
        error = validate_optional_id(payload, field_name)
        if error:
            return error

    return None


def create_task(payload):
    """Validate and save a task, returning (task, error)."""
    validation_error = validate_task_payload(payload)
    if validation_error:
        return None, validation_error

    database = get_database()
    current_time = utc_now()

    # IDs, deletion information, and timestamps are controlled by the server.
    # The client supplies only editable task fields and optional relationships.
    cursor = database.execute(
        """
        INSERT INTO task (
            title,
            description,
            status,
            deadline,
            project_id,
            created_by,
            assigned_to,
            is_deleted,
            deleted_at,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
        """,
        (
            payload["title"].strip(),
            payload.get("description", "").strip(),
            payload.get("status", "todo"),
            payload.get("deadline"),
            payload.get("project_id"),
            payload.get("created_by"),
            payload.get("assigned_to"),
            current_time,
            current_time,
        ),
    )
    database.commit()
    return get_task(cursor.lastrowid), None


def list_tasks():
    """Return active tasks in ID order, excluding soft-deleted records."""
    rows = get_database().execute(
        """
        SELECT
            id, title, description, status, deadline, project_id,
            created_by, assigned_to, is_deleted, deleted_at,
            created_at, updated_at
        FROM task
        WHERE is_deleted = 0
        ORDER BY id
        """
    ).fetchall()
    return [task_to_dict(row) for row in rows]


def get_task(task_id):
    """Return one active task, or None when it is missing or soft-deleted."""
    row = get_database().execute(
        """
        SELECT
            id, title, description, status, deadline, project_id,
            created_by, assigned_to, is_deleted, deleted_at,
            created_at, updated_at
        FROM task
        WHERE id = ? AND is_deleted = 0
        """,
        (task_id,),
    ).fetchone()
    return None if row is None else task_to_dict(row)


def task_to_dict(row):
    """Convert a SQLite row into a dictionary Flask can serialize as JSON."""
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "deadline": row["deadline"],
        "project_id": row["project_id"],
        "created_by": row["created_by"],
        "assigned_to": row["assigned_to"],
        # SQLite stores Boolean values as 0 and 1. Convert that integer into a
        # real Boolean before Flask serializes the response as JSON.
        "is_deleted": bool(row["is_deleted"]),
        "deleted_at": row["deleted_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def delete_task(task_id):
    """Hide a task while preserving its data for 24-hour recovery.

    Repeated deletion does not reset the original recovery window.
    """
    database = get_database()
    now = utc_now()
    cursor = database.execute(
        """UPDATE task SET is_deleted = 1, deleted_at = ?, updated_at = ?
        WHERE id = ? AND is_deleted = 0""", (now, now, task_id)
    )
    database.commit()
    return cursor.rowcount > 0


def list_deleted_tasks():
    """Return deleted tasks that can still be restored."""
    now = datetime.now(timezone.utc)
    rows = get_database().execute(
        "SELECT * FROM task WHERE is_deleted = 1 ORDER BY id"
    ).fetchall()
    return [task_to_dict(row) for row in rows if is_recoverable(row, now)]


def is_recoverable(row, now):
    """Use elapsed UTC time rather than formatted timestamp comparisons."""
    from datetime import timedelta

    try:
        deleted_at = datetime.fromisoformat(row["deleted_at"])
        if deleted_at.tzinfo is None:
            deleted_at = deleted_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return False
    return deleted_at <= now < deleted_at + timedelta(hours=24)


def restore_task(task_id):
    """Restore a deleted task before its recovery window expires."""
    database = get_database()
    # Serialize the check and update so a competing restore cannot race it.
    database.execute("BEGIN IMMEDIATE")
    try:
        row = database.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()
        if row is None or not row["is_deleted"]:
            database.rollback()
            return None, "Deleted task not found", 404
        if not is_recoverable(row, datetime.now(timezone.utc)):
            database.rollback()
            return None, "Task recovery window has expired", 410
        database.execute(
            """UPDATE task SET is_deleted = 0, deleted_at = NULL, updated_at = ?
            WHERE id = ?""", (utc_now(), task_id)
        )
        database.commit()
    except Exception:
        database.rollback()
        raise
    return get_task(task_id), None, 200
