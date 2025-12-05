"""
Build per-declination strip SQLite databases from source catalogs.

These databases are optimized for fast spatial queries during long-term
drift scan operations at fixed declinations.
"""

from __future__ import annotations

import fcntl
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Catalog coverage limits (declination ranges)
CATALOG_COVERAGE_LIMITS = {
    "nvss": {"dec_min": -40.0, "dec_max": 90.0},
    "first": {"dec_min": -40.0, "dec_max": 90.0},
    "rax": {"dec_min": -90.0, "dec_max": 49.9},
    "vlass": {"dec_min": -40.0, "dec_max": 90.0},  # VLA Sky Survey
    "atnf": {"dec_min": -90.0, "dec_max": 90.0},  # All-sky pulsar catalog
}

# Default cache directory for catalog files
DEFAULT_CACHE_DIR = "/data/dsa110-contimg/.cache/catalogs"


def _acquire_db_lock(
    lock_path: Path, timeout_sec: float = 300.0, max_retries: int = 10
) -> Optional[int]:
    """Acquire an exclusive lock on a database build operation.

    Args:
        lock_path: Path to lock file
        timeout_sec: Maximum time to wait for lock (default: 300s = 5min)
        max_retries: Maximum number of retry attempts (default: 10)

    Returns:
        File descriptor if lock acquired, None if timeout
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock_file = open(lock_path, "w")
    start_time = time.time()
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Success!
            return lock_file.fileno()
        except BlockingIOError:
            # Lock is held by another process
            elapsed = time.time() - start_time
            if elapsed > timeout_sec:
                logger.warning(
                    f"Timeout waiting for database lock {lock_path} "
                    f"(waited {elapsed:.1f}s, timeout={timeout_sec}s)"
                )
                lock_file.close()
                return None

            # Wait before retrying (exponential backoff)
            wait_time = min(2.0**retry_count, 10.0)
            time.sleep(wait_time)
            retry_count += 1
        except Exception as e:
            logger.error(f"Error acquiring database lock {lock_path}: {e}")
            lock_file.close()
            return None

    lock_file.close()
    return None


def _release_db_lock(lock_fd: Optional[int], lock_path: Path):
    """Release a database lock.

    Args:
        lock_fd: File descriptor from _acquire_db_lock()
        lock_path: Path to lock file
    """
    if lock_fd is not None:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except Exception as e:
            logger.warning(f"Error releasing database lock {lock_path}: {e}")

    # Remove lock file if it exists
    try:
        if lock_path.exists():
            lock_path.unlink()
    except Exception as e:
        logger.warning(f"Error removing lock file {lock_path}: {e}")


# --------------------------------------------------------------------------
# Full catalog database builders (one-time operations)
# --------------------------------------------------------------------------

# Default path for full NVSS database
NVSS_FULL_DB_PATH = Path("/data/dsa110-contimg/state/catalogs/nvss_full.sqlite3")


def get_nvss_full_db_path() -> Path:
    """Get the path to the full NVSS database.

    Returns:
        Path to nvss_full.sqlite3
    """
    return NVSS_FULL_DB_PATH


def nvss_full_db_exists() -> bool:
    """Check if the full NVSS database exists.

    Returns:
        True if nvss_full.sqlite3 exists and has data
    """
    db_path = get_nvss_full_db_path()
    if not db_path.exists():
        return False

    # Verify it has data
    try:
        with sqlite3.connect(str(db_path)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            return count > 0
    except Exception:
        return False


def build_nvss_full_db(
    output_path: Optional[Path] = None,
    force_rebuild: bool = False,
) -> Path:
    """Build a full NVSS SQLite database from the raw HEASARC file.

    This creates a comprehensive database with all ~1.77M NVSS sources,
    indexed for fast spatial queries. Dec strip databases can then be
    built efficiently from this database instead of re-parsing the raw file.

    Args:
        output_path: Output database path (default: state/catalogs/nvss_full.sqlite3)
        force_rebuild: If True, rebuild even if database exists (default: False)

    Returns:
        Path to created/existing database
    """
    if output_path is None:
        output_path = get_nvss_full_db_path()

    output_path = Path(output_path)

    # Check if already exists
    if output_path.exists() and not force_rebuild:
        logger.info(f"Full NVSS database already exists: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load from raw HEASARC file
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog

    logger.info("Loading NVSS catalog from raw HEASARC file...")
    df_full = read_nvss_catalog()
    logger.info(f"Loaded {len(df_full)} NVSS sources")

    # Acquire lock
    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=600.0)

    if lock_fd is None:
        if output_path.exists():
            logger.info(f"Database {output_path} was created by another process")
            return output_path
        raise RuntimeError(f"Could not acquire lock for {output_path}")

    try:
        # Double-check after lock
        if output_path.exists() and not force_rebuild:
            logger.info(f"Database {output_path} created while waiting for lock")
            return output_path

        # Remove existing if force rebuild
        if output_path.exists() and force_rebuild:
            output_path.unlink()

        logger.info(f"Creating full NVSS database: {output_path}")

        with sqlite3.connect(str(output_path)) as conn:
            # Enable WAL mode for concurrent reads
            conn.execute("PRAGMA journal_mode=WAL")

            # Create sources table with all relevant columns
            conn.execute("""
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL,
                    flux_err_mjy REAL,
                    major_axis REAL,
                    minor_axis REAL,
                    position_angle REAL
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            # Prepare data for insertion
            ra_col = "ra" if "ra" in df_full.columns else "ra_deg"
            dec_col = "dec" if "dec" in df_full.columns else "dec_deg"
            flux_col = "flux_20_cm" if "flux_20_cm" in df_full.columns else "flux_mjy"

            insert_data = []
            for _, row in df_full.iterrows():
                ra = pd.to_numeric(row.get(ra_col), errors="coerce")
                dec = pd.to_numeric(row.get(dec_col), errors="coerce")
                flux = pd.to_numeric(row.get(flux_col), errors="coerce")
                flux_err = pd.to_numeric(row.get("flux_20_cm_error"), errors="coerce")
                major = pd.to_numeric(row.get("major_axis"), errors="coerce")
                minor = pd.to_numeric(row.get("minor_axis"), errors="coerce")
                pa = pd.to_numeric(row.get("position_angle"), errors="coerce")

                if np.isfinite(ra) and np.isfinite(dec):
                    insert_data.append((
                        float(ra),
                        float(dec),
                        float(flux) if np.isfinite(flux) else None,
                        float(flux_err) if np.isfinite(flux_err) else None,
                        float(major) if np.isfinite(major) else None,
                        float(minor) if np.isfinite(minor) else None,
                        float(pa) if np.isfinite(pa) else None,
                    ))

            # Batch insert
            conn.executemany(
                """INSERT INTO sources
                   (ra_deg, dec_deg, flux_mjy, flux_err_mjy, major_axis, minor_axis, position_angle)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                insert_data,
            )

            # Create metadata table
            conn.execute("""
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            build_time = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                ("build_time_iso", build_time),
            )
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                ("n_sources", str(len(insert_data))),
            )
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                ("source", "HEASARC NVSS catalog"),
            )

            conn.commit()

        logger.info(f"Created full NVSS database with {len(insert_data)} sources")
        return output_path

    finally:
        _release_db_lock(lock_fd, lock_path)


def build_nvss_strip_from_full(
    dec_center: float,
    dec_range: tuple[float, float],
    output_path: Optional[Path] = None,
    min_flux_mjy: Optional[float] = None,
    full_db_path: Optional[Path] = None,
) -> Path:
    """Build NVSS dec strip database from the full NVSS database.

    This is faster than parsing the raw HEASARC file because it uses
    indexed SQLite queries.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        output_path: Output SQLite database path (auto-generated if None)
        min_flux_mjy: Minimum flux threshold in mJy (None = no threshold)
        full_db_path: Path to full NVSS database (default: auto-detect)

    Returns:
        Path to created SQLite database

    Raises:
        FileNotFoundError: If full NVSS database doesn't exist
    """
    dec_min, dec_max = dec_range

    # Resolve full database path
    if full_db_path is None:
        full_db_path = get_nvss_full_db_path()

    if not full_db_path.exists():
        raise FileNotFoundError(
            f"Full NVSS database not found: {full_db_path}. "
            f"Run build_nvss_full_db() first."
        )

    # Resolve output path
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"nvss_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("/data/dsa110-contimg/state/catalogs") / db_name

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if already exists
    if output_path.exists():
        logger.info(f"Dec strip database already exists: {output_path}")
        return output_path

    # Acquire lock
    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=300.0)

    if lock_fd is None:
        if output_path.exists():
            return output_path
        raise RuntimeError(f"Could not acquire lock for {output_path}")

    try:
        if output_path.exists():
            return output_path

        logger.info(f"Building NVSS dec strip from full database: {dec_min:.2f}° to {dec_max:.2f}°")

        # Query sources from full database
        with sqlite3.connect(str(full_db_path)) as src_conn:
            query = """
                SELECT ra_deg, dec_deg, flux_mjy
                FROM sources
                WHERE dec_deg >= ? AND dec_deg <= ?
            """
            params = [dec_min, dec_max]

            if min_flux_mjy is not None:
                query += " AND flux_mjy >= ?"
                params.append(min_flux_mjy)

            cursor = src_conn.execute(query, params)
            rows = cursor.fetchall()

        logger.info(f"Found {len(rows)} sources in dec range")

        # Create output database
        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute("""
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL,
                    UNIQUE(ra_deg, dec_deg)
                )
            """)

            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            conn.executemany(
                "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
                rows,
            )

            # Metadata
            conn.execute("""
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            build_time = datetime.now(timezone.utc).isoformat()
            meta = [
                ("dec_center", str(dec_center)),
                ("dec_min", str(dec_min)),
                ("dec_max", str(dec_max)),
                ("build_time_iso", build_time),
                ("n_sources", str(len(rows))),
                ("source", "nvss_full.sqlite3"),
            ]
            conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", meta)

            conn.commit()

        logger.info(f"Created dec strip database: {output_path} ({len(rows)} sources)")
        return output_path

    finally:
        _release_db_lock(lock_fd, lock_path)


# --------------------------------------------------------------------------
# FIRST catalog full database builders
# --------------------------------------------------------------------------

# Default path for full FIRST database
FIRST_FULL_DB_PATH = Path("/data/dsa110-contimg/state/catalogs/first_full.sqlite3")


def get_first_full_db_path() -> Path:
    """Get the path to the full FIRST database.

    Returns:
        Path to first_full.sqlite3
    """
    return FIRST_FULL_DB_PATH


def first_full_db_exists() -> bool:
    """Check if the full FIRST database exists.

    Returns:
        True if first_full.sqlite3 exists and has data
    """
    db_path = get_first_full_db_path()
    if not db_path.exists():
        return False

    try:
        with sqlite3.connect(str(db_path)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            return count > 0
    except Exception:
        return False


def build_first_full_db(
    output_path: Optional[Path] = None,
    force_rebuild: bool = False,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> Path:
    """Build a full FIRST SQLite database from Vizier/cached data.

    Creates a comprehensive database with all FIRST sources,
    indexed for fast spatial queries.

    Args:
        output_path: Output database path (default: state/catalogs/first_full.sqlite3)
        force_rebuild: If True, rebuild even if database exists
        cache_dir: Directory for cached catalog files

    Returns:
        Path to created/existing database
    """
    from dsa110_contimg.calibration.catalogs import read_first_catalog
    from dsa110_contimg.catalog.build_master import _normalize_columns

    if output_path is None:
        output_path = get_first_full_db_path()

    output_path = Path(output_path)

    if output_path.exists() and not force_rebuild:
        logger.info(f"Full FIRST database already exists: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Loading FIRST catalog...")
    df_full = read_first_catalog(cache_dir=cache_dir)
    logger.info(f"Loaded {len(df_full)} FIRST sources")

    # Normalize columns
    FIRST_CANDIDATES = {
        "ra": ["ra", "ra_deg", "raj2000"],
        "dec": ["dec", "dec_deg", "dej2000"],
        "flux": ["peak_flux", "peak_mjy_per_beam", "flux_peak", "flux", "total_flux", "fpeak", "fint", "flux_mjy"],
        "maj": ["deconv_maj", "maj", "fwhm_maj", "deconvolved_major", "maj_deconv"],
        "min": ["deconv_min", "min", "fwhm_min", "deconvolved_minor", "min_deconv"],
    }
    col_map = _normalize_columns(df_full, FIRST_CANDIDATES)
    ra_col = col_map.get("ra", "ra")
    dec_col = col_map.get("dec", "dec")
    flux_col = col_map.get("flux", None)
    maj_col = col_map.get("maj", None)
    min_col = col_map.get("min", None)

    # Acquire lock
    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=600.0)

    if lock_fd is None:
        if output_path.exists():
            return output_path
        raise RuntimeError(f"Could not acquire lock for {output_path}")

    try:
        if output_path.exists() and not force_rebuild:
            return output_path

        if output_path.exists() and force_rebuild:
            output_path.unlink()

        logger.info(f"Creating full FIRST database: {output_path}")

        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute("""
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL,
                    maj_arcsec REAL,
                    min_arcsec REAL
                )
            """)

            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            insert_data = []
            for _, row in df_full.iterrows():
                ra = pd.to_numeric(row.get(ra_col), errors="coerce")
                dec = pd.to_numeric(row.get(dec_col), errors="coerce")

                if not (np.isfinite(ra) and np.isfinite(dec)):
                    continue

                flux = None
                if flux_col and flux_col in row.index:
                    flux_val = pd.to_numeric(row.get(flux_col), errors="coerce")
                    if np.isfinite(flux_val):
                        flux = float(flux_val)

                maj = None
                if maj_col and maj_col in row.index:
                    maj_val = pd.to_numeric(row.get(maj_col), errors="coerce")
                    if np.isfinite(maj_val):
                        maj = float(maj_val)

                min_val = None
                if min_col and min_col in row.index:
                    min_v = pd.to_numeric(row.get(min_col), errors="coerce")
                    if np.isfinite(min_v):
                        min_val = float(min_v)

                insert_data.append((float(ra), float(dec), flux, maj, min_val))

            conn.executemany(
                "INSERT INTO sources (ra_deg, dec_deg, flux_mjy, maj_arcsec, min_arcsec) VALUES (?, ?, ?, ?, ?)",
                insert_data,
            )

            conn.execute("""
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            build_time = datetime.now(timezone.utc).isoformat()
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("build_time_iso", build_time))
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("n_sources", str(len(insert_data))))
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("source", "FIRST catalog (Vizier/cached)"))
            conn.commit()

        logger.info(f"Created full FIRST database with {len(insert_data)} sources")
        return output_path

    finally:
        _release_db_lock(lock_fd, lock_path)


def build_first_strip_from_full(
    dec_center: float,
    dec_range: tuple[float, float],
    output_path: Optional[Path] = None,
    min_flux_mjy: Optional[float] = None,
    full_db_path: Optional[Path] = None,
) -> Path:
    """Build FIRST dec strip database from the full FIRST database.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        output_path: Output SQLite database path (auto-generated if None)
        min_flux_mjy: Minimum flux threshold in mJy
        full_db_path: Path to full FIRST database (default: auto-detect)

    Returns:
        Path to created SQLite database
    """
    dec_min, dec_max = dec_range

    if full_db_path is None:
        full_db_path = get_first_full_db_path()

    if not full_db_path.exists():
        raise FileNotFoundError(f"Full FIRST database not found: {full_db_path}. Run build_first_full_db() first.")

    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"first_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("/data/dsa110-contimg/state/catalogs") / db_name

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logger.info(f"Dec strip database already exists: {output_path}")
        return output_path

    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=300.0)

    if lock_fd is None:
        if output_path.exists():
            return output_path
        raise RuntimeError(f"Could not acquire lock for {output_path}")

    try:
        if output_path.exists():
            return output_path

        logger.info(f"Building FIRST dec strip from full database: {dec_min:.2f}° to {dec_max:.2f}°")

        with sqlite3.connect(str(full_db_path)) as src_conn:
            query = "SELECT ra_deg, dec_deg, flux_mjy, maj_arcsec, min_arcsec FROM sources WHERE dec_deg >= ? AND dec_deg <= ?"
            params = [dec_min, dec_max]

            if min_flux_mjy is not None:
                query += " AND flux_mjy >= ?"
                params.append(min_flux_mjy)

            rows = src_conn.execute(query, params).fetchall()

        logger.info(f"Found {len(rows)} sources in dec range")

        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute("""
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL,
                    maj_arcsec REAL,
                    min_arcsec REAL,
                    UNIQUE(ra_deg, dec_deg)
                )
            """)

            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            conn.executemany(
                "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy, maj_arcsec, min_arcsec) VALUES(?, ?, ?, ?, ?)",
                rows,
            )

            conn.execute("""
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            build_time = datetime.now(timezone.utc).isoformat()
            meta = [
                ("dec_center", str(dec_center)),
                ("dec_min", str(dec_min)),
                ("dec_max", str(dec_max)),
                ("build_time_iso", build_time),
                ("n_sources", str(len(rows))),
                ("source", "first_full.sqlite3"),
            ]
            conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", meta)
            conn.commit()

        logger.info(f"Created dec strip database: {output_path} ({len(rows)} sources)")
        return output_path

    finally:
        _release_db_lock(lock_fd, lock_path)


# --------------------------------------------------------------------------
# VLASS catalog full database builders
# --------------------------------------------------------------------------

VLASS_FULL_DB_PATH = Path("/data/dsa110-contimg/state/catalogs/vlass_full.sqlite3")


def get_vlass_full_db_path() -> Path:
    """Get the path to the full VLASS database."""
    return VLASS_FULL_DB_PATH


def vlass_full_db_exists() -> bool:
    """Check if the full VLASS database exists."""
    db_path = get_vlass_full_db_path()
    if not db_path.exists():
        return False
    try:
        with sqlite3.connect(str(db_path)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            return count > 0
    except Exception:
        return False


def build_vlass_full_db(
    output_path: Optional[Path] = None,
    force_rebuild: bool = False,
    cache_dir: str = DEFAULT_CACHE_DIR,
    vlass_catalog_path: Optional[str] = None,
) -> Path:
    """Build a full VLASS SQLite database from cached data.

    Args:
        output_path: Output database path (default: state/catalogs/vlass_full.sqlite3)
        force_rebuild: If True, rebuild even if database exists
        cache_dir: Directory for cached catalog files
        vlass_catalog_path: Explicit path to VLASS catalog file

    Returns:
        Path to created/existing database
    """
    from dsa110_contimg.catalog.build_master import _normalize_columns, _read_table

    if output_path is None:
        output_path = get_vlass_full_db_path()

    output_path = Path(output_path)

    if output_path.exists() and not force_rebuild:
        logger.info(f"Full VLASS database already exists: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load VLASS catalog
    if vlass_catalog_path:
        df_full = _read_table(vlass_catalog_path)
    else:
        cache_path = Path(cache_dir) / "vlass_catalog"
        for ext in [".csv", ".fits", ".fits.gz", ".csv.gz"]:
            candidate = cache_path.with_suffix(ext)
            if candidate.exists():
                df_full = _read_table(str(candidate))
                break
        else:
            raise FileNotFoundError(
                f"VLASS catalog not found. Provide vlass_catalog_path or place catalog in {cache_dir}/vlass_catalog.csv"
            )

    logger.info(f"Loaded {len(df_full)} VLASS sources")

    VLASS_CANDIDATES = {
        "ra": ["ra", "ra_deg", "raj2000"],
        "dec": ["dec", "dec_deg", "dej2000"],
        "flux": ["peak_flux", "peak_mjy_per_beam", "flux_peak", "flux", "total_flux"],
    }
    col_map = _normalize_columns(df_full, VLASS_CANDIDATES)
    ra_col = col_map.get("ra", "ra")
    dec_col = col_map.get("dec", "dec")
    flux_col = col_map.get("flux", None)

    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=600.0)

    if lock_fd is None:
        if output_path.exists():
            return output_path
        raise RuntimeError(f"Could not acquire lock for {output_path}")

    try:
        if output_path.exists() and not force_rebuild:
            return output_path

        if output_path.exists() and force_rebuild:
            output_path.unlink()

        logger.info(f"Creating full VLASS database: {output_path}")

        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute("""
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL
                )
            """)

            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            insert_data = []
            for _, row in df_full.iterrows():
                ra = pd.to_numeric(row.get(ra_col), errors="coerce")
                dec = pd.to_numeric(row.get(dec_col), errors="coerce")

                if not (np.isfinite(ra) and np.isfinite(dec)):
                    continue

                flux = None
                if flux_col and flux_col in row.index:
                    flux_val = pd.to_numeric(row.get(flux_col), errors="coerce")
                    if np.isfinite(flux_val):
                        flux = float(flux_val)

                insert_data.append((float(ra), float(dec), flux))

            conn.executemany(
                "INSERT INTO sources (ra_deg, dec_deg, flux_mjy) VALUES (?, ?, ?)",
                insert_data,
            )

            conn.execute("""
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            build_time = datetime.now(timezone.utc).isoformat()
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("build_time_iso", build_time))
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("n_sources", str(len(insert_data))))
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("source", "VLASS catalog (cached)"))
            conn.commit()

        logger.info(f"Created full VLASS database with {len(insert_data)} sources")
        return output_path

    finally:
        _release_db_lock(lock_fd, lock_path)


def build_vlass_strip_from_full(
    dec_center: float,
    dec_range: tuple[float, float],
    output_path: Optional[Path] = None,
    min_flux_mjy: Optional[float] = None,
    full_db_path: Optional[Path] = None,
) -> Path:
    """Build VLASS dec strip database from the full VLASS database."""
    dec_min, dec_max = dec_range

    if full_db_path is None:
        full_db_path = get_vlass_full_db_path()

    if not full_db_path.exists():
        raise FileNotFoundError(f"Full VLASS database not found: {full_db_path}. Run build_vlass_full_db() first.")

    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"vlass_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("/data/dsa110-contimg/state/catalogs") / db_name

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logger.info(f"Dec strip database already exists: {output_path}")
        return output_path

    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=300.0)

    if lock_fd is None:
        if output_path.exists():
            return output_path
        raise RuntimeError(f"Could not acquire lock for {output_path}")

    try:
        if output_path.exists():
            return output_path

        logger.info(f"Building VLASS dec strip from full database: {dec_min:.2f}° to {dec_max:.2f}°")

        with sqlite3.connect(str(full_db_path)) as src_conn:
            query = "SELECT ra_deg, dec_deg, flux_mjy FROM sources WHERE dec_deg >= ? AND dec_deg <= ?"
            params = [dec_min, dec_max]

            if min_flux_mjy is not None:
                query += " AND flux_mjy >= ?"
                params.append(min_flux_mjy)

            rows = src_conn.execute(query, params).fetchall()

        logger.info(f"Found {len(rows)} sources in dec range")

        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute("""
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL,
                    UNIQUE(ra_deg, dec_deg)
                )
            """)

            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            conn.executemany(
                "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
                rows,
            )

            conn.execute("""
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            build_time = datetime.now(timezone.utc).isoformat()
            meta = [
                ("dec_center", str(dec_center)),
                ("dec_min", str(dec_min)),
                ("dec_max", str(dec_max)),
                ("build_time_iso", build_time),
                ("n_sources", str(len(rows))),
                ("source", "vlass_full.sqlite3"),
            ]
            conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", meta)
            conn.commit()

        logger.info(f"Created dec strip database: {output_path} ({len(rows)} sources)")
        return output_path

    finally:
        _release_db_lock(lock_fd, lock_path)


# --------------------------------------------------------------------------
# RAX catalog full database builders
# --------------------------------------------------------------------------

RAX_FULL_DB_PATH = Path("/data/dsa110-contimg/state/catalogs/rax_full.sqlite3")


def get_rax_full_db_path() -> Path:
    """Get the path to the full RAX database."""
    return RAX_FULL_DB_PATH


def rax_full_db_exists() -> bool:
    """Check if the full RAX database exists."""
    db_path = get_rax_full_db_path()
    if not db_path.exists():
        return False
    try:
        with sqlite3.connect(str(db_path)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            return count > 0
    except Exception:
        return False


def build_rax_full_db(
    output_path: Optional[Path] = None,
    force_rebuild: bool = False,
    cache_dir: str = DEFAULT_CACHE_DIR,
    rax_catalog_path: Optional[str] = None,
) -> Path:
    """Build a full RAX SQLite database from cached data.

    Args:
        output_path: Output database path (default: state/catalogs/rax_full.sqlite3)
        force_rebuild: If True, rebuild even if database exists
        cache_dir: Directory for cached catalog files
        rax_catalog_path: Explicit path to RAX catalog file

    Returns:
        Path to created/existing database
    """
    from dsa110_contimg.calibration.catalogs import read_rax_catalog
    from dsa110_contimg.catalog.build_master import _normalize_columns

    if output_path is None:
        output_path = get_rax_full_db_path()

    output_path = Path(output_path)

    if output_path.exists() and not force_rebuild:
        logger.info(f"Full RAX database already exists: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Loading RAX catalog...")
    df_full = read_rax_catalog(cache_dir=cache_dir, rax_catalog_path=rax_catalog_path)
    logger.info(f"Loaded {len(df_full)} RAX sources")

    RAX_CANDIDATES = {
        "ra": ["ra", "ra_deg", "raj2000", "ra_hms"],
        "dec": ["dec", "dec_deg", "dej2000", "dec_dms"],
        "flux": ["flux", "flux_mjy", "flux_jy", "peak_flux", "fpeak", "s1.4"],
    }
    col_map = _normalize_columns(df_full, RAX_CANDIDATES)
    ra_col = col_map.get("ra", "ra")
    dec_col = col_map.get("dec", "dec")
    flux_col = col_map.get("flux", None)

    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=600.0)

    if lock_fd is None:
        if output_path.exists():
            return output_path
        raise RuntimeError(f"Could not acquire lock for {output_path}")

    try:
        if output_path.exists() and not force_rebuild:
            return output_path

        if output_path.exists() and force_rebuild:
            output_path.unlink()

        logger.info(f"Creating full RAX database: {output_path}")

        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute("""
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL
                )
            """)

            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            insert_data = []
            for _, row in df_full.iterrows():
                ra = pd.to_numeric(row.get(ra_col), errors="coerce")
                dec = pd.to_numeric(row.get(dec_col), errors="coerce")

                if not (np.isfinite(ra) and np.isfinite(dec)):
                    continue

                flux = None
                if flux_col and flux_col in row.index:
                    flux_val = pd.to_numeric(row.get(flux_col), errors="coerce")
                    if np.isfinite(flux_val):
                        flux = float(flux_val)

                insert_data.append((float(ra), float(dec), flux))

            conn.executemany(
                "INSERT INTO sources (ra_deg, dec_deg, flux_mjy) VALUES (?, ?, ?)",
                insert_data,
            )

            conn.execute("""
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            build_time = datetime.now(timezone.utc).isoformat()
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("build_time_iso", build_time))
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("n_sources", str(len(insert_data))))
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("source", "RAX catalog (cached)"))
            conn.commit()

        logger.info(f"Created full RAX database with {len(insert_data)} sources")
        return output_path

    finally:
        _release_db_lock(lock_fd, lock_path)


def build_rax_strip_from_full(
    dec_center: float,
    dec_range: tuple[float, float],
    output_path: Optional[Path] = None,
    min_flux_mjy: Optional[float] = None,
    full_db_path: Optional[Path] = None,
) -> Path:
    """Build RAX dec strip database from the full RAX database."""
    dec_min, dec_max = dec_range

    if full_db_path is None:
        full_db_path = get_rax_full_db_path()

    if not full_db_path.exists():
        raise FileNotFoundError(f"Full RAX database not found: {full_db_path}. Run build_rax_full_db() first.")

    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"rax_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("/data/dsa110-contimg/state/catalogs") / db_name

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logger.info(f"Dec strip database already exists: {output_path}")
        return output_path

    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=300.0)

    if lock_fd is None:
        if output_path.exists():
            return output_path
        raise RuntimeError(f"Could not acquire lock for {output_path}")

    try:
        if output_path.exists():
            return output_path

        logger.info(f"Building RAX dec strip from full database: {dec_min:.2f}° to {dec_max:.2f}°")

        with sqlite3.connect(str(full_db_path)) as src_conn:
            query = "SELECT ra_deg, dec_deg, flux_mjy FROM sources WHERE dec_deg >= ? AND dec_deg <= ?"
            params = [dec_min, dec_max]

            if min_flux_mjy is not None:
                query += " AND flux_mjy >= ?"
                params.append(min_flux_mjy)

            rows = src_conn.execute(query, params).fetchall()

        logger.info(f"Found {len(rows)} sources in dec range")

        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute("""
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL,
                    UNIQUE(ra_deg, dec_deg)
                )
            """)

            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            conn.executemany(
                "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
                rows,
            )

            conn.execute("""
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            build_time = datetime.now(timezone.utc).isoformat()
            meta = [
                ("dec_center", str(dec_center)),
                ("dec_min", str(dec_min)),
                ("dec_max", str(dec_max)),
                ("build_time_iso", build_time),
                ("n_sources", str(len(rows))),
                ("source", "rax_full.sqlite3"),
            ]
            conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", meta)
            conn.commit()

        logger.info(f"Created dec strip database: {output_path} ({len(rows)} sources)")
        return output_path

    finally:
        _release_db_lock(lock_fd, lock_path)


# --------------------------------------------------------------------------
# ATNF pulsar catalog full database builders
# --------------------------------------------------------------------------

ATNF_FULL_DB_PATH = Path("/data/dsa110-contimg/state/catalogs/atnf_full.sqlite3")


def get_atnf_full_db_path() -> Path:
    """Get the path to the full ATNF database."""
    return ATNF_FULL_DB_PATH


def atnf_full_db_exists() -> bool:
    """Check if the full ATNF database exists."""
    db_path = get_atnf_full_db_path()
    if not db_path.exists():
        return False
    try:
        with sqlite3.connect(str(db_path)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            return count > 0
    except Exception:
        return False


def build_atnf_full_db(
    output_path: Optional[Path] = None,
    force_rebuild: bool = False,
) -> Path:
    """Build a full ATNF pulsar SQLite database from psrqpy.

    Args:
        output_path: Output database path (default: state/catalogs/atnf_full.sqlite3)
        force_rebuild: If True, rebuild even if database exists

    Returns:
        Path to created/existing database
    """
    from dsa110_contimg.catalog.build_atnf_pulsars import (
        _download_atnf_catalog,
        _process_atnf_data,
    )

    if output_path is None:
        output_path = get_atnf_full_db_path()

    output_path = Path(output_path)

    if output_path.exists() and not force_rebuild:
        logger.info(f"Full ATNF database already exists: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading ATNF pulsar catalog...")
    df_raw = _download_atnf_catalog()
    df_processed = _process_atnf_data(df_raw, min_flux_mjy=None)
    logger.info(f"Loaded {len(df_processed)} ATNF pulsars")

    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=600.0)

    if lock_fd is None:
        if output_path.exists():
            return output_path
        raise RuntimeError(f"Could not acquire lock for {output_path}")

    try:
        if output_path.exists() and not force_rebuild:
            return output_path

        if output_path.exists() and force_rebuild:
            output_path.unlink()

        logger.info(f"Creating full ATNF database: {output_path}")

        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute("""
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL,
                    name TEXT,
                    period_s REAL,
                    dm REAL
                )
            """)

            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            insert_data = []
            for _, row in df_processed.iterrows():
                ra = float(row["ra_deg"])
                dec = float(row["dec_deg"])

                if not (np.isfinite(ra) and np.isfinite(dec)):
                    continue

                flux = float(row["flux_1400mhz_mjy"]) if pd.notna(row.get("flux_1400mhz_mjy")) else None
                name = str(row.get("name", "")) if pd.notna(row.get("name")) else None
                period = float(row.get("period_s")) if pd.notna(row.get("period_s")) else None
                dm = float(row.get("dm")) if pd.notna(row.get("dm")) else None

                insert_data.append((ra, dec, flux, name, period, dm))

            conn.executemany(
                "INSERT INTO sources (ra_deg, dec_deg, flux_mjy, name, period_s, dm) VALUES (?, ?, ?, ?, ?, ?)",
                insert_data,
            )

            conn.execute("""
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            build_time = datetime.now(timezone.utc).isoformat()
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("build_time_iso", build_time))
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("n_sources", str(len(insert_data))))
            conn.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("source", "ATNF Pulsar Catalogue (psrqpy)"))
            conn.commit()

        logger.info(f"Created full ATNF database with {len(insert_data)} sources")
        return output_path

    finally:
        _release_db_lock(lock_fd, lock_path)


def build_atnf_strip_from_full(
    dec_center: float,
    dec_range: tuple[float, float],
    output_path: Optional[Path] = None,
    min_flux_mjy: Optional[float] = None,
    full_db_path: Optional[Path] = None,
) -> Path:
    """Build ATNF dec strip database from the full ATNF database."""
    dec_min, dec_max = dec_range

    if full_db_path is None:
        full_db_path = get_atnf_full_db_path()

    if not full_db_path.exists():
        raise FileNotFoundError(f"Full ATNF database not found: {full_db_path}. Run build_atnf_full_db() first.")

    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"atnf_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("/data/dsa110-contimg/state/catalogs") / db_name

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logger.info(f"Dec strip database already exists: {output_path}")
        return output_path

    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=300.0)

    if lock_fd is None:
        if output_path.exists():
            return output_path
        raise RuntimeError(f"Could not acquire lock for {output_path}")

    try:
        if output_path.exists():
            return output_path

        logger.info(f"Building ATNF dec strip from full database: {dec_min:.2f}° to {dec_max:.2f}°")

        with sqlite3.connect(str(full_db_path)) as src_conn:
            query = "SELECT ra_deg, dec_deg, flux_mjy FROM sources WHERE dec_deg >= ? AND dec_deg <= ?"
            params = [dec_min, dec_max]

            if min_flux_mjy is not None:
                query += " AND flux_mjy >= ?"
                params.append(min_flux_mjy)

            rows = src_conn.execute(query, params).fetchall()

        logger.info(f"Found {len(rows)} sources in dec range")

        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            conn.execute("""
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL,
                    UNIQUE(ra_deg, dec_deg)
                )
            """)

            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            conn.executemany(
                "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
                rows,
            )

            conn.execute("""
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            build_time = datetime.now(timezone.utc).isoformat()
            meta = [
                ("dec_center", str(dec_center)),
                ("dec_min", str(dec_min)),
                ("dec_max", str(dec_max)),
                ("build_time_iso", build_time),
                ("n_sources", str(len(rows))),
                ("source", "atnf_full.sqlite3"),
            ]
            conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", meta)
            conn.commit()

        logger.info(f"Created dec strip database: {output_path} ({len(rows)} sources)")
        return output_path

    finally:
        _release_db_lock(lock_fd, lock_path)


def check_catalog_database_exists(
    catalog_type: str,
    dec_deg: float,
    tolerance_deg: float = 1.0,
) -> Tuple[bool, Optional[Path]]:
    """Check if a catalog database exists for the given declination.

    Args:
        catalog_type: One of "nvss", "first", "rax"
        dec_deg: Declination in degrees
        tolerance_deg: Tolerance for matching declination (default: 1.0°)

    Returns:
        Tuple of (exists: bool, db_path: Optional[Path])
    """
    from dsa110_contimg.catalog.query import resolve_catalog_path

    try:
        db_path = resolve_catalog_path(catalog_type, dec_strip=dec_deg)
        if db_path.exists():
            return True, db_path
    except FileNotFoundError:
        pass

    return False, None


def check_missing_catalog_databases(
    dec_deg: float,
    logger_instance: Optional[logging.Logger] = None,
    auto_build: bool = False,
    dec_range_deg: float = 6.0,
) -> Dict[str, bool]:
    """Check which catalog databases are missing when they should exist.

    Args:
        dec_deg: Declination in degrees
        logger_instance: Optional logger instance (uses module logger if None)
        auto_build: If True, automatically build missing databases (default: False)
        dec_range_deg: Declination range (±degrees) for building databases (default: 6.0)

    Returns:
        Dictionary mapping catalog_type -> exists (bool)
    """
    if logger_instance is None:
        logger_instance = logger

    results = {}
    built_databases = []

    for catalog_type, limits in CATALOG_COVERAGE_LIMITS.items():
        dec_min = limits.get("dec_min", -90.0)
        dec_max = limits.get("dec_max", 90.0)

        # Check if declination is within coverage
        within_coverage = dec_deg >= dec_min and dec_deg <= dec_max

        if within_coverage:
            exists, db_path = check_catalog_database_exists(catalog_type, dec_deg)
            results[catalog_type] = exists

            if not exists:
                logger_instance.warning(
                    f":warning:  {catalog_type.upper()} catalog database is missing for declination {dec_deg:.2f}°, "
                    f"but should exist (within coverage limits: {dec_min:.1f}° to {dec_max:.1f}°)."
                )

                if auto_build:
                    try:
                        logger_instance.info(
                            f":hammer: Auto-building {catalog_type.upper()} catalog database for declination {dec_deg:.2f}°..."
                        )
                        dec_range = (dec_deg - dec_range_deg, dec_deg + dec_range_deg)

                        if catalog_type == "nvss":
                            db_path = build_nvss_strip_db(
                                dec_center=dec_deg,
                                dec_range=dec_range,
                            )
                        elif catalog_type == "first":
                            db_path = build_first_strip_db(
                                dec_center=dec_deg,
                                dec_range=dec_range,
                            )
                        elif catalog_type == "rax":
                            db_path = build_rax_strip_db(
                                dec_center=dec_deg,
                                dec_range=dec_range,
                            )
                        elif catalog_type == "vlass":
                            db_path = build_vlass_strip_db(
                                dec_center=dec_deg,
                                dec_range=dec_range,
                            )
                        elif catalog_type == "atnf":
                            # ATNF is all-sky, but we build per-declination
                            # strip databases for efficiency
                            db_path = build_atnf_strip_db(
                                dec_center=dec_deg,
                                dec_range=dec_range,
                            )
                        else:
                            logger_instance.warning(
                                f"Unknown catalog type for auto-build: {catalog_type}"
                            )
                            continue

                        built_databases.append((catalog_type, db_path))
                        results[catalog_type] = True
                        logger_instance.info(
                            f":check: Successfully built {catalog_type.upper()} database: {db_path}"
                        )
                    except Exception as e:
                        logger_instance.error(
                            f":cross: Failed to auto-build {catalog_type.upper()} database: {e}",
                            exc_info=True,
                        )
                        results[catalog_type] = False
                else:
                    logger_instance.warning(
                        "   Database should be built by CatalogSetupStage or use auto_build=True."
                    )
        else:
            # Outside coverage, so database is not expected
            results[catalog_type] = False

    if auto_build and built_databases:
        logger_instance.info(
            f":check: Auto-built {len(built_databases)} catalog database(s): "
            f"{', '.join([f'{cat.upper()}' for cat, _ in built_databases])}"
        )

    return results


def auto_build_missing_catalog_databases(
    dec_deg: float,
    dec_range_deg: float = 6.0,
    logger_instance: Optional[logging.Logger] = None,
) -> Dict[str, Path]:
    """Automatically build missing catalog databases for a given declination.

    Args:
        dec_deg: Declination in degrees
        dec_range_deg: Declination range (±degrees) for building databases (default: 6.0)
        logger_instance: Optional logger instance (uses module logger if None)

    Returns:
        Dictionary mapping catalog_type -> db_path for successfully built databases
    """
    if logger_instance is None:
        logger_instance = logger

    # Use check_missing_catalog_databases with auto_build=True
    check_missing_catalog_databases(
        dec_deg=dec_deg,
        logger_instance=logger_instance,
        auto_build=True,
        dec_range_deg=dec_range_deg,
    )

    # Return paths of databases that now exist
    built_paths = {}
    for catalog_type in CATALOG_COVERAGE_LIMITS.keys():
        exists, db_path = check_catalog_database_exists(catalog_type, dec_deg)
        if exists and db_path:
            built_paths[catalog_type] = db_path

    return built_paths


def build_nvss_strip_db(
    dec_center: float,
    dec_range: Tuple[float, float],
    output_path: Optional[str | os.PathLike[str]] = None,
    nvss_csv_path: Optional[str] = None,
    min_flux_mjy: Optional[float] = None,
    prefer_full_db: bool = True,
) -> Path:
    """Build SQLite database for NVSS sources in a declination strip.

    If a full NVSS database (nvss_full.sqlite3) exists and prefer_full_db=True,
    the strip will be built from that database (faster). Otherwise, falls back
    to parsing the raw HEASARC text file.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        output_path: Output SQLite database path (auto-generated if None)
        nvss_csv_path: Path to full NVSS CSV catalog (downloaded if None)
        min_flux_mjy: Minimum flux threshold in mJy (None = no threshold)
        prefer_full_db: If True, use nvss_full.sqlite3 if available (default: True)

    Returns:
        Path to created SQLite database
    """
    dec_min, dec_max = dec_range

    # Resolve output path - use absolute path to state/catalogs
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"nvss_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("/data/dsa110-contimg/state/catalogs") / db_name

    output_path = Path(output_path)

    # Check if already exists
    if output_path.exists():
        logger.info(f"NVSS dec strip database already exists: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try to use full database if available and preferred
    if prefer_full_db and nvss_full_db_exists():
        logger.info("Using full NVSS database for faster strip extraction")
        return build_nvss_strip_from_full(
            dec_center=dec_center,
            dec_range=dec_range,
            output_path=output_path,
            min_flux_mjy=min_flux_mjy,
        )

    # Fall back to raw HEASARC file
    logger.info("Building from raw HEASARC file (full DB not available)")

    # Load NVSS catalog
    if nvss_csv_path is None:
        from dsa110_contimg.calibration.catalogs import read_nvss_catalog

        df_full = read_nvss_catalog()
    else:
        from dsa110_contimg.calibration.catalogs import read_nvss_catalog

        # If CSV path provided, we'd need to read it differently
        # For now, use the cached read function
        df_full = read_nvss_catalog()

    # Check coverage limits
    coverage_limits = CATALOG_COVERAGE_LIMITS.get("nvss", {})
    if dec_center < coverage_limits.get("dec_min", -90.0):
        logger.warning(
            f":warning:  Declination {dec_center:.2f}° is outside NVSS coverage "
            f"(southern limit: {coverage_limits.get('dec_min', -40.0)}°). "
            f"Database may be empty or have very few sources."
        )
    if dec_center > coverage_limits.get("dec_max", 90.0):
        logger.warning(
            f":warning:  Declination {dec_center:.2f}° is outside NVSS coverage "
            f"(northern limit: {coverage_limits.get('dec_max', 90.0)}°). "
            f"Database may be empty or have very few sources."
        )

    # Filter to declination strip
    dec_col = "dec" if "dec" in df_full.columns else "dec_deg"
    df_strip = df_full[(df_full[dec_col] >= dec_min) & (df_full[dec_col] <= dec_max)].copy()

    print(f"Filtered NVSS catalog: {len(df_full)} :arrow_right: {len(df_strip)} sources")
    print(f"Declination range: {dec_min:.6f} to {dec_max:.6f} degrees")

    # Warn if result is empty
    if len(df_strip) == 0:
        logger.warning(
            f":warning:  No NVSS sources found in declination range [{dec_min:.2f}°, {dec_max:.2f}°]. "
            f"This may indicate declination {dec_center:.2f}° is outside NVSS coverage limits "
            f"(southern limit: {coverage_limits.get('dec_min', -40.0)}°)."
        )

    # Apply flux threshold if specified
    if min_flux_mjy is not None:
        flux_col = "flux_20_cm" if "flux_20_cm" in df_strip.columns else "flux_mjy"
        if flux_col in df_strip.columns:
            flux_val = pd.to_numeric(df_strip[flux_col], errors="coerce")
            df_strip = df_strip[flux_val >= min_flux_mjy].copy()
            print(f"After flux cut ({min_flux_mjy} mJy): {len(df_strip)} sources")

    # Standardize column names
    ra_col = "ra" if "ra" in df_strip.columns else "ra_deg"
    dec_col = "dec" if "dec" in df_strip.columns else "dec_deg"
    flux_col = "flux_20_cm" if "flux_20_cm" in df_strip.columns else "flux_mjy"

    # Ensure flux is in mJy
    df_strip["ra_deg"] = pd.to_numeric(df_strip[ra_col], errors="coerce")
    df_strip["dec_deg"] = pd.to_numeric(df_strip[dec_col], errors="coerce")

    if flux_col in df_strip.columns:
        df_strip["flux_mjy"] = pd.to_numeric(df_strip[flux_col], errors="coerce")
    else:
        df_strip["flux_mjy"] = None

    # Check if database already exists (another process may have created it)
    if output_path.exists():
        logger.info(f"Database {output_path} already exists, skipping build")
        return output_path

    # Acquire lock for database creation
    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=300.0)

    if lock_fd is None:
        # Could not acquire lock - check if database was created by another process
        if output_path.exists():
            logger.info(f"Database {output_path} was created by another process")
            return output_path
        else:
            raise RuntimeError(
                f"Could not acquire lock for {output_path} and database does not exist"
            )

    try:
        # Double-check database doesn't exist (another process may have created it while we waited)
        if output_path.exists():
            logger.info(
                f"Database {output_path} was created by another process while waiting for lock"
            )
            return output_path

        # Create SQLite database
        print(f"Creating SQLite database: {output_path}")

        # Enable WAL mode for concurrent reads
        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

        with sqlite3.connect(str(output_path)) as conn:
            # Create sources table
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                flux_mjy REAL,
                UNIQUE(ra_deg, dec_deg)
            )
        """
            )

        # Create spatial index
        conn.execute("CREATE INDEX IF NOT EXISTS idx_radec ON sources(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dec ON sources(dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flux ON sources(flux_mjy)")

        # Clear existing data
        conn.execute("DELETE FROM sources")

        # Insert sources
        insert_data = []
        for _, row in df_strip.iterrows():
            ra = float(row["ra_deg"])
            dec = float(row["dec_deg"])
            flux = float(row["flux_mjy"]) if pd.notna(row.get("flux_mjy")) else None

            if np.isfinite(ra) and np.isfinite(dec):
                insert_data.append((ra, dec, flux))

        conn.executemany(
            "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
            insert_data,
        )

        # Create metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_center', ?)",
            (str(dec_center),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_min', ?)",
            (str(dec_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_max', ?)",
            (str(dec_max),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('n_sources', ?)",
            (str(len(insert_data)),),
        )
        if min_flux_mjy is not None:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('min_flux_mjy', ?)",
                (str(min_flux_mjy),),
            )

        # Store coverage status
        coverage_limits = CATALOG_COVERAGE_LIMITS.get("nvss", {})
        within_coverage = dec_center >= coverage_limits.get(
            "dec_min", -90.0
        ) and dec_center <= coverage_limits.get("dec_max", 90.0)
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('within_coverage', ?)",
            ("true" if within_coverage else "false",),
        )

        conn.commit()

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f":check: Database created: {output_path}")
        print(f"  Size: {file_size_mb:.2f} MB")
        print(f"  Sources: {len(insert_data)}")

        return output_path
    finally:
        # Always release the lock
        _release_db_lock(lock_fd, lock_path)


def build_first_strip_db(
    dec_center: float,
    dec_range: Tuple[float, float],
    first_catalog_path: Optional[str] = None,
    output_path: Optional[str | os.PathLike[str]] = None,
    min_flux_mjy: Optional[float] = None,
    cache_dir: str = ".cache/catalogs",
    prefer_full_db: bool = True,
) -> Path:
    """Build SQLite database for FIRST sources in a declination strip.

    If a full FIRST database (first_full.sqlite3) exists and prefer_full_db=True,
    the strip will be built from that database (faster). Otherwise, falls back
    to downloading/parsing the raw catalog.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        first_catalog_path: Optional path to FIRST catalog (CSV/FITS).
                           If None, attempts to auto-download/cache like NVSS.
        output_path: Output SQLite database path (auto-generated if None)
        min_flux_mjy: Minimum flux threshold in mJy (None = no threshold)
        cache_dir: Directory for caching catalog files (if auto-downloading)
        prefer_full_db: If True, use first_full.sqlite3 if available (default: True)

    Returns:
        Path to created SQLite database
    """
    from dsa110_contimg.calibration.catalogs import read_first_catalog
    from dsa110_contimg.catalog.build_master import _normalize_columns

    dec_min, dec_max = dec_range

    # Resolve output path
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"first_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("/data/dsa110-contimg/state/catalogs") / db_name

    output_path = Path(output_path)

    # Check if already exists
    if output_path.exists():
        logger.info(f"FIRST dec strip database already exists: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try to use full database if available and preferred
    if prefer_full_db and first_full_db_exists():
        logger.info("Using full FIRST database for faster strip extraction")
        return build_first_strip_from_full(
            dec_center=dec_center,
            dec_range=dec_range,
            output_path=output_path,
            min_flux_mjy=min_flux_mjy,
        )

    # Fall back to raw catalog
    logger.info("Building from raw FIRST catalog (full DB not available)")

    # Check coverage limits
    coverage_limits = CATALOG_COVERAGE_LIMITS.get("first", {})
    if dec_center < coverage_limits.get("dec_min", -90.0):
        logger.warning(
            f":warning:  Declination {dec_center:.2f}° is outside FIRST coverage "
            f"(southern limit: {coverage_limits.get('dec_min', -40.0)}°). "
            f"Database may be empty or have very few sources."
        )
    if dec_center > coverage_limits.get("dec_max", 90.0):
        logger.warning(
            f":warning:  Declination {dec_center:.2f}° is outside FIRST coverage "
            f"(northern limit: {coverage_limits.get('dec_max', 90.0)}°). "
            f"Database may be empty or have very few sources."
        )

    # Load FIRST catalog (auto-downloads if needed, similar to NVSS)
    df_full = read_first_catalog(cache_dir=cache_dir, first_catalog_path=first_catalog_path)

    # Normalize column names (similar to build_master.py)
    FIRST_CANDIDATES = {
        "ra": ["ra", "ra_deg", "raj2000"],
        "dec": ["dec", "dec_deg", "dej2000"],
        "flux": [
            "peak_flux",
            "peak_mjy_per_beam",
            "flux_peak",
            "flux",
            "total_flux",
            "fpeak",
        ],
        "maj": ["deconv_maj", "maj", "fwhm_maj", "deconvolved_major", "maj_deconv"],
        "min": ["deconv_min", "min", "fwhm_min", "deconvolved_minor", "min_deconv"],
    }

    col_map = _normalize_columns(df_full, FIRST_CANDIDATES)

    # Standardize column names
    ra_col = col_map.get("ra", "ra")
    dec_col = col_map.get("dec", "dec")
    flux_col = col_map.get("flux", None)
    maj_col = col_map.get("maj", None)
    min_col = col_map.get("min", None)

    # Filter to declination strip
    df_strip = df_full[
        (pd.to_numeric(df_full[dec_col], errors="coerce") >= dec_min)
        & (pd.to_numeric(df_full[dec_col], errors="coerce") <= dec_max)
    ].copy()

    print(f"Filtered FIRST catalog: {len(df_full)} :arrow_right: {len(df_strip)} sources")
    print(f"Declination range: {dec_min:.6f} to {dec_max:.6f} degrees")

    # Warn if result is empty
    if len(df_strip) == 0:
        coverage_limits = CATALOG_COVERAGE_LIMITS.get("first", {})
        logger.warning(
            f":warning:  No FIRST sources found in declination range [{dec_min:.2f}°, {dec_max:.2f}°]. "
            f"This may indicate declination {dec_center:.2f}° is outside FIRST coverage limits "
            f"(southern limit: {coverage_limits.get('dec_min', -40.0)}°)."
        )

    # Apply flux threshold if specified
    if min_flux_mjy is not None and flux_col:
        flux_val = pd.to_numeric(df_strip[flux_col], errors="coerce")
        # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
        if len(flux_val) > 0 and flux_val.max() > 1000:
            flux_val = flux_val * 1000.0  # Convert Jy to mJy
        df_strip = df_strip[flux_val >= min_flux_mjy].copy()
        print(f"After flux cut ({min_flux_mjy} mJy): {len(df_strip)} sources")

    # Check if database already exists (another process may have created it)
    if output_path.exists():
        logger.info(f"Database {output_path} already exists, skipping build")
        return output_path

    # Acquire lock for database creation
    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=300.0)

    if lock_fd is None:
        # Could not acquire lock - check if database was created by another process
        if output_path.exists():
            logger.info(f"Database {output_path} was created by another process")
            return output_path
        else:
            raise RuntimeError(
                f"Could not acquire lock for {output_path} and database does not exist"
            )

    try:
        # Double-check database doesn't exist (another process may have created it while we waited)
        if output_path.exists():
            logger.info(
                f"Database {output_path} was created by another process while waiting for lock"
            )
            return output_path

        # Create SQLite database
        print(f"Creating SQLite database: {output_path}")

        # Enable WAL mode for concurrent reads
        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

        with sqlite3.connect(str(output_path)) as conn:
            # Create sources table with FIRST-specific columns
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                flux_mjy REAL,
                maj_arcsec REAL,
                min_arcsec REAL,
                UNIQUE(ra_deg, dec_deg)
            )
        """
            )

        # Create spatial index
        conn.execute("CREATE INDEX IF NOT EXISTS idx_radec ON sources(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dec ON sources(dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flux ON sources(flux_mjy)")

        # Clear existing data
        conn.execute("DELETE FROM sources")

        # Insert sources
        insert_data = []
        for _, row in df_strip.iterrows():
            ra = pd.to_numeric(row[ra_col], errors="coerce")
            dec = pd.to_numeric(row[dec_col], errors="coerce")

            if not (np.isfinite(ra) and np.isfinite(dec)):
                continue

            # Handle flux
            flux = None
            if flux_col and flux_col in row.index:
                flux_val = pd.to_numeric(row[flux_col], errors="coerce")
                if np.isfinite(flux_val):
                    # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
                    flux_val_float = float(flux_val)
                    if flux_val_float > 1000:
                        flux = flux_val_float * 1000.0  # Convert Jy to mJy
                    else:
                        flux = flux_val_float

            # Handle size
            maj = None
            if maj_col and maj_col in row.index:
                maj_val = pd.to_numeric(row[maj_col], errors="coerce")
                if np.isfinite(maj_val):
                    maj = float(maj_val)

            min_val = None
            if min_col and min_col in row.index:
                min_val_num = pd.to_numeric(row[min_col], errors="coerce")
                if np.isfinite(min_val_num):
                    min_val = float(min_val_num)

            insert_data.append((ra, dec, flux, maj, min_val))

        conn.executemany(
            "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy, maj_arcsec, min_arcsec) VALUES(?, ?, ?, ?, ?)",
            insert_data,
        )

        # Create metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_center', ?)",
            (str(dec_center),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_min', ?)",
            (str(dec_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_max', ?)",
            (str(dec_max),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('n_sources', ?)",
            (str(len(insert_data)),),
        )

        # Store coverage status
        coverage_limits = CATALOG_COVERAGE_LIMITS.get("first", {})
        within_coverage = dec_center >= coverage_limits.get(
            "dec_min", -90.0
        ) and dec_center <= coverage_limits.get("dec_max", 90.0)
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('within_coverage', ?)",
            ("true" if within_coverage else "false",),
        )

        source_file_str = (
            str(first_catalog_path) if first_catalog_path else "auto-downloaded/cached"
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_file', ?)",
            (source_file_str,),
        )
        if min_flux_mjy is not None:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('min_flux_mjy', ?)",
                (str(min_flux_mjy),),
            )

        conn.commit()

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f":check: Database created: {output_path}")
        print(f"  Size: {file_size_mb:.2f} MB")
        print(f"  Sources: {len(insert_data)}")

        return output_path
    finally:
        # Always release the lock
        _release_db_lock(lock_fd, lock_path)


def build_rax_strip_db(
    dec_center: float,
    dec_range: Tuple[float, float],
    rax_catalog_path: Optional[str] = None,
    output_path: Optional[str | os.PathLike[str]] = None,
    min_flux_mjy: Optional[float] = None,
    cache_dir: str = ".cache/catalogs",
    prefer_full_db: bool = True,
) -> Path:
    """Build SQLite database for RAX sources in a declination strip.

    If a full RAX database (rax_full.sqlite3) exists and prefer_full_db=True,
    the strip will be built from that database (faster). Otherwise, falls back
    to the cached catalog file.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        rax_catalog_path: Optional path to RAX catalog (CSV/FITS).
                         If None, attempts to find cached catalog.
        output_path: Output SQLite database path (auto-generated if None)
        min_flux_mjy: Minimum flux threshold in mJy (None = no threshold)
        cache_dir: Directory for caching catalog files
        prefer_full_db: If True, use rax_full.sqlite3 if available (default: True)

    Returns:
        Path to created SQLite database
    """
    from dsa110_contimg.calibration.catalogs import read_rax_catalog
    from dsa110_contimg.catalog.build_master import _normalize_columns

    dec_min, dec_max = dec_range

    # Resolve output path
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"rax_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("/data/dsa110-contimg/state/catalogs") / db_name

    output_path = Path(output_path)

    # Check if already exists
    if output_path.exists():
        logger.info(f"RAX dec strip database already exists: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try to use full database if available and preferred
    if prefer_full_db and rax_full_db_exists():
        logger.info("Using full RAX database for faster strip extraction")
        return build_rax_strip_from_full(
            dec_center=dec_center,
            dec_range=dec_range,
            output_path=output_path,
            min_flux_mjy=min_flux_mjy,
        )

    # Fall back to raw catalog
    logger.info("Building from raw RAX catalog (full DB not available)")

    # Check coverage limits
    coverage_limits = CATALOG_COVERAGE_LIMITS.get("rax", {})
    if dec_center < coverage_limits.get("dec_min", -90.0):
        logger.warning(
            f":warning:  Declination {dec_center:.2f}° is outside RACS coverage "
            f"(southern limit: {coverage_limits.get('dec_min', -90.0)}°). "
            f"Database may be empty or have very few sources."
        )
    if dec_center > coverage_limits.get("dec_max", 90.0):
        logger.warning(
            f":warning:  Declination {dec_center:.2f}° is outside RACS coverage "
            f"(northern limit: {coverage_limits.get('dec_max', 49.9)}°). "
            f"Database may be empty or have very few sources."
        )

    # Load RAX catalog (uses cached or provided path)
    df_full = read_rax_catalog(cache_dir=cache_dir, rax_catalog_path=rax_catalog_path)

    # Normalize column names (RAX typically similar to NVSS structure)
    RAX_CANDIDATES = {
        "ra": ["ra", "ra_deg", "raj2000", "ra_hms"],
        "dec": ["dec", "dec_deg", "dej2000", "dec_dms"],
        "flux": ["flux", "flux_mjy", "flux_jy", "peak_flux", "fpeak", "s1.4"],
    }

    col_map = _normalize_columns(df_full, RAX_CANDIDATES)

    # Standardize column names
    ra_col = col_map.get("ra", "ra")
    dec_col = col_map.get("dec", "dec")
    flux_col = col_map.get("flux", None)

    # Filter to declination strip
    df_strip = df_full[
        (pd.to_numeric(df_full[dec_col], errors="coerce") >= dec_min)
        & (pd.to_numeric(df_full[dec_col], errors="coerce") <= dec_max)
    ].copy()

    print(f"Filtered RAX catalog: {len(df_full)} :arrow_right: {len(df_strip)} sources")
    print(f"Declination range: {dec_min:.6f} to {dec_max:.6f} degrees")

    # Warn if result is empty
    if len(df_strip) == 0:
        coverage_limits = CATALOG_COVERAGE_LIMITS.get("rax", {})
        logger.warning(
            f":warning:  No RACS sources found in declination range [{dec_min:.2f}°, {dec_max:.2f}°]. "
            f"This may indicate declination {dec_center:.2f}° is outside RACS coverage limits "
            f"(northern limit: {coverage_limits.get('dec_max', 49.9)}°)."
        )

    # Apply flux threshold if specified
    if min_flux_mjy is not None and flux_col:
        flux_val = pd.to_numeric(df_strip[flux_col], errors="coerce")
        # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
        if len(flux_val) > 0 and flux_val.max() > 1000:
            flux_val = flux_val * 1000.0  # Convert Jy to mJy
        df_strip = df_strip[flux_val >= min_flux_mjy].copy()
        print(f"After flux cut ({min_flux_mjy} mJy): {len(df_strip)} sources")

    # Check if database already exists (another process may have created it)
    if output_path.exists():
        logger.info(f"Database {output_path} already exists, skipping build")
        return output_path

    # Acquire lock for database creation
    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=300.0)

    if lock_fd is None:
        # Could not acquire lock - check if database was created by another process
        if output_path.exists():
            logger.info(f"Database {output_path} was created by another process")
            return output_path
        else:
            raise RuntimeError(
                f"Could not acquire lock for {output_path} and database does not exist"
            )

    try:
        # Double-check database doesn't exist (another process may have created it while we waited)
        if output_path.exists():
            logger.info(
                f"Database {output_path} was created by another process while waiting for lock"
            )
            return output_path

        # Create SQLite database
        print(f"Creating SQLite database: {output_path}")

        # Enable WAL mode for concurrent reads
        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

        with sqlite3.connect(str(output_path)) as conn:
            # Create sources table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                flux_mjy REAL,
                UNIQUE(ra_deg, dec_deg)
            )
        """
            )

        # Create spatial index
        conn.execute("CREATE INDEX IF NOT EXISTS idx_radec ON sources(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dec ON sources(dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flux ON sources(flux_mjy)")

        # Clear existing data
        conn.execute("DELETE FROM sources")

        # Insert sources
        insert_data = []
        for _, row in df_strip.iterrows():
            ra = pd.to_numeric(row[ra_col], errors="coerce")
            dec = pd.to_numeric(row[dec_col], errors="coerce")

            if not (np.isfinite(ra) and np.isfinite(dec)):
                continue

            # Handle flux
            flux = None
            if flux_col and flux_col in row.index:
                flux_val = pd.to_numeric(row[flux_col], errors="coerce")
                if np.isfinite(flux_val):
                    # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
                    flux_val_float = float(flux_val)
                    if flux_val_float > 1000:
                        flux = flux_val_float * 1000.0  # Convert Jy to mJy
                    else:
                        flux = flux_val_float

            insert_data.append((ra, dec, flux))

        conn.executemany(
            "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
            insert_data,
        )

        # Create metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_center', ?)",
            (str(dec_center),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_min', ?)",
            (str(dec_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_max', ?)",
            (str(dec_max),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('n_sources', ?)",
            (str(len(insert_data)),),
        )

        # Store coverage status
        coverage_limits = CATALOG_COVERAGE_LIMITS.get("rax", {})
        within_coverage = dec_center >= coverage_limits.get(
            "dec_min", -90.0
        ) and dec_center <= coverage_limits.get("dec_max", 90.0)
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('within_coverage', ?)",
            ("true" if within_coverage else "false",),
        )

        source_file_str = str(rax_catalog_path) if rax_catalog_path else "auto-downloaded/cached"
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_file', ?)",
            (source_file_str,),
        )
        if min_flux_mjy is not None:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('min_flux_mjy', ?)",
                (str(min_flux_mjy),),
            )

        conn.commit()

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f":check: Database created: {output_path}")
        print(f"  Size: {file_size_mb:.2f} MB")
        print(f"  Sources: {len(insert_data)}")

        return output_path
    finally:
        # Always release the lock
        _release_db_lock(lock_fd, lock_path)


def build_vlass_strip_db(
    dec_center: float,
    dec_range: Tuple[float, float],
    vlass_catalog_path: Optional[str] = None,
    output_path: Optional[str | os.PathLike[str]] = None,
    min_flux_mjy: Optional[float] = None,
    cache_dir: str = ".cache/catalogs",
    prefer_full_db: bool = True,
) -> Path:
    """Build SQLite database for VLASS sources in a declination strip.

    If a full VLASS database (vlass_full.sqlite3) exists and prefer_full_db=True,
    the strip will be built from that database (faster). Otherwise, falls back
    to the cached catalog file.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        vlass_catalog_path: Optional path to VLASS catalog (CSV/FITS).
                          If None, attempts to find cached catalog.
        output_path: Output SQLite database path (auto-generated if None)
        min_flux_mjy: Minimum flux threshold in mJy (None = no threshold)
        cache_dir: Directory for caching catalog files
        prefer_full_db: If True, use vlass_full.sqlite3 if available (default: True)

    Returns:
        Path to created SQLite database
    """
    from dsa110_contimg.catalog.build_master import _normalize_columns, _read_table

    dec_min, dec_max = dec_range

    # Resolve output path
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"vlass_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("/data/dsa110-contimg/state/catalogs") / db_name

    output_path = Path(output_path)

    # Check if already exists
    if output_path.exists():
        logger.info(f"VLASS dec strip database already exists: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try to use full database if available and preferred
    if prefer_full_db and vlass_full_db_exists():
        logger.info("Using full VLASS database for faster strip extraction")
        return build_vlass_strip_from_full(
            dec_center=dec_center,
            dec_range=dec_range,
            output_path=output_path,
            min_flux_mjy=min_flux_mjy,
        )

    # Fall back to raw catalog
    logger.info("Building from raw VLASS catalog (full DB not available)")

    # Load VLASS catalog
    if vlass_catalog_path:
        df_full = _read_table(vlass_catalog_path)
    else:
        # Try to find cached VLASS catalog
        cache_path = Path(cache_dir) / "vlass_catalog"
        for ext in [".csv", ".fits", ".fits.gz", ".csv.gz"]:
            candidate = cache_path.with_suffix(ext)
            if candidate.exists():
                df_full = _read_table(str(candidate))
                break
        else:
            raise FileNotFoundError(
                f"VLASS catalog not found. Provide vlass_catalog_path or place "
                f"catalog in {cache_dir}/vlass_catalog.csv or .fits"
            )

    # Normalize column names for VLASS
    VLASS_CANDIDATES = {
        "ra": ["ra", "ra_deg", "raj2000"],
        "dec": ["dec", "dec_deg", "dej2000"],
        "flux": ["peak_flux", "peak_mjy_per_beam", "flux_peak", "flux", "total_flux"],
    }

    col_map = _normalize_columns(df_full, VLASS_CANDIDATES)

    # Standardize column names
    ra_col = col_map.get("ra", "ra")
    dec_col = col_map.get("dec", "dec")
    flux_col = col_map.get("flux", None)

    # Filter to declination strip
    df_strip = df_full[
        (pd.to_numeric(df_full[dec_col], errors="coerce") >= dec_min)
        & (pd.to_numeric(df_full[dec_col], errors="coerce") <= dec_max)
    ].copy()

    print(f"Filtered VLASS catalog: {len(df_full)} :arrow_right: {len(df_strip)} sources")
    print(f"Declination range: {dec_min:.6f} to {dec_max:.6f} degrees")

    # Apply flux threshold if specified
    if min_flux_mjy is not None and flux_col:
        flux_val = pd.to_numeric(df_strip[flux_col], errors="coerce")
        # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
        if len(flux_val) > 0 and flux_val.max() > 1000:
            flux_val = flux_val * 1000.0  # Convert Jy to mJy
        df_strip = df_strip[flux_val >= min_flux_mjy].copy()
        print(f"After flux cut ({min_flux_mjy} mJy): {len(df_strip)} sources")

    # Create SQLite database
    print(f"Creating SQLite database: {output_path}")

    with sqlite3.connect(str(output_path)) as conn:
        # Create sources table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                flux_mjy REAL,
                UNIQUE(ra_deg, dec_deg)
            )
        """
        )

        # Create spatial index
        conn.execute("CREATE INDEX IF NOT EXISTS idx_radec ON sources(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dec ON sources(dec_deg)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_flux ON sources(flux_mjy)")

        # Clear existing data
        conn.execute("DELETE FROM sources")

        # Insert sources
        insert_data = []
        for _, row in df_strip.iterrows():
            ra = pd.to_numeric(row[ra_col], errors="coerce")
            dec = pd.to_numeric(row[dec_col], errors="coerce")

            if not (np.isfinite(ra) and np.isfinite(dec)):
                continue

            # Handle flux
            flux = None
            if flux_col and flux_col in row.index:
                flux_val = pd.to_numeric(row[flux_col], errors="coerce")
                if np.isfinite(flux_val):
                    # Convert to mJy if needed (assume > 1000 means Jy, otherwise mJy)
                    flux_val_float = float(flux_val)
                    if flux_val_float > 1000:
                        flux = flux_val_float * 1000.0  # Convert Jy to mJy
                    else:
                        flux = flux_val_float

            if np.isfinite(ra) and np.isfinite(dec):
                insert_data.append((ra, dec, flux))

        conn.executemany(
            "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
            insert_data,
        )

        # Create metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_center', ?)",
            (str(dec_center),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_min', ?)",
            (str(dec_min),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_max', ?)",
            (str(dec_max),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('n_sources', ?)",
            (str(len(insert_data)),),
        )
        source_file_str = (
            str(vlass_catalog_path) if vlass_catalog_path else "auto-downloaded/cached"
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('source_file', ?)",
            (source_file_str,),
        )
        if min_flux_mjy is not None:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('min_flux_mjy', ?)",
                (str(min_flux_mjy),),
            )

        conn.commit()

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f":check: Database created: {output_path}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Sources: {len(insert_data)}")

    return output_path


def build_atnf_strip_db(
    dec_center: float,
    dec_range: Tuple[float, float],
    output_path: Optional[str | os.PathLike[str]] = None,
    min_flux_mjy: Optional[float] = None,
    cache_dir: str = ".cache/catalogs",
    prefer_full_db: bool = True,
) -> Path:
    """Build SQLite database for ATNF pulsars in a declination strip.

    If a full ATNF database (atnf_full.sqlite3) exists and prefer_full_db=True,
    the strip will be built from that database (faster). Otherwise, falls back
    to downloading from psrqpy.

    Args:
        dec_center: Center declination in degrees
        dec_range: Tuple of (dec_min, dec_max) in degrees
        output_path: Output SQLite database path (auto-generated if None)
        min_flux_mjy: Minimum flux at 1400 MHz in mJy (None = no threshold)
        cache_dir: Directory for caching catalog files
        prefer_full_db: If True, use atnf_full.sqlite3 if available (default: True)

    Returns:
        Path to created SQLite database

    Raises:
        ImportError: If psrqpy is not installed
        Exception: If download or database creation fails
    """
    from dsa110_contimg.catalog.build_atnf_pulsars import (
        _download_atnf_catalog,
        _process_atnf_data,
    )

    dec_min, dec_max = dec_range

    # Resolve output path
    if output_path is None:
        dec_rounded = round(dec_center, 1)
        db_name = f"atnf_dec{dec_rounded:+.1f}.sqlite3"
        output_path = Path("/data/dsa110-contimg/state/catalogs") / db_name

    output_path = Path(output_path)

    # Check if already exists
    if output_path.exists():
        logger.info(f"ATNF dec strip database already exists: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try to use full database if available and preferred
    if prefer_full_db and atnf_full_db_exists():
        logger.info("Using full ATNF database for faster strip extraction")
        return build_atnf_strip_from_full(
            dec_center=dec_center,
            dec_range=dec_range,
            output_path=output_path,
            min_flux_mjy=min_flux_mjy,
        )

    # Fall back to psrqpy download
    logger.info("Building from ATNF psrqpy download (full DB not available)")

    # Check coverage limits (ATNF is all-sky, but warn if outside typical range)
    coverage_limits = CATALOG_COVERAGE_LIMITS.get("atnf", {})
    if dec_center < coverage_limits.get("dec_min", -90.0):
        logger.warning(
            f":warning:  Declination {dec_center:.2f}° is outside typical ATNF coverage "
            f"(southern limit: {coverage_limits.get('dec_min', -90.0)}°). "
            f"Database may be empty or have very few sources."
        )
    if dec_center > coverage_limits.get("dec_max", 90.0):
        logger.warning(
            f":warning:  Declination {dec_center:.2f}° is outside typical ATNF coverage "
            f"(northern limit: {coverage_limits.get('dec_max', 90.0)}°). "
            f"Database may be empty or have very few sources."
        )

    # Acquire lock for database creation
    lock_path = output_path.with_suffix(".lock")
    lock_fd = _acquire_db_lock(lock_path, timeout_sec=300.0)

    if lock_fd is None:
        # Could not acquire lock - check if database was created by another process
        if output_path.exists():
            logger.info(f"Database {output_path} was created by another process")
            return output_path
        else:
            raise RuntimeError(
                f"Could not acquire lock for {output_path} and database does not exist"
            )

    try:
        # Double-check database doesn't exist (another process may have created it while we waited)
        if output_path.exists():
            logger.info(
                f"Database {output_path} was created by another process while waiting for lock"
            )
            return output_path

        # Download and process ATNF catalog
        print("Downloading ATNF Pulsar Catalogue...")
        df_raw = _download_atnf_catalog()
        df_processed = _process_atnf_data(df_raw, min_flux_mjy=None)  # Filter by flux later

        # Filter to declination strip
        df_strip = df_processed[
            (df_processed["dec_deg"] >= dec_min) & (df_processed["dec_deg"] <= dec_max)
        ].copy()

        print(f"Filtered ATNF catalog: {len(df_processed)} :arrow_right: {len(df_strip)} pulsars")
        print(f"Declination range: {dec_min:.6f} to {dec_max:.6f} degrees")

        # Warn if result is empty
        if len(df_strip) == 0:
            logger.warning(
                f":warning:  No ATNF pulsars found in declination range [{dec_min:.2f}°, {dec_max:.2f}°]."
            )

        # Apply flux threshold if specified (use 1400 MHz flux)
        if min_flux_mjy is not None:
            has_flux = df_strip["flux_1400mhz_mjy"].notna()
            bright_enough = df_strip["flux_1400mhz_mjy"] >= min_flux_mjy
            df_strip = df_strip[has_flux & bright_enough].copy()
            print(f"After flux cut ({min_flux_mjy} mJy at 1400 MHz): {len(df_strip)} pulsars")

        # Create SQLite database
        print(f"Creating SQLite database: {output_path}")

        # Enable WAL mode for concurrent reads
        with sqlite3.connect(str(output_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

        with sqlite3.connect(str(output_path)) as conn:
            # Create sources table (same schema as other strip databases)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL,
                    UNIQUE(ra_deg, dec_deg)
                )
            """
            )

            # Create spatial index
            conn.execute("CREATE INDEX IF NOT EXISTS idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flux ON sources(flux_mjy)")

            # Clear existing data
            conn.execute("DELETE FROM sources")

            # Insert sources (use flux_1400mhz_mjy as flux_mjy)
            insert_data = []
            for _, row in df_strip.iterrows():
                ra = float(row["ra_deg"])
                dec = float(row["dec_deg"])
                flux = (
                    float(row["flux_1400mhz_mjy"])
                    if pd.notna(row.get("flux_1400mhz_mjy"))
                    else None
                )

                if np.isfinite(ra) and np.isfinite(dec):
                    insert_data.append((ra, dec, flux))

            conn.executemany(
                "INSERT OR IGNORE INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
                insert_data,
            )

            # Create metadata table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )

            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_center', ?)",
                (str(dec_center),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_min', ?)",
                (str(dec_min),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('dec_max', ?)",
                (str(dec_max),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('build_time_iso', ?)",
                (datetime.now(timezone.utc).isoformat(),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('n_sources', ?)",
                (str(len(insert_data)),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('source_file', ?)",
                ("ATNF Pulsar Catalogue (psrqpy)",),
            )
            if min_flux_mjy is not None:
                conn.execute(
                    "INSERT OR REPLACE INTO meta(key, value) VALUES('min_flux_mjy', ?)",
                    (str(min_flux_mjy),),
                )

            # Store coverage status
            within_coverage = dec_center >= coverage_limits.get(
                "dec_min", -90.0
            ) and dec_center <= coverage_limits.get("dec_max", 90.0)
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES('within_coverage', ?)",
                ("true" if within_coverage else "false",),
            )

            conn.commit()

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f":check: Database created: {output_path}")
        print(f"  Size: {file_size_mb:.2f} MB")
        print(f"  Sources: {len(insert_data)}")

        return output_path
    finally:
        # Always release the lock
        _release_db_lock(lock_fd, lock_path)
