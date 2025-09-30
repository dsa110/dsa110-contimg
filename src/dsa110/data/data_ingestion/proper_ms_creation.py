"""
Proper MS Creation for DSA-110

This module implements the correct MS creation strategy:
- One MS per timestamp (not per sub-band)
- Combine all 16 sub-bands (sb00-sb15) into a single MS
- Follow the reference pipeline approach
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import numpy as np
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u
from pyuvdata import UVData
import glob

from ..utils.logging import get_logger
from ..telescope.dsa110 import get_telescope_location, get_valid_antennas
from ..telescope.antenna_positions import get_antenna_positions_manager
from ..pipeline.exceptions import DataError

logger = get_logger(__name__)


class ProperMSCreationManager:
    """
    Proper MS creation manager that combines sub-bands by timestamp.
    
    This follows the reference pipeline approach of creating one MS per timestamp
    that contains all 16 sub-bands (sb00-sb15).
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the proper MS creation manager.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.ms_config = config.get('ms_creation', {})
        self.paths_config = config.get('paths', {})
        self.telescope_location = get_telescope_location()
        self.valid_antennas = get_valid_antennas()
        self.antenna_positions_manager = get_antenna_positions_manager()
        
        # Sub-band configuration
        self.required_spws = ['sb00', 'sb01', 'sb02', 'sb03', 'sb04', 'sb05', 'sb06', 'sb07',
                             'sb08', 'sb09', 'sb10', 'sb11', 'sb12', 'sb13', 'sb14', 'sb15']
        self.same_timestamp_tolerance = self.ms_config.get('same_timestamp_tolerance', 30.0)
        
    async def create_ms_from_timestamp(self, timestamp: str, hdf5_dir: str, 
                                     output_ms_path: str) -> bool:
        """
        Create a single MS from all sub-bands for a given timestamp.
        
        Args:
            timestamp: Timestamp string (e.g., '2025-09-05T03:23:14')
            hdf5_dir: Directory containing HDF5 files
            output_ms_path: Path for the output MS file
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Creating MS for timestamp: {timestamp}")
        
        try:
            # Find all HDF5 files for this timestamp
            hdf5_files = await self._find_hdf5_files_for_timestamp(timestamp, hdf5_dir)
            
            if not hdf5_files:
                logger.error(f"No HDF5 files found for timestamp: {timestamp}")
                return False
            
            # Check if we have all required sub-bands
            missing_spws = await self._check_missing_subbands(hdf5_files)
            if missing_spws:
                logger.warning(f"Missing sub-bands for {timestamp}: {missing_spws}")
                # Continue anyway, but log the missing ones
            
            # Combine all sub-bands into a single MS
            success = await self._combine_subbands_to_ms(hdf5_files, output_ms_path)
            
            if success:
                logger.info(f"Successfully created MS: {os.path.basename(output_ms_path)}")
            else:
                logger.error(f"Failed to create MS for timestamp: {timestamp}")
            
            return success
            
        except Exception as e:
            logger.error(f"MS creation failed for timestamp {timestamp}: {e}")
            return False
    
    async def _find_hdf5_files_for_timestamp(self, timestamp: str, hdf5_dir: str) -> List[str]:
        """
        Find all HDF5 files for a given timestamp.
        
        Args:
            timestamp: Timestamp string
            hdf5_dir: Directory containing HDF5 files
            
        Returns:
            List of HDF5 file paths
        """
        hdf5_files = []
        
        # Look for files with the timestamp pattern
        pattern = os.path.join(hdf5_dir, f"{timestamp}_sb*.hdf5")
        files = glob.glob(pattern)
        
        # Sort by sub-band number
        files.sort(key=lambda x: int(x.split('_sb')[1].split('.')[0]))
        
        logger.info(f"Found {len(files)} HDF5 files for timestamp {timestamp}")
        
        return files
    
    async def _check_missing_subbands(self, hdf5_files: List[str]) -> List[str]:
        """
        Check which sub-bands are missing from the HDF5 files.
        
        Args:
            hdf5_files: List of HDF5 file paths
            
        Returns:
            List of missing sub-band names
        """
        found_spws = set()
        
        for file_path in hdf5_files:
            filename = os.path.basename(file_path)
            if '_sb' in filename:
                spw = filename.split('_sb')[1].split('.')[0]
                found_spws.add(f'sb{spw.zfill(2)}')
        
        missing_spws = set(self.required_spws) - found_spws
        
        return sorted(list(missing_spws))
    
    async def _combine_subbands_to_ms(self, hdf5_files: List[str], output_ms_path: str) -> bool:
        """
        Combine multiple sub-band HDF5 files into a single MS.
        
        Args:
            hdf5_files: List of HDF5 file paths (one per sub-band)
            output_ms_path: Path for the output MS file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Combining {len(hdf5_files)} sub-bands into MS")
            
            # Read the first HDF5 file to get the basic structure
            uv_data = UVData()
            uv_data.read(hdf5_files[0], file_type='uvh5', run_check=False)
            
            # Set proper antenna positions
            await self._set_antenna_positions(uv_data)
            
            # If we have multiple files, combine them
            if len(hdf5_files) > 1:
                # Read additional files and combine
                for file_path in hdf5_files[1:]:
                    uv_data_additional = UVData()
                    uv_data_additional.read(file_path, file_type='uvh5', run_check=False)
                    
                    # Combine the data
                    uv_data += uv_data_additional
            
            # Write to MS format
            success = await self._write_to_ms(uv_data, output_ms_path)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to combine sub-bands: {e}")
            return False
    
    async def _set_antenna_positions(self, uv_data: UVData) -> None:
        """
        Set proper antenna positions in the UVData object.
        
        Args:
            uv_data: UVData object to modify
        """
        try:
            # Get antenna positions from the CSV file
            antenna_positions, antenna_names = self.antenna_positions_manager.get_antenna_positions_for_uvdata()
            
            # Set antenna positions in UVData
            uv_data.antenna_positions = antenna_positions
            uv_data.antenna_names = antenna_names
            uv_data.antenna_numbers = np.arange(len(antenna_names))
            
            # Set telescope location
            uv_data.telescope_location = self.telescope_location
            
            logger.info(f"Set antenna positions for {len(antenna_names)} antennas")
            
        except Exception as e:
            logger.error(f"Failed to set antenna positions: {e}")
            # Continue without proper positions (will cause issues later)
    
    async def _write_to_ms(self, uv_data: UVData, output_ms_path: str) -> bool:
        """
        Write UVData object to MS format.
        
        Args:
            uv_data: UVData object to write
            output_ms_path: Path for the output MS file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure proper data types
            if uv_data.uvw_array.dtype != np.float64:
                uv_data.uvw_array = uv_data.uvw_array.astype(np.float64)
            
            # Set proper units
            if not hasattr(uv_data, 'vis_units') or uv_data.vis_units is None or uv_data.vis_units == 'uncalib':
                uv_data.vis_units = 'Jy'
            
            # Write to MS format with proper parameters
            uv_data.write_ms(
                output_ms_path, 
                clobber=True, 
                fix_autos=True,  # Fix auto-correlations to be real-only
                force_phase=True,  # Phase data to zenith of first timestamp
                run_check=False  # Skip PyUVData checks during write
            )
            
            logger.info(f"Successfully wrote MS file: {output_ms_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write MS file: {e}")
            return False
    
    async def create_ms_from_hdf5_set(self, hdf5_files: List[str], output_ms_path: str) -> bool:
        """
        Create a single MS from a set of HDF5 files (all sub-bands for one timestamp).
        
        Args:
            hdf5_files: List of HDF5 file paths (one per sub-band)
            output_ms_path: Path for the output MS file
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Creating MS from {len(hdf5_files)} HDF5 files")
        
        try:
            # Combine all sub-bands into a single MS
            success = await self._combine_subbands_to_ms(hdf5_files, output_ms_path)
            
            if success:
                logger.info(f"Successfully created MS: {os.path.basename(output_ms_path)}")
            else:
                logger.error(f"Failed to create MS from HDF5 files")
            
            return success
            
        except Exception as e:
            logger.error(f"MS creation failed: {e}")
            return False
    
    async def process_timestamp_range(self, start_timestamp: str, end_timestamp: str, 
                                    hdf5_dir: str, output_dir: str) -> List[str]:
        """
        Process a range of timestamps and create MS files for each.
        
        Args:
            start_timestamp: Start timestamp string
            end_timestamp: End timestamp string
            hdf5_dir: Directory containing HDF5 files
            output_dir: Directory for output MS files
            
        Returns:
            List of created MS file paths
        """
        logger.info(f"Processing timestamp range: {start_timestamp} to {end_timestamp}")
        
        created_ms_files = []
        
        try:
            # Find all unique timestamps in the directory
            timestamp_pattern = os.path.join(hdf5_dir, "*.hdf5")
            all_files = glob.glob(timestamp_pattern)
            
            # Extract unique timestamps
            timestamps = set()
            for file_path in all_files:
                filename = os.path.basename(file_path)
                if '_sb' in filename:
                    timestamp = filename.split('_sb')[0]
                    timestamps.add(timestamp)
            
            timestamps = sorted(list(timestamps))
            logger.info(f"Found {len(timestamps)} unique timestamps")
            
            # Process each timestamp
            for timestamp in timestamps:
                output_ms_path = os.path.join(output_dir, f"{timestamp}.ms")
                
                success = await self.create_ms_from_timestamp(timestamp, hdf5_dir, output_ms_path)
                
                if success:
                    created_ms_files.append(output_ms_path)
                    logger.info(f"Created MS: {output_ms_path}")
                else:
                    logger.error(f"Failed to create MS for timestamp: {timestamp}")
            
            logger.info(f"Successfully created {len(created_ms_files)} MS files")
            
        except Exception as e:
            logger.error(f"Failed to process timestamp range: {e}")
        
        return created_ms_files


# Legacy compatibility function
async def process_hdf5_set_proper(config: Dict[str, Any], timestamp: str, hdf5_files: List[str]) -> Optional[str]:
    """
    Process a set of HDF5 files for a given timestamp using the proper approach.
    
    Args:
        config: Pipeline configuration dictionary
        timestamp: Timestamp string for the observation
        hdf5_files: List of HDF5 file paths (all sub-bands for one timestamp)
        
    Returns:
        Path to the created MS file, or None if failed
    """
    logger.info(f"Processing HDF5 set for timestamp: {timestamp}")
    logger.info(f"Found {len(hdf5_files)} HDF5 files")
    
    try:
        # Create MS creation manager
        ms_manager = ProperMSCreationManager(config)
        
        # Determine output MS path
        ms_stage1_dir = config.get('paths', {}).get('ms_stage1_dir', 'ms_stage1')
        os.makedirs(ms_stage1_dir, exist_ok=True)
        
        output_ms_path = os.path.join(ms_stage1_dir, f"{timestamp}.ms")
        
        # Create MS from all sub-bands
        success = await ms_manager.create_ms_from_hdf5_set(hdf5_files, output_ms_path)
        
        if success:
            logger.info(f"Successfully created MS: {output_ms_path}")
            return output_ms_path
        else:
            logger.error(f"Failed to create MS from HDF5 files")
            return None
            
    except Exception as e:
        logger.error(f"process_hdf5_set_proper failed: {e}")
        return None
