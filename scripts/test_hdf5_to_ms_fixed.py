#!/usr/bin/env python3
"""
Test HDF5 to MS conversion with real DSA-110 data using the simplified reader.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_ingestion.dsa110_hdf5_reader_fixed import DSA110HDF5Reader

async def test_ms_creation(file_path, output_ms_path):
    """Test MS creation from HDF5 file using the simplified reader."""
    print(f"\n=== Testing MS Creation ===")
    print(f"Input: {os.path.basename(file_path)}")
    print(f"Output: {os.path.basename(output_ms_path)}")
    
    try:
        # Create reader
        reader = DSA110HDF5Reader()
        
        # Read HDF5 file
        print("Reading HDF5 file...")
        uv_data = await reader.create_uvdata_object(file_path)
        if uv_data is None:
            print("Failed to create UVData object")
            return False
        
        print(f"UVData object created successfully:")
        print(f"  Nbls: {uv_data.Nbls}")
        print(f"  Nfreqs: {uv_data.Nfreqs}")
        print(f"  Ntimes: {uv_data.Ntimes}")
        print(f"  Npols: {uv_data.Npols}")
        
        # Write to MS
        print("Writing to MS format...")
        success = reader.write_ms(uv_data, output_ms_path)
        
        if success:
            print(f"Successfully created MS: {output_ms_path}")
            
            # Check if MS file was created
            if os.path.exists(output_ms_path):
                print(f"MS file size: {os.path.getsize(output_ms_path)} bytes")
                return True
            else:
                print("MS file not found after creation")
                return False
        else:
            print("Failed to create MS file")
            return False
            
    except Exception as e:
        print(f"MS creation failed: {e}")
        return False

async def main():
    """Main test function."""
    test_dir = Path("/data/incoming_test/")
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)
    
    if not test_dir.exists():
        print(f"Test directory not found: {test_dir}")
        return
    
    hdf5_files = list(test_dir.glob("*.hdf5"))
    
    if not hdf5_files:
        print("No HDF5 files found in test directory")
        return
    
    print(f"Found {len(hdf5_files)} HDF5 files")
    print("=" * 50)
    
    # Test with first file
    test_file = hdf5_files[0]
    output_ms = output_dir / f"test_{test_file.stem}.ms"
    
    success = await test_ms_creation(test_file, str(output_ms))
    
    if success:
        print("\n✅ HDF5 to MS conversion test PASSED!")
    else:
        print("\n❌ HDF5 to MS conversion test FAILED!")

if __name__ == "__main__":
    asyncio.run(main())
