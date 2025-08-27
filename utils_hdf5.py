"""Create a measurement set from a uvh5 file."""
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


from astropy.coordinates import EarthLocation, HADec, SkyCoord, ICRS
import astropy.units as u
import pandas

from importlib.resources import files



# These were defined in dsacalib.constants but are moved here for now
SECONDS_PER_SIDEREAL_DAY = 3600 * 23.9344699

# import casatools as cc
# me = cc.measures()
# ovro_loc = me.observatory("OVRO_MMA")
# OVRO_LON = ovro_loc["m0"]["value"]
# OVRO_LAT = ovro_loc["m1"]["value"]
# OVRO_ALT = ovro_loc["m2"]["value"]

# These are just the result from CASA:
OVRO_LON = -2.064427799136453
OVRO_LAT = 0.6498455107238486
OVRO_ALT = 1188.0519
ovro_mma = EarthLocation(lat=OVRO_LAT*u.rad, lon=OVRO_LON*u.rad, height=OVRO_ALT*u.m)

# Setting as CARMA for now, since CASA seems to handle it better
# DSA-110/DSA-2000/DSA/whatever aren't recognized which breaks things like listobs
# OVRO-MMA is recognized, but the coordinates seem to be wrong, which breaks plotants and listobs
ovro_mma.info.name = 'CARMA' 

# Imports for removed features
# from casatasks import importuvfits
# from casacore.tables import addImagingColumns, table
# import dsautils.dsa_syslog as dsl
# from dsamfs.fringestopping import calc_uvw_blt
# from dsacalib.fringestopping import calc_uvw_interpolate
# from dsacalib.utils import generate_calibrator_source
# from dsacalib.fringestopping import amplitude_sky_model

def uvh5_to_ms(
        fname, msname, append_coords=False, antenna_list=None,
        field_name=None, telescope_pos=ovro_mma,
        calib_ra=None, calib_dec=None, calib_epoch='J2000.0', calib_flux_jy=None, calib_sidx=None, calib_sidx_f0_ghz=None,
        protect_files=False, verbose=False
):
    """
    Converts a uvh5 data to a uvfits file.

    Parameters
    ----------
    fname : str
        The full path to the uvh5 data file.
    msname : str
        The name of the ms to write. Data will be written to `msname`.ms
    append_coords : bool
        If True, the coordinates (in decimal degrees) of the observed field 
        will be appended to the ms name as _raXX.XX-decXX.XX
    antenna_list : list
        Antennas for which to extract visibilities from the uvh5 file. Default
        is to extract all visibilities in the uvh5 file.
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
    # uvdata is a pyuvdata UVData instance, pt_dec, pt_ra are the pointing direction of the array
    # in radians (have units attached), pt_time is the 
    # ra and dec are the ra and to phase to (data isn't yet phased to this)
    uvdata = load_uvh5_file_v2(fname, antenna_list, verbose=verbose)

    # Corrent antenna positions in ITRF coordinates.
    # RK: fairly sure this is redundant and already being handled correctly upstream
    uvdata = set_antenna_positions(uvdata, telescope_pos, verbose=verbose)

    # Some checks and formatting fixes for frequency array - this is a holdover from 
    # original dsa110-calib and hasn't been changed except to make it return uvdata
    # I don't think we actually want it
    # uvdata = fix_descending_missing_freqs(uvdata)

    # Set the UVW coordinates and phase centers
    uvdata, phasecoords = set_phases(uvdata, field_name, telescope_pos, verbose=verbose)

    # Make calibrator model
    uvcalib = make_calib_model_v2(uvdata, calib_ra, calib_dec, calib_flux_jy, telescope_pos, calib_sidx, calib_sidx_f0_ghz, calib_epoch, verbose=verbose)

    # Phase everything
    uvdata, uvcalib, phasecoords = phase_v2(uvdata, uvcalib, field_name, telescope_pos, verbose=verbose)

    # Write the ms
    msname = write_UV_to_ms(uvdata, uvcalib, msname, protect_files, append_coords, phasecoords, verbose=verbose)

    return msname




    # # Load data from HDF5 files:
    # # uvdata is a pyuvdata UVData instance, pt_dec is the pointing declination of the array
    # # ra and dec are the ra and to phase to (data isn't yet phased to this)
    # uvdata, pt_dec, ra, dec = load_uvh5_file(fname, antenna_list, telescope_pos)

    # # Corrent antenna positions in ITRF coordinates.
    # # RK: fairly sure this is redundant and already being handled correctly upstream
    # uvdata = set_antenna_positions(uvdata, telescope_pos)

    # # New phase up - use UVData code for this:
    # uvdata, field_name = phase(uvdata, ra, dec, field_name)
    # # Replaced with above code, no longer bothers with fringstopping stuff:
    # # phase_visibilities(uvdata, ra, dec, fringestop=False, refmjd=None)

    # # Some checks and formatting fixes for frequency array - this is a holdover from 
    # # original dsa110-calib and hasn't been changed except to make it return uvdata
    # uvdata = fix_descending_missing_freqs(uvdata)

    # # Make calibrator model
    # uvcalib = make_calib_model(uvdata, calib_ra, calib_dec, calib_flux_jy, telescope_pos, calib_sidx, calib_sidx_f0_ghz, calib_epoch)

    # # Write the ms
    # write_UV_to_ms(uvdata, uvcalib, msname, protect_files)



# RK - new version that does what we need for imaging
def load_uvh5_file_v2(
        fname: str,
        antenna_list: list = None,
        verbose = False,
    ):
    """Load specific antennas and times for a uvh5 file.
    """

    if verbose:
        print("Loading data...")

    # Read in the data
    if not isinstance(fname, (list, tuple, np.ndarray)):
        fname = [fname]
    
    uvdata = UVData()

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

    # Rename antennas to differentiate from index number more clearly
    uvdata.antenna_names = ['pad'+n for n in uvdata.antenna_names]

    return uvdata

def compute_pointing(
        uvdata: UVData,
        telescope_pos: EarthLocation,
    ):
    """Determine where the telescope was pointed in RA/Dec for each visibility"""

    # Get pointing information:
    pt_dec = uvdata.extra_keywords['phase_center_dec'] * u.rad

    # Do calculations on unique times - this is faster because of astropy overheads
    utime, uind = np.unique(Time(uvdata.time_array, format='jd'), return_inverse=True)
    coords = [HADec(ha=0.*u.rad, dec=pt_dec, location=telescope_pos, obstime=t) for t in utime]
    coords = [c.transform_to(ICRS()) for c in coords]
    pt_dec = np.array([c.dec.rad for c in coords]) * u.rad
    pt_ra = np.array([c.ra.rad for c in coords]) * u.rad
    
    # Converts back to covering all values
    pt_coords = SkyCoord(pt_ra[uind], pt_dec[uind])

    return pt_coords

def set_phases(uvdata, field_name, telescope_pos, verbose):
    """Determine the pointing of the telescope and set the uvw array to match"""

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
        selection = np.nonzero(vis_coords==center)

        # Compute apparent coordinates and position angle for frame        
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
        new_frame_pa = uvutils.calc_frame_pos_angle(
            uvdata.time_array[selection],
            new_app_ra,
            new_app_dec,
            uvdata.telescope_location_lat_lon_alt,
            uvdata.phase_center_catalog[new_cat_id]["cat_frame"],
            ref_epoch=uvdata.phase_center_catalog[new_cat_id]["cat_epoch"],
            telescope_frame=uvdata._telescope_location.frame,
        )

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

    return uvdata, ucoord



# Compute beam attenuation as a function of distance for a taperd beam of 4.7m dishes
# This came from dsacalib code, but doesn't seem to match data. Trying a Gausian instead
# def pb_dsa110(dist, freq, diameter=4.7):
#     lam = 0.299792458 / freq
#     arg = 1.2 * dist.reshape(-1,1,1,1) * diameter / lam.reshape(1,1,-1,1)
#     pb = (np.cos(np.pi * arg) / (1 - 4 * arg**2)) ** 4
#     return pb

def pb_dsa110(dist, freq, diameter=4.7):
    wl = 0.299792458 / freq
    fwhm = 1.2 * wl / diameter
    sigma = fwhm / 2.355
    pb = np.exp(-0.5 * (dist.reshape(-1,1,1,1) / sigma.reshape(1,1,-1,1))**2)
    return pb


def make_calib_model_v2(
        uvdata: UVData, 
        calib_ra: u.Quantity, 
        calib_dec: u.Quantity, 
        calib_flux_jy: float, 
        telescope_pos: EarthLocation, 
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

    if verbose:
        print("Generating calibrator model...")

    # Make a new dataset by copying the old one
    uvcalib = uvdata.copy()

    # Phase this to the calibrator position
    uvcalib.phase(calib_ra.rad, calib_dec.rad, epoch=calib_epoch, phase_frame="icrs", cat_name='tmp_calib', use_ant_pos=False)

    # Set all visibilities to have calib_flux_jy
    uvcalib.data_array[:] = calib_flux_jy + 0j

    # If a spectral index is provided apply it
    if calib_sidx is not None:
        if calib_sidx_f0_ghz is None:
            raise RuntimeError("calib_sidx_f0_ghz must be specified if calib_sidx is used")

        # freq is the 2nd axis (base 0)
        freq_scale = (uvcalib.freq_array/1e9 / calib_sidx_f0_ghz)**-calib_sidx_f0_ghz
        uvcalib.data_array = uvcalib.data_array * freq_scale.reshape(1,1,-1,1)

    # Compute the beam response and apply it -
    # Determine radial distance from calibrator to pointing center as a function of time
    cal_coords = SkyCoord(calib_ra, calib_dec, equinox=calib_epoch)

    vis_coords = compute_pointing(uvcalib, telescope_pos)
    utime, uind, uinvert = np.unique(uvcalib.time_array, return_index=True, return_inverse=True)
    ucoord = vis_coords[uind]
    dist = ucoord.separation(cal_coords).to(u.rad).value
    dist = dist[uinvert]

    # Apply beam model along axis 0 of data_array
    attenuation = beam_function(dist, uvcalib.freq_array/1e9)
    uvcalib.data_array = uvcalib.data_array * attenuation
    
    # No longer doing this, because all phasing happens later
    # # Phase all data back to desired centers
    # for center_id in np.unique(old_centers):
    #     cat_name = uvcalib.phase_center_catalog[center_id]['cat_name']
    #     print(center_id, cat_name)
    #     uvcalib.phase(0, 0, lookup_name=True, cat_name=cat_name, cleanup_old_sources=False, select_mask=old_centers==center_id)

    return uvcalib

    
def phase_v2(uvdata, uvcalib, field_name, telescope_pos, verbose):
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

    # for i, center in enumerate(ucoord):
    #     ra_hr = center.ra.to_string(u.hour, precision=0)

    #     uvdata.phase(center.ra.rad, center.dec.rad, epoch='J2000', phase_frame='icrs',
    #                  cat_name=field_name.format(ra_hr), use_ant_pos=True, select_mask=vis_coords==center)

    if uvcalib is not None:
        for i, center in enumerate(ucoord):
            ra_hr = center.ra.hour
    
            uvcalib.phase(center.ra.rad, center.dec.rad, epoch='J2000', phase_frame='icrs',
                        cat_name=field_name.format(ra_hr), use_ant_pos=True, select_mask=vis_coords==center)

    return uvdata, uvcalib, ucoord

def write_UV_to_ms(uvdata: "UVData", uvcalib: "UVData", msname: "str", protect_files: bool, append_coords: bool, phasecoords, verbose: bool) -> None:
    """Write a UVData object to a ms.
    """

    if verbose:
        print("Writing measurement set...")

    if append_coords:
        ra = np.mean([c.ra.deg for c in phasecoords])
        dec = np.mean([c.dec.deg for c in phasecoords])
        msname = msname + f"_ra{ra:07.3f}_dec{dec:+07.3f}"

    if os.path.exists(f'{msname}.ms'):
        if not protect_files:
            shutil.rmtree(f'{msname}.ms')
        else:
            raise RuntimeError(f'{msname}.ms already exists')    

    uvdata.write_ms(f'{msname}.ms',
#                    spoof_nonessential=True, # Not sure what this does, not in docs for latest version
                    run_check=False,
                    force_phase=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False)

    if uvcalib is not None:
        tables.addImagingColumns(f'{msname}.ms')
        with tables.table(f'{msname}.ms', readonly=False) as tb:
            tb.putcol('MODEL_DATA', np.squeeze(uvcalib.data_array, axis=1))
            tb.putcol('CORRECTED_DATA', tb.getcol('DATA')[:])

    return f'{msname}.ms'

# Make these paths work from anywhere
#packagepath = files('dsa110hipipeline')
#antposfile = packagepath.joinpath('resources','DSA110_Station_Coordinates.csv')

def get_lonlat(csvfile=antposfile, headerline=5, defaultheight=1182.6000):
    """ Read positions of all antennas from DSA110 CSV file.
    """

    tab       = pandas.read_csv(csvfile, header=headerline)
    stations  = tab['Station Number']
    latitude  = tab['Latitude']
    longitude = tab['Longitude']
    height = tab['Elevation (meters)']

    df = pandas.DataFrame()
    df['Station Number'] = [int(station.split('-')[1]) for station in stations]
    df['Latitude'] = latitude
    df['Longitude'] = longitude
    df['Height (m)'] = height
    df['Height (m)'] = np.where(np.isnan(df['Height (m)']), defaultheight, df['Height (m)'])
    for st_no in ['200E', '200W']:
        idx_to_drop = np.where(df['Station Number'] == st_no)[0]
        if len(idx_to_drop > 0):
            df.drop(idx_to_drop[0], inplace=True)
    df = df.astype({'Station Number': np.int32})
    df.sort_values(by=['Station Number'], inplace=True)
    df.set_index('Station Number', inplace=True)
    return df

def get_itrf(telescope_pos, csvfile=antposfile,
             return_all_stations=True):
    """Read positions of all antennas from DSA110 CSV file and 
    convert to ITRF coordinates. Only provides active stations."""

    df = get_lonlat(csvfile)
    locations = EarthLocation(lat=df['Latitude']*u.degree, lon=df['Longitude']*u.degree, height=df['Height (m)']*u.m)
    df['x_m'] = locations.x.to_value(u.m)
    df['y_m'] = locations.y.to_value(u.m)
    df['z_m'] = locations.z.to_value(u.m)

    df['dx_m'] = (locations.x-telescope_pos.x).to_value(u.m)
    df['dy_m'] = (locations.y-telescope_pos.y).to_value(u.m)
    df['dz_m'] = (locations.z-telescope_pos.z).to_value(u.m)

    return df

def set_antenna_positions(uvdata: UVData, telescope_pos: EarthLocation, verbose: bool) -> np.ndarray:
    """Set the antenna positions in uvdata.

    This should already be done by the writer but for some reason they
    are being converted to ICRS, so we set them using antpos here.
    """

    if verbose:
        print("setting antenna positions...")
    # Get correct ITRF positions of all antennas
    df_itrf = get_itrf(telescope_pos)

    # Print message if length of poisitons array doesn't match uvdata antenna list
    # RPK: chaning this to be an error
    if len(df_itrf['x_m']) != uvdata.antenna_positions.shape[0]:
        message = 'Mismatch between antennas in current environment ' +\
            f'({len(df_itrf["x_m"])}) and correlator environment ' +\
            f'({uvdata.antenna_positions.shape[0]})'
        raise RuntimeError(message)

    # Antenna positions relative to ITRF coords of array center):
    uvdata.antenna_positions = np.array([
        df_itrf['dx_m'],
        df_itrf['dy_m'],
        df_itrf['dz_m']
    ]).T

    uvdata.telescope_location = np.array([telescope_pos.x.to_value(u.m),telescope_pos.y.to_value(u.m),telescope_pos.z.to_value(u.m)])
    uvdata.telescope_name = telescope_pos.info.name

    return uvdata


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
        uvdata.freq_array = uvdata.freq_array[:, ::-1]
        uvdata.data_array = uvdata.data_array[:, :, ::-1, :]
        freq = uvdata.freq_array.squeeze()

    # TODO: Need to update this for missing on either side as well
    uvdata.channel_width = np.abs(uvdata.channel_width)
    # Are there missing channels?
    if not np.all(np.diff(freq) - uvdata.channel_width < 1e-5):
        # There are missing channels!
        nfreq = int(np.rint(np.abs(freq[-1] - freq[0]) / uvdata.channel_width + 1))
        freq_out = freq[0] + np.arange(nfreq) * uvdata.channel_width
        existing_idxs = np.rint((freq - freq[0]) / uvdata.channel_width).astype(int)
        data_out = np.zeros((uvdata.Nblts, uvdata.Nspws, nfreq, uvdata.Npols),
                            dtype=uvdata.data_array.dtype)
        nsample_out = np.zeros((uvdata.Nblts, uvdata.Nspws, nfreq, uvdata.Npols),
                               dtype=uvdata.nsample_array.dtype)
        flag_out = np.zeros((uvdata.Nblts, uvdata.Nspws, nfreq, uvdata.Npols),
                            dtype=uvdata.flag_array.dtype)
        data_out[:, :, existing_idxs, :] = uvdata.data_array
        nsample_out[:, :, existing_idxs, :] = uvdata.nsample_array
        flag_out[:, :, existing_idxs, :] = uvdata.flag_array
        # Now write everything
        uvdata.Nfreqs = nfreq
        uvdata.freq_array = freq_out[np.newaxis, :]
        uvdata.data_array = data_out
        uvdata.nsample_array = nsample_out
        uvdata.flag_array = flag_out

    return uvdata
