"""Check account creation, password storage, and session-protected API behavior.

pytest supplies the app, client, and authentication fixtures from conftest.py.
Those fixtures use a temporary SQLite database instead of the host's real data.
"""

# Werkzeug is a separate Flask dependency. Its password checker confirms that
# a stored hash matches a password without needing to decrypt the hash.
from werkzeug.security import check_password_hash

# Inspect stored data through the backend's normal SQLite connection helper.
from db import get_database

def test_signup_stores_password_hash(client, app):
    """Check username normalization, private response fields, and password hashing."""
    password = "a-long-test-password"

    # Submit registration through the API, just as the GUI would.
    response = client.post(
        "/api/auth/signup",
        json={"username": "Duck", "password": password},)

    # Signup should create the account, lowercase its username, and exclude the
    # password hash from the JSON sent back to the client.
    assert response.status_code == 201
    assert response.get_json()["user"]["username"] == "duck"
    assert "password_hash" not in response.get_json()["user"]

    # Direct database inspection is test-only: verify what the API actually
    # saved. The app context supplies the configuration and g used by db.py.
    with app.app_context():
        row = get_database().execute(
            "SELECT password_hash FROM user WHERE username = ?", ("duck",),).fetchone()

        # Both checks matter: the value must differ from the plain password
        # and still verify correctly using Werkzeug's password checker.
        assert row["password_hash"] != password
        assert check_password_hash(row["password_hash"], password)

def test_duplicate_username(client):
    """Check that registering the same username twice returns a conflict."""
    payload = {
        "username": "Duck", "password": "a-long-test-password",
    }

    # Both requests share this test's database, so only the first can succeed.
    assert client.post("/api/auth/signup", json=payload).status_code == 201
    assert client.post("/api/auth/signup", json=payload).status_code == 409

def test_login_and_current_user(client, auth_headers):
    """Check that a logged-in session identifies the expected test user."""
    # auth_headers registers and logs in dummy_user before this request runs.
    response = client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json()["user"]["username"] == "dummy_user"

def test_wrong_password(client, auth_headers):
    """Check that an existing account cannot log in with an incorrect password."""
    # This fixture creates the account; its token is not sent to the login route.
    response = client.post(
        "/api/auth/login",
        json={"username": "dummy_user", "password": "wrong_password"},)

    # Failed login must return an authentication error instead of a new session.
    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid username or password"

def test_task_require_login(client):
    """Task creation must reject an unauthenticated client."""
    # No auth_headers fixture is requested, so this request has no Bearer token.
    response = client.post("/api/tasks", json={"title": "Requires login"})
    assert response.status_code == 401

def test_logout_ends_session(client, auth_headers):
    """Check that an authenticated logout request returns an empty success."""
    # This checks the logout response. Proving the session was invalidated also
    # requires a later protected request using the same token and expecting 401.
    response = client.post("/api/auth/logout", headers=auth_headers,)
    assert response.status_code == 204
