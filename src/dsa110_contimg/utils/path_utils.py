"""Path utilities for the redesigned directory structure.

This module provides utilities for working with the new stage-based
directory structure while maintaining backward compatibility.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from dsa110_contimg.database.data_config import (
    STAGE_BASE,
    get_calibrated_ms_dir,
    get_raw_ms_dir,
    get_workspace_active_dir,
)


def get_ms_output_path(
    ms_name: str,
    date_str: str,
    is_calibrator: bool = False,
    is_calibrated: bool = False,
) -> Path:
    """Get output path for an MS file in the new structure.

    Args:
        ms_name: Name of the MS file (e.g., "2025-10-28T13:30:07.ms")
        date_str: Date string in YYYY-MM-DD format
        is_calibrator: Whether this is a calibrator MS
        is_calibrated: Whether this MS has been calibrated

    Returns:
        Path to the MS file in the appropriate directory
    """
    if is_calibrated:
        base_dir = get_calibrated_ms_dir()
    else:
        base_dir = get_raw_ms_dir()

    subdir = "calibrators" if is_calibrator else "science"
    return base_dir / subdir / date_str / ms_name


def move_ms_to_calibrated(
    ms_path: Path,
    date_str: Optional[str] = None,
    is_calibrator: bool = False,
) -> Path:
    """Move an MS file from raw to calibrated directory.

    Args:
        ms_path: Current path to the MS file
        date_str: Date string (extracted from path if not provided)
        is_calibrator: Whether this is a calibrator MS

    Returns:
        New path to the calibrated MS file
    """
    import shutil

    if not date_str:
        # Try to extract date from path
        date_str = extract_date_from_path(ms_path)
        if not date_str:
            # Use current date as fallback
            date_str = datetime.now().strftime("%Y-%m-%d")

    # Determine if this is a calibrator MS
    if not is_calibrator:
        is_calibrator = "calibrator" in str(ms_path).lower() or "calibrators" in str(ms_path)

    # Get new path
    ms_name = ms_path.name
    if not ms_name.endswith("_cal.ms"):
        # Add _cal suffix if not already present
        if ms_name.endswith(".ms"):
            ms_name = ms_name[:-3] + "_cal.ms"
        else:
            ms_name = ms_name + "_cal"

    new_path = get_ms_output_path(ms_name, date_str, is_calibrator, is_calibrated=True)

    # Move the file
    new_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(ms_path), str(new_path))
    return new_path


def get_workspace_path(stage: str, job_id: Optional[str] = None) -> Path:
    """Get workspace path for a processing stage.

    Args:
        stage: Stage name (e.g., 'conversion', 'calibration', 'imaging', 'mosaicking')
        job_id: Optional job identifier

    Returns:
        Path to workspace directory for this stage/job
    """
    base = get_workspace_active_dir(stage)
    if job_id:
        return base / job_id
    return base


def ensure_date_directory(base_dir: Path, date_str: str) -> Path:
    """Ensure a date-based subdirectory exists.

    Args:
        base_dir: Base directory
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Path to the date subdirectory
    """
    date_dir = base_dir / date_str
    date_dir.mkdir(parents=True, exist_ok=True)
    return date_dir


def extract_date_from_path(path: Path) -> Optional[str]:
    """Extract date string (YYYY-MM-DD) from a path.

    Args:
        path: Path to analyze

    Returns:
        Date string if found, None otherwise
    """
    parts = path.parts
    for part in parts:
        if len(part) == 10 and part[4] == "-" and part[7] == "-":
            try:
                # Validate it's a valid date
                datetime.strptime(part, "%Y-%m-%d")
                return part
            except ValueError:
                continue
    return None


def get_group_definition_path(group_id: str, date_str: Optional[str] = None) -> Path:
    """Get path for a group definition JSON file.

    Args:
        group_id: Group identifier
        date_str: Date string (extracted if not provided)

    Returns:
        Path to group definition file
    """
    from dsa110_contimg.database.data_config import get_groups_dir

    groups_dir = get_groups_dir()

    if not date_str:
        # Try to extract from group_id or use current date
        date_str = extract_date_from_path(Path(group_id))
        if not date_str:
            from datetime import datetime

            date_str = datetime.now().strftime("%Y-%m-%d")

    date_dir = ensure_date_directory(groups_dir, date_str)
    return date_dir / f"group_{group_id}.json"


def save_group_definition(
    group_id: str,
    ms_files: list,
    start_time: str,
    end_time: str,
    calibrator: Optional[str] = None,
    calibration_tables: Optional[list] = None,
    date_str: Optional[str] = None,
) -> Path:
    """Save a group definition to JSON file.

    Args:
        group_id: Group identifier
        ms_files: List of MS file paths
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        calibrator: Optional calibrator name
        calibration_tables: Optional list of calibration table paths
        date_str: Date string (extracted if not provided)

    Returns:
        Path to saved group definition file
    """
    import json

    if not date_str:
        # Try to extract from first MS file path
        if ms_files:
            date_str = extract_date_from_path(Path(ms_files[0]))
        if not date_str:
            from datetime import datetime

            date_str = datetime.now().strftime("%Y-%m-%d")

    group_path = get_group_definition_path(group_id, date_str)

    definition = {
        "group_id": group_id,
        "start_time": start_time,
        "end_time": end_time,
        "ms_files": [str(p) for p in ms_files],
        "calibrator": calibrator,
        "calibration_tables": [str(p) for p in (calibration_tables or [])],
        "created_at": datetime.now().isoformat(),
    }

    group_path.parent.mkdir(parents=True, exist_ok=True)
    with open(group_path, "w") as f:
        json.dump(definition, f, indent=2)

    return group_path
