"""
Batch job processing and quality assessment utilities.

DEPRECATED: This module is maintained for backwards compatibility.
Import from dsa110_contimg.api.batch instead.

This module has been refactored into focused modules:
- dsa110_contimg.api.batch.jobs: Job creation and management
- dsa110_contimg.api.batch.qa: Quality assessment extraction
- dsa110_contimg.api.batch.thumbnails: Thumbnail generation
"""

from __future__ import annotations

import warnings

# Re-export everything from the new package for backwards compatibility
from .batch import (
    # Job creation and management
    create_batch_job,
    create_batch_conversion_job,
    create_batch_publish_job,
    create_batch_photometry_job,
    create_batch_ese_detect_job,
    update_batch_item,
    update_batch_conversion_item,
    # QA extraction
    extract_calibration_qa,
    extract_image_qa,
    # Thumbnails
    generate_image_thumbnail,
)

__all__ = [
    "create_batch_job",
    "create_batch_conversion_job",
    "create_batch_publish_job",
    "create_batch_photometry_job",
    "create_batch_ese_detect_job",
    "update_batch_item",
    "update_batch_conversion_item",
    "extract_calibration_qa",
    "extract_image_qa",
    "generate_image_thumbnail",
]

# Issue deprecation warning on import
warnings.warn(
    "dsa110_contimg.api.batch_jobs is deprecated. "
    "Import from dsa110_contimg.api.batch instead.",
    DeprecationWarning,
    stacklevel=2
)
