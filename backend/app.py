"""Configure the host's Flask API and translate HTTP requests into helper calls.

Both host and client GUIs use these routes; SQLite access stays in the backend.
"""

# Flask creates the server application; jsonify builds JSON responses; request
# exposes incoming JSON and headers; g shares data within the current request.
import click
from flask.cli import with_appcontext
from flask import Flask, jsonify, request, g
# Allow the configured browser frontend origin to read API responses.
from flask_cors import CORS
# Werkzeug is a separate dependency used by Flask. This helper builds the
# dummy password hash used when login attempts name an unknown account.
from werkzeug.security import generate_password_hash

# Keep database setup and task validation/queries in their own modules.
from db import init_database
from projects import (create_project, list_projects, get_project,
                      update_project, delete_project, can_access_project,
                      project_assignees, list_project_members, set_project_membership)
from tasks import (create_task, list_tasks, get_task, delete_task,
                   list_deleted_tasks, restore_task, update_task)
# Build the database path relative to this file, regardless of working directory.
from pathlib import Path

# Preserve a route function's name and metadata when login_required wraps it.
from functools import wraps
# Account and session helpers handle validation, password checks, and SQLite.
from users import (
    establish_host, list_users, update_user, delete_user, set_user_role,
    create_user,
    authenticate_user,
    create_session,
    get_session_user,
    delete_session,
)


def create_app(test_config=None):
    """Create and configure the Flask application.

    test_config is optional. The real application uses homefield.db, while the
    automated tests pass in a temporary database so tests cannot change the
    developers' local data.
    """
    app = Flask(__name__)  # Create the Flask application instance.

    # Set the location of the SQLite database file.
    app.config["DATABASE"] = str(Path(__file__).resolve().parent / "database" / "homefield.db")

    # Override normal settings when a caller supplies test configuration.
    # For example, the tests replace homefield.db with a temporary test.db.
    if test_config is not None:
        app.config.update(test_config)


    # Allow the Vue development server to access Flask API routes.
    # CORS is needed because Vue and Flask run on different ports.
    # This controls browser access to responses, not authentication or networking.
    CORS(
        app,
        resources={
            # Apply this origin policy to API paths; route decorators below
            # define the endpoints themselves.
            r"/api/*": {
                # Only allow requests from the Vue development server.
                "origins": ["http://localhost:5173", 
                "http://localhost:9000",
                "http://172.20.10.10:9000",]
            }
        },
    )

    # Create the database directory and initialize its tables.
    # Refer to db.py for the initialization logic.
    init_database(app)

    # Generate this once per application, then reuse it for unknown usernames.
    # Running password verification in that case reduces login timing differences.
    dummy_password_hash = generate_password_hash("dummy-password")
    
    # A lightweight endpoint clients can use to verify that the API is available.
    @app.get("/api/health")
    def health_check():
        """Report that the API is responding without returning application data."""
        return jsonify({"status": "running"}), 200

    # Create a task from the JSON object supplied in the request body.
    @app.post("/api/tasks")
    @staff_required
    def create_task_route():
        """Validate incoming JSON through the task helper and return the result."""
        # silent=True returns None instead of raising an error for invalid JSON.
        payload = request.get_json(silent=True)

        if payload is None:
            return jsonify({"error": "Request must contain JSON"}), 400

        # Keep validation and database work in the task helper, outside the route.
        # Identify the creator from the session, not from client-supplied data.
        task, error = create_task(payload, g.user["id"])

        if error:
            return jsonify({"error": error}), 400

        # HTTP 201 indicates that the task was created successfully.
        return jsonify({"task": task}), 201

    # Normal task lists exclude soft-deleted tasks.
    @app.get("/api/tasks")
    @login_required
    def list_tasks_route():
        """Return active tasks for the GUI's initial load and refresh requests."""
        filters = request.args.getlist("project_id")
        if not filters:
            return jsonify({"tasks": list_tasks(g.user)}), 200
        if len(filters) != 1:
            return jsonify({"error": "Provide only one project_id"}), 400
        value = filters[0]
        if value == "unassigned":
            return jsonify({"tasks": list_tasks(g.user, unassigned=True)}), 200
        if (len(value) > 19 or not value.isascii() or not value.isdecimal()
                or not 0 < int(value) <= 9223372036854775807):
            return jsonify({"error": "project_id must be a positive integer or unassigned"}), 400
        project_id = int(value)
        if get_project(project_id) is None or not can_access_project(project_id, g.user):
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"tasks": list_tasks(g.user, project_id=project_id)}), 200

    @app.get("/api/projects")
    @login_required
    def list_projects_route():
        return jsonify({"projects": list_projects(g.user)}), 200

    @app.post("/api/projects")
    @staff_required
    def create_project_route():
        project, error = create_project(request.get_json(silent=True))
        if error:
            return jsonify({"error": error}), 400
        return jsonify({"project": project}), 201

    @app.put("/api/projects/<int:project_id>")
    @app.patch("/api/projects/<int:project_id>")
    @staff_required
    def update_project_route(project_id):
        project, error, status = update_project(
            project_id, request.get_json(silent=True)
        )
        if error:
            return jsonify({"error": error}), status
        return jsonify({"project": project}), status

    @app.delete("/api/projects/<int:project_id>")
    @staff_required
    def delete_project_route(project_id):
        if not delete_project(project_id):
            return jsonify({"error": "Project not found"}), 404
        return "", 204

    # Flask converts the task ID in the URL to an integer before this runs.
    @app.get("/api/tasks/<int:task_id>")
    @login_required
    def get_task_route(task_id):
        """Return one active task, or a JSON error if it cannot be found."""
        task = get_task(task_id)

        # Return a standard not-found response when the requested row is absent.
        if task is None or not can_access_project(task["project_id"], g.user):
            return jsonify({"error": "Task not found"}), 404

        return jsonify({"task": task}), 200

    @app.patch("/api/tasks/<int:task_id>")
    @login_required
    def update_task_route(task_id):
        """Update supplied editable fields for a logged-in user."""
        task, error, status = update_task(
            task_id, request.get_json(silent=True), g.user
        )
        if error:
            return jsonify({"error": error}), status
        return jsonify({"task": task}), status

    @app.delete("/api/tasks/<int:task_id>")
    @staff_required
    def delete_task_route(task_id):
        """Ask the task helper to soft-delete a task rather than erase its row."""
        # A false result means there is no active task to delete. Successful
        # deletion returns HTTP 204, which has no response body.
        if not delete_task(task_id):
            return jsonify({"error": "Task not found"}), 404
        return "", 204

    @app.get("/api/tasks/deleted")
    @staff_required
    def deleted_tasks_route():
        """Return the task helper's deleted-task list for the recovery view."""
        return jsonify({"tasks": list_deleted_tasks()}), 200

    @app.post("/api/tasks/<int:task_id>/restore")
    @staff_required
    def restore_task_route(task_id):
        """Restore a deleted task if the helper's recovery rules allow it."""
        # The helper chooses the status for success, missing tasks, or an
        # expired recovery period; the route passes that decision to the GUI.
        task, error, status = restore_task(task_id)
        if error:
            return jsonify({"error": error}), status
        return jsonify({"task": task}), status

    @app.post("/api/auth/signup")
    def signup_route():
        """Pass registration data to create_user and return its user or error."""
        # Invalid or missing JSON becomes None, which create_user validates.
        payload = request.get_json(silent=True)
        user, error, status = create_user(payload)

        if error:
            return jsonify({"error": error}), status
        return jsonify({"user": user}), status

    @app.post("/api/auth/login")
    def login_route():
        """Check credentials and issue a session token for a successful login."""
        payload = request.get_json(silent=True)
        user = authenticate_user(payload, dummy_password_hash)

        # Use the same error for unknown usernames and incorrect passwords.
        if user is None:
            return jsonify({"error": "Invalid username or password"}), 401

        # The client receives the original token; SQLite stores only its hash.
        token = create_session(user["id"])

        response = jsonify({"user": user, "token": token})

        # Tell clients and intermediaries not to cache a response with a token.
        response.headers["Cache-Control"] = "no-store"
        return response, 200

    @app.get("/api/auth/me")
    @login_required
    def current_user_route():
        """Return the user that login_required attached to this request."""
        return jsonify({"user": g.user}), 200

    @app.post("/api/auth/logout")
    @login_required
    def logout_route():
        """Delete the authenticated session and return an empty 204 response."""
        # The decorator supplies the validated token through Flask's g object.
        delete_session(g.session_token)
        return "", 204

    @app.cli.command("setup-host")
    @click.argument("username")
    @with_appcontext
    def setup_host_command(username):
        """Designate a registered account using trusted host shell access."""
        error = establish_host(username)
        if error:
            raise click.ClickException(error)
        click.echo("Host administrator established.")

    @app.get("/api/users")
    @staff_required
    def list_users_route():
        return jsonify({"users": list_users()}), 200

    @app.patch("/api/users/<int:user_id>")
    @staff_required
    def update_user_route(user_id):
        user, error, status = update_user(user_id, request.get_json(silent=True), g.user["role"])
        if error:
            return jsonify({"error": error}), status
        return jsonify({"user": user}), status

    @app.patch("/api/users/<int:user_id>/role")
    @host_required
    def set_user_role_route(user_id):
        user, error, status = set_user_role(user_id, request.get_json(silent=True))
        if error:
            return jsonify({"error": error}), status
        return jsonify({"user": user}), status

    @app.delete("/api/users/<int:user_id>")
    @host_required
    def delete_user_route(user_id):
        error, status = delete_user(user_id)
        if error:
            return jsonify({"error": error}), status
        return "", status

    @app.get("/api/projects/<int:project_id>")
    @login_required
    def get_project_route(project_id):
        project = get_project(project_id)
        if project is None or not can_access_project(project_id, g.user):
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"project": project}), 200

    @app.get("/api/projects/<int:project_id>/assignees")
    @login_required
    def project_assignees_route(project_id):
        if get_project(project_id) is None or not can_access_project(project_id, g.user):
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"users": project_assignees(project_id)}), 200

    @app.get("/api/projects/<int:project_id>/members")
    @staff_required
    def project_members_route(project_id):
        if get_project(project_id) is None:
            return jsonify({"error": "Project not found"}), 404
        return jsonify({"users": list_project_members(project_id)}), 200

    @app.put("/api/projects/<int:project_id>/members/<int:user_id>")
    @app.delete("/api/projects/<int:project_id>/members/<int:user_id>")
    @staff_required
    def project_membership_route(project_id, user_id):
        error, status = set_project_membership(project_id, user_id, request.method == "PUT")
        if error:
            return jsonify({"error": error}), status
        return "", status

    # Return the configured app so tests or the development entry point can use it.
    return app

def login_required(view):
    """Wrap a route so only a valid, unexpired Bearer session can reach it."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        """Validate this request's token, attach its user, then call the route."""
        # Expect a header such as Authorization: Bearer <session token>.
        # partition also handles missing spaces without raising an exception.
        authorization = request.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")

        # Reject missing, malformed, or oversized credentials before lookup.
        if (
            not separator
            or scheme.lower() != "bearer"
            or not token
            or len(token) > 256
        ):
            return jsonify({"error": "Login required"}), 401

        # Session lookup checks the token hash and expiration in the backend.
        user = get_session_user(token)

        if user is None:
            return jsonify({"error": "Session is invalid or expired"}), 401

        # g lasts only for this request. Protected routes can use these values
        # without parsing the header or checking the session a second time.
        g.user = user
        g.session_token = token

        # Forward any URL parameters to the original route after authentication.
        return view(*args, **kwargs)
    return wrapped_view

def staff_required(view):
    """Allow staff operations, checking the current database role."""
    @login_required
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user["role"] not in {"host", "manager"}:
            return jsonify({"error": "Host administrator or manager required"}), 403
        return view(*args, **kwargs)
    return wrapped_view


def host_required(view):
    @login_required
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user["role"] != "host":
            return jsonify({"error": "Host administrator required"}), 403
        return view(*args, **kwargs)
    return wrapped_view


if __name__ == "__main__":
    from discovery import advertise_host

    # Run only when launched directly, not when tests import create_app.
    # Listening on all interfaces allows LAN clients to use the host's actual
    # private IP and port 50000.
    app = create_app()
    # Disable the reloader so only one process advertises this host. Discovery is
    # outside create_app, so clients and Flask tests never start an advertiser.
    with advertise_host(50000):
        app.run(host="0.0.0.0", port=50000, debug=False, use_reloader=False)
