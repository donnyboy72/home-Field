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


def list_projects(user):
    condition = ""
    parameters = ()
    if not is_staff(user):
        condition = " AND id IN (SELECT project_id FROM project_member WHERE user_id = ?)"
        parameters = (user["id"],)
    rows = get_database().execute(
        "SELECT * FROM project WHERE is_deleted = 0" + condition + " ORDER BY id", parameters
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


def is_staff(user):
    return user["role"] in {"host", "manager"}


def can_access_project(project_id, user):
    """Staff see all data; ordinary users need membership in an active project."""
    if is_staff(user):
        return True
    if project_id is None or get_project(project_id) is None:
        return False
    return get_database().execute(
        "SELECT 1 FROM project_member WHERE project_id = ? AND user_id = ?",
        (project_id, user["id"]),
    ).fetchone() is not None


def can_assign_user(project_id, user_id):
    row = get_database().execute("SELECT id, role FROM user WHERE id = ?", (user_id,)).fetchone()
    return row is not None and can_access_project(project_id, row)


def project_assignees(project_id):
    """Expose only eligible account IDs/names, not general account management."""
    rows = get_database().execute(
        """SELECT id, username FROM user WHERE role IN ('host', 'manager')
        OR id IN (SELECT user_id FROM project_member WHERE project_id = ?)
        ORDER BY username""", (project_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def list_project_members(project_id):
    rows = get_database().execute(
        """SELECT user.id, user.username FROM project_member
        JOIN user ON user.id = project_member.user_id
        WHERE project_id = ? ORDER BY user.username""", (project_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def set_project_membership(project_id, user_id, grant):
    """Staff-only operation. Revocation also clears this project's assignments."""
    if user_id > 9223372036854775807:
        return "User not found", 404
    database = get_database()
    with database:
        database.execute("BEGIN IMMEDIATE")
        if get_project(project_id) is None:
            return "Project not found", 404
        user = database.execute("SELECT role FROM user WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            return "User not found", 404
        if user["role"] != "user":
            return "Host and managers already have access to all projects", 400
        if grant:
            database.execute(
                "INSERT OR IGNORE INTO project_member (project_id, user_id) VALUES (?, ?)",
                (project_id, user_id),
            )
        else:
            database.execute("DELETE FROM project_member WHERE project_id = ? AND user_id = ?",
                             (project_id, user_id))
            database.execute(
                "UPDATE task SET assigned_to = NULL, updated_at = ? WHERE project_id = ? AND assigned_to = ?",
                (datetime.now(timezone.utc).isoformat(), project_id, user_id),
            )
    return None, 204


def clear_inaccessible_assignments(user_id):
    """Called inside role demotion's transaction; no implicit project grants."""
    get_database().execute(
        """UPDATE task SET assigned_to = NULL, updated_at = ? WHERE assigned_to = ?
        AND (project_id IS NULL OR project_id NOT IN (
            SELECT project.id FROM project JOIN project_member ON project.id = project_member.project_id
            WHERE project.is_deleted = 0 AND project_member.user_id = ?))""",
        (datetime.now(timezone.utc).isoformat(), user_id, user_id),
    )
