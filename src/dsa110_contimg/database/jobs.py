"""Job tracking database utilities for the control panel."""

from __future__ import annotations

import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any


def ensure_jobs_table(conn: sqlite3.Connection) -> None:
    """Create jobs table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            ms_path TEXT NOT NULL,
            params TEXT,
            logs TEXT,
            artifacts TEXT,
            created_at REAL NOT NULL,
            started_at REAL,
            finished_at REAL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)")
    conn.commit()


def create_job(
    conn: sqlite3.Connection,
    job_type: str,
    ms_path: str,
    params: Dict[str, Any]
) -> int:
    """Create a new job and return its ID."""
    ensure_jobs_table(conn)
    cursor = conn.execute(
        """
        INSERT INTO jobs (type, status, ms_path, params, created_at, logs, artifacts)
        VALUES (?, 'pending', ?, ?, ?, '', '[]')
        """,
        (job_type, ms_path, json.dumps(params), time.time())
    )
    conn.commit()
    return cursor.lastrowid


def update_job_status(
    conn: sqlite3.Connection,
    job_id: int,
    status: str,
    **kwargs
) -> None:
    """Update job status and optional fields (started_at, finished_at, artifacts)."""
    updates = ["status = ?"]
    values = [status]
    
    if "started_at" in kwargs:
        updates.append("started_at = ?")
        values.append(kwargs["started_at"])
    
    if "finished_at" in kwargs:
        updates.append("finished_at = ?")
        values.append(kwargs["finished_at"])
    
    if "artifacts" in kwargs:
        updates.append("artifacts = ?")
        values.append(kwargs["artifacts"])
    
    values.append(job_id)
    
    conn.execute(
        f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?",
        values
    )
    conn.commit()


def append_job_log(conn: sqlite3.Connection, job_id: int, line: str) -> None:
    """Append a log line to a job's logs."""
    conn.execute(
        "UPDATE jobs SET logs = logs || ? WHERE id = ?",
        (line, job_id)
    )
    # Don't commit every line; caller should batch commits


def get_job(conn: sqlite3.Connection, job_id: int) -> Optional[Dict[str, Any]]:
    """Get a single job by ID."""
    ensure_jobs_table(conn)
    row = conn.execute(
        "SELECT * FROM jobs WHERE id = ?",
        (job_id,)
    ).fetchone()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "type": row[1],
        "status": row[2],
        "ms_path": row[3],
        "params": json.loads(row[4]) if row[4] else {},
        "logs": row[5] or "",
        "artifacts": json.loads(row[6]) if row[6] else [],
        "created_at": row[7],
        "started_at": row[8],
        "finished_at": row[9],
    }


def list_jobs(
    conn: sqlite3.Connection,
    limit: int = 50,
    status: Optional[str] = None
) -> list:
    """List jobs with optional status filter."""
    ensure_jobs_table(conn)
    
    if status:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    
    jobs = []
    for row in rows:
        jobs.append({
            "id": row[0],
            "type": row[1],
            "status": row[2],
            "ms_path": row[3],
            "params": json.loads(row[4]) if row[4] else {},
            "logs": row[5] or "",
            "artifacts": json.loads(row[6]) if row[6] else [],
            "created_at": row[7],
            "started_at": row[8],
            "finished_at": row[9],
        })
    
    return jobs

