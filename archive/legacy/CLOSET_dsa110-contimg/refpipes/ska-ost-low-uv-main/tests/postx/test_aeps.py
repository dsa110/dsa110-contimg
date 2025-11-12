"""Tests for AEP (Antenna Element Pattern) models and loading utilities.

This module contains tests for the aep_models module functionality.
"""

import healpy as hp
import numpy as np
import pylab as plt
import pytest
from astropy.coordinates import Angle, SkyCoord

from ska_ost_low_uv.postx.aeps.aep_models import (
    load_aep,
    load_aep_coeffs,
    load_aep_orth,
)


def test_load_aep_coeffs():
    """Load AEP coefficients."""
    coeffs = load_aep_coeffs(100)
    coeffs = load_aep_coeffs(100, aep='ska_low')
    assert 'xx' in coeffs
    assert 'yy' in coeffs
    assert 're_xy' in coeffs
    assert 'im_xy' in coeffs
    assert coeffs['xx'].shape[0] == 1378


@pytest.mark.mpl_image_compare
def test_load_aep_nside():
    """Test AEP loading."""
    aep = load_aep(200)
    hp.orthview(aep[..., 0], half_sky=True, title='XX')
    hp.graticule(color='white', alpha=0.5)
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_load_aep_rot():
    """Test AEP loading."""
    aep_rot = load_aep(150, rot_angle=30)
    hp.mollview(aep_rot[..., 0], title='Rotation=30')
    hp.graticule(color='white', alpha=0.5)
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_load_aep_rexy():
    """Test AEP loading."""
    aep = load_aep(150)
    hp.mollview(aep[..., 1], title='Re(XY)')
    hp.graticule(color='white', alpha=0.5)
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_load_aep_offset_l():
    """Test AEP loading."""
    sc = SkyCoord(30, 0, unit='deg', frame='galactic')
    aep_offset_l = load_aep(150, sky_coord=sc, rot_angle=Angle(0, unit='deg'))
    hp.mollview(aep_offset_l[..., 0], title='Offset l=30')
    hp.graticule(color='white', alpha=0.5)
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_load_aep_offset_lb():
    """Test AEP loading."""
    sc = SkyCoord(-90, -30, unit='deg', frame='galactic')
    aep_offset_lb = load_aep(150, sky_coord=sc, rot_angle=Angle(0, unit='deg'))
    hp.mollview(aep_offset_lb[..., 0], title='Offset l=-90, b=-30')
    hp.graticule(color='white', alpha=0.5)
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_load_aep_offset_b():
    """Test AEP loading."""
    sc = SkyCoord(0, -30, unit='deg', frame='galactic')
    aep_offset_b = load_aep(150, sky_coord=sc, rot_angle=Angle(0, unit='deg'))
    hp.mollview(aep_offset_b[..., 0], title='Offset b=30')
    hp.graticule(color='white', alpha=0.5)
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_load_aep_stokes():
    """Test AEP loading."""
    aep_stokes = load_aep(150, mode='stokes')
    hp.mollview(aep_stokes[..., 0], title='Stokes I')
    hp.graticule(color='white', alpha=0.5)
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_load_aep_orth():
    """Test loading AEPS to orthographic 2D."""
    img = load_aep_orth(100, npix=800, fill_value=0)[..., 0]
    hpx = load_aep(100, nside=128, fill_value=0)[..., 0]

    orth = hp.orthview(hpx, half_sky=True, return_projected_map=True)

    plt.figure(figsize=(9, 4))
    plt.subplot(1, 3, 1)
    plt.imshow(img)
    plt.colorbar()
    plt.subplot(1, 3, 2)
    plt.imshow(orth)
    plt.colorbar()
    plt.subplot(1, 3, 3)
    diff = img / np.nanmax(img) - orth / np.nanmax(orth)
    plt.imshow(diff)
    plt.colorbar()
    return plt.gcf()
