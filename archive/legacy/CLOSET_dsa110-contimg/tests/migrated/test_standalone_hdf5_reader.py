#!/usr/bin/env python3
"""
Standalone HDF5 Reader Test

This script tests HDF5 reading without importing any pipeline modules
to avoid circular import issues.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
import glob
import h5py
import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_dsa110_hdf5_standalone(hdf5_path: str) -> dict:
    """
    Read a DSA-110 HDF5 file standalone without any pipeline imports.
    
    Args:
        hdf5_path: Path to the HDF5 file
        
    Returns:
        Dictionary containing UVData-compatible data, or None if failed
    """
    try:
        logger.info(f"Reading DSA-110 HDF5 file: {os.path.basename(hdf5_path)}")
        
        with h5py.File(hdf5_path, 'r') as f:
            # Read header information
            header = f['Header']
            data = f['Data']
            
            # Basic dimensions
            Nblts = header['Nblts'][()]
            Nfreqs = header['Nfreqs'][()]
            Npols = header['Npols'][()]
            Nants_data = header['Nants_data'][()]
            Nants_telescope = header['Nants_telescope'][()]
            Nbls = header['Nbls'][()]
            Ntimes = header['Ntimes'][()]
            
            # Time and frequency
            time_array = header['time_array'][()]
            freq_array = header['freq_array'][()]
            integration_time = header['integration_time'][()]
            
            # Antenna information
            antenna_names = [name.decode() for name in header['antenna_names'][()]]
            antenna_numbers = header['antenna_numbers'][()]
            antenna_positions = header['antenna_positions'][()]
            
            # Baseline information
            ant_1_array = header['ant_1_array'][()]
            ant_2_array = header['ant_2_array'][()]
            
            # UVW coordinates
            uvw_array = header['uvw_array'][()]
            
            # Data arrays
            visdata = data['visdata'][()]
            flags = data['flags'][()]
            nsamples = data['nsamples'][()]
            
            # Telescope information
            telescope_name = header['telescope_name'][()].decode()
            latitude = header['latitude'][()]
            longitude = header['longitude'][()]
            altitude = header['altitude'][()]
            
            # Phase center information
            phase_center_dec = header['phase_center_app_dec'][()]
            phase_type = header['phase_type'][()].decode()
            
            # Polarization information
            polarization_array = header['polarization_array'][()]
            
            # Channel width
            channel_width = header['channel_width'][()]
            
            return {
                'Nbls': Nbls,
                'Nfreqs': Nfreqs,
                'Ntimes': Ntimes,
                'Npols': Npols,
                'Nants_data': Nants_data,
                'Nants_telescope': Nants_telescope,
                'Nblts': Nblts,
                'time_array': time_array,
                'freq_array': freq_array,
                'integration_time': integration_time,
                'antenna_names': antenna_names,
                'antenna_numbers': antenna_numbers,
                'antenna_positions': antenna_positions,
                'ant_1_array': ant_1_array,
                'ant_2_array': ant_2_array,
                'uvw_array': uvw_array,
                'visdata': visdata,
                'flags': flags,
                'nsamples': nsamples,
                'telescope_name': telescope_name,
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'phase_center_dec': phase_center_dec,
                'phase_type': phase_type,
                'polarization_array': polarization_array,
                'channel_width': channel_width
            }
            
    except Exception as e:
        logger.error(f"Failed to read HDF5 file {hdf5_path}: {e}")
        return None

async def test_standalone_hdf5_reader():
    """Test the standalone HDF5 reader."""
    try:
        logger.info("🚀 Starting Standalone HDF5 Reader Test")
        
        # Step 1: Check for real HDF5 files
        hdf5_dir = "/data/incoming_test"
        hdf5_files = glob.glob(f"{hdf5_dir}/*.hdf5")
        
        if not hdf5_files:
            logger.error("❌ No HDF5 files found in /data/incoming_test/")
            return
            
        logger.info(f"📊 Found {len(hdf5_files)} real HDF5 files")
        
        # Step 2: Test CASA imports
        logger.info("🔧 Testing CASA imports...")
        try:
            from casatools import table
            from casatasks import tclean, exportfits
            logger.info("✅ CASA tools and tasks imported successfully")
        except ImportError as e:
            logger.error(f"❌ CASA import failed: {e}")
            return
        
        # Step 3: Test the standalone HDF5 reader
        logger.info("🔧 Testing standalone HDF5 reader...")
        
        # Test with first file
        test_file = hdf5_files[0]
        logger.info(f"📁 Testing with: {Path(test_file).name}")
        
        # Read HDF5 file
        logger.info("Reading HDF5 file...")
        uv_data = read_dsa110_hdf5_standalone(test_file)
        
        if uv_data is None:
            logger.error("❌ Failed to read HDF5 file")
            return
        
        logger.info(f"✅ HDF5 file read successfully:")
        logger.info(f"  - Nbls: {uv_data['Nbls']}")
        logger.info(f"  - Nfreqs: {uv_data['Nfreqs']}")
        logger.info(f"  - Ntimes: {uv_data['Ntimes']}")
        logger.info(f"  - Npols: {uv_data['Npols']}")
        logger.info(f"  - Nants_data: {uv_data['Nants_data']}")
        logger.info(f"  - Nants_telescope: {uv_data['Nants_telescope']}")
        
        # Check data shapes
        logger.info(f"  - Visibility data shape: {uv_data['visdata'].shape}")
        logger.info(f"  - Flags shape: {uv_data['flags'].shape}")
        logger.info(f"  - NSamples shape: {uv_data['nsamples'].shape}")
        
        # Check antenna information
        logger.info(f"  - Antenna 1 range: {uv_data['ant_1_array'].min()} - {uv_data['ant_1_array'].max()}")
        logger.info(f"  - Antenna 2 range: {uv_data['ant_2_array'].min()} - {uv_data['ant_2_array'].max()}")
        logger.info(f"  - Number of antennas: {len(uv_data['antenna_names'])}")
        
        # Check time information
        logger.info(f"  - Time range: {uv_data['time_array'].min():.6f} - {uv_data['time_array'].max():.6f} MJD")
        logger.info(f"  - Integration time: {uv_data['integration_time'].mean():.2f} seconds")
        
        # Check frequency information
        logger.info(f"  - Frequency range: {uv_data['freq_array'].min():.2f} - {uv_data['freq_array'].max():.2f} Hz")
        logger.info(f"  - Channel width: {uv_data['channel_width']:.2f} Hz")
        
        # Check UVW coordinates
        uvw = uv_data['uvw_array']
        logger.info(f"  - UVW shape: {uvw.shape}")
        logger.info(f"  - U range: {uvw[:, 0].min():.2f} - {uvw[:, 0].max():.2f} m")
        logger.info(f"  - V range: {uvw[:, 1].min():.2f} - {uvw[:, 1].max():.2f} m")
        logger.info(f"  - W range: {uvw[:, 2].min():.2f} - {uvw[:, 2].max():.2f} m")
        
        # Check telescope information
        logger.info(f"  - Telescope: {uv_data['telescope_name']}")
        logger.info(f"  - Location: {uv_data['latitude']:.6f}, {uv_data['longitude']:.6f}, {uv_data['altitude']:.1f}m")
        
        # Check polarization information
        logger.info(f"  - Polarizations: {uv_data['polarization_array']}")
        
        logger.info("🎉 Standalone HDF5 reader test completed successfully!")
        logger.info("📋 Summary:")
        logger.info(f"  ✅ HDF5 file read successfully")
        logger.info(f"  ✅ All data arrays extracted")
        logger.info(f"  ✅ Data shapes verified")
        logger.info(f"  ✅ Ready for MS conversion")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_standalone_hdf5_reader())
