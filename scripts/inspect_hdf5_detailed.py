#!/usr/bin/env python3
"""
Detailed inspection of DSA-110 HDF5 data with proper PyUVData handling.
"""

import os
import sys
import h5py
import numpy as np
from pathlib import Path
from astropy.time import Time

def inspect_hdf5_detailed(file_path):
    """Detailed inspection of HDF5 file."""
    print(f"\n=== Detailed Inspection: {os.path.basename(file_path)} ===")
    
    with h5py.File(file_path, 'r') as f:
        # Data information
        print("Data Information:")
        visdata = f['Data/visdata']
        flags = f['Data/flags']
        nsamples = f['Data/nsamples']
        
        print(f"  Visibility data shape: {visdata.shape}")
        print(f"  Flags shape: {flags.shape}")
        print(f"  NSamples shape: {nsamples.shape}")
        
        # Check data quality
        flags_array = flags[()]
        nsamples_array = nsamples[()]
        visdata_array = visdata[()]
        
        valid_data = ~flags_array & (nsamples_array > 0)
        n_valid = np.sum(valid_data)
        n_total = visdata_array.size
        print(f"  Valid data points: {n_valid:,} / {n_total:,} ({100*n_valid/n_total:.1f}%)")
        
        if n_valid > 0:
            valid_vis = visdata_array[valid_data]
            print(f"  Visibility range: {np.min(np.abs(valid_vis)):.6f} to {np.max(np.abs(valid_vis)):.6f}")
        
        # Header information
        print("\nHeader Information:")
        header = f['Header']
        
        # Basic dimensions
        print(f"  Nants_data: {header['Nants_data'][()]}")
        print(f"  Nants_telescope: {header['Nants_telescope'][()]}")
        print(f"  Nbls: {header['Nbls'][()]}")
        print(f"  Nblts: {header['Nblts'][()]}")
        print(f"  Nfreqs: {header['Nfreqs'][()]}")
        print(f"  Npols: {header['Npols'][()]}")
        print(f"  Ntimes: {header['Ntimes'][()]}")
        
        # Telescope info
        print(f"  Telescope: {header['telescope_name'][()].decode()}")
        print(f"  Object: {header['object_name'][()].decode()}")
        print(f"  Instrument: {header['instrument'][()].decode()}")
        
        # Coordinates
        lat = header['latitude'][()]
        lon = header['longitude'][()]
        alt = header['altitude'][()]
        print(f"  Location: lat={lat:.6f}, lon={lon:.6f}, alt={alt:.1f}m")
        
        # Frequency info
        freq_array = header['freq_array'][()]
        freq_min = freq_array.min() / 1e9
        freq_max = freq_array.max() / 1e9
        channel_width = header['channel_width'][()] / 1e6  # Convert to MHz
        print(f"  Frequency range: {freq_min:.3f} - {freq_max:.3f} GHz")
        print(f"  Channel width: {channel_width:.3f} MHz")
        
        # Time info
        time_array = header['time_array'][()]
        time_min = Time(time_array.min(), format='mjd')
        time_max = Time(time_array.max(), format='mjd')
        print(f"  Time range: {time_min.iso} - {time_max.iso}")
        print(f"  Duration: {(time_max - time_min).to(u.hour).value:.2f} hours")
        
        # Antenna info
        antenna_names = [name.decode() for name in header['antenna_names'][()]]
        antenna_numbers = header['antenna_numbers'][()]
        print(f"  Antenna names: {antenna_names[:10]}...")  # First 10
        print(f"  Antenna numbers: {antenna_numbers[:10]}...")  # First 10
        
        # Phase center
        phase_center_dec = header['phase_center_app_dec'][()]
        ha_phase_center = header['extra_keywords/ha_phase_center'][()]
        print(f"  Phase center DEC: {phase_center_dec:.6f} deg")
        print(f"  Phase center HA: {ha_phase_center:.6f} hours")
        
        # Polarization
        pol_array = header['polarization_array'][()]
        print(f"  Polarizations: {pol_array}")

def test_pyuvdata_read(file_path):
    """Test reading with PyUVData using different file types."""
    print(f"\n=== PyUVData Reading Test: {os.path.basename(file_path)} ===")
    
    try:
        import pyuvdata
        
        # Try different file types
        file_types = ['uvh5', 'uvfits', 'miriad', 'ms']
        
        for file_type in file_types:
            try:
                print(f"  Trying file_type='{file_type}'...")
                uv_data = pyuvdata.UVData()
                uv_data.read(str(file_path), file_type=file_type)
                
                print(f"  SUCCESS with {file_type}!")
                print(f"    Telescope: {uv_data.telescope_name}")
                print(f"    Nbls: {uv_data.Nbls}")
                print(f"    Nfreqs: {uv_data.Nfreqs}")
                print(f"    Ntimes: {uv_data.Ntimes}")
                
                if hasattr(uv_data, 'freq_array') and uv_data.freq_array is not None:
                    freq_min = uv_data.freq_array.min() / 1e9
                    freq_max = uv_data.freq_array.max() / 1e9
                    print(f"    Frequency range: {freq_min:.3f} - {freq_max:.3f} GHz")
                
                return True
                
            except Exception as e:
                print(f"    Failed with {file_type}: {str(e)[:100]}...")
                continue
        
        print("  All file types failed")
        return False
        
    except ImportError:
        print("  PyUVData not available")
        return False

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
    print("=" * 60)
    
    # Inspect first file in detail
    file_path = hdf5_files[0]
    inspect_hdf5_detailed(file_path)
    test_pyuvdata_read(file_path)
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"- {len(hdf5_files)} HDF5 files found")
    print(f"- Each file: ~138.6 MB")
    print(f"- Data shape: (111744, 1, 48, 2) - baselines, spw, freq, pol")
    print(f"- 117 antennas, 48 frequency channels, 2 polarizations")
    print(f"- Telescope: DSA-110 at OVRO")

if __name__ == "__main__":
    import astropy.units as u
    main()
