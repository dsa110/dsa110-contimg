"""
Products database helpers for imaging artifacts and MS index.

Provides a single place to create/migrate the products DB schema and helper
routines to upsert ms_index rows and insert image artifacts.
"""
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional, Tuple, List


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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path)"
        )
    except Exception:
        pass
    # Index for photometry lookups by image
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_photometry_image ON photometry(image_path)"
        )
    except Exception:
        pass
    # Index for stage filtering and path lookups
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ms_index_stage_path ON ms_index(stage, path)"
        )
    except Exception:
        pass
    # Optional: index to speed up status filters
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ms_index_status ON ms_index(status)"
        )
    except Exception:
        pass
    
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
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id)
        )
        """
    )
    
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cal_qa_ms_path ON calibration_qa(ms_path)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_img_qa_ms_path ON image_qa(ms_path)"
        )
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
    stage_updated_at = (
        stage_updated_at if stage_updated_at is not None else (now if stage is not None else None)
    )
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
        'INSERT INTO images(path, ms_path, created_at, type, beam_major_arcsec, noise_jy, pbcor) '
        'VALUES(?,?,?,?,?,?,?)',
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
        'INSERT INTO photometry(image_path, ra_deg, dec_deg, nvss_flux_mjy, peak_jyb, peak_err_jyb, measured_at) '
        'VALUES(?,?,?,?,?,?,?)',
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


def _ms_time_range(ms_path: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Best-effort extraction of (start, end, mid) MJD from an MS using casatools.
    Returns (None, None, None) if unavailable.
    """
    try:
        from casatools import msmetadata  # type: ignore

        msmd = msmetadata()
        msmd.open(ms_path)
        # Preferred: explicit observation timerange in MJD days
        try:
            tr = msmd.timerangeforobs()
            if tr and isinstance(tr, (list, tuple)) and len(tr) >= 2:
                start_mjd = float(tr[0])
                end_mjd = float(tr[1])
                msmd.close()
                return start_mjd, end_mjd, 0.5 * (start_mjd + end_mjd)
        except Exception:
            pass

        # Fallback: derive from timesforscans() (seconds, MJD seconds offset)
        try:
            tmap = msmd.timesforscans()
            msmd.close()
            if isinstance(tmap, dict) and tmap:
                all_ts = [t for arr in tmap.values() for t in arr]
                if all_ts:
                    t0 = min(all_ts)
                    t1 = max(all_ts)
                    # Convert seconds to MJD days if needed
                    start_mjd = float(t0) / 86400.0
                    end_mjd = float(t1) / 86400.0
                    return start_mjd, end_mjd, 0.5 * (start_mjd + end_mjd)
        except Exception:
            pass
        msmd.close()
    except Exception:
        pass
    return None, None, None


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
            "SELECT path FROM ms_index WHERE path = ?",
            (ms_path_str,)
        ).fetchone()
        
        # Extract time range from MS
        start_mjd, end_mjd, mid_mjd = _ms_time_range(ms_path_str)
        
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


__all__ = ['ensure_products_db', 'ms_index_upsert', 'images_insert', 'photometry_insert', 'discover_ms_files']
