"""
Shared validation for execution tasks.

This module provides validation logic that is shared between
in-process and subprocess execution modes.

Part of Issue #11: Subprocess vs In-Process Execution Consistency.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when task validation fails."""

    pass


@dataclass
class ValidationResult:
    """Result of task validation.

    Attributes:
        valid: Whether the task is valid
        errors: List of validation error messages
        warnings: List of validation warning messages
    """

    valid: bool
    errors: List[str]
    warnings: List[str]

    @classmethod
    def success(cls, warnings: Optional[List[str]] = None) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def failure(cls, errors: List[str], warnings: Optional[List[str]] = None) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(valid=False, errors=errors, warnings=warnings or [])

    def raise_if_invalid(self) -> None:
        """Raise ValidationError if validation failed."""
        if not self.valid:
            raise ValidationError("; ".join(self.errors))


def validate_input_dir(input_dir: Path) -> List[str]:
    """Validate input directory.

    Args:
        input_dir: Path to input directory

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not input_dir.exists():
        errors.append(f"Input directory does not exist: {input_dir}")
    elif not input_dir.is_dir():
        errors.append(f"Input path is not a directory: {input_dir}")
    elif not os.access(input_dir, os.R_OK):
        errors.append(f"Input directory is not readable: {input_dir}")

    return errors


def validate_output_dir(output_dir: Path, create: bool = True) -> List[str]:
    """Validate output directory.

    Args:
        output_dir: Path to output directory
        create: Whether to create directory if it doesn't exist

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not output_dir.exists():
        if create:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                errors.append(f"Cannot create output directory {output_dir}: {e}")
        else:
            errors.append(f"Output directory does not exist: {output_dir}")
    elif not output_dir.is_dir():
        errors.append(f"Output path is not a directory: {output_dir}")
    elif not os.access(output_dir, os.W_OK):
        errors.append(f"Output directory is not writable: {output_dir}")

    return errors


def validate_scratch_dir(scratch_dir: Optional[Path]) -> List[str]:
    """Validate scratch directory.

    Args:
        scratch_dir: Path to scratch directory (None = use system temp)

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if scratch_dir is None:
        return errors

    if not scratch_dir.exists():
        try:
            scratch_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            errors.append(f"Cannot create scratch directory {scratch_dir}: {e}")
            return errors

    if not scratch_dir.is_dir():
        errors.append(f"Scratch path is not a directory: {scratch_dir}")
    elif not os.access(scratch_dir, os.W_OK):
        errors.append(f"Scratch directory is not writable: {scratch_dir}")

    return errors


def validate_time_range(start_time: str | datetime, end_time: str | datetime) -> List[str]:
    """Validate time range.

    Args:
        start_time: Start of time range (string or datetime)
        end_time: End of time range (string or datetime)

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Convert strings to datetime if needed
    if isinstance(start_time, str):
        try:
            start_dt = datetime.fromisoformat(start_time)
        except ValueError as e:
            errors.append(f"Invalid start_time format: {e}")
            return errors
    else:
        start_dt = start_time

    if isinstance(end_time, str):
        try:
            end_dt = datetime.fromisoformat(end_time)
        except ValueError as e:
            errors.append(f"Invalid end_time format: {e}")
            return errors
    else:
        end_dt = end_time

    if start_dt >= end_dt:
        errors.append(f"Start time ({start_time}) must be before end time ({end_time})")
        return errors

    # Check for suspiciously wide time ranges (more than 24 hours)
    duration = (end_dt - start_dt).total_seconds()
    if duration > 86400:  # 24 hours
        logger.warning(
            f"Time range spans {duration / 3600:.1f} hours - this may process "
            "many observation groups"
        )

    return errors


def validate_writer(writer: str) -> List[str]:
    """Validate writer type.

    Args:
        writer: Writer type string

    Returns:
        List of error messages (empty if valid)
    """
    valid_writers = {"auto", "parallel-subband", "direct-subband"}

    if writer not in valid_writers:
        return [f"Invalid writer '{writer}', must be one of: {valid_writers}"]

    return []


def validate_resource_limits(
    memory_mb: Optional[int] = None,
    omp_threads: Optional[int] = None,
    max_workers: Optional[int] = None,
) -> List[str]:
    """Validate resource limit values.

    Args:
        memory_mb: Memory limit in MB
        omp_threads: OMP thread count
        max_workers: Max worker count

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if memory_mb is not None and memory_mb < 1024:
        errors.append(f"Memory limit {memory_mb} MB is too low (minimum 1024 MB)")

    if omp_threads is not None and omp_threads < 1:
        errors.append(f"OMP threads must be >= 1, got {omp_threads}")

    if max_workers is not None and max_workers < 1:
        errors.append(f"Max workers must be >= 1, got {max_workers}")

    return errors


def validate_execution_task(
    input_dir: Path,
    output_dir: Path,
    start_time: str | datetime,
    end_time: str | datetime,
    writer: str = "auto",
    scratch_dir: Optional[Path] = None,
    memory_mb: Optional[int] = None,
    omp_threads: Optional[int] = None,
    max_workers: Optional[int] = None,
) -> ValidationResult:
    """Validate all parameters for an execution task.

    This is the main validation entry point that combines all
    individual validation functions.

    Args:
        input_dir: Path to input directory
        output_dir: Path to output directory
        start_time: Start of time range
        end_time: End of time range
        writer: Writer type
        scratch_dir: Path to scratch directory
        memory_mb: Memory limit in MB
        omp_threads: OMP thread count
        max_workers: Max worker count

    Returns:
        ValidationResult with success/failure status

    Example:
        result = validate_execution_task(
            input_dir=Path("/data/incoming"),
            output_dir=Path("/stage/ms"),
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 2),
        )
        result.raise_if_invalid()
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Validate directories
    errors.extend(validate_input_dir(input_dir))
    errors.extend(validate_output_dir(output_dir, create=True))
    errors.extend(validate_scratch_dir(scratch_dir))

    # Validate time range
    errors.extend(validate_time_range(start_time, end_time))

    # Validate writer
    errors.extend(validate_writer(writer))

    # Validate resource limits
    errors.extend(validate_resource_limits(memory_mb, omp_threads, max_workers))

    if errors:
        return ValidationResult.failure(errors, warnings)

    return ValidationResult.success(warnings)
