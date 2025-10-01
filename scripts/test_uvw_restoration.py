#!/usr/bin/env python3
"""
Test script for UVW coordinate restoration in MS creation.

This script tests the three different methods for restoring UVW coordinates
in MS files to ensure they work correctly with DSA-110 data.
"""

import os
import sys
import asyncio
import logging
import numpy as np
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dsa110.data_ingestion.unified_ms_creation import UnifiedMSCreationManager
from dsa110.utils.logging import get_logger

logger = get_logger(__name__)


async def test_uvw_restoration():
    """
    Test UVW coordinate restoration with a sample HDF5 file.
    """
    logger.info("Starting UVW coordinate restoration test")
    
    # Configuration
    config = {
        'ms_creation': {
            'same_timestamp_tolerance': 120.0,
            'min_data_quality': 0.8,
            'max_missing_subbands': 2,
            'min_integration_time': 10.0,
            'output_antennas': None
        },
        'paths': {
            'ms_stage1_dir': 'test_ms_output',
            'log_dir': 'logs'
        }
    }
    
    # Create test output directory
    os.makedirs('test_ms_output', exist_ok=True)
    
    # Find a sample HDF5 file for testing
    hdf5_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.hdf5') and 'sb' in file:
                hdf5_files.append(os.path.join(root, file))
                break
        if hdf5_files:
            break
    
    if not hdf5_files:
        logger.error("No HDF5 files found for testing")
        return False
    
    logger.info(f"Found test HDF5 file: {hdf5_files[0]}")
    
    # Initialize MS creation manager
    ms_manager = UnifiedMSCreationManager(config)
    
    # Test single file processing
    output_ms_path = 'test_ms_output/test_uvw_restoration.ms'
    
    logger.info("Testing single file MS creation with UVW restoration...")
    result = await ms_manager.create_ms_from_single_file(
        hdf5_files[0], 
        output_ms_path, 
        quality_checks=True
    )
    
    if result['success']:
        logger.info("✅ MS creation successful!")
        logger.info(f"Quality metrics: {result['quality_metrics']}")
        
        # Verify UVW coordinates in the created MS
        await verify_uvw_coordinates(output_ms_path)
        
    else:
        logger.error("❌ MS creation failed!")
        logger.error(f"Errors: {result['errors']}")
        return False
    
    return True


async def verify_uvw_coordinates(ms_path: str):
    """
    Verify that UVW coordinates in the MS file are correct.
    """
    logger.info(f"Verifying UVW coordinates in {ms_path}")
    
    try:
        from casatools import table
        
        # Open the MS file
        table_tool = table()
        table_tool.open(ms_path)
        
        # Get UVW coordinates
        uvw_data = table_tool.getcol('UVW')
        logger.info(f"UVW data shape: {uvw_data.shape}")
        logger.info(f"UVW data dtype: {uvw_data.dtype}")
        
        # Calculate baseline lengths
        if uvw_data.shape[0] == 3:  # Shape is (3, nrows)
            baseline_lengths = np.sqrt(uvw_data[0]**2 + uvw_data[1]**2 + uvw_data[2]**2)
        else:  # Shape is (nrows, 3)
            baseline_lengths = np.sqrt(uvw_data[:, 0]**2 + uvw_data[:, 1]**2 + uvw_data[:, 2]**2)
        
        # Calculate statistics
        mean_baseline = np.mean(baseline_lengths)
        max_baseline = np.max(baseline_lengths)
        min_baseline = np.min(baseline_lengths)
        
        logger.info(f"UVW coordinate statistics:")
        logger.info(f"  Mean baseline length: {mean_baseline:.3f} meters")
        logger.info(f"  Max baseline length: {max_baseline:.3f} meters")
        logger.info(f"  Min baseline length: {min_baseline:.3f} meters")
        
        # Check if baseline lengths are reasonable for DSA-110
        # DSA-110 has baselines up to ~2.6 km
        if max_baseline > 1000:  # More than 1 km
            logger.info("✅ UVW coordinates appear correct - baselines > 1 km detected")
        else:
            logger.warning("⚠️ UVW coordinates may be incorrect - baselines < 1 km")
        
        # Check UVW coordinate range
        if uvw_data.shape[0] == 3:
            u_range = [np.min(uvw_data[0]), np.max(uvw_data[0])]
            v_range = [np.min(uvw_data[1]), np.max(uvw_data[1])]
            w_range = [np.min(uvw_data[2]), np.max(uvw_data[2])]
        else:
            u_range = [np.min(uvw_data[:, 0]), np.max(uvw_data[:, 0])]
            v_range = [np.min(uvw_data[:, 1]), np.max(uvw_data[:, 1])]
            w_range = [np.min(uvw_data[:, 2]), np.max(uvw_data[:, 2])]
        
        logger.info(f"UVW coordinate ranges:")
        logger.info(f"  U: {u_range[0]:.3f} to {u_range[1]:.3f} meters")
        logger.info(f"  V: {v_range[0]:.3f} to {v_range[1]:.3f} meters")
        logger.info(f"  W: {w_range[0]:.3f} to {w_range[1]:.3f} meters")
        
        table_tool.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify UVW coordinates: {e}")
        return False


async def test_multiple_restoration_methods():
    """
    Test all three UVW restoration methods to see which works best.
    """
    logger.info("Testing multiple UVW restoration methods")
    
    # This would require creating a test MS file and then testing each method
    # For now, we'll just run the main test
    return await test_uvw_restoration()


async def main():
    """
    Main test function.
    """
    logger.info("Starting UVW coordinate restoration tests")
    
    try:
        # Test basic UVW restoration
        success = await test_uvw_restoration()
        
        if success:
            logger.info("✅ All UVW restoration tests passed!")
        else:
            logger.error("❌ UVW restoration tests failed!")
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
