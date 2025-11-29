"""
Temporal tracking of flagging statistics throughout the calibration pipeline.

This module captures flag states at each critical phase:
- Phase 1: After pre-calibration flagging (RFI, zeros, etc.)
- Phase 2: After calibration solve (before applycal)
- Phase 3: After calibration application (applycal)

This enables definitive diagnosis of why SPWs fail calibration by comparing
flag states across phases.

Example:
    >>> from dsa110_contimg.calibration.flagging_temporal import capture_flag_snapshot
    >>>
    >>> # After Phase 1 (pre-calibration flagging)
    >>> phase1_stats = capture_flag_snapshot(
    ...     ms_path="/path/to/data.ms",
    ...     phase="phase1_post_rfi",
    ...     refant=103
    ... )
    >>>
    >>> # After Phase 3 (post-applycal)
    >>> phase3_stats = capture_flag_snapshot(
    ...     ms_path="/path/to/data.ms",
    ...     phase="phase3_post_applycal",
    ...     refant=103
    ... )
    >>>
    >>> # Compare
    >>> diff = compare_flag_snapshots(phase1_stats, phase3_stats)
    >>> print(f"SPWs that became 100% flagged: {diff['newly_fully_flagged_spws']}")
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import casacore.tables as casatables  # type: ignore[import]
import numpy as np  # type: ignore[import]

logger = logging.getLogger(__name__)
table = casatables.table  # noqa: N816


@dataclass
class SPWFlaggingStats:
    """Flagging statistics for a single SPW at a specific point in time."""

    spw_id: int
    total_flagged_fraction: float  # Overall fraction flagged (0.0 - 1.0)
    n_rows: int  # Number of rows for this SPW
    n_channels: int  # Number of channels
    n_polarizations: int  # Number of polarizations

    # Per-channel statistics
    channel_flagged_fractions: List[float] = field(default_factory=list)  # Length = n_channels
    fully_flagged_channels: List[int] = field(
        default_factory=list
    )  # Channel IDs with 100% flagging

    # Per-antenna statistics (for reference antenna)
    refant_flagged_fraction: Optional[float] = None  # Flagging fraction for reference antenna
    refant_id: Optional[int] = None


@dataclass
class FlaggingSnapshot:
    """Complete flagging statistics for an MS at a specific point in time."""

    ms_path: str
    phase: str  # e.g., "phase1_post_rfi", "phase3_post_applycal"
    timestamp: datetime

    # Overall statistics
    total_flagged_fraction: float  # Overall fraction flagged across all data

    # Per-SPW statistics
    spw_stats: Dict[int, SPWFlaggingStats]  # spw_id -> SPWFlaggingStats

    # Metadata
    refant: Optional[int] = None
    n_spws: int = 0
    total_rows: int = 0

    # Optional: Calibration table paths (for post-solve phases)
    cal_table_paths: Optional[Dict[str, str]] = None  # e.g., {"K": "/path/to/ktable", ...}


def capture_flag_snapshot(
    ms_path: str,
    phase: str,
    refant: Optional[int] = None,
    cal_table_paths: Optional[Dict[str, str]] = None,
) -> FlaggingSnapshot:
    """Capture a complete snapshot of flagging statistics at a specific pipeline phase.

    Args:
        ms_path: Path to Measurement Set
        phase: Phase identifier (e.g., "phase1_post_rfi", "phase2_post_solve", "phase3_post_applycal")
        refant: Optional reference antenna ID for per-antenna analysis
        cal_table_paths: Optional dict of calibration table paths {"K": path, "BP": path, "G": path}

    Returns:
        FlaggingSnapshot with complete statistics

    Example:
        >>> snapshot = capture_flag_snapshot(
        ...     ms_path="/stage/data.ms",
        ...     phase="phase1_post_rfi",
        ...     refant=103
        ... )
        >>> print(f"SPW 9 flagging: {snapshot.spw_stats[9].total_flagged_fraction * 100:.1f}%")
    """
    logger.info(f"Capturing flag snapshot: phase={phase}, ms={Path(ms_path).name}")

    try:
        with table(ms_path, readonly=True) as tb:
            # Get main data
            flags = tb.getcol("FLAG")  # Shape: (n_rows, n_channels, n_pols)
            data_desc_id = tb.getcol("DATA_DESC_ID")
            antenna1 = tb.getcol("ANTENNA1")
            antenna2 = tb.getcol("ANTENNA2")

            total_rows = tb.nrows()

            # Calculate overall flagging fraction
            total_flagged = np.sum(flags)
            total_elements = flags.size
            overall_fraction = float(total_flagged / total_elements) if total_elements > 0 else 0.0

            # Get SPW mapping
            with table(f"{ms_path}/DATA_DESCRIPTION", readonly=True) as dd:
                spw_ids = dd.getcol("SPECTRAL_WINDOW_ID")

            # Get unique SPWs
            unique_ddids = np.unique(data_desc_id)
            unique_spws = [int(spw_ids[ddid]) for ddid in unique_ddids]

            # Build per-SPW statistics
            spw_stats_dict = {}

            for spw in unique_spws:
                # Get rows for this SPW
                spw_mask = np.array([spw_ids[ddid] == spw for ddid in data_desc_id])
                spw_rows = np.where(spw_mask)[0]

                if len(spw_rows) == 0:
                    continue

                spw_flags = flags[spw_rows, :, :]
                n_rows_spw, n_channels, n_pols = spw_flags.shape

                # Overall SPW flagging
                spw_total_flagged = np.sum(spw_flags)
                spw_total_elements = spw_flags.size
                spw_fraction = (
                    float(spw_total_flagged / spw_total_elements) if spw_total_elements > 0 else 0.0
                )

                # Per-channel flagging
                # Average across rows and polarizations
                channel_flagging = np.mean(spw_flags, axis=(0, 2))  # Length = n_channels
                channel_fractions = channel_flagging.tolist()

                # Find fully flagged channels
                fully_flagged = np.where(channel_flagging >= 0.999)[
                    0
                ].tolist()  # 99.9% threshold for numerical stability

                # Reference antenna statistics (if provided)
                refant_fraction = None
                if refant is not None:
                    refant_mask = (antenna1 == refant) | (antenna2 == refant)
                    combined_mask = refant_mask & spw_mask
                    refant_rows = np.where(combined_mask)[0]

                    if len(refant_rows) > 0:
                        refant_flags = flags[refant_rows, :, :]
                        refant_flagged = np.sum(refant_flags)
                        refant_elements = refant_flags.size
                        refant_fraction = (
                            float(refant_flagged / refant_elements) if refant_elements > 0 else 0.0
                        )

                # Create SPW stats object
                spw_stat = SPWFlaggingStats(
                    spw_id=spw,
                    total_flagged_fraction=spw_fraction,
                    n_rows=n_rows_spw,
                    n_channels=n_channels,
                    n_polarizations=n_pols,
                    channel_flagged_fractions=channel_fractions,
                    fully_flagged_channels=fully_flagged,
                    refant_flagged_fraction=refant_fraction,
                    refant_id=refant,
                )

                spw_stats_dict[spw] = spw_stat

            # Create snapshot
            snapshot = FlaggingSnapshot(
                ms_path=ms_path,
                phase=phase,
                timestamp=datetime.now(),
                total_flagged_fraction=overall_fraction,
                spw_stats=spw_stats_dict,
                refant=refant,
                n_spws=len(unique_spws),
                total_rows=total_rows,
                cal_table_paths=cal_table_paths,
            )

            logger.info(
                f":check_mark: Captured flag snapshot: {len(unique_spws)} SPWs, "
                f"overall {overall_fraction * 100:.1f}% flagged"
            )

            return snapshot

    except Exception as e:
        logger.error(f"Failed to capture flag snapshot: {e}")
        raise


def compare_flag_snapshots(
    before: FlaggingSnapshot,
    after: FlaggingSnapshot,
) -> Dict:
    """Compare two flag snapshots to identify changes.

    Args:
        before: Earlier snapshot (e.g., phase1_post_rfi)
        after: Later snapshot (e.g., phase3_post_applycal)

    Returns:
        Dict with comparison results including:
        - newly_fully_flagged_spws: SPWs that became 100% flagged
        - flag_increase_per_spw: Flagging increase for each SPW
        - newly_flagged_channels: Channels that became fully flagged

    Example:
        >>> diff = compare_flag_snapshots(phase1, phase3)
        >>> if diff['newly_fully_flagged_spws']:
        ...     print(f"SPWs that became fully flagged: {diff['newly_fully_flagged_spws']}")
    """
    logger.info(f"Comparing snapshots: {before.phase} → {after.phase}")

    result = {
        "before_phase": before.phase,
        "after_phase": after.phase,
        "before_timestamp": before.timestamp,
        "after_timestamp": after.timestamp,
        "newly_fully_flagged_spws": [],
        "flag_increase_per_spw": {},
        "newly_flagged_channels": {},
        "refant_flag_changes": {},
    }

    # Find SPWs that became fully flagged
    for spw_id in before.spw_stats:
        if spw_id not in after.spw_stats:
            continue

        before_stat = before.spw_stats[spw_id]
        after_stat = after.spw_stats[spw_id]

        # Check if became fully flagged
        if (
            before_stat.total_flagged_fraction < 0.999
            and after_stat.total_flagged_fraction >= 0.999
        ):
            result["newly_fully_flagged_spws"].append(spw_id)

        # Calculate flagging increase
        increase = after_stat.total_flagged_fraction - before_stat.total_flagged_fraction
        result["flag_increase_per_spw"][spw_id] = {
            "before": before_stat.total_flagged_fraction,
            "after": after_stat.total_flagged_fraction,
            "increase": increase,
            "increase_pct": increase * 100,
        }

        # Check newly flagged channels
        before_flagged = set(before_stat.fully_flagged_channels)
        after_flagged = set(after_stat.fully_flagged_channels)
        newly_flagged = after_flagged - before_flagged

        if newly_flagged:
            result["newly_flagged_channels"][spw_id] = sorted(list(newly_flagged))

        # Reference antenna changes
        if (
            before_stat.refant_flagged_fraction is not None
            and after_stat.refant_flagged_fraction is not None
        ):
            refant_increase = (
                after_stat.refant_flagged_fraction - before_stat.refant_flagged_fraction
            )
            result["refant_flag_changes"][spw_id] = {
                "before": before_stat.refant_flagged_fraction,
                "after": after_stat.refant_flagged_fraction,
                "increase": refant_increase,
                "increase_pct": refant_increase * 100,
            }

    return result


def diagnose_spw_failure(
    phase1_snapshot: FlaggingSnapshot,
    phase3_snapshot: FlaggingSnapshot,
    failed_spw: int,
) -> Dict:
    """Provide definitive diagnosis of why a specific SPW failed calibration.

    Args:
        phase1_snapshot: Snapshot after pre-calibration flagging
        phase3_snapshot: Snapshot after applycal
        failed_spw: SPW ID that failed calibration

    Returns:
        Dict with definitive diagnosis including:
        - definitive_cause: String description of root cause
        - phase1_flagging: Pre-calibration flagging percentage
        - phase3_flagging: Post-applycal flagging percentage
        - refant_phase1: Reference antenna flagging pre-calibration
        - became_fully_flagged_in_applycal: Boolean

    Example:
        >>> diagnosis = diagnose_spw_failure(phase1, phase3, failed_spw=9)
        >>> print(diagnosis['definitive_cause'])
        "Reference antenna 103 was 85.2% flagged pre-calibration, insufficient for calibration solve"
    """
    result = {
        "spw_id": failed_spw,
        "definitive_cause": "Unknown",
        "phase1_flagging_pct": None,
        "phase3_flagging_pct": None,
        "refant_phase1_pct": None,
        "refant_phase3_pct": None,
        "became_fully_flagged_in_applycal": False,
    }

    # Get phase 1 stats (pre-calibration)
    if failed_spw not in phase1_snapshot.spw_stats:
        result["definitive_cause"] = f"SPW {failed_spw} not found in Phase 1 snapshot"
        return result

    phase1_stat = phase1_snapshot.spw_stats[failed_spw]
    result["phase1_flagging_pct"] = phase1_stat.total_flagged_fraction * 100
    result["refant_phase1_pct"] = (
        phase1_stat.refant_flagged_fraction * 100
        if phase1_stat.refant_flagged_fraction is not None
        else None
    )

    # Get phase 3 stats (post-applycal)
    if failed_spw in phase3_snapshot.spw_stats:
        phase3_stat = phase3_snapshot.spw_stats[failed_spw]
        result["phase3_flagging_pct"] = phase3_stat.total_flagged_fraction * 100
        result["refant_phase3_pct"] = (
            phase3_stat.refant_flagged_fraction * 100
            if phase3_stat.refant_flagged_fraction is not None
            else None
        )

        # Check if became fully flagged during applycal
        if (
            phase1_stat.total_flagged_fraction < 0.999
            and phase3_stat.total_flagged_fraction >= 0.999
        ):
            result["became_fully_flagged_in_applycal"] = True

    # Determine definitive cause
    refant_id = phase1_stat.refant_id or phase1_snapshot.refant

    if result["refant_phase1_pct"] is not None and result["refant_phase1_pct"] >= 99.9:
        result["definitive_cause"] = (
            f"Reference antenna {refant_id} was 100% flagged pre-calibration in SPW {failed_spw}, "
            f"making calibration solve impossible"
        )
    elif result["refant_phase1_pct"] is not None and result["refant_phase1_pct"] >= 90.0:
        result["definitive_cause"] = (
            f"Reference antenna {refant_id} was {result['refant_phase1_pct']:.1f}% flagged pre-calibration "
            f"in SPW {failed_spw}, insufficient unflagged data for calibration solve"
        )
    elif result["phase1_flagging_pct"] >= 99.9:
        result["definitive_cause"] = (
            f"SPW {failed_spw} was 100% flagged pre-calibration (all antennas), "
            f"making calibration solve impossible"
        )
    elif result["phase1_flagging_pct"] >= 90.0:
        result["definitive_cause"] = (
            f"SPW {failed_spw} was {result['phase1_flagging_pct']:.1f}% flagged pre-calibration, "
            f"insufficient unflagged data for calibration solve"
        )
    elif result["became_fully_flagged_in_applycal"]:
        result["definitive_cause"] = (
            f"SPW {failed_spw} was {result['phase1_flagging_pct']:.1f}% flagged pre-calibration "
            f"(not 100%), but calibration solve failed due to insufficient S/N or other factors. "
            f"CASA applycal then flagged remaining data, resulting in 100% flagging."
        )
    else:
        result["definitive_cause"] = (
            f"SPW {failed_spw} had {result['phase1_flagging_pct']:.1f}% pre-calibration flagging. "
            f"Calibration failure cause unclear - may be due to low S/N, RFI patterns, "
            f"or other factors not directly related to flagging percentage."
        )

    return result


def format_snapshot_summary(snapshot: FlaggingSnapshot) -> str:
    """Format a human-readable summary of a flagging snapshot.

    Args:
        snapshot: FlaggingSnapshot to summarize

    Returns:
        Formatted string summary
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"Flagging Snapshot: {snapshot.phase}")
    lines.append("=" * 80)
    lines.append(f"MS: {Path(snapshot.ms_path).name}")
    lines.append(f"Timestamp: {snapshot.timestamp.isoformat()}")
    lines.append(f"Overall flagging: {snapshot.total_flagged_fraction * 100:.1f}%")
    lines.append(f"Number of SPWs: {snapshot.n_spws}")
    lines.append(f"Total rows: {snapshot.total_rows}")
    if snapshot.refant is not None:
        lines.append(f"Reference antenna: {snapshot.refant}")
    lines.append("")
    lines.append("Per-SPW Statistics:")
    lines.append("-" * 80)

    for spw_id in sorted(snapshot.spw_stats.keys()):
        stat = snapshot.spw_stats[spw_id]
        lines.append(f"SPW {spw_id:2d}: {stat.total_flagged_fraction * 100:5.1f}% flagged")

        if stat.refant_flagged_fraction is not None:
            lines.append(
                f"         Refant {stat.refant_id}: {stat.refant_flagged_fraction * 100:5.1f}% flagged"
            )

        if stat.fully_flagged_channels:
            if len(stat.fully_flagged_channels) <= 5:
                lines.append(f"         Fully flagged channels: {stat.fully_flagged_channels}")
            else:
                lines.append(
                    f"         Fully flagged channels: {len(stat.fully_flagged_channels)} "
                    f"(e.g., {stat.fully_flagged_channels[:5]}...)"
                )

    lines.append("=" * 80)
    return "\n".join(lines)


def format_comparison_summary(comparison: Dict) -> str:
    """Format a human-readable summary of snapshot comparison.

    Args:
        comparison: Result from compare_flag_snapshots()

    Returns:
        Formatted string summary
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"Flagging Comparison: {comparison['before_phase']} → {comparison['after_phase']}")
    lines.append("=" * 80)
    lines.append("")

    if comparison["newly_fully_flagged_spws"]:
        lines.append(f"SPWs that became 100% flagged: {comparison['newly_fully_flagged_spws']}")
        lines.append("")

    lines.append("Flagging changes per SPW:")
    lines.append("-" * 80)

    for spw_id in sorted(comparison["flag_increase_per_spw"].keys()):
        change = comparison["flag_increase_per_spw"][spw_id]
        lines.append(
            f"SPW {spw_id:2d}: {change['before'] * 100:5.1f}% → {change['after'] * 100:5.1f}% "
            f"(+{change['increase_pct']:5.1f}%)"
        )

        if spw_id in comparison["refant_flag_changes"]:
            refant_change = comparison["refant_flag_changes"][spw_id]
            lines.append(
                f"         Refant: {refant_change['before'] * 100:5.1f}% → {refant_change['after'] * 100:5.1f}% "
                f"(+{refant_change['increase_pct']:5.1f}%)"
            )

        if spw_id in comparison["newly_flagged_channels"]:
            newly_flagged = comparison["newly_flagged_channels"][spw_id]
            if len(newly_flagged) <= 5:
                lines.append(f"         Newly flagged channels: {newly_flagged}")
            else:
                lines.append(
                    f"         Newly flagged channels: {len(newly_flagged)} (e.g., {newly_flagged[:5]}...)"
                )

    lines.append("=" * 80)
    return "\n".join(lines)
