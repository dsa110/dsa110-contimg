#!/opt/miniforge/envs/casa6/bin/python
"""
Unified script to process first 10 groups and create one mosaic.

This script:
1. Bootstraps existing files from /data/incoming/
2. Processes first 10 groups (convert → MS → calibrate → image)
3. Creates one mosaic from the first 10 MS files
4. Stops automatically
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Set up CASA environment before any CASA imports
from dsa110_contimg.utils.cli_helpers import setup_casa_environment

setup_casa_environment()

from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.conversion.streaming.streaming_converter import QueueDB
from dsa110_contimg.database.products import (
    ensure_products_db,
    images_insert,
    ms_index_upsert,
)
from dsa110_contimg.database.registry import ensure_db as ensure_cal_db
from dsa110_contimg.database.registry import get_active_applylist
from dsa110_contimg.imaging.cli import image_ms
from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager
from dsa110_contimg.utils.ms_organization import create_path_mapper
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def process_one_group(
    gid: str,
    args: argparse.Namespace,
    queue: QueueDB,
) -> bool:
    """Process a single group through conversion → MS → calibration → imaging.

    Returns:
        True if successful, False otherwise
    """

    log = logging.getLogger("stream.worker")
    t0 = time.perf_counter()

    # Use group timestamp for start/end
    # Group ID represents a 5-minute chunk, so add 5 minutes to end_time
    from datetime import datetime, timedelta

    start_time = gid.replace("T", " ")
    start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    end_dt = start_dt + timedelta(minutes=5)
    end_time = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    # Create path mapper for organized output
    ms_base_dir = Path(args.output_dir)
    path_mapper = create_path_mapper(ms_base_dir, is_calibrator=False, is_failed=False)

    # Determine MS path and check if it exists and is valid
    files = queue.group_files(gid)
    if not files:
        raise RuntimeError("no subband files recorded for group")
    first = os.path.basename(files[0])
    base = os.path.splitext(first)[0].split("_sb")[0]
    ms_path = path_mapper(base, args.output_dir)

    # Check if MS exists and validate it before skipping conversion
    ms_path_obj = Path(ms_path)
    if ms_path_obj.exists():
        try:
            from dsa110_contimg.utils.validation import validate_ms

            validate_ms(
                ms_path,
                check_empty=True,
                check_columns=["DATA", "ANTENNA1", "ANTENNA2", "TIME", "UVW"],
            )
            log.info(f"MS already exists and is valid, skipping conversion: {ms_path}")
            writer_type = "skipped"
        except Exception as val_exc:
            log.warning(f"MS exists but is invalid ({val_exc}), removing and re-converting")
            # Remove invalid MS directory
            import shutil

            try:
                shutil.rmtree(ms_path)
                log.info(f"Removed invalid MS directory: {ms_path}")
            except Exception as rm_exc:
                log.warning(f"Failed to remove invalid MS: {rm_exc}")
            # Fall through to conversion

    # Convert subband group to MS (only if MS doesn't exist or was invalid)
    writer_type = "skipped"  # Default if MS already exists
    if not ms_path_obj.exists():
        try:
            from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                convert_subband_groups_to_ms,
            )

            convert_subband_groups_to_ms(
                args.input_dir,
                args.output_dir,
                start_time,
                end_time,
                scratch_dir=args.scratch_dir,
                writer="auto",
                writer_kwargs={
                    "max_workers": getattr(args, "max_workers", 4),
                    "stage_to_tmpfs": getattr(args, "stage_to_tmpfs", False),
                    "tmpfs_path": getattr(args, "tmpfs_path", "/dev/shm"),
                },
                path_mapper=path_mapper,
            )
            writer_type = "auto"
        except Exception as exc:
            log.error(f"Conversion failed for {gid}: {exc}", exc_info=True)
            queue.update_state(gid, "failed", error=str(exc))
            writer_type = "failed"
            return False

    total = time.perf_counter() - t0
    queue.record_metrics(gid, total_time=total, writer_type=writer_type)

    # MS path already determined above, verify it exists and is valid
    products_db_path = os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3")
    try:
        # CRITICAL: Verify MS file exists and is valid before proceeding
        ms_path_obj = Path(ms_path)
        if not ms_path_obj.exists():
            raise FileNotFoundError(
                f"MS file does not exist at expected path: {ms_path}. "
                f"Conversion may not have completed or path is incorrect."
            )

        # Validate MS is readable (double-check after conversion)
        from dsa110_contimg.utils.validation import validate_ms

        validate_ms(
            ms_path,
            check_empty=True,
            check_columns=["DATA", "ANTENNA1", "ANTENNA2", "TIME", "UVW"],
        )
        log.debug(f"Verified MS file exists and is valid: {ms_path}")
    except Exception as exc:
        log.error(f"Failed to locate or verify MS for {gid}: {exc}", exc_info=True)
        queue.update_state(gid, "completed")
        return False

    # Record conversion in products DB
    try:
        conn = ensure_products_db(Path(products_db_path))
        start_mjd = end_mjd = mid_mjd = None
        try:
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
        except Exception as e:
            log.debug(f"Failed to extract time range from {ms_path}: {e} (will use fallback)")
            # Fallback: Use observation time from filename, not current time
            try:
                from datetime import datetime

                from astropy.time import Time

                # Parse timestamp from group ID (format: YYYY-MM-DDTHH:MM:SS)
                obs_time_str = gid.replace("T", " ")
                obs_dt = datetime.strptime(obs_time_str, "%Y-%m-%d %H:%M:%S")
                mid_mjd = Time(obs_dt).mjd
                # Estimate 5-minute observation duration
                start_mjd = mid_mjd - (2.5 / 1440.0)  # 2.5 minutes before
                end_mjd = mid_mjd + (2.5 / 1440.0)  # 2.5 minutes after
                log.info(f"Using filename timestamp as fallback: mid_mjd={mid_mjd:.6f}")
            except Exception as fallback_error:
                log.warning(f"Fallback time extraction also failed: {fallback_error}")

        ms_index_upsert(
            conn,
            ms_path,
            start_mjd=start_mjd,
            end_mjd=end_mjd,
            mid_mjd=mid_mjd,
            processed_at=time.time(),
            status="converted",
            stage="converted",
        )
        conn.commit()
    except Exception:
        log.debug("ms_index conversion upsert failed", exc_info=True)

    # Apply calibration and image
    try:
        if mid_mjd is None:
            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
            except Exception:
                # Fallback: Use observation time from filename
                try:
                    from datetime import datetime

                    from astropy.time import Time

                    obs_time_str = gid.replace("T", " ")
                    obs_dt = datetime.strptime(obs_time_str, "%Y-%m-%d %H:%M:%S")
                    mid_mjd = Time(obs_dt).mjd
                    log.info(
                        f"Using filename timestamp for calibration lookup: mid_mjd={mid_mjd:.6f}"
                    )
                except Exception:
                    log.error(f"Cannot determine observation time for {gid}, skipping calibration")
                    mid_mjd = None

        applylist = []
        if mid_mjd is not None:
            try:
                applylist = get_active_applylist(
                    Path(args.registry_db),
                    float(mid_mjd),
                )
            except Exception:
                applylist = []
        else:
            log.warning(f"Skipping calibration application for {gid} due to missing time")

        cal_applied = 0
        if applylist:
            try:
                apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
                cal_applied = 1
            except Exception:
                log.warning(f"applycal failed for {ms_path}", exc_info=True)

        # Image MS
        imgroot = os.path.join(args.output_dir, base + ".img")
        try:
            image_ms(
                ms_path,
                imagename=imgroot,
                field="",
                quality_tier="standard",
                skip_fits=False,
            )
        except Exception as img_exc:
            log.error(f"imaging failed for {ms_path}: {img_exc}", exc_info=True)
            raise  # Re-raise to ensure warning monitor catches it

        # Update products DB
        try:
            conn = ensure_products_db(Path(products_db_path))
            ms_index_upsert(
                conn,
                ms_path,
                status="done",
                stage="imaged",
                cal_applied=cal_applied,
                imagename=imgroot,
            )
            now_ts = time.time()
            for suffix, pbcor in [
                (".image", 0),
                (".pb", 0),
                (".pbcor", 1),
                (".residual", 0),
                (".model", 0),
            ]:
                p = f"{imgroot}{suffix}"
                if os.path.isdir(p) or os.path.isfile(p):
                    images_insert(conn, p, ms_path, now_ts, "5min", pbcor)
            conn.commit()
        except Exception:
            log.debug("products DB update failed", exc_info=True)
    except Exception:
        log.exception(f"post-conversion processing failed for {gid}")

    queue.update_state(gid, "completed")
    log.info(f"Completed {gid} in {time.perf_counter() - t0:.2f}s")
    return True


def process_groups_until_count(
    args: argparse.Namespace,
    queue: QueueDB,
    target_count: int = 10,
) -> int:
    """Process groups until we have target_count completed groups.

    Returns:
        Number of groups actually processed
    """
    log = logging.getLogger("stream.worker")
    processed_count = 0

    while processed_count < target_count:
        gid = queue.acquire_next_pending()
        if gid is None:
            log.info(f"No pending groups. Processed {processed_count}/{target_count} groups.")
            time.sleep(5.0)
            continue

        log.info(f"Processing group {processed_count + 1}/{target_count}: {gid}")

        success = process_one_group(gid, args, queue)
        if success:
            processed_count += 1
            log.info(f":check_mark: Completed group {processed_count}/{target_count}")
        else:
            log.error(f":ballot_x: Failed to process group {gid}")
            # Continue to next group even if one fails

    return processed_count


def main():
    parser = argparse.ArgumentParser(description="Process first 10 groups and create one mosaic")
    parser.add_argument(
        "--input-dir",
        default="/data/incoming",
        help="Input directory with HDF5 files (default: /data/incoming)",
    )
    parser.add_argument(
        "--output-dir",
        default="/stage/dsa110-contimg/raw/ms",
        help="Output directory for MS files (default: /stage/dsa110-contimg/raw/ms)",
    )
    parser.add_argument(
        "--images-dir",
        default="/stage/dsa110-contimg/images",
        help="Directory for images (default: /stage/dsa110-contimg/images)",
    )
    parser.add_argument(
        "--mosaic-dir",
        default="/stage/dsa110-contimg/mosaics",
        help="Directory for mosaics (default: /stage/dsa110-contimg/mosaics)",
    )
    parser.add_argument(
        "--scratch-dir",
        default="/stage/dsa110-contimg",
        help="Scratch directory (default: /stage/dsa110-contimg)",
    )
    parser.add_argument(
        "--queue-db",
        default="state/db/ingest.sqlite3",
        help="Queue database path (default: state/db/ingest.sqlite3)",
    )
    parser.add_argument(
        "--products-db",
        default="state/db/products.sqlite3",
        help="Products database path (default: state/db/products.sqlite3)",
    )
    parser.add_argument(
        "--registry-db",
        default="state/db/cal_registry.sqlite3",
        help="Calibration registry database path (default: state/db/cal_registry.sqlite3)",
    )
    parser.add_argument(
        "--expected-subbands",
        type=int,
        default=16,
        help="Expected number of subbands per group (default: 16)",
    )
    parser.add_argument(
        "--chunk-duration",
        type=float,
        default=5.0,
        help="Chunk duration in minutes (default: 5.0)",
    )
    parser.add_argument(
        "--register-bpcal",
        metavar="NAME,RA_DEG,DEC_DEG",
        help="Register bandpass calibrator (format: NAME,RA_DEG,DEC_DEG)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum workers for conversion (default: 4)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Log level (default: INFO)",
    )

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    # Validate directories
    input_path = Path(args.input_dir)
    if not input_path.exists():
        logger.error(f"Input directory does not exist: {args.input_dir}")
        return 1
    if not input_path.is_dir():
        logger.error(f"Input path is not a directory: {args.input_dir}")
        return 1

    # Create output directories
    for dir_path in [
        args.output_dir,
        args.images_dir,
        args.mosaic_dir,
        args.scratch_dir,
    ]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_path}")

    # Initialize databases
    products_db_path = Path(args.products_db)
    registry_db_path = Path(args.registry_db)
    queue_db_path = Path(args.queue_db)

    products_db_path.parent.mkdir(parents=True, exist_ok=True)
    registry_db_path.parent.mkdir(parents=True, exist_ok=True)
    queue_db_path.parent.mkdir(parents=True, exist_ok=True)

    ensure_products_db(products_db_path)
    ensure_cal_db(registry_db_path)

    logger.info(":check_mark: Databases initialized")

    # Initialize queue and bootstrap existing files
    logger.info(f"Bootstrapping existing files from {args.input_dir}...")
    queue = QueueDB(
        queue_db_path,
        expected_subbands=int(args.expected_subbands),
        chunk_duration_minutes=float(args.chunk_duration),
    )

    try:
        queue.bootstrap_directory(input_path)
        logger.info(":check_mark: Bootstrap complete")
    except Exception as e:
        logger.error(f"Bootstrap failed: {e}", exc_info=True)
        return 1

    # Register bandpass calibrator if provided
    if args.register_bpcal:
        parts = args.register_bpcal.split(",")
        if len(parts) != 3:
            logger.error("--register-bpcal format: NAME,RA_DEG,DEC_DEG")
            return 1

        calibrator_name = parts[0].strip()
        try:
            ra_deg = float(parts[1].strip())
            dec_deg = float(parts[2].strip())
        except ValueError:
            logger.error("RA_DEG and DEC_DEG must be numeric")
            return 1

        logger.info(
            f"Registering bandpass calibrator: {calibrator_name} (RA={ra_deg:.6f}, Dec={dec_deg:.6f})"
        )

        mosaic_manager = StreamingMosaicManager(
            products_db_path=products_db_path,
            registry_db_path=registry_db_path,
            ms_output_dir=Path(args.output_dir),
            images_dir=Path(args.images_dir),
            mosaic_output_dir=Path(args.mosaic_dir),
        )

        mosaic_manager.register_bandpass_calibrator(
            calibrator_name=calibrator_name,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            dec_tolerance=5.0,
            registered_by="run_first_mosaic",
        )
        logger.info(":check_mark: Calibrator registered")

    # Process first 10 groups
    logger.info("=" * 80)
    logger.info("PHASE 1: Processing first 10 groups (convert → MS → calibrate → image)")
    logger.info("=" * 80)

    processed = process_groups_until_count(args, queue, target_count=10)

    if processed < 10:
        logger.warning(f"Only processed {processed} groups, but need 10 for mosaic")
        logger.info("Waiting for more groups or checking if enough MS files exist...")
        # Check if we have enough MS files anyway
        conn = ensure_products_db(products_db_path)
        ms_count = conn.execute(
            "SELECT COUNT(*) FROM ms_index WHERE stage IN ('converted', 'imaged', 'done')"
        ).fetchone()[0]
        logger.info(f"Found {ms_count} MS files in database")

        if ms_count < 10:
            logger.error(f"Need at least 10 MS files, but only found {ms_count}")
            return 1

    logger.info("=" * 80)
    logger.info("PHASE 2: Creating mosaic from first 10 MS files")
    logger.info("=" * 80)

    # Initialize mosaic manager
    mosaic_manager = StreamingMosaicManager(
        products_db_path=products_db_path,
        registry_db_path=registry_db_path,
        ms_output_dir=Path(args.output_dir),
        images_dir=Path(args.images_dir),
        mosaic_output_dir=Path(args.mosaic_dir),
    )

    # Process one group (creates mosaic)
    success = mosaic_manager.process_next_group(use_sliding_window=False)

    if success:
        logger.info("=" * 80)
        logger.info(":check_mark: SUCCESS: First mosaic created!")
        logger.info("=" * 80)
        return 0
    else:
        logger.error("Failed to create mosaic")
        return 1


if __name__ == "__main__":
    sys.exit(main())
