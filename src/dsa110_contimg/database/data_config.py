"""Configuration for data registry paths and auto-publish settings."""

from pathlib import Path
from typing import Any, Dict

# Base paths
STAGE_BASE = Path("/stage/dsa110-contimg")  # SSD - fast access for active work
PRODUCTS_BASE = Path("/data/dsa110-contimg/products")  # HDD - long-term storage

# Auto-publish configuration
AUTO_PUBLISH_ENABLED_BY_DEFAULT = True
AUTO_PUBLISH_DELAY_SECONDS = 0  # Delay before auto-publish (0 = immediate)

# Data type configurations
DATA_TYPES: Dict[str, Dict[str, Any]] = {
    "ms": {
        "staging_dir": STAGE_BASE / "ms",
        "published_dir": PRODUCTS_BASE / "ms",
        "auto_publish_criteria": {
            "qa_required": False,  # MS files don't need QA
            "validation_required": True,
        },
    },
    "calib_ms": {
        "staging_dir": STAGE_BASE / "calib_ms",
        "published_dir": PRODUCTS_BASE / "calib_ms",
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "caltable": {
        "staging_dir": STAGE_BASE / "caltables",
        "published_dir": PRODUCTS_BASE / "caltables",
        "auto_publish_criteria": {
            "qa_required": True,
            "qa_status": "passed",
            "validation_required": True,
        },
    },
    "image": {
        "staging_dir": STAGE_BASE / "images",
        "published_dir": PRODUCTS_BASE / "images",
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
        "staging_dir": STAGE_BASE / "catalogs",
        "published_dir": PRODUCTS_BASE / "catalogs",
        "auto_publish_criteria": {
            "qa_required": False,
            "validation_required": True,
        },
    },
    "qa": {
        "staging_dir": STAGE_BASE / "qa",
        "published_dir": PRODUCTS_BASE / "qa",
        "subdirs": ["cal_qa", "ms_qa", "image_qa"],
        "auto_publish_criteria": {
            "qa_required": False,
            "validation_required": False,  # QA reports auto-publish with their data
        },
    },
    "metadata": {
        "staging_dir": STAGE_BASE / "metadata",
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
            "validation_required": False,  # Metadata auto-publishes with its data
        },
    },
}


def get_staging_dir(data_type: str) -> Path:
    """Get staging directory for a data type."""
    return DATA_TYPES[data_type]["staging_dir"]


def get_published_dir(data_type: str) -> Path:
    """Get published directory for a data type."""
    return DATA_TYPES[data_type]["published_dir"]


def get_auto_publish_criteria(data_type: str) -> Dict[str, Any]:
    """Get auto-publish criteria for a data type."""
    return DATA_TYPES[data_type].get("auto_publish_criteria", {})
