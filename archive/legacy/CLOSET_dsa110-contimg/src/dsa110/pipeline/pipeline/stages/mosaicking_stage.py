# core/pipeline/stages/mosaicking_stage.py
"""
Mosaicking stage for DSA-110 pipeline.

This module handles mosaicking operations using CASA's linearmosaic tool.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from shutil import rmtree
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u

from ...utils.logging import get_logger
from ...utils.dependencies import OptionalDependency, require_dependency
from ...utils.config_validation import ConfigValidator
from ..exceptions import MosaickingError

logger = get_logger(__name__)


class MosaickingStage:
    """
    Handles mosaicking operations for the pipeline.
    
    This class consolidates mosaicking logic from the original
    mosaicking.py module and provides a cleaner interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the mosaicking stage.
        
        Args:
            config: Pipeline configuration dictionary
        """
        # Validate configuration
        errors = []
        errors.extend(ConfigValidator.validate_mosaicking_config(config))
        errors.extend(ConfigValidator.validate_paths_config(config))
        
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")
            
        self.config = config
        self.mosaicking_config = config.get('mosaicking', {})
        self.paths_config = config.get('paths', {})
    
    async def create_mosaic(self, image_list: List[str], pb_list: List[str], 
                           block, max_retries: int = 3) -> Dict[str, Any]:
        """
        Create a mosaic from a list of images and primary beam files with retry logic.
        
        Args:
            image_list: List of paths to image files
            pb_list: List of paths to primary beam files
            block: ProcessingBlock object
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary containing mosaicking results
        """
        logger.info(f"Creating mosaic from {len(image_list)} images")
        
        for attempt in range(max_retries + 1):
            try:
                # Validate inputs
                if not image_list or not pb_list or len(image_list) != len(pb_list):
                    raise MosaickingError(f"Invalid input lists: {len(image_list)} images, {len(pb_list)} PBs")
                
                # Check that all input files exist
                for file_path in image_list + pb_list:
                    if not os.path.exists(file_path):
                        raise MosaickingError(f"Input file not found: {file_path}")
                
                # Generate proper weight maps
                weight_maps = await self._generate_weight_maps(image_list, pb_list)
                if not weight_maps:
                    raise MosaickingError("Failed to generate weight maps")
                
                # Calculate mosaic center
                phase_center = self._calculate_mosaic_center(image_list)
                if not phase_center:
                    raise MosaickingError("Could not determine mosaic center")
                
                # Create mosaic
                mosaic_result = await self._run_linearmosaic(image_list, weight_maps, phase_center, block)
                if not mosaic_result['success']:
                    raise MosaickingError(f"Mosaicking failed: {mosaic_result['error']}")
                
                # Assess mosaic quality
                quality_metrics = await self._assess_mosaic_quality(mosaic_result['image_path'], mosaic_result['weight_path'])
                mosaic_result['quality_metrics'] = quality_metrics
                
                # Export to FITS if requested
                fits_path = None
                if self.mosaicking_config.get('save_fits', True):
                    fits_path = await self._export_mosaic_to_fits(mosaic_result['image_path'])
                    if fits_path:
                        mosaic_result['fits_path'] = fits_path
                
                logger.info(f"Mosaic created successfully: {os.path.basename(mosaic_result['image_path'])}")
                logger.info(f"Mosaic quality score: {quality_metrics.get('overall_quality_score', 'N/A')}")
                
                return {
                    'success': True,
                    'image_path': mosaic_result['image_path'],
                    'weight_path': mosaic_result['weight_path'],
                    'fits_path': fits_path,
                    'quality_metrics': quality_metrics
                }
                
            except Exception as e:
                if attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Mosaicking failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                 f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Mosaicking failed after {max_retries + 1} attempts: {e}")
                    return {
                        'success': False,
                        'error': str(e),
                        'image_path': None,
                        'weight_path': None,
                        'fits_path': None,
                        'quality_metrics': None
                    }
    
    def _calculate_mosaic_center(self, image_list: List[str]) -> Optional[str]:
        """
        Calculate the center coordinates for the mosaic from input images.
        
        Args:
            image_list: List of image file paths
            
        Returns:
            CASA-formatted center string, or None if failed
        """
        logger.info(f"Calculating mosaic center from {len(image_list)} images")
        
        ras = []
        decs = []
        
        # Try using CASA image tool first
        try:
            from casatools import image
            ia = image()
            
            for image_path in image_list:
                try:
                    ia.open(image_path)
                    cs = ia.coordsys()
                    direction = cs.referencevalue(type='direction')
                    ras.append(direction['numeric'][0])  # RA in radians
                    decs.append(direction['numeric'][1])  # Dec in radians
                    cs.done()
                    ia.close()
                except Exception as e:
                    logger.warning(f"Could not get phase center from {image_path}: {e}")
                    continue
            
            if ia.isopen():
                ia.done()
                
        except ImportError:
            logger.warning("CASA image tool not available, falling back to FITS WCS")
        except Exception as e:
            logger.warning(f"CASA image tool failed: {e}")
        
        # Fallback to FITS WCS if CASA failed or no results
        if not ras or not decs:
            logger.info("Using FITS WCS headers for center calculation")
            for image_path in image_list:
                fits_path = f"{os.path.splitext(image_path)[0]}.fits"
                if os.path.exists(fits_path):
                    try:
                        with fits.open(fits_path) as hdul:
                            w = WCS(hdul[0].header).celestial
                            center_pix = [(ax / 2.0) for ax in w.pixel_shape]
                            center_coord = w.pixel_to_world(*center_pix)
                            ras.append(center_coord.ra.rad)
                            decs.append(center_coord.dec.rad)
                    except Exception as e:
                        logger.warning(f"Could not get WCS center from {fits_path}: {e}")
                        continue
        
        if not ras or not decs:
            logger.error("Failed to determine mosaic center from any input images")
            return None
        
        # Calculate mean RA/Dec, handling RA wrap-around
        mean_ra_rad = np.arctan2(np.mean(np.sin(ras)), np.mean(np.cos(ras)))
        mean_dec_rad = np.mean(decs)
        
        center_coord = SkyCoord(ra=mean_ra_rad*u.rad, dec=mean_dec_rad*u.rad, frame='icrs')
        logger.info(f"Calculated mosaic center: {center_coord.to_string('hmsdms')}")
        
        # Format for CASA
        casa_center_str = (f"J2000 {center_coord.ra.to_string(unit=u.hour, sep='hms', precision=4)} "
                          f"{center_coord.dec.to_string(unit=u.deg, sep='dms', precision=3, alwayssign=True)}")
        
        return casa_center_str
    
    async def _run_linearmosaic(self, image_list: List[str], pb_list: List[str],
                               phase_center: str, block) -> Dict[str, Any]:
        """
        Run CASA linearmosaic to create the mosaic.
        
        Args:
            image_list: List of image file paths
            pb_list: List of primary beam file paths
            phase_center: CASA-formatted center string
            block: ProcessingBlock object
            
        Returns:
            Dictionary containing linearmosaic results
        """
        with OptionalDependency('casatools') as casa:
            if not casa:
                logger.error("CASA linearmosaic tool not available")
                return {'success': False, 'error': 'CASA not available'}
        
        # Set up output paths
        mosaic_dir = self.paths_config.get('mosaics_dir')
        if not mosaic_dir:
            return {'success': False, 'error': 'Mosaics directory not configured'}
        
        os.makedirs(mosaic_dir, exist_ok=True)
        
        mosaic_basename = f"mosaic_{block.start_time.strftime('%Y%m%dT%H%M%S')}_{block.end_time.strftime('%Y%m%dT%H%M%S')}"
        mosaic_image_path = os.path.join(mosaic_dir, f"{mosaic_basename}.linmos")
        mosaic_weight_path = os.path.join(mosaic_dir, f"{mosaic_basename}.weightlinmos")
        
        # Clean up existing outputs
        for path in [mosaic_image_path, mosaic_weight_path]:
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        rmtree(path)
                    else:
                        os.remove(path)
                except Exception as e:
                    logger.warning(f"Failed to remove existing mosaic product {path}: {e}")
        
        try:
            # Initialize linearmosaic
            lm = linearmosaic()
            
            # Set mosaic type
            lm.setlinmostype(self.mosaicking_config.get('mosaic_type', 'optimal'))
            
            # Define output image grid
            nx = self.mosaicking_config.get('mosaic_nx', 28800)
            ny = self.mosaicking_config.get('mosaic_ny', 4800)
            cell = self.mosaicking_config.get('mosaic_cell', '3arcsec')
            
            if nx is None or ny is None:
                return {'success': False, 'error': 'Mosaic dimensions not configured'}
            
            logger.info(f"Defining output mosaic grid: nx={nx}, ny={ny}, cell={cell}")
            
            lm.defineoutputimage(
                nx=nx, ny=ny,
                cellx=cell, celly=cell,
                imagecenter=phase_center,
                outputimage=mosaic_image_path,
                outputweight=mosaic_weight_path
            )
            
            # Run mosaicking
            logger.info("Running linearmosaic makemosaic...")
            lm.makemosaic(images=image_list, weightimages=pb_list)
            
            lm.done()
            
            logger.info("Mosaic creation successful")
            return {
                'success': True,
                'image_path': mosaic_image_path,
                'weight_path': mosaic_weight_path
            }
            
        except Exception as e:
            logger.error(f"Linearmosaic failed: {e}")
            if 'lm' in locals():
                lm.done()
            
            # Clean up partial outputs
            for path in [mosaic_image_path, mosaic_weight_path]:
                if os.path.exists(path):
                    try:
                        if os.path.isdir(path):
                            rmtree(path)
                    except Exception:
                        pass
            
            return {'success': False, 'error': str(e)}
    
    async def _export_mosaic_to_fits(self, mosaic_image_path: str) -> Optional[str]:
        """
        Export mosaic image to FITS format.
        
        Args:
            mosaic_image_path: Path to the CASA mosaic image
            
        Returns:
            Path to the FITS file, or None if failed
        """
        try:
            from casatasks import exportfits
            casa_available = True
        except ImportError:
            logger.error("CASA tasks not available for FITS export")
            return None
        
        if not os.path.exists(mosaic_image_path):
            logger.error(f"Mosaic image not found: {mosaic_image_path}")
            return None
        
        fits_path = f"{os.path.splitext(mosaic_image_path)[0]}.linmos.fits"
        
        try:
            exportfits(imagename=mosaic_image_path, fitsimage=fits_path, overwrite=True)
            logger.info(f"Exported mosaic FITS: {os.path.basename(fits_path)}")
            return fits_path
            
        except Exception as e:
            logger.error(f"Mosaic FITS export failed: {e}")
            return None
    
    async def _generate_weight_maps(self, image_list: List[str], pb_list: List[str]) -> List[str]:
        """
        Generate proper weight maps for mosaicking with noise weighting.
        
        Args:
            image_list: List of image file paths
            pb_list: List of primary beam file paths
            
        Returns:
            List of weight map file paths
        """
        logger.info(f"Generating weight maps for {len(image_list)} images")
        
        weight_maps = []
        
        for i, (image_path, pb_path) in enumerate(zip(image_list, pb_list)):
            try:
                # Generate weight map for this image
                weight_map_path = await self._create_single_weight_map(image_path, pb_path, i)
                if weight_map_path:
                    weight_maps.append(weight_map_path)
                    logger.debug(f"Generated weight map {i+1}/{len(image_list)}: {os.path.basename(weight_map_path)}")
                else:
                    logger.warning(f"Failed to generate weight map for {os.path.basename(image_path)}")
                    # Use primary beam as fallback
                    weight_maps.append(pb_path)
                    
            except Exception as e:
                logger.warning(f"Error generating weight map for {os.path.basename(image_path)}: {e}")
                # Use primary beam as fallback
                weight_maps.append(pb_path)
        
        logger.info(f"Generated {len(weight_maps)} weight maps")
        return weight_maps
    
    async def _create_single_weight_map(self, image_path: str, pb_path: str, index: int) -> Optional[str]:
        """
        Create a single weight map with noise weighting.
        
        Args:
            image_path: Path to the image file
            pb_path: Path to the primary beam file
            index: Index for unique naming
            
        Returns:
            Path to the generated weight map, or None if failed
        """
        try:
            from casatools import image
            from casatasks import immath
            casa_available = True
        except ImportError:
            logger.warning("CASA not available for weight map generation")
            return None
        
        # Generate weight map name
        weight_map_path = f"{os.path.splitext(image_path)[0]}.weight"
        
        try:
            # Calculate noise from image
            noise_level = await self._estimate_image_noise(image_path)
            if noise_level is None:
                logger.warning(f"Could not estimate noise for {os.path.basename(image_path)}")
                return None
            
            # Create weight map: weight = pb^2 / noise^2
            # This gives proper noise weighting for mosaicking
            weight_expression = f"IM0*IM0/({noise_level}*{noise_level})"
            
            immath(
                imagename=[pb_path],
                expr=weight_expression,
                outfile=weight_map_path,
                overwrite=True
            )
            
            # Verify the weight map was created
            if os.path.exists(weight_map_path):
                logger.debug(f"Created weight map: {os.path.basename(weight_map_path)}")
                return weight_map_path
            else:
                logger.warning(f"Weight map creation failed for {os.path.basename(image_path)}")
                return None
                
        except Exception as e:
            logger.warning(f"Weight map creation failed for {os.path.basename(image_path)}: {e}")
            return None
    
    async def _estimate_image_noise(self, image_path: str) -> Optional[float]:
        """
        Estimate noise level in an image for weight calculation.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Estimated noise level, or None if failed
        """
        try:
            from casatools import image
            import casacore.tables as pt
            
            ia = image()
            ia.open(image_path)
            
            # Get image data
            image_data = ia.getchunk()
            ia.close()
            
            if image_data is None or image_data.size == 0:
                return None
            
            # Calculate RMS in outer regions (assuming center is source region)
            # Use robust statistics to avoid outliers
            flat_data = image_data.flatten()
            valid_data = flat_data[~np.isnan(flat_data)]
            
            if len(valid_data) == 0:
                return None
            
            # Use median absolute deviation for robust noise estimation
            median_val = np.median(valid_data)
            mad = np.median(np.abs(valid_data - median_val))
            noise_estimate = 1.4826 * mad  # Convert MAD to standard deviation
            
            logger.debug(f"Estimated noise level: {noise_estimate:.6f}")
            return float(noise_estimate)
            
        except ImportError:
            logger.warning("CASA not available for noise estimation")
            return None
        except Exception as e:
            logger.warning(f"Noise estimation failed: {e}")
            return None
    
    async def _assess_mosaic_quality(self, mosaic_image_path: str, mosaic_weight_path: str) -> Dict[str, Any]:
        """
        Assess the quality of a generated mosaic.
        
        Args:
            mosaic_image_path: Path to the mosaic image
            mosaic_weight_path: Path to the mosaic weight map
            
        Returns:
            Dictionary containing quality metrics
        """
        logger.info(f"Assessing mosaic quality: {os.path.basename(mosaic_image_path)}")
        
        quality_metrics = {
            'overall_quality_score': 0.0,
            'mosaic_coverage': 0.0,
            'noise_level': 0.0,
            'dynamic_range': 0.0,
            'weight_map_quality': 0.0,
            'warnings': [],
            'errors': []
        }
        
        try:
            import casacore.tables as pt
            
            # Assess image quality
            with pt.table(mosaic_image_path) as image_table:
                image_data = image_table.getcol('map')
                
                if len(image_data) == 0:
                    quality_metrics['errors'].append("Mosaic image data is empty")
                    return quality_metrics
                
                # Calculate basic statistics
                image_flat = image_data.flatten()
                valid_data = image_flat[~np.isnan(image_flat)]
                
                if len(valid_data) == 0:
                    quality_metrics['errors'].append("No valid mosaic data found")
                    return quality_metrics
                
                # Calculate metrics
                peak_flux = float(np.max(valid_data))
                rms_noise = float(np.std(valid_data))
                
                if rms_noise > 0:
                    quality_metrics['dynamic_range'] = peak_flux / rms_noise
                
                quality_metrics['noise_level'] = rms_noise
            
            # Assess weight map quality
            if os.path.exists(mosaic_weight_path):
                weight_quality = await self._assess_weight_map_quality(mosaic_weight_path)
                quality_metrics['weight_map_quality'] = weight_quality
            else:
                quality_metrics['warnings'].append("Weight map not found")
            
            # Calculate mosaic coverage
            coverage = await self._calculate_mosaic_coverage(mosaic_image_path)
            quality_metrics['mosaic_coverage'] = coverage
            
            # Calculate overall quality score
            quality_metrics['overall_quality_score'] = self._calculate_mosaic_quality_score(quality_metrics)
            
        except ImportError:
            quality_metrics['warnings'].append("casacore not available for detailed quality assessment")
            quality_metrics['overall_quality_score'] = 5.0  # Default score
        except Exception as e:
            quality_metrics['errors'].append(f"Quality assessment error: {e}")
            quality_metrics['overall_quality_score'] = 0.0
        
        logger.info(f"Mosaic quality score: {quality_metrics['overall_quality_score']:.2f}/10.0")
        return quality_metrics
    
    async def _assess_weight_map_quality(self, weight_path: str) -> float:
        """
        Assess the quality of a weight map.
        
        Args:
            weight_path: Path to the weight map
            
        Returns:
            Quality score from 0.0 to 10.0
        """
        try:
            import casacore.tables as pt
            
            with pt.table(weight_path) as weight_table:
                weight_data = weight_table.getcol('map')
                
                if len(weight_data) == 0:
                    return 0.0
                
                # Calculate weight statistics
                weight_flat = weight_data.flatten()
                valid_weights = weight_flat[~np.isnan(weight_flat)]
                
                if len(valid_weights) == 0:
                    return 0.0
                
                # Quality based on weight distribution
                max_weight = np.max(valid_weights)
                min_weight = np.min(valid_weights)
                weight_range = max_weight - min_weight
                
                # Good weight maps have reasonable range and no extreme values
                if weight_range > 0 and max_weight < 1e6:  # Avoid extreme values
                    return min(10.0, weight_range / 100.0)  # Scale to 0-10
                else:
                    return 5.0  # Default score
                    
        except Exception as e:
            logger.warning(f"Weight map quality assessment failed: {e}")
            return 5.0
    
    async def _calculate_mosaic_coverage(self, mosaic_image_path: str) -> float:
        """
        Calculate the coverage fraction of the mosaic.
        
        Args:
            mosaic_image_path: Path to the mosaic image
            
        Returns:
            Coverage fraction from 0.0 to 1.0
        """
        try:
            import casacore.tables as pt
            
            with pt.table(mosaic_image_path) as image_table:
                image_data = image_table.getcol('map')
                
                if len(image_data) == 0:
                    return 0.0
                
                # Calculate coverage as fraction of non-zero pixels
                image_flat = image_data.flatten()
                valid_pixels = image_flat[~np.isnan(image_flat)]
                non_zero_pixels = valid_pixels[valid_pixels != 0]
                
                if len(valid_pixels) == 0:
                    return 0.0
                
                coverage = len(non_zero_pixels) / len(valid_pixels)
                return float(coverage)
                
        except Exception as e:
            logger.warning(f"Coverage calculation failed: {e}")
            return 0.0
    
    def _calculate_mosaic_quality_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate overall mosaic quality score.
        
        Args:
            metrics: Dictionary of mosaic quality metrics
            
        Returns:
            Quality score from 0.0 to 10.0
        """
        score = 10.0
        
        # Dynamic range scoring
        dynamic_range = metrics.get('dynamic_range', 0)
        if dynamic_range < 10:
            score -= 2.0
        elif dynamic_range < 50:
            score -= 1.0
        elif dynamic_range > 1000:
            score -= 1.0  # Possible artifacts
        
        # Coverage scoring
        coverage = metrics.get('mosaic_coverage', 0)
        if coverage < 0.5:
            score -= 2.0
        elif coverage < 0.8:
            score -= 1.0
        
        # Weight map quality scoring
        weight_quality = metrics.get('weight_map_quality', 0)
        if weight_quality < 5.0:
            score -= 1.0
        
        # Noise level scoring
        noise_level = metrics.get('noise_level', 0)
        if noise_level > 0.01:  # 10 mJy
            score -= 1.5
        elif noise_level > 0.005:  # 5 mJy
            score -= 0.5
        
        # Penalize for warnings
        warning_count = len(metrics.get('warnings', []))
        score -= warning_count * 0.5
        
        # Penalize for errors
        error_count = len(metrics.get('errors', []))
        score -= error_count * 2.0
        
        return max(0.0, round(score, 2))
    
    async def create_multiple_mosaics(self, mosaic_blocks: List[Dict[str, Any]], 
                                    max_concurrent: int = 2) -> Dict[str, Any]:
        """
        Create multiple mosaics with parallel processing and memory management.
        
        Args:
            mosaic_blocks: List of dictionaries containing image_list, pb_list, and block info
            max_concurrent: Maximum number of concurrent mosaic operations
            
        Returns:
            Dictionary containing processing results
        """
        logger.info(f"Creating {len(mosaic_blocks)} mosaics with max {max_concurrent} concurrent operations")
        
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
        
        # Process mosaics in batches to manage memory
        batch_size = min(max_concurrent, len(mosaic_blocks))
        
        for i in range(0, len(mosaic_blocks), batch_size):
            batch = mosaic_blocks[i:i + batch_size]
            logger.info(f"Processing mosaic batch {i//batch_size + 1}: {len(batch)} mosaics")
            
            # Process batch concurrently
            tasks = []
            for mosaic_info in batch:
                task = self.create_mosaic(
                    mosaic_info['image_list'],
                    mosaic_info['pb_list'],
                    mosaic_info['block']
                )
                tasks.append(task)
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                mosaic_info = batch[j]
                results['total_processed'] += 1
                
                if isinstance(result, Exception):
                    logger.error(f"Exception creating mosaic {j}: {result}")
                    results['failed'].append({
                        'mosaic_info': mosaic_info,
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
        
        logger.info(f"Mosaic batch processing complete: {results['total_successful']}/{results['total_processed']} "
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
    
    async def generate_quality_report(self, mosaic_results: List[Dict[str, Any]], 
                                    output_path: str) -> bool:
        """
        Generate a comprehensive quality report for mosaic results.
        
        Args:
            mosaic_results: List of mosaic result dictionaries
            output_path: Path to save the quality report
            
        Returns:
            True if report generated successfully, False otherwise
        """
        logger.info(f"Generating quality report for {len(mosaic_results)} mosaics")
        
        try:
            report_content = []
            report_content.append("# DSA-110 Mosaic Quality Report")
            report_content.append(f"Generated: {np.datetime64('now')}")
            report_content.append(f"Total Mosaics: {len(mosaic_results)}")
            report_content.append("")
            
            # Overall statistics
            successful_mosaics = [r for r in mosaic_results if r.get('success', False)]
            failed_mosaics = [r for r in mosaic_results if not r.get('success', False)]
            
            report_content.append("## Overall Statistics")
            report_content.append(f"- Successful: {len(successful_mosaics)}")
            report_content.append(f"- Failed: {len(failed_mosaics)}")
            report_content.append(f"- Success Rate: {len(successful_mosaics)/len(mosaic_results)*100:.1f}%")
            report_content.append("")
            
            if successful_mosaics:
                # Quality metrics summary
                quality_scores = [r.get('quality_metrics', {}).get('overall_quality_score', 0) 
                                for r in successful_mosaics]
                
                report_content.append("## Quality Metrics Summary")
                report_content.append(f"- Average Quality Score: {np.mean(quality_scores):.2f}/10.0")
                report_content.append(f"- Best Quality Score: {np.max(quality_scores):.2f}/10.0")
                report_content.append(f"- Worst Quality Score: {np.min(quality_scores):.2f}/10.0")
                report_content.append(f"- Standard Deviation: {np.std(quality_scores):.2f}")
                report_content.append("")
                
                # Individual mosaic details
                report_content.append("## Individual Mosaic Details")
                for i, result in enumerate(successful_mosaics):
                    quality_metrics = result.get('quality_metrics', {})
                    report_content.append(f"### Mosaic {i+1}")
                    report_content.append(f"- Image: {os.path.basename(result.get('image_path', 'N/A'))}")
                    report_content.append(f"- Quality Score: {quality_metrics.get('overall_quality_score', 'N/A')}/10.0")
                    report_content.append(f"- Dynamic Range: {quality_metrics.get('dynamic_range', 'N/A')}")
                    report_content.append(f"- Coverage: {quality_metrics.get('mosaic_coverage', 'N/A')*100:.1f}%")
                    report_content.append(f"- Noise Level: {quality_metrics.get('noise_level', 'N/A')}")
                    report_content.append(f"- Weight Map Quality: {quality_metrics.get('weight_map_quality', 'N/A')}/10.0")
                    
                    if quality_metrics.get('warnings'):
                        report_content.append(f"- Warnings: {', '.join(quality_metrics['warnings'])}")
                    if quality_metrics.get('errors'):
                        report_content.append(f"- Errors: {', '.join(quality_metrics['errors'])}")
                    report_content.append("")
            
            if failed_mosaics:
                report_content.append("## Failed Mosaics")
                for i, result in enumerate(failed_mosaics):
                    report_content.append(f"### Failed Mosaic {i+1}")
                    report_content.append(f"- Error: {result.get('error', 'Unknown error')}")
                    report_content.append("")
            
            # Write report
            with open(output_path, 'w') as f:
                f.write('\n'.join(report_content))
            
            logger.info(f"Quality report saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Quality report generation failed: {e}")
            return False
