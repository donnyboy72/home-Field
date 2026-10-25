"""Validate and query projects in the host database."""
from datetime import datetime, timezone

from db import get_database


def project_to_dict(row):
    project = dict(row)
    project["is_deleted"] = bool(project["is_deleted"])
    return project


def get_project(project_id):
    """Return an active project; deleted projects behave like missing ones."""
    if project_id > 9223372036854775807:
        return None
    row = get_database().execute(
        "SELECT * FROM project WHERE id = ? AND is_deleted = 0", (project_id,)
    ).fetchone()
    return project_to_dict(row) if row is not None else None


def list_projects():
    rows = get_database().execute(
        "SELECT * FROM project WHERE is_deleted = 0 ORDER BY id"
    ).fetchall()
    return [project_to_dict(row) for row in rows]


def validate_project(payload):
    if not isinstance(payload, dict):
        return "Project data must be a JSON object"
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return "Project name must be a non-empty string"
    return None


def create_project(payload):
    error = validate_project(payload)
    if error:
        return None, error
    database = get_database()
    now = datetime.now(timezone.utc).isoformat()
    cursor = database.execute(
        "INSERT INTO project (name, created_at, updated_at) VALUES (?, ?, ?)",
        (payload["name"].strip(), now, now),
    )
    database.commit()
    return get_project(cursor.lastrowid), None


def update_project(project_id, payload):
    """Only the name is editable; identity and lifecycle fields are server-owned."""
    error = validate_project(payload)
    if error:
        return None, error, 400
    if set(payload) != {"name"}:
        return None, "Request contains fields that cannot be edited", 400
    if project_id > 9223372036854775807:
        return None, "Project not found", 404
    database = get_database()
    with database:
        cursor = database.execute(
            """UPDATE project SET name = ?, updated_at = ?
            WHERE id = ? AND is_deleted = 0""",
            (payload["name"].strip(), datetime.now(timezone.utc).isoformat(), project_id),
        )
        if cursor.rowcount == 0:
            return None, "Project not found", 404
        project = get_project(project_id)
    return project, None, 200


def delete_project(project_id):
    """Hide the project, preserving its tasks and their project relationships."""
    if project_id > 9223372036854775807:
        return False
    database = get_database()
    now = datetime.now(timezone.utc).isoformat()
    cursor = database.execute(
        """UPDATE project SET is_deleted = 1, deleted_at = ?, updated_at = ?
        WHERE id = ? AND is_deleted = 0""", (now, now, project_id),
    )
    database.commit()
    return cursor.rowcount > 0
