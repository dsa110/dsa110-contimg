#!/usr/bin/env python3
"""
Test Unified MS Creation

This script demonstrates the unified approach that combines:
- Single-file processing with DSA-110 specific fixes (from dsa110_hdf5_reader_fixed.py)
- Multi-subband combination with quality validation (from nextgen_ms_creation.py)
- Proper antenna position integration
- Advanced error handling and recovery
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_ingestion.unified_ms_creation import UnifiedMSCreationManager
from core.utils.config_loader import load_pipeline_config
from core.utils.logging import get_logger

logger = get_logger(__name__)

async def test_unified_ms_creation():
    """Test the unified MS creation system."""
    print("\n" + "="*80)
    print("UNIFIED MS CREATION TEST")
    print("="*80)
    
    # Load configuration
    config = load_pipeline_config()
    
    # Initialize manager
    ms_manager = UnifiedMSCreationManager(config)
    
    # Test data directory
    hdf5_dir = "/data/incoming_test"
    output_dir = "test_outputs/unified_ms"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Testing with HDF5 directory: {hdf5_dir}")
    print(f"Output directory: {output_dir}")
    
    # Test 1: Single file processing
    print("\nTEST 1: Single File Processing (with DSA-110 fixes)")
    print("-" * 60)
    
    test_file = "/data/incoming_test/2025-09-05T03:23:14_sb00.hdf5"
    output_ms_path = os.path.join(output_dir, "single_file_test.ms")
    
    try:
        result = await ms_manager.create_ms_from_single_file(
            test_file, output_ms_path, quality_checks=True
        )
        
        if result['success']:
            print(f"SUCCESS: {os.path.basename(output_ms_path)}")
            print(f"   - Quality Score: {result['quality_metrics'].get('quality_score', 'N/A'):.2f}")
            print(f"   - Antennas: {result['quality_metrics'].get('n_antennas', 'N/A')}")
            print(f"   - Baselines: {result['quality_metrics'].get('n_baselines', 'N/A')}")
            print(f"   - Times: {result['quality_metrics'].get('n_times', 'N/A')}")
            print(f"   - Frequencies: {result['quality_metrics'].get('n_freqs', 'N/A')}")
            print(f"   - Integration Time: {result['quality_metrics'].get('integration_time_s', 'N/A'):.1f}s")
            print(f"   - Frequency Range: {result['quality_metrics'].get('frequency_range_ghz', 'N/A')}")
            
            if result['warnings']:
                print(f"   - Warnings: {len(result['warnings'])}")
                for warning in result['warnings']:
                    print(f"     * {warning}")
        else:
            print(f"FAILED: {result.get('errors', [])}")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 2: Multiple file processing
    print("\nTEST 2: Multiple File Processing (sub-band combination)")
    print("-" * 60)
    
    # Find all HDF5 files for the test timestamp
    import glob
    test_timestamp = "2025-09-05T03:23:14"
    hdf5_files = glob.glob(os.path.join(hdf5_dir, f"{test_timestamp}_sb*.hdf5"))
    hdf5_files.sort()
    
    if hdf5_files:
        output_ms_path = os.path.join(output_dir, "multi_file_test.ms")
        
        try:
            result = await ms_manager.create_ms_from_multiple_files(
                hdf5_files, output_ms_path, quality_checks=True
            )
            
            if result['success']:
                print(f"SUCCESS: {os.path.basename(output_ms_path)}")
                print(f"   - Files processed: {len(hdf5_files)}")
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
                print(f"FAILED: {result.get('errors', [])}")
                
        except Exception as e:
            print(f"ERROR: {e}")
    else:
        print("No HDF5 files found for multi-file testing")
    
    # Test 3: DSA-110 specific fixes
    print("\nTEST 3: DSA-110 Specific Fixes")
    print("-" * 60)
    
    try:
        # Test the fixes on a single file
        uv_data = await ms_manager._read_and_fix_hdf5_file(test_file)
        
        if uv_data is not None:
            print("SUCCESS: DSA-110 fixes applied successfully:")
            print(f"   - Telescope name: {uv_data.telescope.name}")
            print(f"   - Visibility units: {uv_data.vis_units}")
            print(f"   - UVW array type: {uv_data.uvw_array.dtype}")
            print(f"   - Mount type: {uv_data.telescope.mount_type[:3]}...")  # Show first 3
            print(f"   - Number of antennas: {getattr(uv_data, 'Nants_data', 'N/A')}")
            print(f"   - Number of baselines: {getattr(uv_data, 'Nbls', 'N/A')}")
        else:
            print("FAILED: Failed to apply DSA-110 fixes")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 4: Quality validation
    print("\nTEST 4: Quality Validation")
    print("-" * 60)
    
    try:
        if hdf5_files:
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
        print(f"ERROR: {e}")
    
    # Test 5: Antenna position integration
    print("\nTEST 5: Antenna Position Integration")
    print("-" * 60)
    
    try:
        antenna_info = ms_manager.antenna_positions_manager.get_antenna_info()
        
        if antenna_info['positions_loaded']:
            print(f"SUCCESS: Antenna positions loaded successfully")
            print(f"   - Number of antennas: {antenna_info['n_antennas']}")
            print(f"   - Max baseline: {antenna_info['max_baseline']:.1f} m")
            print(f"   - Min baseline: {antenna_info['min_baseline']:.1f} m")
            print(f"   - Mean baseline: {antenna_info['mean_baseline']:.1f} m")
            print(f"   - CSV path: {antenna_info['csv_path']}")
        else:
            print(f"FAILED: Failed to load antenna positions: {antenna_info.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    print(f"\nUNIFIED MS CREATION TEST COMPLETED!")
    return True

async def main():
    """Main test function."""
    success = await test_unified_ms_creation()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
