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
permanent deletion are not implemented. Project filtering now enforces project
access (see Step 3 below).

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
signup, and login remain public. Step 1 introduced these user endpoints
(Step 2 extends listing and username editing to managers):

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
API was included in Step 1; Step 2 adds the role endpoint below.

Step 3 below now restricts ordinary accounts to authorized projects. The agreed
final rules give logged-in managers access to all projects automatically. Average users will be able to
edit, assign, and change existing tasks' status in authorized projects, but will
not create, delete, or restore tasks or manage projects or membership. The ban on
average-user task creation supersedes the original Step 3 request.


## Manager permissions (Step 2)

Restart Flask to apply the migration, then reload the frontend. Log in as the
host and choose **Manage users**, beside **New task**. Each non-host account
has a **Make manager** or **Remove manager role** button. Removing the role
returns the account to `user`. The host cannot change their own host role, and
neither registration nor username editing can set roles.

`PATCH /api/users/<id>/role` accepts exactly `{"role": "manager"}` or
`{"role": "user"}` and returns `{"user": {...}}`. It requires the host's
Bearer session. Missing/invalid sessions return `401`, other signed-in accounts
receive `403`, invalid bodies return `400`, and missing accounts return `404`.
The host account's role cannot be changed (`403`).

Managers can view all users and edit usernames, including their own and other
managers' usernames. They cannot modify the host administrator, delete any
account, or change anyone's role. These restrictions are enforced by Flask,
including direct API requests. The interface hides forbidden controls.
Managers have the same existing task/project operations as the host, including
deleting tasks and restoring them within the existing 24-hour window. They
access every project automatically, without individual membership.

Sessions read the account's current role from SQLite on every API request:
promotion and demotion apply to existing sessions without another login.
The task screen checks the current account during its five-second refresh;
the users screen also checks every five seconds and provides **Refresh users**
to reload the list. Permission changes are enforced immediately by the next
API request even if a displayed control has not refreshed yet.

The migration rebuilds the old user table transactionally to expand its SQLite
role constraint. It preserves IDs, password hashes, roles, timestamps, sessions,
and the account ID sequence, including previously deleted IDs. Tasks and
projects are not reset. The single-host constraint remains enforced. Only
temporary databases are used by the permission and migration tests.

No separate requirements document is present in this checkout. Step 2 follows
the agreed requirement that logged-in managers automatically access all
projects. Project membership and ordinary-user restrictions are implemented in
Step 3 below.


## Ordinary-user permissions and project access (Step 3)

Restart Flask and reload the frontend. The migration adds an initially empty
`project_member` table; it does not reset accounts, sessions, projects, or tasks.
Existing ordinary accounts have no project access until the host or a manager
explicitly grants it. Creating a task in the past, being assigned one, or knowing
its ID does not grant access.

To grant access, log in as host or manager, open the project's **…** menu and
choose **Manage access**. Toggle each ordinary user's access. Host and managers
always access all projects without individual membership. Revocation applies on
the next API request using the same session and clears the user's assignments
on active and deleted tasks in that project. Those tasks are preserved.
Deleting an account also removes its memberships. A manager demoted to `user`
keeps any explicit memberships they previously had; implicit access ends and
assignments in inaccessible projects are cleared.

| Operation | Host | Manager | Ordinary user |
| --- | --- | --- | --- |
| View projects and active tasks | All | All | Authorized active projects only |
| Create tasks | Yes | Yes | No |
| Edit, assign, change task status | Yes | Yes | Authorized projects only |
| Delete or restore tasks / view recovery | Yes | Yes | No |
| Create, edit, delete projects | Yes | Yes | No |
| Grant or revoke project access | Yes | Yes | No |
| View users / edit usernames | Yes | Except editing host | No |
| Change manager roles / delete users | Yes, except host | No | No |

Ordinary users cannot see tasks without a project or tasks in deleted projects;
the host and managers retain access to those tasks. Inaccessible individual
project/task requests return `404` to avoid revealing other projects' data.
Forbidden operations return `403`; missing or invalid sessions return `401`.
Ordinary-user task creation is deliberately forbidden following the clarified
requirement, superseding the original Step 3 request that permitted it. No
separate requirements document was found in the checkout.

Assignments on task creation and editing are checked by Flask for every role.
Eligible assignees are the host, managers, and explicit members of the task's
active project. Clearing an assignment is allowed. For tasks with no project
or a deleted project, only the host and managers are eligible. Existing data
is retained by migration; an old assignment to an ineligible account must be
cleared or replaced when that task is edited. The task form offers only eligible
assignees, using usernames rather than requiring account IDs.

New API endpoints (all require Bearer sessions):

| Method | Route | Permission / response |
| --- | --- | --- |
| GET | `/api/projects/<id>/assignees` | Project access; eligible `{"users": [{"id": ..., "username": ...}]}`. |
| GET | `/api/projects/<id>/members` | Host/manager; explicitly granted users in the same `users` format. |
| PUT | `/api/projects/<id>/members/<user_id>` | Host/manager; grant ordinary account access, `204`. |
| DELETE | `/api/projects/<id>/members/<user_id>` | Host/manager; revoke ordinary account access, `204`. |

Grants/revocations are idempotent and require an existing active project and an
existing ordinary account. Host/manager targets return `400` because their
access is automatic. Missing projects/accounts return `404`.

The interface checks the current role during its five-second refresh, hides
forbidden controls, and loads only accessible data. An already open task form
closes when a refresh shows that its task is no longer accessible. Backend
checks apply independently of the interface. Clients and the host's interface
continue to use HTTP/JSON through Flask; only the host backend opens SQLite.
