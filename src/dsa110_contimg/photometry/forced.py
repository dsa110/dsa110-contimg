"""
Forced photometry utilities on FITS images (PB-corrected mosaics or tiles).

Enhanced implementation with features from VAST forced_phot:
- Cluster fitting for blended sources
- Chi-squared goodness-of-fit metrics
- Optional noise maps (separate FITS files)
- Source injection for testing
- Weighted convolution (Condon 1997) for accurate flux measurement
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from astropy import units as u
from astropy.io import fits  # type: ignore[reportMissingTypeStubs]

# type: ignore[reportMissingTypeStubs]
from astropy.modeling import fitting, models
from astropy.wcs import WCS  # type: ignore[reportMissingTypeStubs]

# type: ignore[reportMissingTypeStubs]
from astropy.wcs.utils import proj_plane_pixel_scales

try:
    import scipy.spatial  # type: ignore[reportMissingTypeStubs]

    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False

from dsa110_contimg.utils.runtime_safeguards import (
    filter_non_finite_2d,
)


@dataclass
class ForcedPhotometryResult:
    """Result from forced photometry measurement."""

    ra_deg: float
    dec_deg: float
    peak_jyb: float
    peak_err_jyb: float
    pix_x: float
    pix_y: float
    box_size_pix: int
    chisq: Optional[float] = None  # Chi-squared goodness-of-fit
    dof: Optional[int] = None  # Degrees of freedom
    # Cluster ID if part of blended source group
    cluster_id: Optional[int] = None


# Position angle offset: VAST uses E of N convention
PA_OFFSET = 90 * u.deg


def _world_to_pixel(
    wcs: WCS,
    ra_deg: float,
    dec_deg: float,
) -> Tuple[float, float]:
    xy = wcs.world_to_pixel_values(ra_deg, dec_deg)
    # astropy WCS: returns (x, y) with 0-based pixel coordinates
    return float(xy[0]), float(xy[1])


class G2D:
    """2D Gaussian kernel for forced photometry.

    Generates a 2D Gaussian kernel with specified FWHM and position angle.
    Used for weighted convolution flux measurement (Condon 1997).
    """

    def __init__(
        self,
        x0: float,
        y0: float,
        fwhm_x: float,
        fwhm_y: float,
        pa: Union[float, u.Quantity],
    ):
        """Initialize 2D Gaussian kernel.

        Args:
            x0: Mean x coordinate (pixels)
            y0: Mean y coordinate (pixels)
            fwhm_x: FWHM in x direction (pixels)
            fwhm_y: FWHM in y direction (pixels)
            pa: Position angle (E of N) in degrees or Quantity
        """
        self.x0 = x0
        self.y0 = y0
        self.fwhm_x = fwhm_x
        self.fwhm_y = fwhm_y
        # Convert PA to radians, adjust for E of N convention
        if isinstance(pa, u.Quantity):
            pa_rad = (pa - PA_OFFSET).to(u.rad).value
        else:
            pa_rad = np.deg2rad(pa - PA_OFFSET.value)
        self.pa = pa_rad

        # Convert FWHM to sigma
        self.sigma_x = self.fwhm_x / 2 / np.sqrt(2 * np.log(2))
        self.sigma_y = self.fwhm_y / 2 / np.sqrt(2 * np.log(2))

        # Pre-compute coefficients for efficiency
        self.a = (
            np.cos(self.pa) ** 2 / 2 / self.sigma_x**2
            + np.sin(self.pa) ** 2 / 2 / self.sigma_y**2
        )
        self.b = (
            np.sin(2 * self.pa) / 2 / self.sigma_x**2
            - np.sin(2 * self.pa) / 2 / self.sigma_y**2
        )
        self.c = (
            np.sin(self.pa) ** 2 / 2 / self.sigma_x**2
            + np.cos(self.pa) ** 2 / 2 / self.sigma_y**2
        )

    def __call__(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Evaluate kernel at given pixel coordinates.

        Args:
            x: X coordinates (pixels)
            y: Y coordinates (pixels)

        Returns:
            Kernel values at (x, y)
        """
        return np.exp(
            -self.a * (x - self.x0) ** 2
            - self.b * (x - self.x0) * (y - self.y0)
            - self.c * (y - self.y0) ** 2
        )


def _weighted_convolution(
    data: np.ndarray,
    noise: np.ndarray,
    kernel: np.ndarray,
) -> Tuple[float, float, float]:
    """Calculate flux using weighted convolution (Condon 1997).

    Args:
        data: Background-subtracted data
        noise: Noise map (RMS)
        kernel: 2D Gaussian kernel

    Returns:
        Tuple of (flux, flux_err, chisq)
    """
    kernel_n2 = kernel / noise**2
    flux = ((data) * kernel_n2).sum() / (kernel**2 / noise**2).sum()
    flux_err = ((noise) * kernel_n2).sum() / kernel_n2.sum()
    chisq = (((data - kernel * flux) / noise) ** 2).sum()

    return float(flux), float(flux_err), float(chisq)


def _identify_clusters(
    X0: np.ndarray,
    Y0: np.ndarray,
    threshold_pixels: float,
) -> Tuple[Dict[int, set], List[int]]:
    """Identify clusters of sources using KDTree.

    Args:
        X0: X pixel coordinates
        Y0: Y pixel coordinates
        threshold_pixels: Distance threshold in pixels

    Returns:
        Tuple of (clusters dict, in_cluster list)
    """
    if not HAVE_SCIPY:
        return {}, []

    if threshold_pixels <= 0 or len(X0) == 0:
        return {}, []

    tree = scipy.spatial.KDTree(np.c_[X0, Y0])
    clusters: Dict[int, set] = {}

    for i in range(len(X0)):
        dists, indices = tree.query(
            np.c_[X0[i], Y0[i]],
            k=min(10, len(X0)),
            distance_upper_bound=threshold_pixels,
        )
        indices = indices[~np.isinf(dists)]
        if len(indices) > 1:
            # Check if any indices are already in a cluster
            existing_cluster = None
            for idx in indices:
                for cluster_id, members in clusters.items():
                    if idx in members:
                        existing_cluster = cluster_id
                        break
                if existing_cluster is not None:
                    break

            if existing_cluster is not None:
                # Add all indices to existing cluster
                for idx in indices:
                    clusters[existing_cluster].add(idx)
            else:
                # Create new cluster
                clusters[i] = set(indices)

    in_cluster = sorted(list(chain.from_iterable(clusters.values())))
    return clusters, in_cluster


def measure_forced_peak(
    fits_path: str,
    ra_deg: float,
    dec_deg: float,
    *,
    box_size_pix: int = 5,
    annulus_pix: Tuple[int, int] = (12, 20),
    noise_map_path: Optional[str] = None,
    background_map_path: Optional[str] = None,
    nbeam: float = 3.0,
    use_weighted_convolution: bool = True,
) -> ForcedPhotometryResult:
    """Measure flux using forced photometry with optional weighted convolution.

    Uses weighted convolution (Condon 1997) when beam information is available,
    otherwise falls back to simple peak measurement.

    Args:
        fits_path: Path to FITS image
        ra_deg: Right ascension (degrees)
        dec_deg: Declination (degrees)
        box_size_pix: Size of measurement box (pixels) - used for simple peak mode
        annulus_pix: Annulus for RMS estimation (r_in, r_out) pixels
        noise_map_path: Optional path to noise map FITS file
        background_map_path: Optional path to background map FITS file
        nbeam: Size of cutout in units of beam major axis (for weighted convolution)
        use_weighted_convolution: Use weighted convolution if beam info available

    Returns:
        ForcedPhotometryResult with flux measurements and quality metrics
    """
    p = Path(fits_path)
    if not p.exists():
        return ForcedPhotometryResult(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            peak_jyb=float("nan"),
            peak_err_jyb=float("nan"),
            pix_x=float("nan"),
            pix_y=float("nan"),
            box_size_pix=box_size_pix,
        )

    # Load data/header
    hdr = fits.getheader(p)
    data = np.asarray(fits.getdata(p)).squeeze()

    # Load background if provided
    if background_map_path:
        bg_data = np.asarray(fits.getdata(background_map_path)).squeeze()
        if bg_data.shape != data.shape:
            raise ValueError(
                f"Background map shape {bg_data.shape} != image shape {data.shape}"
            )
        data = data - bg_data

    # Load noise map if provided
    noise_map = None
    if noise_map_path:
        noise_path = Path(noise_map_path)
        if noise_path.exists():
            noise_map = np.asarray(fits.getdata(noise_path)).squeeze()
            if noise_map.shape != data.shape:
                raise ValueError(
                    f"Noise map shape {noise_map.shape} != image shape {data.shape}"
                )
            # Convert zero-valued noise pixels to NaN
            noise_map[noise_map == 0] = np.nan

    # Use celestial 2D WCS
    wcs = WCS(hdr).celestial
    x0, y0 = _world_to_pixel(wcs, ra_deg, dec_deg)

    # Check for invalid coordinates
    if not (np.isfinite(x0) and np.isfinite(y0)):
        return ForcedPhotometryResult(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            peak_jyb=float("nan"),
            peak_err_jyb=float("nan"),
            pix_x=x0,
            pix_y=y0,
            box_size_pix=box_size_pix,
        )

    # Check if we can use weighted convolution
    has_beam_info = (
        "BMAJ" in hdr and "BMIN" in hdr and "BPA" in hdr and use_weighted_convolution
    )

    if has_beam_info:
        # Use weighted convolution method
        pixelscale = (proj_plane_pixel_scales(wcs)[1] * u.deg).to(u.arcsec)

        # Some generators (tests) store BMAJ/BMIN in arcsec instead of degrees.
        # Heuristic: values > 2 likely given in arcsec; else assume degrees.
        def _to_arcsec(v: float) -> float:
            try:
                val = float(v)
            except Exception:
                return float("nan")
            return val if val > 2.0 else val * 3600.0

        bmaj_arcsec = _to_arcsec(hdr["BMAJ"])  # Accept deg or arcsec
        bmin_arcsec = _to_arcsec(hdr["BMIN"])  # Accept deg or arcsec
        bpa_deg = hdr.get("BPA", 0.0)

        # Calculate cutout size in pixels
        npix = int(round((nbeam / 2.0) * bmaj_arcsec / pixelscale.value))
        cx, cy = int(round(x0)), int(round(y0))
        xmin = max(0, cx - npix)
        xmax = min(data.shape[-1], cx + npix + 1)
        ymin = max(0, cy - npix)
        ymax = min(data.shape[-2], cy + npix + 1)

        # Extract cutout
        sl = (slice(ymin, ymax), slice(xmin, xmax))
        cutout_data = data[sl]
        cutout_noise = noise_map[sl] if noise_map is not None else None

        # Generate kernel
        fwhm_x_pix = bmaj_arcsec / pixelscale.value
        fwhm_y_pix = bmin_arcsec / pixelscale.value
        x_coords = np.arange(xmin, xmax)
        y_coords = np.arange(ymin, ymax)
        xx, yy = np.meshgrid(x_coords, y_coords)
        g = G2D(x0, y0, fwhm_x_pix, fwhm_y_pix, bpa_deg)
        kernel = g(xx, yy)

        # Calculate noise if not provided
        if cutout_noise is None:
            # Use annulus-based RMS
            h, w = data.shape[-2], data.shape[-1]
            yy_full, xx_full = np.ogrid[0:h, 0:w]
            r = np.sqrt((xx_full - cx) ** 2 + (yy_full - cy) ** 2)
            rin, rout = annulus_pix
            ann = (r >= rin) & (r <= rout)
            vals = data[ann]
            finite_vals = vals[np.isfinite(vals)]
            if finite_vals.size == 0:
                rms = float("nan")
            else:
                m = np.median(finite_vals)
                s = 1.4826 * np.median(np.abs(finite_vals - m))
                mask = (finite_vals > (m - 3 * s)) & (finite_vals < (m + 3 * s))
                rms = float(np.std(finite_vals[mask])) if np.any(mask) else float("nan")
            cutout_noise = np.full_like(cutout_data, rms)

        # Filter NaN pixels
        good = (
            np.isfinite(cutout_data) & np.isfinite(cutout_noise) & np.isfinite(kernel)
        )
        if good.sum() == 0:
            return ForcedPhotometryResult(
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                peak_jyb=float("nan"),
                peak_err_jyb=float("nan"),
                pix_x=x0,
                pix_y=y0,
                box_size_pix=box_size_pix,
            )

        cutout_data_good = cutout_data[good]
        cutout_noise_good = cutout_noise[good]
        kernel_good = kernel[good]

        # Weighted convolution
        flux, flux_err, chisq = _weighted_convolution(
            cutout_data_good, cutout_noise_good, kernel_good
        )
        dof = int(good.sum() - 1)

        return ForcedPhotometryResult(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            peak_jyb=flux,
            peak_err_jyb=flux_err,
            pix_x=x0,
            pix_y=y0,
            box_size_pix=box_size_pix,
            chisq=chisq,
            dof=dof,
        )

    else:
        # Fall back to simple peak measurement (original method)
        cx, cy = int(round(x0)), int(round(y0))
        half = max(1, box_size_pix // 2)
        x1, x2 = cx - half, cx + half
        y1, y2 = cy - half, cy + half
        h, w = data.shape[-2], data.shape[-1]
        x1c, x2c = max(0, x1), min(w - 1, x2)
        y1c, y2c = max(0, y1), min(h - 1, y2)
        cut = data[y1c : y2c + 1, x1c : x2c + 1]
        finite_cut = cut[np.isfinite(cut)]
        peak = float(np.max(finite_cut)) if finite_cut.size > 0 else float("nan")

        # Local RMS in annulus
        rin, rout = annulus_pix
        yy, xx = np.ogrid[0:h, 0:w]
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        ann = (r >= rin) & (r <= rout)
        vals = data[ann]
        finite_vals = vals[np.isfinite(vals)]
        if finite_vals.size == 0:
            rms = float("nan")
        else:
            m = np.median(finite_vals)
            s = 1.4826 * np.median(np.abs(finite_vals - m))
            mask = (finite_vals > (m - 3 * s)) & (finite_vals < (m + 3 * s))
            rms = float(np.std(finite_vals[mask])) if np.any(mask) else float("nan")

        return ForcedPhotometryResult(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            peak_jyb=peak,
            peak_err_jyb=rms,
            pix_x=x0,
            pix_y=y0,
            box_size_pix=box_size_pix,
        )


def _measure_cluster(
    fits_path: str,
    positions: List[Tuple[float, float]],
    wcs: WCS,
    data: np.ndarray,
    noise_map: Optional[np.ndarray],
    hdr: fits.Header,
    nbeam: float = 3.0,
    annulus_pix: Tuple[int, int] = (12, 20),
) -> List[ForcedPhotometryResult]:
    """Measure flux for a cluster of blended sources using simultaneous fitting.

    Args:
        fits_path: Path to FITS image (for error messages)
        positions: List of (ra_deg, dec_deg) tuples
        wcs: WCS object
        data: Image data array
        noise_map: Optional noise map array
        hdr: FITS header
        nbeam: Size of cutout in units of beam major axis
        annulus_pix: Annulus for RMS estimation

    Returns:
        List of ForcedPhotometryResult objects
    """
    if not ("BMAJ" in hdr and "BMIN" in hdr and "BPA" in hdr):
        # Fall back to individual measurements
        return [
            measure_forced_peak(
                fits_path, ra, dec, nbeam=nbeam, annulus_pix=annulus_pix
            )
            for ra, dec in positions
        ]

    pixelscale = (proj_plane_pixel_scales(wcs)[1] * u.deg).to(u.arcsec)
    bmaj_arcsec = hdr["BMAJ"] * 3600.0
    bmin_arcsec = hdr["BMIN"] * 3600.0
    bpa_deg = hdr.get("BPA", 0.0)

    # Convert positions to pixels
    X0 = []
    Y0 = []
    for ra, dec in positions:
        x, y = _world_to_pixel(wcs, ra, dec)
        X0.append(x)
        Y0.append(y)
    X0 = np.array(X0)
    Y0 = np.array(Y0)

    # Calculate cutout bounds
    npix = int(round((nbeam / 2.0) * bmaj_arcsec / pixelscale.value))
    xmin = max(0, int(round((X0 - npix).min())))
    xmax = min(data.shape[-1], int(round((X0 + npix).max())) + 1)
    ymin = max(0, int(round((Y0 - npix).min())))
    ymax = min(data.shape[-2], int(round((Y0 + npix).max())) + 1)

    # Extract cutout
    sl = (slice(ymin, ymax), slice(xmin, xmax))
    cutout_data = data[sl]
    cutout_noise = noise_map[sl] if noise_map is not None else None

    # Calculate noise if not provided
    if cutout_noise is None:
        cx, cy = int(round(X0.mean())), int(round(Y0.mean()))
        h, w = data.shape[-2], data.shape[-1]
        yy_full, xx_full = np.ogrid[0:h, 0:w]
        r = np.sqrt((xx_full - cx) ** 2 + (yy_full - cy) ** 2)
        rin, rout = annulus_pix
        ann = (r >= rin) & (r <= rout)
        vals = data[ann]
        finite_vals = vals[np.isfinite(vals)]
        if finite_vals.size == 0:
            rms = float("nan")
        else:
            m = np.median(finite_vals)
            s = 1.4826 * np.median(np.abs(finite_vals - m))
            mask = (finite_vals > (m - 3 * s)) & (finite_vals < (m + 3 * s))
            rms = float(np.std(finite_vals[mask])) if np.any(mask) else float("nan")
        cutout_noise = np.full_like(cutout_data, rms)

    # Create meshgrid for cutout
    x_coords = np.arange(xmin, xmax)
    y_coords = np.arange(ymin, ymax)
    xx, yy = np.meshgrid(x_coords, y_coords)

    # Build composite model with fixed positions/shapes
    fwhm_x_pix = bmaj_arcsec / pixelscale.value
    fwhm_y_pix = bmin_arcsec / pixelscale.value
    sigma_x = fwhm_x_pix / 2 / np.sqrt(2 * np.log(2))
    sigma_y = fwhm_y_pix / 2 / np.sqrt(2 * np.log(2))
    pa_rad = np.deg2rad(bpa_deg - PA_OFFSET.value)

    composite_model = None
    for i, (x0, y0) in enumerate(zip(X0, Y0)):
        g = models.Gaussian2D(
            amplitude=1.0,  # Will be fitted
            x_mean=x0,
            y_mean=y0,
            x_stddev=sigma_x,
            y_stddev=sigma_y,
            theta=pa_rad,
            fixed={
                "x_mean": True,
                "y_mean": True,
                "x_stddev": True,
                "y_stddev": True,
                "theta": True,
            },
        )
        if composite_model is None:
            composite_model = g
        else:
            composite_model = composite_model + g

    # Filter NaN pixels
    good = np.isfinite(cutout_data) & np.isfinite(cutout_noise)
    if good.sum() == 0:
        return [
            ForcedPhotometryResult(
                ra_deg=ra,
                dec_deg=dec,
                peak_jyb=float("nan"),
                peak_err_jyb=float("nan"),
                pix_x=x,
                pix_y=y,
                box_size_pix=int(npix * 2),
            )
            for (ra, dec), x, y in zip(positions, X0, Y0)
        ]

    # Fit model
    fitter = fitting.LevMarLSQFitter()
    try:
        fitted_model = fitter(
            composite_model,
            xx[good],
            yy[good],
            cutout_data[good],
            weights=1.0 / cutout_noise[good] ** 2,
        )
        model = fitted_model(xx, yy)
        chisq_total = (
            ((cutout_data[good] - model[good]) / cutout_noise[good]) ** 2
        ).sum()
        dof_total = int(good.sum() - len(positions))
    except Exception:
        # Fit failed, return NaN results
        return [
            ForcedPhotometryResult(
                ra_deg=ra,
                dec_deg=dec,
                peak_jyb=float("nan"),
                peak_err_jyb=float("nan"),
                pix_x=x,
                pix_y=y,
                box_size_pix=int(npix * 2),
            )
            for (ra, dec), x, y in zip(positions, X0, Y0)
        ]

    # Extract fluxes and errors
    results = []
    for i, ((ra, dec), x, y) in enumerate(zip(positions, X0, Y0)):
        if i == 0:
            flux = fitted_model.amplitude_0.value
        else:
            flux = getattr(fitted_model, f"amplitude_{i}").value

        # Error estimated from noise map at source position
        cy_idx = int(round(y - ymin))
        cx_idx = int(round(x - xmin))
        if 0 <= cy_idx < cutout_noise.shape[0] and 0 <= cx_idx < cutout_noise.shape[1]:
            flux_err = float(cutout_noise[cy_idx, cx_idx])
        else:
            flux_err = float("nan")

        results.append(
            ForcedPhotometryResult(
                ra_deg=ra,
                dec_deg=dec,
                peak_jyb=float(flux),
                peak_err_jyb=flux_err,
                pix_x=x,
                pix_y=y,
                box_size_pix=int(npix * 2),
                chisq=chisq_total,
                dof=dof_total,
                cluster_id=0,  # All sources in same cluster
            )
        )

    return results


def measure_many(
    fits_path: str,
    coords: List[Tuple[float, float]],
    *,
    box_size_pix: int = 5,
    annulus_pix: Tuple[int, int] = (12, 20),
    noise_map_path: Optional[str] = None,
    background_map_path: Optional[str] = None,
    use_cluster_fitting: bool = False,
    cluster_threshold: float = 1.5,
    nbeam: float = 3.0,
) -> List[ForcedPhotometryResult]:
    """Measure flux for multiple sources with optional cluster fitting.

    Args:
        fits_path: Path to FITS image
        coords: List of (ra_deg, dec_deg) tuples
        box_size_pix: Size of measurement box (for simple peak mode)
        annulus_pix: Annulus for RMS estimation
        noise_map_path: Optional path to noise map FITS file
        background_map_path: Optional path to background map FITS file
        use_cluster_fitting: Enable cluster fitting for blended sources
        cluster_threshold: Cluster threshold in units of BMAJ (default 1.5)
        nbeam: Size of cutout in units of beam major axis

    Returns:
        List of ForcedPhotometryResult objects
    """
    if len(coords) == 0:
        return []

    # Load data once
    p = Path(fits_path)
    if not p.exists():
        return [
            ForcedPhotometryResult(
                ra_deg=ra,
                dec_deg=dec,
                peak_jyb=float("nan"),
                peak_err_jyb=float("nan"),
                pix_x=float("nan"),
                pix_y=float("nan"),
                box_size_pix=box_size_pix,
            )
            for ra, dec in coords
        ]

    hdr = fits.getheader(p)
    data = np.asarray(fits.getdata(p)).squeeze()

    # Load background if provided
    if background_map_path:
        bg_data = np.asarray(fits.getdata(background_map_path)).squeeze()
        data = data - bg_data

    # Load noise map if provided
    noise_map = None
    if noise_map_path:
        noise_path = Path(noise_map_path)
        if noise_path.exists():
            noise_map = np.asarray(fits.getdata(noise_path)).squeeze()
            noise_map[noise_map == 0] = np.nan

    wcs = WCS(hdr).celestial

    # Check if cluster fitting is enabled and beam info available
    if use_cluster_fitting and HAVE_SCIPY and "BMAJ" in hdr:
        # Identify clusters
        X0 = []
        Y0 = []
        for ra, dec in coords:
            x, y = _world_to_pixel(wcs, ra, dec)
            X0.append(x)
            Y0.append(y)
        X0 = np.array(X0)
        Y0 = np.array(Y0)

        pixelscale = (proj_plane_pixel_scales(wcs)[1] * u.deg).to(u.arcsec)
        bmaj_arcsec = hdr["BMAJ"] * 3600.0
        threshold_pixels = cluster_threshold * (bmaj_arcsec / pixelscale.value)

        clusters, in_cluster = _identify_clusters(X0, Y0, threshold_pixels)

        # Measure individual sources (not in clusters)
        results: List[ForcedPhotometryResult] = []
        cluster_results: Dict[int, List[ForcedPhotometryResult]] = {}

        for i, (ra, dec) in enumerate(coords):
            if i not in in_cluster:
                # Individual measurement
                result = measure_forced_peak(
                    fits_path,
                    ra,
                    dec,
                    box_size_pix=box_size_pix,
                    annulus_pix=annulus_pix,
                    noise_map_path=noise_map_path,
                    background_map_path=background_map_path,
                    nbeam=nbeam,
                )
                results.append(result)

        # Measure clusters
        for cluster_id, members in clusters.items():
            cluster_positions = [coords[i] for i in members]
            cluster_result = _measure_cluster(
                fits_path,
                cluster_positions,
                wcs,
                data,
                noise_map,
                hdr,
                nbeam=nbeam,
                annulus_pix=annulus_pix,
            )
            # Assign cluster IDs
            for j, member_idx in enumerate(members):
                cluster_result[j].cluster_id = cluster_id
            cluster_results[cluster_id] = cluster_result

        # Combine results in original order
        final_results: List[ForcedPhotometryResult] = []
        cluster_idx = {cluster_id: 0 for cluster_id in clusters.keys()}
        for i, (ra, dec) in enumerate(coords):
            if i not in in_cluster:
                # Find individual result
                for r in results:
                    if abs(r.ra_deg - ra) < 1e-6 and abs(r.dec_deg - dec) < 1e-6:
                        final_results.append(r)
                        break
            else:
                # Find cluster result
                for cluster_id, members in clusters.items():
                    if i in members:
                        idx = list(members).index(i)
                        final_results.append(cluster_results[cluster_id][idx])
                        break

        return final_results

    else:
        # Simple individual measurements
        return [
            measure_forced_peak(
                fits_path,
                ra,
                dec,
                box_size_pix=box_size_pix,
                annulus_pix=annulus_pix,
                noise_map_path=noise_map_path,
                background_map_path=background_map_path,
                nbeam=nbeam,
            )
            for ra, dec in coords
        ]


def inject_source(
    fits_path: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    *,
    output_path: Optional[str] = None,
    nbeam: float = 15.0,
) -> str:
    """Inject a fake source into a FITS image for testing.

    Args:
        fits_path: Path to input FITS image
        ra_deg: Right ascension (degrees)
        dec_deg: Declination (degrees)
        flux_jy: Flux to inject (Jy/beam)
        output_path: Optional output path (default: overwrites input)
        nbeam: Size of injection region in units of beam major axis

    Returns:
        Path to modified FITS file
    """
    p = Path(fits_path)
    if not p.exists():
        raise FileNotFoundError(f"FITS file not found: {fits_path}")

    # Load data/header
    hdul = fits.open(fits_path, mode="update" if output_path is None else "readonly")
    hdr = hdul[0].header
    data = hdul[0].data.squeeze()

    # Check for beam info
    if not ("BMAJ" in hdr and "BMIN" in hdr and "BPA" in hdr):
        raise ValueError("FITS header missing BMAJ, BMIN, or BPA keywords")

    wcs = WCS(hdr).celestial
    x0, y0 = _world_to_pixel(wcs, ra_deg, dec_deg)

    if not (np.isfinite(x0) and np.isfinite(y0)):
        raise ValueError(f"Invalid coordinates: ({ra_deg}, {dec_deg})")

    pixelscale = (proj_plane_pixel_scales(wcs)[1] * u.deg).to(u.arcsec)
    bmaj_arcsec = hdr["BMAJ"] * 3600.0
    bmin_arcsec = hdr["BMIN"] * 3600.0
    bpa_deg = hdr.get("BPA", 0.0)

    # Calculate cutout bounds
    npix = int(round((nbeam / 2.0) * bmaj_arcsec / pixelscale.value))
    xmin = max(0, int(round(x0 - npix)))
    xmax = min(data.shape[-1], int(round(x0 + npix)) + 1)
    ymin = max(0, int(round(y0 - npix)))
    ymax = min(data.shape[-2], int(round(y0 + npix)) + 1)

    # Generate kernel
    fwhm_x_pix = bmaj_arcsec / pixelscale.value
    fwhm_y_pix = bmin_arcsec / pixelscale.value
    x_coords = np.arange(xmin, xmax)
    y_coords = np.arange(ymin, ymax)
    xx, yy = np.meshgrid(x_coords, y_coords)
    g = G2D(x0, y0, fwhm_x_pix, fwhm_y_pix, bpa_deg)
    kernel = g(xx, yy)

    # Inject source
    sl = (slice(ymin, ymax), slice(xmin, xmax))
    data[sl] = data[sl] + kernel * flux_jy

    # Update HDU
    hdul[0].data = data.reshape(hdul[0].data.shape)

    # Write output
    if output_path:
        hdul.writeto(output_path, overwrite=True)
        hdul.close()
        return output_path
    else:
        hdul.flush()
        hdul.close()
        return fits_path
