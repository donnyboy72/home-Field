"""Shared setup used by the backend test files.

pytest automatically discovers fixtures in conftest.py. Tests request them by
using fixture names as function arguments; no explicit import is needed.
"""

# sys exposes the import search path so tests can find the backend modules.
import sys
# Path builds file locations independently of the current working directory.
from pathlib import Path

# pytest supplies fixture decorators and the built-in tmp_path fixture.
import pytest


# Add the backend directory to Python's import search path. This allows tests
# to be run from either the repository root or the backend directory without
# installing the backend as a Python package.
# Starting at backend/tests/conftest.py, parents[1] selects backend/.
BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

# Import the application factory only after making backend/ importable.
from app import create_app  # noqa: E402  (import after updating sys.path)


@pytest.fixture()
def app(tmp_path):
    """Create a Flask application with a fresh temporary database.

    pytest creates a different tmp_path for each test. As a result, tests do
    not read or overwrite backend/database/homefield.db and do not leave test
    database files inside the repository.
    """
    # Fixtures use function scope by default, so each test gets its own app
    # and database rather than sharing accounts, tasks, or sessions across tests.
    test_database = tmp_path / "test.db"

    # Use the same factory as the real host server, with test-only overrides.
    # Database initialization therefore runs against this temporary path.
    application = create_app(
        {
            # TESTING tells Flask to expose errors instead of hiding them
            # behind a generic HTTP 500 response during automated tests.
            "TESTING": True,
            # Replace the normal database path with the temporary test file.
            "DATABASE": str(test_database),
        }
    )

    # Give the configured app to the test or another fixture. Cleanup code
    # could go after yield; pytest manages the temporary directory separately.
    yield application


@pytest.fixture()
def client(app):
    """Return a client that can call Flask routes without a real web server."""
    # pytest builds the app fixture first. Flask's client sends requests inside
    # this process while still running route handling and database operations.
    return app.test_client()

@pytest.fixture()
def auth_headers(client):
    """Register and log in a test user, then return its Bearer token header."""
    # Create the account through the API so authentication tests exercise the
    # backend's normal validation and password hashing in the temporary database.
    client.post(
        "/api/auth/signup",
        json={"username": "dummy_user",
              "password": "dummy_password_123"},
    )

    # Log in with the same credentials to obtain a server-issued session token.
    response = client.post(
        "/api/auth/login",
        json={"username": "dummy_user",
              "password": "dummy_password_123"},)

    # Protected routes expect Authorization: Bearer <token>. Tests can pass
    # this dictionary as headers=auth_headers on individual client requests.
    token = response.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def authenticated_client(client, auth_headers):
    """Return the test client with its session header included by default."""
    # Depending on auth_headers runs signup and login before this fixture.
    # Flask's test environment uses HTTP_AUTHORIZATION for the Authorization
    # request header, so subsequent requests need not supply it each time.
    client.environ_base["HTTP_AUTHORIZATION"] = (
        auth_headers["Authorization"]
    )
    return client
