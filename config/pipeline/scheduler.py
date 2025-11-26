#!/usr/bin/env python3
"""
Simple scheduler for nightly mosaic and periodic housekeeping when running under Docker.

Environment variables:
  PIPELINE_PRODUCTS_DB     (e.g., /data/dsa110-contimg/state/db/products.sqlite3)
  PIPELINE_QUEUE_DB        (e.g., /data/dsa110-contimg/state/db/ingest.sqlite3)
  CONTIMG_SCRATCH_DIR      (for temp dir cleanup)

  SCHED_MOSAIC_ENABLE=1
  SCHED_MOSAIC_HOUR_UTC=3        # run after this UTC hour daily
  SCHED_MOSAIC_OUTPUT_DIR=/data/ms/mosaics
  SCHED_MOSAIC_NAME_PREFIX=night
  SCHED_MOSAIC_WINDOW_DAYS=1

  SCHED_HOUSEKEEP_ENABLE=1
  SCHED_HOUSEKEEP_INTERVAL_SEC=3600

This is a lightweight loop; for strict scheduling use cron.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess


def _epoch(dt: datetime) -> float:
    return dt.replace(tzinfo=timezone.utc).timestamp()


def run_housekeeping(queue_db: str, scratch_dir: str, inprog_timeout: float = 3600.0, collecting_timeout: float = 86400.0, temp_age: float = 86400.0) -> None:
    cmd = [
        "python",
        "ops/pipeline/housekeeping.py",
        "--queue-db", queue_db,
        "--scratch-dir", scratch_dir,
        "--in-progress-timeout", str(inprog_timeout),
        "--collecting-timeout", str(collecting_timeout),
        "--temp-age", str(temp_age),
    ]
    subprocess.run(cmd, check=False)


def run_mosaic(products_db: str, output_dir: str, name_prefix: str, window_days: int, hour_utc: int) -> None:
    now = datetime.now(timezone.utc)
    # Build mosaic for the previous UTC day once we're past the configured hour
    prev = (now - timedelta(days=1)).date()
    day_start = datetime(prev.year, prev.month, prev.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
    if now.hour < hour_utc:
        # Too early in the day, skip
        return
    name = f"{name_prefix}_{prev.strftime('%Y_%m_%d')}"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_base = out_dir / f"{name}.img"

    since = _epoch(day_start)
    until = _epoch(day_end)
    # Plan
    subprocess.run([
        "python", "-m", "dsa110_contimg.mosaic.cli", "plan",
        "--products-db", products_db,
        "--name", name,
        "--since", str(since),
        "--until", str(until),
    ], check=False)
    # Build
    subprocess.run([
        "python", "-m", "dsa110_contimg.mosaic.cli", "build",
        "--products-db", products_db,
        "--name", name,
        "--output", str(out_base),
    ], check=False)


def main() -> int:
    products_db = os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3")
    queue_db = os.getenv("PIPELINE_QUEUE_DB", "state/db/ingest.sqlite3")
    scratch_dir = os.getenv("CONTIMG_SCRATCH_DIR", "/tmp")

    mosaic_enable = os.getenv("SCHED_MOSAIC_ENABLE", "0") == "1"
    mosaic_hour = int(os.getenv("SCHED_MOSAIC_HOUR_UTC", "3"))
    mosaic_output = os.getenv("SCHED_MOSAIC_OUTPUT_DIR", "state/mosaics")
    mosaic_prefix = os.getenv("SCHED_MOSAIC_NAME_PREFIX", "night")
    mosaic_window_days = int(os.getenv("SCHED_MOSAIC_WINDOW_DAYS", "1"))

    hk_enable = os.getenv("SCHED_HOUSEKEEP_ENABLE", "1") == "1"
    hk_interval = float(os.getenv("SCHED_HOUSEKEEP_INTERVAL_SEC", "3600"))
    inprog_timeout = float(os.getenv("SCHED_INPROG_TIMEOUT", "3600"))
    collecting_timeout = float(os.getenv("SCHED_COLLECTING_TIMEOUT", "86400"))
    temp_age = float(os.getenv("SCHED_TEMP_AGE", "86400"))

    last_hk = 0.0
    last_mosaic_day = None

    while True:
        now = time.time()
        # housekeeping
        if hk_enable and (now - last_hk >= hk_interval):
            run_housekeeping(queue_db, scratch_dir, inprog_timeout, collecting_timeout, temp_age)
            last_hk = now

        # nightly mosaic (once per day)
        if mosaic_enable:
            today = datetime.now(timezone.utc).date()
            if last_mosaic_day != today:
                run_mosaic(products_db, mosaic_output, mosaic_prefix, mosaic_window_days, mosaic_hour)
                last_mosaic_day = today

        time.sleep(30.0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

