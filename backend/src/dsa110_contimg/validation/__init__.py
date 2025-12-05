"""
Validation utilities for DSA-110 data products.

This module provides validation for:
- Measurement Sets (MS)
- HDF5/UVH5 files
- Calibration tables
- Images

Primary interface:
    from dsa110_contimg.validation import validate_ms, MSValidator

    report = validate_ms("/path/to/file.ms")
    print(report.summary())
"""

from dsa110_contimg.validation.ms_validator import (
    MSValidationReport,
    MSValidator,
    ValidationResult,
    validate_ms,
)

__all__ = [
    "MSValidator",
    "MSValidationReport",
    "ValidationResult",
    "validate_ms",
]
