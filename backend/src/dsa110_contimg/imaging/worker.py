"""
Imaging worker: watches a directory of freshly converted 5-minute MS files,
looks up an active calibration apply list from the registry by observation
time, applies calibration, and makes quick continuum images.

This is a first-pass skeleton that can run in one-shot (scan) mode or in a
simple polling loop. It records products in a small SQLite DB for later
mosaicking.
"""

import argparse
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from dsa110_contimg.database import (
    ensure_products_db,
    images_insert,
    ms_index_upsert,
    get_active_applylist,
)
from dsa110_contimg.imaging.fast_imaging import run_fast_imaging

logger = logging.getLogger("imaging_worker")
try:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except ImportError:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _apply_and_image(ms_path: str, out_dir: Path, gaintables: List[str]) -> List[str]:
    """Apply calibration and produce a quick image; returns artifact paths."""
    artifacts: List[str] = []
    # Route temp files to scratch and chdir to output directory to avoid repo pollution
    try:
        if prepare_temp_environment is not None:
            prepare_temp_environment(
                os.getenv("CONTIMG_SCRATCH_DIR") or "/stage/dsa110-contimg",
                cwd_to=os.fspath(out_dir),
            )
    except (OSError, RuntimeError):
        pass
    # Apply to all fields by default
    try:
        from dsa110_contimg.calibration.applycal import apply_to_target
        from dsa110_contimg.imaging.cli import image_ms

        apply_to_target(ms_path, field="", gaintables=gaintables, calwt=True)
        imgroot = out_dir / (Path(ms_path).stem + ".img")

        # Run deep imaging (standard) and fast imaging (transients) in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Task 1: Standard Deep Imaging
            future_deep = executor.submit(
                image_ms,
                ms_path,
                imagename=str(imgroot),
                field="",
                quality_tier="standard",
                skip_fits=True,
            )

            # Task 2: Fast Transient Imaging
            # Note: Running on CORRECTED_DATA (calibrated visibilities).
            # Ideally requires residuals for pure transient detection.
            future_fast = executor.submit(
                run_fast_imaging,
                ms_path,
                interval_seconds=None,  # Auto-detect
                threshold_sigma=6.0,
                datacolumn="CORRECTED_DATA",
                work_dir=str(out_dir),
            )

            # Wait for deep imaging (critical path)
            try:
                future_deep.result()
            except Exception as e:
                logger.error("Deep imaging failed: %s", e)
                raise e

            # Wait for fast imaging (auxiliary)
            try:
                future_fast.result()
            except Exception as e:
                logger.warning("Fast imaging failed (non-fatal): %s", e)

        # Return whatever CASA produced
        for ext in [".image", ".image.pbcor", ".residual", ".psf", ".pb"]:
            p = f"{imgroot}{ext}"
            if os.path.exists(p):
                artifacts.append(p)
    except Exception as e:
        logger.error("apply/image failed for %s: %s", ms_path, e)
    return artifacts


def process_once(
    ms_dir: Path,
    out_dir: Path,
    registry_db: Path,
    products_db: Path,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = ensure_products_db(products_db)
    processed = 0
    for ms in sorted(ms_dir.glob("**/*.ms")):
        row = conn.execute(
            "SELECT status FROM ms_index WHERE path = ?", (os.fspath(ms),)
        ).fetchone()
        if row and row[0] == "done":
            continue
        from dsa110_contimg.utils.time_utils import extract_ms_time_range

        start_mjd, end_mjd, mid_mjd = extract_ms_time_range(os.fspath(ms))
        if mid_mjd is None:
            # Fallback: use current time in MJD
            from astropy.time import Time

            mid_mjd = Time.now().mjd
        applylist = get_active_applylist(registry_db, mid_mjd)
        if not applylist:
            logger.warning("No active caltables for %s (mid MJD %.5f)", ms, mid_mjd)
            status = "skipped_no_caltables"
            ms_index_upsert(
                conn,
                os.fspath(ms),
                start_mjd=start_mjd,
                end_mjd=end_mjd,
                mid_mjd=mid_mjd,
                processed_at=time.time(),
                status=status,
            )
            conn.commit()
            continue

        artifacts = _apply_and_image(os.fspath(ms), out_dir, applylist)
        status = "done" if artifacts else "failed"
        ms_index_upsert(
            conn,
            os.fspath(ms),
            start_mjd=start_mjd,
            end_mjd=end_mjd,
            mid_mjd=mid_mjd,
            processed_at=time.time(),
            status=status,
        )
        for art in artifacts:
            images_insert(
                conn,
                art,
                os.fspath(ms),
                time.time(),
                "5min",
                1 if art.endswith(".image.pbcor") else 0,
            )
        conn.commit()
        processed += 1
        logger.info("Processed %s (artifacts: %d)", ms, len(artifacts))
    return processed


def cmd_scan(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    n = process_once(
        Path(args.ms_dir),
        Path(args.out_dir),
        Path(args.registry_db),
        Path(args.products_db),
    )
    logger.info("Scan complete: %d MS processed", n)
    return 0 if n >= 0 else 1


def cmd_daemon(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    ms_dir = Path(args.ms_dir)
    out_dir = Path(args.out_dir)
    registry_db = Path(args.registry_db)
    products_db = Path(args.products_db)
    poll = float(args.poll_interval)
    while True:
        try:
            process_once(ms_dir, out_dir, registry_db, products_db)
        except Exception as e:
            logger.error("Worker loop error: %s", e)
        time.sleep(poll)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Imaging worker for 5-min MS")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("scan", help="One-shot scan of an MS directory")
    sp.add_argument("--ms-dir", required=True)
    sp.add_argument("--out-dir", required=True)
    sp.add_argument("--registry-db", required=True)
    sp.add_argument("--products-db", required=True)
    sp.add_argument("--log-level", default="INFO")
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("daemon", help="Poll and process arriving MS")
    sp.add_argument("--ms-dir", required=True)
    sp.add_argument("--out-dir", required=True)
    sp.add_argument("--registry-db", required=True)
    sp.add_argument("--products-db", required=True)
    sp.add_argument("--poll-interval", type=float, default=60.0)
    sp.add_argument("--log-level", default="INFO")
    sp.set_defaults(func=cmd_daemon)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, "func"):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
