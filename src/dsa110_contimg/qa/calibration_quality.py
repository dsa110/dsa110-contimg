"""
Calibration quality assessment for DSA-110 continuum imaging pipeline.

Evaluates the quality of CASA calibration tables and applied calibration solutions.
"""

import logging
import numpy as np
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from casacore.tables import table
from dsa110_contimg.utils.angles import wrap_phase_deg

logger = logging.getLogger(__name__)


@dataclass
class CalibrationQualityMetrics:
    """Quality metrics for calibration tables and solutions."""
    
    # Calibration table info
    caltable_path: str
    cal_type: str  # K, B, G, etc.
    n_antennas: int
    n_spws: int
    n_solutions: int
    
    # Solution statistics
    fraction_flagged: float
    median_amplitude: float
    rms_amplitude: float
    amplitude_scatter: float  # RMS of deviations from median
    median_phase_deg: float
    rms_phase_deg: float
    phase_scatter_deg: float
    
    # Quality flags
    has_issues: bool = False
    has_warnings: bool = False
    issues: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "caltable": self.caltable_path,
            "cal_type": self.cal_type,
            "n_antennas": self.n_antennas,
            "n_spws": self.n_spws,
            "n_solutions": self.n_solutions,
            "solution_quality": {
                "fraction_flagged": self.fraction_flagged,
                "median_amplitude": self.median_amplitude,
                "rms_amplitude": self.rms_amplitude,
                "amplitude_scatter": self.amplitude_scatter,
                "median_phase_deg": self.median_phase_deg,
                "rms_phase_deg": self.rms_phase_deg,
                "phase_scatter_deg": self.phase_scatter_deg,
            },
            "quality": {
                "has_issues": self.has_issues,
                "has_warnings": self.has_warnings,
                "issues": self.issues,
                "warnings": self.warnings,
            },
        }


def validate_caltable_quality(caltable_path: str) -> CalibrationQualityMetrics:
    """
    Validate quality of a calibration table.
    
    Args:
        caltable_path: Path to calibration table
    
    Returns:
        CalibrationQualityMetrics object
    """
    logger.info(f"Validating calibration table: {caltable_path}")
    
    if not os.path.exists(caltable_path):
        raise FileNotFoundError(f"Calibration table not found: {caltable_path}")
    
    issues = []
    warnings = []
    
    # Infer cal type from filename
    basename = os.path.basename(caltable_path).lower()
    if "kcal" in basename or "delay" in basename:
        cal_type = "K"
    elif "bpcal" in basename or "bandpass" in basename:
        cal_type = "BP"
    elif "gpcal" in basename or "gacal" in basename or "gain" in basename:
        cal_type = "G"
    else:
        cal_type = "UNKNOWN"
    
    try:
        with table(caltable_path, readonly=True, ack=False) as tb:
            n_solutions = tb.nrows()
            
            if n_solutions == 0:
                issues.append("Calibration table has zero solutions")
            
            # Get antenna and SPW info first (needed for all cal types)
            antenna_ids = tb.getcol("ANTENNA1")
            spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
            n_antennas = len(np.unique(antenna_ids))
            n_spws = len(np.unique(spw_ids))
            
            flags = tb.getcol("FLAG")
            
            # K-calibration tables store delays in FPARAM (float), not CPARAM (complex)
            # BP and G tables store gains in CPARAM (complex)
            colnames = tb.colnames()
            
            if cal_type == "K":
                # K-calibration: delays stored in FPARAM as float values
                if "FPARAM" not in colnames:
                    issues.append("K-calibration table missing FPARAM column")
                    raise ValueError("FPARAM column not found in K-calibration table")
                
                fparam = tb.getcol("FPARAM")  # Shape: (n_rows, n_channels, n_pols)
                # FPARAM interpretation: According to CASA documentation, FPARAM contains
                # delays in seconds. However, some CASA versions may store unwrapped
                # phase values instead. We handle both cases:
                # 1. If values are < 1e-3: treat as delays in seconds
                # 2. If values are larger: treat as unwrapped phase (radians) and convert
                unflagged_fparam = fparam[~flags]
                
                if len(unflagged_fparam) == 0:
                    issues.append("All solutions are flagged")
                    fraction_flagged = 1.0
                    median_amplitude = 0.0  # Not applicable for delays
                    rms_amplitude = 0.0
                    amplitude_scatter = 0.0
                    median_phase_deg = 0.0  # Not applicable for delays
                    rms_phase_deg = 0.0
                    phase_scatter_deg = 0.0
                else:
                    fraction_flagged = float(np.mean(flags))
                    
                    # Determine if FPARAM contains delays or unwrapped phase
                    # Delays should be < 1e-6 seconds (nanoseconds)
                    # Phase values are typically in radians, potentially unwrapped
                    median_fparam = float(np.abs(np.median(unflagged_fparam)))
                    
                    if median_fparam < 1e-3:
                        # Likely delays in seconds (per CASA documentation)
                        delays_ns = unflagged_fparam * 1e9  # Convert seconds to nanoseconds
                    else:
                        # Likely unwrapped phase (radians) - convert to delays
                        # Get reference frequency from MS if available
                        # delay = phase / (2π × frequency)
                        ref_freq_hz = 1400e6  # Default L-band fallback
                        try:
                            # Try to infer MS path from caltable path
                            # Caltable path format: <ms_path>_<field>_kcal
                            caltable_dir = os.path.dirname(caltable_path)
                            caltable_basename = os.path.basename(caltable_path)
                            
                            # Try to find MS in same directory
                            # Pattern: remove suffixes like "_0_kcal" to get MS name
                            ms_candidates = []
                            if "_kcal" in caltable_basename:
                                ms_base = caltable_basename.split("_kcal")[0]
                                # Try different MS name patterns
                                ms_candidates.extend([
                                    os.path.join(caltable_dir, ms_base + ".ms"),
                                    os.path.join(caltable_dir, ms_base.rsplit("_", 1)[0] + ".ms"),
                                ])
                            
                            # Also try globbing for .ms files in same directory
                            import glob
                            ms_files = glob.glob(os.path.join(caltable_dir, "*.ms"))
                            ms_candidates.extend(ms_files)
                            
                            # Try to open first valid MS
                            for ms_candidate in ms_candidates:
                                if os.path.exists(ms_candidate) and os.path.isdir(ms_candidate):
                                    try:
                                        with table(f"{ms_candidate}::SPECTRAL_WINDOW", readonly=True, ack=False) as spw_tb:
                                            ref_freqs = spw_tb.getcol("REF_FREQUENCY")
                                            if len(ref_freqs) > 0:
                                                # Use median reference frequency across SPWs
                                                ref_freq_hz = float(np.median(ref_freqs))
                                                logger.debug(f"Extracted reference frequency {ref_freq_hz/1e6:.1f} MHz from MS {os.path.basename(ms_candidate)}")
                                                break
                                    except Exception:
                                        continue
                            
                            delays_sec = unflagged_fparam / (2 * np.pi * ref_freq_hz)
                            delays_ns = delays_sec * 1e9
                            # Log that we're interpreting as phase
                            logger.debug(f"Interpreting FPARAM as unwrapped phase (radians) for K-calibration, using {ref_freq_hz/1e6:.1f} MHz")
                        except Exception as e:
                            # Fallback: treat as delays in seconds
                            logger.warning(f"Could not extract reference frequency from MS: {e}. Using default {ref_freq_hz/1e6:.1f} MHz")
                            delays_ns = unflagged_fparam * 1e9
                    
                    median_delay_ns = float(np.median(delays_ns))
                    rms_delay_ns = float(np.sqrt(np.mean(delays_ns**2)))
                    
                    # For K-cal, use delay statistics as "amplitude" metrics
                    median_amplitude = median_delay_ns  # Store as delay in ns
                    rms_amplitude = rms_delay_ns
                    amplitude_scatter = float(np.std(delays_ns))
                    
                    # Phase metrics not applicable for delays
                    median_phase_deg = 0.0
                    rms_phase_deg = 0.0
                    phase_scatter_deg = 0.0
                    
                    # Quality checks for delays
                    # Instrumental delays should be < 1 microsecond (< 1000 ns)
                    if abs(median_delay_ns) > 1000:  # > 1 microsecond
                        warnings.append(f"Large median delay: {median_delay_ns:.1f} ns")
                    if amplitude_scatter > 100:  # > 100 ns scatter
                        warnings.append(f"High delay scatter: {amplitude_scatter:.1f} ns")
            
            else:
                # BP and G calibration: complex gains stored in CPARAM
                if "CPARAM" not in colnames:
                    issues.append(f"{cal_type}-calibration table missing CPARAM column")
                    raise ValueError("CPARAM column not found in calibration table")
                
                gains = tb.getcol("CPARAM")  # Complex gains
                
                # Compute statistics on unflagged solutions
                unflagged_gains = gains[~flags]
                
                if len(unflagged_gains) == 0:
                    issues.append("All solutions are flagged")
                    fraction_flagged = 1.0
                    median_amplitude = 0.0
                    rms_amplitude = 0.0
                    amplitude_scatter = 0.0
                    median_phase_deg = 0.0
                    rms_phase_deg = 0.0
                    phase_scatter_deg = 0.0
                else:
                    fraction_flagged = float(np.mean(flags))
                    
                    # Amplitude statistics
                    amplitudes = np.abs(unflagged_gains)
                    median_amplitude = float(np.median(amplitudes))
                    rms_amplitude = float(np.sqrt(np.mean(amplitudes**2)))
                    amplitude_scatter = float(np.std(amplitudes))
                    
                    # Phase statistics (wrap to [-180, 180) before computing metrics)
                    phases_rad = np.angle(unflagged_gains)
                    phases_deg = np.degrees(phases_rad)
                    phases_deg = wrap_phase_deg(phases_deg)
                    median_phase_deg = float(np.median(phases_deg))
                    rms_phase_deg = float(np.sqrt(np.mean(phases_deg**2)))
                    phase_scatter_deg = float(np.std(phases_deg))
                
                    # Quality checks for gain/phase tables
                    if fraction_flagged > 0.3:
                        warnings.append(f"High fraction of flagged solutions: {fraction_flagged:.1%}")
                    
                    # Check for bad amplitudes (too close to zero or too large)
                    if median_amplitude < 0.1:
                        warnings.append(f"Very low median amplitude: {median_amplitude:.3f}")
                    elif median_amplitude > 10.0:
                        warnings.append(f"Very high median amplitude: {median_amplitude:.3f}")
                    
                    # Check amplitude scatter (should be relatively stable)
                    if median_amplitude > 0 and amplitude_scatter / median_amplitude > 0.5:
                        warnings.append(f"High amplitude scatter: {amplitude_scatter/median_amplitude:.1%} of median")
                    
                    # Check for large phase jumps
                    if phase_scatter_deg > 90:
                        warnings.append(f"Large phase scatter: {phase_scatter_deg:.1f} degrees")
                
                # Check for antennas with all solutions flagged
                for ant_id in np.unique(antenna_ids):
                    ant_mask = antenna_ids == ant_id
                    ant_flags = flags[ant_mask]
                    if np.all(ant_flags):
                        warnings.append(f"Antenna {ant_id} has all solutions flagged")
    
    except Exception as e:
        logger.error(f"Error validating calibration table: {e}")
        issues.append(f"Exception during validation: {e}")
        # Set dummy values
        cal_type = "UNKNOWN"
        n_antennas = 0
        n_spws = 0
        n_solutions = 0
        fraction_flagged = 0.0
        median_amplitude = 0.0
        rms_amplitude = 0.0
        amplitude_scatter = 0.0
        median_phase_deg = 0.0
        rms_phase_deg = 0.0
        phase_scatter_deg = 0.0
    
    metrics = CalibrationQualityMetrics(
        caltable_path=caltable_path,
        cal_type=cal_type,
        n_antennas=n_antennas,
        n_spws=n_spws,
        n_solutions=n_solutions,
        fraction_flagged=fraction_flagged,
        median_amplitude=median_amplitude,
        rms_amplitude=rms_amplitude,
        amplitude_scatter=amplitude_scatter,
        median_phase_deg=median_phase_deg,
        rms_phase_deg=rms_phase_deg,
        phase_scatter_deg=phase_scatter_deg,
        has_issues=len(issues) > 0,
        has_warnings=len(warnings) > 0,
        issues=issues,
        warnings=warnings,
    )
    
    # Log results
    if metrics.has_issues:
        logger.error(f"Calibration table has issues: {', '.join(issues)}")
    if metrics.has_warnings:
        logger.warning(f"Calibration table has warnings: {', '.join(warnings)}")
    if not metrics.has_issues and not metrics.has_warnings:
        logger.info(f"Calibration table passed quality checks")
    
    return metrics


@dataclass
class PerSPWFlaggingStats:
    """Per-spectral-window flagging statistics."""
    spw_id: int
    total_solutions: int
    flagged_solutions: int
    fraction_flagged: float
    n_channels: int
    channels_with_high_flagging: int  # Channels with >50% solutions flagged
    avg_flagged_per_channel: float
    max_flagged_in_channel: int
    is_problematic: bool  # True if SPW exceeds thresholds


def analyze_per_spw_flagging(
    caltable_path: str,
    high_flagging_threshold: float = 0.5,
    problematic_spw_threshold: float = 0.8,
) -> List[PerSPWFlaggingStats]:
    """
    Analyze flagged solutions per spectral window in a calibration table.
    
    This function provides per-SPW statistics to identify problematic spectral windows
    with high flagging rates. This is primarily a DIAGNOSTIC tool to understand which
    SPWs have systematic issues.
    
    **Note on Flagging Philosophy:**
    - The pipeline uses per-channel flagging BEFORE calibration (preserves good channels)
    - Per-SPW analysis is diagnostic - helps identify problematic SPWs
    - Flagging entire SPWs should be a LAST RESORT if per-channel flagging is insufficient
    - Prefer reviewing per-channel flagging statistics first
    
    **Multi-field Bandpass:**
    - Works correctly with multi-field bandpass solutions (combine_fields=True)
    - Analyzes the combined solutions across all fields
    
    Args:
        caltable_path: Path to calibration table
        high_flagging_threshold: Fraction threshold for considering a channel as having
            high flagging (default: 0.5 = 50%)
        problematic_spw_threshold: Average flagged fraction threshold for considering
            an entire SPW as problematic (default: 0.8 = 80%)
    
    Returns:
        List of PerSPWFlaggingStats objects, one per SPW
    
    References:
        - NRAO VLA/VLBA calibration guides recommend per-SPW evaluation for diagnostics
        - Best practice: Use per-channel flagging first, SPW-level flagging as last resort
    """
    from casacore.tables import table
    import numpy as np
    
    if not os.path.exists(caltable_path):
        raise FileNotFoundError(f"Calibration table not found: {caltable_path}")
    
    stats_list = []
    
    with table(caltable_path, readonly=True, ack=False) as tb:
        if "SPECTRAL_WINDOW_ID" not in tb.colnames():
            logger.warning("Calibration table does not have SPECTRAL_WINDOW_ID column")
            return stats_list
        
        spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")  # Shape: (n_solutions,)
        flags = tb.getcol("FLAG")  # Shape: (n_solutions, n_channels, n_pols) for BP/G tables
        
        # Get shape information
        if flags.ndim == 3:  # (n_solutions, n_channels, n_pols)
            n_channels = flags.shape[1]
            n_pols = flags.shape[2]
        elif flags.ndim == 2:  # (n_solutions, n_channels) or (n_solutions, n_pols)
            # For some tables, might be 2D
            n_channels = flags.shape[1]  # Assume second dimension is channels
            n_pols = 1
        else:
            logger.warning(f"Unexpected FLAG shape: {flags.shape}")
            return stats_list
        
        unique_spws = np.unique(spw_ids)
        
        for spw_id in unique_spws:
            spw_mask = spw_ids == spw_id  # Boolean mask for solutions in this SPW
            spw_flags = flags[spw_mask]  # Shape: (n_solutions_in_spw, n_channels, n_pols)
            
            # Calculate total flagged solutions (across all channels and pols)
            total_solutions = spw_flags.size
            flagged_solutions = np.sum(spw_flags)
            fraction_flagged = float(flagged_solutions / total_solutions) if total_solutions > 0 else 0.0
            
            # Analyze per-channel flagging
            # For per-channel analysis, we look at flagging across all solutions and pols for each channel
            if spw_flags.ndim == 3:
                # Collapse polarization dimension: (n_solutions, n_channels, n_pols) -> (n_solutions, n_channels)
                # A channel is considered flagged if ANY polarization is flagged
                spw_flags_2d = np.any(spw_flags, axis=2)  # Shape: (n_solutions, n_channels)
            else:
                spw_flags_2d = spw_flags  # Shape: (n_solutions, n_channels)
            
            # For each channel, count how many solutions are flagged
            n_solutions_per_channel = spw_flags_2d.shape[0]
            flagged_per_channel = np.sum(spw_flags_2d, axis=0)  # Sum over solutions: (n_channels,)
            fraction_flagged_per_channel = flagged_per_channel / n_solutions_per_channel if n_solutions_per_channel > 0 else np.zeros(n_channels)
            
            channels_with_high_flagging = np.sum(fraction_flagged_per_channel > high_flagging_threshold)
            avg_flagged_per_channel = float(np.mean(fraction_flagged_per_channel))
            max_flagged_in_channel = int(np.max(flagged_per_channel))
            
            # Determine if SPW is problematic
            # An SPW is problematic if:
            # 1. Average flagged fraction exceeds threshold, OR
            # 2. More than 50% of channels have high flagging
            is_problematic = (
                avg_flagged_per_channel > problematic_spw_threshold or
                channels_with_high_flagging > (n_channels * 0.5)
            )
            
            stats = PerSPWFlaggingStats(
                spw_id=int(spw_id),
                total_solutions=int(np.sum(spw_mask)),
                flagged_solutions=int(flagged_solutions),
                fraction_flagged=fraction_flagged,
                n_channels=n_channels,
                channels_with_high_flagging=int(channels_with_high_flagging),
                avg_flagged_per_channel=avg_flagged_per_channel,
                max_flagged_in_channel=max_flagged_in_channel,
                is_problematic=is_problematic,
            )
            stats_list.append(stats)
    
    return stats_list


def flag_problematic_spws(
    ms_path: str,
    caltable_path: str,
    high_flagging_threshold: float = 0.5,
    problematic_spw_threshold: float = 0.8,
    datacolumn: str = "data",
) -> List[int]:
    """
    Flag data in problematic spectral windows based on bandpass calibration quality.
    
    **WARNING: This flags entire SPWs, which may remove good channels.**
    
    **Recommended Approach:**
    1. First, review per-channel flagging statistics (done pre-calibration)
    2. Use per-channel flagging to preserve good channels in "bad" SPWs
    3. Only use this function as a LAST RESORT if per-channel flagging is insufficient
    
    This function identifies SPWs with consistently high flagging rates in bandpass
    solutions and flags the corresponding data in the MS, following NRAO/VLBA best
    practices for handling low S/N spectral windows.
    
    Args:
        ms_path: Path to Measurement Set
        caltable_path: Path to bandpass calibration table
        high_flagging_threshold: Fraction threshold for considering a channel as having
            high flagging (default: 0.5 = 50%)
        problematic_spw_threshold: Average flagged fraction threshold for considering
            an entire SPW as problematic (default: 0.8 = 80%)
        datacolumn: Data column to flag (default: "data")
    
    Returns:
        List of SPW IDs that were flagged
    
    References:
        - NRAO/VLBA calibration guides recommend flagging or excluding SPWs with
          consistently high flagging rates that cannot be effectively calibrated
    """
    from dsa110_contimg.calibration.flagging import flag_manual
    
    # Analyze per-SPW flagging
    spw_stats = analyze_per_spw_flagging(
        caltable_path,
        high_flagging_threshold=high_flagging_threshold,
        problematic_spw_threshold=problematic_spw_threshold,
    )
    
    problematic_spws = [s.spw_id for s in spw_stats if s.is_problematic]
    
    if not problematic_spws:
        logger.info("No problematic SPWs found - no flagging needed")
        return []
    
    # Flag each problematic SPW
    flagged_spws = []
    for spw_id in problematic_spws:
        try:
            spw_str = str(spw_id)
            flag_manual(ms_path, spw=spw_str, datacolumn=datacolumn)
            flagged_spws.append(spw_id)
            logger.info(f"Flagged SPW {spw_id} due to high bandpass solution flagging rate")
        except Exception as e:
            logger.warning(f"Failed to flag SPW {spw_id}: {e}")
    
    return flagged_spws


def export_per_spw_stats(
    spw_stats: List[PerSPWFlaggingStats],
    output_path: str,
    format: str = "json",
) -> str:
    """
    Export per-SPW flagging statistics to a file.
    
    Args:
        spw_stats: List of PerSPWFlaggingStats objects
        output_path: Output file path (extension will be added if not present)
        format: Output format - "json" or "csv" (default: "json")
    
    Returns:
        Path to the created file
    """
    import json
    import csv
    from pathlib import Path
    
    output = Path(output_path)
    
    if format.lower() == "json":
        if not output.suffix:
            output = output.with_suffix(".json")
        
        # Convert dataclass to dict for JSON serialization
        stats_dict = {
            "per_spw_statistics": [
                {
                    "spw_id": s.spw_id,
                    "total_solutions": s.total_solutions,
                    "flagged_solutions": s.flagged_solutions,
                    "fraction_flagged": s.fraction_flagged,
                    "n_channels": s.n_channels,
                    "channels_with_high_flagging": s.channels_with_high_flagging,
                    "avg_flagged_per_channel": s.avg_flagged_per_channel,
                    "max_flagged_in_channel": s.max_flagged_in_channel,
                    "is_problematic": bool(s.is_problematic),
                }
                for s in spw_stats
            ],
            "summary": {
                "total_spws": len(spw_stats),
                "problematic_spws": [s.spw_id for s in spw_stats if s.is_problematic],
                "n_problematic": len([s for s in spw_stats if s.is_problematic]),
            },
        }
        
        with open(output, "w") as f:
            json.dump(stats_dict, f, indent=2)
    
    elif format.lower() == "csv":
        if not output.suffix:
            output = output.with_suffix(".csv")
        
        with open(output, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "SPW_ID",
                "Total_Solutions",
                "Flagged_Solutions",
                "Fraction_Flagged",
                "N_Channels",
                "Channels_With_High_Flagging",
                "Avg_Flagged_Per_Channel",
                "Max_Flagged_In_Channel",
                "Is_Problematic",
            ])
            for s in sorted(spw_stats, key=lambda x: x.spw_id):
                writer.writerow([
                    s.spw_id,
                    s.total_solutions,
                    s.flagged_solutions,
                    f"{s.fraction_flagged:.6f}",
                    s.n_channels,
                    s.channels_with_high_flagging,
                    f"{s.avg_flagged_per_channel:.6f}",
                    s.max_flagged_in_channel,
                    s.is_problematic,
                ])
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'")
    
    return str(output)


def plot_per_spw_flagging(
    spw_stats: List[PerSPWFlaggingStats],
    output_path: str,
    title: str = "Per-Spectral-Window Flagging Analysis",
) -> str:
    """
    Create a visualization of per-SPW flagging statistics.
    
    Args:
        spw_stats: List of PerSPWFlaggingStats objects
        output_path: Output file path (extension will be added if not present)
        title: Plot title (default: "Per-Spectral-Window Flagging Analysis")
    
    Returns:
        Path to the created plot file
    """
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    import numpy as np
    from pathlib import Path
    
    output = Path(output_path)
    if not output.suffix:
        output = output.with_suffix(".png")
    
    # Sort by SPW ID
    sorted_stats = sorted(spw_stats, key=lambda x: x.spw_id)
    spw_ids = [s.spw_id for s in sorted_stats]
    fractions = [s.fraction_flagged * 100 for s in sorted_stats]
    avg_per_channel = [s.avg_flagged_per_channel * 100 for s in sorted_stats]
    problematic = [s.is_problematic for s in sorted_stats]
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Plot 1: Overall flagged fraction per SPW
    colors = ['#d62728' if p else '#2ca02c' for p in problematic]
    bars1 = ax1.bar(spw_ids, fractions, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
    ax1.axhline(y=80, color='red', linestyle='--', linewidth=1, label='Problematic threshold (80%)')
    ax1.set_ylabel('Flagged Fraction (%)', fontsize=11)
    ax1.set_title(f'{title}\nOverall Flagged Fraction per SPW', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.legend()
    ax1.set_ylim(0, max(fractions) * 1.1 if fractions else 100)
    
    # Add value labels on bars
    for bar, frac in zip(bars1, fractions):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{frac:.1f}%', ha='center', va='bottom', fontsize=8)
    
    # Plot 2: Average flagged per channel
    bars2 = ax2.bar(spw_ids, avg_per_channel, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
    ax2.axhline(y=80, color='red', linestyle='--', linewidth=1, label='Problematic threshold (80%)')
    ax2.set_xlabel('Spectral Window ID', fontsize=11)
    ax2.set_ylabel('Avg Flagged per Channel (%)', fontsize=11)
    ax2.set_title('Average Flagged Fraction per Channel', fontsize=11)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.legend()
    ax2.set_ylim(0, max(avg_per_channel) * 1.1 if avg_per_channel else 100)
    
    # Add value labels on bars
    for bar, avg in zip(bars2, avg_per_channel):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{avg:.1f}%', ha='center', va='bottom', fontsize=8)
    
    # Add problematic SPW labels
    problematic_spws = [s.spw_id for s in sorted_stats if s.is_problematic]
    if problematic_spws:
        ax2.text(0.02, 0.98, f'Problematic SPWs: {", ".join(map(str, problematic_spws))}',
                transform=ax2.transAxes, fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(output)


def check_corrected_data_quality(
    ms_path: str,
    sample_fraction: float = 0.1,
) -> Tuple[bool, Dict, List[str]]:
    """
    Check quality of CORRECTED_DATA after calibration.
    
    Args:
        ms_path: Path to MS
        sample_fraction: Fraction of data to sample
    
    Returns:
        (passed, metrics_dict, issues) tuple
    """
    logger.info(f"Checking CORRECTED_DATA quality: {ms_path}")
    
    issues = []
    metrics = {}
    
    try:
        with table(ms_path, readonly=True, ack=False) as tb:
            if "CORRECTED_DATA" not in tb.colnames():
                issues.append("CORRECTED_DATA column not present")
                return False, metrics, issues
            
            n_rows = tb.nrows()
            if n_rows == 0:
                issues.append("MS has zero rows")
                return False, metrics, issues
            
            # Sample data
            sample_size = max(100, int(n_rows * sample_fraction))
            indices = np.linspace(0, n_rows - 1, sample_size, dtype=int)
            
            corrected_data = tb.getcol("CORRECTED_DATA", startrow=indices[0], nrow=len(indices))
            data = tb.getcol("DATA", startrow=indices[0], nrow=len(indices))
            flags = tb.getcol("FLAG", startrow=indices[0], nrow=len(indices))
            
            # Check for all zeros
            if np.all(np.abs(corrected_data) < 1e-10):
                issues.append("CORRECTED_DATA is all zeros - calibration may have failed")
                return False, metrics, issues
            
            # Compute statistics
            unflagged_corrected = corrected_data[~flags]
            unflagged_data = data[~flags]
            
            if len(unflagged_corrected) == 0:
                issues.append("All CORRECTED_DATA is flagged")
                return False, metrics, issues
            
            corrected_amps = np.abs(unflagged_corrected)
            data_amps = np.abs(unflagged_data)
            
            metrics["median_corrected_amp"] = float(np.median(corrected_amps))
            metrics["median_data_amp"] = float(np.median(data_amps))
            metrics["calibration_factor"] = metrics["median_corrected_amp"] / metrics["median_data_amp"] if metrics["median_data_amp"] > 0 else 0.0
            metrics["corrected_amp_range"] = (float(np.min(corrected_amps)), float(np.max(corrected_amps)))
            
            # Check for reasonable calibration factor (should be close to 1 for good calibration)
            if metrics["calibration_factor"] > 10 or metrics["calibration_factor"] < 0.1:
                issues.append(f"Unusual calibration factor: {metrics['calibration_factor']:.2f}x")
            
            logger.info(f"CORRECTED_DATA quality check passed: median amp={metrics['median_corrected_amp']:.3e}, factor={metrics['calibration_factor']:.2f}x")
            return True, metrics, issues
    
    except Exception as e:
        logger.error(f"Error checking CORRECTED_DATA: {e}")
        issues.append(f"Exception: {e}")
        return False, metrics, issues


# ============================================================================
# Delay-Specific QA Functions (moved from calibration/qa.py)
# ============================================================================

def check_upstream_delay_correction(ms_path: str, n_baselines: int = 100) -> Dict[str, Any]:
    """
    Check if delays are already corrected upstream by analyzing phase vs frequency.
    
    This function performs a statistical analysis of phase slopes across
    frequency to estimate residual delays. It analyzes both per-baseline delays
    and antenna-consistent delays (which are more indicative of instrumental
    delays vs geometric delays).
    
    Args:
        ms_path: Path to Measurement Set (should contain raw DATA column)
        n_baselines: Number of baselines to analyze (default: 100)
                     Analyzes first N unflagged baselines
        
    Returns:
        Dictionary with keys:
        - 'median_ns': Median absolute delay (ns)
        - 'mean_ns': Mean absolute delay (ns)
        - 'std_ns': Standard deviation of delays (ns)
        - 'min_ns', 'max_ns': Delay range (ns)
        - 'antenna_median_ns': Median delay per antenna (ns)
        - 'antenna_std_ns': Std dev of antenna delays (ns)
        - 'n_baselines': Number of baselines analyzed
        - 'recommendation': 'likely_corrected', 'partial', or 'needs_correction'
    """
    print(f"\n{'='*70}")
    print(f"Checking Upstream Delay Correction")
    print(f"MS: {ms_path}")
    print(f"{'='*70}\n")
    
    with table(ms_path, readonly=True) as tb:
        n_rows = tb.nrows()
        n_sample = min(n_baselines, n_rows)
        
        print(f"Analyzing {n_sample} baselines from {n_rows} total rows...\n")
        
        # Get data
        data = tb.getcol('DATA', startrow=0, nrow=n_sample)
        flags = tb.getcol('FLAG', startrow=0, nrow=n_sample)
        ant1 = tb.getcol('ANTENNA1', startrow=0, nrow=n_sample)
        ant2 = tb.getcol('ANTENNA2', startrow=0, nrow=n_sample)
        
        # Get frequency information
        with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
            chan_freqs = spw_tb.getcol('CHAN_FREQ')  # Shape: (n_spw, n_chan)
        
        # Get DATA_DESCRIPTION mapping
        with table(f"{ms_path}::DATA_DESCRIPTION", readonly=True) as dd_tb:
            spw_map = dd_tb.getcol('SPECTRAL_WINDOW_ID')
        
        dd_ids = tb.getcol('DATA_DESC_ID', startrow=0, nrow=n_sample)
        
        # Analyze phase slopes
        delays_ns = []
        phase_slopes_per_antenna: Dict[int, list] = {}
        
        for i in range(n_sample):
            # Skip flagged data
            if np.all(flags[i]):
                continue
            
            # Get frequency array for this baseline
            dd_id = int(dd_ids[i])
            if dd_id >= len(spw_map):
                continue
            spw_id = int(spw_map[dd_id])
            if spw_id >= len(chan_freqs):
                continue
            
            freqs = chan_freqs[spw_id]  # Shape: (n_chan,)
            vis = data[i, :, 0]  # First polarization
            
            # Extract unflagged channels
            unflagged = ~flags[i, :, 0]
            if np.sum(unflagged) < 10:  # Need at least 10 channels
                continue
            
            unflagged_freqs = freqs[unflagged]
            unflagged_vis = vis[unflagged]
            
            # Compute phase
            phases = np.angle(unflagged_vis)
            phases_unwrapped = np.unwrap(phases)
            
            # Fit linear: phase = a * freq + b
            # Delay causes linear phase vs frequency
            coeffs = np.polyfit(unflagged_freqs, phases_unwrapped, 1)
            delay_sec = coeffs[0] / (2 * np.pi)
            delay_ns = delay_sec * 1e9
            
            delays_ns.append(delay_ns)
            
            # Track per antenna (average delays involving this antenna)
            for ant in [int(ant1[i]), int(ant2[i])]:
                if ant not in phase_slopes_per_antenna:
                    phase_slopes_per_antenna[ant] = []
                phase_slopes_per_antenna[ant].append(delay_ns)
        
        if not delays_ns:
            print("⚠ Could not extract sufficient data for analysis")
            return {"error": "Insufficient unflagged data"}
        
        delays_ns = np.array(delays_ns)
        
        # Compute statistics
        delay_stats = {
            "median_ns": float(np.median(np.abs(delays_ns))),
            "mean_ns": float(np.mean(np.abs(delays_ns))),
            "std_ns": float(np.std(delays_ns)),
            "min_ns": float(np.min(delays_ns)),
            "max_ns": float(np.max(delays_ns)),
            "range_ns": float(np.max(np.abs(delays_ns)) - np.min(np.abs(delays_ns))),
            "n_baselines": len(delays_ns),
        }
        
        # Compute antenna-consistent delays (instrumental)
        ant_delays = {}
        for ant, delays in phase_slopes_per_antenna.items():
            ant_delays[ant] = np.median(delays)
        
        if ant_delays:
            ant_delay_values = np.array(list(ant_delays.values()))
            delay_stats["antenna_median_ns"] = float(np.median(np.abs(ant_delay_values)))
            delay_stats["antenna_std_ns"] = float(np.std(ant_delay_values))
            delay_stats["antenna_range_ns"] = float(np.max(np.abs(ant_delay_values)) - np.min(np.abs(ant_delay_values)))
        
        # Print results
        print(f"Phase Slope Analysis:")
        print(f"  Baselines analyzed: {delay_stats['n_baselines']}")
        print(f"  Median |delay|: {delay_stats['median_ns']:.3f} ns")
        print(f"  Mean |delay|: {delay_stats['mean_ns']:.3f} ns")
        print(f"  Std dev: {delay_stats['std_ns']:.3f} ns")
        print(f"  Range: {delay_stats['min_ns']:.3f} to {delay_stats['max_ns']:.3f} ns")
        
        if ant_delays:
            print(f"\nAntenna-Consistent Delays (Instrumental):")
            print(f"  Antennas: {len(ant_delays)}")
            print(f"  Median |delay|: {delay_stats['antenna_median_ns']:.3f} ns")
            print(f"  Std dev: {delay_stats['antenna_std_ns']:.3f} ns")
            print(f"  Range: {delay_stats['antenna_range_ns']:.3f} ns")
        
        # Assess if delays are corrected
        print(f"\n{'='*70}")
        print("Assessment:")
        print(f"{'='*70}\n")
        
        # Thresholds for determining if delays are corrected
        threshold_well_corrected = 1.0  # ns
        threshold_needs_correction = 5.0  # ns
        
        max_delay = delay_stats['antenna_median_ns'] if ant_delays else delay_stats['median_ns']
        
        if max_delay < threshold_well_corrected:
            print("✓ DELAYS APPEAR TO BE CORRECTED UPSTREAM")
            print(f"  Median delay ({max_delay:.3f} ns) is < {threshold_well_corrected} ns")
            print("  → K-calibration may be redundant")
            print("  → Phase slopes are minimal")
            recommendation = "likely_corrected"
        elif max_delay < threshold_needs_correction:
            print("⚠ DELAYS PARTIALLY CORRECTED")
            print(f"  Median delay ({max_delay:.3f} ns) is {threshold_well_corrected}-{threshold_needs_correction} ns")
            print("  → Small residual delays present")
            print("  → K-calibration may still improve quality")
            recommendation = "partial"
        else:
            print("✗ DELAYS NOT CORRECTED UPSTREAM")
            print(f"  Median delay ({max_delay:.3f} ns) is > {threshold_needs_correction} ns")
            print("  → Significant delays present")
            print("  → K-calibration is NECESSARY")
            recommendation = "needs_correction"
        
        # Additional check: Are delays antenna-consistent?
        if ant_delays:
            ant_std = delay_stats['antenna_std_ns']
            baseline_std = delay_stats['std_ns']
            
            print(f"\nDelay Consistency Check:")
            print(f"  Antenna std dev: {ant_std:.3f} ns")
            print(f"  Baseline std dev: {baseline_std:.3f} ns")
            
            if ant_std < baseline_std * 0.7:
                print("  → Delays are antenna-consistent (instrumental)")
                print("  → K-calibration can correct these")
            else:
                print("  → Delays vary more by baseline (geometric or mixed)")
                print("  → May need geometric correction or K-calibration")
        
        delay_stats["recommendation"] = recommendation
        return delay_stats


def verify_kcal_delays(ms_path: str, kcal_path: Optional[str] = None,
                       cal_field: Optional[str] = None, refant: str = "103",
                       no_create: bool = False) -> None:
    """
    Verify K-calibration delay values and assess their significance.
    
    This function finds or creates a K-calibration table, inspects delay values,
    and provides recommendations.
    
    Args:
        ms_path: Path to Measurement Set
        kcal_path: Path to K-calibration table (auto-detected if not provided)
        cal_field: Calibrator field selection (auto-detected if not provided)
        refant: Reference antenna (default: 103)
        no_create: Don't create K-cal table if missing, just report
    """
    from pathlib import Path
    
    ms_dir = Path(ms_path).parent
    ms_stem = Path(ms_path).stem
    
    # Find existing K-cal table
    if kcal_path and Path(kcal_path).exists():
        kcal_table = kcal_path
    else:
        kcal_pattern = f"{ms_stem}*kcal"
        existing_kcals = list(ms_dir.glob(kcal_pattern))
        if existing_kcals:
            kcal_table = str(existing_kcals[0])
            print(f"Found existing K-calibration table: {kcal_table}")
        else:
            if no_create:
                print(f"✗ No K-calibration table found and --no-create specified")
                print(f"  MS: {ms_path}")
                print(f"  Searched in: {ms_dir}")
                return
            else:
                print(f"No existing K-calibration table found. Creating one...")
                from dsa110_contimg.calibration.calibration import solve_delay
                if cal_field is None:
                    cal_field = "0"  # Default to field 0
                try:
                    ktabs = solve_delay(ms_path, cal_field, refant)
                    if ktabs:
                        kcal_table = ktabs[0]
                        print(f"✓ Created K-calibration table: {kcal_table}")
                    else:
                        print("✗ Failed to create K-calibration table")
                        return
                except Exception as e:
                    print(f"✗ Failed to create K-calibration table: {e}")
                    return
    
    # Inspect the table
    inspect_kcal_simple(kcal_table, ms_path, find=False)


def inspect_kcal_simple(kcal_path: Optional[str] = None, ms_path: Optional[str] = None,
                        find: bool = False) -> None:
    """
    Inspect K-calibration delay values from a calibration table.
    
    Args:
        kcal_path: Path to K-calibration table (or None if using --find)
        ms_path: Path to MS (to auto-find K-cal table if --find)
        find: If True, find K-cal tables for MS instead of inspecting
    """
    from pathlib import Path
    
    if find:
        if not ms_path:
            print("✗ Error: --find requires --ms")
            return
        ms_dir = Path(ms_path).parent
        ms_stem = Path(ms_path).stem
        
        kcal_patterns = [
            f"{ms_stem}*kcal",
            f"{ms_stem}*_0_kcal",
            "*kcal",
        ]
        
        found_tables = []
        for pattern in kcal_patterns:
            found_tables.extend(ms_dir.glob(pattern))
        
        found_tables = sorted(set(found_tables), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if found_tables:
            print(f"\nFound {len(found_tables)} K-calibration table(s):\n")
            for i, table_path in enumerate(found_tables, 1):
                print(f"  {i}. {table_path}")
            print()
        else:
            print(f"\n✗ No K-calibration tables found in: {ms_dir}")
            print("\nTo create one, run:")
            print(f"  python -m dsa110_contimg.calibration.cli calibrate --ms {ms_path} --field 0 --refant 103 --do-k")
        return
    
    if not kcal_path:
        print("✗ Error: --kcal required when not using --find")
        return
    
    if not Path(kcal_path).exists():
        print(f"✗ Error: File not found: {kcal_path}")
        return
    
    print(f"\n{'='*70}")
    print(f"Inspecting K-calibration table: {kcal_path}")
    print(f"{'='*70}\n")
    
    try:
        with table(kcal_path, readonly=True, ack=False) as tb:
            n_rows = tb.nrows()
            print(f"Total solutions: {n_rows}")
            
            if n_rows == 0:
                print("⚠ WARNING: Table has zero solutions!")
                return
            
            colnames = tb.colnames()
            print(f"Table columns: {colnames}")
            
            if "CPARAM" not in colnames:
                print("⚠ WARNING: CPARAM column not found.")
                print("  This may not be a K-calibration table.")
                return
            
            # Read data
            cparam = tb.getcol("CPARAM")
            flags = tb.getcol("FLAG")
            antenna_ids = tb.getcol("ANTENNA1")
            
            print(f"CPARAM shape: {cparam.shape}")
            
            # Get frequency - try to find associated MS
            if ms_path and Path(ms_path).exists():
                try:
                    with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
                        ref_freqs = spw_tb.getcol("REF_FREQUENCY")
                        print(f"Found MS with {len(ref_freqs)} SPWs")
                        print(f"Reference frequencies: {ref_freqs / 1e6:.1f} MHz")
                except Exception as e:
                    print(f"⚠ Could not read frequencies from MS: {e}")
                    ref_freqs = np.array([1400e6])  # Default L-band
            else:
                ms_dir = Path(kcal_path).parent
                ms_files = list(ms_dir.glob("*.ms"))
                
                if ms_files:
                    ms_path_check = ms_files[0]
                    try:
                        with table(f"{ms_path_check}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
                            ref_freqs = spw_tb.getcol("REF_FREQUENCY")
                            print(f"Found MS with {len(ref_freqs)} SPWs")
                    except Exception:
                        ref_freqs = np.array([1400e6])
                else:
                    print("⚠ No MS found in same directory. Using default frequency (1.4 GHz)")
                    ref_freqs = np.array([1400e6])
            
            # Extract delays per antenna
            unique_ants = np.unique(antenna_ids)
            delays_per_antenna = {}
            delays_ns = []
            
            # Handle different CPARAM shapes
            if len(cparam.shape) == 3:
                # Shape: (n_rows, n_channels, n_pols)
                for i, ant_id in enumerate(unique_ants):
                    ant_mask = antenna_ids == ant_id
                    ant_indices = np.where(ant_mask)[0]
                    
                    if len(ant_indices) == 0:
                        continue
                    
                    # Use first unflagged solution
                    for idx in ant_indices:
                        if len(flags.shape) == 3:
                            if not flags[idx, 0, 0]:
                                cval = cparam[idx, 0, 0]
                                break
                        elif len(flags.shape) == 2:
                            if not flags[idx, 0]:
                                cval = cparam[idx, 0, 0]
                                break
                        else:
                            if not flags[idx]:
                                cval = cparam[idx, 0, 0]
                                break
                    else:
                        continue  # All flagged
                    
                    # Get frequency (use first SPW if multiple)
                    freq_hz = ref_freqs[0] if len(ref_freqs) > 0 else 1400e6
                    
                    # Compute delay from phase
                    phase_rad = np.angle(cval)
                    delay_sec = phase_rad / (2 * np.pi * freq_hz)
                    delay_ns = delay_sec * 1e9
                    
                    delays_per_antenna[int(ant_id)] = delay_ns
                    delays_ns.append(delay_ns)
            
            delays_ns = np.array(delays_ns)
            
            if len(delays_ns) == 0:
                print("⚠ Could not extract any delay values")
                return
            
            # Statistics
            print(f"\n{'='*70}")
            print("Delay Statistics:")
            print(f"{'='*70}\n")
            
            print(f"Number of antennas: {len(delays_ns)}")
            print(f"Median delay: {np.median(delays_ns):.3f} ns")
            print(f"Mean delay:   {np.mean(delays_ns):.3f} ns")
            print(f"Std dev:      {np.std(delays_ns):.3f} ns")
            print(f"Min delay:    {np.min(delays_ns):.3f} ns")
            print(f"Max delay:    {np.max(delays_ns):.3f} ns")
            print(f"Range:        {np.max(delays_ns) - np.min(delays_ns):.3f} ns")
            
            # Impact assessment
            print(f"\n{'='*70}")
            print("Impact Assessment:")
            print(f"{'='*70}\n")
            
            freq_center_hz = 1400e6  # L-band center
            bandwidth_hz = 200e6  # 200 MHz
            
            max_delay_sec = np.max(np.abs(delays_ns)) * 1e-9
            phase_error_rad = 2 * np.pi * max_delay_sec * bandwidth_hz
            phase_error_deg = np.degrees(phase_error_rad)
            
            print(f"Phase error across 200 MHz bandwidth:")
            print(f"  Maximum delay ({max_delay_sec*1e9:.3f} ns):")
            print(f"    → Phase error: {phase_error_deg:.1f}°")
            
            # Coherence loss
            coherence = np.abs(np.sinc(phase_error_rad / (2 * np.pi)))
            coherence_loss_percent = (1 - coherence) * 100
            
            print(f"\nCoherence Impact:")
            print(f"  Estimated coherence: {coherence:.3f}")
            print(f"  Coherence loss: {coherence_loss_percent:.1f}%")
            
            # Recommendation
            print(f"\n{'='*70}")
            print("Recommendation:")
            print(f"{'='*70}\n")
            
            delay_range = np.max(delays_ns) - np.min(delays_ns)
            
            if delay_range < 1.0:
                print("✓ Delays are very small (< 1 ns range)")
                print("  → K-calibration impact is minimal")
                print("  → However, still recommended for precision")
            elif delay_range < 10.0:
                print("⚠ Delays are moderate (1-10 ns range)")
                print("  → K-calibration is RECOMMENDED")
                print(f"  → Expected coherence loss: {coherence_loss_percent:.1f}%")
            else:
                print("✗ Delays are large (> 10 ns range)")
                print("  → K-calibration is ESSENTIAL")
                print(f"  → Significant coherence loss: {coherence_loss_percent:.1f}%")
            
            # Show top delays
            print(f"\n{'='*70}")
            print("Top 10 Antennas by Delay Magnitude:")
            print(f"{'='*70}\n")
            
            sorted_ants = sorted(
                delays_per_antenna.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:10]
            
            print(f"{'Antenna':<10} {'Delay (ns)':<15}")
            print("-" * 25)
            for ant_id, delay_ns in sorted_ants:
                print(f"{ant_id:<10} {delay_ns:>13.3f}")
            
            print(f"\n{'='*70}")
            print("Inspection Complete")
            print(f"{'='*70}\n")
            
    except Exception as e:
        print(f"✗ Error inspecting table: {e}")
        import traceback
        traceback.print_exc()

