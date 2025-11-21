"""
MS quality validation for DSA-110 continuum imaging pipeline.

Performs comprehensive checks on Measurement Sets to ensure data quality
before calibration and imaging.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

import casacore.tables as casatables  # type: ignore
import numpy as np

table = casatables.table  # noqa: N816

from dsa110_contimg.qa.base import ValidationInputError

logger = logging.getLogger(__name__)


@dataclass
class MSQualityMetrics:
    """Quality metrics for a Measurement Set."""

    # Basic properties
    ms_path: str
    ms_size_gb: float
    n_rows: int
    n_antennas: int
    n_baselines: int
    n_channels: int
    n_spws: int
    n_fields: int
    n_scans: int
    time_range_seconds: float

    # Data quality
    data_column_present: bool
    model_data_present: bool
    corrected_data_present: bool
    weight_spectrum_present: bool

    # Data statistics
    fraction_flagged: float
    fraction_zeros: float
    median_amplitude: float
    rms_amplitude: float
    amplitude_range: Tuple[float, float]

    # UVW validity
    uvw_present: bool
    uvw_all_zeros: bool
    median_uv_distance: float

    # Quality flags
    has_critical_issues: bool = False
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
            "ms_path": self.ms_path,
            "ms_size_gb": self.ms_size_gb,
            "n_rows": self.n_rows,
            "n_antennas": self.n_antennas,
            "n_baselines": self.n_baselines,
            "n_channels": self.n_channels,
            "n_spws": self.n_spws,
            "n_fields": self.n_fields,
            "n_scans": self.n_scans,
            "time_range_seconds": self.time_range_seconds,
            "data_quality": {
                "data_column_present": self.data_column_present,
                "model_data_present": self.model_data_present,
                "corrected_data_present": self.corrected_data_present,
                "weight_spectrum_present": self.weight_spectrum_present,
                "fraction_flagged": self.fraction_flagged,
                "fraction_zeros": self.fraction_zeros,
                "median_amplitude": self.median_amplitude,
                "rms_amplitude": self.rms_amplitude,
                "amplitude_range": self.amplitude_range,
            },
            "uvw": {
                "present": self.uvw_present,
                "all_zeros": self.uvw_all_zeros,
                "median_uv_distance": self.median_uv_distance,
            },
            "quality": {
                "has_critical_issues": self.has_critical_issues,
                "has_warnings": self.has_warnings,
                "issues": self.issues,
                "warnings": self.warnings,
            },
        }


def validate_ms_quality(
    ms_path: str,
    check_data_column: str = "DATA",
    sample_fraction: float = 0.1,
) -> MSQualityMetrics:
    """
    Perform comprehensive quality validation on a Measurement Set.

    Args:
        ms_path: Path to MS
        check_data_column: Which data column to check (DATA, CORRECTED_DATA, MODEL_DATA)
        sample_fraction: Fraction of data to sample for statistics (0.1 = 10%)

    Returns:
        MSQualityMetrics object with validation results

    Raises:
        ValidationInputError: If MS path is invalid or MS not found
    """
    logger.info(f"Validating MS quality: {ms_path}")

    if not os.path.exists(ms_path):
        raise ValidationInputError(f"MS not found: {ms_path}")

    # Get MS size
    ms_size_bytes = sum(
        os.path.getsize(os.path.join(dirpath, filename))
        for dirpath, dirnames, filenames in os.walk(ms_path)
        for filename in filenames
    )
    ms_size_gb = ms_size_bytes / (1024**3)

    issues = []
    warnings = []

    try:
        with table(ms_path, readonly=True, ack=False) as tb:
            # Basic properties
            n_rows = tb.nrows()

            if n_rows == 0:
                issues.append("MS has zero rows")

            # Get column names
            colnames = tb.colnames()
            data_column_present = check_data_column in colnames
            model_data_present = "MODEL_DATA" in colnames
            corrected_data_present = "CORRECTED_DATA" in colnames
            weight_spectrum_present = "WEIGHT_SPECTRUM" in colnames

            if not data_column_present:
                issues.append(f"Required column {check_data_column} not present")

            # Get UVW info
            uvw_present = "UVW" in colnames
            uvw_all_zeros = False
            median_uv_distance = 0.0

            if uvw_present and n_rows > 0:
                # Sample UVW
                sample_size = max(100, int(n_rows * sample_fraction))
                indices = np.linspace(0, n_rows - 1, sample_size, dtype=int)
                uvw_sample = tb.getcol("UVW", startrow=indices[0], nrow=len(indices))
                uv_distances = np.sqrt(uvw_sample[0] ** 2 + uvw_sample[1] ** 2)
                median_uv_distance = float(np.median(uv_distances))

                if np.all(np.abs(uvw_sample) < 1e-10):
                    issues.append("UVW coordinates are all zeros")
                    uvw_all_zeros = True
            elif not uvw_present:
                issues.append("UVW column not present")

            # Get data statistics
            fraction_flagged = 0.0
            fraction_zeros = 0.0
            median_amplitude = 0.0
            rms_amplitude = 0.0
            amplitude_range = (0.0, 0.0)

            if data_column_present and n_rows > 0:
                # Sample data for statistics
                sample_size = max(100, int(n_rows * sample_fraction))
                indices = np.linspace(0, n_rows - 1, sample_size, dtype=int)

                try:
                    data_sample = tb.getcol(
                        check_data_column, startrow=indices[0], nrow=len(indices)
                    )
                    flags_sample = tb.getcol("FLAG", startrow=indices[0], nrow=len(indices))

                    # Compute amplitudes
                    amps = np.abs(data_sample)

                    # Flag statistics
                    fraction_flagged = float(np.mean(flags_sample))

                    # Zero fraction (in unflagged data)
                    unflagged_amps = amps[~flags_sample]
                    if len(unflagged_amps) > 0:
                        fraction_zeros = float(np.mean(unflagged_amps < 1e-10))

                        # Amplitude statistics
                        nonzero_amps = unflagged_amps[unflagged_amps > 0]
                        if len(nonzero_amps) > 0:
                            median_amplitude = float(np.median(nonzero_amps))
                            rms_amplitude = float(np.sqrt(np.mean(nonzero_amps**2)))
                            amplitude_range = (
                                float(np.min(nonzero_amps)),
                                float(np.max(nonzero_amps)),
                            )
                        else:
                            warnings.append("All unflagged amplitudes are zero")
                    else:
                        warnings.append("All data is flagged")

                except Exception as e:
                    warnings.append(f"Could not compute data statistics: {e}")

            # Quality checks
            if fraction_flagged > 0.5:
                warnings.append(f"High fraction of flagged data: {fraction_flagged:.1%}")

            if fraction_zeros > 0.3:
                warnings.append(f"High fraction of zero amplitudes: {fraction_zeros:.1%}")

            if median_amplitude > 0 and (amplitude_range[1] / amplitude_range[0] > 1000):
                warnings.append(
                    f"Very large amplitude dynamic range: {amplitude_range[1] / amplitude_range[0]:.1f}x"
                )

    except Exception as e:
        logger.error(f"Error validating MS: {e}")
        issues.append(f"Exception during validation: {e}")

    # Get metadata from subtables
    try:
        with table(f"{ms_path}::ANTENNA", readonly=True, ack=False) as ant_tb:
            n_antennas = ant_tb.nrows()

        with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True, ack=False) as spw_tb:
            n_spws = spw_tb.nrows()
            n_channels = int(spw_tb.getcol("NUM_CHAN")[0]) if spw_tb.nrows() > 0 else 0

        with table(f"{ms_path}::FIELD", readonly=True, ack=False) as field_tb:
            n_fields = field_tb.nrows()

        with table(ms_path, readonly=True, ack=False) as tb:
            if n_rows > 0:
                scan_ids = tb.getcol("SCAN_NUMBER")
                n_scans = len(np.unique(scan_ids))

                times = tb.getcol("TIME")
                time_range_seconds = float(np.max(times) - np.min(times))
            else:
                n_scans = 0
                time_range_seconds = 0.0

        n_baselines = (n_antennas * (n_antennas - 1)) // 2 if n_antennas > 0 else 0

    except Exception as e:
        logger.warning(f"Could not read MS metadata: {e}")
        n_antennas = 0
        n_spws = 0
        n_channels = 0
        n_fields = 0
        n_scans = 0
        n_baselines = 0
        time_range_seconds = 0.0
        warnings.append(f"Could not read metadata: {e}")

    # Create metrics object
    metrics = MSQualityMetrics(
        ms_path=ms_path,
        ms_size_gb=ms_size_gb,
        n_rows=n_rows,
        n_antennas=n_antennas,
        n_baselines=n_baselines,
        n_channels=n_channels,
        n_spws=n_spws,
        n_fields=n_fields,
        n_scans=n_scans,
        time_range_seconds=time_range_seconds,
        data_column_present=data_column_present,
        model_data_present=model_data_present,
        corrected_data_present=corrected_data_present,
        weight_spectrum_present=weight_spectrum_present,
        fraction_flagged=fraction_flagged,
        fraction_zeros=fraction_zeros,
        median_amplitude=median_amplitude,
        rms_amplitude=rms_amplitude,
        amplitude_range=amplitude_range,
        uvw_present=uvw_present,
        uvw_all_zeros=uvw_all_zeros,
        median_uv_distance=median_uv_distance,
        has_critical_issues=len(issues) > 0,
        has_warnings=len(warnings) > 0,
        issues=issues,
        warnings=warnings,
    )

    # Log results
    if metrics.has_critical_issues:
        logger.error(f"MS has critical issues: {', '.join(issues)}")
    if metrics.has_warnings:
        logger.warning(f"MS has warnings: {', '.join(warnings)}")
    if not metrics.has_critical_issues and not metrics.has_warnings:
        logger.info(f"MS passed quality checks: {ms_path}")

    return metrics


def quick_ms_check(ms_path: str) -> Tuple[bool, str]:
    """
    Quick sanity check for MS quality.

    Args:
        ms_path: Path to MS

    Returns:
        (passed, message) tuple

    Note: This function maintains backward compatibility by returning a tuple.
    For new code, prefer using validate_ms_quality() which raises exceptions.
    """
    try:
        if not os.path.exists(ms_path):
            return False, "MS does not exist"

        with table(ms_path, readonly=True, ack=False) as tb:
            n_rows = tb.nrows()
            if n_rows == 0:
                return False, "MS has zero rows"

            colnames = tb.colnames()
            if "DATA" not in colnames:
                return False, "DATA column missing"

            if "UVW" not in colnames:
                return False, "UVW column missing"

        return True, "MS passed quick check"

    except ValidationInputError as e:
        return False, str(e)
    except Exception as e:
        logger.exception(f"Exception during quick MS check: {e}")
        return False, f"Exception during check: {e}"
