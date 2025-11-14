"""
Products database helpers for imaging artifacts and MS index.

Provides a single place to create/migrate the products DB schema and helper
routines to upsert ms_index rows and insert image artifacts.
"""

import os
import sqlite3
import time
from pathlib import Path
from typing import List, Optional


def ensure_products_db(path: Path) -> sqlite3.Connection:
    """Open or create the products SQLite DB and ensure schema exists.

    Tables:
      - ms_index(path PRIMARY KEY, start_mjd, end_mjd, mid_mjd, processed_at,
        status, stage, stage_updated_at, cal_applied, imagename)
      - images(id PRIMARY KEY, path, ms_path, created_at, type,
        beam_major_arcsec, noise_jy, pbcor)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Add timeout to prevent hanging on locked database
    conn = sqlite3.connect(os.fspath(path), timeout=30.0)
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
            imagename TEXT,
            ra_deg REAL,
            dec_deg REAL
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
    # Photometry results table (forced photometry on images)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS photometry (
            id INTEGER PRIMARY KEY,
            image_path TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            nvss_flux_mjy REAL,
            peak_jyb REAL NOT NULL,
            peak_err_jyb REAL,
            measured_at REAL NOT NULL
        )
        """
    )
    # Minimal index to speed lookups by Measurement Set
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path)")
    except Exception:
        pass
    # Index for photometry lookups by image
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_photometry_image ON photometry(image_path)")
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

    # Storage locations registry for recovery
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS storage_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_type TEXT NOT NULL,
            base_path TEXT NOT NULL,
            description TEXT,
            registered_at REAL NOT NULL,
            status TEXT DEFAULT 'active',
            notes TEXT,
            UNIQUE(location_type, base_path)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_storage_locations_type ON storage_locations(location_type, status)"
    )

    # Auto-register default storage locations if table is empty
    try:
        existing = conn.execute("SELECT COUNT(*) FROM storage_locations").fetchone()[0]
        if existing == 0:
            _register_default_storage_locations(conn)
    except Exception:
        pass

    conn.commit()
    return conn


def _register_default_storage_locations(conn: sqlite3.Connection) -> None:
    """Register default storage locations for recovery."""
    import time

    default_locations = [
        (
            "ms_files",
            "/stage/dsa110-contimg/ms",
            "Measurement Set files (converted from HDF5)",
            "Default location for MS files after conversion",
        ),
        (
            "calibration_tables",
            "/stage/dsa110-contimg/ms",
            "Calibration tables (BP, GP, 2G) stored alongside MS files",
            "Calibration tables are stored in same directory as MS files",
        ),
        (
            "images",
            "/stage/dsa110-contimg/images",
            "Individual tile images (before mosaicking)",
            "Images created from calibrated MS files",
        ),
        (
            "mosaics",
            "/stage/dsa110-contimg/mosaics",
            "Final mosaic images (combined from tiles)",
            "Output location for completed mosaics",
        ),
        (
            "hdf5_staging",
            "/stage/dsa110-contimg/hdf5",
            "HDF5 files staged for conversion (temporary)",
            "HDF5 files moved here from incoming before conversion",
        ),
        (
            "hdf5_incoming",
            "/data/incoming",
            "HDF5 files in incoming directory (never auto-deleted)",
            "Original HDF5 files - never automatically removed",
        ),
        (
            "products_db",
            "state/products.sqlite3",
            "Products database (relative to project root)",
            "SQLite database tracking MS files, images, and mosaics",
        ),
        (
            "registry_db",
            "state/cal_registry.sqlite3",
            "Calibration registry database (relative to project root)",
            "SQLite database tracking calibration table validity windows",
        ),
    ]

    now = time.time()
    for loc_type, base_path, description, notes in default_locations:
        # Resolve relative paths
        if not base_path.startswith("/"):
            # Assume relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            resolved_path = str(project_root / base_path)
        else:
            resolved_path = base_path

        conn.execute(
            """
            INSERT OR IGNORE INTO storage_locations
            (location_type, base_path, description, registered_at, status, notes)
            VALUES (?, ?, ?, ?, 'active', ?)
            """,
            (loc_type, resolved_path, description, now, notes),
        )


def register_storage_location(
    conn: sqlite3.Connection,
    location_type: str,
    base_path: str,
    description: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    """Register a storage location for recovery purposes.

    Args:
        conn: Database connection
        location_type: Type of storage (e.g., 'ms_files', 'calibration_tables', 'images')
        base_path: Base directory path where files are stored
        description: Human-readable description
        notes: Additional notes
    """
    import time

    conn.execute(
        """
        INSERT OR REPLACE INTO storage_locations
        (location_type, base_path, description, registered_at, status, notes)
        VALUES (?, ?, ?, ?, 'active', ?)
        """,
        (location_type, base_path, description, time.time(), notes),
    )
    conn.commit()


def get_storage_locations(
    conn: sqlite3.Connection,
    location_type: Optional[str] = None,
    status: str = "active",
) -> List[dict]:
    """Get registered storage locations.

    Args:
        conn: Database connection
        location_type: Filter by type (None for all types)
        status: Filter by status (default: 'active')

    Returns:
        List of dictionaries with location info
    """
    if location_type:
        rows = conn.execute(
            """
            SELECT location_type, base_path, description, registered_at, notes
            FROM storage_locations
            WHERE location_type = ? AND status = ?
            ORDER BY registered_at DESC
            """,
            (location_type, status),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT location_type, base_path, description, registered_at, notes
            FROM storage_locations
            WHERE status = ?
            ORDER BY location_type, registered_at DESC
            """,
            (status,),
        ).fetchall()

    return [
        {
            "type": row[0],
            "base_path": row[1],
            "description": row[2],
            "registered_at": row[3],
            "notes": row[4],
        }
        for row in rows
    ]

    # Batch jobs table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            total_items INTEGER NOT NULL,
            completed_items INTEGER DEFAULT 0,
            failed_items INTEGER DEFAULT 0,
            params TEXT
        )
        """
    )

    # Batch job items table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS batch_job_items (
            id INTEGER PRIMARY KEY,
            batch_id INTEGER NOT NULL,
            ms_path TEXT NOT NULL,
            job_id INTEGER,
            status TEXT NOT NULL,
            error TEXT,
            started_at REAL,
            completed_at REAL,
            data_id TEXT DEFAULT NULL,
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
        )
        """
    )
    # Migrate existing tables to add data_id column if it doesn't exist
    try:
        conn.execute("SELECT data_id FROM batch_job_items LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        try:
            conn.execute("ALTER TABLE batch_job_items ADD COLUMN data_id TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass  # Column may already exist from concurrent creation

    # Calibration QA metrics table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS calibration_qa (
            id INTEGER PRIMARY KEY,
            ms_path TEXT NOT NULL,
            job_id INTEGER NOT NULL,
            k_metrics TEXT,
            bp_metrics TEXT,
            g_metrics TEXT,
            overall_quality TEXT,
            flags_total REAL,
            per_spw_stats TEXT,
            timestamp REAL NOT NULL
        )
        """
    )

    # Image QA metrics table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS image_qa (
            id INTEGER PRIMARY KEY,
            ms_path TEXT NOT NULL,
            job_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            rms_noise REAL,
            peak_flux REAL,
            dynamic_range REAL,
            beam_major REAL,
            beam_minor REAL,
            beam_pa REAL,
            num_sources INTEGER,
            thumbnail_path TEXT,
            overall_quality TEXT,
            timestamp REAL NOT NULL
        )
        """
    )

    # Indices for batch jobs
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_batch_items_batch_id ON batch_job_items(batch_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_batch_items_ms_path ON batch_job_items(ms_path)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cal_qa_ms_path ON calibration_qa(ms_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_img_qa_ms_path ON image_qa(ms_path)")
    except Exception:
        pass
    # Table for pointing history
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pointing_history (
            timestamp REAL PRIMARY KEY,
            ra_deg REAL,
            dec_deg REAL
        )
        """
    )
    # Lightweight migrations to add missing columns
    # Only migrate if table exists (it's created above)
    try:
        cur = conn.cursor()
        # Check if table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ms_index'")
        if cur.fetchone() is None:
            # Table doesn't exist yet, no migration needed
            return conn

        cur.execute("PRAGMA table_info(ms_index)")
        cols = {r[1] for r in cur.fetchall()}
        migrations_applied = False
        if "stage" not in cols:
            cur.execute("ALTER TABLE ms_index ADD COLUMN stage TEXT")
            migrations_applied = True
        if "stage_updated_at" not in cols:
            cur.execute("ALTER TABLE ms_index ADD COLUMN stage_updated_at REAL")
            migrations_applied = True
        if "cal_applied" not in cols:
            cur.execute("ALTER TABLE ms_index ADD COLUMN cal_applied INTEGER DEFAULT 0")
            migrations_applied = True
        if "imagename" not in cols:
            cur.execute("ALTER TABLE ms_index ADD COLUMN imagename TEXT")
            migrations_applied = True
        if "ra_deg" not in cols:
            cur.execute("ALTER TABLE ms_index ADD COLUMN ra_deg REAL")
            migrations_applied = True
        if "dec_deg" not in cols:
            cur.execute("ALTER TABLE ms_index ADD COLUMN dec_deg REAL")
            migrations_applied = True
        if migrations_applied:
            conn.commit()
    except Exception as e:
        # Log the error but don't fail - migration errors are non-fatal
        # The table will still work, just without the new columns
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to migrate ms_index table: {e}")
        # Re-raise if it's a critical error (like table doesn't exist when it should)
        if "no such table" not in str(e).lower():
            raise
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
    ra_deg: Optional[float] = None,
    dec_deg: Optional[float] = None,
) -> None:
    """Upsert a row into ms_index, preserving existing values when None.

    Uses SQLite UPSERT with COALESCE to avoid overwriting non-null values with
    NULL entries.
    """
    now = time.time()
    stage_updated_at = (
        stage_updated_at if stage_updated_at is not None else (now if stage is not None else None)
    )
    conn.execute(
        """
        INSERT INTO ms_index(path, start_mjd, end_mjd, mid_mjd, processed_at, status, stage, stage_updated_at, cal_applied, imagename, ra_deg, dec_deg)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            start_mjd = COALESCE(excluded.start_mjd, ms_index.start_mjd),
            end_mjd = COALESCE(excluded.end_mjd, ms_index.end_mjd),
            mid_mjd = COALESCE(excluded.mid_mjd, ms_index.mid_mjd),
            processed_at = COALESCE(excluded.processed_at, ms_index.processed_at),
            status = COALESCE(excluded.status, ms_index.status),
            stage = COALESCE(excluded.stage, ms_index.stage),
            stage_updated_at = COALESCE(excluded.stage_updated_at, ms_index.stage_updated_at),
            cal_applied = COALESCE(excluded.cal_applied, ms_index.cal_applied),
            imagename = COALESCE(excluded.imagename, ms_index.imagename),
            ra_deg = COALESCE(excluded.ra_deg, ms_index.ra_deg),
            dec_deg = COALESCE(excluded.dec_deg, ms_index.dec_deg)
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
            ra_deg,
            dec_deg,
        ),
    )


def log_pointing(
    conn: sqlite3.Connection,
    timestamp_mjd: float,
    ra_deg: float,
    dec_deg: float,
) -> None:
    """Log pointing to pointing_history table.

    Args:
        conn: Database connection
        timestamp_mjd: Observation timestamp (MJD)
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
    """
    conn.execute(
        """
        INSERT OR REPLACE INTO pointing_history (timestamp, ra_deg, dec_deg)
        VALUES (?, ?, ?)
        """,
        (timestamp_mjd, ra_deg, dec_deg),
    )
    conn.commit()


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
        "INSERT INTO images(path, ms_path, created_at, type, beam_major_arcsec, noise_jy, pbcor) "
        "VALUES(?,?,?,?,?,?,?)",
        (
            path,
            ms_path,
            created_at,
            img_type,
            beam_major_arcsec,
            noise_jy,
            pbcor,
        ),
    )


def photometry_insert(
    conn: sqlite3.Connection,
    *,
    image_path: str,
    ra_deg: float,
    dec_deg: float,
    nvss_flux_mjy: float | None,
    peak_jyb: float,
    peak_err_jyb: float | None,
    measured_at: float,
) -> None:
    """Insert a forced photometry measurement."""
    conn.execute(
        "INSERT INTO photometry(image_path, ra_deg, dec_deg, nvss_flux_mjy, peak_jyb, peak_err_jyb, measured_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (
            image_path,
            ra_deg,
            dec_deg,
            nvss_flux_mjy,
            peak_jyb,
            peak_err_jyb,
            measured_at,
        ),
    )


def discover_ms_files(
    db_path: Path,
    scan_dir: str | Path,
    *,
    recursive: bool = True,
    status: str = "discovered",
    stage: str = "discovered",
) -> List[str]:
    """Scan filesystem for MS files and register them in the database.

    Args:
        db_path: Path to products database
        scan_dir: Directory to scan for MS files
        recursive: If True, scan subdirectories recursively
        status: Status to assign to newly discovered MS files
        stage: Stage to assign to newly discovered MS files

    Returns:
        List of MS file paths that were registered (new or updated)
    """
    scan_path = Path(scan_dir)
    if not scan_path.exists():
        return []

    conn = ensure_products_db(db_path)
    registered = []

    # Find all MS files
    if recursive:
        ms_files = list(scan_path.rglob("*.ms"))
    else:
        ms_files = list(scan_path.glob("*.ms"))

    # Filter to only directories (MS files are directories)
    ms_files = [ms for ms in ms_files if ms.is_dir()]

    for ms_path in ms_files:
        ms_path_str = os.fspath(ms_path)

        # Check if already registered
        existing = conn.execute(
            "SELECT path FROM ms_index WHERE path = ?", (ms_path_str,)
        ).fetchone()

        # Extract time range from MS using standardized utility
        from dsa110_contimg.utils.time_utils import extract_ms_time_range

        start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path_str)

        # Use current time in MJD as fallback if extraction failed
        if mid_mjd is None:
            from astropy.time import Time

            mid_mjd = Time.now().mjd

        # Register/update in database
        ms_index_upsert(
            conn,
            ms_path_str,
            start_mjd=start_mjd,
            end_mjd=end_mjd,
            mid_mjd=mid_mjd,
            status=status,
            stage=stage,
            processed_at=time.time(),
        )
        registered.append(ms_path_str)

    conn.commit()
    conn.close()

    return registered


__all__ = [
    "ensure_products_db",
    "ms_index_upsert",
    "images_insert",
    "photometry_insert",
    "discover_ms_files",
]
