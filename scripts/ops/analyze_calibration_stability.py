#!/usr/bin/env python3
"""
Analyze DSA-110 Calibration Stability from CASA Caltables

This script reads CASA calibration tables (.cal directories) to characterize
the stability of gain amplitudes and phases over time and frequency.

Extracts:
- Gain amplitude statistics (mean, std, RMS) per antenna
- Phase stability (std, wrapped phase RMS) per antenna  
- Temporal trends (drift over observation)
- Frequency-dependent variations (bandpass characteristics)

Used to validate whether simulation defaults (10% gain std, 10° phase std)
are realistic for DSA-110.

Usage:
    python analyze_calibration_stability.py \\
        --caltable /path/to/observation.G0 \\
        --output-dir stability_analysis/

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

    import casatools
    from casacore import tables as casatables
except ImportError:
    print("ERROR: Required CASA tools not found. Run in casa6 environment:")
    print("  conda activate casa6")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def read_caltable(caltable_path: str) -> Dict:
    """
    Read CASA calibration table and extract gain solutions.

    Parameters
    ----------
    caltable_path : str
        Path to .cal directory

    Returns
    -------
    data : dict
        Contains:
        - 'gains': Complex gain array (ntime, nant, nfreq, npol)
        - 'flags': Boolean flag array (same shape)
        - 'times': Time array (MJD seconds)
        - 'antenna_ids': Antenna IDs
        - 'frequencies': Frequency array (Hz)
        - 'caltype': Type of calibration table (G, B, K, etc.)
    """
    logger.info(f"Reading caltable: {caltable_path}")

    tb = casatools.table()
    tb.open(caltable_path)

    try:
        # Get gain solutions
        gains = tb.getcol("CPARAM")  # Complex parameters (nfreq, npol, nrow)
        flags = tb.getcol("FLAG")  # Flags (same shape)
        times = tb.getcol("TIME")  # Time in MJD seconds
        antenna_ids = tb.getcol("ANTENNA1")  # Antenna IDs

        # Rearrange to (nrow, nfreq, npol) for easier processing
        gains = np.transpose(gains, (2, 0, 1))
        flags = np.transpose(flags, (2, 0, 1))

        tb.close()

        # Get spectral window info
        tb.open(f"{caltable_path}/SPECTRAL_WINDOW")
        frequencies = tb.getcol("CHAN_FREQ")[0, :]  # Hz
        tb.close()

        # Get antenna info
        tb.open(f"{caltable_path}/ANTENNA")
        antenna_names = tb.getcol("NAME")
        tb.close()

        # Determine calibration type from table keywords
        tb.open(caltable_path)
        keywords = tb.getkeywords()
        caltype = keywords.get("VisCal", "Unknown")
        tb.close()

        logger.info(f"Caltable type: {caltype}")
        logger.info(f"Shape: {gains.shape} (nrow, nfreq, npol)")
        logger.info(f"Time range: {len(np.unique(times))} unique times")
        logger.info(f"Antennas: {len(np.unique(antenna_ids))}")
        logger.info(f"Frequencies: {len(frequencies)}")

        return {
            "gains": gains,
            "flags": flags,
            "times": times,
            "antenna_ids": antenna_ids,
            "antenna_names": antenna_names,
            "frequencies": frequencies,
            "caltype": caltype,
            "caltable_path": caltable_path,
        }

    except Exception as e:
        tb.close()
        raise RuntimeError(f"Failed to read caltable: {e}")


def analyze_antenna_stability(
    gains: np.ndarray,
    flags: np.ndarray,
    times: np.ndarray,
    antenna_id: int,
) -> Dict:
    """
    Analyze gain stability for a single antenna.

    Parameters
    ----------
    gains : np.ndarray
        Complex gains (nrow, nfreq, npol)
    flags : np.ndarray
        Flags (same shape)
    times : np.ndarray
        Time array (nrow,)
    antenna_id : int
        Antenna ID to analyze

    Returns
    -------
    stats : dict
        Statistics including:
        - Amplitude: mean, std, rms, fractional_std
        - Phase: mean, std (degrees), wrapped_rms
        - Temporal: drift_rate, stability_timescale
    """
    # Apply flags
    gains_copy = gains.copy()
    gains_copy[flags] = np.nan

    # Extract amplitudes and phases
    amplitudes = np.abs(gains_copy)
    phases = np.angle(gains_copy, deg=True)  # Degrees

    # Average over frequency and polarization for time series
    amp_vs_time = np.nanmean(amplitudes, axis=(1, 2))
    phase_vs_time = np.nanmean(phases, axis=(1, 2))

    # Amplitude statistics
    amp_mean = np.nanmean(amplitudes)
    amp_std = np.nanstd(amplitudes)
    amp_rms = np.sqrt(np.nanmean(amplitudes**2))
    amp_fractional_std = (amp_std / amp_mean) if amp_mean > 0 else np.nan

    # Phase statistics (need to handle wrapping)
    phase_mean = np.nanmean(phases)
    phase_std = np.nanstd(phases)

    # Wrapped phase RMS (more robust for phase)
    phase_rad = np.angle(gains_copy)
    phase_wrapped_rms = np.sqrt(
        np.nanmean(1 - np.cos(phase_rad - np.nanmean(phase_rad)))
    )
    phase_wrapped_rms_deg = np.rad2deg(phase_wrapped_rms)

    # Temporal stability: fit linear trend to amplitude
    valid_mask = ~np.isnan(amp_vs_time)
    if np.sum(valid_mask) > 2:
        t_valid = times[valid_mask]
        amp_valid = amp_vs_time[valid_mask]

        # Normalize time to hours
        t_hours = (t_valid - t_valid[0]) / 3600.0

        slope, intercept, r_value, p_value, std_err = stats.linregress(
            t_hours, amp_valid
        )
        drift_rate = (
            slope / amp_mean if amp_mean > 0 else np.nan
        )  # Fractional drift per hour
    else:
        drift_rate = np.nan
        std_err = np.nan

    return {
        "amplitude": {
            "mean": float(amp_mean),
            "std": float(amp_std),
            "rms": float(amp_rms),
            "fractional_std": float(amp_fractional_std),
            "fractional_std_percent": float(amp_fractional_std * 100),
        },
        "phase": {
            "mean_deg": float(phase_mean),
            "std_deg": float(phase_std),
            "wrapped_rms_deg": float(phase_wrapped_rms_deg),
        },
        "temporal": {
            "drift_rate_per_hour": float(drift_rate),
            "drift_uncertainty": float(std_err),
        },
        "n_samples": int(np.sum(~flags)),
        "n_flagged": int(np.sum(flags)),
    }


def analyze_all_antennas(cal_data: Dict) -> Dict:
    """
    Analyze stability for all antennas in caltable.

    Parameters
    ----------
    cal_data : dict
        Caltable data from read_caltable()

    Returns
    -------
    results : dict
        Per-antenna statistics and summary
    """
    gains = cal_data["gains"]
    flags = cal_data["flags"]
    times = cal_data["times"]
    antenna_ids = cal_data["antenna_ids"]
    antenna_names = cal_data["antenna_names"]

    unique_antennas = np.unique(antenna_ids)
    logger.info(f"Analyzing {len(unique_antennas)} antennas")

    antenna_results = []

    for ant_id in unique_antennas:
        # Select data for this antenna
        ant_mask = antenna_ids == ant_id
        ant_gains = gains[ant_mask, :, :]
        ant_flags = flags[ant_mask, :, :]
        ant_times = times[ant_mask]

        if len(ant_gains) == 0:
            logger.warning(f"No data for antenna {ant_id}")
            continue

        # Analyze stability
        stats = analyze_antenna_stability(ant_gains, ant_flags, ant_times, ant_id)

        antenna_result = {
            "antenna_id": int(ant_id),
            "antenna_name": (
                str(antenna_names[ant_id])
                if ant_id < len(antenna_names)
                else f"Ant{ant_id}"
            ),
            **stats,
        }

        antenna_results.append(antenna_result)

        logger.info(
            f"Ant {ant_id:3d} ({antenna_result['antenna_name']:>10}): "
            f"Amp std = {stats['amplitude']['fractional_std_percent']:.1f}%, "
            f"Phase std = {stats['phase']['std_deg']:.1f}°"
        )

    # Compute summary statistics
    amp_stds = [r["amplitude"]["fractional_std_percent"] for r in antenna_results]
    phase_stds = [r["phase"]["std_deg"] for r in antenna_results]
    phase_rms = [r["phase"]["wrapped_rms_deg"] for r in antenna_results]

    summary = {
        "amplitude_stability": {
            "mean_fractional_std_percent": float(np.mean(amp_stds)),
            "median_fractional_std_percent": float(np.median(amp_stds)),
            "std_fractional_std_percent": float(np.std(amp_stds)),
            "min_fractional_std_percent": float(np.min(amp_stds)),
            "max_fractional_std_percent": float(np.max(amp_stds)),
        },
        "phase_stability": {
            "mean_std_deg": float(np.mean(phase_stds)),
            "median_std_deg": float(np.median(phase_stds)),
            "std_std_deg": float(np.std(phase_stds)),
            "mean_wrapped_rms_deg": float(np.mean(phase_rms)),
            "median_wrapped_rms_deg": float(np.median(phase_rms)),
        },
    }

    logger.info("\n=== Summary Statistics ===")
    logger.info(
        f"Amplitude stability: {summary['amplitude_stability']['mean_fractional_std_percent']:.1f}% "
        f"(median: {summary['amplitude_stability']['median_fractional_std_percent']:.1f}%)"
    )
    logger.info(
        f"Phase stability: {summary['phase_stability']['mean_std_deg']:.1f}° "
        f"(median: {summary['phase_stability']['median_std_deg']:.1f}°)"
    )

    return {
        "measurement_date": datetime.utcnow().isoformat(),
        "caltable_path": cal_data["caltable_path"],
        "caltype": cal_data["caltype"],
        "n_antennas": len(antenna_results),
        "summary": summary,
        "antenna_results": antenna_results,
    }


def plot_stability_results(results: Dict, output_dir: Path):
    """Create diagnostic plots of calibration stability."""
    if not results["antenna_results"]:
        logger.warning("No results to plot")
        return

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    antenna_ids = [r["antenna_id"] for r in results["antenna_results"]]
    amp_stds = [
        r["amplitude"]["fractional_std_percent"] for r in results["antenna_results"]
    ]
    phase_stds = [r["phase"]["std_deg"] for r in results["antenna_results"]]
    phase_rms = [r["phase"]["wrapped_rms_deg"] for r in results["antenna_results"]]
    amp_means = [r["amplitude"]["mean"] for r in results["antenna_results"]]
    drift_rates = [
        r["temporal"]["drift_rate_per_hour"] for r in results["antenna_results"]
    ]

    # Amplitude std per antenna
    axes[0, 0].plot(antenna_ids, amp_stds, "o-", alpha=0.7)
    axes[0, 0].axhline(
        results["summary"]["amplitude_stability"]["mean_fractional_std_percent"],
        color="r",
        linestyle="--",
        label="Mean",
    )
    axes[0, 0].axhline(
        10, color="orange", linestyle=":", label="Simulation default (10%)"
    )
    axes[0, 0].set_xlabel("Antenna ID")
    axes[0, 0].set_ylabel("Amplitude Std (%)")
    axes[0, 0].set_title("Gain Amplitude Stability per Antenna")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # Phase std per antenna
    axes[0, 1].plot(antenna_ids, phase_stds, "o-", alpha=0.7, color="orange")
    axes[0, 1].axhline(
        results["summary"]["phase_stability"]["mean_std_deg"],
        color="r",
        linestyle="--",
        label="Mean",
    )
    axes[0, 1].axhline(
        10, color="orange", linestyle=":", label="Simulation default (10°)"
    )
    axes[0, 1].set_xlabel("Antenna ID")
    axes[0, 1].set_ylabel("Phase Std (degrees)")
    axes[0, 1].set_title("Gain Phase Stability per Antenna")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # Phase wrapped RMS
    axes[0, 2].plot(antenna_ids, phase_rms, "o-", alpha=0.7, color="green")
    axes[0, 2].axhline(
        results["summary"]["phase_stability"]["mean_wrapped_rms_deg"],
        color="r",
        linestyle="--",
        label="Mean",
    )
    axes[0, 2].set_xlabel("Antenna ID")
    axes[0, 2].set_ylabel("Phase Wrapped RMS (degrees)")
    axes[0, 2].set_title("Phase Wrapped RMS per Antenna")
    axes[0, 2].legend()
    axes[0, 2].grid(True, alpha=0.3)

    # Amplitude std histogram
    axes[1, 0].hist(amp_stds, bins=20, alpha=0.7, edgecolor="black")
    axes[1, 0].axvline(
        results["summary"]["amplitude_stability"]["mean_fractional_std_percent"],
        color="r",
        linestyle="--",
        label="Mean",
    )
    axes[1, 0].axvline(10, color="orange", linestyle=":", label="Sim default")
    axes[1, 0].set_xlabel("Amplitude Std (%)")
    axes[1, 0].set_ylabel("Count")
    axes[1, 0].set_title("Amplitude Std Distribution")
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # Phase std histogram
    axes[1, 1].hist(phase_stds, bins=20, alpha=0.7, edgecolor="black", color="orange")
    axes[1, 1].axvline(
        results["summary"]["phase_stability"]["mean_std_deg"],
        color="r",
        linestyle="--",
        label="Mean",
    )
    axes[1, 1].axvline(10, color="orange", linestyle=":", label="Sim default")
    axes[1, 1].set_xlabel("Phase Std (degrees)")
    axes[1, 1].set_ylabel("Count")
    axes[1, 1].set_title("Phase Std Distribution")
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    # Amplitude drift rate
    axes[1, 2].plot(antenna_ids, drift_rates, "o-", alpha=0.7, color="purple")
    axes[1, 2].axhline(0, color="black", linestyle="-", linewidth=0.5)
    axes[1, 2].set_xlabel("Antenna ID")
    axes[1, 2].set_ylabel("Drift Rate (per hour)")
    axes[1, 2].set_title("Amplitude Drift Rate per Antenna")
    axes[1, 2].grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = output_dir / "calibration_stability.png"
    plt.savefig(plot_path, dpi=150)
    logger.info(f"Saved plot: {plot_path}")
    plt.close()


def compare_with_simulation_defaults(results: Dict) -> Dict:
    """
    Compare measured stability with simulation defaults.

    Returns
    -------
    comparison : dict
        Statistical comparison results
    """
    sim_amp_std_percent = 10.0  # Default in visibility_models.py
    sim_phase_std_deg = 10.0

    measured_amp_mean = results["summary"]["amplitude_stability"][
        "mean_fractional_std_percent"
    ]
    measured_amp_median = results["summary"]["amplitude_stability"][
        "median_fractional_std_percent"
    ]
    measured_phase_mean = results["summary"]["phase_stability"]["mean_std_deg"]
    measured_phase_median = results["summary"]["phase_stability"]["median_std_deg"]

    comparison = {
        "amplitude": {
            "simulation_default_percent": sim_amp_std_percent,
            "measured_mean_percent": measured_amp_mean,
            "measured_median_percent": measured_amp_median,
            "ratio_mean_to_default": measured_amp_mean / sim_amp_std_percent,
            "ratio_median_to_default": measured_amp_median / sim_amp_std_percent,
            "recommendation": (
                "Simulation default is reasonable"
                if 0.5 < measured_amp_median / sim_amp_std_percent < 2.0
                else f"Consider updating to {measured_amp_median:.1f}%"
            ),
        },
        "phase": {
            "simulation_default_deg": sim_phase_std_deg,
            "measured_mean_deg": measured_phase_mean,
            "measured_median_deg": measured_phase_median,
            "ratio_mean_to_default": measured_phase_mean / sim_phase_std_deg,
            "ratio_median_to_default": measured_phase_median / sim_phase_std_deg,
            "recommendation": (
                "Simulation default is reasonable"
                if 0.5 < measured_phase_median / sim_phase_std_deg < 2.0
                else f"Consider updating to {measured_phase_median:.1f}°"
            ),
        },
    }

    logger.info("\n=== Comparison with Simulation Defaults ===")
    logger.info(
        f"Amplitude: Sim={sim_amp_std_percent:.1f}%, Measured={measured_amp_median:.1f}% "
        f"(ratio: {comparison['amplitude']['ratio_median_to_default']:.2f})"
    )
    logger.info(f"  :arrow_right: {comparison['amplitude']['recommendation']}")
    logger.info(
        f"Phase: Sim={sim_phase_std_deg:.1f}°, Measured={measured_phase_median:.1f}° "
        f"(ratio: {comparison['phase']['ratio_median_to_default']:.2f})"
    )
    logger.info(f"  :arrow_right: {comparison['phase']['recommendation']}")

    return comparison


def save_results(results: Dict, comparison: Dict, output_dir: Path):
    """Save analysis results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Add comparison to results
    results["comparison_with_simulation"] = comparison

    # JSON (full detail)
    json_path = output_dir / "calibration_stability.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved JSON: {json_path}")

    # YAML (human-readable)
    yaml_path = output_dir / "calibration_stability.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(results, f, default_flow_style=False, sort_keys=False)
    logger.info(f"Saved YAML: {yaml_path}")

    # Text summary
    txt_path = output_dir / "calibration_stability_summary.txt"
    with open(txt_path, "w") as f:
        f.write("DSA-110 Calibration Stability Analysis\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Analysis Date: {results['measurement_date']}\n")
        f.write(f"Caltable: {results['caltable_path']}\n")
        f.write(f"Calibration Type: {results['caltype']}\n")
        f.write(f"Number of Antennas: {results['n_antennas']}\n\n")

        f.write("Summary Statistics\n")
        f.write("-" * 60 + "\n")
        f.write("Amplitude Stability:\n")
        f.write(
            f"  Mean:   {results['summary']['amplitude_stability']['mean_fractional_std_percent']:.2f}%\n"
        )
        f.write(
            f"  Median: {results['summary']['amplitude_stability']['median_fractional_std_percent']:.2f}%\n"
        )
        f.write(
            f"  Range:  {results['summary']['amplitude_stability']['min_fractional_std_percent']:.2f}% - "
            f"{results['summary']['amplitude_stability']['max_fractional_std_percent']:.2f}%\n\n"
        )

        f.write("Phase Stability:\n")
        f.write(
            f"  Mean Std:   {results['summary']['phase_stability']['mean_std_deg']:.2f}°\n"
        )
        f.write(
            f"  Median Std: {results['summary']['phase_stability']['median_std_deg']:.2f}°\n"
        )
        f.write(
            f"  Mean Wrapped RMS: {results['summary']['phase_stability']['mean_wrapped_rms_deg']:.2f}°\n\n"
        )

        f.write("Comparison with Simulation Defaults\n")
        f.write("-" * 60 + "\n")
        f.write(
            f"Amplitude: Sim={comparison['amplitude']['simulation_default_percent']:.1f}%, "
            f"Measured={comparison['amplitude']['measured_median_percent']:.1f}% "
            f"(ratio: {comparison['amplitude']['ratio_median_to_default']:.2f})\n"
        )
        f.write(f"  :arrow_right: {comparison['amplitude']['recommendation']}\n\n")
        f.write(
            f"Phase: Sim={comparison['phase']['simulation_default_deg']:.1f}°, "
            f"Measured={comparison['phase']['measured_median_deg']:.1f}° "
            f"(ratio: {comparison['phase']['ratio_median_to_default']:.2f})\n"
        )
        f.write(f"  :arrow_right: {comparison['phase']['recommendation']}\n\n")

        f.write("Per-Antenna Results\n")
        f.write("-" * 60 + "\n")
        f.write(
            f"{'ID':>4} {'Name':>10} {'Amp Std(%)':>12} {'Phase Std(°)':>13} {'Phase RMS(°)':>13}\n"
        )
        for ant_result in results["antenna_results"]:
            f.write(
                f"{ant_result['antenna_id']:4d} "
                f"{ant_result['antenna_name']:>10} "
                f"{ant_result['amplitude']['fractional_std_percent']:12.2f} "
                f"{ant_result['phase']['std_deg']:13.2f} "
                f"{ant_result['phase']['wrapped_rms_deg']:13.2f}\n"
            )

    logger.info(f"Saved summary: {txt_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze DSA-110 calibration stability from CASA caltables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze gain table
    python analyze_calibration_stability.py \\
        --caltable /data/dsa110-contimg/products/caltables/observation.G0 \\
        --output-dir stability_analysis/

    # Analyze bandpass table
    python analyze_calibration_stability.py \\
        --caltable /data/dsa110-contimg/products/caltables/observation.B0 \\
        --output-dir stability_analysis/ \\
        --plot
        """,
    )

    parser.add_argument(
        "--caltable",
        required=True,
        type=str,
        help="Path to calibration table (.cal directory)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="stability_analysis",
        help="Output directory for results",
    )
    parser.add_argument("--plot", action="store_true", help="Generate diagnostic plots")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read caltable
    cal_data = read_caltable(args.caltable)

    # Analyze stability
    results = analyze_all_antennas(cal_data)

    # Compare with simulation defaults
    comparison = compare_with_simulation_defaults(results)

    # Save results
    save_results(results, comparison, output_dir)

    # Generate plots
    if args.plot:
        plot_stability_results(results, output_dir)

    logger.info("Analysis complete!")


if __name__ == "__main__":
    main()
