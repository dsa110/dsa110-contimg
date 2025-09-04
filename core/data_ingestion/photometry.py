# core/data_ingestion/photometry.py
"""
Photometry management for DSA-110 pipeline.

This module handles photometry operations including source identification,
aperture photometry, and result storage.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np
from astropy.time import Time
from astropy.table import Table, vstack
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
from photutils import CircularAperture, aperture_photometry
from photutils.detection import DAOStarFinder
import warnings

from ..utils.logging import get_logger
from ..pipeline.exceptions import PhotometryError

logger = get_logger(__name__)


class PhotometryManager:
    """
    Manages photometry operations for the pipeline.
    
    This class consolidates photometry functionality from the original
    photometry.py module and provides a cleaner interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the photometry manager.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.photometry_config = config.get('photometry', {})
        self.paths_config = config.get('paths', {})
    
    async def identify_sources(self, mosaic_fits_path: str) -> Tuple[Optional[Table], Optional[Table]]:
        """
        Identify target and reference sources from a mosaic FITS file.
        
        Args:
            mosaic_fits_path: Path to the mosaic FITS file
            
        Returns:
            Tuple of (targets_table, references_table)
        """
        logger.info(f"Identifying sources in {os.path.basename(mosaic_fits_path)}")
        
        try:
            # Read FITS file
            with fits.open(mosaic_fits_path) as hdul:
                data = hdul[0].data
                header = hdul[0].header
            
            # Handle different data shapes
            if data.ndim == 4:
                # Stokes, frequency, dec, ra
                image_data = data[0, 0, :, :]
            elif data.ndim == 3:
                # Frequency, dec, ra or stokes, dec, ra
                image_data = data[0, :, :]
            elif data.ndim == 2:
                # dec, ra
                image_data = data
            else:
                raise PhotometryError(f"Unsupported data shape: {data.shape}")
            
            # Get WCS
            w = WCS(header).celestial
            
            # Source detection parameters
            detection_config = self.photometry_config.get('detection', {})
            fwhm_pixels = detection_config.get('fwhm_pixels', 3.0)
            threshold_sigma = detection_config.get('threshold_sigma', 5.0)
            
            # Calculate noise level
            noise_level = np.std(image_data)
            threshold = threshold_sigma * noise_level
            
            # Find sources
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                finder = DAOStarFinder(
                    fwhm=fwhm_pixels,
                    threshold=threshold,
                    exclude_border=True
                )
                sources = finder(image_data)
            
            if sources is None or len(sources) == 0:
                logger.warning("No sources detected")
                return None, None
            
            # Convert pixel coordinates to sky coordinates
            sky_coords = w.pixel_to_world(sources['xcentroid'], sources['ycentroid'])
            
            # Create source table
            source_table = Table()
            source_table['id'] = np.arange(len(sources))
            source_table['ra'] = sky_coords.ra.deg
            source_table['dec'] = sky_coords.dec.deg
            source_table['x_pixel'] = sources['xcentroid']
            source_table['y_pixel'] = sources['ycentroid']
            source_table['peak'] = sources['peak']
            source_table['flux'] = sources['flux']
            
            # Classify sources as targets or references
            targets, references = self._classify_sources(source_table)
            
            logger.info(f"Identified {len(targets)} targets and {len(references)} references")
            return targets, references
            
        except Exception as e:
            logger.error(f"Source identification failed: {e}")
            return None, None
    
    def _classify_sources(self, source_table: Table) -> Tuple[Table, Table]:
        """
        Classify sources as targets or references based on configuration.
        
        Args:
            source_table: Table of all detected sources
            
        Returns:
            Tuple of (targets_table, references_table)
        """
        classification_config = self.photometry_config.get('classification', {})
        
        # Get classification criteria
        target_flux_range = classification_config.get('target_flux_range', [0.001, 0.1])
        reference_flux_range = classification_config.get('reference_flux_range', [0.01, 1.0])
        min_separation_arcsec = classification_config.get('min_separation_arcsec', 30.0)
        
        # Convert flux ranges to the same units as source fluxes
        target_min_flux = target_flux_range[0]
        target_max_flux = target_flux_range[1]
        ref_min_flux = reference_flux_range[0]
        ref_max_flux = reference_flux_range[1]
        
        # Select targets based on flux range
        target_mask = (source_table['flux'] >= target_min_flux) & (source_table['flux'] <= target_max_flux)
        targets = source_table[target_mask].copy()
        
        # Select references based on flux range
        ref_mask = (source_table['flux'] >= ref_min_flux) & (source_table['flux'] <= ref_max_flux)
        references = source_table[ref_mask].copy()
        
        # Remove targets that are too close to references
        if len(targets) > 0 and len(references) > 0:
            targets = self._remove_close_sources(targets, references, min_separation_arcsec)
        
        return targets, references
    
    def _remove_close_sources(self, targets: Table, references: Table, 
                            min_separation_arcsec: float) -> Table:
        """
        Remove targets that are too close to reference sources.
        
        Args:
            targets: Table of target sources
            references: Table of reference sources
            min_separation_arcsec: Minimum separation in arcseconds
            
        Returns:
            Filtered targets table
        """
        if len(targets) == 0 or len(references) == 0:
            return targets
        
        # Create coordinate objects
        target_coords = SkyCoord(ra=targets['ra'], dec=targets['dec'], unit='deg')
        ref_coords = SkyCoord(ra=references['ra'], dec=references['dec'], unit='deg')
        
        # Find targets that are too close to any reference
        keep_mask = np.ones(len(targets), dtype=bool)
        
        for i, target_coord in enumerate(target_coords):
            # Calculate separation to all references
            separations = target_coord.separation(ref_coords)
            min_sep_arcsec = separations.arcsec.min()
            
            if min_sep_arcsec < min_separation_arcsec:
                keep_mask[i] = False
        
        return targets[keep_mask]
    
    async def perform_aperture_photometry(self, mosaic_fits_path: str, 
                                        targets: Table, references: Table) -> Optional[Table]:
        """
        Perform aperture photometry on targets and references.
        
        Args:
            mosaic_fits_path: Path to the mosaic FITS file
            targets: Table of target sources
            references: Table of reference sources
            
        Returns:
            Table containing photometry results
        """
        logger.info(f"Performing aperture photometry on {len(targets)} targets and {len(references)} references")
        
        try:
            # Read FITS file
            with fits.open(mosaic_fits_path) as hdul:
                data = hdul[0].data
                header = hdul[0].header
            
            # Handle different data shapes
            if data.ndim == 4:
                image_data = data[0, 0, :, :]
            elif data.ndim == 3:
                image_data = data[0, :, :]
            elif data.ndim == 2:
                image_data = data
            else:
                raise PhotometryError(f"Unsupported data shape: {data.shape}")
            
            # Get WCS
            w = WCS(header).celestial
            
            # Aperture photometry parameters
            aperture_config = self.photometry_config.get('aperture', {})
            aperture_radius_arcsec = aperture_config.get('radius_arcsec', 3.0)
            inner_annulus_arcsec = aperture_config.get('inner_annulus_arcsec', 6.0)
            outer_annulus_arcsec = aperture_config.get('outer_annulus_arcsec', 9.0)
            
            # Convert arcseconds to pixels
            pixel_scale = w.pixel_scale_matrix[0, 0] * 3600  # arcsec per pixel
            aperture_radius_pixels = aperture_radius_arcsec / pixel_scale
            inner_annulus_pixels = inner_annulus_arcsec / pixel_scale
            outer_annulus_pixels = outer_annulus_arcsec / pixel_scale
            
            # Combine targets and references
            all_sources = vstack([targets, references])
            all_sources['is_target'] = np.concatenate([
                np.ones(len(targets), dtype=bool),
                np.zeros(len(references), dtype=bool)
            ])
            
            # Create apertures
            positions = np.column_stack([all_sources['x_pixel'], all_sources['y_pixel']])
            apertures = CircularAperture(positions, r=aperture_radius_pixels)
            
            # Perform photometry
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                phot_table = aperture_photometry(image_data, apertures)
            
            # Add source information
            phot_table['source_id'] = all_sources['id']
            phot_table['ra'] = all_sources['ra']
            phot_table['dec'] = all_sources['dec']
            phot_table['is_target'] = all_sources['is_target']
            phot_table['aperture_sum'] = phot_table['aperture_sum']
            
            # Calculate background (simple local background estimation)
            # This is a simplified version - in practice, you might want more sophisticated background estimation
            phot_table['background'] = 0.0  # Placeholder
            phot_table['net_flux'] = phot_table['aperture_sum'] - phot_table['background']
            
            logger.info("Aperture photometry completed")
            return phot_table
            
        except Exception as e:
            logger.error(f"Aperture photometry failed: {e}")
            return None
    
    async def calculate_relative_fluxes(self, photometry_table: Table) -> Optional[Table]:
        """
        Calculate relative fluxes using reference sources.
        
        Args:
            photometry_table: Table containing photometry results
            
        Returns:
            Table containing relative flux results
        """
        logger.info("Calculating relative fluxes")
        
        try:
            # Separate targets and references
            targets = photometry_table[photometry_table['is_target']]
            references = photometry_table[~photometry_table['is_target']]
            
            if len(references) == 0:
                logger.warning("No reference sources available for relative flux calculation")
                return None
            
            # Calculate reference flux statistics
            ref_fluxes = references['net_flux']
            ref_flux_mean = np.mean(ref_fluxes)
            ref_flux_std = np.std(ref_fluxes)
            
            # Calculate relative fluxes for targets
            target_fluxes = targets['net_flux']
            relative_fluxes = target_fluxes / ref_flux_mean
            
            # Create results table
            results_table = Table()
            results_table['source_id'] = targets['source_id']
            results_table['ra'] = targets['ra']
            results_table['dec'] = targets['dec']
            results_table['net_flux'] = target_fluxes
            results_table['relative_flux'] = relative_fluxes
            results_table['reference_flux_mean'] = ref_flux_mean
            results_table['reference_flux_std'] = ref_flux_std
            results_table['n_references'] = len(references)
            
            logger.info(f"Calculated relative fluxes for {len(targets)} targets")
            return results_table
            
        except Exception as e:
            logger.error(f"Relative flux calculation failed: {e}")
            return None
    
    async def store_photometry_results(self, mosaic_time: Time, 
                                     rel_flux_table: Table) -> bool:
        """
        Store photometry results in the database.
        
        Args:
            mosaic_time: Time of the mosaic observation
            rel_flux_table: Table containing relative flux results
            
        Returns:
            True if successful, False otherwise
        """
        logger.info("Storing photometry results")
        
        try:
            # Get photometry storage directory
            photometry_dir = self.paths_config.get('photometry_dir')
            if not photometry_dir:
                logger.warning("Photometry directory not configured")
                return False
            
            os.makedirs(photometry_dir, exist_ok=True)
            
            # Create output filename
            timestamp_str = mosaic_time.strftime('%Y%m%dT%H%M%S')
            output_filename = f"photometry_{timestamp_str}.ecsv"
            output_path = os.path.join(photometry_dir, output_filename)
            
            # Write results table
            rel_flux_table.write(output_path, format='ascii.ecsv', overwrite=True)
            
            logger.info(f"Stored photometry results: {os.path.basename(output_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Photometry storage failed: {e}")
            return False
