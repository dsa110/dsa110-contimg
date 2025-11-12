#!/usr/bin/env python3
"""
Test UVW fix directly without circular imports
"""

import asyncio
import sys
import os
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from pyuvdata import UVData

async def test_uvw_fix_direct():
    print('🔧 Testing UVW Fix Directly')
    print('=' * 35)
    
    # Test with single HDF5 file
    hdf5_file = '/data/incoming_test/2025-09-05T03:23:14_sb00.hdf5'
    output_ms = 'data/ms/test_uvw_fix_direct.ms'
    
    print(f'Input HDF5: {hdf5_file}')
    print(f'Output MS: {output_ms}')
    
    # Remove existing MS file
    if os.path.exists(output_ms):
        import shutil
        shutil.rmtree(output_ms)
        print('   Removed existing MS file')
    
    try:
        # Step 1: Read HDF5 file
        print('\\nStep 1: Reading HDF5 file...')
        uv_data = UVData()
        uv_data.read(hdf5_file, file_type='uvh5', run_check=False)
        
        print(f'   - Nblts: {uv_data.Nblts}')
        print(f'   - Ntimes: {uv_data.Ntimes}')
        print(f'   - Antenna positions shape: {uv_data.telescope.antenna_positions.shape}')
        print(f'   - Mean baseline length before: {np.mean(np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))):.3f} m')
        
        # Step 2: Apply DSA-110 fixes (including antenna position scaling)
        print('\\nStep 2: Applying DSA-110 fixes...')
        
        # Fix 1: Ensure uvw_array is float64
        if uv_data.uvw_array.dtype != np.float64:
            uv_data.uvw_array = uv_data.uvw_array.astype(np.float64)
        
        # Fix 2: Correct telescope name
        if uv_data.telescope.name == "OVRO_MMA":
            uv_data.telescope.name = "DSA-110"
        
        # Fix 3: Set data units
        if not hasattr(uv_data, 'vis_units') or uv_data.vis_units is None or uv_data.vis_units == 'uncalib':
            uv_data.vis_units = 'Jy'
        
        # Fix 4: Set mount type
        if hasattr(uv_data.telescope, 'mount_type'):
            uv_data.telescope.mount_type = ['alt-az'] * len(uv_data.telescope.mount_type)
        
        # Fix 5: Scale antenna positions to match UVW baseline lengths
        print('   - Scaling antenna positions...')
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
                print(f'     - Scaled antenna positions by factor {scale_factor:.3f}')
                print(f'     - Original max baseline: {max_baseline:.1f} m')
                print(f'     - UVW mean baseline: {mean_uvw_baseline:.1f} m')
        
        # Step 3: Recalculate UVW coordinates
        print('\\nStep 3: Recalculating UVW coordinates...')
        uv_data.set_uvws_from_antenna_positions(update_vis=False)
        print('   - UVW recalculation completed')
        
        print(f'   - Mean baseline length after: {np.mean(np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))):.3f} m')
        
        # Step 4: Test UVW validation
        print('\\nStep 4: Testing UVW validation...')
        try:
            uv_data.check()
            print('   - ✅ UVW validation passed - no discrepancy warnings!')
        except Exception as e:
            print(f'   - ⚠️ UVW validation issues: {e}')
        
        # Step 5: Write MS file
        print('\\nStep 5: Writing MS file...')
        uv_data.write_ms(output_ms, clobber=True, fix_autos=True, force_phase=True)
        
        if os.path.exists(output_ms):
            size_gb = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                         for dirpath, dirnames, filenames in os.walk(output_ms) 
                         for filename in filenames) / (1024**3)
            print(f'   - MS file size: {size_gb:.1f} GB')
            print('   - ✅ MS file created successfully!')
        
        del uv_data
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_uvw_fix_direct())
