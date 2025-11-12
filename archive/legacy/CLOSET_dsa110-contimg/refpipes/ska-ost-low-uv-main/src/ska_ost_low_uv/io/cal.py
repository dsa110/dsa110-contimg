"""cal: calibration data I/O utils."""

import h5py
import numpy as np
from astropy.units import Quantity
from loguru import logger

import ska_ost_low_uv
from ska_ost_low_uv.datamodel.cal import (
    UVXAntennaCal,
    create_uvx_antenna_cal,
)
from ska_ost_low_uv.utils import get_resource_path, load_yaml


def write_cal(cal: UVXAntennaCal, filename: str):
    """Write a UVXAntennaCAl object to a HDF5 file.

    Args:
        cal (UVXAntennaCal): ska_ost_low_uv.datamodel.UVXAntennaCal object
        filename (str): name of output file
    """
    # Load UVX schema from YAML. We can use this to load descriptions
    # And other metadata from the schema (e.g. dimensions)
    cal_schema = load_yaml(get_resource_path('datamodel/cal.yaml'))

    def _str2bytes(darr):
        if 'U' in str(darr.dtype) or 'obj' in str(darr.dtype):
            return darr.astype('bytes')
        else:
            return darr

    def _set_attrs(dobj, dset):
        for k, v in dobj.attrs.items():
            try:
                dset.attrs[k] = v
            except TypeError:
                dset.attrs[k] = v.astype('bytes')

    def _create_dset(group, name, dobj):
        data = _str2bytes(dobj.values)
        dset = group.create_dataset(name, data=data)
        _set_attrs(dobj, dset)

    # telescope: str          # Antenna array name, e.g. AAVS3
    # method: str             # Calibration method name (e.g. JishnuCal)
    # cal: xp.DataArray       # An xarray dataset  (frequency, antenna, pol)
    # flags: xp.DataArray     # Flag xarray dataset (frequency, antenna, pol)
    # provenance: dict        # Provenance/history information and other metadata

    with h5py.File(filename, mode='w') as h:
        # Basic metadata
        h.attrs['CLASS'] = cal_schema['cal']['CLASS']
        h.attrs['VERSION'] = ska_ost_low_uv.__version__

        ##################
        # CAL ROOT GROUP #
        ##################

        g_cal = h['/']
        _create_dset(g_cal, 'gains', cal.gains)
        _create_dset(g_cal, 'flags', cal.flags)

        g_cal_a = g_cal.create_group('attrs')
        g_cal_c = g_cal.create_group('coords')

        for coord in cal.gains.coords.keys():
            _create_dset(g_cal_c, coord, cal.gains.coords[coord])

        g_cal_a.attrs['telescope'] = cal.telescope
        g_cal_a.attrs['method'] = cal.method

        ####################
        # PROVENANCE GROUP #
        ####################

        g_prov = h.create_group('provenance')
        for k, v in cal.provenance.items():
            if isinstance(v, dict):
                g_prov_a = g_prov.create_group(k)
                for sk, sv in v.items():
                    g_prov_a.attrs[sk] = sv
            else:
                g_prov.attrs[k] = v

        # Add descriptions from cal.yaml schema
        cal_schema.pop('cal')  # Get rid of root cal group to supress message
        for k, v in cal_schema.items():
            k = k.replace('cal/', '')  # Strip cal/ prefix to get hdf5 path
            if k in h.keys():
                if 'description' in v.keys():
                    h[k].attrs['description'] = v['description']
                if 'dims' in v.keys():
                    # Convert dims into a string
                    h[k].attrs['dims'] = str(tuple(v['dims']))
            else:
                logger.warning(f'Could not find {k} in HDF5 file: {list(h.keys())}')


def read_cal(filename: str) -> UVXAntennaCal:
    """Load ska_ost_low_uv UVXAntennaCal object from uvx cal (HDF5) file.

    Args:
        filename (str): path to uvx cal file, or h5py.File

    Returns:
        uv (ska_ost_low_uv.datamodel.UVXAntennaCal): UVXAntenna object
    """

    def _to_list(lstr):
        return [x.strip("'").strip() for x in lstr.strip('()[]').split(', ')]

    if isinstance(filename, h5py.File):
        fh = filename
    else:
        fh = h5py.File(filename, mode='r')

    with fh as h:
        ##################
        # CAL ROOT GROUP #
        ##################
        f = Quantity(h['coords/frequency'][:], unit=h['coords/frequency'].attrs['units'])
        a = np.array([a.decode('ascii') for a in h['coords/antenna'][:]])
        p = np.array([p.decode('ascii') for p in h['coords/polarization'][:]])

        flags_arr = h['flags'][:]
        gains_arr = h['gains'][:]

        provenance = dict(h['provenance'].attrs.items())
        for k, v in h['provenance'].items():
            provenance[k] = dict(v.attrs.items())

        cal = create_uvx_antenna_cal(
            telescope=h['attrs'].attrs['telescope'],
            method=h['attrs'].attrs['method'],
            antenna_gains_arr=gains_arr,
            antenna_flags_arr=flags_arr,
            f=f,
            a=a,
            p=p,
            provenance=provenance,
        )

        return cal
