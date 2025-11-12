"""test_antenna_cal: Testing antenna calibration tools."""

import numpy as np
from astropy.units import Quantity

from ska_ost_low_uv.datamodel.cal import (
    create_antenna_flags,
    create_antenna_gains,
    create_uvx_antenna_cal,
)


def test_antenna_cal():
    """Test antenna calibration array creation."""
    N_ant = 256
    N_freq = 1
    N_pol = 4

    cal = np.zeros((N_freq, N_ant, N_pol), dtype='complex64')
    flags = np.zeros_like(cal, dtype='bool')

    a = np.arange(N_ant)
    f = Quantity(np.arange(N_freq), unit='Hz')
    p = np.array(('xx', 'xy', 'yx', 'yy'))

    antenna_cal = create_antenna_gains(cal, f, a, p)
    antenna_flags = create_antenna_flags(cal, f, a, p)

    print(antenna_cal)
    print(antenna_flags)

    cal = create_uvx_antenna_cal('AAVS3', 'manual', cal, flags, f, a, p, {'history': 'yo'})

    cal_mat = cal.to_matrix(f_idx=0)
    assert cal_mat.shape == (256, 256, 4)


if __name__ == '__main__':
    test_antenna_cal()
