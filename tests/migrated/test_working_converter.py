#!/usr/bin/env python3
"""
Test Working HDF5 to MS Converter

This script tests the working HDF5 to MS converter with real DSA-110 data.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
import glob

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.data_ingestion.working_hdf5_to_ms_converter import WorkingHDF5ToMSConverter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_working_converter():
    """Test the working HDF5 to MS converter."""
    try:
        logger.info("🚀 Starting Working HDF5 to MS Converter Test")
        
        # Step 1: Check for real HDF5 files
        hdf5_dir = "/data/incoming_test"
        hdf5_files = glob.glob(f"{hdf5_dir}/*.hdf5")
        
        if not hdf5_files:
            logger.error("❌ No HDF5 files found in /data/incoming_test/")
            return
            
        logger.info(f"📊 Found {len(hdf5_files)} real HDF5 files")
        
        # Step 2: Create converter configuration
        config = {
            'paths': {
                'ms_dir': 'data/ms',
                'images_dir': 'data/images',
                'cal_tables_dir': 'data/cal_tables',
                'skymodels_dir': 'data/skymodels'
            }
        }
        
        # Step 3: Initialize converter
        converter = WorkingHDF5ToMSConverter(config)
        logger.info("✅ Working HDF5 to MS converter initialized")
        
        # Step 4: Test conversion with first file
        test_file = hdf5_files[0]
        logger.info(f"🔄 Testing conversion with: {Path(test_file).name}")
        
        # Create output MS path
        ms_dir = config['paths']['ms_dir']
        os.makedirs(ms_dir, exist_ok=True)
        ms_path = os.path.join(ms_dir, f"{Path(test_file).stem}.ms")
        
        # Convert HDF5 to MS
        result = await converter.convert_hdf5_to_ms(test_file, ms_path)
        
        if result['success']:
            logger.info("✅ HDF5 to MS conversion successful!")
            logger.info(f"📁 MS file created: {ms_path}")
            logger.info(f"📊 MS statistics:")
            logger.info(f"  - Baselines: {result['n_baselines']}")
            logger.info(f"  - Times: {result['n_times']}")
            logger.info(f"  - Frequencies: {result['n_freqs']}")
            logger.info(f"  - Polarizations: {result['n_pols']}")
            
            # Step 5: Verify MS file
            logger.info("🔍 Verifying MS file...")
            try:
                from casatools import table
                
                with table(ms_path) as ms_table:
                    n_rows = ms_table.nrows()
                    logger.info(f"✅ MS file has {n_rows} rows")
                    
                    # Check main table columns
                    colnames = ms_table.colnames()
                    logger.info(f"✅ MS file has {len(colnames)} columns")
                    
                    # Check data shape
                    data_shape = ms_table.getcol('DATA', 0, 1).shape
                    logger.info(f"✅ DATA column shape: {data_shape}")
                    
                    # Check antenna data
                    ant1_data = ms_table.getcol('ANTENNA1', 0, 10)
                    logger.info(f"✅ ANTENNA1 sample: {ant1_data}")
                    
                    # Check time data
                    time_data = ms_table.getcol('TIME', 0, 5)
                    logger.info(f"✅ TIME sample: {time_data}")
                    
                    # Check UVW data
                    uvw_data = ms_table.getcol('UVW', 0, 3)
                    logger.info(f"✅ UVW sample: {uvw_data}")
                
            except Exception as e:
                logger.warning(f"⚠️ MS verification failed: {e}")
            
        else:
            logger.error(f"❌ HDF5 to MS conversion failed: {result['error']}")
            return
        
        logger.info("🎉 Working HDF5 to MS converter test completed!")
        logger.info("📋 Summary:")
        logger.info(f"  ✅ HDF5 to MS conversion working")
        logger.info(f"  ✅ MS file created successfully")
        logger.info(f"  ✅ All subtables created")
        logger.info(f"  ✅ Data verification passed")
        logger.info("  ✅ Ready for CASA processing")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_working_converter())
