"""
Custom exceptions for mosaic building operations.

Provides specific exception types for different failure modes with
actionable error messages and recovery suggestions.
"""

from typing import Optional


class MosaicError(Exception):
    """Base exception for mosaic building operations."""
    
    def __init__(self, message: str, recovery_hint: str = None, context: Optional[dict] = None):
        """
        Args:
            message: Error message describing what went wrong
            recovery_hint: Optional suggestion for how to recover
            context: Optional dictionary with additional context (e.g., {'tile': path, 'operation': 'read'})
        """
        super().__init__(message)
        self.message = message
        self.recovery_hint = recovery_hint
        self.context = context or {}
    
    def __str__(self) -> str:
        msg = self.message
        if self.context:
            ctx_parts = []
            if 'tile' in self.context:
                ctx_parts.append(f"Tile: {self.context['tile']}")
            if 'operation' in self.context:
                ctx_parts.append(f"Operation: {self.context['operation']}")
            if 'tool' in self.context:
                ctx_parts.append(f"Tool: {self.context['tool']}")
            if ctx_parts:
                msg = f"{msg}\nContext: {', '.join(ctx_parts)}"
        if self.recovery_hint:
            msg = f"{msg}\n\nRecovery suggestion: {self.recovery_hint}"
        return msg


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

