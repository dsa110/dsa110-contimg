"""Convert SKA-Low AEP (Antenna Element Pattern) files to HDF5 format.

This module provides functions to convert AEP .npz files into spherical harmonics
and store them in HDF5 format for efficient access and storage.
"""

import h5py
import hdf5plugin
import healpy as hp
import numpy as np
import pyshtools as pysh
import tqdm


def load_to_clm(fn: str, lmax: int = 99, pad_mode: str = 'reflect') -> dict:
    """Convert a SKA-Low EEP file (.npz) into spherical harmonics.

    Uses pyshtools to do a spherical mode expansion on each EEP.
    The npz files contain 'Ephi' and 'Etheta', which are numpy arrays
    with shape (n_ant=256, n_phi=721, n_theta=181), complex128 dtype.

    Args:
        fn (str): Name of .npz file to load. Both pols are loaded
                        i.e. Xpol.npz and Ypol.npz files.
        lmax (int): Maximum mode order l to expand to. Default 99.
        pad_mode (str): One of 'reflect', 'edge', 'mean', 'median', 'minimum', 'constant'

    Returns:
        aep_coeffs (dict): Dictionary of AEP spherical harmonic coefficients.
                           Keys are xx, re_xy, im_xy, and yy.
                           Data are in complex 1D array in healpix convention.
    """
    # Load data
    dx = np.load(fn.replace('Ypol', 'Xpol'))
    dy = np.load(fn.replace('Xpol', 'Ypol'))

    # Create padded arrays
    # fmt: off
    Ephi_x   = np.pad(dx['Ephi'], pad_width=((0, 0), (0, 180)), mode='edge')
    Etheta_x = np.pad(dx['Etheta'], pad_width=((0, 0), (0, 180)), mode='edge')
    Ephi_y   = np.pad(dy['Ephi'], pad_width=((0, 0), (0, 180)), mode='edge')
    Etheta_y = np.pad(dy['Etheta'], pad_width=((0, 0), (0, 180)), mode='edge')
    # fmt: on

    # Generate AEPs
    J = np.array(((Etheta_x, Ephi_x), (Etheta_y, Ephi_y))).transpose((2, 3, 0, 1))
    C = np.matmul(J, np.conjugate(np.swapaxes(J, -2, -1)))

    # fmt: off
    aep_dict = {
        'xx':   np.real(C[..., 0, 0]),
        're_xy': np.real(C[..., 0, 1]),
        'im_xy': np.imag(C[..., 0, 1]),
        'yy':    np.real(C[..., 1, 1]),
    }
    # fmt: on

    aep_coeffs = {}

    # Create a Healpix grid of lon, lat
    nside = 256
    pix_idx = np.arange(hp.nside2npix(nside))
    lon, lat = hp.pix2ang(nside, pix_idx, lonlat=True)

    for k, d in aep_dict.items():
        # Method 1: Brute force evaluate on grid
        E = pysh.SHGrid.from_array(d.T)
        E_clm = E.expand(lmax_calc=lmax, normalization='ortho', csphase=-1)

        # Evaluate at healpix grid locations
        hpx_sh = pysh.expand.MakeGridPoint(E_clm.coeffs, lat=lat, lon=lon, norm=4)  # norm=4 == ortho
        aep_coeffs[k] = hp.map2alm(hpx_sh, lmax=lmax)

        # Method 2: Complex coefficients
        # ~ DCP 2025.09.02 - Better than real coefficients, but still not right compared to direct
        # E = pysh.SHGrid.from_array(d.astype('complex64').T)
        # E_clm = E.expand(lmax_calc=lmax, normalization='ortho', csphase=-1)
        # alm = hp.Alm()
        # l, m = alm.getlm(lmax)
        # coeffs = E_clm.coeffs[0]
        # aep_coeffs[k] = coeffs[l, m]

        # Method 3: Real coefficients
        #! DCP 2025.09.02 - This method introduces a peculiar difference I don't quite understand
        #! Maps go negative, which is incorrect. Seems to be due to scaling of imaginary component of coeffs?
        # Convert to coefficients - use ortho normalization for healpix
        # E_clm = E.expand(lmax_calc=lmax, normalization='ortho', csphase=-1)
        # alm = hp.Alm()
        # l, m = alm.getlm(lmax)
        # coeffs = E_clm.coeffs[0] + 1j * E_clm.coeffs[1]
        # aep_coeffs[k] = coeffs[l, m]

    return aep_coeffs


def aeps_to_hdf5(aep_dirpath: str, outpath: str, lmax: int = 99, compression=None, chunks=None):
    """Convert directory of AEP .npz files to a HDF5 file.

    Notes:
        Assumes name convention HARP_SKALA41_randvogel_avg_{ff}MHz_Xpol.npz
        spaced by 1 MHz across 50-350 MHz (301 files per pol).

    Args:
        aep_dirpath (str): Directory containing AEP files.
        outpath (str): Output filename for HDF5
        lmax (int): Maximum spherical harmonic mode order l
        compression (hdf5plugin filter): compression filter to use (or None)
        chunks (tuple): Chunk shape to use, Defaults to None
    """
    # Set max l-mode for spherical harmonics
    alm = hp.Alm()
    l, m = alm.getlm(lmax)

    # fmt: off
    d = {
        'xx':   np.zeros(shape=(301, len(l)), dtype='complex64'),
        'yy':    np.zeros(shape=(301, len(l)), dtype='complex64'),
        're_xy': np.zeros(shape=(301, len(l)), dtype='complex64'),
        'im_xy': np.zeros(shape=(301, len(l)), dtype='complex64'),
    }
    # fmt: on

    for ii in tqdm.tqdm(range(301)):
        ff = ii + 50
        fp = f'{aep_dirpath}/HARP_SKALA41_randvogel_avg_{ff}MHz_Xpol.npz'
        coeffs = load_to_clm(fp, lmax=lmax)
        d['xx'][ii] = coeffs['xx']
        d['yy'][ii] = coeffs['yy']
        d['re_xy'][ii] = coeffs['re_xy']
        d['im_xy'][ii] = coeffs['im_xy']

    with h5py.File(outpath, 'w') as h5:
        for k in ('xx', 'yy', 're_xy', 'im_xy'):
            ds = h5.create_dataset(k, data=d[k], compression=compression, chunks=chunks)
            ds.attrs['convention'] = 'healpy'
            ds.attrs['lmax'] = lmax
            ds.attrs['start_frequency'] = 50
            ds.attrs['start_frequency_unit'] = 'MHz'
            ds.attrs['frequency_step'] = 1
            ds.attrs['frequency_step_unit'] = 'MHz'


if __name__ == '__main__':
    import os

    import hdf5plugin

    outpath = './ska_low.h5'

    # comp=None
    # comp = hdf5plugin.Zfp(reversible=True)
    comp = hdf5plugin.Blosc(cname='lz4hc', clevel=9)
    lmax = 51
    chunks = (32, 128)
    # chunks = None

    print(f'Saving to {outpath}...')
    aeps_to_hdf5(
        aep_dirpath='/Users/daniel.price/Data/ant-sph-tools/average-eeps',
        outpath=outpath,
        lmax=lmax,
        compression=comp,
        chunks=chunks,
    )
    print(f'File size: {os.path.getsize(outpath) / 1e6: .2f} MB')
