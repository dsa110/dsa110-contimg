#!/usr/bin/env python3
"""
Debug script to isolate the MS conversion issue.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.data_ingestion.dsa110_hdf5_reader import DSA110HDF5Reader

def debug_ms_conversion():
    """Debug the MS conversion process step by step."""
    print("=== Debugging MS Conversion ===")
    
    # Test file
    test_file = "/data/incoming_test/2025-09-05T03:23:14_sb00.hdf5"
    
    # Create reader
    reader = DSA110HDF5Reader()
    
    # Read HDF5 file
    print("1. Reading HDF5 file...")
    uv_data = reader.create_uvdata_object(test_file)
    
    if uv_data is None:
        print("❌ Failed to create UVData object")
        return
    
    print("✅ UVData object created successfully")
    print(f"   - Data shape: {uv_data.data_array.shape}")
    print(f"   - Telescope: {uv_data.telescope_name}")
    print(f"   - Extra keywords: {uv_data.extra_keywords}")
    print(f"   - Extra keywords type: {type(uv_data.extra_keywords)}")
    
    # Try to write MS
    print("\n2. Attempting MS conversion...")
    output_ms = "test_outputs/debug_test.ms"
    os.makedirs("test_outputs", exist_ok=True)
    
    try:
        # Remove existing MS if it exists
        if os.path.exists(output_ms):
            import shutil
            shutil.rmtree(output_ms)
        
        # Write MS
        uv_data.write_ms(output_ms, clobber=True)
        print("✅ MS conversion successful!")
        print(f"   - Output: {output_ms}")
        
    except Exception as e:
        print(f"❌ MS conversion failed: {e}")
        print(f"   - Error type: {type(e)}")
        
        # Try to get more details about the error
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ms_conversion()
