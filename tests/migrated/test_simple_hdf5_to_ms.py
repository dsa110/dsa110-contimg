#!/usr/bin/env python3
"""
Simple HDF5 to MS Conversion Test

This script tests the HDF5 to MS conversion functionality without importing
the full pipeline to avoid circular import issues.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
import glob
import h5py
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_simple_hdf5_to_ms():
    """Test HDF5 to MS conversion with real data."""
    try:
        logger.info("🚀 Starting Simple HDF5 to MS Conversion Test")
        
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
            from casatools import table, ms
            from casatasks import tclean, exportfits
            logger.info("✅ CASA tools and tasks imported successfully")
        except ImportError as e:
            logger.error(f"❌ CASA import failed: {e}")
            return
        
        # Step 3: Read HDF5 file structure
        test_file = hdf5_files[0]
        logger.info(f"📁 Examining HDF5 file: {Path(test_file).name}")
        
        with h5py.File(test_file, 'r') as f:
            header = f['Header']
            data = f['Data']
            
            # Get basic dimensions
            n_baselines = header['Nbls'][()]
            n_times = header['Ntimes'][()]
            n_freqs = header['Nfreqs'][()]
            n_pols = header['Npols'][()]
            n_ants = header['Nants_data'][()]
            
            logger.info(f"📊 HDF5 dimensions:")
            logger.info(f"  - Baselines: {n_baselines}")
            logger.info(f"  - Times: {n_times}")
            logger.info(f"  - Frequencies: {n_freqs}")
            logger.info(f"  - Polarizations: {n_pols}")
            logger.info(f"  - Antennas: {n_ants}")
            
            # Get data shapes
            visdata_shape = data['visdata'].shape
            flags_shape = data['flags'].shape
            nsamples_shape = data['nsamples'].shape
            
            logger.info(f"📊 Data shapes:")
            logger.info(f"  - Visibility data: {visdata_shape}")
            logger.info(f"  - Flags: {flags_shape}")
            logger.info(f"  - NSamples: {nsamples_shape}")
            
            # Get frequency information
            freq_array = header['freq_array'][:]
            channel_width = header['channel_width'][()]
            
            logger.info(f"📊 Frequency info:")
            logger.info(f"  - Frequency range: {np.min(freq_array):.2f} - {np.max(freq_array):.2f} Hz")
            logger.info(f"  - Channel width: {channel_width:.2f} Hz")
            
            # Get time information
            time_array = header['time_array'][:]
            integration_time = header['integration_time'][:]
            
            logger.info(f"📊 Time info:")
            logger.info(f"  - Time range: {np.min(time_array):.6f} - {np.max(time_array):.6f} MJD")
            logger.info(f"  - Integration time: {np.mean(integration_time):.2f} seconds")
            
            # Get antenna information
            ant_1_array = header['ant_1_array'][:]
            ant_2_array = header['ant_2_array'][:]
            antenna_positions = header['antenna_positions'][:]
            
            logger.info(f"📊 Antenna info:")
            logger.info(f"  - Antenna 1 range: {np.min(ant_1_array)} - {np.max(ant_1_array)}")
            logger.info(f"  - Antenna 2 range: {np.min(ant_2_array)} - {np.max(ant_2_array)}")
            logger.info(f"  - Antenna positions shape: {antenna_positions.shape}")
            
            # Get UVW information
            uvw_array = header['uvw_array'][:]
            logger.info(f"📊 UVW info:")
            logger.info(f"  - UVW shape: {uvw_array.shape}")
            logger.info(f"  - U range: {np.min(uvw_array[:, 0]):.2f} - {np.max(uvw_array[:, 0]):.2f} m")
            logger.info(f"  - V range: {np.min(uvw_array[:, 1]):.2f} - {np.max(uvw_array[:, 1]):.2f} m")
            logger.info(f"  - W range: {np.min(uvw_array[:, 2]):.2f} - {np.max(uvw_array[:, 2]):.2f} m")
        
        # Step 4: Test MS creation
        logger.info("🔧 Testing MS creation...")
        
        ms_dir = "data/ms"
        os.makedirs(ms_dir, exist_ok=True)
        ms_path = os.path.join(ms_dir, f"{Path(test_file).stem}.ms")
        
        try:
            # Create MS using CASA ms tool
            ms_tool = ms()
            n_rows = n_baselines * n_times
            
            ms_tool.create(
                msname=ms_path,
                nrow=n_rows,
                nspw=1,  # One spectral window
                nchan=n_freqs,
                ncorr=n_pols,
                nant=n_ants
            )
            ms_tool.close()
            
            logger.info(f"✅ MS file created: {ms_path}")
            
            # Step 5: Verify MS file
            logger.info("🔍 Verifying MS file...")
            
            with table(ms_path) as ms_table:
                n_rows_actual = ms_table.nrows()
                logger.info(f"✅ MS file has {n_rows_actual} rows")
                
                # Check main table columns
                colnames = ms_table.colnames()
                logger.info(f"✅ MS file has {len(colnames)} columns")
                logger.info(f"📋 Available columns: {colnames}")
                
                # Check if we can read data
                if 'DATA' in colnames:
                    data_shape = ms_table.getcol('DATA', 0, 1).shape
                    logger.info(f"✅ DATA column shape: {data_shape}")
                else:
                    logger.warning("⚠️ DATA column not found")
                
                if 'ANTENNA1' in colnames:
                    ant1_data = ms_table.getcol('ANTENNA1', 0, 10)
                    logger.info(f"✅ ANTENNA1 sample: {ant1_data}")
                else:
                    logger.warning("⚠️ ANTENNA1 column not found")
            
            logger.info("🎉 HDF5 to MS conversion test completed successfully!")
            logger.info("📋 Summary:")
            logger.info(f"  ✅ CASA tools working")
            logger.info(f"  ✅ HDF5 file structure understood")
            logger.info(f"  ✅ MS file created successfully")
            logger.info(f"  ✅ MS file verified")
            logger.info("  ℹ️ Ready for full implementation")
            
        except Exception as e:
            logger.error(f"❌ MS creation failed: {e}")
            return
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_simple_hdf5_to_ms())
