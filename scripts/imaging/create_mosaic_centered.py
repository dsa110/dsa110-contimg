#!/opt/miniforge/envs/casa6/bin/python
"""
Create a mosaic centered on a calibrator transit.

Single trigger, hands-off operation: creates mosaic and waits until published.

This script orchestrates a complete end-to-end pipeline from HDF5 data to published
science-ready mosaic. The workflow proceeds through initialization, transit discovery,
HDF5 conversion (if needed), calibration solving/application, imaging, mosaic creation,
validation/QA, and automatic publishing.

Usage:
    PYTHONPATH=/data/dsa110-contimg/src python scripts/mosaic/create_mosaic_centered.py \
        --calibrator 0834+555 \
        [--timespan-minutes 50] \
        [--no-wait]

See inline comments for detailed phase-by-phase breakdown of internal steps.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path before importing project modules
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "src"))

from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main function.

    Orchestrates complete pipeline workflow from HDF5 data to published mosaic.

    Returns:
        0 on success (mosaic published), 1 on failure
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Create mosaic centered on calibrator transit")
    parser.add_argument(
        "--calibrator",
        required=True,
        help="Calibrator name (e.g., '0834+555')",
    )
    parser.add_argument(
        "--timespan-minutes",
        type=int,
        default=50,
        help="Mosaic timespan in minutes (default: 50)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for published status (return immediately after creation)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Polling interval in seconds for published status (default: 5)",
    )
    parser.add_argument(
        "--max-wait-hours",
        type=float,
        default=24.0,
        help="Maximum hours to wait for published status (default: 24)",
    )

    args = parser.parse_args()

    logger.info(f"Creating {args.timespan_minutes}-minute mosaic centered on {args.calibrator}")

    # PHASE 1: Initialize orchestrator
    # Sets up database connections (products.sqlite3, data_registry.sqlite3),
    # calibrator service (dsa110_contimg.conversion.calibrator_ms_service), and
    # prepares for lazy initialization of StreamingMosaicManager
    orchestrator = MosaicOrchestrator()

    # PHASES 2-11: Execute complete pipeline workflow via orchestrator
    #
    # This single call (orchestrator.create_mosaic_centered_on_calibrator) internally
    # executes the following workflow:
    #
    # PHASE 2: Transit Window Discovery (orchestrator.find_transit_centered_window)
    #   - Queries calibrator service (CalibratorMSService.list_available_transits)
    #   - Finds earliest transit (most recent first, so last in list)
    #   - Calculates time window: ±(timespan/2) minutes centered on transit
    #   - Extracts Dec from calibrator coordinates (_load_radec)
    #   - Queries ms_index table to count existing MS files in window
    #
    # PHASE 3: MS File Availability & Conversion (orchestrator.ensure_ms_files_in_window)
    #   - Queries ms_index for MS files in time window with valid status
    #   - If insufficient MS files (< required_count):
    #     * Calls orchestrator._trigger_hdf5_conversion()
    #     * Triggers hdf5_orchestrator.convert_subband_groups_to_ms()
    #     * Converts HDF5 files from /data/incoming/ to MS files in /stage/
    #     * During conversion, streaming_converter extracts RA/Dec pointing from
    #       HDF5 headers via _peek_uvh5_phase_and_midtime()
    #     * Logs pointing to ms_index (ra_deg, dec_deg) and pointing_history tables
    #       via products.ms_index_upsert() and products.log_pointing()
    #   - Re-queries ms_index after conversion
    #   - Returns list of MS paths (up to required_count, or fewer if asymmetric)
    #
    # PHASE 4: Group Formation (orchestrator._form_group_from_ms_paths)
    #   - Generates group_id: mosaic_{transit_time.isot} (sanitized)
    #   - Inserts group into mosaic_groups table with status='formed'
    #   - Registers storage locations in data_registry with status='staging'
    #     via StreamingMosaicManager._register_storage_locations()
    #
    # PHASE 5: Calibration Solving (orchestrator._process_group_workflow →
    #          StreamingMosaicManager.solve_calibration_for_group)
    #   - Selects 5th MS (index 4) as calibration source via
    #     StreamingMosaicManager.select_calibration_ms()
    #   - Extracts mid_mjd from calibration MS
    #   - Checks cal_registry.sqlite3 for existing BP/GP tables
    #   - If missing:
    #     * Infers BP calibrator from Dec via
    #       StreamingMosaicManager.get_bandpass_calibrator_for_dec()
    #     * Solves BP calibration (CASA bandpass task)
    #     * Solves gain calibration (CASA gaincal task with skymodel)
    #     * Registers calibration tables in cal_registry
    #
    # PHASE 6: Calibration Application (StreamingMosaicManager.apply_calibration_to_group)
    #   - For each MS in group:
    #     * Loads BP/GP tables from cal_registry
    #     * Applies using CASA applycal task
    #     * Updates ms_index status to 'calibrated'
    #   - Updates mosaic_groups table: stage='calibrated', cal_applied=1
    #
    # PHASE 7: Imaging (StreamingMosaicManager.image_group)
    #   - For each calibrated MS:
    #     * Checks if image already exists (queries images table)
    #     * If missing: runs WSClean imaging (CASA tclean fallback)
    #     * Registers image in images table
    #     * Updates ms_index status to 'imaged'
    #   - Updates mosaic_groups table: stage='imaged'
    #
    # PHASE 8: Mosaic Creation (StreamingMosaicManager.create_mosaic)
    #   - Validates MS paths are in chronological order (by mid_mjd)
    #   - Queries images table for all group images
    #   - Plans mosaic (mosaic.cli plan): determines tile grid and sky coverage
    #   - Builds mosaic (mosaic.cli build):
    #     * Combines tiles using immath with imageweighttype=0 (PB-weighted)
    #     * Output: /stage/dsa110-contimg/mosaics/{group_id}.fits
    #   - Registers mosaic in images table with image_type='mosaic'
    #   - Updates mosaic_groups table: stage='mosaicked', status='done'
    #   - Registers mosaic in data_registry with status='staging'
    #
    # PHASE 9: Validation & QA (automatic, triggered by data_registry)
    #   - Tile consistency checks (grid, astrometry, calibration, PB correction)
    #   - QA validation runs automatically via data_registry pipeline
    #   - Updates data_registry: qa_status='passed', validation_status='validated'
    #
    # PHASE 10: Publishing (data_registry.trigger_auto_publish)
    #   - When qa_status='passed' and validation_status='validated':
    #     * Moves mosaic from /stage/ to /data/dsa110-contimg/products/mosaics/
    #     * Updates data_registry: status='published', published_path, published_at
    #   - Updates images table with published path
    #
    # PHASE 11: Wait for Publication (orchestrator.wait_for_published, if wait_for_published=True)
    #   - Polls data_registry every poll_interval_seconds via data_registry.get_data()
    #   - Checks if status == 'published' and published_path exists
    #   - Continues until published or timeout (max_wait_hours)
    #
    # Returns: Published mosaic path (in /data/) or None if failed
    published_path = orchestrator.create_mosaic_centered_on_calibrator(
        calibrator_name=args.calibrator,
        timespan_minutes=args.timespan_minutes,
        wait_for_published=not args.no_wait,
        poll_interval_seconds=args.poll_interval,
        max_wait_hours=args.max_wait_hours,
    )

    # PHASE 12: Completion
    # Check result and return appropriate exit code
    if published_path:
        logger.info(f"SUCCESS: Mosaic published at {published_path}")
        print(f"Published mosaic: {published_path}")
        return 0  # Success: mosaic published and ready for science use
    else:
        logger.error("FAILED: Mosaic creation or publishing failed")
        return 1  # Failure: check logs for error details


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        logger.exception("Unhandled error while creating mosaic")
        sys.exit(1)
