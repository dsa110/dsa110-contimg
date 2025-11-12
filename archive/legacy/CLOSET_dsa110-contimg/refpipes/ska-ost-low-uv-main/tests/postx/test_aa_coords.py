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
    aa.coords.get_sun()
    aa.coords.get_zenith()
    aa.coords.get_alt_az(aa.coords.get_zenith())
    aa.coords.generate_phase_vector(aa.coords.get_sun())
