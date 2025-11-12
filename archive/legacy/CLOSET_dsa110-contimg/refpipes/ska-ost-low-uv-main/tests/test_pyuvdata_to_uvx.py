"""test_pyuvdata_to_uvx: tests for ska_ost_low_uv.io.from_pyuvdata."""

from pyuvdata import UVData

from ska_ost_low_uv.io.from_pyuvdata import (
    convert_data_to_uvx_convention,
    pyuvdata_to_uvx,
)
from ska_ost_low_uv.utils import get_test_data


def test_pyuvdata_to_uvx():
    """Test conversion from pyuvdata.UVData to UVX."""
    fn = get_test_data('aavs3/aavs3_chan204_20231115.uvfits')
    uv = UVData().from_file(fn)

    convert_data_to_uvx_convention(uv, check=True)
    convert_data_to_uvx_convention(uv, check=False)

    uvx = pyuvdata_to_uvx(uv)

    print(uvx)


if __name__ == '__main__':
    test_pyuvdata_to_uvx()
