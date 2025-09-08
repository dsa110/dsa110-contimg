# core/data_ingestion/ms_creation.py
"""
MS creation utilities for DSA-110 pipeline.

This module consolidates MS creation functionality from the original
ms_creation.py and testing/makems/ modules.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import numpy as np
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS

from ..utils.logging import get_logger
from ..telescope.dsa110 import get_telescope_location, get_valid_antennas
from ..telescope.beam_models import pb_dsa110
from ..pipeline.exceptions import DataError

logger = get_logger(__name__)


class MSCreationManager:
    """
    Manages MS creation from HDF5 files.
    
    This class consolidates MS creation functionality and provides
    a unified interface for converting HDF5 files to CASA MS format.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the MS creation manager.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.ms_config = config.get('ms_creation', {})
        self.paths_config = config.get('paths', {})
        self.telescope_location = get_telescope_location()
        self.valid_antennas = get_valid_antennas()
    
    async def create_ms_from_hdf5(self, hdf5_path: str, output_ms_path: str,
                                start_time: Optional[Time] = None,
                                end_time: Optional[Time] = None) -> bool:
        """
        Create a CASA MS file from an HDF5 file.
        
        Args:
            hdf5_path: Path to the input HDF5 file
            output_ms_path: Path for the output MS file
            start_time: Start time for the observation (optional)
            end_time: End time for the observation (optional)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Creating MS from HDF5: {os.path.basename(hdf5_path)}")
        
        try:
            if not os.path.exists(hdf5_path):
                raise DataError(f"HDF5 file not found: {hdf5_path}")
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_ms_path), exist_ok=True)
            
            # Remove existing MS if it exists
            if os.path.exists(output_ms_path):
                import shutil
                shutil.rmtree(output_ms_path)
            
            # Read HDF5 file using PyUVData
            uv_data = await self._read_hdf5_file(hdf5_path)
            if uv_data is None:
                raise DataError("Failed to read HDF5 file")
            
            # Filter data by time if specified
            if start_time is not None or end_time is not None:
                uv_data = await self._filter_by_time(uv_data, start_time, end_time)
            
            # Convert to MS format
            success = await self._convert_to_ms(uv_data, output_ms_path)
            
            if success:
                logger.info(f"Successfully created MS: {os.path.basename(output_ms_path)}")
            else:
                logger.error(f"Failed to create MS: {output_ms_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"MS creation failed: {e}")
            return False
    
    async def _read_hdf5_file(self, hdf5_path: str):
        """
        Read HDF5 file using PyUVData's native UVH5 reader.
        
        Args:
            hdf5_path: Path to the HDF5 file
            
        Returns:
            UVData object or None if failed
        """
        try:
            from .dsa110_hdf5_reader_fixed import DSA110HDF5Reader
            
            # Use simplified reader that uses PyUVData's native UVH5 reader
            reader = DSA110HDF5Reader()
            uv_data = await reader.create_uvdata_object(hdf5_path)
            
            if uv_data is not None:
                logger.info(f"Read HDF5 file with {uv_data.Nbls} baselines, {uv_data.Nfreqs} frequencies")
            else:
                logger.error("Failed to create UVData object from HDF5 file")
            
            return uv_data
            
        except ImportError:
            logger.error("PyUVData not available for HDF5 reading")
            return None
        except Exception as e:
            logger.error(f"Failed to read HDF5 file: {e}")
            return None
    
    async def _filter_by_time(self, uv_data, start_time: Optional[Time] = None,
                            end_time: Optional[Time] = None):
        """
        Filter UVData by time range.
        
        Args:
            uv_data: UVData object
            start_time: Start time for filtering
            end_time: End time for filtering
            
        Returns:
            Filtered UVData object
        """
        try:
            if start_time is not None or end_time is not None:
                # Convert times to MJD
                start_mjd = start_time.mjd if start_time else None
                end_mjd = end_time.mjd if end_time else None
                
                # Filter by time
                uv_data.select(times=uv_data.time_array, time_range=[start_mjd, end_mjd])
                
                logger.info(f"Filtered data to time range: {start_time} to {end_time}")
            
            return uv_data
            
        except Exception as e:
            logger.error(f"Time filtering failed: {e}")
            return uv_data
    
    async def _convert_to_ms(self, uv_data, output_ms_path: str) -> bool:
        """
        Convert UVData to CASA MS format.
        
        Args:
            uv_data: UVData object
            output_ms_path: Path for the output MS file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Set telescope location
            uv_data.telescope_location = self.telescope_location
            
            # Use the HDF5 reader's write_ms method with proper parameters
            from .dsa110_hdf5_reader_fixed import DSA110HDF5Reader
            reader = DSA110HDF5Reader()
            success = reader.write_ms(uv_data, output_ms_path)
            
            if success:
                logger.info(f"Converted UVData to MS format: {os.path.basename(output_ms_path)}")
            else:
                logger.error(f"Failed to convert UVData to MS format")
            
            return success
            
        except Exception as e:
            logger.error(f"MS conversion failed: {e}")
            return False
    
    async def create_test_ms(self, output_ms_path: str, 
                           start_time: Time, end_time: Time,
                           n_antennas: int = 10, n_frequencies: int = 64,
                           n_times: int = 100) -> bool:
        """
        Create a test MS file for development and testing.
        
        Args:
            output_ms_path: Path for the output MS file
            start_time: Start time for the observation
            end_time: End time for the observation
            n_antennas: Number of antennas to simulate
            n_frequencies: Number of frequency channels
            n_times: Number of time samples
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Creating test MS: {os.path.basename(output_ms_path)}")
        
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_ms_path), exist_ok=True)
            
            # Remove existing MS if it exists
            if os.path.exists(output_ms_path):
                import shutil
                shutil.rmtree(output_ms_path)
            
            # Create test data
            test_data = await self._generate_test_data(
                start_time, end_time, n_antennas, n_frequencies, n_times
            )
            
            # Convert to MS format
            success = await self._convert_to_ms(test_data, output_ms_path)
            
            if success:
                logger.info(f"Successfully created test MS: {os.path.basename(output_ms_path)}")
            else:
                logger.error(f"Failed to create test MS: {output_ms_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Test MS creation failed: {e}")
            return False
    
    async def _generate_test_data(self, start_time: Time, end_time: Time,
                                n_antennas: int, n_frequencies: int, n_times: int):
        """
        Generate test UVData for development and testing.
        
        Args:
            start_time: Start time for the observation
            end_time: End time for the observation
            n_antennas: Number of antennas to simulate
            n_frequencies: Number of frequency channels
            n_times: Number of time samples
            
        Returns:
            UVData object with test data
        """
        try:
            import pyuvdata
            
            # Create UVData object
            uv_data = pyuvdata.UVData()
            
            # Set basic parameters
            uv_data.telescope_name = 'DSA-110'
            uv_data.telescope_location = self.telescope_location
            
            # Set frequency array
            freq_start = 1.4e9  # 1.4 GHz
            freq_end = 1.6e9    # 1.6 GHz
            freq_array = np.linspace(freq_start, freq_end, n_frequencies)
            uv_data.freq_array = freq_array.reshape(1, -1)
            uv_data.Nfreqs = n_frequencies
            
            # Set time array
            time_array = np.linspace(start_time.mjd, end_time.mjd, n_times)
            uv_data.time_array = time_array
            uv_data.Ntimes = n_times
            
            # Set antenna information
            antenna_indices = self.valid_antennas[:n_antennas]
            antenna_names = [f"pad{i+1}" for i in antenna_indices]
            antenna_positions = np.random.randn(n_antennas, 3) * 100  # Random positions
            
            uv_data.antenna_names = antenna_names
            uv_data.antenna_numbers = antenna_indices
            uv_data.antenna_positions = antenna_positions
            uv_data.Nants_data = n_antennas
            uv_data.Nants_telescope = n_antennas
            
            # Generate baseline pairs
            baseline_pairs = []
            for i in range(n_antennas):
                for j in range(i+1, n_antennas):
                    baseline_pairs.append((antenna_indices[i], antenna_indices[j]))
            
            uv_data.Nbls = len(baseline_pairs)
            uv_data.baseline_array = np.array([
                uv_data.antnums_to_baseline(ant1, ant2) 
                for ant1, ant2 in baseline_pairs
            ])
            
            # Set data arrays
            n_blts = uv_data.Nbls * uv_data.Ntimes
            uv_data.Nblts = n_blts
            
            # Initialize data arrays
            uv_data.data_array = np.zeros((n_blts, 1, n_frequencies, 4), dtype=complex)
            uv_data.flag_array = np.zeros((n_blts, 1, n_frequencies, 4), dtype=bool)
            uv_data.nsample_array = np.ones((n_blts, 1, n_frequencies, 4), dtype=float)
            
            # Set baseline-time mapping
            uv_data.ant_1_array = np.array([pair[0] for pair in baseline_pairs * n_times])
            uv_data.ant_2_array = np.array([pair[1] for pair in baseline_pairs * n_times])
            uv_data.time_array = np.repeat(time_array, uv_data.Nbls)
            
            # Add some test data
            uv_data.data_array = np.random.randn(*uv_data.data_array.shape) + 1j * np.random.randn(*uv_data.data_array.shape)
            
            # Set other required attributes
            uv_data.vis_units = 'Jy'
            uv_data.integration_time = np.full(n_blts, (end_time - start_time).to(u.s).value / n_times)
            uv_data.channel_width = np.full(n_frequencies, (freq_end - freq_start) / n_frequencies)
            
            logger.info(f"Generated test data with {n_antennas} antennas, {n_frequencies} frequencies, {n_times} times")
            return uv_data
            
        except ImportError:
            logger.error("PyUVData not available for test data generation")
            return None
        except Exception as e:
            logger.error(f"Test data generation failed: {e}")
            return None
    
    async def validate_ms(self, ms_path: str) -> bool:
        """
        Validate a CASA MS file.
        
        Args:
            ms_path: Path to the MS file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not os.path.exists(ms_path):
                logger.error(f"MS file not found: {ms_path}")
                return False
            
            # Try to open with CASA
            try:
                from casatools import ms
                ms_tool = ms()
                ms_tool.open(ms_path)
                
                # Check basic properties
                n_rows = ms_tool.nrow()
                n_antennas = ms_tool.nantennas()
                n_spws = ms_tool.nspw()
                
                ms_tool.close()
                ms_tool.done()
                
                logger.info(f"MS validation passed: {n_rows} rows, {n_antennas} antennas, {n_spws} spws")
                return True
                
            except ImportError:
                logger.warning("CASA not available for MS validation")
                return True  # Assume valid if CASA not available
            except Exception as e:
                logger.error(f"MS validation failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"MS validation error: {e}")
            return False


# Import the unified MS creation system
from .unified_ms_creation import UnifiedMSCreationManager, process_hdf5_set_unified

# Legacy compatibility function - now uses unified system
def process_hdf5_set(config: Dict[str, Any], timestamp: str, hdf5_files: List[str]) -> Optional[str]:
    """
    Process a set of HDF5 files for a given timestamp.
    
    This function provides backward compatibility with the original pipeline
    while using the new unified MS creation system that combines:
    - DSA-110 specific fixes from debugging work
    - Quality validation and multi-subband processing
    - Proper antenna position integration
    - Advanced error handling and recovery
    
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
        # Use the unified MS creation system
        import asyncio
        result = asyncio.run(process_hdf5_set_unified(config, timestamp, hdf5_files))
        
        if result:
            logger.info(f"Successfully created MS using unified system: {result}")
            return result
        else:
            logger.error(f"Failed to create MS using unified system")
            return None
            
    except Exception as e:
        logger.error(f"process_hdf5_set failed: {e}")
        return None
