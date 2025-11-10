"""
Spatial profile extraction utilities for DSA-110 pipeline.

This module provides functions for extracting 1D profiles from 2D astronomical images,
including line profiles, polyline profiles, and radial profiles. It also provides
profile fitting capabilities using scipy and astropy.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import skycoord_to_pixel
from scipy import interpolate, optimize, stats

LOG = logging.getLogger(__name__)


def extract_line_profile(
    fits_file_path: str,
    start_coord: Tuple[float, float],
    end_coord: Tuple[float, float],
    coordinate_system: str = "wcs",
    width_pixels: int = 1,
) -> Dict[str, Any]:
    """
    Extract a 1D profile along a line in a FITS image.

    Args:
        fits_file_path: Path to FITS file
        start_coord: Starting coordinate (RA, Dec) in degrees if wcs, (x, y) if pixel
        end_coord: Ending coordinate (RA, Dec) in degrees if wcs, (x, y) if pixel
        coordinate_system: 'wcs' or 'pixel'
        width_pixels: Width of profile extraction in pixels (for averaging perpendicular to line)

    Returns:
        Dictionary with:
        - distance: Array of distances along profile (arcsec)
        - flux: Array of flux values (Jy/beam)
        - error: Array of error values (Jy/beam) if available
        - coordinates: List of coordinate pairs along profile
        - units: Dictionary with unit information
    """
    try:
        with fits.open(fits_file_path) as hdul:
            wcs = WCS(hdul[0].header)
            data = hdul[0].data

            # Handle multi-dimensional data (Stokes, frequency axes)
            if data.ndim > 2:
                data = data.squeeze()
                if data.ndim > 2:
                    LOG.warning(
                        f"Image {fits_file_path} has >2 dimensions, taking first slice for profile."
                    )
                    data = data[0, 0] if data.ndim == 4 else data[0]

            # Convert coordinates to pixel space if needed
            if coordinate_system == "wcs":
                start_skycoord = SkyCoord(start_coord[0], start_coord[1], unit="deg")
                end_skycoord = SkyCoord(end_coord[0], end_coord[1], unit="deg")
                start_pixel = skycoord_to_pixel(start_skycoord, wcs)
                end_pixel = skycoord_to_pixel(end_skycoord, wcs)
            else:
                start_pixel = (start_coord[0], start_coord[1])
                end_pixel = (end_coord[0], end_coord[1])

            # Calculate line length and number of samples
            line_length_pixels = np.sqrt(
                (end_pixel[0] - start_pixel[0]) ** 2
                + (end_pixel[1] - start_pixel[1]) ** 2
            )
            n_samples = max(int(line_length_pixels), 10)  # At least 10 samples

            # Generate points along the line
            t_values = np.linspace(0, 1, n_samples)
            x_coords = start_pixel[0] + t_values * (end_pixel[0] - start_pixel[0])
            y_coords = start_pixel[1] + t_values * (end_pixel[1] - start_pixel[1])

            # Extract flux values along the line
            flux_values = []
            coordinates = []

            for i, (x, y) in enumerate(zip(x_coords, y_coords)):
                # Extract perpendicular to line for averaging
                if width_pixels > 1:
                    # Calculate perpendicular direction
                    dx = end_pixel[0] - start_pixel[0]
                    dy = end_pixel[1] - start_pixel[1]
                    length = np.sqrt(dx**2 + dy**2)
                    if length > 0:
                        perp_x = -dy / length
                        perp_y = dx / length

                        # Sample perpendicular to line
                        width_samples = []
                        for w in np.linspace(
                            -width_pixels / 2, width_pixels / 2, width_pixels
                        ):
                            px = int(x + w * perp_x)
                            py = int(y + w * perp_y)
                            if 0 <= px < data.shape[1] and 0 <= py < data.shape[0]:
                                width_samples.append(data[py, px])

                        if width_samples:
                            flux = np.mean(width_samples)
                        else:
                            flux = np.nan
                    else:
                        flux = np.nan
                else:
                    # Single pixel extraction
                    px = int(round(x))
                    py = int(round(y))
                    if 0 <= px < data.shape[1] and 0 <= py < data.shape[0]:
                        flux = data[py, px]
                    else:
                        flux = np.nan

                flux_values.append(float(flux))

                # Convert back to WCS if needed
                if coordinate_system == "wcs":
                    pixel_coord = (x, y)
                    sky_coord = wcs.pixel_to_world_values(
                        pixel_coord[0], pixel_coord[1]
                    )
                    coordinates.append([float(sky_coord[0]), float(sky_coord[1])])
                else:
                    coordinates.append([float(x), float(y)])

            # Calculate distances along profile
            if coordinate_system == "wcs":
                # Calculate angular distance in arcsec
                pixel_scale = wcs.proj_plane_pixel_scales()[0].to("arcsec").value
                distances = np.linspace(0, line_length_pixels * pixel_scale, n_samples)
                distance_unit = "arcsec"
            else:
                distances = np.linspace(0, line_length_pixels, n_samples)
                distance_unit = "pixels"

            # Estimate errors (use local RMS if available, otherwise use std of perpendicular samples)
            error_values = [0.0] * len(flux_values)  # Placeholder

            # Try to get flux unit from header
            flux_unit = "Jy/beam"  # Default
            if "BUNIT" in hdul[0].header:
                flux_unit = str(hdul[0].header["BUNIT"])

            return {
                "distance": distances.tolist(),
                "flux": flux_values,
                "error": error_values,
                "coordinates": coordinates,
                "units": {
                    "distance": distance_unit,
                    "flux": flux_unit,
                },
            }

    except Exception as e:
        LOG.error(f"Error extracting line profile from {fits_file_path}: {e}")
        raise


def extract_polyline_profile(
    fits_file_path: str,
    coordinates: List[Tuple[float, float]],
    coordinate_system: str = "wcs",
    width_pixels: int = 1,
) -> Dict[str, Any]:
    """
    Extract a 1D profile along a polyline (multiple connected line segments).

    Args:
        fits_file_path: Path to FITS file
        coordinates: List of coordinate pairs defining the polyline
        coordinate_system: 'wcs' or 'pixel'
        width_pixels: Width of profile extraction in pixels

    Returns:
        Dictionary with profile data (same format as extract_line_profile)
    """
    if len(coordinates) < 2:
        raise ValueError("Polyline must have at least 2 points")

    # Extract profile for each segment and concatenate
    all_distances = []
    all_flux = []
    all_error = []
    all_coords = []
    cumulative_distance = 0.0

    for i in range(len(coordinates) - 1):
        start_coord = coordinates[i]
        end_coord = coordinates[i + 1]

        segment_profile = extract_line_profile(
            fits_file_path,
            start_coord,
            end_coord,
            coordinate_system,
            width_pixels,
        )

        # Adjust distances to be cumulative
        segment_distances = np.array(segment_profile["distance"])
        if i > 0:
            # Skip first point to avoid duplication
            segment_distances = segment_distances[1:] + cumulative_distance
            all_distances.extend(segment_distances.tolist())
            all_flux.extend(segment_profile["flux"][1:])
            all_error.extend(segment_profile["error"][1:])
            all_coords.extend(segment_profile["coordinates"][1:])
        else:
            all_distances.extend(segment_distances.tolist())
            all_flux.extend(segment_profile["flux"])
            all_error.extend(segment_profile["error"])
            all_coords.extend(segment_profile["coordinates"])

        cumulative_distance = all_distances[-1] if all_distances else 0.0

    return {
        "distance": all_distances,
        "flux": all_flux,
        "error": all_error,
        "coordinates": all_coords,
        "units": segment_profile["units"],  # Same units for all segments
    }


def extract_point_profile(
    fits_file_path: str,
    center_coord: Tuple[float, float],
    radius_arcsec: float,
    coordinate_system: str = "wcs",
    n_annuli: int = 20,
) -> Dict[str, Any]:
    """
    Extract a radial profile from a point (ensemble profile).

    Args:
        fits_file_path: Path to FITS file
        center_coord: Center coordinate (RA, Dec) in degrees if wcs, (x, y) if pixel
        radius_arcsec: Maximum radius in arcseconds
        coordinate_system: 'wcs' or 'pixel'
        n_annuli: Number of radial bins

    Returns:
        Dictionary with radial profile data
    """
    try:
        with fits.open(fits_file_path) as hdul:
            wcs = WCS(hdul[0].header)
            data = hdul[0].data

            # Handle multi-dimensional data
            if data.ndim > 2:
                data = data.squeeze()
                if data.ndim > 2:
                    LOG.warning(
                        f"Image {fits_file_path} has >2 dimensions, taking first slice for profile."
                    )
                    data = data[0, 0] if data.ndim == 4 else data[0]

            # Convert center to pixel space if needed
            if coordinate_system == "wcs":
                center_skycoord = SkyCoord(center_coord[0], center_coord[1], unit="deg")
                center_pixel = skycoord_to_pixel(center_skycoord, wcs)
            else:
                center_pixel = (center_coord[0], center_coord[1])

            # Calculate pixel scale
            pixel_scale = wcs.proj_plane_pixel_scales()[0].to("arcsec").value
            radius_pixels = radius_arcsec / pixel_scale

            # Create radial bins
            radii = np.linspace(0, radius_pixels, n_annuli + 1)
            radial_distances = []
            flux_values = []
            error_values = []

            yy, xx = np.mgrid[0 : data.shape[0], 0 : data.shape[1]]
            distances_from_center = np.sqrt(
                (xx - center_pixel[0]) ** 2 + (yy - center_pixel[1]) ** 2
            )

            for i in range(n_annuli):
                r_inner = radii[i]
                r_outer = radii[i + 1]

                # Find pixels in this annulus
                mask = (distances_from_center >= r_inner) & (
                    distances_from_center < r_outer
                )
                annulus_data = data[mask]

                if annulus_data.size > 0:
                    flux_mean = np.mean(annulus_data)
                    flux_std = np.std(annulus_data)
                    radial_dist = (r_inner + r_outer) / 2 * pixel_scale
                else:
                    flux_mean = np.nan
                    flux_std = 0.0
                    radial_dist = (r_inner + r_outer) / 2 * pixel_scale

                radial_distances.append(float(radial_dist))
                flux_values.append(float(flux_mean))
                error_values.append(
                    float(flux_std / np.sqrt(annulus_data.size))
                    if annulus_data.size > 0
                    else 0.0
                )

            # Get flux unit from header
            flux_unit = "Jy/beam"
            if "BUNIT" in hdul[0].header:
                flux_unit = str(hdul[0].header["BUNIT"])

            return {
                "distance": radial_distances,
                "flux": flux_values,
                "error": error_values,
                "coordinates": [
                    [center_coord[0], center_coord[1]]
                ],  # Single center point
                "units": {
                    "distance": "arcsec",
                    "flux": flux_unit,
                },
            }

    except Exception as e:
        LOG.error(f"Error extracting point profile from {fits_file_path}: {e}")
        raise


def fit_gaussian_profile(
    distance: np.ndarray,
    flux: np.ndarray,
    error: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Fit a 1D Gaussian profile to flux data.

    Args:
        distance: Distance values along profile
        flux: Flux values
        error: Optional error values for weighted fitting

    Returns:
        Dictionary with fit parameters and statistics
    """
    # Remove NaN values
    valid_mask = ~(np.isnan(distance) | np.isnan(flux))
    if error is not None:
        valid_mask = valid_mask & ~np.isnan(error)

    distance_clean = distance[valid_mask]
    flux_clean = flux[valid_mask]
    error_clean = error[valid_mask] if error is not None else None

    if len(distance_clean) < 3:
        raise ValueError("Not enough valid data points for fitting")

    # Initial guess
    max_idx = np.argmax(flux_clean)
    amplitude_guess = flux_clean[max_idx]
    center_guess = distance_clean[max_idx]

    # Estimate width from FWHM
    half_max = amplitude_guess / 2
    above_half_max = flux_clean >= half_max
    if np.any(above_half_max):
        fwhm_guess = np.max(distance_clean[above_half_max]) - np.min(
            distance_clean[above_half_max]
        )
        sigma_guess = fwhm_guess / (2 * np.sqrt(2 * np.log(2)))
    else:
        sigma_guess = (distance_clean[-1] - distance_clean[0]) / 4

    # Background estimate
    background_guess = np.median(flux_clean)

    # Gaussian function: A * exp(-0.5 * ((x - x0) / sigma)^2) + bg
    def gaussian_model(x, amplitude, center, sigma, background):
        return amplitude * np.exp(-0.5 * ((x - center) / sigma) ** 2) + background

    try:
        # Fit
        if error_clean is not None:
            popt, pcov = optimize.curve_fit(
                gaussian_model,
                distance_clean,
                flux_clean,
                p0=[amplitude_guess, center_guess, sigma_guess, background_guess],
                sigma=error_clean,
                bounds=(
                    [0, distance_clean[0], 0, -np.inf],
                    [np.inf, distance_clean[-1], np.inf, np.inf],
                ),
            )
        else:
            popt, pcov = optimize.curve_fit(
                gaussian_model,
                distance_clean,
                flux_clean,
                p0=[amplitude_guess, center_guess, sigma_guess, background_guess],
                bounds=(
                    [0, distance_clean[0], 0, -np.inf],
                    [np.inf, distance_clean[-1], np.inf, np.inf],
                ),
            )

        amplitude, center, sigma, background = popt

        # Calculate fitted flux
        fitted_flux = gaussian_model(distance_clean, *popt)

        # Calculate statistics
        residuals = flux_clean - fitted_flux
        chi_squared = np.sum(
            (residuals / (error_clean if error_clean is not None else 1.0)) ** 2
        )
        n_params = 4
        reduced_chi_squared = (
            chi_squared / (len(distance_clean) - n_params)
            if len(distance_clean) > n_params
            else np.nan
        )

        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((flux_clean - np.mean(flux_clean)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan

        fwhm = 2 * np.sqrt(2 * np.log(2)) * sigma

        return {
            "model": "gaussian",
            "parameters": {
                "amplitude": float(amplitude),
                "center": float(center),
                "sigma": float(sigma),
                "fwhm": float(fwhm),
                "background": float(background),
            },
            "statistics": {
                "chi_squared": float(chi_squared),
                "reduced_chi_squared": float(reduced_chi_squared),
                "r_squared": float(r_squared),
            },
            "fitted_flux": fitted_flux.tolist(),
            "parameter_errors": {
                "amplitude": float(np.sqrt(pcov[0, 0])),
                "center": float(np.sqrt(pcov[1, 1])),
                "sigma": float(np.sqrt(pcov[2, 2])),
                "background": float(np.sqrt(pcov[3, 3])),
            },
        }

    except Exception as e:
        LOG.error(f"Error fitting Gaussian profile: {e}")
        raise


def fit_moffat_profile(
    distance: np.ndarray,
    flux: np.ndarray,
    error: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Fit a 1D Moffat profile to flux data.

    Moffat profile: A * (1 + ((x - x0) / alpha)^2)^(-beta) + bg

    Args:
        distance: Distance values along profile
        flux: Flux values
        error: Optional error values for weighted fitting

    Returns:
        Dictionary with fit parameters and statistics
    """
    # Remove NaN values
    valid_mask = ~(np.isnan(distance) | np.isnan(flux))
    if error is not None:
        valid_mask = valid_mask & ~np.isnan(error)

    distance_clean = distance[valid_mask]
    flux_clean = flux[valid_mask]
    error_clean = error[valid_mask] if error is not None else None

    if len(distance_clean) < 4:
        raise ValueError("Not enough valid data points for Moffat fitting")

    # Initial guess
    max_idx = np.argmax(flux_clean)
    amplitude_guess = flux_clean[max_idx]
    center_guess = distance_clean[max_idx]

    # Estimate alpha (width parameter)
    half_max = amplitude_guess / 2
    above_half_max = flux_clean >= half_max
    if np.any(above_half_max):
        fwhm_guess = np.max(distance_clean[above_half_max]) - np.min(
            distance_clean[above_half_max]
        )
        alpha_guess = fwhm_guess / (
            2 * np.sqrt(2 ** (1 / 2.5) - 1)
        )  # Approximate for beta=2.5
    else:
        alpha_guess = (distance_clean[-1] - distance_clean[0]) / 4

    beta_guess = 2.5  # Typical value
    background_guess = np.median(flux_clean)

    # Moffat function: A * (1 + ((x - x0) / alpha)^2)^(-beta) + bg
    def moffat_model(x, amplitude, center, alpha, beta, background):
        return amplitude * (1 + ((x - center) / alpha) ** 2) ** (-beta) + background

    try:
        # Fit
        if error_clean is not None:
            popt, pcov = optimize.curve_fit(
                moffat_model,
                distance_clean,
                flux_clean,
                p0=[
                    amplitude_guess,
                    center_guess,
                    alpha_guess,
                    beta_guess,
                    background_guess,
                ],
                sigma=error_clean,
                bounds=(
                    [0, distance_clean[0], 0, 0.5, -np.inf],
                    [np.inf, distance_clean[-1], np.inf, 10, np.inf],
                ),
            )
        else:
            popt, pcov = optimize.curve_fit(
                moffat_model,
                distance_clean,
                flux_clean,
                p0=[
                    amplitude_guess,
                    center_guess,
                    alpha_guess,
                    beta_guess,
                    background_guess,
                ],
                bounds=(
                    [0, distance_clean[0], 0, 0.5, -np.inf],
                    [np.inf, distance_clean[-1], np.inf, 10, np.inf],
                ),
            )

        amplitude, center, alpha, beta, background = popt

        # Calculate fitted flux
        fitted_flux = moffat_model(distance_clean, *popt)

        # Calculate statistics
        residuals = flux_clean - fitted_flux
        chi_squared = np.sum(
            (residuals / (error_clean if error_clean is not None else 1.0)) ** 2
        )
        n_params = 5
        reduced_chi_squared = (
            chi_squared / (len(distance_clean) - n_params)
            if len(distance_clean) > n_params
            else np.nan
        )

        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((flux_clean - np.mean(flux_clean)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan

        # Calculate FWHM for Moffat
        fwhm = 2 * alpha * np.sqrt(2 ** (1 / beta) - 1)

        return {
            "model": "moffat",
            "parameters": {
                "amplitude": float(amplitude),
                "center": float(center),
                "alpha": float(alpha),
                "beta": float(beta),
                "fwhm": float(fwhm),
                "background": float(background),
            },
            "statistics": {
                "chi_squared": float(chi_squared),
                "reduced_chi_squared": float(reduced_chi_squared),
                "r_squared": float(r_squared),
            },
            "fitted_flux": fitted_flux.tolist(),
            "parameter_errors": {
                "amplitude": float(np.sqrt(pcov[0, 0])),
                "center": float(np.sqrt(pcov[1, 1])),
                "alpha": float(np.sqrt(pcov[2, 2])),
                "beta": float(np.sqrt(pcov[3, 3])),
                "background": float(np.sqrt(pcov[4, 4])),
            },
        }

    except Exception as e:
        LOG.error(f"Error fitting Moffat profile: {e}")
        raise
