#!/usr/bin/env python3
"""
Test Improved Calibration Pipeline for DSA-110

This script tests the improved calibration pipeline with real DSA-110 data
to address the SNR issues and parameter problems.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dsa110.casa.improved_calibration import ImprovedCASACalibrationPipeline
from dsa110.data_ingestion.ms_creation import MSCreationManager
from dsa110.utils.config_loader import load_pipeline_config
from dsa110.utils.logging import get_logger

logger = get_logger(__name__)

async def test_improved_calibration():
    """Test the improved calibration pipeline."""
    print("\n" + "="*80)
    print("IMPROVED CASA CALIBRATION TEST")
    print("="*80)
    
    # Load configuration
    config = load_pipeline_config()
    
    # Initialize managers
    ms_manager = MSCreationManager(config)
    cal_pipeline = ImprovedCASACalibrationPipeline(config)
    
    # Test data
    test_file = "/data/incoming_test/2025-09-05T03:23:14_sb00.hdf5"
    output_ms = "test_outputs/improved_calibration/test_calibration.ms"
    
    # Create output directory
    os.makedirs(os.path.dirname(output_ms), exist_ok=True)
    
    print(f"Testing with: {os.path.basename(test_file)}")
    print(f"Output MS: {os.path.basename(output_ms)}")
    
    # Step 1: Convert HDF5 to MS
    print("\n📁 STEP 1: HDF5 to MS Conversion")
    print("-" * 40)
    
    try:
        success = await ms_manager.create_ms_from_hdf5(test_file, output_ms)
        if success and os.path.exists(output_ms):
            file_size = os.path.getsize(output_ms)
            print(f"✅ Success: {os.path.basename(output_ms)} ({file_size:,} bytes)")
        else:
            print(f"❌ Failed: HDF5 to MS conversion")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Step 2: Run improved calibration
    print("\n🔧 STEP 2: Improved Calibration Pipeline")
    print("-" * 40)
    
    try:
        cal_result = await cal_pipeline.run_robust_calibration(output_ms)
        
        if cal_result['success']:
            print(f"✅ Calibration Success!")
            print(f"   - Calibration tables: {len(cal_result['calibration_tables'])}")
            print(f"   - Tables created:")
            for table in cal_result['calibration_tables']:
                print(f"     * {os.path.basename(table)}")
            
            # Show quality metrics
            quality = cal_result.get('quality_metrics', {})
            print(f"   - Quality metrics:")
            for key, value in quality.items():
                print(f"     * {key}: {value}")
                
        else:
            print(f"❌ Calibration Failed!")
            print(f"   - Errors: {cal_result.get('errors', [])}")
            return False
            
    except Exception as e:
        print(f"❌ Error during calibration: {e}")
        return False
    
    print(f"\n🎉 IMPROVED CALIBRATION TEST COMPLETED SUCCESSFULLY!")
    return True

async def main():
    """Main test function."""
    success = await test_improved_calibration()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
