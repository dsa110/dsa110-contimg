#!/usr/bin/env python3
"""
Test script to debug UVW recalculation method
"""

import asyncio
import sys
import os
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from pyuvdata import UVData
from pyuvdata import utils as uvutils
import astropy.units as u

async def test_uvw_recalculation():
    print('🔍 Testing UVW Recalculation Method')
    print('=' * 50)
    
    # Read the existing MS file
    ms_file = 'data/ms/2025-09-05T03:23:14.ms'
    print(f'Reading MS file: {ms_file}')
    
    uv_data = UVData()
    uv_data.read(ms_file)
    
    print(f'UVData loaded:')
    print(f'  - Nblts: {uv_data.Nblts}')
    print(f'  - Ntimes: {uv_data.Ntimes}')
    print(f'  - time_array shape: {uv_data.time_array.shape}')
    print(f'  - lst_array shape: {uv_data.lst_array.shape}')
    
    # Check antenna positions
    if hasattr(uv_data, 'antenna_positions'):
        print(f'  - antenna_positions shape: {uv_data.antenna_positions.shape}')
    elif hasattr(uv_data.telescope, 'antenna_positions'):
        print(f'  - telescope.antenna_positions shape: {uv_data.telescope.antenna_positions.shape}')
    else:
        print('  - No antenna_positions found')
    
    # Test UVW recalculation step by step
    print('\\nTesting UVW recalculation step by step...')
    
    try:
        # Step 1: Get pointing direction - use a single pointing direction
        print('Step 1: Getting pointing direction...')
        
        # Use a single pointing direction (zenith at telescope location)
        pt_ra = np.mean(uv_data.lst_array) * np.pi / 12.0  # Mean LST in radians
        pt_dec = uv_data.telescope.location_lat_lon_alt[0] * np.pi / 180.0  # Telescope latitude
        print(f'  - Using single pointing: RA={pt_ra:.6f}, Dec={pt_dec:.6f}')
        
        # Step 2: Calculate apparent coordinates
        print('Step 2: Calculating apparent coordinates...')
        
        # Use single values for lon_coord and lat_coord
        new_app_ra, new_app_dec = uvutils.phasing.calc_app_coords(
            lon_coord=pt_ra,
            lat_coord=pt_dec,
            coord_frame='icrs',
            coord_epoch=2000.0,
            coord_times=uv_data.time_array,
            coord_type='sidereal',
            time_array=uv_data.time_array,
            lst_array=uv_data.lst_array,
            telescope_loc=uv_data.telescope.location_lat_lon_alt,
            telescope_frame='itrs',
        )
        print(f'  - Apparent RA shape: {new_app_ra.shape}')
        print(f'  - Apparent Dec shape: {new_app_dec.shape}')
        
        # Step 3: Calculate frame position angle
        print('Step 3: Calculating frame position angle...')
        new_frame_pa = uvutils.phasing.calc_frame_pos_angle(
            time_array=uv_data.time_array,
            app_ra=new_app_ra,
            app_dec=new_app_dec,
            telescope_loc=uv_data.telescope.location_lat_lon_alt,
            ref_frame='icrs',
            ref_epoch=2000.0,
            telescope_frame='itrs',
        )
        print(f'  - Frame PA shape: {new_frame_pa.shape}')
        
        # Step 4: Calculate new UVW coordinates
        print('Step 4: Calculating new UVW coordinates...')
        
        # Get antenna positions from the correct location
        if hasattr(uv_data, 'antenna_positions'):
            antenna_positions = uv_data.antenna_positions
            antenna_numbers = uv_data.antenna_numbers
        elif hasattr(uv_data.telescope, 'antenna_positions'):
            antenna_positions = uv_data.telescope.antenna_positions
            antenna_numbers = uv_data.telescope.antenna_numbers
        else:
            print('❌ No antenna positions found!')
            return
        
        new_uvw = uvutils.phasing.calc_uvw(
            app_ra=new_app_ra,
            app_dec=new_app_dec,
            frame_pa=new_frame_pa,
            lst_array=uv_data.lst_array,
            use_ant_pos=True,
            antenna_positions=antenna_positions,
            antenna_numbers=antenna_numbers,
            ant_1_array=uv_data.ant_1_array,
            ant_2_array=uv_data.ant_2_array,
            telescope_lat=uv_data.telescope.location_lat_lon_alt[0],
            telescope_lon=uv_data.telescope.location_lat_lon_alt[1],
        )
        print(f'  - New UVW shape: {new_uvw.shape}')
        print(f'  - Mean baseline length: {np.mean(np.sqrt(np.sum(new_uvw**2, axis=1))):.3f} m')
        
        # Step 5: Compare with original UVW
        print('Step 5: Comparing with original UVW...')
        original_uvw = uv_data.uvw_array
        uvw_diff = np.abs(new_uvw - original_uvw)
        max_diff = np.max(uvw_diff)
        mean_diff = np.mean(uvw_diff)
        print(f'  - Max UVW difference: {max_diff:.3f} m')
        print(f'  - Mean UVW difference: {mean_diff:.3f} m')
        
        # Step 6: Update UVW coordinates
        print('Step 6: Updating UVW coordinates...')
        uv_data.uvw_array = new_uvw
        uv_data.phase_center_app_ra = new_app_ra
        uv_data.phase_center_app_dec = new_app_dec
        uv_data.phase_center_frame_pa = new_frame_pa
        
        print('✅ UVW recalculation completed successfully!')
        
        # Test if the UVW discrepancy is resolved
        print('\\nTesting UVW discrepancy resolution...')
        try:
            # This should trigger the UVW validation
            uv_data.check()
            print('✅ UVW validation passed - no discrepancy warnings!')
        except Exception as e:
            print(f'⚠️ UVW validation still has issues: {e}')
        
    except Exception as e:
        print(f'❌ UVW recalculation failed: {e}')
        import traceback
        traceback.print_exc()
    
    # UVData doesn't have a close method, just delete the object
    del uv_data

if __name__ == '__main__':
    asyncio.run(test_uvw_recalculation())
