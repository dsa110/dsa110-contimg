"""
HDF5 file indexing and querying for DSA-110 Continuum Imaging Pipeline.

This module provides utilities for indexing, querying, and grouping HDF5
subband files with proper error handling and logging.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import h5py

from dsa110_contimg.utils.exceptions import (
    DatabaseError,
    UVH5ReadError,
    ValidationError,
    InvalidPathError,
)
from dsa110_contimg.utils.logging_config import log_context

logger = logging.getLogger(__name__)


def index_hdf5_files(directory: str) -> list[tuple[str, list[str]]]:
    """
    Index HDF5 files in the specified directory.

    Args:
        directory: The path to the directory containing HDF5 files.

    Returns:
        A list of tuples where each tuple contains the filename and 
        a list of datasets within that file.

    Raises:
        InvalidPathError: If the directory does not exist.
        UVH5ReadError: If an HDF5 file cannot be read.
    """
    if not os.path.isdir(directory):
        raise InvalidPathError(
            path=directory,
            path_type="directory",
            reason="Directory does not exist",
        )

    indexed_files = []
    errors = []

    for filename in os.listdir(directory):
        if not filename.endswith('.hdf5'):
            continue
            
        file_path = os.path.join(directory, filename)
        
        try:
            with h5py.File(file_path, 'r') as hdf_file:
                datasets = list(hdf_file.keys())
                indexed_files.append((filename, datasets))
                logger.debug(
                    f"Indexed HDF5 file: {filename}",
                    extra={
                        "file_path": file_path,
                        "dataset_count": len(datasets),
                    }
                )
        except OSError as e:
            error_msg = f"Failed to read HDF5 file: {filename}: {e}"
            logger.warning(error_msg, extra={"file_path": file_path})
            errors.append({"file": filename, "error": str(e)})
        except Exception as e:
            error_msg = f"Unexpected error reading HDF5 file: {filename}: {e}"
            logger.error(error_msg, exc_info=True, extra={"file_path": file_path})
            errors.append({"file": filename, "error": str(e)})

    if errors:
        logger.warning(
            f"Indexed {len(indexed_files)} files with {len(errors)} errors",
            extra={
                "directory": directory,
                "indexed_count": len(indexed_files),
                "error_count": len(errors),
                "errors": errors,
            }
        )
    else:
        logger.info(
            f"Indexed {len(indexed_files)} HDF5 files",
            extra={
                "directory": directory,
                "indexed_count": len(indexed_files),
            }
        )

    return indexed_files


def query_hdf5_file(file_path: str, dataset_name: str) -> Any:
    """
    Query a specific dataset in an HDF5 file.

    Args:
        file_path: The path to the HDF5 file.
        dataset_name: The name of the dataset to query.

    Returns:
        The data from the specified dataset.

    Raises:
        InvalidPathError: If the file does not exist.
        UVH5ReadError: If the file cannot be read.
        ValidationError: If the dataset is not found.
    """
    if not os.path.isfile(file_path):
        raise InvalidPathError(
            path=file_path,
            path_type="file",
            reason="File does not exist",
        )

    try:
        with h5py.File(file_path, 'r') as hdf_file:
            if dataset_name not in hdf_file:
                available = list(hdf_file.keys())
                raise ValidationError(
                    f"Dataset '{dataset_name}' not found in '{file_path}'",
                    field="dataset_name",
                    value=dataset_name,
                    constraint=f"must be one of: {available}",
                    available_datasets=available,
                    file_path=file_path,
                )
            return hdf_file[dataset_name][:]
            
    except ValidationError:
        raise
    except OSError as e:
        raise UVH5ReadError(
            file_path=file_path,
            reason=str(e),
            original_exception=e,
        ) from e
    except Exception as e:
        raise UVH5ReadError(
            file_path=file_path,
            reason=f"Unexpected error: {e}",
            original_exception=e,
        ) from e


def get_hdf5_metadata(file_path: str) -> dict[str, Any]:
    """
    Retrieve metadata from an HDF5 file.

    Args:
        file_path: The path to the HDF5 file.

    Returns:
        A dictionary containing metadata information:
        - filename: Base name of the file
        - datasets: List of dataset names
        - attributes: Dict of file-level attributes

    Raises:
        InvalidPathError: If the file does not exist.
        UVH5ReadError: If the file cannot be read.
    """
    if not os.path.isfile(file_path):
        raise InvalidPathError(
            path=file_path,
            path_type="file",
            reason="File does not exist",
        )

    try:
        with h5py.File(file_path, 'r') as hdf_file:
            metadata = {
                'filename': os.path.basename(file_path),
                'datasets': list(hdf_file.keys()),
                'attributes': {key: hdf_file.attrs[key] for key in hdf_file.attrs}
            }
            
            logger.debug(
                f"Retrieved metadata for {metadata['filename']}",
                extra={
                    "file_path": file_path,
                    "dataset_count": len(metadata['datasets']),
                    "attribute_count": len(metadata['attributes']),
                }
            )
            
            return metadata
            
    except OSError as e:
        raise UVH5ReadError(
            file_path=file_path,
            reason=str(e),
            original_exception=e,
        ) from e
    except Exception as e:
        raise UVH5ReadError(
            file_path=file_path,
            reason=f"Unexpected error: {e}",
            original_exception=e,
        ) from e


def query_subband_groups(
    db_path: str,
    start_time: str,
    end_time: str,
    tolerance_s: float = 1.0,
    cluster_tolerance_s: float = 60.0,
) -> list[list[str]]:
    """
    Query subband file groups from the HDF5 index database.

    Groups files by timestamp within the specified tolerance, returning
    complete or partial subband groups.

    Args:
        db_path: Path to the HDF5 index SQLite database.
        start_time: Start of time window (ISO format).
        end_time: End of time window (ISO format).
        tolerance_s: Small window expansion for query (default: 1.0s).
        cluster_tolerance_s: Tolerance for clustering subbands (default: 60.0s).

    Returns:
        List of subband groups, where each group is a list of file paths.

    Raises:
        DatabaseError: If the database query fails.
        InvalidPathError: If the database file does not exist.
    """
    if not os.path.isfile(db_path):
        raise InvalidPathError(
            path=db_path,
            path_type="file",
            reason="HDF5 index database does not exist",
        )

    with log_context(
        pipeline_stage="subband_grouping",
        db_path=db_path,
        start_time=start_time,
        end_time=end_time,
    ):
        try:
            import sqlite3
            
            conn = sqlite3.connect(db_path, timeout=30)
            cursor = conn.cursor()
            
            # Query files in time window using correct column names
            cursor.execute("""
                SELECT path, timestamp_iso
                FROM hdf5_file_index
                WHERE timestamp_iso BETWEEN ? AND ?
                ORDER BY timestamp_iso, path
            """, (start_time, end_time))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Group by timestamp within tolerance
            groups = _cluster_by_timestamp(rows, cluster_tolerance_s)
            
            logger.info(
                f"Found {len(groups)} subband groups",
                extra={
                    "group_count": len(groups),
                    "file_count": sum(len(g) for g in groups),
                    "start_time": start_time,
                    "end_time": end_time,
                }
            )
            
            return groups
            
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to query HDF5 index database: {e}",
                db_name="hdf5",
                db_path=db_path,
                operation="query",
                table_name="hdf5_file_index",
                original_exception=e,
            ) from e
        except Exception as e:
            raise DatabaseError(
                f"Unexpected error querying HDF5 index: {e}",
                db_name="hdf5",
                db_path=db_path,
                operation="query",
                original_exception=e,
            ) from e


def _cluster_by_timestamp(
    rows: list[tuple[str, str]],
    tolerance_s: float,
) -> list[list[str]]:
    """
    Cluster file paths by timestamp within tolerance.

    Args:
        rows: List of (file_path, timestamp) tuples.
        tolerance_s: Maximum time difference to consider same group.

    Returns:
        List of file path groups.
    """
    if not rows:
        return []
    
    from datetime import datetime
    
    groups = []
    current_group = []
    current_time = None
    
    for file_path, timestamp in rows:
        try:
            file_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(
                f"Invalid timestamp format: {timestamp}",
                extra={"file_path": file_path, "timestamp": timestamp}
            )
            continue
        
        if current_time is None:
            current_time = file_time
            current_group = [file_path]
        elif abs((file_time - current_time).total_seconds()) <= tolerance_s:
            current_group.append(file_path)
        else:
            if current_group:
                groups.append(current_group)
            current_group = [file_path]
            current_time = file_time
    
    if current_group:
        groups.append(current_group)
    
    return groups