"""test_yaml: test yaml loading."""

from ska_ost_low_uv.utils import load_config


def test_yaml():
    """Test load_config works."""
    print(load_config('aavs2'))


if __name__ == '__main__':
    test_yaml()
