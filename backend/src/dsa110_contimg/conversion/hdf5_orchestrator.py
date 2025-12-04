"""
HDF5 Subband Group Orchestrator for DSA-110 Continuum Imaging Pipeline.

Orchestrates the conversion of HDF5 subband files to Measurement Sets,
handling subband grouping, combination, and MS writing with proper
error handling and logging.

Configuration is loaded from settings.conversion for rarely-changed parameters.
Only essential arguments (input, output, time range) are passed to functions.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

import pyuvdata

from dsa110_contimg.config import settings
from dsa110_contimg.conversion.writers import get_writer
from dsa110_contimg.database.hdf5_index import query_subband_groups
from dsa110_contimg.utils import FastMeta, timed, timed_debug
from dsa110_contimg.utils.antpos_local import get_itrf
from dsa110_contimg.utils.exceptions import (
    ConversionError,
    IncompleteSubbandGroupError,
    MSWriteError,
    UVH5ReadError,
    is_recoverable,
    wrap_exception,
)
from dsa110_contimg.utils.logging_config import log_context, log_exception

logger = logging.getLogger(__name__)

# Regex to match subband codes in filenames (e.g., "_sb00", "_sb15")
_SUBBAND_PATTERN = re.compile(r"_sb(\d{2})")


def _extract_subband_code(filename: str) -> Optional[str]:
    """Extract the subband code (e.g., 'sb00') from a filename.

    DSA-110 subband files follow the pattern: {timestamp}_sb{NN}.hdf5
    where NN is a two-digit subband number (00-15).

    Args:
        filename: Filename or path to extract subband code from.

    Returns:
        Subband code like 'sb00', 'sb15', or None if not found.
    """
    basename = os.path.basename(filename)
    match = _SUBBAND_PATTERN.search(basename)
    if match:
        return f"sb{match.group(1)}"
    return None


@timed("conversion.convert_subband_groups")
def convert_subband_groups_to_ms(
    input_dir: str,
    output_dir: str,
    start_time: str,
    end_time: str,
    *,
    # Override settings if needed (most callers just use defaults)
    tolerance_s: Optional[float] = None,
    skip_incomplete: Optional[bool] = None,
    skip_existing: Optional[bool] = None,
) -> dict:
    """
    Orchestrates the conversion of HDF5 subband files to Measurement Sets.

    Most parameters are pulled from settings.conversion. Only override
    explicitly if you need non-default behavior.

    Parameters:
        input_dir: Directory containing the HDF5 subband files.
        output_dir: Directory where the Measurement Sets will be saved.
        start_time: Start time for the conversion window (ISO format).
        end_time: End time for the conversion window (ISO format).
        tolerance_s: Time tolerance for grouping subbands (default: settings.conversion.cluster_tolerance_s).
        skip_incomplete: Skip incomplete groups (default: settings.conversion.skip_incomplete).
        skip_existing: Skip existing MS files (default: settings.conversion.skip_existing).

    Returns:
        Dictionary with conversion statistics:
        - converted: List of successfully converted group IDs
        - skipped: List of skipped group IDs (incomplete or existing)
        - failed: List of failed group IDs with error details

    Raises:
        ConversionError: If no groups are found or critical error occurs.
    """
    # Apply settings defaults for optional parameters
    if tolerance_s is None:
        tolerance_s = settings.conversion.cluster_tolerance_s
    if skip_incomplete is None:
        skip_incomplete = settings.conversion.skip_incomplete
    if skip_existing is None:
        skip_existing = settings.conversion.skip_existing

    results = {
        "converted": [],
        "skipped": [],
        "failed": [],
    }

    # Validate paths
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        raise ConversionError(
            f"Input directory does not exist: {input_dir}",
            input_path=input_dir,
        )

    # Create output directory if needed
    output_path.mkdir(parents=True, exist_ok=True)

    # Query subband groups based on the provided time window
    hdf5_db = os.path.join(input_dir, 'hdf5_file_index.sqlite3')

    try:
        groups = query_subband_groups(hdf5_db, start_time, end_time, tolerance_s=tolerance_s)
    except Exception as e:
        raise ConversionError(
            f"Failed to query subband groups from database: {e}",
            input_path=input_dir,
            original_exception=e,
        ) from e

    if not groups:
        logger.warning(
            "No subband groups found in time window",
            extra={
                "input_dir": input_dir,
                "start_time": start_time,
                "end_time": end_time,
                "tolerance_s": tolerance_s,
            }
        )
        return results

    logger.info(
        f"Found {len(groups)} subband groups to process",
        extra={
            "input_dir": input_dir,
            "start_time": start_time,
            "end_time": end_time,
            "group_count": len(groups),
        }
    )

    for group in groups:
        group_id = _extract_group_id(group)

        with log_context(group_id=group_id, pipeline_stage="conversion"):
            try:
                result = _convert_single_group(
                    group=group,
                    group_id=group_id,
                    output_dir=output_dir,
                    skip_incomplete=skip_incomplete,
                    skip_existing=skip_existing,
                )

                if result == "converted":
                    results["converted"].append(group_id)
                elif result == "skipped":
                    results["skipped"].append(group_id)

            except IncompleteSubbandGroupError as e:
                # Log warning but continue with next group
                logger.warning(
                    str(e),
                    extra=e.context,
                )
                results["skipped"].append(group_id)

            except (UVH5ReadError, MSWriteError, ConversionError) as e:
                # Log error with full context
                log_exception(logger, e, group_id=group_id)
                results["failed"].append({
                    "group_id": group_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "recoverable": e.recoverable,
                })

                # Re-raise if not recoverable
                if not e.recoverable:
                    raise

            except Exception as e:
                # Unexpected error - wrap and log
                wrapped = wrap_exception(
                    e,
                    ConversionError,
                    f"Unexpected error during conversion: {e}",
                    group_id=group_id,
                )
                log_exception(logger, wrapped, group_id=group_id)
                results["failed"].append({
                    "group_id": group_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "recoverable": is_recoverable(e),
                })

    # Log summary
    logger.info(
        f"Conversion complete: {len(results['converted'])} converted, "
        f"{len(results['skipped'])} skipped, {len(results['failed'])} failed",
        extra={
            "converted_count": len(results["converted"]),
            "skipped_count": len(results["skipped"]),
            "failed_count": len(results["failed"]),
        }
    )

    return results


@timed_debug("conversion.convert_single_group")
def _convert_single_group(
    group: list[str],
    group_id: str,
    output_dir: str,
    skip_incomplete: bool,
    skip_existing: bool,
) -> str:
    """
    Convert a single subband group to Measurement Set.

    Returns:
        "converted" if successful, "skipped" if skipped

    Raises:
        IncompleteSubbandGroupError: If group is incomplete and skip_incomplete=True
        UVH5ReadError: If reading UVH5 fails
        MSWriteError: If writing MS fails
    """
    # Check for complete group (use settings for expected count)
    expected_subbands = settings.conversion.expected_subbands
    if len(group) < expected_subbands:
        if skip_incomplete:
            raise IncompleteSubbandGroupError(
                group_id=group_id,
                expected_count=expected_subbands,
                actual_count=len(group),
                missing_subbands=_find_missing_subbands(group),
            )
        else:
            logger.warning(
                f"Processing incomplete group: {len(group)}/{expected_subbands} subbands",
                extra={
                    "group_id": group_id,
                    "subband_count": len(group),
                    "expected_count": expected_subbands,
                }
            )

    # Prepare output path
    output_path = os.path.join(output_dir, f"{group_id}.ms")

    if skip_existing and os.path.exists(output_path):
        logger.info(
            f"Skipping existing MS: {output_path}",
            extra={"output_path": output_path}
        )
        return "skipped"

    logger.info(
        f"Converting {len(group)} subbands to {output_path}",
        extra={
            "subband_count": len(group),
            "output_path": output_path,
            "file_list": group,
        }
    )

    # Combine subbands using pyuvdata (with parallel I/O from settings)
    uvdata = _load_and_combine_subbands(
        group,
        group_id,
        parallel=settings.conversion.parallel_loading,
        max_workers=settings.conversion.io_max_workers,
    )

    # Get antenna positions
    try:
        antpos = get_itrf()
        logger.debug("Loaded antenna positions", extra={"ant_count": len(antpos)})
    except Exception as e:
        raise ConversionError(
            f"Failed to load antenna positions: {e}",
            group_id=group_id,
            original_exception=e,
        ) from e

    # Write Measurement Set (use settings for writer type)
    try:
        writer_type = settings.conversion.writer_type
        writer_cls = get_writer(writer_type)
        writer_instance = writer_cls(uvdata, output_path)
        actual_writer = writer_instance.write()

        logger.info(
            f"Successfully wrote MS: {output_path}",
            extra={
                "output_path": output_path,
                "writer_type": actual_writer,
            }
        )
    except Exception as e:
        raise MSWriteError(
            output_path=output_path,
            reason=str(e),
            original_exception=e,
            group_id=group_id,
        ) from e

    return "converted"


def _load_single_subband(subband_file: str, group_id: str) -> pyuvdata.UVData:
    """Load a single subband file.

    This function is designed to be called in parallel for I/O-bound speedup.
    Thread-safe: Each call creates its own UVData object.

    Args:
        subband_file: Path to the UVH5 subband file.
        group_id: Group identifier for error messages.

    Returns:
        Loaded UVData object.

    Raises:
        UVH5ReadError: If reading fails.
    """
    try:
        # Validate file with fast metadata read first
        with FastMeta(subband_file) as meta:
            _ = meta.time_array  # Quick validation

        # Read full data
        subband_data = pyuvdata.UVData()
        subband_data.read(subband_file, strict_uvw_antpos_check=False)
        return subband_data

    except FileNotFoundError as e:
        raise UVH5ReadError(
            file_path=subband_file,
            reason="File not found",
            original_exception=e,
            group_id=group_id,
        ) from e
    except Exception as e:
        raise UVH5ReadError(
            file_path=subband_file,
            reason=str(e),
            original_exception=e,
            group_id=group_id,
        ) from e


@timed_debug("conversion.load_and_combine_subbands")
def _load_and_combine_subbands(
    group: list[str],
    group_id: str,
    *,
    parallel: bool = True,
    max_workers: int = 4,
) -> pyuvdata.UVData:
    """Load and combine subband files into a single UVData object.

    Args:
        group: List of subband file paths.
        group_id: Group identifier for logging/errors.
        parallel: If True, load subbands in parallel (default: True).
        max_workers: Maximum number of parallel I/O threads (default: 4).
            Higher values may not help due to HDD seek limits.

    Returns:
        Combined UVData object with all subbands merged.

    Raises:
        UVH5ReadError: If any subband file fails to read.
        ConversionError: If no valid data is loaded.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    sorted_files = sorted(group)
    n_files = len(sorted_files)

    if n_files == 0:
        raise ConversionError(
            "No subband files provided",
            group_id=group_id,
        )

    # For small groups or if parallel disabled, use sequential loading
    if not parallel or n_files <= 2:
        return _load_subbands_sequential(sorted_files, group_id)

    # Parallel loading: load all subbands concurrently, then combine
    logger.info(
        f"Loading {n_files} subbands in parallel (max_workers={max_workers})",
        extra={
            "group_id": group_id,
            "subband_count": n_files,
            "max_workers": max_workers,
        }
    )

    # Use dict to preserve order: {file_index: UVData}
    loaded_subbands: dict[int, pyuvdata.UVData] = {}
    errors: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all load tasks
        future_to_index = {
            executor.submit(_load_single_subband, f, group_id): i
            for i, f in enumerate(sorted_files)
        }

        # Collect results as they complete
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            file_path = sorted_files[idx]

            try:
                uvdata = future.result()
                loaded_subbands[idx] = uvdata
                logger.debug(
                    f"Loaded subband {idx + 1}/{n_files}: {file_path}",
                    extra={"subband_index": idx, "subband_file": file_path}
                )
            except UVH5ReadError as e:
                errors.append((file_path, str(e)))
                logger.error(
                    f"Failed to load subband {idx + 1}/{n_files}: {e}",
                    extra={"subband_index": idx, "subband_file": file_path}
                )

    # Check for load failures
    if errors:
        failed_files = [f for f, _ in errors]
        raise UVH5ReadError(
            file_path=failed_files[0],
            reason=f"Failed to load {len(errors)} subband(s): {errors[0][1]}",
            group_id=group_id,
        )

    if not loaded_subbands:
        raise ConversionError(
            "No valid subband data loaded",
            group_id=group_id,
        )

    # Combine subbands in order (must be sequential for memory safety)
    logger.debug(
        f"Combining {len(loaded_subbands)} subbands sequentially",
        extra={"group_id": group_id}
    )

    uvdata = None
    for idx in range(n_files):
        if idx not in loaded_subbands:
            continue

        subband_data = loaded_subbands[idx]
        if uvdata is None:
            uvdata = subband_data
        else:
            uvdata += subband_data

        # Free memory as we go
        del loaded_subbands[idx]

    if uvdata is None:
        raise ConversionError(
            "No valid subband data loaded after combining",
            group_id=group_id,
        )

    return uvdata


def _load_subbands_sequential(
    sorted_files: list[str],
    group_id: str,
) -> pyuvdata.UVData:
    """Sequential subband loading (fallback when parallel is disabled).

    Args:
        sorted_files: List of subband file paths (sorted).
        group_id: Group identifier for logging/errors.

    Returns:
        Combined UVData object.

    Raises:
        UVH5ReadError: If any file fails to read.
        ConversionError: If no data loaded.
    """
    uvdata = None

    for i, subband_file in enumerate(sorted_files):
        logger.debug(
            f"Loading subband {i + 1}/{len(sorted_files)}: {subband_file}",
            extra={
                "subband_index": i,
                "subband_file": subband_file,
            }
        )

        subband_data = _load_single_subband(subband_file, group_id)

        if uvdata is None:
            uvdata = subband_data
        else:
            uvdata += subband_data

    if uvdata is None:
        raise ConversionError(
            "No valid subband data loaded",
            group_id=group_id,
        )

    return uvdata


def _extract_group_id(group: list[str]) -> str:
    """Extract group ID (timestamp) from first file in group."""
    if not group:
        return "unknown"

    first_file = os.path.basename(group[0])
    # Format: 2025-01-15T12:30:00_sb00.hdf5
    return first_file.rsplit("_sb", 1)[0]


def _find_missing_subbands(group: list[str]) -> list[str]:
    """Find which subband indices are missing from a group."""
    expected = set(f"sb{i:02d}" for i in range(16))
    found = set()

    for file_path in group:
        filename = os.path.basename(file_path)
        # Extract sbXX from filename
        for sb in expected:
            if f"_{sb}" in filename:
                found.add(sb)
                break

    return sorted(expected - found)
