#!/usr/bin/env python3
"""
Test script for UVW coordinate validation in existing MS files.

This script tests the UVW coordinate validation functionality
using existing MS files in the ms_stage1 directory.
"""

import os
import sys
import logging
import numpy as np
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dsa110.utils.logging import get_logger

logger = get_logger(__name__)


def test_ms_uvw_validation(ms_path: str):
    """
    Test UVW coordinate validation in an existing MS file.
    """
    logger.info(f"Testing UVW coordinates in MS file: {ms_path}")
    
    try:
        from casatools import table
        
        # Open MS file
        table_tool = table()
        table_tool.open(ms_path)
        
        # Get basic table information
        nrows = table_tool.nrows()
        logger.info(f"MS table has {nrows} rows")
        
        # Get UVW coordinates
        uvw_data = table_tool.getcol('UVW')
        logger.info(f"UVW data shape: {uvw_data.shape}")
        logger.info(f"UVW data dtype: {uvw_data.dtype}")
        
        # Calculate baseline lengths based on shape
        if uvw_data.shape[0] == 3:  # Shape is (3, nrows)
            baseline_lengths = np.sqrt(uvw_data[0]**2 + uvw_data[1]**2 + uvw_data[2]**2)
            u_range = [np.min(uvw_data[0]), np.max(uvw_data[0])]
            v_range = [np.min(uvw_data[1]), np.max(uvw_data[1])]
            w_range = [np.min(uvw_data[2]), np.max(uvw_data[2])]
        else:  # Shape is (nrows, 3)
            baseline_lengths = np.sqrt(uvw_data[:, 0]**2 + uvw_data[:, 1]**2 + uvw_data[:, 2]**2)
            u_range = [np.min(uvw_data[:, 0]), np.max(uvw_data[:, 0])]
            v_range = [np.min(uvw_data[:, 1]), np.max(uvw_data[:, 1])]
            w_range = [np.min(uvw_data[:, 2]), np.max(uvw_data[:, 2])]
        
        # Calculate statistics
        mean_baseline = np.mean(baseline_lengths)
        max_baseline = np.max(baseline_lengths)
        min_baseline = np.min(baseline_lengths)
        std_baseline = np.std(baseline_lengths)
        
        logger.info(f"UVW coordinate statistics:")
        logger.info(f"  Mean baseline length: {mean_baseline:.3f} meters")
        logger.info(f"  Max baseline length: {max_baseline:.3f} meters")
        logger.info(f"  Min baseline length: {min_baseline:.3f} meters")
        logger.info(f"  Std baseline length: {std_baseline:.3f} meters")
        
        logger.info(f"UVW coordinate ranges:")
        logger.info(f"  U: {u_range[0]:.3f} to {u_range[1]:.3f} meters")
        logger.info(f"  V: {v_range[0]:.3f} to {v_range[1]:.3f} meters")
        logger.info(f"  W: {w_range[0]:.3f} to {w_range[1]:.3f} meters")
        
        # Check for any NaN or infinite values
        has_nan = np.any(np.isnan(uvw_data))
        has_inf = np.any(np.isinf(uvw_data))
        
        logger.info(f"UVW data quality:")
        logger.info(f"  Has NaN values: {has_nan}")
        logger.info(f"  Has infinite values: {has_inf}")
        
        # Assess if UVW coordinates look correct for DSA-110
        # DSA-110 has baselines up to ~2.6 km
        if max_baseline > 1000:  # More than 1 km
            logger.info("✅ UVW coordinates appear correct - baselines > 1 km detected")
            uv_correct = True
        else:
            logger.warning("⚠️ UVW coordinates may be incorrect - baselines < 1 km")
            uv_correct = False
        
        # Check if baseline lengths are reasonable
        if mean_baseline > 100:  # Mean baseline > 100m
            logger.info("✅ Mean baseline length appears reasonable")
            mean_correct = True
        else:
            logger.warning("⚠️ Mean baseline length seems too small")
            mean_correct = False
        
        table_tool.close()
        
        return {
            'uvw_data': uvw_data,
            'baseline_lengths': baseline_lengths,
            'mean_baseline': mean_baseline,
            'max_baseline': max_baseline,
            'min_baseline': min_baseline,
            'has_nan': has_nan,
            'has_inf': has_inf,
            'uv_correct': uv_correct,
            'mean_correct': mean_correct
        }
        
    except Exception as e:
        logger.error(f"Failed to validate UVW coordinates: {e}")
        return None


def test_uvw_restoration_methods(ms_path: str):
    """
    Test the UVW restoration methods on an existing MS file.
    """
    logger.info(f"Testing UVW restoration methods on: {ms_path}")
    
    try:
        from casatools import table
        
        # First, get the current UVW data
        table_tool = table()
        table_tool.open(ms_path, nomodify=False)
        
        current_uvw = table_tool.getcol('UVW')
        logger.info(f"Current UVW shape: {current_uvw.shape}")
        
        # Calculate current baseline lengths
        if current_uvw.shape[0] == 3:
            current_baseline_lengths = np.sqrt(current_uvw[0]**2 + current_uvw[1]**2 + current_uvw[2]**2)
        else:
            current_baseline_lengths = np.sqrt(current_uvw[:, 0]**2 + current_uvw[:, 1]**2 + current_uvw[:, 2]**2)
        
        logger.info(f"Current mean baseline: {np.mean(current_baseline_lengths):.3f} meters")
        
        # Create some test UVW coordinates (simulate original HDF5 data)
        # This simulates the correct DSA-110 baseline lengths
        nrows = current_uvw.shape[1] if current_uvw.shape[0] == 3 else current_uvw.shape[0]
        
        # Generate test UVW coordinates with realistic DSA-110 baseline lengths
        np.random.seed(42)  # For reproducible results
        test_uvw = np.random.normal(0, 500, (nrows, 3))  # Mean baseline ~500m
        test_uvw[:, 2] = np.random.normal(0, 100, nrows)  # W coordinates typically smaller
        
        logger.info(f"Test UVW shape: {test_uvw.shape}")
        test_baseline_lengths = np.sqrt(np.sum(test_uvw**2, axis=1))
        logger.info(f"Test mean baseline: {np.mean(test_baseline_lengths):.3f} meters")
        
        # Test Method 1: Direct putcol
        logger.info("Testing Method 1: Direct putcol")
        try:
            uvw_for_ms = test_uvw.T.astype(np.float64)
            table_tool.putcol('UVW', uvw_for_ms)
            
            restored_uvw = table_tool.getcol('UVW')
            if restored_uvw.shape[0] == 3:
                restored_baseline_lengths = np.sqrt(restored_uvw[0]**2 + restored_uvw[1]**2 + restored_uvw[2]**2)
            else:
                restored_baseline_lengths = np.sqrt(restored_uvw[:, 0]**2 + restored_uvw[:, 1]**2 + restored_uvw[:, 2]**2)
            
            logger.info(f"Method 1 - Restored mean baseline: {np.mean(restored_baseline_lengths):.3f} meters")
            
            # Check if restoration was successful
            expected_mean = np.mean(test_baseline_lengths)
            actual_mean = np.mean(restored_baseline_lengths)
            success = abs(actual_mean - expected_mean) < 1.0
            
            logger.info(f"Method 1 success: {success} (expected: {expected_mean:.3f}, actual: {actual_mean:.3f})")
            
        except Exception as e:
            logger.error(f"Method 1 failed: {e}")
        
        # Test Method 2: Row-by-row putcell
        logger.info("Testing Method 2: Row-by-row putcell")
        try:
            # Restore original UVW first
            table_tool.putcol('UVW', current_uvw)
            
            # Now test row-by-row method
            uvw_for_ms = test_uvw.T.astype(np.float64)
            for i in range(min(10, nrows)):  # Test first 10 rows
                table_tool.putcell('UVW', i, uvw_for_ms[:, i])
            
            restored_uvw = table_tool.getcol('UVW')
            if restored_uvw.shape[0] == 3:
                restored_baseline_lengths = np.sqrt(restored_uvw[0]**2 + restored_uvw[1]**2 + restored_uvw[2]**2)
            else:
                restored_baseline_lengths = np.sqrt(restored_uvw[:, 0]**2 + restored_uvw[:, 1]**2 + restored_uvw[:, 2]**2)
            
            logger.info(f"Method 2 - Restored mean baseline: {np.mean(restored_baseline_lengths):.3f} meters")
            
            # Check if restoration was successful
            expected_mean = np.mean(test_baseline_lengths)
            actual_mean = np.mean(restored_baseline_lengths)
            success = abs(actual_mean - expected_mean) < 1.0
            
            logger.info(f"Method 2 success: {success} (expected: {expected_mean:.3f}, actual: {actual_mean:.3f})")
            
        except Exception as e:
            logger.error(f"Method 2 failed: {e}")
        
        # Restore original UVW data
        table_tool.putcol('UVW', current_uvw)
        table_tool.close()
        
    except Exception as e:
        logger.error(f"Failed to test UVW restoration methods: {e}")


def main():
    """
    Main test function.
    """
    logger.info("Starting UVW coordinate validation tests")
    
    # Find MS files (MS files are directories, not files)
    ms_files = []
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name.endswith('.ms'):
                ms_files.append(os.path.join(root, dir_name))
                break
        if ms_files:
            break
    
    if not ms_files:
        logger.error("No MS files found for testing")
        return
    
    ms_path = ms_files[0]
    logger.info(f"Using MS file: {ms_path}")
    
    # Test UVW validation
    result = test_ms_uvw_validation(ms_path)
    if result is None:
        logger.error("Failed to validate UVW coordinates")
        return
    
    # Test UVW restoration methods
    test_uvw_restoration_methods(ms_path)
    
    logger.info("UVW coordinate validation tests completed")


if __name__ == "__main__":
    main()
