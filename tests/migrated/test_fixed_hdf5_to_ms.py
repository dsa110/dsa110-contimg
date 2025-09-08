#!/usr/bin/env python3
"""
Test Fixed HDF5 to MS Conversion

This script tests the HDF5 to MS conversion using the existing pipeline code
after fixing the circular import issues.
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

async def test_fixed_hdf5_to_ms():
    """Test the fixed HDF5 to MS conversion using existing pipeline code."""
    try:
        logger.info("🚀 Testing Fixed HDF5 to MS Conversion")
        
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
        
        # Step 3: Test the existing HDF5 to MS conversion
        logger.info("🔧 Testing existing HDF5 to MS conversion...")
        
        try:
            # Import the existing pipeline components
            from core.pipeline.orchestrator import PipelineOrchestrator
            from core.data_ingestion.dsa110_hdf5_reader_fixed import DSA110HDF5Reader
            
            # Create a simple config for testing
            config = {
                'paths': {
                    'ms_stage1_dir': 'data/ms',
                    'log_dir': 'logs'
                },
                'ms_creation': {
                    'same_timestamp_tolerance': 30.0,
                    'min_data_quality': 0.8,
                    'max_missing_subbands': 2,
                    'min_integration_time': 10.0
                }
            }
            
            # Create orchestrator
            orchestrator = PipelineOrchestrator(config)
            logger.info("✅ Pipeline orchestrator created successfully")
            
            # Test HDF5 to MS conversion
            logger.info("🔧 Testing HDF5 to MS conversion...")
            ms_files = await orchestrator.process_hdf5_to_ms(hdf5_dir)
            
            if ms_files:
                logger.info(f"✅ Successfully created {len(ms_files)} MS files")
                
                # Check the first MS file
                if ms_files:
                    ms_path = ms_files[0]
                    logger.info(f"📁 First MS file: {ms_path}")
                    
                    # Verify MS file
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
                        logger.info(f"  ✅ Circular imports fixed")
                        logger.info(f"  ✅ Pipeline orchestrator working")
                        logger.info(f"  ✅ HDF5 to MS conversion working")
                        logger.info(f"  ✅ MS files created: {len(ms_files)}")
                        logger.info(f"  ✅ MS file verified")
                        logger.info("  ✅ Ready for CASA processing")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ MS verification failed: {e}")
                else:
                    logger.error("❌ No MS files were created")
                    return
            else:
                logger.error("❌ No MS files were created")
                return
                
        except ImportError as e:
            logger.error(f"❌ Failed to import pipeline components: {e}")
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
    asyncio.run(test_fixed_hdf5_to_ms())
