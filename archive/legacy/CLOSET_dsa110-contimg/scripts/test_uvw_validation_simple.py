#!/usr/bin/env python3
"""
Simple UVW coordinate validation test.

This script validates that the UVW coordinates in MS files are correct
without requiring CASA calibration operations.
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


def validate_uvw_coordinates(ms_path: str):
    """
    Validate UVW coordinates in MS file.
    """
    logger.info(f"Validating UVW coordinates in: {ms_path}")
    
    try:
        from casatools import table
        
        # Open MS file
        table_tool = table()
        table_tool.open(ms_path)
        
        # Get basic information
        nrows = table_tool.nrows()
        logger.info(f"MS table has {nrows} rows")
        
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
        std_baseline = np.std(baseline_lengths)
        
        logger.info(f"UVW coordinate statistics:")
        logger.info(f"  Mean baseline length: {mean_baseline:.3f} meters")
        logger.info(f"  Max baseline length: {max_baseline:.3f} meters")
        logger.info(f"  Min baseline length: {min_baseline:.3f} meters")
        logger.info(f"  Std baseline length: {std_baseline:.3f} meters")
        
        # Check UVW coordinate ranges
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
        
        # Check for data quality issues
        has_nan = np.any(np.isnan(uvw_data))
        has_inf = np.any(np.isinf(uvw_data))
        
        logger.info(f"UVW data quality:")
        logger.info(f"  Has NaN values: {has_nan}")
        logger.info(f"  Has infinite values: {has_inf}")
        
        # Validate against DSA-110 characteristics
        validation_results = {
            'mean_baseline': mean_baseline,
            'max_baseline': max_baseline,
            'min_baseline': min_baseline,
            'has_nan': has_nan,
            'has_inf': has_inf,
            'uvw_ranges': {
                'u': u_range,
                'v': v_range,
                'w': w_range
            }
        }
        
        # DSA-110 validation criteria
        dsa110_criteria = {
            'max_baseline_reasonable': max_baseline > 1000,  # More than 1 km
            'mean_baseline_reasonable': mean_baseline > 100,  # Mean > 100m
            'no_nan_values': not has_nan,
            'no_inf_values': not has_inf,
            'uvw_range_reasonable': (
                abs(u_range[0]) < 2000 and abs(u_range[1]) < 2000 and
                abs(v_range[0]) < 2000 and abs(v_range[1]) < 2000 and
                abs(w_range[0]) < 2000 and abs(w_range[1]) < 2000
            )
        }
        
        logger.info(f"DSA-110 validation criteria:")
        for criterion, passed in dsa110_criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {criterion}: {status}")
        
        # Overall validation
        all_criteria_passed = all(dsa110_criteria.values())
        validation_results['all_criteria_passed'] = all_criteria_passed
        validation_results['criteria'] = dsa110_criteria
        
        if all_criteria_passed:
            logger.info("✅ UVW coordinates validation PASSED - all criteria met!")
        else:
            logger.warning("⚠️ UVW coordinates validation FAILED - some criteria not met")
        
        logger.info(f"Validation result: {'PASS' if all_criteria_passed else 'FAIL'}")
        
        table_tool.close()
        return validation_results
        
    except Exception as e:
        logger.error(f"Failed to validate UVW coordinates: {e}")
        return None


def main():
    """
    Main validation function.
    """
    logger.info("Starting UVW coordinate validation")
    
    # Test with existing MS files
    ms_files = [
        'ms_stage1/2025-09-05T03:23:14.ms',
        'ms_stage1/2025-09-05T03:23:14_calibrated.ms'
    ]
    
    results = {}
    
    for ms_path in ms_files:
        if os.path.exists(ms_path):
            logger.info(f"\n{'='*60}")
            logger.info(f"Validating: {ms_path}")
            logger.info(f"{'='*60}")
            
            result = validate_uvw_coordinates(ms_path)
            if result:
                results[ms_path] = result
            else:
                logger.error(f"Failed to validate {ms_path}")
        else:
            logger.warning(f"MS file not found: {ms_path}")
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("VALIDATION SUMMARY")
    logger.info(f"{'='*60}")
    
    for ms_path, result in results.items():
        status = "✅ PASS" if result['all_criteria_passed'] else "❌ FAIL"
        logger.info(f"{os.path.basename(ms_path)}: {status}")
        logger.info(f"  Mean baseline: {result['mean_baseline']:.3f}m")
        logger.info(f"  Max baseline: {result['max_baseline']:.3f}m")
    
    # Overall result
    all_passed = all(result['all_criteria_passed'] for result in results.values())
    if all_passed:
        logger.info("\n🎉 ALL UVW VALIDATIONS PASSED!")
    else:
        logger.warning("\n⚠️ SOME UVW VALIDATIONS FAILED!")


if __name__ == "__main__":
    main()
