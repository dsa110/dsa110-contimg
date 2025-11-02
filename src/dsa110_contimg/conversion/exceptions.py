"""
Custom exceptions for calibrator MS generation.
"""


class CalibratorMSError(Exception):
    """Base exception for calibrator MS generation."""
    pass


class TransitNotFoundError(CalibratorMSError):
    """Raised when no transit is found for the calibrator."""
    pass


class GroupNotFoundError(CalibratorMSError):
    """Raised when no subband group is found for the transit."""
    pass


class ConversionError(CalibratorMSError):
    """Raised when MS conversion fails."""
    pass


class CalibratorNotFoundError(CalibratorMSError):
    """Raised when calibrator is not found in catalogs."""
    pass


class ValidationError(CalibratorMSError):
    """Raised when input validation fails."""
    pass

