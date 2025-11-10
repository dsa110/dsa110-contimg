"""Utilities for detecting and repairing corrupted Measurement Sets.

This module provides functions to detect MS corruption (often caused by
WSClean or other external tools modifying MODEL_DATA) and attempt repairs.
"""

from __future__ import annotations

import os
from typing import Optional
import warnings


def detect_ms_corruption(ms_path: str) -> tuple[bool, list[str]]:
    """Detect if an MS is corrupted.

    Returns:
        (is_corrupted, list_of_issues) tuple
    """
    from casacore.tables import table  # type: ignore

    issues = []

    try:
        # Try to open MS
        t = table(ms_path, readonly=True)

        # Check if MODEL_DATA exists and has data
        if "MODEL_DATA" in t.colnames():
            try:
                if t.nrows() > 0:
                    model_sample = t.getcell("MODEL_DATA", 0)
                    if model_sample is not None:
                        model_sum = abs(model_sample).sum()
                        if model_sum > 0:
                            issues.append(
                                f"MODEL_DATA contains data (sum={model_sum:.2f}), "
                                "may have been modified by WSClean"
                            )
            except Exception as e:
                issues.append(f"Cannot read MODEL_DATA: {e}")

        # Check subtables
        subtable_names = ["SPECTRAL_WINDOW", "FIELD", "ANTENNA"]
        for subtable_name in subtable_names:
            try:
                st = table(f"{ms_path}::{subtable_name}", readonly=True)
                nrows = st.nrows()
                # Try to read a row
                if nrows > 0:
                    try:
                        st.getcell(st.colnames()[0], 0)
                    except Exception as e:
                        issues.append(f"Subtable {subtable_name} corrupted: {e}")
                st.close()
            except Exception as e:
                issues.append(f"Cannot access subtable {subtable_name}: {e}")

        t.close()

    except Exception as e:
        issues.append(f"Cannot open MS: {e}")

    return len(issues) > 0, issues


def attempt_model_data_repair(ms_path: str) -> bool:
    """Attempt to repair MODEL_DATA column by removing and recreating it.

    WARNING: This may fail if the MS has deeper corruption.

    Returns:
        True if repair succeeded, False otherwise
    """
    from casacore.tables import table, addImagingColumns  # type: ignore

    try:
        # Open MS
        t = table(ms_path, readonly=False)

        # Remove MODEL_DATA if it exists
        if "MODEL_DATA" in t.colnames():
            t.removecols(["MODEL_DATA"])

        t.close()

        # Recreate MODEL_DATA
        addImagingColumns(ms_path)

        return True

    except Exception as e:
        warnings.warn(
            f"Failed to repair MODEL_DATA in {ms_path}: {e}. "
            "The MS may be too corrupted. Consider recreating from original data.",
            RuntimeWarning,
        )
        return False


def is_ms_safe_for_ft(ms_path: str) -> bool:
    """Check if MS is safe for CASA ft() operation.

    Returns:
        True if MS appears safe, False if corruption detected
    """
    is_corrupted, issues = detect_ms_corruption(ms_path)

    if is_corrupted:
        # Check if corruption is only MODEL_DATA (repairable)
        # vs deeper structural issues (not repairable)
        model_data_only = all(
            "MODEL_DATA" in issue or "cannot read MODEL_DATA" in issue.lower()
            for issue in issues
        )

        return not model_data_only  # Only safe if corruption is repairable

    return True  # No corruption detected


def repair_ms_for_ft(ms_path: str, backup: bool = True) -> Optional[str]:
    """Attempt to repair an MS so it can be used with CASA ft().

    Args:
        ms_path: Path to MS
        backup: If True, create backup before attempting repair

    Returns:
        Path to repaired MS if successful, None if repair failed
    """
    is_corrupted, issues = detect_ms_corruption(ms_path)

    if not is_corrupted:
        return ms_path  # Already safe

    # Check if corruption is repairable
    if not is_ms_safe_for_ft(ms_path):
        warnings.warn(
            f"MS {ms_path} has deep corruption (issues: {issues}). "
            "Recreation from original data may be required.",
            RuntimeWarning,
        )
        return None

    # Create backup if requested
    backup_path = None
    if backup:
        backup_path = ms_path + ".backup"
        if os.path.exists(backup_path):
            import shutil

            shutil.rmtree(backup_path)

        from casacore.tables import table

        t = table(ms_path, readonly=True)
        t.copy(backup_path, deep=True, valuecopy=True)
        t.close()

    # Attempt repair
    if attempt_model_data_repair(ms_path):
        return ms_path

    return None
