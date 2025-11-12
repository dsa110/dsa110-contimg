"""Utilities from loading AEPs into pyshtools."""

import healpy as hp
import numpy as np
from pyshtools import SHCoeffs

from ska_ost_low_uv.postx.aeps import load_aep_coeffs


def load_aep_coeffs_pysh(
    freq: float,
    aep: str = 'ska_low',
) -> dict[SHCoeffs]:
    """Load AEP from HDF5 file to pyshtools SHCoeffs.

    Args:
        freq (float): Frequency in MHz.
        aep (str): AEP to load (currently only 'ska_low' supported)

    Returns:
        aep_coeffs (dict): Dictionary with keys xx, yy, re_xy, im_xy.
                           Each entry is a 1D numpy array of SHC coefficients
                           that can be loaded with hp.sphtfunc.alm2map()
    """
    coeffs = load_aep_coeffs(freq, aep)

    lmax = coeffs['lmax']

    shc = {}
    for c in ('xx', 'yy', 're_xy', 'im_xy'):
        alm = hp.Alm()
        l, m = alm.getlm(lmax)
        d = np.zeros((2, lmax + 1, lmax + 1), dtype='float32')
        d[0, l, m] = coeffs[c].real
        d[1, l, m] = coeffs[c].imag
        shc[c] = SHCoeffs.from_array(d, normalization='ortho')
    return shc
