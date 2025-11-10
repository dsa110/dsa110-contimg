"""
Centralized validation functions for CLI and pipeline operations.

This module provides validation utilities using exception-based design,
following Python best practices (aligns with Pydantic, argparse patterns).

Validation functions raise ValidationError when validation fails,
ensuring type safety and enforcing the "parse, don't validate" principle.
"""

from typing import Optional, List
from pathlib import Path
import os
import shutil
import numpy as np

# Import ValidationError from unified exception hierarchy
from dsa110_contimg.utils.exceptions import ValidationError

# Re-export for backward compatibility
__all__ = [
    'ValidationError',
    'validate_file_path',
    'validate_directory',
    'validate_ms',
    'validate_ms_for_calibration',
    'validate_corrected_data_quality',
    'check_disk_space',
]


def validate_file_path(path: str, must_exist: bool = True,
                       must_readable: bool = True) -> Path:
    """
    Validate a file path with clear error messages.

    Args:
        path: File path to validate
        must_exist: Whether file must exist
        must_readable: Whether file must be readable

    Returns:
        Path object if valid

    Raises:
        ValidationError: If validation fails
    """
    p = Path(path)

    if must_exist and not p.exists():
        raise ValidationError(
            [f"File does not exist: {path}"],
            error_types=['ms_not_found'] if path.endswith('.ms') else [
                'file_not_found'],
            error_details=[{'path': path}]
        )

    if must_exist and not p.is_file():
        raise ValidationError(
            [f"Path is not a file: {path}"],
            error_types=['file_not_found'],
            error_details=[{'path': path}]
        )

    if must_readable and not os.access(path, os.R_OK):
        raise ValidationError(
            [f"File is not readable: {path}"],
            error_types=['permission_denied'],
            error_details=[{'path': path}]
        )

    return p


def validate_directory(path: str, must_exist: bool = True,
                       must_readable: bool = False,
                       must_writable: bool = False) -> Path:
    """
    Validate a directory path with clear error messages.

    Args:
        path: Directory path to validate
        must_exist: Whether directory must exist (if False, creates it)
        must_readable: Whether directory must be readable
        must_writable: Whether directory must be writable

    Returns:
        Path object if valid

    Raises:
        ValidationError: If validation fails
    """
    p = Path(path)

    if must_exist:
        if not p.exists():
            # Try to create it
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                raise ValidationError(
                    [f"Cannot create directory {path}: {exc}"])

        if not p.is_dir():
            raise ValidationError([f"Path is not a directory: {path}"])

    if must_readable and not os.access(path, os.R_OK):
        raise ValidationError([f"Directory is not readable: {path}"])

    if must_writable and not os.access(path, os.W_OK):
        raise ValidationError([f"Directory is not writable: {path}"])

    return p


def validate_ms(ms_path: str, check_empty: bool = True,
                check_columns: Optional[List[str]] = None) -> None:
    """
    Validate a Measurement Set with clear error messages.

    Args:
        ms_path: Path to Measurement Set
        check_empty: Whether to check if MS is empty
        check_columns: Optional list of required column names

    Raises:
        ValidationError: If validation fails
    """
    # MS files are directories, not files - validate as directory
    validate_directory(ms_path, must_exist=True, must_readable=True)

    # Validate MS structure (lazy import CASA dependency)
    # Ensure CASAPATH is set before importing CASA modules
    from dsa110_contimg.utils.casa_init import ensure_casa_path
    ensure_casa_path()

    try:
        from casacore.tables import table
    except ImportError:
        raise ValidationError(
            [f"Cannot import casacore.tables. Is CASA installed?"])

    try:
        with table(ms_path, readonly=True) as tb:
            if check_empty and tb.nrows() == 0:
                raise ValidationError(
                    [f"MS is empty: {ms_path}"],
                    error_types=['ms_empty'],
                    error_details=[{'path': ms_path}]
                )

            if check_columns:
                missing = [c for c in check_columns if c not in tb.colnames()]
                if missing:
                    raise ValidationError(
                        [f"MS missing required columns: {missing}. Path: {ms_path}"],
                        error_types=['ms_missing_columns'],
                        error_details=[{'path': ms_path, 'missing': missing}]
                    )
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(
            [f"MS is not readable: {ms_path}. Error: {e}"]) from e


def validate_ms_for_calibration(ms_path: str, field: Optional[str] = None,
                                refant: Optional[str] = None) -> List[str]:
    """
    Comprehensive MS validation for calibration operations.

    Validates:
    - MS exists and is readable
    - MS is not empty
    - Field exists (if provided)
    - Reference antenna exists (if provided)

    Args:
        ms_path: Path to Measurement Set
        field: Optional field selection (for validation)
        refant: Optional reference antenna ID (for validation)

    Returns:
        List of warning messages (errors raise ValidationError)

    Raises:
        ValidationError: If validation fails (errors prevent operation)
    """
    warnings = []

    # Basic MS validation
    validate_ms(ms_path, check_empty=True,
                check_columns=['DATA', 'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW'])

    # Field validation if provided
    if field:
        try:
            from casacore.tables import table
            from dsa110_contimg.calibration.calibration import _resolve_field_ids

            with table(ms_path, readonly=True) as tb:
                field_ids = tb.getcol('FIELD_ID')
                available_fields = sorted(set(field_ids))

            target_ids = _resolve_field_ids(ms_path, field)
            if not target_ids:
                raise ValidationError([f"Cannot resolve field: {field}"])

            missing = set(target_ids) - set(available_fields)
            if missing:
                raise ValidationError(
                    [f"Field(s) not found: {sorted(missing)}. Available fields: {available_fields}"],
                    error_types=['field_not_found'],
                    error_details=[{
                        'field': field,
                        'missing': sorted(missing),
                        'available': available_fields
                    }]
                )
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError([f"Failed to validate field: {e}"]) from e

    # Reference antenna validation if provided
    if refant:
        try:
            from casacore.tables import table

            with table(ms_path, readonly=True) as tb:
                ant1 = tb.getcol('ANTENNA1')
                ant2 = tb.getcol('ANTENNA2')
                all_antennas = set(ant1) | set(ant2)

            refant_int = int(refant) if isinstance(refant, str) else refant
            if refant_int not in all_antennas:
                # Try to suggest alternatives
                suggestions = []
                try:
                    from dsa110_contimg.utils.antenna_classification import (
                        select_outrigger_refant, get_outrigger_antennas
                    )
                    outrigger_refant = select_outrigger_refant(
                        list(all_antennas), preferred_refant=refant_int
                    )
                    if outrigger_refant:
                        suggestions.append(
                            f"Suggested outrigger: {outrigger_refant}")
                    outriggers = get_outrigger_antennas(list(all_antennas))
                    if outriggers:
                        suggestions.append(
                            f"Available outriggers: {outriggers}")
                except Exception:
                    pass

                error_msg = (
                    f"Reference antenna {refant} not found. "
                    f"Available antennas: {sorted(all_antennas)}"
                )
                if suggestions:
                    error_msg += f". {'; '.join(suggestions)}"

                suggested_refant = None
                if outrigger_refant:
                    suggested_refant = outrigger_refant
                else:
                    suggested_refant = sorted(all_antennas)[
                        0] if all_antennas else None

                raise ValidationError(
                    [error_msg],
                    error_types=['refant_not_found'],
                    error_details=[{
                        'refant': refant,
                        'available': sorted(all_antennas),
                        'suggested': suggested_refant
                    }]
                )
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                [f"Failed to validate reference antenna: {e}"]) from e

    # Check flagged data fraction (warning only)
    try:
        from casacore.tables import table
        with table(ms_path, readonly=True) as tb:
            flags = tb.getcol('FLAG')
            unflagged_fraction = np.sum(
                ~flags) / flags.size if flags.size > 0 else 0
            if unflagged_fraction < 0.1:
                warnings.append(
                    f"Very little unflagged data: {unflagged_fraction*100:.1f}%"
                )
    except (OSError, IOError, RuntimeError, AttributeError) as e:
        # Non-fatal check - log but don't fail
        import logging
        logging.debug("Could not check flagged data fraction: %s", e)

    return warnings


def validate_corrected_data_quality(ms_path: str, sample_size: int = 10000) -> List[str]:
    """
    Validate CORRECTED_DATA column quality.

    **CRITICAL**: If CORRECTED_DATA exists but is unpopulated (all zeros), this indicates
    calibration was attempted but failed. Returns warnings that should cause the caller
    to FAIL rather than proceed with uncalibrated data.

    Args:
        ms_path: Path to Measurement Set
        sample_size: Number of rows to sample for validation

    Returns:
        List of warning messages (empty if no issues). If CORRECTED_DATA exists but is
        unpopulated, returns warnings that should cause the caller to raise an error.
    """
    warnings = []

    try:
        from casacore.tables import table

        with table(ms_path, readonly=True) as tb:
            if 'CORRECTED_DATA' not in tb.colnames():
                # No corrected data column - calibration never attempted, this is fine
                return warnings  # Return empty warnings

            # CORRECTED_DATA exists - calibration was attempted, must verify it worked
            n_rows = tb.nrows()
            if n_rows == 0:
                warnings.append(
                    "CORRECTED_DATA column exists but MS has zero rows - calibration may have failed"
                )
                return warnings

            sample_size = min(sample_size, n_rows)

            if sample_size > 0:
                corrected_data = tb.getcol(
                    'CORRECTED_DATA', startrow=0, nrow=sample_size)
                flags = tb.getcol('FLAG', startrow=0, nrow=sample_size)

                unflagged = corrected_data[~flags]
                if len(unflagged) == 0:
                    warnings.append(
                        "CORRECTED_DATA column exists but all sampled data is flagged - "
                        "calibration may have failed"
                    )
                else:
                    nonzero_count = np.count_nonzero(np.abs(unflagged) > 1e-10)
                    nonzero_fraction = nonzero_count / len(unflagged)

                    if nonzero_fraction < 0.01:
                        warnings.append(
                            f"CORRECTED_DATA column exists but appears unpopulated "
                            f"({nonzero_fraction*100:.1f}% non-zero in sampled data) - "
                            f"calibration appears to have failed"
                        )
    except Exception as e:
        # If we can't check, that's a problem - return a warning
        warnings.append(f"Error validating CORRECTED_DATA: {e}")

    return warnings


def check_disk_space(path: str, min_bytes: Optional[int] = None) -> List[str]:
    """
    Check available disk space for a path.

    Args:
        path: Path to check disk space for
        min_bytes: Minimum required bytes (None to skip check)

    Returns:
        List of warning messages (empty if sufficient space)
    """
    warnings = []

    try:
        output_dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(output_dir, exist_ok=True)
        available = shutil.disk_usage(output_dir).free

        if min_bytes and available < min_bytes:
            warnings.append(
                f"Insufficient disk space: need {min_bytes/1e9:.1f} GB, "
                f"available {available/1e9:.1f} GB"
            )
    except Exception as e:
        warnings.append(f"Failed to check disk space: {e}")

    return warnings
