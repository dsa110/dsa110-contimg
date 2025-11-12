"""aep_viewers.py."""

import healpy as hp
from pylab import plt

from .aep_models import load_aep


def orthview_aep(f: float, reuse_fig: bool = False, mode: str = 'linear', aep: str = 'ska_low', **kwargs):
    """Plot AEPs.

    Args:
        f (float): Frequency to plot in MHz.
        mode (str): Either 'linear' or 'stokes' basis.
        reuse_fig (bool): If true, will not create new figure.
        aep (str): AEP to load (currently only 'ska_low' supported)
        **kwargs (dict): Dictionary of kwargs to pass to plotter
    """
    aep_hpx = load_aep(f, mode=mode, aep=aep)

    labels = ('XX*', 'real(XY*)', 'imag(XY*)', 'YY*')

    if mode == 'stokes':
        labels = ('Stokes I', 'Stokes Q', 'Stokes U', 'Stokes V')

    if not reuse_fig:
        plt.figure(figsize=(8, 8))

    plt.subplot(2, 2, 1)
    hp.orthview(aep_hpx[..., 0], half_sky=True, hold=True, title=labels[0], min=0, **kwargs)
    plt.subplot(2, 2, 2)
    hp.orthview(aep_hpx[..., 1], half_sky=True, hold=True, title=labels[1], **kwargs)
    plt.subplot(2, 2, 3)
    hp.orthview(aep_hpx[..., 2], half_sky=True, hold=True, title=labels[2], **kwargs)
    plt.subplot(2, 2, 4)
    cmin = 0 if mode == 'linear' else None
    hp.orthview(aep_hpx[..., 3], half_sky=True, hold=True, title=labels[3], min=cmin, **kwargs)
    plt.suptitle(f'AEP @ {f} MHz')
    plt.tight_layout()
