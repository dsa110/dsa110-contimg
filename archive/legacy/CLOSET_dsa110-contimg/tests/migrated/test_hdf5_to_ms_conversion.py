#!/usr/bin/env python3
"""
Test HDF5 to MS Conversion

This script tests the HDF5 to MS conversion functionality with real DSA-110 data.
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

from dsa110.utils.logging import get_logger
from dsa110.data_ingestion.complete_hdf5_to_ms_converter import CompleteHDF5ToMSConverter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

async def test_hdf5_to_ms_conversion():
    """Test HDF5 to MS conversion with real data."""
    try:
        logger.info("🚀 Starting HDF5 to MS Conversion Test")
        
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
        converter = CompleteHDF5ToMSConverter(config)
        logger.info("✅ HDF5 to MS converter initialized")
        
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
                    
            except Exception as e:
                logger.warning(f"⚠️ MS verification failed: {e}")
            
        else:
            logger.error(f"❌ HDF5 to MS conversion failed: {result['error']}")
            return
        
        # Step 6: Test multiple file conversion
        logger.info("🔄 Testing multiple file conversion...")
        
        # Use first 3 files for testing
        test_files = hdf5_files[:3]
        logger.info(f"🔄 Converting {len(test_files)} files...")
        
        multi_result = await converter.convert_multiple_hdf5_files(test_files, ms_dir)
        
        if multi_result['total_successful'] > 0:
            logger.info(f"✅ Multiple file conversion successful!")
            logger.info(f"📊 Results: {multi_result['total_successful']}/{multi_result['total_processed']} successful")
            
            # List created MS files
            ms_files = glob.glob(f"{ms_dir}/*.ms")
            logger.info(f"📁 Created {len(ms_files)} MS files:")
            for ms_file in ms_files:
                logger.info(f"  - {Path(ms_file).name}")
        else:
            logger.error("❌ Multiple file conversion failed")
        
        logger.info("🎉 HDF5 to MS conversion test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_hdf5_to_ms_conversion())
