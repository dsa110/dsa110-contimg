"""
DSA-110 HDF5 Reader using PyUVData's native UVH5 reader.

This module provides a simple interface to read DSA-110 HDF5 files using
PyUVData's built-in UVH5 reader, which automatically handles all parameter setup.
"""

import logging
import numpy as np
from typing import Optional
from pyuvdata import UVData
from astropy.coordinates import EarthLocation
import astropy.units as u

logger = logging.getLogger(__name__)


class DSA110HDF5Reader:
    """Reader for DSA-110 HDF5 files using PyUVData's native UVH5 reader."""
    
    def __init__(self):
        """Initialize the HDF5 reader."""
        self.logger = logging.getLogger(__name__)
    
    async def create_uvdata_object(self, hdf5_path: str) -> Optional[UVData]:
        """
        Create a UVData object from HDF5 file using PyUVData's native UVH5 reader.
        
        This approach uses PyUVData's built-in UVH5 reader which automatically
        handles all the parameter setup that we were doing manually. This is
        the same approach used by the reference pipelines.
        
        Args:
            hdf5_path: Path to the HDF5 file
            
        Returns:
            UVData object if successful, None otherwise
        """
        try:
            # Use PyUVData's native UVH5 reader - this automatically sets all required parameters
            uv_data = UVData()
            
            # Read the HDF5 file using PyUVData's built-in UVH5 reader
            # This automatically handles all the parameter setup that we were doing manually
            uv_data.read(hdf5_path, file_type='uvh5', run_check=False)
            
            # Fix known issues with DSA-110 data
            uv_data = self._fix_dsa110_issues(uv_data)
            
            self.logger.info(f"Successfully created UVData object with {uv_data.Nbls} baselines, {uv_data.Nfreqs} frequencies")
            return uv_data
            
        except Exception as e:
            self.logger.error(f"Failed to create UVData object: {e}")
            return None
    
    def _fix_dsa110_issues(self, uv_data: UVData) -> UVData:
        """
        Fix known issues with DSA-110 HDF5 data.
        
        Args:
            uv_data: UVData object to fix
            
        Returns:
            Fixed UVData object
        """
        # Fix 1: Ensure uvw_array is float64 as required by PyUVData
        if uv_data.uvw_array.dtype != np.float64:
            self.logger.info("Converting UVW array from float32 to float64")
            uv_data.uvw_array = uv_data.uvw_array.astype(np.float64)
        
        # Fix 2: Correct telescope name from OVRO_MMA to DSA-110
        if uv_data.telescope.name == "OVRO_MMA":
            self.logger.info("Correcting telescope name from OVRO_MMA to DSA-110")
            uv_data.telescope.name = "DSA-110"
        
        # Fix 3: Ensure data units are properly set
        if not hasattr(uv_data, 'vis_units') or uv_data.vis_units is None or uv_data.vis_units == 'uncalib':
            uv_data.vis_units = 'Jy'
            self.logger.info("Set visibility units to Jy")
        
        # Fix 4: Set proper mount type for DSA-110 (alt-az mount)
        # This will help reduce CASA MSDerivedValues warnings
        if hasattr(uv_data.telescope, 'mount_type'):
            # DSA-110 uses alt-az mounts, so set all antennas to 'alt-az' (with hyphen)
            uv_data.telescope.mount_type = ['alt-az'] * len(uv_data.telescope.mount_type)
            self.logger.info(f"Set telescope mount type to alt-az for {len(uv_data.telescope.mount_type)} antennas")
        
        return uv_data
    
    def write_ms(self, uv_data: UVData, output_ms_path: str) -> bool:
        """
        Write UVData object to MS format with proper parameters.
        
        Args:
            uv_data: UVData object to write
            output_ms_path: Path for the output MS file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Write to MS format with parameters that work for DSA-110 data
            uv_data.write_ms(
                output_ms_path, 
                clobber=True, 
                fix_autos=True,  # Fix auto-correlations to be real-only
                force_phase=True,  # Phase data to zenith of first timestamp
                run_check=False  # Skip PyUVData checks during write
            )
            
            self.logger.info(f"Successfully wrote MS file: {output_ms_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write MS file: {e}")
            return False
    
    def _prepare_for_ms_write(self, uv_data: UVData) -> UVData:
        """
        Prepare UVData object for MS writing by fixing common issues.
        
        Args:
            uv_data: UVData object to prepare
            
        Returns:
            Prepared UVData object
        """
        # Ensure proper data types
        if uv_data.uvw_array.dtype != np.float64:
            uv_data.uvw_array = uv_data.uvw_array.astype(np.float64)
        
        # Ensure proper units
        if not hasattr(uv_data, 'vis_units') or uv_data.vis_units is None or uv_data.vis_units == 'uncalib':
            uv_data.vis_units = 'Jy'
        
        # Note: Baseline conjugation is handled by PyUVData's write_ms method
        # with the force_phase=True parameter, so we don't need to fix it here
        
        return uv_data
