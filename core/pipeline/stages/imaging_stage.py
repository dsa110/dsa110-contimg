# core/pipeline/stages/imaging_stage.py
"""
Imaging stage for DSA-110 pipeline.

This module handles all imaging-related operations including
tclean execution, mask creation, and FITS export.
"""

import os
import logging
from typing import Dict, Any, Optional
from shutil import rmtree

from ...utils.logging import get_logger
from ..exceptions import ImagingError

logger = get_logger(__name__)


class ImagingStage:
    """
    Handles imaging operations for the pipeline.
    
    This class consolidates imaging logic from the original
    imaging.py module and provides a cleaner interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the imaging stage.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.imaging_config = config.get('imaging', {})
        self.paths_config = config.get('paths', {})
    
    async def process_ms(self, ms_path: str, bcal_table: str, gcal_table: str,
                        cl_path: Optional[str] = None, mask_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a single MS file through imaging.
        
        This includes flagging, calibration application, and tclean execution.
        
        Args:
            ms_path: Path to the MS file
            bcal_table: Path to the bandpass calibration table
            gcal_table: Path to the gain calibration table
            cl_path: Path to the component list (optional)
            mask_path: Path to the clean mask (optional)
            
        Returns:
            Dictionary containing imaging results
        """
        logger.info(f"Processing MS file: {os.path.basename(ms_path)}")
        
        try:
            # Apply flagging
            if not await self._apply_flagging(ms_path):
                raise ImagingError("Flagging failed")
            
            # Apply calibration
            if not await self._apply_calibration(ms_path, bcal_table, [gcal_table]):
                raise ImagingError("Calibration application failed")
            
            # Run tclean
            image_result = await self._run_tclean(ms_path, cl_path, mask_path)
            if not image_result['success']:
                raise ImagingError(f"tclean failed: {image_result['error']}")
            
            # Export to FITS if requested
            if self.imaging_config.get('save_fits', True):
                fits_path = await self._export_to_fits(image_result['image_path'])
                if fits_path:
                    image_result['fits_path'] = fits_path
            
            logger.info(f"Successfully processed MS: {os.path.basename(ms_path)}")
            return {
                'success': True,
                'image_path': image_result['image_path'],
                'pb_path': image_result['pb_path'],
                'fits_path': image_result.get('fits_path')
            }
            
        except Exception as e:
            logger.error(f"MS processing failed for {ms_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'image_path': None,
                'pb_path': None,
                'fits_path': None
            }
    
    async def _apply_flagging(self, ms_path: str) -> bool:
        """
        Apply RFI and general flagging to an MS file.
        
        Args:
            ms_path: Path to the MS file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from casatasks import flagdata
            casa_available = True
        except ImportError:
            logger.error("CASA tasks not available for flagging")
            return False
        
        if not os.path.exists(ms_path):
            logger.error(f"MS file not found: {ms_path}")
            return False
        
        try:
            # RFI flagging with tfcrop
            flag_params = self.config.get('calibration', {}).get('flagging', {})
            flagdata(
                vis=ms_path,
                mode='tfcrop',
                datacolumn='data',
                field='',
                action='apply',
                timecutoff=flag_params.get('tfcrop_timecutoff', 4.0),
                freqcutoff=flag_params.get('tfcrop_freqcutoff', 4.0),
                flagbackup=False
            )
            
            # General flagging
            flagdata(vis=ms_path, mode='manual', autocorr=True, flagbackup=False, action='apply')
            flagdata(vis=ms_path, mode='shadow', tolerance=0.0, flagbackup=False, action='apply')
            flagdata(vis=ms_path, mode='clip', clipzeros=True, flagbackup=False, action='apply')
            
            logger.debug(f"Flagging completed for {os.path.basename(ms_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Flagging failed for {ms_path}: {e}")
            return False
    
    async def _apply_calibration(self, ms_path: str, bcal_table: str, 
                               gcal_tables: list) -> bool:
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
        
        # Check if all calibration tables exist
        if not os.path.exists(bcal_table):
            logger.error(f"Bandpass calibration table not found: {bcal_table}")
            return False
        
        for gcal_table in gcal_tables:
            if not os.path.exists(gcal_table):
                logger.error(f"Gain calibration table not found: {gcal_table}")
                return False
        
        try:
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
            
            logger.debug(f"Calibration applied to {os.path.basename(ms_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply calibration to {ms_path}: {e}")
            return False
    
    async def _run_tclean(self, ms_path: str, cl_path: Optional[str] = None,
                         mask_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run tclean on an MS file.
        
        Args:
            ms_path: Path to the MS file
            cl_path: Path to the component list (optional)
            mask_path: Path to the clean mask (optional)
            
        Returns:
            Dictionary containing tclean results
        """
        try:
            from casatasks import tclean
            casa_available = True
        except ImportError:
            logger.error("CASA tasks not available for imaging")
            return {'success': False, 'error': 'CASA not available'}
        
        if not os.path.exists(ms_path):
            logger.error(f"MS file not found: {ms_path}")
            return {'success': False, 'error': 'MS file not found'}
        
        # Generate output image name
        ms_base = os.path.splitext(os.path.basename(ms_path))[0]
        images_dir = self.paths_config.get('images_dir')
        if not images_dir:
            return {'success': False, 'error': 'Images directory not configured'}
        
        os.makedirs(images_dir, exist_ok=True)
        output_imagename = os.path.join(images_dir, ms_base)
        
        # Prepare tclean parameters
        tclean_params = {
            'vis': ms_path,
            'imagename': output_imagename,
            'specmode': 'mfs',
            'deconvolver': self.imaging_config.get('deconvolver', 'hogbom'),
            'gridder': self.imaging_config.get('gridder', 'wproject'),
            'wprojplanes': self.imaging_config.get('wprojplanes', -1),
            'niter': self.imaging_config.get('niter', 5000),
            'threshold': self.imaging_config.get('threshold', '1mJy'),
            'interactive': False,
            'imsize': self.imaging_config.get('image_size', [4800, 4800]),
            'cell': self.imaging_config.get('cell_size', '3arcsec'),
            'weighting': self.imaging_config.get('weighting', 'briggs'),
            'robust': self.imaging_config.get('robust', 0.5),
            'pblimit': self.imaging_config.get('pblimit', 0.1),
            'pbcor': True,
            'savemodel': 'modelcolumn'
        }
        
        # Add start model if provided
        if cl_path and os.path.exists(cl_path):
            tclean_params['startmodel'] = cl_path
            logger.info(f"Using start model: {os.path.basename(cl_path)}")
        
        # Add mask if provided
        use_mask = self.imaging_config.get('use_clean_mask', False)
        if use_mask and mask_path and os.path.exists(mask_path):
            tclean_params['usemask'] = 'user'
            tclean_params['mask'] = mask_path
            logger.info(f"Using user mask: {os.path.basename(mask_path)}")
        
        # Clean up previous run outputs
        self._cleanup_previous_outputs(output_imagename)
        
        try:
            # Run tclean
            tclean(**tclean_params)
            
            # Check for output files
            image_path = f"{output_imagename}.image"
            pb_path = f"{output_imagename}.pb"
            
            if not os.path.exists(image_path):
                return {'success': False, 'error': 'tclean output image missing'}
            
            if not os.path.exists(pb_path):
                return {'success': False, 'error': 'tclean output pb missing'}
            
            logger.info(f"tclean completed successfully: {os.path.basename(output_imagename)}")
            return {
                'success': True,
                'image_path': image_path,
                'pb_path': pb_path
            }
            
        except Exception as e:
            logger.error(f"tclean failed for {output_imagename}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _cleanup_previous_outputs(self, output_imagename: str):
        """
        Clean up previous tclean outputs to avoid conflicts.
        
        Args:
            output_imagename: Base name for tclean outputs
        """
        extensions = ['.image', '.mask', '.model', '.image.pbcor', '.psf', 
                     '.residual', '.pb', '.sumwt']
        
        for ext in extensions:
            product_path = f"{output_imagename}{ext}"
            if os.path.exists(product_path):
                try:
                    if os.path.isdir(product_path):
                        rmtree(product_path)
                    else:
                        os.remove(product_path)
                    logger.debug(f"Removed existing product: {product_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove existing product {product_path}: {e}")
    
    async def _export_to_fits(self, image_path: str) -> Optional[str]:
        """
        Export a CASA image to FITS format.
        
        Args:
            image_path: Path to the CASA image
            
        Returns:
            Path to the FITS file, or None if failed
        """
        try:
            from casatasks import exportfits
            casa_available = True
        except ImportError:
            logger.error("CASA tasks not available for FITS export")
            return None
        
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return None
        
        fits_path = f"{os.path.splitext(image_path)[0]}.fits"
        
        try:
            exportfits(imagename=image_path, fitsimage=fits_path, overwrite=True)
            logger.info(f"Exported FITS file: {os.path.basename(fits_path)}")
            return fits_path
            
        except Exception as e:
            logger.error(f"FITS export failed for {image_path}: {e}")
            return None
    
    async def create_clean_mask(self, cl_path: str, template_image_path: str,
                               output_mask_path: str) -> bool:
        """
        Create a clean mask from a component list using a template image.
        
        Args:
            cl_path: Path to the component list
            template_image_path: Path to the template image
            output_mask_path: Path for the output mask
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from casatasks import makemask
            casa_available = True
        except ImportError:
            logger.error("CASA tasks not available for mask creation")
            return False
        
        if not os.path.exists(cl_path):
            logger.error(f"Component list not found: {cl_path}")
            return False
        
        if not os.path.exists(template_image_path):
            logger.error(f"Template image not found: {template_image_path}")
            return False
        
        os.makedirs(os.path.dirname(output_mask_path), exist_ok=True)
        
        # Clean up existing mask
        if os.path.exists(output_mask_path):
            try:
                if os.path.isdir(output_mask_path):
                    rmtree(output_mask_path)
                else:
                    os.remove(output_mask_path)
            except Exception as e:
                logger.warning(f"Failed to remove existing mask: {e}")
        
        try:
            makemask(
                mode='copy',
                inpimage=template_image_path,
                inpmask=cl_path,
                output=f"'{output_mask_path}:mask0'",
                overwrite=True
            )
            
            logger.info(f"Created clean mask: {os.path.basename(output_mask_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Mask creation failed: {e}")
            return False
