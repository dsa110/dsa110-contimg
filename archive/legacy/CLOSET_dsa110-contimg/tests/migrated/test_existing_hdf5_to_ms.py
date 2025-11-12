#!/usr/bin/env python3
"""
Test Existing HDF5 to MS Conversion

This script tests the existing HDF5 to MS conversion system without importing
the full pipeline to avoid circular import issues.
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_existing_hdf5_to_ms():
    """Test the existing HDF5 to MS conversion system."""
    try:
        logger.info("🚀 Starting Existing HDF5 to MS Conversion Test")
        
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
        
        # Step 3: Test the existing HDF5 reader directly
        logger.info("🔧 Testing existing HDF5 reader...")
        try:
            # Import the HDF5 reader directly to avoid circular imports
            from dsa110.data_ingestion.dsa110_hdf5_reader_fixed import DSA110HDF5Reader
            
            # Test with first file
            test_file = hdf5_files[0]
            logger.info(f"📁 Testing with: {Path(test_file).name}")
            
            # Create reader
            reader = DSA110HDF5Reader()
            
            # Read HDF5 file
            logger.info("Reading HDF5 file...")
            uv_data = await reader.create_uvdata_object(test_file)
            
            if uv_data is None:
                logger.error("❌ Failed to create UVData object")
                return
            
            logger.info(f"✅ UVData object created successfully:")
            logger.info(f"  - Nbls: {uv_data.Nbls}")
            logger.info(f"  - Nfreqs: {uv_data.Nfreqs}")
            logger.info(f"  - Ntimes: {uv_data.Ntimes}")
            logger.info(f"  - Npols: {uv_data.Npols}")
            
            # Create output MS path
            ms_dir = "data/ms"
            os.makedirs(ms_dir, exist_ok=True)
            ms_path = os.path.join(ms_dir, f"{Path(test_file).stem}.ms")
            
            # Write to MS
            logger.info("Writing to MS format...")
            success = reader.write_ms(uv_data, ms_path)
            
            if success:
                logger.info(f"✅ Successfully created MS: {ms_path}")
                
                # Check if MS file was created
                if os.path.exists(ms_path):
                    file_size = os.path.getsize(ms_path)
                    logger.info(f"✅ MS file size: {file_size} bytes")
                    
                    # Step 4: Verify MS file
                    logger.info("🔍 Verifying MS file...")
                    try:
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
                        
                        logger.info("🎉 HDF5 to MS conversion completed successfully!")
                        logger.info("📋 Summary:")
                        logger.info(f"  ✅ HDF5 file read successfully")
                        logger.info(f"  ✅ UVData object created")
                        logger.info(f"  ✅ MS file created: {ms_path}")
                        logger.info(f"  ✅ MS file verified")
                        logger.info("  ✅ Ready for CASA processing")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ MS verification failed: {e}")
                else:
                    logger.error("❌ MS file was not created")
                    return
            else:
                logger.error("❌ Failed to write MS file")
                return
                
        except ImportError as e:
            logger.error(f"❌ Failed to import HDF5 reader: {e}")
            return
        except Exception as e:
            logger.error(f"❌ HDF5 to MS conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_existing_hdf5_to_ms())
