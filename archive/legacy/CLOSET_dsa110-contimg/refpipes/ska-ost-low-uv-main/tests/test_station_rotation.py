"""test_station_rotation: test application of station rotation code."""

import os

import numpy as np
from astropy.io import fits as pf

from ska_ost_low_uv.converter import run
from ska_ost_low_uv.io import (
    hdf5_to_pyuvdata,
    hdf5_to_uvx,
    read_uvx,
    uvx_to_pyuvdata,
    write_ms,
    write_uvfits,
    write_uvx,
)
from ska_ost_low_uv.utils import get_test_data, import_optional_dependency

tables = import_optional_dependency('casacore.tables', errors='raise')

TEST_DATA = get_test_data('s8-6/correlation_burst_204_20240701_65074_0.hdf5')
TEST_RANG = 193.6
TEST_RANG_MS = [-3.37895743, -1.808161103]


def test_station_rotation():
    """Test station rotation keywords in written files."""
    try:
        uvx = hdf5_to_uvx(TEST_DATA, telescope_name='s8-6')

        # write to file, then read back
        write_uvx(uvx, 'tests/test_rotation.uvx')
        uvx2 = read_uvx('tests/test_rotation.uvx')

        # confirm they match known angle
        assert np.isclose(uvx.antennas.attrs['array_rotation_angle'], TEST_RANG)
        assert np.isclose(uvx2.antennas.attrs['array_rotation_angle'], TEST_RANG)

        # Confirm rotation angle added to UVData object
        uv = uvx_to_pyuvdata(uvx)
        uv2 = hdf5_to_pyuvdata(TEST_DATA, telescope_name='s8-6')
        assert np.isclose(uv.receptor_angle, TEST_RANG)
        assert np.isclose(uv2.receptor_angle, TEST_RANG)

        # Confirm MS writing adds RECEPTOR_ANGLE
        write_ms(uv, 'tests/test_rotation.ms')
        with tables.table('tests/test_rotation.ms/FEED', readonly=True) as t:
            assert np.allclose(t.getcol('RECEPTOR_ANGLE'), TEST_RANG_MS)

        # Confirm UVFITS writing adds POLAA/POLAB
        write_uvfits(uv, 'tests/test_rotation.uvfits')
        with pf.open('tests/test_rotation.uvfits', mode='readonly') as hdu:
            assert np.allclose(hdu[1].data['POLAA'], TEST_RANG)
            assert np.allclose(hdu[1].data['POLAB'], TEST_RANG + 90)

    finally:
        if os.path.exists('tests/test_rotation.uvx'):
            os.remove('tests/test_rotation.uvx')
        if os.path.exists('tests/test_rotation.uvfits'):
            os.remove('tests/test_rotation.uvfits')
        if os.path.exists('tests/test_rotation.ms'):
            os.system('rm -rf tests/test_rotation.ms')


def test_converter_rotation():
    """Test with sun phasing applied."""
    try:
        cmd = [
            '-o',
            'ms',
            '-n',
            's8-6',
            get_test_data('s8-6/correlation_burst_204_20240701_65074_0.hdf5'),
            'tests/test_rotation2.ms',
        ]
        run(cmd)

        # Confirm MS writing adds RECEPTOR_ANGLE
        with tables.table('tests/test_rotation2.ms/FEED', readonly=True) as t:
            assert np.allclose(t.getcol('RECEPTOR_ANGLE'), TEST_RANG_MS)
    finally:
        if os.path.exists('tests/test_rotation2.ms'):
            os.system('rm -rf tests/test_rotation2.ms')


if __name__ == '__main__':
    # test_station_rotation()
    test_converter_rotation()
