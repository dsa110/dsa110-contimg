"""
Concrete pipeline stage implementations.

These stages wrap existing conversion, calibration, and imaging functions
to provide a unified pipeline interface.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, Tuple

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import PipelineStage
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logger = logging.getLogger(__name__)


class ConversionStage(PipelineStage):
    """Conversion stage: UVH5 → MS.

    Discovers complete subband groups in the specified time window and
    converts them to CASA Measurement Sets.
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

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute conversion stage."""
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

        # Execute conversion (function returns None, creates MS files in output_dir)
        convert_subband_groups_to_ms(
            str(context.config.paths.input_dir),
            str(context.config.paths.output_dir),
            start_time,
            end_time,
            writer=self.config.conversion.writer,
            writer_kwargs=writer_kwargs,
        )

        # Discover created MS files (similar to current run_convert_job)
        # Only include main MS files matching YYYY-MM-DDTHH:MM:SS.ms pattern
        # Exclude legacy files with suffixes (.phased.ms, .phased_concat.ms, etc.)
        # and files in subdirectories (legacy/, etc.)
        output_path = Path(context.config.paths.output_dir)
        ms_files = []
        if output_path.exists():
            # Pattern: YYYY-MM-DDTHH:MM:SS.ms (no suffixes, no subdirectories)
            pattern = re.compile(
                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.ms$'
            )

            # Only search in the main output directory, not subdirectories
            for ms in output_path.glob("*.ms"):
                if ms.is_dir():
                    # Check if filename matches pattern (no suffixes)
                    if pattern.match(ms.name):
                        ms_files.append(str(ms))
                    else:
                        logger.debug(
                            "Skipping legacy/duplicate MS file: %s", ms.name
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

        # Update MS index via state repository if available
        if context.state_repository:
            try:
                for ms_file in ms_files:
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

        # Return both single MS path (for backward compatibility) and all MS paths
        return context.with_outputs({
            "ms_path": ms_path,  # Single MS for backward compatibility
            "ms_paths": ms_files,  # All MS files
        })

    def get_name(self) -> str:
        """Get stage name."""
        return "conversion"


class CalibrationSolveStage(PipelineStage):
    """Calibration solve stage: Solve calibration solutions (K, BP, G).

    This stage solves calibration tables (delay/K, bandpass/BP, gains/G)
    for a calibrator Measurement Set. This wraps the calibration CLI
    functions directly without subprocess overhead.
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
            return False, "ms_path required in context.outputs (conversion must run first)"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration solve stage."""
        from dsa110_contimg.calibration.calibration import (
            solve_delay,
            solve_bandpass,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            reset_flags,
            flag_zeros,
            flag_rfi,
        )
        import glob
        import os

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration solve stage: {ms_path}")

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
            ms_base = os.path.basename(ms_path).replace('.ms', '')
            
            if not solve_delay_flag and not existing_k:
                k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
                k_tables = sorted([p for p in glob.glob(k_pattern) if os.path.isdir(p)], 
                                key=os.path.getmtime, reverse=True)
                if k_tables:
                    existing_k = k_tables[0]
            
            if not solve_bandpass_flag and not existing_bp:
                bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
                bp_tables = sorted([p for p in glob.glob(bp_pattern) if os.path.isdir(p)], 
                                 key=os.path.getmtime, reverse=True)
                if bp_tables:
                    existing_bp = bp_tables[0]
            
            if not solve_gains_flag and not existing_g:
                g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")
                g_tables = sorted([p for p in glob.glob(g_pattern) if os.path.isdir(p)], 
                                key=os.path.getmtime, reverse=True)
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
        
        # Ensure registry DB directory exists (will be created by ensure_db if needed)
        try:
            from dsa110_contimg.database.registry import register_set_from_prefix, ensure_db
            from dsa110_contimg.utils.time_utils import extract_ms_time_range
            
            # Ensure registry DB exists (creates if missing)
            ensure_db(registry_db)
            
            # Extract time range from MS for validity window
            # Use wider window (±1 hour) to cover observation period, not just single MS
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
            if mid_mjd is None:
                logger.warning(f"Could not extract time range from {ms_path}, using current time")
                from astropy.time import Time
                mid_mjd = Time.now().mjd
                start_mjd = mid_mjd - 1.0 / 24.0  # 1 hour before
                end_mjd = mid_mjd + 1.0 / 24.0    # 1 hour after
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
            
            # Use table prefix (common prefix of all tables)
            if all_tables:
                # Get common directory and base name
                table_dir = Path(all_tables[0]).parent
                # Extract prefix from first table (e.g., "2025-10-29T13:54:17_0_bpcal" -> "2025-10-29T13:54:17_0")
                first_table_name = Path(all_tables[0]).stem
                # Remove table type suffixes (e.g., "_bpcal", "_gpcal", "_2gcal")
                # Pattern: find the last underscore followed by table type
                prefix_base = re.sub(r'_(bpcal|gpcal|gacal|2gcal|kcal|bacal|flux)$', '', first_table_name, flags=re.IGNORECASE)
                table_prefix = table_dir / prefix_base
                
                logger.info(f"Registering calibration tables in registry: {set_name}")
                logger.debug(f"Using table prefix: {table_prefix}")
                registered = register_set_from_prefix(
                    registry_db,
                    set_name,
                    table_prefix,
                    cal_field=field,
                    refant=refant,
                    valid_start_mjd=start_mjd,
                    valid_end_mjd=end_mjd,
                    status="active",
                )
                if registered:
                    logger.info(f"✓ Registered {len(registered)} calibration tables in registry")
                else:
                    # No tables found with prefix - this is a critical failure
                    error_msg = (
                        f"Failed to register calibration tables: No tables found with prefix {table_prefix}. "
                        f"Tables were created but not registered. This will cause CalibrationStage to fail."
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
            else:
                # No tables to register - this shouldn't happen if solve succeeded
                error_msg = "No calibration tables generated to register"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        except Exception as e:
            # Registration failure is CRITICAL - CalibrationStage will fail without registered tables
            error_msg = (
                f"CRITICAL: Failed to register calibration tables in registry: {e}. "
                f"CalibrationStage will not be able to find tables via registry lookup. "
                f"Tables were created but not registered."
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

        return context.with_output("calibration_tables", all_tables)

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration_solve"


class CalibrationStage(PipelineStage):
    """Calibration stage: Apply calibration solutions to MS.

    This stage applies calibration solutions (bandpass, gain) to the
    Measurement Set. In the current implementation, this wraps the
    existing calibration service.
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
            return False, "ms_path required in context.outputs (conversion must run first)"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration stage."""
        from dsa110_contimg.calibration.apply_service import apply_calibration
        from pathlib import Path

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration stage: {ms_path}")

        # Check if calibration tables were provided by a previous stage (e.g., CalibrationSolveStage)
        caltables = context.outputs.get("calibration_tables")
        
        # Get registry database path from config (needed for lookup if tables not provided)
        registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"
        if not registry_db.exists():
            # Try alternative location
            registry_db = Path("/data/dsa110-contimg/state/cal_registry.sqlite3")
            if not registry_db.exists():
                if caltables is None:
                    # No tables provided and no registry - can't proceed
                    error_msg = (
                        f"Cannot apply calibration: No calibration tables provided and "
                        f"registry not found at {registry_db}. Calibration is required for imaging."
                )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                # Tables provided but no registry - that's OK, we'll use the provided tables
                registry_db = None

        # Apply calibration using the calibration service
        # Use imaging.field if available, otherwise empty string (all fields)
        field = getattr(context.config.imaging, "field", None) or ""
        
        # If caltables provided, use them directly; otherwise lookup from registry
        if caltables:
            logger.info(f"Using calibration tables from previous stage: {len(caltables)} tables")
            # When tables are provided, registry_db can be None (not needed)
            result = apply_calibration(
                ms_path,
                registry_db or Path("/tmp"),  # Dummy path since we're providing tables
                caltables=caltables,  # Explicitly pass tables
                field=field,
                verify=True,
                update_db=True,
                products_db=context.config.paths.state_dir / "products.sqlite3",
            )
        else:
            # Lookup tables from registry
            if registry_db is None or not registry_db.exists():
                error_msg = (
                    f"Cannot apply calibration: No calibration tables provided and "
                    f"registry not found. Calibration is required for imaging."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            logger.info("Looking up calibration tables from registry")
        result = apply_calibration(
            ms_path,
            registry_db,
            field=field,
            verify=True,
            update_db=True,
            products_db=context.config.paths.state_dir / "products.sqlite3",
        )

        if not result.success:
            if result.error and "No calibration tables available" in result.error:
                error_msg = (
                    f"Cannot apply calibration: No calibration tables available for {ms_path}. "
                    "Calibration is required for downstream imaging."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            else:
                raise RuntimeError(
                    f"Calibration application failed: {result.error}"
                )

        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_applied": 1 if result.success else 0,
                        "stage": "calibration",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        return context

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration"


class ImagingStage(PipelineStage):
    """Imaging stage: Create images from calibrated MS.

    This stage runs imaging on the calibrated Measurement Set to produce
    continuum images.
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

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute imaging stage."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        from casacore.tables import table
        import numpy as np

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
                        logger.info("CORRECTED_DATA is empty, copying DATA to CORRECTED_DATA for imaging")
                        data_col = t.getcol("DATA")
                        t.putcol("CORRECTED_DATA", data_col)
                        t.flush()
        except Exception as e:
            logger.warning(f"Could not check/fix CORRECTED_DATA: {e}")

        # Construct output imagename
        ms_name = Path(ms_path).stem
        out_dir = Path(ms_path).parent.parent / "images" / Path(ms_path).parent.name
        out_dir.mkdir(parents=True, exist_ok=True)
        imagename = str(out_dir / f"{ms_name}.img")

        # Run imaging
        image_ms(
            ms_path,
            imagename=imagename,
            field=context.config.imaging.field or "",
            gridder=context.config.imaging.gridder,
            wprojplanes=context.config.imaging.wprojplanes,
            quality_tier="standard",
            skip_fits=False,
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

        return context.with_output("image_path", primary_image)

    def get_name(self) -> str:
        """Get stage name."""
        return "imaging"
