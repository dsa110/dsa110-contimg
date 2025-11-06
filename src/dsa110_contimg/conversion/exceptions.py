"""
Custom exceptions for calibrator MS generation.

All exceptions inherit from the unified DSA110Error hierarchy.
"""

from dsa110_contimg.utils.exceptions import DSA110Error, ConversionError, ValidationError

# Re-export for backward compatibility
__all__ = [
    'DSA110Error',
    'ConversionError',
    'ValidationError',
    'CalibratorMSError',
    'TransitNotFoundError',
    'GroupNotFoundError',
    'CalibratorConversionError',
    'CalibratorNotFoundError',
    'CalibratorValidationError',
]


class CalibratorMSError(DSA110Error):
    """Base exception for calibrator MS generation."""
    pass


class TransitNotFoundError(CalibratorMSError):
    """Raised when no transit is found for the calibrator."""
    pass


class GroupNotFoundError(CalibratorMSError):
    """Raised when no subband group is found for the transit."""
    pass


class CalibratorConversionError(ConversionError):
    """Raised when MS conversion fails during calibrator processing."""
    pass


class CalibratorNotFoundError(CalibratorMSError):
    """Raised when calibrator is not found in catalogs."""
    pass


# Note: ValidationError is imported from utils.exceptions for consistency
# CalibratorValidationError can be used if calibrator-specific validation is needed
class CalibratorValidationError(ValidationError):
    """Raised when input validation fails during calibrator processing."""
    pass

