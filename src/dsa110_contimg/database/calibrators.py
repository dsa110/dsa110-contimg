"""
Calibrators Database Management

Manages the calibrators.sqlite3 database for bandpass calibrators,
gain calibrators, and unified catalog sources.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def get_calibrators_db_path() -> Path:
    """Get the path to the calibrators database.

    Returns:
        Path to calibrators.sqlite3
    """
    # Try standard locations
    candidates = [
        Path("/data/dsa110-contimg/state/calibrators.sqlite3"),
        Path("state/calibrators.sqlite3"),
        Path.cwd() / "state" / "calibrators.sqlite3",
    ]

    # Try relative to current file
    try:
        current_file = Path(__file__).resolve()
        potential_root = current_file.parents[2]  # src/dsa110_contimg/database -> root
        candidates.append(potential_root / "state" / "calibrators.sqlite3")
    except Exception:
        pass

    # Return first existing, or default to first candidate
    for candidate in candidates:
        if candidate.parent.exists():
            return candidate

    # Default to first candidate (will create parent if needed)
    return candidates[0]


def ensure_calibrators_db(calibrators_db: Optional[Path] = None) -> sqlite3.Connection:
    """Create/ensure calibrators.sqlite3 database with all required tables.

    Args:
        calibrators_db: Path to database (auto-resolved if None)

    Returns:
        Connection to the database
    """
    if calibrators_db is None:
        calibrators_db = get_calibrators_db_path()

    calibrators_db = Path(calibrators_db)
    calibrators_db.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(calibrators_db))
    conn.row_factory = sqlite3.Row

    # Create bandpass_calibrators table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bandpass_calibrators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calibrator_name TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            dec_range_min REAL,
            dec_range_max REAL,
            source_catalog TEXT,
            flux_jy REAL,
            registered_at REAL NOT NULL,
            registered_by TEXT,
            status TEXT DEFAULT 'active',
            notes TEXT,
            UNIQUE(calibrator_name)
        )
    """
    )

    # Create gain_calibrators table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gain_calibrators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id TEXT NOT NULL,
            source_name TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            flux_jy REAL,
            catalog_source TEXT,
            catalog_id TEXT,
            created_at REAL NOT NULL,
            skymodel_path TEXT,
            notes TEXT,
            UNIQUE(field_id, source_name)
        )
    """
    )

    # Create catalog_sources table (unified VLA/NVSS/FIRST/RACS)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS catalog_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            flux_jy REAL,
            flux_freq_ghz REAL,
            spectral_index REAL,
            catalog TEXT NOT NULL,
            catalog_id TEXT,
            position_uncertainty_arcsec REAL,
            flux_uncertainty REAL,
            is_extended INTEGER DEFAULT 0,
            major_axis_arcsec REAL,
            minor_axis_arcsec REAL,
            position_angle_deg REAL,
            matched_to TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            UNIQUE(catalog, catalog_id)
        )
    """
    )

    # Create vla_calibrators table (from VLA calibrator list)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vla_calibrators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            flux_jy REAL,
            flux_freq_ghz REAL,
            code_20_cm TEXT,
            registered_at REAL NOT NULL,
            notes TEXT
        )
    """
    )

    # Create vla_flux_info table (frequency-specific flux measurements)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vla_flux_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vla_calibrator_id INTEGER NOT NULL,
            frequency_ghz REAL NOT NULL,
            flux_jy REAL NOT NULL,
            flux_uncertainty REAL,
            measurement_date TEXT,
            FOREIGN KEY (vla_calibrator_id) REFERENCES vla_calibrators(id),
            UNIQUE(vla_calibrator_id, frequency_ghz)
        )
    """
    )

    # Create skymodel_metadata table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS skymodel_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id TEXT NOT NULL,
            skymodel_path TEXT NOT NULL,
            n_sources INTEGER NOT NULL,
            total_flux_jy REAL,
            created_at REAL NOT NULL,
            created_by TEXT,
            notes TEXT,
            UNIQUE(field_id, skymodel_path)
        )
    """
    )

    # Create indexes
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bp_dec_range ON bandpass_calibrators(dec_range_min, dec_range_max)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bp_status ON bandpass_calibrators(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bp_name ON bandpass_calibrators(calibrator_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gain_field ON gain_calibrators(field_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_catalog_radec ON catalog_sources(ra_deg, dec_deg)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_catalog_name ON catalog_sources(source_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_catalog_type ON catalog_sources(catalog)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vla_radec ON vla_calibrators(ra_deg, dec_deg)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vla_name ON vla_calibrators(name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_skymodel_field ON skymodel_metadata(field_id)")

    conn.commit()
    return conn


def register_bandpass_calibrator(
    calibrator_name: str,
    ra_deg: float,
    dec_deg: float,
    dec_range_min: Optional[float] = None,
    dec_range_max: Optional[float] = None,
    source_catalog: Optional[str] = None,
    flux_jy: Optional[float] = None,
    registered_by: Optional[str] = None,
    status: str = "active",
    notes: Optional[str] = None,
    calibrators_db: Optional[Path] = None,
) -> int:
    """Register a bandpass calibrator in the database.

    Args:
        calibrator_name: Name of the calibrator (e.g., "3C286")
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        dec_range_min: Minimum declination for which this calibrator is valid
        dec_range_max: Maximum declination for which this calibrator is valid
        source_catalog: Source catalog (e.g., "VLA", "NVSS")
        flux_jy: Flux in Jansky
        registered_by: Who registered this calibrator
        status: Status ("active", "inactive", "deprecated")
        notes: Optional notes
        calibrators_db: Path to database (auto-resolved if None)

    Returns:
        ID of the registered calibrator
    """
    conn = ensure_calibrators_db(calibrators_db)
    registered_at = datetime.now(timezone.utc).timestamp()

    try:
        cursor = conn.execute(
            """
            INSERT OR REPLACE INTO bandpass_calibrators (
                calibrator_name, ra_deg, dec_deg, dec_range_min, dec_range_max,
                source_catalog, flux_jy, registered_at, registered_by, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                calibrator_name,
                ra_deg,
                dec_deg,
                dec_range_min,
                dec_range_max,
                source_catalog,
                flux_jy,
                registered_at,
                registered_by,
                status,
                notes,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logger.error(f"Failed to register bandpass calibrator {calibrator_name}: {e}")
        raise


def get_bandpass_calibrators(
    dec_deg: Optional[float] = None,
    status: Optional[str] = "active",
    calibrators_db: Optional[Path] = None,
) -> List[Dict]:
    """Get bandpass calibrators from the database.

    Args:
        dec_deg: If provided, only return calibrators valid for this declination
        status: Filter by status (default: "active")
        calibrators_db: Path to database (auto-resolved if None)

    Returns:
        List of calibrator dictionaries
    """
    conn = ensure_calibrators_db(calibrators_db)

    query = "SELECT * FROM bandpass_calibrators WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if dec_deg is not None:
        # Check if query dec_deg falls within calibrator's declination range
        # Range is valid if: dec_range_min <= dec_deg <= dec_range_max
        query += " AND (dec_range_min IS NULL OR dec_range_min <= ?)"
        query += " AND (dec_range_max IS NULL OR dec_range_max >= ?)"
        params.append(dec_deg)
        params.append(dec_deg)

    query += " ORDER BY calibrator_name"

    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def register_gain_calibrator(
    field_id: str,
    source_name: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: Optional[float] = None,
    catalog_source: Optional[str] = None,
    catalog_id: Optional[str] = None,
    skymodel_path: Optional[str] = None,
    notes: Optional[str] = None,
    calibrators_db: Optional[Path] = None,
) -> int:
    """Register a gain calibrator source for a field.

    Args:
        field_id: Field identifier
        source_name: Name of the source
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        flux_jy: Flux in Jansky
        catalog_source: Source catalog (e.g., "NVSS", "VLA")
        catalog_id: ID in the source catalog
        skymodel_path: Path to skymodel file containing this source
        notes: Optional notes
        calibrators_db: Path to database (auto-resolved if None)

    Returns:
        ID of the registered gain calibrator
    """
    conn = ensure_calibrators_db(calibrators_db)
    created_at = datetime.now(timezone.utc).timestamp()

    try:
        cursor = conn.execute(
            """
            INSERT OR REPLACE INTO gain_calibrators (
                field_id, source_name, ra_deg, dec_deg, flux_jy,
                catalog_source, catalog_id, created_at, skymodel_path, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                field_id,
                source_name,
                ra_deg,
                dec_deg,
                flux_jy,
                catalog_source,
                catalog_id,
                created_at,
                skymodel_path,
                notes,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logger.error(f"Failed to register gain calibrator {source_name} for {field_id}: {e}")
        raise


def get_gain_calibrators(
    field_id: Optional[str] = None,
    calibrators_db: Optional[Path] = None,
) -> List[Dict]:
    """Get gain calibrators from the database.

    Args:
        field_id: If provided, only return calibrators for this field
        calibrators_db: Path to database (auto-resolved if None)

    Returns:
        List of gain calibrator dictionaries
    """
    conn = ensure_calibrators_db(calibrators_db)

    if field_id:
        cursor = conn.execute(
            "SELECT * FROM gain_calibrators WHERE field_id = ? ORDER BY source_name",
            (field_id,),
        )
    else:
        cursor = conn.execute("SELECT * FROM gain_calibrators ORDER BY field_id, source_name")

    return [dict(row) for row in cursor.fetchall()]
