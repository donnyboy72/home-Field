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
