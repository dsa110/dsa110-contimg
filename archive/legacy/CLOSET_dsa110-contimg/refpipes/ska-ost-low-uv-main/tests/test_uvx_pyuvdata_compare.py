"""test_uvx_pyuvdata_compare: roundtrip comparisons between UVX and UVData."""

import numpy as np

from ska_ost_low_uv.io import (
    hdf5_to_pyuvdata,
    hdf5_to_uvx,
    pyuvdata_to_uvx,
    uvx_to_pyuvdata,
)
from ska_ost_low_uv.utils import get_test_data


def test_compare_uv_paths():
    """Compare HDF5 -> UVX -> UVData against HDF5 -> UVData path."""
    fn = get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5')

    uvx = hdf5_to_uvx(fn, telescope_name='aavs2')
    uv = hdf5_to_pyuvdata(fn, telescope_name='aavs2')
    uv2 = uvx_to_pyuvdata(uvx)

    assert np.allclose(np.abs(uv.data_array), np.abs(uv2.data_array))
    assert np.allclose(uv.data_array, uv2.data_array)

    assert np.allclose(uv.uvw_array, uv2.uvw_array)
    assert np.allclose(uv.ant_1_array, uv2.ant_1_array)
    assert np.allclose(uv.ant_2_array, uv2.ant_2_array)
    assert np.allclose(uv.baseline_array, uv2.baseline_array)

    for k in ('cat_name', 'cat_type', 'cat_lon', 'cat_lat'):
        assert uv.phase_center_catalog[1][k] == uv2.phase_center_catalog[1][k]

    # To compare hdf5 -> pyuvdata -> UVX we need to turn off phasing to t0
    uv = hdf5_to_pyuvdata(fn, telescope_name='aavs2', phase_to_t0=False)
    uvx2 = pyuvdata_to_uvx(uv)

    assert np.allclose(uvx.data, uvx2.data)

    # Test if phase_type is carried over when phase_to_t0 set
    uv = hdf5_to_pyuvdata(fn, telescope_name='aavs2', phase_to_t0=True)
    uvx3 = pyuvdata_to_uvx(uv)
    assert uvx.phase_center.phase_type == 'drift'
    assert uvx2.phase_center.phase_type == 'drift'
    assert uvx3.phase_center.phase_type == 'track'


if __name__ == '__main__':
    test_compare_uv_paths()
