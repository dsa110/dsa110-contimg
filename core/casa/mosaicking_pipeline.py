"""
CASA Mosaicking Pipeline for DSA-110

This module provides comprehensive CASA-based mosaicking functionality
for the DSA-110 continuum imaging pipeline, including linearmosaic
integration, primary beam correction, and mosaic quality assessment.
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

from casatools import ms, image, imager, linearmosaic
from casatasks import exportfits, imhead, imstat, imval

from core.utils.logging import get_logger
from core.telescope.dsa110 import get_telescope_location, get_primary_beam_model
from core.telescope.beam_models import GaussianBeamModel, AiryDiskBeamModel

logger = get_logger(__name__)


class CASAMosaickingPipeline:
    """
    Comprehensive CASA mosaicking pipeline for DSA-110.
    
    This class provides advanced mosaicking capabilities using CASA linearmosaic,
    including primary beam correction, noise weighting, and mosaic quality assessment.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the CASA mosaicking pipeline.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.mosaicking_config = config.get('mosaicking', {})
        self.paths_config = config.get('paths', {})
        self.telescope_config = config.get('telescope', {})
        
        # Initialize CASA tools
        self.ms_tool = ms()
        self.image_tool = image()
        self.imager_tool = imager()
        self.linearmosaic_tool = linearmosaic()
        
        # Set up paths
        self.mosaics_dir = Path(self.paths_config.get('mosaics_dir', 'mosaics'))
        self.mosaics_dir.mkdir(parents=True, exist_ok=True)
        
        # Mosaicking parameters
        self.default_params = self.mosaicking_config.get('default', {})
        self.primary_beam_config = self.mosaicking_config.get('primary_beam', {})
        self.weighting_config = self.mosaicking_config.get('weighting', {})
        
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
    
    async def run_advanced_mosaicking(self, image_list: List[str], 
                                    pb_list: List[str],
                                    mosaic_name: Optional[str] = None,
                                    mosaic_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run advanced mosaicking with multiple weighting schemes.
        
        Args:
            image_list: List of image paths to mosaic
            pb_list: List of primary beam images
            mosaic_name: Optional custom mosaic name
            mosaic_params: Optional custom mosaic parameters
            
        Returns:
            Dictionary with mosaicking results
        """
        logger.info(f"Starting advanced mosaicking with {len(image_list)} images")
        
        # Generate mosaic name if not provided
        if not mosaic_name:
            mosaic_name = f"mosaic_{len(image_list)}_images"
        
        mosaic_path = self.mosaics_dir / mosaic_name
        
        results = {
            'image_list': image_list,
            'pb_list': pb_list,
            'mosaic_name': mosaic_name,
            'mosaic_path': str(mosaic_path),
            'success': False,
            'mosaics_created': [],
            'quality_metrics': {},
            'errors': []
        }
        
        try:
            # Step 1: Validate input images
            logger.info("Step 1: Validate input images")
            validation_result = await self._validate_input_images(image_list, pb_list)
            if not validation_result['success']:
                results['errors'].extend(validation_result['errors'])
                return results
            
            # Step 2: Calculate mosaic center and parameters
            logger.info("Step 2: Calculate mosaic center and parameters")
            mosaic_params = await self._calculate_mosaic_parameters(
                image_list, mosaic_params
            )
            
            # Step 3: Run noise-weighted mosaicking
            logger.info("Step 3: Run noise-weighted mosaicking")
            noise_weighted_result = await self._run_noise_weighted_mosaicking(
                image_list, pb_list, f"{mosaic_name}_noise_weighted", mosaic_params
            )
            if noise_weighted_result['success']:
                results['mosaics_created'].append(noise_weighted_result['mosaic_path'])
            
            # Step 4: Run primary beam weighted mosaicking
            logger.info("Step 4: Run primary beam weighted mosaicking")
            pb_weighted_result = await self._run_pb_weighted_mosaicking(
                image_list, pb_list, f"{mosaic_name}_pb_weighted", mosaic_params
            )
            if pb_weighted_result['success']:
                results['mosaics_created'].append(pb_weighted_result['mosaic_path'])
            
            # Step 5: Run uniform mosaicking
            logger.info("Step 5: Run uniform mosaicking")
            uniform_result = await self._run_uniform_mosaicking(
                image_list, pb_list, f"{mosaic_name}_uniform", mosaic_params
            )
            if uniform_result['success']:
                results['mosaics_created'].append(uniform_result['mosaic_path'])
            
            # Step 6: Mosaic quality assessment
            logger.info("Step 6: Mosaic quality assessment")
            quality_result = await self._assess_mosaic_quality(results['mosaics_created'])
            results['quality_metrics'] = quality_result
            
            # Step 7: Export to FITS
            logger.info("Step 7: Export to FITS")
            fits_result = await self._export_mosaics_to_fits(results['mosaics_created'])
            results['fits_files'] = fits_result.get('fits_files', [])
            
            if results['mosaics_created']:
                results['success'] = True
                logger.info(f"Advanced mosaicking completed: {len(results['mosaics_created'])} mosaics created")
            else:
                results['errors'].append("No mosaics were created successfully")
                
        except Exception as e:
            logger.error(f"Advanced mosaicking failed: {e}")
            results['errors'].append(str(e))
            
        return results
    
    async def _validate_input_images(self, image_list: List[str], 
                                   pb_list: List[str]) -> Dict[str, Any]:
        """
        Validate input images for mosaicking.
        
        Args:
            image_list: List of image paths
            pb_list: List of primary beam image paths
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        valid_images = []
        valid_pbs = []
        
        # Validate images
        for i, image_path in enumerate(image_list):
            if not os.path.exists(image_path):
                errors.append(f"Image not found: {image_path}")
                continue
            
            try:
                # Check if it's a valid CASA image
                header = imhead(imagename=image_path, mode='summary')
                if header:
                    valid_images.append(image_path)
                else:
                    errors.append(f"Invalid CASA image: {image_path}")
            except Exception as e:
                errors.append(f"Error reading image {image_path}: {e}")
        
        # Validate primary beam images
        for i, pb_path in enumerate(pb_list):
            if not os.path.exists(pb_path):
                errors.append(f"Primary beam image not found: {pb_path}")
                continue
            
            try:
                # Check if it's a valid CASA image
                header = imhead(imagename=pb_path, mode='summary')
                if header:
                    valid_pbs.append(pb_path)
                else:
                    errors.append(f"Invalid primary beam image: {pb_path}")
            except Exception as e:
                errors.append(f"Error reading primary beam image {pb_path}: {e}")
        
        # Check if we have matching numbers of images and primary beams
        if len(valid_images) != len(valid_pbs):
            errors.append(f"Mismatch between images ({len(valid_images)}) and primary beams ({len(valid_pbs)})")
        
        return {
            'success': len(errors) == 0 and len(valid_images) > 0,
            'valid_images': valid_images,
            'valid_pbs': valid_pbs,
            'errors': errors
        }
    
    async def _calculate_mosaic_parameters(self, image_list: List[str], 
                                         custom_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate optimal mosaic parameters.
        
        Args:
            image_list: List of image paths
            custom_params: Optional custom parameters
            
        Returns:
            Dictionary with mosaic parameters
        """
        # Start with default parameters
        params = self.default_params.copy()
        
        # Calculate mosaic center from image centers
        mosaic_center = await self._calculate_mosaic_center(image_list)
        if mosaic_center:
            params['center'] = mosaic_center
        
        # Set primary beam parameters
        params.update({
            'pblimit': self.primary_beam_config.get('pblimit', 0.1),
            'pbcor': self.primary_beam_config.get('pbcor', True),
            'minpb': self.primary_beam_config.get('minpb', 0.1),
            'cutoff': self.primary_beam_config.get('cutoff', 0.1)
        })
        
        # Set weighting parameters
        params.update({
            'weighting': self.weighting_config.get('weighting', 'briggs'),
            'robust': self.weighting_config.get('robust', 0.5)
        })
        
        # Apply custom parameters if provided
        if custom_params:
            params.update(custom_params)
        
        return params
    
    async def _calculate_mosaic_center(self, image_list: List[str]) -> Optional[str]:
        """
        Calculate the center of the mosaic from image centers.
        
        Args:
            image_list: List of image paths
            
        Returns:
            Mosaic center coordinates as string
        """
        try:
            centers = []
            
            for image_path in image_list:
                try:
                    # Get image center from header
                    header = imhead(imagename=image_path, mode='get', hdkey='crval1')
                    ra = header.get('crval1', {}).get('value', 0)
                    
                    header = imhead(imagename=image_path, mode='get', hdkey='crval2')
                    dec = header.get('crval2', {}).get('value', 0)
                    
                    centers.append((ra, dec))
                    
                except Exception as e:
                    logger.warning(f"Could not get center for {image_path}: {e}")
            
            if not centers:
                return None
            
            # Calculate average center
            avg_ra = np.mean([c[0] for c in centers])
            avg_dec = np.mean([c[1] for c in centers])
            
            # Convert to degrees
            ra_deg = avg_ra * 180 / np.pi
            dec_deg = avg_dec * 180 / np.pi
            
            return f"{ra_deg:.6f}deg {dec_deg:.6f}deg"
            
        except Exception as e:
            logger.warning(f"Could not calculate mosaic center: {e}")
            return None
    
    async def _run_noise_weighted_mosaicking(self, image_list: List[str], 
                                           pb_list: List[str],
                                           mosaic_name: str,
                                           params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run noise-weighted mosaicking.
        
        Args:
            image_list: List of image paths
            pb_list: List of primary beam image paths
            mosaic_name: Name for the output mosaic
            params: Mosaic parameters
            
        Returns:
            Dictionary with mosaicking results
        """
        try:
            mosaic_path = self.mosaics_dir / mosaic_name
            
            # Set noise weighting parameters
            noise_params = params.copy()
            noise_params.update({
                'weighting': 'briggs',
                'robust': 0.5,
                'noise_weight': True
            })
            
            # Run linearmosaic
            self.linearmosaic_tool.linear_mosaic(
                imagename=image_list,
                pbimage=pb_list,
                mosaicimage=str(mosaic_path),
                **noise_params
            )
            
            logger.info(f"Noise-weighted mosaicking completed: {mosaic_name}")
            
            return {
                'success': True,
                'mosaic_path': str(mosaic_path),
                'mosaic_type': 'noise_weighted',
                'parameters': noise_params
            }
            
        except Exception as e:
            logger.error(f"Noise-weighted mosaicking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_pb_weighted_mosaicking(self, image_list: List[str], 
                                        pb_list: List[str],
                                        mosaic_name: str,
                                        params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run primary beam weighted mosaicking.
        
        Args:
            image_list: List of image paths
            pb_list: List of primary beam image paths
            mosaic_name: Name for the output mosaic
            params: Mosaic parameters
            
        Returns:
            Dictionary with mosaicking results
        """
        try:
            mosaic_path = self.mosaics_dir / mosaic_name
            
            # Set primary beam weighting parameters
            pb_params = params.copy()
            pb_params.update({
                'weighting': 'briggs',
                'robust': 0.0,
                'pb_weight': True
            })
            
            # Run linearmosaic
            self.linearmosaic_tool.linear_mosaic(
                imagename=image_list,
                pbimage=pb_list,
                mosaicimage=str(mosaic_path),
                **pb_params
            )
            
            logger.info(f"Primary beam weighted mosaicking completed: {mosaic_name}")
            
            return {
                'success': True,
                'mosaic_path': str(mosaic_path),
                'mosaic_type': 'pb_weighted',
                'parameters': pb_params
            }
            
        except Exception as e:
            logger.error(f"Primary beam weighted mosaicking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_uniform_mosaicking(self, image_list: List[str], 
                                    pb_list: List[str],
                                    mosaic_name: str,
                                    params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run uniform mosaicking.
        
        Args:
            image_list: List of image paths
            pb_list: List of primary beam image paths
            mosaic_name: Name for the output mosaic
            params: Mosaic parameters
            
        Returns:
            Dictionary with mosaicking results
        """
        try:
            mosaic_path = self.mosaics_dir / mosaic_name
            
            # Set uniform weighting parameters
            uniform_params = params.copy()
            uniform_params.update({
                'weighting': 'uniform',
                'uniform_weight': True
            })
            
            # Run linearmosaic
            self.linearmosaic_tool.linear_mosaic(
                imagename=image_list,
                pbimage=pb_list,
                mosaicimage=str(mosaic_path),
                **uniform_params
            )
            
            logger.info(f"Uniform mosaicking completed: {mosaic_name}")
            
            return {
                'success': True,
                'mosaic_path': str(mosaic_path),
                'mosaic_type': 'uniform',
                'parameters': uniform_params
            }
            
        except Exception as e:
            logger.error(f"Uniform mosaicking failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _assess_mosaic_quality(self, mosaic_paths: List[str]) -> Dict[str, Any]:
        """
        Assess quality of created mosaics.
        
        Args:
            mosaic_paths: List of mosaic paths to assess
            
        Returns:
            Dictionary with quality metrics
        """
        quality_metrics = {}
        
        for mosaic_path in mosaic_paths:
            try:
                # Get mosaic statistics
                stats = imstat(imagename=mosaic_path)
                
                # Get mosaic header information
                header = imhead(imagename=mosaic_path, mode='summary')
                
                # Calculate quality metrics
                rms = stats.get('rms', 0)
                peak = stats.get('max', 0)
                dynamic_range = peak / rms if rms > 0 else 0
                
                # Get beam information
                beam_info = imhead(imagename=mosaic_path, mode='get', hdkey='beammajor')
                beam_major = beam_info.get('beammajor', {}).get('value', 0)
                
                # Calculate coverage metrics
                coverage = self._calculate_mosaic_coverage(mosaic_path)
                
                quality_metrics[os.path.basename(mosaic_path)] = {
                    'rms': rms,
                    'peak': peak,
                    'dynamic_range': dynamic_range,
                    'beam_major': beam_major,
                    'n_pixels': stats.get('npts', 0),
                    'min_value': stats.get('min', 0),
                    'max_value': stats.get('max', 0),
                    'coverage': coverage
                }
                
            except Exception as e:
                logger.warning(f"Could not assess quality for {mosaic_path}: {e}")
                quality_metrics[os.path.basename(mosaic_path)] = {'error': str(e)}
        
        return quality_metrics
    
    def _calculate_mosaic_coverage(self, mosaic_path: str) -> Dict[str, Any]:
        """
        Calculate mosaic coverage metrics.
        
        Args:
            mosaic_path: Path to the mosaic image
            
        Returns:
            Dictionary with coverage metrics
        """
        try:
            # Get image dimensions
            header = imhead(imagename=mosaic_path, mode='get', hdkey='shape')
            shape = header.get('shape', {}).get('value', [0, 0, 0, 0])
            
            if len(shape) >= 2:
                n_pixels = shape[0] * shape[1]
                
                # Count non-zero pixels (simple coverage estimate)
                # This is a simplified approach - in practice, you'd want more sophisticated coverage calculation
                return {
                    'n_pixels': n_pixels,
                    'coverage_fraction': 1.0  # Simplified - would need actual coverage calculation
                }
            else:
                return {'n_pixels': 0, 'coverage_fraction': 0.0}
                
        except Exception as e:
            logger.warning(f"Could not calculate coverage for {mosaic_path}: {e}")
            return {'n_pixels': 0, 'coverage_fraction': 0.0}
    
    async def _export_mosaics_to_fits(self, mosaic_paths: List[str]) -> Dict[str, Any]:
        """
        Export CASA mosaics to FITS format.
        
        Args:
            mosaic_paths: List of mosaic paths to export
            
        Returns:
            Dictionary with export results
        """
        fits_files = []
        
        for mosaic_path in mosaic_paths:
            try:
                # Generate FITS filename
                fits_path = str(Path(mosaic_path).with_suffix('.fits'))
                
                # Export to FITS
                exportfits(
                    imagename=mosaic_path,
                    fitsimage=fits_path,
                    overwrite=True
                )
                
                fits_files.append(fits_path)
                logger.info(f"Exported mosaic to FITS: {os.path.basename(fits_path)}")
                
            except Exception as e:
                logger.warning(f"Could not export {mosaic_path} to FITS: {e}")
        
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
            self.linearmosaic_tool.done()
        except:
            pass
