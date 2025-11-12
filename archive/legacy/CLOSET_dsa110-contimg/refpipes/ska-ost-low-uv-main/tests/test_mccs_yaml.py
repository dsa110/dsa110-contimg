"""test_mccs_yaml: Testing MCCS YAML parsing."""

from ska_ost_low_uv.io.mccs_yaml import station_location_from_platform_yaml
from ska_ost_low_uv.utils import get_resource_path


def test_mccs_yaml():
    """Test MCCS YAML parsing."""
    fn = get_resource_path('config/aavs3/mccs_aavs3_0.1.0.yaml')
    earth_loc, ant_enu = station_location_from_platform_yaml(fn, 'aavs3')
    print(earth_loc)
    print(ant_enu)


if __name__ == '__main__':
    test_mccs_yaml()
