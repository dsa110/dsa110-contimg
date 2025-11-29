"""
Custom exception classes for the DSA-110 Continuum Imaging Pipeline.

This module provides pipeline-specific exceptions for clearer error semantics,
better logging, and consistent error handling across all pipeline stages.

Exception Hierarchy:
    PipelineError (base)
    ├── SubbandGroupingError - Errors during subband file grouping
    ├── ConversionError - Errors during UVH5:arrow_right:MS conversion
    ├── DatabaseError - Database access and migration errors
    │   └── DatabaseMigrationError - Schema migration failures
    ├── CalibrationError - Calibration pipeline errors
    ├── ImagingError - Imaging pipeline errors
    ├── QueueError - Streaming queue operation errors
    └── ValidationError - Input validation errors

Usage:
    from dsa110_contimg.utils.exceptions import (
        SubbandGroupingError,
        ConversionError,
        DatabaseError,
    )
    
    # Raise with context
    raise SubbandGroupingError(
        "Incomplete subband group",
        group_id="2025-01-15T12:30:00",
        expected_count=16,
        actual_count=14,
        missing_subbands=["sb03", "sb07"],
    )
    
    # Handle with logging
    try:
        convert_data(...)
    except ConversionError as e:
        logger.error(str(e), extra=e.context)
        raise

Logging Integration:
    All pipeline exceptions include a `context` dict with structured data
    suitable for passing to logger.error(..., extra=context).
"""

from __future__ import annotations

import traceback
from typing import Any, Optional
from datetime import datetime


class PipelineError(Exception):
    """
    Base exception for all DSA-110 pipeline errors.
    
    Provides structured context for logging and error tracking.
    
    Attributes:
        message: Human-readable error message
        context: Structured data for logging (file paths, IDs, etc.)
        timestamp: When the error occurred
        pipeline_stage: Which pipeline stage raised the error
        recoverable: Whether the error allows continued processing
        original_exception: The underlying exception, if any
    """
    
    def __init__(
        self,
        message: str,
        pipeline_stage: str = "unknown",
        recoverable: bool = False,
        original_exception: Optional[BaseException] = None,
        **context: Any,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.pipeline_stage = pipeline_stage
        self.recoverable = recoverable
        self.original_exception = original_exception
        self.timestamp = datetime.utcnow().isoformat()
        self._context = context
        
        # Capture traceback if original exception provided
        if original_exception:
            self._traceback = traceback.format_exception(
                type(original_exception),
                original_exception,
                original_exception.__traceback__,
            )
        else:
            self._traceback = None
    
    @property
    def context(self) -> dict[str, Any]:
        """Get structured context for logging."""
        base_context = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "pipeline_stage": self.pipeline_stage,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp,
        }
        
        if self.original_exception:
            base_context["original_error"] = str(self.original_exception)
            base_context["original_type"] = type(self.original_exception).__name__
        
        if self._traceback:
            base_context["traceback"] = "".join(self._traceback)
        
        return {**base_context, **self._context}
    
    def __str__(self) -> str:
        """Format error message with key context."""
        parts = [self.message]
        
        if self.pipeline_stage != "unknown":
            parts.append(f"[stage={self.pipeline_stage}]")
        
        # Include key context items in message
        key_items = ["group_id", "file_path", "ms_path", "db_name"]
        for key in key_items:
            if key in self._context:
                parts.append(f"[{key}={self._context[key]}]")
        
        return " ".join(parts)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r}, context={self._context})"


# =============================================================================
# Subband Grouping Errors
# =============================================================================

class SubbandGroupingError(PipelineError):
    """
    Error during subband file grouping.
    
    Raised when:
    - Expected 16 subbands but found fewer (incomplete group)
    - Duplicate subband indices in a group
    - Time tolerance exceeded for group formation
    - Missing or corrupted subband files
    
    Context keys:
        group_id: Observation group identifier (timestamp)
        expected_count: Expected number of subbands (usually 16)
        actual_count: Actual number found
        missing_subbands: List of missing subband identifiers
        file_list: List of files in the group
    """
    
    def __init__(
        self,
        message: str,
        group_id: str = "",
        expected_count: int = 16,
        actual_count: int = 0,
        missing_subbands: Optional[list[str]] = None,
        file_list: Optional[list[str]] = None,
        recoverable: bool = True,  # Often can skip and continue
        **context: Any,
    ) -> None:
        super().__init__(
            message,
            pipeline_stage="subband_grouping",
            recoverable=recoverable,
            group_id=group_id,
            expected_count=expected_count,
            actual_count=actual_count,
            missing_subbands=missing_subbands or [],
            file_list=file_list or [],
            **context,
        )


class IncompleteSubbandGroupError(SubbandGroupingError):
    """Specific error for groups with missing subbands."""
    
    def __init__(
        self,
        group_id: str,
        expected_count: int,
        actual_count: int,
        missing_subbands: Optional[list[str]] = None,
        **context: Any,
    ) -> None:
        message = (
            f"Incomplete subband group: expected {expected_count} subbands, "
            f"found {actual_count}"
        )
        super().__init__(
            message,
            group_id=group_id,
            expected_count=expected_count,
            actual_count=actual_count,
            missing_subbands=missing_subbands,
            recoverable=True,  # Can skip incomplete groups
            **context,
        )


# =============================================================================
# Conversion Errors
# =============================================================================

class ConversionError(PipelineError):
    """
    Error during UVH5 to Measurement Set conversion.
    
    Raised when:
    - UVH5 file read fails
    - Subband combination fails
    - MS write fails
    - Antenna position update fails
    - Field configuration fails
    
    Context keys:
        input_path: Path to input UVH5 file(s)
        output_path: Path to output MS
        group_id: Observation group identifier
        writer_type: Type of MS writer used
    """
    
    def __init__(
        self,
        message: str,
        input_path: str = "",
        output_path: str = "",
        group_id: str = "",
        writer_type: str = "",
        original_exception: Optional[BaseException] = None,
        recoverable: bool = False,
        **context: Any,
    ) -> None:
        super().__init__(
            message,
            pipeline_stage="conversion",
            recoverable=recoverable,
            original_exception=original_exception,
            input_path=input_path,
            output_path=output_path,
            group_id=group_id,
            writer_type=writer_type,
            **context,
        )


class UVH5ReadError(ConversionError):
    """Error reading UVH5 file."""
    
    def __init__(
        self,
        file_path: str,
        reason: str = "",
        original_exception: Optional[BaseException] = None,
        **context: Any,
    ) -> None:
        message = f"Failed to read UVH5 file: {file_path}"
        if reason:
            message += f" ({reason})"
        super().__init__(
            message,
            input_path=file_path,
            original_exception=original_exception,
            reason=reason,
            **context,
        )


class MSWriteError(ConversionError):
    """Error writing Measurement Set."""
    
    def __init__(
        self,
        output_path: str,
        reason: str = "",
        original_exception: Optional[BaseException] = None,
        **context: Any,
    ) -> None:
        message = f"Failed to write Measurement Set: {output_path}"
        if reason:
            message += f" ({reason})"
        super().__init__(
            message,
            output_path=output_path,
            original_exception=original_exception,
            reason=reason,
            recoverable=False,
            **context,
        )


# =============================================================================
# Database Errors
# =============================================================================

class DatabaseError(PipelineError):
    """
    Error during database operations.
    
    Raised when:
    - Database connection fails
    - Query execution fails
    - Transaction commit/rollback fails
    - Integrity constraints violated
    
    Context keys:
        db_name: Name of the database (products, ingest, etc.)
        db_path: Path to the database file
        operation: What operation was attempted (insert, update, query)
        table_name: Which table was affected
    """
    
    def __init__(
        self,
        message: str,
        db_name: str = "",
        db_path: str = "",
        operation: str = "",
        table_name: str = "",
        original_exception: Optional[BaseException] = None,
        recoverable: bool = False,
        **context: Any,
    ) -> None:
        super().__init__(
            message,
            pipeline_stage="database",
            recoverable=recoverable,
            original_exception=original_exception,
            db_name=db_name,
            db_path=db_path,
            operation=operation,
            table_name=table_name,
            **context,
        )


class DatabaseMigrationError(DatabaseError):
    """Error during database schema migration."""
    
    def __init__(
        self,
        db_name: str,
        migration_version: str = "",
        reason: str = "",
        original_exception: Optional[BaseException] = None,
        **context: Any,
    ) -> None:
        message = f"Database migration failed for {db_name}"
        if migration_version:
            message += f" (version: {migration_version})"
        if reason:
            message += f": {reason}"
        super().__init__(
            message,
            db_name=db_name,
            operation="migration",
            original_exception=original_exception,
            migration_version=migration_version,
            reason=reason,
            recoverable=False,
            **context,
        )


class DatabaseConnectionError(DatabaseError):
    """Error connecting to database."""
    
    def __init__(
        self,
        db_name: str,
        db_path: str = "",
        reason: str = "",
        original_exception: Optional[BaseException] = None,
        **context: Any,
    ) -> None:
        message = f"Failed to connect to database: {db_name}"
        if reason:
            message += f" ({reason})"
        super().__init__(
            message,
            db_name=db_name,
            db_path=db_path,
            operation="connect",
            original_exception=original_exception,
            reason=reason,
            recoverable=False,
            **context,
        )


class DatabaseLockError(DatabaseError):
    """Database lock timeout error."""
    
    def __init__(
        self,
        db_name: str,
        timeout_seconds: float = 30.0,
        original_exception: Optional[BaseException] = None,
        **context: Any,
    ) -> None:
        message = f"Database lock timeout ({timeout_seconds}s) for {db_name}"
        super().__init__(
            message,
            db_name=db_name,
            operation="lock",
            original_exception=original_exception,
            timeout_seconds=timeout_seconds,
            recoverable=True,  # Can retry
            **context,
        )


# =============================================================================
# Queue Errors
# =============================================================================

class QueueError(PipelineError):
    """
    Error during streaming queue operations.
    
    Raised when:
    - Queue state transition fails
    - Queue record insertion fails
    - Invalid queue state encountered
    
    Context keys:
        group_id: Observation group identifier
        current_state: Current queue state
        target_state: Intended state transition
        queue_db: Path to queue database
    """
    
    def __init__(
        self,
        message: str,
        group_id: str = "",
        current_state: str = "",
        target_state: str = "",
        queue_db: str = "",
        original_exception: Optional[BaseException] = None,
        recoverable: bool = True,
        **context: Any,
    ) -> None:
        super().__init__(
            message,
            pipeline_stage="queue",
            recoverable=recoverable,
            original_exception=original_exception,
            group_id=group_id,
            current_state=current_state,
            target_state=target_state,
            queue_db=queue_db,
            **context,
        )


class QueueStateTransitionError(QueueError):
    """Invalid queue state transition."""
    
    def __init__(
        self,
        group_id: str,
        current_state: str,
        target_state: str,
        reason: str = "",
        **context: Any,
    ) -> None:
        message = (
            f"Invalid queue state transition for {group_id}: "
            f"{current_state} -> {target_state}"
        )
        if reason:
            message += f" ({reason})"
        super().__init__(
            message,
            group_id=group_id,
            current_state=current_state,
            target_state=target_state,
            reason=reason,
            recoverable=False,
            **context,
        )


# =============================================================================
# Calibration Errors
# =============================================================================

class CalibrationError(PipelineError):
    """
    Error during calibration operations.
    
    Raised when:
    - Calibration table not found
    - Calibration apply fails
    - Calibrator not found in catalog
    - Solution quality is poor
    
    Context keys:
        ms_path: Path to Measurement Set
        cal_table: Path to calibration table
        calibrator: Calibrator source name
    """
    
    def __init__(
        self,
        message: str,
        ms_path: str = "",
        cal_table: str = "",
        calibrator: str = "",
        original_exception: Optional[BaseException] = None,
        recoverable: bool = False,
        **context: Any,
    ) -> None:
        super().__init__(
            message,
            pipeline_stage="calibration",
            recoverable=recoverable,
            original_exception=original_exception,
            ms_path=ms_path,
            cal_table=cal_table,
            calibrator=calibrator,
            **context,
        )


class CalibrationTableNotFoundError(CalibrationError):
    """Calibration table not found."""
    
    def __init__(
        self,
        ms_path: str,
        cal_table: str,
        **context: Any,
    ) -> None:
        message = f"Calibration table not found: {cal_table} for MS {ms_path}"
        super().__init__(
            message,
            ms_path=ms_path,
            cal_table=cal_table,
            recoverable=False,
            **context,
        )


class CalibratorNotFoundError(CalibrationError):
    """Calibrator source not found in catalog."""
    
    def __init__(
        self,
        calibrator: str,
        ms_path: str = "",
        catalog: str = "",
        **context: Any,
    ) -> None:
        message = f"Calibrator {calibrator} not found in catalog"
        if catalog:
            message += f" ({catalog})"
        super().__init__(
            message,
            ms_path=ms_path,
            calibrator=calibrator,
            catalog=catalog,
            recoverable=False,
            **context,
        )


# =============================================================================
# Imaging Errors
# =============================================================================

class ImagingError(PipelineError):
    """
    Error during imaging operations.
    
    Raised when:
    - WSClean or tclean fails
    - Image file not found
    - Image quality check fails
    
    Context keys:
        ms_path: Path to Measurement Set
        image_path: Path to output image
        imager: Imaging tool used (wsclean, tclean)
    """
    
    def __init__(
        self,
        message: str,
        ms_path: str = "",
        image_path: str = "",
        imager: str = "",
        original_exception: Optional[BaseException] = None,
        recoverable: bool = False,
        **context: Any,
    ) -> None:
        super().__init__(
            message,
            pipeline_stage="imaging",
            recoverable=recoverable,
            original_exception=original_exception,
            ms_path=ms_path,
            image_path=image_path,
            imager=imager,
            **context,
        )


class ImageNotFoundError(ImagingError):
    """Image file not found."""
    
    def __init__(
        self,
        image_path: str,
        **context: Any,
    ) -> None:
        message = f"Image not found: {image_path}"
        super().__init__(
            message,
            image_path=image_path,
            recoverable=False,
            **context,
        )


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(PipelineError):
    """
    Error during input validation.
    
    Raised when:
    - Required parameters missing
    - Parameter values out of range
    - Invalid file formats
    - Inconsistent input data
    
    Context keys:
        field: Name of the invalid field
        value: The invalid value (if safe to log)
        constraint: The validation constraint that failed
    """
    
    def __init__(
        self,
        message: str,
        field: str = "",
        value: Any = None,
        constraint: str = "",
        recoverable: bool = True,  # User can fix and retry
        **context: Any,
    ) -> None:
        # Don't log potentially sensitive values unless explicitly allowed
        safe_value = value if context.get("log_value", False) else "<redacted>"
        super().__init__(
            message,
            pipeline_stage="validation",
            recoverable=recoverable,
            field=field,
            value=safe_value,
            constraint=constraint,
            **context,
        )


class MissingParameterError(ValidationError):
    """Required parameter is missing."""
    
    def __init__(
        self,
        parameter: str,
        **context: Any,
    ) -> None:
        message = f"Missing required parameter: {parameter}"
        super().__init__(
            message,
            field=parameter,
            constraint="required",
            **context,
        )


class InvalidPathError(ValidationError):
    """File or directory path is invalid or doesn't exist."""
    
    def __init__(
        self,
        path: str,
        path_type: str = "path",  # "file", "directory", "path"
        reason: str = "",
        **context: Any,
    ) -> None:
        message = f"Invalid {path_type}: {path}"
        if reason:
            message += f" ({reason})"
        super().__init__(
            message,
            field=path_type,
            value=path,
            log_value=True,  # Paths are safe to log
            reason=reason,
            **context,
        )


# =============================================================================
# Exception helpers
# =============================================================================

def wrap_exception(
    exc: BaseException,
    wrapper_class: type[PipelineError] = PipelineError,
    message: Optional[str] = None,
    **context: Any,
) -> PipelineError:
    """
    Wrap a standard exception in a pipeline-specific exception.
    
    Preserves the original exception and its traceback.
    
    Args:
        exc: The original exception to wrap
        wrapper_class: The pipeline exception class to use
        message: Optional override message (defaults to str(exc))
        **context: Additional context for the exception
    
    Returns:
        A pipeline exception wrapping the original
    
    Example:
        try:
            h5py.File(path, 'r')
        except OSError as e:
            raise wrap_exception(e, UVH5ReadError, file_path=path)
    """
    # Use the base PipelineError if wrapper has incompatible signature
    try:
        return wrapper_class(
            message or str(exc),
            original_exception=exc,
            **context,
        )
    except TypeError:
        # Fall back to base PipelineError for incompatible signatures
        return PipelineError(
            message or str(exc),
            original_exception=exc,
            **context,
        )


def is_recoverable(exc: BaseException) -> bool:
    """
    Check if an exception indicates a recoverable error.
    
    Args:
        exc: The exception to check
    
    Returns:
        True if processing can continue, False if it should halt
    """
    if isinstance(exc, PipelineError):
        return exc.recoverable
    
    # Standard exceptions that are typically recoverable
    recoverable_types = (
        FileNotFoundError,  # Can skip missing files
        PermissionError,    # Can retry with different permissions
        TimeoutError,       # Can retry
    )
    return isinstance(exc, recoverable_types)
