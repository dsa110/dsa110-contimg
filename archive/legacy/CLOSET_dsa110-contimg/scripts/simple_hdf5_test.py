#!/usr/bin/env python3
"""
Simple test for HDF5 to MS conversion using the original pipeline code.
"""

import os
import sys
from pathlib import Path

# Add the original pipeline directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "archive" / "legacy_pipeline"))

def test_with_original_code():
    """Test using the original pipeline code."""
    print("Testing HDF5 to MS conversion with original pipeline code...")
    
    try:
        # Import the original MS creation module
        from ms_creation import process_hdf5_set
        
        # Test data
        test_dir = Path("/data/incoming_test/")
        hdf5_files = list(test_dir.glob("*.hdf5"))
        
        if not hdf5_files:
            print("No HDF5 files found")
            return False
        
        # Group files by timestamp
        timestamp_groups = {}
        for file in hdf5_files:
            timestamp = file.name.split('_')[0]
            if timestamp not in timestamp_groups:
                timestamp_groups[timestamp] = []
            timestamp_groups[timestamp].append(file)
        
        # Test with first timestamp group
        first_timestamp = list(timestamp_groups.keys())[0]
        files = sorted(timestamp_groups[first_timestamp])
        
        print(f"Testing with timestamp {first_timestamp}")
        print(f"Found {len(files)} files for this timestamp")
        
        # Create a simple config
        config = {
            'paths': {
                'pipeline_base_dir': '/data/jfaber/dsa110-contimg/pipeline/',
                'ms_stage1_dir': 'ms_stage1/'
            },
            'ms_creation': {
                'spws': ['sb00','sb01','sb02','sb03','sb04','sb05','sb06','sb07','sb08','sb09','sb10','sb11','sb12','sb13','sb14','sb15']
            }
        }
        
        # Test with first few files
        test_files = files[:3]  # Test with first 3 files
        print(f"Testing with {len(test_files)} files:")
        for f in test_files:
            print(f"  {f.name}")
        
        # Process the files
        ms_path = process_hdf5_set(config, first_timestamp, [str(f) for f in test_files])
        
        if ms_path:
            print(f"✅ Successfully created MS: {ms_path}")
            return True
        else:
            print("❌ MS creation failed")
            return False
            
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Main test function."""
    print("DSA-110 HDF5 to MS Conversion Test")
    print("=" * 40)
    
    success = test_with_original_code()
    
    if success:
        print("\n🎉 Test PASSED!")
    else:
        print("\n💥 Test FAILED!")

if __name__ == "__main__":
    main()
