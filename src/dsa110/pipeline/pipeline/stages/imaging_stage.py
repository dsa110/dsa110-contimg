# core/pipeline/stages/imaging_stage.py
"""
Imaging stage for DSA-110 pipeline.

This module handles all imaging-related operations including
tclean execution, mask creation, and FITS export.
"""

import os
import logging
import asyncio
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from shutil import rmtree
from astropy.coordinates import SkyCoord
import astropy.units as u

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
                        cl_path: Optional[str] = None, mask_path: Optional[str] = None,
                        max_retries: int = 3) -> Dict[str, Any]:
        """
        Process a single MS file through imaging with retry logic.
        
        This includes flagging, calibration application, and tclean execution.
        
        Args:
            ms_path: Path to the MS file
            bcal_table: Path to the bandpass calibration table
            gcal_table: Path to the gain calibration table
            cl_path: Path to the component list (optional)
            mask_path: Path to the clean mask (optional)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary containing imaging results
        """
        logger.info(f"Processing MS file: {os.path.basename(ms_path)}")
        
        for attempt in range(max_retries + 1):
            try:
                # Apply flagging
                if not await self._apply_flagging(ms_path):
                    raise ImagingError("Flagging failed")
                
                # Apply calibration
                if not await self._apply_calibration(ms_path, bcal_table, [gcal_table]):
                    raise ImagingError("Calibration application failed")
                
                # Run tclean with DSA-110 optimization
                image_result = await self._run_tclean_optimized(ms_path, cl_path, mask_path)
                if not image_result['success']:
                    raise ImagingError(f"tclean failed: {image_result['error']}")
                
                # Assess image quality
                quality_metrics = await self._assess_image_quality(image_result['image_path'])
                image_result['quality_metrics'] = quality_metrics
                
                # Export to FITS if requested
                if self.imaging_config.get('save_fits', True):
                    fits_path = await self._export_to_fits(image_result['image_path'])
                    if fits_path:
                        image_result['fits_path'] = fits_path
                
                logger.info(f"Successfully processed MS: {os.path.basename(ms_path)}")
                logger.info(f"Image quality score: {quality_metrics.get('overall_quality_score', 'N/A')}")
                
                return {
                    'success': True,
                    'image_path': image_result['image_path'],
                    'pb_path': image_result['pb_path'],
                    'fits_path': image_result.get('fits_path'),
                    'quality_metrics': quality_metrics
                }
                
            except Exception as e:
                if attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.warning(f"MS processing failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                 f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"MS processing failed after {max_retries + 1} attempts: {e}")
                    return {
                        'success': False,
                        'error': str(e),
                        'image_path': None,
                        'pb_path': None,
                        'fits_path': None,
                        'quality_metrics': None
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
    
    async def _run_tclean_optimized(self, ms_path: str, cl_path: Optional[str] = None,
                                   mask_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Run tclean with DSA-110 specific optimizations.
        
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
        
        # Get DSA-110 optimized parameters
        tclean_params = self._get_dsa110_optimized_params(ms_path, output_imagename)
        
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
        elif use_mask:
            # Generate automatic mask
            auto_mask_path = await self._generate_automatic_mask(ms_path, output_imagename)
            if auto_mask_path:
                tclean_params['usemask'] = 'user'
                tclean_params['mask'] = auto_mask_path
                logger.info(f"Using automatic mask: {os.path.basename(auto_mask_path)}")
        
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
    
    def _get_dsa110_optimized_params(self, ms_path: str, output_imagename: str) -> Dict[str, Any]:
        """
        Get DSA-110 optimized tclean parameters.
        
        Args:
            ms_path: Path to the MS file
            output_imagename: Base name for tclean outputs
            
        Returns:
            Dictionary of tclean parameters optimized for DSA-110
        """
        # Base parameters
        params = {
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
        
        # DSA-110 specific optimizations
        # Use more aggressive cleaning for DSA-110's wide field
        params['niter'] = min(params['niter'], 10000)  # Cap iterations for performance
        
        # Optimize for DSA-110's frequency range and resolution
        if 'cell' not in self.imaging_config:
            # Auto-determine cell size based on frequency
            try:
                import casacore.tables as pt
                with pt.table(ms_path) as main_table:
                    if 'SPECTRAL_WINDOW' in main_table.colnames():
                        spw_table = pt.table(f"{ms_path}/SPECTRAL_WINDOW")
                        ref_freq = spw_table.getcol('REF_FREQUENCY')[0]  # Hz
                        # Use Nyquist sampling: λ/(2*D) where D is baseline length
                        # For DSA-110, typical baseline ~100m, so cell ~λ/200
                        wavelength = 3e8 / ref_freq  # meters
                        optimal_cell_rad = wavelength / (2 * 100)  # radians
                        optimal_cell_arcsec = np.degrees(optimal_cell_rad) * 3600
                        # Round to reasonable value
                        if optimal_cell_arcsec < 1:
                            params['cell'] = '0.5arcsec'
                        elif optimal_cell_arcsec < 3:
                            params['cell'] = '1arcsec'
                        else:
                            params['cell'] = '3arcsec'
                        logger.info(f"Auto-determined cell size: {params['cell']} (freq: {ref_freq/1e9:.1f} GHz)")
            except Exception as e:
                logger.warning(f"Could not auto-determine cell size: {e}")
        
        # Adaptive threshold based on data quality
        if 'threshold' not in self.imaging_config:
            # Use a more conservative threshold for DSA-110
            params['threshold'] = '0.5mJy'
        
        # Memory optimization for large images
        if params['imsize'][0] > 4000:
            params['parallel'] = True
            params['parallel_algorithm'] = 'auto'
        
        return params
    
    async def _assess_image_quality(self, image_path: str) -> Dict[str, Any]:
        """
        Assess the quality of a generated image.
        
        Args:
            image_path: Path to the CASA image
            
        Returns:
            Dictionary containing quality metrics
        """
        logger.info(f"Assessing image quality: {os.path.basename(image_path)}")
        
        quality_metrics = {
            'overall_quality_score': 0.0,
            'dynamic_range': 0.0,
            'rms_noise': 0.0,
            'peak_flux': 0.0,
            'image_size_mb': 0.0,
            'warnings': [],
            'errors': []
        }
        
        try:
            import casacore.tables as pt
            
            with pt.table(image_path) as image_table:
                # Get image data
                image_data = image_table.getcol('map')
                
                if len(image_data) == 0:
                    quality_metrics['errors'].append("Image data is empty")
                    return quality_metrics
                
                # Calculate basic statistics
                image_flat = image_data.flatten()
                valid_data = image_flat[~np.isnan(image_flat)]
                
                if len(valid_data) == 0:
                    quality_metrics['errors'].append("No valid image data found")
                    return quality_metrics
                
                # Calculate metrics
                quality_metrics['peak_flux'] = float(np.max(valid_data))
                quality_metrics['rms_noise'] = float(np.std(valid_data))
                
                if quality_metrics['rms_noise'] > 0:
                    quality_metrics['dynamic_range'] = quality_metrics['peak_flux'] / quality_metrics['rms_noise']
                
                # Calculate image size
                quality_metrics['image_size_mb'] = os.path.getsize(image_path) / (1024 * 1024)
                
                # Quality checks
                if quality_metrics['dynamic_range'] < 10:
                    quality_metrics['warnings'].append("Low dynamic range")
                elif quality_metrics['dynamic_range'] > 1000:
                    quality_metrics['warnings'].append("Very high dynamic range - possible artifacts")
                
                if quality_metrics['rms_noise'] > 0.01:  # 10 mJy
                    quality_metrics['warnings'].append("High RMS noise")
                
                # Calculate overall quality score
                quality_metrics['overall_quality_score'] = self._calculate_image_quality_score(quality_metrics)
                
        except ImportError:
            quality_metrics['warnings'].append("casacore not available for detailed quality assessment")
            quality_metrics['overall_quality_score'] = 5.0  # Default score
        except Exception as e:
            quality_metrics['errors'].append(f"Quality assessment error: {e}")
            quality_metrics['overall_quality_score'] = 0.0
        
        logger.info(f"Image quality score: {quality_metrics['overall_quality_score']:.2f}/10.0")
        return quality_metrics
    
    def _calculate_image_quality_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate overall image quality score.
        
        Args:
            metrics: Dictionary of image quality metrics
            
        Returns:
            Quality score from 0.0 to 10.0
        """
        score = 10.0
        
        # Dynamic range scoring
        dynamic_range = metrics.get('dynamic_range', 0)
        if dynamic_range < 5:
            score -= 3.0
        elif dynamic_range < 10:
            score -= 1.5
        elif dynamic_range > 1000:
            score -= 1.0  # Possible artifacts
        
        # RMS noise scoring
        rms_noise = metrics.get('rms_noise', 0)
        if rms_noise > 0.01:  # 10 mJy
            score -= 2.0
        elif rms_noise > 0.005:  # 5 mJy
            score -= 1.0
        
        # Peak flux scoring
        peak_flux = metrics.get('peak_flux', 0)
        if peak_flux < 0.001:  # 1 mJy
            score -= 2.0
        elif peak_flux < 0.01:  # 10 mJy
            score -= 1.0
        
        # Penalize for warnings
        warning_count = len(metrics.get('warnings', []))
        score -= warning_count * 0.5
        
        # Penalize for errors
        error_count = len(metrics.get('errors', []))
        score -= error_count * 2.0
        
        return max(0.0, round(score, 2))
    
    async def _generate_automatic_mask(self, ms_path: str, output_imagename: str) -> Optional[str]:
        """
        Generate an automatic clean mask from the data.
        
        Args:
            ms_path: Path to the MS file
            output_imagename: Base name for outputs
            
        Returns:
            Path to the generated mask, or None if failed
        """
        try:
            from casatasks import tclean
            casa_available = True
        except ImportError:
            logger.error("CASA tasks not available for mask generation")
            return None
        
        mask_path = f"{output_imagename}.auto_mask"
        
        try:
            # Run a quick tclean to generate a mask
            tclean(
                vis=ms_path,
                imagename=f"{output_imagename}.mask_temp",
                specmode='mfs',
                deconvolver='multiscale',
                scales=[0, 6, 18, 54],
                niter=1000,
                threshold='0.5mJy',
                interactive=False,
                imsize=self.imaging_config.get('image_size', [4800, 4800]),
                cell=self.imaging_config.get('cell_size', '3arcsec'),
                weighting=self.imaging_config.get('weighting', 'briggs'),
                robust=self.imaging_config.get('robust', 0.5),
                usemask='auto-multithresh',
                pbmask=0.1,
                savemodel='none'
            )
            
            # Copy the generated mask
            temp_mask = f"{output_imagename}.mask_temp.mask"
            if os.path.exists(temp_mask):
                import shutil
                shutil.copy2(temp_mask, mask_path)
                os.remove(temp_mask)
                logger.info(f"Generated automatic mask: {os.path.basename(mask_path)}")
                return mask_path
            
        except Exception as e:
            logger.warning(f"Automatic mask generation failed: {e}")
        
        return None
    
    async def process_multiple_ms(self, ms_files: List[str], bcal_table: str, gcal_table: str,
                                 cl_path: Optional[str] = None, mask_path: Optional[str] = None,
                                 max_concurrent: int = 2) -> Dict[str, Any]:
        """
        Process multiple MS files with parallel processing and memory management.
        
        Args:
            ms_files: List of MS file paths
            bcal_table: Path to the bandpass calibration table
            gcal_table: Path to the gain calibration table
            cl_path: Path to the component list (optional)
            mask_path: Path to the clean mask (optional)
            max_concurrent: Maximum number of concurrent processing tasks
            
        Returns:
            Dictionary containing processing results
        """
        logger.info(f"Processing {len(ms_files)} MS files with max {max_concurrent} concurrent tasks")
        
        results = {
            'successful': [],
            'failed': [],
            'total_processed': 0,
            'total_successful': 0,
            'total_failed': 0,
            'quality_metrics': {
                'average_quality_score': 0.0,
                'best_quality_score': 0.0,
                'worst_quality_score': 10.0
            }
        }
        
        # Process MS files in batches to manage memory
        batch_size = min(max_concurrent, len(ms_files))
        
        for i in range(0, len(ms_files), batch_size):
            batch = ms_files[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} files")
            
            # Process batch concurrently
            tasks = []
            for ms_path in batch:
                task = self.process_ms(ms_path, bcal_table, gcal_table, cl_path, mask_path)
                tasks.append(task)
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                ms_path = batch[j]
                results['total_processed'] += 1
                
                if isinstance(result, Exception):
                    logger.error(f"Exception processing {ms_path}: {result}")
                    results['failed'].append({
                        'ms_path': ms_path,
                        'error': str(result),
                        'quality_metrics': None
                    })
                    results['total_failed'] += 1
                elif result.get('success', False):
                    results['successful'].append(result)
                    results['total_successful'] += 1
                    
                    # Update quality metrics
                    quality_score = result.get('quality_metrics', {}).get('overall_quality_score', 0)
                    results['quality_metrics']['best_quality_score'] = max(
                        results['quality_metrics']['best_quality_score'], quality_score
                    )
                    results['quality_metrics']['worst_quality_score'] = min(
                        results['quality_metrics']['worst_quality_score'], quality_score
                    )
                else:
                    results['failed'].append(result)
                    results['total_failed'] += 1
            
            # Memory cleanup between batches
            await self._cleanup_memory()
        
        # Calculate average quality score
        if results['total_successful'] > 0:
            total_quality = sum(
                result.get('quality_metrics', {}).get('overall_quality_score', 0)
                for result in results['successful']
            )
            results['quality_metrics']['average_quality_score'] = round(
                total_quality / results['total_successful'], 2
            )
        
        success_rate = (results['total_successful'] / results['total_processed']) * 100 if results['total_processed'] > 0 else 0
        
        logger.info(f"Batch processing complete: {results['total_successful']}/{results['total_processed']} "
                   f"successful ({success_rate:.1f}%)")
        logger.info(f"Average quality score: {results['quality_metrics']['average_quality_score']:.2f}/10.0")
        
        return results
    
    async def _cleanup_memory(self):
        """
        Perform memory cleanup between processing batches.
        """
        try:
            import gc
            gc.collect()
            logger.debug("Memory cleanup completed")
        except Exception as e:
            logger.warning(f"Memory cleanup failed: {e}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage information.
        
        Returns:
            Dictionary containing memory usage metrics
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / (1024 * 1024),  # Resident Set Size
                'vms_mb': memory_info.vms / (1024 * 1024),  # Virtual Memory Size
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / (1024 * 1024)
            }
        except ImportError:
            logger.warning("psutil not available for memory monitoring")
            return {
                'rss_mb': 0,
                'vms_mb': 0,
                'percent': 0,
                'available_mb': 0
            }
        except Exception as e:
            logger.warning(f"Memory monitoring failed: {e}")
            return {
                'rss_mb': 0,
                'vms_mb': 0,
                'percent': 0,
                'available_mb': 0
            }
    
    async def adaptive_imaging(self, ms_path: str, bcal_table: str, gcal_table: str,
                              cl_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform adaptive imaging based on data quality assessment.
        
        Args:
            ms_path: Path to the MS file
            bcal_table: Path to the bandpass calibration table
            gcal_table: Path to the gain calibration table
            cl_path: Path to the component list (optional)
            
        Returns:
            Dictionary containing imaging results
        """
        logger.info(f"Performing adaptive imaging for: {os.path.basename(ms_path)}")
        
        # First, assess data quality
        data_quality = await self._assess_data_quality(ms_path)
        
        # Adjust imaging parameters based on quality
        imaging_params = self._get_adaptive_imaging_params(data_quality)
        
        # Update imaging config temporarily
        original_config = self.imaging_config.copy()
        self.imaging_config.update(imaging_params)
        
        try:
            # Process with adaptive parameters
            result = await self.process_ms(ms_path, bcal_table, gcal_table, cl_path)
            result['adaptive_params'] = imaging_params
            result['data_quality'] = data_quality
            
            return result
        finally:
            # Restore original config
            self.imaging_config = original_config
    
    async def _assess_data_quality(self, ms_path: str) -> Dict[str, Any]:
        """
        Assess the quality of input data to determine optimal imaging parameters.
        
        Args:
            ms_path: Path to the MS file
            
        Returns:
            Dictionary containing data quality metrics
        """
        quality_metrics = {
            'data_volume_mb': 0,
            'baseline_count': 0,
            'frequency_coverage_ghz': 0,
            'time_coverage_hours': 0,
            'uv_coverage_score': 0.0,
            'recommended_imaging_params': {}
        }
        
        try:
            import casacore.tables as pt
            
            with pt.table(ms_path) as main_table:
                # Get basic data metrics
                nrows = main_table.nrows()
                quality_metrics['data_volume_mb'] = os.path.getsize(ms_path) / (1024 * 1024)
                
                # Get baseline information
                if 'ANTENNA1' in main_table.colnames() and 'ANTENNA2' in main_table.colnames():
                    ant1 = main_table.getcol('ANTENNA1')
                    ant2 = main_table.getcol('ANTENNA2')
                    unique_baselines = len(set(zip(ant1, ant2)))
                    quality_metrics['baseline_count'] = unique_baselines
                
                # Get frequency information
                if 'SPECTRAL_WINDOW' in main_table.colnames():
                    spw_table = pt.table(f"{ms_path}/SPECTRAL_WINDOW")
                    ref_freqs = spw_table.getcol('REF_FREQUENCY')
                    if len(ref_freqs) > 0:
                        freq_range = (np.max(ref_freqs) - np.min(ref_freqs)) / 1e9  # GHz
                        quality_metrics['frequency_coverage_ghz'] = freq_range
                
                # Get time information
                if 'TIME' in main_table.colnames():
                    times = main_table.getcol('TIME')
                    if len(times) > 0:
                        time_range = (np.max(times) - np.min(times)) / 3600  # hours
                        quality_metrics['time_coverage_hours'] = time_range
                
                # Calculate UV coverage score
                quality_metrics['uv_coverage_score'] = self._calculate_uv_coverage_score(quality_metrics)
                
                # Recommend imaging parameters
                quality_metrics['recommended_imaging_params'] = self._recommend_imaging_params(quality_metrics)
                
        except ImportError:
            logger.warning("casacore not available for data quality assessment")
        except Exception as e:
            logger.warning(f"Data quality assessment failed: {e}")
        
        return quality_metrics
    
    def _calculate_uv_coverage_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate UV coverage score based on data metrics.
        
        Args:
            metrics: Dictionary of data quality metrics
            
        Returns:
            UV coverage score from 0.0 to 10.0
        """
        score = 5.0  # Base score
        
        # Baseline count scoring
        baseline_count = metrics.get('baseline_count', 0)
        if baseline_count > 1000:
            score += 2.0
        elif baseline_count > 500:
            score += 1.0
        elif baseline_count < 100:
            score -= 2.0
        
        # Frequency coverage scoring
        freq_coverage = metrics.get('frequency_coverage_ghz', 0)
        if freq_coverage > 1.0:
            score += 1.5
        elif freq_coverage > 0.5:
            score += 1.0
        elif freq_coverage < 0.1:
            score -= 1.0
        
        # Time coverage scoring
        time_coverage = metrics.get('time_coverage_hours', 0)
        if time_coverage > 2.0:
            score += 1.5
        elif time_coverage > 1.0:
            score += 1.0
        elif time_coverage < 0.5:
            score -= 1.0
        
        return max(0.0, min(10.0, round(score, 2)))
    
    def _recommend_imaging_params(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend imaging parameters based on data quality.
        
        Args:
            metrics: Dictionary of data quality metrics
            
        Returns:
            Dictionary of recommended imaging parameters
        """
        params = {}
        
        uv_score = metrics.get('uv_coverage_score', 5.0)
        data_volume = metrics.get('data_volume_mb', 0)
        
        # Adjust image size based on UV coverage
        if uv_score > 8.0:
            params['image_size'] = [4800, 4800]
        elif uv_score > 6.0:
            params['image_size'] = [2400, 2400]
        else:
            params['image_size'] = [1200, 1200]
        
        # Adjust cell size based on frequency coverage
        freq_coverage = metrics.get('frequency_coverage_ghz', 0)
        if freq_coverage > 1.0:
            params['cell_size'] = '1arcsec'
        elif freq_coverage > 0.5:
            params['cell_size'] = '2arcsec'
        else:
            params['cell_size'] = '3arcsec'
        
        # Adjust threshold based on data volume
        if data_volume > 1000:  # > 1GB
            params['threshold'] = '0.5mJy'
        elif data_volume > 500:  # > 500MB
            params['threshold'] = '1mJy'
        else:
            params['threshold'] = '2mJy'
        
        # Adjust iterations based on UV coverage
        if uv_score > 8.0:
            params['niter'] = 10000
        elif uv_score > 6.0:
            params['niter'] = 5000
        else:
            params['niter'] = 2000
        
        return params
    
    def _get_adaptive_imaging_params(self, data_quality: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get adaptive imaging parameters based on data quality.
        
        Args:
            data_quality: Dictionary of data quality metrics
            
        Returns:
            Dictionary of adaptive imaging parameters
        """
        return data_quality.get('recommended_imaging_params', {})
