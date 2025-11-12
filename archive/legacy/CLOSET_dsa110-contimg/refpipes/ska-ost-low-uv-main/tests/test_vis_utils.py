"""test_vis_utils: Test visibility utilities."""

import numpy as np
import pytest

from ska_ost_low_uv.vis_utils import vis_arr_to_matrix, vis_arr_to_matrix_4pol


def test_vis_arr_to_matrix():
    """Test vis_array_to_matrix."""
    # Upper
    d = np.arange(32896)
    V0 = vis_arr_to_matrix(d, 256)
    V = vis_arr_to_matrix(d, 256, 'upper')
    assert np.allclose(V, V0)

    V = vis_arr_to_matrix(d, 256, 'upper', conj=False)
    assert np.allclose(V, np.conj(V0))

    # Roundtrip
    ix, iy = np.triu_indices(256)
    assert np.allclose(V[ix, iy], d)

    # Lower
    d = np.arange(32896)
    V = vis_arr_to_matrix(d, 256, 'lower')
    # Roundtrip: lower
    ix, iy = np.tril_indices(256)
    assert np.allclose(V[ix, iy], d)

    # Use existing array
    V = np.zeros((256, 256))
    V = vis_arr_to_matrix(d, 256, 'lower', V=V)

    # Error - wrong N_ant
    with pytest.raises(RuntimeError):
        V = vis_arr_to_matrix(d, 99, 'lower')

    # Error - not upper/lower
    with pytest.raises(RuntimeError):
        V = vis_arr_to_matrix(d, 256, 'chicken')

    # Error - wrong vis shape
    with pytest.raises(RuntimeError):
        V = np.zeros((99, 99))
        V = vis_arr_to_matrix(d, 256, 'upper', V=V)


def test_vis_arr_to_matrix_4pol():
    """Test vis_array_to_matrix, 4-pol version."""
    d = np.arange(32896 * 4).reshape((32896, 4))
    V = vis_arr_to_matrix_4pol(d, 256)
    assert V.shape == (256, 256, 4)

    V = vis_arr_to_matrix_4pol(d, 256, 'upper')
    V = vis_arr_to_matrix_4pol(d, 256, 'lower')
    V = vis_arr_to_matrix_4pol(d, 256, 'lower', conj=False)
    Vc = vis_arr_to_matrix_4pol(d, 256, 'lower', conj=True)
    assert np.allclose(V, np.conj(Vc))

    with pytest.raises(RuntimeError):
        V = vis_arr_to_matrix_4pol(d, 256, 'chicken')

    with pytest.raises(RuntimeError):
        d = np.zeros((99, 99))
        V = vis_arr_to_matrix_4pol(d, 256, 'upper')


if __name__ == '__main__':
    test_vis_arr_to_matrix()
    test_vis_arr_to_matrix_4pol()
