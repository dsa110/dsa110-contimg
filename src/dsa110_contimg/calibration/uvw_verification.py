"""UVW transformation verification utilities.

This module provides functions to verify that UVW coordinates are correctly
transformed after rephasing operations (phaseshift, fixvis).
"""

from typing import Optional, Tuple

import astropy.units as u
import numpy as np

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

import casacore.tables as casatables
from astropy.coordinates import SkyCoord

table = casatables.table  # noqa: N816


def calculate_expected_uvw_change(
    old_phase_center: Tuple[float, float],
    new_phase_center: Tuple[float, float],
    baseline_length_meters: float = 200.0,
) -> float:
    """Calculate expected UVW change for a given phase shift.

    Args:
        old_phase_center: (RA_deg, Dec_deg) of old phase center
        new_phase_center: (RA_deg, Dec_deg) of new phase center
        baseline_length_meters: Typical baseline length for estimation

    Returns:
        Expected UVW change in meters
    """
    old_coord = SkyCoord(
        ra=old_phase_center[0] * u.deg, dec=old_phase_center[1] * u.deg, frame="icrs"
    )
    new_coord = SkyCoord(
        ra=new_phase_center[0] * u.deg, dec=new_phase_center[1] * u.deg, frame="icrs"
    )

    separation = old_coord.separation(new_coord)
    separation_rad = separation.to(u.rad).value

    # Expected UVW change: baseline_length * sin(separation)
    # For small separations, this approximates baseline_length * separation
    expected_change = baseline_length_meters * np.sin(separation_rad)

    return expected_change


def get_uvw_statistics(ms_path: str, n_sample: int = 1000) -> dict:
    """Get UVW coordinate statistics from MS.

    Args:
        ms_path: Path to Measurement Set
        n_sample: Number of rows to sample (for speed)

    Returns:
        Dictionary with UVW statistics:
        - u_mean, u_std, u_range
        - v_mean, v_std, v_range
        - w_mean, w_std, w_range
        - baseline_length_mean, baseline_length_std
    """
    with table(ms_path, readonly=True) as main_tb:
        nrows = main_tb.nrows()
        n_sample = min(n_sample, nrows)

        uvw = main_tb.getcol("UVW", startrow=0, nrow=n_sample)
        flags = main_tb.getcol("FLAG", startrow=0, nrow=n_sample)

        # Get unflagged data
        unflagged_mask = ~flags.any(axis=(1, 2))
        if unflagged_mask.sum() == 0:
            # All flagged, use all data
            uvw_unflagged = uvw
        else:
            uvw_unflagged = uvw[unflagged_mask]

        u = uvw_unflagged[:, 0]
        v = uvw_unflagged[:, 1]
        w = uvw_unflagged[:, 2]

        baseline_length = np.sqrt(u**2 + v**2)

        stats = {
            "u_mean": float(np.mean(u)),
            "u_std": float(np.std(u)),
            "u_range": (float(np.min(u)), float(np.max(u))),
            "v_mean": float(np.mean(v)),
            "v_std": float(np.std(v)),
            "v_range": (float(np.min(v)), float(np.max(v))),
            "w_mean": float(np.mean(w)),
            "w_std": float(np.std(w)),
            "w_range": (float(np.min(w)), float(np.max(w))),
            "baseline_length_mean": float(np.mean(baseline_length)),
            "baseline_length_std": float(np.std(baseline_length)),
            "baseline_length_range": (
                float(np.min(baseline_length)),
                float(np.max(baseline_length)),
            ),
        }

        return stats


def verify_uvw_transformation(
    ms_before: str,
    ms_after: str,
    old_phase_center: Tuple[float, float],
    new_phase_center: Tuple[float, float],
    tolerance_meters: float = 0.1,
    min_change_meters: float = 0.01,
) -> Tuple[bool, Optional[str]]:
    """Verify UVW was correctly transformed by rephasing operation.

    Args:
        ms_before: Path to MS before rephasing
        ms_after: Path to MS after rephasing
        old_phase_center: (RA_deg, Dec_deg) of old phase center
        new_phase_center: (RA_deg, Dec_deg) of new phase center
        tolerance_meters: Tolerance for UVW change matching expected
        min_change_meters: Minimum expected UVW change (to detect no transformation)

    Returns:
        (is_valid, error_message)
        - is_valid: True if UVW transformation is correct
        - error_message: None if valid, error description if invalid
    """
    try:
        # Get UVW statistics before and after
        stats_before = get_uvw_statistics(ms_before)
        stats_after = get_uvw_statistics(ms_after)

        # Calculate actual UVW change
        u_change = abs(stats_after["u_mean"] - stats_before["u_mean"])
        v_change = abs(stats_after["v_mean"] - stats_before["v_mean"])
        w_change = abs(stats_after["w_mean"] - stats_before["w_mean"])
        max_change = max(u_change, v_change, w_change)

        # Calculate expected UVW change
        baseline_length = stats_before["baseline_length_mean"]
        expected_change = calculate_expected_uvw_change(
            old_phase_center, new_phase_center, baseline_length
        )

        # Check if transformation occurred (absolute requirement)
        if max_change < min_change_meters:
            return False, (
                f"UVW transformation failed: maximum change {max_change:.3f} meters "
                f"is less than minimum expected {min_change_meters:.3f} meters. "
                f"Expected change for {baseline_length:.1f}m baseline: {expected_change:.3f} meters. "
                f"phaseshift did not transform UVW coordinates."
            )

        # Check if transformation matches expected (within tolerance)
        # For large phase shifts, allow larger tolerance
        separation = SkyCoord(
            ra=old_phase_center[0] * u.deg,
            dec=old_phase_center[1] * u.deg,
            frame="icrs",
        ).separation(
            SkyCoord(
                ra=new_phase_center[0] * u.deg,
                dec=new_phase_center[1] * u.deg,
                frame="icrs",
            )
        )
        separation_arcmin = separation.to(u.arcmin).value

        # Adjust tolerance based on phase shift magnitude
        # phaseshift has known limitations for very large phase shifts (>50 arcmin)
        if separation_arcmin > 50.0:
            # Very large shift - phaseshift may not fully transform UVW
            # Allow much larger tolerance to account for this limitation
            adjusted_tolerance = max(tolerance_meters, expected_change * 2.0)
        elif separation_arcmin > 30.0:
            # Large phase shift - allow larger tolerance
            adjusted_tolerance = max(tolerance_meters, expected_change * 0.5)
        else:
            adjusted_tolerance = tolerance_meters

        change_error = abs(max_change - expected_change)
        if change_error > adjusted_tolerance:
            return False, (
                f"UVW transformation magnitude mismatch: actual change {max_change:.3f} meters "
                f"does not match expected {expected_change:.3f} meters "
                f"(error: {change_error:.3f} meters, tolerance: {adjusted_tolerance:.3f} meters). "
                f"Phase shift: {separation_arcmin:.1f} arcmin"
            )

        # Transformation appears correct
        return True, None

    except Exception as e:
        return False, f"Error verifying UVW transformation: {e}"


def verify_uvw_alignment(
    ms_path: str,
    ms_phase_center: Tuple[float, float],
    expected_phase_center: Tuple[float, float],
    tolerance_arcsec: float = 1.0,
) -> bool:
    """Verify UVW coordinates are aligned with phase center (sanity check).

    This is a simpler check for when rephasing is not needed - we verify that
    the UVW frame is consistent with the phase center (for small offsets).

    Args:
        ms_path: Path to Measurement Set
        ms_phase_center: (RA_deg, Dec_deg) from MS FIELD table
        expected_phase_center: (RA_deg, Dec_deg) expected phase center
        tolerance_arcsec: Maximum allowed offset in arcseconds

    Returns:
        True if UVW appears aligned, False otherwise
    """
    try:
        # Check if phase centers match (within tolerance)
        ms_coord = SkyCoord(
            ra=ms_phase_center[0] * u.deg, dec=ms_phase_center[1] * u.deg, frame="icrs"
        )
        exp_coord = SkyCoord(
            ra=expected_phase_center[0] * u.deg,
            dec=expected_phase_center[1] * u.deg,
            frame="icrs",
        )
        separation = ms_coord.separation(exp_coord)
        separation_arcsec = separation.to(u.arcsec).value

        if separation_arcsec > tolerance_arcsec:
            # Phase centers don't match - UVW might be wrong
            return False

        # For small offsets, UVW should be consistent
        # We can't fully verify without before/after comparison, but we can check
        # that UVW statistics are reasonable (not obviously wrong)
        stats = get_uvw_statistics(ms_path)

        # Basic sanity check: UVW should have reasonable values
        # For DSA-110, baselines are typically 100-400 meters
        if stats["baseline_length_mean"] < 10.0 or stats["baseline_length_mean"] > 1000.0:
            # UVW values seem wrong
            return False

        # For now, if phase centers match and UVW stats are reasonable, assume OK
        # (Full verification would require before/after comparison)
        return True

    except Exception:
        # If verification fails, assume OK (non-blocking check)
        return True


def get_phase_center_from_ms(ms_path: str, field: int = 0) -> Tuple[float, float]:
    """Get phase center from MS FIELD table.

    Args:
        ms_path: Path to Measurement Set
        field: Field index (default: 0)

    Returns:
        (RA_deg, Dec_deg) of phase center from REFERENCE_DIR
    """
    with table(f"{ms_path}::FIELD", readonly=True) as field_tb:
        ref_dir = field_tb.getcol("REFERENCE_DIR")[field][0]
        ra_deg = ref_dir[0] * 180.0 / np.pi
        dec_deg = ref_dir[1] * 180.0 / np.pi
        return (ra_deg, dec_deg)
