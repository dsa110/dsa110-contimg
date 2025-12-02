from typing import List, Optional, Union

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

# CASA import moved to function level to prevent logs in workspace root
# See: docs/dev-notes/analysis/casa_log_handling_investigation.md

from dsa110_contimg.calibration.validate import (
    validate_caltables_for_use,
)
from dsa110_contimg.utils import timed


def _verify_corrected_data_populated(ms_path: str, min_fraction: float = 0.01) -> None:
    """Verify CORRECTED_DATA column is populated after applycal.

    This ensures we follow "measure twice, cut once" - verify calibration
    was applied successfully before proceeding.

    Args:
        ms_path: Path to Measurement Set
        min_fraction: Minimum fraction of unflagged data that must be non-zero

    Raises:
        RuntimeError: If CORRECTED_DATA is not populated
    """
    import casacore.tables as casatables  # type: ignore[import]
    import numpy as np  # type: ignore[import]

    table = casatables.table  # noqa: N816

    try:
        with table(ms_path, readonly=True) as tb:
            if "CORRECTED_DATA" not in tb.colnames():
                raise RuntimeError(
                    f"CORRECTED_DATA column not present in MS: {ms_path}. "
                    f"Calibration may not have been applied successfully."
                )

            n_rows = tb.nrows()
            if n_rows == 0:
                raise RuntimeError(f"MS has zero rows: {ms_path}. Cannot verify calibration.")

            # Sample data (up to 10000 rows for efficiency)
            sample_size = min(10000, n_rows)
            corrected_data = tb.getcol("CORRECTED_DATA", startrow=0, nrow=sample_size)
            flags = tb.getcol("FLAG", startrow=0, nrow=sample_size)

            # Check unflagged data
            unflagged = corrected_data[~flags]
            if len(unflagged) == 0:
                raise RuntimeError(
                    f"All CORRECTED_DATA is flagged in MS: {ms_path}. "
                    f"Cannot verify calibration was applied."
                )

            # Check fraction non-zero
            nonzero_count = np.count_nonzero(np.abs(unflagged) > 1e-10)
            nonzero_fraction = nonzero_count / len(unflagged) if len(unflagged) > 0 else 0.0

            if nonzero_fraction < min_fraction:
                raise RuntimeError(
                    f"CORRECTED_DATA appears unpopulated in MS: {ms_path}. "
                    f"Only {nonzero_fraction * 100:.1f}% of unflagged data is non-zero "
                    f"(minimum {min_fraction * 100:.1f}% required). "
                    f"Calibration may not have been applied successfully."
                )

            print(
                f":check: Verified CORRECTED_DATA populated: {nonzero_fraction * 100:.1f}% "
                f"non-zero ({nonzero_count}/{len(unflagged)} unflagged samples)"
            )
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(
            f"Failed to verify CORRECTED_DATA population in MS: {ms_path}. Error: {e}"
        ) from e


@timed("calibration.apply_to_target")
def apply_to_target(
    ms_target: str,
    field: str,
    gaintables: List[str],
    interp: Optional[List[str]] = None,
    calwt: bool = True,
    # CASA accepts a single list (applied to all tables) or a list-of-lists
    # (one mapping per gaintable). Use Union typing to document both shapes.
    spwmap: Optional[Union[List[int], List[List[int]]]] = None,
    verify: bool = True,
) -> None:
    """Apply calibration tables to a target MS field.

    **PRECONDITION**: All calibration tables must exist and be compatible with
    the MS. This ensures consistent, reliable calibration application.

    **POSTCONDITION**: If `verify=True`, CORRECTED_DATA is verified to be populated
    after application. This ensures calibration was applied successfully.

    interp defaults will be set to 'linear' matching list length.
    """
    # PRECONDITION CHECK: Validate all calibration tables before applying
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration application.
    if not gaintables:
        raise ValueError("No calibration tables provided for applycal")

    print(f"Validating {len(gaintables)} calibration table(s) before applying...")

    # STRICT SEPARATION: Reject NON_SCIENCE calibration tables for production use
    for gaintable in gaintables:
        if "NON_SCIENCE" in gaintable:
            raise ValueError(
                f":warning:  STRICT SEPARATION VIOLATION: Attempting to apply NON_SCIENCE calibration table '{gaintable}' to production data.\n"
                f"   NON_SCIENCE tables (prefixed with 'NON_SCIENCE_*') are created by development tier calibration.\n"
                f"   These tables CANNOT be applied to production/science data due to time-channel binning mismatches.\n"
                f"   Use standard or high_precision tier calibration for production data."
            )

    try:
        validate_caltables_for_use(gaintables, ms_target, require_all=True)
    except (FileNotFoundError, ValueError) as e:
        raise ValueError(
            f"Calibration table validation failed. This is a required precondition for "
            f"applycal. Error: {e}"
        ) from e

    if interp is None:
        # Prefer 'nearest' for bandpass-like tables, 'linear' for gains.
        # Heuristic by table name; callers can override explicitly.
        _defaults: List[str] = []
        for gt in gaintables:
            low = gt.lower()
            if "bpcal" in low or "bandpass" in low:
                _defaults.append("nearest")
            else:
                _defaults.append("linear")
        interp = _defaults
    kwargs = dict(
        vis=ms_target,
        field=field,
        gaintable=gaintables,
        interp=interp,
        calwt=calwt,
    )
    # Only pass spwmap if explicitly provided; CASA rejects explicit null
    if spwmap is not None:
        kwargs["spwmap"] = spwmap

    print(f"Applying {len(gaintables)} calibration table(s) to {ms_target}...")
    from casatasks import applycal as casa_applycal

    casa_applycal(**kwargs)

    # POSTCONDITION CHECK: Verify CORRECTED_DATA was populated successfully
    # This ensures we follow "measure twice, cut once" - verify calibration was
    # applied successfully before proceeding.
    if verify:
        _verify_corrected_data_populated(ms_target)
