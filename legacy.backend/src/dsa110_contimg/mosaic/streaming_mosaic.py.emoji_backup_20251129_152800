#!/opt/miniforge/envs/casa6/bin/python
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
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import astropy.units as u
import numpy as np
from astropy.coordinates import EarthLocation
from astropy.time import Time

from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.calibration.calibration import solve_bandpass, solve_gains
from dsa110_contimg.calibration.model import populate_model_from_catalog
from dsa110_contimg.calibration.selection import select_bandpass_from_catalog
from dsa110_contimg.database.products import (
    ensure_products_db,
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
        ms_per_group: int = MS_PER_GROUP,
        config: Optional[Any] = None,
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
            ms_per_group: Number of MS files required per mosaic group (default: 10)
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
        # Use explicit None check to avoid EarthLocation truthiness ambiguity
        if observatory_location is None:
            self.observatory_location = EarthLocation.of_site("greenwich")
        else:
            self.observatory_location = observatory_location

        # Organized subdirectories within ms_output_dir
        self.ms_calibrators_dir = ms_output_dir / "calibrators"
        self.ms_science_dir = ms_output_dir / "science"
        self.ms_failed_dir = ms_output_dir / "failed"
        self.refant = refant
        self.bp_validity_hours = bp_validity_hours
        self.gain_validity_minutes = gain_validity_minutes
        self.min_calibrator_flux_jy = min_calibrator_flux_jy
        self.min_calibrator_pb_response = min_calibrator_pb_response
        self.ms_per_group = ms_per_group

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

        # Pipeline configuration (optional, for cross-matching and other stages)
        if config is None:
            from dsa110_contimg.pipeline.config import PipelineConfig

            try:
                self.config = PipelineConfig.from_env(validate_paths=False)
                # Enable Phase 3 features
                self.config.transient_detection.enabled = True
                self.config.astrometric_calibration.enabled = True
            except Exception:
                # Create minimal config if env vars not available
                # Only create config if we actually need it (not just for registration)
                try:
                    self.config = PipelineConfig()
                    # Enable Phase 3 features
                    self.config.transient_detection.enabled = True
                    self.config.astrometric_calibration.enabled = True
                except Exception:
                    # If config creation fails, set to None - will be created lazily if needed
                    self.config = None
        else:
            self.config = config

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

        # Note: Bandpass calibrators are now stored in calibrators.sqlite3
        # Use dsa110_contimg.database.calibrators module to access them

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

        Raises:
            ValueError: If calibrator_name is invalid
        """
        # Validate calibrator name
        from dsa110_contimg.database.calibrators import (
            get_bandpass_calibrators,
            register_bandpass_calibrator,
        )
        from dsa110_contimg.utils.naming import validate_calibrator_name

        is_valid, error = validate_calibrator_name(calibrator_name)
        if not is_valid:
            raise ValueError(f"Invalid calibrator name: {error}")

        dec_range_min = dec_deg - dec_tolerance
        dec_range_max = dec_deg + dec_tolerance

        # Deactivate any existing calibrators in this Dec range
        existing = get_bandpass_calibrators(dec_deg=dec_deg, status="active")
        for existing_cal in existing:
            if (
                existing_cal.get("dec_range_min") is not None
                and existing_cal.get("dec_range_max") is not None
            ):
                if (
                    existing_cal["dec_range_min"] <= dec_range_max
                    and existing_cal["dec_range_max"] >= dec_range_min
                ):
                    # Deactivate by re-registering with inactive status
                    register_bandpass_calibrator(
                        calibrator_name=existing_cal["calibrator_name"],
                        ra_deg=existing_cal["ra_deg"],
                        dec_deg=existing_cal["dec_deg"],
                        dec_range_min=existing_cal.get("dec_range_min"),
                        dec_range_max=existing_cal.get("dec_range_max"),
                        source_catalog=existing_cal.get("source_catalog"),
                        flux_jy=existing_cal.get("flux_jy"),
                        registered_by=existing_cal.get("registered_by"),
                        status="inactive",
                        notes=existing_cal.get("notes"),
                    )

        # Register new calibrator
        register_bandpass_calibrator(
            calibrator_name=calibrator_name,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            dec_range_min=dec_range_min,
            dec_range_max=dec_range_max,
            registered_by=registered_by,
            status="active",
            notes=notes,
        )

        logger.info(
            f"Registered bandpass calibrator {calibrator_name} "
            f"(RA={ra_deg:.6f}, Dec={dec_deg:.6f}) "
            f"for Dec range [{dec_range_min:.2f}, {dec_range_max:.2f}]"
        )

        # Pre-calculate transit times for this calibrator
        try:
            from dsa110_contimg.conversion.transit_precalc import (
                precalculate_transits_for_calibrator,
            )

            logger.info(f"Pre-calculating transit times for {calibrator_name}...")
            transits_with_data = precalculate_transits_for_calibrator(
                products_db=self.products_db,
                calibrator_name=calibrator_name,
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                max_days_back=60,
            )
            logger.info(
                f"✓ Pre-calculated transit times: {transits_with_data} transits have available data"
            )
        except Exception as e:
            logger.warning(
                f"Failed to pre-calculate transit times for {calibrator_name}: {e}. "
                f"Transit times will be calculated on-demand."
            )

    def get_bandpass_calibrator_for_dec(self, dec_deg: float) -> Optional[Dict]:
        """Get active bandpass calibrator for a given Dec.

        Args:
            dec_deg: Declination in degrees

        Returns:
            Dictionary with calibrator info, or None if not found
        """
        from dsa110_contimg.database.calibrators import get_bandpass_calibrators

        calibrators = get_bandpass_calibrators(dec_deg=dec_deg, status="active")

        if not calibrators:
            return None

        # Sort by registered_at (most recent first) and return first match
        calibrators.sort(key=lambda x: x.get("registered_at", 0), reverse=True)
        cal = calibrators[0]

        return {
            "name": cal["calibrator_name"],
            "ra_deg": cal["ra_deg"],
            "dec_deg": cal["dec_deg"],
            "dec_range_min": cal.get("dec_range_min"),
            "dec_range_max": cal.get("dec_range_max"),
            "registered_at": cal.get("registered_at"),
            "notes": cal.get("notes"),
        }

    def check_for_new_group(self) -> Optional[str]:
        """Check if a new group of 10 MS files is ready for processing.

        Returns:
            Group ID if ready, None otherwise
        """
        # Query for MS files that are ready for mosaic creation
        # CRITICAL: Only select MS files that have been imaged (not just converted)
        # This ensures images exist before group formation
        rows = self.products_db.execute(
            """
            SELECT path, mid_mjd
            FROM ms_index
            WHERE stage IN ('imaged', 'done') AND status IN ('imaged', 'done', 'converted')
            ORDER BY mid_mjd ASC
            LIMIT ?
            """,
            (self.ms_per_group,),
        ).fetchall()

        if len(rows) < self.ms_per_group:
            return None

        # CRITICAL: Verify files exist on filesystem before forming group
        # Filter out paths that don't exist
        valid_rows = []
        for row in rows:
            ms_path = row[0]
            if Path(ms_path).exists():
                valid_rows.append(row)
            else:
                logger.warning(
                    f"MS file from database does not exist on filesystem: {ms_path}. "
                    f"Skipping this file."
                )

        if len(valid_rows) < self.ms_per_group:
            logger.debug(f"Only {len(valid_rows)}/{self.ms_per_group} MS files exist on filesystem")
            return None

        # CRITICAL: Keep paths in chronological order (by mid_mjd), not alphabetical
        # Store as (mid_mjd, path) tuples to preserve chronological order
        ms_paths_with_time = [(row[1], row[0]) for row in valid_rows]
        # Sort by mid_mjd to ensure chronological order (should already be sorted, but enforce it)
        ms_paths_with_time.sort(key=lambda x: x[0])

        # CRITICAL: Validate that MS files are sequential 5-minute observation chunks at the same declination
        # Each MS file represents a 5-minute observation, so consecutive files must be ~5 minutes apart
        # and all files must be at the same declination (within tolerance)
        if not self._validate_sequential_5min_chunks(ms_paths_with_time):
            logger.debug(
                "MS files are not sequential 5-minute chunks at the same declination. "
                "Need exactly 10 neighboring 5-minute observations at the same Dec. Skipping group formation."
            )
            return None

        # CRITICAL: Validate total time span is reasonable for mosaic
        # 10 files × 5 minutes = 50 minutes ideal, allow up to 60 minutes total span
        if not self._validate_total_time_span(ms_paths_with_time):
            logger.debug(
                "Total time span too large for coherent mosaic. "
                "Need contiguous observations within 60 minutes. Skipping group formation."
            )
            return None

        ms_paths = [path for _, path in ms_paths_with_time]
        # Store paths in chronological order (comma-separated)
        ms_paths_str = ",".join(ms_paths)

        existing = self.products_db.execute(
            "SELECT group_id FROM mosaic_groups WHERE ms_paths = ? AND status != 'completed'",
            (ms_paths_str,),
        ).fetchone()

        if existing:
            return existing[0]

        # Create new group with collision-resistant ID
        # Use hash of MS paths + timestamp to prevent collisions and ensure uniqueness
        import hashlib

        ms_paths_hash = hashlib.sha256(ms_paths_str.encode()).hexdigest()[:12]
        # Include microseconds for collision prevention
        timestamp = int(time.time() * 1000000)
        group_id = f"group_{ms_paths_hash}_{timestamp}"

        # CRITICAL: Check for duplicate group_id (shouldn't happen, but safeguard)
        existing_id = self.products_db.execute(
            "SELECT group_id FROM mosaic_groups WHERE group_id = ?",
            (group_id,),
        ).fetchone()

        if existing_id:
            # Collision detected - add random suffix
            import random

            suffix = random.randint(1000, 9999)
            group_id = f"group_{ms_paths_hash}_{timestamp}_{suffix}"
            logger.warning(f"Group ID collision detected, using alternative ID: {group_id}")

        self.products_db.execute(
            """
            INSERT INTO mosaic_groups (group_id, ms_paths, created_at, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (group_id, ms_paths_str, time.time()),
        )
        self.products_db.commit()

        logger.info(
            f"Created new mosaic group: {group_id} with {len(ms_paths)} MS files "
            f"(sequential 5-minute chunks, chronological order)"
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
        # CRITICAL: Verify files exist before attempting time extraction
        ms_paths_with_time = []
        for ms_path in ms_paths:
            ms_path_obj = Path(ms_path)
            if not ms_path_obj.exists():
                logger.error(
                    f"MS file from database does not exist on filesystem: {ms_path}. "
                    f"Skipping this path."
                )
                continue  # Skip non-existent files

            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
                if mid_mjd is not None:
                    ms_paths_with_time.append((mid_mjd, ms_path))
                else:
                    # If time extraction fails, log warning but include path
                    logger.warning(f"Could not extract time from {ms_path}, using path order")
                    ms_paths_with_time.append((float("inf"), ms_path))  # Put at end
            except Exception as e:
                logger.warning(f"Error extracting time from {ms_path}: {e}")
                ms_paths_with_time.append((float("inf"), ms_path))  # Put at end

        # Sort by mid_mjd (chronological order)
        ms_paths_with_time.sort(key=lambda x: x[0])

        # Return paths in chronological order
        return [path for _, path in ms_paths_with_time]

    def _validate_sequential_5min_chunks(self, ms_paths_with_time: List[Tuple[float, str]]) -> bool:
        """Validate that MS files are sequential 5-minute observation chunks at the same declination.

        Each MS file represents a 5-minute observation. This function ensures that:
        1. Consecutive MS files are less than 6 minutes apart
        2. All MS files are at the same declination (within tolerance for field tracking)

        Args:
            ms_paths_with_time: List of (mid_mjd, path) tuples in chronological order

        Returns:
            True if all consecutive MS files are ~5 minutes apart and at same Dec, False otherwise
        """
        if len(ms_paths_with_time) < 2:
            # Need at least 2 files to check spacing
            return len(ms_paths_with_time) == self.ms_per_group

        # Maximum time difference: 6 minutes = 6/60/24 days = 0.004166667... days
        # Consecutive MS files must be less than 6 minutes apart
        max_diff_days = 6.0 / 60.0 / 24.0  # 6 minutes in days

        # Extract declinations from all MS files
        dec_degrees = []
        for mid_mjd, ms_path in ms_paths_with_time:
            try:
                import casacore.tables as casatables

                table = casatables.table  # noqa: N816

                t = table(ms_path)
                field_table = t.getkeyword("FIELD")
                # Get mean declination across all fields in the MS (in radians)
                dec_rad = np.mean([f["REFERENCE_DIR"][0][1] for f in field_table])
                dec_deg = dec_rad * 180.0 / np.pi
                dec_degrees.append(dec_deg)
                t.close()
            except Exception as e:
                logger.debug(f"Failed to extract declination from {Path(ms_path).name}: {e}")
                return False

        if len(dec_degrees) != len(ms_paths_with_time):
            logger.debug(
                f"Could not extract declination from all MS files. "
                f"Extracted {len(dec_degrees)}/{len(ms_paths_with_time)} declinations."
            )
            return False

        # Check that all declinations are the same (within tolerance)
        # Tolerance: ±0.1 degrees (~6 arcminutes) to account for field tracking variations
        dec_tolerance_deg = 0.1
        mean_dec = np.mean(dec_degrees)
        for i, (mid_mjd, ms_path) in enumerate(ms_paths_with_time):
            dec_diff = abs(dec_degrees[i] - mean_dec)
            if dec_diff > dec_tolerance_deg:
                logger.debug(
                    f"MS files are not at the same declination: "
                    f"{Path(ms_path).name} has Dec={dec_degrees[i]:.6f}°, "
                    f"mean Dec={mean_dec:.6f}° (difference: {dec_diff:.6f}°, "
                    f"tolerance: ±{dec_tolerance_deg:.6f}°)"
                )
                return False

        # Check spacing between consecutive MS files
        for i in range(len(ms_paths_with_time) - 1):
            mid_mjd_1 = ms_paths_with_time[i][0]
            mid_mjd_2 = ms_paths_with_time[i + 1][0]
            path_1 = ms_paths_with_time[i][1]
            path_2 = ms_paths_with_time[i + 1][1]

            # Skip if either time is invalid (inf indicates extraction failure)
            if not (
                mid_mjd_1 is not None
                and mid_mjd_2 is not None
                and mid_mjd_1 != float("inf")
                and mid_mjd_2 != float("inf")
            ):
                logger.debug(
                    f"Invalid time extracted from MS files, cannot validate spacing: "
                    f"{Path(path_1).name} or {Path(path_2).name}"
                )
                return False

            diff_days = mid_mjd_2 - mid_mjd_1

            if diff_days > max_diff_days:
                # Calculate actual time difference in minutes for logging
                diff_minutes = diff_days * 24.0 * 60.0
                logger.debug(
                    f"MS files are not sequential 5-minute chunks: "
                    f"{Path(path_1).name} → {Path(path_2).name} "
                    f"(gap: {diff_minutes:.2f} minutes, must be < 6.00 minutes)"
                )
                return False

        # All consecutive pairs are valid 5-minute chunks at the same declination
        logger.debug(
            f"Validated {len(ms_paths_with_time)} MS files: "
            f"sequential 5-minute chunks at Dec={mean_dec:.6f}° "
            f"(all within ±{dec_tolerance_deg:.6f}° tolerance)"
        )
        return True

    def _validate_total_time_span(self, ms_paths_with_time: List[Tuple[float, str]]) -> bool:
        """Validate total time span is reasonable for mosaic creation.

        For 10 sequential 5-minute observations, total span should be:
        - Ideal: 50 minutes (10 × 5 minutes)
        - Maximum: 60 minutes (allowing for small gaps)

        Args:
            ms_paths_with_time: List of (mid_mjd, path) tuples in chronological order

        Returns:
            True if total time span is within limits, False otherwise
        """
        if len(ms_paths_with_time) < 2:
            return True

        first_time = ms_paths_with_time[0][0]
        last_time = ms_paths_with_time[-1][0]

        # Skip if times are invalid
        if (
            first_time == float("inf")
            or last_time == float("inf")
            or first_time is None
            or last_time is None
        ):
            return False

        total_span_days = last_time - first_time
        total_span_minutes = total_span_days * 24.0 * 60.0

        # Maximum span: 60 minutes (10 files × 5 minutes + 10 minutes tolerance)
        max_span_minutes = 60.0

        if total_span_minutes > max_span_minutes:
            logger.debug(
                f"Total time span too large for mosaic: {total_span_minutes:.2f} minutes "
                f"(max: {max_span_minutes:.2f} minutes). "
                f"First: {Path(ms_paths_with_time[0][1]).name}, "
                f"Last: {Path(ms_paths_with_time[-1][1]).name}"
            )
            return False

        return True

    def select_calibration_ms(
        self,
        ms_paths: List[str],
        min_required: Optional[int] = None,
        calibrator_ra: Optional[float] = None,
    ) -> Optional[str]:
        """Select calibration MS, preferring one that contains peak transit.

        Args:
            ms_paths: List of MS file paths
            min_required: Minimum required MS count (defaults to self.ms_per_group for streaming mode)
            calibrator_ra: Optional calibrator RA in degrees for transit-based selection

        Returns:
            Path to calibration MS, or None if unable to determine
        """
        # Get time ranges for each MS
        ms_times = []
        for ms_path in ms_paths:
            try:
                start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
                if mid_mjd is not None and start_mjd is not None and end_mjd is not None:
                    ms_times.append((start_mjd, end_mjd, mid_mjd, ms_path))
            except Exception as e:
                logger.warning(f"Failed to extract time from {ms_path}: {e}")
                continue

        # Use provided min_required for manual mode, otherwise use self.ms_per_group
        required_count = min_required if min_required is not None else self.ms_per_group

        if len(ms_times) < required_count:
            logger.warning(f"Only {len(ms_times)} MS files have valid times, need {required_count}")
            return None

        # Sort by time
        ms_times.sort(key=lambda x: x[2])  # Sort by mid_mjd

        # If calibrator RA is provided, try to find MS that contains peak transit
        if calibrator_ra is not None:
            # Calculate transit time for middle MS
            mid_time = Time(ms_times[len(ms_times) // 2][2], format="mjd")
            transit_mjd = self.calculate_calibrator_transit(calibrator_ra, mid_time)

            # Find MS that contains transit time
            for start_mjd, end_mjd, mid_mjd, ms_path in ms_times:
                if start_mjd <= transit_mjd <= end_mjd:
                    transit_offset_hours = abs(transit_mjd - mid_mjd) * 24.0
                    logger.info(
                        f"Selected calibration MS containing peak transit: {ms_path} "
                        f"(transit at {transit_mjd:.6f} MJD, offset: {transit_offset_hours:.2f} hours)"
                    )
                    return ms_path

            # If no MS contains transit, warn and fall back to default selection
            logger.warning(
                f"No MS found containing peak transit ({transit_mjd:.6f} MJD). "
                f"Falling back to default selection (5th MS)."
            )

        # Default: select 5th MS (middle by time) for streaming mode
        # For manual mode (<10 MS): select middle MS
        if len(ms_times) >= 5:
            # Standard case: select 5th MS (index 4)
            calib_index = CALIBRATION_MS_INDEX
        else:
            # Manual mode with fewer MS: select middle MS
            calib_index = len(ms_times) // 2

        calibration_ms = ms_times[calib_index][3]

        logger.info(
            f"Selected calibration MS: {calibration_ms} ({calib_index + 1} of {len(ms_times)} MS)"
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

    def calculate_calibrator_transit(self, calibrator_ra: float, observation_date: Time) -> float:
        """Calculate calibrator transit time (MJD).

        Args:
            calibrator_ra: Calibrator RA in degrees
            observation_date: Observation date/time

        Returns:
            Transit MJD
        """
        # Calculate local sidereal time at observation
        # Transit occurs when LST = RA
        lst = observation_date.sidereal_time("mean", longitude=self.observatory_location.lon)

        # Calculate time difference to transit
        # RA and LST are both in degrees (RA is already in degrees, LST converted to degrees)
        ra_angle = calibrator_ra * u.deg  # pylint: disable=no-member
        lst_angle = lst.to(u.deg)  # pylint: disable=no-member
        hour_angle_deg = ra_angle - lst_angle

        # Normalize to [-180, 180] degrees (equivalent to [-12, 12] hours)
        hour_angle_deg = hour_angle_deg.wrap_at(180 * u.deg)  # pylint: disable=no-member

        # Convert hour angle from degrees to days
        # 1 hour = 15 degrees, 1 day = 24 hours
        # So: degrees / 15 degrees/hour / 24 hours/day = degrees / 360 degrees/day
        hour_angle_days = hour_angle_deg.to_value(u.deg) / 360.0  # pylint: disable=no-member

        # Transit time
        transit_time = observation_date + hour_angle_days * u.day  # pylint: disable=no-member

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
        organized_ms_path = self._get_organized_ms_path(ms_path, is_calibrator, date_str)
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
            logger.warning(f"Failed to organize MS file {ms_path}: {e}. Using original path.")
            return ms_path

    def _get_ms_declination(self, ms_path: str) -> Optional[float]:
        """Look up declination for an MS path from ms_index."""
        try:
            row = self.products_db.execute(
                "SELECT dec_deg FROM ms_index WHERE path = ?",
                (str(ms_path),),
            ).fetchone()
            if row and row[0] is not None:
                return float(row[0])
        except Exception as exc:
            logger.debug(f"Failed to fetch declination for {ms_path}: {exc}")
        return None

    def _model_data_is_populated(self, ms_path: str) -> bool:
        """Return True if MODEL_DATA exists and contains non-zero entries."""
        try:
            import casacore.tables as casatables  # type: ignore[import]
        except Exception as exc:  # pragma: no cover - CASA import guard
            logger.debug(f"casacore.tables unavailable while checking MODEL_DATA: {exc}")
            return False

        try:
            with casatables.table(ms_path, readonly=True) as tb:  # type: ignore[attr-defined]
                if "MODEL_DATA" not in tb.colnames():
                    return False
                nrows = tb.nrows()
                if nrows == 0:
                    return False
                sample_rows = min(4, nrows)
                model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=sample_rows)
                if np.any(np.abs(model_sample) > 1e-9):
                    return True
        except Exception as exc:
            logger.debug(f"Error inspecting MODEL_DATA for {ms_path}: {exc}")
        return False

    def _populate_science_model(self, ms_path: str) -> bool:
        """Populate MODEL_DATA for a science MS using the nearest bandpass calibrator."""
        try:
            dec_deg = self._get_ms_declination(ms_path)
            if dec_deg is None:
                logger.warning(f"Declination unknown for {ms_path}; cannot seed MODEL_DATA")
                return False

            bp_cal = self.get_bandpass_calibrator_for_dec(dec_deg)
            if not bp_cal:
                logger.warning(
                    f"No bandpass calibrator registered for Dec={dec_deg:.3f}°. "
                    f"Cannot seed MODEL_DATA for {ms_path}"
                )
                return False

            populate_model_from_catalog(
                ms_path,
                field="0~63",  # cover all fields in the MS (meridian-tracking)
                calibrator_name=bp_cal["name"],
                cal_ra_deg=bp_cal["ra_deg"],
                cal_dec_deg=bp_cal["dec_deg"],
                cal_flux_jy=bp_cal.get("flux_jy", 2.5),
            )
            logger.info(f"MODEL_DATA populated for science MS {ms_path}")
            return True
        except Exception as exc:
            logger.error(f"Failed to populate MODEL_DATA for {ms_path}: {exc}")
            return False

    def _ensure_model_ready_for_imaging(self, ms_path: str) -> bool:
        """Ensure MODEL_DATA exists and is populated before imaging."""
        if self._model_data_is_populated(ms_path):
            return True

        logger.info(f"MODEL_DATA missing for {ms_path}; repopulating before imaging")
        if not self._populate_science_model(ms_path):
            return False
        return self._model_data_is_populated(ms_path)

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
                        logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
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
                        keyword.lower() in str(error_msg).lower() for keyword in transient_keywords
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
                    keyword.lower() in last_error.lower() for keyword in transient_keywords
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
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(calibration_ms_path)
            if mid_mjd is None:
                error_msg = f"Could not extract time from calibration MS: {calibration_ms_path}"
                logger.error(error_msg)
                return False, False, error_msg
            if start_mjd is None or end_mjd is None:
                error_msg = (
                    f"Could not extract full time range from calibration MS: {calibration_ms_path}"
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
        has_g = len(registry_tables.get("GP", [])) > 0 and len(registry_tables.get("2G", [])) > 0

        # CRITICAL: Verify tables exist on disk, not just in registry
        if has_bp:
            bp_table_path = registry_tables.get("BP", [])[0]
            if not Path(bp_table_path).exists():
                logger.warning(f"BP table in registry does not exist on disk: {bp_table_path}")
                has_bp = False

        if has_g:
            gp_table_path = registry_tables.get("GP", [])[0]
            g2_table_path = registry_tables.get("2G", [])[0]
            if not Path(gp_table_path).exists() or not Path(g2_table_path).exists():
                logger.warning("Gain tables in registry do not exist on disk")
                has_g = False

        bpcal_solved = False
        gaincal_solved = False

        # Solve bandpass if not in registry or tables missing
        if not has_bp:
            # Get observation Dec from calibration MS
            # Ensure CASAPATH is set before importing CASA modules
            from dsa110_contimg.utils.casa_init import ensure_casa_path

            ensure_casa_path()

            try:
                import casacore.tables as casatables

                table = casatables.table  # noqa: N816
                import numpy as np

                # Read declination from FIELD table
                with table(f"{calibration_ms_path}::FIELD", readonly=True) as field_tb:
                    if "REFERENCE_DIR" in field_tb.colnames():
                        ref_dir = field_tb.getcol("REFERENCE_DIR")
                        # Shape: (nfields, 1, 2) or (nfields, 2)
                        # Extract Dec from first field
                        dec_rad = ref_dir[0][0][1] if ref_dir.ndim == 3 else ref_dir[0][1]
                        dec_deg = float(np.degrees(dec_rad))
                    elif "PHASE_DIR" in field_tb.colnames():
                        phase_dir = field_tb.getcol("PHASE_DIR")
                        dec_rad = phase_dir[0][0][1] if phase_dir.ndim == 3 else phase_dir[0][1]
                        dec_deg = float(np.degrees(dec_rad))
                    else:
                        raise ValueError("No REFERENCE_DIR or PHASE_DIR column in FIELD table")

                # CRITICAL: Extract all field positions (RA/Dec) from MS
                # Each of the 24 fields is phased to a slightly different meridian,
                # so we need to account for field-specific RAs when calculating transit
                from dsa110_contimg.utils.ms_helpers import get_fields_cached

                try:
                    fields = get_fields_cached(calibration_ms_path)
                    if not fields:
                        error_msg = f"Could not extract field positions from {calibration_ms_path}"
                        logger.error(error_msg)
                        return False, False, error_msg

                    # Extract RA and Dec for all fields
                    field_ras = [ra for _, ra, _ in fields]
                    field_decs = [dec for _, _, dec in fields]

                    # Use mean Dec for calibrator lookup (fields track together in Dec)
                    dec_deg = float(np.mean(field_decs))
                    logger.debug(
                        f"Extracted {len(fields)} fields from MS. "
                        f"RA range: {min(field_ras):.6f}° - {max(field_ras):.6f}°, "
                        f"Mean Dec: {dec_deg:.6f}°"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not extract all field positions, using first field only: {e}"
                    )
                    # Fallback to first field only
                    if "REFERENCE_DIR" in field_tb.colnames():
                        ref_dir = field_tb.getcol("REFERENCE_DIR")
                        ra_rad = ref_dir[0][0][0] if ref_dir.ndim == 3 else ref_dir[0][0]
                        dec_rad = ref_dir[0][0][1] if ref_dir.ndim == 3 else ref_dir[0][1]
                    elif "PHASE_DIR" in field_tb.colnames():
                        phase_dir = field_tb.getcol("PHASE_DIR")
                        ra_rad = phase_dir[0][0][0] if phase_dir.ndim == 3 else phase_dir[0][0]
                        dec_rad = phase_dir[0][0][1] if phase_dir.ndim == 3 else phase_dir[0][1]
                    else:
                        raise ValueError("No REFERENCE_DIR or PHASE_DIR column in FIELD table")

                    dec_deg = float(np.degrees(dec_rad))
                    field_ras = [float(np.degrees(ra_rad))]
                    field_decs = [dec_deg]

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

                # CRITICAL: Calculate transit time using calibrator's RA
                # Each field is phased to a different meridian (different RA),
                # but the calibrator has a fixed RA, so we calculate when it transits
                # Then we verify that at least one field's meridian is close to the calibrator's RA
                calibrator_ra = bp_cal["ra_deg"]
                transit_mjd = self.calculate_calibrator_transit(
                    calibrator_ra, Time(mid_mjd, format="mjd")
                )

                # Find which field's meridian is closest to the calibrator's RA
                # This tells us which field will have the best SNR for calibration
                best_field_idx = None
                min_ra_separation = float("inf")

                for field_idx, field_ra in enumerate(field_ras):
                    # Calculate angular separation between field meridian and calibrator RA
                    # Account for RA wrap-around (e.g., 359° and 1° are close)
                    ra_diff = abs(field_ra - calibrator_ra)
                    ra_separation = min(ra_diff, 360.0 - ra_diff)  # Handle wrap-around

                    if ra_separation < min_ra_separation:
                        min_ra_separation = ra_separation
                        best_field_idx = field_idx

                # Validate transit time is within MS time range
                transit_within_range = start_mjd <= transit_mjd <= end_mjd
                transit_offset_hours = abs(transit_mjd - mid_mjd) * 24.0

                # Warn if no field is close to calibrator RA (calibrator may not be visible)
                if min_ra_separation > 5.0:  # More than 5 degrees separation
                    logger.warning(
                        f"Calibrator RA ({calibrator_ra:.6f}°) is {min_ra_separation:.2f}° "
                        f"from nearest field meridian (field {best_field_idx}, RA={field_ras[best_field_idx]:.6f}°). "
                        f"Calibrator may have low visibility in this MS."
                    )
                else:
                    logger.info(
                        f"Field {best_field_idx} (RA={field_ras[best_field_idx]:.6f}°) is closest to "
                        f"calibrator RA ({calibrator_ra:.6f}°), separation: {min_ra_separation:.2f}°"
                    )

                if not transit_within_range:
                    error_msg = (
                        f"CRITICAL: Calculated transit time for calibrator {bp_cal['name']} "
                        f"({transit_mjd:.6f} MJD, RA={calibrator_ra:.6f}°) "
                        f"is NOT within calibration MS time range ({start_mjd:.6f} - {end_mjd:.6f} MJD). "
                        f"Offset: {transit_offset_hours:.2f} hours. "
                        f"Closest field: {best_field_idx} (RA={field_ras[best_field_idx]:.6f}°, "
                        f"separation: {min_ra_separation:.2f}°). "
                        f"This indicates the MS is misassociated with the calibrator transit. "
                        f"Bandpass solve will fail with low SNR."
                    )
                    logger.error(error_msg)
                    return False, False, error_msg

                # Warn if transit is far from MS center (more than 1 hour)
                if transit_offset_hours > 1.0:
                    logger.warning(
                        f"Transit time for calibrator {bp_cal['name']} ({transit_mjd:.6f} MJD, "
                        f"RA={calibrator_ra:.6f}°) is {transit_offset_hours:.2f} hours "
                        f"from MS center ({mid_mjd:.6f} MJD). "
                        f"Closest field: {best_field_idx} (RA={field_ras[best_field_idx]:.6f}°). "
                        f"Calibrator may not be at peak transit in this MS."
                    )
                else:
                    logger.info(
                        f"✓ Transit time for calibrator {bp_cal['name']} ({transit_mjd:.6f} MJD, "
                        f"RA={calibrator_ra:.6f}°) validated within MS time range. "
                        f"Offset from MS center: {transit_offset_hours:.2f} hours. "
                        f"Closest field: {best_field_idx} (RA={field_ras[best_field_idx]:.6f}°, "
                        f"separation: {min_ra_separation:.2f}°)"
                    )

                # Check if calibrator is present in any MS in the group
                ms_paths = self.get_group_ms_paths(group_id)
                calibrator_ms = None
                cal_field_sel = None

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
                                pb_response = peak_pb_flux / cal_flux_jy if cal_flux_jy > 0 else 0.0

                                if pb_response < self.min_calibrator_pb_response:
                                    logger.warning(
                                        f"Calibrator {cal_name} PB response ({pb_response:.3f}) "
                                        f"below minimum threshold ({self.min_calibrator_pb_response:.3f}) "
                                        f"in {ms_path}. Skipping."
                                    )
                                    continue

                            calibrator_ms = str(ms_path)
                            cal_field_sel = field_sel_str
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
                                pb_response = peak_pb_flux / cal_flux_jy if cal_flux_jy > 0 else 0.0

                                if pb_response < self.min_calibrator_pb_response:
                                    logger.warning(
                                        f"Calibrator {cal_name} PB response ({pb_response:.3f}) "
                                        f"below minimum threshold ({self.min_calibrator_pb_response:.3f}) "
                                        f"in calibration MS. Skipping."
                                    )
                                else:
                                    calibrator_ms = str(calibration_ms_path)
                                    cal_field_sel = field_sel_str
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
                    except Exception as e:
                        logger.debug(f"Could not find calibrator in calibration MS: {e}")

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

                        # CRITICAL: Rephase MS to calibrator position
                        # BEFORE populating MODEL_DATA and calibration
                        # This makes all 24 fields coherently phased to
                        # the calibrator, enabling proper calibration
                        logger.info(
                            f"Rephasing MS to calibrator position: "
                            f"{bp_cal['name']} @ ({bp_cal['ra_deg']:.6f}°, "
                            f"{bp_cal['dec_deg']:.6f}°)"
                        )
                        try:
                            from dsa110_contimg.calibration.cli_utils import (
                                rephase_ms_to_calibrator,
                            )

                            rephase_success = rephase_ms_to_calibrator(
                                calibrator_ms,
                                bp_cal["ra_deg"],
                                bp_cal["dec_deg"],
                                bp_cal["name"],
                                logger,
                            )
                            if not rephase_success:
                                error_msg = (
                                    f"Failed to rephase MS to calibrator "
                                    f"position for {bp_cal['name']}"
                                )
                                logger.error(error_msg)
                                return False, False, error_msg
                            logger.info(f"Successfully rephased MS to " f"{bp_cal['name']}")
                        except Exception as e:
                            error_msg = f"Exception during MS rephasing: {e}"
                            logger.error(error_msg, exc_info=True)
                            return False, False, error_msg

                        # Populate MODEL_DATA before solving bandpass
                        # calibration (REQUIRED PRECONDITION)
                        # solve_bandpass() requires MODEL_DATA beforehand
                        # We use calibrator info from
                        # select_bandpass_from_catalog()
                        logger.info(
                            f"Populating MODEL_DATA for bandpass "
                            f"calibration using {bp_cal['name']}..."
                        )
                        try:
                            populate_model_from_catalog(
                                calibrator_ms,
                                field=cal_field_sel,
                                calibrator_name=bp_cal["name"],
                                cal_ra_deg=bp_cal["ra_deg"],
                                cal_dec_deg=bp_cal["dec_deg"],
                                cal_flux_jy=2.5,  # Default flux
                            )
                            logger.info(
                                f"MODEL_DATA successfully populated for "
                                f"{bp_cal['name']} at fields "
                                f"{cal_field_sel}"
                            )
                        except Exception as e:
                            error_msg = (
                                f"Failed to populate MODEL_DATA for " f"bandpass calibration: {e}"
                            )
                            logger.error(error_msg)
                            return False, False, error_msg

                        # Solve bandpass calibration with retry logic
                        # for transient errors
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
                                    model_standard=self.calibration_params["model_standard"],
                                    combine_fields=self.calibration_params["combine_fields"],
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
                            logger.info(f"Bandpass calibration solved successfully: {bp_tables}")

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
                                ms_stem = Path(calibration_ms_path).stem
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
                                bpcal_solved = True  # Only set True after successful registration
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
                                logger.debug(f"Organized calibration MS to: {organized_cal_ms}")
                            except Exception as e:
                                logger.error(
                                    f"Failed to register bandpass calibration tables: {e}. "
                                    f"Calibration tables exist but are not registered. "
                                    f"Marking BP calibration as failed."
                                )
                                bpcal_solved = False  # Ensure consistent state
                        else:
                            logger.error("Bandpass calibration solving returned no tables")
                            bpcal_solved = False
                    except Exception as e:
                        logger.error(f"Failed to solve bandpass calibration: {e}", exc_info=True)
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
            # Tables exist and are verified on disk, mark as solved
            bpcal_solved = True

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
                    bp_table_path = Path(table_prefix).parent / f"{table_prefix.name}_bpcal"
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
                        raise ValueError("No calibrator found in MS for gain calibration")
                except Exception as e:
                    error_msg = f"Failed to select calibrator field for gain calibration: {e}"
                    logger.error(error_msg)
                    return bpcal_solved, False, error_msg

                # Populate MODEL_DATA before solving gains
                try:
                    populate_model_from_catalog(
                        calibration_ms_path,
                        field=field_sel_str,
                    )
                    logger.debug("MODEL_DATA populated for gain calibration")
                except Exception as e:
                    logger.warning(f"Failed to populate MODEL_DATA: {e}. Proceeding anyway.")

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

                # Handle both tuple (success, tables) and list (tables) return formats
                # This supports both the actual API (returns List[str]) and test mocks
                # that may return (bool, List[str]) tuples
                if isinstance(gain_tables, tuple) and len(gain_tables) == 2:
                    # Tuple format: (success: bool, tables: List[str])
                    success, tables = gain_tables
                    if not success or not tables or len(tables) == 0:
                        logger.error("Gain calibration solving returned failure or no tables")
                        gaincal_solved = False
                        gain_tables = []  # Set to empty list to skip processing
                    else:
                        gain_tables = tables  # Use the tables list for processing
                        # gaincal_solved remains False until registration succeeds
                elif not gain_tables or len(gain_tables) == 0:
                    # Empty list or None indicates failure
                    logger.error("Gain calibration solving returned no tables")
                    gaincal_solved = False

                # Process gain tables if we have them (only if not already marked as failed)
                if not gaincal_solved and gain_tables and len(gain_tables) > 0:
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
                            ms_stem = Path(calibration_ms_path).stem
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
                            gaincal_solved = True  # Only set True after successful registration
                            logger.info(
                                f"Registered gain calibration with validity window: "
                                f"{valid_start_mjd:.6f} - {valid_end_mjd:.6f} MJD"
                            )

                            # Organize calibration MS file to calibrators directory (if not already organized)
                            organized_cal_ms = self._organize_ms_file(
                                cal_ms_path, is_calibrator=True, date_str=date_str
                            )
                            logger.debug(f"Organized calibration MS to: {organized_cal_ms}")
                        except Exception as e:
                            logger.error(
                                f"Failed to register gain calibration tables: {e}. "
                                f"Calibration tables exist but are not registered. "
                                f"Marking gain calibration as failed."
                            )
                            gaincal_solved = False  # Ensure consistent state
                    else:
                        logger.error("Could not extract time from calibration MS for registration")
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
            # Tables exist and are verified on disk, mark as solved
            gaincal_solved = True

        # Update group status
        self.products_db.execute(
            """
            UPDATE mosaic_groups
            SET calibration_ms_path = ?, bpcal_solved = ?, gaincal_solved = ?
            WHERE group_id = ?
            """,
            (
                calibration_ms_path,
                1 if bpcal_solved else 0,
                1 if gaincal_solved else 0,
                group_id,
            ),
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

        # Check if calibration already applied (check database state)
        row = self.products_db.execute(
            """
            SELECT status, stage, cal_applied FROM mosaic_groups 
            WHERE group_id = ?
            """,
            (group_id,),
        ).fetchone()

        if row and row[1] == "calibrated" and row[2] == 1:
            logger.info(f"Calibration already applied to group {group_id}, skipping")
            return True

        success_count = 0
        updated_paths: List[str] = []
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
                    logger.warning(f"No valid calibration tables found in registry for {ms_path}")
                    continue

                # CRITICAL: Validate all calibration tables exist on filesystem before applying
                missing_tables = []
                for table_path in applylist:
                    table_path_obj = Path(table_path)
                    if not table_path_obj.exists():
                        missing_tables.append(table_path)
                    elif table_path_obj.is_dir():
                        # CASA tables are directories - check for required files
                        if not (table_path_obj / "table.dat").exists():
                            missing_tables.append(table_path)

                if missing_tables:
                    logger.error(
                        f"CRITICAL: Calibration tables not found on filesystem for {ms_path}: "
                        f"{missing_tables}. Cannot apply calibration."
                    )
                    continue

                # Apply calibration
                apply_to_target(str(ms_path_obj), field="", gaintables=applylist, calwt=True)

                # Organize MS file to science directory after calibration
                # Extract date from filename
                ms_name = ms_path_obj.stem
                import re

                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", ms_name)
                date_str = date_match.group(1) if date_match else None

                organized_path = self._organize_ms_file(
                    ms_path_obj, is_calibrator=False, date_str=date_str
                )
                organized_str = str(organized_path)

                # Update products database with organized path
                ms_index_upsert(
                    self.products_db,
                    organized_str,
                    stage="calibrated",
                    cal_applied=1,
                )

                # Populate MODEL_DATA so imaging has a starting model
                if not self._populate_science_model(organized_str):
                    logger.warning(
                        f"MODEL_DATA seeding failed for {organized_str}; "
                        "imaging will retry before running."
                    )

                updated_paths.append(organized_str)
                success_count += 1
                logger.info(f"Applied calibration to {ms_path} (organized to {organized_path})")

            except Exception as e:
                logger.error(f"Failed to apply calibration to {ms_path}: {e}", exc_info=True)

        self.products_db.commit()

        if updated_paths and len(updated_paths) == len(ms_paths):
            try:
                self.products_db.execute(
                    "UPDATE mosaic_groups SET ms_paths = ? WHERE group_id = ?",
                    (",".join(updated_paths), group_id),
                )
                self.products_db.commit()
            except Exception as exc:
                logger.warning(f"Failed to record organized MS paths for group {group_id}: {exc}")

        if success_count == len(ms_paths):
            self.products_db.execute(
                """
                UPDATE mosaic_groups
                SET calibrated_at = ?, status = 'calibrated', stage = 'calibrated', cal_applied = 1
                WHERE group_id = ?
                """,
                (time.time(), group_id),
            )
            self.products_db.commit()
            return True
        else:
            logger.warning(f"Only {success_count}/{len(ms_paths)} MS files calibrated successfully")
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

        # Check if images already exist (check database state first)
        row = self.products_db.execute(
            """
            SELECT status, stage FROM mosaic_groups 
            WHERE group_id = ?
            """,
            (group_id,),
        ).fetchone()

        # Database says imaged - verify filesystem to detect missing files
        if row and row[1] == "imaged":
            # Verify at least one image exists per MS file
            from dsa110_contimg.utils.naming import construct_image_basename

            all_exist = True
            for ms_path in ms_paths:
                ms_path_obj = Path(ms_path)
                img_basename = construct_image_basename(ms_path_obj)
                imgroot = str(self.images_dir / img_basename.replace(".img", ""))
                pbcor_fits = f"{imgroot}-image-pb.fits"
                pbcor_path = f"{imgroot}.pbcor"
                image_path = f"{imgroot}.image"
                if not (
                    Path(pbcor_fits).exists()
                    or Path(pbcor_path).exists()
                    or Path(image_path).exists()
                ):
                    all_exist = False
                    logger.warning(
                        f"Database says imaged but image missing for {ms_path}, re-imaging"
                    )
                    break

            if all_exist:
                logger.info(
                    f"Images already exist for group {group_id} (verified), skipping imaging"
                )
                return True
            # If files missing, fall through to re-image

        success_count = 0
        image_paths = []

        for ms_path in ms_paths:
            try:
                # Derive image name from MS path using validated naming
                from dsa110_contimg.utils.naming import construct_image_basename

                ms_path_obj = Path(ms_path)
                img_basename = construct_image_basename(ms_path_obj)
                imgroot = str(self.images_dir / img_basename.replace(".img", ""))

                # Check if image already exists on disk
                pbcor_fits = f"{imgroot}-image-pb.fits"
                pbcor_path = f"{imgroot}.pbcor"
                image_path = f"{imgroot}.image"

                if (
                    Path(pbcor_fits).exists()
                    or Path(pbcor_path).exists()
                    or Path(image_path).exists()
                ):
                    logger.debug(f"Image already exists for {ms_path}, skipping")
                    success_count += 1
                    continue

                if not self._ensure_model_ready_for_imaging(str(ms_path_obj)):
                    logger.error(
                        f"MODEL_DATA could not be populated for {ms_path}; aborting imaging workflow"
                    )
                    return False

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
                SET imaged_at = ?, status = 'imaged', stage = 'imaged'
                WHERE group_id = ?
                """,
                (time.time(), group_id),
            )
            self.products_db.commit()
            return True
        else:
            logger.warning(f"Only {success_count}/{len(ms_paths)} MS files imaged successfully")
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
                logger.warning(f"Error extracting time from {ms_path} for validation: {e}")

        # Check if times are in chronological order
        if len(ms_times) > 1:
            is_chronological = all(ms_times[i] <= ms_times[i + 1] for i in range(len(ms_times) - 1))
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
                logger.info(f"Re-sorted MS paths to chronological order for group {group_id}")
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
                    logger.error(
                        f"CRITICAL: Image file not found for MS {Path(ms_path).name}, imagename={imagename}. "
                        f"Cannot create mosaic without all images."
                    )

        # CRITICAL: Validate all images exist before mosaic creation
        # Use actual number of MS files in group, not hardcoded MS_PER_GROUP
        expected_image_count = len(ms_paths)
        if len(image_paths) < expected_image_count:
            missing_count = expected_image_count - len(image_paths)
            logger.error(
                f"CRITICAL: Only {len(image_paths)}/{expected_image_count} images found for group {group_id}. "
                f"Missing {missing_count} images. Cannot create mosaic. "
                f"All MS files must have corresponding images before mosaic creation."
            )
            return None

        # Verify all image files are readable
        for image_path in image_paths:
            if not Path(image_path).exists():
                logger.error(
                    f"CRITICAL: Image file does not exist: {image_path}. " f"Cannot create mosaic."
                )
                return None
            if not Path(image_path).is_file() and not Path(image_path).is_dir():
                logger.error(f"CRITICAL: Image path is not a valid file or directory: {image_path}")
                return None

        logger.debug(f"Validated {len(image_paths)} image files exist for group {group_id}")

        # Check if mosaic already exists (check database state)
        # Note: mosaic_path column doesn't exist, use mosaic_id to check
        row = self.products_db.execute(
            """
            SELECT mosaic_id, status FROM mosaic_groups 
            WHERE group_id = ? AND mosaic_id IS NOT NULL
            """,
            (group_id,),
        ).fetchone()

        if row and row[1] == "completed":
            mosaic_id = row[0]
            # Reconstruct mosaic path from mosaic_id
            mosaic_path = str(self.mosaic_output_dir / f"{mosaic_id}.image")
            fits_path = mosaic_path.replace(".image", ".fits")
            # Verify mosaic file actually exists
            if Path(fits_path).exists() or Path(mosaic_path).exists():
                logger.info(f"Mosaic already exists for group {group_id}: {mosaic_id}, skipping")
                return fits_path if Path(fits_path).exists() else mosaic_path

        # Generate mosaic
        # Construct mosaic ID using validated naming conventions
        from dsa110_contimg.utils.naming import construct_mosaic_id

        mosaic_id = construct_mosaic_id(group_id)
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

            # Store validation result for later use in publishing
            validation_passed = is_valid
            validation_issues = issues if issues else []

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
                from dsa110_contimg.imaging.export import (
                    export_fits,
                    save_png_from_fits,
                )

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
                SET mosaic_id = ?, mosaicked_at = ?, status = 'completed', stage = 'mosaicked'
                WHERE group_id = ?
                """,
                (mosaic_id, time.time(), group_id),
            )
            self.products_db.commit()

            logger.info(f"Mosaic created: {final_mosaic_path}")

            # CRITICAL: Register mosaic in data_registry for publishing workflow
            try:
                self._register_mosaic_for_publishing(
                    mosaic_id=mosaic_id,
                    mosaic_path=final_mosaic_path,
                    group_id=group_id,
                    image_paths=image_paths,
                    validation_passed=validation_passed,
                    validation_issues=validation_issues,
                )
            except Exception as e:
                logger.error(
                    f"Failed to register mosaic {mosaic_id} for publishing: {e}",
                    exc_info=True,
                )
                # Don't fail mosaic creation if registration fails, but log error

            # Hook: Update mosaic quality monitoring after mosaic creation
            try:
                from dsa110_contimg.qa.pipeline_hooks import hook_mosaic_complete

                hook_mosaic_complete()
            except Exception as e:
                logger.debug(f"Mosaic quality monitoring hook failed: {e}")

            return final_mosaic_path

        except Exception as e:
            logger.error(f"Failed to create mosaic: {e}", exc_info=True)
            return None

    def _register_mosaic_for_publishing(
        self,
        mosaic_id: str,
        mosaic_path: str,
        group_id: str,
        image_paths: List[str],
        validation_passed: bool = True,
        validation_issues: Optional[List[str]] = None,
    ) -> bool:
        """Register mosaic in data_registry and trigger publishing workflow.

        Args:
            mosaic_id: Mosaic identifier
            mosaic_path: Path to mosaic file
            group_id: Group identifier
            image_paths: List of image paths used to create mosaic

        Returns:
            True if successful, False otherwise
        """
        try:
            from dsa110_contimg.database.data_registration import register_pipeline_data
            from dsa110_contimg.database.data_registry import (
                ensure_data_registry_db,
                finalize_data,
            )
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            # Determine data_registry DB path (same precedence as products DB)
            registry_db_path = Path(
                os.getenv(
                    "DATA_REGISTRY_DB",
                    os.getenv(
                        "PIPELINE_STATE_DIR",
                        str(self.products_db_path.parent),
                    )
                    + "/data_registry.sqlite3",
                )
            )

            # Extract time range from first and last MS files
            ms_paths = self.get_group_ms_paths(group_id)
            start_mjd = end_mjd = None
            if ms_paths:
                try:
                    first_start, _, first_mid = extract_ms_time_range(ms_paths[0])
                    _, last_end, last_mid = extract_ms_time_range(ms_paths[-1])
                    start_mjd = first_start if first_start else first_mid
                    end_mjd = last_end if last_end else last_mid
                except Exception as e:
                    logger.warning(f"Could not extract time range for mosaic metadata: {e}")

            # Prepare metadata
            metadata = {
                "group_id": group_id,
                "mosaic_id": mosaic_id,
                "n_images": len(image_paths),
                "image_paths": image_paths,
                "ms_paths": ms_paths,
                "start_mjd": start_mjd,
                "end_mjd": end_mjd,
            }

            # Register mosaic in data_registry
            mosaic_path_obj = Path(mosaic_path).resolve()
            success = register_pipeline_data(
                data_type="mosaic",
                data_id=mosaic_id,
                file_path=mosaic_path_obj,
                metadata=metadata,
                auto_publish=True,
                db_path=registry_db_path,
            )

            if not success:
                logger.error(f"Failed to register mosaic {mosaic_id} in data_registry")
                return False

            logger.info(f"Registered mosaic {mosaic_id} in data_registry")

            # Finalize data to trigger auto-publish
            # Use actual validation result from validate_tiles_consistency
            conn = ensure_data_registry_db(registry_db_path)
            try:
                # Set QA status based on validation result
                # If validation passed, QA is passed; if issues found, QA is warning
                # Note: Warnings will prevent auto-publish (qa_status='passed' required for mosaics)
                # Mosaics with warnings can still be manually published via API
                # The warnings are stored in metadata for review
                qa_status = "passed" if validation_passed else "warning"
                # Always validated if mosaic was created (warnings are non-fatal)
                validation_status = "validated"

                # Add validation issues to metadata if present
                if validation_issues:
                    metadata["validation_issues"] = validation_issues

                finalize_success = finalize_data(
                    conn,
                    data_id=mosaic_id,
                    qa_status=qa_status,
                    validation_status=validation_status,
                )
                if finalize_success:
                    logger.info(f"Finalized mosaic {mosaic_id}, auto-publish triggered")
                else:
                    logger.warning(f"Finalization of mosaic {mosaic_id} did not trigger publish")
            finally:
                conn.close()

            return True

        except Exception as e:
            logger.error(
                f"Error registering mosaic {mosaic_id} for publishing: {e}",
                exc_info=True,
            )
            return False

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

        if len(all_ms) < self.ms_per_group:
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

        # Create new group with collision-resistant ID (same as check_for_new_group)
        import hashlib

        ms_paths_hash = hashlib.sha256(ms_paths_str.encode()).hexdigest()[:12]
        # Include microseconds for collision prevention
        timestamp = int(time.time() * 1000000)
        group_id = f"group_{ms_paths_hash}_{timestamp}"

        # CRITICAL: Check for duplicate group_id (shouldn't happen, but safeguard)
        existing_id = self.products_db.execute(
            "SELECT group_id FROM mosaic_groups WHERE group_id = ?",
            (group_id,),
        ).fetchone()

        if existing_id:
            # Collision detected - add random suffix
            import random

            suffix = random.randint(1000, 9999)
            group_id = f"group_{ms_paths_hash}_{timestamp}_{suffix}"
            logger.warning(
                f"Group ID collision detected in sliding window, using alternative ID: {group_id}"
            )

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

        If no calibrator is registered, attempts to auto-register one from catalog lookup.

        Args:
            ms_paths: List of MS file paths

        Returns:
            Tuple of (is_valid, dec_deg) or (False, None) if validation fails
        """
        # Get Dec from first MS
        try:
            import casacore.tables as casatables

            table = casatables.table  # noqa: N816

            t = table(ms_paths[0])
            field_table = t.getkeyword("FIELD")
            import numpy as np

            dec_deg = np.mean([f["REFERENCE_DIR"][0][1] * 180 / np.pi for f in field_table])
            t.close()

            # Check if calibrator is registered
            bp_cal = self.get_bandpass_calibrator_for_dec(dec_deg)
            if not bp_cal:
                # DOCUMENTATION FIX: Auto-register calibrator from catalog if not found
                # This enables zero-config operation as documented in DEFAULTS_AND_MINIMAL_INPUT.md
                logger.info(
                    f"No bandpass calibrator registered for Dec={dec_deg:.6f}. "
                    f"Attempting to auto-register from catalog..."
                )

                try:
                    from dsa110_contimg.calibration.selection import select_bandpass_from_catalog

                    # Try to find calibrator in the first MS
                    (
                        field_sel_str,
                        field_indices,
                        weighted_flux,
                        cal_info,
                        peak_field_idx,
                    ) = select_bandpass_from_catalog(
                        str(ms_paths[0]),
                        catalog_path=None,  # Auto-resolve to SQLite catalog
                        search_radius_deg=1.0,
                        freq_GHz=1.4,
                        window=3,
                    )

                    if cal_info:
                        cal_name, cal_ra, cal_dec, cal_flux_jy = cal_info
                        logger.info(
                            f"Found calibrator {cal_name} in catalog "
                            f"(RA={cal_ra:.6f}, Dec={cal_dec:.6f}, flux={cal_flux_jy:.3f} Jy). "
                            f"Auto-registering..."
                        )

                        # Auto-register with default tolerance
                        self.register_bandpass_calibrator(
                            calibrator_name=cal_name,
                            ra_deg=cal_ra,
                            dec_deg=cal_dec,
                            dec_tolerance=5.0,  # Default tolerance
                            registered_by="auto-registration",
                            notes=f"Auto-registered from catalog lookup for Dec={dec_deg:.6f}",
                        )

                        logger.info(
                            f"Successfully auto-registered bandpass calibrator {cal_name} "
                            f"for Dec={dec_deg:.6f}"
                        )

                        # Re-check after registration
                        bp_cal = self.get_bandpass_calibrator_for_dec(dec_deg)
                        if bp_cal:
                            logger.info(
                                f"Group Dec={dec_deg:.6f} validated: "
                                f"bandpass calibrator {bp_cal['name']} is now registered"
                            )
                            return True, dec_deg
                        else:
                            logger.error(f"Failed to retrieve calibrator after auto-registration")
                            return False, None
                    else:
                        logger.error(
                            f"No bandpass calibrator found in catalog for Dec={dec_deg:.6f}. "
                            f"Cannot process group. Please register a calibrator manually using "
                            f"--register-bpcal or ensure catalog contains suitable calibrators."
                        )
                        return False, None

                except Exception as e:
                    logger.error(
                        f"Failed to auto-register calibrator for Dec={dec_deg:.6f}: {e}. "
                        f"Please register manually using --register-bpcal.",
                        exc_info=True,
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
        if len(ms_paths) < self.ms_per_group:
            logger.warning(f"Group {group_id} has only {len(ms_paths)} MS files")
            return False

        # Validate Dec and calibrator registration
        is_valid, dec_deg = self.validate_group_dec(ms_paths)
        if not is_valid:
            logger.error(f"Group {group_id} validation failed: no calibrator registered for Dec")
            return False

        # Get calibrator RA for transit-based MS selection
        bp_cal = self.get_bandpass_calibrator_for_dec(dec_deg)
        calibrator_ra = bp_cal["ra_deg"] if bp_cal else None

        # Select calibration MS, preferring one that contains peak transit
        calibration_ms = self.select_calibration_ms(ms_paths, calibrator_ra=calibrator_ra)
        if not calibration_ms:
            logger.error(f"Could not select calibration MS for group {group_id}")
            return False

        # Solve calibration
        bpcal_solved, gaincal_solved, error_msg = self.solve_calibration_for_group(
            group_id, calibration_ms
        )
        if error_msg:
            logger.error(f"Calibration solving failed for group {group_id}: {error_msg}")
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

        # Run cross-matching if enabled
        if self.config and self.config.crossmatch.enabled:
            try:
                self.run_crossmatch_for_mosaic(group_id, mosaic_path)
            except Exception as e:
                logger.warning(
                    f"Cross-matching failed for group {group_id}: {e}. "
                    "Continuing without cross-match results."
                )

        logger.info(f"Successfully processed group {group_id}, mosaic: {mosaic_path}")
        return True

    def run_crossmatch_for_mosaic(self, group_id: str, mosaic_path: str) -> Optional[str]:
        """Run cross-matching stage for a completed mosaic.

        Args:
            group_id: Group identifier
            mosaic_path: Path to mosaic image (FITS or CASA)

        Returns:
            Cross-match status string, or None if disabled/failed
        """
        if not self.config or not self.config.crossmatch.enabled:
            logger.debug("Cross-matching is disabled, skipping")
            return None

        logger.info(f"Running cross-matching for mosaic: {mosaic_path}")

        try:
            from dsa110_contimg.pipeline import stages_impl
            from dsa110_contimg.pipeline.context import PipelineContext

            # Create pipeline context with mosaic as image output
            # Note: state_repository is optional - CrossMatchStage doesn't require it
            context = PipelineContext(
                config=self.config,
                job_id=None,
                inputs={},
                outputs={"image_path": mosaic_path},
                metadata={"group_id": group_id, "mosaic_path": mosaic_path},
                state_repository=None,
            )

            # Create and execute cross-match stage
            crossmatch_stage = stages_impl.CrossMatchStage(self.config)

            # Validate prerequisites
            is_valid, error_msg = crossmatch_stage.validate(context)
            if not is_valid:
                logger.warning(f"Cross-match validation failed for {mosaic_path}: {error_msg}")
                return None

            # Execute cross-matching
            updated_context = crossmatch_stage.execute(context)

            # Extract status from outputs
            status = updated_context.outputs.get("crossmatch_status", "unknown")
            n_matches = updated_context.outputs.get("n_matches", 0)
            n_catalogs = updated_context.outputs.get("n_catalogs", 0)

            logger.info(
                f"Cross-matching completed for {mosaic_path}: "
                f"status={status}, matches={n_matches}, catalogs={n_catalogs}"
            )

            return status

        except Exception as e:
            logger.error(
                f"Error running cross-matching for {mosaic_path}: {e}",
                exc_info=True,
            )
            raise


def main() -> int:
    """CLI entry point for streaming mosaic processing."""
    import argparse

    parser = argparse.ArgumentParser(description="Process streaming mosaic groups")
    parser.add_argument(
        "--products-db",
        type=Path,
        default=Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3")),
        help="Path to products database",
    )
    parser.add_argument(
        "--registry-db",
        type=Path,
        default=Path(os.getenv("CAL_REGISTRY_DB", "state/db/cal_registry.sqlite3")),
        help="Path to calibration registry database",
    )
    parser.add_argument(
        "--ms-dir",
        type=Path,
        default=Path(os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/raw/ms")),
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
        images_dir=args.images_dir,
        mosaic_output_dir=args.mosaic_dir,
    )

    use_sliding_window = not args.no_sliding_window

    if args.loop:
        logger.info("Starting streaming mosaic daemon (sliding window: %s)", use_sliding_window)
        while True:
            try:
                processed = manager.process_next_group(use_sliding_window=use_sliding_window)
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
