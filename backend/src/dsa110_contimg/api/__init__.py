# backend/src/dsa110_contimg/api/__init__.py
"""
DSA-110 Continuum Imaging Pipeline API.

This package provides the REST API for the pipeline, including:
- Image detail and download endpoints
- Measurement Set metadata endpoints
- Source catalog and lightcurve endpoints
- Job provenance and logging endpoints
- Standardized error handling via exceptions module
"""

from .app import app, create_app
from .exceptions import (
    DSA110APIError,
    RecordNotFoundError,
    ValidationError,
    DatabaseConnectionError,
    FileNotAccessibleError,
    ProcessingError,
)

__all__ = [
    # App
    "app",
    "create_app",
    # Exception classes
    "DSA110APIError",
    "RecordNotFoundError",
    "ValidationError",
    "DatabaseConnectionError",
    "FileNotAccessibleError",
    "ProcessingError",
]