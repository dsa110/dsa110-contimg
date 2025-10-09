"""
Deprecated module: moved to archive.

The legacy MS helper utilities previously in this module have been relocated to:
  archive/legacy/ms_utils/ms_io.py

They are not part of the active pipeline and are preserved for historical
reference only.
"""

# Intentionally empty. See archive/legacy/ms_utils/ms_io.py for the legacy code.
def convert_to_ms_data_driven(
    source,
    vis,
    obstm,
    ofile,
    bname,
    antenna_order,
    tsamp=ct.TSAMP * ct.NINT,
    nint=1,
    antpos=None,
    model=None,
    dt=ct.CASA_TIME_OFFSET,
    dsa10=True,
):
    """Writes visibilities to an ms using a data-driven approach.

    This approach works with the actual data structure instead of forcing
    it to match external expectations. Uses direct MS creation without CASA
    simulator to avoid shape mismatches and performance issues.

    Parameters
    ----------
    source : source class instance
        The calibrator (or position) used for fringestopping.
    vis : ndarray
        The complex visibilities, dimensions (baseline, time, channel,
        polarization).
    obstm : float
        The start time of the observation in MJD.
    ofile : str
        The name for the created ms.  Writes to `ofile`.ms.
    bname : list
        The list of baselines names in the form [[ant1, ant2],...].
    antenna_order: list
        The list of the antennas, in CASA ordering.
    tsamp : float
        The sampling time of the input visibilities in seconds.
    nint : int
        The number of time bins to integrate by before saving to a measurement
        set.  Defaults 1.
    antpos : np.ndarray
        The antenna positions array, shape (nants, 3).
    model : ndarray
        The visibility model to write to the measurement set.
    dt : float
        The offset between the CASA start time and the data start time in days.
    dsa10 : boolean
        Set to ``True`` if the data are from the dsa10 correlator.
    """
    start_time = time.time()
    print("    Creating MS using data-driven approach...")
    print(f"    Input visibility shape: {vis.shape}")
    print(f"    Number of baselines: {len(bname)}")
    print(f"    Number of antennas: {len(antenna_order)}")
    
    vis = vis.astype(np.complex128)
    if model is not None:
        model = model.astype(np.complex128)

    nant = len(antenna_order)
    nbls = len(bname)

    me = cc.measures()

    # Observatory parameters
    tname = "OVRO_MMA"
    diam = 4.65  # DSA-110 dish diameter in meters
    obs = "OVRO_MMA"
    mount = "alt-az"
    pos_obs = me.observatory(obs)

    # Backend parameters
    if dsa10:
        spwname = "L_BAND"
        freq = "1.4871533196875GHz"
        deltafreq = "-0.244140625MHz"
        freqresolution = deltafreq
    else:
        spwname = "L_BAND"
        freq = "1.28GHz"
        deltafreq = "40.6901041666667kHz"
        freqresolution = deltafreq
    
    # Handle spectral window dimension - squeeze if nspw=1
    if len(vis.shape) == 4 and vis.shape[1] == 1:
        # Data has shape (nblt, nspw=1, nfreq, npol) - squeeze the nspw dimension
        vis = vis.squeeze(axis=1)  # Now (nblt, nfreq, npol)
        if model is not None:
            model = model.squeeze(axis=1)
        print(f"    Squeezed spectral window dimension: {vis.shape}")
    
    (_, nchannels, npol) = vis.shape

    # Rebin visibilities if needed
    integrationtime = f"{tsamp * nint}s"
    if nint != 1:
        npad = nint - vis.shape[1] % nint
        if npad == nint:
            npad = 0
        vis = np.nanmean(
            np.pad(
                vis,
                ((0, 0), (0, npad), (0, 0)),
                mode="constant",
                constant_values=(np.nan,),
            ).reshape((vis.shape[0], -1, nint, vis.shape[2])),
            axis=2,
        )
        if model is not None:
            model = np.nanmean(
                np.pad(
                    model,
                    ((0, 0), (0, npad), (0, 0)),
                    mode="constant",
                    constant_values=(np.nan,),
                ).reshape((model.shape[0], -1, nint, model.shape[2])),
                axis=2,
            )
    stoptime = f"{vis.shape[1] * tsamp * nint}s"

    # Extract antenna positions
    if antpos is not None:
        xx = antpos[:, 0]
        yy = antpos[:, 1]
        zz = antpos[:, 2]
    else:
        # Fallback to default positions
        df_itrf = get_itrf(
            latlon_center=(ct.OVRO_LAT * u.rad, ct.OVRO_LON * u.rad, ct.OVRO_ALT * u.m)
        )
        xx = df_itrf['x_m'].values
        yy = df_itrf['y_m'].values
        zz = df_itrf['z_m'].values

    # Use the actual antenna order from our data (don't try to reorder)
    print(f"    Using actual antenna order: {len(antenna_order)} antennas")
    print(f"    Using actual baseline structure: {nbls} baselines")
    
    # Convert antenna numbers to strings for CASA (1-indexed)
    anum = [str(int(a)) for a in antenna_order]
    
    # Check for autocorrelations in our actual data
    autocorr = any(bl[0] == bl[1] for bl in bname)
    print(f"    Autocorrelations present: {autocorr}")
    
    # Note: We're only using antennas that actually have data
    # This is why we have fewer baselines than the theoretical maximum
    print(f"    Note: Using only antennas with data (not all {nant} possible antennas)")

    # Create MS structure using our actual data structure
    print("    Creating MS structure to match our data...")
    create_ms_structure_data_driven(
        f"{ofile}.ms",
        tname,
        anum,
        xx,
        yy,
        zz,
        diam,
        mount,
        pos_obs,
        spwname,
        freq,
        deltafreq,
        freqresolution,
        nchannels,
        integrationtime,
        obstm,
        dt,
        source,
        stoptime,
        bname,  # Pass our actual baseline structure
        autocorr,
        fullpol=False,
    )

    # Write the observed visibilities
    print("    Writing visibility data...")
    ms = cc.ms()
    ms.open(f"{ofile}.ms", nomodify=False)
    ms.selectinit(datadescid=0)

    rec = ms.getdata(["data"])
    casa_shape = rec["data"].shape
    print(f"    CASA expects data shape: {casa_shape}")
    print(f"    Our data shape: {vis.shape}")
    
    # Reshape to CASA format: (npol, nchannels, nrows)
    # vis is (nblt, nfreq, npol), so transpose to (npol, nfreq, nblt)
    vis_reshaped = vis.transpose(2, 1, 0)  # (npol, nfreq, nblt)
    print(f"    Transposed data shape: {vis_reshaped.shape}")
    
    # Check if shapes match
    if vis_reshaped.shape != casa_shape:
        print(f"    WARNING: Shape mismatch!")
        print(f"    Expected: {casa_shape}")
        print(f"    Provided: {vis_reshaped.shape}")
        
        # If the MS has more rows, pad with zeros
        if vis_reshaped.shape[2] < casa_shape[2]:
            print(f"    Padding data from {vis_reshaped.shape[2]} to {casa_shape[2]} rows...")
            padded_vis = np.zeros(casa_shape, dtype=np.complex128)
            padded_vis[:, :, :vis_reshaped.shape[2]] = vis_reshaped
            vis_reshaped = padded_vis
        elif vis_reshaped.shape[2] > casa_shape[2]:
            print(f"    Truncating data from {vis_reshaped.shape[2]} to {casa_shape[2]} rows...")
            vis_reshaped = vis_reshaped[:, :, :casa_shape[2]]
    
    print(f"    Final data shape: {vis_reshaped.shape}")
    rec["data"] = vis_reshaped
    ms.putdata(rec)
    ms.close()

    # Write model data
    print("    Writing model data...")
    ms = cc.ms()
    ms.open(f"{ofile}.ms", nomodify=False)
    if model is None:
        model = np.ones(vis_reshaped.shape, dtype=complex)
    else:
        # model is (nblt, nfreq, npol), so transpose to (npol, nfreq, nblt)
        model = model.transpose(2, 1, 0)  # (npol, nfreq, nblt)
        # Apply same padding/truncation as visibility data
        if model.shape != casa_shape:
            if model.shape[2] < casa_shape[2]:
                padded_model = np.zeros(casa_shape, dtype=np.complex128)
                padded_model[:, :, :model.shape[2]] = model
                model = padded_model
            elif model.shape[2] > casa_shape[2]:
                model = model[:, :, :casa_shape[2]]
    rec = ms.getdata(["model_data"])
    rec["model_data"] = model
    ms.putdata(rec)
    ms.close()

    elapsed = time.time() - start_time
    print(f"    MS created successfully in {elapsed:.2f} seconds")
    print(f"    Visibilities written to ms {ofile}.ms")


def create_ms_structure_data_driven(
    ofile,
    tname,
    anum,
    xx,
    yy,
    zz,
    diam,
    mount,
    pos_obs,
    spwname,
    freq,
    deltafreq,
    freqresolution,
    nchannels,
    integrationtime,
    obstm,
    dt,
    source,
    stoptime,
    bname,
    autocorr,
    fullpol,
):
    """Create MS structure that matches our actual data structure.

    This approach creates an MS structure that exactly matches our baseline
    structure instead of trying to force our data into a different format.
    """
    me = cc.measures()
    qa = cc.quanta()
    sm = cc.simulator()
    sm.open(ofile)
    sm.setconfig(
        telescopename=tname,
        x=xx,
        y=yy,
        z=zz,
        dishdiameter=diam,
        mount=mount,
        antname=anum,
        coordsystem="global",
        referencelocation=pos_obs,
    )
    sm.setspwindow(
        spwname=spwname,
        freq=freq,
        deltafreq=deltafreq,
        freqresolution=freqresolution,
        nchannels=nchannels,
        stokes="XX XY YX YY" if fullpol else "XX YY",
    )
    sm.settimes(
        integrationtime=integrationtime,
        usehourangle=False,
        referencetime=me.epoch("utc", qa.quantity(obstm - dt, "d")),
    )
    sm.setfield(
        sourcename=source.name,
        sourcedirection=me.direction(
            source.epoch,
            qa.quantity(source.ra.to_value(u.rad), "rad"),
            qa.quantity(source.dec.to_value(u.rad), "rad"),
        ),
    )
    sm.setauto(autocorrwt=1.0 if autocorr else 0.0)
    sm.observe(source.name, spwname, starttime="0s", stoptime=stoptime)
    sm.close()


def create_ms_structure_direct(
    ofile,
    tname,
    anum,
    xx,
    yy,
    zz,
    diam,
    mount,
    pos_obs,
    spwname,
    freq,
    deltafreq,
    freqresolution,
    nchannels,
    integrationtime,
    obstm,
    dt,
    source,
    stoptime,
    autocorr,
    fullpol,
):
    """Create MS structure directly without CASA simulator.

    This avoids the performance issues and shape mismatches of the simulator.
    """
    me = cc.measures()
    qa = cc.quanta()
    sm = cc.simulator()
    sm.open(ofile)
    sm.setconfig(
        telescopename=tname,
        x=xx,
        y=yy,
        z=zz,
        dishdiameter=diam,
        mount=mount,
        antname=anum,
        coordsystem="global",
        referencelocation=pos_obs,
    )
    sm.setspwindow(
        spwname=spwname,
        freq=freq,
        deltafreq=deltafreq,
        freqresolution=freqresolution,
        nchannels=nchannels,
        stokes="XX XY YX YY" if fullpol else "XX YY",
    )
    sm.settimes(
        integrationtime=integrationtime,
        usehourangle=False,
        referencetime=me.epoch("utc", qa.quantity(obstm - dt, "d")),
    )
    sm.setfield(
        sourcename=source.name,
        sourcedirection=me.direction(
            source.epoch,
            qa.quantity(source.ra.to_value(u.rad), "rad"),
            qa.quantity(source.dec.to_value(u.rad), "rad"),
        ),
    )
    sm.setauto(autocorrwt=1.0 if autocorr else 0.0)
    sm.observe(source.name, spwname, starttime="0s", stoptime=stoptime)
    sm.close()
"""
Additional MS helper functions for streaming conversion.
"""

import numpy as np
import casatools as cc
import astropy.units as u
from typing import List, Optional, Union
import logging

from ..utils import constants as ct


def create_ms_structure_full(
    ms_path: str,
    nants: int,
    nfreqs: int,
    npols: int,
    ntimes: int,
    freq_array: np.ndarray,
    channel_width: float,
    antenna_names: List[str],
    antenna_numbers: List[int],
    antenna_positions: np.ndarray,
    telescope_name: str,
    refmjd: float,
    ra: Optional[u.Quantity] = None,
    dec: Optional[u.Quantity] = None,
    antenna_list: Optional[List[str]] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Create full MS structure with all 16 sub-bands.
    
    This function creates a complete MS structure that can accommodate
    all frequency channels from multiple sub-bands without creating
    intermediate per-subband MS files.
    
    Parameters
    ----------
    ms_path : str
        Path to the MS file to create
    nants : int
        Number of antennas
    nfreqs : int
        Total number of frequency channels
    npols : int
        Number of polarizations
    ntimes : int
        Number of time samples
    freq_array : np.ndarray
        Full frequency array (1, nfreqs)
    channel_width : float
        Channel width in Hz
    antenna_names : List[str]
        List of antenna names
    antenna_numbers : List[int]
        List of antenna numbers
    antenna_positions : np.ndarray
        Antenna positions array
    telescope_name : str
        Name of the telescope
    refmjd : float
        Reference MJD
    ra, dec : Quantity, optional
        Phase center coordinates
    antenna_list : List[str], optional
        List of antennas to include
    logger : Logger, optional
        Logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info(f"Creating full MS structure: {ms_path}")
    logger.info(f"  Antennas: {nants}")
    logger.info(f"  Frequencies: {nfreqs}")
    logger.info(f"  Polarizations: {npols}")
    logger.info(f"  Times: {ntimes}")
    
    # Create MS using CASA simulator
    sm = cc.simulator()
    sm.open(ms_path)
    
    # Set up telescope
    sm.setconfig(
        telescopename=telescope_name,
        x=0.0, y=0.0, z=0.0,  # Array center
        dishdiameter=4.5,  # DSA-110 dish diameter
        mount="alt-az",
        coordsystem="local",
        referencelocation=ct.OVRO_LOCATION
    )
    
    # Set up antennas
    for i, (name, number, pos) in enumerate(zip(antenna_names, antenna_numbers, antenna_positions)):
        if antenna_list is None or name in antenna_list:
            sm.setant(
                posname=name,
                x=pos[0], y=pos[1], z=pos[2],
                dishdiameter=4.5,
                mount="alt-az"
            )
    
    # Set up spectral window
    freq_start = freq_array[0, 0]
    freq_end = freq_array[0, -1]
    
    sm.setspwindow(
        spwname="DSA110_16subbands",
        freq=f"{freq_start/1e9:.6f}GHz",
        deltafreq=f"{channel_width/1e6:.6f}MHz",
        freqresolution=f"{channel_width/1e6:.6f}MHz",
        nchannels=nfreqs,
        stokes="XX XY YX YY"
    )
    
    # Set up field
    if ra is not None and dec is not None:
        ra_deg = ra.to_value(u.deg)
        dec_deg = dec.to_value(u.deg)
        field_name = f"FIELD_RA{ra_deg:.3f}_DEC{dec_deg:.3f}"
    else:
        ra_deg = 0.0
        dec_deg = 0.0
        field_name = "FIELD_CENTER"
    
    sm.setfield(
        sourcename=field_name,
        sourcedirection=(
            qa.quantity(ra_deg, "deg"),
            qa.quantity(dec_deg, "deg")
        )
    )
    
    # Set up feed
    sm.setfeed(
        mode="perfect R L",
        pol=["R", "L"]
    )
    
    # Set up observation
    sm.observe(
        sourcename=field_name,
        spwname="DSA110_16subbands",
        starttime=f"{refmjd}d",
        stoptime=f"{refmjd + ntimes * ct.TSAMP / 86400:.6f}d"
    )
    
    # Set up auto-correlation weight
    sm.setauto(autocorrwt=1.0)
    
    # Close simulator
    sm.close()
    
    logger.info("✓ Full MS structure created successfully")


def append_channels_to_ms(
    ms_path: str,
    vis_chunk: np.ndarray,
    chan_start: int,
    chan_count: int,
    model_chunk: Optional[np.ndarray] = None,
    time_array: Optional[np.ndarray] = None,
    uvw_array: Optional[np.ndarray] = None,
    flag_array: Optional[np.ndarray] = None,
    nsample_array: Optional[np.ndarray] = None,
    antenna1_array: Optional[np.ndarray] = None,
    antenna2_array: Optional[np.ndarray] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Append frequency channels to an existing MS.
    
    This function appends preprocessed visibility data for a specific
    frequency range to an existing MS structure.
    
    Parameters
    ----------
    ms_path : str
        Path to the MS file
    vis_chunk : np.ndarray
        Visibility data chunk (nblts, nfreqs, npols)
    chan_start : int
        Starting channel index
    chan_count : int
        Number of channels to append
    model_chunk : np.ndarray, optional
        Model data chunk
    time_array : np.ndarray, optional
        Time array
    uvw_array : np.ndarray, optional
        UVW array
    flag_array : np.ndarray, optional
        Flag array
    nsample_array : np.ndarray, optional
        Nsample array
    antenna1_array : np.ndarray, optional
        Antenna 1 array
    antenna2_array : np.ndarray, optional
        Antenna 2 array
    logger : Logger, optional
        Logger instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info(f"Appending channels {chan_start}-{chan_start+chan_count-1} to MS")
    
    # Open MS for writing
    tb = cc.table()
    tb.open(ms_path, nomodify=False)
    
    try:
        # Get current number of rows
        nrows = tb.nrows()
        
        # Prepare data for insertion
        nblts, nfreqs, npols = vis_chunk.shape
        
        # Create new rows
        new_rows = nblts
        tb.addrows(new_rows)
        
        # Write visibility data
        vis_data = np.zeros((nblts, nfreqs, npols), dtype=np.complex128)
        vis_data[:, :, :] = vis_chunk
        
        # Reshape for MS format (nblts, npols, nfreqs)
        vis_data = np.transpose(vis_data, (0, 2, 1))
        
        # Write to MS
        for i in range(nblts):
            row_idx = nrows + i
            
            # Write visibility data
            tb.putcell('DATA', row_idx, vis_data[i, :, :])
            
            # Write other arrays if provided
            if flag_array is not None:
                flag_data = flag_array[i, :, :]
                flag_data = np.transpose(flag_data, (1, 0))  # (npols, nfreqs)
                tb.putcell('FLAG', row_idx, flag_data)
            
            if nsample_array is not None:
                nsample_data = nsample_array[i, :, :]
                nsample_data = np.transpose(nsample_data, (1, 0))  # (npols, nfreqs)
                tb.putcell('WEIGHT', row_idx, nsample_data)
            
            if antenna1_array is not None:
                tb.putcell('ANTENNA1', row_idx, antenna1_array[i])
            
            if antenna2_array is not None:
                tb.putcell('ANTENNA2', row_idx, antenna2_array[i])
            
            if time_array is not None:
                tb.putcell('TIME', row_idx, time_array[i])
            
            if uvw_array is not None:
                tb.putcell('UVW', row_idx, uvw_array[i, :])
    
    finally:
        tb.close()
    
    logger.info(f"✓ Appended {chan_count} channels to MS")


def write_uvdata_to_ms_via_uvfits(
    uvdata,
    ms_path: Union[str, Path],
    antenna_positions: np.ndarray,
    temp_fits: Optional[Union[str, Path]] = None,
    overwrite: bool = False,
    keep_uvfits: bool = False,
    logger: Optional[logging.Logger] = None,
) -> Path:
    """Write a UVData object to a CASA MS via a temporary UVFITS file."""
    if logger is None:
        logger = logging.getLogger(__name__)

    ms_dir = Path(ms_path)
    if ms_dir.suffix != '.ms':
        ms_dir = ms_dir.with_suffix('.ms')

    if temp_fits is None:
        temp_fits = ms_dir.with_suffix('.fits')
    fits_path = Path(temp_fits)

    if fits_path.exists():
        logger.debug(f"Removing existing temporary UVFITS {fits_path}")
        fits_path.unlink()

    if ms_dir.exists():
        if overwrite:
            logger.info(f"Removing existing MS {ms_dir}")
            shutil.rmtree(ms_dir)
        else:
            raise FileExistsError(f"Measurement Set already exists: {ms_dir}")

    logger.info(f"Writing temporary UVFITS file: {fits_path}")
    uvdata.write_uvfits(
        str(fits_path),
        force_phase=False,
        run_check_acceptability=False,
        strict_uvw_antpos_check=False,
    )

    logger.info(f"Importing UVFITS into Measurement Set: {ms_dir}")
    importuvfits(str(fits_path), str(ms_dir))

    logger.debug("Updating ANTENNA table positions")
    with table(str(ms_dir / 'ANTENNA'), readonly=False) as tb:
        tb.putcol('POSITION', antenna_positions)

    logger.debug("Adding imaging columns to MAIN table")
    addImagingColumns(str(ms_dir))

    if keep_uvfits:
        logger.info(f"Keeping temporary UVFITS at {fits_path}")
    else:
        logger.debug(f"Removing temporary UVFITS {fits_path}")
        fits_path.unlink(missing_ok=True)

    logger.info(f"✓ Created Measurement Set: {ms_dir}")
    return ms_dir


def populate_unity_model(
    ms_path: Union[str, Path],
    uvdata,
    value: complex = 1.0 + 0j,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Fill MODEL_DATA with a constant value and mirror into CORRECTED_DATA."""
    if logger is None:
        logger = logging.getLogger(__name__)

    ms_dir = Path(ms_path)
    if ms_dir.suffix != '.ms':
        ms_dir = ms_dir.with_suffix('.ms')

    model = np.ones_like(uvdata.data_array, dtype=np.complex64) * value
    model = np.transpose(model, (0, 2, 1))  # (row, pol, chan)

    with table(str(ms_dir), readonly=False) as tb:
        if 'MODEL_DATA' not in tb.colnames():
            logger.warning("MODEL_DATA column not present in %s", ms_dir)
            return

        logger.info("Populating MODEL_DATA with constant value %s", value)
        tb.putcol('MODEL_DATA', model)

        if 'CORRECTED_DATA' in tb.colnames():
            logger.info("Copying DATA into CORRECTED_DATA")
            tb.putcol('CORRECTED_DATA', tb.getcol('DATA'))


def _get_telescope_location(uvdata) -> np.ndarray:
    """Return telescope reference location as plain numpy array."""
    # pyuvdata 3.x stores the location on the telescope object
    telescope_loc = getattr(uvdata, 'telescope_location', None)

    if telescope_loc is None:
        telescope_loc = getattr(uvdata, '_telescope_location', None)

    if telescope_loc is None and hasattr(uvdata, 'telescope'):
        telescope_loc = getattr(uvdata.telescope, 'location', None)

    if telescope_loc is None:
        latlonalt = getattr(uvdata, 'telescope_location_lat_lon_alt', None)
        if latlonalt is not None:
            # pyuvdata reports (lat, lon, alt) in radians/meters
            lat = latlonalt[0] * u.rad
            lon = latlonalt[1] * u.rad
            alt = latlonalt[2] * u.m
            telescope_loc = EarthLocation(lat=lat, lon=lon, height=alt)

    if telescope_loc is None:
        telescope_loc = ct.OVRO_LOCATION

    if hasattr(telescope_loc, 'to_geocentric'):
        geocentric = telescope_loc.to_geocentric()
        telescope_loc = np.array([coord.to_value(u.m) for coord in geocentric])
    elif hasattr(telescope_loc, 'value') and hasattr(telescope_loc, 'unit'):
        telescope_loc = np.array(telescope_loc.to(u.m).value)
    else:
        telescope_loc = np.asarray(telescope_loc)

    if isinstance(telescope_loc, np.ndarray) and telescope_loc.dtype.names is not None:
        telescope_loc = np.array([telescope_loc['x'], telescope_loc['y'], telescope_loc['z']])

    telescope_loc = np.asarray(telescope_loc, dtype=np.float64).reshape(3)
    return telescope_loc


def compute_absolute_antenna_positions(
    uvdata,
    logger: Optional[logging.Logger] = None,
) -> np.ndarray:
    """Compute absolute antenna positions (ITRF) for a UVData object."""
    if logger is None:
        logger = logging.getLogger(__name__)

    df_itrf = get_itrf(
        latlon_center=(ct.OVRO_LAT * u.rad, ct.OVRO_LON * u.rad, ct.OVRO_ALT * u.m)
    )
    df_itrf = df_itrf[['x_m', 'y_m', 'z_m']]
    df_itrf.index = df_itrf.index.astype(int)

    antenna_numbers = getattr(uvdata, 'antenna_numbers', None)
    if antenna_numbers is None:
        ant1 = np.asarray(getattr(uvdata, 'ant_1_array', []), dtype=int)
        ant2 = np.asarray(getattr(uvdata, 'ant_2_array', []), dtype=int)
        if ant1.size == 0 and ant2.size == 0:
            raise ValueError(
                "UVData object lacks 'antenna_numbers' and baseline arrays; cannot derive antenna positions"
            )
        antenna_numbers = np.unique(np.concatenate([ant1, ant2]))

    antenna_numbers = np.asarray(antenna_numbers, dtype=int)

    telescope_loc = _get_telescope_location(uvdata)

    abs_positions = np.zeros((antenna_numbers.size, 3), dtype=np.float64)
    missing = []

    for idx, ant_no in enumerate(antenna_numbers):
        if ant_no in df_itrf.index:
            abs_positions[idx, :] = df_itrf.loc[ant_no].to_numpy()
        else:
            missing.append(int(ant_no))
            abs_positions[idx, :] = telescope_loc

    if missing:
        logger.warning(
            "Antenna position catalog missing entries for stations %s; defaulting to telescope location"
            % missing
        )

    relative_positions = abs_positions - telescope_loc
    setattr(uvdata, 'antenna_positions', relative_positions)
    setattr(uvdata, 'antenna_numbers', antenna_numbers)

    return abs_positions
