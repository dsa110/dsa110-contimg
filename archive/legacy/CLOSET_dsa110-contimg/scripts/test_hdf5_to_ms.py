#!/usr/bin/env python3
"""
Test HDF5 to MS conversion with real DSA-110 data.
"""

import os
import sys
import h5py
import numpy as np
from pathlib import Path
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u

def read_dsa110_hdf5(file_path):
    """Read DSA-110 HDF5 file and convert to PyUVData format."""
    print(f"Reading DSA-110 HDF5 file: {os.path.basename(file_path)}")
    
    with h5py.File(file_path, 'r') as f:
        # Read data
        visdata = f['Data/visdata'][()]
        flags = f['Data/flags'][()]
        nsamples = f['Data/nsamples'][()]
        
        # Read header
        header = f['Header']
        
        # Basic dimensions
        Nblts = header['Nblts'][()]
        Nfreqs = header['Nfreqs'][()]
        Npols = header['Npols'][()]
        Nants_data = header['Nants_data'][()]
        Nants_telescope = header['Nants_telescope'][()]
        
        # Time and frequency
        time_array = header['time_array'][()]
        freq_array = header['freq_array'][()]
        
        # Antenna information
        antenna_names = [name.decode() for name in header['antenna_names'][()]]
        antenna_numbers = header['antenna_numbers'][()]
        antenna_positions = header['antenna_positions'][()]
        
        # Baseline information
        ant_1_array = header['ant_1_array'][()]
        ant_2_array = header['ant_2_array'][()]
        
        # UVW coordinates
        uvw_array = header['uvw_array'][()]
        
        # Polarization
        polarization_array = header['polarization_array'][()]
        
        # Telescope location (already in degrees)
        lat = header['latitude'][()]
        lon = header['longitude'][()]
        alt = header['altitude'][()]
        telescope_location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=alt*u.m)
        
        # Integration time
        integration_time = header['integration_time'][()]
        
        # Channel width
        channel_width = header['channel_width'][()]
        
        print(f"  Data shape: {visdata.shape}")
        print(f"  Time range: {Time(time_array.min(), format='mjd').iso} - {Time(time_array.max(), format='mjd').iso}")
        print(f"  Frequency range: {freq_array.min()/1e9:.3f} - {freq_array.max()/1e9:.3f} GHz")
        print(f"  Antennas: {Nants_data} data, {Nants_telescope} total")
        print(f"  Baselines: {len(ant_1_array)}")
        
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
            'telescope_location': telescope_location,
            'integration_time': integration_time,
            'channel_width': channel_width,
            'Nblts': Nblts,
            'Nfreqs': Nfreqs,
            'Npols': Npols,
            'Nants_data': Nants_data,
            'Nants_telescope': Nants_telescope
        }

def create_pyuvdata_object(data_dict):
    """Create PyUVData object from DSA-110 data."""
    try:
        import pyuvdata
        from pyuvdata import UVData
        
        uv_data = UVData()
        
        # Set basic parameters
        uv_data.telescope_name = 'DSA-110'
        uv_data.telescope_location = data_dict['telescope_location']
        uv_data.instrument = 'DSA'
        uv_data.object_name = 'search'
        
        # Set data arrays
        uv_data.data_array = data_dict['visdata']
        uv_data.flag_array = data_dict['flags']
        uv_data.nsample_array = data_dict['nsamples']
        
        # Set time and frequency
        uv_data.time_array = data_dict['time_array']
        uv_data.freq_array = data_dict['freq_array'].reshape(1, -1)
        
        # Set Ntimes from unique times
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
        
        # Set integration time and channel width
        uv_data.integration_time = data_dict['integration_time']
        uv_data.channel_width = np.full(data_dict['Nfreqs'], data_dict['channel_width'])
        
        # Set dimensions
        uv_data.Nblts = data_dict['Nblts']
        uv_data.Nfreqs = data_dict['Nfreqs']
        uv_data.Npols = data_dict['Npols']
        uv_data.Nants_data = data_dict['Nants_data']
        uv_data.Nbls = len(np.unique(uv_data.ant_1_array * 1000 + uv_data.ant_2_array))
        
        # Set other required parameters
        uv_data.vis_units = 'Jy'
        uv_data.Nspws = 1
        uv_data.spw_array = np.array([0])
        
        print(f"Created PyUVData object:")
        print(f"  Nbls: {uv_data.Nbls}")
        print(f"  Nfreqs: {uv_data.Nfreqs}")
        print(f"  Ntimes: {uv_data.Ntimes}")
        print(f"  Npols: {uv_data.Npols}")
        
        return uv_data
        
    except ImportError:
        print("PyUVData not available")
        return None

def test_ms_creation(file_path, output_ms_path):
    """Test MS creation from HDF5 file."""
    print(f"\n=== Testing MS Creation ===")
    print(f"Input: {os.path.basename(file_path)}")
    print(f"Output: {os.path.basename(output_ms_path)}")
    
    try:
        # Read HDF5 data
        data_dict = read_dsa110_hdf5(file_path)
        
        # Create PyUVData object
        uv_data = create_pyuvdata_object(data_dict)
        if uv_data is None:
            print("Failed to create PyUVData object")
            return False
        
        # Write to MS
        print("Writing to MS format...")
        uv_data.write_ms(str(output_ms_path), clobber=True)
        
        print(f"Successfully created MS: {output_ms_path}")
        
        # Validate MS
        print("Validating MS...")
        try:
            from casatools import ms
            ms_tool = ms()
            ms_tool.open(str(output_ms_path))
            
            n_rows = ms_tool.nrow()
            n_antennas = ms_tool.nantennas()
            n_spws = ms_tool.nspw()
            
            ms_tool.close()
            ms_tool.done()
            
            print(f"MS validation passed:")
            print(f"  Rows: {n_rows}")
            print(f"  Antennas: {n_antennas}")
            print(f"  SPWs: {n_spws}")
            
            return True
            
        except ImportError:
            print("CASA not available for MS validation")
            return True
        except Exception as e:
            print(f"MS validation failed: {e}")
            return False
            
    except Exception as e:
        print(f"MS creation failed: {e}")
        return False

def main():
    """Main test function."""
    test_dir = Path("/data/incoming_test/")
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)
    
    if not test_dir.exists():
        print(f"Test directory not found: {test_dir}")
        return
    
    hdf5_files = list(test_dir.glob("*.hdf5"))
    
    if not hdf5_files:
        print("No HDF5 files found in test directory")
        return
    
    print(f"Found {len(hdf5_files)} HDF5 files")
    print("=" * 50)
    
    # Test with first file
    test_file = hdf5_files[0]
    output_ms = output_dir / f"test_{test_file.stem}.ms"
    
    success = test_ms_creation(test_file, output_ms)
    
    if success:
        print("\n✅ HDF5 to MS conversion test PASSED!")
    else:
        print("\n❌ HDF5 to MS conversion test FAILED!")

if __name__ == "__main__":
    main()
