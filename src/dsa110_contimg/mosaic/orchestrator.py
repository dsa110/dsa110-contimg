#!/usr/bin/env python3
"""
Mosaic Orchestrator - Intelligent mosaic creation with auto-inference and overrides.

This module implements the high-level logic for creating mosaics with minimal user input:
- Default behavior: Process earliest incomplete observations first
- Override options: Center on specific RA, customize timespan
- Auto-inference: Dec from data → BP calibrator → validity windows → skymodels
- Hands-off operation: Single trigger → wait until published
"""

import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time

from dsa110_contimg.calibration.schedule import previous_transits
from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.config import CalibratorMSConfig
from dsa110_contimg.database.data_registry import (
    ensure_data_registry_db,
    get_data,
    link_photometry_to_data,
)
from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager
from dsa110_contimg.photometry.manager import PhotometryConfig, PhotometryManager
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MOSAIC_SPAN_MINUTES = 50  # 10 MS files (5 min each)
DEFAULT_MS_PER_MOSAIC = 10
MS_OVERLAP = 2  # Overlap between consecutive mosaics
MS_DURATION_MINUTES = 5  # Each MS is ~5 minutes


class MosaicOrchestrator:
    """Orchestrates mosaic creation with intelligent defaults and overrides."""

    def __init__(
        self,
        products_db_path: Optional[Path] = None,
        registry_db_path: Optional[Path] = None,
        data_registry_db_path: Optional[Path] = None,
        ms_output_dir: Optional[Path] = None,
        images_dir: Optional[Path] = None,
        mosaic_output_dir: Optional[Path] = None,
        input_dir: Optional[Path] = None,
        observatory_location: Optional[EarthLocation] = None,
        enable_photometry: bool = False,
        photometry_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize mosaic orchestrator.

        Args:
            products_db_path: Path to products database (defaults from env)
            registry_db_path: Path to calibration registry (defaults from env)
            data_registry_db_path: Path to data registry (defaults from env)
            ms_output_dir: Directory for MS files (defaults from env)
            images_dir: Directory for images (defaults from env)
            mosaic_output_dir: Directory for mosaics (defaults from env)
            input_dir: Input directory for HDF5 files (defaults from env)
            observatory_location: Observatory location (defaults to DSA-110)
            enable_photometry: Enable automatic photometry after mosaic creation
            photometry_config: Photometry configuration dict with keys:
                catalog (str): Catalog to use ("nvss", "first", etc.)
                radius_deg (float): Search radius in degrees
                normalize (bool): Enable normalization
                max_sources (int): Maximum sources to measure
        """
        # Determine paths from environment or defaults
        state_dir = Path(os.getenv("PIPELINE_STATE_DIR", "/data/dsa110-contimg/state"))
        self.products_db_path = products_db_path or Path(
            os.getenv("PIPELINE_PRODUCTS_DB", str(state_dir / "products.sqlite3"))
        )
        self.registry_db_path = registry_db_path or Path(
            os.getenv(
                "CAL_REGISTRY_DB",
                str(state_dir / "cal_registry.sqlite3"),
            )
        )
        self.data_registry_db_path = data_registry_db_path or Path(
            os.getenv(
                "DATA_REGISTRY_DB",
                str(state_dir / "data_registry.sqlite3"),
            )
        )

        # Output directories
        output_base = Path(os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg"))
        self.ms_output_dir = ms_output_dir or (output_base / "ms")
        self.images_dir = images_dir or (output_base / "images")
        self.mosaic_output_dir = mosaic_output_dir or (output_base / "mosaics")

        # Input directory
        self.input_dir = input_dir or Path(os.getenv("CONTIMG_INPUT_DIR", "/data/incoming"))

        # Observatory location
        if observatory_location is None:
            from dsa110_contimg.calibration.schedule import DSA110_LOCATION

            observatory_location = DSA110_LOCATION
        self.observatory_location = observatory_location

        # Initialize databases
        self.products_db = ensure_products_db(self.products_db_path)
        self.registry_db = None  # Will be initialized by StreamingMosaicManager
        self.data_registry_db = ensure_data_registry_db(self.data_registry_db_path)

        # Initialize calibrator service for transit finding
        try:
            config = CalibratorMSConfig.from_env()
            self.calibrator_service = CalibratorMSGenerator.from_config(config, verbose=False)
        except Exception as e:
            logger.warning(f"Could not initialize calibrator service: {e}")
            self.calibrator_service = None

        # Initialize streaming mosaic manager (lazy, after we know what we're doing)
        self.mosaic_manager: Optional[StreamingMosaicManager] = None

        # Photometry configuration and manager
        self.enable_photometry = enable_photometry
        photometry_config_dict = photometry_config or {
            "catalog": "nvss",
            "radius_deg": 1.0,
            "normalize": False,
            "max_sources": None,
        }
        self.photometry_config = photometry_config_dict  # Keep for backward compatibility
        self.photometry_manager: Optional[PhotometryManager] = None
        if self.enable_photometry:
            pm_config = PhotometryConfig.from_dict(photometry_config_dict)
            self.photometry_manager = PhotometryManager(
                products_db_path=self.products_db_path,
                data_registry_db_path=self.data_registry_db_path,
                default_config=pm_config,
            )

    def _get_mosaic_manager(self) -> StreamingMosaicManager:
        """Get or create StreamingMosaicManager instance."""
        if self.mosaic_manager is None:
            self.mosaic_manager = StreamingMosaicManager(
                products_db_path=self.products_db_path,
                registry_db_path=self.registry_db_path,
                ms_output_dir=self.ms_output_dir,
                images_dir=self.images_dir,
                mosaic_output_dir=self.mosaic_output_dir,
                observatory_location=self.observatory_location,
            )
        return self.mosaic_manager

    def find_earliest_incomplete_window(self, max_days_back: int = 60) -> Optional[Dict]:
        """Find earliest incomplete observation window (has data, no published mosaic).

        This implements the default behavior: process earliest data first.

        Args:
            max_days_back: Maximum days to search back

        Returns:
            Dict with window info: {
                'start_time': Time,
                'end_time': Time,
                'dec_deg': float,
                'bp_calibrator': str,
                'transit_time': Time (if calibrator found),
                'ms_count': int (available MS files in window)
            }
            or None if no incomplete window found
        """
        # Query products DB for earliest MS files that don't have published mosaics
        # This is complex - we need to:
        # 1. Find earliest MS files
        # 2. Determine Dec from those files
        # 3. Find BP calibrator for that Dec
        # 4. Check if mosaic exists for that window
        # 5. Return window info

        # For now, simplified approach: find earliest MS files
        cursor = self.products_db.cursor()
        rows = cursor.execute(
            """
            SELECT path, mid_mjd
            FROM ms_index
            WHERE status IN ('converted', 'calibrated', 'imaged', 'done')
            ORDER BY mid_mjd ASC
            LIMIT 100
            """
        ).fetchall()

        if not rows:
            logger.info("No MS files found in products database")
            return None

        # Get earliest MS files with Dec information
        earliest_ms_paths = [row[0] for row in rows[:DEFAULT_MS_PER_MOSAIC]]
        earliest_mjd = rows[0][1]

        # Extract Dec from ms_index (now available from HDF5 extraction!)
        dec_deg = None
        if earliest_ms_paths:
            # Query for Dec from first MS file
            dec_row = cursor.execute(
                """
                SELECT dec_deg
                FROM ms_index
                WHERE path = ?
                """,
                (earliest_ms_paths[0],),
            ).fetchone()
            if dec_row and dec_row[0] is not None:
                dec_deg = dec_row[0]
                logger.info(f"Found Dec from ms_index: {dec_deg:.6f} deg")
            else:
                logger.warning(
                    f"Dec not found in ms_index for {earliest_ms_paths[0]}, "
                    "may need to extract from MS file header"
                )

        if dec_deg is None:
            logger.error("Could not determine Dec for earliest MS files")
            return None

        # Find BP calibrator for this Dec
        manager = self._get_mosaic_manager()
        bp_calibrator = manager.get_bandpass_calibrator_for_dec(dec_deg)
        if not bp_calibrator:
            logger.warning(f"No BP calibrator found for Dec {dec_deg}")
            return None

        calibrator_name = bp_calibrator["name"]
        transit_time = None

        # Calculate transit time for this calibrator at earliest observation
        if earliest_mjd:
            transit_time = manager.calculate_calibrator_transit(
                calibrator_name, Time(earliest_mjd, format="mjd")
            )

        # Check for existing published mosaics to find earliest incomplete window
        # Query data_registry for published mosaics in this time range
        data_registry_cursor = self.data_registry_db.cursor()
        published_mosaics = data_registry_cursor.execute(
            """
            SELECT data_id, metadata_json
            FROM data_registry
            WHERE data_type = 'mosaic' AND status = 'published'
            ORDER BY created_at ASC
            """
        ).fetchall()

        # Find earliest incomplete window (no published mosaic covering this time)
        # For now, start from earliest MS file
        # TODO: Check if published mosaics cover this time range and skip if covered
        start_time = Time(earliest_mjd, format="mjd")

        # Default: process earliest data in pre-transit half (12 hours before transit)
        # If transit_time is available, adjust window to be in pre-transit half
        if transit_time:
            # Validity window is ±12 hours around transit
            # Pre-transit half: 12 hours before transit
            from astropy.time import TimeDelta

            pre_transit_start = transit_time - TimeDelta(12 * 3600, format="sec")
            # Use earliest of: earliest MS time or pre-transit start
            if start_time < pre_transit_start:
                # Start from earliest MS, but ensure we're in pre-transit half
                window_start = start_time
            else:
                window_start = pre_transit_start

            # Span DEFAULT_MOSAIC_SPAN_MINUTES from window_start
            start_time = window_start
        else:
            # No transit time available, just use earliest MS
            start_time = Time(earliest_mjd, format="mjd")

        # Calculate end time using TimeDelta with explicit units
        from astropy.time import TimeDelta

        end_time = start_time + TimeDelta(DEFAULT_MOSAIC_SPAN_MINUTES * 60, format="sec")

        return {
            "start_time": start_time,
            "end_time": end_time,
            "dec_deg": dec_deg,
            "bp_calibrator": calibrator_name,
            "transit_time": transit_time,
            "ms_count": len(earliest_ms_paths),
        }

    def find_transit_centered_window(
        self,
        calibrator_name: str,
        timespan_minutes: int = DEFAULT_MOSAIC_SPAN_MINUTES,
        max_days_back: int = 60,
    ) -> Optional[Dict]:
        """Find window centered on earliest transit of specified calibrator.

        This implements the override behavior: center mosaic on specific RA (via calibrator).

        Args:
            calibrator_name: Name of calibrator (e.g., "0834+555")
            timespan_minutes: Mosaic timespan in minutes (default: 50)
            max_days_back: Maximum days to search back

        Returns:
            Dict with window info: {
                'transit_time': Time,
                'start_time': Time,
                'end_time': Time,
                'dec_deg': float,
                'bp_calibrator': str,
                'ms_count': int (available MS files in window)
            }
            or None if no transit found
        """
        if not self.calibrator_service:
            logger.error("Calibrator service not available")
            return None

        # List all available transits for this calibrator
        transits = self.calibrator_service.list_available_transits(
            calibrator_name, max_days_back=max_days_back
        )

        if not transits:
            logger.warning(f"No transits found for {calibrator_name}")
            return None

        # Find earliest transit (list is sorted most recent first, so get last)
        earliest_transit = transits[-1]
        transit_iso = earliest_transit["transit_iso"]
        transit_time = Time(transit_iso)

        # Calculate window centered on transit
        from astropy.time import TimeDelta

        half_span = TimeDelta(timespan_minutes / 2.0 * 60, format="sec")
        start_time = transit_time - half_span
        end_time = transit_time + half_span

        # Get Dec from calibrator
        ra_deg, dec_deg = self.calibrator_service._load_radec(calibrator_name)

        # Check how many MS files exist in this window
        cursor = self.products_db.cursor()
        start_mjd = start_time.mjd
        end_mjd = end_time.mjd
        rows = cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM ms_index
            WHERE mid_mjd >= ? AND mid_mjd <= ?
            AND status IN ('converted', 'calibrated', 'imaged', 'done')
            """,
            (start_mjd, end_mjd),
        ).fetchone()
        ms_count = rows[0] if rows else 0

        return {
            "transit_time": transit_time,
            "start_time": start_time,
            "end_time": end_time,
            "dec_deg": dec_deg,
            "bp_calibrator": calibrator_name,
            "ms_count": ms_count,
        }

    def _trigger_hdf5_conversion(self, start_time: Time, end_time: Time) -> bool:
        """Trigger conversion of HDF5 files to MS files for a time window.

        Args:
            start_time: Window start time
            end_time: Window end time

        Returns:
            True if conversion triggered successfully, False otherwise
        """
        try:
            from dsa110_contimg.conversion.config import CalibratorMSConfig
            from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                convert_subband_groups_to_ms,
            )
            from dsa110_contimg.utils.ms_organization import create_path_mapper

            # Get input/output directories from environment
            input_dir = Path(os.getenv("CONTIMG_INPUT_DIR", "/data/incoming"))
            output_dir = self.ms_output_dir

            # Convert time range to strings for orchestrator
            start_str = start_time.isot.split("T")[0] + " " + start_time.isot.split("T")[1]
            end_str = end_time.isot.split("T")[0] + " " + end_time.isot.split("T")[1]

            # Create path mapper for organized output
            path_mapper = create_path_mapper(output_dir, is_calibrator=False, is_failed=False)

            logger.info(f"Triggering HDF5 conversion for window: {start_str} to {end_str}")

            # Trigger conversion
            convert_subband_groups_to_ms(
                str(input_dir),
                str(output_dir),
                start_str,
                end_str,
                scratch_dir=Path(os.getenv("CONTIMG_SCRATCH_DIR", "/dev/shm")),
                writer="auto",
                writer_kwargs={
                    "max_workers": int(os.getenv("CONTIMG_MAX_WORKERS", "4")),
                    "stage_to_tmpfs": os.getenv("CONTIMG_STAGE_TO_TMPFS", "false").lower()
                    == "true",
                    "tmpfs_path": os.getenv("CONTIMG_TMPFS_PATH", "/dev/shm"),
                },
                path_mapper=path_mapper,
            )

            logger.info("HDF5 conversion completed")
            return True

        except Exception as e:
            logger.error(f"Failed to trigger HDF5 conversion: {e}", exc_info=True)
            return False

    def ensure_ms_files_in_window(
        self, start_time: Time, end_time: Time, required_count: int
    ) -> List[str]:
        """Ensure MS files exist in window, converting HDF5 if needed.

        Args:
            start_time: Window start time
            end_time: Window end time
            required_count: Required number of MS files

        Returns:
            List of MS file paths
        """
        # Check existing MS files in window
        cursor = self.products_db.cursor()
        start_mjd = start_time.mjd
        end_mjd = end_time.mjd
        rows = cursor.execute(
            """
            SELECT path
            FROM ms_index
            WHERE mid_mjd >= ? AND mid_mjd <= ?
            AND status IN ('converted', 'calibrated', 'imaged', 'done')
            ORDER BY mid_mjd ASC
            """,
            (start_mjd, end_mjd),
        ).fetchall()

        existing_ms = [row[0] for row in rows]

        if len(existing_ms) >= required_count:
            return existing_ms[:required_count]

        # Need to convert HDF5 files
        logger.info(
            f"Only {len(existing_ms)} MS files found, need {required_count}. "
            "Triggering HDF5 conversion..."
        )

        # Trigger conversion
        if self._trigger_hdf5_conversion(start_time, end_time):
            # Wait a bit for conversion to complete and database to update
            import time

            time.sleep(5)  # Give conversion time to complete

            # Re-check for MS files
            rows = cursor.execute(
                """
                SELECT path
                FROM ms_index
                WHERE mid_mjd >= ? AND mid_mjd <= ?
                AND status IN ('converted', 'calibrated', 'imaged', 'done')
                ORDER BY mid_mjd ASC
                """,
                (start_mjd, end_mjd),
            ).fetchall()

            existing_ms = [row[0] for row in rows]
            logger.info(f"After conversion: {len(existing_ms)} MS files found")

        return existing_ms[:required_count] if len(existing_ms) >= required_count else existing_ms

    def _form_group_from_ms_paths(self, ms_paths: List[str], group_id: str) -> bool:
        """Manually form a group from specific MS file paths.

        Args:
            ms_paths: List of MS file paths (must be in chronological order)
            group_id: Group identifier

        Returns:
            True if group created successfully
        """
        manager = self._get_mosaic_manager()

        # Verify all MS files exist
        for ms_path in ms_paths:
            if not Path(ms_path).exists():
                logger.error(f"MS file does not exist: {ms_path}")
                return False

        # Insert group into database
        ms_paths_str = ",".join(ms_paths)
        try:
            manager.products_db.execute(
                """
                INSERT OR REPLACE INTO mosaic_groups 
                (group_id, ms_paths, created_at, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (group_id, ms_paths_str, time.time()),
            )
            manager.products_db.commit()
            logger.info(f"Created group {group_id} with {len(ms_paths)} MS files")
            return True
        except Exception as e:
            logger.error(f"Failed to create group {group_id}: {e}")
            return False

    def _process_group_workflow(self, group_id: str) -> Optional[str]:
        """Process a group through full workflow: calibration → imaging → mosaic.

        Args:
            group_id: Group identifier

        Returns:
            Mosaic path if successful, None otherwise
        """
        manager = self._get_mosaic_manager()

        # Get MS paths
        ms_paths = manager.get_group_ms_paths(group_id)
        if len(ms_paths) < DEFAULT_MS_PER_MOSAIC:
            logger.warning(
                f"Group {group_id} has only {len(ms_paths)} MS files, "
                f"need {DEFAULT_MS_PER_MOSAIC}"
            )
            # Allow asymmetric mosaics if data availability requires it
            if len(ms_paths) < 3:
                logger.error(f"Too few MS files ({len(ms_paths)}) for mosaic")
                return None

        # Select calibration MS (5th MS, index 4)
        calibration_ms = manager.select_calibration_ms(ms_paths)
        if not calibration_ms:
            logger.error(f"Could not select calibration MS for group {group_id}")
            return None

        # Solve calibration
        bpcal_solved, gaincal_solved, error_msg = manager.solve_calibration_for_group(
            group_id, calibration_ms
        )
        if error_msg:
            logger.error(f"Calibration solving failed for group {group_id}: {error_msg}")
            return None

        # Apply calibration
        if not manager.apply_calibration_to_group(group_id):
            logger.error(f"Failed to apply calibration to group {group_id}")
            return None

        # Image all MS
        if not manager.image_group(group_id):
            logger.error(f"Failed to image group {group_id}")
            return None

        # Create mosaic
        mosaic_path = manager.create_mosaic(group_id)
        if not mosaic_path:
            logger.error(f"Failed to create mosaic for group {group_id}")
            return None

        logger.info(f"Successfully processed group {group_id}, mosaic: {mosaic_path}")

        # Trigger photometry if enabled
        if self.enable_photometry and mosaic_path:
            photometry_job_id = self._trigger_photometry_for_mosaic(
                mosaic_path=Path(mosaic_path),
                group_id=group_id,
            )
            if photometry_job_id:
                logger.info(f"Photometry job {photometry_job_id} created for mosaic {mosaic_path}")
                # Link photometry job to data registry
                try:
                    mosaic_data_id = Path(mosaic_path).stem
                    if link_photometry_to_data(
                        self.data_registry_db, mosaic_data_id, str(photometry_job_id)
                    ):
                        logger.debug(
                            f"Linked photometry job {photometry_job_id} to mosaic data_id {mosaic_data_id}"
                        )
                    else:
                        logger.debug(
                            f"Could not link photometry job (mosaic data_id {mosaic_data_id} may not exist in registry)"
                        )
                except Exception as e:
                    logger.debug(f"Failed to link photometry to data registry (non-fatal): {e}")
            else:
                logger.warning(f"No photometry job created for mosaic {mosaic_path}")

        return mosaic_path

    def _trigger_photometry_for_mosaic(
        self,
        mosaic_path: Path,
        group_id: str,
    ) -> Optional[int]:
        """Trigger photometry measurement for a newly created mosaic.

        Args:
            mosaic_path: Path to mosaic FITS file
            group_id: Mosaic group ID

        Returns:
            Batch job ID if successful, None otherwise
        """
        if not self.photometry_manager:
            logger.warning("Photometry manager not initialized")
            return None

        try:
            # Generate data_id from mosaic path (stem without extension)
            mosaic_data_id = mosaic_path.stem

            # Use PhotometryManager to handle the workflow
            result = self.photometry_manager.measure_for_mosaic(
                mosaic_path=mosaic_path,
                create_batch_job=True,
                data_id=mosaic_data_id,
                group_id=group_id,
            )

            if result and result.batch_job_id:
                logger.info(
                    f"Created photometry batch job {result.batch_job_id} for mosaic {mosaic_path.name}"
                )
                return result.batch_job_id
            return None

        except Exception as e:
            logger.error(
                f"Failed to trigger photometry for mosaic {mosaic_path}: {e}",
                exc_info=True,
            )
            return None

    def create_mosaic_centered_on_calibrator(
        self,
        calibrator_name: str,
        timespan_minutes: int = DEFAULT_MOSAIC_SPAN_MINUTES,
        wait_for_published: bool = True,
        poll_interval_seconds: int = 5,
        max_wait_hours: float = 24.0,
    ) -> Optional[str]:
        """Create mosaic centered on earliest transit of specified calibrator.

        Single trigger, hands-off operation: returns only when mosaic is published.

        Args:
            calibrator_name: Name of calibrator (e.g., "0834+555")
            timespan_minutes: Mosaic timespan in minutes (default: 50)
            wait_for_published: Wait until mosaic is published (default: True)
            poll_interval_seconds: Polling interval for published status (default: 5)
            max_wait_hours: Maximum hours to wait (default: 24)

        Returns:
            Published mosaic path, or None if failed
        """
        logger.info(f"Creating {timespan_minutes}-minute mosaic centered on {calibrator_name}")

        # Find transit-centered window
        window_info = self.find_transit_centered_window(calibrator_name, timespan_minutes)
        if not window_info:
            logger.error(f"Could not find transit window for {calibrator_name}")
            return None

        transit_time = window_info["transit_time"]
        start_time = window_info["start_time"]
        end_time = window_info["end_time"]
        required_ms_count = int(timespan_minutes / MS_DURATION_MINUTES)

        logger.info(
            f"Transit time: {transit_time.isot}\n"
            f"Window: {start_time.isot} to {end_time.isot}\n"
            f"Required MS files: {required_ms_count}"
        )

        # Ensure MS files exist in window
        ms_paths = self.ensure_ms_files_in_window(start_time, end_time, required_ms_count)
        if len(ms_paths) < required_ms_count:
            # Allow asymmetric mosaics if data availability requires it
            if len(ms_paths) < 3:
                logger.error(f"Only {len(ms_paths)} MS files available, need at least 3")
                return None
            logger.warning(f"Only {len(ms_paths)} MS files available, creating asymmetric mosaic")

        # Form group ID (sanitize transit time for use as identifier)
        transit_str = transit_time.isot.replace(":", "-").replace(".", "-").replace("T", "_")
        group_id = f"mosaic_{transit_str}"
        if not self._form_group_from_ms_paths(ms_paths, group_id):
            logger.error("Failed to form group")
            return None

        # Process the group: calibration → imaging → mosaic creation
        logger.info(f"Processing group {group_id}...")
        mosaic_path = self._process_group_workflow(group_id)

        if not mosaic_path:
            logger.error("Mosaic creation failed")
            return None

        logger.info(f"Mosaic created at: {mosaic_path}")

        # Extract mosaic ID from path
        mosaic_id = Path(mosaic_path).stem

        if wait_for_published:
            logger.info("Waiting for mosaic to be published...")
            published_path = self.wait_for_published(
                mosaic_id, poll_interval_seconds, max_wait_hours
            )
            if published_path:
                logger.info(f"Mosaic published at: {published_path}")
                return published_path
            else:
                logger.error("Mosaic was not published within timeout")
                return None

        return mosaic_path

    def create_mosaic_default_behavior(
        self,
        timespan_minutes: int = DEFAULT_MOSAIC_SPAN_MINUTES,
        wait_for_published: bool = True,
        poll_interval_seconds: int = 5,
        max_wait_hours: float = 24.0,
    ) -> Optional[str]:
        """Create mosaic using default behavior: earliest incomplete window.

        Single trigger, hands-off operation: processes earliest incomplete observations first.

        Args:
            timespan_minutes: Mosaic timespan in minutes (default: 50)
            wait_for_published: Wait until mosaic is published (default: True)
            poll_interval_seconds: Polling interval for published status (default: 5)
            max_wait_hours: Maximum hours to wait (default: 24)

        Returns:
            Published mosaic path, or None if failed
        """
        logger.info("Creating mosaic using default behavior (earliest incomplete window)")

        # Find earliest incomplete window
        window_info = self.find_earliest_incomplete_window()
        if not window_info:
            logger.error("Could not find earliest incomplete window")
            return None

        start_time = window_info["start_time"]
        end_time = window_info["end_time"]
        required_ms_count = int(timespan_minutes / MS_DURATION_MINUTES)

        logger.info(
            f"Earliest incomplete window:\n"
            f"  Start: {start_time.isot}\n"
            f"  End: {end_time.isot}\n"
            f"  Dec: {window_info['dec_deg']:.6f} deg\n"
            f"  BP Calibrator: {window_info['bp_calibrator']}\n"
            f"  Required MS files: {required_ms_count}"
        )

        # Ensure MS files exist in window
        ms_paths = self.ensure_ms_files_in_window(start_time, end_time, required_ms_count)
        if len(ms_paths) < required_ms_count:
            # Allow asymmetric mosaics if data availability requires it
            if len(ms_paths) < 3:
                logger.error(f"Only {len(ms_paths)} MS files available, need at least 3")
                return None
            logger.warning(f"Only {len(ms_paths)} MS files available, creating asymmetric mosaic")

        # Form group
        group_id = f"mosaic_default_{start_time.isot.replace(':', '-').replace('.', '-').replace('T', '_')}"
        if not self._form_group_from_ms_paths(ms_paths, group_id):
            logger.error("Failed to form group")
            return None

        # Process the group: calibration → imaging → mosaic creation
        logger.info(f"Processing group {group_id}...")
        mosaic_path = self._process_group_workflow(group_id)

        if not mosaic_path:
            logger.error("Mosaic creation failed")
            return None

        logger.info(f"Mosaic created at: {mosaic_path}")

        # Extract mosaic ID from path
        mosaic_id = Path(mosaic_path).stem

        if wait_for_published:
            logger.info("Waiting for mosaic to be published...")
            published_path = self.wait_for_published(
                mosaic_id, poll_interval_seconds, max_wait_hours
            )
            if published_path:
                logger.info(f"Mosaic published at: {published_path}")
                return published_path
            else:
                logger.error("Mosaic was not published within timeout")
                return None

        return mosaic_path

    def create_mosaic_in_time_window(
        self,
        start_time: str,
        end_time: str,
        wait_for_published: bool = True,
        poll_interval_seconds: int = 5,
        max_wait_hours: float = 24.0,
    ) -> Optional[str]:
        """Create mosaic for a specific time window.

        Args:
            start_time: Start time in ISO format (e.g., "2025-11-12T10:00:00")
            end_time: End time in ISO format (e.g., "2025-11-12T10:50:00")
            wait_for_published: Wait until mosaic is published (default: True)
            poll_interval_seconds: Polling interval for published status (default: 5)
            max_wait_hours: Maximum hours to wait (default: 24)

        Returns:
            Published mosaic path, or None if failed
        """
        logger.info(f"Creating mosaic for time window: {start_time} to {end_time}")

        # Parse time strings to Time objects
        try:
            start_time_obj = Time(start_time, format="isot", scale="utc")
            end_time_obj = Time(end_time, format="isot", scale="utc")
        except Exception as e:
            logger.error(f"Invalid time format: {e}")
            return None

        # Calculate timespan and required MS count
        timespan_minutes = (end_time_obj - start_time_obj).to("min").value
        required_ms_count = int(timespan_minutes / MS_DURATION_MINUTES)

        logger.info(
            f"Time window: {start_time_obj.isot} to {end_time_obj.isot}\n"
            f"Timespan: {timespan_minutes:.1f} minutes\n"
            f"Required MS files: {required_ms_count}"
        )

        # Ensure MS files exist in window
        ms_paths = self.ensure_ms_files_in_window(start_time_obj, end_time_obj, required_ms_count)
        if len(ms_paths) < required_ms_count:
            # Allow asymmetric mosaics if data availability requires it
            if len(ms_paths) < 3:
                logger.error(f"Only {len(ms_paths)} MS files available, need at least 3")
                return None
            logger.warning(f"Only {len(ms_paths)} MS files available, creating asymmetric mosaic")

        # Form group ID (sanitize start time for use as identifier)
        start_str = start_time_obj.isot.replace(":", "-").replace(".", "-").replace("T", "_")
        group_id = f"mosaic_{start_str}"
        if not self._form_group_from_ms_paths(ms_paths, group_id):
            logger.error("Failed to form group")
            return None

        # Process the group: calibration → imaging → mosaic creation
        logger.info(f"Processing group {group_id}...")
        mosaic_path = self._process_group_workflow(group_id)

        if not mosaic_path:
            logger.error("Mosaic creation failed")
            return None

        logger.info(f"Mosaic created at: {mosaic_path}")

        # Extract mosaic ID from path
        mosaic_id = Path(mosaic_path).stem

        if wait_for_published:
            logger.info("Waiting for mosaic to be published...")
            published_path = self.wait_for_published(
                mosaic_id, poll_interval_seconds, max_wait_hours
            )
            if published_path:
                logger.info(f"Mosaic published at: {published_path}")
                return published_path
            else:
                logger.error("Mosaic was not published within timeout")
                return None

        return mosaic_path

    def process_sequential_mosaics_with_overlap(
        self,
        max_mosaics: Optional[int] = None,
        timespan_minutes: int = DEFAULT_MOSAIC_SPAN_MINUTES,
        wait_for_published: bool = True,
    ) -> List[str]:
        """Process multiple mosaics sequentially with sliding window overlap.

        Uses StreamingMosaicManager's sliding window logic:
        - 10 MS files per mosaic
        - 2 MS overlap between consecutive mosaics (8 new + 2 overlap)
        - Maintains overlap on both sides

        Args:
            max_mosaics: Maximum number of mosaics to create (None = process all available)
            timespan_minutes: Mosaic timespan in minutes (default: 50)
            wait_for_published: Wait until each mosaic is published (default: True)

        Returns:
            List of published mosaic paths
        """
        logger.info(
            f"Processing sequential mosaics with sliding window overlap "
            f"(max={max_mosaics or 'unlimited'})"
        )

        manager = self._get_mosaic_manager()
        published_paths = []
        mosaic_count = 0

        while True:
            if max_mosaics and mosaic_count >= max_mosaics:
                logger.info(f"Reached maximum mosaic count: {max_mosaics}")
                break

            # Use sliding window logic (8 new + 2 overlap)
            group_id = manager.check_for_sliding_window_group()
            if not group_id:
                logger.info("No more groups available for processing")
                break

            logger.info(f"Processing group {group_id} (mosaic {mosaic_count + 1})...")

            # Process group through full workflow
            mosaic_path = self._process_group_workflow(group_id)
            if not mosaic_path:
                logger.error(f"Failed to create mosaic for group {group_id}")
                continue

            mosaic_id = Path(mosaic_path).stem
            mosaic_count += 1

            if wait_for_published:
                published_path = self.wait_for_published(mosaic_id)
                if published_path:
                    published_paths.append(published_path)
                    logger.info(f"Mosaic {mosaic_count} published at: {published_path}")
                else:
                    logger.warning(
                        f"Mosaic {mosaic_count} created but not published: {mosaic_path}"
                    )
            else:
                published_paths.append(mosaic_path)

        logger.info(f"Completed processing {mosaic_count} mosaics")
        return published_paths

    def wait_for_published(
        self,
        mosaic_id: str,
        poll_interval_seconds: int = 5,
        max_wait_hours: float = 24.0,
    ) -> Optional[str]:
        """Wait until mosaic is published (moved to /data/ and status='published').

        Args:
            mosaic_id: Mosaic identifier
            poll_interval_seconds: Polling interval in seconds
            max_wait_hours: Maximum hours to wait

        Returns:
            Published path if successful, None if timeout
        """
        max_wait_seconds = max_wait_hours * 3600
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            # Check status in data_registry
            instance = get_data(self.data_registry_db, mosaic_id)
            if instance:
                if instance.status == "published":
                    published_path = instance.published_path
                    if published_path and Path(published_path).exists():
                        return published_path
                    else:
                        logger.warning(f"Mosaic {mosaic_id} marked published but file not found")

            time.sleep(poll_interval_seconds)

        logger.error(f"Timeout waiting for mosaic {mosaic_id} to be published")
        return None
