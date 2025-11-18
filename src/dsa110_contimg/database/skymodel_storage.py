"""
Skymodel Storage System

Manages creation, storage, and retrieval of skymodels used for gain calibration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from dsa110_contimg.database.calibrators import (
    ensure_calibrators_db,
    get_calibrators_db_path,
    register_gain_calibrator,
)

logger = logging.getLogger(__name__)


def create_skymodel(
    field_id: str,
    sources: List[Dict],
    output_path: Optional[Path] = None,
    created_by: Optional[str] = None,
    notes: Optional[str] = None,
    calibrators_db: Optional[Path] = None,
) -> Path:
    """Create a skymodel file and register it in the database.

    Args:
        field_id: Field identifier
        sources: List of source dictionaries with keys:
                 - source_name: Name of source
                 - ra_deg: RA in degrees
                 - dec_deg: Dec in degrees
                 - flux_jy: Flux in Jansky
                 - catalog_source: Optional catalog name
                 - catalog_id: Optional catalog ID
        output_path: Path to save skymodel (auto-generated if None)
        created_by: Who created this skymodel
        notes: Optional notes
        calibrators_db: Path to calibrators database (auto-resolved if None)

    Returns:
        Path to created skymodel file
    """
    if output_path is None:
        output_path = Path(f"state/skymodels/{field_id}.skymodel")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create skymodel file (format: name, ra, dec, flux)
    with open(output_path, "w") as f:
        f.write("# Skymodel for field {}\n".format(field_id))
        f.write("# Format: name ra_deg dec_deg flux_jy\n")
        f.write("# Created: {}\n".format(datetime.now(timezone.utc).isoformat()))
        if notes:
            f.write("# Notes: {}\n".format(notes))
        f.write("\n")

        total_flux = 0.0
        for source in sources:
            name = source.get("source_name", "UNKNOWN")
            ra = source.get("ra_deg", 0.0)
            dec = source.get("dec_deg", 0.0)
            flux = source.get("flux_jy", 0.0) or 0.0

            f.write(f"{name} {ra:.10f} {dec:.10f} {flux:.10f}\n")
            total_flux += flux

            # Register each source as a gain calibrator
            try:
                register_gain_calibrator(
                    field_id=field_id,
                    source_name=name,
                    ra_deg=ra,
                    dec_deg=dec,
                    flux_jy=flux,
                    catalog_source=source.get("catalog_source"),
                    catalog_id=source.get("catalog_id"),
                    skymodel_path=str(output_path),
                    notes=source.get("notes"),
                    calibrators_db=calibrators_db,
                )
            except Exception as e:
                logger.warning(f"Failed to register gain calibrator {name}: {e}")

    # Register skymodel metadata
    conn = ensure_calibrators_db(calibrators_db)
    created_at = datetime.now(timezone.utc).timestamp()

    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO skymodel_metadata
            (field_id, skymodel_path, n_sources, total_flux_jy, created_at, created_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                field_id,
                str(output_path),
                len(sources),
                total_flux,
                created_at,
                created_by,
                notes,
            ),
        )
        conn.commit()
        logger.info(
            f"Created skymodel for field {field_id}: {output_path} "
            f"({len(sources)} sources, {total_flux:.2f} Jy total)"
        )
    except Exception as e:
        logger.error(f"Failed to register skymodel metadata: {e}")
        raise

    return output_path


def get_skymodel_for_field(
    field_id: str,
    calibrators_db: Optional[Path] = None,
) -> Optional[Dict]:
    """Get skymodel information for a field.

    Args:
        field_id: Field identifier
        calibrators_db: Path to calibrators database (auto-resolved if None)

    Returns:
        Dictionary with skymodel info, or None if not found
    """
    conn = ensure_calibrators_db(calibrators_db)

    cursor = conn.execute(
        """
        SELECT field_id, skymodel_path, n_sources, total_flux_jy,
               created_at, created_by, notes
        FROM skymodel_metadata
        WHERE field_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    """,
        (field_id,),
    )

    row = cursor.fetchone()
    if not row:
        return None

    return {
        "field_id": row[0],
        "skymodel_path": row[1],
        "n_sources": row[2],
        "total_flux_jy": row[3],
        "created_at": row[4],
        "created_by": row[5],
        "notes": row[6],
    }


def list_skymodels(
    field_id: Optional[str] = None,
    calibrators_db: Optional[Path] = None,
) -> List[Dict]:
    """List all skymodels in the database.

    Args:
        field_id: If provided, only return skymodels for this field
        calibrators_db: Path to calibrators database (auto-resolved if None)

    Returns:
        List of skymodel dictionaries
    """
    conn = ensure_calibrators_db(calibrators_db)

    if field_id:
        cursor = conn.execute(
            """
            SELECT field_id, skymodel_path, n_sources, total_flux_jy,
                   created_at, created_by, notes
            FROM skymodel_metadata
            WHERE field_id = ?
            ORDER BY created_at DESC
        """,
            (field_id,),
        )
    else:
        cursor = conn.execute(
            """
            SELECT field_id, skymodel_path, n_sources, total_flux_jy,
                   created_at, created_by, notes
            FROM skymodel_metadata
            ORDER BY field_id, created_at DESC
        """
        )

    return [dict(row) for row in cursor.fetchall()]


def delete_skymodel(
    field_id: str,
    skymodel_path: Optional[str] = None,
    calibrators_db: Optional[Path] = None,
) -> bool:
    """Delete a skymodel and its metadata.

    Args:
        field_id: Field identifier
        skymodel_path: Path to skymodel (if None, deletes all for field)
        calibrators_db: Path to calibrators database (auto-resolved if None)

    Returns:
        True if deleted, False if not found
    """
    conn = ensure_calibrators_db(calibrators_db)

    if skymodel_path:
        cursor = conn.execute(
            """
            DELETE FROM skymodel_metadata
            WHERE field_id = ? AND skymodel_path = ?
        """,
            (field_id, skymodel_path),
        )
    else:
        cursor = conn.execute(
            """
            DELETE FROM skymodel_metadata
            WHERE field_id = ?
        """,
            (field_id,),
        )

    deleted = cursor.rowcount > 0
    conn.commit()

    if deleted:
        # Also delete gain calibrators for this field
        conn.execute(
            """
            DELETE FROM gain_calibrators
            WHERE field_id = ?
        """,
            (field_id,),
        )
        conn.commit()

        # Optionally delete the skymodel file
        if skymodel_path:
            try:
                Path(skymodel_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to delete skymodel file {skymodel_path}: {e}")

        logger.info(f"Deleted skymodel for field {field_id}")
    else:
        logger.warning(f"Skymodel not found for field {field_id}")

    return deleted


def get_sources_for_skymodel(
    field_id: str,
    calibrators_db: Optional[Path] = None,
) -> List[Dict]:
    """Get all sources in a skymodel for a field.

    Args:
        field_id: Field identifier
        calibrators_db: Path to calibrators database (auto-resolved if None)

    Returns:
        List of source dictionaries
    """
    from dsa110_contimg.database.calibrators import get_gain_calibrators

    return get_gain_calibrators(field_id=field_id, calibrators_db=calibrators_db)
