#!/usr/bin/env python3
"""
Streaming mosaic generation workflow for DSA-110 continuum imaging.

This module implements the streaming mosaic workflow that processes groups of 10 MS files
in a sliding window pattern with 2 MS overlap between consecutive mosaics.

Key features:
- Registry-based calibration decisions (registry is authoritative source)
- Transit-centered validity windows for bandpass calibration
- Time-centered validity windows for gain calibration
- Automatic group formation and sliding window management
"""

import logging
import os
import sqlite3
import time
from functools import wraps
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, TypeVar

import astropy.units as u
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time

from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.calibration.calibration import solve_bandpass, solve_gains
from dsa110_contimg.calibration.model import populate_model_from_catalog
from dsa110_contimg.calibration.selection import select_bandpass_from_catalog
from dsa110_contimg.database.products import (
    ensure_products_db,
    get_storage_locations,
    images_insert,
    ms_index_upsert,
    register_storage_location,
)
from dsa110_contimg.database.registry import ensure_db as ensure_cal_db
from dsa110_contimg.database.registry import (
    get_active_applylist,
    register_set_from_prefix,
)
from dsa110_contimg.imaging.cli import image_ms
from dsa110_contimg.mosaic.validation import validate_tiles_consistency
from dsa110_contimg.utils.ms_organization import (
    determine_ms_type,
    get_organized_ms_path,
    organize_ms_file,
)

# Lazy import to avoid syntax errors in cli.py
# from dsa110_contimg.mosaic.cli import _build_weighted_mosaic, _ensure_mosaics_table
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logger = logging.getLogger(__name__)

# Constants
MS_PER_GROUP = 10
MS_OVERLAP = 2
MS_NEW_PER_MOSAIC = 8  # 8 new + 2 overlap = 10 total
CALIBRATION_MS_INDEX = 4  # 5th MS (0-indexed)


class StreamingMosaicManager:
    """Manages streaming mosaic generation workflow.

    This class orchestrates the complete workflow from MS file groups through
    calibration, imaging, and mosaic creation. It maintains organized directory
    structures and tracks all files in registry databases.

    Directory Organization:
        MS files are automatically organized by type and date:
        - Calibrator MS: ms/calibrators/YYYY-MM-DD/<timestamp>.ms/
        - Science MS: ms/science/YYYY-MM-DD/<timestamp>.ms/
        - Failed MS: ms/failed/YYYY-MM-DD/<timestamp>.ms/
        - Images: images/<timestamp>.img-*/
        - Mosaics: mosaics/<mosaic_name>.fits

        Calibration tables are stored alongside calibrator MS files:
        - ms/calibrators/YYYY-MM-DD/<timestamp>_bpcal/
        - ms/calibrators/YYYY-MM-DD/<timestamp>_gpcal/
        - ms/calibrators/YYYY-MM-DD/<timestamp>_2gcal/

    Storage Location Registration:
        Base directories are registered in products.sqlite3 storage_locations table:
        - ms_files, calibration_tables, science_ms, failed_ms, images, mosaics

        Individual file paths are tracked in:
        - ms_index table (products.sqlite3) for MS files
        - cal_registry.sqlite3 for calibration tables

        Paths are automatically updated when files are moved to organized locations.

    Workflow:
        1. Form groups of MS files (default: 10 MS per group, 2 MS overlap)
        2. Solve calibration using 5th MS (middle by time)
        3. Apply calibration to all MS files in group
        4. Image each MS individually
        5. Create mosaic from group of images
        6. Organize files into date-based subdirectories
    """

    def __init__(
        self,
        products_db_path: Path,
        registry_db_path: Path,
        ms_output_dir: Path,
        images_dir: Path,
        mosaic_output_dir: Path,
        observatory_location: Optional[EarthLocation] = None,
        refant: str = "103",
        bp_validity_hours: float = 24.0,
        gain_validity_minutes: float = 30.0,
        calibration_params: Optional[Dict] = None,
        min_calibrator_flux_jy: float = 0.1,
        min_calibrator_pb_response: float = 0.3,
    ):
        """Initialize streaming mosaic manager.

        Args:
            products_db_path: Path to products database
            registry_db_path: Path to calibration registry database
            ms_output_dir: Directory containing MS files
            images_dir: Directory for individual image outputs
            mosaic_output_dir: Directory for mosaic output
            observatory_location: Observatory location for transit calculations
            refant: Reference antenna ID (default: "103")
            bp_validity_hours: Bandpass calibration validity window in hours (default: 24.0)
            gain_validity_minutes: Gain calibration validity window in minutes (default: 30.0)
            calibration_params: Optional dict of calibration parameters to override defaults
            min_calibrator_flux_jy: Minimum calibrator flux in Jy for visibility validation (default: 0.1)
            min_calibrator_pb_response: Minimum primary beam response for calibrator visibility (default: 0.3)
        """
        self.products_db_path = products_db_path
        self.registry_db_path = registry_db_path
        self.ms_output_dir = ms_output_dir
        self.images_dir = images_dir
        self.mosaic_output_dir = mosaic_output_dir
        self.observatory_location = observatory_location or EarthLocation.of_site(
            "greenwich"
        )

        # Organized subdirectories within ms_output_dir
        self.ms_calibrators_dir = ms_output_dir / "calibrators"
        self.ms_science_dir = ms_output_dir / "science"
        self.ms_failed_dir = ms_output_dir / "failed"
        self.refant = refant
        self.bp_validity_hours = bp_validity_hours
        self.gain_validity_minutes = gain_validity_minutes
        self.min_calibrator_flux_jy = min_calibrator_flux_jy
        self.min_calibrator_pb_response = min_calibrator_pb_response

        # Set default calibration parameters
        self.calibration_params = {
            "minsnr": 5.0,
            "model_standard": "Perley-Butler 2017",
            "combine_fields": False,
            "combine_spw": False,
            "uvrange": "",
        }
        # Override with user-provided parameters
        if calibration_params:
            self.calibration_params.update(calibration_params)

        # Retry configuration
        self.max_retries = 3
        self.retry_delay_seconds = 5.0

        # Ensure output directories exist
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.mosaic_output_dir.mkdir(parents=True, exist_ok=True)
        self.ms_calibrators_dir.mkdir(parents=True, exist_ok=True)
        self.ms_science_dir.mkdir(parents=True, exist_ok=True)
        self.ms_failed_dir.mkdir(parents=True, exist_ok=True)

        # Initialize databases
        self.products_db = ensure_products_db(products_db_path)
        self.registry_db = ensure_cal_db(registry_db_path)
        self._ensure_mosaic_groups_table()
        self._register_storage_locations()

    def _ensure_mosaic_groups_table(self) -> None:
        """Ensure mosaic_groups table exists in products database."""
        self.products_db.execute(
            """
            CREATE TABLE IF NOT EXISTS mosaic_groups (
                group_id TEXT PRIMARY KEY,
                mosaic_id TEXT,
                ms_paths TEXT NOT NULL,
                calibration_ms_path TEXT,
                bpcal_solved INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                calibrated_at REAL,
                imaged_at REAL,
                mosaicked_at REAL,
                status TEXT DEFAULT 'pending'
            )
            """
        )
        self.products_db.execute(
            "CREATE INDEX IF NOT EXISTS idx_mosaic_groups_status ON mosaic_groups(status)"
        )

        # Ensure bandpass calibrator registry table exists
        self.products_db.execute(
            """
            CREATE TABLE IF NOT EXISTS bandpass_calibrators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calibrator_name TEXT NOT NULL,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                dec_range_min REAL NOT NULL,
                dec_range_max REAL NOT NULL,
                registered_at REAL NOT NULL,
                registered_by TEXT,
                status TEXT DEFAULT 'active',
                notes TEXT
            )
            """
        )
        self.products_db.execute(
            "CREATE INDEX IF NOT EXISTS idx_bpcal_dec_range ON bandpass_calibrators(dec_range_min, dec_range_max)"
        )
        self.products_db.execute(
            "CREATE INDEX IF NOT EXISTS idx_bpcal_status ON bandpass_calibrators(status)"
        )
        self.products_db.commit()

    def _register_storage_locations(self) -> None:
        """Register storage locations for recovery.

        Registers base directories in the storage_locations table of products.sqlite3.
        This enables recovery and discovery of files even after reorganization.

        Registered locations:
        - ms_files: Base MS directory
        - calibration_tables: Calibrator MS directory (where calibration tables are stored)
        - science_ms: Science MS directory
        - failed_ms: Failed MS directory
        - images: Images directory
        - mosaics: Mosaics directory

        Individual file paths are tracked separately:
        - MS files: ms_index table (updated when files are moved)
        - Calibration tables: cal_registry.sqlite3 (registered with full organized paths)
        """
        from dsa110_contimg.database.products import register_storage_location

        # Register MS files location
        register_storage_location(
            self.products_db,
            "ms_files",
            str(self.ms_output_dir),
            "Measurement Set files",
            "MS files created from HDF5 conversion",
        )

        # Register calibration tables location (organized by date in calibrators/)
        register_storage_location(
            self.products_db,
            "calibration_tables",
            str(self.ms_calibrators_dir),
            "Calibration tables",
            "BP, GP, 2G calibration tables organized by date in calibrators/YYYY-MM-DD/",
        )

        # Register science MS location
        register_storage_location(
            self.products_db,
            "science_ms",
            str(self.ms_science_dir),
            "Science observations",
            "Science MS files organized by date in science/YYYY-MM-DD/",
        )

        # Register failed MS location
        register_storage_location(
            self.products_db,
            "failed_ms",
            str(self.ms_failed_dir),
            "Failed conversions",
            "Failed/corrupted MS files for manual review",
        )

        # Register images location
        register_storage_location(
            self.products_db,
            "images",
            str(self.images_dir),
            "Individual images",
            "Single-epoch images created from calibrated MS files",
        )

        # Register mosaic output location
        register_storage_location(
            self.products_db,
            "mosaics",
            str(self.mosaic_output_dir),
            "Mosaic images",
            "Final mosaic images created from tile groups",
        )

        self.products_db.commit()

    def register_bandpass_calibrator(
        self,
        calibrator_name: str,
        ra_deg: float,
        dec_deg: float,
        dec_tolerance: float = 5.0,
        registered_by: str = "system",
        notes: Optional[str] = None,
    ) -> None:
        """Register a bandpass calibrator for a Dec range.

        Args:
            calibrator_name: Name of calibrator (e.g., '0834+555')
            ra_deg: RA in degrees
            dec_deg: Dec in degrees
            dec_tolerance: Tolerance in degrees for Dec range (default: 5.0)
            registered_by: Who registered this calibrator
            notes: Optional notes
        """
        dec_range_min = dec_deg - dec_tolerance
        dec_range_max = dec_deg + dec_tolerance

        # Deactivate any existing calibrators in this Dec range
        self.products_db.execute(
            """
            UPDATE bandpass_calibrators
            SET status = 'inactive'
            WHERE dec_range_min <= ? AND dec_range_max >= ?
            AND status = 'active'
            """,
            (dec_range_max, dec_range_min),
        )

        # Register new calibrator
        self.products_db.execute(
            """
            INSERT INTO bandpass_calibrators
            (calibrator_name, ra_deg, dec_deg, dec_range_min, dec_range_max,
             registered_at, registered_by, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                calibrator_name,
                ra_deg,
                dec_deg,
                dec_range_min,
                dec_range_max,
                time.time(),
                registered_by,
                notes,
            ),
        )
        self.products_db.commit()

        logger.info(
            f"Registered bandpass calibrator {calibrator_name} "
            f"(RA={ra_deg:.6f}, Dec={dec_deg:.6f}) "
            f"for Dec range [{dec_range_min:.2f}, {dec_range_max:.2f}]"
        )

    def get_bandpass_calibrator_for_dec(self, dec_deg: float) -> Optional[Dict]:
        """Get active bandpass calibrator for a given Dec.

        Args:
            dec_deg: Declination in degrees

        Returns:
            Dictionary with calibrator info, or None if not found
        """
        row = self.products_db.execute(
            """
            SELECT calibrator_name, ra_deg, dec_deg, dec_range_min, dec_range_max,
                   registered_at, notes
            FROM bandpass_calibrators
            WHERE dec_range_min <= ? AND dec_range_max >= ?
            AND status = 'active'
            ORDER BY registered_at DESC
            LIMIT 1
            """,
            (dec_deg, dec_deg),
        ).fetchone()

        if not row:
            return None

        return {
            "name": row[0],
            "ra_deg": row[1],
            "dec_deg": row[2],
            "dec_range_min": row[3],
            "dec_range_max": row[4],
            "registered_at": row[5],
            "notes": row[6],
        }

    def check_for_new_group(self) -> Optional[str]:
        """Check if a new group of 10 MS files is ready for processing.

        Returns:
            Group ID if ready, None otherwise
        """
        # Query for MS files in 'converted' stage, ordered by time
        rows = self.products_db.execute(
            """
            SELECT path, mid_mjd
            FROM ms_index
            WHERE stage = 'converted' AND status = 'converted'
            ORDER BY mid_mjd ASC
            LIMIT ?
            """,
            (MS_PER_GROUP,),
        ).fetchall()

        if len(rows) < MS_PER_GROUP:
            return None

        # CRITICAL: Keep paths in chronological order (by mid_mjd), not alphabetical
        # Store as (mid_mjd, path) tuples to preserve chronological order
        ms_paths_with_time = [(row[1], row[0]) for row in rows]
        # Sort by mid_mjd to ensure chronological order (should already be sorted, but enforce it)
        ms_paths_with_time.sort(key=lambda x: x[0])
        ms_paths = [path for _, path in ms_paths_with_time]
        # Store paths in chronological order (comma-separated)
        ms_paths_str = ",".join(ms_paths)

        existing = self.products_db.execute(
            "SELECT group_id FROM mosaic_groups WHERE ms_paths = ? AND status != 'completed'",
            (ms_paths_str,),
        ).fetchone()

        if existing:
            return existing[0]

        # Create new group
        group_id = f"group_{int(time.time())}"
        self.products_db.execute(
            """
            INSERT INTO mosaic_groups (group_id, ms_paths, created_at, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (group_id, ms_paths_str, time.time()),
        )
        self.products_db.commit()

        logger.info(
            f"Created new mosaic group: {group_id} with {len(ms_paths)} MS files (chronological order)"
        )
        return group_id

    def get_group_ms_paths(self, group_id: str) -> List[str]:
        """Get MS paths for a group in chronological order.

        CRITICAL: Returns paths sorted by observation time (mid_mjd), not alphabetical order.
        This ensures tiles are passed to the mosaic builder in chronological order.
        """
        row = self.products_db.execute(
            "SELECT ms_paths FROM mosaic_groups WHERE group_id = ?",
            (group_id,),
        ).fetchone()

        if not row:
            return []

        ms_paths = row[0].split(",")

        # CRITICAL: Sort by observation time (mid_mjd) to ensure chronological order
        # Extract mid_mjd for each path and sort
        ms_paths_with_time = []
        for ms_path in ms_paths:
            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
                if mid_mjd is not None:
                    ms_paths_with_time.append((mid_mjd, ms_path))
                else:
                    # If time extraction fails, log warning but include path
                    logger.warning(
                        f"Could not extract time from {ms_path}, using path order"
                    )
                    ms_paths_with_time.append((float("inf"), ms_path))  # Put at end
            except Exception as e:
                logger.warning(f"Error extracting time from {ms_path}: {e}")
                ms_paths_with_time.append((float("inf"), ms_path))  # Put at end

        # Sort by mid_mjd (chronological order)
        ms_paths_with_time.sort(key=lambda x: x[0])

        # Return paths in chronological order
        return [path for _, path in ms_paths_with_time]

    def select_calibration_ms(self, ms_paths: List[str]) -> Optional[str]:
        """Select the 5th MS (middle by time) for calibration solving.

        Args:
            ms_paths: List of MS file paths

        Returns:
            Path to calibration MS, or None if unable to determine
        """
        # Get mid_mjd for each MS
        ms_times = []
        for ms_path in ms_paths:
            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
                if mid_mjd is not None:
                    ms_times.append((mid_mjd, ms_path))
            except Exception as e:
                logger.warning(f"Failed to extract time from {ms_path}: {e}")
                continue

        if len(ms_times) < MS_PER_GROUP:
            logger.warning(
                f"Only {len(ms_times)} MS files have valid times, need {MS_PER_GROUP}"
            )
            return None

        # Sort by time and select 5th (index 4)
        ms_times.sort(key=lambda x: x[0])
        calibration_ms = ms_times[CALIBRATION_MS_INDEX][1]

        logger.info(
            f"Selected calibration MS: {calibration_ms} (5th of {len(ms_times)} MS)"
        )
        return calibration_ms

    def check_registry_for_calibration(
        self, ms_mid_mjd: float, table_types: List[str] = None
    ) -> Dict[str, List[str]]:
        """Check registry for existing valid calibration tables.

        Args:
            ms_mid_mjd: Observation time (MJD) to check
            table_types: List of table types to check (e.g., ['BP', 'GP', '2G'])

        Returns:
            Dictionary mapping table_type -> list of table paths (empty if not found)
        """
        if table_types is None:
            table_types = ["BP", "GP", "2G"]

        try:
            applylist = get_active_applylist(self.registry_db_path, ms_mid_mjd)
        except Exception as e:
            logger.warning(f"Registry query failed: {e}")
            return {t: [] for t in table_types}

        # Categorize tables by type
        result = {t: [] for t in table_types}

        for table_path in applylist:
            table_path_lower = table_path.lower()
            if "_bpcal" in table_path_lower or table_path.endswith("_bpcal"):
                result["BP"].append(table_path)
            elif "_gpcal" in table_path_lower or table_path.endswith("_gpcal"):
                result["GP"].append(table_path)
            elif "_2gcal" in table_path_lower or table_path.endswith("_2gcal"):
                result["2G"].append(table_path)

        return result

    def calculate_calibrator_transit(
        self, calibrator_ra: float, observation_date: Time
    ) -> float:
        """Calculate calibrator transit time (MJD).

        Args:
            calibrator_ra: Calibrator RA in degrees
            observation_date: Observation date/time

        Returns:
            Transit MJD
        """
        # Convert RA to hours
        ra_hours = calibrator_ra / 15.0

        # Calculate local sidereal time at transit
        # Transit occurs when LST = RA
        lst = observation_date.sidereal_time(
            "mean", longitude=self.observatory_location.lon
        )

        # Calculate time difference to transit
        ra_angle = calibrator_ra * u.deg
        lst_angle = lst.to(u.deg)
        hour_angle = ra_angle - lst_angle

        # Normalize to [-12, 12] hours
        hour_angle = hour_angle.wrap_at(12 * u.hourangle)

        # Transit time
        transit_time = observation_date + hour_angle.to(u.day)

        return transit_time.mjd

    def _get_organized_ms_path(
        self, ms_path: Path, is_calibrator: bool = False, date_str: Optional[str] = None
    ) -> Path:
        """Get organized path for MS file based on type and date.

        Organizes MS files into hierarchical structure:
        - Calibrator MS → ms/calibrators/YYYY-MM-DD/<timestamp>.ms/
        - Science MS → ms/science/YYYY-MM-DD/<timestamp>.ms/
        - Failed MS → ms/failed/YYYY-MM-DD/<timestamp>.ms/

        Args:
            ms_path: Current MS file path
            is_calibrator: Whether this is a calibrator observation
            date_str: Date string in YYYY-MM-DD format (extracted from MS filename if None)

        Returns:
            Organized path in appropriate subdirectory (date directory created if needed)
        """
        if date_str is None:
            # Extract date from MS filename or path
            ms_name = ms_path.stem
            # Try to extract date from filename (format: YYYY-MM-DDTHH:MM:SS)
            import re

            match = re.search(r"(\d{4}-\d{2}-\d{2})", ms_name)
            if match:
                date_str = match.group(1)
            else:
                # Fallback: use current date
                from datetime import datetime

                date_str = datetime.now().strftime("%Y-%m-%d")

        if is_calibrator:
            target_dir = self.ms_calibrators_dir / date_str
        else:
            target_dir = self.ms_science_dir / date_str

        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / ms_path.name

    def _get_calibration_table_prefix(
        self, ms_path: Path, is_calibrator: bool = False, date_str: Optional[str] = None
    ) -> Path:
        """Get organized path prefix for calibration tables.

        Calibration tables are stored alongside their corresponding calibrator MS files
        in the organized directory structure. The prefix is used to generate table names:
        - {prefix}_bpcal/ for bandpass tables
        - {prefix}_gpcal/ for gain phase tables
        - {prefix}_2gcal/ for short-timescale gain tables

        Args:
            ms_path: MS file path
            is_calibrator: Whether this is a calibrator observation
            date_str: Date string in YYYY-MM-DD format (extracted from MS filename if None)

        Returns:
            Path prefix for calibration tables (e.g., ms/calibrators/YYYY-MM-DD/timestamp)
            Tables will be created as {prefix}_bpcal/, {prefix}_gpcal/, etc.
        """
        organized_ms_path = self._get_organized_ms_path(
            ms_path, is_calibrator, date_str
        )
        return organized_ms_path.parent / organized_ms_path.stem

    def _organize_ms_file(
        self, ms_path: Path, is_calibrator: bool = False, date_str: Optional[str] = None
    ) -> Path:
        """Move MS file to organized directory structure.

        Organizes MS files into date-based subdirectories:
        - Calibrator MS → ms/calibrators/YYYY-MM-DD/
        - Science MS → ms/science/YYYY-MM-DD/
        - Failed MS → ms/failed/YYYY-MM-DD/

        After moving, updates the ms_index table in products.sqlite3 with the new path.
        This ensures the registry always reflects the current file location.

        Args:
            ms_path: Current MS file path
            is_calibrator: Whether this is a calibrator observation
            date_str: Date string in YYYY-MM-DD format (extracted from MS filename if None)

        Returns:
            New organized path (or original path if move fails or already organized)

        Note:
            Uses the shared ms_organization utility for consistency across the pipeline.
        """
        try:
            ms_base_dir = self.ms_output_dir
            is_failed = False  # StreamingMosaicManager doesn't handle failed MS

            organized_path = organize_ms_file(
                ms_path,
                ms_base_dir,
                self.products_db,
                is_calibrator=is_calibrator,
                is_failed=is_failed,
                date_str=date_str,
                update_database=True,
            )

            return organized_path
        except Exception as e:
            logger.warning(
                f"Failed to organize MS file {ms_path}: {e}. Using original path."
            )
            return ms_path

    def _retry_on_transient_error(
        self, func: Callable, *args, **kwargs
    ) -> Tuple[bool, Optional[str]]:
        """Retry a function on transient errors.

        Args:
            func: Function to retry (should return (success: bool, error_msg: Optional[str]))
            *args, **kwargs: Arguments to pass to func

        Returns:
            Tuple of (success, error_message)
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                success, error_msg = func(*args, **kwargs)
                if success:
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} succeeded on attempt {attempt + 1}"
                        )
                    return success, error_msg
                else:
                    last_error = error_msg
                    # Check if error is transient (I/O, network, etc.)
                    transient_keywords = [
                        "timeout",
                        "connection",
                        "network",
                        "i/o",
                        "disk",
                        "temporary",
                        "resource",
                        "busy",
                        "locked",
                    ]
                    is_transient = any(
                        keyword.lower() in str(error_msg).lower()
                        for keyword in transient_keywords
                    )

                    if not is_transient or attempt == self.max_retries - 1:
                        # Not transient or last attempt
                        return success, error_msg

                    logger.warning(
                        f"Transient error on attempt {attempt + 1}/{self.max_retries}: "
                        f"{error_msg}. Retrying in {self.retry_delay_seconds}s..."
                    )
                    time.sleep(self.retry_delay_seconds)
            except Exception as e:
                last_error = str(e)
                transient_keywords = [
                    "timeout",
                    "connection",
                    "network",
                    "i/o",
                    "disk",
                    "temporary",
                    "resource",
                    "busy",
                    "locked",
                ]
                is_transient = any(
                    keyword.lower() in last_error.lower()
                    for keyword in transient_keywords
                )

                if not is_transient or attempt == self.max_retries - 1:
                    return False, last_error

                logger.warning(
                    f"Transient exception on attempt {attempt + 1}/{self.max_retries}: "
                    f"{last_error}. Retrying in {self.retry_delay_seconds}s..."
                )
                time.sleep(self.retry_delay_seconds)

        return False, last_error

    def solve_calibration_for_group(
        self, group_id: str, calibration_ms_path: str
    ) -> Tuple[bool, bool, Optional[str]]:
        """Solve calibration for a group using the calibration MS.

        Args:
            group_id: Group identifier
            calibration_ms_path: Path to MS used for calibration solving

        Returns:
            Tuple of (bpcal_solved, gaincal_solved, error_message) where error_message
            is None on success or a descriptive error string on failure
        """
        try:
            _, _, mid_mjd = extract_ms_time_range(calibration_ms_path)
            if mid_mjd is None:
                error_msg = (
                    f"Could not extract time from calibration MS: {calibration_ms_path}"
                )
                logger.error(error_msg)
                return False, False, error_msg
        except Exception as e:
            error_msg = f"Failed to extract time from calibration MS: {e}"
            logger.error(error_msg)
            return False, False, error_msg

        # Check registry first
        registry_tables = self.check_registry_for_calibration(mid_mjd)
        has_bp = len(registry_tables.get("BP", [])) > 0
        has_g = (
            len(registry_tables.get("GP", [])) > 0
            and len(registry_tables.get("2G", [])) > 0
        )

        bpcal_solved = False
        gaincal_solved = False

        # Solve bandpass if not in registry
        if not has_bp:
            # Get observation Dec from calibration MS
            # Ensure CASAPATH is set before importing CASA modules
            from dsa110_contimg.utils.casa_init import ensure_casa_path
            ensure_casa_path()

            try:
                from casacore.tables import table

                t = table(calibration_ms_path)
                field_table = t.getkeyword("FIELD")
                import numpy as np

                dec_deg = np.mean(
                    [f["REFERENCE_DIR"][0][1] * 180 / np.pi for f in field_table]
                )
                t.close()

                # Check if bandpass calibrator is registered for this Dec
                bp_cal = self.get_bandpass_calibrator_for_dec(dec_deg)
                if not bp_cal:
                    error_msg = (
                        f"No bandpass calibrator registered for Dec={dec_deg:.6f}. "
                        f"Cannot proceed with calibration. Please register a calibrator first."
                    )
                    logger.error(error_msg)
                    return False, False, error_msg

                logger.info(
                    f"Found bandpass calibrator {bp_cal['name']} "
                    f"for Dec={dec_deg:.6f} (RA={bp_cal['ra_deg']:.6f})"
                )

                # Check if calibrator is present in any MS in the group
                ms_paths = self.get_group_ms_paths(group_id)
                calibrator_ms = None
                cal_field_sel = None
                calibrator_info = None

                # Try to find calibrator in each MS file
                for ms_path in ms_paths:
                    try:
                        # Use select_bandpass_from_catalog to find calibrator in MS
                        # This searches for calibrators near the pointing and selects optimal fields
                        (
                            field_sel_str,
                            field_indices,
                            weighted_flux,
                            cal_info,
                            peak_field_idx,
                        ) = select_bandpass_from_catalog(
                            str(ms_path),
                            catalog_path=None,  # Auto-resolve to SQLite catalog
                            search_radius_deg=1.0,
                            freq_GHz=1.4,
                            window=3,
                        )

                        # Check if the found calibrator matches our registered calibrator
                        if cal_info and cal_info[0] == bp_cal["name"]:
                            # Validate calibrator visibility: check flux and PB response
                            cal_name, cal_ra, cal_dec, cal_flux_jy = cal_info

                            # Check flux threshold
                            if cal_flux_jy < self.min_calibrator_flux_jy:
                                logger.warning(
                                    f"Calibrator {cal_name} flux ({cal_flux_jy:.3f} Jy) "
                                    f"below minimum threshold ({self.min_calibrator_flux_jy:.3f} Jy) "
                                    f"in {ms_path}. Skipping."
                                )
                                continue

                            # Check PB-weighted flux at peak field
                            if len(weighted_flux) > 0 and peak_field_idx is not None:
                                peak_pb_flux = (
                                    weighted_flux[peak_field_idx]
                                    if peak_field_idx < len(weighted_flux)
                                    else 0.0
                                )
                                pb_response = (
                                    peak_pb_flux / cal_flux_jy
                                    if cal_flux_jy > 0
                                    else 0.0
                                )

                                if pb_response < self.min_calibrator_pb_response:
                                    logger.warning(
                                        f"Calibrator {cal_name} PB response ({pb_response:.3f}) "
                                        f"below minimum threshold ({self.min_calibrator_pb_response:.3f}) "
                                        f"in {ms_path}. Skipping."
                                    )
                                    continue

                            calibrator_ms = str(ms_path)
                            cal_field_sel = field_sel_str
                            calibrator_info = cal_info
                            logger.info(
                                f"Found and validated calibrator {bp_cal['name']} in {ms_path} "
                                f"at fields {field_sel_str} (peak field: {peak_field_idx}, "
                                f"flux: {cal_flux_jy:.3f} Jy, PB response: {pb_response:.3f})"
                            )
                            break
                    except Exception as e:
                        logger.debug(f"Could not find calibrator in {ms_path}: {e}")
                        continue

                # If not found via catalog search, try calibration MS directly
                if not calibrator_ms:
                    try:
                        (
                            field_sel_str,
                            field_indices,
                            weighted_flux,
                            cal_info,
                            peak_field_idx,
                        ) = select_bandpass_from_catalog(
                            str(calibration_ms_path),
                            catalog_path=None,
                            search_radius_deg=1.0,
                            freq_GHz=1.4,
                            window=3,
                        )
                        if cal_info and cal_info[0] == bp_cal["name"]:
                            # Validate calibrator visibility
                            cal_name, cal_ra, cal_dec, cal_flux_jy = cal_info

                            if cal_flux_jy < self.min_calibrator_flux_jy:
                                logger.warning(
                                    f"Calibrator {cal_name} flux ({cal_flux_jy:.3f} Jy) "
                                    f"below minimum threshold ({self.min_calibrator_flux_jy:.3f} Jy) "
                                    f"in calibration MS. Skipping."
                                )
                            elif len(weighted_flux) > 0 and peak_field_idx is not None:
                                peak_pb_flux = (
                                    weighted_flux[peak_field_idx]
                                    if peak_field_idx < len(weighted_flux)
                                    else 0.0
                                )
                                pb_response = (
                                    peak_pb_flux / cal_flux_jy
                                    if cal_flux_jy > 0
                                    else 0.0
                                )

                                if pb_response < self.min_calibrator_pb_response:
                                    logger.warning(
                                        f"Calibrator {cal_name} PB response ({pb_response:.3f}) "
                                        f"below minimum threshold ({self.min_calibrator_pb_response:.3f}) "
                                        f"in calibration MS. Skipping."
                                    )
                                else:
                                    calibrator_ms = str(calibration_ms_path)
                                    cal_field_sel = field_sel_str
                                    calibrator_info = cal_info
                                    logger.info(
                                        f"Found and validated calibrator {bp_cal['name']} in calibration MS "
                                        f"at fields {field_sel_str} (flux: {cal_flux_jy:.3f} Jy, "
                                        f"PB response: {pb_response:.3f})"
                                    )
                            else:
                                # No PB response data, proceed with caution
                                logger.warning(
                                    f"Could not compute PB response for calibrator {cal_name}. "
                                    f"Proceeding with caution."
                                )
                                calibrator_ms = str(calibration_ms_path)
                                cal_field_sel = field_sel_str
                                calibrator_info = cal_info
                    except Exception as e:
                        logger.debug(
                            f"Could not find calibrator in calibration MS: {e}"
                        )

                if calibrator_ms and cal_field_sel:
                    logger.info(
                        f"Solving bandpass calibration using {bp_cal['name']} "
                        f"in {calibrator_ms} at fields {cal_field_sel}"
                    )
                    try:
                        # Prepare organized table prefix for calibration tables
                        calibrator_ms_path = Path(calibrator_ms)
                        # Extract date from MS filename
                        ms_name = calibrator_ms_path.stem
                        import re

                        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", ms_name)
                        date_str = date_match.group(1) if date_match else None

                        table_prefix = str(
                            self._get_calibration_table_prefix(
                                calibrator_ms_path,
                                is_calibrator=True,
                                date_str=date_str,
                            )
                        )

                        # Solve bandpass calibration with retry logic for transient errors
                        bp_tables = None
                        last_error = None
                        for attempt in range(self.max_retries):
                            try:
                                bp_tables = solve_bandpass(
                                    ms=calibrator_ms,
                                    cal_field=cal_field_sel,
                                    refant=self.refant,
                                    ktable=None,  # No delay table needed for standard calibration
                                    table_prefix=table_prefix,
                                    set_model=True,
                                    model_standard=self.calibration_params[
                                        "model_standard"
                                    ],
                                    combine_fields=self.calibration_params[
                                        "combine_fields"
                                    ],
                                    combine_spw=self.calibration_params["combine_spw"],
                                    minsnr=self.calibration_params["minsnr"],
                                    uvrange=self.calibration_params["uvrange"],
                                )
                                if bp_tables and len(bp_tables) > 0:
                                    if attempt > 0:
                                        logger.info(
                                            f"Bandpass solving succeeded on attempt {attempt + 1}"
                                        )
                                    break
                                else:
                                    last_error = "No tables returned"
                                    if attempt == self.max_retries - 1:
                                        break
                            except Exception as e:
                                last_error = str(e)
                                transient_keywords = [
                                    "timeout",
                                    "connection",
                                    "network",
                                    "i/o",
                                    "disk",
                                    "temporary",
                                    "resource",
                                    "busy",
                                    "locked",
                                ]
                                is_transient = any(
                                    keyword.lower() in last_error.lower()
                                    for keyword in transient_keywords
                                )

                                if not is_transient or attempt == self.max_retries - 1:
                                    break

                                logger.warning(
                                    f"Transient error on attempt {attempt + 1}/{self.max_retries}: "
                                    f"{last_error}. Retrying in {self.retry_delay_seconds}s..."
                                )
                                time.sleep(self.retry_delay_seconds)

                        if bp_tables and len(bp_tables) > 0:
                            logger.info(
                                f"Bandpass calibration solved successfully: {bp_tables}"
                            )

                            # Register bandpass calibration tables with transit-centered validity window
                            # Validity: ±bp_validity_hours around calibrator transit time
                            transit_mjd = self.calculate_calibrator_transit(
                                bp_cal["ra_deg"], Time(mid_mjd, format="mjd")
                            )
                            validity_days = self.bp_validity_hours / 24.0
                            valid_start_mjd = transit_mjd - validity_days
                            valid_end_mjd = transit_mjd + validity_days

                            # Register tables - only set bpcal_solved=True if registration succeeds
                            try:
                                set_name = f"{ms_stem}_bp_{transit_mjd:.6f}"
                                register_set_from_prefix(
                                    self.registry_db_path,
                                    set_name,
                                    Path(table_prefix),
                                    cal_field=cal_field_sel,
                                    refant=self.refant,
                                    valid_start_mjd=valid_start_mjd,
                                    valid_end_mjd=valid_end_mjd,
                                )
                                bpcal_solved = (
                                    True  # Only set True after successful registration
                                )
                                logger.info(
                                    f"Registered bandpass calibration with validity window: "
                                    f"{valid_start_mjd:.6f} - {valid_end_mjd:.6f} MJD "
                                    f"(centered on transit at {transit_mjd:.6f} MJD)"
                                )

                                # Organize calibration MS file to calibrators directory
                                organized_cal_ms = self._organize_ms_file(
                                    calibrator_ms_path,
                                    is_calibrator=True,
                                    date_str=date_str,
                                )
                                logger.debug(
                                    f"Organized calibration MS to: {organized_cal_ms}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Failed to register bandpass calibration tables: {e}. "
                                    f"Calibration tables exist but are not registered. "
                                    f"Marking BP calibration as failed."
                                )
                                bpcal_solved = False  # Ensure consistent state
                        else:
                            logger.error(
                                "Bandpass calibration solving returned no tables"
                            )
                            bpcal_solved = False
                    except Exception as e:
                        logger.error(
                            f"Failed to solve bandpass calibration: {e}", exc_info=True
                        )
                else:
                    logger.warning(
                        f"Bandpass calibrator {bp_cal['name']} not found in group MS files"
                    )

            except Exception as e:
                error_msg = f"Failed to check bandpass calibrator: {e}"
                logger.error(error_msg, exc_info=True)
                return False, False, error_msg
        else:
            logger.info("BP calibration found in registry, skipping solve")

        # Solve gain calibration if not in registry
        if not has_g:
            logger.info("Solving gain calibration...")
            try:
                # Get BP tables from registry if available, otherwise use empty list
                bp_tables_list = registry_tables.get("BP", [])
                if not bp_tables_list and bpcal_solved:
                    # BP was just solved, get tables from the calibration MS
                    cal_ms_path = Path(calibration_ms_path)
                    ms_name = cal_ms_path.stem
                    # Extract date from filename for organized path
                    import re

                    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", ms_name)
                    date_str = date_match.group(1) if date_match else None
                    table_prefix = self._get_calibration_table_prefix(
                        cal_ms_path, is_calibrator=True, date_str=date_str
                    )
                    # Look for BP tables with the expected naming pattern (_bpcal directory)
                    bp_table_path = (
                        Path(table_prefix).parent / f"{table_prefix.name}_bpcal"
                    )
                    if bp_table_path.exists() and bp_table_path.is_dir():
                        bp_tables_list = [str(bp_table_path)]

                # Select calibrator field for gain solving
                try:
                    (
                        field_sel_str,
                        field_indices,
                        weighted_flux,
                        cal_info,
                        peak_field_idx,
                    ) = select_bandpass_from_catalog(
                        str(calibration_ms_path),
                        catalog_path=None,  # Auto-resolve to SQLite catalog
                        search_radius_deg=1.0,
                        freq_GHz=1.4,
                        window=3,
                    )
                    if not cal_info:
                        raise ValueError(
                            "No calibrator found in MS for gain calibration"
                        )
                except Exception as e:
                    error_msg = (
                        f"Failed to select calibrator field for gain calibration: {e}"
                    )
                    logger.error(error_msg)
                    return bpcal_solved, False, error_msg

                # Populate MODEL_DATA before solving gains
                try:
                    populate_model_from_catalog(
                        calibration_ms_path,
                        cal_field=field_sel_str,
                        catalog_path=None,  # Auto-resolve to SQLite catalog
                    )
                    logger.debug("MODEL_DATA populated for gain calibration")
                except Exception as e:
                    logger.warning(
                        f"Failed to populate MODEL_DATA: {e}. Proceeding anyway."
                    )

                # Prepare organized table prefix for calibration tables
                cal_ms_path = Path(calibration_ms_path)
                # Extract date from MS filename
                ms_name = cal_ms_path.stem
                import re

                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", ms_name)
                date_str = date_match.group(1) if date_match else None

                # Determine if this is a calibrator MS (check if it's used for calibration solving)
                # For now, assume calibration MS is a calibrator observation
                table_prefix = str(
                    self._get_calibration_table_prefix(
                        cal_ms_path, is_calibrator=True, date_str=date_str
                    )
                )

                # Solve gain calibration using direct API
                gain_tables = solve_gains(
                    ms=calibration_ms_path,
                    cal_field=field_sel_str,
                    refant=self.refant,
                    ktable=None,  # No delay table for DSA-110
                    bptables=bp_tables_list,
                    table_prefix=table_prefix,
                    t_short="60s",
                    combine_fields=self.calibration_params["combine_fields"],
                    minsnr=self.calibration_params["minsnr"],
                    uvrange=self.calibration_params["uvrange"],
                    peak_field_idx=peak_field_idx,
                )

                if gain_tables and len(gain_tables) > 0:
                    logger.info(f"Gain calibration solved successfully: {gain_tables}")

                    # Register gain calibration tables with validity windows
                    # Validity: ±gain_validity_minutes around calibration MS observation time
                    cal_ms_start, cal_ms_end, cal_ms_mid = extract_ms_time_range(
                        calibration_ms_path
                    )
                    if cal_ms_mid is not None:
                        validity_days = self.gain_validity_minutes / 1440.0
                        valid_start_mjd = cal_ms_mid - validity_days
                        valid_end_mjd = cal_ms_mid + validity_days

                        # Register tables
                        try:
                            set_name = f"{ms_stem}_g_{cal_ms_mid:.6f}"
                            register_set_from_prefix(
                                self.registry_db_path,
                                set_name,
                                Path(table_prefix),
                                cal_field=field_sel_str,
                                refant=self.refant,
                                valid_start_mjd=valid_start_mjd,
                                valid_end_mjd=valid_end_mjd,
                            )
                            gaincal_solved = (
                                True  # Only set True after successful registration
                            )
                            logger.info(
                                f"Registered gain calibration with validity window: "
                                f"{valid_start_mjd:.6f} - {valid_end_mjd:.6f} MJD"
                            )

                            # Organize calibration MS file to calibrators directory (if not already organized)
                            organized_cal_ms = self._organize_ms_file(
                                cal_ms_path, is_calibrator=True, date_str=date_str
                            )
                            logger.debug(
                                f"Organized calibration MS to: {organized_cal_ms}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to register gain calibration tables: {e}. "
                                f"Calibration tables exist but are not registered. "
                                f"Marking gain calibration as failed."
                            )
                            gaincal_solved = False  # Ensure consistent state
                    else:
                        logger.error(
                            "Could not extract time from calibration MS for registration"
                        )
                        gaincal_solved = False
                else:
                    logger.error("Gain calibration solving returned no tables")
                    gaincal_solved = False
            except Exception as e:
                error_msg = f"Gain calibration solving failed: {e}"
                logger.error(error_msg, exc_info=True)
                gaincal_solved = False
                return bpcal_solved, gaincal_solved, error_msg
        else:
            logger.info("Gain calibration found in registry, skipping solve")

        # Update group status
        self.products_db.execute(
            """
            UPDATE mosaic_groups
            SET calibration_ms_path = ?, bpcal_solved = ?
            WHERE group_id = ?
            """,
            (calibration_ms_path, 1 if bpcal_solved else 0, group_id),
        )
        self.products_db.commit()

        return bpcal_solved, gaincal_solved, None

    def apply_calibration_to_group(self, group_id: str) -> bool:
        """Apply calibration from registry to all MS files in group.

        Args:
            group_id: Group identifier

        Returns:
            True if successful, False otherwise
        """
        ms_paths = self.get_group_ms_paths(group_id)
        if not ms_paths:
            logger.error(f"No MS paths found for group {group_id}")
            return False

        success_count = 0
        for ms_path in ms_paths:
            try:
                ms_path_obj = Path(ms_path)
                _, _, mid_mjd = extract_ms_time_range(str(ms_path_obj))
                if mid_mjd is None:
                    logger.warning(f"Could not extract time from {ms_path}, skipping")
                    continue

                # Query registry for valid calibration tables
                applylist = get_active_applylist(self.registry_db_path, mid_mjd)

                if not applylist:
                    logger.warning(
                        f"No valid calibration tables found in registry for {ms_path}"
                    )
                    continue

                # Apply calibration
                apply_to_target(
                    str(ms_path_obj), field="", gaintables=applylist, calwt=True
                )

                # Organize MS file to science directory after calibration
                # Extract date from filename
                ms_name = ms_path_obj.stem
                import re

                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", ms_name)
                date_str = date_match.group(1) if date_match else None

                organized_path = self._organize_ms_file(
                    ms_path_obj, is_calibrator=False, date_str=date_str
                )

                # Update products database with organized path
                ms_index_upsert(
                    self.products_db,
                    str(organized_path),
                    stage="calibrated",
                    cal_applied=1,
                )

                success_count += 1
                logger.info(
                    f"Applied calibration to {ms_path} (organized to {organized_path})"
                )

            except Exception as e:
                logger.error(
                    f"Failed to apply calibration to {ms_path}: {e}", exc_info=True
                )

        self.products_db.commit()

        if success_count == len(ms_paths):
            self.products_db.execute(
                """
                UPDATE mosaic_groups
                SET calibrated_at = ?, status = 'calibrated'
                WHERE group_id = ?
                """,
                (time.time(), group_id),
            )
            self.products_db.commit()
            return True
        else:
            logger.warning(
                f"Only {success_count}/{len(ms_paths)} MS files calibrated successfully"
            )
            return False

    def image_group(self, group_id: str) -> bool:
        """Image all MS files in group individually.

        Args:
            group_id: Group identifier

        Returns:
            True if successful, False otherwise
        """
        ms_paths = self.get_group_ms_paths(group_id)
        if not ms_paths:
            return False

        success_count = 0
        image_paths = []

        for ms_path in ms_paths:
            try:
                # Derive image name from MS path
                ms_name = Path(ms_path).stem
                imgroot = str(self.images_dir / ms_name) + ".img"

                # Image MS
                image_ms(
                    ms_path,
                    imagename=imgroot,
                    field="",
                    quality_tier="standard",
                    skip_fits=False,
                )

                # Update products database
                ms_index_upsert(
                    self.products_db,
                    ms_path,
                    stage="imaged",
                    status="done",
                    imagename=imgroot,
                )

                # Find PB-corrected image
                # WSClean outputs FITS files: .img-image-pb.fits
                # CASA tclean outputs: .pbcor or .image
                pbcor_fits = f"{imgroot}-image-pb.fits"  # WSClean format
                pbcor_path = f"{imgroot}.pbcor"  # CASA format
                image_path = f"{imgroot}.image"  # CASA format

                if Path(pbcor_fits).exists():
                    image_paths.append(pbcor_fits)
                elif Path(pbcor_path).exists():
                    image_paths.append(pbcor_path)
                elif Path(image_path).exists():
                    image_paths.append(image_path)

                success_count += 1

            except Exception as e:
                logger.error(f"Failed to image {ms_path}: {e}", exc_info=True)

        self.products_db.commit()

        if success_count == len(ms_paths):
            self.products_db.execute(
                """
                UPDATE mosaic_groups
                SET imaged_at = ?, status = 'imaged'
                WHERE group_id = ?
                """,
                (time.time(), group_id),
            )
            self.products_db.commit()
            return True
        else:
            logger.warning(
                f"Only {success_count}/{len(ms_paths)} MS files imaged successfully"
            )
            return False

    def create_mosaic(self, group_id: str) -> Optional[str]:
        """Create mosaic from group of 10 images.

        Args:
            group_id: Group identifier

        Returns:
            Mosaic output path if successful, None otherwise.
            Prefers FITS format (.fits extension) if available, otherwise returns
            CASA image format (.image directory).
        """
        ms_paths = self.get_group_ms_paths(group_id)
        if not ms_paths:
            return None

        # CRITICAL: Validate that MS paths are in chronological order
        # This ensures tiles are passed to mosaic builder in correct order
        ms_times = []
        for ms_path in ms_paths:
            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
                if mid_mjd is not None:
                    ms_times.append(mid_mjd)
                else:
                    logger.warning(
                        f"Could not extract time from {ms_path} for chronological validation"
                    )
            except Exception as e:
                logger.warning(
                    f"Error extracting time from {ms_path} for validation: {e}"
                )

        # Check if times are in chronological order
        if len(ms_times) > 1:
            is_chronological = all(
                ms_times[i] <= ms_times[i + 1] for i in range(len(ms_times) - 1)
            )
            if not is_chronological:
                logger.error(
                    f"MS paths for group {group_id} are NOT in chronological order! "
                    f"Times: {ms_times}. This will cause mosaic artifacts."
                )
                # Re-sort by time to fix order
                ms_paths_with_time = []
                for ms_path in ms_paths:
                    try:
                        _, _, mid_mjd = extract_ms_time_range(ms_path)
                        if mid_mjd is not None:
                            ms_paths_with_time.append((mid_mjd, ms_path))
                    except Exception:
                        pass
                ms_paths_with_time.sort(key=lambda x: x[0])
                ms_paths = [path for _, path in ms_paths_with_time]
                logger.info(
                    f"Re-sorted MS paths to chronological order for group {group_id}"
                )
            else:
                logger.debug(
                    f"MS paths for group {group_id} are in chronological order (validated)"
                )

        # Get image paths (in chronological order)
        image_paths = []
        for ms_path in ms_paths:
            row = self.products_db.execute(
                "SELECT imagename FROM ms_index WHERE path = ?",
                (ms_path,),
            ).fetchone()
            if row and row[0]:
                imagename = row[0]
                # Handle both base paths and full paths
                # Try multiple path construction strategies
                found_image = None

                # Strategy 1: Check if imagename is already a full path to an existing file
                if Path(imagename).exists():
                    found_image = imagename
                else:
                    # Strategy 2: Try WSClean FITS format (.img-image-pb.fits)
                    pbcor_fits = f"{imagename}-image-pb.fits"
                    if Path(pbcor_fits).exists():
                        found_image = pbcor_fits
                    else:
                        # Strategy 3: Try CASA PB-corrected format (.pbcor)
                        pbcor = f"{imagename}.pbcor"
                        if Path(pbcor).exists():
                            found_image = pbcor
                        else:
                            # Strategy 4: Try CASA image format (.image)
                            image = f"{imagename}.image"
                            if Path(image).exists():
                                found_image = image
                            else:
                                # Strategy 5: If imagename has extension, try removing it and reconstructing
                                base = (
                                    str(imagename)
                                    .replace(".image", "")
                                    .replace(".pbcor", "")
                                    .replace(".pb", "")
                                )
                                for candidate in [
                                    f"{base}-image-pb.fits",
                                    f"{base}.pbcor",
                                    f"{base}.image",
                                ]:
                                    if Path(candidate).exists():
                                        found_image = candidate
                                        break

                if found_image:
                    image_paths.append(found_image)
                else:
                    logger.warning(
                        f"Could not find image for MS {Path(ms_path).name}, imagename={imagename}"
                    )

        if len(image_paths) < MS_PER_GROUP:
            logger.warning(f"Only {len(image_paths)} images found, need {MS_PER_GROUP}")
            return None

        # Generate mosaic
        mosaic_id = f"mosaic_{group_id}_{int(time.time())}"
        mosaic_path = str(self.mosaic_output_dir / f"{mosaic_id}.image")

        try:
            # Lazy import to avoid syntax errors
            from dsa110_contimg.mosaic.cli import _build_weighted_mosaic

            # Get metrics_dict from validation
            # This validates tiles and computes quality metrics for mosaic building
            is_valid, issues, metrics_dict = validate_tiles_consistency(
                image_paths,
                products_db=self.products_db_path,
            )

            if not is_valid and issues:
                logger.warning(
                    f"Tile validation found issues: {', '.join(issues[:5])}"
                    f"{' (and more)' if len(issues) > 5 else ''}"
                )

            _build_weighted_mosaic(image_paths, metrics_dict, mosaic_path)

            # Check if FITS file was created (preferred output format)
            # FITS path is created by stripping .image and adding .fits
            mosaic_base = mosaic_path.replace(".image", "")
            fits_path = mosaic_base + ".fits"
            if Path(fits_path).exists():
                final_mosaic_path = fits_path
            else:
                final_mosaic_path = mosaic_path

            # Generate PNG visualization automatically
            try:
                from dsa110_contimg.imaging.export import export_fits, save_png_from_fits
                
                # If we have a CASA image but no FITS, export to FITS first
                png_source_path = fits_path if Path(fits_path).exists() else None
                if not png_source_path:
                    logger.info("Exporting CASA image to FITS for PNG generation...")
                    exported_fits = export_fits([mosaic_path])
                    if exported_fits:
                        png_source_path = exported_fits[0]
                        logger.info(f"Exported FITS: {png_source_path}")
                    else:
                        logger.warning("Failed to export FITS for PNG generation")
                
                # Generate PNG from FITS
                if png_source_path:
                    logger.info("Generating PNG visualization...")
                    png_files = save_png_from_fits([png_source_path])
                    if png_files:
                        png_path = png_files[0]
                        logger.info(f"PNG visualization created: {png_path}")
                    else:
                        logger.warning("Failed to generate PNG visualization")
            except Exception as e:
                # Don't fail the mosaic creation if PNG generation fails
                logger.warning(f"PNG visualization generation failed (non-critical): {e}")

            # Update group status
            self.products_db.execute(
                """
                UPDATE mosaic_groups
                SET mosaic_id = ?, mosaicked_at = ?, status = 'completed'
                WHERE group_id = ?
                """,
                (mosaic_id, time.time(), group_id),
            )
            self.products_db.commit()

            logger.info(f"Mosaic created: {final_mosaic_path}")
            return final_mosaic_path

        except Exception as e:
            logger.error(f"Failed to create mosaic: {e}", exc_info=True)
            return None

    def process_next_group(self) -> bool:
        """Process next available group through full workflow.

        Returns:
            True if a group was processed, False if no group available
        """
        group_id = self.check_for_new_group()
        if not group_id:
            return False

        logger.info(f"Processing group: {group_id}")

        # Get MS paths
        ms_paths = self.get_group_ms_paths(group_id)
        if len(ms_paths) < MS_PER_GROUP:
            logger.warning(f"Group {group_id} has only {len(ms_paths)} MS files")
            return False

        # Select calibration MS
        calibration_ms = self.select_calibration_ms(ms_paths)
        if not calibration_ms:
            logger.error(f"Could not select calibration MS for group {group_id}")
            return False

        # Solve calibration
        bpcal_solved, gaincal_solved, error_msg = self.solve_calibration_for_group(
            group_id, calibration_ms
        )
        if error_msg:
            logger.error(
                f"Calibration solving failed for group {group_id}: {error_msg}"
            )
            return False

        # Apply calibration
        if not self.apply_calibration_to_group(group_id):
            logger.error(f"Failed to apply calibration to group {group_id}")
            return False

        # Image all MS
        if not self.image_group(group_id):
            logger.error(f"Failed to image group {group_id}")
            return False

        # Create mosaic
        mosaic_path = self.create_mosaic(group_id)
        if not mosaic_path:
            logger.error(f"Failed to create mosaic for group {group_id}")
            return False

        logger.info(f"Successfully processed group {group_id}, mosaic: {mosaic_path}")
        return True

    def get_last_group_overlap_ms(self) -> List[str]:
        """Get the last 2 MS files from the most recent completed group for overlap.

        Returns:
            List of 2 MS paths (empty if no previous group)
        """
        row = self.products_db.execute(
            """
            SELECT ms_paths
            FROM mosaic_groups
            WHERE status = 'completed'
            ORDER BY mosaicked_at DESC
            LIMIT 1
            """
        ).fetchone()

        if not row:
            return []

        ms_paths = row[0].split(",")
        if len(ms_paths) < MS_OVERLAP:
            return []

        # Get last 2 MS files (by time)
        ms_times = []
        for ms_path in ms_paths:
            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
                if mid_mjd is not None:
                    ms_times.append((mid_mjd, ms_path))
            except Exception:
                continue

        ms_times.sort(key=lambda x: x[0])
        return [ms_times[-2][1], ms_times[-1][1]]  # Last 2

    def clear_calibration_from_ms(self, ms_path: str) -> None:
        """Clear calibration tables from an MS file (for overlap reuse).

        Args:
            ms_path: Path to MS file
        """
        ms_dir = Path(ms_path).parent
        ms_stem = Path(ms_path).stem

        # Find and remove calibration tables
        cal_patterns = ["_bpcal", "_gpcal", "_2gcal"]
        removed = []

        for pattern in cal_patterns:
            cal_table = ms_dir / f"{ms_stem}{pattern}"
            if cal_table.exists():
                try:
                    import shutil

                    if cal_table.is_dir():
                        shutil.rmtree(cal_table)
                    else:
                        cal_table.unlink()
                    removed.append(str(cal_table))
                except Exception as e:
                    logger.warning(f"Failed to remove {cal_table}: {e}")

        if removed:
            logger.info(f"Cleared calibration tables from {ms_path}: {removed}")

        # Update products database
        ms_index_upsert(
            self.products_db,
            ms_path,
            cal_applied=0,
            stage="converted",  # Reset to converted stage
        )
        self.products_db.commit()

    def check_for_sliding_window_group(self) -> Optional[str]:
        """Check if a new sliding window group is ready (8 new + 2 overlap).

        Returns:
            Group ID if ready, None otherwise
        """
        # Get overlap MS from last group
        overlap_ms = self.get_last_group_overlap_ms()

        # Query for new MS files (excluding overlap MS)
        overlap_set = set(overlap_ms) if overlap_ms else set()

        rows = self.products_db.execute(
            """
            SELECT path, mid_mjd
            FROM ms_index
            WHERE stage = 'converted' AND status = 'converted'
            ORDER BY mid_mjd ASC
            """
        ).fetchall()

        # Filter out overlap MS and get new MS
        new_ms = [(row[0], row[1]) for row in rows if row[0] not in overlap_set]

        if len(new_ms) < MS_NEW_PER_MOSAIC:
            return None

        # Combine overlap + new MS
        all_ms = []

        # Add overlap MS first (if available)
        if overlap_ms:
            for ms_path in overlap_ms:
                try:
                    _, _, mid_mjd = extract_ms_time_range(ms_path)
                    if mid_mjd is not None:
                        all_ms.append((mid_mjd, ms_path))
                except Exception:
                    pass

        # Add new MS
        all_ms.extend(new_ms[:MS_NEW_PER_MOSAIC])

        # Sort by time (chronological order)
        all_ms.sort(key=lambda x: x[0])

        if len(all_ms) < MS_PER_GROUP:
            return None

        # Clear calibration from overlap MS
        if overlap_ms:
            for ms_path in overlap_ms:
                self.clear_calibration_from_ms(ms_path)

        # Create group
        # CRITICAL: Keep paths in chronological order (by mid_mjd), not alphabetical
        ms_paths = [ms[1] for ms in all_ms]
        # Store paths in chronological order (already sorted by mid_mjd above)
        ms_paths_str = ",".join(ms_paths)

        # Check if group already exists
        existing = self.products_db.execute(
            "SELECT group_id FROM mosaic_groups WHERE ms_paths = ? AND status != 'completed'",
            (ms_paths_str,),
        ).fetchone()

        if existing:
            return existing[0]

        group_id = f"group_{int(time.time())}"
        self.products_db.execute(
            """
            INSERT INTO mosaic_groups (group_id, ms_paths, created_at, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (group_id, ms_paths_str, time.time()),
        )
        self.products_db.commit()

        logger.info(
            f"Created sliding window group: {group_id} "
            f"({len(overlap_ms)} overlap + {len(new_ms[:MS_NEW_PER_MOSAIC])} new MS)"
        )
        return group_id

    def validate_group_dec(self, ms_paths: List[str]) -> Tuple[bool, Optional[float]]:
        """Validate that a bandpass calibrator is registered for the group's Dec.

        Args:
            ms_paths: List of MS file paths

        Returns:
            Tuple of (is_valid, dec_deg) or (False, None) if validation fails
        """
        # Get Dec from first MS
        try:
            from casacore.tables import table

            t = table(ms_paths[0])
            field_table = t.getkeyword("FIELD")
            import numpy as np

            dec_deg = np.mean(
                [f["REFERENCE_DIR"][0][1] * 180 / np.pi for f in field_table]
            )
            t.close()

            # Check if calibrator is registered
            bp_cal = self.get_bandpass_calibrator_for_dec(dec_deg)
            if not bp_cal:
                logger.error(
                    f"No bandpass calibrator registered for Dec={dec_deg:.6f}. "
                    f"Cannot process group. Please register a calibrator first."
                )
                return False, None

            logger.info(
                f"Group Dec={dec_deg:.6f} validated: "
                f"bandpass calibrator {bp_cal['name']} is registered"
            )
            return True, dec_deg

        except Exception as e:
            logger.error(f"Failed to validate group Dec: {e}", exc_info=True)
            return False, None

    def process_next_group(self, use_sliding_window: bool = True) -> bool:
        """Process next available group through full workflow.

        Args:
            use_sliding_window: If True, use sliding window logic (8 new + 2 overlap)

        Returns:
            True if a group was processed, False if no group available
        """
        if use_sliding_window:
            group_id = self.check_for_sliding_window_group()
        else:
            group_id = self.check_for_new_group()

        if not group_id:
            return False

        logger.info(f"Processing group: {group_id}")

        # Get MS paths
        ms_paths = self.get_group_ms_paths(group_id)
        if len(ms_paths) < MS_PER_GROUP:
            logger.warning(f"Group {group_id} has only {len(ms_paths)} MS files")
            return False

        # Validate Dec and calibrator registration
        is_valid, dec_deg = self.validate_group_dec(ms_paths)
        if not is_valid:
            logger.error(
                f"Group {group_id} validation failed: no calibrator registered for Dec"
            )
            return False

        # Select calibration MS
        calibration_ms = self.select_calibration_ms(ms_paths)
        if not calibration_ms:
            logger.error(f"Could not select calibration MS for group {group_id}")
            return False

        # Solve calibration
        bpcal_solved, gaincal_solved, error_msg = self.solve_calibration_for_group(
            group_id, calibration_ms
        )
        if error_msg:
            logger.error(
                f"Calibration solving failed for group {group_id}: {error_msg}"
            )
            return False

        # Apply calibration
        if not self.apply_calibration_to_group(group_id):
            logger.error(f"Failed to apply calibration to group {group_id}")
            return False

        # Image all MS
        if not self.image_group(group_id):
            logger.error(f"Failed to image group {group_id}")
            return False

        # Create mosaic
        mosaic_path = self.create_mosaic(group_id)
        if not mosaic_path:
            logger.error(f"Failed to create mosaic for group {group_id}")
            return False

        logger.info(f"Successfully processed group {group_id}, mosaic: {mosaic_path}")
        return True


def main() -> int:
    """CLI entry point for streaming mosaic processing."""
    import argparse

    parser = argparse.ArgumentParser(description="Process streaming mosaic groups")
    parser.add_argument(
        "--products-db",
        type=Path,
        default=Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3")),
        help="Path to products database",
    )
    parser.add_argument(
        "--registry-db",
        type=Path,
        default=Path(os.getenv("CAL_REGISTRY_DB", "state/cal_registry.sqlite3")),
        help="Path to calibration registry database",
    )
    parser.add_argument(
        "--ms-dir",
        type=Path,
        default=Path(os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/ms")),
        help="Directory containing MS files",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path(os.getenv("CONTIMG_IMAGES_DIR", "/stage/dsa110-contimg/images")),
        help="Directory for individual image outputs",
    )
    parser.add_argument(
        "--mosaic-dir",
        type=Path,
        default=Path(os.getenv("CONTIMG_MOSAIC_DIR", "/stage/dsa110-contimg/mosaics")),
        help="Directory for mosaic output",
    )
    parser.add_argument(
        "--no-sliding-window",
        action="store_true",
        help="Disable sliding window (use simple 10 MS groups)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Continuously process groups (daemon mode)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=60.0,
        help="Sleep time between checks in loop mode (seconds)",
    )
    parser.add_argument(
        "--register-bpcal",
        metavar="NAME,RA_DEG,DEC_DEG",
        help="Register a bandpass calibrator (format: NAME,RA_DEG,DEC_DEG)",
    )
    parser.add_argument(
        "--dec-tolerance",
        type=float,
        default=5.0,
        help="Dec tolerance in degrees for calibrator registration (default: 5.0)",
    )

    args = parser.parse_args()

    # Handle calibrator registration
    if args.register_bpcal:
        parts = args.register_bpcal.split(",")
        if len(parts) != 3:
            parser.error("--register-bpcal format: NAME,RA_DEG,DEC_DEG")

        calibrator_name = parts[0].strip()
        try:
            ra_deg = float(parts[1].strip())
            dec_deg = float(parts[2].strip())
        except ValueError:
            parser.error("RA_DEG and DEC_DEG must be numeric")

        manager = StreamingMosaicManager(
            products_db_path=args.products_db,
            registry_db_path=args.registry_db,
            ms_output_dir=args.ms_dir,
            images_dir=args.images_dir,
            mosaic_output_dir=args.mosaic_dir,
        )

        manager.register_bandpass_calibrator(
            calibrator_name=calibrator_name,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            dec_tolerance=args.dec_tolerance,
            registered_by="cli",
        )
        return 0

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Initialize manager
    manager = StreamingMosaicManager(
        products_db_path=args.products_db,
        registry_db_path=args.registry_db,
        ms_output_dir=args.ms_dir,
        mosaic_output_dir=args.mosaic_dir,
    )

    use_sliding_window = not args.no_sliding_window

    if args.loop:
        logger.info(
            "Starting streaming mosaic daemon (sliding window: %s)", use_sliding_window
        )
        while True:
            try:
                processed = manager.process_next_group(
                    use_sliding_window=use_sliding_window
                )
                if not processed:
                    time.sleep(args.sleep)
            except KeyboardInterrupt:
                logger.info("Stopping streaming mosaic daemon")
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                time.sleep(args.sleep)
        return 0
    else:
        # Process single group
        processed = manager.process_next_group(use_sliding_window=use_sliding_window)
        return 0 if processed else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
