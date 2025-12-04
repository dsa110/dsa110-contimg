"""
Custom exceptions for the streaming pipeline.

This module defines exception classes for different failure modes in the
streaming data pipeline, enabling precise error handling and retry logic.
"""

from __future__ import annotations

from typing import Optional


class StreamingError(Exception):
    """Base exception for streaming pipeline errors."""

    def __init__(
        self,
        message: str,
        *,
        group_id: Optional[str] = None,
        stage: Optional[str] = None,
        retryable: bool = False,
    ) -> None:
        """Initialize the streaming error.

        Args:
            message: Human-readable error message
            group_id: Optional group identifier where error occurred
            stage: Optional pipeline stage where error occurred
            retryable: Whether this error is transient and retryable
        """
        super().__init__(message)
        self.message = message
        self.group_id = group_id
        self.stage = stage
        self.retryable = retryable


class ConversionError(StreamingError):
    """Error during HDF5 to MS conversion."""

    def __init__(
        self,
        message: str,
        *,
        group_id: Optional[str] = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(
            message,
            group_id=group_id,
            stage="conversion",
            retryable=retryable,
        )


class CalibrationError(StreamingError):
    """Error during calibration solving or application."""

    def __init__(
        self,
        message: str,
        *,
        group_id: Optional[str] = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(
            message,
            group_id=group_id,
            stage="calibration",
            retryable=retryable,
        )


class ImagingError(StreamingError):
    """Error during image generation."""

    def __init__(
        self,
        message: str,
        *,
        group_id: Optional[str] = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(
            message,
            group_id=group_id,
            stage="imaging",
            retryable=retryable,
        )


class QueueError(StreamingError):
    """Error in the subband queue operations."""

    def __init__(
        self,
        message: str,
        *,
        group_id: Optional[str] = None,
        retryable: bool = True,  # Queue errors are usually transient
    ) -> None:
        super().__init__(
            message,
            group_id=group_id,
            stage="queue",
            retryable=retryable,
        )


class DiskSpaceError(StreamingError):
    """Error due to insufficient disk space."""

    def __init__(
        self,
        message: str,
        *,
        path: Optional[str] = None,
        available_gb: Optional[float] = None,
        required_gb: Optional[float] = None,
    ) -> None:
        super().__init__(
            message,
            stage="disk",
            retryable=True,  # May recover after cleanup
        )
        self.path = path
        self.available_gb = available_gb
        self.required_gb = required_gb


class ValidationError(StreamingError):
    """Error during input validation."""

    def __init__(
        self,
        message: str,
        *,
        group_id: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> None:
        super().__init__(
            message,
            group_id=group_id,
            stage="validation",
            retryable=False,
        )
        self.file_path = file_path


class TimeoutError(StreamingError):  # noqa: A001 - shadowing builtin intentionally
    """Error due to operation timeout."""

    def __init__(
        self,
        message: str,
        *,
        group_id: Optional[str] = None,
        stage: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        super().__init__(
            message,
            group_id=group_id,
            stage=stage,
            retryable=True,
        )
        self.timeout_seconds = timeout_seconds


class ShutdownRequested(StreamingError):
    """Raised when graceful shutdown is requested."""

    def __init__(self, message: str = "Shutdown requested") -> None:
        super().__init__(message, retryable=False)
