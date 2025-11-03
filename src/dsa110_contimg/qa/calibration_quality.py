"""
Calibration quality assessment for DSA-110 continuum imaging pipeline.

Evaluates the quality of CASA calibration tables and applied calibration solutions.
"""

import logging
import numpy as np
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from casacore.tables import table

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
                    
                    # Phase statistics
                    phases_rad = np.angle(unflagged_gains)
                    phases_deg = np.degrees(phases_rad)
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

