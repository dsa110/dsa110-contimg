#!/usr/bin/env python3
"""
Test script for UVW coordinate preservation during calibration.

This script tests the fixed calibration pipeline to ensure that
UVW coordinates are preserved during calibration operations.
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
from core.casa.uvw_preservation_calibration import UVWPreservationCalibrationPipeline

logger = get_logger(__name__)


def test_uvw_preservation_calibration():
    """
    Test UVW coordinate preservation during calibration.
    """
    logger.info("Testing UVW coordinate preservation during calibration")
    
    # Configuration
    config = {
        'calibration': {
            'rfi_flagging': {},
            'bandpass': {},
            'gain': {}
        },
        'paths': {
            'cal_tables_dir': 'cal_tables'
        }
    }
    
    # Initialize pipeline
    pipeline = UVWPreservationCalibrationPipeline(config)
    
    # Test with existing MS file
    ms_path = 'ms_stage1/2025-09-05T03:23:14.ms'
    
    if not os.path.exists(ms_path):
        logger.error(f"MS file not found: {ms_path}")
        return False
    
    # Find calibration tables
    cal_tables = []
    for cal_file in ['B0', 'G0', 'G1']:
        cal_path = f'ms_stage1/2025-09-05T03:23:14_calibrated.ms.{cal_file}'
        if os.path.exists(cal_path):
            cal_tables.append(cal_path)
    
    if not cal_tables:
        logger.error("No calibration tables found for testing")
        return False
    
    logger.info(f"Found {len(cal_tables)} calibration tables: {cal_tables}")
    
    # Test UVW preservation calibration
    import asyncio
    result = asyncio.run(pipeline.apply_calibration_with_uvw_preservation(ms_path, cal_tables))
    
    # Report results
    logger.info("=== UVW PRESERVATION CALIBRATION RESULTS ===")
    logger.info(f"Success: {result['success']}")
    logger.info(f"UVW preserved: {result['uvw_preserved']}")
    logger.info(f"UVW restored: {result['uvw_restored']}")
    
    if result['validation']:
        validation = result['validation']
        logger.info(f"Validation valid: {validation['valid']}")
        logger.info(f"UVW preserved: {validation['uvw_preserved']}")
        logger.info(f"Baseline reasonable: {validation['baseline_reasonable']}")
        logger.info(f"Max UVW difference: {validation['max_uvw_difference']:.6f}m")
        logger.info(f"Mean baseline: {validation['mean_baseline']:.3f}m")
        logger.info(f"Max baseline: {validation['max_baseline']:.3f}m")
    
    if result['errors']:
        logger.error("Errors:")
        for error in result['errors']:
            logger.error(f"  - {error}")
    
    return result['success']


def test_applycal_parameters():
    """
    Test different applycal parameters to verify the fix.
    """
    logger.info("Testing applycal parameters")
    
    try:
        from casatools import table
        from casatasks import applycal
        
        # Test MS file
        ms_path = 'ms_stage1/2025-09-05T03:23:14.ms'
        
        if not os.path.exists(ms_path):
            logger.error(f"MS file not found: {ms_path}")
            return False
        
        # Find calibration tables
        cal_tables = []
        for cal_file in ['B0', 'G0', 'G1']:
            cal_path = f'ms_stage1/2025-09-05T03:23:14_calibrated.ms.{cal_file}'
            if os.path.exists(cal_path):
                cal_tables.append(cal_path)
        
        if not cal_tables:
            logger.error("No calibration tables found for testing")
            return False
        
        # Test 1: Original problematic parameters (calflag)
        logger.info("Test 1: Testing problematic parameters (calflag)")
        try:
            # Backup original UVW
            table_tool = table()
            table_tool.open(ms_path)
            original_uvw = table_tool.getcol('UVW')
            table_tool.close()
            
            # Apply with problematic parameters
            applycal(
                vis=ms_path,
                gaintable=cal_tables,
                gainfield=[],
                interp=['nearest', 'linear'],
                calwt=False,
                flagbackup=False,
                applymode='calflag'  # This should modify UVW coordinates
            )
            
            # Check UVW coordinates
            table_tool = table()
            table_tool.open(ms_path)
            modified_uvw = table_tool.getcol('UVW')
            table_tool.close()
            
            uvw_diff = np.abs(original_uvw - modified_uvw)
            max_diff = np.max(uvw_diff)
            
            logger.info(f"  calflag mode - Max UVW difference: {max_diff:.6f}m")
            
            # Restore original UVW
            table_tool = table()
            table_tool.open(ms_path, nomodify=False)
            table_tool.putcol('UVW', original_uvw)
            table_tool.close()
            
        except Exception as e:
            logger.error(f"  calflag test failed: {e}")
        
        # Test 2: Fixed parameters (calonly)
        logger.info("Test 2: Testing fixed parameters (calonly)")
        try:
            # Apply with fixed parameters
            applycal(
                vis=ms_path,
                gaintable=cal_tables,
                gainfield=[],
                interp=['nearest', 'linear'],
                calwt=False,
                flagbackup=False,
                applymode='calonly'  # This should preserve UVW coordinates
            )
            
            # Check UVW coordinates
            table_tool = table()
            table_tool.open(ms_path)
            preserved_uvw = table_tool.getcol('UVW')
            table_tool.close()
            
            uvw_diff = np.abs(original_uvw - preserved_uvw)
            max_diff = np.max(uvw_diff)
            
            logger.info(f"  calonly mode - Max UVW difference: {max_diff:.6f}m")
            
            if max_diff < 1e-10:
                logger.info("  ✅ calonly mode preserves UVW coordinates")
            else:
                logger.warning("  ⚠️ calonly mode still modifies UVW coordinates")
            
        except Exception as e:
            logger.error(f"  calonly test failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Parameter testing failed: {e}")
        return False


def main():
    """
    Main test function.
    """
    logger.info("Starting UVW calibration fix tests")
    
    try:
        # Test 1: Applycal parameters
        logger.info("=== TEST 1: APPLYCAL PARAMETERS ===")
        success1 = test_applycal_parameters()
        
        # Test 2: UVW preservation pipeline
        logger.info("\n=== TEST 2: UVW PRESERVATION PIPELINE ===")
        success2 = test_uvw_preservation_calibration()
        
        # Summary
        logger.info("\n=== TEST SUMMARY ===")
        logger.info(f"Applycal parameters test: {'PASS' if success1 else 'FAIL'}")
        logger.info(f"UVW preservation pipeline test: {'PASS' if success2 else 'FAIL'}")
        
        if success1 and success2:
            logger.info("🎉 All tests passed! UVW coordinate preservation is working.")
        else:
            logger.warning("⚠️ Some tests failed. Check the logs for details.")
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
