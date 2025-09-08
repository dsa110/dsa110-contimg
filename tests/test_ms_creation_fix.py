#!/usr/bin/env python3
"""
Quick test script to verify MS creation fixes work
"""

import sys
import os
import glob
from collections import defaultdict
from datetime import datetime

# Add pipeline path
pipeline_parent_dir = '/data/jfaber/dsa110-contimg/'
if pipeline_parent_dir not in sys.path:
    sys.path.insert(0, pipeline_parent_dir)

from pipeline import ms_creation, config_parser

def test_ms_creation():
    """Test the fixed MS creation on a single timestamp"""
    
    # Load config
    config_path = 'config/pipeline_config.yaml'
    config = config_parser.load_config(config_path)
    if not config:
        print("❌ Failed to load config")
        return False
    
    # Don't move/delete files during test
    config['services']['hdf5_post_handle'] = 'none'
    
    # Find a complete set of HDF5 files
    hdf5_dir = config['paths']['hdf5_incoming']
    print(f"🔍 Looking for HDF5 files in: {hdf5_dir}")
    
    # Find complete sets
    hdf5_sets = ms_creation.find_hdf5_sets(config)
    
    if not hdf5_sets:
        print("❌ No complete HDF5 sets found")
        return False
    
    # Take the first complete set
    timestamp, hdf5_files = list(hdf5_sets.items())[0]
    print(f"📁 Testing with timestamp: {timestamp}")
    print(f"📁 Files: {[os.path.basename(f) for f in hdf5_files]}")
    
    # Test the MS creation
    try:
        print("🚀 Starting MS creation test...")
        ms_path = ms_creation.process_hdf5_set(config, timestamp, hdf5_files)
        
        if ms_path and os.path.exists(ms_path):
            print(f"✅ SUCCESS: Created MS at {ms_path}")
            
            # Quick validation
            #from casatools import table
            #tb = table()
            #tb.open(ms_path)
            #nrows = tb.nrows()
            #tb.close()
            #print(f"📊 MS contains {nrows} visibility rows")
            return True
        else:
            print("❌ FAILED: MS creation returned None or file doesn't exist")
            return False
            
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing MS Creation Fixes...")
    success = test_ms_creation()
    if success:
        print("\n🎉 MS Creation test PASSED!")
    else:
        print("\n💥 MS Creation test FAILED!")
        sys.exit(1)