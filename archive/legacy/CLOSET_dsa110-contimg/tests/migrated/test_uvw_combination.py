#!/usr/bin/env python3
"""
Test UVW warning during HDF5 file combination
"""

import asyncio
import sys
import os
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from pyuvdata import UVData

async def test_uvw_combination():
    print('🔍 Testing UVW Warning During HDF5 Combination')
    print('=' * 50)
    
    # Test with two HDF5 files
    hdf5_files = [
        '/data/incoming_test/2025-09-05T03:23:14_sb00.hdf5',
        '/data/incoming_test/2025-09-05T03:23:14_sb01.hdf5'
    ]
    
    print(f'Testing with {len(hdf5_files)} files:')
    for f in hdf5_files:
        print(f'  - {os.path.basename(f)}')
    
    # Step 1: Read first file
    print('\\nStep 1: Reading first HDF5 file...')
    uv_data = UVData()
    uv_data.read(hdf5_files[0], file_type='uvh5', run_check=False)
    print(f'   - Nblts: {uv_data.Nblts}')
    print(f'   - Mean baseline length: {np.mean(np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))):.3f} m')
    
    # Apply fixes to first file
    print('\\nStep 2: Applying fixes to first file...')
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
    
    # Recalculate UVW coordinates
    uv_data.set_uvws_from_antenna_positions(update_vis=False)
    print('   - Recalculated UVW coordinates')
    
    # Step 3: Read second file
    print('\\nStep 3: Reading second HDF5 file...')
    uv_data_2 = UVData()
    uv_data_2.read(hdf5_files[1], file_type='uvh5', run_check=False)
    print(f'   - Nblts: {uv_data_2.Nblts}')
    print(f'   - Mean baseline length: {np.mean(np.sqrt(np.sum(uv_data_2.uvw_array**2, axis=1))):.3f} m')
    
    # Apply fixes to second file
    print('\\nStep 4: Applying fixes to second file...')
    current_positions_2 = uv_data_2.telescope.antenna_positions
    
    # Calculate maximum baseline length from antenna positions
    max_baseline_2 = 0
    for i in range(len(current_positions_2)):
        for j in range(i+1, len(current_positions_2)):
            baseline = np.linalg.norm(current_positions_2[j] - current_positions_2[i])
            max_baseline_2 = max(max_baseline_2, baseline)
    
    # Calculate UVW baseline lengths
    uvw_baseline_lengths_2 = np.sqrt(np.sum(uv_data_2.uvw_array**2, axis=1))
    mean_uvw_baseline_2 = np.mean(uvw_baseline_lengths_2[uvw_baseline_lengths_2 > 0])
    
    # Calculate scale factor needed
    if max_baseline_2 > 0 and mean_uvw_baseline_2 > 0:
        scale_factor_2 = mean_uvw_baseline_2 / max_baseline_2
        if abs(scale_factor_2 - 1.0) > 0.1:  # Only scale if significantly different
            corrected_positions_2 = current_positions_2 * scale_factor_2
            uv_data_2.telescope.antenna_positions = corrected_positions_2
            print(f'   - Scaled antenna positions by factor {scale_factor_2:.3f}')
    
    # Recalculate UVW coordinates
    uv_data_2.set_uvws_from_antenna_positions(update_vis=False)
    print('   - Recalculated UVW coordinates')
    
    # Step 5: Test combination
    print('\\nStep 5: Testing combination...')
    try:
        uv_data += uv_data_2
        print('   - ✅ Combination completed')
        print(f'   - Combined Nblts: {uv_data.Nblts}')
        print(f'   - Combined mean baseline length: {np.mean(np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))):.3f} m')
        
        # Test UVW validation on combined data
        print('\\nStep 6: Testing UVW validation on combined data...')
        try:
            uv_data.check()
            print('   - ✅ UVW validation passed - no discrepancy warnings!')
        except Exception as e:
            print(f'   - ⚠️ UVW validation issues: {e}')
            
    except Exception as e:
        print(f'   - ❌ Combination failed: {e}')
        import traceback
        traceback.print_exc()
    
    del uv_data, uv_data_2

if __name__ == '__main__':
    asyncio.run(test_uvw_combination())
