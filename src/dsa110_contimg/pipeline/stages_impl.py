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
from typing import Dict, Optional, Tuple

import astropy.units as u
import numpy as np
import pandas as pd

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import PipelineStage
from dsa110_contimg.utils.ms_organization import (
    create_path_mapper,
    determine_ms_type,
    extract_date_from_filename,
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
                from dsa110_contimg.database.products import ensure_products_db

                products_db = self.config.paths.products_db
                conn = ensure_products_db(products_db)
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
                            f"⚠️  DECLINATION CHANGE DETECTED: "
                            f"{previous_dec:.6f}° → {dec_center:.6f}° "
                            f"(Δ = {dec_change:.6f}° > {dec_change_threshold:.6f}° threshold)"
                        )
                        logger.warning(
                            "⚠️  Telescope pointing has changed significantly. "
                            "Catalogs will be rebuilt for new declination strip."
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
                from dsa110_contimg.database.products import ensure_products_db

                products_db = self.config.paths.products_db
                conn = ensure_products_db(products_db)

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

        catalog_types = ["nvss", "first", "rax"]

        for catalog_type in catalog_types:
            try:
                # Check if catalog database exists
                try:
                    catalog_path = resolve_catalog_path(
                        catalog_type=catalog_type, dec_strip=dec_center
                    )
                    if catalog_path.exists():
                        logger.info(f"✓ {catalog_type.upper()} catalog exists: {catalog_path}")
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

                logger.info(
                    f"✓ {catalog_type.upper()} catalog built: {db_path} "
                    f"({db_path.stat().st_size / (1024 * 1024):.2f} MB)"
                )
                catalogs_built.append(catalog_type)

            except Exception as e:
                logger.error(
                    f"✗ Failed to build {catalog_type.upper()} catalog: {e}",
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

        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            convert_subband_groups_to_ms,
        )

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
                    logger.info("✓ MS passed quality checks")
                else:
                    logger.warning("⚠ MS quality issues detected (see alerts)")
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
        import time

        start_time_sec = time.time()
        log_progress("Starting calibration solve stage...")

        import glob
        import os

        from dsa110_contimg.calibration.calibration import (
            solve_bandpass,
            solve_delay,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            flag_rfi,
            flag_zeros,
            reset_flags,
        )
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

    def _execute_calibration_solve(self, context: PipelineContext, ms_path: str) -> PipelineContext:
        """Internal calibration solve execution (called within lock)."""
        import glob
        import os

        from dsa110_contimg.calibration.calibration import (
            solve_bandpass,
            solve_delay,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            flag_rfi,
            flag_zeros,
            reset_flags,
        )

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

        # Step 1: Flagging (if requested)
        if params.get("do_flagging", True):
            logger.info("Resetting flags...")
            reset_flags(ms_path)
            flag_zeros(ms_path)
            flag_rfi(ms_path)
            if flag_autocorr:
                from casatasks import flagdata

                logger.info("Flagging autocorrelations...")
                flagdata(vis=str(ms_path), autocorr=True, flagbackup=False)
                logger.info("✓ Autocorrelations flagged")

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

        # Step 3: Solve delay (K) if requested
        ktabs = []
        if solve_delay_flag and not existing_k:
            logger.info("Solving delay (K) calibration...")
            ktabs = solve_delay(
                ms_path,
                field,
                refant,
                table_prefix=table_prefix,
                combine_spw=params.get("k_combine_spw", False),
                t_slow=params.get("k_t_slow", "inf"),
                t_fast=params.get("k_t_fast", "60s"),
                uvrange=params.get("k_uvrange", ""),
                minsnr=params.get("k_minsnr", 5.0),
                skip_slow=params.get("k_skip_slow", False),
            )
        elif existing_k:
            ktabs = [existing_k]
            logger.info(f"Using existing K table: {existing_k}")

        # Step 4: Pre-bandpass phase (if requested)
        prebp_table = None
        if prebp_phase:
            logger.info("Solving pre-bandpass phase...")
            prebp_table = solve_prebandpass_phase(
                ms_path,
                field,
                refant,
                table_prefix=table_prefix,
                uvrange=params.get("prebp_uvrange", ""),
                minsnr=params.get("prebp_minsnr", 3.0),
            )

        # Step 5: Solve bandpass (BP) if requested
        bptabs = []
        if solve_bandpass_flag and not existing_bp:
            logger.info("Solving bandpass (BP) calibration...")
            bptabs = solve_bandpass(
                ms_path,
                field,
                refant,
                ktable=ktabs[0] if ktabs else None,
                table_prefix=table_prefix,
                set_model=True,
                model_standard=params.get("bp_model_standard", "Perley-Butler 2017"),
                combine_fields=bp_combine_field,
                combine_spw=params.get("bp_combine_spw", False),
                minsnr=params.get("bp_minsnr", 5.0),
                uvrange=params.get("bp_uvrange", ""),
                prebandpass_phase_table=prebp_table,
                bp_smooth_type=params.get("bp_smooth_type"),
                bp_smooth_window=params.get("bp_smooth_window"),
            )
        elif existing_bp:
            bptabs = [existing_bp]
            logger.info(f"Using existing BP table: {existing_bp}")

        # Step 6: Solve gains (G) if requested
        gtabs = []
        if solve_gains_flag and not existing_g:
            logger.info("Solving gains (G) calibration...")
            phase_only = (gain_calmode == "p") or bool(params.get("fast"))
            gtabs = solve_gains(
                ms_path,
                field,
                refant,
                ktable=ktabs[0] if ktabs else None,
                bptables=bptabs,
                table_prefix=table_prefix,
                t_short=params.get("gain_t_short", "60s"),
                combine_fields=bp_combine_field,
                phase_only=phase_only,
                uvrange=params.get("gain_uvrange", ""),
                solint=gain_solint,
                minsnr=params.get("gain_minsnr", 3.0),
            )
        elif existing_g:
            gtabs = [existing_g]
            logger.info(f"Using existing G table: {existing_g}")

        # Combine all tables
        all_tables = (ktabs[:1] if ktabs else []) + bptabs + gtabs
        logger.info(f"Calibration solve complete. Generated {len(all_tables)} tables:")
        for tab in all_tables:
            logger.info(f"  - {tab}")

        # Register calibration tables in registry database
        # CRITICAL: Registration is required for CalibrationStage to find tables via registry lookup
        registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"

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
                        f"Extended validity window from {duration*24*60:.1f} min to "
                        f"{(end_mjd - start_mjd)*24*60:.1f} min (±{window_hours}h)"
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
                f"✓ Registered and verified {len(registered_paths)} calibration tables "
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
            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e
        else:
            # Lookup tables from registry by observation time (consistent with streaming mode)
            registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"
            if not registry_db.exists():
                # Try alternative location
                registry_db = Path("/data/dsa110-contimg/state/cal_registry.sqlite3")
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
            except Exception:
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
            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e

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

        # Register calibrated MS in data registry (as calib_ms type)
        if cal_applied:
            try:
                from dsa110_contimg.database.data_registration import (
                    register_pipeline_data,
                )
                from dsa110_contimg.utils.time_utils import extract_ms_time_range

                ms_path_obj = Path(ms_path)
                # Use MS path as data_id with calib_ms prefix to distinguish from raw MS
                data_id = f"calib_{ms_path_obj}"
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

                register_pipeline_data(
                    data_type="calib_ms",
                    data_id=data_id,
                    file_path=ms_path_obj,
                    metadata=metadata,
                    auto_publish=True,
                )
                logger.info(f"Registered calibrated MS in data registry: {ms_path}")
            except Exception as e:
                logger.warning(f"Failed to register calibrated MS in data registry: {e}")

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
        import numpy as np

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
            use_nvss_mask=context.config.imaging.use_nvss_mask,
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
        image_path_obj = Path(image_path)
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
                    f"scale error={result.flux_scale_error*100:.1f}%"
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
            validate_astrometry,
            validate_flux_scale,
            validate_source_counts,
        )
        from dsa110_contimg.qa.html_reports import generate_validation_report

        image_path = context.outputs["image_path"]
        logger.info(f"Validation stage: {image_path}")

        # Find FITS image (prefer PB-corrected)
        image_path_obj = Path(image_path)
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
                    f"Error: {flux_scale_result.flux_scale_error*100:.1f}%"
                    if flux_scale_result.mean_flux_ratio and flux_scale_result.flux_scale_error
                    else "N/A"
                )

            if source_counts_result:
                logger.info(
                    f"Source counts validation: Completeness: {source_counts_result.completeness*100:.1f}%"
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
        import time

        from astropy.coordinates import Angle
        from astropy.time import Time

        from dsa110_contimg.catalog.crossmatch import (
            calculate_flux_scale,
            calculate_positional_offsets,
            cross_match_dataframes,
            identify_duplicate_catalog_sources,
            multi_catalog_match,
        )
        from dsa110_contimg.catalog.query import query_sources
        from dsa110_contimg.database.products import ensure_products_db
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
                    "dra_median_arcsec": dra_median.to(u.arcsec).value,
                    "ddec_median_arcsec": ddec_median.to(u.arcsec).value,
                    "dra_madfm_arcsec": dra_madfm.to(u.arcsec).value,
                    "ddec_madfm_arcsec": ddec_madfm.to(u.arcsec).value,
                }
                logger.info(
                    f"{catalog_type.upper()} offsets: "
                    f"RA={dra_median.to(u.arcsec).value:.2f}±{dra_madfm.to(u.arcsec).value:.2f} arcsec, "
                    f"Dec={ddec_median.to(u.arcsec).value:.2f}±{ddec_madfm.to(u.arcsec).value:.2f} arcsec"
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

        # Prepare results
        crossmatch_results = {
            "n_catalogs": len(all_matches),
            "catalog_types": list(all_matches.keys()),
            "matches": all_matches,
            "offsets": all_offsets,
            "flux_scales": all_flux_scales,
            "method": method,
            "radius_arcsec": radius_arcsec,
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

        from dsa110_contimg.database.products import ensure_products_db

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

        import astropy.coordinates as acoords
        import casacore.tables as casatables
        import numpy as np

        table = casatables.table

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
                f"Running adaptive binning for source {i+1}/{len(sources)}: RA={ra_deg:.6f}, Dec={dec_deg:.6f}"
            )

            source_output_dir = output_dir / f"source_{i+1:03d}"
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
                        f"Source {i+1}: Found {len(result.detections)} detection(s) "
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
                    logger.warning(f"Source {i+1}: Adaptive binning failed: {result.error_message}")
            except Exception as e:
                logger.error(f"Source {i+1}: Error during adaptive binning: {e}", exc_info=True)

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
            import astropy.coordinates as acoords
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
            from dsa110_contimg.calibration.catalogs import query_nvss_sources

            max_radius_deg = 1.0
            df = query_nvss_sources(
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                radius_deg=max_radius_deg,
                min_flux_mjy=self.config.photometry.min_flux_mjy,
            )

            # Extract coordinates as list of tuples
            if len(df) > 0:
                sources = list(zip(df["ra_deg"].to_numpy(), df["dec_deg"].to_numpy()))
            else:
                sources = []
            logger.info(
                f"Found {len(sources)} NVSS sources in field "
                f"(center: RA={ra_deg:.6f}, Dec={dec_deg:.6f}, "
                f"radius={max_radius_deg} deg, min_flux={self.config.photometry.min_flux_mjy} mJy)"
            )
            return sources

        except Exception as e:
            logger.error(f"Error querying NVSS catalog: {e}", exc_info=True)
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
