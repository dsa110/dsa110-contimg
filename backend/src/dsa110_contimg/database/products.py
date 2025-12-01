"""
Products database helpers for imaging artifacts and MS index.

Provides a single place to create/migrate the products DB schema and helper
routines to upsert ms_index rows and insert image artifacts.

Tables (automatically created/migrated):
  Core tables:
    - ms_index: Measurement Set tracking with pipeline stage
    - images: Image artifacts with QA metadata
    - photometry: Forced photometry measurements
    - hdf5_file_index: HDF5 subband file index

  Batch processing:
    - batch_jobs: Batch job tracking
    - batch_job_items: Individual items in batch jobs
    - calibration_qa: Calibration quality metrics
    - image_qa: Image quality metrics

  Phase 3 - Transient detection (auto-created since v0.9):
    - transient_candidates: Transient/variable source candidates
    - transient_alerts: Alert queue for transient events
    - transient_lightcurves: Time-series flux measurements
    - monitoring_sources: Sources being monitored with variability metrics

  Phase 3 - Astrometry (auto-created since v0.9):
    - astrometric_solutions: WCS correction solutions
    - astrometric_residuals: Per-source astrometric residuals

  Infrastructure:
    - storage_locations: Storage location registry for recovery
"""

import os
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


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
    # Enable WAL mode for better concurrent access (readers don't block writers)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        # If WAL mode can't be enabled (e.g., on network filesystems), continue with default
        pass
    # Set busy timeout explicitly
    conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds in milliseconds
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
            dec_deg REAL,
            pointing_ra_deg REAL,
            pointing_dec_deg REAL
        )
        """
    )
    # Ensure new pointing columns exist on upgraded databases
    ms_cols = {row[1] for row in conn.execute("PRAGMA table_info(ms_index)").fetchall()}
    for col_name, col_def in [
        ("ra_deg", "REAL"),
        ("dec_deg", "REAL"),
        ("pointing_ra_deg", "REAL"),
        ("pointing_dec_deg", "REAL"),
    ]:
        if col_name not in ms_cols:
            try:
                conn.execute(f"ALTER TABLE ms_index ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass
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
            source_id TEXT,
            image_path TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            nvss_flux_mjy REAL,
            peak_jyb REAL NOT NULL,
            peak_err_jyb REAL,
            flux_jy REAL,
            flux_err_jy REAL,
            normalized_flux_jy REAL,
            normalized_flux_err_jy REAL,
            measured_at REAL NOT NULL,
            mjd REAL,
            mosaic_path TEXT
        )
        """
    )
    # Ensure new photometry columns exist for upgraded databases
    photometry_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(photometry)").fetchall()
    }
    for col_name, col_def in [
        ("flux_jy", "REAL"),
        ("flux_err_jy", "REAL"),
        ("normalized_flux_jy", "REAL"),
        ("normalized_flux_err_jy", "REAL"),
        ("mjd", "REAL"),
        ("mosaic_path", "TEXT"),
    ]:
        if col_name not in photometry_cols:
            try:
                conn.execute(f"ALTER TABLE photometry ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass
    # Index for fast time-series lookups
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_photometry_source_mjd ON photometry(source_id, mjd)"
        )
    except sqlite3.Error:
        pass
    # Minimal index to speed lookups by Measurement Set
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path)")
    except sqlite3.Error:
        pass
    # Index for photometry lookups by image
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_photometry_image ON photometry(image_path)")
    except sqlite3.Error:
        pass
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_photometry_source_id ON photometry(source_id)")
    except sqlite3.Error:
        pass
    # Index for stage filtering and path lookups
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ms_index_stage_path ON ms_index(stage, path)")
    except sqlite3.Error:
        pass
    # Optional: index to speed up status filters
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ms_index_status ON ms_index(status)")
    except sqlite3.Error:
        pass

    # HDF5 file index for fast subband group queries
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS hdf5_file_index (
            path TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            group_id TEXT NOT NULL,
            subband_code TEXT NOT NULL,
            timestamp_iso TEXT,
            timestamp_mjd REAL,
            file_size_bytes INTEGER,
            modified_time REAL,
            indexed_at REAL NOT NULL,
            stored INTEGER DEFAULT 1,
            UNIQUE(path)
        )
        """
    )
    # Add stored column if it doesn't exist (for existing databases)
    try:
        conn.execute("ALTER TABLE hdf5_file_index ADD COLUMN stored INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # Column already exists
    # Indexes for fast queries
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hdf5_group_id ON hdf5_file_index(group_id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hdf5_timestamp_mjd ON hdf5_file_index(timestamp_mjd)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_hdf5_group_subband ON hdf5_file_index(group_id, subband_code)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hdf5_stored ON hdf5_file_index(stored)")
    except sqlite3.Error:
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
    except sqlite3.Error:
        pass

    conn.commit()

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

    # Transient candidates table (Phase 3 extended schema)
    # Note: This is the extended schema with variability tracking.
    # The simpler schema was used in early development; new columns are
    # added via migration below for existing databases.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transient_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT,
            image_path TEXT,
            ms_path TEXT,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            peak_mjy REAL,
            flux_obs_mjy REAL,
            flux_baseline_mjy REAL,
            flux_ratio REAL,
            rms_mjy REAL,
            snr REAL,
            significance_sigma REAL,
            detection_type TEXT,
            baseline_catalog TEXT,
            timestamp_mjd REAL,
            detected_at REAL NOT NULL,
            mosaic_id INTEGER,
            classification TEXT,
            variability_index REAL,
            last_updated REAL,
            notes TEXT
        )
        """
    )

    # Transient alerts table (Phase 3)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transient_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            alert_level TEXT NOT NULL,
            alert_message TEXT NOT NULL,
            created_at REAL NOT NULL,
            acknowledged INTEGER DEFAULT 0,
            acknowledged_at REAL,
            acknowledged_by TEXT,
            follow_up_status TEXT,
            notes TEXT,
            FOREIGN KEY (candidate_id) REFERENCES transient_candidates(id)
        )
        """
    )

    # Transient lightcurves table (Phase 3)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transient_lightcurves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            mjd REAL NOT NULL,
            flux_mjy REAL NOT NULL,
            flux_err_mjy REAL,
            frequency_ghz REAL,
            mosaic_id INTEGER,
            image_path TEXT,
            measured_at REAL NOT NULL,
            FOREIGN KEY (candidate_id) REFERENCES transient_candidates(id)
        )
        """
    )

    # Astrometric solutions table (Phase 3)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS astrometric_solutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mosaic_id INTEGER,
            image_path TEXT,
            reference_catalog TEXT NOT NULL,
            n_matches INTEGER NOT NULL,
            ra_offset_mas REAL NOT NULL,
            dec_offset_mas REAL NOT NULL,
            ra_offset_err_mas REAL,
            dec_offset_err_mas REAL,
            rotation_deg REAL,
            scale_factor REAL,
            rms_residual_mas REAL,
            applied INTEGER DEFAULT 0,
            computed_at REAL NOT NULL,
            applied_at REAL,
            notes TEXT
        )
        """
    )

    # Astrometric residuals table (Phase 3)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS astrometric_residuals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solution_id INTEGER NOT NULL,
            source_ra_deg REAL NOT NULL,
            source_dec_deg REAL NOT NULL,
            reference_ra_deg REAL NOT NULL,
            reference_dec_deg REAL NOT NULL,
            ra_offset_mas REAL NOT NULL,
            dec_offset_mas REAL NOT NULL,
            separation_mas REAL NOT NULL,
            source_flux_mjy REAL,
            reference_flux_mjy REAL,
            measured_at REAL NOT NULL,
            FOREIGN KEY (solution_id) REFERENCES astrometric_solutions(id)
        )
        """
    )

    # Monitoring sources table for lightcurve tracking
    # Stores sources being monitored with their variability metrics
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS monitoring_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT UNIQUE NOT NULL,
            name TEXT,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            catalog TEXT,
            priority TEXT DEFAULT 'normal',
            n_detections INTEGER DEFAULT 0,
            mean_flux_jy REAL,
            std_flux_jy REAL,
            eta REAL,
            v_index REAL,
            chi_squared REAL,
            is_variable INTEGER DEFAULT 0,
            ese_candidate INTEGER DEFAULT 0,
            first_detected_at REAL,
            last_detected_at REAL,
            last_updated REAL,
            notes TEXT
        )
        """
    )

    # Indices for batch jobs and Phase 3 tables
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_batch_items_batch_id ON batch_job_items(batch_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_batch_items_ms_path ON batch_job_items(ms_path)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cal_qa_ms_path ON calibration_qa(ms_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_img_qa_ms_path ON image_qa(ms_path)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_transient_ms_path ON transient_candidates(ms_path)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_transient_timestamp ON transient_candidates(timestamp_mjd)"
        )
        # Phase 3 indices for transient detection
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_transients_type ON transient_candidates(detection_type, significance_sigma DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_transients_coords ON transient_candidates(ra_deg, dec_deg)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_transients_detected ON transient_candidates(detected_at DESC)"
        )
        # Transient alerts indices
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_level ON transient_alerts(alert_level, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_status ON transient_alerts(acknowledged, created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_candidate ON transient_alerts(candidate_id)"
        )
        # Transient lightcurves indices
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_lightcurves_candidate ON transient_lightcurves(candidate_id, mjd)"
        )
        # Astrometric solutions indices
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_astrometry_mosaic ON astrometric_solutions(mosaic_id, computed_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_astrometry_applied ON astrometric_solutions(applied, computed_at DESC)"
        )
        # Astrometric residuals indices
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_residuals_solution ON astrometric_residuals(solution_id)"
        )
        # Monitoring sources indices
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitoring_coords ON monitoring_sources(ra_deg, dec_deg)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitoring_variable ON monitoring_sources(is_variable, eta DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_monitoring_ese ON monitoring_sources(ese_candidate)"
        )
    except sqlite3.Error:
        pass
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

        # Migrate photometry table
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='photometry'")
        if cur.fetchone() is not None:
            cur.execute("PRAGMA table_info(photometry)")
            cols = {r[1] for r in cur.fetchall()}
            if "source_id" not in cols:
                cur.execute("ALTER TABLE photometry ADD COLUMN source_id TEXT")
                # Create index for new column
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_photometry_source_id ON photometry(source_id)"
                )
                conn.commit()

        # Migrate transient_candidates table to Phase 3 extended schema
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transient_candidates'"
        )
        if cur.fetchone() is not None:
            cur.execute("PRAGMA table_info(transient_candidates)")
            cols = {r[1] for r in cur.fetchall()}
            phase3_cols = [
                ("source_name", "TEXT"),
                ("flux_obs_mjy", "REAL"),
                ("flux_baseline_mjy", "REAL"),
                ("flux_ratio", "REAL"),
                ("significance_sigma", "REAL"),
                ("detection_type", "TEXT"),
                ("baseline_catalog", "TEXT"),
                ("mosaic_id", "INTEGER"),
                ("classification", "TEXT"),
                ("variability_index", "REAL"),
                ("last_updated", "REAL"),
                ("notes", "TEXT"),
            ]
            for col_name, col_type in phase3_cols:
                if col_name not in cols:
                    try:
                        cur.execute(
                            f"ALTER TABLE transient_candidates ADD COLUMN {col_name} {col_type}"
                        )
                    except sqlite3.OperationalError:
                        pass  # Column may already exist
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


def get_products_db_connection(path: Path) -> sqlite3.Connection:
    """Get connection to the products database.

    Args:
        path: Path to the products database file

    Returns:
        Connection to the products database
    """
    return ensure_products_db(path)


def _register_default_storage_locations(conn: sqlite3.Connection) -> None:
    """Register default storage locations for recovery."""
    import time

    default_locations = [
        (
            "ms_files",
            "/stage/dsa110-contimg/raw/ms",
            "Measurement Set files (converted from HDF5)",
            "Default location for MS files after conversion",
        ),
        (
            "calibration_tables",
            "/stage/dsa110-contimg/raw/ms",
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
            "state/db/products.sqlite3",
            "Products database (relative to project root)",
            "SQLite database tracking MS files, images, and mosaics",
        ),
        (
            "registry_db",
            "state/db/cal_registry.sqlite3",
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


def register_monitoring_sources(
    conn: sqlite3.Connection,
    sources_csv: str,
    catalog: str = "user",
    default_priority: str = "normal",
) -> int:
    """Register sources for lightcurve monitoring from a CSV file.

    CSV format: name,ra,dec[,priority]
    The priority column is optional (defaults to default_priority).

    Args:
        conn: Database connection
        sources_csv: Path to CSV file with source list
        catalog: Catalog name for these sources (default: 'user')
        default_priority: Default priority if not in CSV (default: 'normal')

    Returns:
        Number of sources registered

    Example CSV:
        name,ra,dec,priority
        3C286,202.784,30.509,high
        Cygnus_A,299.868,40.734,high
        My_Target,180.0,45.0,normal
    """
    import csv

    count = 0
    now = time.time()

    with open(sources_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            ra = float(row.get("ra", row.get("ra_deg", 0)))
            dec = float(row.get("dec", row.get("dec_deg", 0)))
            priority = row.get("priority", default_priority).strip() or default_priority

            # Generate source_id from name or coordinates
            source_id = name if name else f"J{ra:.3f}{dec:+.3f}"

            conn.execute(
                """
                INSERT INTO monitoring_sources
                (source_id, name, ra_deg, dec_deg, catalog, priority, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    name = COALESCE(excluded.name, monitoring_sources.name),
                    ra_deg = excluded.ra_deg,
                    dec_deg = excluded.dec_deg,
                    catalog = excluded.catalog,
                    priority = excluded.priority,
                    last_updated = excluded.last_updated
                """,
                (source_id, name, ra, dec, catalog, priority, now),
            )
            count += 1

    conn.commit()
    return count


def get_monitoring_sources(
    conn: sqlite3.Connection,
    *,
    variable_only: bool = False,
    ese_only: bool = False,
    min_detections: int = 0,
    priority: Optional[str] = None,
    limit: int = 1000,
) -> List[dict]:
    """Get registered monitoring sources with their variability metrics.

    Args:
        conn: Database connection
        variable_only: Only return sources flagged as variable
        ese_only: Only return ESE candidates
        min_detections: Minimum number of detections required
        priority: Filter by priority level
        limit: Maximum number of sources to return

    Returns:
        List of source dictionaries with variability metrics
    """
    conditions = ["1=1"]
    params: list = []

    if variable_only:
        conditions.append("is_variable = 1")
    if ese_only:
        conditions.append("ese_candidate = 1")
    if min_detections > 0:
        conditions.append("n_detections >= ?")
        params.append(min_detections)
    if priority:
        conditions.append("priority = ?")
        params.append(priority)

    params.append(limit)
    where_clause = " AND ".join(conditions)

    rows = conn.execute(
        f"""
        SELECT source_id, name, ra_deg, dec_deg, catalog, priority,
               n_detections, mean_flux_jy, std_flux_jy, eta, v_index,
               chi_squared, is_variable, ese_candidate, first_detected_at,
               last_detected_at, notes
        FROM monitoring_sources
        WHERE {where_clause}
        ORDER BY eta DESC NULLS LAST, n_detections DESC
        LIMIT ?
        """,
        params,
    ).fetchall()

    return [
        {
            "source_id": row[0],
            "name": row[1],
            "ra_deg": row[2],
            "dec_deg": row[3],
            "catalog": row[4],
            "priority": row[5],
            "n_detections": row[6],
            "mean_flux_jy": row[7],
            "std_flux_jy": row[8],
            "eta": row[9],
            "v_index": row[10],
            "chi_squared": row[11],
            "is_variable": bool(row[12]),
            "ese_candidate": bool(row[13]),
            "first_detected_at": row[14],
            "last_detected_at": row[15],
            "notes": row[16],
        }
        for row in rows
    ]


def update_source_variability(
    conn: sqlite3.Connection,
    source_id: str,
    *,
    n_detections: Optional[int] = None,
    mean_flux_jy: Optional[float] = None,
    std_flux_jy: Optional[float] = None,
    eta: Optional[float] = None,
    v_index: Optional[float] = None,
    chi_squared: Optional[float] = None,
    is_variable: Optional[bool] = None,
    ese_candidate: Optional[bool] = None,
) -> None:
    """Update variability metrics for a monitoring source.

    Args:
        conn: Database connection
        source_id: Source identifier
        n_detections: Number of detections
        mean_flux_jy: Mean flux in Jy
        std_flux_jy: Standard deviation of flux in Jy
        eta: Variability index (eta statistic)
        v_index: Fractional variability V = std / mean
        chi_squared: Reduced chi-squared against constant model
        is_variable: Whether source is flagged as variable
        ese_candidate: Whether source is an ESE candidate
    """
    now = time.time()
    conn.execute(
        """
        UPDATE monitoring_sources SET
            n_detections = COALESCE(?, n_detections),
            mean_flux_jy = COALESCE(?, mean_flux_jy),
            std_flux_jy = COALESCE(?, std_flux_jy),
            eta = COALESCE(?, eta),
            v_index = COALESCE(?, v_index),
            chi_squared = COALESCE(?, chi_squared),
            is_variable = COALESCE(?, is_variable),
            ese_candidate = COALESCE(?, ese_candidate),
            last_updated = ?
        WHERE source_id = ?
        """,
        (
            n_detections,
            mean_flux_jy,
            std_flux_jy,
            eta,
            v_index,
            chi_squared,
            1 if is_variable else (0 if is_variable is False else None),
            1 if ese_candidate else (0 if ese_candidate is False else None),
            now,
            source_id,
        ),
    )
    conn.commit()


def extract_ms_pointing_center(ms_path: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract mean pointing center from MS FIELD table.

    Returns RA, Dec in degrees (averaged across all fields/times).
    Returns (None, None) if extraction fails.
    """
    try:
        from casatools import table

        tb = table()
        tb.open(f"{ms_path}/FIELD")
        phase_dir = tb.getcol("PHASE_DIR")
        tb.close()

        # phase_dir shape: (2, 1, n_fields) or similar
        # Extract RA (index 0) and Dec (index 1), convert rad -> deg
        ra_rad = np.mean(phase_dir[0])
        dec_rad = np.mean(phase_dir[1])
        ra_deg = float(np.degrees(ra_rad))
        dec_deg = float(np.degrees(dec_rad))
        return ra_deg, dec_deg
    except (OSError, RuntimeError, ValueError):
        # OSError: file access issues, RuntimeError: casatools errors,
        # ValueError: array/conversion issues
        return None, None


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
    pointing_ra_deg: Optional[float] = None,
    pointing_dec_deg: Optional[float] = None,
    auto_extract_coords: bool = True,
) -> None:
    """Upsert a row into ms_index, preserving existing values when None.

    Uses SQLite UPSERT with COALESCE to avoid overwriting non-null values with
    NULL entries.
    """
    # Auto-extract coordinates from MS if not provided and auto_extract_coords is True
    if auto_extract_coords and pointing_ra_deg is None and pointing_dec_deg is None:
        if os.path.exists(ms_path):
            pointing_ra_deg, pointing_dec_deg = extract_ms_pointing_center(ms_path)

    now = time.time()
    stage_updated_at = (
        stage_updated_at if stage_updated_at is not None else (now if stage is not None else None)
    )
    conn.execute(
        """
        INSERT INTO ms_index(path, start_mjd, end_mjd, mid_mjd, processed_at, status, stage, stage_updated_at, cal_applied, imagename, ra_deg, dec_deg, pointing_ra_deg, pointing_dec_deg)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            dec_deg = COALESCE(excluded.dec_deg, ms_index.dec_deg),
            pointing_ra_deg = COALESCE(excluded.pointing_ra_deg, ms_index.pointing_ra_deg),
            pointing_dec_deg = COALESCE(excluded.pointing_dec_deg, ms_index.pointing_dec_deg)
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
            pointing_ra_deg,
            pointing_dec_deg,
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
    peak_jyb: float | None,
    peak_err_jyb: float | None,
    measured_at: float,
    source_id: str | None = None,
    flux_jy: float | None = None,
    flux_err_jy: float | None = None,
    normalized_flux_jy: float | None = None,
    normalized_flux_err_jy: float | None = None,
    mjd: float | None = None,
    mosaic_path: str | None = None,
) -> None:
    """Insert a forced photometry measurement."""
    flux_val = peak_jyb if flux_jy is None else flux_jy
    flux_err_val = peak_err_jyb if flux_err_jy is None else flux_err_jy
    norm_flux_val = (
        flux_val if normalized_flux_jy is None else normalized_flux_jy
    )
    norm_flux_err_val = (
        flux_err_val if normalized_flux_err_jy is None else normalized_flux_err_jy
    )
    mjd_val = mjd if mjd is not None else (measured_at / 86400.0 + 40587.0)
    conn.execute(
        "INSERT INTO photometry(source_id, image_path, ra_deg, dec_deg, nvss_flux_mjy, peak_jyb, peak_err_jyb, flux_jy, flux_err_jy, normalized_flux_jy, normalized_flux_err_jy, measured_at, mjd, mosaic_path) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            source_id,
            image_path,
            ra_deg,
            dec_deg,
            nvss_flux_mjy,
            peak_jyb,
            peak_err_jyb,
            flux_val,
            flux_err_val,
            norm_flux_val,
            norm_flux_err_val,
            measured_at,
            mjd_val,
            mosaic_path,
        ),
    )


def transient_candidate_insert(
    conn: sqlite3.Connection,
    *,
    image_path: str,
    ms_path: str,
    ra_deg: float,
    dec_deg: float,
    peak_mjy: float,
    rms_mjy: float,
    snr: float,
    timestamp_mjd: Optional[float] = None,
) -> int:
    """Insert a transient candidate.

    Returns:
        ID of the inserted row
    """
    import time

    if timestamp_mjd is None:
        # Try to extract from MS path or use current time
        timestamp_mjd = time.time() / 86400.0 + 40587.0  # Very rough approximation if needed

    cursor = conn.execute(
        """
        INSERT INTO transient_candidates(
            image_path, ms_path, ra_deg, dec_deg, peak_mjy, rms_mjy, snr, timestamp_mjd, detected_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            image_path,
            ms_path,
            ra_deg,
            dec_deg,
            peak_mjy,
            rms_mjy,
            snr,
            timestamp_mjd,
            time.time(),
        ),
    )
    return cursor.lastrowid


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

        # Check if already registered (result not used, just checking existence)
        _ = conn.execute("SELECT path FROM ms_index WHERE path = ?", (ms_path_str,)).fetchone()

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


def ensure_ingest_db(path: Path) -> sqlite3.Connection:
    """Open or create the ingest SQLite DB and ensure pointing_history table exists.

    This function creates the pointing_history table in the ingest database.
    The ingest database is used for tracking raw observation data, while
    products database is reserved for processed data products.

    Tables:
      - pointing_history(timestamp PRIMARY KEY, ra_deg, dec_deg)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Add timeout to prevent hanging on locked database
    conn = sqlite3.connect(os.fspath(path), timeout=30.0)
    # Enable WAL mode for better concurrent access
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass

    # Table for pointing history (moved from products database)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pointing_history (
            timestamp REAL PRIMARY KEY,
            ra_deg REAL,
            dec_deg REAL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pointing_timestamp ON pointing_history(timestamp)")

    conn.commit()
    return conn


__all__ = [
    "ensure_products_db",
    "ensure_ingest_db",
    "ms_index_upsert",
    "images_insert",
    "photometry_insert",
    "transient_candidate_insert",
    "discover_ms_files",
]
