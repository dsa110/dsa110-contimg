# pylint: disable=no-member  # astropy.units uses dynamic attributes (min, etc.)
"""
Concrete pipeline stage implementations.

These stages wrap existing conversion, calibration, and imaging functions
to provide a unified pipeline interface.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import astropy.units as u  # pylint: disable=no-member
import numpy as np
import pandas as pd

from dsa110_contimg.catalog.coverage import validate_catalog_choice
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import PipelineStage
from dsa110_contimg.utils.ms_organization import (
    create_path_mapper,
    determine_ms_type,
    organize_ms_file,
)
from dsa110_contimg.utils.runtime_safeguards import (
    log_progress,
    progress_monitor,
    require_casa6_python,
)
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logger = logging.getLogger(__name__)


class CatalogSetupStage(PipelineStage):
    """Catalog setup stage: Build catalog databases if missing for observation declination.

    This stage runs before other stages to ensure catalog databases (NVSS, FIRST, RAX)
    are available for the declination strip being observed. Since DSA-110 only slews
    in elevation and changes declination rarely, catalogs need to be updated when
    declination changes.

    The stage:
    1. Extracts declination from the observation (HDF5 file)
    2. Checks if catalog databases exist for that declination strip
    3. Builds missing catalogs automatically
    4. Logs catalog status for downstream stages

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> stage = CatalogSetupStage(config)
        >>> context = PipelineContext(
        ...     config=config,
        ...     inputs={"input_path": "/data/observation.hdf5"}
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute stage
        ...     result_context = stage.execute(context)
        ...     # Check catalog setup status
        ...     status = result_context.outputs["catalog_setup_status"]
        ...     # Status can be: "completed", "skipped_no_dec", "skipped_error"

    Inputs:
        - `input_path` (str): Path to HDF5 observation file

    Outputs:
        - `catalog_setup_status` (str): Status of catalog setup operation
    """

    def __init__(self, config: PipelineConfig):
        """Initialize catalog setup stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for catalog setup."""
        # Need input_path (HDF5) to extract declination
        if "input_path" not in context.inputs:
            return False, "input_path required to extract declination for catalog setup"

        input_path = context.inputs["input_path"]
        if not Path(input_path).exists():
            return False, f"Input file not found: {input_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute catalog setup: build databases if missing.

        Args:
            context: Pipeline context

        Returns:
            Updated context with catalog status
        """
        from dsa110_contimg.catalog.builders import (
            build_first_strip_db,
            build_nvss_strip_db,
            build_rax_strip_db,
        )
        from dsa110_contimg.catalog.query import resolve_catalog_path
        from dsa110_contimg.pointing.utils import load_pointing

        input_path = context.inputs["input_path"]
        logger.info(f"Catalog setup stage: Checking catalogs for {Path(input_path).name}")

        # Extract declination from HDF5 file
        try:
            info = load_pointing(str(input_path))
            if "dec_deg" not in info:
                logger.warning(
                    f"Could not extract declination from {input_path}. "
                    f"Available keys: {list(info.keys())}. Skipping catalog setup."
                )
                return context.with_output("catalog_setup_status", "skipped_no_dec")

            dec_center = float(info["dec_deg"])
            logger.info(f"Extracted declination: {dec_center:.6f} degrees")

            # Detect declination change
            dec_change_detected = False
            previous_dec = None
            dec_change_threshold = getattr(
                self.config, "catalog_setup_dec_change_threshold", 0.1
            )  # Default 0.1 degrees

            try:
                from dsa110_contimg.database import ensure_ingest_db

                ingest_db = self.config.paths.queue_db
                conn = ensure_ingest_db(ingest_db)
                cursor = conn.cursor()

                # Get most recent declination from pointing_history
                cursor.execute(
                    "SELECT dec_deg FROM pointing_history ORDER BY timestamp DESC LIMIT 1"
                )
                result = cursor.fetchone()
                if result:
                    previous_dec = float(result[0])
                    dec_change = abs(dec_center - previous_dec)

                    if dec_change > dec_change_threshold:
                        dec_change_detected = True
                        logger.warning(
                            f":warning:  DECLINATION CHANGE DETECTED: "
                            f"{previous_dec:.6f}° → {dec_center:.6f}° "
                            f"(Δ = {dec_change:.6f}° > {dec_change_threshold:.6f}° threshold)"
                        )
                        logger.warning(
                            ":warning:  Telescope pointing has changed significantly. "
                            "Catalogs will be rebuilt for new declination strip."
                        )

                        # Pre-calculate transit times for all registered calibrators
                        try:
                            from dsa110_contimg.conversion.transit_precalc import (
                                precalculate_transits_for_calibrator,
                            )
                            from dsa110_contimg.database import (
                                get_products_db_connection,
                            )

                            products_db = get_products_db_connection(self.config.paths.products_db)
                            cursor = products_db.cursor()

                            # Get all active calibrators
                            active_calibrators = cursor.execute(
                                """
                                SELECT calibrator_name, ra_deg, dec_deg
                                FROM bandpass_calibrators
                                WHERE status = 'active'
                                """
                            ).fetchall()

                            if active_calibrators:
                                logger.info(
                                    f"Pre-calculating transit times for {len(active_calibrators)} "
                                    f"registered calibrators after pointing change..."
                                )

                                for cal_name, ra_deg, dec_deg in active_calibrators:
                                    try:
                                        transits_with_data = precalculate_transits_for_calibrator(
                                            products_db=products_db,
                                            calibrator_name=cal_name,
                                            ra_deg=ra_deg,
                                            dec_deg=dec_deg,
                                            max_days_back=60,
                                        )
                                        logger.info(
                                            f"  :check_mark: {cal_name}: {transits_with_data} transits have available data"
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            f"  :ballot_x: Failed to pre-calculate for {cal_name}: {e}"
                                        )

                                products_db.close()
                        except Exception as e:
                            logger.warning(
                                f"Failed to pre-calculate transit times after pointing change: {e}"
                            )
                    else:
                        logger.info(
                            f"Declination stable: {dec_center:.6f}° "
                            f"(previous: {previous_dec:.6f}°, Δ = {dec_change:.6f}°)"
                        )

                conn.close()

            except Exception as e:
                logger.debug(f"Could not check previous declination (first observation?): {e}")
                # First observation or no pointing history - not an error
                pass

            # Log pointing to pointing_history for future change detection
            try:
                from dsa110_contimg.database import ensure_ingest_db

                ingest_db = self.config.paths.queue_db
                conn = ensure_ingest_db(ingest_db)

                # Get timestamp from observation
                timestamp = info.get("mid_time")
                if timestamp:
                    if hasattr(timestamp, "mjd"):
                        timestamp_mjd = timestamp.mjd
                    else:
                        timestamp_mjd = float(timestamp)

                    ra_deg = info.get("ra_deg", 0.0)

                    conn.execute(
                        "INSERT OR REPLACE INTO pointing_history (timestamp, ra_deg, dec_deg) VALUES (?, ?, ?)",
                        (timestamp_mjd, ra_deg, dec_center),
                    )
                    conn.commit()
                    conn.close()

                    if dec_change_detected:
                        logger.info(
                            f"Logged new pointing to pointing_history: "
                            f"RA={ra_deg:.6f}°, Dec={dec_center:.6f}°"
                        )

            except Exception as e:
                logger.debug(f"Could not log pointing to history: {e}")
                # Non-critical - continue with catalog setup
                pass

        except Exception as e:
            logger.warning(
                f"Error reading declination from {input_path}: {e}. Skipping catalog setup."
            )
            return context.with_output("catalog_setup_status", "skipped_error")

        # Calculate declination range (default ±6 degrees, configurable)
        dec_range_deg = getattr(self.config, "catalog_setup_dec_range", 6.0)  # Default ±6 degrees
        dec_min = dec_center - dec_range_deg
        dec_max = dec_center + dec_range_deg
        dec_range = (dec_min, dec_max)

        logger.info(
            f"Catalog declination strip: {dec_min:.6f}° to {dec_max:.6f}° "
            f"(center: {dec_center:.6f}°, range: ±{dec_range_deg}°)"
        )

        # Check and build catalogs
        catalogs_built = []
        catalogs_existed = []
        catalogs_failed = []

        catalog_types = ["nvss", "first", "rax", "atnf"]

        for catalog_type in catalog_types:
            try:
                # Check if catalog database exists
                try:
                    catalog_path = resolve_catalog_path(
                        catalog_type=catalog_type, dec_strip=dec_center
                    )
                    if catalog_path.exists():
                        logger.info(f":check_mark: {catalog_type.upper()} catalog exists: {catalog_path}")
                        catalogs_existed.append(catalog_type)
                        continue
                except FileNotFoundError:
                    # Catalog doesn't exist, will build it
                    pass

                # Build catalog database
                logger.info(f"Building {catalog_type.upper()} catalog database...")

                if catalog_type == "nvss":
                    db_path = build_nvss_strip_db(
                        dec_center=dec_center,
                        dec_range=dec_range,
                        output_path=None,  # Auto-generate path
                        min_flux_mjy=None,  # No flux threshold
                    )
                elif catalog_type == "first":
                    db_path = build_first_strip_db(
                        dec_center=dec_center,
                        dec_range=dec_range,
                        output_path=None,  # Auto-generate path
                        min_flux_mjy=None,  # No flux threshold
                        cache_dir=".cache/catalogs",
                    )
                elif catalog_type == "rax":
                    db_path = build_rax_strip_db(
                        dec_center=dec_center,
                        dec_range=dec_range,
                        output_path=None,  # Auto-generate path
                        min_flux_mjy=None,  # No flux threshold
                        cache_dir=".cache/catalogs",
                    )
                else:
                    logger.warning(f"Unknown catalog type: {catalog_type}, skipping...")
                    continue

                logger.info(
                    f":check_mark: {catalog_type.upper()} catalog built: {db_path} "
                    f"({db_path.stat().st_size / (1024 * 1024):.2f} MB)"
                )
                catalogs_built.append(catalog_type)

            except Exception as e:
                logger.error(
                    f":ballot_x: Failed to build {catalog_type.upper()} catalog: {e}",
                    exc_info=True,
                )
                catalogs_failed.append(catalog_type)

        # Log summary
        if catalogs_built:
            logger.info(
                f"Catalog setup complete: Built {len(catalogs_built)} catalogs "
                f"({', '.join(catalogs_built)})"
            )
        if catalogs_existed:
            logger.info(
                f"Catalog setup complete: {len(catalogs_existed)} catalogs already exist "
                f"({', '.join(catalogs_existed)})"
            )
        if catalogs_failed:
            logger.warning(
                f"Catalog setup incomplete: {len(catalogs_failed)} catalogs failed "
                f"({', '.join(catalogs_failed)}). Pipeline will continue but may use "
                f"CSV fallback or fail if catalogs are required."
            )

        # Store catalog status in context
        catalog_status = {
            "dec_center": dec_center,
            "dec_range": dec_range,
            "catalogs_built": catalogs_built,
            "catalogs_existed": catalogs_existed,
            "catalogs_failed": catalogs_failed,
            "dec_change_detected": dec_change_detected,
            "previous_dec": previous_dec,
        }

        return context.with_output("catalog_setup_status", catalog_status)

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup on failure (nothing to clean up for catalog setup)."""
        pass

    def get_name(self) -> str:
        """Get stage name."""
        return "catalog_setup"


class ConversionStage(PipelineStage):
    """Conversion stage: UVH5 → MS.

    Discovers complete subband groups in the specified time window and
    converts them to CASA Measurement Sets.

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> stage = ConversionStage(config)
        >>> context = PipelineContext(
        ...     config=config,
        ...     inputs={
        ...         "input_path": "/data/observation.hdf5",
        ...         "start_time": "2025-01-01T00:00:00",
        ...         "end_time": "2025-01-01T01:00:00"
        ...     }
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute conversion
        ...     result_context = stage.execute(context)
        ...     # Get converted MS path
        ...     ms_path = result_context.outputs["ms_path"]
        ...     # MS path is now available for calibration stages

    Inputs:
        - `input_path` (str): Path to UVH5 input file
        - `start_time` (str): Start time for conversion window
        - `end_time` (str): End time for conversion window

    Outputs:
        - `ms_path` (str): Path to converted Measurement Set file
    """

    def __init__(self, config: PipelineConfig):
        """Initialize conversion stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for conversion."""
        # Check input directory exists
        if not context.config.paths.input_dir.exists():
            return False, f"Input directory not found: {context.config.paths.input_dir}"

        # Check output directory is writable
        output_dir = context.config.paths.output_dir
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        if not output_dir.parent.exists():
            return False, f"Cannot create output directory: {output_dir.parent}"

        # Check required inputs
        if "start_time" not in context.inputs:
            return False, "start_time required in context.inputs"
        if "end_time" not in context.inputs:
            return False, "end_time required in context.inputs"

        return True, None

    @progress_monitor(operation_name="UVH5 to MS Conversion", warn_threshold=300.0)
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute conversion stage."""
        import time

        start_time_sec = time.time()
        log_progress("Starting UVH5 to MS conversion stage...")

        # Use flattened import from top-level conversion module
        from dsa110_contimg.conversion import convert_subband_groups_to_ms

        start_time = context.inputs["start_time"]
        end_time = context.inputs["end_time"]

        # Prepare writer kwargs
        writer_kwargs = {
            "max_workers": self.config.conversion.max_workers,
            "skip_validation_during_conversion": self.config.conversion.skip_validation_during_conversion,
            "skip_calibration_recommendations": self.config.conversion.skip_calibration_recommendations,
        }
        if self.config.conversion.stage_to_tmpfs:
            writer_kwargs["stage_to_tmpfs"] = True
            if context.config.paths.scratch_dir:
                writer_kwargs["tmpfs_path"] = str(context.config.paths.scratch_dir)

        # Create path mapper for organized output (default to science)
        ms_base_dir = Path(context.config.paths.output_dir)
        path_mapper = create_path_mapper(ms_base_dir, is_calibrator=False, is_failed=False)

        # Execute conversion (function returns None, creates MS files in organized locations)
        convert_subband_groups_to_ms(
            str(context.config.paths.input_dir),
            str(context.config.paths.output_dir),
            start_time,
            end_time,
            writer=self.config.conversion.writer,
            writer_kwargs=writer_kwargs,
            path_mapper=path_mapper,  # Write directly to organized location
        )

        # Discover created MS files (now in organized subdirectories)
        # Pattern: YYYY-MM-DDTHH:MM:SS.ms (no suffixes)
        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.ms$")

        output_path = Path(context.config.paths.output_dir)
        ms_files = []
        if output_path.exists():
            # Search in organized subdirectories (science/, calibrators/, failed/)
            for subdir in ["science", "calibrators", "failed"]:
                subdir_path = output_path / subdir
                if subdir_path.exists():
                    # Search recursively for date subdirectories
                    for date_dir in subdir_path.iterdir():
                        if date_dir.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", date_dir.name):
                            for ms in date_dir.glob("*.ms"):
                                if ms.is_dir() and pattern.match(ms.name):
                                    ms_files.append(str(ms))

            # Also check flat location for backward compatibility (legacy files)
            for ms in output_path.glob("*.ms"):
                if ms.is_dir():
                    if pattern.match(ms.name):
                        ms_files.append(str(ms))
                    else:
                        logger.warning(
                            f"Skipping MS file '{ms.name}' - filename doesn't match expected pattern "
                            f"(YYYY-MM-DDTHH:MM:SS.ms). This may be a legacy file or use a different "
                            f"naming convention."
                        )

        if not ms_files:
            raise ValueError("Conversion produced no MS files")

        # Sort MS files by time for consistency
        ms_files = sorted(ms_files)

        # Use first MS path for backward compatibility (single MS workflows)
        ms_path = ms_files[0]

        # Run quality checks after conversion if they were skipped during conversion
        if self.config.conversion.skip_validation_during_conversion:
            from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion

            logger.info("Running quality checks after conversion...")
            try:
                qa_passed, qa_metrics = check_ms_after_conversion(
                    ms_path=ms_path,
                    quick_check_only=False,
                    alert_on_issues=True,
                )
                if qa_passed:
                    logger.info(":check_mark: MS passed quality checks")
                else:
                    logger.warning(":warning_sign: MS quality issues detected (see alerts)")
            except Exception as e:
                logger.warning(f"Quality check failed (non-fatal): {e}")

        log_progress(
            f"Completed UVH5 to MS conversion stage. Created {len(ms_files)} MS file(s).",
            start_time_sec,
        )

        # MS files are already in organized locations (written directly via path_mapper)
        # No need to move them - they're already organized
        organized_ms_files = ms_files
        organized_ms_path = ms_files[0] if ms_files else ms_path

        # Update MS index via state repository if available (with organized paths)
        if context.state_repository:
            try:
                for ms_file in organized_ms_files:
                    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_file)
                    context.state_repository.upsert_ms_index(
                        ms_file,
                        {
                            "start_mjd": start_mjd,
                            "end_mjd": end_mjd,
                            "mid_mjd": mid_mjd,
                            "status": "converted",
                            "stage": "conversion",
                        },
                    )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Register MS files in data registry (with organized paths)
        try:
            from dsa110_contimg.database.data_registration import register_pipeline_data

            for ms_file in organized_ms_files:
                ms_path_obj = Path(ms_file)
                # Use MS path as data_id (unique identifier)
                data_id = str(ms_path_obj)
                # Extract metadata from MS if available
                metadata = {}
                try:
                    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_file)
                    if start_mjd:
                        metadata["start_mjd"] = start_mjd
                    if end_mjd:
                        metadata["end_mjd"] = end_mjd
                    if mid_mjd:
                        metadata["mid_mjd"] = mid_mjd
                except Exception as e:
                    logger.debug(f"Could not extract MS time range for metadata: {e}")

                register_pipeline_data(
                    data_type="ms",
                    data_id=data_id,
                    file_path=ms_path_obj,
                    metadata=metadata if metadata else None,
                    auto_publish=True,
                )
                logger.info(f"Registered MS in data registry: {ms_file}")
        except Exception as e:
            logger.warning(f"Failed to register MS files in data registry: {e}")

        # Hook: Generate performance monitoring plots after MS conversion
        try:
            from dsa110_contimg.qa.pipeline_hooks import (  # pylint: disable=import-error,no-name-in-module
                hook_ms_conversion_complete,
            )

            hook_ms_conversion_complete()
        except Exception as e:
            logger.debug(f"Performance monitoring hook failed: {e}")

        # Return both single MS path (for backward compatibility) and all MS paths
        return context.with_outputs(
            {
                "ms_path": organized_ms_path,  # Single MS for backward compatibility
                "ms_paths": organized_ms_files,  # All MS files (organized)
            }
        )

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate conversion outputs."""
        if "ms_path" not in context.outputs:
            return False, "ms_path not found in outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file does not exist: {ms_path}"

        # Validate MS is readable and has required columns
        # Ensure CASAPATH is set before importing CASA modules
        from dsa110_contimg.utils.casa_init import ensure_casa_path

        ensure_casa_path()

        try:
            import casacore.tables as casatables

            table = casatables.table

            with table(ms_path, readonly=True) as tb:
                required_cols = ["DATA", "ANTENNA1", "ANTENNA2", "TIME"]
                missing = [col for col in required_cols if col not in tb.colnames()]
                if missing:
                    return False, f"MS missing required columns: {missing}"
                if tb.nrows() == 0:
                    return False, "MS has no data rows"
        except Exception as e:
            return False, f"Cannot validate MS: {e}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial conversion outputs on failure."""
        # If conversion failed, remove any partial MS files created
        if "ms_path" in context.outputs:
            ms_path = Path(context.outputs["ms_path"])
            if ms_path.exists():
                try:
                    import shutil

                    shutil.rmtree(ms_path, ignore_errors=True)
                    logger.info(f"Cleaned up partial MS: {ms_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup partial MS {ms_path}: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "conversion"


class CalibrationSolveStage(PipelineStage):
    """Calibration solve stage: Solve calibration solutions (K, BP, G).

    This stage solves calibration tables (delay/K, bandpass/BP, gains/G)
    for a calibrator Measurement Set. This wraps the calibration CLI
    functions directly without subprocess overhead.

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> stage = CalibrationSolveStage(config)
        >>> # Context should have ms_path from conversion stage
        >>> context = PipelineContext(
        ...     config=config,
        ...     outputs={"ms_path": "/data/converted.ms"}
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute calibration solving
        ...     result_context = stage.execute(context)
        ...     # Get calibration tables
        ...     cal_tables = result_context.outputs["calibration_tables"]
        ...     # Tables include: K, BA, BP, GA, GP, 2G
        ...     assert "K" in cal_tables

    Inputs:
        - `ms_path` (str): Path to Measurement Set (from context.outputs)

    Outputs:
        - `calibration_tables` (dict): Dictionary of calibration table paths
          Keys: "K", "BA", "BP", "GA", "GP", "2G" (depending on config)
    """

    def __init__(self, config: PipelineConfig):
        """Initialize calibration solve stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for calibration solving."""
        if "ms_path" not in context.outputs:
            return (
                False,
                "ms_path required in context.outputs (conversion must run first)",
            )

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    @require_casa6_python
    @progress_monitor(operation_name="Calibration Solving", warn_threshold=600.0)
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration solve stage."""
        log_progress("Starting calibration solve stage...")

        from dsa110_contimg.utils.locking import LockError, file_lock

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration solve stage: {ms_path}")

        # CRITICAL: Acquire lock to prevent concurrent calibration solves for same MS
        # This prevents race conditions when multiple pipeline runs process the same MS
        lock_path = Path(ms_path).parent / f".{Path(ms_path).stem}.cal_lock"
        # 1 hour timeout (calibration can take a long time)
        lock_timeout = 3600.0

        try:
            with file_lock(lock_path, timeout=lock_timeout):
                return self._execute_calibration_solve(context, ms_path)
        except LockError as e:
            error_msg = (
                f"Cannot acquire calibration lock for {ms_path}. "
                f"Another calibration solve may be in progress. "
                f"If no process is running, check for stale lock file: {lock_path}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _execute_calibration_solve(
        self, context: PipelineContext, ms_path: str
    ) -> PipelineContext:  # noqa: E501
        """Internal calibration solve execution (called within lock)."""
        import glob
        import os

        from dsa110_contimg.calibration.calibration import (  # noqa: E501
            solve_bandpass,
            solve_delay,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (  # noqa: E501
            flag_zeros,
            reset_flags,
        )
        from dsa110_contimg.calibration.flagging_adaptive import (  # noqa: E501
            CalibrationFailure,
            flag_rfi_adaptive,
        )

        start_time_sec = time.time()

        # Get calibration parameters from context inputs or config
        params = context.inputs.get("calibration_params", {})
        field = params.get("field", "0")
        refant = params.get("refant", "103")
        solve_delay_flag = params.get("solve_delay", False)
        solve_bandpass_flag = params.get("solve_bandpass", True)
        solve_gains_flag = params.get("solve_gains", True)
        model_source = params.get("model_source", "catalog")
        gain_solint = params.get("gain_solint", "inf")
        gain_calmode = params.get("gain_calmode", "ap")
        bp_combine_field = params.get("bp_combine_field", False)
        prebp_phase = params.get("prebp_phase", False)
        flag_autocorr = params.get("flag_autocorr", True)
        # NEW: Enable adaptive flagging by default
        use_adaptive_flagging = params.get("use_adaptive_flagging", True)

        # Handle existing table discovery
        use_existing = params.get("use_existing_tables", "auto")
        existing_k = params.get("existing_k_table")
        existing_bp = params.get("existing_bp_table")
        existing_g = params.get("existing_g_table")

        if use_existing == "auto":
            ms_dir = os.path.dirname(ms_path)
            ms_base = os.path.basename(ms_path).replace(".ms", "")

            if not solve_delay_flag and not existing_k:
                k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
                k_tables = sorted(
                    [p for p in glob.glob(k_pattern) if os.path.isdir(p)],
                    key=os.path.getmtime,
                    reverse=True,
                )
                if k_tables:
                    existing_k = k_tables[0]

            if not solve_bandpass_flag and not existing_bp:
                bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
                bp_tables = sorted(
                    [p for p in glob.glob(bp_pattern) if os.path.isdir(p)],
                    key=os.path.getmtime,
                    reverse=True,
                )
                if bp_tables:
                    existing_bp = bp_tables[0]

            if not solve_gains_flag and not existing_g:
                g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")
                g_tables = sorted(
                    [p for p in glob.glob(g_pattern) if os.path.isdir(p)],
                    key=os.path.getmtime,
                    reverse=True,
                )
                if g_tables:
                    existing_g = g_tables[0]

        # Determine table prefix
        table_prefix = params.get("table_prefix")
        if not table_prefix:
            table_prefix = f"{os.path.splitext(ms_path)[0]}_{field}"

        # Define internal calibration function for adaptive flagging
        # This will be called by flag_rfi_adaptive to test if calibration succeeds
        cal_tables_result = {}  # Shared dict to store results between function calls

        def _perform_calibration_solve(ms_path_inner: str, refant_inner: str, **kwargs):
            """Internal function to perform calibration solving.

            This is called by flag_rfi_adaptive to test if calibration succeeds.
            Raises CalibrationFailure if calibration fails.
            """
            nonlocal cal_tables_result

            # Clear previous results
            cal_tables_result.clear()

            # Step 3: Solve delay (K) if requested
            ktabs_inner = []
            if solve_delay_flag and not existing_k:
                logger.info("Solving delay (K) calibration...")
                try:
                    ktabs_inner = solve_delay(
                        ms_path_inner,
                        field,
                        refant_inner,
                        table_prefix=table_prefix,
                        combine_spw=params.get("k_combine_spw", False),
                        t_slow=params.get("k_t_slow", "inf"),
                        t_fast=params.get("k_t_fast", "60s"),
                        uvrange=params.get("k_uvrange", ""),
                        minsnr=params.get("k_minsnr", 5.0),
                        skip_slow=params.get("k_skip_slow", False),
                    )
                except Exception as e:
                    logger.error(f"Delay (K) calibration failed: {e}")
                    raise CalibrationFailure(f"Delay calibration failed: {e}") from e
            elif existing_k:
                ktabs_inner = [existing_k]
                logger.info(f"Using existing K table: {existing_k}")

            # Step 4: Pre-bandpass phase (if requested)
            prebp_table_inner = None
            if prebp_phase:
                logger.info("Solving pre-bandpass phase...")
                try:
                    prebp_table_inner = solve_prebandpass_phase(
                        ms_path_inner,
                        field,
                        refant_inner,
                        table_prefix=table_prefix,
                        uvrange=params.get("prebp_uvrange", ""),
                        minsnr=params.get("prebp_minsnr", 3.0),
                    )
                except Exception as e:
                    logger.error(f"Pre-bandpass phase calibration failed: {e}")
                    raise CalibrationFailure(f"Pre-bandpass phase failed: {e}") from e

            # Step 5: Solve bandpass (BP) if requested
            bptabs_inner = []
            if solve_bandpass_flag and not existing_bp:
                logger.info("Solving bandpass (BP) calibration...")
                try:
                    bptabs_inner = solve_bandpass(
                        ms_path_inner,
                        field,
                        refant_inner,
                        ktable=ktabs_inner[0] if ktabs_inner else None,
                        table_prefix=table_prefix,
                        set_model=True,
                        model_standard=params.get("bp_model_standard", "Perley-Butler 2017"),
                        combine_fields=bp_combine_field,
                        combine_spw=params.get("bp_combine_spw", False),
                        minsnr=params.get("bp_minsnr", 5.0),
                        uvrange=params.get("bp_uvrange", ""),
                        prebandpass_phase_table=prebp_table_inner,
                        bp_smooth_type=params.get("bp_smooth_type"),
                        bp_smooth_window=params.get("bp_smooth_window"),
                    )
                except Exception as e:
                    logger.error(f"Bandpass (BP) calibration failed: {e}")
                    raise CalibrationFailure(f"Bandpass calibration failed: {e}") from e
            elif existing_bp:
                bptabs_inner = [existing_bp]
                logger.info(f"Using existing BP table: {existing_bp}")

            # Step 6: Solve gains (G) if requested
            gtabs_inner = []
            if solve_gains_flag and not existing_g:
                logger.info("Solving gains (G) calibration...")
                try:
                    phase_only = (gain_calmode == "p") or bool(params.get("fast"))
                    gtabs_inner = solve_gains(
                        ms_path_inner,
                        field,
                        refant_inner,
                        ktable=ktabs_inner[0] if ktabs_inner else None,
                        bptables=bptabs_inner,
                        table_prefix=table_prefix,
                        t_short=params.get("gain_t_short", "60s"),
                        combine_fields=bp_combine_field,
                        phase_only=phase_only,
                        uvrange=params.get("gain_uvrange", ""),
                        solint=gain_solint,
                        minsnr=params.get("gain_minsnr", 3.0),
                    )
                except Exception as e:
                    logger.error(f"Gains (G) calibration failed: {e}")
                    raise CalibrationFailure(f"Gain calibration failed: {e}") from e
            elif existing_g:
                gtabs_inner = [existing_g]
                logger.info(f"Using existing G table: {existing_g}")

            # Store results for later use
            cal_tables_result["ktabs"] = ktabs_inner
            cal_tables_result["bptabs"] = bptabs_inner
            cal_tables_result["gtabs"] = gtabs_inner
            cal_tables_result["prebp_table"] = prebp_table_inner

            logger.info(":check_mark: Calibration solve completed successfully")

        # Step 1: Flagging (if requested)
        adaptive_result = None
        if params.get("do_flagging", True):
            logger.info("Resetting flags...")
            reset_flags(ms_path)
            flag_zeros(ms_path)

            # Apply adaptive flagging (default → aggressive if calibration fails)
            if use_adaptive_flagging:
                logger.info(
                    "Using adaptive flagging strategy (default → aggressive on calibration failure)"
                )

                # Step 2: Model population (required for calibration)
                # This must be done BEFORE adaptive flagging since calibration needs the model
                if model_source == "catalog":
                    from dsa110_contimg.calibration.model import populate_model_from_catalog

                    logger.info("Populating MODEL_DATA from catalog...")
                    populate_model_from_catalog(
                        ms_path,
                        field=field,
                        calibrator_name=params.get("calibrator_name"),
                        cal_ra_deg=params.get("cal_ra_deg"),
                        cal_dec_deg=params.get("cal_dec_deg"),
                        cal_flux_jy=params.get("cal_flux_jy"),
                    )
                elif model_source == "image":
                    from dsa110_contimg.calibration.model import populate_model_from_image

                    model_image = params.get("model_image")
                    if not model_image:
                        raise ValueError("model_image required when model_source='image'")
                    logger.info(f"Populating MODEL_DATA from image: {model_image}")
                    populate_model_from_image(ms_path, field=field, model_image=model_image)

                # Run adaptive flagging with calibration testing
                aggressive_strategy = params.get(
                    "aggressive_strategy", "/data/dsa110-contimg/config/dsa110-aggressive.lua"
                )
                backend = params.get("flagging_backend", "aoflagger")

                adaptive_result = flag_rfi_adaptive(
                    ms_path=ms_path,
                    refant=refant,
                    calibrate_fn=_perform_calibration_solve,
                    calibrate_kwargs={},
                    aggressive_strategy=aggressive_strategy,
                    backend=backend,
                )

                logger.info(
                    f"Adaptive flagging complete: Used {adaptive_result['strategy']} strategy"
                )
                logger.info(
                    f"Flagging success: {adaptive_result['success']}, Attempts: {adaptive_result['attempts']}"
                )

                # Extract calibration results from shared dict
                ktabs = cal_tables_result.get("ktabs", [])
                bptabs = cal_tables_result.get("bptabs", [])
                gtabs = cal_tables_result.get("gtabs", [])
                # prebp_table available in cal_tables_result if needed for debugging

            else:
                # Legacy non-adaptive flagging
                from dsa110_contimg.calibration.flagging import flag_rfi

                logger.info("Using legacy non-adaptive flagging")
                flag_rfi(ms_path)

                # TEMPORAL TRACKING: Capture flag snapshot after Phase 1 (pre-calibration flagging)
                try:
                    from dsa110_contimg.calibration.flagging_temporal import capture_flag_snapshot

                    phase1_snapshot = capture_flag_snapshot(
                        ms_path=str(ms_path),
                        phase="phase1_post_rfi",
                        refant=refant,
                    )
                    logger.info(
                        ":check_mark: Phase 1 flag snapshot captured: %.1f%% overall flagging",
                        phase1_snapshot.total_flagged_fraction * 100,
                    )

                    # Store snapshot for later comparison (will be saved to database in later step)
                    if "_temporal_snapshots" not in params:
                        params["_temporal_snapshots"] = {}
                    params["_temporal_snapshots"]["phase1"] = phase1_snapshot
                except Exception as e:
                    logger.warning(f"Failed to capture Phase 1 flag snapshot: {e}")
                    logger.warning(
                        "Continuing with calibration (temporal tracking disabled for this run)"
                    )

                # Step 2: Model population (required for calibration)
                if model_source == "catalog":
                    from dsa110_contimg.calibration.model import populate_model_from_catalog

                    logger.info("Populating MODEL_DATA from catalog...")
                    populate_model_from_catalog(
                        ms_path,
                        field=field,
                        calibrator_name=params.get("calibrator_name"),
                        cal_ra_deg=params.get("cal_ra_deg"),
                        cal_dec_deg=params.get("cal_dec_deg"),
                        cal_flux_jy=params.get("cal_flux_jy"),
                    )
                elif model_source == "image":
                    from dsa110_contimg.calibration.model import populate_model_from_image

                    model_image = params.get("model_image")
                    if not model_image:
                        raise ValueError("model_image required when model_source='image'")
                    logger.info(f"Populating MODEL_DATA from image: {model_image}")
                    populate_model_from_image(ms_path, field=field, model_image=model_image)

                # Perform calibration solve
                _perform_calibration_solve(ms_path, refant)

                # Extract results
                ktabs = cal_tables_result.get("ktabs", [])
                bptabs = cal_tables_result.get("bptabs", [])
                gtabs = cal_tables_result.get("gtabs", [])
                # prebp_table available in cal_tables_result if needed for debugging

            # Flag autocorrelations (after RFI flagging)
            if flag_autocorr:
                from casatasks import flagdata

                logger.info("Flagging autocorrelations...")
                flagdata(vis=str(ms_path), autocorr=True, flagbackup=False)
                logger.info(":check_mark: Autocorrelations flagged")

        else:
            # No flagging requested - just do model population and calibration
            logger.info(
                "Flagging disabled, proceeding directly to model population and calibration"
            )

            # Step 2: Model population (required for calibration)
            if model_source == "catalog":
                from dsa110_contimg.calibration.model import populate_model_from_catalog

                logger.info("Populating MODEL_DATA from catalog...")
                populate_model_from_catalog(
                    ms_path,
                    field=field,
                    calibrator_name=params.get("calibrator_name"),
                    cal_ra_deg=params.get("cal_ra_deg"),
                    cal_dec_deg=params.get("cal_dec_deg"),
                    cal_flux_jy=params.get("cal_flux_jy"),
                )
            elif model_source == "image":
                from dsa110_contimg.calibration.model import populate_model_from_image

                model_image = params.get("model_image")
                if not model_image:
                    raise ValueError("model_image required when model_source='image'")
                logger.info(f"Populating MODEL_DATA from image: {model_image}")
                populate_model_from_image(ms_path, field=field, model_image=model_image)

            # Perform calibration solve
            _perform_calibration_solve(ms_path, refant)

            # Extract results
            ktabs = cal_tables_result.get("ktabs", [])
            bptabs = cal_tables_result.get("bptabs", [])
            gtabs = cal_tables_result.get("gtabs", [])
            # prebp_table available in cal_tables_result if needed for debugging

        # Combine all tables
        all_tables = (ktabs[:1] if ktabs else []) + bptabs + gtabs
        logger.info(f"Calibration solve complete. Generated {len(all_tables)} tables:")
        for tab in all_tables:
            logger.info(f"  - {tab}")

        # TEMPORAL TRACKING: Capture flag snapshot after Phase 2 (post-solve, pre-applycal)
        # NOTE: Flags should be UNCHANGED from Phase 1 at this point (solve doesn't change flags)
        try:
            from dsa110_contimg.calibration.flagging_temporal import capture_flag_snapshot

            cal_table_paths = {}
            if ktabs:
                cal_table_paths["K"] = ktabs[0]
            if bptabs:
                cal_table_paths["BP"] = bptabs[0]
            if gtabs:
                cal_table_paths["G"] = gtabs[0]

            phase2_snapshot = capture_flag_snapshot(
                ms_path=str(ms_path),
                phase="phase2_post_solve",
                refant=refant,
                cal_table_paths=cal_table_paths,
            )
            logger.info(
                ":check_mark: Phase 2 flag snapshot captured: %.1f%% overall flagging",
                phase2_snapshot.total_flagged_fraction * 100,
            )
            # Store snapshot for later comparison
            if "_temporal_snapshots" not in params:
                params["_temporal_snapshots"] = {}
            params["_temporal_snapshots"]["phase2"] = phase2_snapshot
        except Exception as e:
            logger.warning(f"Failed to capture Phase 2 flag snapshot: {e}")
            logger.warning("Continuing with calibration (temporal tracking disabled for this run)")

        # Register calibration tables in registry database
        # CRITICAL: Registration is required for CalibrationStage to find tables via registry lookup
        registry_db = context.config.paths.pipeline_db

        try:
            from dsa110_contimg.database.registry import register_and_verify_caltables
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            # Extract time range from MS for validity window
            # Use wider window (±1 hour) to cover observation period, not just single MS
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
            if mid_mjd is None:
                logger.warning(f"Could not extract time range from {ms_path}, using current time")
                from astropy.time import Time

                mid_mjd = Time.now().mjd
                start_mjd = mid_mjd - 1.0 / 24.0  # 1 hour before
                end_mjd = mid_mjd + 1.0 / 24.0  # 1 hour after
            else:
                # Extend validity window to ±1 hour around MS time range
                # This ensures calibration tables are valid for the entire observation period
                window_hours = 1.0
                if start_mjd is None or end_mjd is None:
                    # Fallback: use ±1 hour around mid point
                    start_mjd = mid_mjd - window_hours / 24.0
                    end_mjd = mid_mjd + window_hours / 24.0
                else:
                    # Extend existing window by ±1 hour
                    duration = end_mjd - start_mjd
                    start_mjd = start_mjd - window_hours / 24.0
                    end_mjd = end_mjd + window_hours / 24.0
                    logger.debug(
                        f"Extended validity window from {duration * 24 * 60:.1f} min to "
                        f"{(end_mjd - start_mjd) * 24 * 60:.1f} min (±{window_hours}h)"
                    )

            # Generate set name from MS filename and time
            ms_base = Path(ms_path).stem
            set_name = f"{ms_base}_{mid_mjd:.6f}"

            # Determine table prefix (common prefix of all tables)
            if not all_tables:
                error_msg = "No calibration tables generated to register"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Get common directory and base name
            table_dir = Path(all_tables[0]).parent
            # Extract prefix from first table (e.g., "2025-10-29T13:54:17_0_bpcal" -> "2025-10-29T13:54:17_0")
            first_table_name = Path(all_tables[0]).stem

            # Remove table type suffixes (e.g., "_bpcal", "_gpcal", "_2gcal")
            # Use fallback logic if pattern doesn't match
            prefix_base = re.sub(
                r"_(bpcal|gpcal|gacal|2gcal|kcal|bacal|flux)$",
                "",
                first_table_name,
                flags=re.IGNORECASE,
            )

            # Fallback: If regex didn't change the name, try alternative patterns
            if prefix_base == first_table_name:
                logger.warning(
                    f"Table name '{first_table_name}' doesn't match expected pattern. "
                    f"Trying alternative extraction methods."
                )
                # Try removing common suffixes one by one
                for suffix in [
                    "_bpcal",
                    "_gpcal",
                    "_gacal",
                    "_2gcal",
                    "_kcal",
                    "_bacal",
                    "_flux",
                ]:
                    if first_table_name.lower().endswith(suffix.lower()):
                        prefix_base = first_table_name[: -len(suffix)]
                        logger.info(f"Extracted prefix using suffix removal: {prefix_base}")
                        break

                # Final fallback: use MS path-based prefix
                if prefix_base == first_table_name:
                    logger.warning(
                        f"Could not extract table prefix from '{first_table_name}'. "
                        f"Using MS path-based prefix as fallback."
                    )
                    prefix_base = f"{Path(ms_path).stem}_{field}"

            table_prefix = table_dir / prefix_base

            logger.info(f"Registering calibration tables in registry: {set_name}")
            logger.debug(f"Using table prefix: {table_prefix}")

            # Register and verify tables are discoverable
            # This helper function:
            # - Registers tables (idempotent via upsert)
            # - Verifies tables are discoverable after registration
            # - Retires set if verification fails (rollback)
            registered_paths = register_and_verify_caltables(
                registry_db,
                set_name,
                table_prefix,
                cal_field=field,
                refant=refant,
                valid_start_mjd=start_mjd,
                valid_end_mjd=end_mjd,
                mid_mjd=mid_mjd,
                status="active",
                verify_discoverable=True,
            )

            logger.info(
                f":check_mark: Registered and verified {len(registered_paths)} calibration tables "
                f"in registry (set: {set_name})"
            )

        except Exception as e:
            # Registration failure is CRITICAL - CalibrationStage will fail without registered tables
            error_msg = (
                f"CRITICAL: Failed to register calibration tables in registry: {e}. "
                f"CalibrationStage will not be able to find tables via registry lookup. "
                f"Tables were created but may not be registered."
            )
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

        # Update state repository
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_tables": all_tables,
                        "stage": "calibration_solve",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        log_progress(
            f"Completed calibration solve stage. Generated {len(all_tables)} calibration table(s).",
            start_time_sec,
        )
        return context.with_output("calibration_tables", all_tables)

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate calibration solve outputs."""
        if "calibration_tables" not in context.outputs:
            return False, "calibration_tables not found in outputs"

        caltables = context.outputs["calibration_tables"]
        if not caltables:
            return False, "No calibration tables generated"

        # Validate all tables exist
        missing = [t for t in caltables if not Path(t).exists()]
        if missing:
            return False, f"Calibration tables missing: {missing}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial calibration tables on failure."""
        if "calibration_tables" in context.outputs:
            caltables = context.outputs["calibration_tables"]
            for table_path in caltables:
                table = Path(table_path)
                if table.exists():
                    try:
                        import shutil

                        shutil.rmtree(table, ignore_errors=True)
                        logger.info(f"Cleaned up partial calibration table: {table}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup calibration table {table}: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration_solve"


class CalibrationStage(PipelineStage):
    """Calibration stage: Apply calibration solutions to MS.

    This stage applies calibration solutions (bandpass, gain) to the
    Measurement Set. In the current implementation, this wraps the
    existing calibration service.

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> stage = CalibrationStage(config)
        >>> # Context should have ms_path and calibration_tables
        >>> context = PipelineContext(
        ...     config=config,
        ...     outputs={
        ...         "ms_path": "/data/converted.ms",
        ...         "calibration_tables": {"K": "/data/K.cal", "BA": "/data/BA.cal"}
        ...     }
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute calibration application
        ...     result_context = stage.execute(context)
        ...     # Calibrated MS path available for imaging
        ...     calibrated_ms = result_context.outputs.get("ms_path")
        ...     # Same MS path, now calibrated

    Inputs:
        - `ms_path` (str): Path to uncalibrated Measurement Set (from context.outputs)
        - `calibration_tables` (dict): Calibration tables from CalibrationSolveStage

    Outputs:
        - `ms_path` (str): Path to calibrated Measurement Set (same or updated path)
    """

    def __init__(self, config: PipelineConfig):
        """Initialize calibration stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for calibration."""
        if "ms_path" not in context.outputs:
            return (
                False,
                "ms_path required in context.outputs (conversion must run first)",
            )

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    @require_casa6_python
    @progress_monitor(operation_name="Calibration Application", warn_threshold=300.0)
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration stage.

        Applies calibration from registry (consistent with streaming mode).
        Uses get_active_applylist() to lookup calibration tables by observation time,
        then applies them using apply_to_target() directly.
        """
        import time

        start_time_sec = time.time()
        log_progress("Starting calibration application stage...")

        from pathlib import Path

        from dsa110_contimg.calibration.applycal import apply_to_target
        from dsa110_contimg.database.registry import get_active_applylist
        from dsa110_contimg.utils.time_utils import extract_ms_time_range

        ms_path = context.outputs["ms_path"]
        # Get calibration parameters from context inputs
        params = context.inputs.get("calibration_params", {})
        refant = params.get("refant", "103")
        logger.info(f"Calibration stage: {ms_path}")

        # Check if calibration tables were provided by a previous stage (e.g., CalibrationSolveStage)
        caltables = context.outputs.get("calibration_tables")
        cal_applied = 0
        applylist = []  # Initialize applylist for use in registration

        # If tables provided, use them directly (for workflows that solve calibration)
        if caltables:
            logger.info(f"Using calibration tables from previous stage: {len(caltables)} tables")
            applylist = caltables  # Store for registration
            try:
                apply_to_target(ms_path, field="", gaintables=caltables, calwt=True)
                cal_applied = 1

                # TEMPORAL TRACKING: Capture flag snapshot after Phase 3 (post-applycal)
                try:
                    from dsa110_contimg.calibration.flagging_temporal import capture_flag_snapshot

                    phase3_snapshot = capture_flag_snapshot(
                        ms_path=str(ms_path),
                        phase="phase3_post_applycal",
                        refant=refant,
                        cal_table_paths={"applied": caltables},
                    )
                    logger.info(
                        f":check_mark: Phase 3 flag snapshot captured: {phase3_snapshot.total_flagged_fraction * 100:.1f}% overall flagging"
                    )

                    # Store snapshot for later comparison
                    if "_temporal_snapshots" not in params:
                        params["_temporal_snapshots"] = {}
                    params["_temporal_snapshots"]["phase3"] = phase3_snapshot
                except Exception as e:
                    logger.warning(f"Failed to capture Phase 3 flag snapshot: {e}")

            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e
        else:
            # Lookup tables from registry by observation time (consistent with streaming mode)
            registry_db = context.config.paths.pipeline_db
            if not registry_db.exists():
                # Try default location
                registry_db = Path("/data/dsa110-contimg/state/db/pipeline.sqlite3")
                if not registry_db.exists():
                    error_msg = (
                        f"Cannot apply calibration: No calibration tables provided and "
                        f"registry not found at {registry_db}. Calibration is required for imaging."
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

            # Extract observation time for registry lookup
            mid_mjd = None
            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
            except (OSError, RuntimeError, KeyError):
                # Fallback to current time if extraction fails
                mid_mjd = time.time() / 86400.0

            # Lookup active calibration tables from registry (same as streaming)
            applylist = []
            try:
                applylist = get_active_applylist(registry_db, float(mid_mjd))
            except Exception as e:
                logger.warning(f"Failed to lookup calibration tables from registry: {e}")
                applylist = []

            if not applylist:
                error_msg = (
                    f"Cannot apply calibration: No calibration tables available for {ms_path} "
                    f"(mid MJD: {mid_mjd:.5f}). Calibration is required for downstream imaging."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Apply calibration using apply_to_target() directly (same as streaming)
            logger.info(f"Applying {len(applylist)} calibration tables from registry")
            try:
                apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
                cal_applied = 1

                # TEMPORAL TRACKING: Capture flag snapshot after Phase 3 (post-applycal)
                try:
                    from dsa110_contimg.calibration.flagging_temporal import capture_flag_snapshot

                    phase3_snapshot = capture_flag_snapshot(
                        ms_path=str(ms_path),
                        phase="phase3_post_applycal",
                        refant=refant,
                        cal_table_paths={"applied": applylist},
                    )
                    logger.info(
                        f":check_mark: Phase 3 flag snapshot captured: {phase3_snapshot.total_flagged_fraction * 100:.1f}% overall flagging"
                    )

                    # Store snapshot for later comparison
                    if "_temporal_snapshots" not in params:
                        params["_temporal_snapshots"] = {}
                    params["_temporal_snapshots"]["phase3"] = phase3_snapshot
                except Exception as e:
                    logger.warning(f"Failed to capture Phase 3 flag snapshot: {e}")

            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e

        # TEMPORAL TRACKING: Compare snapshots and diagnose SPW failures
        if (
            "_temporal_snapshots" in params
            and "phase1" in params["_temporal_snapshots"]
            and "phase3" in params["_temporal_snapshots"]
        ):
            try:
                from dsa110_contimg.calibration.flagging_temporal import (
                    compare_flag_snapshots,
                    diagnose_spw_failure,
                    format_comparison_summary,
                )

                phase1_snap = params["_temporal_snapshots"]["phase1"]
                phase3_snap = params["_temporal_snapshots"]["phase3"]

                # Compare snapshots
                comparison = compare_flag_snapshots(phase1_snap, phase3_snap)

                # Log comparison summary
                logger.info("=" * 80)
                logger.info("TEMPORAL FLAGGING ANALYSIS")
                logger.info("=" * 80)
                logger.info(format_comparison_summary(comparison))

                # Diagnose any SPWs that became fully flagged
                if comparison["newly_fully_flagged_spws"]:
                    logger.info("\nDIAGNOSIS of newly fully-flagged SPWs:")
                    logger.info("-" * 80)

                    for failed_spw in comparison["newly_fully_flagged_spws"]:
                        diagnosis = diagnose_spw_failure(phase1_snap, phase3_snap, failed_spw)
                        logger.info(f"\nSPW {failed_spw}:")
                        logger.info(
                            f"  Pre-calibration flagging: {diagnosis['phase1_flagging_pct']:.1f}%"
                        )
                        if diagnosis["refant_phase1_pct"] is not None:
                            logger.info(
                                f"  Pre-calibration refant flagging: {diagnosis['refant_phase1_pct']:.1f}%"
                            )
                        logger.info(
                            f"  Post-applycal flagging: {diagnosis['phase3_flagging_pct']:.1f}%"
                        )
                        logger.info(f"  → CAUSE: {diagnosis['definitive_cause']}")

                    logger.info("=" * 80)

                # Store temporal analysis in params for database storage
                params["_temporal_analysis"] = {
                    "comparison": comparison,
                    "phase1_snapshot": phase1_snap,
                    "phase3_snapshot": phase3_snap,
                }

                # Store in database
                try:
                    from dsa110_contimg.calibration.flagging_temporal import (  # pylint: disable=no-name-in-module
                        store_temporal_analysis_in_database,
                    )

                    products_db = context.config.paths.pipeline_db
                    store_temporal_analysis_in_database(
                        db_path=str(products_db),
                        ms_path=str(ms_path),
                        phase1_snapshot=phase1_snap,
                        phase3_snapshot=phase3_snap,
                        comparison=comparison,
                    )
                except Exception as db_e:
                    logger.warning(f"Failed to store temporal analysis in database: {db_e}")

            except Exception as e:
                logger.warning(f"Failed to perform temporal flagging analysis: {e}")

        # Update MS index (consistent with streaming mode)
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_applied": cal_applied,
                        "stage": "calibration",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Register calibrated MS in data registry (as calibrated_ms type)
        # Move to calibrated directory in the new layout
        if cal_applied:
            try:
                from dsa110_contimg.database.data_registration import (
                    register_pipeline_data,
                )
                from dsa110_contimg.utils.path_utils import (
                    extract_date_from_path,
                    move_ms_to_calibrated,
                )
                from dsa110_contimg.utils.time_utils import extract_ms_time_range

                ms_path_obj = Path(ms_path)

                # Move MS to calibrated directory
                is_calibrator = "calibrator" in str(ms_path_obj).lower() or "calibrators" in str(
                    ms_path_obj
                )
                date_str = extract_date_from_path(ms_path_obj)
                calibrated_ms_path = move_ms_to_calibrated(
                    ms_path_obj,
                    date_str=date_str,
                    is_calibrator=is_calibrator,
                )

                # Update ms_path in context if moved
                if calibrated_ms_path != ms_path_obj:
                    ms_path = str(calibrated_ms_path)
                    ms_path_obj = calibrated_ms_path
                    context.outputs["ms_path"] = ms_path
                    logger.info(f"Moved calibrated MS to: {calibrated_ms_path}")

                # Use MS path as data_id with calibrated_ms prefix
                data_id = f"calibrated_ms_{ms_path_obj.name}"

                # Extract metadata from MS if available
                metadata = {
                    "original_ms_path": str(ms_path_obj),
                    "calibration_applied": True,
                    "calibration_tables": applylist,  # applylist is defined earlier in this function
                }
                try:
                    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
                    if start_mjd:
                        metadata["start_mjd"] = start_mjd
                    if end_mjd:
                        metadata["end_mjd"] = end_mjd
                    if mid_mjd:
                        metadata["mid_mjd"] = mid_mjd
                except Exception as e:
                    logger.debug(f"Could not extract MS time range for metadata: {e}")

                # Use new data type
                data_type = "calibrated_ms"

                register_pipeline_data(
                    data_type=data_type,
                    data_id=data_id,
                    file_path=ms_path_obj,
                    metadata=metadata,
                    auto_publish=True,
                )
                logger.info(f"Registered calibrated MS in data registry: {ms_path}")
            except Exception as e:
                logger.warning(f"Failed to register calibrated MS in data registry: {e}")

        # Hook: Generate calibration quality plots after calibration
        try:
            from dsa110_contimg.qa.pipeline_hooks import (  # pylint: disable=import-error,no-name-in-module
                hook_calibration_complete,
            )

            hook_calibration_complete()
        except Exception as e:
            logger.debug(f"Calibration quality monitoring hook failed: {e}")

        log_progress("Completed calibration application stage.", start_time_sec)
        return context

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate calibration application outputs."""
        if "ms_path" not in context.outputs:
            return False, "ms_path not found in outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file does not exist: {ms_path}"

        # Validate CORRECTED_DATA column exists and has data
        try:
            import casacore.tables as casatables

            table = casatables.table

            with table(ms_path, readonly=True) as tb:
                if "CORRECTED_DATA" not in tb.colnames():
                    return False, "CORRECTED_DATA column missing after calibration"
                if tb.nrows() == 0:
                    return False, "MS has no data rows"
                # Sample to check CORRECTED_DATA is populated
                sample = tb.getcol("CORRECTED_DATA", 0, min(100, tb.nrows()))
                flags = tb.getcol("FLAG", 0, min(100, tb.nrows()))
                unflagged = sample[~flags]
                if len(unflagged) > 0:
                    import numpy as np

                    if np.count_nonzero(np.abs(unflagged) > 1e-10) == 0:
                        return False, "CORRECTED_DATA appears empty after calibration"
        except Exception as e:
            return False, f"Cannot validate calibrated MS: {e}"

        return True, None

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration"


class ImagingStage(PipelineStage):
    """Imaging stage: Create images from calibrated MS.

    This stage runs imaging on the calibrated Measurement Set to produce
    continuum images using CASA's tclean algorithm.

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> stage = ImagingStage(config)
        >>> # Context should have ms_path from previous calibration stage
        >>> context = PipelineContext(
        ...     config=config,
        ...     outputs={"ms_path": "/data/calibrated.ms"}
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute imaging
        ...     result_context = stage.execute(context)
        ...     # Get image path
        ...     image_path = result_context.outputs["image_path"]
        ...     # Image is now available for validation/photometry stages

    Inputs:
        - `ms_path` (str): Path to calibrated Measurement Set (from context.outputs)

    Outputs:
        - `image_path` (str): Path to output FITS image file
    """

    def __init__(self, config: PipelineConfig):
        """Initialize imaging stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for imaging."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    @require_casa6_python
    @progress_monitor(operation_name="Imaging", warn_threshold=1800.0)
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute imaging stage."""
        import time

        start_time_sec = time.time()
        log_progress("Starting imaging stage...")

        import casacore.tables as casatables

        table = casatables.table

        from dsa110_contimg.imaging.cli_imaging import image_ms

        ms_path = context.outputs["ms_path"]
        logger.info(f"Imaging stage: {ms_path}")

        # Check if CORRECTED_DATA exists but is empty (calibration wasn't applied)
        # If so, copy DATA to CORRECTED_DATA so imaging can proceed
        try:
            with table(ms_path, readonly=False) as t:
                if "CORRECTED_DATA" in t.colnames() and t.nrows() > 0:
                    # Sample to check if CORRECTED_DATA is populated
                    sample = t.getcol("CORRECTED_DATA", 0, min(1000, t.nrows()))
                    flags = t.getcol("FLAG", 0, min(1000, t.nrows()))
                    unflagged = sample[~flags]
                    if len(unflagged) > 0 and np.count_nonzero(np.abs(unflagged) > 1e-10) == 0:
                        # CORRECTED_DATA exists but is empty - copy DATA to CORRECTED_DATA
                        logger.info(
                            "CORRECTED_DATA is empty, copying DATA to CORRECTED_DATA for imaging"
                        )
                        data_col = t.getcol("DATA")
                        t.putcol("CORRECTED_DATA", data_col)
                        t.flush()
        except Exception as e:
            logger.warning(f"Could not check/fix CORRECTED_DATA: {e}")

        # Construct output imagename (consistent with streaming mode)
        # Streaming uses: os.path.join(args.output_dir, base + ".img")
        # where base is derived from MS filename (without .ms extension)
        ms_name = Path(ms_path).stem
        output_dir = Path(context.config.paths.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        imagename = str(output_dir / f"{ms_name}.img")

        # Run imaging (consistent with streaming mode)
        image_ms(
            ms_path,
            imagename=imagename,
            field="",  # Use empty string for all fields (same as streaming)
            gridder=context.config.imaging.gridder,
            wprojplanes=context.config.imaging.wprojplanes,
            quality_tier="standard",  # Production quality (same as streaming)
            skip_fits=False,  # Export FITS (same as streaming)
            use_unicat_mask=context.config.imaging.use_unicat_mask,
            mask_radius_arcsec=context.config.imaging.mask_radius_arcsec,
        )

        # Find created image files
        image_paths = []
        for suffix in [".image", ".image.pbcor", ".residual", ".psf", ".pb"]:
            img_path = f"{imagename}{suffix}"
            if Path(img_path).exists():
                image_paths.append(img_path)

        # Primary image path (for output)
        primary_image = f"{imagename}.image"
        if not Path(primary_image).exists():
            # Try FITS if CASA image not found
            fits_image = f"{imagename}.image.fits"
            if Path(fits_image).exists():
                primary_image = fits_image
                logger.info(f"Using FITS image as primary: {primary_image}")
            elif image_paths:
                # Fallback to first available image
                primary_image = image_paths[0]
                logger.warning(
                    f"Primary image not found, using fallback: {primary_image}. "
                    "This may indicate an imaging failure."
                )
            else:
                # No images found - this is a critical failure
                error_msg = (
                    f"Imaging failed: No image files created for {ms_path}. "
                    f"Expected primary image: {imagename}.image"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "imagename": primary_image,
                        "stage": "imaging",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Run catalog-based flux scale validation if enabled
        if context.config.imaging.run_catalog_validation:
            self._run_catalog_validation(
                primary_image, context.config.imaging.catalog_validation_catalog
            )

        # Register image in data registry
        try:
            from dsa110_contimg.database.data_registration import register_pipeline_data

            image_path_obj = Path(primary_image)
            # Use image path as data_id (unique identifier)
            data_id = str(image_path_obj)
            # Extract metadata
            metadata = {
                "ms_path": ms_path,
                "ms_name": ms_name,
                "imagename": imagename,
                "related_images": image_paths,
            }
            # Try to get image metadata if available
            try:
                from casacore.images import image

                with image(str(primary_image)) as img:
                    shape = img.shape()
                    metadata["shape"] = list(shape)
                    metadata["has_data"] = len(shape) > 0 and all(s > 0 for s in shape)
            except Exception as e:
                logger.debug(f"Could not extract image metadata: {e}")

            register_pipeline_data(
                data_type="image",
                data_id=data_id,
                file_path=image_path_obj,
                metadata=metadata,
                auto_publish=True,
            )
            logger.info(f"Registered image in data registry: {primary_image}")
        except Exception as e:
            logger.warning(f"Failed to register image in data registry: {e}")

        log_progress(f"Completed imaging stage. Created image: {primary_image}", start_time_sec)
        return context.with_output("image_path", primary_image)

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate imaging outputs."""
        if "image_path" not in context.outputs:
            return False, "image_path not found in outputs"

        image_path = context.outputs["image_path"]
        if not Path(image_path).exists():
            return False, f"Image file does not exist: {image_path}"

        # Validate image is readable
        try:
            from casacore.images import image

            with image(str(image_path)) as img:
                shape = img.shape()
                if len(shape) == 0 or any(s == 0 for s in shape):
                    return False, f"Image has invalid shape: {shape}"
        except Exception as e:
            return False, f"Cannot validate image: {e}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial image files on failure."""
        if "image_path" in context.outputs:
            image_path = Path(context.outputs["image_path"])
            # Remove all related image files
            base_name = str(image_path).replace(".image", "").replace(".fits", "")
            suffixes = [".image", ".image.pbcor", ".residual", ".psf", ".pb", ".fits"]
            for suffix in suffixes:
                img_file = Path(f"{base_name}{suffix}")
                if img_file.exists():
                    try:
                        import shutil

                        if img_file.is_dir():
                            shutil.rmtree(img_file, ignore_errors=True)
                        else:
                            img_file.unlink()
                        logger.info(f"Cleaned up partial image: {img_file}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup image {img_file}: {e}")

    def _run_catalog_validation(self, image_path: str, catalog: str) -> None:
        """Run catalog-based flux scale validation on image.

        This validates the image flux scale by comparing forced photometry
        at catalog source positions to catalog fluxes. Non-fatal - logs
        warnings but does not fail the pipeline.

        Args:
            image_path: Path to image file (CASA or FITS)
            catalog: Catalog to use for validation ('nvss' or 'vlass')
        """
        from pathlib import Path

        from dsa110_contimg.qa.catalog_validation import validate_flux_scale

        # Find FITS image (prefer PB-corrected)
        fits_image = None

        # Try PB-corrected FITS first
        if image_path.endswith(".image"):
            pbcor_fits = f"{image_path}.pbcor.fits"
            if Path(pbcor_fits).exists():
                fits_image = pbcor_fits
            else:
                # Try regular FITS
                regular_fits = f"{image_path}.fits"
                if Path(regular_fits).exists():
                    fits_image = regular_fits
        elif image_path.endswith(".fits"):
            fits_image = image_path

        if not fits_image or not Path(fits_image).exists():
            logger.warning(
                f"Catalog validation skipped: FITS image not found for {image_path}. "
                "Catalog validation requires FITS format."
            )
            return

        logger.info(
            f"Running catalog-based flux scale validation ({catalog.upper()}) on {fits_image}"
        )

        try:
            result = validate_flux_scale(
                image_path=fits_image,
                catalog=catalog,
                min_snr=5.0,
                flux_range_jy=(0.01, 10.0),
                max_flux_ratio_error=0.2,
            )

            if result.n_matched > 0:
                logger.info(
                    f"Catalog validation ({catalog.upper()}): "
                    f"{result.n_matched} sources matched, "
                    f"flux ratio={result.mean_flux_ratio:.3f}±{result.rms_flux_ratio:.3f}, "
                    f"scale error={result.flux_scale_error * 100:.1f}%"
                )

                if result.has_issues:
                    logger.warning(f"Catalog validation issues: {', '.join(result.issues)}")

                if result.has_warnings:
                    logger.warning(f"Catalog validation warnings: {', '.join(result.warnings)}")
            else:
                logger.warning(
                    f"Catalog validation ({catalog.upper()}): No sources matched. "
                    "This may indicate astrometry issues or insufficient catalog coverage."
                )

        except Exception as e:
            logger.warning(
                f"Catalog validation failed (non-fatal): {e}. "
                "Pipeline will continue, but flux scale was not validated."
            )

    def get_name(self) -> str:
        """Get stage name."""
        return "imaging"


class MosaicStage(PipelineStage):
    """Mosaic stage: Create mosaics from groups of imaged MS files.

    This stage combines multiple 5-minute continuum images into a larger mosaic,
    typically spanning 50 minutes (10 images) with a 2-image overlap between
    consecutive mosaics.

    The stage uses StreamingMosaicManager to:
    1. Group images by time (configurable, default 10 per mosaic)
    2. Validate tile quality and consistency
    3. Create weighted mosaics using optimal overlap handling
    4. Register mosaics in the products database

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> stage = MosaicStage(config)
        >>> # Context should have image paths from previous imaging stages
        >>> context = PipelineContext(
        ...     config=config,
        ...     outputs={
        ...         "image_paths": ["/data/img1.fits", "/data/img2.fits", ...],
        ...         "ms_paths": ["/data/obs1.ms", "/data/obs2.ms", ...]
        ...     }
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute mosaicking
        ...     result_context = stage.execute(context)
        ...     # Get mosaic path
        ...     mosaic_path = result_context.outputs["mosaic_path"]

    Inputs:
        - `image_paths` (List[str]): Paths to input FITS images (from context.outputs)
        - `ms_paths` (List[str], optional): Paths to source MS files for metadata

    Outputs:
        - `mosaic_path` (str): Path to output mosaic FITS file
        - `mosaic_id` (int): Product ID of the mosaic in the database
        - `group_id` (str): Mosaic group identifier
    """

    def __init__(self, config: PipelineConfig):
        """Initialize mosaic stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for mosaicking."""
        # Check for image_paths in outputs
        if "image_paths" not in context.outputs:
            # Also accept single image_path
            if "image_path" not in context.outputs:
                return False, "image_paths or image_path required in context.outputs"

        # Get image paths
        if "image_paths" in context.outputs:
            image_paths = context.outputs["image_paths"]
        else:
            image_paths = [context.outputs["image_path"]]

        if not isinstance(image_paths, list):
            image_paths = [image_paths]

        # Check minimum number of images
        min_images = self.config.mosaic.min_images
        if len(image_paths) < min_images:
            return (
                False,
                f"At least {min_images} images required for mosaic, got {len(image_paths)}",
            )

        # Verify images exist
        missing = [p for p in image_paths if not Path(p).exists()]
        if missing:
            return False, f"Image files not found: {missing[:3]}{'...' if len(missing) > 3 else ''}"

        return True, None

    @require_casa6_python
    @progress_monitor(operation_name="Mosaicking", warn_threshold=600.0)
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute mosaic creation stage.

        Creates a mosaic from the input images using StreamingMosaicManager.

        Args:
            context: Pipeline context with image_paths

        Returns:
            Updated context with mosaic_path, mosaic_id, and group_id
        """
        import time
        from datetime import datetime

        start_time_sec = time.time()
        log_progress("Starting mosaic stage...")

        from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager
        from dsa110_contimg.database import ensure_products_db
        from dsa110_contimg.utils.time_utils import extract_ms_time_range

        # Get image paths
        if "image_paths" in context.outputs:
            image_paths = context.outputs["image_paths"]
        else:
            image_paths = [context.outputs["image_path"]]

        if not isinstance(image_paths, list):
            image_paths = [image_paths]

        logger.info(f"Mosaic stage: Creating mosaic from {len(image_paths)} images")

        # Get MS paths if available (for metadata)
        ms_paths = context.outputs.get("ms_paths", [])
        if not isinstance(ms_paths, list):
            ms_paths = [ms_paths] if ms_paths else []

        # Determine output directories from config
        output_dir = Path(context.config.paths.output_dir)
        mosaic_output_dir = output_dir / "mosaics"
        mosaic_output_dir.mkdir(parents=True, exist_ok=True)

        images_dir = output_dir / "images"
        ms_output_dir = output_dir / "ms"

        # Initialize StreamingMosaicManager
        products_db_path = Path(context.config.paths.products_db)
        registry_db_path = Path(context.config.paths.cal_registry_db)

        try:
            manager = StreamingMosaicManager(
                products_db_path=products_db_path,
                registry_db_path=registry_db_path,
                ms_output_dir=ms_output_dir,
                images_dir=images_dir,
                mosaic_output_dir=mosaic_output_dir,
                ms_per_group=self.config.mosaic.ms_per_mosaic,
            )
        except Exception as e:
            logger.error(f"Failed to initialize StreamingMosaicManager: {e}")
            raise

        # Generate group_id from first image timestamp
        try:
            first_image = Path(image_paths[0])
            # Extract timestamp from image filename (format: YYYY-MM-DDTHH:MM:SS.img-MFS-image.fits)
            timestamp_match = re.match(
                r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})",
                first_image.stem,
            )
            if timestamp_match:
                group_id = f"mosaic_{timestamp_match.group(1)}"
            else:
                group_id = f"mosaic_{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}"
        except (IndexError, AttributeError, OSError):
            group_id = f"mosaic_{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}"

        logger.info(f"Creating mosaic group: {group_id}")

        # Build mosaic using the manager's weighted mosaic builder
        try:
            from dsa110_contimg.mosaic.cli import _build_weighted_mosaic, _ensure_mosaics_table

            # Ensure mosaics table exists
            products_db = ensure_products_db(products_db_path)
            _ensure_mosaics_table(products_db)

            # Build the mosaic
            mosaic_name = group_id.replace("mosaic_", "")
            mosaic_path = _build_weighted_mosaic(
                image_paths=image_paths,
                output_dir=mosaic_output_dir,
                mosaic_name=mosaic_name,
                products_db=products_db,
            )

            if mosaic_path is None:
                raise RuntimeError("Mosaic creation returned None")

            logger.info(f"Mosaic created: {mosaic_path}")

            # Get mosaic_id from database
            cursor = products_db.cursor()
            cursor.execute(
                "SELECT id FROM mosaics WHERE path = ? ORDER BY created_at DESC LIMIT 1",
                (str(mosaic_path),),
            )
            row = cursor.fetchone()
            mosaic_id = row[0] if row else None

        except ImportError:
            # Fallback: Use manager's create_mosaic if cli module not available
            logger.warning("Using fallback mosaic creation via StreamingMosaicManager")

            # Register group with manager
            if ms_paths:
                manager.products_db.execute(
                    """
                    INSERT OR REPLACE INTO mosaic_groups
                    (group_id, ms_paths, created_at, status)
                    VALUES (?, ?, ?, 'pending')
                    """,
                    (group_id, ",".join(str(p) for p in ms_paths), time.time()),
                )
                manager.products_db.commit()

            mosaic_path = manager.create_mosaic(group_id)
            if mosaic_path is None:
                raise RuntimeError(f"Failed to create mosaic for group {group_id}")

            mosaic_id = None

        elapsed = time.time() - start_time_sec
        logger.info(f"Mosaic stage completed in {elapsed:.1f}s: {mosaic_path}")

        # Build result context
        result = context.with_output("mosaic_path", str(mosaic_path))
        result = result.with_output("group_id", group_id)
        if mosaic_id is not None:
            result = result.with_output("mosaic_id", mosaic_id)

        return result

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial mosaic outputs on failure."""
        # Get group_id if available
        group_id = context.outputs.get("group_id")
        if group_id:
            logger.info(f"Cleaning up partial mosaic for group {group_id}")
            # Mark group as failed in database
            try:
                from dsa110_contimg.database import ensure_products_db

                products_db_path = Path(context.config.paths.products_db)
                products_db = ensure_products_db(products_db_path)
                products_db.execute(
                    "UPDATE mosaic_groups SET status = 'failed' WHERE group_id = ?",
                    (group_id,),
                )
                products_db.commit()
            except Exception as e:
                logger.warning(f"Could not mark mosaic group as failed: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "mosaic"


class LightCurveStage(PipelineStage):
    """Light curve stage: Compute variability metrics from photometry measurements.

    This stage queries photometry measurements from the products database and
    computes variability metrics (η, V, σ-deviation) for each source. It then
    updates the variability_stats table and optionally triggers alerts for
    sources exceeding configured thresholds.

    The stage supports two modes:
    1. **Per-mosaic mode**: Compute metrics for sources in a specific mosaic
    2. **Full catalog mode**: Recompute metrics for all sources with sufficient epochs

    Variability metrics computed:
    - **η (eta)**: Weighted variance metric, sensitive to variability accounting for errors
    - **V**: Coefficient of variation (std/mean), fractional variability
    - **σ-deviation**: Maximum deviation from mean in units of std (ESE detection)
    - **χ²/ν**: Reduced chi-squared relative to constant flux model

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> stage = LightCurveStage(config)
        >>> # Context should have photometry outputs from previous stage
        >>> context = PipelineContext(
        ...     config=config,
        ...     outputs={
        ...         "mosaic_path": "/data/mosaics/mosaic_2025-01-01T12:00:00.fits",
        ...         "source_ids": ["NVSS_J123456+420312", "NVSS_J123500+420400"],
        ...     }
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute light curve computation
        ...     result_context = stage.execute(context)
        ...     # Get variability results
        ...     variable_sources = result_context.outputs["variable_sources"]
        ...     ese_candidates = result_context.outputs["ese_candidates"]

    Inputs:
        - `source_ids` (List[str], optional): Specific sources to process
        - `mosaic_path` (str, optional): Mosaic to derive sources from
        - If neither provided, processes all sources with sufficient epochs

    Outputs:
        - `variable_sources` (List[str]): Source IDs flagged as variable
        - `ese_candidates` (List[str]): Source IDs flagged as ESE candidates
        - `metrics_updated` (int): Number of sources with updated metrics
    """

    def __init__(self, config: PipelineConfig):
        """Initialize light curve stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for light curve computation.

        Checks:
        1. Products database exists and is accessible
        2. Photometry table exists
        3. Either source_ids provided OR mosaic_path provided OR sufficient epochs in DB
        """
        # Check products database exists
        products_db_path = Path(context.config.paths.products_db)
        if not products_db_path.exists():
            return False, f"Products database not found: {products_db_path}"

        # Check for source_ids or mosaic_path in context
        has_source_ids = "source_ids" in context.outputs and context.outputs["source_ids"]
        has_mosaic_path = "mosaic_path" in context.outputs and context.outputs["mosaic_path"]

        # If neither provided, we'll process all sources - this is valid
        # but we should warn if database is empty
        if not has_source_ids and not has_mosaic_path:
            logger.info(
                "No source_ids or mosaic_path provided; "
                "will compute metrics for all sources with sufficient epochs"
            )

        return True, None

    @require_casa6_python
    @progress_monitor(operation_name="Light Curve Computation", warn_threshold=120.0)
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute light curve computation stage.

        Queries photometry measurements, computes variability metrics,
        and updates the variability_stats table.

        Args:
            context: Pipeline context with optional source_ids or mosaic_path

        Returns:
            Updated context with variable_sources, ese_candidates, metrics_updated
        """
        import time
        from datetime import datetime

        start_time_sec = time.time()
        log_progress("Starting light curve computation stage...")

        from dsa110_contimg.database import ensure_products_db
        from dsa110_contimg.photometry.variability import (
            calculate_eta_metric,
            calculate_v_metric,
            calculate_sigma_deviation,
        )

        products_db_path = Path(context.config.paths.products_db)
        products_db = ensure_products_db(products_db_path)

        # Get configuration
        lc_config = context.config.light_curve
        min_epochs = lc_config.min_epochs
        eta_threshold = lc_config.eta_threshold
        v_threshold = lc_config.v_threshold
        sigma_threshold = lc_config.sigma_threshold
        use_normalized = lc_config.use_normalized_flux

        # Determine which sources to process
        source_ids = context.outputs.get("source_ids", [])
        mosaic_path = context.outputs.get("mosaic_path")

        if source_ids:
            logger.info(f"Processing {len(source_ids)} specified sources")
        elif mosaic_path:
            # Query sources that have photometry for this mosaic
            logger.info(f"Querying sources with photometry from mosaic: {mosaic_path}")
            cursor = products_db.cursor()
            cursor.execute(
                """
                SELECT DISTINCT source_id FROM photometry
                WHERE mosaic_path = ? OR image_path LIKE ?
                """,
                (mosaic_path, f"%{Path(mosaic_path).stem}%"),
            )
            source_ids = [row[0] for row in cursor.fetchall()]
            logger.info(f"Found {len(source_ids)} sources from mosaic")
        else:
            # Query all sources with sufficient epochs
            logger.info(f"Querying all sources with >= {min_epochs} epochs")
            cursor = products_db.cursor()
            cursor.execute(
                """
                SELECT source_id, COUNT(*) as n_epochs
                FROM photometry
                GROUP BY source_id
                HAVING n_epochs >= ?
                """,
                (min_epochs,),
            )
            source_ids = [row[0] for row in cursor.fetchall()]
            logger.info(f"Found {len(source_ids)} sources with sufficient epochs")

        if not source_ids:
            logger.warning("No sources found for light curve computation")
            result = context.with_output("variable_sources", [])
            result = result.with_output("ese_candidates", [])
            result = result.with_output("metrics_updated", 0)
            return result

        # Ensure variability_stats table exists
        self._ensure_variability_table(products_db)

        # Process each source
        variable_sources = []
        ese_candidates = []
        metrics_updated = 0

        for source_id in source_ids:
            try:
                metrics = self._compute_source_metrics(
                    products_db,
                    source_id,
                    use_normalized=use_normalized,
                    min_epochs=min_epochs,
                )

                if metrics is None:
                    continue

                # Check thresholds
                is_variable = metrics["eta"] > eta_threshold or metrics["v"] > v_threshold
                is_ese_candidate = metrics["sigma_deviation"] > sigma_threshold

                if is_variable:
                    variable_sources.append(source_id)
                if is_ese_candidate:
                    ese_candidates.append(source_id)

                # Update database if configured
                if lc_config.update_database:
                    self._update_variability_stats(products_db, source_id, metrics)
                    metrics_updated += 1

            except Exception as e:
                logger.warning(f"Error computing metrics for {source_id}: {e}")
                continue

        products_db.commit()

        # Trigger alerts if configured
        if lc_config.trigger_alerts and ese_candidates:
            self._trigger_ese_alerts(products_db, ese_candidates)

        elapsed = time.time() - start_time_sec
        logger.info(
            f"Light curve computation completed in {elapsed:.1f}s: "
            f"{metrics_updated} sources updated, "
            f"{len(variable_sources)} variable, "
            f"{len(ese_candidates)} ESE candidates"
        )

        # Build result context
        result = context.with_output("variable_sources", variable_sources)
        result = result.with_output("ese_candidates", ese_candidates)
        result = result.with_output("metrics_updated", metrics_updated)

        return result

    def _ensure_variability_table(self, products_db) -> None:
        """Ensure variability_stats table exists."""
        products_db.execute(
            """
            CREATE TABLE IF NOT EXISTS variability_stats (
                source_id TEXT PRIMARY KEY,
                ra_deg REAL,
                dec_deg REAL,
                nvss_flux_mjy REAL,
                mean_flux_mjy REAL,
                std_flux_mjy REAL,
                chi2_nu REAL,
                eta REAL,
                v REAL,
                sigma_deviation REAL,
                n_epochs INTEGER,
                last_measured_at TEXT,
                last_mjd REAL,
                updated_at TEXT
            )
            """
        )

    def _compute_source_metrics(
        self,
        products_db,
        source_id: str,
        use_normalized: bool = True,
        min_epochs: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """Compute variability metrics for a single source.

        Args:
            products_db: Database connection
            source_id: Source identifier
            use_normalized: Use normalized flux values
            min_epochs: Minimum epochs required

        Returns:
            Dictionary with computed metrics, or None if insufficient data
        """
        import numpy as np
        import pandas as pd
        from dsa110_contimg.photometry.variability import (
            calculate_eta_metric,
            calculate_v_metric,
            calculate_sigma_deviation,
        )

        # Query photometry for this source
        cursor = products_db.cursor()
        flux_col = "normalized_flux_jy" if use_normalized else "flux_jy"
        err_col = "normalized_flux_err_jy" if use_normalized else "flux_err_jy"

        cursor.execute(
            f"""
            SELECT
                source_id, ra_deg, dec_deg, mjd,
                {flux_col} as flux, {err_col} as flux_err,
                nvss_flux_mjy
            FROM photometry
            WHERE source_id = ?
            ORDER BY mjd
            """,
            (source_id,),
        )
        rows = cursor.fetchall()

        if len(rows) < min_epochs:
            return None

        # Build DataFrame
        df = pd.DataFrame(
            rows,
            columns=[
                "source_id",
                "ra_deg",
                "dec_deg",
                "mjd",
                "flux",
                "flux_err",
                "nvss_flux_mjy",
            ],
        )

        # Filter valid measurements
        valid_mask = df["flux"].notna() & df["flux_err"].notna() & (df["flux_err"] > 0)
        df = df[valid_mask]

        if len(df) < min_epochs:
            return None

        # Compute metrics
        fluxes = df["flux"].values
        flux_errs = df["flux_err"].values

        # η metric (weighted variance)
        df_for_eta = df.rename(
            columns={"flux": "normalized_flux_jy", "flux_err": "normalized_flux_err_jy"}
        )
        eta = calculate_eta_metric(df_for_eta)

        # V metric (coefficient of variation)
        v = calculate_v_metric(fluxes)

        # σ-deviation
        sigma_deviation = calculate_sigma_deviation(fluxes)

        # χ²/ν (reduced chi-squared vs constant model)
        mean_flux = np.mean(fluxes)
        chi2 = np.sum(((fluxes - mean_flux) / flux_errs) ** 2)
        dof = len(fluxes) - 1
        chi2_nu = chi2 / dof if dof > 0 else 0.0

        return {
            "ra_deg": float(df["ra_deg"].iloc[0]),
            "dec_deg": float(df["dec_deg"].iloc[0]),
            "nvss_flux_mjy": float(df["nvss_flux_mjy"].iloc[0]) if pd.notna(df["nvss_flux_mjy"].iloc[0]) else None,
            "mean_flux_mjy": float(mean_flux * 1000),  # Convert Jy to mJy
            "std_flux_mjy": float(np.std(fluxes) * 1000),
            "chi2_nu": float(chi2_nu),
            "eta": float(eta),
            "v": float(v),
            "sigma_deviation": float(sigma_deviation),
            "n_epochs": len(df),
            "last_mjd": float(df["mjd"].max()),
        }

    def _update_variability_stats(
        self, products_db, source_id: str, metrics: Dict[str, Any]
    ) -> None:
        """Update variability_stats table for a source."""
        from datetime import datetime

        products_db.execute(
            """
            INSERT OR REPLACE INTO variability_stats
            (source_id, ra_deg, dec_deg, nvss_flux_mjy, mean_flux_mjy, std_flux_mjy,
             chi2_nu, eta, v, sigma_deviation, n_epochs, last_mjd, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                metrics["ra_deg"],
                metrics["dec_deg"],
                metrics.get("nvss_flux_mjy"),
                metrics["mean_flux_mjy"],
                metrics["std_flux_mjy"],
                metrics["chi2_nu"],
                metrics["eta"],
                metrics["v"],
                metrics["sigma_deviation"],
                metrics["n_epochs"],
                metrics["last_mjd"],
                datetime.now().isoformat(),
            ),
        )

    def _trigger_ese_alerts(self, products_db, ese_candidates: List[str]) -> None:
        """Trigger alerts for ESE candidates."""
        from datetime import datetime

        # Ensure alerts table exists
        products_db.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                triggered_at TEXT,
                acknowledged INTEGER DEFAULT 0
            )
            """
        )

        for source_id in ese_candidates:
            products_db.execute(
                """
                INSERT INTO alerts (source_id, alert_type, severity, message, triggered_at)
                VALUES (?, 'ese_candidate', 'warning', ?, ?)
                """,
                (
                    source_id,
                    f"Source {source_id} exceeds sigma deviation threshold - potential ESE candidate",
                    datetime.now().isoformat(),
                ),
            )

        logger.info(f"Triggered {len(ese_candidates)} ESE candidate alerts")

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup on failure - nothing to clean for light curves."""
        logger.info("Light curve stage cleanup - no cleanup needed")

    def get_name(self) -> str:
        """Get stage name."""
        return "light_curve"


class OrganizationStage(PipelineStage):
    """Organization stage: Organize MS files into date-based directory structure.

    Moves MS files into organized subdirectories:
    - Calibrator MS → ms/calibrators/YYYY-MM-DD/
    - Science MS → ms/science/YYYY-MM-DD/
    - Failed MS → ms/failed/YYYY-MM-DD/

    Updates database paths to reflect new locations.

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> stage = OrganizationStage(config)
        >>> # Context should have ms_path or ms_paths from previous stages
        >>> context = PipelineContext(
        ...     config=config,
        ...     outputs={"ms_path": "/data/raw/observation.ms"}
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute organization
        ...     result_context = stage.execute(context)
        ...     # MS file moved to organized location
        ...     organized_path = result_context.outputs.get("ms_path")
        ...     # Path now in: ms/science/2025-01-01/observation.ms

    Inputs:
        - `ms_path` (str) or `ms_paths` (list): MS file(s) to organize (from context.outputs)

    Outputs:
        - `ms_path` (str) or `ms_paths` (list): Updated paths to organized MS files
    """

    def __init__(self, config: PipelineConfig):
        """Initialize organization stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate organization stage prerequisites."""
        if "ms_paths" not in context.outputs and "ms_path" not in context.outputs:
            return False, "No MS files found in context outputs"

        ms_base_dir = Path(context.config.paths.output_dir)
        if not ms_base_dir.exists():
            return False, f"MS base directory does not exist: {ms_base_dir}"

        products_db_path = (
            Path(context.config.paths.products_db)
            if hasattr(context.config.paths, "products_db")
            else None
        )
        if products_db_path and not products_db_path.exists():
            return False, f"Products database does not exist: {products_db_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute organization stage."""
        ms_files = context.outputs.get("ms_paths", [])
        if not ms_files and "ms_path" in context.outputs:
            ms_files = [context.outputs["ms_path"]]

        if not ms_files:
            logger.warning("No MS files to organize")
            return context

        ms_base_dir = Path(context.config.paths.output_dir)
        products_db_path = (
            Path(context.config.paths.products_db)
            if hasattr(context.config.paths, "products_db")
            else None
        )

        if not products_db_path or not products_db_path.exists():
            logger.warning("Products database not available, skipping database updates")
            products_db_path = None

        organized_ms_files = []

        for ms_file in ms_files:
            try:
                ms_path_obj = Path(ms_file)
                if not ms_path_obj.exists():
                    logger.warning(f"MS file does not exist: {ms_file}")
                    organized_ms_files.append(ms_file)
                    continue

                is_calibrator, is_failed = determine_ms_type(ms_path_obj)

                if products_db_path:
                    organized_path = organize_ms_file(
                        ms_path_obj,
                        ms_base_dir,
                        products_db_path,
                        is_calibrator=is_calibrator,
                        is_failed=is_failed,
                        update_database=True,
                    )
                else:
                    # Just get the organized path without moving/updating DB
                    from dsa110_contimg.utils.ms_organization import (
                        get_organized_ms_path,
                    )

                    organized_path = get_organized_ms_path(
                        ms_path_obj,
                        ms_base_dir,
                        is_calibrator=is_calibrator,
                        is_failed=is_failed,
                    )
                    # Move file manually
                    import shutil

                    if ms_path_obj.resolve() != organized_path.resolve():
                        organized_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(ms_path_obj), str(organized_path))
                        logger.info(f"Moved MS file: {ms_file} → {organized_path}")

                organized_ms_files.append(str(organized_path))

            except Exception as e:
                logger.error(f"Failed to organize MS file {ms_file}: {e}", exc_info=True)
                organized_ms_files.append(ms_file)

        organized_ms_path = (
            organized_ms_files[0] if organized_ms_files else context.outputs.get("ms_path")
        )

        return context.with_outputs(
            {
                "ms_path": organized_ms_path,
                "ms_paths": organized_ms_files,
            }
        )

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate organization outputs."""
        ms_paths = context.outputs.get("ms_paths", [])
        if not ms_paths:
            return False, "No organized MS paths in outputs"

        for ms_path in ms_paths:
            if not Path(ms_path).exists():
                return False, f"Organized MS file does not exist: {ms_path}"

        return True, None

    def get_name(self) -> str:
        """Get stage name."""
        return "organization"


class ValidationStage(PipelineStage):
    """Validation stage: Run catalog-based validation on images.

    This stage performs comprehensive validation of images including:
    - Astrometry validation (positional accuracy)
    - Flux scale validation (calibration accuracy)
    - Source counts completeness analysis

    Optionally generates HTML validation reports with diagnostic plots.

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> stage = ValidationStage(config)
        >>> # Context should have image_path from imaging stage
        >>> context = PipelineContext(
        ...     config=config,
        ...     outputs={"image_path": "/data/image.fits"}
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute validation
        ...     result_context = stage.execute(context)
        ...     # Get validation results
        ...     validation_results = result_context.outputs["validation_results"]
        ...     # Results include: status, metrics, report_path
        ...     assert validation_results["status"] in ["passed", "warning", "failed"]

    Inputs:
        - `image_path` (str): Path to FITS image file (from context.outputs)

    Outputs:
        - `validation_results` (dict): Validation results with status, metrics, and report_path
    """

    def __init__(self, config: PipelineConfig):
        """Initialize validation stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for validation."""
        if not self.config.validation.enabled:
            return False, "Validation stage is disabled"

        if "image_path" not in context.outputs:
            return False, "image_path required in context.outputs"

        image_path = context.outputs["image_path"]
        if not Path(image_path).exists():
            return False, f"Image file does not exist: {image_path}"

        return True, None

    @progress_monitor(operation_name="Image Validation", warn_threshold=300.0)
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute validation stage."""
        import time

        start_time_sec = time.time()
        log_progress("Starting image validation stage...")

        from dsa110_contimg.qa.catalog_validation import (
            run_full_validation,
        )

        image_path = context.outputs["image_path"]
        logger.info(f"Validation stage: {image_path}")

        # Find FITS image (prefer PB-corrected)
        fits_image = None

        # Try PB-corrected FITS first
        if image_path.endswith(".image"):
            pbcor_fits = f"{image_path}.pbcor.fits"
            if Path(pbcor_fits).exists():
                fits_image = pbcor_fits
            else:
                # Try regular FITS
                regular_fits = f"{image_path}.fits"
                if Path(regular_fits).exists():
                    fits_image = regular_fits
        elif image_path.endswith(".fits"):
            fits_image = image_path

        if not fits_image or not Path(fits_image).exists():
            logger.warning(
                f"Validation skipped: FITS image not found for {image_path}. "
                "Validation requires FITS format."
            )
            log_progress("Validation stage skipped (no FITS image found).", start_time_sec)
            return context

        validation_config = self.config.validation
        catalog = validation_config.catalog
        validation_types = validation_config.validation_types

        logger.info(
            f"Running catalog-based validation ({catalog.upper()}) on {fits_image}. "
            f"Validation types: {', '.join(validation_types)}"
        )

        try:
            # Prepare HTML report path if needed
            html_report_path = None
            if validation_config.generate_html_report:
                output_dir = Path(context.config.paths.output_dir) / "qa" / "reports"
                output_dir.mkdir(parents=True, exist_ok=True)
                image_name = Path(fits_image).stem
                html_report_path = str(output_dir / f"{image_name}_validation_report.html")

            # Run full validation (all types) and optionally generate HTML report
            astrometry_result, flux_scale_result, source_counts_result = run_full_validation(
                image_path=fits_image,
                catalog=catalog,
                validation_types=validation_types,
                generate_html=validation_config.generate_html_report,
                html_output_path=html_report_path,
            )

            if html_report_path:
                logger.info(f"HTML validation report generated: {html_report_path}")
                context = context.with_output("validation_report_path", html_report_path)

            # Log validation results
            if astrometry_result:
                logger.info(
                    f"Astrometry validation: {astrometry_result.n_matched} matched, "
                    f'RMS offset: {astrometry_result.rms_offset_arcsec:.2f}"'
                    if astrometry_result.rms_offset_arcsec
                    else "N/A"
                )

            if flux_scale_result:
                logger.info(
                    f"Flux scale validation: Mean ratio: {flux_scale_result.mean_flux_ratio:.3f}, "
                    f"Error: {flux_scale_result.flux_scale_error * 100:.1f}%"
                    if flux_scale_result.mean_flux_ratio and flux_scale_result.flux_scale_error
                    else "N/A"
                )

            if source_counts_result:
                logger.info(
                    f"Source counts validation: Completeness: {source_counts_result.completeness * 100:.1f}%"
                    if source_counts_result.completeness
                    else "N/A"
                )

            # Store validation results in context
            if astrometry_result:
                context = context.with_output("astrometry_result", astrometry_result)
            if flux_scale_result:
                context = context.with_output("flux_scale_result", flux_scale_result)
            if source_counts_result:
                context = context.with_output("source_counts_result", source_counts_result)

        except Exception as e:
            # Validation failures are non-fatal - log warning but continue
            logger.warning(f"Validation failed: {e}", exc_info=True)

        log_progress("Completed image validation stage.", start_time_sec)
        return context

    def get_name(self) -> str:
        """Get stage name."""
        return "validation"


class CrossMatchStage(PipelineStage):
    """Cross-match stage: Match detected sources with reference catalogs.

    This stage cross-matches detected sources from images with reference catalogs
    (NVSS, FIRST, RACS) to:
    - Identify known sources
    - Calculate astrometric offsets
    - Calculate flux scale corrections
    - Store cross-match results in database

    The stage supports both basic (nearest neighbor) and advanced (all matches)
    matching methods.

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> config.crossmatch.enabled = True
        >>> stage = CrossMatchStage(config)
        >>> # Context should have detected_sources or image_path
        >>> context = PipelineContext(
        ...     config=config,
        ...     outputs={
        ...         "image_path": "/data/image.fits",
        ...         "detected_sources": pd.DataFrame([...])  # Optional
        ...     }
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute cross-matching
        ...     result_context = stage.execute(context)
        ...     # Get cross-match results
        ...     crossmatch_results = result_context.outputs["crossmatch_results"]
        ...     # Results include matches, offsets, flux scales

    Inputs:
        - `detected_sources` (DataFrame): Detected sources from photometry/validation
        - `image_path` (str): Path to image (used if detected_sources not available)

    Outputs:
        - `crossmatch_results` (dict): Cross-match results with matches, offsets, flux scales
    """

    def __init__(self, config: PipelineConfig):
        """Initialize cross-match stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for cross-matching."""
        if not self.config.crossmatch.enabled:
            return False, "Cross-match stage is disabled"

        # Need detected sources from previous stage (photometry or validation)
        if "detected_sources" not in context.outputs:
            # Try to get from photometry or validation outputs
            if (
                "photometry_results" not in context.outputs
                and "validation_results" not in context.outputs
            ):
                return False, "No detected sources found in context outputs"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute cross-match stage.

        Args:
            context: Pipeline context

        Returns:
            Updated context with cross-match results
        """

        from dsa110_contimg.catalog.crossmatch import (
            calculate_flux_scale,
            calculate_positional_offsets,
            identify_duplicate_catalog_sources,
            multi_catalog_match,
        )
        from dsa110_contimg.catalog.query import query_sources
        from dsa110_contimg.qa.catalog_validation import extract_sources_from_image

        if not self.config.crossmatch.enabled:
            logger.info("Cross-match stage is disabled, skipping")
            return context.with_output("crossmatch_status", "disabled")

        logger.info("Starting cross-match stage...")

        # Get detected sources
        detected_sources = None
        if "detected_sources" in context.outputs:
            detected_sources = context.outputs["detected_sources"]
        elif "photometry_results" in context.outputs:
            # Extract sources from photometry results
            photometry_results = context.outputs["photometry_results"]
            if isinstance(photometry_results, pd.DataFrame):
                detected_sources = photometry_results
        elif "image_path" in context.outputs:
            # Extract sources from image
            image_path = context.outputs["image_path"]
            detected_sources = extract_sources_from_image(
                image_path, min_snr=self.config.validation.min_snr
            )
        else:
            logger.warning("No detected sources found, skipping cross-match")
            return context.with_output("crossmatch_status", "skipped_no_sources")

        if detected_sources is None or len(detected_sources) == 0:
            logger.warning("No detected sources to cross-match")
            return context.with_output("crossmatch_status", "skipped_no_sources")

        # Get image center for catalog querying
        ra_center = detected_sources["ra_deg"].median()
        dec_center = detected_sources["dec_deg"].median()

        # Query reference catalogs
        catalog_types = self.config.crossmatch.catalog_types
        radius_arcsec = self.config.crossmatch.radius_arcsec
        method = self.config.crossmatch.method

        # Step 1: Query all catalogs and prepare for multi-catalog matching
        catalog_data_dict = {}
        catalog_sources_dict = {}

        for catalog_type in catalog_types:
            try:
                # Validate catalog coverage before querying
                is_valid, warning = validate_catalog_choice(
                    catalog_type=catalog_type, ra_deg=ra_center, dec_deg=dec_center
                )
                if not is_valid:
                    logger.info(
                        f"Skipping {catalog_type.upper()}: {warning}"
                    )
                    continue

                logger.info(f"Querying {catalog_type.upper()} catalog...")

                # Query catalog sources
                catalog_sources = query_sources(
                    catalog_type=catalog_type,
                    ra_center=ra_center,
                    dec_center=dec_center,
                    radius_deg=1.5,  # Query within 1.5 degrees
                )

                if catalog_sources is None or len(catalog_sources) == 0:
                    logger.warning(f"No {catalog_type.upper()} sources found in field")
                    continue

                catalog_sources_dict[catalog_type] = catalog_sources

                # Prepare data for multi_catalog_match
                catalog_data_dict[catalog_type] = {
                    "ra": catalog_sources["ra_deg"].values,
                    "dec": catalog_sources["dec_deg"].values,
                }
                if "flux_mjy" in catalog_sources.columns:
                    catalog_data_dict[catalog_type]["flux"] = catalog_sources["flux_mjy"].values
                if "id" in catalog_sources.columns:
                    catalog_data_dict[catalog_type]["id"] = catalog_sources["id"].values
                else:
                    # Generate IDs from index
                    catalog_data_dict[catalog_type]["id"] = [
                        f"{catalog_type}_{i}" for i in range(len(catalog_sources))
                    ]

            except Exception as e:
                logger.error(f"Error querying {catalog_type} catalog: {e}", exc_info=True)
                continue

        if len(catalog_data_dict) == 0:
            logger.warning("No catalogs available for cross-matching")
            return context.with_output("crossmatch_status", "no_catalogs")

        # Step 2: Use multi_catalog_match to find best matches across all catalogs
        logger.info("Performing multi-catalog matching...")
        multi_match_results = multi_catalog_match(
            detected_ra=detected_sources["ra_deg"].values,
            detected_dec=detected_sources["dec_deg"].values,
            catalogs=catalog_data_dict,
            radius_arcsec=radius_arcsec,
        )

        # Step 3: Build individual catalog matches from multi-catalog results
        all_matches = {}
        all_offsets = {}
        all_flux_scales = {}

        for catalog_type in catalog_types:
            if catalog_type not in catalog_sources_dict:
                continue

            catalog_sources = catalog_sources_dict[catalog_type]

            # Extract matches for this catalog from multi-catalog results
            matched_col = f"{catalog_type}_matched"
            if matched_col not in multi_match_results.columns:
                logger.info(f"No matches found with {catalog_type.upper()}")
                continue

            matched_mask = multi_match_results[matched_col]
            matched_indices = matched_mask[matched_mask].index

            if len(matched_indices) == 0:
                logger.info(f"No matches found with {catalog_type.upper()}")
                continue

            # Build matches DataFrame for this catalog
            matches_list = []
            for detected_idx in matched_indices:
                catalog_idx = int(multi_match_results.loc[detected_idx, f"{catalog_type}_idx"])
                separation = float(
                    multi_match_results.loc[detected_idx, f"{catalog_type}_separation_arcsec"]
                )

                # Filter by separation limits
                min_sep = self.config.crossmatch.min_separation_arcsec
                max_sep = self.config.crossmatch.max_separation_arcsec
                if not (min_sep <= separation <= max_sep):
                    continue

                detected_row = detected_sources.iloc[detected_idx]
                catalog_row = catalog_sources.iloc[catalog_idx]

                # Calculate offsets
                dra_arcsec = (detected_row["ra_deg"] - catalog_row["ra_deg"]) * 3600.0
                ddec_arcsec = (detected_row["dec_deg"] - catalog_row["dec_deg"]) * 3600.0

                match_dict = {
                    "detected_idx": detected_idx,
                    "catalog_idx": catalog_idx,
                    "separation_arcsec": separation,
                    "dra_arcsec": dra_arcsec,
                    "ddec_arcsec": ddec_arcsec,
                    "ra_deg": detected_row["ra_deg"],
                    "dec_deg": detected_row["dec_deg"],
                    "catalog_ra_deg": catalog_row["ra_deg"],
                    "catalog_dec_deg": catalog_row["dec_deg"],
                }

                # Add flux information if available
                if "flux_jy" in detected_row:
                    match_dict["detected_flux"] = detected_row["flux_jy"]
                if "flux_mjy" in catalog_row:
                    # Convert to Jy
                    match_dict["catalog_flux"] = catalog_row["flux_mjy"] / 1000.0
                    if "detected_flux" in match_dict:
                        match_dict["flux_ratio"] = (
                            match_dict["detected_flux"] / match_dict["catalog_flux"]
                        )

                # Add catalog source ID
                if "id" in catalog_row:
                    match_dict["catalog_source_id"] = str(catalog_row["id"])
                else:
                    match_dict["catalog_source_id"] = f"{catalog_type}_{catalog_idx}"

                matches_list.append(match_dict)

            if len(matches_list) == 0:
                logger.info(f"No matches within separation limits for {catalog_type.upper()}")
                continue

            matches = pd.DataFrame(matches_list)
            matches["catalog_type"] = catalog_type
            matches["match_method"] = method
            all_matches[catalog_type] = matches

            # Calculate offsets
            try:
                dra_median, ddec_median, dra_madfm, ddec_madfm = calculate_positional_offsets(
                    matches
                )
                all_offsets[catalog_type] = {
                    "dra_median_arcsec": dra_median.to(u.arcsec).value,  # pylint: disable=no-member
                    "ddec_median_arcsec": ddec_median.to(
                        u.arcsec
                    ).value,  # pylint: disable=no-member
                    "dra_madfm_arcsec": dra_madfm.to(u.arcsec).value,  # pylint: disable=no-member
                    "ddec_madfm_arcsec": ddec_madfm.to(u.arcsec).value,  # pylint: disable=no-member
                }
                logger.info(
                    f"{catalog_type.upper()} offsets: "
                    f"RA={dra_median.to(u.arcsec).value:.2f}±{dra_madfm.to(u.arcsec).value:.2f} arcsec, "  # pylint: disable=no-member
                    f"Dec={ddec_median.to(u.arcsec).value:.2f}±{ddec_madfm.to(u.arcsec).value:.2f} arcsec"  # pylint: disable=no-member
                )
            except Exception as e:
                logger.warning(f"Error calculating offsets for {catalog_type}: {e}")

            # Calculate flux scale if flux information available
            if "flux_ratio" in matches.columns:
                try:
                    flux_corr, flux_ratio = calculate_flux_scale(matches)
                    all_flux_scales[catalog_type] = {
                        "flux_correction_factor": flux_corr.nominal_value,
                        "flux_correction_error": flux_corr.std_dev,
                        "flux_ratio": flux_ratio.nominal_value,
                        "flux_ratio_error": flux_ratio.std_dev,
                    }
                    logger.info(
                        f"{catalog_type.upper()} flux scale: "
                        f"correction={flux_corr.nominal_value:.3f}±{flux_corr.std_dev:.3f}"
                    )
                except Exception as e:
                    logger.warning(f"Error calculating flux scale for {catalog_type}: {e}")

        # Step 4: Identify duplicate catalog sources and assign master IDs
        logger.info("Identifying duplicate catalog sources...")
        master_catalog_ids = identify_duplicate_catalog_sources(
            catalog_matches=all_matches,
            deduplication_radius_arcsec=2.0,  # 2 arcsec for deduplication
        )

        # Step 5: Store matches in database with master catalog IDs
        if self.config.crossmatch.store_in_database:
            for catalog_type, matches in all_matches.items():
                try:
                    self._store_matches_in_database(
                        matches, catalog_type, method, context, master_catalog_ids
                    )
                except Exception as e:
                    logger.warning(f"Error storing matches in database: {e}", exc_info=True)

        # Step 6: Calculate spectral indices from multi-catalog matches
        spectral_indices_calculated = 0
        if self.config.crossmatch.calculate_spectral_indices and len(all_matches) >= 2:
            try:
                logger.info("Calculating spectral indices from multi-catalog matches...")
                spectral_indices_calculated = self._calculate_spectral_indices(
                    all_matches, catalog_sources_dict, multi_match_results
                )
                logger.info(f"Calculated {spectral_indices_calculated} spectral indices")
            except Exception as e:
                logger.warning(f"Error calculating spectral indices: {e}", exc_info=True)

        # Prepare results
        crossmatch_results = {
            "n_catalogs": len(all_matches),
            "catalog_types": list(all_matches.keys()),
            "matches": all_matches,
            "offsets": all_offsets,
            "flux_scales": all_flux_scales,
            "method": method,
            "radius_arcsec": radius_arcsec,
            "spectral_indices_calculated": spectral_indices_calculated,
        }

        logger.info(
            f"Cross-match complete: {len(all_matches)} catalogs matched, "
            f"{sum(len(m) for m in all_matches.values())} total matches"
        )

        return context.with_output("crossmatch_results", crossmatch_results)

    def _store_matches_in_database(
        self,
        matches: pd.DataFrame,
        catalog_type: str,
        method: str,
        context: PipelineContext,
        master_catalog_ids: Optional[Dict[str, str]] = None,
    ) -> None:
        """Store cross-match results in database.

        Args:
            matches: DataFrame with cross-matched sources
            catalog_type: Type of catalog used
            method: Matching method used
            context: Pipeline context
            master_catalog_ids: Dictionary mapping catalog entries to master IDs
        """
        import time

        from dsa110_contimg.database import ensure_products_db

        products_db = self.config.paths.products_db
        conn = ensure_products_db(products_db)
        cursor = conn.cursor()

        created_at = time.time()

        # Prepare match quality based on separation
        def get_match_quality(sep_arcsec: float) -> str:
            if sep_arcsec < 2.0:
                return "excellent"
            elif sep_arcsec < 5.0:
                return "good"
            elif sep_arcsec < 10.0:
                return "fair"
            else:
                return "poor"

        # Insert or replace matches (UNIQUE constraint on source_id, catalog_type)
        for _, match in matches.iterrows():
            detected_idx = int(match["detected_idx"])
            catalog_idx = int(match["catalog_idx"])
            separation = match["separation_arcsec"]
            dra = match.get("dra_arcsec")
            ddec = match.get("ddec_arcsec")
            detected_flux = match.get("detected_flux")
            catalog_flux = match.get("catalog_flux")
            flux_ratio = match.get("flux_ratio")

            # Get source_id from detected sources
            # Try to get from context outputs first
            source_id = None
            if "detected_sources" in context.outputs:
                detected_sources = context.outputs["detected_sources"]
                if detected_idx < len(detected_sources):
                    source_id = detected_sources.iloc[detected_idx].get("source_id")

            # Fallback: generate source_id from index if not available
            if source_id is None:
                source_id = f"src_{detected_idx}"

            # Get catalog_source_id
            catalog_source_id = match.get("catalog_source_id")
            if catalog_source_id is None and "catalog_id" in match:
                catalog_source_id = str(match["catalog_id"])
            if catalog_source_id is None:
                catalog_source_id = f"{catalog_type}_{catalog_idx}"

            # Get master catalog ID
            master_catalog_id = None
            if master_catalog_ids:
                entry_key = f"{catalog_type}:{catalog_source_id}"
                master_catalog_id = master_catalog_ids.get(entry_key)

            match_quality = get_match_quality(separation)

            # Use INSERT OR REPLACE to handle UNIQUE constraint
            cursor.execute(
                """
                INSERT OR REPLACE INTO cross_matches (
                    source_id, catalog_type, catalog_source_id,
                    separation_arcsec, dra_arcsec, ddec_arcsec,
                    detected_flux_jy, catalog_flux_jy, flux_ratio,
                    match_quality, match_method, master_catalog_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    catalog_type,
                    catalog_source_id,
                    separation,
                    dra,
                    ddec,
                    detected_flux,
                    catalog_flux,
                    flux_ratio,
                    match_quality,
                    method,
                    master_catalog_id,
                    created_at,
                ),
            )

        conn.commit()
        conn.close()

        logger.info(f"Stored {len(matches)} cross-matches in database for {catalog_type}")

    def _calculate_spectral_indices(
        self,
        all_matches: Dict[str, pd.DataFrame],
        catalog_sources_dict: Dict[str, pd.DataFrame],
        multi_match_results: pd.DataFrame,
    ) -> int:
        """Calculate spectral indices from multi-catalog matches.

        Args:
            all_matches: Dictionary mapping catalog type to matches DataFrame
            catalog_sources_dict: Dictionary mapping catalog type to catalog sources DataFrame
            multi_match_results: Multi-catalog match results

        Returns:
            Number of spectral indices calculated
        """
        from dsa110_contimg.catalog.spectral_index import (
            calculate_and_store_from_catalogs,
            create_spectral_indices_table,
        )

        # Ensure spectral indices table exists
        db_path = self.config.paths.products_db
        create_spectral_indices_table(db_path)

        # Catalog frequency mapping [GHz]
        catalog_frequencies = {
            "nvss": 1.4,
            "first": 1.4,
            "racs": 0.888,
            "vlass": 3.0,
            "dsa110": 1.4,  # DSA-110 operates at 1.4 GHz
        }

        count = 0

        # For each source with multi-catalog matches, calculate spectral indices
        for detected_idx in multi_match_results.index:
            # Find which catalogs matched this source
            matched_catalogs = []
            for cat_type in all_matches.keys():
                matched_col = f"{cat_type}_matched"
                if matched_col in multi_match_results.columns:
                    if multi_match_results.loc[detected_idx, matched_col]:
                        matched_catalogs.append(cat_type)

            # Need at least 2 catalogs for spectral index
            if len(matched_catalogs) < 2:
                continue

            # Build catalog_fluxes dictionary
            catalog_fluxes = {}
            source_ra = None
            source_dec = None

            for cat_type in matched_catalogs:
                # Get catalog index for this match
                catalog_idx = int(multi_match_results.loc[detected_idx, f"{cat_type}_idx"])

                # Get catalog source
                if cat_type not in catalog_sources_dict:
                    continue

                catalog_sources = catalog_sources_dict[cat_type]
                if catalog_idx >= len(catalog_sources):
                    continue

                catalog_row = catalog_sources.iloc[catalog_idx]

                # Get flux and frequency
                flux_mjy = catalog_row.get("flux_mjy")
                if flux_mjy is None or flux_mjy <= 0:
                    continue

                freq_ghz = catalog_frequencies.get(cat_type.lower())
                if freq_ghz is None:
                    continue

                # Get flux error (optional)
                flux_err_mjy = catalog_row.get("flux_err_mjy", flux_mjy * 0.1)  # 10% default

                catalog_fluxes[cat_type.upper()] = (freq_ghz, flux_mjy, flux_err_mjy)

                # Get source coordinates
                if source_ra is None:
                    source_ra = catalog_row.get("ra_deg")
                    source_dec = catalog_row.get("dec_deg")

            # Calculate spectral indices if we have valid data
            if len(catalog_fluxes) >= 2 and source_ra is not None and source_dec is not None:
                source_id = f"J{source_ra:.5f}{source_dec:+.5f}".replace(".", "")

                try:
                    record_ids = calculate_and_store_from_catalogs(
                        source_id=source_id,
                        ra_deg=source_ra,
                        dec_deg=source_dec,
                        catalog_fluxes=catalog_fluxes,
                        db_path=db_path,
                    )
                    count += len(record_ids)
                except Exception as e:
                    logger.debug(f"Error calculating spectral index for {source_id}: {e}")

        return count

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup on failure (nothing to clean up for cross-match)."""
        pass

    def get_name(self) -> str:
        """Get stage name."""
        return "cross_match"


class AdaptivePhotometryStage(PipelineStage):
    """Adaptive binning photometry stage: Measure photometry using adaptive channel binning.

    This stage runs adaptive binning photometry on sources in the field, either
    from a provided list of coordinates or by querying the NVSS catalog.

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> config.photometry.enabled = True
        >>> stage = AdaptivePhotometryStage(config)
        >>> # Context should have ms_path and optionally image_path
        >>> context = PipelineContext(
        ...     config=config,
        ...     outputs={
        ...         "ms_path": "/data/calibrated.ms",
        ...         "image_path": "/data/image.fits"  # Optional
        ...     }
        ... )
        >>> # Validate prerequisites
        >>> is_valid, error = stage.validate(context)
        >>> if is_valid:
        ...     # Execute adaptive photometry
        ...     result_context = stage.execute(context)
        ...     # Get photometry results
        ...     photometry_results = result_context.outputs["photometry_results"]
        ...     # Results include flux measurements with adaptive binning

    Inputs:
        - `ms_path` (str): Path to calibrated Measurement Set (from context.outputs)
        - `image_path` (str): Optional path to image for source detection

    Outputs:
        - `photometry_results` (DataFrame): Photometry results with adaptive binning
    """

    def __init__(self, config: PipelineConfig):
        """Initialize adaptive photometry stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for adaptive photometry."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        if not self.config.photometry.enabled:
            return False, "Adaptive photometry stage is disabled in configuration"

        return True, None

    @require_casa6_python
    @progress_monitor(operation_name="Adaptive Photometry", warn_threshold=600.0)
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute adaptive photometry stage."""
        import time

        start_time_sec = time.time()
        log_progress("Starting adaptive photometry stage...")

        from dsa110_contimg.photometry.adaptive_binning import AdaptiveBinningConfig
        from dsa110_contimg.photometry.adaptive_photometry import (
            measure_with_adaptive_binning,
        )

        ms_path = context.outputs["ms_path"]
        logger.info(f"Adaptive photometry stage: {ms_path}")

        # Get source coordinates
        sources = self._get_source_coordinates(context, ms_path)
        if not sources:
            logger.warning("No sources found for adaptive photometry - skipping stage")
            return context

        # Create adaptive binning config
        config = AdaptiveBinningConfig(
            target_snr=self.config.photometry.target_snr,
            max_width=self.config.photometry.max_width,
        )

        # Prepare imaging kwargs
        imaging_kwargs = {
            "imsize": self.config.photometry.imsize,
            "quality_tier": self.config.photometry.quality_tier,
            "backend": self.config.photometry.backend,
            "parallel": self.config.photometry.parallel,
            "max_workers": self.config.photometry.max_workers,
            "serialize_ms_access": self.config.photometry.serialize_ms_access,
        }

        # Create output directory for adaptive photometry results
        output_dir = Path(context.config.paths.output_dir) / "adaptive_photometry"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run adaptive binning for each source
        results = []
        for i, (ra_deg, dec_deg) in enumerate(sources):
            logger.info(
                f"Running adaptive binning for source {i + 1}/{len(sources)}: RA={ra_deg:.6f}, Dec={dec_deg:.6f}"
            )

            source_output_dir = output_dir / f"source_{i + 1:03d}"
            source_output_dir.mkdir(parents=True, exist_ok=True)

            try:
                result = measure_with_adaptive_binning(
                    ms_path=ms_path,
                    ra_deg=ra_deg,
                    dec_deg=dec_deg,
                    output_dir=source_output_dir,
                    config=config,
                    **imaging_kwargs,
                )

                if result.success:
                    logger.info(
                        f"Source {i + 1}: Found {len(result.detections)} detection(s) "
                        f"(best SNR: {max([d.snr for d in result.detections], default=0.0):.2f})"
                    )
                    results.append(
                        {
                            "ra_deg": ra_deg,
                            "dec_deg": dec_deg,
                            "n_detections": len(result.detections),
                            "detections": [
                                {
                                    "spw_ids": det.channels,
                                    "flux_jy": det.flux_jy,
                                    "rms_jy": det.rms_jy,
                                    "snr": det.snr,
                                    "center_freq_mhz": det.center_freq_mhz,
                                    "bin_width": det.bin_width,
                                }
                                for det in result.detections
                            ],
                            "output_dir": str(source_output_dir),
                        }
                    )
                else:
                    logger.warning(
                        f"Source {i + 1}: Adaptive binning failed: {result.error_message}"
                    )
            except Exception as e:
                logger.error(f"Source {i + 1}: Error during adaptive binning: {e}", exc_info=True)

        # Store results in context
        photometry_results = {
            "n_sources": len(sources),
            "n_successful": len(results),
            "results": results,
            "output_dir": str(output_dir),
        }

        logger.info(
            f"Adaptive photometry complete: {len(results)}/{len(sources)} sources successful"
        )

        log_progress(
            f"Completed adaptive photometry stage. Measured {len(photometry_results)} source(s).",
            start_time_sec,
        )
        return context.with_output("adaptive_photometry_results", photometry_results)

    def _get_source_coordinates(
        self, context: PipelineContext, ms_path: str
    ) -> List[Tuple[float, float]]:
        """Get source coordinates for adaptive photometry.

        Args:
            context: Pipeline context
            ms_path: Path to Measurement Set

        Returns:
            List of (ra_deg, dec_deg) tuples
        """
        # If sources are provided in config, use them
        if self.config.photometry.sources:
            return [(src["ra"], src["dec"]) for src in self.config.photometry.sources]

        # Otherwise, query NVSS catalog for sources in the field
        try:
            import casacore.tables as casatables
            import numpy as np

            table = casatables.table

            # Get field center from MS
            with table(ms_path) as t:
                field_table = t.getkeyword("FIELD")
                if isinstance(field_table, dict) and "PHASE_DIR" in field_table:
                    phase_dir = field_table["PHASE_DIR"]
                    if len(phase_dir) > 0 and len(phase_dir[0]) > 0:
                        # Phase direction is in radians, convert to degrees
                        ra_rad = phase_dir[0][0]
                        dec_rad = phase_dir[0][1]
                        ra_deg = np.degrees(ra_rad)
                        dec_deg = np.degrees(dec_rad)
                    else:
                        logger.warning("Could not extract field center from MS - using default")
                        return []
                else:
                    logger.warning("Could not extract field center from MS - using default")
                    return []

            # Query NVSS catalog using optimized SQLite backend (or CSV fallback)
            from dsa110_contimg.catalog.query import query_sources

            max_radius_deg = 1.0
            df = query_sources(
                catalog_type=self.config.photometry.catalog,
                ra_center=ra_deg,
                dec_center=dec_deg,
                radius_deg=max_radius_deg,
                min_flux_mjy=self.config.photometry.min_flux_mjy,
            )

            # Extract coordinates as list of tuples
            if len(df) > 0:
                sources = list(zip(df["ra_deg"].to_numpy(), df["dec_deg"].to_numpy()))
            else:
                sources = []
            logger.info(
                f"Found {len(sources)} {self.config.photometry.catalog.upper()} sources in field "
                f"(center: RA={ra_deg:.6f}, Dec={dec_deg:.6f}, "
                f"radius={max_radius_deg} deg, min_flux={self.config.photometry.min_flux_mjy} mJy)"
            )
            return sources

        except Exception as e:
            logger.error(
                f"Error querying {self.config.photometry.catalog} catalog: {e}", exc_info=True
            )
            return []

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate adaptive photometry outputs."""
        if "adaptive_photometry_results" not in context.outputs:
            return False, "adaptive_photometry_results not found in outputs"

        results = context.outputs["adaptive_photometry_results"]
        if not isinstance(results, dict) or "n_sources" not in results:
            return False, "Invalid adaptive_photometry_results format"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial adaptive photometry outputs on failure."""
        if "adaptive_photometry_results" in context.outputs:
            results = context.outputs["adaptive_photometry_results"]
            if isinstance(results, dict) and "output_dir" in results:
                output_dir = Path(results["output_dir"])
                if output_dir.exists():
                    try:
                        import shutil

                        shutil.rmtree(output_dir, ignore_errors=True)
                        logger.info(f"Cleaned up partial adaptive photometry output: {output_dir}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup adaptive photometry output: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "adaptive_photometry"


class TransientDetectionStage(PipelineStage):
    """Transient detection stage: Detect and classify transient sources.

    This stage compares detected sources with baseline catalogs to identify:
    - New sources (not in baseline catalog)
    - Variable sources (significant flux changes)
    - Fading sources (baseline sources no longer detected)

    Implements Proposal #2: Transient Detection & Classification

    Example:
        >>> config = PipelineConfig(paths=PathsConfig(...))
        >>> config.transient_detection.enabled = True
        >>> stage = TransientDetectionStage(config)
        >>> context = PipelineContext(
        ...     config=config,
        ...     outputs={"detected_sources": pd.DataFrame([...])}
        ... )
        >>> result_context = stage.execute(context)
        >>> transients = result_context.outputs["transient_results"]

    Inputs:
        - `detected_sources` (DataFrame): Sources from validation/cross-match
        - `mosaic_id` (int, optional): Mosaic product ID for tracking

    Outputs:
        - `transient_results` (dict): Detection results with candidates
        - `alert_ids` (list): List of alert IDs generated
    """

    def __init__(self, config: PipelineConfig):
        """Initialize transient detection stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for transient detection."""
        if not self.config.transient_detection.enabled:
            return False, "Transient detection stage is disabled"

        if "detected_sources" not in context.outputs:
            return (
                False,
                "No detected sources found for transient detection",
            )

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute transient detection stage.

        Args:
            context: Pipeline context

        Returns:
            Updated context with transient detection results
        """
        from dsa110_contimg.catalog.query import query_sources
        from dsa110_contimg.catalog.transient_detection import (
            create_transient_detection_tables,
            detect_transients,
            generate_transient_alerts,
            store_transient_candidates,
        )

        if not self.config.transient_detection.enabled:
            logger.info("Transient detection stage is disabled, skipping")
            return context.with_output("transient_status", "disabled")

        logger.info("Starting transient detection stage...")

        # Ensure tables exist
        db_path = str(self.config.paths.pipeline_db)
        create_transient_detection_tables(db_path)

        # Get detected sources
        detected_sources = context.outputs["detected_sources"]
        if len(detected_sources) == 0:
            logger.warning("No detected sources for transient detection")
            return context.with_output("transient_status", "skipped_no_sources")

        # Get field center for catalog query
        ra_center = detected_sources["ra_deg"].median()
        dec_center = detected_sources["dec_deg"].median()

        # Calculate field radius
        ra_range = detected_sources["ra_deg"].max() - detected_sources["ra_deg"].min()
        dec_range = detected_sources["dec_deg"].max() - detected_sources["dec_deg"].min()
        field_radius_deg = max(ra_range, dec_range) / 2.0 + 0.1

        # Query baseline catalog
        baseline_catalog = self.config.transient_detection.baseline_catalog
        logger.info(
            f"Querying {baseline_catalog} for baseline sources "
            f"(radius={field_radius_deg:.2f} deg)..."
        )

        baseline_sources = query_sources(
            ra=ra_center,
            dec=dec_center,
            radius_arcmin=field_radius_deg * 60.0,
            catalog=baseline_catalog.lower(),
        )

        if baseline_sources is None or len(baseline_sources) == 0:
            logger.warning(f"No baseline sources found in {baseline_catalog}")
            baseline_sources = pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

        # Detect transients
        logger.info("Running transient detection...")
        new_sources, variable_sources, fading_sources = detect_transients(
            observed_sources=detected_sources,
            baseline_sources=baseline_sources,
            detection_threshold_sigma=(self.config.transient_detection.detection_threshold_sigma),
            variability_threshold=(self.config.transient_detection.variability_threshold_sigma),
            match_radius_arcsec=(self.config.transient_detection.match_radius_arcsec),
            baseline_catalog=baseline_catalog,
        )

        # Combine all candidates
        all_candidates = new_sources + variable_sources + fading_sources

        logger.info(
            f"Found {len(new_sources)} new, {len(variable_sources)} "
            f"variable, {len(fading_sources)} fading sources"
        )

        # Store candidates
        mosaic_id = context.outputs.get("mosaic_id")
        candidate_ids = store_transient_candidates(
            all_candidates,
            baseline_catalog=baseline_catalog,
            mosaic_id=mosaic_id,
            db_path=db_path,
        )

        # Generate alerts
        alert_ids = generate_transient_alerts(
            candidate_ids,
            alert_threshold_sigma=(self.config.transient_detection.alert_threshold_sigma),
            db_path=db_path,
        )

        logger.info(f"Generated {len(alert_ids)} transient alerts")

        results = {
            "n_new": len(new_sources),
            "n_variable": len(variable_sources),
            "n_fading": len(fading_sources),
            "candidate_ids": candidate_ids,
            "alert_ids": alert_ids,
            "baseline_catalog": baseline_catalog,
        }

        return context.with_output("transient_results", results).with_output("alert_ids", alert_ids)

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup transient detection resources."""
        pass

    def get_name(self) -> str:
        """Get stage name."""
        return "transient_detection"
