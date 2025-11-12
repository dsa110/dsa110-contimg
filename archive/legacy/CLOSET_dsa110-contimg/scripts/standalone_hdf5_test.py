#!/usr/bin/env python3
"""
Standalone test for HDF5 to MS conversion.
This script tests the core functionality without complex imports.
"""

import os
import sys
import h5py
import numpy as np
from pathlib import Path
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u

def read_dsa110_hdf5_simple(file_path):
    """Read DSA-110 HDF5 file and extract key information."""
    print(f"Reading {os.path.basename(file_path)}...")
    
    with h5py.File(file_path, 'r') as f:
        # Read data
        visdata = f['Data/visdata'][()]
        flags = f['Data/flags'][()]
        nsamples = f['Data/nsamples'][()]
        
        # Read header
        header = f['Header']
        
        # Basic info
        n_blts = header['Nblts'][()]
        n_freqs = header['Nfreqs'][()]
        n_pols = header['Npols'][()]
        n_ants_data = header['Nants_data'][()]
        
        # Time and frequency
        time_array = header['time_array'][()]
        freq_array = header['freq_array'][()]
        
        # Antenna info
        antenna_names = [name.decode() for name in header['antenna_names'][()]]
        antenna_numbers = header['antenna_numbers'][()]
        antenna_positions = header['antenna_positions'][()]
        
        # Baseline info
        ant_1_array = header['ant_1_array'][()]
        ant_2_array = header['ant_2_array'][()]
        
        # UVW
        uvw_array = header['uvw_array'][()]
        
        # Polarization
        polarization_array = header['polarization_array'][()]
        
        # Telescope location
        lat = header['latitude'][()]
        lon = header['longitude'][()]
        alt = header['altitude'][()]
        
        print(f"  Data shape: {visdata.shape}")
        print(f"  Baselines: {n_blts}")
        print(f"  Frequencies: {n_freqs}")
        print(f"  Polarizations: {n_pols}")
        print(f"  Antennas: {n_ants_data}")
        print(f"  Frequency range: {freq_array.min()/1e9:.3f} - {freq_array.max()/1e9:.3f} GHz")
        print(f"  Time range: {Time(time_array.min(), format='mjd').iso} - {Time(time_array.max(), format='mjd').iso}")
        
        return {
            'visdata': visdata,
            'flags': flags,
            'nsamples': nsamples,
            'time_array': time_array,
            'freq_array': freq_array,
            'antenna_names': antenna_names,
            'antenna_numbers': antenna_numbers,
            'antenna_positions': antenna_positions,
            'ant_1_array': ant_1_array,
            'ant_2_array': ant_2_array,
            'uvw_array': uvw_array,
            'polarization_array': polarization_array,
            'telescope_location': (lat, lon, alt),
            'n_blts': n_blts,
            'n_freqs': n_freqs,
            'n_pols': n_pols,
            'n_ants_data': n_ants_data
        }

def test_pyuvdata_conversion(data_dict):
    """Test converting to PyUVData format."""
    print("Testing PyUVData conversion...")
    
    try:
        import pyuvdata
        from pyuvdata import UVData
        
        uv_data = UVData()
        
        # Set basic parameters
        uv_data.telescope_name = 'DSA-110'
        
        # Telescope location
        lat, lon, alt = data_dict['telescope_location']
        telescope_location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=alt*u.m)
        uv_data.telescope_location = telescope_location
        
        # Set data arrays
        uv_data.data_array = data_dict['visdata']
        uv_data.flag_array = data_dict['flags']
        uv_data.nsample_array = data_dict['nsamples']
        
        # Set time and frequency
        uv_data.time_array = data_dict['time_array']
        uv_data.freq_array = data_dict['freq_array'].reshape(1, -1)
        uv_data.Ntimes = len(np.unique(data_dict['time_array']))
        
        # Set antenna information
        uv_data.antenna_names = data_dict['antenna_names']
        uv_data.antenna_numbers = data_dict['antenna_numbers']
        uv_data.antenna_positions = data_dict['antenna_positions']
        
        # Set baseline information
        uv_data.ant_1_array = data_dict['ant_1_array']
        uv_data.ant_2_array = data_dict['ant_2_array']
        uv_data.uvw_array = data_dict['uvw_array']
        
        # Set polarization
        uv_data.polarization_array = data_dict['polarization_array']
        
        # Set dimensions
        uv_data.Nblts = data_dict['n_blts']
        uv_data.Nfreqs = data_dict['n_freqs']
        uv_data.Npols = data_dict['n_pols']
        uv_data.Nants_data = data_dict['n_ants_data']
        uv_data.Nbls = len(np.unique(uv_data.ant_1_array * 1000 + uv_data.ant_2_array))
        
        # Set other required parameters
        uv_data.vis_units = 'Jy'
        uv_data.Nspws = 1
        uv_data.spw_array = np.array([0])
        
        # Set integration time and channel width
        integration_time = np.full(data_dict['n_blts'], 10.0)  # 10 seconds default
        uv_data.integration_time = integration_time
        uv_data.channel_width = np.full(data_dict['n_freqs'], 0.244e6)  # 0.244 MHz
        
        print(f"  Created PyUVData object:")
        print(f"    Nbls: {uv_data.Nbls}")
        print(f"    Nfreqs: {uv_data.Nfreqs}")
        print(f"    Ntimes: {uv_data.Ntimes}")
        print(f"    Npols: {uv_data.Npols}")
        
        return uv_data
        
    except Exception as e:
        print(f"  PyUVData conversion failed: {e}")
        return None

def test_ms_creation(uv_data, output_path):
    """Test MS creation from PyUVData object."""
    print(f"Testing MS creation to {output_path}...")
    
    try:
        # Write to MS
        uv_data.write_ms(str(output_path), clobber=True)
        print(f"  Successfully created MS: {output_path}")
        
        # Validate MS
        try:
            from casatools import ms
            ms_tool = ms()
            ms_tool.open(str(output_path))
            
            n_rows = ms_tool.nrow()
            n_antennas = ms_tool.nantennas()
            n_spws = ms_tool.nspw()
            
            ms_tool.close()
            ms_tool.done()
            
            print(f"  MS validation passed:")
            print(f"    Rows: {n_rows}")
            print(f"    Antennas: {n_antennas}")
            print(f"    SPWs: {n_spws}")
            
            return True
            
        except ImportError:
            print("  CASA not available for MS validation")
            return True
        except Exception as e:
            print(f"  MS validation failed: {e}")
            return False
            
    except Exception as e:
        print(f"  MS creation failed: {e}")
        return False

def main():
    """Main test function."""
    print("DSA-110 Standalone HDF5 to MS Test")
    print("=" * 40)
    
    # Test data
    test_dir = Path("/data/incoming_test/")
    if not test_dir.exists():
        print(f"Test directory not found: {test_dir}")
        return False
    
    hdf5_files = list(test_dir.glob("*.hdf5"))
    if not hdf5_files:
        print("No HDF5 files found")
        return False
    
    print(f"Found {len(hdf5_files)} HDF5 files")
    
    # Test with first file
    test_file = hdf5_files[0]
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)
    output_ms = output_dir / f"test_{test_file.stem}.ms"
    
    try:
        # Read HDF5 data
        data_dict = read_dsa110_hdf5_simple(test_file)
        
        # Convert to PyUVData
        uv_data = test_pyuvdata_conversion(data_dict)
        if uv_data is None:
            print("❌ PyUVData conversion failed")
            return False
        
        # Create MS
        success = test_ms_creation(uv_data, output_ms)
        
        if success:
            print("\n✅ HDF5 to MS conversion test PASSED!")
            print(f"MS file created: {output_ms}")
            return True
        else:
            print("\n❌ HDF5 to MS conversion test FAILED!")
            return False
            
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
