"""Configure the host's Flask API and translate HTTP requests into helper calls.

Both host and client GUIs use these routes; SQLite access stays in the backend.
"""

# Flask creates the server application; jsonify builds JSON responses; request
# exposes incoming JSON and headers; g shares data within the current request.
from flask import Flask, jsonify, request, g
# Allow the configured browser frontend origin to read API responses.
from flask_cors import CORS
# Werkzeug is a separate dependency used by Flask. This helper builds the
# dummy password hash used when login attempts name an unknown account.
from werkzeug.security import generate_password_hash

# Keep database setup and task validation/queries in their own modules.
from db import init_database
from tasks import (create_task, list_tasks, get_task, delete_task,
                   list_deleted_tasks, restore_task)
# Build the database path relative to this file, regardless of working directory.
from pathlib import Path

# Preserve a route function's name and metadata when login_required wraps it.
from functools import wraps
# Account and session helpers handle validation, password checks, and SQLite.
from users import (
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
    @login_required
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
    def list_tasks_route():
        """Return active tasks for the GUI's initial load and refresh requests."""
        return jsonify({"tasks": list_tasks()}), 200

    # Flask converts the task ID in the URL to an integer before this runs.
    @app.get("/api/tasks/<int:task_id>")
    def get_task_route(task_id):
        """Return one active task, or a JSON error if it cannot be found."""
        task = get_task(task_id)

        # Return a standard not-found response when the requested row is absent.
        if task is None:
            return jsonify({"error": "Task not found"}), 404

        return jsonify({"task": task}), 200

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task_route(task_id):
        """Ask the task helper to soft-delete a task rather than erase its row."""
        # A false result means there is no active task to delete. Successful
        # deletion returns HTTP 204, which has no response body.
        if not delete_task(task_id):
            return jsonify({"error": "Task not found"}), 404
        return "", 204

    @app.get("/api/tasks/deleted")
    def deleted_tasks_route():
        """Return the task helper's deleted-task list for the recovery view."""
        return jsonify({"tasks": list_deleted_tasks()}), 200

    @app.post("/api/tasks/<int:task_id>/restore")
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
            return jsonify({"error": "Session is invalid or expride"}), 401

        # g lasts only for this request. Protected routes can use these values
        # without parsing the header or checking the session a second time.
        g.user = user
        g.session_token = token

        # Forward any URL parameters to the original route after authentication.
        return view(*args, **kwargs)
    return wrapped_view

if __name__ == "__main__":
    # Run only when launched directly, not when tests import create_app.
    # Listening on all interfaces allows LAN clients to use the host's actual
    # private IP and port 50000. Debug mode is for trusted development only.
    app = create_app()
    app.run(host="0.0.0.0", port=50000,debug=True)  # Reload the development server when code changes.
