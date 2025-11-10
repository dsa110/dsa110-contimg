"""
Unified exception hierarchy for dsa110_contimg.

This module provides a consistent exception structure across the codebase,
ensuring all errors include context and actionable suggestions.
"""

from typing import Optional, Dict, Any, List


class DSA110Error(Exception):
    """
    Base exception for all dsa110_contimg errors.

    All exceptions in the codebase should inherit from this class to ensure
    consistent error handling, context, and suggestions.

    Attributes:
        message: Primary error message
        context: Dictionary with additional context
            (e.g., {'path': str, 'operation': str})
        suggestion: Optional suggestion for how to fix the issue
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ):
        """
        Initialize DSA110 error.

        Args:
            message: Primary error message describing what went wrong
            context: Optional dictionary with additional context
            suggestion: Optional suggestion for how to fix the issue
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.suggestion = suggestion

    def __str__(self) -> str:
        """Format error message with context and suggestion."""
        msg = self.message

        # Add context if available
        if self.context:
            ctx_parts = []
            for key, value in sorted(self.context.items()):
                if value is not None:
                    ctx_parts.append(f"{key}={value}")
            if ctx_parts:
                msg = f"{msg}\nContext: {', '.join(ctx_parts)}"

        # Add suggestion if available
        if self.suggestion:
            msg = f"{msg}\n\nSuggestion: {self.suggestion}"

        return msg


class ValidationError(DSA110Error):
    """
    Raised when validation fails.

    This exception can include both errors (which prevent operation) and
    warnings (which are informational but don't block execution).

    Attributes:
        errors: List of error messages (operations should fail)
        warnings: List of warning messages (informational)
        error_types: Optional list of error types for suggestion lookup
        error_details: Optional list of dicts with error details for suggestions
    """

    def __init__(
        self,
        errors: List[str],
        warnings: Optional[List[str]] = None,
        error_types: Optional[List[str]] = None,
        error_details: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
    ):
        """
        Initialize validation error.

        Args:
            errors: List of error messages (required)
            warnings: Optional list of warning messages
            error_types: Optional list of error type strings for
                suggestion lookup
            error_details: Optional list of dicts with error details
                for suggestions
            context: Optional dictionary with additional context
            suggestion: Optional suggestion for how to fix the issue
        """
        error_msg = ", ".join(errors) if errors else "Unknown validation error"
        super().__init__(error_msg, context=context, suggestion=suggestion)
        self.errors = errors
        self.warnings = warnings or []
        self.error_types = error_types or []
        self.error_details = error_details or []

    def format_with_suggestions(self) -> str:
        """
        Format error message with suggestions from error_messages module.

        Returns:
            Formatted error message with suggestions
        """
        from dsa110_contimg.utils.error_messages import (
            format_validation_error,
            suggest_fix,
        )

        msg = format_validation_error(self.errors, self.warnings)

        # Add suggestions if available
        if self.error_types and self.error_details:
            msg += "\n\nSuggestions:\n"
            for error_type, details in zip(self.error_types, self.error_details):
                suggestion = suggest_fix(error_type, details)
                if suggestion:
                    # First line only
                    msg += f"  - {suggestion.split(chr(10))[0]}\n"

        return msg


class ConversionError(DSA110Error):
    """Raised when conversion operations fail."""

    pass


class CalibrationError(DSA110Error):
    """Raised when calibration operations fail."""

    pass


class ImagingError(DSA110Error):
    """Raised when imaging operations fail."""

    pass


class MosaicError(DSA110Error):
    """
    Base exception for mosaic building operations.

    Maintains backward compatibility with existing MosaicError interface.
    """

    def __init__(
        self,
        message: str,
        recovery_hint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize mosaic error.

        Args:
            message: Error message describing what went wrong
            recovery_hint: Optional suggestion for how to recover
                (alias for suggestion)
            context: Optional dictionary with additional context
        """
        # Map recovery_hint to suggestion for consistency
        super().__init__(message, context=context, suggestion=recovery_hint)
        # Keep recovery_hint for backward compatibility
        self.recovery_hint = recovery_hint


__all__ = [
    "DSA110Error",
    "ValidationError",
    "ConversionError",
    "CalibrationError",
    "ImagingError",
    "MosaicError",
]
