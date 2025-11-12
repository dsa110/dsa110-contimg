"""Test conjugation."""

import h5py
import numpy as np

from ska_ost_low_uv.io import hdf5_to_pyuvdata, hdf5_to_uvx
from ska_ost_low_uv.utils import get_aa_config, get_test_data

FN_RAW = get_test_data('aavs2_1x1000ms/correlation_burst_204_20230823_21356_0.hdf5')
YAML_RAW = get_aa_config('aavs2')
YAML_NOCONJ = get_test_data('aavs2_noconj/uv_config.yaml')


def test_conj():
    """Test data conjugation is working."""
    # Load original correlation data
    # AAVS2 data will be conjugated and transposed when loaded
    # Due to config/aavs2/uv_config.yaml settings
    h5 = h5py.File(FN_RAW)
    data_orig = h5['correlation_matrix']['data'][:]
    remap = np.array((0, 2, 1, 3))

    print('Testing conjgation: UVX')
    vis = hdf5_to_uvx(FN_RAW, telescope_name='aavs2')
    assert np.allclose(np.conj(vis.data[..., remap]), data_orig)

    print('Testing conjgation: pyuvdata')
    remap_uv = np.array((0, 3, 2, 1))
    vis = hdf5_to_pyuvdata(FN_RAW, telescope_name='aavs2', phase_to_t0=False)
    uv_data = vis.data_array.reshape((1, 1, 32896, 4))
    assert np.allclose(np.conj(uv_data[..., remap_uv]), data_orig)

    print('Testing no conjgation: UVX')
    vis = hdf5_to_uvx(FN_RAW, yaml_config=YAML_NOCONJ)
    assert np.allclose(vis.data, data_orig)

    print('Testing no conjgation: pyuvdata')
    remap_uv = np.array((0, 3, 1, 2))
    vis = hdf5_to_pyuvdata(FN_RAW, yaml_config=YAML_NOCONJ, phase_to_t0=False)
    uv_data = vis.data_array.reshape((1, 1, 32896, 4))
    assert np.allclose(uv_data, data_orig[..., remap_uv])


if __name__ == '__main__':
    test_conj()
