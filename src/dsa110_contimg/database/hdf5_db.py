"""HDF5 database management for input data tracking.

This database tracks incoming HDF5 visibility files, separate from the
products database which tracks pipeline outputs (MS files, images, etc.).

Database: /data/dsa110-contimg/state/hdf5.sqlite3
"""

import os
import sqlite3
from pathlib import Path


def ensure_hdf5_db(path: Path) -> sqlite3.Connection:
    """Open or create HDF5 input data DB and ensure schema exists.

    Tables:
      - hdf5_file_index: HDF5 files for fast subband group queries
      - storage_locations: Storage location configuration

    Args:
        path: Path to HDF5 database file

    Returns:
        SQLite connection
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # HDF5 file index for fast subband group queries
    # Note: ra_deg, dec_deg, obs_date, obs_time are only populated for sb00 files
    # (first subband in each group), others use group_id to find their metadata
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS hdf5_file_index (
            path TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            group_id TEXT NOT NULL,
            subband_code TEXT NOT NULL,
            subband_num INTEGER,
            timestamp_iso TEXT NOT NULL,
            timestamp_mjd REAL NOT NULL,
            file_size_bytes INTEGER,
            modified_time REAL,
            indexed_at REAL,
            stored INTEGER DEFAULT 1,
            ra_deg REAL,
            dec_deg REAL,
            obs_date TEXT,
            obs_time TEXT
        )
        """
    )

    # Add columns if they don't exist (for existing databases)
    try:
        conn.execute("ALTER TABLE hdf5_file_index ADD COLUMN stored INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute("ALTER TABLE hdf5_file_index ADD COLUMN subband_num INTEGER")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute("ALTER TABLE hdf5_file_index ADD COLUMN ra_deg REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute("ALTER TABLE hdf5_file_index ADD COLUMN dec_deg REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute("ALTER TABLE hdf5_file_index ADD COLUMN obs_date TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute("ALTER TABLE hdf5_file_index ADD COLUMN obs_time TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Indexes for fast queries
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hdf5_group_id ON hdf5_file_index(group_id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hdf5_timestamp_mjd " "ON hdf5_file_index(timestamp_mjd)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hdf5_group_subband "
            "ON hdf5_file_index(group_id, subband_code)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hdf5_stored ON hdf5_file_index(stored)")
        # Indexes for spatial/temporal queries
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hdf5_ra_dec " "ON hdf5_file_index(ra_deg, dec_deg)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hdf5_obs_date ON hdf5_file_index(obs_date)")
        # Index for subband ordering
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hdf5_subband_num " "ON hdf5_file_index(subband_num)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hdf5_group_subband_num "
            "ON hdf5_file_index(group_id, subband_num)"
        )
    except Exception:
        pass

    # Storage locations (optional, may be shared with products DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS storage_locations (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            path TEXT NOT NULL,
            description TEXT
        )
        """
    )

    conn.commit()
    return conn


def get_hdf5_db_path() -> Path:
    """Get HDF5 database path from environment or default.

    Environment variable: HDF5_DB_PATH
    Default: /data/dsa110-contimg/state/hdf5.sqlite3

    Returns:
        Path to HDF5 database
    """
    db_path = os.getenv("HDF5_DB_PATH", "state/hdf5.sqlite3")
    path = Path(db_path)

    # If relative path, resolve relative to project root
    if not path.is_absolute():
        # Try common locations
        for base_dir in [
            "/data/dsa110-contimg",
            "/stage/dsa110-contimg",
            os.getcwd(),
        ]:
            candidate = Path(base_dir) / path
            if candidate.exists() or Path(base_dir).exists():
                return candidate
        # Default to /data/dsa110-contimg/state/
        return Path("/data/dsa110-contimg") / path

    return path
