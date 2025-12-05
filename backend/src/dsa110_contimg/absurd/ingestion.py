"""
ABSURD-based ingestion tasks for DSA-110 subband files.

This module provides durable task-based ingestion that replaces the
streaming_converter's SQLite-based queue. Benefits:

- Unified observability (Prometheus metrics, WebSocket events)
- Dead letter queue for failed ingests
- Consistent retry semantics with rest of pipeline
- Single queue system (PostgreSQL) instead of hybrid

Architecture:
    watchdog → spawn "record-subband" → ABSURD claims →
    when group complete → spawn "convert-group" → MS output

Tasks:
    - record-subband: Record a single subband file arrival
    - check-group-complete: Check if a group has all 16 subbands
    - normalize-group: Rename files to use sb00's timestamp
    - convert-group: Convert complete group to MS
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import h5py  # type: ignore[import-unresolved]
import numpy as np  # type: ignore[import-unresolved]

logger = logging.getLogger(__name__)

# Constants
EXPECTED_SUBBANDS = 16
CLUSTER_TOLERANCE_S = 60.0  # Seconds tolerance for grouping subbands
DEFAULT_QUEUE = "dsa110-ingestion"

# Subband filename pattern: 2025-01-15T12:00:00_sb05.hdf5
SUBBAND_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb(?P<index>\d{2})\.hdf5$"
)


def parse_subband_filename(filename: str) -> Optional[Tuple[str, int]]:
    """Parse subband filename to extract group_id and subband index.

    Args:
        filename: Filename like "2025-01-15T12:00:00_sb05.hdf5"

    Returns:
        Tuple of (group_id, subband_idx) or None if not matched
    """
    match = SUBBAND_PATTERN.search(filename)
    if not match:
        return None
    return match.group("timestamp"), int(match.group("index"))


def build_subband_filename(group_id: str, subband_idx: int) -> str:
    """Build canonical subband filename.

    Args:
        group_id: Timestamp string (YYYY-MM-DDTHH:MM:SS)
        subband_idx: Subband index (0-15)

    Returns:
        Filename like "2025-01-15T12:00:00_sb05.hdf5"
    """
    return f"{group_id}_sb{subband_idx:02d}.hdf5"


async def execute_record_subband(params: Dict[str, Any]) -> Dict[str, Any]:
    """Record a subband file arrival in the ingestion database.

    This task is spawned by the file watcher when a new HDF5 file appears.
    It validates the file, extracts metadata, and records it in the
    subband tracking table. If the group becomes complete (16 subbands),
    it spawns a normalize-group task.

    Args:
        params: Must contain:
            - inputs:
                - file_path: Path to the HDF5 subband file
                - incoming_dir: Base directory for incoming files

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs:
                - group_id: Canonical group ID
                - subband_idx: Subband index (0-15)
                - subband_count: Current count for this group
                - group_complete: Whether group now has 16 subbands
            - message: Status message
    """
    logger.info("[Absurd/Ingestion] Recording subband arrival")

    try:
        inputs = params.get("inputs", {})
        file_path = inputs.get("file_path")

        if not file_path:
            return {
                "status": "error",
                "message": "Missing required input: file_path",
                "errors": ["file_path not provided"],
            }

        path = Path(file_path)

        # Validate file exists and is readable
        if not path.exists():
            return {
                "status": "error",
                "message": f"File does not exist: {file_path}",
                "errors": ["file_not_found"],
            }

        if not os.access(file_path, os.R_OK):
            return {
                "status": "error",
                "message": f"File not readable: {file_path}",
                "errors": ["file_not_readable"],
            }

        # Parse filename
        parsed = parse_subband_filename(path.name)
        if parsed is None:
            return {
                "status": "error",
                "message": f"Invalid subband filename: {path.name}",
                "errors": ["invalid_filename_pattern"],
            }

        original_group_id, subband_idx = parsed

        # Validate HDF5 structure
        try:
            with h5py.File(file_path, "r") as f:
                if "Header" not in f and "Data" not in f:
                    return {
                        "status": "error",
                        "message": "Invalid HDF5: missing Header/Data groups",
                        "errors": ["invalid_hdf5_structure"],
                    }
                # Extract pointing for metadata
                dec_deg = None
                if "Header/extra_keywords/phase_center_dec" in f:
                    dec_rad = float(f["Header/extra_keywords/phase_center_dec"][()])
                    dec_deg = float(np.degrees(dec_rad))
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read HDF5: {e}",
                "errors": ["hdf5_read_error"],
            }

        # Find or create group (cluster with existing if within tolerance)
        # This requires database access - delegate to helper
        from dsa110_contimg.absurd.ingestion_db import (
            find_or_create_group,
            record_subband,
            get_group_subband_count,
        )

        canonical_group_id = await find_or_create_group(
            original_group_id,
            tolerance_s=CLUSTER_TOLERANCE_S,
        )

        # Record subband
        await record_subband(
            group_id=canonical_group_id,
            subband_idx=subband_idx,
            file_path=str(path),
            dec_deg=dec_deg,
        )

        # Check if group is complete
        subband_count = await get_group_subband_count(canonical_group_id)
        group_complete = subband_count >= EXPECTED_SUBBANDS

        logger.info(
            f"[Absurd/Ingestion] Recorded sb{subband_idx:02d} for group {canonical_group_id} "
            f"({subband_count}/{EXPECTED_SUBBANDS})"
        )

        # If complete, spawn normalize-group task
        if group_complete:
            logger.info(f"[Absurd/Ingestion] Group {canonical_group_id} complete, spawning normalize task")
            # Note: Task chaining handled by caller or via depends_on

        return {
            "status": "success",
            "outputs": {
                "group_id": canonical_group_id,
                "subband_idx": subband_idx,
                "subband_count": subband_count,
                "group_complete": group_complete,
                "dec_deg": dec_deg,
            },
            "message": f"Recorded subband {subband_idx} for group {canonical_group_id}",
        }

    except Exception as e:
        logger.exception(f"[Absurd/Ingestion] Record subband failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_normalize_group(params: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize all files in a group to use sb00's timestamp.

    This task renames all subband files to use the timestamp from sb00
    as the canonical group_id. This ensures consistent naming and
    simplifies downstream processing.

    Args:
        params: Must contain:
            - inputs:
                - group_id: Current group ID

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs:
                - canonical_group_id: The sb00-based group ID
                - files_renamed: Number of files renamed
            - message: Status message
    """
    logger.info("[Absurd/Ingestion] Normalizing group to sb00 timestamp")

    try:
        inputs = params.get("inputs", {})
        group_id = inputs.get("group_id")

        if not group_id:
            return {
                "status": "error",
                "message": "Missing required input: group_id",
                "errors": ["group_id not provided"],
            }

        from dsa110_contimg.absurd.ingestion_db import get_group_files
        from dsa110_contimg.conversion.streaming.normalize import normalize_subband_path

        # Get all files in group
        files = await get_group_files(group_id)

        if not files:
            return {
                "status": "error",
                "message": f"No files found for group {group_id}",
                "errors": ["group_empty"],
            }

        # Find sb00's path and extract its timestamp
        sb00_path = None
        for subband_idx, file_path in files.items():
            if subband_idx == 0:
                sb00_path = file_path
                break

        if sb00_path is None:
            return {
                "status": "error",
                "message": f"sb00 not found in group {group_id}",
                "errors": ["sb00_missing"],
            }

        # Extract canonical group_id from sb00
        parsed = parse_subband_filename(Path(sb00_path).name)
        if parsed is None:
            return {
                "status": "error",
                "message": f"Could not parse sb00 filename: {sb00_path}",
                "errors": ["sb00_parse_error"],
            }

        canonical_group_id = parsed[0]

        # Rename files if needed
        files_renamed = 0
        new_paths: Dict[int, str] = {}

        for subband_idx, old_path in files.items():
            try:
                new_path, was_renamed = await asyncio.to_thread(
                    normalize_subband_path,
                    Path(old_path),
                    canonical_group_id,
                    dry_run=False,
                )
                new_paths[subband_idx] = str(new_path)
                if was_renamed:
                    files_renamed += 1
            except Exception as e:
                logger.error(f"Failed to normalize sb{subband_idx:02d}: {e}")
                new_paths[subband_idx] = old_path

        # Update database with new paths and group_id
        from dsa110_contimg.absurd.ingestion_db import update_group_after_normalize

        await update_group_after_normalize(
            old_group_id=group_id,
            new_group_id=canonical_group_id,
            new_paths=new_paths,
        )

        logger.info(
            f"[Absurd/Ingestion] Normalized group {group_id} → {canonical_group_id} "
            f"({files_renamed} files renamed)"
        )

        return {
            "status": "success",
            "outputs": {
                "canonical_group_id": canonical_group_id,
                "files_renamed": files_renamed,
                "file_paths": new_paths,
            },
            "message": f"Normalized {files_renamed} files to group {canonical_group_id}",
        }

    except Exception as e:
        logger.exception(f"[Absurd/Ingestion] Normalize group failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_convert_group(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a complete subband group to Measurement Set.

    This task takes a normalized group of 16 subbands and converts
    them to a single MS file using pyuvdata.

    Args:
        params: Must contain:
            - inputs:
                - group_id: Canonical group ID (from normalize-group)
            - config: Optional PipelineConfig

    Returns:
        Result dict with:
            - status: "success" or "error"
            - outputs:
                - ms_path: Path to output MS
                - group_id: Group ID
            - message: Status message
    """
    logger.info("[Absurd/Ingestion] Converting group to MS")

    try:
        inputs = params.get("inputs", {})
        group_id = inputs.get("group_id")
        output_dir = inputs.get("output_dir", "/stage/dsa110-contimg/ms")

        if not group_id:
            return {
                "status": "error",
                "message": "Missing required input: group_id",
                "errors": ["group_id not provided"],
            }

        from dsa110_contimg.absurd.ingestion_db import get_group_files, update_group_state
        from dsa110_contimg.conversion.hdf5_orchestrator import (
            _convert_single_group,
        )

        # Get file paths
        files = await get_group_files(group_id)

        if len(files) < EXPECTED_SUBBANDS:
            return {
                "status": "error",
                "message": f"Incomplete group: {len(files)}/{EXPECTED_SUBBANDS} subbands",
                "errors": ["incomplete_group"],
            }

        # Convert dict to sorted list
        file_list = [files[i] for i in sorted(files.keys())]

        # Mark group as in-progress
        await update_group_state(group_id, "converting")

        # Execute conversion in thread pool
        try:
            await asyncio.to_thread(
                _convert_single_group,
                group=file_list,
                group_id=group_id,
                output_dir=str(output_dir),
                skip_incomplete=False,
                skip_existing=False,
            )
            ms_path = Path(output_dir) / f"{group_id}.ms"
        except Exception as conv_err:
            await update_group_state(group_id, "failed", error=str(conv_err))
            raise

        # Mark group as complete
        await update_group_state(group_id, "completed", ms_path=str(ms_path))

        logger.info(f"[Absurd/Ingestion] Conversion complete: {ms_path}")

        return {
            "status": "success",
            "outputs": {
                "ms_path": str(ms_path),
                "group_id": group_id,
            },
            "message": f"Converted group {group_id} to {ms_path}",
        }

    except Exception as e:
        logger.exception(f"[Absurd/Ingestion] Convert group failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


# Task chain for complete ingestion pipeline
INGESTION_CHAIN = [
    "record-subband",      # Record file arrival
    "normalize-group",     # Normalize filenames when complete
    "convert-group",       # Convert to MS
]
