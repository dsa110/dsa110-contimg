"""Enhanced visibility models for realistic synthetic data generation.

This module provides functions to generate visibilities with:
- Extended source models (Gaussian, disk)
- Thermal noise
- Calibration errors
"""

from typing import Optional, Tuple

import numpy as np


def calculate_thermal_noise_rms(
    integration_time_sec: float,
    channel_width_hz: float,
    system_temperature_k: float = 50.0,
    efficiency: float = 0.7,
    frequency_hz: float = 1.4e9,
) -> float:
    """Calculate RMS thermal noise for a single visibility.

    Uses the radiometer equation:
    sigma = T_sys / (eta * sqrt(2 * delta_nu * delta_t))

    Args:
        integration_time_sec: Integration time in seconds
        channel_width_hz: Channel width in Hz
        system_temperature_k: System temperature in Kelvin (default: 50K for DSA-110)
        efficiency: System efficiency (default: 0.7)
        frequency_hz: Observing frequency in Hz (default: 1.4 GHz for DSA-110)

    Returns:
        RMS noise in Jy
    """
    # Convert system temperature to Jy
    # The conversion factor is frequency-dependent: S = 2*k*T / A_eff
    # For DSA-110 interferometer, the conversion scales approximately as (freq/1.4GHz)²
    # At 1.4 GHz: ~2.0 Jy/K (calibrated value)
    # General: conversion_factor ≈ 2.0 * (1.4e9 / frequency_hz)²
    reference_freq_hz = 1.4e9
    conversion_factor = 2.0 * (reference_freq_hz / frequency_hz) ** 2
    t_sys_jy = system_temperature_k * conversion_factor

    # Radiometer equation
    # sigma = T_sys / (eta * sqrt(2 * delta_nu * delta_t))
    delta_nu = channel_width_hz
    delta_t = integration_time_sec

    rms_jy = t_sys_jy / (efficiency * np.sqrt(2.0 * delta_nu * delta_t))

    return rms_jy


def add_thermal_noise(
    visibilities: np.ndarray,
    integration_time_sec: float,
    channel_width_hz: float,
    system_temperature_k: float = 50.0,
    efficiency: float = 0.7,
    frequency_hz: float = 1.4e9,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Add realistic thermal noise to visibilities.

    Args:
        visibilities: Complex visibility array (shape: Nblts, Nspws, Nfreqs, Npols)
        integration_time_sec: Integration time per visibility
        channel_width_hz: Channel width in Hz
        system_temperature_k: System temperature in Kelvin
        efficiency: System efficiency
        frequency_hz: Observing frequency in Hz (default: 1.4 GHz for DSA-110)
        rng: Random number generator (for reproducibility)

    Returns:
        Visibilities with thermal noise added
    """
    if rng is None:
        rng = np.random.default_rng()

    # Calculate RMS noise per visibility
    rms_jy = calculate_thermal_noise_rms(
        integration_time_sec, channel_width_hz, system_temperature_k, efficiency, frequency_hz
    )

    # Generate complex Gaussian noise
    # Real and imaginary parts are independent, each with sigma = rms/sqrt(2)
    noise_real = rng.normal(0.0, rms_jy / np.sqrt(2.0), visibilities.shape)
    noise_imag = rng.normal(0.0, rms_jy / np.sqrt(2.0), visibilities.shape)
    noise = noise_real + 1j * noise_imag

    return visibilities + noise


def gaussian_source_visibility(
    u_lambda: np.ndarray,
    v_lambda: np.ndarray,
    flux_jy: float,
    major_axis_arcsec: float,
    minor_axis_arcsec: float,
    position_angle_deg: float = 0.0,
) -> np.ndarray:
    """Calculate visibility for a Gaussian extended source.

    For a Gaussian source, the visibility is:
    V(u,v) = S * exp(-2*π² * σ² * (u² + v²))

    where σ is the angular size in radians, and u, v are in wavelengths.
    This is the Fourier transform of a 2D Gaussian brightness distribution.

    Args:
        u_lambda: U coordinates in wavelengths (shape: Nblts)
        v_lambda: V coordinates in wavelengths (shape: Nblts)
        flux_jy: Total flux density in Jy
        major_axis_arcsec: Major axis FWHM in arcseconds
        minor_axis_arcsec: Minor axis FWHM in arcseconds
        position_angle_deg: Position angle in degrees (0 = North)

    Returns:
        Complex visibility array (shape: Nblts)
    """
    # Convert FWHM to sigma (FWHM = 2.355 * sigma)
    sigma_major_arcsec = major_axis_arcsec / 2.355
    sigma_minor_arcsec = minor_axis_arcsec / 2.355

    # Convert arcseconds to radians
    sigma_major_rad = np.deg2rad(sigma_major_arcsec / 3600.0)
    sigma_minor_rad = np.deg2rad(sigma_minor_arcsec / 3600.0)

    # Rotate u,v coordinates by position angle
    # Position angle: 0° = North, measured East of North
    pa_rad = np.deg2rad(position_angle_deg)
    cos_pa = np.cos(pa_rad)
    sin_pa = np.sin(pa_rad)

    u_rot = u_lambda * cos_pa - v_lambda * sin_pa
    v_rot = u_lambda * sin_pa + v_lambda * cos_pa

    # Calculate visibility for Gaussian source
    # Standard formula: V(u,v) = S * exp(-2*π² * σ² * (u² + v²))
    # where σ is the angular size in radians, u and v are in wavelengths
    # This is the Fourier transform of a 2D Gaussian brightness distribution

    exponent = -2.0 * np.pi**2 * (sigma_major_rad**2 * u_rot**2 + sigma_minor_rad**2 * v_rot**2)
    visibility = flux_jy * np.exp(exponent)

    return visibility.astype(np.complex64)


def disk_source_visibility(
    u_lambda: np.ndarray,
    v_lambda: np.ndarray,
    flux_jy: float,
    radius_arcsec: float,
) -> np.ndarray:
    """Calculate visibility for a uniform disk source.

    For a uniform disk, the visibility is:
    V(u,v) = 2 * S * J1(2 * pi * r * rho) / (2 * pi * r * rho)

    where r is the radius, rho = sqrt(u^2 + v^2), and J1 is Bessel function.

    Args:
        u_lambda: U coordinates in wavelengths (shape: Nblts)
        v_lambda: V coordinates in wavelengths (shape: Nblts)
        flux_jy: Total flux density in Jy
        radius_arcsec: Disk radius in arcseconds

    Returns:
        Complex visibility array (shape: Nblts)
    """
    try:
        from scipy.special import j1
    except ImportError:
        raise ImportError(
            "scipy is required for disk source model. Install with: conda install scipy"
        )

    # Convert radius to radians
    radius_rad = np.deg2rad(radius_arcsec / 3600.0)

    # Calculate rho = sqrt(u^2 + v^2) in wavelengths
    rho_lambda = np.sqrt(u_lambda**2 + v_lambda**2)

    # Calculate argument for Bessel function
    # Standard formula: V(ρ) = 2*S * J₁(2π*θ*ρ) / (2π*θ*ρ)
    # where θ is angular radius in radians, ρ is in wavelengths
    # This is the Fourier transform of a uniform disk brightness distribution
    arg = 2.0 * np.pi * radius_rad * rho_lambda

    # Avoid division by zero
    arg = np.where(arg < 1e-10, 1e-10, arg)

    # Visibility: 2 * S * J1(arg) / arg
    visibility = 2.0 * flux_jy * j1(arg) / arg

    # Handle point where arg -> 0 (should be flux_jy)
    visibility = np.where(arg < 1e-10, flux_jy, visibility)

    return visibility.astype(np.complex64)


def add_calibration_errors(
    visibilities: np.ndarray,
    nants: int,
    gain_std: float = 0.1,
    phase_std_deg: float = 10.0,
    bandpass_std: float = 0.05,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Add realistic calibration errors to visibilities.

    Applies antenna-based gain and phase errors, and frequency-dependent
    bandpass variations.

    Args:
        visibilities: Complex visibility array (shape: Nblts, Nspws, Nfreqs, Npols)
        nants: Number of antennas
        gain_std: Standard deviation of gain errors (default: 0.1 = 10%)
        phase_std_deg: Standard deviation of phase errors in degrees (default: 10 deg)
        bandpass_std: Standard deviation of bandpass variations (default: 0.05 = 5%)
        rng: Random number generator (for reproducibility)

    Returns:
        Tuple of (corrected_visibilities, antenna_gains, antenna_phases)
        where gains and phases are arrays of shape (nants, Nfreqs, Npols)
    """
    if rng is None:
        rng = np.random.default_rng()

    nblts, nspws, nfreqs, npols = visibilities.shape

    # Generate antenna-based gains and phases
    # Shape: (nants, nfreqs, npols)
    gain_errors = rng.normal(1.0, gain_std, (nants, nfreqs, npols))
    phase_errors_deg = rng.normal(0.0, phase_std_deg, (nants, nfreqs, npols))
    phase_errors_rad = np.deg2rad(phase_errors_deg)

    # Add frequency-dependent bandpass variations
    bandpass_errors = rng.normal(1.0, bandpass_std, (nants, nfreqs, npols))

    # Combine: total gain = gain_error * bandpass_error
    total_gains = gain_errors * bandpass_errors
    total_phases = phase_errors_rad

    # Convert to complex gains: g = |g| * exp(i * phi)
    complex_gains = total_gains * np.exp(1j * total_phases)

    # Apply to visibilities
    # For baseline (i, j): V_corr = V_true * g_i * conj(g_j)
    # We need to extract antenna indices from baseline-time array
    # This is simplified - in practice we'd need ant_1_array and ant_2_array

    # For now, return gains/phases and let caller apply them
    # This is because we need the antenna arrays to properly apply

    return visibilities, complex_gains, total_phases


def apply_calibration_errors_to_visibilities(
    visibilities: np.ndarray,
    ant_1_array: np.ndarray,
    ant_2_array: np.ndarray,
    complex_gains: np.ndarray,
) -> np.ndarray:
    """Apply calibration errors to visibilities given antenna arrays.

    Args:
        visibilities: Complex visibility array (shape: Nblts, Nspws, Nfreqs, Npols)
        ant_1_array: Antenna 1 indices (shape: Nblts)
        ant_2_array: Antenna 2 indices (shape: Nblts)
        complex_gains: Complex gains (shape: nants, Nfreqs, Npols)

    Returns:
        Visibilities with calibration errors applied
    """
    nblts, nspws, nfreqs, npols = visibilities.shape

    # Apply gains: V_corr = V_true * g_i * conj(g_j)
    corrected = visibilities.copy()

    for blt_idx in range(nblts):
        ant1 = int(ant_1_array[blt_idx])
        ant2 = int(ant_2_array[blt_idx])

        # Get gains for this baseline
        g1 = complex_gains[ant1, :, :]  # (Nfreqs, Npols)
        g2 = complex_gains[ant2, :, :]  # (Nfreqs, Npols)

        # Apply: V_corr = V * g1 * conj(g2)
        # For each spectral window
        for spw in range(nspws):
            # g1 and g2 are (Nfreqs, Npols), need to broadcast with (Nfreqs, Npols) visibility
            corrected[blt_idx, spw, :, :] = visibilities[blt_idx, spw, :, :] * g1 * np.conj(g2)

    return corrected
