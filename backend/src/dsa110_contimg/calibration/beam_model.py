"""Unified primary beam model interface.

This module provides a consistent interface for primary beam calculations
across the pipeline. Uses EveryBeam when available (via MS file), otherwise
falls back to an Airy disk model that matches EveryBeam's generic dish model.

The Airy disk model matches EveryBeam's implementation for generic dishes:
  PB(theta) = (2 * J1(x) / x)²
  where x = π * D * sin(theta) / λ
  J1 is the first-order Bessel function
"""

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.special import j1

logger = logging.getLogger(__name__)

# Try to import EveryBeam if available
try:
    # Set up library path for EveryBeam dependencies
    # This ensures EveryBeam and casacore libraries can be found at runtime
    project_root = Path(__file__).parent.parent.parent.parent.parent
    everybeam_lib = project_root / "external" / "everybeam" / "lib"
    casa6_lib = Path("/opt/miniforge/envs/casa6/lib")

    if everybeam_lib.exists():
        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        new_paths = [str(everybeam_lib), str(casa6_lib)]
        if current_ld_path:
            new_paths.append(current_ld_path)
        os.environ["LD_LIBRARY_PATH"] = ":".join(new_paths)

    import everybeam_py

    _EVERYBEAM_AVAILABLE = True
    logger.info(f"EveryBeam Python bindings available (version: {everybeam_py.version()})")
except ImportError:
    _EVERYBEAM_AVAILABLE = False
    logger.debug("EveryBeam Python bindings not available, using Airy disk model")


def primary_beam_response(
    ant_ra: float,
    ant_dec: float,
    src_ra: float,
    src_dec: float,
    freq_GHz: float,
    dish_dia_m: float = 4.7,
    *,
    ms_path: Optional[str] = None,
    field_id: int = 0,
    beam_mode: str = "analytic",
) -> float:
    """Calculate primary beam response using unified model.

    This function provides a consistent beam model across the pipeline.
    Uses EveryBeam when an MS file is provided, otherwise falls back to
    an Airy disk model that matches EveryBeam's generic dish implementation.

    Args:
        ant_ra: Antenna/field phase center RA in radians
        ant_dec: Antenna/field phase center Dec in radians
        src_ra: Source RA in radians
        src_dec: Source Dec in radians
        freq_GHz: Frequency in GHz
        dish_dia_m: Dish diameter in meters (default: 4.7m for DSA-110)
                    Only used for Airy fallback
        ms_path: Optional path to Measurement Set file. If provided and
                 EveryBeam is available, uses EveryBeam for accurate beam
                 modeling. If None, falls back to Airy disk model.
        field_id: Field ID in MS (default: 0). Only used with EveryBeam.
        beam_mode: EveryBeam beam mode (default: "analytic"). Options:
                   "analytic", "full", "numeric", "element", "array", "none".

    Returns:
        Primary beam response in [0, 1] where 1.0 = at phase center

    Note:
        When using EveryBeam (ms_path provided), the response is extracted
        from the Jones matrix by averaging the diagonal elements. This provides
        a scalar response consistent with the Airy model interface.
    """
    # Use EveryBeam if MS path is provided and EveryBeam is available
    if ms_path is not None and _EVERYBEAM_AVAILABLE:
        try:
            ms_path_obj = Path(ms_path)
            if not ms_path_obj.exists():
                logger.warning(f"MS file not found: {ms_path}, falling back to Airy model")
            else:
                return _everybeam_response(
                    str(ms_path_obj),
                    ant_ra,
                    ant_dec,
                    src_ra,
                    src_dec,
                    freq_GHz,
                    field_id,
                    beam_mode,
                )
        except Exception as e:
            logger.warning(f"EveryBeam evaluation failed: {e}, falling back to Airy model")

    # Use Airy disk model (matches EveryBeam's generic dish model)
    return _airy_primary_beam_response(ant_ra, ant_dec, src_ra, src_dec, freq_GHz, dish_dia_m)


def _everybeam_response(
    ms_path: str,
    ant_ra: float,
    ant_dec: float,
    src_ra: float,
    src_dec: float,
    freq_GHz: float,
    field_id: int = 0,
    beam_mode: str = "analytic",
) -> float:
    """Calculate primary beam response using EveryBeam.

    This function uses EveryBeam to compute Jones matrices and extracts
    a scalar beam response by averaging the diagonal elements.

    Args:
        ms_path: Path to Measurement Set file
        ant_ra: Antenna/field phase center RA in radians
        ant_dec: Antenna/field phase center Dec in radians
        src_ra: Source RA in radians
        src_dec: Source Dec in radians
        freq_GHz: Frequency in GHz
        field_id: Field ID in MS
        beam_mode: EveryBeam beam mode

    Returns:
        Primary beam response in [0, 1]
    """
    # Convert angles from radians to degrees for EveryBeam API
    src_ra_deg = np.rad2deg(src_ra)
    src_dec_deg = np.rad2deg(src_dec)

    # Convert frequency from GHz to Hz
    freq_hz = freq_GHz * 1e9

    # Call EveryBeam to get Jones matrices
    # Shape: (stations, times, frequencies, 2, 2)
    jones_matrices = everybeam_py.evaluate_primary_beam(
        ms_path=ms_path,
        times_seconds=None,  # Use default time from MS
        frequencies_hz=[freq_hz],
        ra_deg=src_ra_deg,
        dec_deg=src_dec_deg,
        field_id=field_id,
        beam_mode=beam_mode,
    )

    # Extract scalar response from Jones matrices
    # Shape: (stations, times, frequencies, 2, 2)
    # Average over stations and times, take diagonal average of 2x2 matrix
    # Jones matrix diagonal represents the beam response for each polarization
    n_stations, n_times, n_freqs = jones_matrices.shape[:3]

    # Average diagonal elements: (J[0,0] + J[1,1]) / 2
    # Then average over stations and times
    # For each station/time, extract the 2x2 Jones matrix and average its diagonal
    diagonal_values = []
    for s in range(n_stations):
        for t in range(n_times):
            # Get the 2x2 Jones matrix for this station/time/frequency
            jones_2x2 = jones_matrices[s, t, 0, :, :]  # Shape: (2, 2)
            # Average diagonal: (J[0,0] + J[1,1]) / 2
            diag_avg = (jones_2x2[0, 0] + jones_2x2[1, 1]) / 2.0
            diagonal_values.append(diag_avg)

    # Average over all stations and times
    diagonal_avg = np.mean(diagonal_values)

    # Take magnitude (Jones matrices are complex)
    response = abs(diagonal_avg)

    # Clamp to [0, 1]
    return float(np.clip(response, 0.0, 1.0))


def _airy_primary_beam_response(
    ant_ra: float,
    ant_dec: float,
    src_ra: float,
    src_dec: float,
    freq_GHz: float,
    dish_dia_m: float = 4.7,
) -> float:
    """Calculate primary beam response using Airy disk pattern.

    This matches EveryBeam's generic dish model for circular apertures.
    Formula: PB(theta) = (2 * J1(x) / x)²
    where J1 is the first-order Bessel function of the first kind.

    Args:
        ant_ra: Antenna/field phase center RA in radians
        ant_dec: Antenna/field phase center Dec in radians
        src_ra: Source RA in radians
        src_dec: Source Dec in radians
        freq_GHz: Frequency in GHz
        dish_dia_m: Dish diameter in meters

    Returns:
        Primary beam response in [0, 1]
    """
    # Offset angle approximation on the sky
    dra = (src_ra - ant_ra) * np.cos(ant_dec)
    ddec = src_dec - ant_dec
    theta = np.sqrt(dra * dra + ddec * ddec)

    # Handle zero separation case (source at phase center)
    if theta == 0.0 or theta < 1e-10:
        return 1.0

    # Airy disk: x = π * D * sin(theta) / λ
    # where λ = c / f
    c_mps = 299792458.0
    lam_m = c_mps / (freq_GHz * 1e9)
    x = np.pi * dish_dia_m * np.sin(theta) / lam_m

    # Avoid division by zero (but we already handled theta == 0 above)
    if x == 0.0 or abs(x) < 1e-10:
        return 1.0

    # Airy pattern: (2 * J1(x) / x)²
    # Using scipy's first-order Bessel function of the first kind
    resp = (2.0 * j1(x) / x) ** 2

    # Clamp numeric noise
    return float(np.clip(resp, 0.0, 1.0))


# Backward compatibility: keep old function name
def airy_primary_beam_response(
    ant_ra: float,
    ant_dec: float,
    src_ra: float,
    src_dec: float,
    freq_GHz: float,
    dish_dia_m: float = 4.7,
) -> float:
    """Legacy function name for backward compatibility.

    Deprecated: Use primary_beam_response() instead.
    This function is kept for backward compatibility.
    """
    return primary_beam_response(ant_ra, ant_dec, src_ra, src_dec, freq_GHz, dish_dia_m)
