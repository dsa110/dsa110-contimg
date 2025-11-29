#!/usr/bin/env python3
"""
Test script to compare AOFlagger vs CASA tfcrop+rflag RFI flagging backends.

This test compares:
1. Execution time (efficiency)
2. Flagging statistics (how much data flagged)
3. Per-SPW flagging patterns
4. Calibration success rates (effectiveness)
5. Final image quality metrics (if full calibration+imaging run)

Usage:
    python test_rfi_backend_comparison.py /path/to/test.ms --refant 103
    python test_rfi_backend_comparison.py /path/to/test.ms --refant 103 --full-pipeline
"""

import argparse
import json
import logging
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class FlaggingStats:
    """Statistics from flagging operation."""

    backend: str
    total_flagged_fraction: float
    execution_time_sec: float
    per_spw_flagging: Dict[int, float]
    fully_flagged_spws: List[int]
    memory_usage_mb: Optional[float] = None


@dataclass
class CalibrationStats:
    """Statistics from calibration operation."""

    backend: str
    success: bool
    execution_time_sec: float
    failed_spws: List[int]
    succeeded_spws: List[int]
    total_spws: int


@dataclass
class ComparisonResults:
    """Complete comparison results."""

    test_ms: str
    timestamp: str
    aoflagger_flagging: FlaggingStats
    casa_flagging: FlaggingStats
    aoflagger_calibration: Optional[CalibrationStats] = None
    casa_calibration: Optional[CalibrationStats] = None
    notes: str = ""


def get_ms_flagging_stats(ms_path: str) -> Tuple[float, Dict[int, float], List[int]]:
    """Get flagging statistics from an MS.

    Args:
        ms_path: Path to Measurement Set

    Returns:
        Tuple of (total_flagged_fraction, per_spw_flagging_dict, fully_flagged_spws)
    """
    try:
        from casacore import tables
    except ImportError:
        logger.error("casacore-python not available. Install with: pip install python-casacore")
        raise

    with tables.table(ms_path, readonly=True, ack=False) as tb:
        flags = tb.getcol("FLAG")
        # Overall flagging fraction
        total_flagged = np.sum(flags) / flags.size

    # Per-SPW flagging
    with tables.table(ms_path, readonly=True, ack=False) as tb:
        spws = tb.getcol("DATA_DESC_ID")
        flags = tb.getcol("FLAG")

    unique_spws = np.unique(spws)
    per_spw = {}
    fully_flagged = []

    for spw in unique_spws:
        spw_mask = spws == spw
        spw_flags = flags[spw_mask]
        spw_frac = np.sum(spw_flags) / spw_flags.size
        per_spw[int(spw)] = float(spw_frac)

        if spw_frac >= 0.9999:  # Consider 100% flagged
            fully_flagged.append(int(spw))

    return float(total_flagged), per_spw, fully_flagged


def copy_ms(source: str, dest: str) -> None:
    """Copy MS directory tree.

    Args:
        source: Source MS path
        dest: Destination MS path
    """
    logger.info(f"Copying MS: {source} -> {dest}")
    if Path(dest).exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)


def reset_ms_flags(ms_path: str) -> None:
    """Reset all flags in MS to False.

    Args:
        ms_path: Path to Measurement Set
    """
    from dsa110_contimg.calibration.flagging import reset_flags

    logger.info(f"Resetting flags in {ms_path}")
    reset_flags(ms_path)


def run_flagging_backend(
    ms_path: str,
    backend: str,
    aoflagger_path: Optional[str] = None,
    strategy: Optional[str] = None,
) -> FlaggingStats:
    """Run flagging with specified backend and collect statistics.

    Args:
        ms_path: Path to Measurement Set
        backend: "aoflagger" or "casa"
        aoflagger_path: Path to aoflagger executable (for AOFlagger backend)
        strategy: Path to strategy file (for AOFlagger backend)

    Returns:
        FlaggingStats with timing and flagging statistics
    """
    from dsa110_contimg.calibration.flagging import flag_rfi, flag_zeros

    logger.info("=" * 80)
    logger.info(f"Testing backend: {backend.upper()}")
    logger.info("=" * 80)

    # Reset flags first
    reset_ms_flags(ms_path)

    # Flag zeros (same for both backends)
    logger.info("Flagging zeros...")
    flag_zeros(ms_path)

    # Run RFI flagging with timing
    logger.info(f"Running RFI flagging with {backend}...")
    start_time = time.time()

    flag_rfi(
        ms_path,
        backend=backend,
        aoflagger_path=aoflagger_path,
        strategy=strategy,
        extend_flags=True,
    )

    execution_time = time.time() - start_time
    logger.info(f":check_mark: RFI flagging completed in {execution_time:.1f} seconds")

    # Collect flagging statistics
    total_frac, per_spw, fully_flagged = get_ms_flagging_stats(ms_path)

    logger.info(f"Overall flagging: {total_frac * 100:.2f}%")
    logger.info(f"Fully flagged SPWs: {fully_flagged}")

    return FlaggingStats(
        backend=backend,
        total_flagged_fraction=total_frac,
        execution_time_sec=execution_time,
        per_spw_flagging=per_spw,
        fully_flagged_spws=fully_flagged,
    )


def run_calibration_test(
    ms_path: str,
    backend: str,
    refant: str,
    field: str = "0",
) -> CalibrationStats:
    """Run calibration and collect success statistics.

    Args:
        ms_path: Path to Measurement Set (already flagged)
        backend: Backend name (for labeling)
        refant: Reference antenna
        field: Field ID

    Returns:
        CalibrationStats with success metrics
    """
    from dsa110_contimg.calibration.calibration import (
        solve_bandpass,
        solve_delay,
        solve_gains,
    )
    from dsa110_contimg.calibration.model import populate_model_from_catalog

    logger.info("=" * 80)
    logger.info(f"Testing calibration with {backend.upper()} flags")
    logger.info("=" * 80)

    start_time = time.time()
    success = True
    failed_spws = []
    succeeded_spws = []

    try:
        # Populate model
        logger.info("Populating MODEL_DATA from catalog...")
        populate_model_from_catalog(ms_path, field=field)

        # Generate table prefix
        ms_base = Path(ms_path).stem
        table_prefix = f"{Path(ms_path).parent}/{ms_base}_{backend}_{field}"

        # Solve delay
        logger.info("Solving delay calibration...")
        ktabs = solve_delay(ms_path, field, refant, table_prefix=table_prefix)

        # Solve bandpass
        logger.info("Solving bandpass calibration...")
        bptabs = solve_bandpass(
            ms_path,
            field,
            refant,
            ktabs=ktabs,
            table_prefix=table_prefix,
        )

        # Solve gains
        logger.info("Solving gain calibration...")
        gtabs = solve_gains(
            ms_path,
            field,
            refant,
            ktabs=ktabs,
            bptabs=bptabs,
            table_prefix=table_prefix,
        )

        # Check which SPWs have solutions
        # Read BP table to determine successful SPWs
        try:
            from casacore import tables

            with tables.table(bptabs[0], readonly=True, ack=False) as tb:
                spw_col = tb.getcol("SPECTRAL_WINDOW_ID")
                succeeded_spws = sorted(set(int(s) for s in spw_col))

            # Get all SPWs from MS
            with tables.table(ms_path, readonly=True, ack=False) as tb:
                all_spws = sorted(set(int(s) for s in tb.getcol("DATA_DESC_ID")))

            failed_spws = [s for s in all_spws if s not in succeeded_spws]

        except Exception as e:
            logger.warning(f"Could not determine SPW success/failure: {e}")

    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        success = False
        # Try to get SPW info anyway
        try:
            from casacore import tables

            with tables.table(ms_path, readonly=True, ack=False) as tb:
                all_spws = sorted(set(int(s) for s in tb.getcol("DATA_DESC_ID")))
            failed_spws = all_spws
        except:
            pass

    execution_time = time.time() - start_time

    # Get total SPW count
    try:
        from casacore import tables

        with tables.table(ms_path, readonly=True, ack=False) as tb:
            total_spws = len(set(tb.getcol("DATA_DESC_ID")))
    except:
        total_spws = len(succeeded_spws) + len(failed_spws)

    logger.info(f":check_mark: Calibration completed in {execution_time:.1f} seconds")
    logger.info(f"Success: {success}")
    logger.info(f"Succeeded SPWs: {succeeded_spws}")
    logger.info(f"Failed SPWs: {failed_spws}")

    return CalibrationStats(
        backend=backend,
        success=success,
        execution_time_sec=execution_time,
        failed_spws=failed_spws,
        succeeded_spws=succeeded_spws,
        total_spws=total_spws,
    )


def generate_comparison_report(results: ComparisonResults, output_path: Path) -> None:
    """Generate human-readable comparison report.

    Args:
        results: Comparison results
        output_path: Path to save report
    """
    report = []
    report.append("=" * 80)
    report.append("RFI BACKEND COMPARISON REPORT")
    report.append("=" * 80)
    report.append(f"Test MS: {results.test_ms}")
    report.append(f"Timestamp: {results.timestamp}")
    report.append("")

    # Flagging comparison
    report.append("=" * 80)
    report.append("FLAGGING PERFORMANCE COMPARISON")
    report.append("=" * 80)
    report.append("")

    ao = results.aoflagger_flagging
    casa = results.casa_flagging

    report.append(f"{'Metric':<40} {'AOFlagger':<20} {'CASA tfcrop+rflag':<20}")
    report.append("-" * 80)
    report.append(
        f"{'Execution Time (sec)':<40} {ao.execution_time_sec:<20.2f} {casa.execution_time_sec:<20.2f}"
    )
    report.append(
        f"{'Overall Flagging (%)':<40} {ao.total_flagged_fraction*100:<20.2f} {casa.total_flagged_fraction*100:<20.2f}"
    )
    report.append(
        f"{'Fully Flagged SPWs':<40} {len(ao.fully_flagged_spws):<20} {len(casa.fully_flagged_spws):<20}"
    )

    # Speed comparison
    speedup = casa.execution_time_sec / ao.execution_time_sec
    report.append("")
    if speedup > 1:
        report.append(f"→ AOFlagger is {speedup:.2f}x FASTER than CASA")
    else:
        report.append(f"→ CASA is {1/speedup:.2f}x FASTER than AOFlagger")

    # Flagging aggressiveness comparison
    flag_diff = (casa.total_flagged_fraction - ao.total_flagged_fraction) * 100
    report.append("")
    if abs(flag_diff) < 1:
        report.append(f"→ Both backends flag similar amounts of data (±{abs(flag_diff):.2f}%)")
    elif flag_diff > 0:
        report.append(f"→ CASA flags {flag_diff:.2f}% MORE data than AOFlagger")
    else:
        report.append(f"→ AOFlagger flags {abs(flag_diff):.2f}% MORE data than CASA")

    # Per-SPW comparison
    report.append("")
    report.append("=" * 80)
    report.append("PER-SPW FLAGGING COMPARISON")
    report.append("=" * 80)
    report.append("")
    report.append(f"{'SPW':<10} {'AOFlagger (%)':<20} {'CASA (%)':<20} {'Difference':<20}")
    report.append("-" * 80)

    all_spws = sorted(set(ao.per_spw_flagging.keys()) | set(casa.per_spw_flagging.keys()))
    for spw in all_spws:
        ao_pct = ao.per_spw_flagging.get(spw, 0) * 100
        casa_pct = casa.per_spw_flagging.get(spw, 0) * 100
        diff = casa_pct - ao_pct
        report.append(f"{spw:<10} {ao_pct:<20.2f} {casa_pct:<20.2f} {diff:+.2f}")

    # Calibration comparison (if available)
    if results.aoflagger_calibration and results.casa_calibration:
        report.append("")
        report.append("=" * 80)
        report.append("CALIBRATION SUCCESS COMPARISON")
        report.append("=" * 80)
        report.append("")

        ao_cal = results.aoflagger_calibration
        casa_cal = results.casa_calibration

        report.append(f"{'Metric':<40} {'AOFlagger':<20} {'CASA tfcrop+rflag':<20}")
        report.append("-" * 80)
        report.append(
            f"{'Execution Time (sec)':<40} {ao_cal.execution_time_sec:<20.2f} {casa_cal.execution_time_sec:<20.2f}"
        )
        report.append(
            f"{'Succeeded SPWs':<40} {len(ao_cal.succeeded_spws):<20} {len(casa_cal.succeeded_spws):<20}"
        )
        report.append(
            f"{'Failed SPWs':<40} {len(ao_cal.failed_spws):<20} {len(casa_cal.failed_spws):<20}"
        )
        report.append(
            f"{'Success Rate (%)':<40} {len(ao_cal.succeeded_spws)/ao_cal.total_spws*100:<20.1f} {len(casa_cal.succeeded_spws)/casa_cal.total_spws*100:<20.1f}"
        )

        report.append("")
        report.append(f"AOFlagger - Failed SPWs: {ao_cal.failed_spws}")
        report.append(f"CASA      - Failed SPWs: {casa_cal.failed_spws}")

        # Determine which is better
        ao_success_rate = len(ao_cal.succeeded_spws) / ao_cal.total_spws
        casa_success_rate = len(casa_cal.succeeded_spws) / casa_cal.total_spws

        report.append("")
        if ao_success_rate > casa_success_rate:
            diff = (ao_success_rate - casa_success_rate) * 100
            report.append(f"→ AOFlagger enables {diff:.1f}% MORE successful calibrations")
        elif casa_success_rate > ao_success_rate:
            diff = (casa_success_rate - ao_success_rate) * 100
            report.append(f"→ CASA enables {diff:.1f}% MORE successful calibrations")
        else:
            report.append("→ Both backends have EQUAL calibration success rates")

    # Notes
    if results.notes:
        report.append("")
        report.append("=" * 80)
        report.append("NOTES")
        report.append("=" * 80)
        report.append(results.notes)

    # Summary
    report.append("")
    report.append("=" * 80)
    report.append("SUMMARY")
    report.append("=" * 80)
    report.append("")

    # Determine winner
    ao_wins = 0
    casa_wins = 0
    ties = 0

    # Speed
    if ao.execution_time_sec < casa.execution_time_sec * 0.9:
        report.append(":check_mark: AOFlagger is significantly faster")
        ao_wins += 1
    elif casa.execution_time_sec < ao.execution_time_sec * 0.9:
        report.append(":check_mark: CASA is significantly faster")
        casa_wins += 1
    else:
        report.append("= Both have similar speed")
        ties += 1

    # Calibration success (if available)
    if results.aoflagger_calibration and results.casa_calibration:
        ao_success_rate = (
            len(results.aoflagger_calibration.succeeded_spws)
            / results.aoflagger_calibration.total_spws
        )
        casa_success_rate = (
            len(results.casa_calibration.succeeded_spws) / results.casa_calibration.total_spws
        )

        if ao_success_rate > casa_success_rate + 0.05:
            report.append(":check_mark: AOFlagger enables better calibration success")
            ao_wins += 1
        elif casa_success_rate > ao_success_rate + 0.05:
            report.append(":check_mark: CASA enables better calibration success")
            casa_wins += 1
        else:
            report.append("= Both have similar calibration success")
            ties += 1

    report.append("")
    if ao_wins > casa_wins:
        report.append(f":trophy: WINNER: AOFlagger ({ao_wins} advantages vs {casa_wins})")
    elif casa_wins > ao_wins:
        report.append(f":trophy: WINNER: CASA ({casa_wins} advantages vs {ao_wins})")
    else:
        report.append(f":handshake: TIE: Both backends perform similarly")

    report.append("")
    report.append("=" * 80)
    report.append("END OF REPORT")
    report.append("=" * 80)

    # Write report
    report_text = "\n".join(report)
    output_path.write_text(report_text)
    logger.info(f":check_mark: Report saved to: {output_path}")

    # Also print to console
    print("\n" + report_text)


def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(
        description="Compare AOFlagger vs CASA tfcrop+rflag RFI flagging backends"
    )
    parser.add_argument("ms", help="Path to test Measurement Set")
    parser.add_argument(
        "--refant",
        default="103",
        help="Reference antenna for calibration (default: 103)",
    )
    parser.add_argument(
        "--field",
        default="0",
        help="Field ID for calibration (default: 0)",
    )
    parser.add_argument(
        "--aoflagger-path",
        help="Path to aoflagger executable or 'docker' (default: auto-detect)",
    )
    parser.add_argument(
        "--aoflagger-strategy",
        help="Path to custom AOFlagger strategy file (optional)",
    )
    parser.add_argument(
        "--full-pipeline",
        action="store_true",
        help="Run full calibration pipeline to compare effectiveness (slower)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/dsa110-contimg/tests/integration/rfi_comparison_results"),
        help="Directory to save results",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Additional notes to include in report",
    )

    args = parser.parse_args()

    # Validate MS exists
    ms_path = Path(args.ms)
    if not ms_path.exists():
        logger.error(f"MS not found: {ms_path}")
        return 1

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Create working copies of MS
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = args.output_dir / f"test_{timestamp}"
    work_dir.mkdir(parents=True, exist_ok=True)

    ms_aoflagger = work_dir / "test_aoflagger.ms"
    ms_casa = work_dir / "test_casa.ms"

    logger.info("=" * 80)
    logger.info("RFI BACKEND COMPARISON TEST")
    logger.info("=" * 80)
    logger.info(f"Test MS: {ms_path}")
    logger.info(f"Working directory: {work_dir}")
    logger.info(f"Full pipeline: {args.full_pipeline}")
    logger.info("")

    # Copy MS for AOFlagger test
    logger.info("Preparing AOFlagger test MS...")
    copy_ms(str(ms_path), str(ms_aoflagger))

    # Copy MS for CASA test
    logger.info("Preparing CASA test MS...")
    copy_ms(str(ms_path), str(ms_casa))

    # Run AOFlagger test
    logger.info("")
    ao_flagging = run_flagging_backend(
        str(ms_aoflagger),
        "aoflagger",
        aoflagger_path=args.aoflagger_path,
        strategy=args.aoflagger_strategy,
    )

    # Run CASA test
    logger.info("")
    casa_flagging = run_flagging_backend(str(ms_casa), "casa")

    # Run calibration tests (if requested)
    ao_cal = None
    casa_cal = None

    if args.full_pipeline:
        logger.info("")
        logger.info("Running full calibration pipeline tests...")

        ao_cal = run_calibration_test(
            str(ms_aoflagger),
            "aoflagger",
            args.refant,
            args.field,
        )

        casa_cal = run_calibration_test(
            str(ms_casa),
            "casa",
            args.refant,
            args.field,
        )

    # Compile results
    results = ComparisonResults(
        test_ms=str(ms_path),
        timestamp=datetime.now().isoformat(),
        aoflagger_flagging=ao_flagging,
        casa_flagging=casa_flagging,
        aoflagger_calibration=ao_cal,
        casa_calibration=casa_cal,
        notes=args.notes,
    )

    # Save JSON results
    json_path = work_dir / "comparison_results.json"
    with open(json_path, "w") as f:
        json.dump(asdict(results), f, indent=2)
    logger.info(f":check_mark: JSON results saved to: {json_path}")

    # Generate and save report
    report_path = work_dir / "comparison_report.txt"
    generate_comparison_report(results, report_path)

    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST COMPLETED")
    logger.info("=" * 80)
    logger.info(f"Results directory: {work_dir}")
    logger.info(f"Report: {report_path}")
    logger.info(f"JSON: {json_path}")

    return 0


if __name__ == "__main__":
    exit(main())
