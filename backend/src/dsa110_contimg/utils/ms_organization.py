"""Utilities for organizing MS files into hierarchical directory structures.

This module provides functions to automatically organize CASA Measurement Set (MS) files
into date-based subdirectories according to the pipeline's directory architecture:

- Calibrator MS :arrow_right: ms/calibrators/YYYY-MM-DD/<timestamp>.ms/
- Science MS :arrow_right: ms/science/YYYY-MM-DD/<timestamp>.ms/
- Failed MS :arrow_right: ms/failed/YYYY-MM-DD/<timestamp>.ms/

Organization happens automatically after conversion and updates the products database
to reflect the new file locations.
"""

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Tuple

from dsa110_contimg.database import ensure_products_db, ms_index_upsert

logger = logging.getLogger(__name__)


def extract_date_from_filename(filename: str) -> Optional[str]:
    """Extract YYYY-MM-DD date from filename.

    Args:
        filename: Filename or path containing date string

    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    return match.group(1) if match else None


def get_organized_ms_path(
    ms_path: Path,
    ms_base_dir: Path,
    is_calibrator: bool = False,
    is_failed: bool = False,
    date_str: Optional[str] = None,
) -> Path:
    """Get organized path for MS file based on type and date.

    Organizes MS files into hierarchical structure:
    - Calibrator MS :arrow_right: ms/calibrators/YYYY-MM-DD/<timestamp>.ms/
    - Science MS :arrow_right: ms/science/YYYY-MM-DD/<timestamp>.ms/
    - Failed MS :arrow_right: ms/failed/YYYY-MM-DD/<timestamp>.ms/

    Args:
        ms_path: Current MS file path
        ms_base_dir: Base directory for MS files (e.g., /stage/dsa110-contimg/ms)
        is_calibrator: Whether this is a calibrator observation
        is_failed: Whether this MS represents a failed conversion
        date_str: Date string in YYYY-MM-DD format (extracted from MS filename if None)

    Returns:
        Organized path in appropriate subdirectory (date directory created if needed)
    """
    if date_str is None:
        date_str = extract_date_from_filename(ms_path.name)
        if date_str is None:
            # Fallback: use current date
            date_str = datetime.now().strftime("%Y-%m-%d")

    if is_failed:
        target_dir = ms_base_dir / "failed" / date_str
    elif is_calibrator:
        target_dir = ms_base_dir / "calibrators" / date_str
    else:
        target_dir = ms_base_dir / "science" / date_str

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / ms_path.name


def organize_ms_file(
    ms_path: Path,
    ms_base_dir: Path,
    products_db_path: Path,
    is_calibrator: bool = False,
    is_failed: bool = False,
    date_str: Optional[str] = None,
    update_database: bool = True,
) -> Path:
    """Move MS file to organized directory structure and update database.

    Organizes MS files into date-based subdirectories:
    - Calibrator MS :arrow_right: ms/calibrators/YYYY-MM-DD/
    - Science MS :arrow_right: ms/science/YYYY-MM-DD/
    - Failed MS :arrow_right: ms/failed/YYYY-MM-DD/

    After moving, updates the ms_index table in the pipeline database with the new path.
    This ensures the registry always reflects the current file location.

    Args:
        ms_path: Current MS file path
        ms_base_dir: Base directory for MS files (e.g., /stage/dsa110-contimg/ms)
        products_db_path: Path to pipeline database (unified pipeline.sqlite3)
        is_calibrator: Whether this is a calibrator observation
        is_failed: Whether this MS represents a failed conversion
        date_str: Date string in YYYY-MM-DD format (extracted from MS filename if None)
        update_database: Whether to update database paths (default: True)

    Returns:
        New organized path (or original path if move fails or already organized)

    Note:
        CASA MS files are directories, so this uses shutil.move() which handles
        directory moves correctly. If the MS is already in an organized location,
        no move is performed.
    """
    try:
        # Check if already organized
        ms_resolved = ms_path.resolve()
        parent_name = ms_resolved.parent.name

        # If already in organized subdirectory, return as-is
        if parent_name in ["calibrators", "science", "failed"]:
            logger.debug(f"MS file already organized: {ms_path}")
            return ms_path

        organized_path = get_organized_ms_path(
            ms_path, ms_base_dir, is_calibrator, is_failed, date_str
        )

        # Only move if not already in organized location
        if ms_resolved != organized_path.resolve():
            if ms_path.exists():
                # Move MS directory
                shutil.move(str(ms_path), str(organized_path))
                logger.info(f"Moved MS file to organized location: {organized_path}")

                # Move associated flagversions if present
                flagversions_path = Path(str(ms_path) + ".flagversions")
                if flagversions_path.exists():
                    flagversions_target = Path(str(organized_path) + ".flagversions")
                    shutil.move(str(flagversions_path), str(flagversions_target))
                    logger.debug(f"Moved flagversions: {flagversions_target}")

                # Update database with new path
                if update_database:
                    try:
                        conn = ensure_products_db(products_db_path)
                        # Get existing metadata
                        existing = conn.execute(
                            "SELECT start_mjd, end_mjd, mid_mjd, status, stage, cal_applied, imagename "
                            "FROM ms_index WHERE path = ?",
                            (str(ms_path),),
                        ).fetchone()

                        if existing:
                            # Update path while preserving metadata
                            ms_index_upsert(
                                conn,
                                str(organized_path),
                                start_mjd=existing[0],
                                end_mjd=existing[1],
                                mid_mjd=existing[2],
                                status=existing[3],
                                stage=existing[4],
                                cal_applied=existing[5],
                                imagename=existing[6],
                            )
                            # Remove old path entry
                            conn.execute("DELETE FROM ms_index WHERE path = ?", (str(ms_path),))
                            conn.commit()
                            logger.debug(f"Updated database path: {ms_path} :arrow_right: {organized_path}")
                        else:
                            # No existing entry, just register new path
                            ms_index_upsert(conn, str(organized_path))
                            conn.commit()
                            logger.debug(f"Registered new organized path: {organized_path}")
                        conn.close()
                    except Exception as e:
                        logger.warning(f"Failed to update database after organizing MS: {e}")

                return organized_path
            else:
                logger.warning(f"MS file does not exist: {ms_path}")
                return ms_path

        return organized_path

    except Exception as e:
        logger.warning(f"Failed to organize MS file {ms_path}: {e}. Using original path.")
        return ms_path


def create_path_mapper(
    ms_base_dir: Path, is_calibrator: bool = False, is_failed: bool = False
) -> Callable[[str, str], str]:
    """Create a path mapper function for writing MS files directly to organized locations.

    This function returns a callable that can be passed to convert_subband_groups_to_ms()
    as the path_mapper parameter. It will write MS files directly to organized subdirectories
    instead of flat locations.

    Args:
        ms_base_dir: Base directory for MS files (e.g., /stage/dsa110-contimg/ms)
        is_calibrator: Whether MS files are calibrator observations (default: False)
        is_failed: Whether MS files represent failed conversions (default: False)

    Returns:
        Path mapper function: (base_name: str, output_dir: str) -> str

    Example:
        >>> mapper = create_path_mapper(Path("/stage/dsa110-contimg/ms"), is_calibrator=False)
        >>> path = mapper("2025-10-28T13:30:07", "/stage/dsa110-contimg/ms")
        >>> # Returns: "/stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:30:07.ms"
    """

    def path_mapper(base_name: str, output_dir: str) -> str:
        """Map base_name to organized MS path."""
        # Extract date from base_name (format: YYYY-MM-DDTHH:MM:SS)
        date_str = extract_date_from_filename(base_name)
        if date_str is None:
            # Fallback: use current date
            date_str = datetime.now().strftime("%Y-%m-%d")

        # Determine target subdirectory
        if is_failed:
            target_dir = ms_base_dir / "failed" / date_str
        elif is_calibrator:
            target_dir = ms_base_dir / "calibrators" / date_str
        else:
            target_dir = ms_base_dir / "science" / date_str

        # Ensure directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        # Return full path
        return str(target_dir / f"{base_name}.ms")

    return path_mapper


def determine_ms_type(ms_path: Path) -> Tuple[bool, bool]:
    """Determine if MS is calibrator or failed based on path and content.

    Args:
        ms_path: Path to MS file

    Returns:
        Tuple of (is_calibrator, is_failed)
    """
    # Check path for indicators
    path_str = str(ms_path).lower()

    # Check for failed indicators
    is_failed = "failed" in path_str or "error" in path_str or "corrupt" in path_str

    # Check for calibrator indicators
    is_calibrator = (
        "calibrator" in path_str or "cal" in path_str or ms_path.parent.name == "calibrators"
    )

    # If already in organized structure, use parent directory
    parent_name = ms_path.parent.name
    if parent_name == "calibrators":
        is_calibrator = True
    elif parent_name == "failed":
        is_failed = True
    elif parent_name == "science":
        is_calibrator = False
        is_failed = False

    return is_calibrator, is_failed
