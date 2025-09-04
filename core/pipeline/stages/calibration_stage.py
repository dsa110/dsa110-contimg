# core/pipeline/stages/calibration_stage.py
"""
Calibration stage for DSA-110 pipeline.

This module handles all calibration-related operations including
bandpass calibration, gain calibration, and calibration application.
"""

import os
import glob
import logging
from typing import Dict, Any, List, Optional
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord

from ...utils.logging import get_logger
from ...telescope.dsa110 import get_telescope_location
from ..exceptions import CalibrationError
from ...data_ingestion.skymodel import SkyModelManager

logger = get_logger(__name__)


class CalibrationStage:
    """
    Handles calibration operations for the pipeline.
    
    This class consolidates calibration logic from the original
    calibration.py module and provides a cleaner interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the calibration stage.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.cal_config = config.get('calibration', {})
        self.paths_config = config.get('paths', {})
        self.skymodel_manager = SkyModelManager(config)
        
        # Ensure calibration tables directory exists
        cal_tables_dir = self.paths_config.get('cal_tables_dir')
        if cal_tables_dir:
            os.makedirs(cal_tables_dir, exist_ok=True)
    
    async def setup_calibration(self, block) -> Dict[str, Any]:
        """
        Set up calibration for a processing block.
        
        This includes finding the appropriate bandpass calibration table
        and generating gain calibration solutions.
        
        Args:
            block: ProcessingBlock object
            
        Returns:
            Dictionary containing calibration setup results
        """
        logger.info(f"Setting up calibration for block {block.block_id}")
        
        try:
            # Find latest bandpass calibration table
            bcal_table = self._find_latest_bcal_table(block.end_time)
            if not bcal_table:
                raise CalibrationError("No suitable bandpass calibration table found")
            
            # Calculate block center coordinates
            center_coord = self._calculate_block_center(block)
            
            # Generate sky model for the block
            cl_path = await self._generate_sky_model(block, center_coord)
            if not cl_path:
                raise CalibrationError("Failed to generate sky model")
            
            # Perform gain calibration
            gcal_table = await self._perform_gain_calibration(block, cl_path)
            if not gcal_table:
                raise CalibrationError("Failed to perform gain calibration")
            
            # Prepare mask path if needed
            mask_path = None
            if self.config.get('imaging', {}).get('use_clean_mask', False):
                mask_path = self._prepare_mask_path(block)
            
            result = {
                'success': True,
                'bcal_table': bcal_table,
                'gcal_table': gcal_table,
                'cl_path': cl_path,
                'mask_path': mask_path,
                'center_coord': center_coord
            }
            
            logger.info(f"Calibration setup completed for block {block.block_id}")
            return result
            
        except Exception as e:
            logger.error(f"Calibration setup failed for block {block.block_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'bcal_table': None,
                'gcal_table': None,
                'cl_path': None,
                'mask_path': None
            }
    
    def _find_latest_bcal_table(self, block_end_time: Time) -> Optional[str]:
        """
        Find the latest bandpass calibration table created before the block end time.
        
        Args:
            block_end_time: End time of the processing block
            
        Returns:
            Path to the bandpass calibration table, or None if not found
        """
        cal_tables_dir = self.paths_config.get('cal_tables_dir')
        if not cal_tables_dir:
            raise CalibrationError("Calibration tables directory not configured")
        
        bcal_files = sorted(glob.glob(os.path.join(cal_tables_dir, "*.bcal")))
        if not bcal_files:
            raise CalibrationError(f"No bandpass calibration tables found in {cal_tables_dir}")
        
        # Find the most recent table created before the block end time
        valid_bcals = []
        for bcal_file in bcal_files:
            try:
                file_mtime = os.path.getmtime(bcal_file)
                file_time = Time(file_mtime, format='unix', scale='utc')
                if file_time <= block_end_time:
                    valid_bcals.append((file_time, bcal_file))
            except Exception as e:
                logger.warning(f"Could not get modification time for {bcal_file}: {e}")
                continue
        
        if not valid_bcals:
            logger.warning("No bandpass calibration table found created before block end time")
            # Use the newest overall table as fallback
            return bcal_files[-1]
        
        # Return the most recent valid table
        valid_bcals.sort(key=lambda x: x[0])
        latest_bcal = valid_bcals[-1][1]
        logger.info(f"Using bandpass calibration table: {os.path.basename(latest_bcal)}")
        return latest_bcal
    
    def _calculate_block_center(self, block) -> SkyCoord:
        """
        Calculate the center coordinates for a processing block.
        
        Args:
            block: ProcessingBlock object
            
        Returns:
            SkyCoord object representing the block center
        """
        # Calculate block center time
        block_center_time = block.start_time + (block.end_time - block.start_time) / 2.0
        
        # Get telescope location
        telescope_loc = get_telescope_location()
        
        # Calculate center RA = LST at center time
        center_lst = block_center_time.sidereal_time('apparent', longitude=telescope_loc.lon)
        center_ra = center_lst.to(u.deg)
        
        # Get fixed declination from config
        fixed_dec_deg = self.cal_config.get('fixed_declination_deg')
        if fixed_dec_deg is None:
            raise CalibrationError("Fixed declination not configured")
        
        center_dec = fixed_dec_deg * u.deg
        center_coord = SkyCoord(ra=center_ra, dec=center_dec, frame='icrs')
        
        logger.info(f"Calculated block center coordinate: {center_coord.to_string('hmsdms')}")
        return center_coord
    
    async def _generate_sky_model(self, block, center_coord: SkyCoord) -> Optional[str]:
        """
        Generate a sky model component list for the block.
        
        Args:
            block: ProcessingBlock object
            center_coord: Center coordinates for the block
            
        Returns:
            Path to the component list file, or None if failed
        """
        try:
            skymodels_dir = self.paths_config.get('skymodels_dir')
            if not skymodels_dir:
                raise CalibrationError("Sky models directory not configured")
            
            os.makedirs(skymodels_dir, exist_ok=True)
            
            # Generate component list filename
            cl_filename = f"sky_field_{block.start_time.strftime('%Y%m%dT%H%M%S')}.cl"
            cl_output_path = os.path.join(skymodels_dir, cl_filename)
            
            # Create the sky model
            cl_path = await self.skymodel_manager.create_field_component_list(
                center_coord, cl_output_path
            )
            
            if cl_path:
                logger.info(f"Generated sky model: {os.path.basename(cl_path)}")
            else:
                logger.error("Failed to generate sky model")
            
            return cl_path
            
        except Exception as e:
            logger.error(f"Sky model generation failed: {e}")
            return None
    
    async def _perform_gain_calibration(self, block, cl_path: str) -> Optional[str]:
        """
        Perform gain calibration for the block.
        
        Args:
            block: ProcessingBlock object
            cl_path: Path to the component list file
            
        Returns:
            Path to the gain calibration table, or None if failed
        """
        try:
            cal_tables_dir = self.paths_config.get('cal_tables_dir')
            if not cal_tables_dir:
                raise CalibrationError("Calibration tables directory not configured")
            
            os.makedirs(cal_tables_dir, exist_ok=True)
            
            # Generate gain calibration table filename
            time_segment_str = f"{block.start_time.strftime('%Y%m%dT%H%M%S')}_{block.end_time.strftime('%Y%m%dT%H%M%S')}"
            gcal_table_name = f"gain_{time_segment_str}.gcal"
            gcal_table_path = os.path.join(cal_tables_dir, gcal_table_name)
            
            # Import CASA tasks
            try:
                from casatasks import gaincal, ft, clearcal
                casa_available = True
            except ImportError:
                logger.error("CASA tasks not available for gain calibration")
                return None
            
            # Apply sky model to MS files and perform gain calibration
            for ms_path in block.ms_files:
                if not os.path.exists(ms_path):
                    logger.error(f"MS file not found: {ms_path}")
                    continue
                
                try:
                    # Clear any existing model
                    clearcal(vis=ms_path, addmodel=True)
                    
                    # Apply sky model
                    ft(vis=ms_path, complist=cl_path, usescratch=True)
                    
                except Exception as e:
                    logger.error(f"Failed to apply sky model to {ms_path}: {e}")
                    continue
            
            # Perform gain calibration
            try:
                gaincal(
                    vis=block.ms_files,
                    caltable=gcal_table_path,
                    gaintype='G',
                    refant=self.cal_config.get('gcal_refant', ''),
                    calmode=self.cal_config.get('gcal_mode', 'ap'),
                    solint=self.cal_config.get('gcal_solint', '30min'),
                    minsnr=self.cal_config.get('gcal_minsnr', 3.0),
                    uvrange=self.cal_config.get('gcal_uvrange', ''),
                    combine='scan',
                    append=False
                )
                
                logger.info(f"Gain calibration completed: {os.path.basename(gcal_table_path)}")
                return gcal_table_path
                
            except Exception as e:
                logger.error(f"Gain calibration failed: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Gain calibration setup failed: {e}")
            return None
    
    def _prepare_mask_path(self, block) -> str:
        """
        Prepare the path for a clean mask file.
        
        Args:
            block: ProcessingBlock object
            
        Returns:
            Path for the mask file
        """
        skymodels_dir = self.paths_config.get('skymodels_dir')
        mask_filename = f"mask_{block.start_time.strftime('%Y%m%dT%H%M%S')}.mask"
        return os.path.join(skymodels_dir, mask_filename)
    
    async def apply_calibration(self, ms_path: str, bcal_table: str, 
                              gcal_tables: List[str]) -> bool:
        """
        Apply calibration tables to an MS file.
        
        Args:
            ms_path: Path to the MS file
            bcal_table: Path to the bandpass calibration table
            gcal_tables: List of paths to gain calibration tables
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from casatasks import applycal
            casa_available = True
        except ImportError:
            logger.error("CASA tasks not available for calibration application")
            return False
        
        if not os.path.exists(ms_path):
            logger.error(f"MS file not found: {ms_path}")
            return False
        
        if not os.path.exists(bcal_table):
            logger.error(f"Bandpass calibration table not found: {bcal_table}")
            return False
        
        for gcal_table in gcal_tables:
            if not os.path.exists(gcal_table):
                logger.error(f"Gain calibration table not found: {gcal_table}")
                return False
        
        try:
            # Build list of tables for applycal
            gaintables = [bcal_table] + gcal_tables
            
            applycal(
                vis=ms_path,
                gaintable=gaintables,
                gainfield=[],
                interp=['nearest,linear'],
                calwt=False,
                flagbackup=False,
                applymode='calonly'
            )
            
            logger.info(f"Successfully applied calibration to {os.path.basename(ms_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply calibration to {ms_path}: {e}")
            return False
