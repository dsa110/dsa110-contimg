"""
Concrete pipeline stage implementations.

These stages wrap existing conversion, calibration, and imaging functions
to provide a unified pipeline interface.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.resources import ResourceManager
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
        writer_kwargs = {}
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
            max_workers=self.config.conversion.max_workers,
        )
        
        # Discover created MS files (similar to current run_convert_job)
        output_path = Path(context.config.paths.output_dir)
        ms_files = []
        if output_path.exists():
            for ms in output_path.glob("**/*.ms"):
                if ms.is_dir():
                    ms_files.append(str(ms))
        
        if not ms_files:
            raise ValueError("Conversion produced no MS files")
        
        # Use first MS path (for now - could handle multiple later)
        ms_path = ms_files[0]
        
        # Update MS index via state repository if available
        if context.state_repository:
            try:
                start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
                context.state_repository.upsert_ms_index(
                    ms_path,
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
        
        return context.with_output("ms_path", ms_path)
    
    def get_name(self) -> str:
        """Get stage name."""
        return "conversion"


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
        # TODO: Implement calibration stage
        # For now, this is a placeholder that would call the calibration service
        # The actual implementation would:
        # 1. Find calibration solutions for the MS
        # 2. Apply calibration using applycal
        # 3. Update MS index with cal_applied flag
        
        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration stage: {ms_path}")
        
        # Placeholder - actual implementation would call calibration service
        # from dsa110_contimg.calibration.apply_service import apply_calibration
        # apply_calibration(ms_path, ...)
        
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_applied": 1,
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
        # TODO: Implement imaging stage
        # For now, this is a placeholder that would call the imaging worker
        # The actual implementation would:
        # 1. Run imaging on the MS
        # 2. Create output images
        # 3. Update MS index with imagename
        
        ms_path = context.outputs["ms_path"]
        logger.info(f"Imaging stage: {ms_path}")
        
        # Placeholder - actual implementation would call imaging worker
        # from dsa110_contimg.imaging.worker import process_once
        # image_paths = process_once(ms_path, ...)
        
        # For now, return context with placeholder image path
        image_path = str(Path(ms_path).parent / "image.fits")
        
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "imagename": image_path,
                        "stage": "imaging",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")
        
        return context.with_output("image_path", image_path)
    
    def get_name(self) -> str:
        """Get stage name."""
        return "imaging"

