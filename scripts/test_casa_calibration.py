#!/usr/bin/env python3
"""
Test CASA calibration with the MS file to validate UVW coordinates.

This script tests basic CASA calibration operations to ensure
the MS file with correct UVW coordinates works properly.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.utils.logging import get_logger

logger = get_logger(__name__)


def test_casa_calibration(ms_path: str):
    """
    Test basic CASA calibration operations on the MS file.
    """
    logger.info(f"Testing CASA calibration with MS file: {ms_path}")
    
    try:
        from casatools import table, ms
        from casatasks import listobs, flagdata, gencal, bandpass, gaincal, applycal
        
        # Test 1: List observations
        logger.info("Test 1: Listing observations")
        try:
            listobs(vis=ms_path, listfile=f"{ms_path}.listobs", overwrite=True)
            logger.info("✅ Listobs successful")
        except Exception as e:
            logger.error(f"❌ Listobs failed: {e}")
            return False
        
        # Test 2: Basic flagging
        logger.info("Test 2: Basic flagging operations")
        try:
            flagdata(vis=ms_path, mode='tfcrop', datacolumn='data', action='calculate')
            logger.info("✅ Flagdata successful")
        except Exception as e:
            logger.error(f"❌ Flagdata failed: {e}")
            return False
        
        # Test 3: Check MS structure
        logger.info("Test 3: Checking MS structure")
        try:
            ms_tool = ms()
            ms_tool.open(ms_path)
            
            # Get basic information
            nrows = ms_tool.nrows()
            nants = ms_tool.nantennas()
            nspw = ms_tool.nspectralwindows()
            
            logger.info(f"MS structure: {nrows} rows, {nants} antennas, {nspw} spectral windows")
            
            # Check UVW coordinates
            table_tool = table()
            table_tool.open(ms_path)
            uvw_data = table_tool.getcol('UVW')
            
            if uvw_data.shape[0] == 3:
                baseline_lengths = np.sqrt(uvw_data[0]**2 + uvw_data[1]**2 + uvw_data[2]**2)
            else:
                baseline_lengths = np.sqrt(uvw_data[:, 0]**2 + uvw_data[:, 1]**2 + uvw_data[:, 2]**2)
            
            mean_baseline = np.mean(baseline_lengths)
            max_baseline = np.max(baseline_lengths)
            
            logger.info(f"UVW coordinates: mean={mean_baseline:.3f}m, max={max_baseline:.3f}m")
            
            if max_baseline > 1000:  # More than 1 km
                logger.info("✅ UVW coordinates appear correct for DSA-110")
            else:
                logger.warning("⚠️ UVW coordinates may be incorrect")
            
            table_tool.close()
            ms_tool.close()
            
        except Exception as e:
            logger.error(f"❌ MS structure check failed: {e}")
            return False
        
        # Test 4: Basic calibration setup
        logger.info("Test 4: Basic calibration setup")
        try:
            # Try to generate a basic calibration table
            gencal(vis=ms_path, caltable=f"{ms_path}.G0", caltype='G', parameter=[0.0])
            logger.info("✅ Basic calibration setup successful")
            
            # Clean up
            if os.path.exists(f"{ms_path}.G0"):
                os.system(f"rm -rf {ms_path}.G0")
                
        except Exception as e:
            logger.error(f"❌ Basic calibration setup failed: {e}")
            return False
        
        logger.info("✅ All CASA calibration tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ CASA calibration test failed: {e}")
        return False


def main():
    """
    Main test function.
    """
    logger.info("Starting CASA calibration validation tests")
    
    # Test with the existing MS file
    ms_path = 'ms_stage1/2025-09-05T03:23:14.ms'
    
    if not os.path.exists(ms_path):
        logger.error(f"MS file not found: {ms_path}")
        return
    
    success = test_casa_calibration(ms_path)
    
    if success:
        logger.info("✅ CASA calibration validation successful!")
    else:
        logger.error("❌ CASA calibration validation failed!")


if __name__ == "__main__":
    import numpy as np
    main()
