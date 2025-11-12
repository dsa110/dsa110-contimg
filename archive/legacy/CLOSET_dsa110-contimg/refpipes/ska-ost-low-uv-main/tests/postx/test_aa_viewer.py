"""test_aa_viewer: tests for postx viewer tools."""

import numpy as np
import pylab as plt
import pytest

from ska_ost_low_uv.io import hdf5_to_uvx
from ska_ost_low_uv.postx import ApertureArray
from ska_ost_low_uv.utils import get_test_data


def setup_test() -> ApertureArray:
    """Setup tests.

    Returns:
        aa (ApertureArray): An ApertureArray object to use in testing.
    """
    fn_data = get_test_data('aavs2_1x1000ms/correlation_burst_204_20230823_21356_0.hdf5')
    v = hdf5_to_uvx(fn_data, telescope_name='aavs2')

    # RadioArray basics
    aa = ApertureArray(v)
    return aa


def test_aa_viewer():
    """Test viewer - basic."""
    aa = setup_test()
    img = aa.imaging.make_image()

    aa.viewer.orthview(img)
    aa.viewer.orthview(img[..., 0])

    aa.viewer.get_pixel(aa.coords.get_sun())
    aa.viewer.get_pixel(aa.coords.get_zenith())

    aa.viewer.get_pixel_healpix(64, aa.coords.get_sun())
    aa.viewer.get_pixel_healpix(64, aa.coords.get_zenith())


@pytest.mark.mpl_image_compare
def test_orthview():
    """Test viewer - orthview()."""
    aa = setup_test()

    plt.figure()
    aa.set_idx(f=0, t=0, p=0)
    img = aa.imaging.make_image()
    aa.viewer.orthview(
        img, overlay_srcs=True, overlay_grid=False, colorbar=True, reuse_fig=True, subplot_id=(1, 2, 1)
    )
    aa.set_idx(f=0, t=0, p=3)
    img = aa.imaging.make_image()
    aa.viewer.orthview(
        img, overlay_srcs=True, overlay_grid=False, colorbar=True, reuse_fig=True, subplot_id=(1, 2, 2)
    )
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_mollview():
    """Test viewer - orthview()."""
    aa = setup_test()
    hpx = aa.imaging.make_healpix()

    aa.viewer.mollview(hpx, overlay_srcs=True, overlay_grid=False, colorbar=True)
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_cmap():
    """Test the SKAO colormap!"""
    aa = setup_test()
    hpx = aa.imaging.make_healpix()
    aa.imaging.make_image()
    aa.viewer.mollview(hpx, cmap='skao')
    plt.close()

    aa.viewer.orthview(cmap='skao', sfunc=np.log)
    return plt.gcf()


if __name__ == '__main__':
    test_aa_viewer()
    test_orthview()
    test_mollview()
