"""vis_utils: Visibility matrix helper tools and utilities."""

import numpy as np


def vis_arr_to_matrix(d: np.ndarray, n_ant: int, tri: str = 'upper', V: np.array = None, conj=False):
    """Convert 1D visibility array (lower/upper) triangular to correlation matrix.

    Args:
        d (np.ndarray): 1D Numpy array with len N_ant * (N_ant + 1) / 2
        n_ant (int): Number of antennas in array
        tri (str): Either 'upper' or 'lower' triangular, to match data
        V (np.ndarray): Either None (create new array) or an (N_ant x N_ant) Numpy array
        conj (bool): Apply conjugation to data (default False)

    Returns:
        V (np.ndarray): (N_ant x N_ant) correlation matrix
    """
    n_bl = n_ant * (n_ant + 1) // 2
    if d.shape[0] != n_bl:
        raise RuntimeError(f'N_ant: {n_ant} -> N_bl: {n_bl}, but d.shape = {d.shape[0]}')
    if tri == 'upper':
        ix, iy = np.triu_indices(n_ant)
    elif tri == 'lower':
        ix, iy = np.tril_indices(n_ant)
    else:
        raise RuntimeError('Must be upper or lower triangular')

    if V is None:
        V = np.zeros((n_ant, n_ant), dtype='complex64')
    else:
        try:
            assert V.shape == (n_ant, n_ant)
        except AssertionError:
            raise RuntimeError('Correlation matrix shape mismatch') from None

    V[ix, iy] = d[:]
    V[iy, ix] = np.conj(d[:])

    if conj:
        V = np.conj(V)

    return V


def vis_arr_to_matrix_4pol(d: np.ndarray, n_ant: int, tri: str = 'upper', V: np.array = None, conj=False):
    """Convert 1D visibility array (lower/upper) triangular to correlation matrix, 4-pol.

    Args:
        d (np.ndarray): 1D Numpy array with len N_ant * (N_ant + 1) / 2
        n_ant (int): Number of antennas in array
        tri (str): Either 'upper' or 'lower' triangular, to match data
        V (np.ndarray): Either None (create new array) or an (N_ant x N_ant) Numpy array
        conj (bool): Apply conjugation to data (default False)

    Returns:
        V (np.ndarray): (N_ant x N_ant x 4 pol) correlation matrix, 4-pol
    """
    n_bl = n_ant * (n_ant + 1) // 2
    if d.shape[0] != n_bl:
        raise RuntimeError(f'N_ant: {n_ant} -> N_bl: {n_bl}, but d.shape = {d.shape[0]}')
    if tri == 'upper':
        ix, iy = np.triu_indices(n_ant)
    elif tri == 'lower':
        ix, iy = np.tril_indices(n_ant)
    else:
        raise RuntimeError('Must be upper or lower triangular')

    if V is None:
        V = np.zeros((n_ant, n_ant, 4), dtype='complex64')
    else:
        try:
            assert V.shape == (n_ant, n_ant, 4)
        except AssertionError:
            raise RuntimeError('Correlation matrix shape mismatch') from None

    V[ix, iy] = d[:]
    V[iy, ix] = np.conj(d[:])

    if conj:
        V = np.conj(V)

    return V
