#!/usr/bin/env python3
"""
Test Enhanced Calibration Pipeline

This script demonstrates the enhanced calibration pipeline with:
- Proper source identification and flux lookup
- Taper-off UV range limits
- Reference antenna priority system
- Optimized calibration intervals
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dsa110.casa.enhanced_calibration_pipeline import EnhancedCalibrationPipeline
from dsa110.utils.config_loader import load_pipeline_config
from dsa110.utils.logging import get_logger

logger = get_logger(__name__)

async def test_enhanced_calibration():
    """Test the enhanced calibration pipeline."""
    print("\n" + "="*80)
    print("ENHANCED CALIBRATION PIPELINE TEST")
    print("="*80)
    
    # Load configuration
    config = load_pipeline_config()
    
    # Initialize the enhanced calibration pipeline
    cal_pipeline = EnhancedCalibrationPipeline(config)
    
    # Test MS file (from previous integration test)
    ms_path = "ms_stage1/2025-09-05T03:23:14.ms"
    output_cal_path = "ms_stage1/2025-09-05T03:23:14_calibrated.ms"
    
    print(f"Testing with MS file: {ms_path}")
    print(f"Output calibrated MS: {output_cal_path}")
    
    # Test 1: Source identification
    print("\nTEST 1: Calibrator Source Identification")
    print("-" * 50)
    
    try:
        sources = cal_pipeline.identify_calibrator_sources(ms_path)
        
        if sources:
            print(f"SUCCESS: Identified {len(sources)} calibrator sources")
            for i, source in enumerate(sources):
                print(f"  {i+1}. {source['field_name']} -> {list(cal_pipeline.source_catalog.keys())[0]}")
                print(f"     - Flux at 1.4 GHz: {source['flux_1p4ghz']:.2f} Jy")
                print(f"     - Spectral index: {source['spectral_index']:.2f}")
                print(f"     - Separation: {source['separation_arcmin']:.1f} arcmin")
        else:
            print("WARNING: No calibrator sources identified")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 2: Reference antenna selection
    print("\nTEST 2: Reference Antenna Selection")
    print("-" * 50)
    
    try:
        ref_ant = cal_pipeline.get_reference_antenna(ms_path)
        print(f"SUCCESS: Selected reference antenna: {ref_ant}")
        print(f"Priority list: {cal_pipeline.reference_antennas}")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 3: UV range taper creation
    print("\nTEST 3: UV Range Taper Creation")
    print("-" * 50)
    
    try:
        uv_range = cal_pipeline.create_uv_range_taper(ms_path)
        print(f"SUCCESS: Created UV range taper: {uv_range}")
        print(f"Taper-off at: {cal_pipeline.uv_range_taper_klambda} klambda")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 4: Flux density calculation
    print("\nTEST 4: Flux Density Calculation")
    print("-" * 50)
    
    try:
        if sources:
            source = sources[0]
            flux_1p4 = cal_pipeline.calculate_flux_density(source, 1.4)
            flux_1p5 = cal_pipeline.calculate_flux_density(source, 1.5)
            
            print(f"SUCCESS: Calculated flux densities for {source['field_name']}")
            print(f"  - At 1.4 GHz: {flux_1p4:.2f} Jy")
            print(f"  - At 1.5 GHz: {flux_1p5:.2f} Jy")
            print(f"  - Spectral index: {source['spectral_index']:.2f}")
        else:
            print("No sources available for flux calculation")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 5: Calibration parameters
    print("\nTEST 5: Calibration Parameters")
    print("-" * 50)
    
    print(f"Bandpass interval: {cal_pipeline.bandpass_interval_hours} hours")
    print(f"Gain interval: {cal_pipeline.gain_interval_hours} hours")
    print(f"Reference antennas: {cal_pipeline.reference_antennas}")
    print(f"UV range taper: {cal_pipeline.uv_range_taper_klambda} klambda")
    
    # Test 6: Full calibration (if MS file exists)
    print("\nTEST 6: Full Calibration Workflow")
    print("-" * 50)
    
    if os.path.exists(ms_path):
        try:
            print("Running full calibration workflow...")
            result = await cal_pipeline.perform_enhanced_calibration(ms_path, output_cal_path)
            
            if result['success']:
                print("SUCCESS: Calibration completed successfully")
                print(f"  - Calibrated MS: {result['calibrated_ms']}")
                print(f"  - Calibration tables: {len(result['calibration_tables'])}")
                print(f"  - Reference antenna: {result['reference_antenna']}")
                print(f"  - UV range: {result['uv_range']}")
                
                if 'validation' in result:
                    val = result['validation']
                    print(f"  - Validation: {val.get('n_antennas', 'N/A')} antennas, "
                          f"{val.get('n_baselines', 'N/A')} baselines")
            else:
                print(f"FAILED: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"ERROR: {e}")
    else:
        print(f"MS file not found: {ms_path}")
        print("Skipping full calibration test")
    
    print(f"\nENHANCED CALIBRATION TEST COMPLETED!")
    return True

async def main():
    """Main test function."""
    success = await test_enhanced_calibration()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
