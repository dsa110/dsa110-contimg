# core/pipeline/stages/mosaicking_stage.py
"""
Mosaicking stage for DSA-110 pipeline.

This module handles mosaicking operations using CASA's linearmosaic tool.
"""

import os
import logging
from typing import Dict, Any, List
from shutil import rmtree
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u

from ...utils.logging import get_logger
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
        self.config = config
        self.mosaicking_config = config.get('mosaicking', {})
        self.paths_config = config.get('paths', {})
    
    async def create_mosaic(self, image_list: List[str], pb_list: List[str], 
                           block) -> Dict[str, Any]:
        """
        Create a mosaic from a list of images and primary beam files.
        
        Args:
            image_list: List of paths to image files
            pb_list: List of paths to primary beam files
            block: ProcessingBlock object
            
        Returns:
            Dictionary containing mosaicking results
        """
        logger.info(f"Creating mosaic from {len(image_list)} images")
        
        try:
            # Validate inputs
            if not image_list or not pb_list or len(image_list) != len(pb_list):
                raise MosaickingError(f"Invalid input lists: {len(image_list)} images, {len(pb_list)} PBs")
            
            # Check that all input files exist
            for file_path in image_list + pb_list:
                if not os.path.exists(file_path):
                    raise MosaickingError(f"Input file not found: {file_path}")
            
            # Calculate mosaic center
            phase_center = self._calculate_mosaic_center(image_list)
            if not phase_center:
                raise MosaickingError("Could not determine mosaic center")
            
            # Create mosaic
            mosaic_result = await self._run_linearmosaic(image_list, pb_list, phase_center, block)
            if not mosaic_result['success']:
                raise MosaickingError(f"Mosaicking failed: {mosaic_result['error']}")
            
            # Export to FITS if requested
            fits_path = None
            if self.mosaicking_config.get('save_fits', True):
                fits_path = await self._export_mosaic_to_fits(mosaic_result['image_path'])
                if fits_path:
                    mosaic_result['fits_path'] = fits_path
            
            logger.info(f"Mosaic created successfully: {os.path.basename(mosaic_result['image_path'])}")
            return {
                'success': True,
                'image_path': mosaic_result['image_path'],
                'weight_path': mosaic_result['weight_path'],
                'fits_path': fits_path
            }
            
        except Exception as e:
            logger.error(f"Mosaicking failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'image_path': None,
                'weight_path': None,
                'fits_path': None
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
        try:
            from casatools import linearmosaic
            casa_available = True
        except ImportError:
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
