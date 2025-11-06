"""
Custom exceptions for mosaic building operations.

Provides specific exception types for different failure modes with
actionable error messages and recovery suggestions.

All exceptions inherit from the unified DSA110Error hierarchy.
"""

from typing import Optional, Dict, Any
from dsa110_contimg.utils.exceptions import DSA110Error


class MosaicError(DSA110Error):
    """
    Base exception for mosaic building operations.
    
    Maintains backward compatibility with existing MosaicError interface.
    """
    
    def __init__(
        self,
        message: str,
        recovery_hint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Args:
            message: Error message describing what went wrong
            recovery_hint: Optional suggestion for how to recover (alias for suggestion)
            context: Optional dictionary with additional context (e.g., {'tile': path, 'operation': 'read'})
        """
        # Map recovery_hint to suggestion for consistency with DSA110Error
        super().__init__(message, context=context, suggestion=recovery_hint)
        # Keep recovery_hint for backward compatibility
        self.recovery_hint = recovery_hint


class ImageReadError(MosaicError):
    """Raised when an image cannot be read (corruption, missing, permission issues)."""
    pass


class ImageCorruptionError(MosaicError):
    """Raised when an image is corrupted or has invalid structure."""
    pass


class MissingPrimaryBeamError(MosaicError):
    """Raised when a primary beam image is missing or cannot be found."""
    pass


class IncompatibleImageFormatError(MosaicError):
    """Raised when images have incompatible formats or coordinate systems."""
    pass


class CASAToolError(MosaicError):
    """Raised when a CASA tool fails (imhead, imregrid, immath, etc.)."""
    pass


class GridMismatchError(MosaicError):
    """Raised when image grids are incompatible (different shapes, cell sizes)."""
    pass


class ValidationError(MosaicError):
    """Raised when pre-mosaicking validation fails."""
    pass


class MetricsGenerationError(MosaicError):
    """Raised when mosaic quality metrics generation fails."""
    pass

