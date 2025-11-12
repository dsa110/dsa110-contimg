#!/usr/bin/env python3
"""
Test to isolate where the UVW warning is coming from
"""

import asyncio
import sys
import os
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from pyuvdata import UVData

async def test_uvw_warning_source():
    print('🔍 Isolating UVW Warning Source')
    print('=' * 35)
    
    # Test with single HDF5 file first
    hdf5_file = '/data/incoming_test/2025-09-05T03:23:14_sb00.hdf5'
    print(f'Testing with single file: {hdf5_file}')
    
    # Step 1: Read HDF5 file
    print('\\nStep 1: Reading HDF5 file...')
    uv_data = UVData()
    uv_data.read(hdf5_file, file_type='uvh5', run_check=False)
    print(f'   - Nblts: {uv_data.Nblts}')
    print(f'   - Mean baseline length: {np.mean(np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))):.3f} m')
    
    # Step 2: Apply antenna position scaling
    print('\\nStep 2: Applying antenna position scaling...')
    current_positions = uv_data.telescope.antenna_positions
    
    # Calculate maximum baseline length from antenna positions
    max_baseline = 0
    for i in range(len(current_positions)):
        for j in range(i+1, len(current_positions)):
            baseline = np.linalg.norm(current_positions[j] - current_positions[i])
            max_baseline = max(max_baseline, baseline)
    
    # Calculate UVW baseline lengths
    uvw_baseline_lengths = np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))
    mean_uvw_baseline = np.mean(uvw_baseline_lengths[uvw_baseline_lengths > 0])
    
    # Calculate scale factor needed
    if max_baseline > 0 and mean_uvw_baseline > 0:
        scale_factor = mean_uvw_baseline / max_baseline
        if abs(scale_factor - 1.0) > 0.1:  # Only scale if significantly different
            corrected_positions = current_positions * scale_factor
            uv_data.telescope.antenna_positions = corrected_positions
            print(f'   - Scaled antenna positions by factor {scale_factor:.3f}')
            print(f'   - Original max baseline: {max_baseline:.1f} m')
            print(f'   - UVW mean baseline: {mean_uvw_baseline:.1f} m')
    
    # Step 3: Test set_uvws_from_antenna_positions
    print('\\nStep 3: Testing set_uvws_from_antenna_positions...')
    try:
        uv_data.set_uvws_from_antenna_positions(update_vis=False)
        print('   - ✅ set_uvws_from_antenna_positions completed')
        
        # Test UVW validation
        print('\\nStep 4: Testing UVW validation...')
        try:
            uv_data.check()
            print('   - ✅ UVW validation passed - no discrepancy warnings!')
        except Exception as e:
            print(f'   - ⚠️ UVW validation issues: {e}')
            
    except Exception as e:
        print(f'   - ❌ set_uvws_from_antenna_positions failed: {e}')
    
    # Step 5: Test MS writing
    print('\\nStep 5: Testing MS writing...')
    output_ms = 'data/ms/test_uvw_warning_source.ms'
    
    # Remove existing MS file
    if os.path.exists(output_ms):
        import shutil
        shutil.rmtree(output_ms)
        print('   - Removed existing MS file')
    
    try:
        uv_data.write_ms(output_ms, clobber=True, fix_autos=True, force_phase=True)
        print('   - ✅ MS writing completed')
        
        if os.path.exists(output_ms):
            size_gb = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                         for dirpath, dirnames, filenames in os.walk(output_ms) 
                         for filename in filenames) / (1024**3)
            print(f'   - MS file size: {size_gb:.1f} GB')
        
    except Exception as e:
        print(f'   - ❌ MS writing failed: {e}')
    
    del uv_data

if __name__ == '__main__':
    asyncio.run(test_uvw_warning_source())
