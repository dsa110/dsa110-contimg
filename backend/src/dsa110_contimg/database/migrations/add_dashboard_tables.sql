-- Dashboard Feature Tables Migration
-- Run: sqlite3 pipeline.sqlite3 < add_dashboard_tables.sql
-- Idempotent: safe to run multiple times

-- Saved Queries (shared filters feature)
CREATE TABLE IF NOT EXISTS saved_queries (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    filters TEXT NOT NULL,  -- JSON: serialized FilterState
    target_type TEXT NOT NULL,  -- 'images', 'sources', 'jobs', 'ms'
    visibility TEXT DEFAULT 'private' CHECK (visibility IN ('private', 'team', 'public')),
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_saved_queries_visibility ON saved_queries(visibility);
CREATE INDEX IF NOT EXISTS idx_saved_queries_target ON saved_queries(target_type);
CREATE INDEX IF NOT EXISTS idx_saved_queries_created_by ON saved_queries(created_by);

-- Backup History
CREATE TABLE IF NOT EXISTS backup_history (
    id TEXT PRIMARY KEY,
    backup_path TEXT NOT NULL,
    backup_type TEXT NOT NULL CHECK (backup_type IN ('full', 'incremental', 'database_only', 'caltables_only')),
    size_bytes INTEGER,
    checksum TEXT,  -- SHA256 for validation
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT,
    status TEXT DEFAULT 'completed' CHECK (status IN ('in_progress', 'completed', 'failed', 'deleted')),
    validation_status TEXT CHECK (validation_status IN ('valid', 'invalid', 'unchecked')),
    validated_at TEXT,
    error_message TEXT,
    metadata TEXT  -- JSON: additional backup info
);
CREATE INDEX IF NOT EXISTS idx_backup_history_status ON backup_history(status);
CREATE INDEX IF NOT EXISTS idx_backup_history_created ON backup_history(created_at);

-- Export Jobs (VO export feature)
CREATE TABLE IF NOT EXISTS export_jobs (
    id TEXT PRIMARY KEY,
    export_type TEXT NOT NULL CHECK (export_type IN ('votable', 'csv', 'fits', 'tar')),
    target_type TEXT NOT NULL,  -- 'sources', 'images', 'ms', 'catalog'
    query_params TEXT,  -- JSON: filter/selection parameters
    output_path TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    progress_pct INTEGER DEFAULT 0,
    total_items INTEGER,
    processed_items INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT,
    created_by TEXT,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_export_jobs_status ON export_jobs(status);
CREATE INDEX IF NOT EXISTS idx_export_jobs_created ON export_jobs(created_at);

-- Trigger to auto-update updated_at on saved_queries
CREATE TRIGGER IF NOT EXISTS saved_queries_updated_at
    AFTER UPDATE ON saved_queries
    FOR EACH ROW
BEGIN
    UPDATE saved_queries SET updated_at = datetime('now') WHERE id = NEW.id;
END;
