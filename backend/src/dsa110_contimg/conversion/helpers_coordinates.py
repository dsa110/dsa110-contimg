"""Coordinate and phase helper functions for conversion."""

import logging
from typing import Optional, Tuple

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.time import Time
from pyuvdata import utils as uvutils

try:  # pyuvdata>=3.2: faster uvw calculator
    from pyuvdata.utils.phasing import calc_uvw as _PU_CALC_UVW  # type: ignore
except (ImportError, AttributeError):  # pragma: no cover - fallback
    _PU_CALC_UVW = None

# pyuvdata 3.2+: phasing functions moved to submodule
try:
    from pyuvdata.utils.phasing import (
        calc_app_coords as _calc_app_coords,
        calc_frame_pos_angle as _calc_frame_pos_angle,
    )
except (ImportError, AttributeError):  # pragma: no cover - fallback for older versions
    _calc_app_coords = uvutils.calc_app_coords
    _calc_frame_pos_angle = uvutils.calc_frame_pos_angle

from dsa110_contimg.conversion.helpers_antenna import (
    _ensure_antenna_diameters,
    set_antenna_positions,
)

# OPTIMIZATION 3: Try to use numba-accelerated angular separation
try:
    from dsa110_contimg.utils.numba_accel import (
        angular_separation_jit,
        NUMBA_AVAILABLE,
    )
    _USE_NUMBA_ANGULAR_SEP = NUMBA_AVAILABLE
except ImportError:
    _USE_NUMBA_ANGULAR_SEP = False

logger = logging.getLogger("dsa110_contimg.conversion.helpers")


def angular_separation(ra1, dec1, ra2, dec2):
    """Compute angular separation, using numba if available.

    Falls back to pure numpy implementation if numba is not installed.
    """
    if _USE_NUMBA_ANGULAR_SEP:
        # Use numba-accelerated version
        return angular_separation_jit(
            np.asarray(ra1, dtype=np.float64),
            np.asarray(dec1, dtype=np.float64),
            np.asarray(ra2, dtype=np.float64),
            np.asarray(dec2, dtype=np.float64),
        )
    # Pure numpy fallback
    ra1 = np.asarray(ra1, dtype=float)
    dec1 = np.asarray(dec1, dtype=float)
    ra2 = np.asarray(ra2, dtype=float)
    dec2 = np.asarray(dec2, dtype=float)
    cossep = np.sin(dec1) * np.sin(dec2) + np.cos(dec1) * np.cos(dec2) * np.cos(ra1 - ra2)
    cossep = np.clip(cossep, -1.0, 1.0)
    return np.arccos(cossep)


# OPTIMIZATION: Pre-compute OVRO longitude in radians for fast LST calculation
# This avoids repeated attribute access during batch processing
_OVRO_LON_RAD: Optional[float] = None


def _get_ovro_lon_rad() -> float:
    """Get OVRO longitude in radians (cached)."""
    global _OVRO_LON_RAD
    if _OVRO_LON_RAD is None:
        from dsa110_contimg.utils.constants import OVRO_LOCATION
        _OVRO_LON_RAD = float(OVRO_LOCATION.lon.to_value(u.rad))
    return _OVRO_LON_RAD


def get_meridian_coords(
    pt_dec: u.Quantity,
    time_mjd: float,
    fast: bool = False,
) -> Tuple[u.Quantity, u.Quantity]:
    """Compute the right ascension/declination of the meridian at DSA-110.

    Args:
        pt_dec: Pointing declination
        time_mjd: Time in MJD
        fast: If True, use approximate LST calculation (numba-accelerated).
              Returns LST as RA (not aberration-corrected ICRS).
              If False (default), use full astropy calculation with proper
              aberration/precession/nutation corrections for rigorous astrometry.

    Returns:
        Tuple of (RA, Dec) as astropy Quantities in radians

    Note:
        The default fast=False ensures rigorous coordinate transformations.
        The fast path is available for non-critical applications but should
        not be used where astrometric accuracy is important.
    """
    if fast:
        # OPTIMIZATION: Use numba-accelerated LST approximation
        # This is ~10x faster than astropy for simple meridian tracking
        try:
            from dsa110_contimg.utils.numba_accel import approx_lst_jit, NUMBA_AVAILABLE
            if NUMBA_AVAILABLE:
                lon_rad = _get_ovro_lon_rad()
                mjd_arr = np.array([time_mjd], dtype=np.float64)
                lst_rad = approx_lst_jit(mjd_arr, lon_rad)[0]
                # At meridian, RA = LST
                return lst_rad * u.rad, pt_dec.to(u.rad)
        except ImportError:
            pass  # Fall through to astropy path

    # Use DSA-110 coordinates from constants.py (single source of truth)
    from dsa110_contimg.utils.constants import OVRO_LOCATION

    dsa110_loc = OVRO_LOCATION
    obstime = Time(time_mjd, format="mjd")
    hadec_coord = SkyCoord(
        ha=0 * u.hourangle,
        dec=pt_dec,
        frame="hadec",
        obstime=obstime,
        location=dsa110_loc,
    )
    icrs_coord = hadec_coord.transform_to("icrs")
    return icrs_coord.ra.to(u.rad), icrs_coord.dec.to(u.rad)


def phase_to_meridian(uvdata, pt_dec: Optional[u.Quantity] = None) -> None:
    """Phase a UVData object to the meridian with time-dependent phase centers.

    This function sets time-dependent phase centers that track the meridian
    (RA=LST) throughout the observation, ensuring proper phase coherence as
    Earth rotates. Each unique time sample gets its own phase center at
    RA=LST(time), Dec=pointing_dec.

    This follows radio interferometry best practices where phase centers must
    continuously track Earth's rotation to maintain coherence and prevent phase
    errors from accumulating.

    Parameters
    ----------
    uvdata : UVData
        The UVData object to be phased.
    pt_dec : astropy.units.Quantity, optional
        The pointing declination. If not provided, it will be extracted from
        the `phase_center_dec` keyword in the UVData object.
    """
    if pt_dec is None:
        pt_dec = uvdata.extra_keywords.get("phase_center_dec", 0.0) * u.rad

    # Set antenna positions and diameters first
    set_antenna_positions(uvdata)
    _ensure_antenna_diameters(uvdata)

    # Get unique times and create phase centers for each
    # This ensures phase center RA tracks LST throughout the observation
    unique_times, _, time_inverse = np.unique(
        uvdata.time_array, return_index=True, return_inverse=True
    )
    n_unique = len(unique_times)

    # OPTIMIZATION: Pre-allocate arrays for phase center coordinates
    # This avoids repeated array allocations in the loop
    phase_ra_arr = np.zeros(n_unique, dtype=np.float64)
    phase_dec_arr = np.zeros(n_unique, dtype=np.float64)

    # OPTIMIZATION: Batch convert JD to MJD once (avoids repeated Time object creation)
    mjd_unique = Time(unique_times, format="jd").mjd

    # Clear existing phase centers and create time-dependent ones
    uvdata.phase_center_catalog = {}
    phase_center_ids = {}

    # Create a phase center for each unique time
    # Use rigorous astropy calculation for accurate phase centers
    for i in range(n_unique):
        phase_ra, phase_dec = get_meridian_coords(pt_dec, float(mjd_unique[i]), fast=False)
        phase_ra_arr[i] = float(phase_ra.to_value(u.rad))
        phase_dec_arr[i] = float(phase_dec.to_value(u.rad))

        # Create phase center with unique name per time
        pc_id = uvdata._add_phase_center(
            cat_name=f"meridian_icrs_t{i}",
            cat_type="sidereal",
            cat_lon=phase_ra_arr[i],
            cat_lat=phase_dec_arr[i],
            cat_frame="icrs",
            cat_epoch=2000.0,
        )
        phase_center_ids[unique_times[i]] = pc_id

    # OPTIMIZATION: Pre-allocate phase_center_id_array if needed
    if getattr(uvdata, "phase_center_id_array", None) is None:
        uvdata.phase_center_id_array = np.zeros(uvdata.Nblts, dtype=np.int32)

    # Vectorized mapping: create array of phase center IDs indexed by time
    # OPTIMIZATION: Use numpy array operations instead of list comprehension
    pc_id_array = np.array(
        [phase_center_ids[unique_times[i]] for i in range(n_unique)],
        dtype=np.int32
    )
    uvdata.phase_center_id_array[:] = pc_id_array[time_inverse]

    # Recompute UVW coordinates
    # (already time-dependent via compute_and_set_uvw)
    compute_and_set_uvw(uvdata, pt_dec)

    # Update metadata to reflect the new phasing
    # Use midpoint values for backward compatibility with legacy code
    phase_time = Time(float(np.mean(uvdata.time_array)), format="jd")
    phase_ra_mid, phase_dec_mid = get_meridian_coords(pt_dec, phase_time.mjd)
    uvdata.phase_type = "phased"
    uvdata.phase_center_ra = phase_ra_mid.to_value(u.rad)
    uvdata.phase_center_dec = phase_dec_mid.to_value(u.rad)
    uvdata.phase_center_frame = "icrs"
    uvdata.phase_center_epoch = 2000.0
    uvdata.reorder_freqs(channel_order="freq", run_check=False)


def compute_and_set_uvw(uvdata, pt_dec: u.Quantity) -> None:
    """Recompute uvw_array for a UVData object at the meridian of pt_dec.

    Uses pyuvdata utilities to compute apparent coordinates and frame
    position angle per unique time, then computes UVW vectors using
    antenna positions and numbers. Updates uvdata.uvw_array in place.
    """
    import numpy as _np
    from astropy.time import Time as _Time

    # Telescope metadata (lat, lon, alt; frame)
    tel_latlonalt = getattr(uvdata, "telescope_location_lat_lon_alt", None)
    if tel_latlonalt is None and hasattr(uvdata, "telescope"):
        tel_latlonalt = getattr(uvdata.telescope, "location_lat_lon_alt", None)
    tel_frame = getattr(uvdata, "_telescope_location", None)
    tel_frame = getattr(tel_frame, "frame", None)

    # Antenna metadata
    ant_pos = getattr(uvdata, "antenna_positions", None)
    if ant_pos is None and hasattr(uvdata, "telescope"):
        ant_pos = getattr(uvdata.telescope, "antenna_positions", None)
    ant_nums = getattr(uvdata, "antenna_numbers", None)
    if ant_nums is None and hasattr(uvdata, "telescope"):
        ant_nums = getattr(uvdata.telescope, "antenna_numbers", None)
    ant_pos = _np.asarray(ant_pos) if ant_pos is not None else None
    ant_nums = _np.asarray(ant_nums) if ant_nums is not None else None

    utime, _, uinvert = _np.unique(uvdata.time_array, return_index=True, return_inverse=True)
    mjd_unique = _Time(utime, format="jd").mjd.astype(float)

    # Compute apparent coords + frame PA per unique time at meridian
    # OPTIMIZATION: Pre-allocate output arrays to avoid resizing
    app_ra_unique = _np.zeros(len(utime), dtype=float)
    app_dec_unique = _np.zeros(len(utime), dtype=float)
    frame_pa_unique = _np.zeros(len(utime), dtype=float)

    for i, mjd in enumerate(mjd_unique):
        # Use rigorous astropy calculation for accurate UVW computation
        ra_icrs, dec_icrs = get_meridian_coords(pt_dec, float(mjd), fast=False)
        try:
            new_app_ra, new_app_dec = uvutils.calc_app_coords(
                ra_icrs.to_value(u.rad),
                dec_icrs.to_value(u.rad),
                coord_frame="icrs",
                coord_epoch=2000.0,
                coord_times=None,
                coord_type="sidereal",
                time_array=uvdata.time_array[uinvert == i],
                lst_array=uvdata.lst_array[uinvert == i],
                pm_ra=None,
                pm_dec=None,
                vrad=None,
                dist=None,
                telescope_loc=tel_latlonalt,
                telescope_frame=tel_frame,
            )
            new_frame_pa = uvutils.calc_frame_pos_angle(
                uvdata.time_array[uinvert == i],
                new_app_ra,
                new_app_dec,
                tel_latlonalt,
                "icrs",
                ref_epoch=2000.0,
                telescope_frame=tel_frame,
            )
            app_ra_unique[i] = float(new_app_ra[0])
            app_dec_unique[i] = float(new_app_dec[0])
            frame_pa_unique[i] = float(new_frame_pa[0])
        except (ValueError, IndexError, TypeError):
            # ValueError: coordinate transformation failures
            # IndexError: array access issues, TypeError: type conversion
            app_ra_unique[i] = float(ra_icrs.to_value(u.rad))
            app_dec_unique[i] = float(dec_icrs.to_value(u.rad))
            frame_pa_unique[i] = 0.0

    app_ra_all = app_ra_unique[uinvert]
    app_dec_all = app_dec_unique[uinvert]
    frame_pa_all = frame_pa_unique[uinvert]

    # Compute UVW using pyuvdata fast path when available
    if _PU_CALC_UVW is not None:
        uvw_all = _PU_CALC_UVW(
            app_ra=app_ra_all,
            app_dec=app_dec_all,
            frame_pa=frame_pa_all,
            lst_array=uvdata.lst_array,
            use_ant_pos=True,
            antenna_positions=ant_pos,
            antenna_numbers=ant_nums,
            ant_1_array=uvdata.ant_1_array,
            ant_2_array=uvdata.ant_2_array,
            telescope_lat=tel_latlonalt[0],
            telescope_lon=tel_latlonalt[1],
        )
    else:  # fallback for older pyuvdata
        uvw_all = uvutils.calc_uvw(
            app_ra=app_ra_all,
            app_dec=app_dec_all,
            frame_pa=frame_pa_all,
            lst_array=uvdata.lst_array,
            use_ant_pos=True,
            antenna_positions=ant_pos,
            antenna_numbers=ant_nums,
            ant_1_array=uvdata.ant_1_array,
            ant_2_array=uvdata.ant_2_array,
            telescope_lat=tel_latlonalt[0],
            telescope_lon=tel_latlonalt[1],
        )

    uvdata.uvw_array[:, :] = uvw_all
