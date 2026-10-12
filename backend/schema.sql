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
