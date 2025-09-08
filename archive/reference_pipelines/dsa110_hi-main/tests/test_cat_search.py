from dsa110hi.pipeline_msmaker import search_for_calibrator
from astropy.coordinates import SkyCoord, Angle
import astropy.units as u

import numpy as np

# Test return without match
# Test return without Sidx
# Test return with Sidx
# Test radius search
# Test ways of specifying the catalog

def test_search_match():
    # Coordinates for 3c48
    coords = SkyCoord("01:37:41.2995 +33:09:35.134", unit=(u.hourangle, u.deg), equinox="J2000.0")

    # Search in default catalog (which contains 3c48)
    match = search_for_calibrator(coords, 1.0)

    assert len(match)==6
    assert isinstance(match[1], Angle)
    assert isinstance(match[2], Angle)
    assert np.isclose(coords.ra.deg, match[1].deg)
    assert np.isclose(coords.dec.deg, match[2].deg)

def test_search_nomatch():
    # Coordinates for 3c48 - then apply an offset so that it won't match
    coords = SkyCoord("01:37:41.2995 +33:09:35.134", unit=(u.hourangle, u.deg), equinox="J2000.0")
    coords_offset = coords.directional_offset_by(0*u.deg, 1.001*u.deg)

    # Search in default catalog
    match = search_for_calibrator(coords_offset, 1.0)

    assert len(match)==6
    assert match[0]==None
    assert match[1]==None

    # Search in a wider radius
    match = search_for_calibrator(coords_offset, 1.1)

    assert len(match)==6
    assert isinstance(match[1], Angle)
    assert isinstance(match[2], Angle)
    assert np.isclose(coords.ra.deg, match[1].deg)
    assert np.isclose(coords.dec.deg, match[2].deg)

def test_search_manual_cat():
    # Coordinates for 3c48
    coords = SkyCoord("01:37:41.2995 +33:09:35.134", unit=(u.hourangle, u.deg), equinox="J2000.0")

    # Search in an alternative catalog (which contains 3c48)
    match = search_for_calibrator(coords, 1.0, '/data/pipeline/package_test_data/test_cal_cat.csv')

    assert len(match)==6
    assert isinstance(match[1], Angle)
    assert isinstance(match[2], Angle)
    assert np.isclose(coords.ra.deg, match[1].deg)
    assert np.isclose(coords.dec.deg, match[2].deg)

def test_search_multiple_sources():
    # Coordinates for a made up source in test catalog
    coords = SkyCoord("00:00:00 +00:00:00", unit=(u.hourangle, u.deg), equinox="J2000.0")

    # Search for it - shouldn't match because there are two sources within the radius
    match = search_for_calibrator(coords, 1.0, '/data/pipeline/package_test_data/test_cal_cat.csv')

    assert len(match)==6
    assert len(match[0])==2
    assert len(match[1])==2
    assert isinstance(match[1][0], Angle)
    assert isinstance(match[1][1], Angle)
    assert isinstance(match[2][0], Angle)
    assert isinstance(match[2][1], Angle)

    # Search again with a very small search radius
    match = search_for_calibrator(coords, 1/100, '/data/pipeline/package_test_data/test_cal_cat.csv')

    assert len(match)==6
    assert isinstance(match[1], Angle)
    assert isinstance(match[2], Angle)
    assert np.isclose(coords.ra.deg, match[1].deg)
    assert np.isclose(coords.dec.deg, match[2].deg)

