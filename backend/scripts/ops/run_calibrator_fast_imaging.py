#!/usr/bin/env python3
"""
Orchestration script to generate fast images of the 5 most recent peak transits
of calibrator 0834+555 using existing pipeline code.

This script:
1. Queries the database to find complete 16-subband HDF5 groups near 0834+555 transits
2. Ranks them by calibrator altitude (peak transit = highest altitude)
3. Converts HDF5 -> MS using the execution module
4. Runs calibration pipeline
5. Runs fast snapshot imaging (WSClean)

Prerequisites:
- casatools installed and importable
- wsclean in PATH or Docker with wsclean-everybeam:0.7.4 image
- HDF5 files indexed in pipeline.sqlite3 (hdf5_files table)
- Output directories exist and are writable

Usage:
    python scripts/ops/run_calibrator_fast_imaging.py --dry-run
    python scripts/ops/run_calibrator_fast_imaging.py --num-transits 5
    python scripts/ops/run_calibrator_fast_imaging.py --skip-calibration  # if MS already calibrated

Environment variables:
    CONTIMG_INPUT_DIR: Override default HDF5 input directory
    CONTIMG_OUTPUT_DIR: Override default MS output directory
    PIPELINE_DB: Override default database path
"""

from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
import astropy.units as u

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# 0834+555 coordinates (J2000)
CALIBRATOR_NAME = "0834+555"
CALIBRATOR_RA_DEG = 8 * 15 + 37 * 0.25 + 56.24 / 240  # ~129.48 deg
CALIBRATOR_DEC_DEG = 55 + 32 / 60 + 30.86 / 3600  # ~55.54 deg

# DSA-110 location
DSA110_LOCATION = EarthLocation(
    lat=37.2339 * u.deg, lon=-118.2821 * u.deg, height=1222 * u.m
)

# Transit window: 0834+555 transits roughly 12:30-13:10 UTC at DSA-110
TRANSIT_WINDOW_START = "12:30:00"
TRANSIT_WINDOW_END = "13:10:00"

# Pointing validation tolerance (degrees)
# DSA-110 primary beam FWHM ~ 2.7° at 1.4 GHz (4.65m dishes)
# Use HWHM (~1.35°) to ensure source is within 50% power point
POINTING_TOLERANCE_DEG = 1.35

# Default paths (can be overridden by environment or config)
DEFAULT_DB_PATH = Path("/data/dsa110-contimg/state/db/pipeline.sqlite3")
DEFAULT_INPUT_DIR = Path("/data/incoming")
DEFAULT_OUTPUT_DIR = Path("/stage/dsa110-contimg/ms")
DEFAULT_CALTABLES_DIR = Path("/stage/dsa110-contimg/caltables")
DEFAULT_IMAGES_DIR = Path("/stage/dsa110-contimg/images")


@dataclass
class TransitObservation:
    """A complete subband group observation near a calibrator transit."""

    group_id: str
    timestamp_iso: str
    file_count: int
    altitude_deg: float
    azimuth_deg: float
    file_paths: List[str]
    pointing_dec_deg: Optional[float] = None  # Actual telescope pointing Dec
    pointing_validated: bool = False  # Whether pointing was checked against calibrator

    @property
    def is_complete(self) -> bool:
        return self.file_count == 16

    @property
    def is_near_meridian(self) -> bool:
        """Check if calibrator was near meridian (az ~ 0 or 360 for northern sources)."""
        return self.azimuth_deg < 30 or self.azimuth_deg > 330


def get_pointing_from_hdf5(hdf5_path: str) -> Optional[float]:
    """
    Extract the pointing declination from an HDF5 file.
    
    Returns:
        Declination in degrees, or None if not found.
    """
    import h5py
    import numpy as np
    
    try:
        with h5py.File(hdf5_path, 'r') as h:
            # Try the standard location for phase center dec
            if 'Header/extra_keywords/phase_center_dec' in h:
                dec_rad = h['Header/extra_keywords/phase_center_dec'][()]
                return float(np.degrees(dec_rad))
            # Fallback to other possible locations
            if 'Header/phase_center_app_dec' in h:
                dec_rad = h['Header/phase_center_app_dec'][()]
                return float(np.degrees(dec_rad))
    except Exception as e:
        logger.debug(f"Could not read pointing from {hdf5_path}: {e}")
    return None


def validate_pointing_matches_calibrator(
    file_paths: List[str],
    calibrator_dec_deg: float = CALIBRATOR_DEC_DEG,
    tolerance_deg: float = POINTING_TOLERANCE_DEG,
) -> tuple[bool, Optional[float]]:
    """
    Validate that an observation's pointing matches the expected calibrator.
    
    Args:
        file_paths: List of HDF5 file paths for this observation
        calibrator_dec_deg: Expected calibrator declination
        tolerance_deg: Maximum allowed deviation in degrees
        
    Returns:
        Tuple of (is_valid, actual_dec_deg)
    """
    # Check pointing from the first available file
    for path in file_paths[:3]:  # Check up to 3 files for robustness
        pointing_dec = get_pointing_from_hdf5(path)
        if pointing_dec is not None:
            offset = abs(pointing_dec - calibrator_dec_deg)
            is_valid = offset <= tolerance_deg
            if not is_valid:
                logger.warning(
                    f"Pointing mismatch: Dec={pointing_dec:.2f}° vs expected "
                    f"{calibrator_dec_deg:.2f}° (offset={offset:.2f}°, tolerance={tolerance_deg}°)"
                )
            return is_valid, pointing_dec
    
    logger.warning(f"Could not extract pointing from any of {len(file_paths)} files")
    return False, None


# =============================================================================
# Database Queries
# =============================================================================


def _merge_split_groups(
    cur: sqlite3.Cursor,
    date: str,
    time_start: str,
    time_end: str,
    tolerance_seconds: int = 5,
) -> List[dict]:
    """
    Find and merge split subband groups that should be one observation.
    
    The HDF5 indexer assigns group_id based on exact filename timestamps,
    but subbands from the same observation can have timestamps 1-2 seconds
    apart due to I/O delays. This function merges adjacent groups.
    
    Args:
        cur: Database cursor
        date: Date string (YYYY-MM-DD)
        time_start: Start time (HH:MM:SS)
        time_end: End time (HH:MM:SS)
        tolerance_seconds: Max seconds between groups to merge
        
    Returns:
        List of merged group dicts with keys: group_id, timestamp_iso, 
        file_count, file_paths, all_group_ids
    """
    # Get all files in the time window for this date
    cur.execute(
        """
        SELECT path, group_id, subband_code, timestamp_iso
        FROM hdf5_files
        WHERE date(timestamp_iso) = ?
          AND time(timestamp_iso) BETWEEN ? AND ?
        ORDER BY timestamp_iso, subband_code
        """,
        (date, time_start, time_end),
    )
    rows = cur.fetchall()
    
    if not rows:
        return []
    
    # Group files by their group_id first
    from collections import defaultdict
    groups_by_id = defaultdict(list)
    group_timestamps = {}
    
    for path, group_id, subband_code, timestamp_iso in rows:
        groups_by_id[group_id].append((path, subband_code))
        if group_id not in group_timestamps:
            group_timestamps[group_id] = timestamp_iso
    
    # Sort group_ids by timestamp
    sorted_group_ids = sorted(groups_by_id.keys(), key=lambda g: group_timestamps[g])
    
    # Merge adjacent groups within tolerance
    merged_groups = []
    current_merge = None
    
    for group_id in sorted_group_ids:
        ts_iso = group_timestamps[group_id]
        files = groups_by_id[group_id]
        
        if current_merge is None:
            # Start new merge group
            current_merge = {
                "group_id": group_id,
                "timestamp_iso": ts_iso,
                "file_paths": [f[0] for f in files],
                "subbands": set(f[1] for f in files),
                "all_group_ids": [group_id],
                "last_timestamp": datetime.fromisoformat(ts_iso),
            }
        else:
            # Check if this group should be merged with current
            this_time = datetime.fromisoformat(ts_iso)
            time_diff = abs((this_time - current_merge["last_timestamp"]).total_seconds())
            
            if time_diff <= tolerance_seconds:
                # Merge into current group
                current_merge["file_paths"].extend([f[0] for f in files])
                current_merge["subbands"].update(f[1] for f in files)
                current_merge["all_group_ids"].append(group_id)
                current_merge["last_timestamp"] = max(current_merge["last_timestamp"], this_time)
            else:
                # Finalize current merge and start new one
                current_merge["file_count"] = len(current_merge["file_paths"])
                del current_merge["last_timestamp"]
                del current_merge["subbands"]
                merged_groups.append(current_merge)
                
                current_merge = {
                    "group_id": group_id,
                    "timestamp_iso": ts_iso,
                    "file_paths": [f[0] for f in files],
                    "subbands": set(f[1] for f in files),
                    "all_group_ids": [group_id],
                    "last_timestamp": this_time,
                }
    
    # Don't forget the last group
    if current_merge is not None:
        current_merge["file_count"] = len(current_merge["file_paths"])
        del current_merge["last_timestamp"]
        del current_merge["subbands"]
        merged_groups.append(current_merge)
    
    return merged_groups


def find_transit_observations(
    db_path: Path,
    num_transits: int = 5,
    min_subbands: int = 16,
) -> List[TransitObservation]:
    """
    Find the PEAK transit observation for each day with 0834+555 data.
    
    A source only transits once per day. The DSA-110 records multiple
    5-minute observation chunks during the ~40 minute transit window.
    This function:
    1. Groups all chunks by date
    2. Merges split subbands (1-2 second timestamp differences)
    3. Selects the chunk closest to peak transit (highest altitude)
    4. Returns ONE observation per transit day
    
    Returns groups sorted by calibrator altitude (highest = best transit).
    """
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Get distinct dates that have data in the transit window
    cur.execute(
        """
        SELECT DISTINCT date(timestamp_iso) as obs_date
        FROM hdf5_files
        WHERE time(timestamp_iso) BETWEEN ? AND ?
        ORDER BY obs_date DESC
        LIMIT 60
        """,
        (TRANSIT_WINDOW_START, TRANSIT_WINDOW_END),
    )
    dates = [r[0] for r in cur.fetchall()]

    results = []
    cal_coord = SkyCoord(
        ra=CALIBRATOR_RA_DEG * u.deg, dec=CALIBRATOR_DEC_DEG * u.deg, frame="icrs"
    )

    for obs_date in dates:
        # Get merged groups for this date
        merged_groups = _merge_split_groups(
            cur, obs_date, TRANSIT_WINDOW_START, TRANSIT_WINDOW_END
        )
        
        # Find the BEST (peak transit) observation for this day
        # Peak transit = highest altitude = closest to meridian crossing
        best_for_day = None
        best_altitude = -90.0
        
        for mg in merged_groups:
            # Skip incomplete groups
            if mg["file_count"] < min_subbands:
                continue
                
            try:
                obs_time = Time(mg["timestamp_iso"], format="isot")
                altaz = cal_coord.transform_to(
                    AltAz(obstime=obs_time, location=DSA110_LOCATION)
                )
                
                altitude = altaz.alt.deg
                
                # Track the highest altitude observation for this day
                if altitude > best_altitude:
                    best_altitude = altitude
                    
                    # Note if this was a merged group
                    group_id = mg["group_id"]
                    if len(mg["all_group_ids"]) > 1:
                        logger.debug(
                            f"Merged {len(mg['all_group_ids'])} split groups into {group_id}: "
                            f"{mg['all_group_ids']}"
                        )
                    
                    best_for_day = TransitObservation(
                        group_id=group_id,
                        timestamp_iso=mg["timestamp_iso"],
                        file_count=mg["file_count"],
                        altitude_deg=altitude,
                        azimuth_deg=altaz.az.deg,
                        file_paths=mg["file_paths"],
                    )
                    
            except Exception as e:
                logger.warning(f"Error processing group {mg['group_id']}: {e}")
                continue
        
        # Add the best observation for this day (ONE per day)
        # BUT FIRST validate that pointing actually matches the calibrator!
        if best_for_day is not None:
            is_valid, actual_dec = validate_pointing_matches_calibrator(
                best_for_day.file_paths
            )
            best_for_day.pointing_dec_deg = actual_dec
            best_for_day.pointing_validated = is_valid
            
            if is_valid:
                results.append(best_for_day)
                logger.debug(
                    f"Selected peak transit for {obs_date}: {best_for_day.group_id} "
                    f"(alt={best_for_day.altitude_deg:.1f}°, dec={actual_dec:.2f}°)"
                )
            else:
                dec_str = f"{actual_dec:.2f}" if actual_dec is not None else "unknown"
                logger.info(
                    f"Skipping {obs_date} {best_for_day.group_id}: pointing Dec={dec_str}° "
                    f"does not match {CALIBRATOR_NAME} (expected ~{CALIBRATOR_DEC_DEG:.2f}°)"
                )
        
        # Stop if we have enough results
        if len(results) >= num_transits:
            break

    conn.close()

    # Sort by altitude (highest first = best transit)
    results.sort(key=lambda x: -x.altitude_deg)

    return results[:num_transits]


# =============================================================================
# Pipeline Steps
# =============================================================================


def convert_hdf5_to_ms(
    obs: TransitObservation,
    input_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
) -> Optional[Path]:
    """
    Convert HDF5 subband group to Measurement Set using execution module.

    Returns path to generated MS, or None if dry_run or error.
    """
    ms_name = f"{CALIBRATOR_NAME}_{obs.group_id.replace(':', '-')}.ms"
    ms_path = output_dir / ms_name

    if ms_path.exists():
        logger.info(f"MS already exists: {ms_path}")
        return ms_path

    if dry_run:
        logger.info(f"[DRY-RUN] Would convert {obs.group_id} -> {ms_path}")
        return None

    logger.info(f"Converting {obs.group_id} to {ms_path}")

    try:
        from dsa110_contimg.execution import ExecutionTask, get_executor
        from dsa110_contimg.execution.task import ResourceLimits

        # Create time window for this specific group (±30 seconds)
        start_time = obs.timestamp_iso
        # Parse and add 30 seconds for end time
        from datetime import timedelta

        start_dt = datetime.fromisoformat(obs.timestamp_iso)
        end_dt = start_dt + timedelta(seconds=30)
        end_time = end_dt.isoformat()

        limits = ResourceLimits(
            memory_mb=8192,
            omp_threads=4,
            max_workers=4,
        )

        task = ExecutionTask(
            group_id=obs.group_id,
            input_dir=input_dir,
            output_dir=output_dir,
            scratch_dir=output_dir / "scratch",
            start_time=start_time,
            end_time=end_time,
            writer="auto",
            resource_limits=limits,
        )

        executor = get_executor(mode="inprocess")
        result = executor.run(task)

        if result.success and result.ms_path:
            logger.info(f"Conversion successful: {result.ms_path}")
            return Path(result.ms_path)
        else:
            logger.error(f"Conversion failed: {result.error_message}")
            return None

    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return None


def run_calibration(
    ms_path: Path,
    caltables_dir: Path,
    db_path: Path,
    dry_run: bool = False,
    calibrator_name: str | None = None,
) -> bool:
    """
    Run calibration pipeline on the MS.

    Args:
        ms_path: Path to the MS file
        caltables_dir: Directory for calibration tables
        db_path: Path to pipeline database
        dry_run: If True, skip actual calibration
        calibrator_name: Expected calibrator name (e.g., "0834+555")

    Returns True if successful.
    """
    if dry_run:
        logger.info(f"[DRY-RUN] Would calibrate {ms_path}")
        return True

    logger.info(f"Running calibration on {ms_path} (calibrator={calibrator_name})")

    try:
        import asyncio
        from dsa110_contimg.calibration.pipeline import (
            CalibrationPipelineConfig,
            run_calibration_pipeline,
        )

        config = CalibrationPipelineConfig(
            database_path=db_path,
            caltable_dir=caltables_dir,
        )

        result = asyncio.run(
            run_calibration_pipeline(
                ms_path=str(ms_path),
                target_field="0",  # Usually field 0 for calibrator
                config=config,
                do_k=False,  # Skip K calibration for speed
                calibrator_name=calibrator_name,
            )
        )

        if result.success:
            logger.info(f"Calibration successful. Tables: {result.gaintables}")
            return True
        else:
            logger.error(f"Calibration failed: {result.errors}")
            return False

    except Exception as e:
        logger.error(f"Calibration error: {e}")
        return False


def run_fast_imaging(
    ms_path: Path,
    images_dir: Path,
    interval_seconds: float = 30.0,
    dry_run: bool = False,
) -> Optional[List[Path]]:
    """
    Run fast snapshot imaging using WSClean.

    Returns list of generated FITS images, or None if dry_run or error.
    """
    output_prefix = images_dir / ms_path.stem

    if dry_run:
        logger.info(f"[DRY-RUN] Would run fast imaging on {ms_path}")
        logger.info(f"[DRY-RUN] Output prefix: {output_prefix}")
        return None

    logger.info(f"Running fast imaging on {ms_path}")

    try:
        from dsa110_contimg.imaging.fast_imaging import run_fast_imaging as _run_fast

        _run_fast(
            ms_path=str(ms_path),
            interval_seconds=interval_seconds,
            imsize=1024,
            cell_arcsec=2.5,
            output_prefix=str(output_prefix),
        )

        # Find generated images
        import glob

        images = list(images_dir.glob(f"{ms_path.stem}*-image.fits"))
        logger.info(f"Generated {len(images)} snapshot images")
        return images

    except Exception as e:
        logger.error(f"Fast imaging error: {e}")
        return None


# =============================================================================
# Main Orchestration
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Generate fast images of 0834+555 peak transits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--num-transits",
        type=int,
        default=5,
        help="Number of transit observations to process (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    parser.add_argument(
        "--skip-calibration",
        action="store_true",
        help="Skip calibration step (use if MS already calibrated)",
    )
    parser.add_argument(
        "--skip-imaging",
        action="store_true",
        help="Skip imaging step (only convert and calibrate)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=os.environ.get("PIPELINE_DB", DEFAULT_DB_PATH),
        help=f"Pipeline database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=os.environ.get("CONTIMG_INPUT_DIR", DEFAULT_INPUT_DIR),
        help=f"HDF5 input directory (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=os.environ.get("CONTIMG_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
        help=f"MS output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Snapshot interval in seconds (default: 30)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate paths
    if not args.db_path.exists():
        logger.error(f"Database not found: {args.db_path}")
        sys.exit(1)

    if not args.input_dir.exists():
        logger.error(f"Input directory not found: {args.input_dir}")
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    DEFAULT_CALTABLES_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Find transit observations
    logger.info(f"Finding {args.num_transits} best 0834+555 transit observations...")
    observations = find_transit_observations(
        db_path=args.db_path,
        num_transits=args.num_transits,
    )

    if not observations:
        logger.error("No complete transit observations found!")
        sys.exit(1)

    logger.info(f"Found {len(observations)} transit observations:")
    for i, obs in enumerate(observations, 1):
        dec_str = f"{obs.pointing_dec_deg:.2f}" if obs.pointing_dec_deg is not None else "?"
        logger.info(
            f"  {i}. {obs.timestamp_iso} | dec={dec_str}° | "
            f"files={obs.file_count} | complete={obs.is_complete}"
        )

    if args.dry_run:
        logger.info("\n[DRY-RUN MODE] - No changes will be made\n")

    # Step 2-4: Process each observation
    results = []
    for i, obs in enumerate(observations, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing transit {i}/{len(observations)}: {obs.group_id}")
        logger.info(f"{'='*60}")

        # Step 2: Convert HDF5 -> MS
        ms_path = convert_hdf5_to_ms(
            obs=obs,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            dry_run=args.dry_run,
        )

        if not args.dry_run and not ms_path:
            logger.warning(f"Skipping {obs.group_id} due to conversion failure")
            results.append({"group_id": obs.group_id, "status": "conversion_failed"})
            continue

        # For dry-run, create a placeholder path
        if args.dry_run:
            ms_path = args.output_dir / f"{CALIBRATOR_NAME}_{obs.group_id.replace(':', '-')}.ms"

        # Step 3: Calibrate
        if not args.skip_calibration:
            cal_success = run_calibration(
                ms_path=ms_path,
                caltables_dir=DEFAULT_CALTABLES_DIR,
                db_path=args.db_path,
                dry_run=args.dry_run,
            )
            if not args.dry_run and not cal_success:
                logger.warning(f"Skipping imaging for {obs.group_id} due to calibration failure")
                results.append({"group_id": obs.group_id, "status": "calibration_failed"})
                continue

        # Step 4: Fast imaging
        if not args.skip_imaging:
            images = run_fast_imaging(
                ms_path=ms_path,
                images_dir=DEFAULT_IMAGES_DIR,
                interval_seconds=args.interval,
                dry_run=args.dry_run,
            )
            results.append({
                "group_id": obs.group_id,
                "status": "completed" if images or args.dry_run else "imaging_failed",
                "ms_path": str(ms_path) if ms_path else None,
                "images": [str(p) for p in (images or [])],
            })
        else:
            results.append({
                "group_id": obs.group_id,
                "status": "completed",
                "ms_path": str(ms_path) if ms_path else None,
            })

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    completed = sum(1 for r in results if r["status"] == "completed")
    logger.info(f"Completed: {completed}/{len(observations)}")
    for r in results:
        status_emoji = "✓" if r["status"] == "completed" else "✗"
        logger.info(f"  {status_emoji} {r['group_id']}: {r['status']}")

    return 0 if completed == len(observations) else 1


if __name__ == "__main__":
    sys.exit(main())
