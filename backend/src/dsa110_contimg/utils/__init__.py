# This file initializes the utils module.

"""
Utilities for the DSA-110 Continuum Imaging Pipeline.

This module provides shared utilities used across pipeline stages:
- Custom exception classes for structured error handling
- Centralized logging configuration
- Constants for DSA-110 telescope parameters
- Fast UVH5 metadata reading utilities
- Antenna position utilities
"""

# Import exceptions for convenient access
from dsa110_contimg.utils.exceptions import (
    # Base exception
    PipelineError,
    # Subband errors
    SubbandGroupingError,
    IncompleteSubbandGroupError,
    # Conversion errors
    ConversionError,
    UVH5ReadError,
    MSWriteError,
    # Database errors
    DatabaseError,
    DatabaseMigrationError,
    DatabaseConnectionError,
    DatabaseLockError,
    # Queue errors
    QueueError,
    QueueStateTransitionError,
    # Calibration errors
    CalibrationError,
    CalibrationTableNotFoundError,
    CalibratorNotFoundError,
    # Imaging errors
    ImagingError,
    ImageNotFoundError,
    # Validation errors
    ValidationError,
    MissingParameterError,
    InvalidPathError,
    # Helpers
    wrap_exception,
    is_recoverable,
)

# Import logging utilities
from dsa110_contimg.utils.logging_config import (
    setup_logging,
    log_context,
    get_logger,
    log_exception,
)

# Import constants
from dsa110_contimg.utils.constants import (
    DSA110_LOCATION,
    DSA110_LATITUDE,
    DSA110_LONGITUDE,
    DSA110_LAT,
    DSA110_LON,
    DSA110_ALT,
    OVRO_LOCATION,  # Legacy, use DSA110_LOCATION
)

# Import fast metadata utilities
from dsa110_contimg.utils.fast_meta import (
    FastMeta,
    get_uvh5_times,
    get_uvh5_mid_mjd,
    get_uvh5_freqs,
    get_uvh5_basic_info,
)

__all__ = [
    # Exceptions
    "PipelineError",
    "SubbandGroupingError",
    "IncompleteSubbandGroupError",
    "ConversionError",
    "UVH5ReadError",
    "MSWriteError",
    "DatabaseError",
    "DatabaseMigrationError",
    "DatabaseConnectionError",
    "DatabaseLockError",
    "QueueError",
    "QueueStateTransitionError",
    "CalibrationError",
    "CalibrationTableNotFoundError",
    "CalibratorNotFoundError",
    "ImagingError",
    "ImageNotFoundError",
    "ValidationError",
    "MissingParameterError",
    "InvalidPathError",
    "wrap_exception",
    "is_recoverable",
    # Logging
    "setup_logging",
    "log_context",
    "get_logger",
    "log_exception",
    # Constants
    "DSA110_LOCATION",
    "DSA110_LATITUDE",
    "DSA110_LONGITUDE",
    "DSA110_LAT",
    "DSA110_LON",
    "DSA110_ALT",
    "OVRO_LOCATION",
    # Fast metadata
    "FastMeta",
    "get_uvh5_times",
    "get_uvh5_mid_mjd",
    "get_uvh5_freqs",
    "get_uvh5_basic_info",
]