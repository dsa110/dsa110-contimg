"""to_pyuvdata: Convert data into pyuvdata standards."""

# Basic imports
import warnings
from datetime import datetime

# Basic science stuff
import h5py
import numpy as np
import pandas as pd
import pyuvdata
import pyuvdata.utils as uvutils
from astropy.coordinates import AltAz, Angle, EarthLocation, get_sun

# Astropy + pyuvdata
from astropy.time import Time
from loguru import logger
from pyuvdata import UVData

from ska_ost_low_uv import __version__
from ska_ost_low_uv.datamodel import UVX
from ska_ost_low_uv.io.metadata import load_observation_metadata
from ska_ost_low_uv.utils import get_resource_path, load_yaml


def phase_to_sun(uv: UVData, t0: Time) -> UVData:
    """Phase UVData to sun, based on timestamp.

    Computes the sun's RA/DEC in GCRS for the given time, then applies phasing.
    This will then recompute UVW and apply phase corrections to data.

    Note:
        Phase center is set to 'sidereal', i.e. fixed RA and DEC, not 'ephem', so that
        we can apply calibration solutions taken at time t0 (where the Sun was when calibration
        was run, not where it is now!)

    Args:
        uv (UVData): UVData object to apply phasing to (needs to have a phase center defined)
        t0 (Time): Astropy Time() to use to compute Sun's RA/DEC

    Returns:
        uv (UVData): Same UVData as input, but with new phase center applied
    """
    sun = get_sun(t0)

    # sun will be returned in GCRS (Geocentric)
    # Need to use GCRS, not ICRS!
    uv.phase(ra=sun.ra.rad, dec=sun.dec.rad, cat_type='sidereal', cat_name=f'sun_{t0.isot}')
    return uv


def uvx_to_pyuvdata(
    uvx: UVX, phase_to_t0: bool = True, start_int: int = 0, max_int: int = None
) -> pyuvdata.UVData:
    """Convert UVX visibility format into UVData object.

    Args:
        uvx (UVX):          UVX object to convert
        phase_to_t0 (bool): Instead of phasing to Zenith, phase all timestamps to
                            the RA/DEC position of zenith at the first timestamp (t0).
                            This is needed if writing UVFITS files, but not if you
                            are doing snapshot imaging of each timestep. Default True.
        start_int (int):    First integration index to read (allows skipping ahead through file)
        max_int (int):      Maximum number of intergrations to read. Default None (read all)

    Returns:
        uv (pyuvdata.UVData): A UVData object that can be used to create
                              UVFITS/MIRIAD/UVH5/etc files
    """
    # fmt: off
    md = {
        'telescope_name': uvx.name,
        'instrument':     uvx.name,
        'n_integrations': uvx.data.time.shape[0],
        'n_antennas':     uvx.antennas.antenna.shape[0],
        'n_baselines':    uvx.data.baseline.shape[0],
        'n_chans':        uvx.data.frequency.shape[0],
        'n_stokes':       uvx.data.polarization.shape[0],
        'tsamp':          uvx.data.time.attrs['resolution'],
        'channel_width': uvx.data.frequency.attrs['channel_bandwidth'],
        'channel_spacing': uvx.data.frequency.attrs['channel_spacing'],
        'Nspws': 1,
        'Nphase': 1,
        'polarization_type': 'linear_crossed', # [XX, XY, YX, YY]
        'history': f"Generated with {__version__} at {Time(datetime.now()).iso}",
    }
    # fmt: on

    if max_int is None:
        max_int = md['n_integrations'] - start_int

    if max_int < uvx.data.time.shape[0]:
        md['n_integrations'] = max_int

    # Telescope location
    # Also instantiate an EarthLocation observer for LST / Zenith calcs
    telescope_earthloc = uvx.origin
    x, y, z = uvx.origin.to_geocentric()
    np.array([x.value, y.value, z.value])

    # Load baselines and antenna locations (ECEF)

    # fmt: off
    telescope_params = {
        'name':              md['telescope_name'],
        'instrument':        md['instrument'],
        'location':          telescope_earthloc,
        'antenna_positions': uvx.antennas.ecef.values,
        'antenna_names':     uvx.antennas.identifier.values.astype('str'),
        'antenna_numbers':   np.array(list(uvx.antennas.antenna.values), dtype='int32'),
    }
    # fmt: on

    telescope = pyuvdata.Telescope.new(**telescope_params)

    # Polarization axis
    # fmt: off
    _pol_types = {
        'stokes':           np.array([ 1,  2,  3,  4]),
        'linear':           np.array([-5, -6, -7, -8]),
        'linear_crossed':   np.array([-5, -7, -8, -6]),   # Note: must be converted to linear for pyuvdata
        'circular':         np.array([-1, -2, -3, -4]),
    }

    uvd_params = {
     'freq_array':          uvx.data.frequency.values,
     'times':               uvx.timestamps.jd,                    # Must be Julian Date
     'polarization_array':  _pol_types['linear_crossed'],
     'telescope':           telescope,
     'history':             md['history'],
     'vis_units':           uvx.data.attrs.get('unit', 'uncalib')
     }
    # fmt: off


    # Create empty UVData object
    # fmt: on
    uv = pyuvdata.UVData.new(**uvd_params)

    # Add in station rotation - note this is not currently part of pyuvdata spec
    uv.receptor_angle = uvx.antennas.attrs['array_rotation_angle']
    # fmt: off

    # Time axis
    t = uvx.timestamps
    t0 = t[0]

    # Reference date RDATE and corresponding Greenwich sidereal time at midnight GST0
    # See https://github.com/RadioAstronomySoftwareGroup/pyuvdata/blob/f703a985869b974892fc4732910c83790f9c72b4/pyuvdata/uvdata/uvfits.py#L1305C13-L1305C85
    # See https://github.com/RadioAstronomySoftwareGroup/pyuvdata/blob/f703a985869b974892fc4732910c83790f9c72b4/pyuvdata/uvdata/uvfits.py#L1318C20-L1318C21
    # See https://github.com/RadioAstronomySoftwareGroup/pyuvdata/blob/f703a985869b974892fc4732910c83790f9c72b4/pyuvdata/uvdata/uvfits.py#L1323C40-L1323C45
    # See https://github.com/RadioAstronomySoftwareGroup/pyuvdata/blob/f703a985869b974892fc4732910c83790f9c72b4/pyuvdata/uvdata/uvfits.py#L1338C13-L1338C47
    # fmt: off
    rdate_obj      = Time(np.floor(uv.time_array[0]), format='jd', scale='utc')
    uv.rdate       = rdate_obj.strftime('%Y-%m-%d')
    uv.gst0        = float(rdate_obj.sidereal_time('apparent', 'tio').deg)
    uv.dut1        = float(rdate_obj.delta_ut1_utc)
    uv.earth_omega = 360.9856438593
    uv.timesys     = 'UTC'
    uv.integration_time = np.zeros_like(uv.time_array) + md['tsamp']
    # fmt: on

    # Compute zenith phase center
    zen_aa = AltAz(
        alt=Angle(90, unit='degree'),
        az=Angle(0, unit='degree'),
        obstime=t0,
        location=uvx.origin,
    )

    # Add phase center
    # Remove any existing phase centers
    if 0 in uv.phase_center_catalog.keys():
        uv.phase_center_catalog.pop(0)

    phs_id = uv._add_phase_center(
        cat_name=f'zenith_at_jd{t0.jd}',
        cat_type='driftscan',
        cat_lon=zen_aa.alt.rad,
        cat_lat=zen_aa.az.rad,
        cat_frame='altaz',
        cat_epoch='J2000',
        info_source='user',
        force_update=False,
        cat_id=0,
    )

    # Apparent RA and DEC
    # fmt: off
    app_ra   = uv.lst_array
    app_dec  = np.zeros_like(app_ra) + uvx.origin.geodetic.lat.to('rad').value
    frame_pa = uvutils.phasing.calc_frame_pos_angle(
        time_array=uv.time_array,
        app_ra=app_ra,
        app_dec=app_dec,
        telescope_loc=uvx.origin,
        ref_frame='icrs',
        ref_epoch='J2000',
        telescope_frame='itrs',
        ellipsoid='SPHERE',
    )

    uv.phase_center_id_array = np.zeros(uv.Nblts, dtype='int32') + phs_id
    uv.phase_center_app_ra   = np.zeros(uv.Nblts, dtype='float64') + app_ra
    uv.phase_center_app_dec  = np.zeros(uv.Nblts, dtype='float64') + app_dec
    uv.phase_center_frame_pa = np.zeros(uv.Nblts, dtype='float64') + frame_pa
    # fmt: on

    # Next, load up data
    # Data have shape (time, freq, baseline, pol)
    # Need to flatten to (nbaseline * nint (Nblts), nspw, nchan, npol)
    n_int = md['n_integrations']
    uv.data_array = uvx.data[start_int : (start_int + n_int)].values
    uv.data_array = np.transpose(uv.data_array, (0, 2, 1, 3))  # tfbp -> tbfp
    uv.data_array = uv.data_array.reshape((uv.Nblts, uv.Nfreqs, uv.Npols))

    # HDF5 data are written as XX, XY, YX, YY (AIPS codes -5, -7, -8, -6)
    if md['polarization_type'].lower() == 'linear_crossed':
        # AIPS expects -5 -6 -7 -8, so we need to remap pols
        pol_remap = [0, 3, 1, 2]
        uv.data_array = uv.data_array[..., pol_remap]
        uv.polarization_array = _pol_types['linear']

    # Add optional arrays
    uv.flag_array = np.zeros_like(uv.data_array, dtype='bool')
    uv.nsample_array = np.ones_like(uv.data_array, dtype='float32')

    # Finally, compute zenith UVW coordinates
    # Miriad convention is xyz(ant2) - xyz(ant1)
    # We assume numbers start at 1, not 0
    uv.uvw_array = np.zeros((uv.Nblts, 3), dtype='float64')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        # Pyuvdata's UVFITS writer needs data to be phased
        # to the zenith of the first timestamp. So, we do this by default
        if phase_to_t0:
            phase_time = Time(uv.time_array[0], format='jd')
            uv.phase_to_time(phase_time, use_ant_pos=True)
        else:
            uv.set_uvws_from_antenna_positions(update_vis=False)

    return uv


def hdf5_to_pyuvdata(
    filename: str,
    yaml_config: str = None,
    telescope_name: str = None,
    phase_to_t0: bool = True,
    start_int: int = 0,
    max_int: int = None,
) -> pyuvdata.UVData:
    """Convert MCCS HDF5 correlator output to UVData object.

    Args:
        filename (str):     Name of file to open
        yaml_config (str):  YAML configuration file with basic telescope info.
                            See README for more information.
        telescope_name (str): Name of telescope/station. If set, will attempt to use
                              internal antenna location files.
        phase_to_t0 (bool): Instead of phasing to Zenith, phase all timestamps to
                            the RA/DEC position of zenith at the first timestamp (t0).
                            This is needed if writing UVFITS files, but not if you
                            are doing snapshot imaging of each timestep. Default True.
        start_int (int):    First integration index to read (allows skipping ahead through file)
        max_int (int):      Maximum number of intergrations to read. Default None (read all)

    Returns:
        uv (pyuvdata.UVData): A UVData object that can be used to create
                              UVFITS/MIRIAD/UVH5/etc files
    """
    # Load metadata
    md = load_observation_metadata(filename, yaml_config, use_config=telescope_name)

    pyuv_md = load_yaml(get_resource_path('config/pyuvdata_config.yaml'))
    md.update(pyuv_md)

    # Create empty UVData object
    uv = pyuvdata.UVData()

    if max_int is None:
        max_int = md['n_integrations'] - start_int

    if max_int < md['n_integrations']:
        md['n_integrations'] = max_int

    # Telescope location
    # Also instantiate an EarthLocation observer for LST / Zenith calcs
    xyz = np.array(list(md[f'telescope_ECEF_{q}'] for q in ('X', 'Y', 'Z')))
    telescope_earthloc = EarthLocation.from_geocentric(*xyz, unit='m')
    uv.telescope.location = telescope_earthloc

    # Load baselines and antenna locations (ENU)
    df_ant = pd.read_csv(md['antenna_locations_file'], delimiter=' ')
    pd.read_csv(md['baseline_order_file'], delimiter=' ')

    # Convert ENU locations to 'local' ECEF
    # Following https://github.com/RadioAstronomySoftwareGroup/pyuvdata/blob/f703a985869b974892fc4732910c83790f9c72b4/pyuvdata/uvdata/mwa_corr_fits.py#L1456
    antpos_ENU = np.column_stack((df_ant['E'], df_ant['N'], df_ant['U']))
    antpos_ECEF = uvutils.ECEF_from_ENU(antpos_ENU, telescope_earthloc) - xyz

    # fmt: off
    telescope_params = {
        'name':              md['telescope_name'],
        'instrument':        md['instrument'],
        'location':          telescope_earthloc,
        'antenna_positions': antpos_ECEF,
        'antenna_names':     df_ant['name'].values.astype('str'),
        'antenna_numbers':   np.array(list(df_ant.index), dtype='int32'),
    }
    # fmt: on

    telescope = pyuvdata.Telescope.new(**telescope_params)

    # Polarization axis
    # fmt: off
    _pol_types = {
        'stokes':           np.array([ 1,  2,  3,  4]),
        'linear':           np.array([-5, -6, -7, -8]),
        'linear_crossed':   np.array([-5, -7, -8, -6]),   # Note: must be converted to linear for pyuvdata
        'circular':         np.array([-1, -2, -3, -4]),
    }


    # Frequency axis
    f0 = md['channel_spacing'] * md['channel_id']
    freq_array = np.array([f0])

    # Time axis
    # Compute JD from unix time and LST - we can do this as we set an EarthLocation on t0 Time
    _t = np.arange(md['n_integrations'], dtype='float64') * md['tsamp'] + md['ts_start']
    _t += (
        md['tsamp'] / 2
    )  # Time array is based on center of integration, so add tdelt / 2
    _t += start_int * md['tsamp']  # Add time offset if not reading from t0

    t = Time(_t, format='unix', location=telescope_earthloc)
    t0 = t[0]

    uvd_params = {
     'freq_array':          freq_array,
     'times':               t.jd,                    # Must be Julian Date
     'polarization_array':  _pol_types[md['polarization_type'].lower()],
     'telescope':           telescope,
     'history':             md['history'],
     'vis_units':           md['vis_units']
     }
    # fmt: off

    # fmt: on
    # Create empty UVData object
    uv = pyuvdata.UVData.new(**uvd_params)

    # NOTE: channel_spacing is used for frequency delta. channel_width exists in metadata too as oversampled PFB
    uv.channel_width = np.repeat(md['channel_spacing'], uv.Nfreqs)

    # Add in station rotation - note this is not currently part of pyuvdata spec
    uv.receptor_angle = md['receptor_angle']

    # Reference date RDATE and corresponding Greenwich sidereal time at midnight GST0
    # See https://github.com/RadioAstronomySoftwareGroup/pyuvdata/blob/f703a985869b974892fc4732910c83790f9c72b4/pyuvdata/uvdata/uvfits.py#L1305C13-L1305C85
    # fmt: off
    rdate_obj       = Time(uv.time_array[0], format='jd', scale='utc', location=t0.location)
    uv.rdate        = rdate_obj.strftime('%Y-%m-%d')
    uv.gst0         = float(rdate_obj.sidereal_time('apparent', 'tio').deg)
    uv.dut1         = float(rdate_obj.delta_ut1_utc)
    uv.earth_omega  = 360.9856438593
    uv.timesys      = 'UTC'
    uv.integration_time = np.zeros_like(uv.time_array) + md['tsamp']
    # fmt: on

    # Compute zenith phase center
    zen_aa = AltAz(
        alt=Angle(90, unit='degree'),
        az=Angle(0, unit='degree'),
        obstime=t0,
        location=telescope_earthloc,
    )

    # Add phase center
    # Remove any existing phase centers
    if 0 in uv.phase_center_catalog.keys():
        uv.phase_center_catalog.pop(0)

    phs_id = uv._add_phase_center(
        cat_name=f'zenith_at_jd{t0.jd}',
        cat_type='driftscan',
        cat_lon=zen_aa.alt.rad,
        cat_lat=zen_aa.az.rad,
        cat_frame='altaz',
        cat_epoch='J2000',
        info_source='user',
        force_update=False,
        cat_id=0,
    )

    # Apparent RA and DEC
    # fmt: off
    app_ra   = uv.lst_array
    app_dec  = np.zeros_like(app_ra) + telescope_earthloc.geodetic.lat.to('rad').value
    frame_pa = uvutils.phasing.calc_frame_pos_angle(
        time_array=uv.time_array,
        app_ra=app_ra,
        app_dec=app_dec,
        telescope_loc=telescope_earthloc,
        ref_frame='icrs',
        ref_epoch='J2000',
        telescope_frame='itrs',
        ellipsoid='SPHERE',
    )

    uv.phase_center_id_array = np.zeros(uv.Nblts, dtype='int32') + phs_id
    uv.phase_center_app_ra   = np.zeros(uv.Nblts, dtype='float64') + app_ra
    uv.phase_center_app_dec  = np.zeros(uv.Nblts, dtype='float64') + app_dec
    uv.phase_center_frame_pa = np.zeros(uv.Nblts, dtype='float64') + frame_pa
    # fmt: on

    # Next, load up data
    with h5py.File(filename, mode='r') as datafile:
        # Data have shape (nint, nbaseline, nchan, npol)
        # Need to flatten to (nbaseline * nint (Nblts), nchan, npol)
        n_int = md['n_integrations']
        data = datafile['correlation_matrix']['data'][start_int : (start_int + n_int)]
        # uv.data_array = np.transpose(data, (0, 2, 1, 3))
        uv.data_array = data.reshape((uv.Nblts, uv.Nfreqs, uv.Npols))

        # HDF5 data are written as XX, XY, YX, YY (AIPS codes -5, -7, -8, -6)
        if md['polarization_type'].lower() == 'linear_crossed':
            # AIPS expects -5 -6 -7 -8, so we need to remap pols
            # we can also do the optional transpose to swap XY and YX here
            pol_remap = [0, 3, 1, 2]
            logger.info(f'Remapping {md["polarization_type"]} to FITS standard')
            if md['transpose_hdf5']:
                logger.info('Transposing cross-pol terms')
                pol_remap = [0, 3, 2, 1]
            uv.data_array = uv.data_array[..., pol_remap]
            uv.polarization_array = _pol_types['linear']

        if md['conjugate_hdf5']:
            logger.info('Conjugating data')
            uv.data_array = np.conj(uv.data_array)

        # Add optional arrays
        uv.flag_array = np.zeros_like(uv.data_array, dtype='bool')
        uv.nsample_array = np.ones_like(uv.data_array, dtype='float32')

    # Finally, compute zenith UVW coordinates
    # Miriad convention is xyz(ant2) - xyz(ant1)
    # We assume numbers start at 1, not 0
    uv.uvw_array = np.zeros((uv.Nblts, 3), dtype='float64')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        # Pyuvdata's UVFITS writer needs data to be phased
        # to the zenith of the first timestamp. So, we do this by default
        if phase_to_t0:
            phase_time = Time(uv.time_array[0], format='jd')
            uv.phase_to_time(phase_time, use_ant_pos=True)
        else:
            uv.set_uvws_from_antenna_positions(update_vis=False)

    return uv
