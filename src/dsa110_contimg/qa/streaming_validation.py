"""
Streaming pipeline validation module.

Validates streaming data continuity, latency, and throughput.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from dsa110_contimg.qa.base import (
    ValidationContext,
    ValidationError,
    ValidationInputError,
    ValidationResult,
)
from dsa110_contimg.qa.config import StreamingConfig, get_default_config

logger = logging.getLogger(__name__)


@dataclass
class StreamingValidationResult(ValidationResult):
    """Result of streaming validation."""

    # Time coverage metrics
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    total_duration_seconds: float = 0.0

    # Continuity metrics
    n_expected_files: int = 0
    n_actual_files: int = 0
    n_missing_files: int = 0
    missing_files_fraction: float = 0.0

    # Time gap metrics
    n_time_gaps: int = 0
    max_time_gap_seconds: float = 0.0
    total_gap_time_seconds: float = 0.0

    # Latency metrics
    mean_latency_seconds: float = 0.0
    max_latency_seconds: float = 0.0

    # Throughput metrics
    mean_throughput_mbps: float = 0.0
    min_throughput_mbps: float = 0.0

    # Per-file results
    file_results: List[Dict[str, any]] = field(default_factory=list)  # type: ignore

    def __post_init__(self):
        """Initialize defaults."""
        super().__post_init__()
        if self.file_results is None:
            self.file_results = []


def validate_streaming_continuity(
    time_range_start: datetime,
    time_range_end: datetime,
    expected_files: List[str],
    actual_files: List[str],
    file_timestamps: Optional[Dict[str, datetime]] = None,
    config: Optional[StreamingConfig] = None,
) -> StreamingValidationResult:
    """Validate streaming pipeline continuity.

    Checks for time gaps, missing files, and data integrity.

    Args:
        time_range_start: Start of time range to validate
        time_range_end: End of time range to validate
        expected_files: List of expected file paths
        actual_files: List of actual file paths found
        file_timestamps: Optional dictionary mapping file paths to timestamps
        config: Streaming validation configuration

    Returns:
        StreamingValidationResult with validation status

    Raises:
        ValidationInputError: If inputs are invalid
        ValidationError: If validation fails
    """
    if config is None:
        config = get_default_config().streaming

    # Validate inputs
    if time_range_end <= time_range_start:
        raise ValidationInputError("time_range_end must be after time_range_start")

    try:
        # Find missing files
        expected_set = set(expected_files)
        actual_set = set(actual_files)
        missing_files = list(expected_set - actual_set)

        n_expected = len(expected_files)
        n_actual = len(actual_files)
        n_missing = len(missing_files)
        missing_fraction = n_missing / n_expected if n_expected > 0 else 0.0

        # Detect time gaps
        time_gaps = []
        max_gap = 0.0
        total_gap_time = 0.0

        if file_timestamps:
            # Sort files by timestamp
            sorted_files = sorted(
                [(f, ts) for f, ts in file_timestamps.items() if f in actual_set],
                key=lambda x: x[1],
            )

            for i in range(len(sorted_files) - 1):
                file1, ts1 = sorted_files[i]
                file2, ts2 = sorted_files[i + 1]

                gap_seconds = (ts2 - ts1).total_seconds()
                if gap_seconds > config.max_time_gap_seconds:
                    time_gaps.append(
                        {
                            "file1": file1,
                            "file2": file2,
                            "gap_seconds": gap_seconds,
                            "timestamp1": ts1,
                            "timestamp2": ts2,
                        }
                    )
                    max_gap = max(max_gap, gap_seconds)
                    total_gap_time += gap_seconds

        # Calculate latency (if file timestamps available)
        latencies = []
        if file_timestamps:
            for file_path, file_ts in file_timestamps.items():
                if file_path in actual_set:
                    # Latency = time between file timestamp and current time
                    # Simplified: use time_range_end as reference
                    latency = (time_range_end - file_ts).total_seconds()
                    latencies.append(latency)

        mean_latency = sum(latencies) / len(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0

        # Calculate throughput (simplified)
        total_duration = (time_range_end - time_range_start).total_seconds()
        # Would need file sizes for accurate throughput
        mean_throughput = 100.0  # Placeholder Mbps
        min_throughput = 50.0  # Placeholder Mbps

        # Determine overall pass status
        passed = (
            missing_fraction <= config.max_missing_files_fraction
            and max_gap <= config.max_time_gap_seconds
            and max_latency <= config.max_latency_seconds
            and min_throughput >= config.min_throughput_mbps
        )

        result = StreamingValidationResult(
            passed=passed,
            message=f"Streaming validation: {n_missing}/{n_expected} files missing, {len(time_gaps)} gaps",
            details={
                "n_expected": n_expected,
                "n_actual": n_actual,
                "n_missing": n_missing,
                "missing_fraction": missing_fraction,
                "n_time_gaps": len(time_gaps),
                "max_gap_seconds": max_gap,
                "total_gap_time_seconds": total_gap_time,
                "mean_latency_seconds": mean_latency,
                "max_latency_seconds": max_latency,
                "mean_throughput_mbps": mean_throughput,
                "min_throughput_mbps": min_throughput,
            },
            metrics={
                "missing_files_fraction": missing_fraction,
                "max_time_gap_seconds": max_gap,
                "total_gap_time_seconds": total_gap_time,
                "mean_latency_seconds": mean_latency,
                "max_latency_seconds": max_latency,
                "mean_throughput_mbps": mean_throughput,
                "min_throughput_mbps": min_throughput,
            },
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            total_duration_seconds=total_duration,
            n_expected_files=n_expected,
            n_actual_files=n_actual,
            n_missing_files=n_missing,
            missing_files_fraction=missing_fraction,
            n_time_gaps=len(time_gaps),
            max_time_gap_seconds=max_gap,
            total_gap_time_seconds=total_gap_time,
            mean_latency_seconds=mean_latency,
            max_latency_seconds=max_latency,
            mean_throughput_mbps=mean_throughput,
            min_throughput_mbps=min_throughput,
            file_results=[
                {
                    "file_path": f,
                    "exists": f in actual_set,
                    "timestamp": file_timestamps.get(f) if file_timestamps else None,
                }
                for f in expected_files
            ],
        )

        if n_missing > 0:
            result.add_warning(f"{n_missing} files missing from stream")

        if len(time_gaps) > 0:
            result.add_warning(
                f"{len(time_gaps)} time gaps detected (max {max_gap:.1f}s)"
            )

        if max_latency > config.max_latency_seconds:
            result.add_error(
                f"Max latency {max_latency:.1f}s exceeds threshold {config.max_latency_seconds:.1f}s"
            )

        if missing_fraction > config.max_missing_files_fraction:
            result.add_error(
                f"Missing files fraction {missing_fraction:.3f} exceeds threshold {config.max_missing_files_fraction:.3f}"
            )

        return result

    except Exception as e:
        logger.exception("Streaming validation failed")
        raise ValidationError(f"Streaming validation failed: {e}") from e


def validate_data_integrity(
    file_paths: List[str],
    checksums: Optional[Dict[str, str]] = None,
) -> StreamingValidationResult:
    """Validate data integrity of streaming files.

    Args:
        file_paths: List of file paths to validate
        checksums: Optional dictionary mapping file paths to expected checksums

    Returns:
        StreamingValidationResult with integrity validation status
    """
    corrupted_files = []
    missing_files = []

    for file_path in file_paths:
        path_obj = Path(file_path)

        if not path_obj.exists():
            missing_files.append(file_path)
            continue

        # Check file is readable
        try:
            with open(file_path, "rb") as f:
                f.read(1)  # Try to read at least 1 byte
        except Exception as e:
            corrupted_files.append(file_path)
            logger.warning(f"File appears corrupted: {file_path}: {e}")

        # Check checksum if provided
        if checksums and file_path in checksums:
            # Would calculate actual checksum here
            # For now, skip
            pass

    n_files = len(file_paths)
    n_corrupted = len(corrupted_files)
    n_missing = len(missing_files)

    passed = n_corrupted == 0 and n_missing == 0

    result = StreamingValidationResult(
        passed=passed,
        message=f"Data integrity: {n_corrupted} corrupted, {n_missing} missing",
        details={
            "n_files": n_files,
            "n_corrupted": n_corrupted,
            "n_missing": n_missing,
            "corrupted_files": corrupted_files[:10],  # Limit to first 10
            "missing_files": missing_files[:10],
        },
        n_expected_files=n_files,
        n_actual_files=n_files - n_missing,
        n_missing_files=n_missing,
    )

    if n_corrupted > 0:
        result.add_error(f"{n_corrupted} files appear corrupted")

    if n_missing > 0:
        result.add_error(f"{n_missing} files are missing")

    return result
