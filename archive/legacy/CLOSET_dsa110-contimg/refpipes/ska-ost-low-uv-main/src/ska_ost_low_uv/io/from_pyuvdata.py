"""from_pyuvdata: Read data using pyuvdata."""

import numpy as np
import pandas as pd
import pyuvdata.utils as uvutils
from astropy.coordinates import EarthLocation
from astropy.io import fits as pf
from astropy.time import Time
from astropy.units import Quantity
from loguru import logger
from pyuvdata import UVData

from ska_ost_low_uv.datamodel.phase_center import PhaseCenter
from ska_ost_low_uv.datamodel.uvx import (
    UVX,
    create_antenna_data_array,
    create_empty_context_dict,
    create_empty_provenance_dict,
    create_visibility_array,
)
from ska_ost_low_uv.utils import import_optional_dependency


def convert_data_to_uvx_convention(uv: UVData, check: bool = False) -> np.array:
    """Convert the uv.data_array to UVX data convention.

    Notes:
        * Assumes the data are in triangular format with baselines sorted and contiguous.
        * Assumes the data polarization runs (XX, YY, XY, YX) i.e. (-5, -6, -7, -8)
        * pyuvdata data_array convention has shape (baseline * time, 1, freq, pol)
        * UVX convention has shape (time, freq, baseline, pol)
        * UVX polarization convention is (XX, XY, YX, YY) i.e. (-5, -8, -6, -7)
        * phase center in UVX generally does not have phase tracking (phase_to_t0=False)

    Args:
        uv (UVData): UV data object with uv.data_array to convert
        check (bool): Run basic sanity checks on incoming data arrangement

    Returns:
        data (np.array): Numpy array of data after remapping to UVX convention
    """
    if check:
        # Pol in correct input order
        assert np.allclose((-5, -6, -7, -8), uv.polarization_array)
        # No missing baselines
        assert uv.Nbls == uv.Nants_data * (uv.Nants_data + 1) // 2

    # Create empty numpy array
    data = np.zeros((uv.Ntimes, uv.Nfreqs, uv.Nbls, uv.Npols), dtype=uv.data_array.dtype)

    # Generate indexes
    # fmt: off
    idx_t  = np.repeat(np.arange(uv.Ntimes), uv.Nbls * uv.Nfreqs * uv.Npols)
    idx_f  = np.repeat(np.arange(uv.Nfreqs), uv.Nbls * uv.Ntimes * uv.Npols)
    idx_bl = np.repeat(np.tile(np.arange(uv.Nbls), uv.Nfreqs * uv.Ntimes), uv.Npols)
    idx_p  = np.tile([0, 3, 1, 2], uv.Nbls * uv.Nfreqs * uv.Ntimes)
    # fmt: on

    data[idx_t, idx_f, idx_bl, idx_p] = uv.data_array.flatten()
    return data


def pyuvdata_to_uvx(uv: UVData, check: bool = False) -> UVX:
    """Convert pyuvdata UVData object to UVX.

    Notes:
        This is experimental, and will only work under certain
        circumstances:

            * Nspws = 1
            * Data are in lower-triangular order, no missing data.
            * Data not phase-tracking (if multiple timesteps)

    Args:
        uv (UVData): Pyuvdata input object
        check (bool): Run basic sanity checks on incoming data arrangement

    Returns:
        uvx (UVX): Converted UVX object

    """
    eloc = EarthLocation(uv.telescope.location)
    xyz = np.array([eloc.x.value, eloc.y.value, eloc.z.value])

    # Create Antenna dataset
    antpos_ENU = uvutils.ENU_from_ECEF(uv.telescope.antenna_positions + xyz, center_loc=eloc)
    df = pd.DataFrame(antpos_ENU, columns=('E', 'N', 'U'))
    df['flagged'] = False
    df['name'] = uv.telescope.antenna_names
    df = df[['name', 'E', 'N', 'U', 'flagged']]
    antennas = create_antenna_data_array(df, eloc)

    # Create frequency, time, and data
    if uv.Nspws != 1:
        logger.warning('Multiple SPWs not supported!')
    f = Quantity(uv.freq_array, unit='Hz')
    t = Time(uv.time_array[:: uv.Nbls], format='jd', scale='utc', location=eloc)
    data_arr = convert_data_to_uvx_convention(uv, check=check)
    # Conjugation and transposition YX<->XY should already be applied
    data = create_visibility_array(data_arr, f, t, eloc, conj=False, transpose=False)

    # Create phase center
    pc_cat = list(uv.phase_center_catalog.values())
    if len(pc_cat) > 1:
        logger.warning('Multiple phase centers detected. Failure likely.')
    pc_dict = list(uv.phase_center_catalog.values())[0]

    pc_types = {'driftscan': 'drift', 'sidereal': 'track'}

    pc_sc = PhaseCenter(
        pc_dict['cat_lon'],
        pc_dict['cat_lat'],
        frame=pc_dict['cat_frame'],
        unit=('rad', 'rad'),
        phase_type=pc_types[pc_dict['cat_type']],
        name=pc_dict['cat_name'],
        location=eloc,
        obstime=t[0],
    )

    # Create UV object
    uvx = UVX(
        name=uv.telescope.name,
        antennas=antennas,
        context=create_empty_context_dict(),
        data=data,
        timestamps=t,
        origin=eloc,
        phase_center=pc_sc,
        provenance=create_empty_provenance_dict(),
    )

    return uvx


def write_ms(uv: UVData, filename: str, *args, **kwargs):
    """Write UVData to MeasurementSet.

    Notes:
        Calls uv.write_ms(), then applies station rotation patch.

    Args:
        uv (UVData): pyuvdata object to write to file.
        filename (str): Name of output filename.
        args (list): Arguments to pass to uv.write_ms
        kwargs (dict): Keyword arguments to pass to uv.write_ms
    """
    tables = import_optional_dependency('casacore.tables', errors='raise')

    uv.write_ms(filename, *args, **kwargs)

    # Patch RECEPTOR_ANGLE column
    with tables.table(f'{filename}/FEED', readonly=False) as t:
        logger.debug('Applying station rotation (RECEPTOR_ANGLE)')
        r_ang = np.zeros(shape=t.getcol('RECEPTOR_ANGLE').shape, dtype='float64')
        x_ang = -np.pi / 180 * uv.receptor_angle
        r_ang[:, 0] = x_ang
        r_ang[:, 1] = x_ang + np.pi / 2

        t.putcol('RECEPTOR_ANGLE', r_ang)


def write_uvfits(uv: UVData, filename: str, *args, **kwargs):
    """Write UVData to MeasurementSet.

    Notes:
        Calls uv.write_uvfits(), then applies station rotation patch.

    Args:
        uv (UVData): pyuvdata object to write to file.
        filename (str): Name of output filename.
        args (list): Arguments to pass to uv.write_uvfits
        kwargs (dict): Keyword arguments to pass to uv.write_uvfits
    """
    # Use Miriad convention for >256 antennas by default
    if 'use_miriad_convention' in kwargs:
        use_miriad_convention = kwargs.pop('use_miriad_convention')
    else:
        use_miriad_convention = True
    uv.write_uvfits(filename, use_miriad_convention=use_miriad_convention, *args, **kwargs)

    # Patch POLAA/POLAB columns
    with pf.open(filename, mode='update') as hdu:
        logger.debug('Applying station rotation (POLAA/POLAB)')
        hdu[1].data['POLAA'] = uv.receptor_angle
        hdu[1].data['POLAB'] = uv.receptor_angle + 90
