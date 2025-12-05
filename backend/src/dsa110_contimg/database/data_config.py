"""Configuration for data registry paths and auto-publish settings.

This module implements the redesigned directory structure that aligns with
the scientific workflow. The new structure provides:
- Clear data provenance (raw → calibrated → images → mosaics)
- Better organization by processing stage
- Separation of active processing from final products
- Support for backward compatibility during migration
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

# Base paths - can be overridden by environment variables
# SSD - fast access for active work
STAGE_BASE = Path(os.getenv("CONTIMG_STAGE_BASE", "/stage/dsa110-contimg"))
# HDD - long-term storage
DATA_BASE = Path(os.getenv("CONTIMG_DATA_BASE", "/data/dsa110-contimg"))
PRODUCTS_BASE = DATA_BASE / "products"  # Published products
STATE_BASE = DATA_BASE / "state"  # Pipeline state (databases)

# Auto-publish configuration
AUTO_PUBLISH_ENABLED_BY_DEFAULT = True
AUTO_PUBLISH_DELAY_SECONDS = 0  # Delay before auto-publish (0 = immediate)

# Stage-based organization (new structure – now default)
DATA_TYPES: Dict[str, Dict[str, Any]] = {
    "raw_ms": {
        "staging_dir": STAGE_BASE / "raw" / "ms",
        "published_dir": None,  # Raw MS not published
        "auto_publish_criteria": {
            "qa_required": False,
            "validation_required": False,
        },
    },
    "calibrated_ms": {
        "staging_dir": STAGE_BASE / "calibrated" / "ms",
        "published_dir": PRODUCTS_BASE / "ms",  # Optional: publish calibrated MS
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "calibration_table": {
        "staging_dir": STAGE_BASE / "calibrated" / "tables",
        "published_dir": PRODUCTS_BASE / "caltables",
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "image": {
        "staging_dir": STAGE_BASE / "images",
        "published_dir": PRODUCTS_BASE / "images",  # Optional
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "mosaic": {
        "staging_dir": STAGE_BASE / "mosaics",
        "published_dir": PRODUCTS_BASE / "mosaics",
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "catalog": {
        "staging_dir": STAGE_BASE / "products" / "catalogs",
        "published_dir": PRODUCTS_BASE / "catalogs",
        "auto_publish_criteria": {
            "qa_required": False,
            "validation_required": True,
        },
    },
    "qa": {
        "staging_dir": STAGE_BASE / "products" / "qa",
        "published_dir": PRODUCTS_BASE / "qa",
        "subdirs": ["cal_qa", "ms_qa", "image_qa"],
        "auto_publish_criteria": {
            "qa_required": False,
            "validation_required": False,
        },
    },
    "metadata": {
        "staging_dir": STAGE_BASE / "products" / "metadata",
        "published_dir": PRODUCTS_BASE / "metadata",
        "subdirs": [
            "pipe_meta",
            "cal_meta",
            "ms_meta",
            "catalog_meta",
            "image_meta",
            "mosaic_meta",
        ],
        "auto_publish_criteria": {
            "qa_required": False,
            "validation_required": False,
        },
    },
    # Legacy types for backward compatibility
    "ms": {
        "staging_dir": STAGE_BASE / "raw" / "ms",
        "published_dir": PRODUCTS_BASE / "ms",
        "auto_publish_criteria": {
            "qa_required": False,
            "validation_required": True,
        },
    },
    "calib_ms": {
        "staging_dir": STAGE_BASE / "calibrated" / "ms",
        "published_dir": PRODUCTS_BASE / "ms",
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "caltable": {
        "staging_dir": STAGE_BASE / "calibrated" / "tables",
        "published_dir": PRODUCTS_BASE / "caltables",
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
}


def get_staging_dir(data_type: str) -> Path:
    """Get staging directory for a data type."""
    if data_type not in DATA_TYPES:
        raise ValueError(f"Unknown data type: {data_type}")
    return DATA_TYPES[data_type]["staging_dir"]


def get_published_dir(data_type: str) -> Optional[Path]:
    """Get published directory for a data type."""
    if data_type not in DATA_TYPES:
        raise ValueError(f"Unknown data type: {data_type}")
    published_dir = DATA_TYPES[data_type].get("published_dir")
    return Path(published_dir) if published_dir else None


def get_auto_publish_criteria(data_type: str) -> Dict[str, Any]:
    """Get auto-publish criteria for a data type."""
    if data_type not in DATA_TYPES:
        raise ValueError(f"Unknown data type: {data_type}")
    return DATA_TYPES[data_type].get("auto_publish_criteria", {})


# New structure helper functions
def get_raw_ms_dir() -> Path:
    """Get directory for raw (uncalibrated) MS files."""
    return STAGE_BASE / "raw" / "ms"


def get_calibrated_ms_dir() -> Path:
    """Get directory for calibrated MS files."""
    return STAGE_BASE / "calibrated" / "ms"


def get_calibration_tables_dir() -> Path:
    """Get directory for calibration tables."""
    return STAGE_BASE / "calibrated" / "tables"


def get_groups_dir() -> Path:
    """Get directory for group definitions."""
    return STAGE_BASE / "raw" / "groups"


def get_workspace_dir() -> Path:
    """Get workspace directory for active processing."""
    return STAGE_BASE / "workspace"


def get_workspace_active_dir(stage: Optional[str] = None) -> Path:
    """Get directory for active processing workspace.

    Args:
        stage: Optional stage name (e.g., 'conversion', 'calibration', 'imaging', 'mosaicking')

    Returns:
        Path to active workspace directory (or stage-specific subdirectory)
    """
    base = STAGE_BASE / "workspace" / "active"
    if stage:
        return base / stage
    return base


def get_workspace_failed_dir() -> Path:
    """Get directory for failed processing attempts."""
    return STAGE_BASE / "workspace" / "failed"


def get_products_dir() -> Path:
    """Get directory for validated products ready to publish."""
    return STAGE_BASE / "products"


def ensure_staging_directories() -> None:
    """Ensure all staging directories exist."""
    directories = [
        get_raw_ms_dir(),
        get_calibrated_ms_dir(),
        get_calibration_tables_dir(),
        get_groups_dir(),
        get_workspace_dir(),
        get_workspace_active_dir(),
        get_workspace_failed_dir(),
        get_products_dir(),
        STAGE_BASE / "images",
        STAGE_BASE / "mosaics",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    # Create subdirectories for raw MS
    (get_raw_ms_dir() / "science").mkdir(parents=True, exist_ok=True)
    (get_raw_ms_dir() / "calibrators").mkdir(parents=True, exist_ok=True)

    # Create subdirectories for calibrated MS
    (get_calibrated_ms_dir() / "science").mkdir(parents=True, exist_ok=True)
    (get_calibrated_ms_dir() / "calibrators").mkdir(parents=True, exist_ok=True)

    # Create workspace subdirectories
    for stage in ["conversion", "calibration", "imaging", "mosaicking"]:
        get_workspace_active_dir(stage).mkdir(parents=True, exist_ok=True)
