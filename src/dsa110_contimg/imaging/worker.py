#!/usr/bin/env python3
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
from pathlib import Path
from typing import List, Optional, Tuple

from dsa110_contimg.database.registry import get_active_applylist
from dsa110_contimg.database.products import ensure_products_db, ms_index_upsert, images_insert


logger = logging.getLogger("imaging_worker")
try:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except Exception:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )



def _ms_time_range(
        ms_path: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Best-effort extraction of (start, end, mid) MJD from an MS using casatools.
    Returns (None, None, None) if unavailable.
    """
    try:
        from casatools import msmetadata  # type: ignore

        msmd = msmetadata()
        msmd.open(ms_path)
        # Preferred: explicit observation timerange in MJD days
        try:
            tr = msmd.timerangeforobs()
            if tr and isinstance(tr, (list, tuple)) and len(tr) >= 2:
                start_mjd = float(tr[0])
                end_mjd = float(tr[1])
                msmd.close()
                return start_mjd, end_mjd, 0.5 * (start_mjd + end_mjd)
        except Exception:
            pass

        # Fallback: derive from timesforscans() (seconds, MJD seconds offset)
        try:
            tmap = msmd.timesforscans()
            msmd.close()
            if isinstance(tmap, dict) and tmap:
                all_ts = [t for arr in tmap.values() for t in arr]
                if all_ts:
                    t0 = min(all_ts)
                    t1 = max(all_ts)
                    # Convert seconds to MJD days if needed
                    start_mjd = float(t0) / 86400.0
                    end_mjd = float(t1) / 86400.0
                    return start_mjd, end_mjd, 0.5 * (start_mjd + end_mjd)
        except Exception:
            pass
        msmd.close()
    except Exception as e:
        logger.debug("Failed to extract time range from %s: %s", ms_path, e)
    return None, None, None


def _apply_and_image(
        ms_path: str,
        out_dir: Path,
        gaintables: List[str]) -> List[str]:
    """Apply calibration and produce a quick image; returns artifact paths."""
    artifacts: List[str] = []
    # Route temp files to scratch and chdir to output directory to avoid repo pollution
    try:
        if prepare_temp_environment is not None:
            prepare_temp_environment(os.getenv('CONTIMG_SCRATCH_DIR') or '/scratch/dsa110-contimg', cwd_to=os.fspath(out_dir))
    except Exception:
        pass
    # Apply to all fields by default
    try:
        from dsa110_contimg.calibration.applycal import apply_to_target
        from dsa110_contimg.imaging.cli import image_ms

        apply_to_target(ms_path, field="", gaintables=gaintables, calwt=True)
        imgroot = out_dir / (Path(ms_path).stem + ".img")
        # Use image_ms with quick=True for quick imaging (replaces calibration/imaging.py quick_image)
        image_ms(ms_path, imagename=str(imgroot), field="", quick=True, skip_fits=True)
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
            "SELECT status FROM ms_index WHERE path = ?",
            (os.fspath(ms),
             )).fetchone()
        if row and row[0] == "done":
            continue
        start_mjd, end_mjd, mid_mjd = _ms_time_range(os.fspath(ms))
        if mid_mjd is None:
            # Fallback: use current time in MJD
            from astropy.time import Time

            mid_mjd = Time.now().mjd
        applylist = get_active_applylist(registry_db, mid_mjd)
        if not applylist:
            logger.warning(
                "No active caltables for %s (mid MJD %.5f)",
                ms,
                mid_mjd)
            status = "skipped_no_caltables"
            ms_index_upsert(conn, os.fspath(ms), start_mjd=start_mjd, end_mjd=end_mjd, mid_mjd=mid_mjd, processed_at=time.time(), status=status)
            conn.commit()
            continue

        artifacts = _apply_and_image(os.fspath(ms), out_dir, applylist)
        status = "done" if artifacts else "failed"
        ms_index_upsert(conn, os.fspath(ms), start_mjd=start_mjd, end_mjd=end_mjd, mid_mjd=mid_mjd, processed_at=time.time(), status=status)
        for art in artifacts:
            images_insert(conn, art, os.fspath(ms), time.time(), "5min", 1 if art.endswith(".image.pbcor") else 0)
        conn.commit()
        processed += 1
        logger.info("Processed %s (artifacts: %d)", ms, len(artifacts))
    return processed


def cmd_scan(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    n = process_once(
        Path(
            args.ms_dir), Path(
            args.out_dir), Path(
                args.registry_db), Path(
                    args.products_db))
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
    if not hasattr(args, 'func'):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
