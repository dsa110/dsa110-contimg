"""
CASA Imaging Pipeline for DSA-110

This module provides comprehensive CASA-based imaging functionality
for the DSA-110 continuum imaging pipeline, including advanced tclean
parameters, deconvolution strategies, and image quality assessment.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import numpy as np
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u

from casatools import ms, image, imager
from casatasks import tclean, exportfits, imhead, imstat, imval

from core.utils.logging import get_logger
from core.telescope.dsa110 import get_telescope_location, get_primary_beam_model
from core.telescope.beam_models import GaussianBeamModel, AiryDiskBeamModel

logger = get_logger(__name__)


class CASAImagingPipeline:
    """
    Comprehensive CASA imaging pipeline for DSA-110.
    
    This class provides advanced imaging capabilities using CASA tclean,
    including multiple deconvolution strategies, weighting schemes,
    and image quality assessment.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the CASA imaging pipeline.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.imaging_config = config.get('imaging', {})
        self.paths_config = config.get('paths', {})
        self.telescope_config = config.get('telescope', {})
        
        # Initialize CASA tools
        self.ms_tool = ms()
        self.image_tool = image()
        self.imager_tool = imager()
        
        # Set up paths
        self.images_dir = Path(self.paths_config.get('images_dir', 'images'))
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Imaging parameters
        self.default_params = self.imaging_config.get('default', {})
        self.deconvolution_config = self.imaging_config.get('deconvolution', {})
        self.weighting_config = self.imaging_config.get('weighting', {})
        self.primary_beam_config = self.imaging_config.get('primary_beam', {})
        
        # Initialize primary beam model
        self.pb_model = self._initialize_primary_beam_model()
        
    def _initialize_primary_beam_model(self):
        """Initialize the primary beam model for DSA-110."""
        pb_type = self.primary_beam_config.get('type', 'gaussian')
        
        if pb_type == 'gaussian':
            return GaussianBeamModel(
                diameter=self.telescope_config.get('diameter', 4.5),
                frequency=self.primary_beam_config.get('frequency', 1.4e9)
            )
        elif pb_type == 'airy':
            return AiryDiskBeamModel(
                diameter=self.telescope_config.get('diameter', 4.5),
                frequency=self.primary_beam_config.get('frequency', 1.4e9)
            )
        else:
            logger.warning(f"Unknown primary beam type: {pb_type}, using Gaussian")
            return GaussianBeamModel(
                diameter=self.telescope_config.get('diameter', 4.5),
                frequency=self.primary_beam_config.get('frequency', 1.4e9)
            )
    
    async def run_advanced_imaging(self, ms_path: str, 
                                 image_name: Optional[str] = None,
                                 imaging_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run advanced imaging with multiple deconvolution strategies.
        
        Args:
            ms_path: Path to the measurement set
            image_name: Optional custom image name
            imaging_params: Optional custom imaging parameters
            
        Returns:
            Dictionary with imaging results
        """
        logger.info(f"Starting advanced imaging for {os.path.basename(ms_path)}")
        
        # Generate image name if not provided
        if not image_name:
            image_name = f"{Path(ms_path).stem}_image"
        
        image_path = self.images_dir / image_name
        
        results = {
            'ms_path': ms_path,
            'image_name': image_name,
            'image_path': str(image_path),
            'success': False,
            'images_created': [],
            'quality_metrics': {},
            'errors': []
        }
        
        try:
            # Step 1: Data inspection and parameter optimization
            logger.info("Step 1: Data inspection and parameter optimization")
            inspection_result = await self._inspect_imaging_data(ms_path)
            if not inspection_result['success']:
                results['errors'].append("Data inspection failed")
                return results
            
            # Step 2: Generate optimal imaging parameters
            logger.info("Step 2: Generate optimal imaging parameters")
            optimal_params = await self._generate_imaging_parameters(
                ms_path, inspection_result, imaging_params
            )
            
            # Step 3: Run multi-scale imaging
            logger.info("Step 3: Run multi-scale imaging")
            multiscale_result = await self._run_multiscale_imaging(
                ms_path, image_name, optimal_params
            )
            if multiscale_result['success']:
                results['images_created'].append(multiscale_result['image_path'])
            
            # Step 4: Run Briggs weighting imaging
            logger.info("Step 4: Run Briggs weighting imaging")
            briggs_result = await self._run_briggs_imaging(
                ms_path, f"{image_name}_briggs", optimal_params
            )
            if briggs_result['success']:
                results['images_created'].append(briggs_result['image_path'])
            
            # Step 5: Run uniform weighting imaging
            logger.info("Step 5: Run uniform weighting imaging")
            uniform_result = await self._run_uniform_imaging(
                ms_path, f"{image_name}_uniform", optimal_params
            )
            if uniform_result['success']:
                results['images_created'].append(uniform_result['image_path'])
            
            # Step 6: Image quality assessment
            logger.info("Step 6: Image quality assessment")
            quality_result = await self._assess_image_quality(results['images_created'])
            results['quality_metrics'] = quality_result
            
            # Step 7: Export to FITS
            logger.info("Step 7: Export to FITS")
            fits_result = await self._export_images_to_fits(results['images_created'])
            results['fits_files'] = fits_result.get('fits_files', [])
            
            if results['images_created']:
                results['success'] = True
                logger.info(f"Advanced imaging completed: {len(results['images_created'])} images created")
            else:
                results['errors'].append("No images were created successfully")
                
        except Exception as e:
            logger.error(f"Advanced imaging failed: {e}")
            results['errors'].append(str(e))
            
        return results
    
    async def _inspect_imaging_data(self, ms_path: str) -> Dict[str, Any]:
        """
        Inspect measurement set for imaging optimization.
        
        Args:
            ms_path: Path to the measurement set
            
        Returns:
            Dictionary with inspection results
        """
        try:
            # Open MS
            self.ms_tool.open(ms_path)
            
            # Get basic information
            n_rows = self.ms_tool.nrow()
            summary = self.ms_tool.summary()
            
            # Get frequency information
            spw_info = summary.get('spectralWindow', {})
            if spw_info:
                # Get frequency range
                freq_info = list(spw_info.values())[0]
                freq_center = freq_info.get('refFreq', 1.4e9)
                freq_width = freq_info.get('totalWidth', 100e6)
                n_channels = freq_info.get('numChan', 1)
            else:
                freq_center = 1.4e9
                freq_width = 100e6
                n_channels = 1
            
            # Get antenna information
            antenna_info = summary.get('antenna', {})
            n_antennas = len(antenna_info) if antenna_info else 0
            
            # Get baseline information
            n_baselines = n_antennas * (n_antennas - 1) // 2
            
            # Calculate optimal cell size and image size
            wavelength = 3e8 / freq_center
            max_baseline = self._estimate_max_baseline(ms_path)
            min_cell_size = wavelength / (2 * max_baseline) * 180 / np.pi * 3600  # arcsec
            
            # Recommended cell size (1/5 of the resolution)
            recommended_cell_size = min_cell_size / 5
            
            # Calculate image size (should be at least 2x the primary beam)
            pb_fwhm = self.pb_model.get_fwhm(freq_center) * 180 / np.pi * 3600  # arcsec
            recommended_imsize = int(2 * pb_fwhm / recommended_cell_size)
            
            # Ensure image size is reasonable
            recommended_imsize = max(512, min(4096, recommended_imsize))
            
            self.ms_tool.close()
            self.ms_tool.done()
            
            logger.info(f"Data inspection: {n_rows:,} rows, {n_antennas} antennas, "
                       f"freq={freq_center/1e9:.2f} GHz, cell_size={recommended_cell_size:.2f} arcsec")
            
            return {
                'success': True,
                'n_rows': n_rows,
                'n_antennas': n_antennas,
                'n_baselines': n_baselines,
                'frequency_center': freq_center,
                'frequency_width': freq_width,
                'n_channels': n_channels,
                'max_baseline': max_baseline,
                'recommended_cell_size': recommended_cell_size,
                'recommended_imsize': recommended_imsize,
                'primary_beam_fwhm': pb_fwhm
            }
            
        except Exception as e:
            logger.error(f"Data inspection failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _estimate_max_baseline(self, ms_path: str) -> float:
        """
        Estimate maximum baseline length from UV coordinates.
        
        Args:
            ms_path: Path to the measurement set
            
        Returns:
            Maximum baseline length in meters
        """
        try:
            self.ms_tool.open(ms_path)
            
            # Get UV coordinates
            data = self.ms_tool.getdata(['uvw'])
            uvw = data['uvw']
            
            # Calculate baseline lengths
            baseline_lengths = np.sqrt(uvw[0]**2 + uvw[1]**2 + uvw[2]**2)
            max_baseline = np.max(baseline_lengths)
            
            self.ms_tool.close()
            self.ms_tool.done()
            
            return max_baseline
            
        except Exception as e:
            logger.warning(f"Could not estimate max baseline: {e}")
            return 1000.0  # Default value
    
    async def _generate_imaging_parameters(self, ms_path: str, 
                                         inspection_result: Dict[str, Any],
                                         custom_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate optimal imaging parameters based on data inspection.
        
        Args:
            ms_path: Path to the measurement set
            inspection_result: Results from data inspection
            custom_params: Optional custom parameters
            
        Returns:
            Dictionary with imaging parameters
        """
        # Start with default parameters
        params = self.default_params.copy()
        
        # Update with inspection results
        params.update({
            'cell': f"{inspection_result['recommended_cell_size']:.2f}arcsec",
            'imsize': inspection_result['recommended_imsize'],
            'niter': self.deconvolution_config.get('niter', 1000),
            'threshold': self.deconvolution_config.get('threshold', '0.1mJy'),
            'deconvolver': self.deconvolution_config.get('deconvolver', 'multiscale'),
            'scales': self.deconvolution_config.get('scales', [0, 3, 10, 30]),
            'smallscalebias': self.deconvolution_config.get('smallscalebias', 0.6),
            'gridder': self.imaging_config.get('gridder', 'standard'),
            'wprojplanes': self.imaging_config.get('wprojplanes', 1),
            'pblimit': self.primary_beam_config.get('pblimit', 0.1),
            'pbcor': self.primary_beam_config.get('pbcor', True),
            'restoringbeam': self.imaging_config.get('restoringbeam', 'common'),
            'savemodel': self.imaging_config.get('savemodel', 'modelcolumn'),
            'calcres': True,
            'calcpsf': True,
            'parallel': self.imaging_config.get('parallel', True)
        })
        
        # Apply custom parameters if provided
        if custom_params:
            params.update(custom_params)
        
        return params
    
    async def _run_multiscale_imaging(self, ms_path: str, image_name: str, 
                                    params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run multi-scale imaging.
        
        Args:
            ms_path: Path to the measurement set
            image_name: Name for the output image
            params: Imaging parameters
            
        Returns:
            Dictionary with imaging results
        """
        try:
            image_path = self.images_dir / image_name
            
            # Set multi-scale specific parameters
            multiscale_params = params.copy()
            multiscale_params.update({
                'deconvolver': 'multiscale',
                'scales': [0, 3, 10, 30],
                'smallscalebias': 0.6
            })
            
            # Run tclean
            tclean(
                vis=ms_path,
                imagename=str(image_path),
                **multiscale_params
            )
            
            logger.info(f"Multi-scale imaging completed: {image_name}")
            
            return {
                'success': True,
                'image_path': str(image_path),
                'imaging_type': 'multiscale',
                'parameters': multiscale_params
            }
            
        except Exception as e:
            logger.error(f"Multi-scale imaging failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_briggs_imaging(self, ms_path: str, image_name: str, 
                                params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Briggs weighting imaging.
        
        Args:
            ms_path: Path to the measurement set
            image_name: Name for the output image
            params: Imaging parameters
            
        Returns:
            Dictionary with imaging results
        """
        try:
            image_path = self.images_dir / image_name
            
            # Set Briggs weighting parameters
            briggs_params = params.copy()
            briggs_params.update({
                'weighting': 'briggs',
                'robust': self.weighting_config.get('robust', 0.5),
                'deconvolver': 'hogbom'
            })
            
            # Run tclean
            tclean(
                vis=ms_path,
                imagename=str(image_path),
                **briggs_params
            )
            
            logger.info(f"Briggs weighting imaging completed: {image_name}")
            
            return {
                'success': True,
                'image_path': str(image_path),
                'imaging_type': 'briggs',
                'parameters': briggs_params
            }
            
        except Exception as e:
            logger.error(f"Briggs weighting imaging failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_uniform_imaging(self, ms_path: str, image_name: str, 
                                 params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run uniform weighting imaging.
        
        Args:
            ms_path: Path to the measurement set
            image_name: Name for the output image
            params: Imaging parameters
            
        Returns:
            Dictionary with imaging results
        """
        try:
            image_path = self.images_dir / image_name
            
            # Set uniform weighting parameters
            uniform_params = params.copy()
            uniform_params.update({
                'weighting': 'uniform',
                'deconvolver': 'hogbom'
            })
            
            # Run tclean
            tclean(
                vis=ms_path,
                imagename=str(image_path),
                **uniform_params
            )
            
            logger.info(f"Uniform weighting imaging completed: {image_name}")
            
            return {
                'success': True,
                'image_path': str(image_path),
                'imaging_type': 'uniform',
                'parameters': uniform_params
            }
            
        except Exception as e:
            logger.error(f"Uniform weighting imaging failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _assess_image_quality(self, image_paths: List[str]) -> Dict[str, Any]:
        """
        Assess quality of created images.
        
        Args:
            image_paths: List of image paths to assess
            
        Returns:
            Dictionary with quality metrics
        """
        quality_metrics = {}
        
        for image_path in image_paths:
            try:
                # Get image statistics
                stats = imstat(imagename=image_path)
                
                # Get image header information
                header = imhead(imagename=image_path, mode='summary')
                
                # Calculate quality metrics
                rms = stats.get('rms', 0)
                peak = stats.get('max', 0)
                dynamic_range = peak / rms if rms > 0 else 0
                
                # Get beam information
                beam_info = imhead(imagename=image_path, mode='get', hdkey='beammajor')
                beam_major = beam_info.get('beammajor', {}).get('value', 0)
                
                quality_metrics[os.path.basename(image_path)] = {
                    'rms': rms,
                    'peak': peak,
                    'dynamic_range': dynamic_range,
                    'beam_major': beam_major,
                    'n_pixels': stats.get('npts', 0),
                    'min_value': stats.get('min', 0),
                    'max_value': stats.get('max', 0)
                }
                
            except Exception as e:
                logger.warning(f"Could not assess quality for {image_path}: {e}")
                quality_metrics[os.path.basename(image_path)] = {'error': str(e)}
        
        return quality_metrics
    
    async def _export_images_to_fits(self, image_paths: List[str]) -> Dict[str, Any]:
        """
        Export CASA images to FITS format.
        
        Args:
            image_paths: List of image paths to export
            
        Returns:
            Dictionary with export results
        """
        fits_files = []
        
        for image_path in image_paths:
            try:
                # Generate FITS filename
                fits_path = str(Path(image_path).with_suffix('.fits'))
                
                # Export to FITS
                exportfits(
                    imagename=image_path,
                    fitsimage=fits_path,
                    overwrite=True
                )
                
                fits_files.append(fits_path)
                logger.info(f"Exported to FITS: {os.path.basename(fits_path)}")
                
            except Exception as e:
                logger.warning(f"Could not export {image_path} to FITS: {e}")
        
        return {
            'success': len(fits_files) > 0,
            'fits_files': fits_files,
            'exported_count': len(fits_files)
        }
    
    def __del__(self):
        """Clean up CASA tools."""
        try:
            self.ms_tool.done()
            self.image_tool.done()
            self.imager_tool.done()
        except:
            pass
