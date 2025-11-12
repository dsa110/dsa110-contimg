"""Test aa_plotter plotting routines."""

import numpy as np

from ska_ost_low_uv.postx.coords.coord_utils import generate_lmn_grid, lmn_to_altaz


def test_coord_utils():
    """Test coordinate routines."""
    l, m, n = generate_lmn_grid(129).T
    alt, az = lmn_to_altaz(l, m, n)

    assert l[64, 64] == 0
    assert m[64, 64] == 0
    assert n[64, 64] == 1
    assert np.isclose(alt[64, 64], np.pi / 2)
    assert np.isclose(az[64, 0], np.pi)
