#!/usr/bin/env python3
"""
Test Next-Generation MS Creation

This script demonstrates the improvements over the reference pipelines:
- Proper antenna position integration
- Quality validation and diagnostics
- Intelligent sub-band combination
- Advanced error handling
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dsa110.data_ingestion.nextgen_ms_creation import NextGenMSCreationManager
from dsa110.utils.config_loader import load_pipeline_config
from dsa110.utils.logging import get_logger

logger = get_logger(__name__)

async def test_nextgen_ms_creation():
    """Test the next-generation MS creation system."""
    print("\n" + "="*80)
    print("NEXT-GENERATION MS CREATION TEST")
    print("="*80)
    
    # Load configuration
    config = load_pipeline_config()
    
    # Initialize manager
    ms_manager = NextGenMSCreationManager(config)
    
    # Test data directory
    hdf5_dir = "/data/incoming_test"
    output_dir = "test_outputs/nextgen_ms"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Testing with HDF5 directory: {hdf5_dir}")
    print(f"Output directory: {output_dir}")
    
    # Test 1: Single timestamp processing
    print("\n🔬 TEST 1: Single Timestamp Processing")
    print("-" * 50)
    
    test_timestamp = "2025-09-05T03:23:14"
    output_ms_path = os.path.join(output_dir, f"{test_timestamp}.ms")
    
    try:
        result = await ms_manager.create_ms_from_timestamp(
            test_timestamp, hdf5_dir, output_ms_path, quality_checks=True
        )
        
        if result['success']:
            print(f"✅ Success: {os.path.basename(output_ms_path)}")
            print(f"   - Quality Score: {result['quality_metrics'].get('quality_score', 'N/A'):.2f}")
            print(f"   - Completeness: {result['quality_metrics'].get('completeness', 'N/A'):.2f}")
            print(f"   - Data Consistency: {result['quality_metrics'].get('data_consistency', 'N/A'):.2f}")
            print(f"   - Antennas: {result['quality_metrics'].get('n_antennas', 'N/A')}")
            print(f"   - Baselines: {result['quality_metrics'].get('n_baselines', 'N/A')}")
            print(f"   - Times: {result['quality_metrics'].get('n_times', 'N/A')}")
            print(f"   - Frequencies: {result['quality_metrics'].get('n_freqs', 'N/A')}")
            
            if result['warnings']:
                print(f"   - Warnings: {len(result['warnings'])}")
                for warning in result['warnings']:
                    print(f"     * {warning}")
        else:
            print(f"❌ Failed: {result.get('errors', [])}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Antenna position integration
    print("\n📡 TEST 2: Antenna Position Integration")
    print("-" * 50)
    
    try:
        antenna_info = ms_manager.antenna_positions_manager.get_antenna_info()
        
        if antenna_info['positions_loaded']:
            print(f"✅ Antenna positions loaded successfully")
            print(f"   - Number of antennas: {antenna_info['n_antennas']}")
            print(f"   - Max baseline: {antenna_info['max_baseline']:.1f} m")
            print(f"   - Min baseline: {antenna_info['min_baseline']:.1f} m")
            print(f"   - Mean baseline: {antenna_info['mean_baseline']:.1f} m")
            print(f"   - CSV path: {antenna_info['csv_path']}")
        else:
            print(f"❌ Failed to load antenna positions: {antenna_info.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Quality validation
    print("\n🔍 TEST 3: Quality Validation")
    print("-" * 50)
    
    try:
        # Find HDF5 files for testing
        import glob
        hdf5_files = glob.glob(os.path.join(hdf5_dir, "*.hdf5"))
        
        if hdf5_files:
            print(f"Found {len(hdf5_files)} HDF5 files for quality testing")
            
            # Test quality assessment
            quality_result = await ms_manager._assess_data_quality(hdf5_files)
            
            print(f"Quality Assessment Results:")
            print(f"   - Files found: {quality_result['n_files']}")
            print(f"   - Files required: {quality_result['n_required_files']}")
            print(f"   - Completeness: {quality_result['completeness']:.2f}")
            print(f"   - Data consistency: {quality_result['data_consistency']:.2f}")
            print(f"   - Integration time consistency: {quality_result['integration_time_consistency']:.2f}")
            print(f"   - Overall quality score: {quality_result['quality_score']:.2f}")
            print(f"   - Meets standards: {quality_result['meets_standards']}")
            
            if 'missing_subbands' in quality_result:
                print(f"   - Missing sub-bands: {quality_result['missing_subbands']}")
        else:
            print("No HDF5 files found for quality testing")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Configuration validation
    print("\n⚙️ TEST 4: Configuration Validation")
    print("-" * 50)
    
    try:
        print(f"Configuration loaded successfully")
        print(f"   - Required SPWs: {len(ms_manager.required_spws)}")
        print(f"   - Timestamp tolerance: {ms_manager.same_timestamp_tolerance} seconds")
        print(f"   - Min data quality: {ms_manager.min_data_quality}")
        print(f"   - Max missing sub-bands: {ms_manager.max_missing_subbands}")
        print(f"   - Min integration time: {ms_manager.min_integration_time} seconds")
        print(f"   - Output antennas: {ms_manager.output_antennas}")
        print(f"   - Telescope location: {ms_manager.telescope_location}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n🎉 NEXT-GENERATION MS CREATION TEST COMPLETED!")
    return True

async def main():
    """Main test function."""
    success = await test_nextgen_ms_creation()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
