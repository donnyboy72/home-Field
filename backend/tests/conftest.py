"""Shared setup used by the backend test files."""

import sys
from pathlib import Path

import pytest


# Add the backend directory to Python's import search path. This allows tests
# to be run from either the repository root or the backend directory without
# installing the backend as a Python package.
BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from app import create_app  # noqa: E402  (import after updating sys.path)


@pytest.fixture()
def app(tmp_path):
    """Create a Flask application with a fresh temporary database.

    pytest creates a different tmp_path for each test. As a result, tests do
    not read or overwrite backend/database/homefield.db and do not leave test
    database files inside the repository.
    """
    test_database = tmp_path / "test.db"

    application = create_app(
        {
            # TESTING tells Flask to expose errors instead of hiding them
            # behind a generic HTTP 500 response during automated tests.
            "TESTING": True,
            # Replace the normal database path with the temporary test file.
            "DATABASE": str(test_database),
        }
    )

    yield application


@pytest.fixture()
def client(app):
    """Return a client that can call Flask routes without a real web server."""
    return app.test_client()
