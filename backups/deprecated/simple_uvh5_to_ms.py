#!/usr/bin/env python3
"""
Simple UVH5 to CASA Measurement Set Converter for DSA-110

A minimal script to convert UVH5 files to CASA Measurement Sets.
"""

import os
import glob
import shutil
import argparse
from datetime import datetime
from typing import List, Optional

import numpy as np
import astropy.units as u
from pyuvdata import UVData
from casatasks import importuvfits
from casacore.tables import addImagingColumns, table


def find_subband_groups(input_dir: str, start_time: str, end_time: str) -> List[List[str]]:
    """Find DSA-110 subband file groups within the specified time range."""
    print(f"Searching for DSA-110 subband files in {input_dir}...")
    
    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    
    # Find all HDF5 subband files in the directory
    hdf5_pattern = os.path.join(input_dir, '*sb??.hdf5')
    all_files = glob.glob(hdf5_pattern)
    
    if not all_files:
        print(f"No HDF5 subband files found in {input_dir}")
        return []
    
    # Group files by timestamp (extract timestamp from filename)
    timestamp_groups = {}
    for file_path in all_files:
        try:
            filename = os.path.basename(file_path)
            # Extract timestamp from filename (e.g., 2024-01-01T12:30:45_sb01.hdf5)
            # Remove subband suffix and file extension
            timestamp_str = filename.replace('.hdf5', '').split('_sb')[0]
            
            # Try different timestamp formats commonly used in DSA-110
            file_dt = None
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y%m%d_%H%M%S']:
                try:
                    file_dt = datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue
            
            if file_dt is None:
                print(f"Warning: Could not parse timestamp from {filename}")
                continue
            
            # Check if file is within time range
            if start_dt <= file_dt <= end_dt:
                if file_dt not in timestamp_groups:
                    timestamp_groups[file_dt] = []
                timestamp_groups[file_dt].append(file_path)
                print(f"  Found: {filename} ({file_dt})")
                
        except Exception as e:
            print(f"Warning: Error processing {file_path}: {e}")
            continue
    
    # Convert to list of file groups and sort by timestamp
    file_groups = []
    for timestamp in sorted(timestamp_groups.keys()):
        group_files = sorted(timestamp_groups[timestamp])
        file_groups.append(group_files)
        print(f"  Group {timestamp}: {len(group_files)} subband files")
    
    print(f"Found {len(file_groups)} observation groups within time range")
    return file_groups


def convert_subband_group(subband_files: List[str], output_dir: str) -> bool:
    """Convert a group of DSA-110 subband files to a single CASA Measurement Set."""
    try:
        print(f"Converting {len(subband_files)} subband files...")
        print(f"  Files: {[os.path.basename(f) for f in subband_files]}")
        
        # Load and combine subband files
        uvdata = UVData()
        
        # Read the first file to initialize the structure
        uvdata.read(subband_files[0], file_type='uvh5', run_check_acceptability=False,
                    strict_uvw_antpos_check=False)
        
        # If there are multiple files, read and combine them
        if len(subband_files) > 1:
            for file_path in subband_files[1:]:
                temp_uv = UVData()
                temp_uv.read(file_path, file_type='uvh5', run_check_acceptability=False,
                            strict_uvw_antpos_check=False)
                # Combine the data
                uvdata += temp_uv
        
        # Generate output filename from the first file (remove subband suffix)
        first_file = subband_files[0]
        base_name = os.path.splitext(os.path.basename(first_file))[0].split('_sb')[0]
        msname = os.path.join(output_dir, base_name)
        
        # Remove existing files
        fits_file = f'{msname}.fits'
        ms_file = f'{msname}.ms'
        
        if os.path.exists(fits_file):
            os.remove(fits_file)
        if os.path.exists(ms_file):
            shutil.rmtree(ms_file)
        
        # Write UVFITS intermediate file
        print("  Writing UVFITS intermediate file...")
        uvdata.write_uvfits(
            fits_file,
            spoof_nonessential=True,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False
        )
        
        # Convert to Measurement Set
        print("  Converting to Measurement Set...")
        importuvfits(fits_file, ms_file)
        
        # Set antenna positions (simplified)
        n_ants = uvdata.Nants_telescope
        antenna_positions = np.zeros((n_ants, 3))
        for i in range(n_ants):
            antenna_positions[i, 0] = i * 4.65  # Simple array layout
        
        with table(f'{ms_file}/ANTENNA', readonly=False) as tb:
            if tb.nrows() == antenna_positions.shape[0]:
                tb.putcol('POSITION', antenna_positions)
        
        # Add imaging columns
        addImagingColumns(ms_file)
        
        # Set model column
        model_data = np.ones((uvdata.Nblts, uvdata.Nfreqs, uvdata.Npols),
                            dtype=np.complex64)
        with table(ms_file, readonly=False) as tb:
            tb.putcol('MODEL_DATA', model_data)
            data = tb.getcol('DATA')
            tb.putcol('CORRECTED_DATA', data)
        
        # Clean up intermediate file
        os.remove(fits_file)
        
        print(f"  ✓ Successfully converted to {msname}.ms")
        return True
        
    except Exception as e:
        print(f"  ✗ Error converting subband group: {e}")
        return False


def main():
    """Main conversion function."""
    parser = argparse.ArgumentParser(
        description="Convert DSA-110 subband files to CASA Measurement Sets"
    )
    
    parser.add_argument('input_dir', help='Directory containing HDF5 subband files (*sb??.hdf5)')
    parser.add_argument('output_dir', help='Directory to write Measurement Sets')
    parser.add_argument('start_time', help='Start time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('end_time', help='End time (YYYY-MM-DD HH:MM:SS)')
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory {args.input_dir} does not exist")
        return 1
    
    # Validate time format
    try:
        datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S')
        datetime.strptime(args.end_time, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        print("Error: Time format must be 'YYYY-MM-DD HH:MM:SS'")
        return 1
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    print("=" * 60)
    print("DSA-110 UVH5 to CASA Measurement Set Converter")
    print("=" * 60)
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Time range: {args.start_time} to {args.end_time}")
    print()
    
    # Find subband file groups
    subband_groups = find_subband_groups(args.input_dir, args.start_time, args.end_time)
    
    if not subband_groups:
        print("No subband file groups found within the specified time range.")
        return 0
    
    # Convert groups
    successful = 0
    failed = 0
    
    for i, subband_files in enumerate(subband_groups):
        print(f"\nProcessing group {i+1}/{len(subband_groups)}")
        if convert_subband_group(subband_files, args.output_dir):
            successful += 1
        else:
            failed += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("CONVERSION SUMMARY")
    print("=" * 60)
    print(f"Total observation groups processed: {len(subband_groups)}")
    print(f"Successful conversions: {successful}")
    print(f"Failed conversions: {failed}")
    print(f"Success rate: {successful/len(subband_groups)*100:.1f}%")
    
    if successful > 0:
        print(f"\nMeasurement Sets written to: {args.output_dir}")
    
    return 0


if __name__ == "__main__":
    exit(main())
