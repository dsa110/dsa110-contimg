from time import process_time

import shutil
import os
import warnings

import numpy as np
import astropy.units as u
import astropy.constants as c
from astropy.time import Time
from pyuvdata import UVData
from pyuvdata import utils as uvutils
from pyuvdata.uvdata.ms import tables

from astropy.coordinates import EarthLocation, HADec, SkyCoord, ICRS, Angle
import astropy.units as u

from utils_dsa110 import loc_dsa110, pb_dsa110



# uvh5_to_ms is the main functionality here - everything else is called from there
# and should probably be left alone
def uvh5_to_ms(
        fname, msname, append_coords=False, antenna_list=None,
        field_name=None, telescope_pos=loc_dsa110,
        calib_ra=None, calib_dec=None, calib_epoch='J2000.0', calib_flux_jy=None, calib_sidx=None, calib_sidx_f0_ghz=None,
        protect_files=False, verbose=False
):
    """
    Converts a uvh5 data to a uvfits file.

    Parameters
    ----------
    fname: str or list of str
        The full path(s) to the hdf5 file(s) to load
    msname : str
        The name of the ms to write. Data will be written to `msname`.ms
    append_coords : bool
        If True, the coordinates (in decimal degrees) of the observed field 
        will be appended to the ms name as _raXX.XX-decXX.XX
    antenna_list : list
        Antennas for which to extract visibilities from the uvh5 file. Default
        is to extract all visibilities in the uvh5 file. Should be given as a list 
        of pad names (e.g. ['pad1', 'pad2', 'pad3']) for the first 3 pads
    field_name : str
        Name of the field
    telescope_pos : EarthLocation object
        EarthLocation object describing the loction of the telescope
    flux : float
        The flux of the calibrator in Jy. If included, will write a model of
        the primary beam response to the calibrator source to the model column
        of the ms. If not included, a model of a constant response over
        frequency and time will be written instead of the primary beam model.
    protect_files : bool
        If True it won't overwrite existing MS files
    verbose : bool
        If True, print status messages
    """

    # Load data from HDF5 files:
    # uvdata is a pyuvdata UVData instance
    uvdata = load_uvh5_file(fname, antenna_list, telescope_pos, verbose=verbose)

    # Set the UVW coordinates and phase centers
    uvdata = set_phases(uvdata, field_name, telescope_pos, verbose=verbose)

    # Make calibrator model - do nothing if no calibrator is given
    #uvcalib = make_calib_model(uvdata, calib_ra, calib_dec, calib_flux_jy, telescope_pos, calib_sidx, calib_sidx_f0_ghz, calib_epoch, verbose=verbose)
    uvcalib = None

    # # Phase everything
    # uvdata, uvcalib, phasecoords = phase_v2(uvdata, uvcalib, field_name, telescope_pos, verbose=verbose)

    # Write the ms
    msname = write_ms(uvdata, uvcalib, msname, protect_files, append_coords, verbose=verbose)

    return msname


def load_uvh5_file(fname: str, antenna_list: list = None, telescope_pos: EarthLocation = None, verbose = False):
    """Load specific antennas from a uvh5 file or files.

    Loads a specified file or files, extracts the requested antennas, and 
    concatenates them if multiple files exist.

    Arguments
    ---------
    fname: str or list of str
        The path(s) to the hdf5 file(s) to load
    antenna_list : list
        Antennas for which to extract visibilities from the uvh5 file. Default
        is to extract all visibilities in the uvh5 file. Should be given as a list 
        of pad names (e.g. ['pad1', 'pad2', 'pad3']) for the first 3 pads
    telescope_pos : EarthLocation object
        EarthLocation object describing the loction of the telescope

    Returns
    -------
    uvdata: UVData instance
        The loaded data
    """

    if verbose:
        print("Loading data...")

    # Read in the data
    if not isinstance(fname, (list, tuple, np.ndarray)):
        fname = [fname]
    
    uvdata = UVData()

    # Strip 'pad' from antenna names if needed
    if antenna_list is not None:
        antenna_list = [n.strip('pad') for n in antenna_list]

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"key []* is longer than 8 characters[]*")
        warnings.filterwarnings("ignore", message=r"Telescope []* is not in known_telescopes[]*")
        # keep_all_metadata removes the unused antennas
        uvdata.read(fname[0], file_type='uvh5', antenna_names=antenna_list, keep_all_metadata=False,
                    run_check=False)

    # pyuvdata really wants uvw_array to be float64:
    uvdata.uvw_array = uvdata.uvw_array.astype(np.float64)

    # Need BLTs and frequencies to check compatibility before combining
    prec_t = -2 * np.floor(np.log10(uvdata._time_array.tols[-1])).astype(int)
    prec_b = 8
    ref_blts = np.array(["{1:.{0}f}_".format(prec_t, blt[0])+str(blt[1]).zfill(prec_b) for blt in zip(uvdata.time_array, uvdata.baseline_array)])

    ref_freq = np.copy(uvdata.freq_array)

    # Iterate over all files and load - this is because of a check 
    # that pyuvdata does when loading multiple arrays at once, which
    # throws an error for uvw_array not being float64 (it's float32)
    uvdata_to_append = []
    for f in fname[1:]:
        uvdataf = UVData()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"key []* is longer than 8 characters[]*")
            warnings.filterwarnings("ignore", message=r"Telescope []* is not in known_telescopes[]*")
            # keep_all_metadata removes the unused antennas
            uvdataf.read(f, file_type='uvh5', antenna_names=antenna_list, keep_all_metadata=False,
                    run_check=False)
        uvdataf.uvw_array = uvdataf.uvw_array.astype(np.float64)

        # Compare baseline-time arrays
        add_blts = np.array(["{1:.{0}f}_".format(prec_t, blt[0])+str(blt[1]).zfill(prec_b) for blt in zip(uvdataf.time_array, uvdataf.baseline_array)])
        if not np.array_equal(add_blts,ref_blts):
            raise ValueError("Baseline-time arrays for files don't match")

        # Make sure we're adding unique frequencies
        if len(np.intersect1d(ref_freq, uvdataf.freq_array)) > 0:
            raise ValueError("Files appear to have repeated frequencies")
        
        uvdata_to_append.append(uvdataf)
        ref_freq = np.concatenate((ref_freq, uvdataf.freq_array))
    
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"key []* is longer than 8 characters[]*")
        uvdata.fast_concat(uvdata_to_append, axis='freq', inplace=True, run_check=False, check_extra=False, run_check_acceptability=False, strict_uvw_antpos_check=False, ignore_name=True)

    # Update frequency ordering
    uvdata.reorder_freqs(channel_order='freq', run_check=False)

    # Name telescope
    if telescope_pos is not None:
        uvdata.telescope_name = telescope_pos.info.name

    # Rename antennas to differentiate from index number more clearly
    # Pyuvdata 3.2+ requires using the underlying _antenna_names.value
    try:
        # Try direct assignment (older pyuvdata)
        current_names = uvdata.antenna_names
        uvdata.antenna_names = ['pad'+n for n in current_names]
    except (AttributeError, TypeError):
        # Pyuvdata 3.2+ approach: access via underlying parameter
        if hasattr(uvdata, '_antenna_names') and uvdata._antenna_names.value is not None:
            current_names = uvdata._antenna_names.value
            uvdata._antenna_names.value = np.array(['pad'+n for n in current_names])
        else:
            warnings.warn("Could not rename antenna_names - UVData object may not be fully initialized")

    return uvdata

def compute_pointing(uvdata: UVData, telescope_pos: EarthLocation):
    """Determine where the telescope was pointed in RA/Dec for each visibility
    
    Gets the time information from the UVData instance and converts that to
    RA assuming the telescope is pointed at hour-angle=0 and the declination
    specified in 'phase_center_dec'. 

    Arguments
    ---------
    uvdata: UVData
        pyuvdata.UVData instance containing the relevant data
    telescope_pos: EarthLocation
        astropy.coordinates.EarthLocation instance describing the 
        location of the telescope
    Returns
    -------
    ptcoords: SkyCoord
        astropy.coordinates.SkyCoord instance containing the pointing
        information for every visibility in uvdata
    """

    # Get pointing information:
    pt_dec = uvdata.extra_keywords['phase_center_dec'] * u.rad

    # Do calculations on unique times - this is faster because of astropy overheads
    utime, uind = np.unique(uvdata.time_array, return_inverse=True)
    utime = Time(utime, format='jd')

    coords = [HADec(ha=0.*u.rad, dec=pt_dec, location=telescope_pos, obstime=t) for t in utime]
    coords = [c.transform_to(ICRS()) for c in coords]

    pt_dec = np.array([c.dec.rad for c in coords]) * u.rad
    pt_ra = np.array([c.ra.rad for c in coords]) * u.rad

    # Converts back to covering all values
    pt_coords = SkyCoord(pt_ra[uind], pt_dec[uind])

    return pt_coords

def set_phases(uvdata: UVData, field_name: str, telescope_pos: EarthLocation, verbose: bool):
    """Determine the pointing of the telescope and set the uvw array to match
    
    Arguments
    ---------
    uvdata: UVData
        pyuvdata.UVData instance containing the relevant data
    field_name : str
        Name of the field
    telescope_pos: EarthLocation
        astropy.coordinates.EarthLocation instance describing the 
        location of the telescope
    Returns
    -------
    uvdata: UVData
        Same pyuvdata.UVData instance - data will be phased to pointing
        direction
    """

    if verbose:
        print("Setting coordinate and uvw information")

    # Determine unique pointing positions:
    vis_coords = compute_pointing(uvdata, telescope_pos)
    utime, uind, uinvert = np.unique(uvdata.time_array, return_index=True, return_inverse=True)
    ucoord = vis_coords[uind]
    ucoord = ucoord[np.argsort(utime)]

    # Format for naming fields:
    if field_name is None:
        field_name = 'drift_ra{}'
    else:
        field_name = field_name + '_drift_ra{}'

    # Iterate through the unique positions, select all data at that position, and update the 
    # phase catalog and uvw information
    for i, center in enumerate(ucoord):

        # Create the catalog entry
        ra_hr = center.ra.to_string(u.hour, precision=0)
        new_cat_id = uvdata._add_phase_center(cat_name=field_name.format(ra_hr), cat_type='sidereal', cat_lon=center.ra.rad, cat_lat=center.dec.rad, cat_frame='icrs', force_update=False)

        # Select data
        selection = np.nonzero((vis_coords.ra.rad==center.ra.rad) & (vis_coords.dec.rad==center.dec.rad))

        # Compute apparent coordinates and position angle for frame
        # Pyuvdata 3.2+ removed calc_app_coords; use astropy directly for sidereal sources
        if hasattr(uvutils, 'calc_app_coords'):
            # Older pyuvdata versions
            new_app_ra, new_app_dec = uvutils.calc_app_coords(
                uvdata.phase_center_catalog[new_cat_id]["cat_lon"],
                uvdata.phase_center_catalog[new_cat_id]["cat_lat"],
                coord_frame=uvdata.phase_center_catalog[new_cat_id]["cat_frame"],
                coord_epoch=uvdata.phase_center_catalog[new_cat_id]["cat_epoch"],
                coord_times=uvdata.phase_center_catalog[new_cat_id]["cat_times"],
                coord_type=uvdata.phase_center_catalog[new_cat_id]["cat_type"],
                time_array=uvdata.time_array[selection],
                lst_array=uvdata.lst_array[selection],
                pm_ra=uvdata.phase_center_catalog[new_cat_id]["cat_pm_ra"],
                pm_dec=uvdata.phase_center_catalog[new_cat_id]["cat_pm_dec"],
                vrad=uvdata.phase_center_catalog[new_cat_id]["cat_vrad"],
                dist=uvdata.phase_center_catalog[new_cat_id]["cat_dist"],
                telescope_loc=uvdata.telescope_location_lat_lon_alt,
                telescope_frame=uvdata._telescope_location.frame,
            )
        else:
            # Pyuvdata 3.2+: compute apparent coords with astropy
            # For sidereal sources without proper motion, apparent coords ≈ ICRS coords
            cat_coord = SkyCoord(
                ra=uvdata.phase_center_catalog[new_cat_id]["cat_lon"] * u.rad,
                dec=uvdata.phase_center_catalog[new_cat_id]["cat_lat"] * u.rad,
                frame='icrs'
            )
            # Apparent coords at each time (simple approach for drift scans)
            new_app_ra = np.full(len(selection[0]), cat_coord.ra.rad)
            new_app_dec = np.full(len(selection[0]), cat_coord.dec.rad)
        
        if hasattr(uvutils, 'calc_frame_pos_angle'):
            new_frame_pa = uvutils.calc_frame_pos_angle(
                uvdata.time_array[selection],
                new_app_ra,
                new_app_dec,
                uvdata.telescope_location_lat_lon_alt,
                uvdata.phase_center_catalog[new_cat_id]["cat_frame"],
                ref_epoch=uvdata.phase_center_catalog[new_cat_id]["cat_epoch"],
                telescope_frame=uvdata._telescope_location.frame,
            )
        else:
            # Pyuvdata 3.2+: frame position angle calculation
            # For equatorial frames, PA ≈ 0
            new_frame_pa = np.zeros(len(selection[0]))

        # Calculate new uvw coordinates from the antenna positions plus the pointing
        new_uvw = uvutils.calc_uvw(
            app_ra=new_app_ra,
            app_dec=new_app_dec,
            frame_pa=new_frame_pa,
            lst_array=uvdata.lst_array[selection],
            use_ant_pos=True,
            antenna_positions=uvdata.antenna_positions,
            antenna_numbers=uvdata.antenna_numbers,
            ant_1_array=uvdata.ant_1_array[selection],
            ant_2_array=uvdata.ant_2_array[selection],
            telescope_lat=uvdata.telescope_location_lat_lon_alt[0],
            telescope_lon=uvdata.telescope_location_lat_lon_alt[1],
        )

        # Set all of this information for the selected data    
        uvdata.uvw_array[selection] = new_uvw
        uvdata.phase_center_app_ra[selection] = new_app_ra
        uvdata.phase_center_app_dec[selection] = new_app_dec
        uvdata.phase_center_frame_pa[selection] = new_frame_pa
        uvdata.phase_center_id_array[selection] = new_cat_id

    uvdata._clear_unused_phase_centers()

    return uvdata

def make_calib_model(
        uvdata: UVData, 
        calib_ra: u.Quantity, 
        calib_dec: u.Quantity, 
        calib_flux_jy: float, 
        telescope_pos: EarthLocation = loc_dsa110, 
        calib_sidx: float = None, 
        calib_sidx_f0_ghz: float = None, 
        calib_epoch='J2000.0', 
        beam_function=pb_dsa110,
        verbose=False
        ):
    """Make a model for a point source by copying uvdata and replacing the visibilities with the model flux"""

    if calib_ra is None or calib_dec is None or calib_flux_jy is None:
        if calib_ra is not None or calib_dec is not None or calib_flux_jy is not None:
            raise RuntimeError("calib_ra, calib_dec, and calib_flux_jy must all be specified if a calibrator is used")
        return None

    # Set up so that we can have mulitple sources
    # If things aren't specified as a list - make them all into lists
    if not isinstance(calib_ra, list) or not isinstance(calib_dec, list) or not isinstance(calib_flux_jy, (list,np.ndarray)):
        # If some things aren't lists but others are, raise an error
        if isinstance(calib_ra, list) or isinstance(calib_dec, list) or isinstance(calib_flux_jy, (list,np.ndarray)):
            raise ValueError("All of calib_ra, calib_dec, calib_flux_jy must be specified as either single values or lists")
        if isinstance(calib_sidx, (list,np.ndarray)) or isinstance(calib_sidx_f0_ghz, (list,np.ndarray)):
            raise ValueError("Single calibrator position/flux and multiple spectral indices not supported")
        # Convert everything to a list
        calib_ra = [calib_ra]
        calib_dec = [calib_dec]
        calib_flux_jy = [calib_flux_jy]
    
    elif not calib_sidx is None and not isinstance(calib_sidx, (list,np.ndarray)):
        raise ValueError("Multiple calibrator position/flux and single spectral indices not supported")
    elif not calib_sidx_f0_ghz is None and not isinstance(calib_sidx_f0_ghz, (list,np.ndarray)):
        raise ValueError("Multiple calibrator position/flux and single spectral indices not supported")

    # Handle that don't have to be specified on input:
    if calib_sidx is None:
        calib_sidx = [None for _ in range(len(calib_ra))]
    if calib_sidx_f0_ghz is None:
        calib_sidx_f0_ghz = [None for _ in range(len(calib_ra))]

    if isinstance(calib_epoch, str):
        calib_epoch = [calib_epoch for _ in range(len(calib_ra))]
    elif not isinstance(calib_epoch, (list,np.ndarray)):
        raise ValueError("calib_epoch input not recognized")
    elif len(calib_epoch) != len(calib_ra):
        raise ValueError("Must specify either single calib_epoch or a list with one value per calibrator source")

    if np.any(np.array([len(calib_ra),len(calib_dec),len(calib_flux_jy),len(calib_sidx),len(calib_sidx_f0_ghz),len(calib_epoch)]) != len(calib_ra)):
        raise ValueError("all calibrator information must have the same length")

    if verbose:
        print("Generating calibrator model...")

    # Make a new dataset by copying the old one
    uvcalib = uvdata.copy()
    uvcalib.data_array[:] = 0+0j

    # Iterate through calibrators
    for ra, dec, flux, epoch, sidx, sidx_f0, i in zip(calib_ra, calib_dec, calib_flux_jy, calib_epoch, calib_sidx, calib_sidx_f0_ghz, np.arange(len(calib_ra))):
        # Phase uvcalib to the calibrator position
        uvcalib.phase(ra.rad, dec.rad, epoch=epoch, phase_frame="icrs", cat_name=f'tmp_calib_{i}')

        # Set all visibilities to have calib_flux_jy
        if sidx is not None:
            if sidx_f0 is None:
                raise RuntimeError("calib_sidx_f0_ghz must be specified if calib_sidx is used")

            # freq is the 2nd axis (base 0)
            freq_scale = (uvcalib.freq_array.reshape(1,1,-1,1)/1e9 / sidx_f0)**-sidx

        else:
            freq_scale = np.ones((1,1,len(uvcalib.freq_array.flatten()),1))

        # # If a spectral index is provided apply it
        # if calib_sidx is not None:
        #     if calib_sidx_f0_ghz is None:
        #         raise RuntimeError("calib_sidx_f0_ghz must be specified if calib_sidx is used")

        #     # freq is the 2nd axis (base 0)
        #     freq_scale = (uvcalib.freq_array/1e9 / calib_sidx_f0_ghz)**-calib_sidx
        #     uvcalib.data_array = uvcalib.data_array * freq_scale.reshape(1,1,-1,1)

        # Compute the beam response and apply it -
        # Determine radial distance from calibrator to pointing center as a function of time
        cal_coords = SkyCoord(ra, dec, equinox=epoch)

        vis_coords = compute_pointing(uvcalib, telescope_pos)
        utime, uind, uinvert = np.unique(uvcalib.time_array, return_index=True, return_inverse=True)
        ucoord = vis_coords[uind]

        dist = ucoord.separation(cal_coords).to(u.rad).value
        dist = dist[uinvert]

        # Apply beam model along axis 0 of data_array
        attenuation = beam_function(dist.astype(np.complex64), uvcalib.freq_array.astype(np.complex64)/1e9)
        # uvcalib.data_array = uvcalib.data_array * attenuation

        uvcalib.data_array += (flux+0j) * freq_scale.reshape(1,1,-1,1) * attenuation

    # Phase all data back to desired centers
    # Use phase center id array and catalog entries from uvdata 
    # so that we don't need to worry about making other copies
    for center_id in np.unique(uvdata.phase_center_id_array):
        cat = uvdata.phase_center_catalog[center_id]
        uvcalib.phase(cat['cat_lon'], cat['cat_lat'], cat_name=cat['cat_name'], epoch=cat['cat_epoch'], phase_frame=cat['cat_frame'], select_mask=uvdata.phase_center_id_array==center_id)
    
    uvcalib.phase_center_id_array = np.copy(uvdata.phase_center_id_array)
    uvcalib.phase_center_catalog = uvdata.phase_center_catalog.copy()

    return uvcalib

def write_ms(uvdata: "UVData", uvcalib: "UVData", msname: "str", protect_files: bool, append_coords: bool, verbose: bool) -> None:
    """Write a UVData object to a ms.

    Arguments
    ---------
    uvdata: UVData
        pyuvdata.UVData instance containing the relevant data
    uvcalib: UVData or None
        pyuvdata.UVData instance containing model visibilities - pass
        None if no model is desired
    msname: str
        Path to save the file in, up to a file name prefix. E.g. to 
        save a file as /data/test_ms_raXX_decXX.ms give arguments
        msname='/data/test_ms' and append_coords=True
    protect_files: bool
        If True, existing files won't be overwritten and an error will
        be raised. Otherwise files are overwritten
    append_coords: bool
        If True, the approximate coordinates of the observation will be 
        appended to the file name (coordinates in decimal degrees)
    
    
    """

    if verbose:
        print("Writing measurement set...")

    if append_coords:
        ra = [cat['cat_lon'] for i,cat in uvdata.phase_center_catalog.items()]
        dec = [cat['cat_lat'] for i,cat in uvdata.phase_center_catalog.items()]
        ra = np.mean(ra)*180/np.pi
        dec = np.mean(dec)*180/np.pi
        msname = msname + f"_ra{ra:05.1f}_dec{dec:+05.1f}"

    if os.path.exists(f'{msname}.ms'):
        if not protect_files:
            shutil.rmtree(f'{msname}.ms')
        else:
            raise RuntimeError(f'{msname}.ms already exists')    

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"Writing in the MS file that the units of the data are uncalib, although some CASA process will ignore this and assume the units are all in Jy (or may not know how to handle data in these units).")

        uvdata.write_ms(f'{msname}.ms',
                        run_check=False,
                        force_phase=False,
                        run_check_acceptability=False,
                        strict_uvw_antpos_check=False)

        if uvcalib is not None:
            tables.addImagingColumns(f'{msname}.ms')
            with tables.table(f'{msname}.ms', readonly=False) as tb:
                tb.putcol('MODEL_DATA', np.squeeze(uvcalib.data_array, axis=1))
                tb.putcol('CORRECTED_DATA', tb.getcol('DATA')[:])

    if verbose:
        print("Done.\n")

    return f'{msname}.ms'



# I believe this is no longer needed, leaving it here for now just in case
def phase(uvdata, uvcalib, field_name, telescope_pos, verbose):
    """Phase data to pointing direction"""

    if verbose:
        print("Phasing visibilities to pointing direction...")

    vis_coords = compute_pointing(uvdata, telescope_pos)
    utime, uind, uinvert = np.unique(uvdata.time_array, return_index=True, return_inverse=True)
    ucoord = vis_coords[uind]
    ucoord = ucoord[np.argsort(utime)]

    if field_name is None:
        field_name = 'drift_ra{}'
    else:
        field_name = field_name + '_drift_ra{}'

    if uvcalib is not None:
        for i, center in enumerate(ucoord):
            ra_hr = center.ra.hour
    
            uvcalib.phase(center.ra.rad, center.dec.rad, epoch='J2000', phase_frame='icrs',
                        cat_name=field_name.format(ra_hr), use_ant_pos=True, select_mask=vis_coords==center)

    return uvdata, uvcalib, ucoord


def load_uvh5_file_v1(fname: str, antenna_list: list = None, telescope_pos: EarthLocation = None, verbose = False):
    """Load specific antennas from a uvh5 file or files.

    Loads a specified file or files, extracts the requested antennas, and 
    concatenates them if multiple files exist.

    This is an old version that used pyuvdata's more robust (but redundant
    for dsa110 data) compatibility checking between files. For combining
    16 SPWs it is about a factor of 6 slower.
    
    Arguments
    ---------
    fname: str or list of str
        The path(s) to the hdf5 file(s) to load
    antenna_list : list
        Antennas for which to extract visibilities from the uvh5 file. Default
        is to extract all visibilities in the uvh5 file. Should be given as a list 
        of pad names (e.g. ['pad1', 'pad2', 'pad3']) for the first 3 pads
    telescope_pos : EarthLocation object
        EarthLocation object describing the loction of the telescope

    Returns
    -------
    uvdata: UVData instance
        The loaded data
    """

    if verbose:
        print("Loading data...")

    # Read in the data
    if not isinstance(fname, (list, tuple, np.ndarray)):
        fname = [fname]
    
    uvdata = UVData()

    # Strip 'pad' from antenna names if needed
    if antenna_list is not None:
        antenna_list = [n.strip('pad') for n in antenna_list]

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"key []* is longer than 8 characters[]*")
        warnings.filterwarnings("ignore", message=r"Telescope []* is not in known_telescopes[]*")
        uvdata.read(fname[0], file_type='uvh5', antenna_names=antenna_list,
                    run_check=False)


    # pyuvdata really wants uvw_array to be float64:
    uvdata.uvw_array = uvdata.uvw_array.astype(np.float64)

    # Iterate over all files and load - this is because of a check 
    # that pyuvdata does when loading multiple arrays at once, which
    # throws an error for uvw_array not being float64 (it's float32)
    for f in fname[1:]:
        uvdataf = UVData()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"key []* is longer than 8 characters[]*")
            warnings.filterwarnings("ignore", message=r"Telescope []* is not in known_telescopes[]*")
            uvdataf.read(f, file_type='uvh5', antenna_names=antenna_list,
                    run_check=False)
        uvdataf.uvw_array = uvdataf.uvw_array.astype(np.float64)

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"key []* is longer than 8 characters[]*")
            uvdata.__add__(uvdataf, inplace=True, run_check=False, check_extra=False, run_check_acceptability=False, strict_uvw_antpos_check=False, ignore_name=True)

    # Name telescope
    if telescope_pos is not None:
        uvdata.telescope_name = telescope_pos.info.name

    # Rename antennas to differentiate from index number more clearly
    uvdata.antenna_names = ['pad'+n for n in uvdata.antenna_names]

    return uvdata

