"""Helper functions for registering data in the pipeline."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from dsa110_contimg.database.data_config import get_staging_dir
from dsa110_contimg.database.data_registry import (
    ensure_data_registry_db,
    link_data,
    register_data,
)
from dsa110_contimg.database.products import ensure_products_db

logger = logging.getLogger(__name__)


def register_pipeline_data(
    data_type: str,
    data_id: str,
    file_path: Path,
    metadata: Optional[Dict[str, Any]] = None,
    auto_publish: bool = True,
    db_path: Optional[Path] = None,
) -> bool:
    """Register a data product created by the pipeline.

    Args:
        data_type: Type of data ('ms', 'calib_ms', 'image', etc.)
        data_id: Unique identifier
        file_path: Path to the data file/directory
        metadata: Optional metadata dictionary
        auto_publish: Whether auto-publish is enabled
        db_path: Path to products database (defaults to standard location)

    Returns:
        True if successful
    """
    if db_path is None:
        db_path = Path("/data/dsa110-contimg/state/products.sqlite3")

    try:
        # Ensure file_path is in staging directory
        file_path = Path(file_path).resolve()
        staging_dir = get_staging_dir(data_type)

        # If file is not in staging, move it or use staging path
        if not str(file_path).startswith(str(staging_dir)):
            # File is elsewhere - we'll register it with its current path
            # but note that it should ideally be in staging
            logger.warning(
                f"Data {data_id} is not in staging directory {staging_dir}. "
                f"Current path: {file_path}"
            )
            stage_path = str(file_path)
        else:
            stage_path = str(file_path)

        # Register in data registry
        conn = ensure_data_registry_db(db_path)
        register_data(
            conn,
            data_type=data_type,
            data_id=data_id,
            stage_path=stage_path,
            metadata=metadata,
            auto_publish=auto_publish,
        )
        conn.close()

        logger.info(f"Registered {data_type} {data_id} at {stage_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to register {data_type} {data_id}: {e}")
        return False


def link_pipeline_data(
    parent_id: str,
    child_id: str,
    relationship_type: str,
    db_path: Optional[Path] = None,
) -> bool:
    """Link two data instances with a relationship.

    Args:
        parent_id: Parent data ID
        child_id: Child data ID
        relationship_type: Type of relationship (e.g., 'derived_from', 'contains')
        db_path: Path to products database

    Returns:
        True if successful
    """
    if db_path is None:
        db_path = Path("/data/dsa110-contimg/state/products.sqlite3")

    try:
        conn = ensure_data_registry_db(db_path)
        link_data(conn, parent_id, child_id, relationship_type)
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to link {parent_id} -> {child_id}: {e}")
        return False
