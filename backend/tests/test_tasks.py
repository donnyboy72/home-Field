"""Tests for the health and task API routes."""

import sqlite3

from app import create_app


def test_health_check(client):
    """The health route should confirm that the Flask API is available."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "running"}


def test_create_and_retrieve_task(authenticated_client):
    """A task created through POST should be returned by later GET requests."""
    client = authenticated_client
    user = client.get("/api/auth/me").get_json()["user"]
    # Send the same kind of JSON request that the Vue/Electron client will use.
    create_response = client.post(
        "/api/tasks",
        json={
            "title": "Connect Vue to Flask",
            "description": "Send tasks through the Flask API",
            "status": "in_progress",
            "deadline": "2026-10-20T23:59:00+00:00",
            # Project and assignee IDs are preserved. A supplied creator ID
            # must be replaced with the authenticated user's ID.
            "project_id": 1,
            "created_by": user["id"] + 1,
            "assigned_to": user["id"],
        },
    )

    # 201 Created means Flask successfully stored a new database row.
    assert create_response.status_code == 201

    created_task = create_response.get_json()["task"]
    assert created_task["title"] == "Connect Vue to Flask"
    assert created_task["description"] == "Send tasks through the Flask API"
    assert created_task["status"] == "in_progress"
    assert created_task["deadline"] == "2026-10-20T23:59:00+00:00"
    assert created_task["project_id"] == 1
    assert created_task["created_by"] == user["id"]
    assert created_task["assigned_to"] == user["id"]
    assert created_task["is_deleted"] is False
    assert created_task["deleted_at"] is None
    assert created_task["created_at"]
    assert created_task["updated_at"]

    # Verify the individual-task endpoint can retrieve the new task by ID.
    task_response = client.get(f"/api/tasks/{created_task['id']}")
    assert task_response.status_code == 200
    assert task_response.get_json()["task"] == created_task

    # Verify the task also appears in the endpoint that returns all tasks.
    list_response = client.get("/api/tasks")
    assert list_response.status_code == 200
    assert list_response.get_json()["tasks"] == [created_task]


def test_create_task_requires_json(authenticated_client):
    """POST requests without JSON should receive a useful client error."""
    client = authenticated_client
    response = client.post("/api/tasks")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Request must contain JSON"}


def test_create_task_requires_title(authenticated_client):
    """Task JSON should be rejected when its title is missing or empty."""
    client = authenticated_client
    response = client.post("/api/tasks", json={"title": "   "})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Task title must be a non-empty string"
    }


def test_create_task_uses_defaults(authenticated_client):
    """Optional fields should receive predictable server-side defaults."""
    client = authenticated_client
    response = client.post("/api/tasks", json={"title": "Minimal task"})

    assert response.status_code == 201
    task = response.get_json()["task"]
    assert task["description"] == ""
    assert task["status"] == "todo"
    assert task["deadline"] is None
    assert task["project_id"] is None
    user = client.get("/api/auth/me").get_json()["user"]
    assert task["created_by"] == user["id"]
    assert task["assigned_to"] is None


def test_create_task_rejects_invalid_status(authenticated_client):
    """A task status must match one of the values supported by the workflow."""
    client = authenticated_client
    response = client.post(
        "/api/tasks",
        json={"title": "Invalid task", "status": "almost_finished"},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Task status must be todo, in_progress, review, or done"
    }


def test_create_task_rejects_invalid_optional_id(authenticated_client):
    """Project and user references must be positive integer IDs or null."""
    client = authenticated_client
    response = client.post(
        "/api/tasks",
        json={"title": "Invalid project", "project_id": -1},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "project_id must be a positive integer or null"
    }


def test_unknown_task_returns_not_found(client):
    """Requesting an ID that is not in SQLite should return HTTP 404."""
    response = client.get("/api/tasks/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Task not found"}


def test_existing_minimal_database_is_migrated(tmp_path):
    """Starting Flask should preserve and expand an older task database."""
    database_path = tmp_path / "legacy.db"

    # Recreate the three-column schema used before the task model expansion.
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE task (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute(
            "INSERT INTO task (title) VALUES (?)",
            ("Existing task",),
        )

    # create_app() runs the startup migration before serving any requests.
    application = create_app(
        {
            "TESTING": True,
            "DATABASE": str(database_path),
        }
    )

    response = application.test_client().get("/api/tasks")
    assert response.status_code == 200

    migrated_task = response.get_json()["tasks"][0]
    assert migrated_task["title"] == "Existing task"
    assert migrated_task["description"] == ""
    assert migrated_task["status"] == "todo"
    assert migrated_task["created_at"]
    assert migrated_task["updated_at"]
