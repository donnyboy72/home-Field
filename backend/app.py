from flask import Flask, jsonify, request
from flask_cors import CORS

from db import init_database
from tasks import create_task, list_tasks, get_task
from pathlib import Path


def create_app():
    app = Flask(__name__) #create a flash app instance

    # Set the location of the SQLite database file.
    app.config["DATABASE"] = str(Path(__file__).resolve().parent / "database" / "homefield.db")

    # if test_config:
    #     app.config.update(test_config)


    # enable CORS for the app
    # Allow the Vue development server to access Flask API routes.
    # CORS is needed because Vue and Flask run on different ports.
    CORS(
        app,
        resources={
            #this is what creates the api call for vue to access the backend.
            r"/api/*": {
                # Only allow requests from the Vue development server.
                "origins": "http://localhost:5173",
            }
        },
    )

    # Create the database directory and initialize its tables.
    # Refer to db.py for the initialization logic.
    init_database(app)

    # A lightweight endpoint clients can use to verify that the API is available.
    @app.get("/api/health")
    def health_check():
        return jsonify({"status": "running"}), 200

    # Create a task from the JSON object supplied in the request body.
    @app.post("/api/tasks")
    def create_task_route():
        # silent=True returns None instead of raising an error for invalid JSON.
        payload = request.get_json(silent=True)

        if payload is None:
            return jsonify({"error": "Request must contain JSON"}), 400

        # Keep validation and database work in the task helper, outside the route.
        task, error = create_task(payload)

        if error:
            return jsonify({"error": error}), 400

        # HTTP 201 indicates that the task was created successfully.
        return jsonify({"task": task}), 201

    # Return every stored task as a JSON array.
    @app.get("/api/tasks")
    def list_tasks_route():
        return jsonify({"tasks": list_tasks()}), 200

    # Flask converts the task ID in the URL to an integer before this runs.
    @app.get("/api/tasks/<int:task_id>")
    def get_task_route(task_id):
        task = get_task(task_id)

        # Return a standard not-found response when the requested row is absent.
        if task is None:
            return jsonify({"error": "Task not found"}), 404

        return jsonify({"task": task}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)  # Reload the development server when code changes.
