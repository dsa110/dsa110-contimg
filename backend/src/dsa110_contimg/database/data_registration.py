"""Data registration utilities for the pipeline.

Provides a simplified interface for registering pipeline data products
(MS files, images, calibration tables) in the data registry.

This module wraps the lower-level data_registry functions to provide
a convenient API for pipeline stages.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def register_pipeline_data(
    data_type: str,
    data_id: str,
    file_path: Path,
    metadata: Optional[Dict[str, Any]] = None,
    auto_publish: bool = True,
) -> str:
    """Register a pipeline data product in the data registry.

    This is a convenience wrapper for pipeline stages that creates the
    necessary database connections and handles common data types.

    Args:
        data_type: Type of data product. Common types:
            - 'ms': Measurement Set file
            - 'calib_ms': Calibrated Measurement Set
            - 'image': FITS or CASA image
            - 'mosaic': Mosaic image
            - 'caltable': Calibration table
        data_id: Unique identifier for this data instance.
            Typically the file path or a derived unique name.
        file_path: Path to the data file/directory.
        metadata: Optional metadata dictionary. Will be JSON-encoded.
            Common keys: ms_path, imagename, shape, has_data, etc.
        auto_publish: Whether auto-publish is enabled (default True).

    Returns:
        The data_id (same as input).

    Example:
        >>> from pathlib import Path
        >>> register_pipeline_data(
        ...     data_type='image',
        ...     data_id='/stage/dsa110-contimg/images/2025-01-01T12:00:00.img.image',
        ...     file_path=Path('/stage/dsa110-contimg/images/2025-01-01T12:00:00.img.image'),
        ...     metadata={'ms_path': '/stage/dsa110-contimg/ms/2025-01-01T12:00:00.ms'},
        ... )
        '/stage/dsa110-contimg/images/2025-01-01T12:00:00.img.image'
    """
    from dsa110_contimg.database.data_registry import (
        get_data_registry_connection,
        register_data,
    )

    try:
        conn = get_data_registry_connection()
        result = register_data(
            conn=conn,
            data_type=data_type,
            data_id=data_id,
            stage_path=str(file_path),
            metadata=metadata,
            auto_publish=auto_publish,
        )
        conn.close()
        logger.debug(f"Registered {data_type} data: {data_id}")
        return result

    except Exception as e:
        logger.warning(f"Failed to register data {data_id}: {e}")
        # Registration failures are non-fatal - return the data_id anyway
        return data_id


def register_ms(
    ms_path: Path,
    metadata: Optional[Dict[str, Any]] = None,
    is_calibrated: bool = False,
    auto_publish: bool = True,
) -> str:
    """Register a Measurement Set in the data registry.

    Args:
        ms_path: Path to the MS directory.
        metadata: Optional metadata dictionary.
        is_calibrated: If True, registers as 'calib_ms', else 'ms'.
        auto_publish: Whether auto-publish is enabled.

    Returns:
        The data_id (MS path as string).
    """
    data_type = "calib_ms" if is_calibrated else "ms"
    data_id = str(ms_path)

    if metadata is None:
        metadata = {}

    # Add standard MS metadata
    metadata.setdefault("ms_name", ms_path.stem)
    metadata.setdefault("is_calibrated", is_calibrated)

    return register_pipeline_data(
        data_type=data_type,
        data_id=data_id,
        file_path=ms_path,
        metadata=metadata,
        auto_publish=auto_publish,
    )


def register_image(
    image_path: Path,
    ms_path: Optional[Path] = None,
    metadata: Optional[Dict[str, Any]] = None,
    auto_publish: bool = True,
) -> str:
    """Register an image in the data registry.

    Args:
        image_path: Path to the image file.
        ms_path: Optional source MS path (for provenance).
        metadata: Optional metadata dictionary.
        auto_publish: Whether auto-publish is enabled.

    Returns:
        The data_id (image path as string).
    """
    data_id = str(image_path)

    if metadata is None:
        metadata = {}

    # Add standard image metadata
    metadata.setdefault("image_name", image_path.stem)
    if ms_path:
        metadata.setdefault("ms_path", str(ms_path))

    return register_pipeline_data(
        data_type="image",
        data_id=data_id,
        file_path=image_path,
        metadata=metadata,
        auto_publish=auto_publish,
    )


def register_caltable(
    table_path: Path,
    table_type: str,
    ms_path: Optional[Path] = None,
    metadata: Optional[Dict[str, Any]] = None,
    auto_publish: bool = False,
) -> str:
    """Register a calibration table in the data registry.

    Args:
        table_path: Path to the calibration table directory.
        table_type: Type of calibration table ('K', 'BP', 'G', etc.).
        ms_path: Optional source MS path (for provenance).
        metadata: Optional metadata dictionary.
        auto_publish: Whether auto-publish is enabled (default False for caltables).

    Returns:
        The data_id (table path as string).
    """
    data_id = str(table_path)

    if metadata is None:
        metadata = {}

    # Add standard caltable metadata
    metadata.setdefault("table_type", table_type)
    metadata.setdefault("table_name", table_path.stem)
    if ms_path:
        metadata.setdefault("ms_path", str(ms_path))

    return register_pipeline_data(
        data_type="caltable",
        data_id=data_id,
        file_path=table_path,
        metadata=metadata,
        auto_publish=auto_publish,
    )
