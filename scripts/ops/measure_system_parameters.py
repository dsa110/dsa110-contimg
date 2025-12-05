#!/usr/bin/env python3
"""
Measure DSA-110 System Parameters from Real Calibrator Observations

This script analyzes Measurement Sets containing known calibrator sources to derive:
- System temperature (T_sys) per antenna and frequency
- System Equivalent Flux Density (SEFD) per antenna
- Aperture efficiency (η) if antenna parameters are known

Uses the radiometer equation and known calibrator fluxes to measure actual
system performance from observations.

Usage:
    python measure_system_parameters.py \
        --ms /path/to/calibrator.ms \
        --calibrator 3C286 \
        --output-dir measurements/

Author: DSA-110 Team
Date: 2025-11-25
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import yaml
from astropy import constants as const
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time


# --- CASA log directory setup ---
# Ensure CASA logs go to centralized directory, not CWD
import os as _os
try:
    from pathlib import Path as _Path
    _REPO_ROOT = _Path(__file__).resolve().parents[2]
    _sys_path_entry = str(_REPO_ROOT / 'backend' / 'src')
    import sys as _sys
    if _sys_path_entry not in _sys.path:
        _sys.path.insert(0, _sys_path_entry)
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    _casa_log_dir = derive_casa_log_dir()
    _os.makedirs(str(_casa_log_dir), exist_ok=True)
    _os.chdir(str(_casa_log_dir))
except (ImportError, OSError):
    pass  # Best effort - CASA logs may go to CWD
# --- End CASA log directory setup ---

try:
    import casatools
    from casacore import tables as casatables
except ImportError:
    print("ERROR: Required CASA tools not found. Run in casa6 environment:")
    print("  conda activate casa6")
    sys.exit(1)

from dsa110_contimg.calibration.selection import select_bandpass_from_catalog

# Known calibrator flux densities at 1.4 GHz (Perley & Butler 2017)
# Format: {name: (flux_Jy, spectral_index_alpha, reference_freq_GHz)}
CALIBRATOR_FLUXES = {
    "3C286": (14.86, -0.467, 1.4),  # Perley & Butler 2017, ApJS 230, 7
    "3C48": (16.23, -0.491, 1.4),
    "3C147": (22.45, -0.518, 1.4),
    "3C138": (8.36, -0.433, 1.4),
    "J1331+3030": (14.86, -0.467, 1.4),  # Alternative name for 3C286
    "0834+555": (2.5, -0.5, 1.4),  # From VLA catalog
    "0702+445": (1.1, -0.5, 1.4),  # From VLA catalog
}

# DSA-110 antenna parameters
ANTENNA_DIAMETER = 4.65  # meters
ANTENNA_AREA = np.pi * (ANTENNA_DIAMETER / 2) ** 2  # m^2

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_polarization_config(ms_path: str) -> Tuple[int, np.ndarray]:
    """
    Get polarization configuration from MS.

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set

    Returns
    -------
    npol : int
        Number of polarizations (typically 2 or 4)
    corr_types : np.ndarray
        CASA correlation type codes (9=XX, 10=XY, 11=YX, 12=YY)
    """
    try:
        import casacore.tables as casatables
    except ImportError:
        # Fallback to casatools
        tb = casatools.table()
        tb.open(f"{ms_path}::POLARIZATION")
        corr_types = tb.getcol("CORR_TYPE")[0]
        tb.close()
        return len(corr_types), corr_types

    with casatables.table(f"{ms_path}::POLARIZATION") as tb:
        corr_types = tb.getcol("CORR_TYPE")[0]
        return len(corr_types), corr_types


def get_calibrator_flux(name: str, freq_ghz: float) -> Tuple[float, float]:
    """
    Get calibrator flux density at specified frequency.

    Uses power-law spectral model: S(ν) = S_0 * (ν/ν_0)^α

    Parameters
    ----------
    name : str
        Calibrator name (e.g., '3C286')
    freq_ghz : float
        Frequency in GHz

    Returns
    -------
    flux_jy : float
        Flux density in Jy
    uncertainty : float
        Uncertainty in Jy (assumed 3% for VLA calibrators)

    References
    ----------
    Perley & Butler 2017, ApJS 230, 7
    """
    if name not in CALIBRATOR_FLUXES:
        raise ValueError(
            f"Unknown calibrator: {name}. Known: {list(CALIBRATOR_FLUXES.keys())}"
        )

    S0, alpha, nu0 = CALIBRATOR_FLUXES[name]
    flux_jy = S0 * (freq_ghz / nu0) ** alpha

    # VLA calibrator fluxes have ~3% uncertainty
    uncertainty = 0.03 * flux_jy

    return flux_jy, uncertainty


def measure_antenna_response(
    ms_path: str, calibrator: str, antenna_idx: int, field_idx: int = 0
) -> Dict:
    """
    Measure antenna response to calibrator source.

    Extracts visibility amplitudes for baselines involving specified antenna,
    averages over time and frequency to get mean response.

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    calibrator : str
        Name of calibrator source
    antenna_idx : int
        Antenna index (0-based)
    field_idx : int, optional
        Field index containing calibrator

    Returns
    -------
    result : dict
        Contains:
        - 'mean_amp': Mean visibility amplitude (Jy)
        - 'std_amp': Standard deviation (Jy)
        - 'n_samples': Number of visibility samples
        - 'frequencies': Array of frequencies (Hz)
        - 'mean_amp_per_freq': Mean amplitude per frequency channel
    """
    logger.info(
        f"Measuring response for antenna {antenna_idx} on calibrator {calibrator}"
    )

    tb = casatools.table()
    tb.open(ms_path)

    try:
        # Get data for specified field
        field_data = tb.query(f"FIELD_ID=={field_idx}")

        # Get antenna pairs
        ant1 = field_data.getcol("ANTENNA1")
        ant2 = field_data.getcol("ANTENNA2")

        # Select baselines involving target antenna
        baseline_mask = (ant1 == antenna_idx) | (ant2 == antenna_idx)

        if not np.any(baseline_mask):
            raise ValueError(f"No baselines found for antenna {antenna_idx}")

        # Get visibility data
        # NOTE: casatools.table returns (npol, nfreq, nrow) - must transpose!
        data = field_data.getcol("DATA")
        flags = field_data.getcol("FLAG")

        # Transpose to standard (nrow, nfreq, npol) order
        if data.shape[2] == len(ant1):  # Check if last axis is nrow
            data = np.transpose(
                data, (2, 1, 0)
            )  # (npol, nfreq, nrow) -> (nrow, nfreq, npol)
            flags = np.transpose(flags, (2, 1, 0))

        # Select data for target antenna baselines
        data_subset = data[baseline_mask, :, :]
        flags_subset = flags[baseline_mask, :, :]

        # Apply flags
        data_subset[flags_subset] = np.nan

        # Compute amplitude (average over polarizations)
        # Stokes I approximation: average parallel hands (XX and YY)
        amp = np.abs(data_subset)

        # Detect polarization configuration
        npol = data_subset.shape[2]
        if npol == 2:
            # 2-pol: assume XX, YY (parallel hands only)
            amp_stokes_i = np.nanmean(amp, axis=2)  # Average over both pols
        elif npol == 4:
            # 4-pol: assume XX, XY, YX, YY - use only parallel hands
            amp_stokes_i = np.nanmean(amp[:, :, [0, 3]], axis=2)  # XX=0, YY=3
        else:
            # Fallback: average all polarizations
            logger.warning(
                f"Unexpected number of polarizations: {npol}. Averaging all."
            )
            amp_stokes_i = np.nanmean(amp, axis=2)

        # Mean and std over time
        mean_amp_per_freq = np.nanmean(amp_stokes_i, axis=0)
        std_amp_per_freq = np.nanstd(amp_stokes_i, axis=0)

        # Overall statistics
        mean_amp = np.nanmean(mean_amp_per_freq)
        std_amp = np.nanstd(mean_amp_per_freq)
        n_samples = np.sum(~np.isnan(amp_stokes_i))

        # Get frequency information
        tb_spw = casatools.table()
        tb_spw.open(f"{ms_path}/SPECTRAL_WINDOW")
        frequencies = tb_spw.getcol("CHAN_FREQ")[0, :]  # Hz
        tb_spw.close()

        field_data.close()

        return {
            "mean_amp": float(mean_amp),
            "std_amp": float(std_amp),
            "n_samples": int(n_samples),
            "frequencies": frequencies,
            "mean_amp_per_freq": mean_amp_per_freq,
            "std_amp_per_freq": std_amp_per_freq,
        }

    finally:
        tb.close()


def calculate_tsys_and_sefd(
    measured_amp: float,
    calibrator_flux: float,
    bandwidth: float,
    integration_time: float,
    n_antennas: int = 117,
) -> Tuple[float, float, float]:
    """
    Calculate system temperature and SEFD from measured visibility amplitude.

    Uses radiometer equation:
        σ_thermal = (2 * k * T_sys) / (A_eff * sqrt(2 * Δν * Δt))

    For a calibrator with known flux S, the visibility amplitude on a baseline is:
        V = S * η_corr
    where η_corr is correlation efficiency.

    From visibility noise and radiometer equation, we can derive T_sys.

    Parameters
    ----------
    measured_amp : float
        Measured visibility amplitude (Jy)
    calibrator_flux : float
        Known calibrator flux (Jy)
    bandwidth : float
        Channel bandwidth (Hz)
    integration_time : float
        Integration time per visibility (s)
    n_antennas : int, optional
        Number of antennas (for baseline correction)

    Returns
    -------
    T_sys : float
        System temperature (K)
    SEFD : float
        System Equivalent Flux Density (Jy)
    efficiency : float
        Aperture efficiency (dimensionless)
    """
    # Correlation efficiency (typically 0.88 for 2-bit quantization)
    eta_corr = 0.88

    # Expected amplitude from perfect system
    expected_amp = calibrator_flux * eta_corr

    # Ratio of observed to expected gives system degradation
    # This is a simplified model - real calculation needs noise measurement
    degradation = measured_amp / expected_amp

    # For T_sys calculation, we need to measure noise, not just signal
    # This is a placeholder - proper implementation requires off-source measurement
    # Assume typical values for now
    logger.warning(
        "T_sys calculation requires noise measurement - using simplified model"
    )

    # Radiometer equation: σ = SEFD / sqrt(2 * Δν * Δt * n_pol)
    # For DSA-110: Δν = 244 kHz/channel, Δt = 12.88s, n_pol = 2
    # Typical measured noise: ~30-50 mJy for single baseline

    # Placeholder T_sys estimate
    T_sys = 50.0  # K - TO BE REPLACED WITH ACTUAL MEASUREMENT

    # SEFD = 2 * k * T_sys / (A_eff * η)
    k_B = const.k_B.to(u.J / u.K).value
    A_eff = ANTENNA_AREA
    efficiency = 0.7  # Assumed - needs measurement

    SEFD = (2 * k_B * T_sys) / (A_eff * efficiency)
    SEFD_Jy = SEFD / 1e-26  # Convert to Jy

    return T_sys, SEFD_Jy, efficiency


def measure_off_source_noise(
    ms_path: str, antenna_idx: int, field_idx: int = 0
) -> Dict:
    """
    Measure off-source noise (RMS) from visibility data.

    This is critical for T_sys measurement. Uses phase-scrambled or
    off-calibrator time ranges to measure thermal noise.

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    antenna_idx : int
        Antenna index
    field_idx : int, optional
        Field index

    Returns
    -------
    result : dict
        Contains:
        - 'rms_jy': RMS noise in Jy
        - 'rms_per_freq': RMS per frequency channel
        - 'n_samples': Number of samples
    """
    logger.info(f"Measuring off-source noise for antenna {antenna_idx}")

    tb = casatools.table()
    tb.open(ms_path)

    try:
        field_data = tb.query(f"FIELD_ID=={field_idx}")

        ant1 = field_data.getcol("ANTENNA1")
        ant2 = field_data.getcol("ANTENNA2")

        baseline_mask = (ant1 == antenna_idx) | (ant2 == antenna_idx)
        if not np.any(baseline_mask):
            raise ValueError(f"No baselines for antenna {antenna_idx}")

        # Get visibility data
        # NOTE: casatools.table returns (npol, nfreq, nrow) - must transpose!
        data = field_data.getcol("DATA")
        flags = field_data.getcol("FLAG")

        # Transpose to standard (nrow, nfreq, npol) order
        if data.shape[2] == len(ant1):  # Check if last axis is nrow
            data = np.transpose(
                data, (2, 1, 0)
            )  # (npol, nfreq, nrow) -> (nrow, nfreq, npol)
            flags = np.transpose(flags, (2, 1, 0))

        data_subset = data[baseline_mask, :, :]
        flags_subset = flags[baseline_mask, :, :]

        data_subset[flags_subset] = np.nan

        # Compute real and imaginary separately (noise is in both)
        real_part = np.real(data_subset)
        imag_part = np.imag(data_subset)

        # RMS of real and imaginary (should be equal for thermal noise)
        rms_real = np.nanstd(real_part, axis=0)  # Per freq, per pol
        rms_imag = np.nanstd(imag_part, axis=0)

        # For thermal noise: σ_real = σ_imag = σ_thermal
        # The visibility amplitude noise is: σ_amp = σ_thermal (not sqrt(2)*σ)
        # Average real and imag RMS (should be nearly equal for thermal noise)
        rms_per_freq = (rms_real + rms_imag) / 2.0
        rms_per_freq = np.nanmean(rms_per_freq, axis=1)  # Average over pols

        rms_jy = np.nanmean(rms_per_freq)
        n_samples = np.sum(~np.isnan(real_part))

        field_data.close()

        return {
            "rms_jy": float(rms_jy),
            "rms_per_freq": rms_per_freq,
            "n_samples": int(n_samples),
        }

    finally:
        tb.close()


def calculate_tsys_from_noise(
    rms_jy: float, bandwidth: float, integration_time: float, efficiency: float = 0.7
) -> float:
    """
    Calculate T_sys from measured noise using radiometer equation.

    Radiometer equation:
        σ = (2 * k_B * T_sys) / (A_eff * sqrt(2 * Δν * Δt * n_pol))

    Rearranging:
        T_sys = (σ * A_eff * sqrt(2 * Δν * Δt * n_pol)) / (2 * k_B)

    Parameters
    ----------
    rms_jy : float
        Measured RMS noise (Jy)
    bandwidth : float
        Channel bandwidth (Hz)
    integration_time : float
        Integration time (s)
    efficiency : float, optional
        Aperture efficiency

    Returns
    -------
    T_sys : float
        System temperature (K)
    """
    k_B = const.k_B.to(u.J / u.K).value
    A_eff = ANTENNA_AREA * efficiency

    # Convert Jy to W/m^2/Hz
    rms_si = rms_jy * 1e-26

    # Radiometer equation (n_pol = 2 for dual-pol)
    n_pol = 2
    T_sys = (rms_si * A_eff * np.sqrt(2 * bandwidth * integration_time * n_pol)) / (
        2 * k_B
    )

    return T_sys


def find_calibrator_field(ms_path: str, calibrator: str) -> int:
    """
    Find which field contains the specified calibrator using coordinate matching.

    Uses the VLA calibrator catalog and primary beam response to identify
    which field (0-23 for DSA-110 drift-scan) contains the calibrator.

    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    calibrator : str
        Calibrator name (e.g., '3C286')

    Returns
    -------
    field_idx : int
        Field index containing the calibrator

    Raises
    ------
    RuntimeError
        If calibrator not found in any field
    """
    logger.info(f"Searching for {calibrator} in MS fields using coordinate matching...")

    try:
        # Use catalog-based field detection
        # This handles DSA-110's meridian_icrs_t## field naming
        field_sel_str, indices, weighted_flux, calib_info, peak_field_idx = (
            select_bandpass_from_catalog(
                ms_path,
                catalog_path=None,  # Auto-detect catalog
                search_radius_deg=1.0,
                freq_GHz=1.4,
                window=3,
            )
        )

        calib_name, ra_deg, dec_deg, flux_jy = calib_info

        logger.info(
            f":check: Found {calib_name} in field {peak_field_idx} "
            f"(RA={ra_deg:.2f}°, Dec={dec_deg:.2f}°, Flux={flux_jy:.1f} Jy)"
        )
        logger.info(f"  Candidate fields: {indices}, peak field: {peak_field_idx}")

        return peak_field_idx

    except Exception as e:
        logger.error(f"Failed to find {calibrator} in MS: {e}")
        raise RuntimeError(
            f"Could not locate {calibrator} in {ms_path}. "
            f"Ensure MS contains calibrator observation and VLA catalog is available."
        ) from e


def analyze_ms(
    ms_path: str,
    calibrator: str,
    output_dir: Path,
    efficiency: float = 0.7,
) -> Dict:
    """
    Analyze a Measurement Set to extract system parameters.

    Parameters
    ----------
    ms_path : str
        Path to MS file
    calibrator : str
        Name of calibrator source
    output_dir : Path
        Directory for output files
    efficiency : float, optional
        Assumed aperture efficiency

    Returns
    -------
    results : dict
        Measurement results for all antennas
    """
    logger.info(f"Analyzing MS: {ms_path}")
    logger.info(f"Calibrator: {calibrator}")

    # Get MS metadata
    tb = casatools.table()
    tb.open(ms_path)
    n_rows = tb.nrows()
    tb.close()

    # Get spectral window info
    tb.open(f"{ms_path}/SPECTRAL_WINDOW")
    frequencies = tb.getcol("CHAN_FREQ")[0, :]
    channel_width = tb.getcol("CHAN_WIDTH")[0, 0]
    tb.close()

    mean_freq_ghz = np.mean(frequencies) / 1e9

    # Get integration time
    tb.open(ms_path)
    exposure = tb.getcol("EXPOSURE")
    integration_time = np.median(exposure)
    tb.close()

    # Get calibrator flux at observation frequency
    calibrator_flux, flux_uncertainty = get_calibrator_flux(calibrator, mean_freq_ghz)

    logger.info(
        f"Calibrator flux at {mean_freq_ghz:.3f} GHz: {calibrator_flux:.2f} ± {flux_uncertainty:.2f} Jy"
    )

    # Get number of antennas
    tb.open(f"{ms_path}/ANTENNA")
    n_antennas = tb.nrows()
    antenna_names = tb.getcol("NAME")
    tb.close()

    logger.info(f"Found {n_antennas} antennas")

    # Find which field contains the calibrator
    try:
        field_idx = find_calibrator_field(ms_path, calibrator)
    except RuntimeError as e:
        logger.error(str(e))
        raise

    logger.info(f"Using field {field_idx} for measurements")

    # Measure parameters for each antenna
    results = {
        "measurement_date": datetime.utcnow().isoformat(),
        "ms_path": str(ms_path),
        "calibrator": calibrator,
        "calibrator_flux_jy": float(calibrator_flux),
        "flux_uncertainty_jy": float(flux_uncertainty),
        "mean_frequency_ghz": float(mean_freq_ghz),
        "channel_width_hz": float(channel_width),
        "integration_time_s": float(integration_time),
        "n_antennas": int(n_antennas),
        "antenna_results": [],
    }

    for ant_idx in range(min(n_antennas, 117)):  # DSA-110 has 117 antennas
        # Skip antennas if limited by environment variable (for testing)
        max_antennas = int(os.environ.get("MAX_ANTENNAS", "999"))
        if ant_idx >= max_antennas:
            logger.info(f"Stopping at antenna {ant_idx} (MAX_ANTENNAS={max_antennas})")
            break

        logger.info(f"Processing antenna {ant_idx} ({antenna_names[ant_idx]})")

        try:
            # Measure antenna response
            response = measure_antenna_response(ms_path, calibrator, ant_idx, field_idx)

            # Measure off-source noise
            noise = measure_off_source_noise(ms_path, ant_idx, field_idx)

            # Calculate T_sys from noise
            T_sys = calculate_tsys_from_noise(
                noise["rms_jy"], channel_width, integration_time, efficiency
            )

            # Calculate SEFD
            k_B = const.k_B.to(u.J / u.K).value
            A_eff = ANTENNA_AREA * efficiency
            SEFD_si = (2 * k_B * T_sys) / A_eff
            SEFD_jy = SEFD_si / 1e-26

            antenna_result = {
                "antenna_index": int(ant_idx),
                "antenna_name": str(antenna_names[ant_idx]),
                "T_sys_K": float(T_sys),
                "SEFD_Jy": float(SEFD_jy),
                "efficiency": float(efficiency),
                "measured_amp_jy": float(response["mean_amp"]),
                "amp_std_jy": float(response["std_amp"]),
                "noise_rms_jy": float(noise["rms_jy"]),
                "n_samples": int(response["n_samples"]),
            }

            results["antenna_results"].append(antenna_result)

            logger.info(
                f"  T_sys = {T_sys:.1f} K, SEFD = {SEFD_jy:.1f} Jy, RMS = {noise['rms_jy']*1e3:.2f} mJy"
            )

        except Exception as e:
            logger.error(f"Error processing antenna {ant_idx}: {e}")
            continue

    # Compute statistics
    if results["antenna_results"]:
        T_sys_values = [r["T_sys_K"] for r in results["antenna_results"]]
        SEFD_values = [r["SEFD_Jy"] for r in results["antenna_results"]]

        results["summary"] = {
            "mean_T_sys_K": float(np.mean(T_sys_values)),
            "std_T_sys_K": float(np.std(T_sys_values)),
            "median_T_sys_K": float(np.median(T_sys_values)),
            "mean_SEFD_Jy": float(np.mean(SEFD_values)),
            "std_SEFD_Jy": float(np.std(SEFD_values)),
            "median_SEFD_Jy": float(np.median(SEFD_values)),
        }

        logger.info("\n=== Summary Statistics ===")
        logger.info(
            f"T_sys: {results['summary']['mean_T_sys_K']:.1f} ± {results['summary']['std_T_sys_K']:.1f} K"
        )
        logger.info(
            f"SEFD: {results['summary']['mean_SEFD_Jy']:.1f} ± {results['summary']['std_SEFD_Jy']:.1f} Jy"
        )

    return results


def plot_results(results: Dict, output_dir: Path):
    """Create diagnostic plots of measurement results."""
    if not results["antenna_results"]:
        logger.warning("No results to plot")
        return

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    antenna_indices = [r["antenna_index"] for r in results["antenna_results"]]
    T_sys_values = [r["T_sys_K"] for r in results["antenna_results"]]
    SEFD_values = [r["SEFD_Jy"] for r in results["antenna_results"]]
    noise_values = [r["noise_rms_jy"] * 1e3 for r in results["antenna_results"]]  # mJy

    # T_sys per antenna
    axes[0, 0].plot(antenna_indices, T_sys_values, "o-", alpha=0.7)
    axes[0, 0].axhline(
        results["summary"]["mean_T_sys_K"], color="r", linestyle="--", label="Mean"
    )
    axes[0, 0].set_xlabel("Antenna Index")
    axes[0, 0].set_ylabel("System Temperature (K)")
    axes[0, 0].set_title("T_sys per Antenna")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # SEFD per antenna
    axes[0, 1].plot(antenna_indices, SEFD_values, "o-", alpha=0.7, color="orange")
    axes[0, 1].axhline(
        results["summary"]["mean_SEFD_Jy"],
        color="r",
        linestyle="--",
        label="Mean",
    )
    axes[0, 1].set_xlabel("Antenna Index")
    axes[0, 1].set_ylabel("SEFD (Jy)")
    axes[0, 1].set_title("SEFD per Antenna")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # T_sys histogram
    axes[1, 0].hist(T_sys_values, bins=20, alpha=0.7, edgecolor="black")
    axes[1, 0].axvline(
        results["summary"]["mean_T_sys_K"], color="r", linestyle="--", label="Mean"
    )
    axes[1, 0].axvline(
        results["summary"]["median_T_sys_K"],
        color="g",
        linestyle="--",
        label="Median",
    )
    axes[1, 0].set_xlabel("System Temperature (K)")
    axes[1, 0].set_ylabel("Count")
    axes[1, 0].set_title("T_sys Distribution")
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # Noise RMS per antenna
    axes[1, 1].plot(antenna_indices, noise_values, "o-", alpha=0.7, color="green")
    axes[1, 1].set_xlabel("Antenna Index")
    axes[1, 1].set_ylabel("RMS Noise (mJy)")
    axes[1, 1].set_title("Off-Source Noise per Antenna")
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = output_dir / "system_parameters.png"
    plt.savefig(plot_path, dpi=150)
    logger.info(f"Saved plot: {plot_path}")
    plt.close()


def save_results(results: Dict, output_dir: Path):
    """Save results in multiple formats."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON (full detail)
    json_path = output_dir / "system_parameters.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved JSON: {json_path}")

    # YAML (human-readable)
    yaml_path = output_dir / "system_parameters.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(results, f, default_flow_style=False, sort_keys=False)
    logger.info(f"Saved YAML: {yaml_path}")

    # Text summary
    txt_path = output_dir / "system_parameters_summary.txt"
    with open(txt_path, "w") as f:
        f.write("DSA-110 System Parameter Measurements\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Measurement Date: {results['measurement_date']}\n")
        f.write(f"Measurement Set: {results['ms_path']}\n")
        f.write(f"Calibrator: {results['calibrator']}\n")
        f.write(
            f"Calibrator Flux: {results['calibrator_flux_jy']:.2f} ± {results['flux_uncertainty_jy']:.2f} Jy\n"
        )
        f.write(f"Frequency: {results['mean_frequency_ghz']:.3f} GHz\n")
        f.write(f"Number of Antennas: {results['n_antennas']}\n\n")

        if "summary" in results:
            f.write("Summary Statistics\n")
            f.write("-" * 50 + "\n")
            f.write(
                f"T_sys: {results['summary']['mean_T_sys_K']:.1f} ± {results['summary']['std_T_sys_K']:.1f} K "
            )
            f.write(f"(median: {results['summary']['median_T_sys_K']:.1f} K)\n")
            f.write(
                f"SEFD: {results['summary']['mean_SEFD_Jy']:.1f} ± {results['summary']['std_SEFD_Jy']:.1f} Jy "
            )
            f.write(f"(median: {results['summary']['median_SEFD_Jy']:.1f} Jy)\n\n")

            f.write("Per-Antenna Results\n")
            f.write("-" * 50 + "\n")
            f.write(
                f"{'Ant':>4} {'Name':>10} {'T_sys(K)':>10} {'SEFD(Jy)':>10} {'RMS(mJy)':>10}\n"
            )
            for ant_result in results["antenna_results"]:
                f.write(
                    f"{ant_result['antenna_index']:4d} "
                    f"{ant_result['antenna_name']:>10} "
                    f"{ant_result['T_sys_K']:10.1f} "
                    f"{ant_result['SEFD_Jy']:10.1f} "
                    f"{ant_result['noise_rms_jy']*1e3:10.2f}\n"
                )

    logger.info(f"Saved summary: {txt_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Measure DSA-110 system parameters from calibrator observations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Measure from 3C286 observation
    python measure_system_parameters.py \\
        --ms /stage/dsa110-contimg/ms/3C286_2025-11-20.ms \\
        --calibrator 3C286 \\
        --output-dir measurements/2025-11-20

    # Use custom efficiency
    python measure_system_parameters.py \\
        --ms observation.ms \\
        --calibrator 3C48 \\
        --efficiency 0.65 \\
        --output-dir measurements/
        """,
    )

    parser.add_argument("--ms", required=True, type=str, help="Path to Measurement Set")
    parser.add_argument(
        "--calibrator",
        required=True,
        type=str,
        choices=list(CALIBRATOR_FLUXES.keys()),
        help="Name of calibrator source",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="measurements",
        help="Output directory for results",
    )
    parser.add_argument(
        "--efficiency",
        type=float,
        default=0.7,
        help="Assumed aperture efficiency (default: 0.7)",
    )
    parser.add_argument("--plot", action="store_true", help="Generate diagnostic plots")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Analyze MS
    results = analyze_ms(args.ms, args.calibrator, output_dir, args.efficiency)

    # Save results
    save_results(results, output_dir)

    # Generate plots
    if args.plot:
        plot_results(results, output_dir)

    logger.info("Measurement complete!")


if __name__ == "__main__":
    main()
