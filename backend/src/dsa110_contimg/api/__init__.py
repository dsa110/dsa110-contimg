# backend/src/dsa110_contimg/api/__init__.py
"""
DSA-110 Continuum Imaging Pipeline API.

This package provides the REST API for the pipeline, including:
- Image detail and download endpoints
- Measurement Set metadata endpoints
- Source catalog and lightcurve endpoints
- Job provenance and logging endpoints
- Standardized error handling
"""

from .errors import (
    ErrorCode,
    ErrorEnvelope,
    make_error,
    cal_table_missing,
    cal_apply_failed,
    image_not_found,
    ms_not_found,
    source_not_found,
    validation_failed,
    db_unavailable,
    internal_error,
)
from .app import app, create_app

__all__ = [
    # App
    "app",
    "create_app",
    # Error utilities
    "ErrorCode",
    "ErrorEnvelope",
    "make_error",
    "cal_table_missing",
    "cal_apply_failed",
    "image_not_found",
    "ms_not_found",
    "source_not_found",
    "validation_failed",
    "db_unavailable",
    "internal_error",
]

# This file initializes the API module.