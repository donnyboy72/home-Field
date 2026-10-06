from db import get_database


def create_task(payload):
    """Validate and save a task, returning (task, error)."""
    if not isinstance(payload, dict):
        return None, "Task data must be a JSON object"

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return None, "Task title must be a non-empty string"

    database = get_database()
    cursor = database.execute(
        "INSERT INTO task (title) VALUES (?)", (title.strip(),)
    )
    database.commit()
    return get_task(cursor.lastrowid), None


def list_tasks():
    """Return every task in ID order."""
    rows = get_database().execute(
        "SELECT id, title, completed FROM task ORDER BY id"
    ).fetchall()
    return [task_to_dict(row) for row in rows]


def get_task(task_id):
    """Return one task, or None when its ID does not exist."""
    row = get_database().execute(
        "SELECT id, title, completed FROM task WHERE id = ?", (task_id,)
    ).fetchone()
    return None if row is None else task_to_dict(row)


def task_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "completed": bool(row["completed"]),
    }
