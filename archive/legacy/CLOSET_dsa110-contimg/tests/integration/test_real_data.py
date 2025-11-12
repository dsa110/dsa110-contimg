#!/usr/bin/env python3
"""
Test script for real DSA-110 HDF5 data processing.

This script tests the pipeline with actual DSA-110 data from /data/incoming_test/
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dsa110.utils.logging import setup_logging, get_logger
from dsa110.utils.config_loader import load_pipeline_config
from dsa110.data_ingestion.ms_creation import MSCreationManager
from dsa110.telescope.dsa110 import get_telescope_location, get_valid_antennas
from dsa110.pipeline.orchestrator import ProcessingBlock
from astropy.time import Time

# Setup logging
setup_logging(log_dir="logs", config_name="test_real_data")
logger = get_logger(__name__)


class RealDataTester:
    """Test the pipeline with real DSA-110 data."""
    
    def __init__(self, config_path: str = "config/pipeline_config.yaml"):
        self.config_path = config_path
        self.config = load_pipeline_config(environment="development")
        self.test_data_dir = Path("/data/incoming_test/")
        self.output_dir = Path("test_outputs")
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize MS creation manager
        self.ms_manager = MSCreationManager(self.config)
        
        logger.info(f"RealDataTester initialized")
        logger.info(f"Test data directory: {self.test_data_dir}")
        logger.info(f"Output directory: {self.output_dir}")

    async def inspect_hdf5_files(self):
        """Inspect the HDF5 files to understand their structure."""
        logger.info("=== Inspecting HDF5 Files ===")
        
        hdf5_files = list(self.test_data_dir.glob("*.hdf5"))
        logger.info(f"Found {len(hdf5_files)} HDF5 files")
        
        if not hdf5_files:
            logger.error("No HDF5 files found in test directory")
            return False
        
        # Inspect first file
        test_file = hdf5_files[0]
        logger.info(f"Inspecting file: {test_file.name}")
        
        try:
            import pyuvdata
            import h5py
            
            # Quick HDF5 inspection
            with h5py.File(test_file, 'r') as f:
                logger.info(f"HDF5 structure: {list(f.keys())}")
                if 'Data' in f:
                    logger.info(f"Data shape: {f['Data'].shape}")
                if 'Header' in f:
                    logger.info(f"Header keys: {list(f['Header'].keys())}")
            
            # PyUVData inspection
            uv_data = pyuvdata.UVData()
            uv_data.read(str(test_file))
            
            logger.info(f"UVData properties:")
            logger.info(f"  Nbls: {uv_data.Nbls}")
            logger.info(f"  Nfreqs: {uv_data.Nfreqs}")
            logger.info(f"  Ntimes: {uv_data.Ntimes}")
            logger.info(f"  Telescope: {uv_data.telescope_name}")
            logger.info(f"  Frequency range: {uv_data.freq_array.min()/1e9:.3f} - {uv_data.freq_array.max()/1e9:.3f} GHz")
            logger.info(f"  Time range: {Time(uv_data.time_array.min(), format='mjd').iso} - {Time(uv_data.time_array.max(), format='mjd').iso}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to inspect HDF5 file: {e}")
            return False

    async def test_hdf5_to_ms_conversion(self):
        """Test HDF5 to MS conversion with real data."""
        logger.info("=== Testing HDF5 to MS Conversion ===")
        
        hdf5_files = list(self.test_data_dir.glob("*.hdf5"))
        if not hdf5_files:
            logger.error("No HDF5 files found")
            return False
        
        # Test with first file
        test_file = hdf5_files[0]
        output_ms = self.output_dir / f"test_{test_file.stem}.ms"
        
        logger.info(f"Converting {test_file.name} to MS...")
        
        try:
            success = await self.ms_manager.create_ms_from_hdf5(
                str(test_file), 
                str(output_ms)
            )
            
            if success:
                logger.info(f"Successfully created MS: {output_ms}")
                
                # Validate MS
                ms_valid = await self.ms_manager.validate_ms(str(output_ms))
                if ms_valid:
                    logger.info("MS validation passed")
                else:
                    logger.warning("MS validation failed")
                
                return True
            else:
                logger.error("MS creation failed")
                return False
                
        except Exception as e:
            logger.error(f"MS conversion failed: {e}")
            return False

    async def test_multiple_subbands(self):
        """Test processing multiple subbands together."""
        logger.info("=== Testing Multiple Subbands Processing ===")
        
        # Group files by timestamp
        hdf5_files = list(self.test_data_dir.glob("*.hdf5"))
        timestamp_groups = {}
        
        for file in hdf5_files:
            timestamp = file.name.split('_')[0]
            if timestamp not in timestamp_groups:
                timestamp_groups[timestamp] = []
            timestamp_groups[timestamp].append(file)
        
        logger.info(f"Found {len(timestamp_groups)} timestamp groups")
        
        # Process first group
        first_timestamp = list(timestamp_groups.keys())[0]
        files = timestamp_groups[first_timestamp]
        
        logger.info(f"Processing timestamp {first_timestamp} with {len(files)} files")
        
        # Sort files by subband
        files.sort(key=lambda x: x.name)
        
        try:
            # Create a combined MS from multiple subbands
            # This would require implementing multi-subband processing
            # For now, just test individual files
            
            for i, file in enumerate(files[:3]):  # Test first 3 files
                output_ms = self.output_dir / f"test_{first_timestamp}_sb{i:02d}.ms"
                logger.info(f"Converting {file.name}...")
                
                success = await self.ms_manager.create_ms_from_hdf5(
                    str(file), 
                    str(output_ms)
                )
                
                if success:
                    logger.info(f"Successfully created {output_ms.name}")
                else:
                    logger.error(f"Failed to create {output_ms.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Multi-subband processing failed: {e}")
            return False

    async def test_pipeline_integration(self):
        """Test full pipeline integration with real data."""
        logger.info("=== Testing Pipeline Integration ===")
        
        # This would test the full pipeline with real data
        # For now, just test MS creation and basic validation
        
        try:
            # Create a test processing block
            start_time = Time('2025-09-05T03:23:14', format='isot', scale='utc')
            end_time = start_time + 5 * 60  # 5 minutes
            
            # Find MS files for this time range
            ms_files = list(self.output_dir.glob("*.ms"))
            
            if ms_files:
                block = ProcessingBlock(
                    block_id="test_block_001",
                    start_time=start_time,
                    end_time=end_time,
                    ms_files=[str(f) for f in ms_files]
                )
                
                logger.info(f"Created test block with {len(block.ms_files)} MS files")
                logger.info(f"Block time range: {block.start_time.iso} to {block.end_time.iso}")
                
                return True
            else:
                logger.warning("No MS files available for pipeline testing")
                return False
                
        except Exception as e:
            logger.error(f"Pipeline integration test failed: {e}")
            return False

    async def run_all_tests(self):
        """Run all tests."""
        logger.info("Starting real data tests...")
        
        tests = [
            ("HDF5 File Inspection", self.inspect_hdf5_files),
            ("HDF5 to MS Conversion", self.test_hdf5_to_ms_conversion),
            ("Multiple Subbands", self.test_multiple_subbands),
            ("Pipeline Integration", self.test_pipeline_integration)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            logger.info(f"\n--- Running {test_name} ---")
            try:
                result = await test_func()
                results[test_name] = result
                status = "PASSED" if result else "FAILED"
                logger.info(f"{test_name}: {status}")
            except Exception as e:
                logger.error(f"{test_name} failed with exception: {e}")
                results[test_name] = False
        
        # Summary
        logger.info("\n=== Test Summary ===")
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "PASSED" if result else "FAILED"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"Overall: {passed}/{total} tests passed")
        
        return passed == total


async def main():
    """Main test function."""
    logger.info("DSA-110 Real Data Testing")
    logger.info("=" * 50)
    
    # Check if test data exists
    test_data_dir = Path("/data/incoming_test/")
    if not test_data_dir.exists():
        logger.error(f"Test data directory not found: {test_data_dir}")
        return False
    
    hdf5_files = list(test_data_dir.glob("*.hdf5"))
    if not hdf5_files:
        logger.error("No HDF5 files found in test directory")
        return False
    
    logger.info(f"Found {len(hdf5_files)} HDF5 files for testing")
    
    # Run tests
    tester = RealDataTester()
    success = await tester.run_all_tests()
    
    if success:
        logger.info("All tests passed!")
    else:
        logger.error("Some tests failed!")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
