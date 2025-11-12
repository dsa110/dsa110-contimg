"""holography: Tools for holographic calibration.

Implementation based on J. Thekkeppattu et al. (2024)
https://ui.adsabs.harvard.edu/abs/2024RaSc...5907847T/abstract
"""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    from ..aperture_array import ApertureArray

import warnings

import matplotlib as mpl
import numpy as np
import pylab as plt
from astropy.constants import c
from astropy.coordinates import SkyCoord
from loguru import logger

from ska_ost_low_uv.datamodel.cal import UVXAntennaCal, create_uvx_antenna_cal

from ..aa_module import AaBaseModule
from ..coords.coord_utils import gaincal_vec_to_matrix
from ..imaging.aa_imaging import generate_weight_grid

LIGHT_SPEED = c.value


##################
# HELPER FUNCTIONS
##################


def db(x):
    """Return dB value of power magnitude."""
    return 10 * np.log10(x)


def window2d(lmn: np.array, sigma: float = 1) -> np.array:
    """Apply 2D-Gaussian window to lmn data."""
    w2d = 1 / np.sqrt(2 * np.pi * sigma**2)
    w2d = w2d * np.exp(-(1 / (2 * sigma**2)) * (lmn[..., :2] ** 2).sum(axis=2))
    return w2d


def fft_2d_4pol(x: np.array, NFFT: int):
    """Apply 2D FFT with FFT shift to 4-pol data."""
    x_shifted = np.fft.ifftshift(x, axes=(0, 1))
    return np.fft.ifftshift(np.fft.ifft2(x_shifted, axes=(0, 1)), axes=(0, 1))


#################
## CORE JISNU CAL
#################


def generate_aperture_image(
    beam_corr: np.array, lm_matrix: np.array, sigma: float = 1.0, NFFT: int = 513
) -> np.array:
    """Generate aperture illumination from beam correlation (far-field E-pattern).

    Args:
        beam_corr (np.array): Beam cross-correlation between a calibrator source and a grid of
                              beams (spanning the range in lm_matrix arg). This is a measure of
                              the far-field electric field pattern.
                              Shape: (N_v, N_v) and dtype: complex64
        lm_matrix (np.array): A grid of direction cosine unit vectors, where N_v is
                              the number of pointings across the grid, each with a (l, m, n) value.
                              This can be generated with coord_utils.generate_lmn_grid().
                              Shape: (N_v, N_v, N_lmn=3), dtype: float
                              TODO: Why does it work better with unphysical l,m > 1?
        sigma (float): Sets width of Gaussian window applied before FFT. Defaults to 1.0
        NFFT (int): Number of points in the 2D FFT (and final image). Defaults to 513.
    """
    # Apply 2D gaussian window to lm_matrix
    w2d = window2d(lm_matrix, sigma=sigma)
    Ndim = beam_corr.shape[0]

    # Apply windowing and padding to beam_corr
    pad_len = int((NFFT - Ndim) / 2)
    beam_corr_windowed = np.einsum('ij,ijp->ijp', w2d, beam_corr)
    beam_corr_windowed_padded = np.pad(
        beam_corr_windowed, ((pad_len, pad_len), (pad_len, pad_len), (0, 0)), 'constant'
    )

    # Generate aperture image from 2D FFT (on all 4 pols)
    aperture_image = fft_2d_4pol(beam_corr_windowed_padded, NFFT)

    return aperture_image


def meas_corr_to_magcal(mc: np.array, target_mag: float = 1.0, sigma_thr: float = 10) -> np.array:
    """Compute magnitude calibration coefficients from meas_corr.

    Args:
        mc (np.array): Measured correlations between reference beam.
                       and each antenna.
                       Shape (N_ant, N_pol=4), dtype complex.
                       Pol ordering is XX, XY, YX, YY
        target_mag (float): Target magnitude to normalize to.
        sigma_thr (float): Masking threshold in terms of standard deviation

    Returns:
        pc (np.array): Phase calibration solutions.
                       Shape (N_ant, N_pol=2), dtype complex
    """
    mc_xy = mc[..., [0, 3]]

    # Magnitude Calibration
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', 'divide by zero encountered in divide')
        gc = target_mag / np.abs(mc_xy) * mc_xy.shape[0]

        # Simple normalization: mask values > 10x median
        # Then do (data - avg) / std
        gcm = (np.ma.array(gc, mask=gc > np.median(gc) * 10)).compressed()
        gcm = gcm[gcm > 0]
        gc_norm = (gc - np.median(gcm)) / np.std(gcm)
        gc = np.ma.array(gc, mask=gc_norm > sigma_thr)
        gc[gc.mask] = 0
        gc.mask = gc <= 0

    return gc


def meas_corr_to_phasecal(mc: np.array) -> np.array:
    """Compute phase calibration coefficients from meas_corr.

    Args:
        mc (np.array): Measured correlations between reference beam.
                              and each antenna.
                              Shape (N_ant, N_pol=4), dtype complex.
                              Pol ordering is XX, XY, YX, YY
    Returns:
        pc (np.array): Phase calibration solutions.
                       Shape (N_ant, N_pol=2), dtype complex
    """
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', "Warning: 'partition' will ignore the 'mask' of the MaskedArray.")

        mc_xy = mc[..., [0, 3]]

        # Run magcal first, so we can look for and flag bad antennas
        # Note we only use gc.mask, and ignore magnitude cal coeffs
        gc = meas_corr_to_magcal(mc, target_mag=1.0)

        # Phase calibration
        phs_ang = np.ma.array(np.angle(np.conj(mc_xy)), mask=gc.mask)
        phs_ang -= np.median(phs_ang)
        pc = np.exp(1j * phs_ang)
        pc[gc.mask] = 0
        pc.mask = gc.mask

    return pc


def jishnu_selfholo(
    aa: ApertureArray,
    cal_src: SkyCoord,
    abs_max: int = 4,
    aperture_padding: float = 3,
    NFFT: int = 2049,
    min_baseline_len: float = None,
    oversample_factor: int = 3,
    vis: str = 'data',
) -> dict:
    """Calibrate aperture array data using self-holography.

    Implementation based on J. Thekkeppattu et al. (2024)
    https://ui.adsabs.harvard.edu/abs/2024RaSc...5907847T/abstract

    Computes gain and phase calibration via self-holography on visibility data.
    A post-correlation beam is formed toward a strong calibrator source,
    then cross-correlated against a grid of beams (also formed from visibilities).

    The resulting 'beam correlation' is a measure of the far-field electric field
    pattern. A Fourier transform of the electric field pattern yields the
    'aperture illumination', which shows the gain and phase of each antenna.

    Args:
        aa (ApertureArray): Aperture array object (contains antenna positions
                            and data).
        cal_src (SkyCoord): Calibration source to use, such as the Sun. The source
                            needs to be much brighter than the background.
        abs_max (int): Maximum value of direction cosines (l, m). Default value 2.
                       Used to form a grid of beams across bounds (-abs_max, abs_max).
                       Note that values where sqrt(l^2 + m^2) > 1 are unphysical
                       (i.e. (l,m,n) is no longer a unit vector!), but we gain resolution
                       for reasons that Jishnu will explain at some stage.
        aperture_padding (float): Padding, in meters, around the maximum extents
                                  of the antenna array. For example, 3 meters
                                  around a 35 meter AAVS2 station.
                                  Sets the dimensions of the returned aperture
                                  illumination.
        NFFT (int): Size of FFT applied to produce aperture illumination. Default 1025.
                    Values of 2^N + 1 are the best choice. Data will be zero-padded before
                    the FFT is applied, which improves resolution in final image.
        min_baseline_len (float): Flags baselines shorter than this distance, if set.
                                  Note this does not seem to help much.
        oversample_factor (int): Amount to oversample lmn direction cosine plane. This increases
                                 resolution for the beam_corr (far-field E-pattern), at the
                                 expense of increasing the aperture illumination image size.
        vis (str): Visibility type to use - one of 'data', 'cal', 'corrected', or 'model'.
                   Passed to generate_vis_matrix() to select visibility data.

    Returns:
        cal = {

            'lmn_grid': Grid of direction cosines l,m,n. Shape (N_pix, N_pix, N_pol=4)
            'beam_corr': beam correlation, complex-valued (N_pix, N_pix, N_pol=4)
            'aperture_img': aperture illumination, complex-valued (NFFT, NFFT, N_pol=4)
            'meas_corr': measured correlations agains source for each antenna
                         (N_ant, N_pol=4)
            'vis_matrix': Visibility matrix, complex-valued (N_ant, N_ant, N_pol=4)
            'aperture_size': width of aperture plane in meters,
            'n_pix': Number of pixels in image
            'oversample_factor': oversample factor
        }

    Citation:
        Implentation based on J. Thekkeppattu et al. (2024)
        https://ui.adsabs.harvard.edu/abs/2024RaSc...5907847T/abstract
    """
    # Compute number of pixels required
    aperture_dim = np.max(aa.xyz_enu) - np.min(aa.xyz_enu) + aperture_padding
    λ = LIGHT_SPEED / aa.f.to('Hz').value
    n_pix = 2 * int(abs_max / (λ / aperture_dim)) + 1

    # Oversample so we can form beam pattern
    n_pix *= oversample_factor

    # Generate visibility matrix (N_ant, N_ant, N_pol=4)
    logger.info(f'Generating vis matrix: {vis}')
    V = aa.generate_vis_matrix(vis)

    if min_baseline_len:
        short_bls = aa.bl_matrix < min_baseline_len
        V[short_bls] = 0

    # Generate a grid of pointing vectors, and lmn direction cosine coords
    pv_grid, lmn = generate_weight_grid(aa, n_pix, abs_max=abs_max, nan_below_horizon=False)

    # Compute the phase vector required to phase up to the cal source
    pv_src = aa.coords.generate_phase_vector(cal_src, coplanar=True)

    # Compute the measured correlation between the source and each antenna
    # This has shape (N_ant, N_pol=4)
    meas_corr_src = np.einsum('i,ilp,l->ip', pv_src[0], V, np.conj(pv_src[0]), optimize='optimal')

    # Compute the beam correlation (a measure of far-field radiation pattern)
    # beam_corr will have shape (N_pix, N_pix, N_pol=4)
    beam_corr = np.einsum('alm,ap->lmp', pv_grid, meas_corr_src, optimize='optimal')

    # Finally, compute the aperture illumination
    # aperture_img will have shape (NFFT, NFFT, N_pol=4)
    aperture_img = generate_aperture_image(beam_corr, lmn, 1.0, NFFT)

    cal = {
        'beam_corr': beam_corr,
        'aperture_img': aperture_img,
        'meas_corr': meas_corr_src,
        'lmn_grid': lmn,
        'vis_matrix': V,
        'aperture_size': (λ / (lmn[0, 0, 0] - lmn[0, 1, 0]))[0],
        'n_pix': n_pix,
        'oversample_factor': oversample_factor,
    }
    return cal


def jishnu_phasecal(
    aa: ApertureArray,
    cal_src: dict,
    min_baseline_len: float = None,
    n_iter_max: int = 50,
    target_phs_std: float = 1.0,
) -> UVXAntennaCal:
    """Iteratively apply Jishnu Cal phase calibration.

    Args:
        aa (ApertureArray): Aperture Array object to apply calibration to
        cal_src (SkyCoord): Reference calibration source sky coordinates.
                            Must be dominant source in sky to work (e.g. the Sun)
        n_iter_max (int): Maximum number of iterations. Default 50
        min_baseline_len (float): Minimum baseline length to use in visibilty array
        target_phs_std (float): Target phase STDEV (in deg) at which to stop iterating.

    Returns:
        cal (UVXAntennaCal): Calibration solutions, in UVXAntennaCal format.
                        Phase calibration solution and runtime info, in provenance dict with keys:
                        'phs_cal': complex-valued np.array of phase corrections.
                                   Shape: (N_ant, N_pol=2), complex data.
                        'n_iter': Number of iterations before break point reached.
                        'phs_std': np.array of STD reached at each iteration.
                                   Shape (N_iter), dtype float.
    """
    # Compute the phase vector required to phase up to the cal source
    pv_src = aa.coords.generate_phase_vector(cal_src, coplanar=True)

    # Generate visibility matrix from aa
    V = aa.generate_vis_matrix()

    if min_baseline_len:
        short_bls = aa.bl_matrix < min_baseline_len
        V[short_bls] = 0

    # Now, we loop over n_iter, until the STD of phase stops decreasing
    phs_iter_list = np.zeros(n_iter_max)
    for ii in range(n_iter_max):
        if ii == 0:
            meas_corr_src = np.einsum('i,ilp,l->ip', pv_src[0], V, np.conj(pv_src[0]), optimize='optimal')
            cc = meas_corr_to_phasecal(meas_corr_src)

            cc_mat = gaincal_vec_to_matrix(cc)
            phs_std = np.std(np.angle(cc))
        else:
            meas_corr_iter = np.einsum(
                'i,ilp,l->ip',
                pv_src[0],
                V * cc_mat,
                np.conj(pv_src[0]),
                optimize='optimal',
            )
            cc_iter = meas_corr_to_phasecal(meas_corr_iter)

            phs_std_iter = np.std(np.angle(cc_iter))
            if phs_std_iter >= phs_std:
                logger.info(f'Iter {ii - 1}: Iteration phase std minima reached, breaking')
                break
            elif target_phs_std > np.rad2deg(phs_std_iter):
                logger.info(f'Iter {ii - 1}: Target phase std reached, breaking')
                break
            else:
                cc_iter_mat = gaincal_vec_to_matrix(cc_iter)
                cc_mat *= cc_iter_mat
                cc *= cc_iter

                # Update phs_std comparator
                phs_std = phs_std_iter

        # Log phase stdev iteration to
        phs_iter_list[ii] = phs_std

    # TODO: Check this. I think cc_iter needs to be iteratively applied?
    cc_dict = {'phs_cal': cc, 'n_iter': ii, 'phs_std': phs_iter_list[:ii]}

    cal_arr = np.expand_dims(cc_dict['phs_cal'].data, axis=0)
    flag_arr = np.expand_dims(cc_dict['phs_cal'].mask, axis=0)

    cal = create_uvx_antenna_cal(
        telescope=aa.name,
        method='jishnu_phasecal',
        antenna_gains_arr=cal_arr,
        antenna_flags_arr=flag_arr,
        f=aa.f,
        a=aa.ant_names,
        p=np.array(('X', 'Y')),
        provenance={'jishnu_phasecal': cc_dict},
    )

    return cal


def jishnu_cal(
    aa: ApertureArray,
    cal_src: dict,
    min_baseline_len: float = 0,
    n_iter_max: int = 50,
    target_phs_std: float = 1.0,
    target_mag: float = 1.0,
) -> UVXAntennaCal:
    """Iteratively apply Jishnu Cal phase calibration, then compute magnitude calibraiton.

    Args:
        aa (ApertureArray): Aperture Array object to apply calibration to
        cal_src (SkyCoord): Reference calibration source sky coordinates.
                            Must be dominant source in sky to work (e.g. the Sun)
        n_iter_max (int): Maximum number of iterations. Default 50
        min_baseline_len (float): Minimum baseline length to use in visibilty array
        target_phs_std (float): Target phase STDEV (in deg) at which to stop iterating.
        target_mag (float): Target magnitude. Default 1.0 (unity)

    Returns:
        cc_dict (dict): Phase calibration solution and runtime info, in dictionary with keys:
                        'phs_cal': complex-valued np.array of phase corrections.
                                   Shape: (N_ant, N_pol=2), complex data.
                        'n_iter': Number of iterations before break point reached.
                        'phs_std': np.array of STD reached at each iteration.
                                   Shape (N_iter), dtype float.
                        'target_phs_std': Target phase STDEV.
                        'target_mag': Target gain magnitude
                        'mag_cal': Magnitude-only calibration coefficents.
                        'cal': Magnitude + Phase calibration
    """
    # First, compute phase calibration
    cal = jishnu_phasecal(aa, cal_src, min_baseline_len, n_iter_max, target_phs_std)

    # Now we apply the phase calibration to the data temporarily and generate phase-cal visibilities
    aa.set_cal(cal)
    V = aa.generate_vis_matrix(vis='cal')
    aa.set_cal(None)

    # Compute the measured correlation between the source and each antenna
    pv_src = aa.coords.generate_phase_vector(cal_src, coplanar=True)
    meas_corr_src = np.einsum('i,ilp,l->ip', pv_src[0], V, np.conj(pv_src[0]), optimize='optimal')

    # Now, get gain coefficients and combine with phase corrs
    mag_cal = meas_corr_to_magcal(meas_corr_src, target_mag)
    cal_arr = mag_cal * cal.gains.values
    flag_arr = np.logical_or(mag_cal.mask, cal.flags)

    # Set any flagged antennas to zero
    cal_arr[flag_arr] = 0

    cal = create_uvx_antenna_cal(
        telescope=aa.name,
        method='jishnu_cal',
        antenna_gains_arr=cal_arr,
        antenna_flags_arr=flag_arr,
        f=aa.f,
        a=aa.ant_names,
        p=np.array(('X', 'Y')),
        provenance={'jishnu_cal': cal.provenance['jishnu_phasecal']},
    )

    return cal


###########################
## POST JISHNU-CAL ROUTINES
###########################


def report_flagged_antennas(aa: ApertureArray, cal: UVXAntennaCal) -> dict:
    """Find antennas that have been flagged during phase calibration.

    Args:
        aa (ApertureArray): Array object to use
        cal (UVXAntennaCal): UVXAntennaCal returned by calibration routine, e.g.
                         jishnu_phasecal

    Returns:
        bad_ants (dict): Dictionary of bad antenna identifiers and indexes.
                         Keys are 'x', 'y'
    """
    return cal.report_flagged_antennas()


####################
## PLOTTING ROUTINES
####################


def plot_aperture(
    aa: ApertureArray,
    cal: dict,
    pol_idx: int = 0,
    plot_type: str = 'mag',
    vmin: float = -40,
    phs_range: tuple = None,
    annotate: bool = False,
    s: int = None,
):
    """Plot aperture illumnation for given polarization index.

    Args:
        aa (ApertureArray): Aperture Array to use
        cal (dict): Calibration dictionary from jishnu_cal
        pol_idx (int): Polarization axis index. Default 0 (X-pol)
        plot_type (str): Either 'mag' for magnitude, or 'phs' for phase
        vmin (float): sets vmin in dB for magnitude plot colorscale range (vmin, 0)
                      Default value is -40 (-40 dB)
        phs_range (tuple): Sets phase scale range. Two floats in degrees, e.g. (-90, 90).
                           Default value is (-180, 180) degrees
        annotate (bool): Set to True to overlay antenna identifiers/names
        s (int): Sets circle size around antenna locations
    """
    ap_ex = cal['aperture_size']
    apim = cal['aperture_img']

    # Compute normalized magnitude
    img_db = 10 * np.log10(np.abs(apim[..., pol_idx]))
    img_db -= np.max(img_db)

    # Mask out areas where magnitude is low, so phase plot is cleaner
    img_phs = np.rad2deg(np.angle(apim[..., pol_idx]))
    phs_mask = img_db < -20
    img_phs = np.ma.array(img_phs, mask=phs_mask)

    # Create colormap for phase data
    phs_cmap = mpl.colormaps.get_cmap('viridis').copy()
    phs_cmap.set_bad(color='black')

    # set plotting limits, override if phs_range is set
    phs_range = (-180, 180) if phs_range is None else phs_range
    extent = [-ap_ex / 2, ap_ex / 2, ap_ex / 2, -ap_ex / 2]

    # Get antenna flags
    pcal = meas_corr_to_phasecal(cal['meas_corr'])
    ant_flags = np.logical_or(pcal.mask[:, 0], pcal.mask[:, 1])

    if plot_type == 'mag':
        plt.title(f'{aa.p[pol_idx]} Magnitude')
        plt.imshow(img_db, cmap='inferno', vmin=vmin, extent=extent)
        plt.colorbar(label='dB')
    elif plot_type == 'phs':
        plt.title(f'{aa.p[pol_idx]} Phase')
        plt.imshow(img_phs, cmap=phs_cmap, vmin=phs_range[0], vmax=phs_range[1], extent=extent)
        plt.colorbar(label='deg')
    else:
        raise RuntimeError("Need to plot 'mag' or 'phs'")
    plt.xlabel('E (m)')
    plt.ylabel('N (m)')

    # Account for oversample
    osamp = cal['oversample_factor']
    plt.xlim(-ap_ex / 2 / osamp, ap_ex / 2 / osamp)
    plt.ylim(-ap_ex / 2 / osamp, ap_ex / 2 / osamp)

    if annotate:
        ix, iy = aa.xyz_enu[:, 0], -aa.xyz_enu[:, 1]
        ixy = np.column_stack((ix, iy))
        for ii in range(aa.n_ant):
            text_color = 'red' if ant_flags[ii] else 'white'
            plt.annotate(
                text=aa.uvx.antennas.identifier[ii].values,
                xy=ixy[ii],
                color=text_color,
                size=8,
            )

        # Draw circles around antenna locations, showing bad antennas from flags in red
        # fmt: off
        circle_size = s if s else cal['aperture_img'].shape[0] / np.sqrt(aa.n_ant)
        plt.scatter(ix[ant_flags], iy[ant_flags], s=circle_size, facecolors='none', edgecolors='red', alpha=0.7)
        plt.scatter(ix[~ant_flags], iy[~ant_flags], s=circle_size, facecolors='none', edgecolors='white', alpha=0.7)
        # fmt: on


def plot_aperture_xy(
    aa: ApertureArray,
    cal: dict,
    vmin: float = -40,
    phs_range: tuple = None,
    annotate: bool = False,
    figsize: tuple = (10, 8),
):
    """Plot aperture illumnation function magnitude and phase, both polarizations.

    Plots a 2x2 grid for aperture illumination image, showing magnitude and phase
    for X and Y polarizations.

    Args:
        aa (ApertureArray): Aperture Array to use
        cal (dict): Calibration dictionary from jishnu_cal
        vmin (float): sets vmin in dB for magnitude plot colorscale range (vmin, 0)
                      Default value is -40 (-40 dB)
        phs_range (tuple): Sets phase scale range. Two floats in degrees, e.g. (-90, 90).
                           Default value is (-180, 180) degrees
        annotate (bool): Set to True to overlay antenna identifiers/names
        figsize (tuple): Size of figure, passed to plt.figure(figsize). Default (10, 8)

    """
    plt.figure(figsize=figsize)
    pidxs = [0, 3]
    for ii in range(2):
        pidx = pidxs[ii]

        plt.subplot(2, 2, 2 * ii + 1)
        plot_aperture(aa, cal, pidx, 'mag', vmin=vmin, annotate=annotate)

        plt.subplot(2, 2, 2 * ii + 2)
        plot_aperture(aa, cal, pidx, 'phs', phs_range=phs_range, annotate=annotate)

    plt.suptitle(f'{aa.name} station holography')
    plt.tight_layout()


def plot_jishnu_phasecal_iterations(cc_dict: dict):
    """Plot the iterative phase corrections applied in phasecal.

    Args:
        cc_dict (dict): Output dict from jishnu_phasecal
    """
    phs_std = np.rad2deg(cc_dict['phs_std'])
    plt.loglog(phs_std)
    plt.xlabel('Jishnu cal iteration')
    plt.ylabel('Phase STD [deg]')
    plt.ylim(phs_std[-1] / 1.5, phs_std[0])


def plot_farfield_beam_pattern(holo_dict: dict):
    """Plot the far-field beam power pattern, 2D cuts.

    Args:
        holo_dict (dict): Output of jishnu_selfholo()
    """
    bp = holo_dict['beam_corr']
    bp_x = bp[bp.shape[0] // 2, :, 0]
    bp_y = bp[:, bp.shape[0] // 2, 0]

    bp_x_pow = db(np.abs(bp_x**2))
    bp_y_pow = db(np.abs(bp_y**2))

    theta = np.rad2deg(np.arccos(holo_dict['lmn_grid'][0, :, 0])) - 90

    plt.plot(
        theta,
        bp_x_pow - np.max(bp_x_pow),
        label='X',
        color=mpl.cm.viridis(10),
        alpha=0.9,
    )
    plt.plot(
        theta,
        bp_y_pow - np.max(bp_y_pow),
        label='Y',
        color=mpl.cm.viridis(200),
        alpha=0.9,
    )
    plt.xlim(-90, 90)
    plt.xlabel('$\\theta$ from ref. beam [deg]')
    plt.ylabel('Normalized gain [dB]')
    plt.legend()
    plt.tight_layout()


####################
## HOLOGRAPHER CLASS
####################


class AaHolographer(AaBaseModule):
    """A class version of the above jishnu-cal holography routines."""

    def __init__(self, aa: ApertureArray, cal_src: SkyCoord = None):
        """Setup Holographer.

        Args:
            aa (ApertureArray): Aperture array 'parent' object to use
            cal_src (SkyCoord): Calibration reference source
        """
        self.aa = aa
        self.cal_src = cal_src
        self.phs_cal = None
        self.holo_dict = None
        self.cal = None
        self.__setup_docstrings('holography')

    def set_cal_src(self, cal_src: SkyCoord):
        """Set/change calibration source."""
        self.cal_src = cal_src

    def __setup_docstrings(self, name):
        self.__name__ = name
        self.name = name
        # Inherit docstrings
        self.run_phasecal.__func__.__doc__ = jishnu_phasecal.__doc__
        self.run_jishnucal.__func__.__doc__ = jishnu_cal.__doc__
        self.run_selfholo.__func__.__doc__ = jishnu_selfholo.__doc__
        self.report_flagged_antennas.__func__.__doc__ = report_flagged_antennas.__doc__
        self.plot_aperture.__func__.__doc__ = plot_aperture.__doc__
        self.plot_aperture_xy.__func__.__doc__ = plot_aperture_xy.__doc__
        self.plot_farfield_beam_pattern.__func__.__doc__ = plot_farfield_beam_pattern.__doc__
        self.plot_phasecal_iterations.__func__.__doc__ = plot_jishnu_phasecal_iterations.__doc__

    def __check_cal_src_set(self):
        if self.cal_src is None:
            e = 'Calibration source not set! Run set_cal_src() first.'
            logger.error(e)
            raise RuntimeError(e)

    def __check_holo_dict_set(self):
        if self.holo_dict is None:
            e = 'Self-holography not run yet! Run run_selfholo() first.'
            logger.error(e)
            raise RuntimeError(e)

    def __check_phs_cal_set(self):
        if self.phs_cal is None:
            e = 'Phase calibration not run yet! Run run_phasecal() first.'
            logger.error(e)
            raise RuntimeError(e)

    def run_phasecal(self, *args, **kwargs):
        # Docstring inherited from jishnu_phasecal function
        self.__check_cal_src_set()
        self.phs_cal = jishnu_phasecal(self.aa, self.cal_src, *args, **kwargs)
        return self.phs_cal

    def run_jishnucal(self, *args, **kwargs):
        # Docstring inherited from jishnu_phasecal function
        self.__check_cal_src_set()
        self.cal = jishnu_cal(self.aa, self.cal_src, *args, **kwargs)
        return self.cal

    def run_selfholo(self, *args, **kwargs):
        # Docstring inherited from jishnu_selfholo function
        self.__check_cal_src_set()
        self.holo_dict = jishnu_selfholo(self.aa, self.cal_src, *args, **kwargs)
        return self.holo_dict

    def report_flagged_antennas(self, *args, **kwargs):
        # Docstring inherited from report_flagged_antennas
        self.__check_phs_cal_set()
        return report_flagged_antennas(self.aa, self.phs_cal)

    def plot_phasecal_iterations(self, *args, **kwargs):
        # Docstring inherited from plot_jishnu_phasecal_iterations function
        self.__check_phs_cal_set()
        plot_jishnu_phasecal_iterations(self.phs_cal.provenance['jishnu_phasecal'])

    def plot_aperture(self, *args, **kwargs):
        # Docstring inherited from plot_aperture function
        self.__check_holo_dict_set()
        plot_aperture(self.aa, self.holo_dict, *args, **kwargs)

    def plot_aperture_xy(self, *args, **kwargs):
        # Docstring inherited from plot_aperture_xy function
        self.__check_holo_dict_set()
        plot_aperture_xy(self.aa, self.holo_dict, *args, **kwargs)

    def plot_farfield_beam_pattern(self, *args, **kwargs):
        # Docstring inherited from plot_farfield_beam_pattern
        self.__check_holo_dict_set()
        plot_farfield_beam_pattern(self.holo_dict)
