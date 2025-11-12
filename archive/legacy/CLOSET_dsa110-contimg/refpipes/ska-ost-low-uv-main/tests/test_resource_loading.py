"""Test_resource_loading: Test file path resolution tools."""

from ska_ost_low_uv.utils import get_aa_config, get_resource_path


def test_resource_loading():
    """Test get_resource_path."""
    print(get_resource_path('catch/me/if/you/can'))
    print(get_resource_path('config/aavs3/uv_config.yaml'))


def test_get_config():
    """Test get_aa_config."""
    print(get_aa_config('aavs2'))
    print(get_aa_config('aavs3'))


if __name__ == '__main__':
    test_resource_loading()
