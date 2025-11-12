#!/usr/bin/env python
"""
Test script to use makems_rk pipeline on the 16 test sub-bands.
This is a minimal adapter to the existing makems_rk toolchain.
"""

import sys
import os

# Add our patched makems directory first, then the original for other modules
sys.path.insert(0, '/data/dsa110-contimg/sandbox/makems')
sys.path.insert(1, '/data/dsa110-contimg/dsacamera/makems/hdf52ms/makems_rk/makems')

# Import the patched utils_hdf5 first to override the original
import utils_hdf5_patched as utils_hdf5
sys.modules['utils_hdf5'] = utils_hdf5

from pipeline_msmaker import convert_to_ms

def test_conversion():
    """Test the makems_rk pipeline on the 16 test sub-bands."""
    
    # Input/output paths
    incoming_path = '/data/incoming_test'
    output_path = '/data/dsa110-contimg/data/ms_out_makems_rk'
    
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    print("="*70)
    print("Testing makems_rk pipeline")
    print("="*70)
    print(f"Input directory: {incoming_path}")
    print(f"Output directory: {output_path}")
    print()
    
    # Run the conversion
    # This will:
    # 1. Find all HDF5 files in incoming_path
    # 2. Group files by timestamp (within 30s tolerance)
    # 3. Combine all 16 sub-bands into a single MS per observation
    # 4. Write to output_path
    convert_to_ms(
        incoming_file_path=incoming_path,
        tmin='2025-09-05T00:00:00',  # Filter for our test observation
        tmax='2025-09-05T23:59:59',
        spw=['sb00','sb01','sb02','sb03','sb04','sb05','sb06','sb07',
             'sb08','sb09','sb10','sb11','sb12','sb13','sb14','sb15'],
        same_timestamp_tolerance=30.0,  # 30 second tolerance for grouping
        output_file_path=output_path,
        output_antennas=None,  # Use all antennas
        cal_do_search=False,  # Don't search for calibrators
        post_handle='none'  # Don't move/delete input files
    )
    
    print()
    print("="*70)
    print("Conversion complete!")
    print("="*70)
    
    # List the output files
    if os.path.exists(output_path):
        output_files = sorted([f for f in os.listdir(output_path) if f.endswith('.ms')])
        if output_files:
            print(f"\nGenerated {len(output_files)} MS file(s):")
            for ms_file in output_files:
                ms_path = os.path.join(output_path, ms_file)
                # Get size
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(ms_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if os.path.exists(fp):
                            total_size += os.path.getsize(fp)
                size_mb = total_size / (1024**2)
                print(f"  - {ms_file} ({size_mb:.1f} MB)")
        else:
            print("\nNo MS files generated - check logs above for errors.")
    
    return output_path

if __name__ == '__main__':
    try:
        output_path = test_conversion()
        print(f"\nNext step: Validate the MS with:")
        print(f"  conda run -n casa6 python -c \"from casatasks import listobs; listobs(vis='{output_path}/<ms_name>.ms')\"")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

