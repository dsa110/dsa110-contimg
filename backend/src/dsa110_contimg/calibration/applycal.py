"""
Apply calibration tables to target measurement sets.

GPU Safety:
    Entry point apply_to_target() is wrapped with @memory_safe to ensure
    system RAM limits are respected before processing. Calibration is memory-
    intensive and can cause OOM on large datasets.

GPU Acceleration (Phase 3.3):
    The module now supports GPU-accelerated gain application via apply_gains().
    This provides ~10x speedup for large datasets when CuPy is available.
    Falls back to CASA applycal or CPU when GPU is unavailable.
"""

import logging
from typing import List, Optional, Tuple, Union

import numpy as np

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

# CASA import moved to function level to prevent logs in workspace root
# See: docs/dev-notes/analysis/casa_log_handling_investigation.md

from dsa110_contimg.calibration.validate import (
    validate_caltables_for_use,
)
from dsa110_contimg.utils import timed
from dsa110_contimg.utils.gpu_safety import (
    memory_safe,
    gpu_safe,
    initialize_gpu_safety,
    check_gpu_memory_available,
    is_gpu_available,
)

logger = logging.getLogger("applycal")

# Initialize GPU safety limits at module load time
initialize_gpu_safety()

# Check if GPU calibration is available
try:
    from dsa110_contimg.calibration.gpu_calibration import (
        apply_gains,
        ApplyCalResult,
    )
    GPU_CALIBRATION_AVAILABLE = True
except ImportError:
    GPU_CALIBRATION_AVAILABLE = False
    apply_gains = None  # type: ignore[assignment]
    ApplyCalResult = None  # type: ignore[assignment]


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

    table = casatables.table  # noqa: N816

    try:
        with table(ms_path, readonly=True) as tb:
            _check_corrected_data_column(tb, ms_path)
            _verify_nonzero_fraction(tb, ms_path, min_fraction)
    except RuntimeError:
        raise
    except (OSError, ValueError, KeyError) as e:
        raise RuntimeError(
            f"Failed to verify CORRECTED_DATA population in MS: {ms_path}. Error: {e}"
        ) from e


def _check_corrected_data_column(tb, ms_path: str) -> None:
    """Check that CORRECTED_DATA column exists and MS has data."""
    if "CORRECTED_DATA" not in tb.colnames():
        raise RuntimeError(
            f"CORRECTED_DATA column not present in MS: {ms_path}. "
            f"Calibration may not have been applied successfully."
        )

    if tb.nrows() == 0:
        raise RuntimeError(f"MS has zero rows: {ms_path}. Cannot verify calibration.")


def _verify_nonzero_fraction(tb, ms_path: str, min_fraction: float) -> None:
    """Verify that a sufficient fraction of CORRECTED_DATA is non-zero."""
    n_rows = tb.nrows()
    sample_size = min(10000, n_rows)
    corrected_data = tb.getcol("CORRECTED_DATA", startrow=0, nrow=sample_size)
    flags = tb.getcol("FLAG", startrow=0, nrow=sample_size)

    unflagged = corrected_data[~flags]
    if len(unflagged) == 0:
        raise RuntimeError(
            f"All CORRECTED_DATA is flagged in MS: {ms_path}. "
            f"Cannot verify calibration was applied."
        )

    nonzero_count = np.count_nonzero(np.abs(unflagged) > 1e-10)
    nonzero_fraction = nonzero_count / len(unflagged) if len(unflagged) > 0 else 0.0

    if nonzero_fraction < min_fraction:
        raise RuntimeError(
            f"CORRECTED_DATA appears unpopulated in MS: {ms_path}. "
            f"Only {nonzero_fraction * 100:.1f}% of unflagged data is non-zero "
            f"(minimum {min_fraction * 100:.1f}% required). "
        )

    logger.info(
        "Verified CORRECTED_DATA populated: %.1f%% non-zero (%d/%d samples)",
        nonzero_fraction * 100, nonzero_count, len(unflagged)
    )


def _read_gains_from_caltable(caltable_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Read complex gains from a CASA calibration table.

    Args:
        caltable_path: Path to calibration table

    Returns:
        Tuple of (gains, antenna_ids) where gains shape is (n_ant, n_pol)
    """
    import casacore.tables as casatables

    with casatables.table(caltable_path, readonly=True) as tb:
        gains = tb.getcol("CPARAM")  # Complex gains
        ant_ids = tb.getcol("ANTENNA1")
        flags = tb.getcol("FLAG")

        # Average over time/spw if multiple solutions
        # Take first solution interval for simplicity
        if gains.ndim == 3:  # (n_rows, n_chan, n_pol)
            gains = gains[:, 0, :]  # Take first channel
        elif gains.ndim == 2:  # (n_rows, n_pol)
            pass
        else:
            gains = gains.reshape(-1, 1)

        # Apply flags - set flagged gains to 1.0 (identity)
        if flags.ndim == 3:
            flags = flags[:, 0, :]
        gains = np.where(flags, 1.0 + 0j, gains)

        return gains, ant_ids


def _read_ms_for_gpu_cal(
    ms_path: str, datacolumn: str = "DATA",
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read visibilities and antenna indices from MS for GPU calibration.

    Args:
        ms_path: Path to Measurement Set
        datacolumn: Data column to read

    Returns:
        Tuple of (vis, ant1, ant2) arrays
    """
    import casacore.tables as casatables

    with casatables.table(ms_path, readonly=True) as tb:
        vis = tb.getcol(datacolumn)
        ant1 = tb.getcol("ANTENNA1")
        ant2 = tb.getcol("ANTENNA2")

    return vis, ant1, ant2


def _write_corrected_data(ms_path: str, corrected: np.ndarray) -> None:
    """Write corrected visibilities back to MS."""
    import casacore.tables as casatables

    with casatables.table(ms_path, readonly=False) as tb:
        tb.putcol("CORRECTED_DATA", corrected)


@gpu_safe(max_gpu_gb=6.0, max_system_gb=6.0)
def apply_gains_to_ms(
    ms_path: str,
    gaintable: str,
    *,
    datacolumn: str = "DATA",
    use_gpu: bool = True,
) -> Optional["ApplyCalResult"]:
    """Apply gains from a calibration table to an MS using GPU acceleration.

    GPU Acceleration:
        Uses CuPy-based gain application for ~10x speedup on large datasets.
        Falls back to CPU when GPU is unavailable.

    Args:
        ms_path: Path to Measurement Set
        gaintable: Path to calibration table with complex gains
        datacolumn: Data column to calibrate (default: DATA)
        use_gpu: Whether to attempt GPU acceleration

    Returns:
        ApplyCalResult with statistics, or None if GPU calibration unavailable
    """
    if not GPU_CALIBRATION_AVAILABLE:
        logger.warning("GPU calibration not available")
        return None

    logger.info("GPU gain application %s with %s", ms_path, gaintable)

    try:
        # Read gains from caltable
        gains, gain_ant_ids = _read_gains_from_caltable(gaintable)
        n_ant = int(np.max(gain_ant_ids)) + 1

        # Reorganize gains by antenna ID
        gains_by_ant = np.ones((n_ant, gains.shape[1]), dtype=np.complex128)
        for i, ant_id in enumerate(gain_ant_ids):
            gains_by_ant[ant_id] = gains[i]

        # Read MS data
        vis, ant1, ant2 = _read_ms_for_gpu_cal(ms_path, datacolumn)

        # Flatten for GPU processing if needed
        original_shape = vis.shape
        if vis.ndim > 1:
            vis_flat = vis.reshape(-1)
            # Expand antenna indices to match flattened vis
            n_extra = vis.size // len(ant1)
            ant1_exp = np.repeat(ant1, n_extra)
            ant2_exp = np.repeat(ant2, n_extra)
        else:
            vis_flat = vis
            ant1_exp = ant1
            ant2_exp = ant2

        # Extract scalar gains (first polarization)
        gains_scalar = gains_by_ant[:, 0]

        # Check GPU availability
        gpu_ok, _ = check_gpu_memory_available(2.0)
        actual_use_gpu = use_gpu and gpu_ok and is_gpu_available()

        # Apply gains
        result = apply_gains(
            vis_flat, gains_scalar, ant1_exp, ant2_exp, use_gpu=actual_use_gpu
        )

        # Reshape and write back
        corrected = vis_flat.reshape(original_shape)
        _write_corrected_data(ms_path, corrected)

        logger.info(
            "GPU calibration complete: %d/%d vis calibrated in %.2fs",
            result.n_vis_calibrated, result.n_vis_processed, result.processing_time_s
        )
        return result

    except (OSError, RuntimeError, ValueError) as exc:
        logger.error("GPU gain application failed: %s", exc)
        return None


@memory_safe(max_system_gb=6.0)
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
    
    Memory Safety:
        Wrapped with @memory_safe to check system RAM availability before
        processing. Rejects if less than 30% RAM available or less than 2GB free.

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
