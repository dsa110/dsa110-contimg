"""
Create a measurement set from a uvh5 file.

Adapted from dsacalib.uvh5_to_ms
"""
import shutil
import os

import numpy as np
import scipy  # noqa
import astropy.units as u
import astropy.constants as c
from astropy.time import Time
from casatasks import importuvfits
from casacore.tables import addImagingColumns, table
from pyuvdata import UVData

# Import from our local utilities
from ...utils.antpos import get_itrf
from ...utils import logging as dsl
from ...utils.fringestopping import calc_uvw_blt, calc_uvw_interpolate, amplitude_sky_model
from ...utils import constants as ct
from ...utils.coordinates import Direction, generate_calibrator_source


def uvh5_to_ms(
        fname_or_uvdata, msname, refmjd, ra=None, dec=None, dt=None, antenna_list=None,
        flux=None, fringestop=True, logger=None
):
    """
    Converts a uvh5 file or UVData object to a CASA measurement set.

    Parameters
    ----------
    fname_or_uvdata : str or UVData
        Either the full path to the uvh5 data file, or a UVData object directly.
    msname : str
        The name of the ms to write. Data will be written to `msname`.ms
    refmjd : float
        The mjd used in the fringestopper.
    ra : astropy quantity, optional
        The RA at which to phase the data. If None, will phase at the meridian
        of the center of the uvh5 file.
    dec : astropy quantity, optional
        The DEC at which to phase the data. If None, will phase at the pointing
        declination.
    dt : astropy quantity, optional
        Duration of data to extract. Default is to extract the entire file.
    antenna_list : list, optional
        Antennas for which to extract visibilities from the uvh5 file. Default
        is to extract all visibilities in the uvh5 file.
    flux : float, optional
        The flux of the calibrator in Jy. If included, will write a model of
        the primary beam response to the calibrator source to the model column
        of the ms. If not included, a model of a constant response over
        frequency and time will be written instead of the primary beam model.
    fringestop : bool, optional
        Whether to apply fringestopping. Default is True.
    logger : dsautils.dsa_syslog.DsaSyslogger() instance, optional
        Logger to write messages too. If None, messages are printed.
    """
    print(f"\n{'='*80}")
    print(f"Starting HDF5 to MS conversion")
    if isinstance(fname_or_uvdata, str):
        print(f"Input file: {fname_or_uvdata}")
    else:
        print(f"Input: UVData object")
    print(f"Output MS: {msname}.ms")
    print(f"{'='*80}\n")
    
    # Handle both file paths and UVData objects
    if isinstance(fname_or_uvdata, str):
        print("[Step 1/5] Loading uvh5 file...")
        uvdata, pt_dec, ra, dec = load_uvh5_file(fname_or_uvdata, antenna_list, dt, ra, dec)
        print(f"  Loaded data shape: {uvdata.data_array.shape}")
        print(f"  Number of baselines: {uvdata.Nbls}")
        print(f"  Number of times: {uvdata.Ntimes}")
        print(f"  Number of frequencies: {uvdata.Nfreqs}")
        print(f"  Phase center: RA={ra}, Dec={dec}")
    else:
        # fname_or_uvdata is already a UVData object
        print("[Step 1/5] Using provided UVData object...")
        uvdata = fname_or_uvdata
        print(f"  Data shape: {uvdata.data_array.shape}")
        print(f"  Number of baselines: {uvdata.Nbls}")
        print(f"  Number of times: {uvdata.Ntimes}")
        print(f"  Number of frequencies: {uvdata.Nfreqs}")
        
        # Get phase center information
        pt_dec = uvdata.extra_keywords['phase_center_dec'] * u.rad
        if ra is None or dec is None:
            # Get pointing information from UVData
            phase_time = Time(np.mean(uvdata.time_array), format='jd')
            pointing = Direction(
                'HADEC',
                0.,
                pt_dec.to_value(u.rad),
                phase_time.mjd)
            ra, dec = pointing.J2000()
        print(f"  Phase center: RA={ra}, Dec={dec}")

    print("\n[Step 2/5] Setting antenna positions...")
    antenna_positions = set_antenna_positions(uvdata, logger)
    print(f"  Set positions for {antenna_positions.shape[0]} antennas")

    print("\n[Step 3/5] Phasing visibilities...")
    # Use interpolated UVW calculation for much faster performance
    # This calculates UVW only at unique times (24) instead of all baseline-times (111744)
    import time as time_module
    start_phase = time_module.time()
    phase_visibilities(uvdata, ra, dec, fringestop, interpolate_uvws=True, refmjd=refmjd)
    elapsed_phase = time_module.time() - start_phase
    print(f"  Phasing complete in {elapsed_phase:.2f} seconds")

    print("\n[Step 4/5] Fixing frequency axis...")
    fix_descending_missing_freqs(uvdata)
    print("  Frequency axis fixed")

    print("\n[Step 5/5] Writing to measurement set...")
    import time as time_module
    start_ms = time_module.time()
    write_UV_to_ms_direct(uvdata, msname, antenna_positions, ra, dec)
    elapsed_ms = time_module.time() - start_ms
    print(f"  MS written in {elapsed_ms:.2f} seconds")

    print("\n[Final] Setting model column...")
    set_ms_model_column(msname, uvdata, pt_dec, ra, dec, flux)
    print("  Model column set")
    
    print(f"\n{'='*80}")
    print(f"Conversion complete: {msname}.ms")
    print(f"{'='*80}\n")


def phase_visibilities(
        uvdata, phase_ra, phase_dec, fringestop=True, interpolate_uvws=False, refmjd=None
):
    """Phase a UVData instance.

    If fringestop is False, then no phasing is done,
    but the phase centre is set to the meridian at the midpoint of the observation,
    and the uvdata object is modified to indicate that it is phased.
    """
    print("  Getting baseline lengths...")
    blen = get_blen(uvdata)
    print(f"    Calculated {blen.shape[0]} baselines")
    
    print("  Computing wavelengths...")
    lamb = c.c / (uvdata.freq_array * u.Hz)
    time = Time(uvdata.time_array, format='jd')

    if refmjd is None:
        refmjd = np.mean(time.mjd)
    print(f"    Reference MJD: {refmjd}")

    pt_dec = uvdata.extra_keywords['phase_center_dec'] * u.rad
    print("  Calculating UVW coordinates at meridian...")
    uvw_m = calc_uvw_blt(
        blen, np.tile(refmjd, (uvdata.Nbls)), 'HADEC',
        np.zeros(uvdata.Nbls) * u.rad, np.tile(pt_dec, (uvdata.Nbls)))
    print(f"    UVW_m shape: {uvw_m.shape}")

    if fringestop:
        print("  Fringestopping is enabled")
        # Calculate uvw coordinates
        if interpolate_uvws:
            print("    Calculating interpolated UVW coordinates...")
            uvw = calc_uvw_interpolate(
                blen, time[::uvdata.Nbls], 'RADEC', phase_ra.to(u.rad), phase_dec.to(u.rad))
            uvw = uvw.reshape(-1, 3)
        else:
            print("    Calculating UVW coordinates (non-interpolated)...")
            blen = np.tile(blen[np.newaxis, :, :], (uvdata.Ntimes, 1, 1)).reshape(-1, 3)
            uvw = calc_uvw_blt(
                blen, time.mjd, 'RADEC', phase_ra.to(u.rad), phase_dec.to(u.rad)
            )
        print(f"    UVW shape: {uvw.shape}")

        # Fringestop and phase
        # If needed, this could be done in chunks (in time) to save on memory
        print("    Generating antenna-based phase model...")
        import time as time_module
        start_pm = time_module.time()
        phase_model = generate_phase_model_antbased(
            uvw, uvw_m, uvdata.Nbls, uvdata.Ntimes, lamb, uvdata.ant_1_array[:uvdata.Nbls],
            uvdata.ant_2_array[:uvdata.Nbls])
        elapsed_pm = time_module.time() - start_pm
        print(f"    Phase model generated in {elapsed_pm:.2f} seconds, shape: {phase_model.shape}")
        print("    Applying phase model to data...")
        print(f"      Data array shape: {uvdata.data_array.shape}, dtype: {uvdata.data_array.dtype}")
        print(f"      Phase model shape: {phase_model.shape}, dtype: {phase_model.dtype}")
        import time as time_module
        start_div = time_module.time()
        print("      Starting division operation...")
        # phase_model is now (nblt, nfreq), data_array is (nblt, nfreq, npol)
        # Broadcasting will automatically expand phase_model across the polarization axis
        uvdata.data_array = uvdata.data_array / phase_model[..., np.newaxis]
        elapsed_div = time_module.time() - start_div
        print(f"    Phase model applied successfully in {elapsed_div:.2f} seconds")

    else:
        print("  Fringestopping is disabled, using J2000 coordinates")
        uvw = calc_uvw_blt(
            blen, np.tile(np.mean(time.mjd), (uvdata.Nbls)), 'J2000',
            np.tile(phase_ra, (uvdata.Nbls)), np.tile(phase_dec, (uvdata.Nbls)))
        phase_model = generate_phase_model_antbased(
            uvw, uvw_m, uvdata.Nbls, 1, lamb, uvdata.ant_1_array[:uvdata.Nbls],
            uvdata.ant_2_array[:uvdata.Nbls])
        uvdata.data_array = uvdata.data_array / phase_model[..., np.newaxis]
        uvw = np.tile(uvw.reshape((1, uvdata.Nbls, 3)),
                      (1, uvdata.Ntimes, 1)).reshape((uvdata.Nblts, 3))

    uvdata.uvw_array = uvw
    uvdata.phase_type = 'phased'
    uvdata.phase_center_dec = phase_dec.to_value(u.rad)
    uvdata.phase_center_ra = phase_ra.to_value(u.rad)
    uvdata.phase_center_epoch = 2000.
    uvdata.phase_center_frame = 'icrs'
    try:
        uvdata._set_app_coords_helper()
    except AttributeError:
        pass


def load_uvh5_file(
        fname: str,
        antenna_list: list = None,
        dt: u.Quantity = None,
        phase_ra: u.Quantity = None,
        phase_dec: u.Quantity = None,
        phase_time: Time = None
) -> UVData:
    """Load specific antennas and times for a uvh5 file.

    phase_ra and phase_dec are set here, but the uvh5 file is not phased.
    """
    if (
            (phase_ra is None and phase_dec is not None)
            or (phase_ra is not None and phase_dec is None)):
        raise RuntimeError(
            "Only one of phase_ra and phase_dec defined.  Please define both or neither."
        )
    if phase_time is not None and phase_ra is not None:
        raise RuntimeError(
            "Please specific only one of phase_time and phasing direction (phase_ra + phase_dec)"
        )

    uvdata = UVData()

    # Read in the data
    print(f"  Reading HDF5 file: {fname}")
    read_kwargs = {
        'file_type': 'uvh5',
        'check_extra': False,
        'run_check': False,
        'run_check_acceptability': False,
        'strict_uvw_antpos_check': False,
        'fix_old_proj': False,
        'fix_use_ant_pos': False
    }
    
    if antenna_list is not None:
        read_kwargs['antenna_names'] = antenna_list
        print(f"    Filtering to {len(antenna_list)} antennas")
    
    uvdata.read(fname, **read_kwargs)
    print(f"  Read complete: {uvdata.Nblts} baseline-times, {uvdata.Nfreqs} channels")
    
    # Fix data types to satisfy pyuvdata requirements
    # Convert float32 to float64 for uvw_array
    if hasattr(uvdata, 'uvw_array') and uvdata.uvw_array is not None:
        if uvdata.uvw_array.dtype == np.float32:
            uvdata.uvw_array = uvdata.uvw_array.astype(np.float64)
    
    # Convert float32 to float64 for integration_time if needed
    if hasattr(uvdata, 'integration_time') and uvdata.integration_time is not None:
        if uvdata.integration_time.dtype == np.float32:
            uvdata.integration_time = uvdata.integration_time.astype(np.float64)

    pt_dec = uvdata.extra_keywords['phase_center_dec'] * u.rad

    # Get pointing information
    if phase_ra is None:
        if phase_time is None:
            phase_time = Time(np.mean(uvdata.time_array), format='jd')
        pointing = Direction(
            'HADEC',
            0.,
            pt_dec.to_value(u.rad),
            phase_time.mjd)

        phase_ra, phase_dec = pointing.J2000()
        # J2000() already returns Quantities with units, so don't multiply again

    if dt is not None:
        extract_times(uvdata, phase_ra, dt)

    return uvdata, pt_dec, phase_ra, phase_dec


def extract_times(uvdata, ra, dt):
    """Extracts data from specified times from an already open UVData instance.

    This is an alternative to opening the file with the times specified using
    pyuvdata.UVData.open().

    Parameters
    ----------
    UV : pyuvdata.UVData() instance
        The UVData instance from which to extract data. Modified in-place.
    ra : float
        The ra of the source around which to extract data, in radians.
    dt : astropy quantity
        The amount of data to extract, units seconds or equivalent.
    """
    lst_min = (
        ra - (dt * 2 * np.pi * u.rad / (ct.SECONDS_PER_SIDEREAL_DAY * u.s)) / 2
    ).to_value(u.rad) % (2 * np.pi)
    lst_max = (
        ra + (dt * 2 * np.pi * u.rad / (ct.SECONDS_PER_SIDEREAL_DAY * u.s)) / 2
    ).to_value(u.rad) % (2 * np.pi)
    if lst_min < lst_max:
        idx_to_extract = np.where(
            (uvdata.lst_array >= lst_min) & (uvdata.lst_array <= lst_max)
        )[0]
    else:
        idx_to_extract = np.where(
            (uvdata.lst_array >= lst_min) | (uvdata.lst_array <= lst_max)
        )[0]
    if len(idx_to_extract) == 0:
        raise ValueError(
            "No times in uvh5 file match requested timespan "
            f"with duration {dt} centered at RA {ra}."
        )
    idxmin = min(idx_to_extract)
    idxmax = max(idx_to_extract) + 1
    assert (idxmax - idxmin) % uvdata.Nbls == 0

    uvdata.uvw_array = uvdata.uvw_array[idxmin:idxmax, ...]
    uvdata.data_array = uvdata.data_array[idxmin:idxmax, ...]
    uvdata.time_array = uvdata.time_array[idxmin:idxmax, ...]
    uvdata.lst_array = uvdata.lst_array[idxmin:idxmax, ...]
    uvdata.nsample_array = uvdata.nsample_array[idxmin:idxmax, ...]
    uvdata.flag_array = uvdata.flag_array[idxmin:idxmax, ...]
    uvdata.ant_1_array = uvdata.ant_1_array[idxmin:idxmax, ...]
    uvdata.ant_2_array = uvdata.ant_2_array[idxmin:idxmax, ...]
    uvdata.baseline_array = uvdata.baseline_array[idxmin:idxmax, ...]
    uvdata.integration_time = uvdata.integration_time[idxmin:idxmax, ...]
    uvdata.Nblts = int(idxmax - idxmin)
    assert uvdata.data_array.shape[0] == uvdata.Nblts
    uvdata.Ntimes = uvdata.Nblts // uvdata.Nbls


def set_antenna_positions(uvdata: UVData, logger: dsl.DsaSyslogger = None) -> np.ndarray:
    """Set and return the antenna positions.

    This should already be done by the writer but for some reason they
    are being converted to ICRS, so we set them using antpos here.
    """
    df_itrf = get_itrf(
        latlon_center=(ct.OVRO_LAT * u.rad, ct.OVRO_LON * u.rad, ct.OVRO_ALT * u.m)
    )
    
    # Handle different possible attribute names for antenna_positions
    # In newer pyuvdata versions, these are under telescope object
    if hasattr(uvdata, 'telescope') and hasattr(uvdata.telescope, 'antenna_positions'):
        ant_pos = uvdata.telescope.antenna_positions
        tel_location = uvdata.telescope.location
    elif hasattr(uvdata, 'antenna_positions'):
        ant_pos = uvdata.antenna_positions
        tel_location = uvdata.telescope_location
    elif hasattr(uvdata, '_antenna_positions'):
        ant_pos = uvdata._antenna_positions
        tel_location = uvdata.telescope_location
    else:
        raise AttributeError("UVData object has no antenna_positions attribute")
    
    # Ensure tel_location is a plain numpy array (handle astropy Quantity and structured arrays)
    if hasattr(tel_location, 'value'):
        tel_location = tel_location.value
    tel_location = np.asarray(tel_location)
    
    # Handle structured arrays (newer pyuvdata uses EarthLocation with xyz structured array)
    if tel_location.dtype.names is not None:
        # It's a structured array, extract x, y, z fields
        tel_location = np.array([tel_location['x'], tel_location['y'], tel_location['z']])
    
    if len(df_itrf['x_m']) != ant_pos.shape[0]:
        message = 'Mismatch between antennas in current environment ' +\
            f'({len(df_itrf["x_m"])}) and correlator environment ' +\
            f'({ant_pos.shape[0]})'
        if logger is not None:
            logger.info(message)
        else:
            print(message)
    ant_pos[:len(df_itrf['x_m'])] = np.array([
        df_itrf['x_m'],
        df_itrf['y_m'],
        df_itrf['z_m']
    ]).T - tel_location
    antenna_positions = ant_pos + tel_location
    return antenna_positions


def get_blen(uvdata: "UVData") -> "np.ndarray":
    """Calculate baseline lenghts using antenna positions in the UVData file."""
    # Handle different pyuvdata versions
    if hasattr(uvdata, 'telescope') and hasattr(uvdata.telescope, 'antenna_positions'):
        ant_pos = uvdata.telescope.antenna_positions
    elif hasattr(uvdata, 'antenna_positions'):
        ant_pos = uvdata.antenna_positions
    else:
        ant_pos = uvdata._antenna_positions
    
    blen = np.zeros((uvdata.Nbls, 3))
    for i, ant1 in enumerate(uvdata.ant_1_array[:uvdata.Nbls]):
        ant2 = uvdata.ant_2_array[i]
        blen[i, ...] = ant_pos[ant2, :] - ant_pos[ant1, :]
    return blen


def fix_descending_missing_freqs(uvdata: "UVData") -> None:
    """Flip descending freq arrays, and fills in missing channels."""
    # Look for missing channels
    freq = uvdata.freq_array.squeeze()
    # The channels may have been reordered by pyuvdata so check that the
    # parameter uvdata.channel_width makes sense now.
    ascending = np.median(np.diff(freq)) > 0
    if ascending:
        assert np.all(np.diff(freq) > 0)
    else:
        assert np.all(np.diff(freq) < 0)
        # Handle both 1D and 2D freq_array for different pyuvdata versions
        if uvdata.freq_array.ndim == 1:
            uvdata.freq_array = uvdata.freq_array[::-1]
            # data_array is (nblt, nfreq, npol) in newer versions
            uvdata.data_array = uvdata.data_array[:, ::-1, :]
        else:
            uvdata.freq_array = uvdata.freq_array[:, ::-1]
            # data_array is (nblt, nspw, nfreq, npol) in older versions
            uvdata.data_array = uvdata.data_array[:, :, ::-1, :]
        freq = uvdata.freq_array.squeeze()

    # TODO: Need to update this for missing on either side as well
    if np.isscalar(uvdata.channel_width):
        uvdata.channel_width = np.full((uvdata.Nspws, uvdata.Nfreqs), float(np.abs(uvdata.channel_width)))
    else:
        uvdata.channel_width = np.abs(uvdata.channel_width)
        if uvdata.channel_width.ndim == 1:
            uvdata.channel_width = np.broadcast_to(uvdata.channel_width[np.newaxis, :], (uvdata.Nspws, uvdata.Nfreqs))
        elif uvdata.channel_width.shape[-1] != uvdata.Nfreqs:
            uvdata.channel_width = np.broadcast_to(uvdata.channel_width[..., :1], (uvdata.Nspws, uvdata.Nfreqs))
    # Are there missing channels?
    # Note: np.diff reduces array size by 1, so we need to handle scalar or array channel_width
    if np.isscalar(uvdata.channel_width) or uvdata.channel_width.size == 1:
        channel_width_val = float(np.atleast_1d(uvdata.channel_width)[0])
    else:
        # Use the first value if it's an array
        channel_width_val = float(uvdata.channel_width[0])
    
    if not np.all(np.abs(np.diff(freq)) - channel_width_val < 1e-5):
        # There are missing channels!
        nfreq = int(np.rint(np.abs(freq[-1] - freq[0]) / channel_width_val + 1))
        freq_out = freq[0] + np.arange(nfreq) * channel_width_val
        existing_idxs = np.rint((freq - freq[0]) / channel_width_val).astype(int)
        
        # Handle different data array shapes for different pyuvdata versions
        if uvdata.data_array.ndim == 3:
            # Newer pyuvdata: (nblt, nfreq, npol)
            data_out = np.zeros((uvdata.Nblts, nfreq, uvdata.Npols),
                                dtype=uvdata.data_array.dtype)
            nsample_out = np.zeros((uvdata.Nblts, nfreq, uvdata.Npols),
                                   dtype=uvdata.nsample_array.dtype)
            flag_out = np.zeros((uvdata.Nblts, nfreq, uvdata.Npols),
                                dtype=uvdata.flag_array.dtype)
            data_out[:, existing_idxs, :] = uvdata.data_array
            nsample_out[:, existing_idxs, :] = uvdata.nsample_array
            flag_out[:, existing_idxs, :] = uvdata.flag_array
            uvdata.freq_array = freq_out[np.newaxis, :]
        else:
            # Older pyuvdata: (nblt, nspw, nfreq, npol)
            data_out = np.zeros((uvdata.Nblts, uvdata.Nspws, nfreq, uvdata.Npols),
                                dtype=uvdata.data_array.dtype)
            nsample_out = np.zeros((uvdata.Nblts, uvdata.Nspws, nfreq, uvdata.Npols),
                                   dtype=uvdata.nsample_array.dtype)
            flag_out = np.zeros((uvdata.Nblts, uvdata.Nspws, nfreq, uvdata.Npols),
                                dtype=uvdata.flag_array.dtype)
            data_out[:, :, existing_idxs, :] = uvdata.data_array
            nsample_out[:, :, existing_idxs, :] = uvdata.nsample_array
            flag_out[:, :, existing_idxs, :] = uvdata.flag_array
            uvdata.freq_array = freq_out[np.newaxis, :]
        
        # Now write everything
        uvdata.Nfreqs = nfreq
        uvdata.data_array = data_out
        uvdata.nsample_array = nsample_out
        uvdata.flag_array = flag_out


def write_UV_to_ms_direct_OLD(uvdata: "UVData", msname: "str", antenna_positions: "np.ndarray", 
                          phase_ra: u.Quantity, phase_dec: u.Quantity) -> None:
    """Write a UVData object to MS using CASA simulator and MS tools directly.
    
    DEPRECATED: This method has performance issues due to shape mismatches.
    Use write_UV_to_ms_direct() instead.
    
    This bypasses UVFITS entirely, avoiding performance issues with large arrays (>20 antennas).
    Based on the approach in dsacalib.ms_io.convert_to_ms().
    
    Parameters
    ----------
    uvdata : UVData
        The visibility data to write
    msname : str
        Output MS name (without .ms extension)
    antenna_positions : np.ndarray
        ITRF antenna positions, shape (nants, 3)
    phase_ra : astropy.units.Quantity
        Phase center RA
    phase_dec : astropy.units.Quantity
        Phase center Dec
    """
    import time
    import casatools as cc
    
    start_time = time.time()
    print("  Writing MS directly using CASA simulator and MS tools...")
    print(f"  (Bypassing UVFITS for {uvdata.Nants_telescope} antenna array)")
    
    # Remove existing MS if present
    if os.path.exists(f'{msname}.ms'):
        shutil.rmtree(f'{msname}.ms')
    
    # Get CASA tools
    me = cc.measures()
    qa = cc.quanta()
    sm = cc.simulator()
    
    # Observatory parameters
    tname = "OVRO_MMA"
    obs = "OVRO_MMA"
    diam = 4.65  # DSA-110 dish diameter in meters
    mount = "alt-az"
    pos_obs = me.observatory(obs)
    
    # Get antenna info - need to handle different pyuvdata versions
    if hasattr(uvdata, 'telescope') and hasattr(uvdata.telescope, 'antenna_numbers'):
        ant_nums = uvdata.telescope.antenna_numbers
        ant_names = uvdata.telescope.antenna_names
    else:
        ant_nums = uvdata.antenna_numbers
        ant_names = uvdata.antenna_names
    
    # Convert antenna names to strings
    anum = [str(int(n)+1) for n in ant_nums]  # CASA uses 1-indexed antenna names
    
    # Extract ITRF positions
    xx = antenna_positions[:, 0]
    yy = antenna_positions[:, 1]
    zz = antenna_positions[:, 2]
    
    # Spectral window parameters
    spwname = "L_BAND"
    freq_hz = uvdata.freq_array.squeeze()[0]  # First channel frequency
    channel_width_hz = np.abs(np.median(np.diff(uvdata.freq_array.squeeze())))
    
    # Convert to CASA strings
    freq = f"{freq_hz}Hz"
    # Use negative deltafreq if frequencies are descending
    deltafreq_sign = -1 if np.median(np.diff(uvdata.freq_array.squeeze())) < 0 else 1
    deltafreq = f"{deltafreq_sign * channel_width_hz}Hz"
    freqresolution = f"{np.abs(channel_width_hz)}Hz"
    nchannels = uvdata.Nfreqs
    
    # Time parameters
    integration_time_s = np.median(uvdata.integration_time)
    integrationtime = f"{integration_time_s}s"
    
    # Start time in MJD
    time_jd = Time(uvdata.time_array, format='jd')
    obstm = np.min(time_jd.mjd)
    
    # Duration
    duration_s = uvdata.Ntimes * integration_time_s
    stoptime = f"{duration_s}s"
    
    # Polarization - DSA-110 uses XX and YY
    stokes = "XX YY"
    
    # Check for autocorrelations
    autocorr = np.any(uvdata.ant_1_array == uvdata.ant_2_array)
    
    print(f"    Telescope: {tname}, {len(anum)} antennas")
    print(f"    Frequency: {freq_hz/1e9:.4f} GHz, {nchannels} channels")
    print(f"    Channel width: {channel_width_hz/1e6:.4f} MHz")
    print(f"    Integration time: {integration_time_s:.2f} s")
    print(f"    Start time: MJD {obstm:.6f}")
    print(f"    Duration: {duration_s:.2f} s ({uvdata.Ntimes} integrations)")
    print(f"    Autocorrelations: {autocorr}")
    
    # Step 1: Create MS structure with simulator
    print("  Step 1: Creating MS structure with CASA simulator...")
    sm.open(f'{msname}.ms')
    
    sm.setconfig(
        telescopename=tname,
        x=xx.tolist(),
        y=yy.tolist(),
        z=zz.tolist(),
        dishdiameter=diam,
        mount=mount,
        antname=anum,
        coordsystem="global",
        referencelocation=pos_obs
    )
    
    sm.setspwindow(
        spwname=spwname,
        freq=freq,
        deltafreq=deltafreq,
        freqresolution=freqresolution,
        nchannels=nchannels,
        stokes=stokes
    )
    
    sm.settimes(
        integrationtime=integrationtime,
        usehourangle=False,
        referencetime=me.epoch("utc", qa.quantity(obstm, "d"))
    )
    
    # Create a simple source for the phase center
    source_name = "PHASE_CENTER"
    sm.setfield(
        sourcename=source_name,
        sourcedirection=me.direction(
            "J2000",
            qa.quantity(phase_ra.to_value(u.rad), "rad"),
            qa.quantity(phase_dec.to_value(u.rad), "rad")
        )
    )
    
    sm.setauto(autocorrwt=1.0 if autocorr else 0.0)
    sm.observe(source_name, spwname, starttime="0s", stoptime=stoptime)
    sm.close()
    
    print(f"    MS structure created")
    
    # Step 2: Write visibility data using MS tool
    print("  Step 2: Writing visibility data...")
    ms = cc.ms()
    ms.open(f'{msname}.ms', nomodify=False)
    ms.selectinit(datadescid=0)
    
    # Get the data structure that CASA created
    rec = ms.getdata(["data"])
    casa_shape = rec["data"].shape
    print(f"    CASA MS data shape: {casa_shape}")
    print(f"    UVData array shape: {uvdata.data_array.shape}")
    
    # Reshape visibilities from UVData format to CASA format
    # UVData: (nblt, nfreq, npol)
    # CASA expects: (npol, nfreq, nrows) where nrows might differ from nblt
    # due to autocorrelations or baseline ordering
    
    # First transpose to (npol, nfreq, nblt)
    vis = uvdata.data_array.T.astype(np.complex128)
    print(f"    Transposed visibility shape: {vis.shape}")
    
    # Check if shapes match
    if vis.shape != casa_shape:
        print(f"    WARNING: Shape mismatch between data and MS!")
        print(f"    Expected by MS: {casa_shape}")
        print(f"    Provided: {vis.shape}")
        print(f"    Attempting to match MS structure...")
        
        # If the MS has more rows, it might have created rows we don't have data for
        # Pad or truncate as needed
        if vis.shape[2] < casa_shape[2]:
            print(f"    MS has more rows ({casa_shape[2]}) than data ({vis.shape[2]})")
            print(f"    This might be due to autocorrelations or baseline ordering")
            # Pad with zeros
            padded_vis = np.zeros(casa_shape, dtype=np.complex128)
            padded_vis[:, :, :vis.shape[2]] = vis
            vis = padded_vis
        elif vis.shape[2] > casa_shape[2]:
            print(f"    Data has more rows ({vis.shape[2]}) than MS ({casa_shape[2]})")
            print(f"    Truncating to match MS")
            vis = vis[:, :, :casa_shape[2]]
    
    print(f"    Writing {vis.shape} visibility array...")
    rec["data"] = vis
    ms.putdata(rec)
    ms.close()
    
    print("  Step 3: Adding imaging columns...")
    addImagingColumns(f'{msname}.ms')
    
    elapsed = time.time() - start_time
    print(f"  MS written successfully in {elapsed:.2f} seconds")
    print(f"  Output: {msname}.ms")


def write_UV_to_ms_direct(uvdata: "UVData", msname: "str", antenna_positions: "np.ndarray", 
                          phase_ra: u.Quantity, phase_dec: u.Quantity) -> None:
    """Write a UVData object to MS using dsacalib's efficient approach.
    
    This method extracts data arrays from UVData and uses dsacalib's convert_to_ms
    approach to avoid shape mismatches and CASA simulator performance issues.
    
    Parameters
    ----------
    uvdata : UVData
        The visibility data to write
    msname : str
        Output MS name (without .ms extension)
    antenna_positions : np.ndarray
        ITRF antenna positions, shape (nants, 3)
    phase_ra : astropy.units.Quantity
        Phase center RA
    phase_dec : astropy.units.Quantity
        Phase center Dec
    """
    import time
    import casatools as cc
    from casacore.tables import table
    
    start_time = time.time()
    print("  Writing MS using dsacalib's efficient approach...")
    print(f"  (Direct MS creation for {uvdata.Nants_telescope} antenna array)")
    
    # Remove existing MS if present
    if os.path.exists(f'{msname}.ms'):
        shutil.rmtree(f'{msname}.ms')
    
    # Extract data arrays in the format dsacalib expects
    print("  Step 1: Extracting data arrays...")
    
    # Get antenna info
    if hasattr(uvdata, 'telescope') and hasattr(uvdata.telescope, 'antenna_numbers'):
        ant_nums = uvdata.telescope.antenna_numbers
        ant_names = uvdata.telescope.antenna_names
    else:
        ant_nums = uvdata.antenna_numbers
        ant_names = uvdata.antenna_names
    
    # Create baseline names in CASA format (1-indexed)
    bname = []
    for i in range(uvdata.Nbls):
        ant1 = int(uvdata.ant_1_array[i]) + 1  # Convert to 1-indexed
        ant2 = int(uvdata.ant_2_array[i]) + 1
        bname.append([ant1, ant2])
    
    # Create antenna order (CASA format, 1-indexed)
    antenna_order = [int(n) + 1 for n in ant_nums]
    
    # Extract visibility data in the correct format: (baseline, time, channel, polarization)
    # UVData has shape (nblt, nspw, nfreq, npol) where nblt = nbls * ntimes
    nbls = uvdata.Nbls
    ntimes = uvdata.Ntimes
    nspws = uvdata.Nspws
    nfreqs = uvdata.Nfreqs
    npols = uvdata.Npols
    
    print(f"    Data dimensions: {nbls} baselines, {ntimes} times, {nspws} spws, {nfreqs} channels, {npols} pols")
    print(f"    Actual data shape: {uvdata.data_array.shape}")
    
    # Handle the correct data shape: (nblt, nspw, nfreq, npol) or (nblt, nfreq, npol)
    if len(uvdata.data_array.shape) == 4 and nspws == 1:
        # Data has shape (nblt, nspw=1, nfreq, npol) - squeeze out the spw dimension
        vis_data = uvdata.data_array.squeeze(axis=1)  # (nblt, nfreq, npol)
        print(f"    Squeezed data shape: {vis_data.shape}")
    elif len(uvdata.data_array.shape) == 3:
        # Data already has shape (nblt, nfreq, npol) - no squeezing needed
        vis_data = uvdata.data_array  # (nblt, nfreq, npol)
        print(f"    Data already in correct shape: {vis_data.shape}")
    else:
        # Multiple spectral windows - keep as is
        vis_data = uvdata.data_array  # (nblt, nspw, nfreq, npol)
        print(f"    Multi-spw data shape: {vis_data.shape}")
    
    # Keep data in (nblt, nfreq, npol) format for convert_to_ms_data_driven
    # No need to reshape - convert_to_ms_data_driven expects (nblt, nfreq, npol)
    print(f"    Keeping data in (nblt, nfreq, npol) format: {vis_data.shape}")
    
    # Convert to complex128 as dsacalib expects
    vis_data = vis_data.astype(np.complex128)
    
    print(f"    Reshaped visibility array: {vis_data.shape}")
    
    # Create source object for phase center
    from ...utils.coordinates import Direction
    source = Direction('J2000', phase_ra.to_value(u.rad), phase_dec.to_value(u.rad))
    source.name = "PHASE_CENTER"
    source.epoch = "J2000"
    source.ra = phase_ra
    source.dec = phase_dec
    
    # Get observation time
    time_jd = Time(uvdata.time_array, format='jd')
    obstm = np.min(time_jd.mjd)
    
    # Get integration time
    tsamp = np.median(uvdata.integration_time)
    
    print("  Step 2: Creating MS using data-driven approach...")
    
    # Use our data-driven convert_to_ms function
    from ...utils import ms_io
    
    ms_io.convert_to_ms_data_driven(
        source=source,
        vis=vis_data,
        obstm=obstm,
        ofile=msname,
        bname=bname,
        antenna_order=antenna_order,
        tsamp=tsamp,
        nint=1,
        antpos=antenna_positions,
        model=None,
        dt=0.0,  # No time offset
        dsa10=True
    )
    
    print("  Step 3: Adding imaging columns...")
    addImagingColumns(f'{msname}.ms')
    
    elapsed = time.time() - start_time
    print(f"  MS written successfully in {elapsed:.2f} seconds")
    print(f"  Output: {msname}.ms")


def write_UV_to_ms(uvdata: "UVData", msname: "str", antenna_positions: "np.ndarray") -> None:
    """Write a UVData object to a ms.

    DEPRECATED: Uses UVFITS as intermediate, which fails for DSA-110 scale arrays.
    Use write_UV_to_ms_direct() instead.
    
    Uses a fits file as the intermediate between UVData and ms, which is removed after
    the measurement set is written.
    """
    print("  Writing intermediate UVFITS file...")
    print(f"  WARNING: Writing UVFITS for {uvdata.Nants_telescope} antennas may be very slow!")
    if os.path.exists(f'{msname}.fits'):
        os.remove(f'{msname}.fits')

    # pyuvdata 3.2.4 has different parameters
    # NOTE: force_phase=True tells pyuvdata to phase the data even if not perfectly phased
    # This is needed after our fringestopping operation
    import time
    start_write = time.time()
    uvdata.write_uvfits(
        f'{msname}.fits',
        force_phase=True,
        run_check=False,
        check_extra=False,
        run_check_acceptability=False
    )
    write_time = time.time() - start_write
    print(f"    Written: {msname}.fits in {write_time:.2f} seconds")
    print(f"    NOTE: For large arrays (>20 antennas), consider using direct MS writing")

    print("  Converting UVFITS to MS format...")
    if os.path.exists(f'{msname}.ms'):
        shutil.rmtree(f'{msname}.ms')
    importuvfits(f'{msname}.fits', f'{msname}.ms')
    print(f"    Created MS: {msname}.ms")

    print("  Updating antenna positions in MS...")
    with table(f'{msname}.ms/ANTENNA', readonly=False) as tb:
        tb.putcol('POSITION', antenna_positions)
    print(f"    Updated {antenna_positions.shape[0]} antenna positions")

    print("  Adding imaging columns...")
    addImagingColumns(f'{msname}.ms')
    print("    Imaging columns added")

    print("  Cleaning up intermediate FITS file...")
    os.remove(f'{msname}.fits')
    print("    Cleanup complete")


def set_ms_model_column(msname: str, uvdata: "UVData", pt_dec: u.Quantity, ra: u.Quantity,
                        dec: u.Quantity, flux_Jy: float) -> None:
    """Set the measurement model column."""
    # First, check the actual MS structure
    with table(f'{msname}.ms', readonly=True) as tb:
        nrows = tb.nrows()
        data_shape = tb.getcol('DATA').shape
    
    print(f"  MS has {nrows} rows, data shape: {data_shape}")
    
    if flux_Jy is not None:
        print(f"  Generating calibrator model with flux {flux_Jy} Jy...")
        fobs = uvdata.freq_array.squeeze() / 1e9
        lst = uvdata.lst_array
        source = generate_calibrator_source('cal', ra, dec, flux_Jy)
        print("  Computing amplitude sky model...")
        model = amplitude_sky_model(source, lst, pt_dec, fobs)
        model = np.tile(model[:, :, np.newaxis], (1, 1, uvdata.Npols))
        print(f"    Model shape (from UVData): {model.shape}")
        
        # Pad if needed to match MS structure
        if model.shape[0] < nrows:
            print(f"    Padding model from {model.shape[0]} to {nrows} rows...")
            model_padded = np.ones((nrows, model.shape[1], model.shape[2]), dtype=model.dtype)
            model_padded[:model.shape[0], :, :] = model
            model = model_padded
    else:
        print("  Using unit model (no flux specified)...")
        # Create a model that matches the MS structure
        model = np.ones((nrows, uvdata.Nfreqs, uvdata.Npols), dtype=np.complex64)

    print(f"  Final model shape: {model.shape}")
    print("  Writing MODEL_DATA and CORRECTED_DATA columns...")
    with table(f'{msname}.ms', readonly=False) as tb:
        tb.putcol('MODEL_DATA', model)
        tb.putcol('CORRECTED_DATA', tb.getcol('DATA')[:])
    print("    Columns written")


def coordinates_differ(meridian, phase, tol=1e-7):
    """Determine if meridian and phase coordinates differ to within tol."""
    phase_ra, phase_dec = phase
    meridian_ra, meridian_dec = meridian
    if (
            phase_ra is None
            or np.abs(phase_ra.to_value(u.rad) - meridian_ra.to_value(u.rad)) < tol):
        if (
                phase_dec is None
                or np.abs(phase_dec.to_value(u.rad) - meridian_dec.to_value(u.rad)) < tol):
            return False
    return True


def generate_phase_model(uvw, uvw_m, nts, lamb):
    """Generates a phase model to apply using baseline-based delays.

    Parameters
    ----------
    uvw : np.ndarray
        The uvw coordinates at each time bin (baseline, 3)
    uvw_m : np.ndarray
        The uvw coordinates at the meridian, (time, baseline, 3)
    nts : int
        The number of unique times.
    lamb : astropy quantity
        The observing wavelength of each channel.
    ant1, ant2 : list
        The antenna indices in order.

    Returns:
    --------
    np.ndarray
        The phase model to apply.
    """
    dw = (uvw[:, -1] - np.tile(uvw_m[np.newaxis, :, -1], (nts, 1, 1)).reshape(-1)) * u.m
    phase_model = np.exp((2j * np.pi / lamb * dw[:, np.newaxis, np.newaxis]
                          ).to_value(u.dimensionless_unscaled))
    return phase_model


def generate_phase_model_antbased(uvw, uvw_m, nbls, nts, lamb, ant1, ant2):
    """Generates a phase model to apply using antenna-based geometric delays.

    Parameters
    ----------
    uvw : np.ndarray
        The uvw coordinates at each time bin (baseline, 3)
    uvw_m : np.ndarray
        The uvw coordinates at the meridian, (time, baseline, 3)
    nbls, nts : int
        The number of unique baselines, times.
    lamb : astropy quantity
        The observing wavelength of each channel.
    ant1, ant2 : list
        The antenna indices in order.

    Returns:
    --------
    np.ndarray
        The phase model to apply.
    """
    # Need ant1 and ant2 to be passed here
    # Need to check that this gets the correct refidxs
    refant = ant1[0]
    refidxs = np.where(ant1 == refant)[0]

    antenna_order = list(ant2[refidxs])

    antenna_w_m = uvw_m[refidxs, -1]
    uvw_delays = uvw.reshape((nts, nbls, 3))
    antenna_w = uvw_delays[:, refidxs, -1]
    antenna_dw = antenna_w - antenna_w_m[np.newaxis, :]
    dw = np.zeros((nts, nbls))
    for i, a1 in enumerate(ant1):
        a2 = ant2[i]
        dw[:, i] = antenna_dw[:, antenna_order.index(a2)] - \
            antenna_dw[:, antenna_order.index(a1)]
    dw = dw.reshape(-1) * u.m
    # lamb is (1, nfreq), dw is (nblt,)
    # Result should be (nblt, nfreq) for proper broadcasting with data_array (nblt, nfreq, npol)
    phase_model = np.exp((2j * np.pi * dw[:, np.newaxis] / lamb
                          ).to_value(u.dimensionless_unscaled))
    return phase_model


def get_meridian_coords(pt_dec, time_mjd):
    """Get coordinates for the meridian in J2000."""
    pointing = Direction(
        'HADEC', 0., pt_dec.to_value(u.rad), time_mjd)
    meridian_ra, meridian_dec = pointing.J2000()
    meridian_ra = meridian_ra * u.rad
    meridian_dec = meridian_dec * u.rad
    return meridian_ra, meridian_dec
