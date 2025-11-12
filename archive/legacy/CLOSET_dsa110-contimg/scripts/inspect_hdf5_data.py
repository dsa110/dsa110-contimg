#!/usr/bin/env python3
"""
Quick inspection script for DSA-110 HDF5 data.

This script provides a quick way to inspect the structure and content
of the HDF5 files in /data/incoming_test/
"""

import os
import sys
import h5py
import numpy as np
from pathlib import Path
from astropy.time import Time

def inspect_hdf5_file(file_path):
    """Inspect a single HDF5 file."""
    print(f"\n=== Inspecting {os.path.basename(file_path)} ===")
    
    try:
        with h5py.File(file_path, 'r') as f:
            print(f"File size: {os.path.getsize(file_path) / 1024**2:.1f} MB")
            print(f"HDF5 structure:")
            
            def print_structure(name, obj):
                if isinstance(obj, h5py.Dataset):
                    print(f"  {name}: {obj.shape} {obj.dtype}")
                else:
                    print(f"  {name}/ (group)")
            
            f.visititems(print_structure)
            
            # Look for common radio astronomy data
            if 'Data' in f:
                data = f['Data']
                print(f"\nData array shape: {data.shape}")
                print(f"Data array dtype: {data.dtype}")
                
                # Sample a small portion
                if data.size > 0:
                    sample = data[0] if data.ndim > 0 else data[()]
                    print(f"Data sample: {sample}")
            
            if 'Header' in f:
                header = f['Header']
                print(f"\nHeader information:")
                for key in header.keys():
                    value = header[key][()]
                    if hasattr(value, 'shape') and value.size > 1:
                        print(f"  {key}: {value.shape} {value.dtype}")
                    else:
                        print(f"  {key}: {value}")
            
            # Look for time/frequency information
            for key in f.keys():
                if 'time' in key.lower() or 'freq' in key.lower():
                    data = f[key]
                    if hasattr(data, 'shape'):
                        print(f"\n{key}: {data.shape} {data.dtype}")
                        if data.size < 20:  # Only print if small
                            print(f"  Values: {data[()]}")
    
    except Exception as e:
        print(f"Error inspecting file: {e}")

def inspect_with_pyuvdata(file_path):
    """Inspect using PyUVData."""
    print(f"\n=== PyUVData Inspection of {os.path.basename(file_path)} ===")
    
    try:
        import pyuvdata
        uv_data = pyuvdata.UVData()
        uv_data.read(str(file_path))
        
        print(f"Telescope: {uv_data.telescope_name}")
        print(f"Number of baselines: {uv_data.Nbls}")
        print(f"Number of frequencies: {uv_data.Nfreqs}")
        print(f"Number of times: {uv_data.Ntimes}")
        print(f"Number of polarizations: {uv_data.Npols}")
        
        if hasattr(uv_data, 'freq_array') and uv_data.freq_array is not None:
            freq_min = uv_data.freq_array.min() / 1e9
            freq_max = uv_data.freq_array.max() / 1e9
            print(f"Frequency range: {freq_min:.3f} - {freq_max:.3f} GHz")
        
        if hasattr(uv_data, 'time_array') and uv_data.time_array is not None:
            time_min = Time(uv_data.time_array.min(), format='mjd')
            time_max = Time(uv_data.time_array.max(), format='mjd')
            print(f"Time range: {time_min.iso} - {time_max.iso}")
        
        if hasattr(uv_data, 'telescope_location') and uv_data.telescope_location is not None:
            print(f"Telescope location: {uv_data.telescope_location}")
        
        if hasattr(uv_data, 'antenna_names') and uv_data.antenna_names is not None:
            print(f"Antenna names: {uv_data.antenna_names[:5]}...")  # First 5
            print(f"Number of antennas: {len(uv_data.antenna_names)}")
        
        if hasattr(uv_data, 'data_array') and uv_data.data_array is not None:
            print(f"Data array shape: {uv_data.data_array.shape}")
            print(f"Data array dtype: {uv_data.data_array.dtype}")
            
            # Check for valid data
            valid_data = ~np.isnan(uv_data.data_array) & (uv_data.data_array != 0)
            print(f"Valid data points: {np.sum(valid_data)} / {uv_data.data_array.size}")
            
            if np.sum(valid_data) > 0:
                valid_values = uv_data.data_array[valid_data]
                print(f"Data range: {np.min(valid_values):.6f} to {np.max(valid_values):.6f}")
        
    except ImportError:
        print("PyUVData not available")
    except Exception as e:
        print(f"PyUVData inspection failed: {e}")

def main():
    """Main inspection function."""
    test_dir = Path("/data/incoming_test/")
    
    if not test_dir.exists():
        print(f"Test directory not found: {test_dir}")
        return
    
    hdf5_files = list(test_dir.glob("*.hdf5"))
    
    if not hdf5_files:
        print("No HDF5 files found in test directory")
        return
    
    print(f"Found {len(hdf5_files)} HDF5 files")
    print("=" * 50)
    
    # Inspect first few files
    for i, file_path in enumerate(hdf5_files[:3]):
        inspect_hdf5_file(file_path)
        inspect_with_pyuvdata(file_path)
        
        if i < len(hdf5_files) - 1:
            print("\n" + "="*50)
    
    if len(hdf5_files) > 3:
        print(f"\n... and {len(hdf5_files) - 3} more files")

if __name__ == "__main__":
    main()
