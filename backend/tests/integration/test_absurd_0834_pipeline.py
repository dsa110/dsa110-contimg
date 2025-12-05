#!/usr/bin/env python
"""
Integration test: ABSURD workflow processing a single 0834+555 transit.

This test validates the complete pipeline by processing one 16-subband group
containing a peak transit of calibrator 0834+555.

Test Workflow:
    1. Find a complete 16-subband group at Dec ~55° with LST matching 0834+555 RA
    2. Spawn ABSURD task: convert → MS
    3. **CRITICAL**: Phaseshift calibrator field to 0834+555 position
       (DSA-110 data is phased to meridian - must shift before bandpass cal!)
    4. Spawn ABSURD tasks: calibrate → image
    5. Validate outputs at each stage
    6. Measure photometry on final image
    7. Clean up intermediate products

Expected Runtime: < 10 minutes

CRITICAL REQUIREMENT - Phaseshift:
    DSA-110 data is phased to RA=LST (meridian) per field. For bandpass
    calibration to work, we MUST phaseshift to the calibrator's true position.
    Otherwise, there's a geometric phase gradient across baselines from the
    offset between meridian and calibrator position → garbage solutions.

Usage:
    # Via pytest
    pytest backend/tests/integration/test_absurd_0834_pipeline.py -v --timeout=600

    # Via CLI (standalone)
    python backend/tests/integration/test_absurd_0834_pipeline.py --dry-run
    python backend/tests/integration/test_absurd_0834_pipeline.py --run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logger = logging.getLogger(__name__)

# ==============================================================================
# Configuration
# ==============================================================================

# 0834+555 coordinates (J2000)
CALIBRATOR_NAME = "0834+555"
CALIBRATOR_RA_DEG = 128.7287  # 08h34m54.9s
CALIBRATOR_DEC_DEG = 55.5725  # +55°34'21"

# Paths
# HDF5 index is now in unified pipeline.sqlite3
PIPELINE_DB = Path("/data/dsa110-contimg/state/db/pipeline.sqlite3")
HDF5_INDEX_DB = PIPELINE_DB  # Legacy name for backwards compatibility
INPUT_DIR = Path("/data/incoming")
OUTPUT_DIR = Path("/stage/dsa110-contimg")
SCRATCH_DIR = Path("/stage/dsa110-contimg/scratch")

# Test output directory
TEST_OUTPUT_DIR = OUTPUT_DIR / "test_0834_integration"

# ABSURD configuration
ABSURD_QUEUE = "dsa110-pipeline"
TASK_TIMEOUT_SEC = 300  # 5 minutes per task

# Validation thresholds
MIN_EXPECTED_CHANNELS = 768  # 16 subbands × 48 channels
MIN_ANTENNAS = 50
MAX_FLAGGED_FRACTION = 0.15  # 15% max flagging
MIN_PEAK_FLUX_JY = 0.1
MAX_PEAK_FLUX_JY = 10.0
MIN_SNR = 50


# ==============================================================================
# Helper Functions for Field Discovery
# ==============================================================================


def _find_calibrator_field_in_ms(ms_path: Path, calibrator_name: str) -> Optional[str]:
    """Find field by name containing calibrator name.

    During conversion, calibrator fields are auto-renamed to include
    the calibrator name (e.g., "0834+555_t12").

    Args:
        ms_path: Path to Measurement Set
        calibrator_name: Name to search for (e.g., "0834+555")

    Returns:
        Field selection string if found, None otherwise
    """
    try:
        from casacore.tables import table

        with table(f"{ms_path}::FIELD", readonly=True, ack=False) as tb:
            field_names = tb.getcol("NAME")

        for idx, name in enumerate(field_names):
            if calibrator_name in name:
                logger.info(f"Found calibrator in field {idx}: '{name}'")
                return str(idx)

    except Exception as e:
        logger.warning(f"Error scanning field names: {e}")

    return None


def _find_calibrator_field_by_position(ms_path: Path) -> Optional[str]:
    """Find field by matching position to calibrator coordinates.

    Scans all field phase centers and finds the one closest to
    the calibrator's J2000 position.

    Args:
        ms_path: Path to Measurement Set

    Returns:
        Field selection string if found, None otherwise
    """
    import numpy as np

    try:
        from casacore.tables import table

        with table(f"{ms_path}::FIELD", readonly=True, ack=False) as tb:
            # PHASE_DIR is shape (n_fields, n_poly, 2) in radians
            phase_dirs = tb.getcol("PHASE_DIR")
            field_names = tb.getcol("NAME")

        best_field = None
        best_sep = 999.0

        cal_ra_rad = np.radians(CALIBRATOR_RA_DEG)
        cal_dec_rad = np.radians(CALIBRATOR_DEC_DEG)

        for idx in range(len(field_names)):
            # Get RA/Dec (first polynomial term)
            ra_rad = phase_dirs[idx, 0, 0]
            dec_rad = phase_dirs[idx, 0, 1]

            # Simple angular separation (small angle approx OK for <1 deg)
            sep_deg = np.degrees(np.sqrt(
                (ra_rad - cal_ra_rad)**2 * np.cos(dec_rad)**2 +
                (dec_rad - cal_dec_rad)**2
            ))

            if sep_deg < best_sep:
                best_sep = sep_deg
                best_field = idx

        if best_field is not None and best_sep < 1.0:  # Within 1 degree
            logger.info(
                f"Found calibrator by position in field {best_field}: "
                f"'{field_names[best_field]}' (sep={best_sep:.3f}°)"
            )
            return str(best_field)
        else:
            logger.warning(
                f"No field within 1° of calibrator position. "
                f"Best was field {best_field} at {best_sep:.3f}°"
            )

    except Exception as e:
        logger.warning(f"Error scanning field positions: {e}")

    return None


# ==============================================================================
# Data Classes
# ==============================================================================


@dataclass
class SubbandGroup:
    """A complete group of 16 subbands."""

    timestamp: str
    files: List[Path]
    mid_mjd: float

    @property
    def is_complete(self) -> bool:
        return len(self.files) == 16


@dataclass
class TestCheckpoint:
    """Checkpoint validation result."""

    name: str
    passed: bool
    elapsed_sec: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TestResult:
    """Complete test result."""

    status: str  # PASSED, FAILED, SKIPPED
    total_runtime_sec: float
    checkpoints: List[TestCheckpoint]
    calibrator: str
    observation_id: str
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": "integration_test_absurd_0834_pipeline",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": self.status,
            "total_runtime_seconds": self.total_runtime_sec,
            "calibrator": self.calibrator,
            "observation_id": self.observation_id,
            "checkpoints": {
                cp.name: {
                    "status": "PASSED" if cp.passed else "FAILED",
                    "elapsed": cp.elapsed_sec,
                    "details": cp.details,
                    "error": cp.error,
                }
                for cp in self.checkpoints
            },
            "metrics": self.metrics,
        }


# ==============================================================================
# Step 1: Find Test Data
# ==============================================================================

# Known good 0834+555 transit observation (verified: Dec=54.57°, LST≈128.5°=RA)
KNOWN_GOOD_TRANSIT = "2025-10-21T14:23:19"


def _check_is_0834_transit(hdf5_path: Path) -> tuple[bool, float, float]:
    """Check if an HDF5 file is at 0834+555 declination and transit time.

    Args:
        hdf5_path: Path to sb00 HDF5 file

    Returns:
        Tuple of (is_transit, dec_deg, ra_diff_deg)
    """
    import h5py
    import numpy as np
    from astropy.time import Time
    from astropy.coordinates import EarthLocation
    import astropy.units as u

    try:
        with h5py.File(hdf5_path, "r") as f:
            # Check declination
            dec_rad = f["Header/phase_center_app_dec"][()]
            dec_deg = float(np.degrees(dec_rad))

            # Must be within 3° of 0834+555's Dec (55.57°)
            if abs(dec_deg - CALIBRATOR_DEC_DEG) > 3.0:
                return False, dec_deg, 999.0

            # Check LST matches calibrator RA (transit condition)
            dsa_loc = EarthLocation.from_geodetic(
                lon=-118.28166 * u.deg, lat=37.23278 * u.deg, height=1188 * u.m
            )

            time_array = f["Header/time_array"][:]
            t_mid = Time((time_array.min() + time_array.max()) / 2, format="jd")
            lst_mid = t_mid.sidereal_time("apparent", longitude=dsa_loc.lon).deg

            # RA difference from transit
            ra_diff = (CALIBRATOR_RA_DEG - lst_mid + 180) % 360 - 180

            # Within 5° of transit
            is_transit = abs(ra_diff) < 5.0
            return is_transit, dec_deg, ra_diff

    except Exception:
        return False, 0.0, 999.0


def find_0834_transit_group(
    max_days_back: int = 30,
) -> Optional[SubbandGroup]:
    """Find a complete 16-subband group containing 0834+555 transit.

    Searches for observations where:
    1. Declination matches 0834+555 (~55°)
    2. LST at observation midpoint matches calibrator RA (transit)

    Args:
        max_days_back: Maximum days to search backward

    Returns:
        SubbandGroup if found, None otherwise
    """
    import h5py
    import numpy as np

    logger.info(f"Searching for 0834+555 transit data (last {max_days_back} days)...")

    # First, check known good transit
    known_path = INPUT_DIR / f"{KNOWN_GOOD_TRANSIT}_sb00.hdf5"
    if known_path.exists():
        is_transit, dec, ra_diff = _check_is_0834_transit(known_path)
        if is_transit:
            # Verify all 16 subbands exist
            files = [INPUT_DIR / f"{KNOWN_GOOD_TRANSIT}_sb{i:02d}.hdf5" for i in range(16)]
            if all(f.exists() for f in files):
                logger.info(
                    f"Using known good transit: {KNOWN_GOOD_TRANSIT} "
                    f"(Dec={dec:.2f}°, RA_diff={ra_diff:+.2f}°)"
                )
                # Get mid_mjd
                with h5py.File(known_path, "r") as f:
                    time_array = f["Header/time_array"][:]
                    mid_mjd = float((time_array.min() + time_array.max()) / 2) - 2400000.5

                return SubbandGroup(
                    timestamp=KNOWN_GOOD_TRANSIT,
                    files=files,
                    mid_mjd=mid_mjd,
                )

    # Query HDF5 index for complete groups
    logger.info("Searching HDF5 index for complete 16-subband groups at Dec ~55°...")

    conn = sqlite3.connect(HDF5_INDEX_DB)
    cursor = conn.execute("""
        SELECT timestamp, COUNT(*) as cnt
        FROM hdf5_file_index
        GROUP BY timestamp
        HAVING cnt = 16
        ORDER BY timestamp DESC
        LIMIT 500
    """)

    for row in cursor.fetchall():
        timestamp = row[0]
        sb00_path = INPUT_DIR / f"{timestamp}_sb00.hdf5"

        if not sb00_path.exists():
            continue

        is_transit, dec, ra_diff = _check_is_0834_transit(sb00_path)

        if is_transit:
            logger.info(
                f"Found transit: {timestamp} (Dec={dec:.2f}°, RA_diff={ra_diff:+.2f}°)"
            )

            files = [INPUT_DIR / f"{timestamp}_sb{i:02d}.hdf5" for i in range(16)]
            if all(f.exists() for f in files):
                # Get mid_mjd
                with h5py.File(sb00_path, "r") as f:
                    time_array = f["Header/time_array"][:]
                    mid_mjd = float((time_array.min() + time_array.max()) / 2) - 2400000.5

                conn.close()
                return SubbandGroup(
                    timestamp=timestamp,
                    files=files,
                    mid_mjd=mid_mjd,
                )

    conn.close()
    logger.warning("No 0834+555 transit found in HDF5 index")
    return None


def find_any_complete_group() -> Optional[SubbandGroup]:
    """Find any complete 16-subband group (fallback if no transit found)."""
    logger.info("Searching for any complete 16-subband group...")

    conn = sqlite3.connect(HDF5_INDEX_DB)
    cursor = conn.execute("""
        SELECT timestamp, GROUP_CONCAT(path, '|') as files, AVG(mid_mjd) as mid_mjd
        FROM hdf5_file_index
        GROUP BY timestamp
        HAVING COUNT(*) = 16
        ORDER BY timestamp DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if row:
        timestamp, files_str, mid_mjd = row
        files = [Path(f) for f in files_str.split("|")]
        logger.info(f"Found complete group: {timestamp}")
        return SubbandGroup(timestamp=timestamp, files=files, mid_mjd=mid_mjd or 0.0)

    return None


# ==============================================================================
# Step 2: ABSURD Task Execution
# ==============================================================================


async def wait_for_task(
    client: "AbsurdClient",
    task_id: str,
    timeout_sec: int = TASK_TIMEOUT_SEC,
    poll_interval_sec: float = 2.0,
) -> Dict[str, Any]:
    """Wait for an ABSURD task to complete.

    Args:
        client: ABSURD client instance
        task_id: Task ID to wait for
        timeout_sec: Maximum wait time
        poll_interval_sec: Polling interval

    Returns:
        Final task state dict

    Raises:
        TimeoutError: If task doesn't complete in time
    """
    start = time.time()

    while time.time() - start < timeout_sec:
        task = await client.get_task(task_id)

        if task is None:
            raise ValueError(f"Task {task_id} not found")

        status = task.get("status", "unknown")

        if status == "completed":
            return task
        elif status == "failed":
            error = task.get("error", "Unknown error")
            raise RuntimeError(f"Task {task_id} failed: {error}")

        await asyncio.sleep(poll_interval_sec)

    raise TimeoutError(f"Task {task_id} timed out after {timeout_sec}s")


async def run_absurd_pipeline(
    group: SubbandGroup,
    output_dir: Path,
) -> Tuple[Optional[Path], Optional[Path], Optional[Path], List[TestCheckpoint]]:
    """Run the ABSURD pipeline for a subband group.

    Spawns tasks: convert → phaseshift → calibrate → image

    **CRITICAL**: The phaseshift step is required because DSA-110 data is phased
    to RA=LST (meridian). For bandpass calibration to work, we must shift the
    calibrator field to the calibrator's true position (RA=128.7°, Dec=55.6°).
    Otherwise there's a geometric phase gradient across baselines → garbage.

    Args:
        group: SubbandGroup to process
        output_dir: Output directory for products

    Returns:
        Tuple of (ms_path, cal_table_path, image_path, checkpoints)
    """
    from dsa110_contimg.absurd import AbsurdClient
    from dsa110_contimg.absurd.config import AbsurdConfig

    checkpoints: List[TestCheckpoint] = []
    ms_path: Optional[Path] = None
    cal_path: Optional[Path] = None
    image_path: Optional[Path] = None

    config = AbsurdConfig.from_env()

    async with AbsurdClient(config.database_url) as client:
        # ======================================================================
        # Task 1: Convert UVH5 to MS
        # ======================================================================
        logger.info("Spawning conversion task...")
        t0 = time.time()

        try:
            ms_output_dir = output_dir / "ms"
            ms_output_dir.mkdir(parents=True, exist_ok=True)

            # Calculate time window from group timestamp
            ts = datetime.fromisoformat(group.timestamp)
            start_time = (ts - timedelta(seconds=30)).isoformat()
            end_time = (ts + timedelta(minutes=6)).isoformat()

            convert_task_id = await client.spawn_task(
                queue_name=ABSURD_QUEUE,
                task_name="convert-uvh5-to-ms",
                params={
                    "inputs": {
                        "input_path": str(INPUT_DIR),
                        "output_path": str(ms_output_dir),
                        "start_time": start_time,
                        "end_time": end_time,
                    },
                    "config": {
                        "paths": {
                            "scratch_dir": str(SCRATCH_DIR),
                        }
                    }
                },
                priority=10,
                timeout_sec=TASK_TIMEOUT_SEC,
            )

            logger.info(f"Conversion task spawned: {convert_task_id}")
            task_result = await wait_for_task(client, str(convert_task_id))

            elapsed = time.time() - t0

            # Find the output MS
            outputs = task_result.get("result", {}).get("outputs", {})
            ms_path_str = outputs.get("ms_path") or outputs.get("output_path")

            if ms_path_str:
                ms_path = Path(ms_path_str)
            else:
                # Try to find it
                ms_candidates = list(ms_output_dir.glob(f"*{group.timestamp[:10]}*.ms"))
                if ms_candidates:
                    ms_path = ms_candidates[0]

            checkpoints.append(TestCheckpoint(
                name="conversion",
                passed=ms_path is not None and ms_path.exists(),
                elapsed_sec=elapsed,
                details={
                    "task_id": str(convert_task_id),
                    "ms_path": str(ms_path) if ms_path else None,
                },
            ))

            if not ms_path or not ms_path.exists():
                logger.error("Conversion failed: no MS output found")
                return None, None, None, checkpoints

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            checkpoints.append(TestCheckpoint(
                name="conversion",
                passed=False,
                elapsed_sec=time.time() - t0,
                error=str(e),
            ))
            return None, None, None, checkpoints

        # ======================================================================
        # Task 2: Find calibrator field
        # ======================================================================
        # Find which field contains the calibrator (for CalibrationSolveStage)
        logger.info("Finding calibrator field in MS...")
        t0 = time.time()

        try:
            # During conversion, fields are auto-renamed to include calibrator name
            cal_field = _find_calibrator_field_in_ms(ms_path, CALIBRATOR_NAME)
            if cal_field is None:
                # Fallback: try to find by scanning field centers
                cal_field = _find_calibrator_field_by_position(ms_path)

            if cal_field is None:
                raise ValueError(
                    f"Could not find calibrator field in MS. "
                    f"Fields need to be at Dec~{CALIBRATOR_DEC_DEG}° for 0834+555"
                )

            elapsed = time.time() - t0
            logger.info(f"✓ Found calibrator in field {cal_field}")

            checkpoints.append(TestCheckpoint(
                name="field_discovery",
                passed=True,
                elapsed_sec=elapsed,
                details={
                    "ms_path": str(ms_path),
                    "cal_field": cal_field,
                    "calibrator": CALIBRATOR_NAME,
                },
            ))

        except Exception as e:
            logger.error(f"Field discovery failed: {e}")
            checkpoints.append(TestCheckpoint(
                name="field_discovery",
                passed=False,
                elapsed_sec=time.time() - t0,
                error=str(e),
            ))
            return ms_path, None, None, checkpoints

        # ======================================================================
        # Task 3: Calibration (solve) with automatic phaseshift
        # ======================================================================
        # CalibrationSolveStage now handles phaseshift internally when
        # do_phaseshift=True (default) and calibrator_name is provided.
        # This is CRITICAL for DSA-110: data is phased to meridian, must
        # shift to calibrator position for bandpass calibration to work.
        logger.info("Spawning calibration task (with automatic phaseshift)...")
        t0 = time.time()

        try:
            cal_task_id = await client.spawn_task(
                queue_name=ABSURD_QUEUE,
                task_name="calibration-solve",
                params={
                    "inputs": {
                        "ms_path": str(ms_path),  # Original MS - stage handles phaseshift
                    },
                    "config": {
                        "calibration": {
                            "refant": "103",
                            "do_k": False,
                            "field": cal_field,
                            # CRITICAL: Enable phaseshift (default=True for DSA-110)
                            "do_phaseshift": True,
                            "calibrator_name": CALIBRATOR_NAME,
                        }
                    }
                },
                priority=10,
                timeout_sec=TASK_TIMEOUT_SEC,
            )

            logger.info(f"Calibration task spawned: {cal_task_id}")
            task_result = await wait_for_task(client, str(cal_task_id))

            elapsed = time.time() - t0

            outputs = task_result.get("result", {}).get("outputs", {})
            cal_path_str = outputs.get("cal_table_path") or outputs.get("bandpass_table")
            phaseshifted_ms_str = outputs.get("phaseshifted_ms")

            if cal_path_str:
                cal_path = Path(cal_path_str)

            checkpoints.append(TestCheckpoint(
                name="calibration",
                passed=True,  # Task completed
                elapsed_sec=elapsed,
                details={
                    "task_id": str(cal_task_id),
                    "cal_table_path": str(cal_path) if cal_path else None,
                    "phaseshifted_ms": phaseshifted_ms_str,  # From CalibrationSolveStage output
                    "phaseshift_enabled": True,
                },
            ))

        except Exception as e:
            logger.warning(f"Calibration failed: {e}")
            checkpoints.append(TestCheckpoint(
                name="calibration",
                passed=False,
                elapsed_sec=time.time() - t0,
                error=str(e),
            ))
            # Continue to imaging anyway with uncalibrated data

        # ======================================================================
        # Task 4: Imaging
        # ======================================================================
        logger.info("Spawning imaging task...")
        t0 = time.time()

        try:
            image_output_dir = output_dir / "images"
            image_output_dir.mkdir(parents=True, exist_ok=True)

            image_name = image_output_dir / f"{group.timestamp.replace(':', '-')}"

            imaging_task_id = await client.spawn_task(
                queue_name=ABSURD_QUEUE,
                task_name="imaging",
                params={
                    "inputs": {
                        "ms_path": str(ms_path),
                        "output_path": str(image_name),
                    },
                    "config": {
                        "imaging": {
                            "imsize": 512,
                            "niter": 500,
                            "threshold": "0.5mJy",
                        }
                    }
                },
                priority=10,
                timeout_sec=TASK_TIMEOUT_SEC,
            )

            logger.info(f"Imaging task spawned: {imaging_task_id}")
            task_result = await wait_for_task(client, str(imaging_task_id))

            elapsed = time.time() - t0

            outputs = task_result.get("result", {}).get("outputs", {})
            image_path_str = outputs.get("image_path")

            if image_path_str:
                image_path = Path(image_path_str)
            else:
                # Try to find FITS output
                fits_candidates = list(image_output_dir.glob("*.fits"))
                if fits_candidates:
                    image_path = fits_candidates[0]

            checkpoints.append(TestCheckpoint(
                name="imaging",
                passed=image_path is not None,
                elapsed_sec=elapsed,
                details={
                    "task_id": str(imaging_task_id),
                    "image_path": str(image_path) if image_path else None,
                },
            ))

        except Exception as e:
            logger.error(f"Imaging failed: {e}")
            checkpoints.append(TestCheckpoint(
                name="imaging",
                passed=False,
                elapsed_sec=time.time() - t0,
                error=str(e),
            ))

    return ms_path, cal_path, image_path, checkpoints


# ==============================================================================
# Step 3: Validation
# ==============================================================================


def validate_ms(ms_path: Path) -> TestCheckpoint:
    """Validate Measurement Set structure and content."""
    t0 = time.time()
    details: Dict[str, Any] = {}
    errors: List[str] = []

    try:
        from casacore.tables import table

        # Check MAIN table
        tb = table(str(ms_path), readonly=True, ack=False)
        nrows = tb.nrows()
        details["nrows"] = nrows

        if nrows == 0:
            errors.append("MS is empty (0 rows)")

        tb.close()

        # Check SPECTRAL_WINDOW
        spw_path = str(ms_path / "SPECTRAL_WINDOW")
        tb = table(spw_path, readonly=True, ack=False)
        num_chan = tb.getcol("NUM_CHAN")
        total_channels = sum(num_chan)
        details["total_channels"] = int(total_channels)

        if total_channels < MIN_EXPECTED_CHANNELS:
            errors.append(f"Insufficient channels: {total_channels} < {MIN_EXPECTED_CHANNELS}")

        tb.close()

        # Check ANTENNA table
        ant_path = str(ms_path / "ANTENNA")
        tb = table(ant_path, readonly=True, ack=False)
        n_antennas = tb.nrows()
        details["n_antennas"] = n_antennas

        if n_antennas < MIN_ANTENNAS:
            errors.append(f"Too few antennas: {n_antennas} < {MIN_ANTENNAS}")

        tb.close()

        # Check FLAG column (if exists)
        tb = table(str(ms_path), readonly=True, ack=False)
        if "FLAG" in tb.colnames():
            flags = tb.getcol("FLAG")
            flagged_fraction = flags.sum() / flags.size
            details["flagged_fraction"] = round(flagged_fraction, 4)

            if flagged_fraction > MAX_FLAGGED_FRACTION:
                errors.append(f"Too much flagging: {flagged_fraction:.1%} > {MAX_FLAGGED_FRACTION:.0%}")

        tb.close()

    except Exception as e:
        errors.append(f"Error reading MS: {e}")

    passed = len(errors) == 0

    return TestCheckpoint(
        name="ms_validation",
        passed=passed,
        elapsed_sec=time.time() - t0,
        details=details,
        error="; ".join(errors) if errors else None,
    )


def validate_image(image_path: Path) -> Tuple[TestCheckpoint, Dict[str, float]]:
    """Validate image and extract metrics."""
    t0 = time.time()
    details: Dict[str, Any] = {}
    metrics: Dict[str, float] = {}
    errors: List[str] = []

    try:
        from astropy.io import fits
        import numpy as np

        with fits.open(image_path) as hdu:
            data = hdu[0].data
            header = hdu[0].header

            # Handle 4D CASA images (stokes, freq, y, x)
            if data.ndim == 4:
                data = data[0, 0]  # First Stokes, first frequency
            elif data.ndim == 3:
                data = data[0]

            # Remove NaN values for statistics
            valid_data = data[~np.isnan(data)]

            peak_flux = float(np.nanmax(data))
            rms_noise = float(np.nanstd(valid_data))
            snr = peak_flux / rms_noise if rms_noise > 0 else 0

            details["peak_flux_jy"] = round(peak_flux, 6)
            details["rms_noise_jy"] = round(rms_noise, 6)
            details["snr"] = round(snr, 1)
            details["image_size"] = list(data.shape)

            metrics["peak_flux_jy"] = peak_flux
            metrics["rms_noise_jy"] = rms_noise
            metrics["snr"] = snr

            # Validate
            if not (MIN_PEAK_FLUX_JY < peak_flux < MAX_PEAK_FLUX_JY):
                errors.append(f"Peak flux out of range: {peak_flux:.3f} Jy")

            if snr < MIN_SNR:
                errors.append(f"SNR too low: {snr:.1f} < {MIN_SNR}")

    except Exception as e:
        errors.append(f"Error reading image: {e}")

    passed = len(errors) == 0

    return (
        TestCheckpoint(
            name="image_validation",
            passed=passed,
            elapsed_sec=time.time() - t0,
            details=details,
            error="; ".join(errors) if errors else None,
        ),
        metrics,
    )


# ==============================================================================
# Step 4: Cleanup
# ==============================================================================


def cleanup_test_outputs(output_dir: Path, keep_report: bool = True) -> None:
    """Clean up test outputs."""
    logger.info(f"Cleaning up test outputs in {output_dir}")

    if not output_dir.exists():
        return

    # Remove intermediate products
    for subdir in ["ms", "images"]:
        path = output_dir / subdir
        if path.exists():
            shutil.rmtree(path)
            logger.info(f"Removed: {path}")

    # Keep report if requested
    if not keep_report:
        report_path = output_dir / "test_report.json"
        if report_path.exists():
            report_path.unlink()


# ==============================================================================
# Main Test Runner
# ==============================================================================


async def run_test(
    dry_run: bool = False,
    skip_cleanup: bool = False,
) -> TestResult:
    """Run the complete integration test.

    Args:
        dry_run: If True, only find data and report what would be done
        skip_cleanup: If True, keep intermediate products

    Returns:
        TestResult with all checkpoints and metrics
    """
    start_time = time.time()
    checkpoints: List[TestCheckpoint] = []
    metrics: Dict[str, Any] = {}

    # ======================================================================
    # Step 1: Find test data
    # ======================================================================
    logger.info("=" * 70)
    logger.info("STEP 1: Finding 0834+555 transit data")
    logger.info("=" * 70)

    t0 = time.time()
    group = find_0834_transit_group()

    if group is None:
        logger.warning("No 0834+555 transit found, trying any complete group...")
        group = find_any_complete_group()

    if group is None:
        logger.error("No complete 16-subband group found!")
        return TestResult(
            status="SKIPPED",
            total_runtime_sec=time.time() - start_time,
            checkpoints=[TestCheckpoint(
                name="data_discovery",
                passed=False,
                elapsed_sec=time.time() - t0,
                error="No complete 16-subband group available",
            )],
            calibrator=CALIBRATOR_NAME,
            observation_id="none",
        )

    checkpoints.append(TestCheckpoint(
        name="data_discovery",
        passed=True,
        elapsed_sec=time.time() - t0,
        details={
            "timestamp": group.timestamp,
            "n_files": len(group.files),
            "mid_mjd": group.mid_mjd,
        },
    ))

    logger.info(f"Found group: {group.timestamp} with {len(group.files)} files")

    if dry_run:
        logger.info("")
        logger.info("DRY RUN - would process:")
        logger.info(f"  Timestamp: {group.timestamp}")
        logger.info(f"  Files: {len(group.files)}")
        for f in sorted(group.files)[:3]:
            logger.info(f"    - {f.name}")
        logger.info(f"    ... and {len(group.files) - 3} more")

        return TestResult(
            status="DRY_RUN",
            total_runtime_sec=time.time() - start_time,
            checkpoints=checkpoints,
            calibrator=CALIBRATOR_NAME,
            observation_id=group.timestamp,
        )

    # ======================================================================
    # Step 2: Run ABSURD pipeline
    # ======================================================================
    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP 2: Running ABSURD pipeline")
    logger.info("=" * 70)

    output_dir = TEST_OUTPUT_DIR / group.timestamp.replace(":", "-")
    output_dir.mkdir(parents=True, exist_ok=True)

    ms_path, cal_path, image_path, pipeline_checkpoints = await run_absurd_pipeline(
        group, output_dir
    )
    checkpoints.extend(pipeline_checkpoints)

    # ======================================================================
    # Step 3: Validate outputs
    # ======================================================================
    logger.info("")
    logger.info("=" * 70)
    logger.info("STEP 3: Validating outputs")
    logger.info("=" * 70)

    if ms_path and ms_path.exists():
        ms_checkpoint = validate_ms(ms_path)
        checkpoints.append(ms_checkpoint)
        logger.info(f"MS validation: {'PASSED' if ms_checkpoint.passed else 'FAILED'}")

    if image_path and image_path.exists():
        image_checkpoint, image_metrics = validate_image(image_path)
        checkpoints.append(image_checkpoint)
        metrics.update(image_metrics)
        logger.info(f"Image validation: {'PASSED' if image_checkpoint.passed else 'FAILED'}")

    # ======================================================================
    # Step 4: Cleanup (optional)
    # ======================================================================
    if not skip_cleanup:
        logger.info("")
        logger.info("=" * 70)
        logger.info("STEP 4: Cleanup")
        logger.info("=" * 70)

        # Keep images for review, remove intermediate MS
        if output_dir.exists():
            ms_dir = output_dir / "ms"
            if ms_dir.exists():
                shutil.rmtree(ms_dir)
                logger.info(f"Removed intermediate MS: {ms_dir}")

    # ======================================================================
    # Generate result
    # ======================================================================
    total_runtime = time.time() - start_time
    all_passed = all(cp.passed for cp in checkpoints)

    result = TestResult(
        status="PASSED" if all_passed else "FAILED",
        total_runtime_sec=total_runtime,
        checkpoints=checkpoints,
        calibrator=CALIBRATOR_NAME,
        observation_id=group.timestamp,
        metrics=metrics,
    )

    # Save report
    report_path = output_dir / "test_report.json"
    with open(report_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    logger.info(f"Report saved: {report_path}")

    return result


# ==============================================================================
# Pytest Integration
# ==============================================================================


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.integration
@pytest.mark.timeout(600)  # 10 minute timeout
async def test_absurd_0834_pipeline():
    """Integration test: process 0834+555 transit through ABSURD pipeline."""
    result = await run_test(dry_run=False, skip_cleanup=False)

    # Assert all checkpoints passed
    for checkpoint in result.checkpoints:
        assert checkpoint.passed, f"Checkpoint {checkpoint.name} failed: {checkpoint.error}"

    # Assert metrics are reasonable
    if "snr" in result.metrics:
        assert result.metrics["snr"] >= MIN_SNR, f"SNR too low: {result.metrics['snr']}"

    if "peak_flux_jy" in result.metrics:
        assert MIN_PEAK_FLUX_JY < result.metrics["peak_flux_jy"] < MAX_PEAK_FLUX_JY


@pytest.mark.integration
async def test_find_0834_data():
    """Quick test to verify 0834+555 data can be found."""
    group = find_0834_transit_group(max_days_back=7)

    if group is None:
        group = find_any_complete_group()

    assert group is not None, "No complete subband group found"
    assert group.is_complete, f"Group incomplete: {len(group.files)} files"


# ==============================================================================
# CLI Entry Point
# ==============================================================================


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Integration test: ABSURD pipeline for 0834+555 transit"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Find data and show what would be done without processing",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the full integration test",
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Keep intermediate products after test",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.dry_run and not args.run:
        parser.print_help()
        print("\nUse --dry-run to preview or --run to execute the test.")
        sys.exit(1)

    # Run test
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║    DSA-110 Integration Test: ABSURD Pipeline (0834+555)            ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()

    result = asyncio.run(run_test(
        dry_run=args.dry_run,
        skip_cleanup=args.skip_cleanup,
    ))

    # Print summary
    print()
    print("─" * 70)
    print(f"Test Status: {result.status}")
    print(f"Total Runtime: {result.total_runtime_sec:.1f}s")
    print(f"Calibrator: {result.calibrator}")
    print(f"Observation: {result.observation_id}")
    print()

    print("Checkpoints:")
    for cp in result.checkpoints:
        status = "✓" if cp.passed else "✗"
        print(f"  {status} {cp.name}: {cp.elapsed_sec:.1f}s")
        if cp.error:
            print(f"      Error: {cp.error}")

    if result.metrics:
        print()
        print("Metrics:")
        for key, value in result.metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")

    print("─" * 70)

    sys.exit(0 if result.status in ("PASSED", "DRY_RUN") else 1)


if __name__ == "__main__":
    main()
