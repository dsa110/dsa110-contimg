"""
Products database helpers for imaging artifacts and MS index.

Provides a single place to create/migrate the products DB schema and helper
routines to upsert ms_index rows and insert image artifacts.
"""
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional


def ensure_products_db(path: Path) -> sqlite3.Connection:
    """Open or create the products SQLite DB and ensure schema exists.

    Tables:
      - ms_index(path PRIMARY KEY, start_mjd, end_mjd, mid_mjd, processed_at,
                 status, stage, stage_updated_at, cal_applied, imagename)
      - images(id PRIMARY KEY, path, ms_path, created_at, type, beam_major_arcsec,
               noise_jy, pbcor)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(os.fspath(path))
    # Base tables
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ms_index (
            path TEXT PRIMARY KEY,
            start_mjd REAL,
            end_mjd REAL,
            mid_mjd REAL,
            processed_at REAL,
            status TEXT,
            stage TEXT,
            stage_updated_at REAL,
            cal_applied INTEGER DEFAULT 0,
            imagename TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            ms_path TEXT NOT NULL,
            created_at REAL NOT NULL,
            type TEXT NOT NULL,
            beam_major_arcsec REAL,
            noise_jy REAL,
            pbcor INTEGER DEFAULT 0
        )
        """
    )
    # Minimal index to speed lookups by Measurement Set
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path)")
    except Exception:
        pass
    # Index for stage filtering and path lookups
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ms_index_stage_path ON ms_index(stage, path)")
    except Exception:
        pass
    # Optional: index to speed up status filters
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ms_index_status ON ms_index(status)")
    except Exception:
        pass
    # Lightweight migrations to add missing columns
    try:
        cols = {r[1] for r in conn.execute('PRAGMA table_info(ms_index)').fetchall()}
        cur = conn.cursor()
        if 'stage' not in cols:
            cur.execute('ALTER TABLE ms_index ADD COLUMN stage TEXT')
        if 'stage_updated_at' not in cols:
            cur.execute('ALTER TABLE ms_index ADD COLUMN stage_updated_at REAL')
        if 'cal_applied' not in cols:
            cur.execute('ALTER TABLE ms_index ADD COLUMN cal_applied INTEGER DEFAULT 0')
        if 'imagename' not in cols:
            cur.execute('ALTER TABLE ms_index ADD COLUMN imagename TEXT')
        conn.commit()
    except Exception:
        pass
    return conn


def ms_index_upsert(
    conn: sqlite3.Connection,
    ms_path: str,
    *,
    start_mjd: Optional[float] = None,
    end_mjd: Optional[float] = None,
    mid_mjd: Optional[float] = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    cal_applied: Optional[int] = None,
    imagename: Optional[str] = None,
    processed_at: Optional[float] = None,
    stage_updated_at: Optional[float] = None,
) -> None:
    """Upsert a row into ms_index, preserving existing values when None.

    Uses SQLite UPSERT with COALESCE to avoid overwriting non-null values with
    NULL entries.
    """
    now = time.time()
    stage_updated_at = stage_updated_at if stage_updated_at is not None else (now if stage is not None else None)
    conn.execute(
        """
        INSERT INTO ms_index(path, start_mjd, end_mjd, mid_mjd, processed_at, status, stage, stage_updated_at, cal_applied, imagename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            start_mjd = COALESCE(excluded.start_mjd, ms_index.start_mjd),
            end_mjd = COALESCE(excluded.end_mjd, ms_index.end_mjd),
            mid_mjd = COALESCE(excluded.mid_mjd, ms_index.mid_mjd),
            processed_at = COALESCE(excluded.processed_at, ms_index.processed_at),
            status = COALESCE(excluded.status, ms_index.status),
            stage = COALESCE(excluded.stage, ms_index.stage),
            stage_updated_at = COALESCE(excluded.stage_updated_at, ms_index.stage_updated_at),
            cal_applied = COALESCE(excluded.cal_applied, ms_index.cal_applied),
            imagename = COALESCE(excluded.imagename, ms_index.imagename)
        """,
        (
            ms_path,
            start_mjd,
            end_mjd,
            mid_mjd,
            processed_at,
            status,
            stage,
            stage_updated_at,
            cal_applied,
            imagename,
        ),
    )


def images_insert(
    conn: sqlite3.Connection,
    path: str,
    ms_path: str,
    created_at: float,
    img_type: str,
    pbcor: int,
    *,
    beam_major_arcsec: Optional[float] = None,
    noise_jy: Optional[float] = None,
) -> None:
    """Insert an image artifact record."""
    conn.execute(
        'INSERT INTO images(path, ms_path, created_at, type, beam_major_arcsec, noise_jy, pbcor) VALUES(?,?,?,?,?,?,?)',
        (path, ms_path, created_at, img_type, beam_major_arcsec, noise_jy, pbcor),
    )


__all__ = ['ensure_products_db', 'ms_index_upsert', 'images_insert']
