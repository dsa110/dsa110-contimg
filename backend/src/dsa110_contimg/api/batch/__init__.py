"""
Batch job processing package for DSA-110 Continuum Imaging Pipeline.

This package provides utilities for:
- Creating and managing batch jobs
- Tracking batch job items and progress
- Quality assessment extraction
- Thumbnail generation

The package is organized into focused modules:
- jobs: Batch job creation and status management
- qa: Quality assessment extraction utilities
- thumbnails: Image thumbnail generation
"""

from .jobs import (
    create_batch_conversion_job,
    create_batch_ese_detect_job,
    create_batch_job,
    create_batch_photometry_job,
    create_batch_publish_job,
    update_batch_conversion_item,
    update_batch_item,
)
from .qa import (
    extract_calibration_qa,
    extract_image_qa,
)
from .thumbnails import (
    generate_image_thumbnail,
)

__all__ = [
    # Job creation and management
    "create_batch_job",
    "create_batch_conversion_job",
    "create_batch_publish_job",
    "create_batch_photometry_job",
    "create_batch_ese_detect_job",
    "update_batch_item",
    "update_batch_conversion_item",
    # QA extraction
    "extract_calibration_qa",
    "extract_image_qa",
    # Thumbnails
    "generate_image_thumbnail",
]
