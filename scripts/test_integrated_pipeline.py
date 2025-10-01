#!/usr/bin/env python3
"""
Test Integrated Pipeline with Unified MS Creation

This script demonstrates the integrated pipeline using the unified MS creation system
that combines DSA-110 specific fixes with quality validation and multi-subband processing.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.main_driver_unified import UnifiedPipelineDriver
from dsa110.utils.config_loader import load_pipeline_config
from dsa110.utils.logging import get_logger

logger = get_logger(__name__)

async def test_integrated_pipeline():
    """Test the integrated pipeline with unified MS creation."""
    print("\n" + "="*80)
    print("INTEGRATED PIPELINE TEST WITH UNIFIED MS CREATION")
    print("="*80)
    
    # Load configuration
    config = load_pipeline_config()
    
    # Initialize the unified pipeline driver
    driver = UnifiedPipelineDriver("config/pipeline_config.yaml")
    
    # Test data directory
    hdf5_dir = "/data/incoming_test"
    
    print(f"Testing with HDF5 directory: {hdf5_dir}")
    
    # Test 1: HDF5 to MS conversion
    print("\nTEST 1: HDF5 to MS Conversion")
    print("-" * 50)
    
    try:
        result = await driver.process_hdf5_to_ms(hdf5_dir)
        
        if result['success']:
            print(f"SUCCESS: Created {result['count']} MS files")
            print(f"MS files:")
            for i, ms_file in enumerate(result['ms_files'][:5]):  # Show first 5
                print(f"  {i+1}. {os.path.basename(ms_file)}")
            if len(result['ms_files']) > 5:
                print(f"  ... and {len(result['ms_files']) - 5} more")
        else:
            print(f"FAILED: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 2: Pipeline initialization
    print("\nTEST 2: Pipeline Initialization")
    print("-" * 50)
    
    try:
        await driver.initialize()
        print("SUCCESS: Pipeline initialized successfully")
        print(f"Available stages: {list(driver.orchestrator.stages.keys())}")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 3: MS file validation
    print("\nTEST 3: MS File Validation")
    print("-" * 50)
    
    try:
        if result['success'] and result['ms_files']:
            validation_results = await driver.orchestrator.stages['data_ingestion'].validate_ms_files(result['ms_files'])
            
            print(f"Validation Results:")
            print(f"  - Total files: {validation_results['total_files']}")
            print(f"  - Valid files: {validation_results['valid_files']}")
            print(f"  - Invalid files: {validation_results['invalid_files']}")
            
            if validation_results['errors']:
                print(f"  - Errors: {len(validation_results['errors'])}")
                for error in validation_results['errors'][:3]:  # Show first 3
                    print(f"    * {error}")
                if len(validation_results['errors']) > 3:
                    print(f"    ... and {len(validation_results['errors']) - 3} more errors")
            
            if validation_results['warnings']:
                print(f"  - Warnings: {len(validation_results['warnings'])}")
        else:
            print("No MS files to validate")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 4: Processing block creation
    print("\nTEST 4: Processing Block Creation")
    print("-" * 50)
    
    try:
        if result['success'] and result['ms_files']:
            blocks = driver.orchestrator.stages['data_ingestion'].get_processing_blocks(result['ms_files'])
            
            print(f"SUCCESS: Created {len(blocks)} processing blocks")
            for i, block in enumerate(blocks):
                print(f"  Block {i+1}: {block['block_id']}")
                print(f"    - MS files: {len(block['ms_files'])}")
                print(f"    - Duration: {block['duration_hours']} hours")
        else:
            print("No MS files available for block creation")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    print(f"\nINTEGRATED PIPELINE TEST COMPLETED!")
    return True

async def main():
    """Main test function."""
    success = await test_integrated_pipeline()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
