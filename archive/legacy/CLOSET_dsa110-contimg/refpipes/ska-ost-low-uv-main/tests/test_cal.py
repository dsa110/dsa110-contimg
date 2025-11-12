"""Test cal schema and reading/writing to disk."""

import os

import numpy as np
import pylab as plt
import pytest

from ska_ost_low_uv.io import hdf5_to_uvx, read_cal, write_cal
from ska_ost_low_uv.postx import ApertureArray
from ska_ost_low_uv.utils import get_test_data

test_data = {
    'aavs2': (
        get_test_data('aavs2/correlation_burst_100_20211113_14447_0.hdf5'),
        get_test_data('aavs2/correlation_burst_204_20211113_14653_0.hdf5'),
    ),
    'aavs3': (
        get_test_data('aavs3/correlation_burst_100_20240107_19437_0.hdf5'),
        get_test_data('aavs3/correlation_burst_204_20240107_19437_0.hdf5'),
    ),
    'eda2': (
        get_test_data('eda2/correlation_burst_100_20211211_14167_0.hdf5'),
        get_test_data('eda2/correlation_burst_204_20211211_14373_0.hdf5'),
    ),
}


@pytest.fixture
def fixture_aa():
    """Fixture to create an ApertureArray object."""
    uvx = hdf5_to_uvx(test_data['aavs2'][0], telescope_name='aavs2')
    aa = ApertureArray(uvx)

    aa.calibration.holography.set_cal_src(aa.coords.get_sun())
    sc = aa.calibration.holography.run_jishnucal()
    return aa, sc


@pytest.mark.mpl_image_compare
def test_cal_plot(fixture_aa):
    """Test cal plotting."""
    aa, sc = fixture_aa

    plt.figure()
    plt.subplot(1, 2, 1)
    sc.plot_gains(plot_type='phs')
    plt.subplot(1, 2, 2)
    sc.plot_gains(plot_type='mag')
    return plt.gcf()


def test_cal_io(fixture_aa):
    """Test cal read/write."""
    aa, sc = fixture_aa
    try:
        write_cal(sc, 'tests/test_cal.h5')
        sc2 = read_cal('tests/test_cal.h5')

        assert np.allclose(sc.flags, sc2.flags)
        assert np.allclose(sc.gains, sc2.gains)
        assert sc.telescope == sc2.telescope
        assert sc.method == sc2.method

        for k in sc.provenance.keys():
            assert k in sc2.provenance.keys()

        aa.load_cal('tests/test_cal.h5')
        assert np.allclose(aa.workspace['cal'].gains, sc.gains)

    finally:
        if os.path.exists('tests/test_cal.h5'):
            os.remove('tests/test_cal.h5')


if __name__ == '__main__':
    test_cal_io()
