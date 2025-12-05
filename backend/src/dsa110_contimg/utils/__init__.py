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
# Import constants
from dsa110_contimg.utils.constants import (
    DSA110_ALT,
    DSA110_LAT,
    DSA110_LATITUDE,
    DSA110_LOCATION,
    DSA110_LON,
    DSA110_LONGITUDE,
)

# Import timing decorators
from dsa110_contimg.utils.decorators import (
    timed,
    timed_context,
    timed_debug,
    timed_verbose,
)
from dsa110_contimg.utils.exceptions import (
    # Calibration errors
    CalibrationError,
    CalibrationTableNotFoundError,
    CalibratorNotFoundError,
    # Conversion errors
    ConversionError,
    DatabaseConnectionError,
    # Database errors
    DatabaseError,
    DatabaseLockError,
    DatabaseMigrationError,
    ImageNotFoundError,
    # Imaging errors
    ImagingError,
    IncompleteSubbandGroupError,
    InvalidPathError,
    MissingParameterError,
    MSWriteError,
    # Base exception
    PipelineError,
    # Queue errors
    QueueError,
    QueueStateTransitionError,
    # Subband errors
    SubbandGroupingError,
    UVH5ReadError,
    # Validation errors
    ValidationError,
    is_recoverable,
    # Helpers
    wrap_exception,
)

# Import fast metadata utilities
from dsa110_contimg.utils.fast_meta import (
    FastMeta,
    get_uvh5_basic_info,
    get_uvh5_freqs,
    get_uvh5_mid_mjd,
    get_uvh5_times,
    peek_uvh5_phase_and_midtime,
)

# Import logging utilities
from dsa110_contimg.utils.logging_config import (
    get_logger,
    log_context,
    log_exception,
    setup_logging,
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
    # Fast metadata
    "FastMeta",
    "get_uvh5_times",
    "get_uvh5_mid_mjd",
    "get_uvh5_freqs",
    "get_uvh5_basic_info",
    "peek_uvh5_phase_and_midtime",
    # Timing decorators
    "timed",
    "timed_context",
    "timed_debug",
    "timed_verbose",
]
