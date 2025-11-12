"""uvx: Data models for interferometer data (UVX)."""

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pyuvdata.utils as uvutils
import xarray as xp
from astropy.coordinates import AltAz, Angle, EarthLocation
from astropy.time import Time
from astropy.units import Quantity
from loguru import logger

from ska_ost_low_uv.datamodel.phase_center import PhaseCenter
from ska_ost_low_uv.utils import (
    get_resource_path,
    get_software_versions,
    load_config,
    load_yaml,
)


# Define the data class for UV data
@dataclass
class UVX:
    """Dataclass for storing UVX interferometer data."""

    # fmt: off
    name: str                  # Antenna array name, e.g. AAVS3
    context: dict              # Contextual information (observation intent, notes, observer name)
    antennas: xp.Dataset       # An xarray dataset (generated with create_antenna_data_array)
    data: xp.DataArray         # An xarray DataArray (generated with create_visibility_array)
    timestamps: Time           # Astropy timestamps Time() array
    origin: EarthLocation      # Astropy EarthLocation for array origin
    phase_center: PhaseCenter  # PhaseCenter (based on astropy SkyCoord) corresponding to phase center
    provenance: dict           # Provenance/history information and other metadata
    # fmt: on


def create_empty_context_dict():
    """Create an empty context dictionary with default keys."""
    context = {
        'intent': '',
        'date': '',
        'notes': '',
        'observer': '',
        'execution_block': '',
    }
    return context


def create_empty_provenance_dict():
    """Create a provenance dict with default keys."""
    provenance = {
        'ska_ost_low_uv_config': get_software_versions(),
        'input_files': {},
        'input_metadata': {},
    }
    return provenance


def create_antenna_data_array(
    antpos: pd.DataFrame, eloc: EarthLocation, array_rotation_angle: Angle = None
) -> xp.Dataset:
    """Create an xarray Dataset for antenna locations.

    Args:
        antpos (pd.Dataframe): Pandas dataframe with antenna positions. Should have
                               columns: ``id | name | E | N | U | flagged``
        eloc (EarthLocation): Astropy EarthLocation corresponding to array center
        array_rotation_angle (Angle): Station rotation angle in degrees (optional)

    Returns:
        dant (xp.Dataset): xarray Dataset with antenna locations

    Notes:
        ::

            <xarray.Dataset>
                Dimensions:  (antenna: N_ant, spatial: 3)
                Coordinates:
                * antenna  (antenna) int64 0 1 2 3 4 5 6 7 ... N_ant
                * spatial  (spatial) <U1 'x' 'y' 'z'

                Data variables:
                    enu      (antenna, spatial) float64 East-North-Up coordinates relative to eloc
                    ecef     (antenna, spatial) float64 ECEF XYZ coordinates (XYZ - eloc.XYZ0)

    Attributes:
                    identifier:               Antenna names / identifiers
                    flags:                    Flags if antenna is bad
                    array_origin_geocentric:  Array origin (ECEF)
                    array_origin_geodetic:    Array origin (lat/lon/height)
                    array_rotation_angle:     Array rotation angle
    """
    uvx_schema = load_yaml(get_resource_path('datamodel/uvx.yaml'))

    x0, y0, z0 = [_.to('m').value for _ in eloc.to_geocentric()]

    antpos_enu = np.column_stack((antpos['E'], antpos['N'], antpos['U']))
    antpos_ecef = uvutils.ECEF_from_ENU(antpos_enu, eloc) - (x0, y0, z0)

    # Check if flags in antpos, otherwise add column
    if 'flagged' not in antpos.columns:
        antpos['flagged'] = False

    data_vars = {
        'enu': xp.DataArray(
            antpos_enu,
            dims=uvx_schema['uvx/antennas/enu']['dims'],
            attrs={
                'units': uvx_schema['uvx/antennas/enu']['units'],
                'description': uvx_schema['uvx/antennas/enu']['description'],
            },
        ),
        'ecef': xp.DataArray(
            antpos_ecef,
            dims=uvx_schema['uvx/antennas/ecef']['dims'],
            attrs={
                'units': uvx_schema['uvx/antennas/ecef']['units'],
                'description': uvx_schema['uvx/antennas/ecef']['description'],
            },
        ),
    }

    attrs = {
        'identifier': xp.DataArray(
            antpos['name'],
            dims=uvx_schema['uvx/antennas/attrs/identifier']['dims'],
            attrs={'description': uvx_schema['uvx/antennas/attrs/identifier']['description']},
        ),
        'flags': xp.DataArray(
            antpos['flagged'],
            dims=uvx_schema['uvx/antennas/attrs/flags']['dims'],
            attrs={'description': uvx_schema['uvx/antennas/attrs/flags']['description']},
        ),
    }

    coords = {'antenna': np.arange(256), 'spatial': np.array(('x', 'y', 'z'))}

    # Add array origin
    array_origin_m = (eloc['x'].value, eloc['y'].value, eloc['z'].value)
    array_origin_ecef = xp.DataArray(
        np.array(array_origin_m),
        attrs={
            'units': 'm',
            'description': uvx_schema['uvx/antennas/attrs/array_origin_geocentric']['description'],
        },
        coords={'spatial': np.array(('x', 'y', 'z'))},
        dims=('spatial'),
    )

    array_origin_geodetic = xp.DataArray(
        np.array((eloc.lon.value, eloc.lat.value, eloc.height.value)),
        attrs={
            'units': np.array(('deg', 'deg', 'm')),
            'description': uvx_schema['uvx/antennas/attrs/array_origin_geodetic']['description'],
        },
        coords={'spatial': np.array(('longitude', 'latitude', 'height'))},
        dims=('spatial'),
    )

    # Array rotation angle
    rot_angle_deg = 0 if array_rotation_angle is None else array_rotation_angle.to('deg').value
    array_rotation_angle = xp.DataArray(
        rot_angle_deg,
        attrs={
            'units': 'deg',
            'description': uvx_schema['uvx/antennas/attrs/array_rotation_angle']['description'],
        },
    )

    attrs['array_origin_geocentric'] = array_origin_ecef
    attrs['array_origin_geodetic'] = array_origin_geodetic
    attrs['array_rotation_angle'] = array_rotation_angle

    dant = xp.Dataset(data_vars=data_vars, coords=coords, attrs=attrs)

    return dant


def create_visibility_array(
    data: np.ndarray,
    f: Quantity,
    t: Time,
    eloc: EarthLocation,
    conj: bool = True,
    transpose: bool = True,
    N_ant: int = 256,
) -> xp.DataArray:
    """Create visibility array out of data array + metadata.

    Takes a data array, frequency and time axes, and an EarthLocation.
    Currently assumes (-5, -6, -7, -8) polarization and upper triangle baseline coordinates.

    Args:
        data (np.array): Numpy array or duck-type similar data (e.g. h5py.dataset)
        t (Time): Astropy time array corresponding to timestamps
        f (Quantity): Astropy quantity array of frequency for channel centers
        md (dict): Dictionary of metadata, as found in raw HDF5 file.
        eloc (EarthLocation): Astropy EarthLocation for array center
        conj (bool): Conjugate visibility data (default True).
        transpose (bool): Transpose XY* and YX* (default True).
        N_ant (int): Number of antennas in array.


    Returns:
        vis (xp.DataArray): xarray DataArray object, see notes below

    Notes:
        ::

            <xarray.DataArray (time: N_time, frequency: N_freq, baseline: N_bl, polarization: N_pol)>
                Coordinates:
                * time          (time) object MultiIndex
                * mjd           (time) time in MJD
                * lst           (time) time in LST
                * polarization  (polarization) <U2 'XX' 'XY' 'YX' 'YY'
                * baseline      (baseline) object MultiIndex
                * ant1          (baseline) int64 0 0 0 0 0 0 0 ... N_ant
                * ant2          (baseline) int64 0 1 2 3 4 5 6 ... N_ant
                * frequency     (frequency) float64 channel frequency values, in Hz


    Speed notes:
        this code generates MJD and LST timestamps attached as coordinates, as well as an
        astropy `Time()` array (which provides useful conversion between time formats that
        `DataArray` does not). Conversion to/from `datetime64` takes significantly longer than
        generation from an array of MJD values.
    """
    uvx_schema = load_yaml(get_resource_path('datamodel/uvx.yaml'))

    # Coordinate - time
    t = Time(t, location=eloc)  # Add location
    lst = t.sidereal_time('apparent').to('hourangle')
    t_coord = pd.MultiIndex.from_arrays((t.mjd, lst.value, t.unix), names=('mjd', 'lst', 'unix'))

    # Coordinate - baseline
    ix, iy = np.triu_indices(N_ant)
    bl_coord = pd.MultiIndex.from_arrays((ix, iy), names=('ant1', 'ant2'))

    # Coordinate - polarization
    pol_coord = np.array(('XX', 'XY', 'YX', 'YY'))

    # Coordinate - frequency
    f_center = f.to('Hz').value
    f_coord = xp.DataArray(
        f_center,
        dims=('frequency',),
        attrs={
            'units': uvx_schema['uvx/visibilities/coords/frequency']['units'],
            'description': uvx_schema['uvx/visibilities/coords/frequency']['description'],
        },
    )

    coords = {
        'time': t_coord,
        'polarization': pol_coord,
        'baseline': bl_coord,
        'frequency': f_coord,
    }

    if conj:
        logger.info('Conjugating data')
        data = np.conj(data)

    if transpose:
        logger.info('Transposing data')
        # Remap XX,XY,YX,YY -> XX,YX,XY,YY
        data = data[..., [0, 2, 1, 3]]

    vis = xp.DataArray(data, coords=coords, dims=('time', 'frequency', 'baseline', 'polarization'))
    return vis


def create_empty_uvx(name: str, t: Time = None, f: Quantity = None) -> UVX:
    """Create an empty UVX dataclass instance."""
    context = create_empty_context_dict()
    provenance = create_empty_provenance_dict()

    md = load_config(name)

    # fmt: off
    xyz     = np.array(list(md[f'telescope_ECEF_{q}'] for q in ('X', 'Y', 'Z')))
    eloc    = EarthLocation.from_geocentric(*xyz, unit='m')
    antpos  = pd.read_csv(md['antenna_locations_file'], delimiter=' ')
    rot_ang = Angle(md['receptor_angle'], unit='deg')
    ant_arr = create_antenna_data_array(antpos, eloc, array_rotation_angle=rot_ang)
    # fmt: on

    # Dummy data with shape (time, frequency, baseline, polarization)
    data = np.zeros((1, 1, 32896, 4), dtype='complex64')

    # Dummy time + frequency axes
    if t is None:
        t = Time([datetime.now(timezone.utc)], location=eloc, format='datetime')
    if f is None:
        f = Quantity([50e6], unit='Hz')

    # Make sure time has location set
    t = Time(t, location=eloc)

    data = create_visibility_array(data, f, t, eloc, conj=False, transpose=False)
    data.attrs['unit'] = md['vis_units']

    # Add extra info about time resolution and frequency resolution from input metadata
    # fmt: off
    data.time.attrs['resolution']             = 1.0
    data.time.attrs['resolution_unit']        = 's'

    data.frequency.attrs['resolution']        = md['channel_spacing']
    data.frequency.attrs['channel_spacing']   = md['channel_spacing']
    data.frequency.attrs['channel_bandwidth'] = md['channel_width']
    data.frequency.attrs['channel_id']        = 1
    data.frequency.attrs['resolution_unit']   = 'Hz'
    # fmt: on

    # Compute zenith RA/DEC for phase center
    zen_aa = AltAz(
        alt=Angle(90, unit='degree'),
        az=Angle(0, unit='degree'),
        obstime=t[0],
        location=t.location,
    )
    zen_sc = PhaseCenter(zen_aa).icrs

    return UVX(
        name=name,
        context=context,
        antennas=ant_arr,
        data=data,
        timestamps=t,
        origin=eloc,
        phase_center=zen_sc,
        provenance=provenance,
    )
