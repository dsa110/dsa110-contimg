#!/usr/bin/env python3
"""
Refactored UVH5 to MS converter using production modules.

This replaces convert_uvh5_standalone.py and convert_uvh5_simple.py
by using the production conversion modules directly.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Add source to path (for tests)
if "/data/dsa110-contimg/src" not in sys.path:
    sys.path.insert(0, "/data/dsa110-contimg/src")

# Import production modules
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
    convert_subband_groups_to_ms,
    find_subband_groups,
)
from dsa110_contimg.conversion.helpers import (
    set_antenna_positions,
    _ensure_antenna_diameters,
    get_meridian_coords,
    set_model_column,
)
from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
from dsa110_contimg.conversion.validation import (
    validate_hdf5_files,
    validate_calibrator_transit,
    find_calibrator_sources_in_data,
)

logger = logging.getLogger("convert_uvh5_refactored")


def convert_with_calibrator_model(
    input_dir: str,
    output_dir: str,
    start_time: str,
    end_time: str,
    *,
    flux: Optional[float] = None,
    cal_catalog: Optional[str] = None,
    cal_search_radius_deg: float = 0.0,
    cal_output_dir: Optional[str] = None,
) -> None:
    """
    Convert subband groups using production modules.

    This function demonstrates how to use production modules instead of
    duplicating conversion logic. For most use cases, use the CLI directly:

        python -m dsa110_contimg.conversion.cli groups ...

    Args:
        input_dir: Directory containing UVH5 files
        output_dir: Directory for output MS files
        start_time: Start time (YYYY-MM-DD HH:MM:SS)
        end_time: End time (YYYY-MM-DD HH:MM:SS)
        flux: Optional flux for MODEL_DATA
        cal_catalog: Optional calibrator catalog path
        cal_search_radius_deg: Search radius for calibrator matching
        cal_output_dir: Optional output directory for calibrator MS
    """
    # Use production convert_subband_groups_to_ms
    convert_subband_groups_to_ms(
        input_dir=input_dir,
        output_dir=output_dir,
        start_time=start_time,
        end_time=end_time,
        flux=flux,
        scratch_dir=None,
        writer="auto",
        writer_kwargs=None,
    )

    # If calibrator catalog provided, find and create calibrator MS
    if cal_catalog and cal_search_radius_deg > 0:
        logger.info("Calibrator MS generation using production modules...")
        # This would require additional logic using production modules
        # For now, log that this feature would use CalibratorMSGenerator
        logger.info(
            "For calibrator MS generation, use CalibratorMSGenerator "
            "from dsa110_contimg.conversion.calibrator_ms_service"
        )


def main() -> int:
    """Main entry point for testing purposes."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert DSA-110 subband UVH5 to MS (refactored to use production modules)"
    )
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("start_time", help="YYYY-MM-DD HH:MM:SS")
    parser.add_argument("end_time", help="YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--flux", type=float)
    parser.add_argument(
        "--cal-catalog", default=None, help="Path to VLA calibrator CSV"
    )
    parser.add_argument("--cal-search-radius-deg", type=float, default=0.0)
    parser.add_argument("--cal-output-dir", default=None)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate files, do not convert",
    )
    parser.add_argument(
        "--validate-calibrator",
        type=str,
        help="Validate calibrator transit (e.g., '0834+555')",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Validation mode
    if args.validate_only:
        logger.info("Validation mode: checking files...")
        groups = find_subband_groups(args.input_dir, args.start_time, args.end_time)

        all_files = []
        for group in groups:
            all_files.extend(group)

        results = validate_hdf5_files(all_files)

        valid_count = sum(1 for r in results.values() if r.valid)
        total_count = len(results)

        logger.info(
            f"Validated {total_count} files: {valid_count} valid, {total_count - valid_count} invalid"
        )

        for path, result in results.items():
            if not result.valid:
                logger.error(f"Invalid: {path}")
                for error in result.errors:
                    logger.error(f"  - {error}")
            if result.warnings:
                for warning in result.warnings:
                    logger.warning(f"  - {warning}")

        return 0 if valid_count == total_count else 1

    # Calibrator validation mode
    if args.validate_calibrator:
        logger.info(f"Validating calibrator transit for {args.validate_calibrator}...")
        result = validate_calibrator_transit(
            args.validate_calibrator,
            Path(args.input_dir),
            window_minutes=60,
            max_days_back=30,
        )

        if result.found:
            logger.info(f"✓ Transit found: {result.transit_time.iso}")
            logger.info(f"  Data available: {result.data_available}")
            logger.info(f"  Files: {len(result.files) if result.files else 0}")
            logger.info(f"  Declination match: {result.dec_match}")
            if result.errors:
                for error in result.errors:
                    logger.error(f"  - {error}")
            if result.warnings:
                for warning in result.warnings:
                    logger.warning(f"  - {warning}")
            return 0 if result.data_available and not result.errors else 1
        else:
            logger.error("✗ Transit not found")
            if result.errors:
                for error in result.errors:
                    logger.error(f"  - {error}")
            return 1

    # Normal conversion mode
    os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    os.environ.setdefault("MKL_NUM_THREADS", "4")

    convert_with_calibrator_model(
        args.input_dir,
        args.output_dir,
        args.start_time,
        args.end_time,
        flux=args.flux,
        cal_catalog=args.cal_catalog,
        cal_search_radius_deg=float(args.cal_search_radius_deg or 0.0),
        cal_output_dir=args.cal_output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
