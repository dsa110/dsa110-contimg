#!/usr/bin/env python3
"""
Antenna Position Swapper Utility

This utility demonstrates how to swap antenna positions from HDF5 file headers
with positions from a CSV file when using Pyuvdata. It shows multiple approaches
for different use cases.
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


class AntennaPositionSwapper:
    """
    Utility class for swapping antenna positions between HDF5 files and CSV files.
    """
    
    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize the antenna position swapper.
        
        Args:
            csv_path: Path to CSV file with antenna positions
        """
        self.csv_path = csv_path
        self.antenna_positions_df = None
        
    def load_csv_positions(self, csv_path: str) -> pd.DataFrame:
        """
        Load antenna positions from CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            DataFrame with antenna positions
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
            
            self.antenna_positions_df = df
            print(f"Loaded antenna positions for {len(df)} stations from {csv_path}")
            
            return df
            
        except Exception as e:
            print(f"Error loading CSV positions: {e}")
            raise
    
    def read_hdf5_antenna_positions(self, hdf5_path: str) -> Tuple[np.ndarray, List[str], np.ndarray]:
        """
        Read antenna positions directly from HDF5 file.
        
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
                    
                    print(f"Read antenna positions from HDF5: {len(antenna_names)} antennas")
                    return antenna_positions, antenna_names, antenna_numbers
                else:
                    print("No antenna positions found in HDF5 file")
                    return None, None, None
                    
        except Exception as e:
            print(f"Error reading HDF5 antenna positions: {e}")
            return None, None, None
    
    def convert_csv_to_itrf(self, df: pd.DataFrame) -> np.ndarray:
        """
        Convert CSV lat/lon/alt coordinates to ITRF coordinates.
        
        Args:
            df: DataFrame with Latitude, Longitude, Elevation columns
            
        Returns:
            Array of ITRF coordinates (N_ants, 3)
        """
        try:
            # Convert to ITRF coordinates
            telescope_location = EarthLocation(
                lat=df['Latitude'].values * u.deg,
                lon=df['Longitude'].values * u.deg,
                height=df['Elevation (meters)'].values * u.m
            )
            
            # Get ITRF coordinates
            itrf_positions = telescope_location.to_geocentric()
            
            print(f"Converted {len(itrf_positions)} positions to ITRF coordinates")
            return itrf_positions
            
        except Exception as e:
            print(f"Error converting to ITRF: {e}")
            raise
    
    def swap_positions_in_uvdata(self, uv_data: UVData, csv_path: str) -> UVData:
        """
        Swap antenna positions in a UVData object with positions from CSV file.
        
        Args:
            uv_data: UVData object to modify
            csv_path: Path to CSV file with new positions
            
        Returns:
            Modified UVData object
        """
        try:
            # Load CSV positions
            df = self.load_csv_positions(csv_path)
            
            # Convert to ITRF coordinates
            new_positions = self.convert_csv_to_itrf(df)
            
            # Create antenna names and numbers
            antenna_names = [f"pad{station_num}" for station_num in df.index]
            antenna_numbers = np.arange(len(antenna_names))
            
            # Update UVData object
            uv_data.antenna_positions = new_positions
            uv_data.antenna_names = antenna_names
            uv_data.antenna_numbers = antenna_numbers
            
            print(f"Updated UVData with {len(antenna_names)} antennas from CSV file")
            
            return uv_data
            
        except Exception as e:
            print(f"Error swapping positions in UVData: {e}")
            raise
    
    def swap_positions_in_hdf5(self, hdf5_path: str, csv_path: str, output_path: str) -> bool:
        """
        Swap antenna positions in HDF5 file with positions from CSV file.
        
        Args:
            hdf5_path: Path to input HDF5 file
            csv_path: Path to CSV file with new positions
            output_path: Path to output HDF5 file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load CSV positions
            df = self.load_csv_positions(csv_path)
            new_positions = self.convert_csv_to_itrf(df)
            
            # Create antenna names and numbers
            antenna_names = [f"pad{station_num}" for station_num in df.index]
            antenna_numbers = np.arange(len(antenna_names))
            
            # Read original HDF5 file
            with h5py.File(hdf5_path, 'r') as f_in:
                # Create output file
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
                    antenna_names_bytes = [name.encode('utf-8') for name in antenna_names]
                    f_out['Header/antenna_names'] = antenna_names_bytes
                    
                    # Update antenna numbers
                    if 'Header/antenna_numbers' in f_out:
                        del f_out['Header/antenna_numbers']
                    f_out['Header/antenna_numbers'] = antenna_numbers
            
            print(f"Successfully updated HDF5 file: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error swapping positions in HDF5: {e}")
            return False
    
    def compare_positions(self, hdf5_path: str, csv_path: str) -> Dict[str, Any]:
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
            hdf5_pos, hdf5_names, hdf5_nums = self.read_hdf5_antenna_positions(hdf5_path)
            df = self.load_csv_positions(csv_path)
            csv_pos = self.convert_csv_to_itrf(df)
            
            if hdf5_pos is None:
                return {'error': 'Could not read HDF5 positions'}
            
            # Compare
            n_hdf5 = len(hdf5_pos)
            n_csv = len(csv_pos)
            
            comparison = {
                'hdf5_antennas': n_hdf5,
                'csv_antennas': n_csv,
                'hdf5_names': hdf5_names,
                'csv_names': [f"pad{station_num}" for station_num in df.index],
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


def demonstrate_swapping():
    """
    Demonstrate different approaches to swapping antenna positions.
    """
    print("=== ANTENNA POSITION SWAPPING DEMONSTRATION ===\n")
    
    # Initialize swapper
    swapper = AntennaPositionSwapper()
    
    # Example file paths (adjust as needed)
    hdf5_file = "data/hdf5/example.hdf5"  # Replace with actual file
    csv_file = "archive/reference_pipelines/dsa110_hi-main/dsa110hi/resources/DSA110_Station_Coordinates.csv"
    output_hdf5 = "data/hdf5/example_swapped.hdf5"
    
    print("1. COMPARING POSITIONS")
    print("-" * 30)
    if os.path.exists(hdf5_file) and os.path.exists(csv_file):
        comparison = swapper.compare_positions(hdf5_file, csv_file)
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
        print("Example files not found - skipping comparison")
    
    print("\n2. SWAPPING IN UVData OBJECT")
    print("-" * 35)
    if os.path.exists(hdf5_file) and os.path.exists(csv_file):
        try:
            # Read HDF5 with Pyuvdata
            uv_data = UVData()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                uv_data.read(hdf5_file, file_type='uvh5', run_check=False)
            
            print(f"Original UVData: {len(uv_data.antenna_names)} antennas")
            
            # Swap positions
            uv_data_swapped = swapper.swap_positions_in_uvdata(uv_data, csv_file)
            
            print(f"Swapped UVData: {len(uv_data_swapped.antenna_names)} antennas")
            print("UVData antenna position swap completed successfully!")
            
        except Exception as e:
            print(f"UVData swap error: {e}")
    else:
        print("Example files not found - skipping UVData swap")
    
    print("\n3. SWAPPING IN HDF5 FILE")
    print("-" * 30)
    if os.path.exists(hdf5_file) and os.path.exists(csv_file):
        success = swapper.swap_positions_in_hdf5(hdf5_file, csv_file, output_hdf5)
        if success:
            print("HDF5 file position swap completed successfully!")
        else:
            print("HDF5 file position swap failed!")
    else:
        print("Example files not found - skipping HDF5 swap")
    
    print("\n=== DEMONSTRATION COMPLETE ===")


if __name__ == "__main__":
    demonstrate_swapping()
