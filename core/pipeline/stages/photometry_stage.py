# core/pipeline/stages/photometry_stage.py
"""
Photometry stage for DSA-110 pipeline.

This module handles photometry operations including source identification,
aperture photometry, and relative flux calculations.
"""

import os
import logging
from typing import Dict, Any, Optional
import numpy as np
import warnings
from astropy.time import Time
from astropy.table import Table

from ...utils.logging import get_logger
from ..exceptions import PhotometryError
from ...data_ingestion.photometry import PhotometryManager

logger = get_logger(__name__)


class PhotometryStage:
    """
    Handles photometry operations for the pipeline.
    
    This class consolidates photometry logic from the original
    photometry.py module and provides a cleaner interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the photometry stage.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.photometry_config = config.get('photometry', {})
        self.paths_config = config.get('paths', {})
        self.photometry_manager = PhotometryManager(config)
    
    async def process_mosaic(self, mosaic_fits_path: str, mosaic_time: Time) -> Dict[str, Any]:
        """
        Process a mosaic for photometry.
        
        This includes source identification, aperture photometry,
        relative flux calculation, and result storage.
        
        Args:
            mosaic_fits_path: Path to the mosaic FITS file
            mosaic_time: Time of the mosaic observation
            
        Returns:
            Dictionary containing photometry results
        """
        logger.info(f"Processing photometry for mosaic: {os.path.basename(mosaic_fits_path)}")
        
        try:
            if not os.path.exists(mosaic_fits_path):
                raise PhotometryError(f"Mosaic FITS file not found: {mosaic_fits_path}")
            
            # Identify sources
            logger.info("Identifying sources...")
            source_result = await self._identify_sources(mosaic_fits_path)
            if not source_result['success']:
                raise PhotometryError(f"Source identification failed: {source_result['error']}")
            
            targets = source_result['targets']
            references = source_result['references']
            
            if targets is None or len(targets) == 0:
                logger.warning("No target sources identified")
                return {
                    'success': True,
                    'targets_count': 0,
                    'references_count': len(references) if references else 0,
                    'photometry_stored': False
                }
            
            if references is None or len(references) == 0:
                logger.warning("No reference sources identified")
                return {
                    'success': True,
                    'targets_count': len(targets),
                    'references_count': 0,
                    'photometry_stored': False
                }
            
            # Perform aperture photometry
            logger.info("Performing aperture photometry...")
            photometry_result = await self._perform_aperture_photometry(
                mosaic_fits_path, targets, references
            )
            if not photometry_result['success']:
                raise PhotometryError(f"Aperture photometry failed: {photometry_result['error']}")
            
            phot_table = photometry_result['photometry_table']
            
            # Calculate relative fluxes
            logger.info("Calculating relative fluxes...")
            relative_flux_result = await self._calculate_relative_fluxes(phot_table)
            if not relative_flux_result['success']:
                raise PhotometryError(f"Relative flux calculation failed: {relative_flux_result['error']}")
            
            rel_flux_table = relative_flux_result['relative_flux_table']
            
            # Store results
            logger.info("Storing photometry results...")
            storage_result = await self._store_photometry_results(mosaic_time, rel_flux_table)
            if not storage_result['success']:
                logger.warning(f"Failed to store photometry results: {storage_result['error']}")
            
            logger.info(f"Photometry processing completed successfully")
            return {
                'success': True,
                'targets_count': len(targets),
                'references_count': len(references),
                'photometry_stored': storage_result['success'],
                'relative_flux_table': rel_flux_table
            }
            
        except Exception as e:
            logger.error(f"Photometry processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'targets_count': 0,
                'references_count': 0,
                'photometry_stored': False
            }
    
    async def _identify_sources(self, mosaic_fits_path: str) -> Dict[str, Any]:
        """
        Identify target and reference sources from the mosaic.
        
        Args:
            mosaic_fits_path: Path to the mosaic FITS file
            
        Returns:
            Dictionary containing identified sources
        """
        try:
            targets, references = await self.photometry_manager.identify_sources(mosaic_fits_path)
            
            return {
                'success': True,
                'targets': targets,
                'references': references
            }
            
        except Exception as e:
            logger.error(f"Source identification failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'targets': None,
                'references': None
            }
    
    async def _perform_aperture_photometry(self, mosaic_fits_path: str, 
                                         targets: Table, references: Table) -> Dict[str, Any]:
        """
        Perform aperture photometry on targets and references.
        
        Args:
            mosaic_fits_path: Path to the mosaic FITS file
            targets: Table of target sources
            references: Table of reference sources
            
        Returns:
            Dictionary containing photometry results
        """
        try:
            phot_table = await self.photometry_manager.perform_aperture_photometry(
                mosaic_fits_path, targets, references
            )
            
            if phot_table is None:
                return {
                    'success': False,
                    'error': 'Photometry returned None',
                    'photometry_table': None
                }
            
            return {
                'success': True,
                'photometry_table': phot_table
            }
            
        except Exception as e:
            logger.error(f"Aperture photometry failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'photometry_table': None
            }
    
    async def _calculate_relative_fluxes(self, photometry_table: Table) -> Dict[str, Any]:
        """
        Calculate relative fluxes using reference sources.
        
        Args:
            photometry_table: Table containing photometry results
            
        Returns:
            Dictionary containing relative flux results
        """
        try:
            rel_flux_table = await self.photometry_manager.calculate_relative_fluxes(photometry_table)
            
            if rel_flux_table is None:
                return {
                    'success': False,
                    'error': 'Relative flux calculation returned None',
                    'relative_flux_table': None
                }
            
            return {
                'success': True,
                'relative_flux_table': rel_flux_table
            }
            
        except Exception as e:
            logger.error(f"Relative flux calculation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'relative_flux_table': None
            }
    
    async def _store_photometry_results(self, mosaic_time: Time, 
                                      rel_flux_table: Table) -> Dict[str, Any]:
        """
        Store photometry results in the database.
        
        Args:
            mosaic_time: Time of the mosaic observation
            rel_flux_table: Table containing relative flux results
            
        Returns:
            Dictionary containing storage results
        """
        try:
            success = await self.photometry_manager.store_photometry_results(
                mosaic_time, rel_flux_table
            )
            
            return {
                'success': success,
                'error': None if success else 'Storage failed'
            }
            
        except Exception as e:
            logger.error(f"Photometry storage failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
