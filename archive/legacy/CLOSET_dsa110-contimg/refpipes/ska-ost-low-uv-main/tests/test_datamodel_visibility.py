"""test_datamodel_visibility: tests for uvx datamodel."""

import h5py
import numpy as np
import pandas as pd
from astropy.coordinates import EarthLocation
from astropy.time import Time
from astropy.units import Quantity

from ska_ost_low_uv.datamodel.uvx import (
    create_antenna_data_array,
    create_empty_uvx,
    create_visibility_array,
)
from ska_ost_low_uv.io import hdf5_to_uvx
from ska_ost_low_uv.io.metadata import load_observation_metadata
from ska_ost_low_uv.utils import get_aa_config, get_test_data

FN_DATA = get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5')
FN_CONFIG = get_aa_config('aavs3')


def test_create_arrays():
    """Test visibility array creation."""
    md = load_observation_metadata(FN_DATA, FN_CONFIG)

    xyz = np.array(list(md[f'telescope_ECEF_{q}'] for q in ('X', 'Y', 'Z')))
    eloc = EarthLocation.from_geocentric(*xyz, unit='m')
    antpos = pd.read_csv(md['antenna_locations_file'], delimiter=' ')
    antennas = create_antenna_data_array(antpos, eloc)
    print(antennas)

    h5 = h5py.File(FN_DATA, mode='r')
    data = h5['correlation_matrix']['data']

    t = Time(
        np.arange(md['n_integrations'], dtype='float64') * md['tsamp'] + md['ts_start'],
        format='unix',
        location=eloc,
    )
    f_arr = (np.arange(md['n_chans'], dtype='float64') + 1) * md['channel_spacing'] * md['channel_id']
    f = Quantity(f_arr, unit='Hz')
    data = create_visibility_array(data, f, t, eloc)
    print(data)


def test_create_uv():
    """Test hdf5_to_uvx creation."""
    aavs = hdf5_to_uvx(FN_DATA, yaml_config=FN_CONFIG)
    print(aavs)


def test_create_empty_uvx():
    """Test creation of a dummy UVX object."""
    uvx = create_empty_uvx('s8-6')
    print(uvx)
    return uvx


if __name__ == '__main__':
    test_create_arrays()
    test_create_uv()
    test_create_empty_uvx()
