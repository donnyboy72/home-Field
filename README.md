# home-Field

## Project API

Projects and tasks are stored in SQLite on the host. All GUIs communicate with
Flask through HTTP and JSON. Project UI implementation is left to the frontend.

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/api/projects` | List active projects in `{"projects": [...]}`. |
| POST | `/api/projects` | Create a project with `{"name": "Coursework"}`; returns `201`. |
| PUT or PATCH | `/api/projects/<id>` | Rename with `{"name": "New name"}`; returns `200`. |
| DELETE | `/api/projects/<id>` | Soft-delete; returns `204` with no body. |
| GET | `/api/tasks?project_id=1` | List active tasks belonging to an active project. |
| GET | `/api/tasks?project_id=unassigned` | List active tasks with no project. |

Project creation, editing, and deletion require the existing
`Authorization: Bearer <token>` login header. Create and edit responses use
`{"project": {...}}`. Project objects include `id`, `name`, `created_at`,
`updated_at`, `is_deleted`, and `deleted_at`. Timestamps use UTC ISO 8601 strings.
Only `name` is editable. Blank or invalid names and non-editable fields in edit
requests return `400` JSON errors. Missing or deleted projects return `404`
when editing, deleting, or filtering tasks by project.

`POST /api/tasks` accepts `project_id` as an existing active project ID or `null`.
Deleting a project preserves its row and its tasks, including their project IDs.
It does not delete or reassign tasks. Those tasks remain accessible through
`GET /api/tasks` and the individual task API, while the deleted project is hidden
from `GET /api/projects` and cannot accept new tasks. Project restoration and
permanent deletion are not implemented. Project filtering does not enforce
user membership or access permissions.

Restart Flask to apply the project schema migration automatically. Existing
projects and tasks are preserved; no database reset is needed.

## Host administrator setup (permission Step 1)

1. Register the administrator's account through the normal Sign up screen.
2. On the trusted host computer, stop Flask and run from the repository root:

   ```bash
   source .venv/bin/activate
   python -m flask --app backend/app.py setup-host YOUR_USERNAME
   ```

3. Restart Flask and log in with that account. **Manage users** opens the user
   list, username editing, and deletion controls. Existing task/project controls
   give the host full access, including task recovery within the existing
   24-hour limit.

The setup command requires trusted shell access to the host and can designate
only one registered account. It cannot replace an existing host. No HTTP setup
endpoint exists; registration rejects `role`. Connecting from localhost or
sending a role header does not grant administrator access. Keep the host's
shell and database file accessible only to trusted people.

Startup adds a `role` column without resetting the database. All existing and
new accounts default to `user`; none is automatically promoted. Public user
JSON now also includes `role`. Session lookup reads it from SQLite on every
request. No setup command has been run against the real database as part of
this implementation.

All task/project reads, deletion, and restoration now require the existing
Bearer session header, as do their existing creation/editing endpoints. Health,
signup, and login remain public. Host-only user endpoints are:

| Method | Route | Behavior |
| --- | --- | --- |
| GET | `/api/users` | List public account fields. |
| PATCH | `/api/users/<id>` | Edit `username` only. |
| DELETE | `/api/users/<id>` | Delete a non-host account; return `204`. |

User deletion atomically removes all their sessions, clears assignments on
active and deleted tasks, and preserves tasks and projects. Task `created_by`
IDs remain as historical attribution even after the account is removed; account
IDs are not reused. The current project model has no creator field, so projects
remain unchanged. Host deletion returns `403`. No password-reset or role-editing
API is included in Step 1.

Steps 2 and 3 remain pending review: authenticated non-host accounts retain
existing task/project access for now. The agreed final rules give logged-in
managers access to all projects automatically. Average users will be able to
edit, assign, and change existing tasks' status in authorized projects, but will
not create, delete, or restore tasks or manage projects or membership. The ban on
average-user task creation supersedes the original Step 3 request.
