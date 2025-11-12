# core/data_ingestion/skymodel.py
"""
Sky model management for DSA-110 pipeline.

This module handles sky model creation and management, consolidating
the functionality from the original skymodel.py module.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.table import Table
import astropy.units as u

from ..utils.logging import get_logger
from ..utils.exceptions import DataError

logger = get_logger(__name__)


class SkyModelManager:
    """
    Manages sky model creation and component list generation.
    
    This class consolidates sky model functionality from the original
    skymodel.py module and provides a cleaner interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the sky model manager.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.skymodel_config = config.get('skymodel', {})
        self.paths_config = config.get('paths', {})
    
    async def create_field_component_list(self, center_coord: SkyCoord, 
                                        output_path: str) -> Optional[str]:
        """
        Create a component list for a field centered at the given coordinates.
        
        Args:
            center_coord: Center coordinates for the field
            output_path: Path for the output component list file
            
        Returns:
            Path to the created component list file, or None if failed
        """
        logger.info(f"Creating field component list centered at {center_coord.to_string('hmsdms')}")
        
        try:
            # Get field configuration
            field_config = self.skymodel_config.get('field', {})
            field_radius_deg = field_config.get('radius_deg', 0.5)
            n_sources = field_config.get('n_sources', 100)
            
            # Generate source positions
            source_coords = self._generate_source_positions(center_coord, field_radius_deg, n_sources)
            
            # Generate source fluxes
            source_fluxes = self._generate_source_fluxes(n_sources)
            
            # Create component list
            cl_path = await self._write_component_list(output_path, source_coords, source_fluxes)
            
            if cl_path:
                logger.info(f"Created component list with {len(source_coords)} sources: {os.path.basename(cl_path)}")
            
            return cl_path
            
        except Exception as e:
            logger.error(f"Component list creation failed: {e}")
            return None
    
    def _generate_source_positions(self, center_coord: SkyCoord, 
                                 field_radius_deg: float, n_sources: int) -> List[SkyCoord]:
        """
        Generate random source positions within a field.
        
        Args:
            center_coord: Center coordinates of the field
            field_radius_deg: Field radius in degrees
            n_sources: Number of sources to generate
            
        Returns:
            List of SkyCoord objects representing source positions
        """
        # Generate random positions in a circle
        # Use rejection sampling to ensure uniform distribution
        max_radius_rad = np.radians(field_radius_deg)
        
        # Generate random points in a square
        x = np.random.uniform(-max_radius_rad, max_radius_rad, n_sources * 2)
        y = np.random.uniform(-max_radius_rad, max_radius_rad, n_sources * 2)
        
        # Keep only points within the circle
        r_squared = x**2 + y**2
        valid_mask = r_squared <= max_radius_rad**2
        x_valid = x[valid_mask][:n_sources]
        y_valid = y[valid_mask][:n_sources]
        
        # If we don't have enough points, generate more
        while len(x_valid) < n_sources:
            x_new = np.random.uniform(-max_radius_rad, max_radius_rad, n_sources)
            y_new = np.random.uniform(-max_radius_rad, max_radius_rad, n_sources)
            r_squared_new = x_new**2 + y_new**2
            valid_mask_new = r_squared_new <= max_radius_rad**2
            x_valid = np.concatenate([x_valid, x_new[valid_mask_new]])
            y_valid = np.concatenate([y_valid, y_new[valid_mask_new]])
        
        # Truncate to requested number
        x_valid = x_valid[:n_sources]
        y_valid = y_valid[:n_sources]
        
        # Convert to RA/Dec offsets
        # Approximate conversion for small fields
        ra_offset = x_valid / np.cos(center_coord.dec.rad)
        dec_offset = y_valid
        
        # Create source coordinates
        source_coords = []
        for ra_off, dec_off in zip(ra_offset, dec_offset):
            source_ra = center_coord.ra + ra_off * u.rad
            source_dec = center_coord.dec + dec_off * u.rad
            source_coords.append(SkyCoord(ra=source_ra, dec=source_dec, frame='icrs'))
        
        return source_coords
    
    def _generate_source_fluxes(self, n_sources: int) -> np.ndarray:
        """
        Generate source fluxes following a power law distribution.
        
        Args:
            n_sources: Number of sources to generate
            
        Returns:
            Array of source fluxes in Jy
        """
        flux_config = self.skymodel_config.get('flux', {})
        min_flux_jy = flux_config.get('min_flux_jy', 0.001)
        max_flux_jy = flux_config.get('max_flux_jy', 1.0)
        power_law_index = flux_config.get('power_law_index', -1.5)
        
        # Generate power law distribution
        # For a power law P(x) ∝ x^α, we use inverse transform sampling
        # If α = -1.5, then P(x) ∝ x^(-1.5)
        # The cumulative distribution is F(x) = (x^(α+1) - x_min^(α+1)) / (x_max^(α+1) - x_min^(α+1))
        # The inverse is x = (F * (x_max^(α+1) - x_min^(α+1)) + x_min^(α+1))^(1/(α+1))
        
        alpha = power_law_index
        x_min = min_flux_jy
        x_max = max_flux_jy
        
        # Generate uniform random numbers
        u_rand = np.random.uniform(0, 1, n_sources)
        
        # Apply inverse transform
        if alpha == -1:
            # Special case: uniform in log space
            fluxes = x_min * (x_max / x_min)**u_rand
        else:
            # General case
            x_min_power = x_min**(alpha + 1)
            x_max_power = x_max**(alpha + 1)
            fluxes = (u_rand * (x_max_power - x_min_power) + x_min_power)**(1.0 / (alpha + 1))
        
        return fluxes
    
    async def _write_component_list(self, output_path: str, 
                                  source_coords: List[SkyCoord], 
                                  source_fluxes: np.ndarray) -> Optional[str]:
        """
        Write a CASA component list file.
        
        Args:
            output_path: Path for the output file
            source_coords: List of source coordinates
            source_fluxes: Array of source fluxes in Jy
            
        Returns:
            Path to the created file, or None if failed
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Remove existing file if it exists
            if os.path.exists(output_path):
                os.remove(output_path)
            
            # Create component list using CASA
            try:
                from casatools import componentlist
                cl = componentlist()
                
                # Open new component list (create if doesn't exist)
                cl.open(output_path)
                
                # Add sources
                for i, (coord, flux) in enumerate(zip(source_coords, source_fluxes)):
                    # Convert coordinates to CASA format
                    ra_str = coord.ra.to_string(unit=u.hour, sep='hms', precision=4)
                    dec_str = coord.dec.to_string(unit=u.deg, sep='dms', precision=3, alwayssign=True)
                    
                    # Add point source
                    cl.addcomponent(
                        flux=flux,
                        fluxunit='Jy',
                        dir=f"J2000 {ra_str} {dec_str}",
                        shape='point',
                        spectrumtype='constant'
                    )
                
                cl.close()
                cl.done()
                
                logger.info(f"Created component list with {len(source_coords)} sources")
                return output_path
                
            except ImportError:
                logger.error("CASA componentlist tool not available")
                return None
            except Exception as e:
                logger.error(f"Failed to create component list: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Component list writing failed: {e}")
            return None
    
    async def create_catalog_component_list(self, catalog_path: str, 
                                          output_path: str) -> Optional[str]:
        """
        Create a component list from an external catalog.
        
        Args:
            catalog_path: Path to the input catalog file
            output_path: Path for the output component list file
            
        Returns:
            Path to the created component list file, or None if failed
        """
        logger.info(f"Creating component list from catalog: {os.path.basename(catalog_path)}")
        
        try:
            if not os.path.exists(catalog_path):
                raise DataError(f"Catalog file not found: {catalog_path}")
            
            # Read catalog
            catalog = Table.read(catalog_path)
            
            # Extract coordinates and fluxes
            # Assume standard column names - this could be made configurable
            if 'RA' in catalog.colnames and 'DEC' in catalog.colnames:
                ra_col = 'RA'
                dec_col = 'DEC'
            elif 'ra' in catalog.colnames and 'dec' in catalog.colnames:
                ra_col = 'ra'
                dec_col = 'dec'
            else:
                raise DataError("Catalog must contain RA/Dec columns")
            
            if 'FLUX' in catalog.colnames:
                flux_col = 'FLUX'
            elif 'flux' in catalog.colnames:
                flux_col = 'flux'
            else:
                raise DataError("Catalog must contain flux column")
            
            # Create coordinates
            source_coords = SkyCoord(ra=catalog[ra_col], dec=catalog[dec_col], unit='deg')
            source_fluxes = catalog[flux_col].data
            
            # Create component list
            cl_path = await self._write_component_list(output_path, source_coords, source_fluxes)
            
            if cl_path:
                logger.info(f"Created component list from catalog with {len(catalog)} sources")
            
            return cl_path
            
        except Exception as e:
            logger.error(f"Catalog component list creation failed: {e}")
            return None
