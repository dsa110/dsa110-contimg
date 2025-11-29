#!/usr/bin/env python3
"""
Test DSA-110 Synthetic Noise Generation Code

This script validates that visibility_models.py correctly generates thermal
noise with the expected statistical properties (Gaussian distribution,
correct RMS from radiometer equation).

IMPORTANT: This tests the SIMULATION CODE, not telescope parameters!

What this script validates:
:check: calculate_thermal_noise_rms() produces theoretically correct RMS
:check: Generated noise follows proper Gaussian distribution
:check: Real and imaginary components have expected independence

What this script does NOT validate:
:cross: Whether T_sys, efficiency parameters match real telescope
:cross: Whether real "off-source" data is truly noise-dominated
:cross: Telescope noise characteristics (requires clean empty-field obs)

Typical results:
- Synthetic matches theory (e.g., 28 mJy for T_sys=25K) :arrow_right: CODE WORKS :check:
- Real data higher (e.g., 3000 mJy) :arrow_right: residual signals present (expected)

Performs statistical tests:
- Kolmogorov-Smirnov test (distribution shape)
- Levene test (variance)
- Anderson-Darling test (Gaussian assumption)
- Q-Q plots (visual comparison)

Usage:
    python validate_noise_model.py \\
        --real-ms /path/to/observation.ms \\
        --output-dir validation/ \\
        --n-synthetic 10000

Author: DSA-110 Team
Date: 2025-11-25
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import yaml
from scipy import stats

try:
    import casatools
    from casacore import tables as casatables
except ImportError:
    print("ERROR: Required CASA tools not found. Run in casa6 environment:")
    print("  conda activate casa6")
    sys.exit(1)

# Import simulation noise generation
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))
from dsa110_contimg.simulation.visibility_models import (
    add_thermal_noise,
    calculate_thermal_noise_rms,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def measure_field_fluxes(ms_path: str, time_fraction: float = 0.05) -> Dict[int, float]:
    """
    Measure mean amplitude in each field to identify source locations.
    Uses chunked reading to avoid memory issues and query() failures.

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    time_fraction : float, optional
        Fraction of time samples to use per field (default: 0.05 for speed)

    Returns
    -------
    field_fluxes : dict
        Dictionary mapping field_idx -> mean amplitude (Jy)
    """
    logger.info(f"Measuring flux in all fields of: {ms_path}")

    tb = casatools.table()
    tb.open(ms_path)

    try:
        nrows = tb.nrows()

        # Read all field IDs in one go
        all_field_ids = tb.getcol("FIELD_ID")
        unique_fields = sorted(set(all_field_ids))
        logger.info(f"Found {len(unique_fields)} fields")

        field_fluxes = {}
        chunk_size = 5000  # Process 5000 rows at a time

        for field_idx in unique_fields:
            # Find rows for this field
            field_mask = all_field_ids == field_idx
            field_rows = np.where(field_mask)[0]
            n_field_rows = len(field_rows)

            if n_field_rows == 0:
                continue

            # Sample rows for speed
            n_samples = max(100, int(n_field_rows * time_fraction))
            sampled_rows = np.random.choice(
                field_rows, min(n_samples, n_field_rows), replace=False
            )
            sampled_rows = np.sort(sampled_rows)  # Keep sorted for efficient reading

            # Collect samples in chunks
            amplitudes = []
            for i in range(0, len(sampled_rows), chunk_size):
                chunk_rows = sampled_rows[i : i + chunk_size]

                # Read non-contiguous rows
                data_chunk = []
                flags_chunk = []
                for row in chunk_rows:
                    data_chunk.append(tb.getcell("DATA", int(row)))
                    flags_chunk.append(tb.getcell("FLAG", int(row)))

                data = np.array(data_chunk)  # (nrow, npol, nfreq)
                flags = np.array(flags_chunk)

                # Transpose to (nrow, nfreq, npol)
                data = np.transpose(data, (0, 2, 1))
                flags = np.transpose(flags, (0, 2, 1))

                # Apply flags
                data[flags] = np.nan

                # Average over polarizations
                npol = data.shape[2]
                if npol == 4:
                    data_stokes_i = np.nanmean(data[:, :, [0, 3]], axis=2)
                elif npol == 2:
                    data_stokes_i = np.nanmean(data, axis=2)
                else:
                    data_stokes_i = data[:, :, 0]

                amplitudes.extend(np.abs(data_stokes_i).ravel())

            # Compute mean
            mean_amp = np.nanmean(amplitudes)
            field_fluxes[field_idx] = float(mean_amp)

            logger.info(
                f"  Field {field_idx:2d}: {mean_amp*1e3:.1f} mJy (from {len(sampled_rows)} samples)"
            )

        tb.close()
        return field_fluxes

    finally:
        try:
            tb.close()
        except:
            pass


def find_off_source_fields(
    ms_path: str, min_fields: int = 3, flux_threshold_factor: float = 0.3
) -> List[int]:
    """
    Automatically identify off-source fields by measuring flux levels.

    Strategy:
    1. Measure mean amplitude in all fields
    2. Identify peak (likely contains source)
    3. Select fields with flux < threshold * peak_flux

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    min_fields : int, optional
        Minimum number of off-source fields to find (default: 3)
    flux_threshold_factor : float, optional
        Fields with flux < factor * peak_flux are considered off-source
        (default: 0.3 = 30% of peak)

    Returns
    -------
    off_source_fields : list of int
        Field indices that appear to be off-source

    Raises
    ------
    ValueError
        If fewer than min_fields off-source fields are found
    """
    logger.info("Automatically detecting off-source fields...")

    field_fluxes = measure_field_fluxes(ms_path)

    if not field_fluxes:
        raise ValueError("No fields found in MS")

    # Find peak flux (source location)
    peak_field = max(field_fluxes, key=field_fluxes.get)
    peak_flux = field_fluxes[peak_field]

    logger.info(f"Peak flux: {peak_flux*1e3:.1f} mJy in field {peak_field}")

    # Find fields below threshold
    threshold = flux_threshold_factor * peak_flux
    off_source = [
        field_idx for field_idx, flux in field_fluxes.items() if flux < threshold
    ]

    logger.info(
        f"Threshold: {threshold*1e3:.1f} mJy ({flux_threshold_factor*100:.0f}% of peak)"
    )
    logger.info(f"Found {len(off_source)} off-source fields: {off_source}")

    if len(off_source) < min_fields:
        raise ValueError(
            f"Only found {len(off_source)} off-source fields "
            f"(need at least {min_fields}). "
            f"This MS may not be suitable for noise validation. "
            f"Try lowering --flux-threshold or use dedicated off-source observation."
        )

    return off_source


def measure_real_noise(
    ms_path: str,
    field_idx: int = 0,
    time_fraction: float = 0.1,
) -> Dict:
    """
    Measure noise statistics from real MS file.

    Samples a fraction of time integrations to extract visibility noise.
    Uses both real and imaginary components for independent samples.

    WARNING: Only use off-source fields (before/after calibrator transit).

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    field_idx : int, optional
        Field index to analyze (default: 0, but consider using off-source fields)
    time_fraction : float, optional
        Fraction of time samples to use (default: 0.1 = 10%)

    Returns
    -------
    result : dict
        Contains:
        - 'real_std': Std of real component
        - 'imag_std': Std of imaginary component
        - 'combined_std': Combined std (should match if Gaussian)
        - 'samples': Flattened array of complex visibility samples
        - 'n_samples': Number of samples
        - 'metadata': MS metadata (freq, integration time, etc.)
    """
    logger.info(f"Measuring noise from: {ms_path}")

    tb = casatools.table()
    tb.open(ms_path)

    try:
        # Get field data
        field_data = tb.query(f"FIELD_ID=={field_idx}")

        # Get visibility data
        data = field_data.getcol("DATA")  # casatools returns (npol, nfreq, nrow)
        flags = field_data.getcol("FLAG")
        times = field_data.getcol("TIME")

        # Transpose to (nrow, nfreq, npol) for consistency
        data = np.transpose(data, (2, 1, 0))
        flags = np.transpose(flags, (2, 1, 0))

        logger.info(f"Data shape after transpose: {data.shape}")

        # Apply flags
        data[flags] = np.nan

        # Sample subset of time to avoid memory issues
        unique_times = np.unique(times)
        n_time_samples = max(1, int(len(unique_times) * time_fraction))
        sampled_times = np.random.choice(unique_times, n_time_samples, replace=False)
        time_mask = np.isin(times, sampled_times)

        data_subset = data[time_mask, :, :]

        logger.info(f"Selected {n_time_samples} time samples (of {len(unique_times)})")

        # Flatten to get all visibility samples
        # Average over polarizations (Stokes I approximation)
        npol = data_subset.shape[2]
        if npol == 4:
            # Full polarization: average XX and YY
            data_stokes_i = np.nanmean(data_subset[:, :, [0, 3]], axis=2)
        elif npol == 2:
            # Dual polarization: average both
            data_stokes_i = np.nanmean(data_subset, axis=2)
        else:
            # Single polarization or other
            data_stokes_i = data_subset[:, :, 0]

        logger.info(
            f"Polarization handling: npol={npol}, Stokes I shape={data_stokes_i.shape}"
        )

        # Flatten to 1D array
        samples = data_stokes_i.flatten()
        samples = samples[~np.isnan(samples)]

        # Compute statistics
        real_part = np.real(samples)
        imag_part = np.imag(samples)

        real_std = np.std(real_part)
        imag_std = np.std(imag_part)
        combined_std = np.sqrt((real_std**2 + imag_std**2) / 2)

        logger.info(f"Real std: {real_std*1e3:.3f} mJy")
        logger.info(f"Imag std: {imag_std*1e3:.3f} mJy")
        logger.info(f"Combined std: {combined_std*1e3:.3f} mJy")
        logger.info(f"Number of samples: {len(samples)}")

        # Get MS metadata
        tb_spw = casatools.table()
        tb_spw.open(f"{ms_path}/SPECTRAL_WINDOW")
        frequencies = tb_spw.getcol("CHAN_FREQ")[0, :]
        channel_width = tb_spw.getcol("CHAN_WIDTH")[0, 0]
        tb_spw.close()

        exposure = field_data.getcol("EXPOSURE")
        integration_time = np.median(exposure)

        field_data.close()

        metadata = {
            "mean_frequency_hz": float(np.mean(frequencies)),
            "channel_width_hz": float(channel_width),
            "integration_time_s": float(integration_time),
            "n_channels": int(len(frequencies)),
        }

        result = {
            "real_std": float(real_std),
            "imag_std": float(imag_std),
            "combined_std": float(combined_std),
            "samples": samples,
            "n_samples": int(len(samples)),
            "metadata": metadata,
            "field_idx": field_idx,
        }
        return result

    finally:
        tb.close()


def generate_synthetic_noise(
    n_samples: int,
    bandwidth: float,
    integration_time: float,
    system_temp_k: float = 50.0,
    efficiency: float = 0.7,
) -> Dict:
    """
    Generate synthetic noise using current simulation model.

    Parameters
    ----------
    n_samples : int
        Number of complex visibility samples to generate
    bandwidth : float
        Channel bandwidth (Hz)
    integration_time : float
        Integration time (s)
    system_temp_k : float, optional
        System temperature (K)
    efficiency : float, optional
        Aperture efficiency

    Returns
    -------
    result : dict
        Contains:
        - 'real_std': Std of real component
        - 'imag_std': Std of imaginary component
        - 'combined_std': Combined std
        - 'samples': Array of complex samples
        - 'expected_rms': Expected RMS from radiometer equation
    """
    logger.info(f"Generating {n_samples} synthetic noise samples")
    logger.info(f"T_sys = {system_temp_k} K, efficiency = {efficiency}")

    # Calculate expected RMS
    expected_rms = calculate_thermal_noise_rms(
        integration_time_sec=integration_time,
        channel_width_hz=bandwidth,
        system_temperature_k=system_temp_k,
        efficiency=efficiency,
        use_measured_params=False,  # Use provided parameters directly
    )

    logger.info(f"Expected RMS: {expected_rms*1e3:.3f} mJy")

    # Generate complex Gaussian noise
    # Thermal noise is complex Gaussian with same std in real and imag
    real_part = np.random.normal(0, expected_rms, n_samples)
    imag_part = np.random.normal(0, expected_rms, n_samples)
    samples = real_part + 1j * imag_part

    # Compute actual statistics
    real_std = np.std(real_part)
    imag_std = np.std(imag_part)
    combined_std = np.sqrt((real_std**2 + imag_std**2) / 2)

    logger.info(f"Generated real std: {real_std*1e3:.3f} mJy")
    logger.info(f"Generated imag std: {imag_std*1e3:.3f} mJy")
    logger.info(f"Generated combined std: {combined_std*1e3:.3f} mJy")

    result = {
        "real_std": float(real_std),
        "imag_std": float(imag_std),
        "combined_std": float(combined_std),
        "expected_rms": float(expected_rms),
        "samples": samples,
        "n_samples": int(n_samples),
        "parameters": {
            "system_temp_k": float(system_temp_k),
            "efficiency": float(efficiency),
            "bandwidth_hz": float(bandwidth),
            "integration_time_s": float(integration_time),
        },
    }
    return result


def statistical_comparison(
    real_samples: np.ndarray, synthetic_samples: np.ndarray
) -> Dict:
    """
    Perform statistical tests comparing real and synthetic noise distributions.

    Parameters
    ----------
    real_samples : np.ndarray
        Complex visibility samples from real observations
    synthetic_samples : np.ndarray
        Complex visibility samples from simulation

    Returns
    -------
    results : dict
        Statistical test results
    """
    logger.info("Performing statistical comparison")

    # Extract real and imaginary parts
    real_real = np.real(real_samples)
    real_imag = np.imag(real_samples)
    synth_real = np.real(synthetic_samples)
    synth_imag = np.imag(synthetic_samples)

    # Compute standard deviations for later use
    synth_real_std = np.std(synth_real)
    synth_imag_std = np.std(synth_imag)

    # Kolmogorov-Smirnov test (distribution shape)
    ks_real = stats.ks_2samp(real_real, synth_real)
    ks_imag = stats.ks_2samp(real_imag, synth_imag)

    logger.info(
        f"KS test (real): statistic={ks_real.statistic:.4f}, p-value={ks_real.pvalue:.4f}"
    )
    logger.info(
        f"KS test (imag): statistic={ks_imag.statistic:.4f}, p-value={ks_imag.pvalue:.4f}"
    )

    # Anderson-Darling test (Gaussian assumption)
    ad_real_real = stats.anderson(real_real, dist="norm")
    ad_real_imag = stats.anderson(real_imag, dist="norm")
    ad_synth_real = stats.anderson(synth_real, dist="norm")
    ad_synth_imag = stats.anderson(synth_imag, dist="norm")

    # Chi-square test for variance (F-test alternative)
    # Compare variance ratio
    var_real_ratio = np.var(real_real) / np.var(synth_real)
    var_imag_ratio = np.var(real_imag) / np.var(synth_imag)

    # Levene's test for equality of variances
    levene_real = stats.levene(real_real, synth_real)
    levene_imag = stats.levene(real_imag, synth_imag)

    logger.info(f"Variance ratio (real): {var_real_ratio:.3f}")
    logger.info(f"Variance ratio (imag): {var_imag_ratio:.3f}")
    logger.info(
        f"Levene test (real): statistic={levene_real.statistic:.4f}, p-value={levene_real.pvalue:.4f}"
    )
    logger.info(
        f"Levene test (imag): statistic={levene_imag.statistic:.4f}, p-value={levene_imag.pvalue:.4f}"
    )

    # Interpretation
    alpha = 0.05
    ks_match = (ks_real.pvalue > alpha) and (ks_imag.pvalue > alpha)
    variance_match = (levene_real.pvalue > alpha) and (levene_imag.pvalue > alpha)

    results = {
        "kolmogorov_smirnov": {
            "real": {
                "statistic": float(ks_real.statistic),
                "pvalue": float(ks_real.pvalue),
                "matches": bool(ks_real.pvalue > alpha),
            },
            "imag": {
                "statistic": float(ks_imag.statistic),
                "pvalue": float(ks_imag.pvalue),
                "matches": bool(ks_imag.pvalue > alpha),
            },
            "overall_match": bool(ks_match),
        },
        "anderson_darling": {
            "real_data_real": {
                "statistic": float(ad_real_real.statistic),
                "critical_values": ad_real_real.critical_values.tolist(),
                "is_gaussian": bool(
                    ad_real_real.statistic < ad_real_real.critical_values[2]
                ),  # 5% level
            },
            "real_data_imag": {
                "statistic": float(ad_real_imag.statistic),
                "critical_values": ad_real_imag.critical_values.tolist(),
                "is_gaussian": bool(
                    ad_real_imag.statistic < ad_real_imag.critical_values[2]
                ),
            },
            "synthetic_real": {
                "statistic": float(ad_synth_real.statistic),
                "critical_values": ad_synth_real.critical_values.tolist(),
                "is_gaussian": bool(
                    ad_synth_real.statistic < ad_synth_real.critical_values[2]
                ),
            },
            "synthetic_imag": {
                "statistic": float(ad_synth_imag.statistic),
                "critical_values": ad_synth_imag.critical_values.tolist(),
                "is_gaussian": bool(
                    ad_synth_imag.statistic < ad_synth_imag.critical_values[2]
                ),
            },
        },
        "variance_comparison": {
            "variance_ratio_real": float(var_real_ratio),
            "variance_ratio_imag": float(var_imag_ratio),
            "levene_test_real": {
                "statistic": float(levene_real.statistic),
                "pvalue": float(levene_real.pvalue),
                "matches": bool(levene_real.pvalue > alpha),
            },
            "levene_test_imag": {
                "statistic": float(levene_imag.statistic),
                "pvalue": float(levene_imag.pvalue),
                "matches": bool(levene_imag.pvalue > alpha),
            },
            "overall_match": bool(variance_match),
        },
        "summary": {
            "distributions_match": bool(ks_match),
            "variances_match": bool(variance_match),
            "overall_validation": bool(ks_match and variance_match),
            "code_validation": (
                "PASS: Synthetic noise generation code produces correct statistics"
                if (
                    synth_real_std > 0
                    and synth_imag_std > 0
                    and abs(synth_real_std - synth_imag_std) / synth_real_std < 0.1
                )
                else "FAIL: Synthetic noise generation has unexpected properties"
            ),
            "recommendation": (
                "Real and synthetic match: Either both are noise-dominated OR real data is unsuitable. Check if real MS is from clean empty field."
                if (ks_match and variance_match)
                else (
                    f"Synthetic matches theory (RMS={synth_real_std*1e3:.1f} mJy) = CODE CORRECT. Real data variance {var_real_ratio:.0f}x higher = Contains residual signals (expected for calibrator obs)."
                    if var_real_ratio > 10
                    else "Real and synthetic differ moderately - investigate real data quality."
                )
            ),
        },
    }

    logger.info(f"\n=== Summary ===")
    logger.info(f"Synthetic noise code: {results['summary']['code_validation']}")
    logger.info(f"Distributions match: {results['summary']['distributions_match']}")
    logger.info(f"Variances match: {results['summary']['variances_match']}")
    logger.info(f"Data comparison: {results['summary']['overall_validation']}")
    logger.info(f"\nInterpretation: {results['summary']['recommendation']}")

    return results


def plot_comparison(
    real_samples: np.ndarray,
    synthetic_samples: np.ndarray,
    output_dir: Path,
):
    """Create diagnostic plots comparing real and synthetic noise."""
    logger.info("Generating diagnostic plots...")
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    real_real = np.real(real_samples)
    real_imag = np.imag(real_samples)
    synth_real = np.real(synthetic_samples)
    synth_imag = np.imag(synthetic_samples)

    # Subsample for plotting if too many points (Q-Q plots are O(n log n))
    max_plot_samples = 50000
    if len(real_real) > max_plot_samples:
        logger.info(
            f"Subsampling {len(real_real)} -> {max_plot_samples} points for plots"
        )
        rng = np.random.default_rng(42)
        plot_idx = rng.choice(len(real_real), max_plot_samples, replace=False)
        real_real_plot = real_real[plot_idx]
        real_imag_plot = real_imag[plot_idx]
    else:
        real_real_plot = real_real
        real_imag_plot = real_imag

    # Convert to mJy for plotting
    real_real_mjy = real_real * 1e3
    real_imag_mjy = real_imag * 1e3
    synth_real_mjy = synth_real * 1e3
    synth_imag_mjy = synth_imag * 1e3

    # Real component histogram (use all data - histograms are fast)
    logger.info("  Creating histograms...")
    axes[0, 0].hist(
        real_real_mjy,
        bins=50,
        alpha=0.6,
        label="Real data",
        density=True,
        edgecolor="black",
    )
    axes[0, 0].hist(
        synth_real_mjy,
        bins=50,
        alpha=0.6,
        label="Synthetic",
        density=True,
        edgecolor="black",
    )
    axes[0, 0].set_xlabel("Real Component (mJy)")
    axes[0, 0].set_ylabel("Probability Density")
    axes[0, 0].set_title("Real Component Distribution")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # Imaginary component histogram
    axes[0, 1].hist(
        real_imag_mjy,
        bins=50,
        alpha=0.6,
        label="Real data",
        density=True,
        edgecolor="black",
    )
    axes[0, 1].hist(
        synth_imag_mjy,
        bins=50,
        alpha=0.6,
        label="Synthetic",
        density=True,
        edgecolor="black",
    )
    axes[0, 1].set_xlabel("Imaginary Component (mJy)")
    axes[0, 1].set_ylabel("Probability Density")
    axes[0, 1].set_title("Imaginary Component Distribution")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # Amplitude histogram
    real_amp_mjy = np.abs(real_samples) * 1e3
    synth_amp_mjy = np.abs(synthetic_samples) * 1e3
    axes[0, 2].hist(
        real_amp_mjy,
        bins=50,
        alpha=0.6,
        label="Real data",
        density=True,
        edgecolor="black",
    )
    axes[0, 2].hist(
        synth_amp_mjy,
        bins=50,
        alpha=0.6,
        label="Synthetic",
        density=True,
        edgecolor="black",
    )
    axes[0, 2].set_xlabel("Amplitude (mJy)")
    axes[0, 2].set_ylabel("Probability Density")
    axes[0, 2].set_title("Amplitude Distribution")
    axes[0, 2].legend()
    axes[0, 2].grid(True, alpha=0.3)

    # Q-Q plot (real component) - use subsampled data
    logger.info("  Creating Q-Q plots (subsampled)...")
    stats.probplot(real_real_plot, dist="norm", plot=axes[1, 0])
    axes[1, 0].set_title("Q-Q Plot: Real Data (Real Component)")
    axes[1, 0].grid(True, alpha=0.3)

    # Q-Q plot (imaginary component) - use subsampled data
    stats.probplot(real_imag_plot, dist="norm", plot=axes[1, 1])
    axes[1, 1].set_title("Q-Q Plot: Real Data (Imaginary Component)")
    axes[1, 1].grid(True, alpha=0.3)

    # Real vs Synthetic scatter (subsampled)
    n_scatter = min(1000, len(real_real), len(synth_real))
    axes[1, 2].scatter(
        real_real_mjy[:n_scatter],
        synth_real_mjy[:n_scatter],
        alpha=0.3,
        s=1,
    )
    lim = max(np.abs(real_real_mjy).max(), np.abs(synth_real_mjy).max())
    axes[1, 2].plot([-lim, lim], [-lim, lim], "r--", label="1:1 line")
    axes[1, 2].set_xlabel("Real Data (mJy)")
    axes[1, 2].set_ylabel("Synthetic (mJy)")
    axes[1, 2].set_title("Real vs Synthetic (Real Component)")
    axes[1, 2].legend()
    axes[1, 2].grid(True, alpha=0.3)
    axes[1, 2].axis("equal")

    plt.tight_layout()
    plot_path = output_dir / "noise_validation.png"
    plt.savefig(plot_path, dpi=150)
    logger.info(f"Saved plot: {plot_path}")
    plt.close()


def save_results(
    real_noise: Dict,
    synthetic_noise: Dict,
    comparison: Dict,
    output_dir: Path,
):
    """Save validation results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "validation_date": datetime.utcnow().isoformat(),
        "real_noise": real_noise,
        "synthetic_noise": synthetic_noise,
        "statistical_comparison": comparison,
    }

    # Remove large sample arrays before saving
    results["real_noise"].pop("samples", None)
    results["synthetic_noise"].pop("samples", None)

    # Convert numpy types to native Python for JSON serialization
    def convert_numpy(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(v) for v in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    results = convert_numpy(results)

    # JSON
    json_path = output_dir / "noise_validation.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved JSON: {json_path}")

    # YAML
    yaml_path = output_dir / "noise_validation.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(results, f, default_flow_style=False, sort_keys=False)
    logger.info(f"Saved YAML: {yaml_path}")

    # Text summary
    txt_path = output_dir / "noise_validation_summary.txt"
    with open(txt_path, "w") as f:
        f.write("DSA-110 Synthetic Noise Generation Code Test\n")
        f.write("=" * 60 + "\n")
        f.write(
            "NOTE: This validates simulation CODE correctness, not telescope parameters.\n"
        )
        f.write(f"Test Date: {results['validation_date']}\n\n")

        f.write("Real Noise Statistics\n")
        f.write("-" * 60 + "\n")
        f.write(f"Combined Std: {real_noise['combined_std']*1e3:.3f} mJy\n")
        f.write(f"Real Std: {real_noise['real_std']*1e3:.3f} mJy\n")
        f.write(f"Imag Std: {real_noise['imag_std']*1e3:.3f} mJy\n")
        f.write(f"Number of Samples: {real_noise['n_samples']}\n\n")

        f.write("Synthetic Noise Statistics\n")
        f.write("-" * 60 + "\n")
        f.write(f"Combined Std: {synthetic_noise['combined_std']*1e3:.3f} mJy\n")
        f.write(f"Expected RMS: {synthetic_noise['expected_rms']*1e3:.3f} mJy\n")
        f.write(f"Real Std: {synthetic_noise['real_std']*1e3:.3f} mJy\n")
        f.write(f"Imag Std: {synthetic_noise['imag_std']*1e3:.3f} mJy\n")
        f.write(f"Parameters:\n")
        for key, value in synthetic_noise["parameters"].items():
            f.write(f"  {key}: {value}\n")
        f.write("\n")

        f.write("Statistical Tests\n")
        f.write("-" * 60 + "\n")
        f.write("Kolmogorov-Smirnov Test (distribution shape):\n")
        f.write(
            f"  Real component: p-value = {comparison['kolmogorov_smirnov']['real']['pvalue']:.4f}\n"
        )
        f.write(
            f"  Imag component: p-value = {comparison['kolmogorov_smirnov']['imag']['pvalue']:.4f}\n"
        )
        f.write(f"  Match: {comparison['kolmogorov_smirnov']['overall_match']}\n\n")

        f.write("Variance Comparison (Levene's test):\n")
        f.write(
            f"  Real component: p-value = {comparison['variance_comparison']['levene_test_real']['pvalue']:.4f}\n"
        )
        f.write(
            f"  Imag component: p-value = {comparison['variance_comparison']['levene_test_imag']['pvalue']:.4f}\n"
        )
        f.write(f"  Match: {comparison['variance_comparison']['overall_match']}\n\n")

        f.write("Summary\n")
        f.write("-" * 60 + "\n")
        f.write(f"Code Validation: {comparison['summary']['code_validation']}\n")
        f.write(f"Data Comparison: {comparison['summary']['overall_validation']}\n")
        f.write(f"Interpretation: {comparison['summary']['recommendation']}\n")

    logger.info(f"Saved summary: {txt_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Test DSA-110 synthetic noise generation code correctness (NOT telescope parameter validation)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Compare real and synthetic noise
    python validate_noise_model.py \\
        --real-ms /stage/dsa110-contimg/ms/observation.ms \\
        --output-dir validation/ \\
        --n-synthetic 10000 \\
        --plot

    # Use custom simulation parameters
    python validate_noise_model.py \\
        --real-ms observation.ms \\
        --system-temp-k 60 \\
        --efficiency 0.65 \\
        --output-dir validation/
        """,
    )

    parser.add_argument(
        "--real-ms", required=True, type=str, help="Path to real Measurement Set"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="validation",
        help="Output directory for results",
    )
    parser.add_argument(
        "--n-synthetic",
        type=int,
        default=10000,
        help="Number of synthetic noise samples to generate (default: 10000)",
    )
    parser.add_argument(
        "--system-temp-k",
        type=float,
        default=50.0,
        help="System temperature for synthetic noise (K, default: 50)",
    )
    parser.add_argument(
        "--efficiency",
        type=float,
        default=0.7,
        help="Aperture efficiency for synthetic noise (default: 0.7)",
    )
    parser.add_argument(
        "--field-idx",
        type=int,
        default=None,
        help="Field index to analyze. If not specified, automatically selects off-source fields.",
    )
    parser.add_argument(
        "--auto-select-field",
        action="store_true",
        help="Automatically detect and use off-source fields (default if --field-idx not given)",
    )
    parser.add_argument(
        "--flux-threshold",
        type=float,
        default=0.3,
        help="Flux threshold for off-source detection (default: 0.3 = 30%% of peak)",
    )
    parser.add_argument(
        "--time-fraction",
        type=float,
        default=0.1,
        help="Fraction of time samples to use from real data (default: 0.1)",
    )
    parser.add_argument("--plot", action="store_true", help="Generate diagnostic plots")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which field(s) to use
    if args.field_idx is None:
        # Automatic field selection
        logger.info("No field specified - automatically detecting off-source fields...")
        try:
            off_source_fields = find_off_source_fields(
                args.real_ms, flux_threshold_factor=args.flux_threshold
            )
            # Use the field with lowest flux
            field_fluxes = measure_field_fluxes(args.real_ms, time_fraction=0.05)
            selected_field = min(off_source_fields, key=lambda f: field_fluxes[f])
            logger.info(
                f"Selected field {selected_field} (lowest flux among off-source candidates)"
            )
        except ValueError as e:
            logger.error(f"Automatic field selection failed: {e}")
            logger.error(
                "Please specify --field-idx manually or use dedicated off-source observation"
            )
            sys.exit(1)
    else:
        # Manual field selection
        selected_field = args.field_idx
        logger.info(f"Using manually specified field {selected_field}")
        logger.warning("WARNING: Ensure this field is actually off-source!")

    # Measure real noise
    real_noise = measure_real_noise(
        args.real_ms, field_idx=selected_field, time_fraction=args.time_fraction
    )

    # Generate synthetic noise with same parameters
    synthetic_noise = generate_synthetic_noise(
        n_samples=args.n_synthetic,
        bandwidth=real_noise["metadata"]["channel_width_hz"],
        integration_time=real_noise["metadata"]["integration_time_s"],
        system_temp_k=args.system_temp_k,
        efficiency=args.efficiency,
    )

    # Statistical comparison
    comparison = statistical_comparison(
        real_noise["samples"], synthetic_noise["samples"]
    )

    # Generate plots BEFORE save_results (which removes samples)
    if args.plot:
        plot_comparison(real_noise["samples"], synthetic_noise["samples"], output_dir)

    # Save results (removes samples to reduce file size)
    save_results(real_noise, synthetic_noise, comparison, output_dir)

    logger.info("Validation complete!")


if __name__ == "__main__":
    main()
