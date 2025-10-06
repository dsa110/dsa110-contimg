#!/usr/bin/env python3
"""
DSA-110 UVH5 to CASA Measurement Set Converter

This script converts UVH5 (HDF5) visibility files from the DSA-110 radio telescope
into CASA Measurement Sets (MS) using the dsacalib library functions.

Usage:
    python dsa110_uvh5_to_ms.py <input_dir> <output_dir> <start_time> <end_time>

Example:
    python dsa110_uvh5_to_ms.py /data/uvh5 /data/ms "2024-01-01 00:00:00" "2024-01-01 23:59:59"
"""

import os
import glob
import sys
import argparse
from datetime import datetime
from typing import List, Optional

import numpy as np
import astropy.units as u
from astropy.time import Time
from pyuvdata import UVData

# Import dsacalib functions
try:
    from dsacalib.uvh5_to_ms import uvh5_to_ms, load_uvh5_file
    from dsacalib.utils import Direction, generate_calibrator_source
    from dsacalib.fringestopping import amplitude_sky_model
    from dsacalib import constants as ct
except ImportError as e:
    print(f"Error importing dsacalib: {e}")
    print("Please ensure dsacalib is installed and in your Python path")
    sys.exit(1)


def find_subband_groups_in_time_range(input_dir: str, start_time: str, end_time: str) -> List[List[str]]:
    """
    Find all DSA-110 subband file groups in the input directory that fall within the specified time range.
    
    This function searches for HDF5 subband files with pattern *sb??.hdf5 and groups them by timestamp
    to form complete observations. Each group represents a single observation with multiple subbands.
    
    Parameters:
    -----------
    input_dir : str
        Path to directory containing HDF5 subband files
    start_time : str
        Start time in 'YYYY-MM-DD HH:MM:SS' format
    end_time : str
        End time in 'YYYY-MM-DD HH:MM:SS' format
        
    Returns:
    --------
    List[List[str]]
        List of subband file groups, where each group contains all subband files for one observation
    """
    print(f"Searching for DSA-110 subband files in {input_dir}...")
    
    # Convert time strings to datetime objects for comparison
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


def convert_subband_group(subband_files: List[str], output_dir: str, refmjd: float = 59215.0) -> bool:
    """
    Convert a group of DSA-110 subband files to a single CASA Measurement Set using dsacalib functions.
    
    This function uses the dsacalib.uvh5_to_ms.uvh5_to_ms function to perform
    the conversion, which handles all the necessary steps including phasing,
    antenna positioning, and MS creation. It combines multiple subband files
    into a single Measurement Set.
    
    Parameters:
    -----------
    subband_files : List[str]
        List of paths to the HDF5 subband files to convert
    output_dir : str
        Directory to write the Measurement Set
    refmjd : float
        Reference MJD for fringestopping (default: 59215.0)
        
    Returns:
    --------
    bool
        True if conversion successful, False otherwise
    """
    try:
        # Generate output filename from the first file (remove subband suffix)
        first_file = subband_files[0]
        base_name = os.path.splitext(os.path.basename(first_file))[0].split('_sb')[0]
        msname = os.path.join(output_dir, base_name)
        
        print(f"Converting {len(subband_files)} subband files to {base_name}.ms...")
        print(f"  Files: {[os.path.basename(f) for f in subband_files]}")
        
        # Use dsacalib's uvh5_to_ms function for conversion
        # This function handles:
        # - Loading multiple HDF5 subband files
        # - Combining them into a single observation
        # - Setting antenna positions
        # - Phasing visibilities
        # - Writing to Measurement Set format
        # - Setting model column
        uvh5_to_ms(
            fname=subband_files,  # Pass list of files
            msname=msname,
            refmjd=refmjd,
            ra=None,  # Will phase at meridian
            dec=None,  # Will use pointing declination
            dt=None,  # Extract entire file
            antenna_list=None,  # Include all antennas
            flux=None,  # No flux model
            fringestop=True,  # Apply fringestopping
            logger=None  # No logging
        )
        
        print(f"✓ Successfully converted to {msname}.ms")
        return True
        
    except Exception as e:
        print(f"✗ Error converting subband group: {e}")
        return False


def convert_subband_groups_to_ms(input_dir: str, output_dir: str, start_time: str, end_time: str) -> None:
    """
    Main function to convert DSA-110 subband file groups to CASA Measurement Sets.
    
    This function orchestrates the entire conversion process:
    1. Finds subband file groups within the specified time range
    2. Creates the output directory if it doesn't exist
    3. Converts each group using dsacalib functions
    4. Reports success/failure for each group
    
    Parameters:
    -----------
    input_dir : str
        Directory containing HDF5 subband files
    output_dir : str
        Directory to write Measurement Sets
    start_time : str
        Start time in 'YYYY-MM-DD HH:MM:SS' format
    end_time : str
        End time in 'YYYY-MM-DD HH:MM:SS' format
    """
    print("=" * 70)
    print("DSA-110 Subband to CASA Measurement Set Converter")
    print("Using dsacalib library functions")
    print("=" * 70)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Time range: {start_time} to {end_time}")
    print()
    
    # Find subband file groups within time range
    subband_groups = find_subband_groups_in_time_range(input_dir, start_time, end_time)
    
    if not subband_groups:
        print("No subband file groups found within the specified time range.")
        return
    
    # Convert each subband group
    successful_conversions = 0
    failed_conversions = 0
    
    for i, subband_files in enumerate(subband_groups):
        print(f"\nProcessing group {i+1}/{len(subband_groups)}")
        
        success = convert_subband_group(subband_files, output_dir)
        
        if success:
            successful_conversions += 1
        else:
            failed_conversions += 1
    
    # Print summary
    print("\n" + "=" * 70)
    print("CONVERSION SUMMARY")
    print("=" * 70)
    print(f"Total observation groups processed: {len(subband_groups)}")
    print(f"Successful conversions: {successful_conversions}")
    print(f"Failed conversions: {failed_conversions}")
    print(f"Success rate: {successful_conversions/len(subband_groups)*100:.1f}%")
    
    if successful_conversions > 0:
        print(f"\nMeasurement Sets written to: {output_dir}")
        print("You can now use these Measurement Sets with CASA for calibration and imaging.")


def main():
    """Command-line interface for the UVH5 to MS converter."""
    parser = argparse.ArgumentParser(
        description="Convert DSA-110 subband files to CASA Measurement Sets using dsacalib",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dsa110_uvh5_to_ms.py /path/to/subband/files /path/to/output "2024-01-01 00:00:00" "2024-01-01 23:59:59"
  python dsa110_uvh5_to_ms.py /data/hdf5 /data/ms "2024-01-01 00:00:00" "2024-01-01 01:00:00"

Note:
  This script expects DSA-110 subband files with pattern *sb??.hdf5 (e.g., 2024-01-01T12:30:45_sb01.hdf5)
  and groups them by timestamp to form complete observations. Each group is converted to a single MS.
  This script requires the dsacalib library to be installed and accessible.
        """
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
    
    # Run conversion
    convert_subband_groups_to_ms(
        args.input_dir,
        args.output_dir,
        args.start_time,
        args.end_time
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
