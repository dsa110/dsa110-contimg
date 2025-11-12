"""simulate_beam: Simple beam pattern simulation tool."""

from __future__ import annotations

import typing
import warnings

if typing.TYPE_CHECKING:  # pragma: no cover
    from ..aperture_array import ApertureArray

import numpy as np
import pylab as plt
from astropy.constants import c
from astropy.coordinates import SkyCoord

from ..aeps import load_aep_orth
from ..imaging.aa_imaging import generate_lmn_grid, make_image

LIGHT_SPEED = c.to('m/s').value
cos, sin = np.cos, np.sin


def to_db(x: np.ndarray) -> np.ndarray:
    """Convert array to dB scale, suppressing division by zero warnings.

    Args:
        x (np.ndarray): Input array to convert to dB scale.

    Returns:
        np.ndarray: Array converted to dB scale (10 * log10(x)).
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        return 10 * np.log10(np.abs(x))


def plot_beam_cuts(
    ant_arr: ApertureArray,
    img: np.ndarray,
    phase_center: SkyCoord,
    db: bool = True,
    figsize: tuple = (8, 4),
    reuse_fig: bool = False,
    subplot_id: tuple = None,
    pol_idx: int = 0,
):
    """Plot beam pattern cuts through pointing centre.

    Args:
        ant_arr (ApertureArray): ApertureArray station object
        img (np.ndarray): All-sky beam pattern image.
        lmn_grid (np.ndarray): Pointing grid in (l, m, n) coordinates.
        phase_center (SkyCoord): Pointing centre for beam.
        db (bool): If True, will plot in dB scale.
        figsize (tuple): Size for figure to plot
        reuse_fig (bool): If True, reuse the current figure for plotting.
        subplot_id (tuple): Subplot identifier for multi-panel plots.
        pol_idx (int): Coherence (pol) to load (0-3, default 0)
    """
    if subplot_id:
        plt.subplot(*subplot_id)

    n_pix = img.shape[0]
    lmn_grid = generate_lmn_grid(n_pix, abs_max=1, nan_below_horizon=True)
    ant_arr.viewer.n_pix = n_pix

    # Setup direction cosines
    px, py = ant_arr.viewer.get_pixel(phase_center)
    ll = lmn_grid[:, py, 1]
    mm = lmn_grid[px, :, 0]
    θx = np.rad2deg(np.arccos(ll)) - 90
    θy = np.rad2deg(np.arccos(mm)) - 90

    if img.ndim == 2:
        x_cut = img[px, :]
        y_cut = img[:, py]
    else:
        x_cut = img[px, :, pol_idx]
        y_cut = img[:, py, pol_idx]

    if db:
        x_cut = to_db(x_cut)
        y_cut = to_db(y_cut)
        x_cut -= np.nanmax(x_cut)
        y_cut -= np.nanmax(y_cut)

    if not reuse_fig:
        plt.figure(figsize=figsize)
    plt.subplot(1, 2, 1)
    plt.plot(θx, x_cut)
    plt.xlabel('X cut direction cosine [deg]')
    plt.ylabel('Magnitude [dB]')
    if db:
        plt.ylim(-50, 1)
    plt.minorticks_on()
    plt.subplot(1, 2, 2)
    plt.plot(θy, y_cut)
    plt.xlabel('Y cut direction cosine [deg]')
    plt.minorticks_on()
    if db:
        plt.ylim(-50, 1)
    plt.tight_layout()


def plot_beam_orthview(
    ant_arr: ApertureArray,
    img: np.ndarray,
    db: int = True,
    reuse_fig: bool = False,
    pol_idx: int = 0,
    **kwargs,
):
    """Plot beam pattern: 2D orthographic view.

    Args:
        ant_arr (AntArray): Antenna array to use.
        img (np.ndarray): All-sky beam pattern image.
        db (bool): If True, plot in dB scale.
        reuse_fig (bool): If True, reuse the current figure for plotting.
        pol_idx (int): Coherence (pol) to load (0-3, default 0)
        **kwargs: Additional keyword arguments passed to the viewer's orthview method.
    """
    f = ant_arr.f[ant_arr.idx['f']].to('MHz').value

    if 'overlay_coords' not in kwargs:
        kwargs['overlay_coords'] = 'altaz'
    if 'title' not in kwargs:
        kwargs['title'] = f'Beam pattern {f} MHz \n'
    if 'cmap' not in kwargs:
        kwargs['cmap'] = 'magma'

    if db:
        img_db = to_db(img)
        img = img_db - np.nanmax(img_db)
        # Set max and min
        kwargs['vmin'] = -50
        kwargs['vmax'] = 1

    if img.ndim == 2:
        ant_arr.viewer.orthview(img, **kwargs, colorbar=True, reuse_fig=reuse_fig)
    else:
        ant_arr.viewer.orthview(img[..., pol_idx], **kwargs, colorbar=True, reuse_fig=reuse_fig)

    cbar = plt.gca().images[-1].colorbar
    if db:
        cbar.set_label('Magnitude [dB]')
    else:
        cbar.set_label('Magnitude')


def simulate_beam(
    ant_arr: ApertureArray,
    phase_center: SkyCoord,
    n_pix: int = 129,
    weights: np.ndarray = None,
    apply_aep: bool = False,
    aep_name: str = 'ska_low',
    show: bool = False,
    plot_type: str = 'cut',
    db: bool = False,
    reuse_fig: bool = False,
    **kwargs,
) -> np.ndarray:
    """Simulate beam pattern.

    Currently only simulates array factor; element pattern and other effects are not yet included.

    Args:
        ant_arr (AntArray): Antenna array to use.
        phase_center (SkyCoord): Pointing direction for the beam pattern simulation.
        weights (np.ndarray): Optional per-antenna weights. Complex-valued, one weight per antenna.
        apply_aep (bool): Apply AEP to the beam pattern. Default False
        aep_name (str): AEP to load. Defaults to 'ska_low',
        aep_mode (str): Either 'linear' or 'stokes' AEP.
        n_pix (int): Number of pixels in beam pattern output
        show (bool): Plots beam pattern if True.
        plot_type (str): Type of plot to generate, either 'cut' or 'orthview'.
        db (bool): If True, will plot in dB scale (default False)
        reuse_fig (bool): If True, will reuse the current figure for plotting.
        **kwargs: Additional keyword arguments passed to plotting functions.

    Returns:
        image (np.array): Image of the simulated beam pattern. The pattern is a 2D array
                          with shape (n_pix, n_pix) representing the beam response at
                          different directions across the sky. Coordinates are in (l, m) space,
                          i.e. (-1, 1) corresponds to the full sky, and (l=0, m=0) is the zenith.
                          Note direction cosine angle theta = arccos(l) - 90

    """
    phs = ant_arr.coords.generate_phase_vector(phase_center, conj=True).squeeze()
    phsmat = np.outer(phs, np.conj(phs))

    if weights is not None:
        phsmat *= np.outer(weights, np.conj(weights))

    # For the beam sim, we do not use v0
    # v0 = np.zeros_like(phsmat)
    V_shape = list(phsmat.shape)
    V_shape.append(4)
    V = np.zeros_like(phsmat, shape=V_shape)
    V[..., 0] = phsmat
    V[..., 1] = phsmat
    V[..., 2] = phsmat
    V[..., 3] = phsmat

    img = make_image(ant_arr, vis=V, n_pix=n_pix)

    if apply_aep:
        _img = make_image(ant_arr, vis=V, n_pix=n_pix)
        aep = load_aep_orth(
            freq=ant_arr.f[ant_arr.idx['f']].to('MHz').value,
            npix=n_pix,
            fill_value=0,
            mode='linear',
            aep=aep_name,
            rot_angle=ant_arr.uvx.antennas.array_rotation_angle,
        )

        img[..., 0] = _img[..., 0] * aep[..., 0]
        img[..., 1] = _img[..., 0] * aep[..., 1]
        img[..., 2] = _img[..., 0] * aep[..., 2]
        img[..., 3] = _img[..., 0] * aep[..., 3]

    if show:
        if plot_type == 'cut':
            plot_beam_cuts(ant_arr, img, phase_center, db=db, reuse_fig=reuse_fig)
        elif plot_type == 'orthview':
            plot_beam_orthview(ant_arr, img, sfunc=np.real, db=db, reuse_fig=reuse_fig, **kwargs)
        else:
            raise ValueError(f'Unknown plot type: {plot_type}')

    if db:
        if apply_aep:
            return to_db(img)
        else:
            return to_db(img[..., 0])
    else:
        if apply_aep:
            return img
        else:
            return img[..., 0]
