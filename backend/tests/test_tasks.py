"""Tests for the health and task API routes."""


def test_health_check(client):
    """The health route should confirm that the Flask API is available."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "running"}


def test_create_and_retrieve_task(client):
    """A task created through POST should be returned by later GET requests."""
    # Send the same kind of JSON request that the Vue/Electron client will use.
    create_response = client.post(
        "/api/tasks",
        json={"title": "Connect Vue to Flask"},
    )

    # 201 Created means Flask successfully stored a new database row.
    assert create_response.status_code == 201

    created_task = create_response.get_json()["task"]
    assert created_task["title"] == "Connect Vue to Flask"
    assert created_task["completed"] is False

    # Verify the individual-task endpoint can retrieve the new task by ID.
    task_response = client.get(f"/api/tasks/{created_task['id']}")
    assert task_response.status_code == 200
    assert task_response.get_json()["task"] == created_task

    # Verify the task also appears in the endpoint that returns all tasks.
    list_response = client.get("/api/tasks")
    assert list_response.status_code == 200
    assert list_response.get_json()["tasks"] == [created_task]


def test_create_task_requires_json(client):
    """POST requests without JSON should receive a useful client error."""
    response = client.post("/api/tasks")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Request must contain JSON"}


def test_create_task_requires_title(client):
    """Task JSON should be rejected when its title is missing or empty."""
    response = client.post("/api/tasks", json={"title": "   "})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Task title must be a non-empty string"
    }


def test_unknown_task_returns_not_found(client):
    """Requesting an ID that is not in SQLite should return HTTP 404."""
    response = client.get("/api/tasks/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Task not found"}
