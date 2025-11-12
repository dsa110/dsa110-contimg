"""Test aa_plotter plotting routines."""

from ska_ost_low_uv.io import hdf5_to_uvx
from ska_ost_low_uv.postx import ApertureArray
from ska_ost_low_uv.utils import get_test_data


def test_aa_coords():
    """Test coordinate routines."""
    uvx = hdf5_to_uvx(
        get_test_data('aavs2_1x1000ms/correlation_burst_204_20230823_21356_0.hdf5'),
        telescope_name='aavs2',
    )
    aa = ApertureArray(uvx)
    tles = aa.coords.satellites.load_tles(get_test_data('satellites/tles_2025.01.22.txt'))
    aa.coords.satellites.compute_satellite_altaz(tles['SVOM'])
    aa.coords.satellites.compute_satellite_radec(tles['SVOM'])
    n_id = aa.coords.satellites.satchecker_lookup_norad('svom')
    aa.coords.satellites.satchecker_get_tle(t=aa.t[0], name='svom')
    aa.coords.satellites.satchecker_get_tle(t=aa.t[0], norad_id=n_id)
    aa.coords.satellites.satchecker_above_horizon(min_altitude=80)
