"""User and session helpers for the host's Flask backend.

These functions validate input and query SQLite through db.get_database().
The API routes are responsible for reading requests and returning HTTP responses.
"""

import hashlib  # Hash session tokens before storing or looking them up.
import re  # Check usernames against the allowed characters and length.
import secrets  # Generate unpredictable session tokens suitable for login.
import sqlite3  # Catch database constraint errors, such as duplicate usernames.
# datetime reads the current time, timedelta sets session lifetimes, and
# timezone keeps stored timestamps and expiration checks in UTC.
from datetime import datetime, timedelta, timezone

# Werkzeug is a separate library that Flask depends on. Its security helpers
# create salted password hashes and verify passwords without storing plain text.
from werkzeug.security import generate_password_hash, check_password_hash

# Reuse the host's SQLite connection for the current Flask request; db.py
# handles opening the connection, enabling foreign keys, and closing it.
from db import get_database


def user_to_dict(row):
    """Return only user fields that are safe to send to clients."""
    # Explicitly select public fields so password hashes never reach the GUI,
    # even when the query returned every column from the user table.
    return {
        "id": row["id"],
        "username": row["username"],
        "created_at": row["created_at"],
    }

def normalize_username(value):
    """Trim and lowercase a username, or return None for non-string input."""
    # Registration and login use the same normalization so capitalization and
    # surrounding spaces do not cause different account lookups.
    if not isinstance(value, str):
        return None

    return value.strip().lower()

def hash_token(token):
    """Return a consistent SHA-256 digest for storing or finding a token."""
    # These tokens are random secrets, unlike user-chosen passwords. A fast
    # hash supports lookups without keeping the original login token in SQLite.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_user(payload):
    """Create an account and return (public user, error message, HTTP status).

    Success returns a user dictionary and no error; validation or duplicate
    username failures return no user and an error for the route to send back.
    """
    # Reject non-object JSON before trying to read registration fields.
    if not isinstance(payload, dict):
        return None, "User data must be a JSON object", 400

    # Normalize only the username. Password spaces and case remain significant.
    username = normalize_username(payload.get("username"))
    password = payload.get("password")

    # Validate on the server even if the GUI already checked these fields.
    if username is None or not re.fullmatch(r"[a-z0-9_]{3,30}", username):
        return None, "Username must be 3-30 characters of lowercase letters, numbers, or underscores", 400

    if not isinstance(password, str) or not 15 <= len(password) <= 128:
        return None, "Password must be 15-28 characters", 400

    # Prepare the password hash and server-controlled UTC creation timestamp.
    password_hash = generate_password_hash(password)
    created_at = datetime.now(timezone.utc).isoformat()
    database = get_database()

    # SQL placeholders keep client values separate from the SQL statement.
    # Commit saves the account; rollback clears the failed transaction if a
    # database constraint rejects it (the intended case is a taken username).
    try:
        cursor = database.execute(
            """
            INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)
            """, 
            (username, password_hash, created_at)
        )
        database.commit()
    except sqlite3.IntegrityError:
        database.rollback()
        return None, "Username is aldready in use", 409

    # Read back the database-assigned ID and return only public account fields.
    row = database.execute(
        "SELECT id, username, created_at FROM user WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()

    return user_to_dict(row), None, 201

def authenticate_user(payload, dummy_password_hash):
    """Return the public user for valid credentials, otherwise None.

    The caller supplies a precomputed dummy password hash so an unknown
    username still goes through password verification.
    """
    # Reject malformed credentials before running a query or password check.
    if not isinstance(payload, dict):
        return None
    username = normalize_username(payload.get("username"))
    password = payload.get("password")

    if (
        username is None
        or not isinstance(password, str)
        or not 1 <= len(password) <= 128
    ):
        return None

    # The password hash is needed internally for verification, but user_to_dict
    # removes it from the result returned to the caller.
    row = get_database().execute(
        "SELECT * FROM user WHERE username = ?",
        (username,),
    ).fetchone()

    # Perform password verification even when the username does not exist.
    # This reduces timing differences that could reveal registered usernames.
    stored_hash = row["password_hash"] if row else dummy_password_hash
    password_matches = check_password_hash(stored_hash, password)

    if row is None or not password_matches:
        return None

    return user_to_dict(row)


def create_session(user_id):
    """Save an eight-hour session for a user ID and return its original token."""
    # Generate a fresh secret for this login and an ISO 8601 expiration in UTC.
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=8)
    ).isoformat()

    # Store only the token hash, linked to the user and its expiration time.
    database = get_database()
    database.execute(
        """
        INSERT INTO session (token_hash, user_id, expires_at)
        VALUES (?, ?, ?)
        """,
        (hash_token(token), user_id, expires_at),
    )
    database.commit()

    # Return the original token once; only its hash stays in the database.
    return token


def get_session_user(token):
    """Return the public user for a stored, unexpired token, otherwise None."""
    # Hash the supplied token to find the session. The JOIN retrieves its user
    # in the same query, avoiding a separate account lookup.
    row = get_database().execute(
        """
        SELECT user.id, user.username, user.created_at, session.expires_at
        FROM session
        JOIN user ON user.id = session.user_id
        WHERE session.token_hash = ?
        """,
        (hash_token(token),),
    ).fetchone()

    # An unknown or deleted session cannot identify a logged-in user.
    if row is None:
        return None

    # Parse the stored UTC timestamp before comparing times. Expired sessions
    # are rejected here; this lookup does not delete their database rows.
    expires_at = datetime.fromisoformat(row["expires_at"])

    if expires_at <= datetime.now(timezone.utc):
        return None

    return user_to_dict(row)



def delete_session(token):
    """Invalidate a token by deleting its session; unknown tokens are harmless."""
    # Logout removes the session rather than the user account. Later lookups
    # with this token will no longer find a session.
    database = get_database()
    database.execute(
        "DELETE FROM session WHERE token_hash = ?",
        (hash_token(token),),
    )
    database.commit()
