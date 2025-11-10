"""
2D image fitting utilities for DSA-110 pipeline.

This module provides functions for fitting 2D models (Gaussian, Moffat) to sources
in astronomical images, including support for region constraints and initial guess estimation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.modeling import fitting, models
from astropy.wcs import WCS
from astropy.wcs.utils import skycoord_to_pixel
from scipy import ndimage, optimize

LOG = logging.getLogger(__name__)


def estimate_initial_guess(
    data: np.ndarray,
    mask: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """
    Estimate initial parameters for 2D fitting.

    Args:
        data: 2D image data
        mask: Optional boolean mask (True = use pixel, False = ignore)

    Returns:
        Dictionary with initial guess parameters:
        - amplitude: Peak flux value
        - x_center: X center in pixels
        - y_center: Y center in pixels
        - major_axis: Major axis FWHM in pixels
        - minor_axis: Minor axis FWHM in pixels
        - pa: Position angle in degrees
        - background: Background level
    """
    if mask is not None:
        masked_data = np.where(mask, data, np.nan)
    else:
        masked_data = data

    # Find peak location
    peak_idx = np.unravel_index(np.nanargmax(masked_data), masked_data.shape)
    y_center = float(peak_idx[0])
    x_center = float(peak_idx[1])
    amplitude = float(masked_data[peak_idx])

    # Estimate background (median of outer regions or percentile)
    if mask is not None:
        background_data = data[mask]
    else:
        # Use outer 20% of image for background estimate
        h, w = data.shape
        border_mask = np.zeros_like(data, dtype=bool)
        border_size = int(min(h, w) * 0.2)
        border_mask[border_size:-border_size, border_size:-border_size] = True
        background_data = data[~border_mask]

    background = (
        float(np.nanmedian(background_data)) if background_data.size > 0 else 0.0
    )

    # Estimate width using second moments
    # Subtract background for moment calculation
    signal_data = masked_data - background
    signal_data = np.where(signal_data > 0, signal_data, 0)

    if np.sum(signal_data) > 0:
        # Calculate weighted moments
        y_coords, x_coords = np.mgrid[0 : data.shape[0], 0 : data.shape[1]]

        total_flux = np.sum(signal_data)
        x_mean = np.sum(x_coords * signal_data) / total_flux
        y_mean = np.sum(y_coords * signal_data) / total_flux

        # Second moments
        xx_moment = np.sum((x_coords - x_mean) ** 2 * signal_data) / total_flux
        yy_moment = np.sum((y_coords - y_mean) ** 2 * signal_data) / total_flux
        xy_moment = (
            np.sum((x_coords - x_mean) * (y_coords - y_mean) * signal_data) / total_flux
        )

        # Calculate eigenvalues and eigenvectors for ellipse parameters
        cov_matrix = np.array([[xx_moment, xy_moment], [xy_moment, yy_moment]])
        eigenvals, eigenvecs = np.linalg.eigh(cov_matrix)

        # Major and minor axes (convert from sigma to FWHM)
        major_sigma = np.sqrt(eigenvals[1]) if eigenvals[1] > 0 else 1.0
        minor_sigma = np.sqrt(eigenvals[0]) if eigenvals[0] > 0 else 1.0

        major_axis = 2 * np.sqrt(2 * np.log(2)) * major_sigma  # FWHM
        minor_axis = 2 * np.sqrt(2 * np.log(2)) * minor_sigma  # FWHM

        # Position angle (angle of major axis)
        pa = np.degrees(np.arctan2(eigenvecs[1, 1], eigenvecs[0, 1]))
    else:
        # Fallback: use simple FWHM estimate from peak
        # Find FWHM by scanning from peak
        peak_value = amplitude - background
        half_max = peak_value / 2

        # Simple radial scan
        y_coords, x_coords = np.mgrid[0 : data.shape[0], 0 : data.shape[1]]
        distances = np.sqrt((x_coords - x_center) ** 2 + (y_coords - y_center) ** 2)

        above_half_max = signal_data >= half_max
        if np.any(above_half_max):
            max_distance = np.max(distances[above_half_max])
            major_axis = 2 * max_distance
            minor_axis = major_axis * 0.8  # Assume slight ellipticity
        else:
            major_axis = 2.0
            minor_axis = 2.0

        pa = 0.0

    return {
        "amplitude": amplitude - background,
        "x_center": x_center,
        "y_center": y_center,
        "major_axis": float(major_axis),
        "minor_axis": float(minor_axis),
        "pa": float(pa),
        "background": background,
    }


def fit_2d_gaussian(
    fits_file_path: str,
    region_mask: Optional[np.ndarray] = None,
    initial_guess: Optional[Dict[str, float]] = None,
    fit_background: bool = True,
    wcs: Optional[WCS] = None,
) -> Dict[str, Any]:
    """
    Fit a 2D Gaussian model to an image.

    Args:
        fits_file_path: Path to FITS file
        region_mask: Optional boolean mask (True = fit within, False = ignore)
        initial_guess: Optional initial parameters dictionary
        fit_background: Whether to fit background level
        wcs: Optional WCS object for coordinate conversion

    Returns:
        Dictionary with fit results:
        - model: "gaussian"
        - parameters: Fitted parameters (amplitude, center, major/minor axes, PA, background)
        - statistics: Fit statistics (chi-squared, reduced chi-squared, R-squared)
        - residuals: Residual statistics (mean, std, max)
        - center_wcs: Center coordinates in WCS (RA, Dec) if WCS available
    """
    try:
        with fits.open(fits_file_path) as hdul:
            if wcs is None:
                wcs = WCS(hdul[0].header)

            data = hdul[0].data

            # Handle multi-dimensional data
            if data.ndim > 2:
                data = data.squeeze()
                if data.ndim > 2:
                    LOG.warning(
                        f"Image {fits_file_path} has >2 dimensions, taking first slice for fitting."
                    )
                    data = data[0, 0] if data.ndim == 4 else data[0]

            # Apply region mask if provided
            if region_mask is not None:
                if region_mask.shape != data.shape:
                    raise ValueError("Region mask shape must match image shape")
                fit_mask = region_mask
            else:
                fit_mask = np.ones_like(data, dtype=bool)

            # Estimate initial guess if not provided
            if initial_guess is None:
                initial_guess = estimate_initial_guess(data, fit_mask)

            # Create coordinate grids
            y_coords, x_coords = np.mgrid[0 : data.shape[0], 0 : data.shape[1]]

            # Create 2D Gaussian model using astropy.modeling
            # Gaussian2D: amplitude, x_mean, y_mean, x_stddev, y_stddev, theta
            # We need to convert major/minor axes (FWHM) to stddev
            major_stddev = initial_guess["major_axis"] / (2 * np.sqrt(2 * np.log(2)))
            minor_stddev = initial_guess["minor_axis"] / (2 * np.sqrt(2 * np.log(2)))
            theta = np.radians(initial_guess["pa"])

            if fit_background:
                gaussian_model = models.Gaussian2D(
                    amplitude=initial_guess["amplitude"],
                    x_mean=initial_guess["x_center"],
                    y_mean=initial_guess["y_center"],
                    x_stddev=major_stddev,
                    y_stddev=minor_stddev,
                    theta=theta,
                ) + models.Const2D(amplitude=initial_guess["background"])
            else:
                gaussian_model = models.Gaussian2D(
                    amplitude=initial_guess["amplitude"],
                    x_mean=initial_guess["x_center"],
                    y_mean=initial_guess["y_center"],
                    x_stddev=major_stddev,
                    y_stddev=minor_stddev,
                    theta=theta,
                )

            # Prepare data for fitting
            fit_data = data[fit_mask]
            fit_x = x_coords[fit_mask]
            fit_y = y_coords[fit_mask]

            # Filter out non-finite values (NaN/Inf)
            finite_mask = np.isfinite(fit_data)
            if np.sum(finite_mask) == 0:
                raise ValueError("No finite values in data for fitting")

            fit_data = fit_data[finite_mask]
            fit_x = fit_x[finite_mask]
            fit_y = fit_y[finite_mask]

            # Fit the model
            fitter = fitting.LevMarLSQFitter()
            try:
                fitted_model = fitter(gaussian_model, fit_x, fit_y, fit_data)
            except Exception as e:
                LOG.error(f"Fitting failed, trying with bounds: {e}")
                # Retry with bounds
                if fit_background:
                    gaussian_model.amplitude_0.min = 0
                    gaussian_model.x_stddev_0.min = 0.1
                    gaussian_model.y_stddev_0.min = 0.1
                else:
                    gaussian_model.amplitude.min = 0
                    gaussian_model.x_stddev.min = 0.1
                    gaussian_model.y_stddev.min = 0.1

                fitted_model = fitter(gaussian_model, fit_x, fit_y, fit_data)

            # Extract fitted parameters
            if fit_background:
                gaussian_comp = fitted_model[0]
                background_comp = fitted_model[1]
                amplitude = float(gaussian_comp.amplitude.value)
                x_center = float(gaussian_comp.x_mean.value)
                y_center = float(gaussian_comp.y_mean.value)
                x_stddev = float(gaussian_comp.x_stddev.value)
                y_stddev = float(gaussian_comp.y_stddev.value)
                theta = float(gaussian_comp.theta.value)
                background = float(background_comp.amplitude.value)
            else:
                amplitude = float(fitted_model.amplitude.value)
                x_center = float(fitted_model.x_mean.value)
                y_center = float(fitted_model.y_mean.value)
                x_stddev = float(fitted_model.x_stddev.value)
                y_stddev = float(fitted_model.y_stddev.value)
                theta = float(fitted_model.theta.value)
                background = 0.0

            # Convert stddev back to FWHM
            major_axis = 2 * np.sqrt(2 * np.log(2)) * max(x_stddev, y_stddev)
            minor_axis = 2 * np.sqrt(2 * np.log(2)) * min(x_stddev, y_stddev)
            pa = np.degrees(theta)

            # Calculate fitted model values
            fitted_values = fitted_model(x_coords, y_coords)

            # Calculate residuals
            residuals = data - fitted_values
            residual_masked = residuals[fit_mask]

            # Calculate statistics
            chi_squared = np.sum((residual_masked) ** 2)
            n_params = 7 if fit_background else 6
            n_points = np.sum(fit_mask)
            reduced_chi_squared = (
                chi_squared / (n_points - n_params) if n_points > n_params else np.nan
            )

            ss_res = np.sum(residual_masked**2)
            ss_tot = np.sum((fit_data - np.mean(fit_data)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan

            # Convert center to WCS if available
            center_wcs = None
            if wcs is not None:
                try:
                    # Handle 4D WCS (common in radio astronomy)
                    if hasattr(wcs, "naxis") and wcs.naxis == 4:
                        # Use all_pix2world for 4D WCS
                        world_coords = wcs.all_pix2world(x_center, y_center, 0, 0, 0)
                        center_wcs = {
                            "ra": float(world_coords[0]),
                            "dec": float(world_coords[1]),
                        }
                    else:
                        # Standard 2D WCS
                        sky_coord = wcs.pixel_to_world(x_center, y_center)
                        center_wcs = {
                            "ra": float(sky_coord.ra.deg),
                            "dec": float(sky_coord.dec.deg),
                        }
                except Exception as e:
                    LOG.warning(f"Could not convert center to WCS: {e}")

            return {
                "model": "gaussian",
                "parameters": {
                    "amplitude": amplitude,
                    "center": {
                        "x": x_center,
                        "y": y_center,
                    },
                    "major_axis": float(major_axis),
                    "minor_axis": float(minor_axis),
                    "pa": float(pa),
                    "background": background,
                },
                "statistics": {
                    "chi_squared": float(chi_squared),
                    "reduced_chi_squared": float(reduced_chi_squared),
                    "r_squared": float(r_squared),
                },
                "residuals": {
                    "mean": float(np.mean(residual_masked)),
                    "std": float(np.std(residual_masked)),
                    "max": float(np.max(np.abs(residual_masked))),
                },
                "center_wcs": center_wcs,
            }

    except Exception as e:
        LOG.error(f"Error fitting 2D Gaussian to {fits_file_path}: {e}")
        raise


def fit_2d_moffat(
    fits_file_path: str,
    region_mask: Optional[np.ndarray] = None,
    initial_guess: Optional[Dict[str, float]] = None,
    fit_background: bool = True,
    wcs: Optional[WCS] = None,
) -> Dict[str, Any]:
    """
    Fit a 2D Moffat model to an image.

    Moffat profile: I(r) = A * (1 + (r/alpha)^2)^(-beta) + bg

    **Note:** This implementation supports circular Moffat profiles only
    (no rotation/ellipticity). For elliptical sources, use `fit_2d_gaussian`
    instead, which supports rotation and ellipticity.

    Args:
        fits_file_path: Path to FITS file
        region_mask: Optional boolean mask (True = fit within, False = ignore)
        initial_guess: Optional initial parameters dictionary
        fit_background: Whether to fit background level
        wcs: Optional WCS object for coordinate conversion

    Returns:
        Dictionary with fit results (same format as fit_2d_gaussian)
        Note: `pa` (position angle) will always be 0.0, and `minor_axis`
        is approximated as 0.9 * `major_axis` since rotation is not supported.

    See Also:
        fit_2d_gaussian: For elliptical sources (supports rotation)
        docs/analysis/MOFFAT_ROTATION_DEFERRED.md: Decision to defer rotation support
    """
    try:
        with fits.open(fits_file_path) as hdul:
            if wcs is None:
                wcs = WCS(hdul[0].header)

            data = hdul[0].data

            # Handle multi-dimensional data
            if data.ndim > 2:
                data = data.squeeze()
                if data.ndim > 2:
                    LOG.warning(
                        f"Image {fits_file_path} has >2 dimensions, taking first slice for fitting."
                    )
                    data = data[0, 0] if data.ndim == 4 else data[0]

            # Apply region mask if provided
            if region_mask is not None:
                if region_mask.shape != data.shape:
                    raise ValueError("Region mask shape must match image shape")
                fit_mask = region_mask
            else:
                fit_mask = np.ones_like(data, dtype=bool)

            # Estimate initial guess if not provided
            if initial_guess is None:
                initial_guess = estimate_initial_guess(data, fit_mask)

            # Create coordinate grids
            y_coords, x_coords = np.mgrid[0 : data.shape[0], 0 : data.shape[1]]

            # Create 2D Moffat model using astropy.modeling
            # Moffat2D: amplitude, x_0, y_0, gamma (alpha), alpha (beta)
            # Convert major/minor axes to gamma (alpha parameter)
            # For Moffat: FWHM = 2 * gamma * sqrt(2^(1/beta) - 1)
            # We'll use beta=2.5 as typical value, estimate gamma from FWHM
            beta = 2.5  # Typical value
            major_gamma = initial_guess["major_axis"] / (
                2 * np.sqrt(2 ** (1 / beta) - 1)
            )
            minor_gamma = initial_guess["minor_axis"] / (
                2 * np.sqrt(2 ** (1 / beta) - 1)
            )
            theta = np.radians(initial_guess["pa"])

            if fit_background:
                moffat_model = models.Moffat2D(
                    amplitude=initial_guess["amplitude"],
                    x_0=initial_guess["x_center"],
                    y_0=initial_guess["y_center"],
                    gamma=max(major_gamma, minor_gamma),
                    alpha=beta,
                ) + models.Const2D(amplitude=initial_guess["background"])
            else:
                moffat_model = models.Moffat2D(
                    amplitude=initial_guess["amplitude"],
                    x_0=initial_guess["x_center"],
                    y_0=initial_guess["y_center"],
                    gamma=max(major_gamma, minor_gamma),
                    alpha=beta,
                )

            # Prepare data for fitting
            fit_data = data[fit_mask]
            fit_x = x_coords[fit_mask]
            fit_y = y_coords[fit_mask]

            # Filter out non-finite values (NaN/Inf)
            finite_mask = np.isfinite(fit_data)
            if np.sum(finite_mask) == 0:
                raise ValueError("No finite values in data for fitting")

            fit_data = fit_data[finite_mask]
            fit_x = fit_x[finite_mask]
            fit_y = fit_y[finite_mask]

            # Fit the model
            fitter = fitting.LevMarLSQFitter()
            try:
                fitted_model = fitter(moffat_model, fit_x, fit_y, fit_data)
            except Exception as e:
                LOG.error(f"Moffat fitting failed, trying with bounds: {e}")
                # Retry with bounds
                if fit_background:
                    moffat_model.amplitude_0.min = 0
                    moffat_model.gamma_0.min = 0.1
                    moffat_model.alpha_0.min = 0.5
                    moffat_model.alpha_0.max = 10.0
                else:
                    moffat_model.amplitude.min = 0
                    moffat_model.gamma.min = 0.1
                    moffat_model.alpha.min = 0.5
                    moffat_model.alpha.max = 10.0

                fitted_model = fitter(moffat_model, fit_x, fit_y, fit_data)

            # Extract fitted parameters
            if fit_background:
                moffat_comp = fitted_model[0]
                background_comp = fitted_model[1]
                amplitude = float(moffat_comp.amplitude.value)
                x_center = float(moffat_comp.x_0.value)
                y_center = float(moffat_comp.y_0.value)
                gamma = float(moffat_comp.gamma.value)
                alpha = float(moffat_comp.alpha.value)
                background = float(background_comp.amplitude.value)
            else:
                amplitude = float(fitted_model.amplitude.value)
                x_center = float(fitted_model.x_0.value)
                y_center = float(fitted_model.y_0.value)
                gamma = float(fitted_model.gamma.value)
                alpha = float(fitted_model.alpha.value)
                background = 0.0

            # Convert gamma to FWHM
            fwhm_factor = 2 * np.sqrt(2 ** (1 / alpha) - 1)
            major_axis = fwhm_factor * gamma
            # Approximate (Moffat is circular in this implementation)
            minor_axis = major_axis * 0.9
            pa = 0.0  # Moffat2D in astropy doesn't support rotation directly
            # NOTE: For elliptical sources, use Gaussian fitting instead.
            # Moffat rotation support is deferred - see docs/analysis/MOFFAT_ROTATION_DEFERRED.md

            # Calculate fitted model values
            fitted_values = fitted_model(x_coords, y_coords)

            # Calculate residuals
            residuals = data - fitted_values
            residual_masked = residuals[fit_mask]

            # Calculate statistics
            chi_squared = np.sum((residual_masked) ** 2)
            n_params = 6 if fit_background else 5
            n_points = np.sum(fit_mask)
            reduced_chi_squared = (
                chi_squared / (n_points - n_params) if n_points > n_params else np.nan
            )

            ss_res = np.sum(residual_masked**2)
            ss_tot = np.sum((fit_data - np.mean(fit_data)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan

            # Convert center to WCS if available
            center_wcs = None
            if wcs is not None:
                try:
                    # Handle 4D WCS (common in radio astronomy)
                    if hasattr(wcs, "naxis") and wcs.naxis == 4:
                        # Use all_pix2world for 4D WCS
                        world_coords = wcs.all_pix2world(x_center, y_center, 0, 0, 0)
                        center_wcs = {
                            "ra": float(world_coords[0]),
                            "dec": float(world_coords[1]),
                        }
                    else:
                        # Standard 2D WCS
                        sky_coord = wcs.pixel_to_world(x_center, y_center)
                        center_wcs = {
                            "ra": float(sky_coord.ra.deg),
                            "dec": float(sky_coord.dec.deg),
                        }
                except Exception as e:
                    LOG.warning(f"Could not convert center to WCS: {e}")

            return {
                "model": "moffat",
                "parameters": {
                    "amplitude": amplitude,
                    "center": {
                        "x": x_center,
                        "y": y_center,
                    },
                    "major_axis": float(major_axis),
                    "minor_axis": float(minor_axis),
                    "pa": float(pa),
                    "background": background,
                    "gamma": float(gamma),
                    "alpha": float(alpha),
                },
                "statistics": {
                    "chi_squared": float(chi_squared),
                    "reduced_chi_squared": float(reduced_chi_squared),
                    "r_squared": float(r_squared),
                },
                "residuals": {
                    "mean": float(np.mean(residual_masked)),
                    "std": float(np.std(residual_masked)),
                    "max": float(np.max(np.abs(residual_masked))),
                },
                "center_wcs": center_wcs,
            }

    except Exception as e:
        LOG.error(f"Error fitting 2D Moffat to {fits_file_path}: {e}")
        raise
