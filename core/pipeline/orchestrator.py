# core/pipeline/orchestrator.py
"""
Unified Pipeline Orchestrator for DSA-110 Continuum Imaging Pipeline

This module provides a centralized orchestrator that eliminates code duplication
between batch processing and service-based processing by providing a unified
interface for pipeline execution.
"""

import os
import glob
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord

# Pipeline imports
from ..utils.logging import get_logger
from ..utils.monitoring import PipelineMetrics
from ..utils.casa_logging import ensure_casa_log_directory, force_casa_logging_to_directory, get_casa_log_directory
from .exceptions import PipelineError, StageError, CalibrationError, ImagingError
from .stages.data_ingestion_stage import DataIngestionStage
from .stages.calibration_stage import CalibrationStage
from .stages.imaging_stage import ImagingStage
from .stages.mosaicking_stage import MosaickingStage
from .stages.photometry_stage import PhotometryStage

logger = get_logger(__name__)


@dataclass
class ProcessingBlock:
    """Represents a block of MS files to be processed together."""
    start_time: Time
    end_time: Time
    ms_files: List[str]
    block_id: str
    
    def __post_init__(self):
        if not self.ms_files:
            raise ValueError("ProcessingBlock must have at least one MS file")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")


@dataclass
class ProcessingResult:
    """Results from processing a block."""
    block_id: str
    success: bool
    stage_results: Dict[str, Any]
    errors: List[str]
    processing_time: float
    output_files: Dict[str, str]


class PipelineOrchestrator:
    """
    Unified orchestrator for DSA-110 pipeline processing.
    
    This class eliminates the duplication between main_driver.py and 
    ms_processor_service.py by providing a single, well-tested processing
    implementation that can be used by both batch and service modes.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the pipeline orchestrator.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.metrics = PipelineMetrics()
        
        # Force CASA logging to use the casalogs directory
        casa_log_dir = get_casa_log_directory(config)
        force_casa_logging_to_directory(casa_log_dir)
        
        self.stages = self._initialize_stages()
        self._ensure_output_directories()
        
        logger.info("Pipeline orchestrator initialized")
    
    def _initialize_stages(self) -> Dict[str, Any]:
        """Initialize all pipeline stages."""
        stages = {}
        
        try:
            stages['data_ingestion'] = DataIngestionStage(self.config)
            stages['calibration'] = CalibrationStage(self.config)
            stages['imaging'] = ImagingStage(self.config)
            stages['mosaicking'] = MosaickingStage(self.config)
            stages['photometry'] = PhotometryStage(self.config)
            
            logger.info(f"Initialized {len(stages)} pipeline stages")
            return stages
            
        except Exception as e:
            logger.error(f"Failed to initialize pipeline stages: {e}")
            raise PipelineError(f"Stage initialization failed: {e}")
    
    def _ensure_output_directories(self):
        """Ensure all required output directories exist."""
        paths_config = self.config.get('paths', {})
        required_dirs = [
            'cal_tables_dir', 'skymodels_dir', 'images_dir', 
            'mosaics_dir', 'photometry_dir'
        ]
        
        for dir_key in required_dirs:
            dir_path = paths_config.get(dir_key)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
                logger.debug(f"Ensured directory exists: {dir_path}")
    
    async def process_block(self, block: ProcessingBlock) -> ProcessingResult:
        """
        Process a single block of MS files through the complete pipeline.
        
        Args:
            block: ProcessingBlock containing MS files and timing information
            
        Returns:
            ProcessingResult with success status and output information
        """
        start_time = datetime.now()
        logger.info(f"Starting processing block {block.block_id}")
        logger.info(f"Block time range: {block.start_time.iso} to {block.end_time.iso}")
        logger.info(f"MS files: {len(block.ms_files)}")
        
        result = ProcessingResult(
            block_id=block.block_id,
            success=False,
            stage_results={},
            errors=[],
            processing_time=0.0,
            output_files={}
        )
        
        try:
            # Stage 1: Calibration Setup
            logger.info("=== Stage 1: Calibration Setup ===")
            cal_result = await self.stages['calibration'].setup_calibration(block)
            result.stage_results['calibration'] = cal_result
            
            if not cal_result['success']:
                raise CalibrationError(f"Calibration setup failed: {cal_result['error']}")
            
            # Stage 2: Process Individual MS Files
            logger.info("=== Stage 2: MS Processing ===")
            processed_images = []
            processed_pbs = []
            
            for i, ms_path in enumerate(block.ms_files):
                logger.info(f"Processing MS {i+1}/{len(block.ms_files)}: {os.path.basename(ms_path)}")
                
                try:
                    # Apply calibration and imaging to each MS
                    img_result = await self.stages['imaging'].process_ms(
                        ms_path, 
                        cal_result['bcal_table'],
                        cal_result['gcal_table'],
                        cal_result['cl_path'],
                        cal_result.get('mask_path')
                    )
                    
                    if img_result['success']:
                        processed_images.append(img_result['image_path'])
                        processed_pbs.append(img_result['pb_path'])
                        logger.info(f"Successfully processed {ms_path}")
                    else:
                        logger.error(f"Failed to process {ms_path}: {img_result['error']}")
                        result.errors.append(f"MS processing failed for {ms_path}: {img_result['error']}")
                        
                except Exception as e:
                    error_msg = f"Exception processing {ms_path}: {e}"
                    logger.error(error_msg, exc_info=True)
                    result.errors.append(error_msg)
            
            # Check if we have enough successful images
            min_images_needed = int(len(block.ms_files) * 0.75)  # 75% success rate
            if len(processed_images) < min_images_needed:
                raise ImagingError(f"Insufficient successful images: {len(processed_images)}/{len(block.ms_files)}")
            
            # Stage 3: Mosaicking
            logger.info("=== Stage 3: Mosaicking ===")
            mosaic_result = await self.stages['mosaicking'].create_mosaic(
                processed_images, processed_pbs, block
            )
            result.stage_results['mosaicking'] = mosaic_result
            
            if not mosaic_result['success']:
                raise ImagingError(f"Mosaicking failed: {mosaic_result['error']}")
            
            # Stage 4: Photometry
            logger.info("=== Stage 4: Photometry ===")
            if mosaic_result.get('fits_path'):
                phot_result = await self.stages['photometry'].process_mosaic(
                    mosaic_result['fits_path'], block.end_time
                )
                result.stage_results['photometry'] = phot_result
                
                if not phot_result['success']:
                    logger.warning(f"Photometry failed: {phot_result['error']}")
                    result.errors.append(f"Photometry failed: {phot_result['error']}")
            
            # Mark as successful
            result.success = True
            result.output_files = {
                'mosaic_image': mosaic_result.get('image_path'),
                'mosaic_fits': mosaic_result.get('fits_path'),
                'processed_images': processed_images,
                'processed_pbs': processed_pbs
            }
            
            logger.info(f"Successfully completed processing block {block.block_id}")
            
        except Exception as e:
            error_msg = f"Pipeline processing failed for block {block.block_id}: {e}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            result.success = False
        
        finally:
            # Calculate processing time
            result.processing_time = (datetime.now() - start_time).total_seconds()
            
            # Record metrics
            self.metrics.record_block_processing(
                block_id=block.block_id,
                success=result.success,
                processing_time=result.processing_time,
                ms_count=len(block.ms_files),
                image_count=len(result.output_files.get('processed_images', []))
            )
            
            logger.info(f"Block {block.block_id} processing completed in {result.processing_time:.1f}s")
        
        return result
    
    async def process_hdf5_to_ms(self, hdf5_dir: str, start_timestamp: Optional[str] = None,
                                end_timestamp: Optional[str] = None) -> List[str]:
        """
        Process HDF5 files to MS format using the unified data ingestion stage.
        
        This method handles the conversion of HDF5 files to Measurement Sets
        using the unified MS creation system with DSA-110 specific fixes.
        
        Args:
            hdf5_dir: Directory containing HDF5 files
            start_timestamp: Start timestamp for processing (optional)
            end_timestamp: End timestamp for processing (optional)
            
        Returns:
            List of created MS file paths
        """
        logger.info(f"Processing HDF5 files from directory: {hdf5_dir}")
        
        try:
            data_ingestion_stage = self.stages['data_ingestion']
            
            if start_timestamp and end_timestamp:
                # Process specific timestamp range
                ms_files = await data_ingestion_stage.process_timestamp_range(
                    start_timestamp, end_timestamp, hdf5_dir
                )
            else:
                # Process all timestamps in directory
                ms_files = await data_ingestion_stage.process_timestamp_range(
                    "", "", hdf5_dir
                )
            
            if ms_files:
                logger.info(f"Successfully created {len(ms_files)} MS files")
                
                # Validate the created MS files
                validation_results = await data_ingestion_stage.validate_ms_files(ms_files)
                logger.info(f"MS validation: {validation_results['valid_files']} valid, "
                           f"{validation_results['invalid_files']} invalid")
                
                if validation_results['errors']:
                    for error in validation_results['errors']:
                        logger.error(f"MS validation error: {error}")
                
                return ms_files
            else:
                logger.error("No MS files were created")
                return []
                
        except Exception as e:
            logger.error(f"HDF5 to MS processing failed: {e}")
            raise PipelineError(f"HDF5 to MS processing failed: {e}")
    
    def find_ms_blocks_for_batch(self, start_time_iso: Optional[str] = None, 
                                end_time_iso: Optional[str] = None) -> Dict[Time, List[str]]:
        """
        Find blocks of MS files suitable for batch processing.
        
        This method consolidates the logic from main_driver.py's 
        find_ms_blocks_for_batch function.
        
        Args:
            start_time_iso: ISO timestamp to start processing from
            end_time_iso: ISO timestamp to end processing at
            
        Returns:
            Dictionary mapping block end times to lists of MS file paths
        """
        logger.info("Finding MS blocks for batch processing")
        
        paths_config = self.config.get('paths', {})
        services_config = self.config.get('services', {})
        
        ms_dir = paths_config.get('ms_stage1_dir')
        if not ms_dir:
            raise PipelineError("Config missing 'paths:ms_stage1_dir'")
        
        duration = timedelta(minutes=services_config.get('mosaic_duration_min', 60))
        overlap = timedelta(minutes=services_config.get('mosaic_overlap_min', 10))
        ms_chunk = timedelta(minutes=services_config.get('ms_chunk_duration_min', 5))
        num_ms_per_block = int(duration / ms_chunk)
        
        if num_ms_per_block <= 0:
            raise PipelineError("Invalid timing configuration: num_ms_per_block <= 0")
        
        if not os.path.isdir(ms_dir):
            raise PipelineError(f"MS Stage 1 directory not found: {ms_dir}")
        
        # Find all MS files
        all_ms = sorted(glob.glob(os.path.join(ms_dir, "drift_*.ms")))
        if not all_ms:
            logger.warning(f"No MS files found in {ms_dir}")
            return {}
        
        # Parse timestamps and create time-indexed dictionary
        ms_times = {}
        for ms_path in all_ms:
            ms_name = os.path.basename(ms_path)
            try:
                ts_str = ms_name.split('_')[1].replace('.ms', '')
                ms_start_time = Time(datetime.strptime(ts_str, "%Y%m%dT%H%M%S"), 
                                   format='datetime', scale='utc')
                ms_times[ms_start_time.mjd] = {'path': ms_path, 'time': ms_start_time}
            except Exception as e:
                logger.warning(f"Could not parse time from {ms_name}: {e}")
                continue
        
        if not ms_times:
            raise PipelineError("No valid MS files found after time parsing")
        
        # Determine processing range
        sorted_mjds = sorted(ms_times.keys())
        sorted_times = [ms_times[mjd]['time'] for mjd in sorted_mjds]
        
        first_ms_time = sorted_times[0]
        last_ms_time = sorted_times[-1]
        
        proc_start_time = Time(start_time_iso) if start_time_iso else first_ms_time
        proc_end_time_limit = Time(end_time_iso) if end_time_iso else (last_ms_time + ms_chunk)
        
        logger.info(f"Processing range: {proc_start_time.iso} to {proc_end_time_limit.iso}")
        
        # Group MS files into overlapping blocks
        blocks = {}
        current_search_start_time = first_ms_time
        
        while True:
            current_block_end_time = current_search_start_time + duration
            current_block_start_time = current_block_end_time - duration
            
            if current_block_end_time > proc_end_time_limit + overlap:
                break
            
            # Find MS files within this block
            block_files_dict = {}
            for mjd, data in ms_times.items():
                if current_block_start_time <= data['time'] < current_block_end_time:
                    block_files_dict[mjd] = data['path']
            
            # Check if we have enough files for this block
            if len(block_files_dict) >= num_ms_per_block:
                block_mjds_sorted = sorted(block_files_dict.keys())
                final_block_mjds = block_mjds_sorted[:num_ms_per_block]
                final_block_files = [block_files_dict[mjd] for mjd in final_block_mjds]
                
                if current_block_end_time >= proc_start_time:
                    blocks[current_block_end_time] = final_block_files
                    logger.debug(f"Identified block ending {current_block_end_time.iso} with {len(final_block_files)} files")
            
            # Advance to next block
            current_search_start_time += (duration - overlap)
        
        logger.info(f"Identified {len(blocks)} processing blocks")
        return blocks
    
    def create_processing_block(self, block_end_time: Time, ms_files: List[str]) -> ProcessingBlock:
        """
        Create a ProcessingBlock from block end time and MS files.
        
        Args:
            block_end_time: End time of the block
            ms_files: List of MS file paths
            
        Returns:
            ProcessingBlock object
        """
        services_config = self.config.get('services', {})
        duration = timedelta(minutes=services_config.get('mosaic_duration_min', 60))
        
        block_start_time = block_end_time - duration
        block_id = f"{block_start_time.strftime('%Y%m%dT%H%M%S')}_{block_end_time.strftime('%Y%m%dT%H%M%S')}"
        
        return ProcessingBlock(
            start_time=block_start_time,
            end_time=block_end_time,
            ms_files=ms_files,
            block_id=block_id
        )
