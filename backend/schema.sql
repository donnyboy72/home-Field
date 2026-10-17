-- The task table is the host database's authoritative task record.
-- Project and user ID columns are nullable for now because those features have
-- not been implemented yet. Foreign-key constraints can be added when the
-- project and user tables are introduced.
CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'todo'
        CHECK (status IN ('todo', 'in_progress', 'review', 'done')),
    deadline TEXT,
    project_id INTEGER,
    created_by INTEGER,
    assigned_to INTEGER,
    is_deleted INTEGER NOT NULL DEFAULT 0
        CHECK (is_deleted IN (0, 1)),
    deleted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- This table is used to store users
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
);

-- This table is used to store sessions for users
-- Allowing for host to remember users and keep them logged in for a period of time
CREATE TABLE IF NOT EXISTS session (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user(id),
    expires_at TEXT NOT NULL,
);
