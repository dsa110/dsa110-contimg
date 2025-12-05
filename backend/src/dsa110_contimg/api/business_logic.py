"""
Shared business logic functions for the API layer.

This module centralizes business logic that was previously duplicated across
repository classes. Functions here are pure/stateless and operate on records
or simple data types.

Functions:
    stage_to_qa_grade: Convert pipeline stage/status to QA grade
    generate_qa_summary: Create human-readable QA summary from metrics
    generate_run_id: Generate job run ID from MS path
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .repositories import ImageRecord, MSRecord


def stage_to_qa_grade(stage: Optional[str], status: Optional[str] = None) -> str:
    """Convert pipeline stage/status to QA grade.

    Maps pipeline processing stages to quality grades for display.

    Args:
        stage: Pipeline stage (e.g., 'imaged', 'calibrated', 'mosaicked')
        status: Optional status string (currently unused, reserved for future)

    Returns:
        QA grade: 'good', 'warn', or 'fail'

    Examples:
        >>> stage_to_qa_grade('imaged')
        'good'
        >>> stage_to_qa_grade('calibrated')
        'warn'
        >>> stage_to_qa_grade(None)
        'fail'
    """
    if not stage:
        return "fail"
    if stage in ["imaged", "mosaicked", "cataloged"]:
        return "good"
    if stage in ["calibrated"]:
        return "warn"
    return "fail"


def generate_image_qa_summary(record: "ImageRecord") -> str:
    """Generate QA summary string from image metadata.

    Creates a human-readable summary of key image quality metrics.

    Args:
        record: ImageRecord with quality metrics

    Returns:
        Comma-separated summary string, e.g. "RMS 1.23 mJy, DR 500, Beam 5.0\""
    """
    parts = []
    if record.noise_jy:
        parts.append(f"RMS {record.noise_jy * 1000:.2f} mJy")
    if record.dynamic_range:
        parts.append(f"DR {record.dynamic_range:.0f}")
    if record.beam_major_arcsec:
        parts.append(f'Beam {record.beam_major_arcsec:.1f}"')
    return ", ".join(parts) if parts else "No QA metrics available"


def generate_ms_qa_summary(record: "MSRecord") -> str:
    """Generate QA summary string from MS metadata.

    Creates a human-readable summary of MS calibration status.

    Args:
        record: MSRecord with calibration info

    Returns:
        Comma-separated summary string, e.g. "Calibrated, Stage: imaged"
    """
    parts = []
    if record.cal_applied:
        parts.append("Calibrated")
    if record.stage:
        parts.append(f"Stage: {record.stage}")
    return ", ".join(parts) if parts else "No QA info"


def generate_run_id(ms_path: str) -> str:
    """Generate a job run ID from MS path.

    Extracts timestamp from MS filename to create a unique run identifier.

    Args:
        ms_path: Path to measurement set file

    Returns:
        Run ID in format "job-YYYY-MM-DD-HHMMSS" or "job-{basename}"

    Examples:
        >>> generate_run_id("/data/2024-01-15T12:30:00.ms")
        'job-2024-01-15-123000'
        >>> generate_run_id("/data/observation.ms")
        'job-observation'
    """
    basename = Path(ms_path).stem
    if "T" in basename:
        timestamp_part = (
            basename.split("T")[0] + "-" + basename.split("T")[1].replace(":", "").split(".")[0]
        )
        return f"job-{timestamp_part}"
    return f"job-{basename}"
