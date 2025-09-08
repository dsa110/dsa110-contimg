#!/usr/bin/env python3
"""
Diagnostic script for UVW coordinate issues in DSA-110 MS creation.

This script provides detailed diagnostics of UVW coordinate problems
and helps identify the root cause of restoration failures.
"""

import os
import sys
import logging
import numpy as np
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.utils.logging import get_logger

logger = get_logger(__name__)


def diagnose_hdf5_uvw(hdf5_path: str):
    """
    Diagnose UVW coordinates in HDF5 file.
    """
    logger.info(f"Diagnosing UVW coordinates in HDF5 file: {hdf5_path}")
    
    try:
        import h5py
        from pyuvdata import UVData
        
        # Read HDF5 file with PyUVData
        uv_data = UVData()
        uv_data.read(hdf5_path, file_type='uvh5', run_check=False)
        
        # Analyze UVW coordinates
        uvw_array = uv_data.uvw_array
        logger.info(f"HDF5 UVW array shape: {uvw_array.shape}")
        logger.info(f"HDF5 UVW array dtype: {uvw_array.dtype}")
        
        # Calculate baseline lengths
        baseline_lengths = np.sqrt(np.sum(uvw_array**2, axis=1))
        
        logger.info(f"HDF5 UVW statistics:")
        logger.info(f"  Mean baseline length: {np.mean(baseline_lengths):.3f} meters")
        logger.info(f"  Max baseline length: {np.max(baseline_lengths):.3f} meters")
        logger.info(f"  Min baseline length: {np.min(baseline_lengths):.3f} meters")
        logger.info(f"  Std baseline length: {np.std(baseline_lengths):.3f} meters")
        
        # Check UVW coordinate ranges
        u_range = [np.min(uvw_array[:, 0]), np.max(uvw_array[:, 0])]
        v_range = [np.min(uvw_array[:, 1]), np.max(uvw_array[:, 1])]
        w_range = [np.min(uvw_array[:, 2]), np.max(uvw_array[:, 2])]
        
        logger.info(f"HDF5 UVW coordinate ranges:")
        logger.info(f"  U: {u_range[0]:.3f} to {u_range[1]:.3f} meters")
        logger.info(f"  V: {v_range[0]:.3f} to {v_range[1]:.3f} meters")
        logger.info(f"  W: {w_range[0]:.3f} to {w_range[1]:.3f} meters")
        
        # Check for any NaN or infinite values
        has_nan = np.any(np.isnan(uvw_array))
        has_inf = np.any(np.isinf(uvw_array))
        
        logger.info(f"HDF5 UVW data quality:")
        logger.info(f"  Has NaN values: {has_nan}")
        logger.info(f"  Has infinite values: {has_inf}")
        
        return {
            'uvw_array': uvw_array,
            'baseline_lengths': baseline_lengths,
            'mean_baseline': np.mean(baseline_lengths),
            'max_baseline': np.max(baseline_lengths),
            'has_nan': has_nan,
            'has_inf': has_inf
        }
        
    except Exception as e:
        logger.error(f"Failed to diagnose HDF5 UVW coordinates: {e}")
        return None


def diagnose_ms_uvw(ms_path: str):
    """
    Diagnose UVW coordinates in MS file.
    """
    logger.info(f"Diagnosing UVW coordinates in MS file: {ms_path}")
    
    try:
        from casatools import table
        
        # Open MS file
        table_tool = table()
        table_tool.open(ms_path)
        
        # Get UVW coordinates
        uvw_data = table_tool.getcol('UVW')
        logger.info(f"MS UVW data shape: {uvw_data.shape}")
        logger.info(f"MS UVW data dtype: {uvw_data.dtype}")
        
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
        
        logger.info(f"MS UVW statistics:")
        logger.info(f"  Mean baseline length: {np.mean(baseline_lengths):.3f} meters")
        logger.info(f"  Max baseline length: {np.max(baseline_lengths):.3f} meters")
        logger.info(f"  Min baseline length: {np.min(baseline_lengths):.3f} meters")
        logger.info(f"  Std baseline length: {np.std(baseline_lengths):.3f} meters")
        
        logger.info(f"MS UVW coordinate ranges:")
        logger.info(f"  U: {u_range[0]:.3f} to {u_range[1]:.3f} meters")
        logger.info(f"  V: {v_range[0]:.3f} to {v_range[1]:.3f} meters")
        logger.info(f"  W: {w_range[0]:.3f} to {w_range[1]:.3f} meters")
        
        # Check for any NaN or infinite values
        has_nan = np.any(np.isnan(uvw_data))
        has_inf = np.any(np.isinf(uvw_data))
        
        logger.info(f"MS UVW data quality:")
        logger.info(f"  Has NaN values: {has_nan}")
        logger.info(f"  Has infinite values: {has_inf}")
        
        table_tool.close()
        
        return {
            'uvw_data': uvw_data,
            'baseline_lengths': baseline_lengths,
            'mean_baseline': np.mean(baseline_lengths),
            'max_baseline': np.max(baseline_lengths),
            'has_nan': has_nan,
            'has_inf': has_inf
        }
        
    except Exception as e:
        logger.error(f"Failed to diagnose MS UVW coordinates: {e}")
        return None


def test_uvw_restoration_methods(ms_path: str, original_uvw: np.ndarray):
    """
    Test different methods for restoring UVW coordinates.
    """
    logger.info("Testing different UVW restoration methods")
    
    try:
        from casatools import table
        
        # Method 1: Direct putcol with transposed data
        logger.info("Testing Method 1: Direct putcol with transposed data")
        table_tool = table()
        table_tool.open(ms_path, nomodify=False)
        
        # Get current UVW data
        current_uvw = table_tool.getcol('UVW')
        logger.info(f"Current MS UVW shape: {current_uvw.shape}")
        
        # Prepare data for Method 1
        uvw_transposed = original_uvw.T.astype(np.float64)
        logger.info(f"Transposed UVW shape: {uvw_transposed.shape}")
        
        # Try Method 1
        try:
            table_tool.putcol('UVW', uvw_transposed)
            restored_uvw_1 = table_tool.getcol('UVW')
            logger.info(f"Method 1 - Restored UVW shape: {restored_uvw_1.shape}")
            
            # Calculate baseline lengths
            if restored_uvw_1.shape[0] == 3:
                baseline_lengths_1 = np.sqrt(restored_uvw_1[0]**2 + restored_uvw_1[1]**2 + restored_uvw_1[2]**2)
            else:
                baseline_lengths_1 = np.sqrt(restored_uvw_1[:, 0]**2 + restored_uvw_1[:, 1]**2 + restored_uvw_1[:, 2]**2)
            
            logger.info(f"Method 1 - Mean baseline: {np.mean(baseline_lengths_1):.3f} meters")
            
        except Exception as e:
            logger.error(f"Method 1 failed: {e}")
            restored_uvw_1 = None
            baseline_lengths_1 = None
        
        # Method 2: Row-by-row putcell
        logger.info("Testing Method 2: Row-by-row putcell")
        try:
            nrows = table_tool.nrows()
            for i in range(min(10, nrows)):  # Test first 10 rows
                table_tool.putcell('UVW', i, uvw_transposed[:, i])
            
            restored_uvw_2 = table_tool.getcol('UVW')
            logger.info(f"Method 2 - Restored UVW shape: {restored_uvw_2.shape}")
            
            # Calculate baseline lengths
            if restored_uvw_2.shape[0] == 3:
                baseline_lengths_2 = np.sqrt(restored_uvw_2[0]**2 + restored_uvw_2[1]**2 + restored_uvw_2[2]**2)
            else:
                baseline_lengths_2 = np.sqrt(restored_uvw_2[:, 0]**2 + restored_uvw_2[:, 1]**2 + restored_uvw_2[:, 2]**2)
            
            logger.info(f"Method 2 - Mean baseline: {np.mean(baseline_lengths_2):.3f} meters")
            
        except Exception as e:
            logger.error(f"Method 2 failed: {e}")
            restored_uvw_2 = None
            baseline_lengths_2 = None
        
        table_tool.close()
        
        # Compare results
        original_mean = np.mean(np.sqrt(np.sum(original_uvw**2, axis=1)))
        logger.info(f"Original mean baseline: {original_mean:.3f} meters")
        
        if baseline_lengths_1 is not None:
            method1_success = abs(np.mean(baseline_lengths_1) - original_mean) < 1.0
            logger.info(f"Method 1 success: {method1_success}")
        
        if baseline_lengths_2 is not None:
            method2_success = abs(np.mean(baseline_lengths_2) - original_mean) < 1.0
            logger.info(f"Method 2 success: {method2_success}")
        
    except Exception as e:
        logger.error(f"Failed to test UVW restoration methods: {e}")


def main():
    """
    Main diagnostic function.
    """
    logger.info("Starting UVW coordinate diagnostic")
    
    # Find HDF5 files
    hdf5_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.hdf5') and 'sb' in file:
                hdf5_files.append(os.path.join(root, file))
                break
        if hdf5_files:
            break
    
    if not hdf5_files:
        logger.error("No HDF5 files found for diagnosis")
        return
    
    hdf5_path = hdf5_files[0]
    logger.info(f"Using HDF5 file: {hdf5_path}")
    
    # Diagnose HDF5 UVW coordinates
    hdf5_info = diagnose_hdf5_uvw(hdf5_path)
    if hdf5_info is None:
        logger.error("Failed to diagnose HDF5 file")
        return
    
    # Find MS files
    ms_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.ms'):
                ms_files.append(os.path.join(root, file))
                break
        if ms_files:
            break
    
    if ms_files:
        ms_path = ms_files[0]
        logger.info(f"Using MS file: {ms_path}")
        
        # Diagnose MS UVW coordinates
        ms_info = diagnose_ms_uvw(ms_path)
        if ms_info is not None:
            # Test restoration methods
            test_uvw_restoration_methods(ms_path, hdf5_info['uvw_array'])
    else:
        logger.info("No MS files found for diagnosis")


if __name__ == "__main__":
    main()
