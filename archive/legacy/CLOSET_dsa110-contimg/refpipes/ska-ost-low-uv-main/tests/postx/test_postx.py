"""test_postx: tests for postx utilities and tools."""

import os

import numpy as np
import pylab as plt
import pytest
from astropy.coordinates import SkyCoord

from ska_ost_low_uv.io import hdf5_to_uvx
from ska_ost_low_uv.postx import ApertureArray
from ska_ost_low_uv.postx.sky_model import generate_skycat, sun_model
from ska_ost_low_uv.postx.viewer.aa_viewer import AllSkyViewer
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


def test_postx():
    """Test postx - basic."""
    aa = setup_test()
    aa.help()
    print(aa.coords.get_zenith())

    print(aa.simulation)
    aa.simulation.help()

    # RadioArray - images
    img = aa.imaging.make_image()
    hmap = aa.imaging.make_healpix(n_side=64)
    hmap = aa.imaging.make_healpix(n_side=64, apply_mask=False)

    img_stokes = aa.imaging.make_image(mode='stokes')
    hmap_stokes = aa.imaging.make_healpix(n_side=64, mode='stokes')

    assert np.allclose(np.nan_to_num(img_stokes[..., 0], 0), np.nan_to_num(img[..., 0] + img[..., 3], 0))
    assert np.allclose(np.nan_to_num(hmap_stokes[..., 0], 0), np.nan_to_num(hmap[..., 0] + hmap[..., 3]))

    assert img.shape == (128, 128, 4)
    assert hmap.ndim == 2

    # Sky catalog
    skycat = generate_skycat(aa)
    assert isinstance(skycat, dict)
    sun_model(aa, 0)

    # AllSkyViewer
    asv = AllSkyViewer(aa, skycat=skycat)
    asv.load_labels(skycat)
    asv.update()

    print(asv.get_pixel(aa.coords.get_zenith()))
    sc_north = SkyCoord('12:00', '80:00:00', unit=('hourangle', 'deg'))
    assert asv.get_pixel(sc_north) == (0, 0)

    # Simulation
    aa.simulation.sim_vis_gsm()


def test_viewer():
    """Test viewer tools."""
    aa = setup_test()
    print(aa)
    aa.set_idx(f=0, t=0, p=0)

    # All-sky-viewer via aa
    aa.viewer.orthview()
    aa.viewer.mollview()

    img = aa.imaging.make_image(n_pix=150)
    hmap = aa.imaging.make_healpix(n_side=64)
    aa.viewer.orthview(img)
    aa.viewer.mollview(hmap)

    try:
        aa.viewer.write_fits(img, 'tests/test.fits')
        aa.viewer.write_fits(hmap, 'tests/test_hpx.fits')
    finally:
        if os.path.exists('tests/test.fits'):
            os.system('rm tests/test.fits')
        if os.path.exists('tests/test_hpx.fits'):
            os.system('rm tests/test_hpx.fits')


@pytest.mark.mpl_image_compare
def test_viewer_orthview():
    """Test orthview."""
    aa = setup_test()
    aa.viewer.new_fig()
    aa.viewer.orthview()
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_viewer_mollview():
    """Test mollview."""
    aa = setup_test()
    fig = aa.viewer.new_fig()
    aa.viewer.mollview(fig=fig)
    return fig


if __name__ == '__main__':
    test_postx()
