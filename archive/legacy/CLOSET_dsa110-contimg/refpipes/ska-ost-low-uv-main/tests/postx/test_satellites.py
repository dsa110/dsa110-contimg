"""test_satellites.py -- test satellite TLE loading."""

import numpy as np
import pylab as plt
import pytest

from ska_ost_low_uv.io import read_uvx
from ska_ost_low_uv.postx import ApertureArray
from ska_ost_low_uv.postx.coords.satellites import (
    compute_satellite_altaz,
    compute_satellite_radec,
    load_tles,
    satchecker_above_horizon,
    satchecker_get_tle,
    satchecker_lookup_norad,
)
from ska_ost_low_uv.utils import get_test_data


@pytest.fixture
def fixture_aa():
    """Fixture to create an ApertureArray.

    These data have SVOM satellite detection, and corresponding TLEs.
    """
    uvx = read_uvx(get_test_data('satellites/s81-svom.uvx'))
    aa = ApertureArray(uvx)

    tles = load_tles(aa, get_test_data('satellites/tles_2025.01.22.txt'))
    print(tles)
    for name in ('CATCH-1', 'SVOM', 'STARLINK-31239'):
        assert name in tles.keys()

    aa.viewer.skycat = tles

    return aa, tles


@pytest.mark.mpl_image_compare
def test_plot_satellite(fixture_aa):
    """Subtest plotting of satellite positions."""
    aa, _tles = fixture_aa
    aa.imaging.make_image()
    aa.viewer.orthview(overlay_srcs=True, overlay_grid=True)
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_plot_satellite_hpx(fixture_aa):
    """Subtest plotting of satellite positions."""
    aa, _tles = fixture_aa
    aa.imaging.make_healpix()
    aa.viewer.mollview(overlay_srcs=True)
    return plt.gcf()


def test_satellites(fixture_aa):
    """Test satellite TLE loading."""
    aa, tles = fixture_aa

    altaz = compute_satellite_altaz(aa, satellite=tles['SVOM'])
    radec = compute_satellite_radec(aa, satellite=tles['SVOM'])
    print(radec)
    print(altaz)

    ra_known = 325.94274827
    dec_known = 23.23994588
    assert np.isclose(radec.ra.to('deg').value, ra_known)
    assert np.isclose(radec.dec.to('deg').value, dec_known)


def test_satchecker(fixture_aa):
    """Test routines using satchecker API."""
    aa, tles = fixture_aa
    norad_id = satchecker_lookup_norad(aa, 'svom')
    print(norad_id)
    satchecker_get_tle(aa, t=aa.t[0], name='svom')
    satchecker_get_tle(aa, t=aa.t[0], norad_id=norad_id)
    aa.coords.satellites.satchecker_get_tle(t=aa.t[0], name='svom')

    satchecker_above_horizon(aa, min_altitude=80)
    aa.coords.satellites.satchecker_above_horizon(80)


if __name__ == '__main__':
    test_satellites()
