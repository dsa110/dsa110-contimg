"""
Variability metrics for DSA-110 photometry analysis.

Adopted from VAST Tools for calculating variability metrics on source measurements.
These metrics complement χ²-based variability detection for ESE analysis.

Reference: archive/references/vast-tools/vasttools/utils.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional


def calculate_eta_metric(
    df: pd.DataFrame,
    flux_col: str = 'normalized_flux_jy',
    err_col: str = 'normalized_flux_err_jy'
) -> float:
    """
    Calculate η metric (weighted variance) - adopted from VAST Tools.
    
    The η metric is a weighted variance metric that accounts for measurement
    uncertainties. It provides a complementary measure to χ² for variability
    detection.
    
    See VAST Tools: vasttools/utils.py::pipeline_get_eta_metric()
    
    Formula:
        η = (N / (N-1)) * (
            (w * f²).mean() - ((w * f).mean()² / w.mean())
        )
    where w = 1 / σ² (weights), f = flux values
    
    Args:
        df: DataFrame containing flux measurements
        flux_col: Column name for flux values
        err_col: Column name for flux errors
    
    Returns:
        η metric value (float)
    
    Raises:
        ValueError: If insufficient data or missing columns
    """
    if len(df) <= 1:
        return 0.0
    
    if flux_col not in df.columns:
        raise ValueError(f"Flux column '{flux_col}' not found in DataFrame")
    
    if err_col not in df.columns:
        raise ValueError(f"Error column '{err_col}' not found in DataFrame")
    
    # Filter out invalid values
    valid_mask = (
        np.isfinite(df[flux_col]) &
        np.isfinite(df[err_col]) &
        (df[err_col] > 0)
    )
    
    if valid_mask.sum() < 2:
        return 0.0
    
    df_valid = df[valid_mask]
    
    # Calculate weights (1 / σ²)
    weights = 1.0 / (df_valid[err_col].values ** 2)
    fluxes = df_valid[flux_col].values
    
    n = len(df_valid)
    
    # Calculate η metric
    eta = (n / (n - 1)) * (
        (weights * fluxes ** 2).mean() - (
            (weights * fluxes).mean() ** 2 / weights.mean()
        )
    )
    
    return float(eta)


def calculate_vs_metric(
    flux_a: float,
    flux_b: float,
    flux_err_a: float,
    flux_err_b: float
) -> float:
    """
    Calculate Vs metric (two-epoch t-statistic) - adopted from VAST Tools.
    
    The Vs metric is the t-statistic that two flux measurements are variable.
    See Section 5 of Mooley et al. (2016) for details.
    DOI: 10.3847/0004-637X/818/2/105
    
    See VAST Tools: vasttools/utils.py::calculate_vs_metric()
    
    Formula:
        Vs = (flux_a - flux_b) / sqrt(σ_a² + σ_b²)
    
    Args:
        flux_a: Flux value at epoch A
        flux_b: Flux value at epoch B
        flux_err_a: Uncertainty of flux_a
        flux_err_b: Uncertainty of flux_b
    
    Returns:
        Vs metric value (float)
    
    Raises:
        ValueError: If errors are invalid (non-positive or NaN)
    """
    if not (np.isfinite(flux_err_a) and np.isfinite(flux_err_b)):
        raise ValueError("Flux errors must be finite")
    
    if flux_err_a <= 0 or flux_err_b <= 0:
        raise ValueError("Flux errors must be positive")
    
    return (flux_a - flux_b) / np.hypot(flux_err_a, flux_err_b)


def calculate_m_metric(flux_a: float, flux_b: float) -> float:
    """
    Calculate m metric (modulation index) - adopted from VAST Tools.
    
    The m metric is the modulation index between two fluxes, proportional
    to the fractional variability.
    See Section 5 of Mooley et al. (2016) for details.
    DOI: 10.3847/0004-637X/818/2/105
    
    See VAST Tools: vasttools/utils.py::calculate_m_metric()
    
    Formula:
        m = 2 * ((flux_a - flux_b) / (flux_a + flux_b))
    
    Args:
        flux_a: Flux value at epoch A
        flux_b: Flux value at epoch B
    
    Returns:
        m metric value (float)
    
    Raises:
        ValueError: If sum of fluxes is zero
    """
    flux_sum = flux_a + flux_b
    if flux_sum == 0:
        raise ValueError("Sum of fluxes cannot be zero")
    
    return 2 * ((flux_a - flux_b) / flux_sum)


def calculate_v_metric(fluxes: np.ndarray) -> float:
    """
    Calculate V metric (coefficient of variation).
    
    The V metric is the fractional variability: std / mean.
    This is already implemented in DSA-110's variability_stats table,
    but provided here for completeness.
    
    Args:
        fluxes: Array of flux values
    
    Returns:
        V metric value (float)
    """
    if len(fluxes) == 0:
        return 0.0
    
    valid_fluxes = fluxes[np.isfinite(fluxes)]
    if len(valid_fluxes) < 2:
        return 0.0
    
    mean_flux = np.mean(valid_fluxes)
    if mean_flux == 0:
        return 0.0
    
    return float(np.std(valid_fluxes) / mean_flux)

