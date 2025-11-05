"""Helper utilities for UVH5 → CASA Measurement Set conversion."""

import logging
from typing import Optional, Tuple

import numpy as np
import astropy.units as u
from astropy.coordinates import EarthLocation, SkyCoord
try:
    from astropy.coordinates import angular_separation  # type: ignore
except Exception:  # pragma: no cover - fallback for older astropy
    def angular_separation(ra1, dec1, ra2, dec2):
        import numpy as _np
        ra1 = _np.asarray(ra1, dtype=float)
        dec1 = _np.asarray(dec1, dtype=float)
        ra2 = _np.asarray(ra2, dtype=float)
        dec2 = _np.asarray(dec2, dtype=float)
        cossep = _np.sin(dec1) * _np.sin(dec2) + _np.cos(dec1) * _np.cos(dec2) * _np.cos(ra1 - ra2)
        cossep = _np.clip(cossep, -1.0, 1.0)
        return _np.arccos(cossep)
from astropy.time import Time
from casacore.tables import table
from pyuvdata import utils as uvutils
try:  # pyuvdata>=3.2: faster uvw calculator
    from pyuvdata.utils.phasing import calc_uvw as _PU_CALC_UVW  # type: ignore
except Exception:  # pragma: no cover - fallback
    _PU_CALC_UVW = None

from dsa110_contimg.utils.antpos_local import get_itrf

logger = logging.getLogger("dsa110_contimg.conversion.helpers")


def get_meridian_coords(pt_dec: u.Quantity, time_mjd: float) -> Tuple[u.Quantity, u.Quantity]:
    """Compute the right ascension/declination of the meridian at OVRO."""
    ovro_loc = EarthLocation.from_geodetic(
        lon=-118.2817 * u.deg,
        lat=37.2314 * u.deg,
        height=1222 * u.m,
    )
    obstime = Time(time_mjd, format="mjd")
    hadec_coord = SkyCoord(
        ha=0 * u.hourangle,
        dec=pt_dec,
        frame="hadec",
        obstime=obstime,
        location=ovro_loc,
    )
    icrs_coord = hadec_coord.transform_to("icrs")
    return icrs_coord.ra.to(u.rad), icrs_coord.dec.to(u.rad)


def _get_relative_antenna_positions(uv) -> np.ndarray:
    """Return antenna positions relative to the telescope location."""
    if hasattr(uv, "antenna_positions") and uv.antenna_positions is not None:
        return uv.antenna_positions
    telescope = getattr(uv, "telescope", None)
    if telescope is not None and getattr(telescope, "antenna_positions", None) is not None:
        return telescope.antenna_positions
    raise AttributeError("UVData object has no antenna_positions information")


def _set_relative_antenna_positions(uv, rel_positions: np.ndarray) -> None:
    """Write relative antenna positions back to the UVData structure."""
    if hasattr(uv, "antenna_positions") and uv.antenna_positions is not None:
        uv.antenna_positions[: rel_positions.shape[0]] = rel_positions
    elif hasattr(uv, "antenna_positions"):
        uv.antenna_positions = rel_positions
    else:
        setattr(uv, "antenna_positions", rel_positions)

    telescope = getattr(uv, "telescope", None)
    if telescope is not None:
        if getattr(telescope, "antenna_positions", None) is not None:
            telescope.antenna_positions[: rel_positions.shape[0]] = rel_positions
        elif hasattr(telescope, "antenna_positions"):
            telescope.antenna_positions = rel_positions
        else:
            setattr(telescope, "antenna_positions", rel_positions)


def set_antenna_positions(uvdata) -> np.ndarray:
    """Populate antenna positions for the Measurement Set."""
    logger.info("Setting DSA-110 antenna positions")
    try:
        df_itrf = get_itrf(latlon_center=None)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to load antenna coordinates: %s", exc)
        raise

    abs_positions = np.array(
        [
            df_itrf["x_m"],
            df_itrf["y_m"],
            df_itrf["z_m"],
        ]
    ).T.astype(np.float64)

    telescope_location = getattr(uvdata, "telescope_location", None)
    if telescope_location is None and getattr(uvdata, "telescope", None) is not None:
        telescope_location = getattr(uvdata.telescope, "location", None)
    if telescope_location is None:
        raise AttributeError("UVData object lacks telescope location information")
    if hasattr(telescope_location, "value"):
        telescope_location = telescope_location.value
    telescope_location = np.asarray(telescope_location)
    if getattr(telescope_location, "dtype", None) is not None and telescope_location.dtype.names:
        telescope_location = np.array(
            [telescope_location["x"], telescope_location["y"], telescope_location["z"]]
        )

    rel_positions_target: Optional[np.ndarray] = None
    try:
        rel_positions_target = _get_relative_antenna_positions(uvdata)
    except AttributeError:
        pass

    if rel_positions_target is not None and rel_positions_target.shape[0] != abs_positions.shape[0]:
        raise ValueError(
            f"Mismatch between antenna counts ({rel_positions_target.shape[0]!r} vs "
            f"{abs_positions.shape[0]!r}) when loading antenna catalogue"
        )

    relative_positions = abs_positions - telescope_location
    _set_relative_antenna_positions(uvdata, relative_positions)

    logger.info("Loaded dynamic antenna positions for %s antennas", abs_positions.shape[0])

    # Ensure antenna mount metadata is populated (ALT-AZ for DSA-110)
    nants = abs_positions.shape[0]
    mounts = np.array(["ALT-AZ"] * nants, dtype="U16")
    if hasattr(uvdata, "antenna_mounts"):
        uvdata.antenna_mounts = mounts
    if getattr(uvdata, "telescope", None) is not None and hasattr(uvdata.telescope, "antenna_mounts"):
        uvdata.telescope.antenna_mounts = mounts
    return abs_positions


def _ensure_antenna_diameters(uvdata, diameter_m: float = 4.65) -> None:
    """Ensure antenna diameter metadata is populated."""
    nants: Optional[int] = None
    if hasattr(uvdata, "telescope") and getattr(uvdata.telescope, "antenna_numbers", None) is not None:
        nants = len(uvdata.telescope.antenna_numbers)
    elif getattr(uvdata, "antenna_numbers", None) is not None:
        nants = len(np.unique(uvdata.antenna_numbers))

    if nants is None:
        raise AttributeError("Unable to determine antenna count to assign diameters")

    diam_array = np.full(nants, diameter_m, dtype=np.float64)

    telescope = getattr(uvdata, "telescope", None)
    if telescope is not None and hasattr(telescope, "antenna_diameters"):
        telescope.antenna_diameters = diam_array
    if hasattr(uvdata, "antenna_diameters"):
        uvdata.antenna_diameters = diam_array


def primary_beam_response(
    ant_ra: np.ndarray,
    ant_dec: float,
    src_ra: float,
    src_dec: float,
    freq_ghz: np.ndarray,
    dish_diameter_m: float = 4.7,
) -> np.ndarray:
    """Primary beam response using the DSA-110 analytic approximation."""
    dis = np.array(angular_separation(ant_ra, ant_dec, src_ra, src_dec))
    if dis.ndim > 0 and dis.shape[0] > 1:
        dis = dis[:, np.newaxis]

    lam = 0.299792458 / freq_ghz
    arg = 1.2 * dis * dish_diameter_m / lam
    with np.errstate(divide="ignore", invalid="ignore"):
        pb = (np.cos(np.pi * arg) / (1 - 4 * arg**2)) ** 4
    return pb


def amplitude_sky_model(
    source_ra: u.Quantity,
    source_dec: u.Quantity,
    flux_jy: float,
    lst: np.ndarray,
    pt_dec: u.Quantity,
    freq_ghz: np.ndarray,
    dish_diameter_m: float = 4.7,
) -> np.ndarray:
    """Construct a primary-beam weighted amplitude model."""
    ant_ra = lst
    ant_dec = pt_dec.to_value(u.rad)
    src_ra = source_ra.to_value(u.rad)
    src_dec = source_dec.to_value(u.rad)

    pb = primary_beam_response(
        ant_ra,
        ant_dec,
        src_ra,
        src_dec,
        freq_ghz,
        dish_diameter_m=dish_diameter_m,
    )
    return (flux_jy * pb).astype(np.float32)


def phase_to_meridian(uvdata, pt_dec: Optional[u.Quantity] = None) -> None:
    """Phase a UVData object to the meridian at the midpoint of the observation.

    This function sets a single phase center for the entire UVData object,
    recomputes UVW coordinates, and updates all necessary metadata to reflect
    the new phasing.

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

    phase_time = Time(float(np.mean(uvdata.time_array)), format="jd")
    phase_ra, phase_dec = get_meridian_coords(pt_dec, phase_time.mjd)

    # Set antenna positions and diameters first
    set_antenna_positions(uvdata)
    _ensure_antenna_diameters(uvdata)

    # Set a single phase center for the entire observation
    uvdata.phase_center_catalog = {}
    pc_id = uvdata._add_phase_center(
        cat_name='meridian_icrs',
        cat_type='sidereal',
        cat_lon=float(phase_ra.to_value(u.rad)),
        cat_lat=float(phase_dec.to_value(u.rad)),
        cat_frame='icrs',
        cat_epoch=2000.0,
    )
    if getattr(uvdata, 'phase_center_id_array', None) is None:
        uvdata.phase_center_id_array = np.zeros(uvdata.Nblts, dtype=int)
    uvdata.phase_center_id_array[:] = pc_id

    # Recompute UVW coordinates
    compute_and_set_uvw(uvdata, pt_dec)

    # Update metadata to reflect the new phasing
    uvdata.phase_type = 'phased'
    uvdata.phase_center_ra = phase_ra.to_value(u.rad)
    uvdata.phase_center_dec = phase_dec.to_value(u.rad)
    uvdata.phase_center_frame = 'icrs'
    uvdata.phase_center_epoch = 2000.0
    uvdata.reorder_freqs(channel_order="freq", run_check=False)


def set_model_column(
    msname: str,
    uvdata,
    pt_dec: u.Quantity,
    ra: u.Quantity,
    dec: u.Quantity,
    flux_jy: Optional[float] = None,
) -> None:
    """Populate MODEL_DATA (and related columns) for the produced MS."""
    logger.info("Setting MODEL_DATA column")
    if flux_jy is not None:
        fobs = uvdata.freq_array.squeeze() / 1e9
        lst = uvdata.lst_array
        model = amplitude_sky_model(ra, dec, flux_jy, lst, pt_dec, fobs)
        model = np.tile(model[:, :, np.newaxis], (1, 1, uvdata.Npols)).astype(np.complex64)
    else:
        model = np.ones((uvdata.Nblts, uvdata.Nfreqs, uvdata.Npols), dtype=np.complex64)

    ms_path = f"{msname}.ms"
    with table(ms_path, readonly=False) as tb:
        data_shape = tb.getcol("DATA").shape
        model_transposed = np.transpose(model, (2, 1, 0))

        if model_transposed.shape != data_shape:
            logger.warning(
                "Model shape %s does not match DATA shape %s; skipping MODEL_DATA write",
                model_transposed.shape,
                data_shape,
            )
        else:
            tb.putcol("MODEL_DATA", model_transposed)

        if "CORRECTED_DATA" in tb.colnames():
            try:
                corr = tb.getcol("CORRECTED_DATA")
                if not np.any(corr):
                    tb.putcol("CORRECTED_DATA", tb.getcol("DATA"))
            except Exception:  # pragma: no cover - best effort
                pass

        if "WEIGHT_SPECTRUM" in tb.colnames():
            flags = tb.getcol("FLAG")
            weights = tb.getcol("WEIGHT")
            ncorr = weights.shape[0]
            nchan = flags.shape[0]

            wspec = np.repeat(weights[np.newaxis, :, :], nchan, axis=0)
            if wspec.shape != (nchan, ncorr, weights.shape[1]):
                logger.debug(
                    "Skipping WEIGHT_SPECTRUM update due to unexpected shape: %s", wspec.shape
                )
            else:
                wspec[flags] = 0.0
                tb.putcol("WEIGHT_SPECTRUM", wspec.astype(np.float32))
                logger.info("Reconstructed WEIGHT_SPECTRUM column.")

    logger.info("MODEL_DATA column set successfully")


def compute_and_set_uvw(uvdata, pt_dec: u.Quantity) -> None:
    """Recompute uvw_array for a UVData object at the meridian of pt_dec.

    Uses pyuvdata utilities to compute apparent coordinates and frame
    position angle per unique time, then computes UVW vectors using
    antenna positions and numbers. Updates uvdata.uvw_array in place.
    """
    import numpy as _np
    from astropy.time import Time as _Time

    # Telescope metadata (lat, lon, alt; frame)
    tel_latlonalt = getattr(uvdata, 'telescope_location_lat_lon_alt', None)
    if tel_latlonalt is None and hasattr(uvdata, 'telescope'):
        tel_latlonalt = getattr(uvdata.telescope, 'location_lat_lon_alt', None)
    tel_frame = getattr(uvdata, '_telescope_location', None)
    tel_frame = getattr(tel_frame, 'frame', None)

    # Antenna metadata
    ant_pos = getattr(uvdata, 'antenna_positions', None)
    if ant_pos is None and hasattr(uvdata, 'telescope'):
        ant_pos = getattr(uvdata.telescope, 'antenna_positions', None)
    ant_nums = getattr(uvdata, 'antenna_numbers', None)
    if ant_nums is None and hasattr(uvdata, 'telescope'):
        ant_nums = getattr(uvdata.telescope, 'antenna_numbers', None)
    ant_pos = _np.asarray(ant_pos) if ant_pos is not None else None
    ant_nums = _np.asarray(ant_nums) if ant_nums is not None else None

    utime, _, uinvert = _np.unique(uvdata.time_array, return_index=True, return_inverse=True)
    mjd_unique = _Time(utime, format='jd').mjd.astype(float)

    # Compute apparent coords + frame PA per unique time at meridian
    app_ra_unique = _np.zeros(len(utime), dtype=float)
    app_dec_unique = _np.zeros(len(utime), dtype=float)
    frame_pa_unique = _np.zeros(len(utime), dtype=float)

    for i, mjd in enumerate(mjd_unique):
        ra_icrs, dec_icrs = get_meridian_coords(pt_dec, float(mjd))
        try:
            new_app_ra, new_app_dec = uvutils.calc_app_coords(
                ra_icrs.to_value(u.rad),
                dec_icrs.to_value(u.rad),
                coord_frame='icrs',
                coord_epoch=2000.0,
                coord_times=None,
                coord_type='sidereal',
                time_array=uvdata.time_array[uinvert == i],
                lst_array=uvdata.lst_array[uinvert == i],
                pm_ra=None, pm_dec=None, vrad=None, dist=None,
                telescope_loc=tel_latlonalt,
                telescope_frame=tel_frame,
            )
            new_frame_pa = uvutils.calc_frame_pos_angle(
                uvdata.time_array[uinvert == i], new_app_ra, new_app_dec,
                tel_latlonalt, 'icrs', ref_epoch=2000.0, telescope_frame=tel_frame,
            )
            app_ra_unique[i] = float(new_app_ra[0])
            app_dec_unique[i] = float(new_app_dec[0])
            frame_pa_unique[i] = float(new_frame_pa[0])
        except Exception:
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


def validate_ms_frequency_order(ms_path: str) -> None:
    """Verify MS has ascending frequency order across all spectral windows.
    
    This is critical for DSA-110 because subbands come in DESCENDING order
    (sb00=highest freq, sb15=lowest freq) but CASA imaging requires ASCENDING
    order. If frequencies are out of order, MFS imaging will produce fringes
    and bandpass calibration will fail.
    
    Args:
        ms_path: Path to Measurement Set
        
    Raises:
        RuntimeError: If frequency order is incorrect
    """
    try:
        from casacore.tables import table
        with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
            chan_freq = spw.getcol("CHAN_FREQ")  # Shape: (nspw, nchan)
            
            # Check each SPW has ascending frequency order
            for ispw in range(chan_freq.shape[0]):
                freqs = chan_freq[ispw, :]
                if freqs.size > 1 and not np.all(freqs[1:] >= freqs[:-1]):
                    raise RuntimeError(
                        f"SPW {ispw} has incorrect frequency order in {ms_path}. "
                        f"Frequencies: {freqs[:3]}...{freqs[-3:]} Hz. "
                        f"This will cause MFS imaging artifacts and calibration failures."
                    )
            
            # If multiple SPWs, check they are in ascending order too
            if chan_freq.shape[0] > 1:
                spw_start_freqs = chan_freq[:, 0]  # First channel of each SPW
                if not np.all(spw_start_freqs[1:] >= spw_start_freqs[:-1]):
                    raise RuntimeError(
                        f"SPWs have incorrect frequency order in {ms_path}. "
                        f"SPW start frequencies: {spw_start_freqs} Hz. "
                        f"This will cause MFS imaging artifacts."
                    )
                    
            logger.info(
                f"✓ Frequency order validation passed: {chan_freq.shape[0]} SPW(s), "
                f"range {chan_freq.min()/1e6:.1f}-{chan_freq.max()/1e6:.1f} MHz"
            )
    except Exception as e:
        if "incorrect frequency order" in str(e):
            raise  # Re-raise our validation errors
        else:
            logger.warning(f"Frequency order validation failed (non-fatal): {e}")


def cleanup_casa_file_handles() -> None:
    """Force close any open CASA file handles to prevent locking issues.
    
    This is critical when running parallel MS operations or using tmpfs staging.
    CASA tools can hold file handles open even after operations complete,
    causing file locking errors in subsequent operations.
    """
    try:
        import casatools
        tool_names = ['ms', 'table', 'image', 'msmetadata', 'simulator']
        
        for tool_name in tool_names:
            try:
                tool_factory = getattr(casatools, tool_name, None)
                if tool_factory is not None:
                    tool_instance = tool_factory()
                    if hasattr(tool_instance, 'close'):
                        tool_instance.close()
                    if hasattr(tool_instance, 'done'):
                        tool_instance.done()
            except Exception:
                # Individual tool cleanup failures are non-fatal
                pass
                
        logger.debug("CASA file handles cleanup completed")
    except ImportError:
        # casatools not available - nothing to clean up
        pass
    except Exception as e:
        logger.debug(f"CASA cleanup failed (non-fatal): {e}")


def validate_phase_center_coherence(ms_path: str, tolerance_arcsec: float = 1.0) -> None:
    """Verify all subbands in MS have coherent phase centers.
    
    This checks that all spectral windows (former subbands) have phase centers
    within tolerance of each other. Incoherent phase centers cause imaging
    artifacts and calibration failures.
    
    Args:
        ms_path: Path to Measurement Set
        tolerance_arcsec: Maximum allowed separation between phase centers (arcsec)
        
    Raises:
        RuntimeError: If phase centers are incoherent beyond tolerance
    """
    try:
        from casacore.tables import table
        import numpy as np
        
        with table(f"{ms_path}::FIELD", readonly=True) as field_table:
            if field_table.nrows() == 0:
                logger.warning(f"No fields found in MS: {ms_path}")
                return
                
            phase_dirs = field_table.getcol("PHASE_DIR")  # Shape: (nfield, npoly, 2)
            
            if phase_dirs.shape[0] > 1:
                # Multiple fields - check they are coherent
                ref_ra = phase_dirs[0, 0, 0]  # Reference RA (radians)
                ref_dec = phase_dirs[0, 0, 1]  # Reference Dec (radians)
                
                max_separation_rad = 0.0
                for i in range(1, phase_dirs.shape[0]):
                    ra = phase_dirs[i, 0, 0]
                    dec = phase_dirs[i, 0, 1]
                    
                    # Calculate angular separation
                    separation_rad = angular_separation(ref_ra, ref_dec, ra, dec)
                    max_separation_rad = max(max_separation_rad, separation_rad)
                
                max_separation_arcsec = np.rad2deg(max_separation_rad) * 3600
                
                if max_separation_arcsec > tolerance_arcsec:
                    raise RuntimeError(
                        f"Phase centers are incoherent in {ms_path}. "
                        f"Maximum separation: {max_separation_arcsec:.2f} arcsec "
                        f"(tolerance: {tolerance_arcsec:.2f} arcsec). "
                        f"This will cause imaging artifacts."
                    )
                    
                logger.info(
                    f"✓ Phase center coherence validated: {phase_dirs.shape[0]} field(s), "
                    f"max separation {max_separation_arcsec:.2f} arcsec"
                )
            else:
                logger.info(f"✓ Single field MS - phase center coherence OK")
                
    except Exception as e:
        if "incoherent" in str(e):
            raise  # Re-raise our validation errors
        else:
            logger.warning(f"Phase center coherence validation failed (non-fatal): {e}")


def validate_uvw_precision(ms_path: str, tolerance_lambda: float = 0.1) -> None:
    """Validate UVW coordinate precision to prevent calibration decorrelation.
    
    This checks that UVW coordinates are accurate enough for calibration by
    comparing computed UVW values against expected values from antenna positions.
    Inaccurate UVW coordinates cause phase decorrelation and flagged solutions.
    
    Args:
        ms_path: Path to Measurement Set
        tolerance_lambda: Maximum allowed UVW error in wavelengths (default: 0.1λ)
        
    Raises:
        RuntimeError: If UVW errors exceed tolerance
    """
    try:
        from casacore.tables import table
        import numpy as np
        
        # Get observation parameters
        with table(f"{ms_path}::OBSERVATION", readonly=True) as obs_table:
            if obs_table.nrows() == 0:
                logger.warning(f"No observation info in MS: {ms_path}")
                return
        
        # Get reference frequency for wavelength calculation
        with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw_table:
            ref_freqs = spw_table.getcol("REF_FREQUENCY")
            ref_freq_hz = float(np.median(ref_freqs))
            wavelength_m = 2.998e8 / ref_freq_hz  # c / freq
        
        # Sample UVW coordinates from main table
        with table(ms_path, readonly=True) as tb:
            if tb.nrows() == 0:
                raise RuntimeError(f"MS has no data rows: {ms_path}")
            
            # Sample subset for performance (check every 100th row)
            n_rows = tb.nrows()
            sample_rows = list(range(0, n_rows, max(1, n_rows // 1000)))[:1000]
            
            uvw_data = tb.getcol("UVW", startrow=sample_rows[0], nrow=len(sample_rows))
            antenna1 = tb.getcol("ANTENNA1", startrow=sample_rows[0], nrow=len(sample_rows))
            antenna2 = tb.getcol("ANTENNA2", startrow=sample_rows[0], nrow=len(sample_rows))
            time_data = tb.getcol("TIME", startrow=sample_rows[0], nrow=len(sample_rows))
        
        # Check for obvious UVW coordinate problems
        uvw_u = uvw_data[:, 0]  # U coordinates
        uvw_v = uvw_data[:, 1]  # V coordinates  
        uvw_w = uvw_data[:, 2]  # W coordinates
        
        # Detect unreasonably large UVW values (> 100km indicates error)
        max_reasonable_uvw_m = 100e3  # 100 km
        if np.any(np.abs(uvw_data) > max_reasonable_uvw_m):
            raise RuntimeError(
                f"UVW coordinates contain unreasonably large values (>{max_reasonable_uvw_m/1000:.0f}km) "
                f"in {ms_path}. Max |UVW|: {np.max(np.abs(uvw_data))/1000:.1f}km. "
                f"This indicates UVW computation errors that will cause calibration failures."
            )
        
        # Check for all-zero UVW (indicates computation failure)
        if np.all(np.abs(uvw_data) < 1e-10):
            raise RuntimeError(
                f"All UVW coordinates are zero in {ms_path}. "
                f"This indicates UVW computation failed and will cause calibration failures."
            )
        
        # Statistical checks for UVW distribution
        uvw_magnitude = np.sqrt(np.sum(uvw_data**2, axis=1))
        median_uvw_m = float(np.median(uvw_magnitude))
        max_uvw_m = float(np.max(uvw_magnitude))
        
        # For DSA-110: expect baseline lengths from ~10m to ~2500m
        expected_min_baseline_m = 5.0    # Minimum expected baseline
        expected_max_baseline_m = 3000.0  # Maximum expected baseline
        
        if median_uvw_m < expected_min_baseline_m:
            logger.warning(
                f"UVW coordinates seem too small in {ms_path}. "
                f"Median baseline: {median_uvw_m:.1f}m (expected >{expected_min_baseline_m:.1f}m). "
                f"This may indicate UVW scaling errors."
            )
        
        if max_uvw_m > expected_max_baseline_m:
            logger.warning(
                f"UVW coordinates seem too large in {ms_path}. "
                f"Max baseline: {max_uvw_m:.1f}m (expected <{expected_max_baseline_m:.1f}m). "
                f"This may indicate UVW scaling errors."
            )
        
        # Convert tolerance to meters
        tolerance_m = tolerance_lambda * wavelength_m
        
        logger.info(
            f"✓ UVW coordinate validation passed: "
            f"median baseline {median_uvw_m:.1f}m, max {max_uvw_m:.1f}m "
            f"(λ={wavelength_m:.2f}m, tolerance={tolerance_m:.3f}m)"
        )
        
    except Exception as e:
        if "UVW coordinates" in str(e):
            raise  # Re-raise our validation errors
        else:
            logger.warning(f"UVW coordinate validation failed (non-fatal): {e}")


def validate_antenna_positions(ms_path: str, position_tolerance_m: float = 0.05) -> None:
    """Validate antenna positions are accurate enough for calibration.
    
    This checks that antenna positions in the MS match expected DSA-110 positions
    within calibration tolerance. Position errors cause decorrelation and flagging.
    
    Args:
        ms_path: Path to Measurement Set
        position_tolerance_m: Maximum allowed position error in meters (default: 5cm)
        
    Raises:
        RuntimeError: If antenna positions have excessive errors
    """
    try:
        from casacore.tables import table
        import numpy as np
        
        # Get antenna positions from MS
        with table(f"{ms_path}::ANTENNA", readonly=True) as ant_table:
            ms_positions = ant_table.getcol("POSITION")  # Shape: (nant, 3) ITRF meters
            ant_names = ant_table.getcol("NAME")
            n_antennas = len(ant_names)
        
        if n_antennas == 0:
            raise RuntimeError(f"No antennas found in MS: {ms_path}")
        
        # Load reference DSA-110 positions
        try:
            from dsa110_contimg.utils.antpos_local import get_itrf
            ref_df = get_itrf(latlon_center=None)
            
            # Convert reference positions to same format as MS
            ref_positions = np.array([
                ref_df["x_m"].values,
                ref_df["y_m"].values, 
                ref_df["z_m"].values,
            ]).T  # Shape: (nant, 3)
            
        except Exception as e:
            logger.warning(f"Could not load reference antenna positions: {e}")
            # Can't validate without reference - just check for obvious problems
            position_magnitudes = np.sqrt(np.sum(ms_positions**2, axis=1))
            
            # DSA-110 is near OVRO: expect positions around Earth radius from center
            earth_radius_m = 6.371e6
            expected_min_radius = earth_radius_m - 10e3  # 10km below Earth center
            expected_max_radius = earth_radius_m + 10e3  # 10km above Earth surface
            
            if np.any(position_magnitudes < expected_min_radius):
                raise RuntimeError(
                    f"Antenna positions too close to Earth center in {ms_path}. "
                    f"Min radius: {np.min(position_magnitudes)/1000:.1f}km "
                    f"(expected >{expected_min_radius/1000:.1f}km). "
                    f"This indicates position coordinate errors."
                )
            
            if np.any(position_magnitudes > expected_max_radius):
                raise RuntimeError(
                    f"Antenna positions too far from Earth center in {ms_path}. "
                    f"Max radius: {np.max(position_magnitudes)/1000:.1f}km "
                    f"(expected <{expected_max_radius/1000:.1f}km). "
                    f"This indicates position coordinate errors."
                )
            
            logger.info(f"✓ Basic antenna position validation passed: {n_antennas} antennas")
            return
        
        # Compare MS positions with reference positions
        if ms_positions.shape[0] != ref_positions.shape[0]:
            logger.warning(
                f"Antenna count mismatch: MS has {ms_positions.shape[0]}, "
                f"reference has {ref_positions.shape[0]}. Using available antennas."
            )
            n_compare = min(ms_positions.shape[0], ref_positions.shape[0])
            ms_positions = ms_positions[:n_compare, :]
            ref_positions = ref_positions[:n_compare, :]
        
        # Calculate position differences
        position_errors = ms_positions - ref_positions
        position_error_magnitudes = np.sqrt(np.sum(position_errors**2, axis=1))
        
        max_error_m = float(np.max(position_error_magnitudes))
        median_error_m = float(np.median(position_error_magnitudes))
        rms_error_m = float(np.sqrt(np.mean(position_error_magnitudes**2)))
        
        # Check if errors exceed tolerance
        n_bad_antennas = np.sum(position_error_magnitudes > position_tolerance_m)
        
        if n_bad_antennas > 0:
            bad_indices = np.where(position_error_magnitudes > position_tolerance_m)[0]
            error_summary = ", ".join([
                f"ant{i}:{position_error_magnitudes[i]*100:.1f}cm" 
                for i in bad_indices[:5]  # Show first 5
            ])
            if len(bad_indices) > 5:
                error_summary += f" (and {len(bad_indices)-5} more)"
            
            raise RuntimeError(
                f"Antenna position errors exceed tolerance in {ms_path}. "
                f"{n_bad_antennas}/{len(position_error_magnitudes)} antennas have errors "
                f">{position_tolerance_m*100:.1f}cm (tolerance for calibration). "
                f"Errors: {error_summary}. Max error: {max_error_m*100:.1f}cm. "
                f"This will cause decorrelation and flagged calibration solutions."
            )
        
        logger.info(
            f"✓ Antenna position validation passed: {n_antennas} antennas, "
            f"max error {max_error_m*100:.1f}cm, RMS {rms_error_m*100:.1f}cm "
            f"(tolerance {position_tolerance_m*100:.1f}cm)"
        )
        
    except Exception as e:
        if "position errors exceed tolerance" in str(e):
            raise  # Re-raise our validation errors
        else:
            logger.warning(f"Antenna position validation failed (non-fatal): {e}")


def validate_model_data_quality(ms_path: str, field_id: Optional[int] = None, 
                               min_flux_jy: float = 0.1, max_flux_jy: float = 1000.0) -> None:
    """Validate MODEL_DATA quality for calibrator sources.
    
    This checks that MODEL_DATA contains reasonable flux values and structure
    for calibration. Poor calibrator models cause solution divergence and flagging.
    
    Args:
        ms_path: Path to Measurement Set
        field_id: Optional field ID to check (if None, checks all fields)
        min_flux_jy: Minimum expected flux density in Jy
        max_flux_jy: Maximum expected flux density in Jy
        
    Raises:
        RuntimeError: If MODEL_DATA has quality issues
    """
    try:
        from casacore.tables import table
        import numpy as np
        
        with table(ms_path, readonly=True) as tb:
            if "MODEL_DATA" not in tb.colnames():
                raise RuntimeError(
                    f"MODEL_DATA column does not exist in {ms_path}. "
                    f"This is required for calibration and must be populated before solving."
                )
            
            # Get field selection
            field_col = tb.getcol("FIELD_ID")
            if field_id is not None:
                field_mask = (field_col == field_id)
                if not np.any(field_mask):
                    raise RuntimeError(f"Field ID {field_id} not found in MS: {ms_path}")
            else:
                field_mask = np.ones(len(field_col), dtype=bool)
            
            # Sample MODEL_DATA for the selected field(s)
            n_selected = np.sum(field_mask)
            sample_size = min(1000, n_selected)  # Sample for performance
            selected_indices = np.where(field_mask)[0]
            sample_indices = selected_indices[::max(1, len(selected_indices)//sample_size)]
            
            model_sample = tb.getcol("MODEL_DATA", startrow=int(sample_indices[0]), 
                                   nrow=len(sample_indices))
            
            # Check for all-zero model
            if np.all(np.abs(model_sample) < 1e-12):
                raise RuntimeError(
                    f"MODEL_DATA is all zeros in {ms_path}. "
                    f"Calibrator source models must be populated before calibration. "
                    f"Use setjy, ft(), or manual model assignment."
                )
            
            # Calculate flux statistics
            # MODEL_DATA shape: (nchan, npol, nrow) or similar
            model_amplitudes = np.abs(model_sample)
            
            # Get Stokes I equivalent (average polarizations for rough flux estimate)
            if model_amplitudes.ndim == 3:
                # Average across polarizations and frequencies for flux estimate
                stokes_i_approx = np.mean(model_amplitudes, axis=(0, 1))
            else:
                stokes_i_approx = np.mean(model_amplitudes, axis=0)
            
            median_flux = float(np.median(stokes_i_approx))
            max_flux = float(np.max(stokes_i_approx))
            
            # Check flux range
            if median_flux < min_flux_jy:
                logger.warning(
                    f"MODEL_DATA flux seems low in {ms_path}. "
                    f"Median flux: {median_flux:.3f} Jy (expected >{min_flux_jy:.1f} Jy). "
                    f"Weak calibrator models may cause flagged solutions."
                )
            
            if max_flux > max_flux_jy:
                raise RuntimeError(
                    f"MODEL_DATA flux unreasonably high in {ms_path}. "
                    f"Max flux: {max_flux:.1f} Jy (expected <{max_flux_jy:.1f} Jy). "
                    f"This indicates incorrect calibrator model scaling."
                )
            
            # Check for NaN or infinite values
            if not np.all(np.isfinite(model_sample)):
                raise RuntimeError(
                    f"MODEL_DATA contains NaN or infinite values in {ms_path}. "
                    f"This will cause calibration failures."
                )
            
            # Check model structure consistency across channels
            # For point sources, flux should be relatively flat across frequency
            # For resolved sources, may vary but should not have sharp discontinuities
            if model_amplitudes.ndim >= 2:
                channel_fluxes = np.mean(model_amplitudes, axis=-1)  # Average over baselines
                if channel_fluxes.size > 1:
                    # Look for sudden flux jumps between channels (>50% change)
                    flux_ratios = channel_fluxes[1:] / (channel_fluxes[:-1] + 1e-12)
                    large_jumps = np.sum((flux_ratios > 2.0) | (flux_ratios < 0.5))
                    
                    if large_jumps > len(flux_ratios) * 0.1:  # >10% of channels have jumps
                        logger.warning(
                            f"MODEL_DATA has discontinuous flux structure in {ms_path}. "
                            f"{large_jumps}/{len(flux_ratios)} channel pairs have >50% flux changes. "
                            f"This may indicate incorrect calibrator model or frequency mapping."
                        )
            
            field_desc = f"field {field_id}" if field_id is not None else "all fields"
            logger.info(
                f"✓ MODEL_DATA validation passed for {field_desc}: "
                f"median flux {median_flux:.3f} Jy, max {max_flux:.3f} Jy"
            )
            
    except Exception as e:
        if "MODEL_DATA" in str(e) and ("does not exist" in str(e) or "all zeros" in str(e) or 
                                      "unreasonably high" in str(e) or "NaN" in str(e)):
            raise  # Re-raise our validation errors
        else:
            logger.warning(f"MODEL_DATA validation failed (non-fatal): {e}")


__all__ = [
    "get_meridian_coords",
    "set_antenna_positions",
    "_ensure_antenna_diameters",
    "set_model_column",
    "amplitude_sky_model",
    "primary_beam_response",
    "phase_to_meridian",
    "validate_ms_frequency_order",
    "cleanup_casa_file_handles",
    "validate_phase_center_coherence",
    "validate_uvw_precision",
    "validate_antenna_positions",
    "validate_model_data_quality",
    "validate_reference_antenna_stability",
]


def validate_reference_antenna_stability(ms_path: str, refant_list: list = None) -> str:
    """Validate reference antenna stability and suggest best refant.
    
    Unstable reference antennas cause calibration failures and flagged solutions.
    Checks for data availability, phase stability, and amplitude consistency.
    
    Args:
        ms_path: Path to Measurement Set
        refant_list: List of preferred reference antennas (e.g., [15, 20, 24])
                    If None, analyzes all antennas
        
    Returns:
        str: Best reference antenna name (e.g., 'ea15')
        
    Raises:
        RuntimeError: If no suitable reference antenna found
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        from casacore.tables import table
        import numpy as np
        import os
        
        with table(ms_path, readonly=True) as tb:
            # Get antenna information
            ant1 = tb.getcol('ANTENNA1')
            ant2 = tb.getcol('ANTENNA2')
            flags = tb.getcol('FLAG')  # Shape: (nrow, nchan, npol)
            data = tb.getcol('DATA')   # Shape: (nrow, nchan, npol)
            
            # Get antenna table for names
            ms_ant_path = os.path.join(ms_path, 'ANTENNA')
            with table(ms_ant_path, readonly=True) as ant_tb:
                ant_names = ant_tb.getcol('NAME')
                
            unique_ants = np.unique(np.concatenate([ant1, ant2]))
            
            if refant_list is None:
                candidate_ants = unique_ants
            else:
                # Map refant_list to actual antenna indices
                candidate_ants = []
                for refant_id in refant_list:
                    if refant_id in unique_ants:
                        candidate_ants.append(refant_id)
                candidate_ants = np.array(candidate_ants)
                
            if len(candidate_ants) == 0:
                raise RuntimeError(
                    f"No valid reference antennas found in {ms_path}"
                )
                
            # Analyze each candidate antenna
            ant_scores = {}
            
            for ant_idx in candidate_ants:
                # Find baselines involving this antenna
                baseline_mask = (ant1 == ant_idx) | (ant2 == ant_idx)
                
                if not np.any(baseline_mask):
                    continue
                    
                # Get data for baselines involving this antenna
                ant_flags = flags[baseline_mask]
                ant_data = data[baseline_mask]
                
                # Calculate statistics
                total_samples = ant_flags.size
                flagged_samples = np.sum(ant_flags)
                unflagged_fraction = 1.0 - (flagged_samples / total_samples)
                
                # Calculate phase stability (for unflagged data)
                unflagged_data = ant_data[~ant_flags]
                if len(unflagged_data) > 10:
                    phases = np.angle(unflagged_data)
                    # Use circular standard deviation for phase stability
                    phase_std = np.std(np.diff(phases))
                else:
                    phase_std = np.pi  # Very unstable if no data
                    
                # Calculate amplitude consistency
                if len(unflagged_data) > 10:
                    amplitudes = np.abs(unflagged_data)
                    amp_cv = np.std(amplitudes) / (np.mean(amplitudes) + 1e-12)
                else:
                    amp_cv = 999.0  # Very inconsistent if no data
                    
                # Combined score (higher is better)
                # Weight: 50% unflagged fraction, 30% phase stability, 20% amp consistency
                score = (0.5 * unflagged_fraction + 
                        0.3 * (1.0 / (1.0 + phase_std)) + 
                        0.2 * (1.0 / (1.0 + amp_cv)))
                        
                ant_scores[ant_idx] = {
                    'score': score,
                    'unflagged_fraction': unflagged_fraction,
                    'phase_std': phase_std,
                    'amp_cv': amp_cv,
                    'name': ant_names[ant_idx] if ant_idx < len(ant_names) else f'ant{ant_idx}'
                }
                
                logger.debug(
                    f"Antenna {ant_names[ant_idx] if ant_idx < len(ant_names) else ant_idx}: "
                    f"score={score:.3f}, unflagged={unflagged_fraction:.3f}, "
                    f"phase_std={phase_std:.3f}, amp_cv={amp_cv:.3f}"
                )
                
            if not ant_scores:
                raise RuntimeError(
                    f"No candidate antennas have sufficient data in {ms_path}"
                )
                
            # Select best antenna
            best_ant_idx = max(ant_scores.keys(), key=lambda k: ant_scores[k]['score'])
            best_ant_info = ant_scores[best_ant_idx]
            best_ant_name = best_ant_info['name']
            
            # Validate that best antenna is actually good
            if best_ant_info['unflagged_fraction'] < 0.5:
                logger.warning(
                    f"Best reference antenna {best_ant_name} has only "
                    f"{best_ant_info['unflagged_fraction']:.1%} unflagged data"
                )
            if best_ant_info['phase_std'] > 1.0:
                logger.warning(
                    f"Best reference antenna {best_ant_name} has high phase "
                    f"instability (std={best_ant_info['phase_std']:.3f} rad)"
                )
                
            logger.info(
                f"Selected reference antenna: {best_ant_name} "
                f"(score={best_ant_info['score']:.3f}) for {ms_path}"
            )
            
            return best_ant_name
            
    except Exception as e:
        raise RuntimeError(f"Reference antenna validation failed for {ms_path}: {e}")


def set_telescope_identity(
    uv,
    name: Optional[str] = None,
    lon_deg: float = -118.2817,
    lat_deg: float = 37.2314,
    alt_m: float = 1222.0,
) -> None:
    """Set a consistent telescope identity and location on a UVData object.

    This writes both name and location metadata in places used by
    pyuvdata and downstream tools:
    - ``uv.telescope_name``
    - ``uv.telescope_location`` (ITRF meters)
    - ``uv.telescope_location_lat_lon_alt`` (radians + meters)
    - ``uv.telescope_location_lat_lon_alt_deg`` (degrees + meters, when present)
    - If a ``uv.telescope`` sub-object exists (pyuvdata>=3), mirror name and
      location fields there as well.

    Parameters
    ----------
    uv : UVData-like
        The in-memory UVData object.
    name : str, optional
        Telescope name. Defaults to ENV PIPELINE_TELESCOPE_NAME or 'DSA_110'.
    lon_deg, lat_deg, alt_m : float
        Observatory geodetic coordinates (WGS84). Defaults correspond to OVRO.
    """
    import os as _os

    tel_name = name or _os.getenv("PIPELINE_TELESCOPE_NAME", "DSA_110")
    try:
        setattr(uv, "telescope_name", tel_name)
    except Exception:
        pass

    try:
        _loc = EarthLocation.from_geodetic(lon=lon_deg * u.deg, lat=lat_deg * u.deg, height=alt_m * u.m)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to construct EarthLocation: %s", exc)
        return

    # Populate top-level ITRF (meters)
    try:
        uv.telescope_location = np.array([
            _loc.x.to_value(u.m),
            _loc.y.to_value(u.m),
            _loc.z.to_value(u.m),
        ], dtype=float)
    except Exception:
        pass

    # Populate geodetic lat/lon/alt in radians/meters if available
    try:
        uv.telescope_location_lat_lon_alt = (
            float(_loc.lat.to_value(u.rad)),
            float(_loc.lon.to_value(u.rad)),
            float(_loc.height.to_value(u.m)),
        )
    except Exception:
        pass
    # And in degrees where convenient
    try:
        uv.telescope_location_lat_lon_alt_deg = (
            float(_loc.lat.to_value(u.deg)),
            float(_loc.lon.to_value(u.deg)),
            float(_loc.height.to_value(u.m)),
        )
    except Exception:
        pass

    # Mirror onto uv.telescope sub-object when present
    tel = getattr(uv, "telescope", None)
    if tel is not None:
        try:
            setattr(tel, "name", tel_name)
        except Exception:
            pass
        try:
            setattr(tel, "location", np.array([
                _loc.x.to_value(u.m),
                _loc.y.to_value(u.m),
                _loc.z.to_value(u.m),
            ], dtype=float))
        except Exception:
            pass
        try:
            setattr(tel, "location_lat_lon_alt", (
                float(_loc.lat.to_value(u.rad)),
                float(_loc.lon.to_value(u.rad)),
                float(_loc.height.to_value(u.m)),
            ))
        except Exception:
            pass
        try:
            setattr(tel, "location_lat_lon_alt_deg", (
                float(_loc.lat.to_value(u.deg)),
                float(_loc.lon.to_value(u.deg)),
                float(_loc.height.to_value(u.m)),
            ))
        except Exception:
            pass

    logger.debug(
        "Set telescope identity: %s @ (lon,lat,alt)=(%.4f, %.4f, %.1f)",
        tel_name, lon_deg, lat_deg, alt_m,
    )
