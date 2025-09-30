#!/usr/bin/env python3
"""
HDF5 Antenna Position Swapper

This utility provides specific methods for swapping antenna positions
between HDF5 files and CSV files when using Pyuvdata.
"""

import sys
import os
import numpy as np
import pandas as pd
import h5py
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import warnings

# Add pipeline path
pipeline_parent_dir = '/data/jfaber/dsa110-contimg/'
if pipeline_parent_dir not in sys.path:
    sys.path.insert(0, pipeline_parent_dir)

from pyuvdata import UVData
from astropy.coordinates import EarthLocation
import astropy.units as u


def read_hdf5_antenna_info(hdf5_path: str) -> Tuple[Optional[np.ndarray], Optional[List[str]], Optional[np.ndarray]]:
    """
    Read antenna information directly from HDF5 file.
    
    Args:
        hdf5_path: Path to HDF5 file
        
    Returns:
        Tuple of (antenna_positions, antenna_names, antenna_numbers)
    """
    try:
        with h5py.File(hdf5_path, 'r') as f:
            if 'Header/antenna_positions' in f and 'Header/antenna_names' in f:
                antenna_positions = f['Header/antenna_positions'][:]
                antenna_names = [name.decode('utf-8') if isinstance(name, bytes) else str(name) 
                               for name in f['Header/antenna_names'][:]]
                
                # Get antenna numbers if available
                if 'Header/antenna_numbers' in f:
                    antenna_numbers = f['Header/antenna_numbers'][:]
                else:
                    antenna_numbers = np.arange(len(antenna_names))
                
                return antenna_positions, antenna_names, antenna_numbers
            else:
                print("No antenna positions found in HDF5 file")
                return None, None, None
                
    except Exception as e:
        print(f"Error reading HDF5 antenna info: {e}")
        return None, None, None


def load_csv_antenna_positions(csv_path: str) -> Tuple[np.ndarray, List[str], np.ndarray]:
    """
    Load antenna positions from CSV file and convert to ITRF coordinates.
    
    Args:
        csv_path: Path to CSV file with antenna positions
        
    Returns:
        Tuple of (antenna_positions_itrf, antenna_names, antenna_numbers)
    """
    try:
        # Read CSV file - adjust skiprows based on your file format
        df = pd.read_csv(csv_path, skiprows=5)  # Adjust as needed
        
        # Clean up the data
        df = df.dropna(subset=['Latitude', 'Longitude', 'Elevation (meters)'])
        
        # Extract station numbers
        def extract_station_number(station_str):
            if isinstance(station_str, str) and station_str.startswith('DSA-'):
                return int(station_str.split('-')[1])
            return int(station_str)
        
        station_numbers = [extract_station_number(str(idx)) for idx in df.index]
        df['Station Number'] = station_numbers
        df.set_index('Station Number', inplace=True)
        
        # Convert to ITRF coordinates
        telescope_location = EarthLocation(
            lat=df['Latitude'].values * u.deg,
            lon=df['Longitude'].values * u.deg,
            height=df['Elevation (meters)'].values * u.m
        )
        
        # Get ITRF coordinates
        antenna_positions_itrf = telescope_location.to_geocentric()
        
        # Create antenna names and numbers
        antenna_names = [f"pad{station_num}" for station_num in df.index]
        antenna_numbers = np.arange(len(antenna_names))
        
        print(f"Loaded {len(antenna_names)} antenna positions from CSV file")
        
        return antenna_positions_itrf, antenna_names, antenna_numbers
        
    except Exception as e:
        print(f"Error loading CSV antenna positions: {e}")
        raise


def swap_uvdata_antenna_positions(uv_data: UVData, csv_path: str) -> UVData:
    """
    Swap antenna positions in a UVData object with positions from CSV file.
    
    This is the recommended approach when working with Pyuvdata UVData objects.
    
    Args:
        uv_data: UVData object to modify
        csv_path: Path to CSV file with new positions
        
    Returns:
        Modified UVData object
    """
    try:
        # Load new positions from CSV
        new_positions, new_names, new_numbers = load_csv_antenna_positions(csv_path)
        
        # Update UVData object
        uv_data.antenna_positions = new_positions
        uv_data.antenna_names = new_names
        uv_data.antenna_numbers = new_numbers
        
        print(f"Updated UVData with {len(new_names)} antennas from CSV file")
        
        return uv_data
        
    except Exception as e:
        print(f"Error swapping UVData antenna positions: {e}")
        raise


def swap_hdf5_antenna_positions(hdf5_path: str, csv_path: str, output_path: str) -> bool:
    """
    Swap antenna positions in HDF5 file with positions from CSV file.
    
    This directly modifies the HDF5 file structure.
    
    Args:
        hdf5_path: Path to input HDF5 file
        csv_path: Path to CSV file with new positions
        output_path: Path to output HDF5 file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load new positions from CSV
        new_positions, new_names, new_numbers = load_csv_antenna_positions(csv_path)
        
        # Read original HDF5 file and create new one with updated positions
        with h5py.File(hdf5_path, 'r') as f_in:
            with h5py.File(output_path, 'w') as f_out:
                # Copy all groups and datasets
                def copy_group(src, dst):
                    for key in src.keys():
                        if isinstance(src[key], h5py.Group):
                            new_group = dst.create_group(key)
                            copy_group(src[key], new_group)
                        else:
                            dst.create_dataset(key, data=src[key][:])
                
                copy_group(f_in, f_out)
                
                # Update antenna positions
                if 'Header/antenna_positions' in f_out:
                    del f_out['Header/antenna_positions']
                f_out['Header/antenna_positions'] = new_positions
                
                # Update antenna names
                if 'Header/antenna_names' in f_out:
                    del f_out['Header/antenna_names']
                antenna_names_bytes = [name.encode('utf-8') for name in new_names]
                f_out['Header/antenna_names'] = antenna_names_bytes
                
                # Update antenna numbers
                if 'Header/antenna_numbers' in f_out:
                    del f_out['Header/antenna_numbers']
                f_out['Header/antenna_numbers'] = new_numbers
        
        print(f"Successfully updated HDF5 file: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error swapping HDF5 antenna positions: {e}")
        return False


def compare_antenna_positions(hdf5_path: str, csv_path: str) -> Dict[str, Any]:
    """
    Compare antenna positions between HDF5 file and CSV file.
    
    Args:
        hdf5_path: Path to HDF5 file
        csv_path: Path to CSV file
        
    Returns:
        Dictionary with comparison results
    """
    try:
        # Read positions from both sources
        hdf5_pos, hdf5_names, hdf5_nums = read_hdf5_antenna_info(hdf5_path)
        csv_pos, csv_names, csv_nums = load_csv_antenna_positions(csv_path)
        
        if hdf5_pos is None:
            return {'error': 'Could not read HDF5 positions'}
        
        # Compare
        n_hdf5 = len(hdf5_pos)
        n_csv = len(csv_pos)
        
        comparison = {
            'hdf5_antennas': n_hdf5,
            'csv_antennas': n_csv,
            'hdf5_names': hdf5_names,
            'csv_names': csv_names,
            'position_differences': None
        }
        
        if n_hdf5 == n_csv:
            # Calculate differences
            pos_diff = np.abs(hdf5_pos - csv_pos)
            comparison['position_differences'] = {
                'max_diff': np.max(pos_diff),
                'mean_diff': np.mean(pos_diff),
                'rms_diff': np.sqrt(np.mean(pos_diff**2))
            }
        
        return comparison
        
    except Exception as e:
        return {'error': str(e)}


def demonstrate_approaches():
    """
    Demonstrate different approaches to swapping antenna positions.
    """
    print("=== HDF5 ANTENNA POSITION SWAPPING APPROACHES ===\n")
    
    # Example file paths (adjust as needed)
    hdf5_file = "data/hdf5/example.hdf5"  # Replace with actual file
    csv_file = "archive/reference_pipelines/dsa110_hi-main/dsa110hi/resources/DSA110_Station_Coordinates.csv"
    output_hdf5 = "data/hdf5/example_swapped.hdf5"
    
    print("APPROACH 1: WORKING WITH UVData OBJECTS (RECOMMENDED)")
    print("=" * 55)
    print("""
    This is the recommended approach when using Pyuvdata:
    
    1. Read HDF5 file with Pyuvdata:
       uv_data = UVData()
       uv_data.read(hdf5_file, file_type='uvh5')
    
    2. Load new positions from CSV:
       new_positions, new_names, new_numbers = load_csv_antenna_positions(csv_file)
    
    3. Update UVData object:
       uv_data.antenna_positions = new_positions
       uv_data.antenna_names = new_names
       uv_data.antenna_numbers = new_numbers
    
    4. Write to new format:
       uv_data.write_ms(output_ms_file)
       # or
       uv_data.write_uvh5(output_hdf5_file)
    """)
    
    print("APPROACH 2: DIRECT HDF5 FILE MODIFICATION")
    print("=" * 45)
    print("""
    This directly modifies the HDF5 file structure:
    
    1. Read original HDF5 file
    2. Load new positions from CSV
    3. Create new HDF5 file with updated positions
    4. Copy all other data unchanged
    
    Use this when you need to preserve the exact HDF5 structure.
    """)
    
    print("APPROACH 3: COMPARISON AND VALIDATION")
    print("=" * 40)
    print("""
    Before swapping, compare positions to understand differences:
    
    1. Read positions from both sources
    2. Calculate differences
    3. Validate antenna counts match
    4. Check coordinate system consistency
    """)
    
    # Demonstrate with actual files if they exist
    if os.path.exists(hdf5_file) and os.path.exists(csv_file):
        print("\nDEMONSTRATION WITH ACTUAL FILES:")
        print("-" * 35)
        
        # Compare positions
        comparison = compare_antenna_positions(hdf5_file, csv_file)
        if 'error' not in comparison:
            print(f"HDF5 antennas: {comparison['hdf5_antennas']}")
            print(f"CSV antennas: {comparison['csv_antennas']}")
            if comparison['position_differences']:
                diff = comparison['position_differences']
                print(f"Max position difference: {diff['max_diff']:.3f} m")
                print(f"Mean position difference: {diff['mean_diff']:.3f} m")
                print(f"RMS position difference: {diff['rms_diff']:.3f} m")
        else:
            print(f"Comparison error: {comparison['error']}")
    else:
        print("\nExample files not found - using demonstration code only")
    
    print("\n=== KEY CONSIDERATIONS ===")
    print("""
    1. Coordinate Systems:
       - HDF5 positions are typically in ITRF coordinates (meters)
       - CSV positions need conversion from lat/lon/alt to ITRF
       - Use astropy.coordinates.EarthLocation for conversion
    
    2. Antenna Numbering:
       - Ensure antenna numbers match between sources
       - Check for 0-based vs 1-based indexing
       - Verify antenna names are consistent
    
    3. UVW Recalculation:
       - After changing antenna positions, UVW coordinates may need recalculation
       - Use pyuvdata.utils.phasing.calc_uvw() for recalculation
       - Consider phase center adjustments
    
    4. Data Validation:
       - Always validate antenna counts match
       - Check baseline lengths are reasonable
       - Verify coordinate system consistency
    """)


if __name__ == "__main__":
    demonstrate_approaches()
