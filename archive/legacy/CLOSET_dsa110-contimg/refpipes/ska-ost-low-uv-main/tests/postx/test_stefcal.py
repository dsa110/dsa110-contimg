"""Test stefcal calibration approach."""

import numpy as np
import pylab as plt
import pytest

from ska_ost_low_uv.io import hdf5_to_uvx
from ska_ost_low_uv.postx import ApertureArray
from ska_ost_low_uv.utils import get_test_data


@pytest.mark.mpl_image_compare
def test_stefcal():
    """Test Stefcal is working."""
    uvx = hdf5_to_uvx(
        get_test_data('aavs3/correlation_burst_100_20240107_19437_0.hdf5'),
        telescope_name='aavs3',
    )
    aa = ApertureArray(uvx)

    # Manual flags
    flags = [0, 72, 73, 85, 88, 98, 115, 117, 120, 121, 155, 188, 242, 244]
    flag_arr = np.zeros(256, dtype='bool')
    flag_arr[flags] = True

    # Run stefcal
    aa.calibration.stefcal.set_sky_model({'sun': aa.coords.get_sun()})
    sc = aa.calibration.stefcal.run_stefcal(antenna_flags=flag_arr, min_baseline=15)

    # Run self-holography
    aa.calibration.holography.set_cal_src(aa.coords.get_sun())
    jc = aa.calibration.holography.run_jishnucal()

    # Compare in plot
    a = np.arange(256)
    fig = plt.figure(figsize=(8, 6))

    plt.subplot(2, 1, 1)
    plt.scatter(a, np.rad2deg(np.angle(sc.gains[0, :, 0])), marker='.', label='stefcal X')
    plt.scatter(a, np.rad2deg(np.angle(jc.gains[0, :, 0])), marker='.', label='self-holo X')

    plt.subplot(2, 1, 2)
    plt.scatter(a, np.rad2deg(np.angle(sc.gains[0, :, 1])), marker='.', label='stefcal Y')
    plt.scatter(a, np.rad2deg(np.angle(jc.gains[0, :, 1])), marker='.', label='self-holo Y')
    plt.xlabel('Antenna ID')
    plt.legend()

    return fig


def test_stefcal_args():
    """Test Stefcal is working."""
    uvx = hdf5_to_uvx(
        get_test_data('aavs3/correlation_burst_100_20240107_19437_0.hdf5'),
        telescope_name='aavs3',
    )
    aa = ApertureArray(uvx)

    with pytest.raises(RuntimeError):
        aa.calibration.stefcal.run_stefcal(antenna_flags=None, min_baseline=15)

    # Run stefcal
    aa.calibration.stefcal.set_sky_model({'sun': aa.coords.get_sun()})
    sc = aa.calibration.stefcal.run_stefcal(antenna_flags=None, min_baseline=15)
    aa.set_cal(sc)

    # Run with pre-existing calibration set
    sc = aa.calibration.stefcal.run_stefcal(antenna_flags=None, min_baseline=15)

    # Manual flags
    flags = [0, 72, 73, 85, 88, 98, 115, 117, 120, 121, 155, 188, 242, 244]
    flag_arr = np.zeros(256, dtype='bool')
    flag_arr[flags] = True

    aa.calibration.stefcal.run_stefcal(antenna_flags=flag_arr, min_baseline=15)

    aa.calibration.stefcal.run_stefcal(min_baseline=10, sky_model={'sun': aa.coords.get_sun()})


if __name__ == '__main__':
    fig = test_stefcal()
    test_stefcal_args()
