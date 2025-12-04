"""
Canonical error codes for execution results.

This module provides standardized error codes and exception mapping
to ensure consistent error handling between in-process and subprocess
execution modes.

Part of Issue #11: Subprocess vs In-Process Execution Consistency.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ErrorCode(IntEnum):
    """Canonical error codes for execution results.

    These codes are used consistently across both in-process and
    subprocess execution modes to ensure identical error semantics.

    The integer values are used as subprocess return codes.
    """

    SUCCESS = 0
    GENERAL_ERROR = 1
    IO_ERROR = 2
    OOM_ERROR = 3
    TIMEOUT_ERROR = 4
    VALIDATION_ERROR = 5
    RESOURCE_LIMIT_ERROR = 6
    CALIBRATION_ERROR = 7
    CONVERSION_ERROR = 8
    DATABASE_ERROR = 9
    SUBPROCESS_ERROR = 10

    @property
    def description(self) -> str:
        """Human-readable description of the error code."""
        descriptions = {
            ErrorCode.SUCCESS: "Completed successfully",
            ErrorCode.GENERAL_ERROR: "Unspecified error",
            ErrorCode.IO_ERROR: "File I/O failure",
            ErrorCode.OOM_ERROR: "Out of memory",
            ErrorCode.TIMEOUT_ERROR: "Execution timeout exceeded",
            ErrorCode.VALIDATION_ERROR: "Input validation failed",
            ErrorCode.RESOURCE_LIMIT_ERROR: "Resource limit exceeded",
            ErrorCode.CALIBRATION_ERROR: "Calibration data missing or invalid",
            ErrorCode.CONVERSION_ERROR: "UVH5 to MS conversion failed",
            ErrorCode.DATABASE_ERROR: "Database operation failed",
            ErrorCode.SUBPROCESS_ERROR: "Subprocess execution failed",
        }
        return descriptions.get(self, "Unknown error")


class ExecutionError(Exception):
    """Base exception for execution errors.

    All execution-related exceptions should inherit from this class
    to enable consistent error handling and code mapping.

    Attributes:
        code: Canonical error code
        message: Human-readable error message
        cause: Original exception that caused this error
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        base = f"[{self.code.name}] {self.message}"
        if self.cause:
            base += f" (caused by: {self.cause})"
        return base


class ValidationError(ExecutionError):
    """Raised when task validation fails."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(ErrorCode.VALIDATION_ERROR, message, cause)


class IOError(ExecutionError):
    """Raised when file I/O fails."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(ErrorCode.IO_ERROR, message, cause)


class TimeoutError(ExecutionError):
    """Raised when execution times out."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(ErrorCode.TIMEOUT_ERROR, message, cause)


class ResourceLimitError(ExecutionError):
    """Raised when resource limits are exceeded."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(ErrorCode.RESOURCE_LIMIT_ERROR, message, cause)


class ConversionError(ExecutionError):
    """Raised when conversion fails."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(ErrorCode.CONVERSION_ERROR, message, cause)


class CalibrationError(ExecutionError):
    """Raised when calibration fails."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(ErrorCode.CALIBRATION_ERROR, message, cause)


def map_exception_to_error_code(exc: Exception) -> Tuple[ErrorCode, str]:
    """Map an exception to a canonical error code.

    This function provides consistent error code mapping regardless
    of whether the exception came from in-process or subprocess execution.

    Args:
        exc: The exception to map

    Returns:
        Tuple of (ErrorCode, error_message)
    """
    # Handle our own exceptions first
    if isinstance(exc, ExecutionError):
        return exc.code, exc.message

    # Map standard Python exceptions
    exc_type = type(exc).__name__
    exc_msg = str(exc)

    # Memory errors
    if isinstance(exc, MemoryError):
        return ErrorCode.OOM_ERROR, f"Out of memory: {exc_msg}"

    # Timeout (from concurrent.futures or signal)
    if "timeout" in exc_type.lower() or "timeout" in exc_msg.lower():
        return ErrorCode.TIMEOUT_ERROR, f"Timeout: {exc_msg}"

    # File/IO errors
    if isinstance(exc, (FileNotFoundError, PermissionError, IsADirectoryError)):
        return ErrorCode.IO_ERROR, f"I/O error: {exc_msg}"
    if isinstance(exc, OSError) and exc.errno in (28, 122):  # ENOSPC, EDQUOT
        return ErrorCode.IO_ERROR, f"Disk space error: {exc_msg}"

    # Value/Type errors often indicate validation issues
    if isinstance(exc, (ValueError, TypeError)):
        return ErrorCode.VALIDATION_ERROR, f"Validation error: {exc_msg}"

    # Check for known error patterns in message
    msg_lower = exc_msg.lower()
    if "calibration" in msg_lower or "caltable" in msg_lower:
        return ErrorCode.CALIBRATION_ERROR, f"Calibration error: {exc_msg}"
    if "conversion" in msg_lower or "uvh5" in msg_lower or "measurement set" in msg_lower:
        return ErrorCode.CONVERSION_ERROR, f"Conversion error: {exc_msg}"
    if "database" in msg_lower or "sqlite" in msg_lower:
        return ErrorCode.DATABASE_ERROR, f"Database error: {exc_msg}"
    if "resource" in msg_lower or "limit" in msg_lower or "rlimit" in msg_lower:
        return ErrorCode.RESOURCE_LIMIT_ERROR, f"Resource limit error: {exc_msg}"

    # Default to general error
    return ErrorCode.GENERAL_ERROR, f"Unexpected error ({exc_type}): {exc_msg}"


def map_return_code_to_error_code(return_code: int) -> ErrorCode:
    """Map a subprocess return code to ErrorCode.

    Args:
        return_code: Process exit code

    Returns:
        Corresponding ErrorCode
    """
    try:
        return ErrorCode(return_code)
    except ValueError:
        # Unknown return code
        if return_code < 0:
            # Negative codes indicate signal termination
            # -9 = SIGKILL (often OOM killer), -15 = SIGTERM
            if return_code == -9:
                return ErrorCode.OOM_ERROR
            return ErrorCode.SUBPROCESS_ERROR
        return ErrorCode.GENERAL_ERROR
