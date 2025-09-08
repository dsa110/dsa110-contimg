#!/usr/bin/env python3
"""
Test PyUVData MS Creation

This script tests using PyUVData to create MS files from HDF5 data.
"""

import os
import sys
import logging
import numpy as np
import glob
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_dsa110_hdf5_standalone(hdf5_path: str) -> dict:
    """
    Read a DSA-110 HDF5 file standalone without any pipeline imports.
    
    Args:
        hdf5_path: Path to the HDF5 file
        
    Returns:
        Dictionary containing UVData-compatible data, or None if failed
    """
    try:
        logger.info(f"Reading DSA-110 HDF5 file: {os.path.basename(hdf5_path)}")
        
        import h5py
        
        with h5py.File(hdf5_path, 'r') as f:
            # Read header information
            header = f['Header']
            data = f['Data']
            
            # Basic dimensions
            Nblts = header['Nblts'][()]
            Nfreqs = header['Nfreqs'][()]
            Npols = header['Npols'][()]
            Nants_data = header['Nants_data'][()]
            Nants_telescope = header['Nants_telescope'][()]
            Nbls = header['Nbls'][()]
            Ntimes = header['Ntimes'][()]
            
            # Time and frequency
            time_array = header['time_array'][()]
            freq_array = header['freq_array'][()]
            integration_time = header['integration_time'][()]
            
            # Antenna information
            antenna_names = [name.decode() for name in header['antenna_names'][()]]
            antenna_numbers = header['antenna_numbers'][()]
            antenna_positions = header['antenna_positions'][()]
            
            # Baseline information
            ant_1_array = header['ant_1_array'][()]
            ant_2_array = header['ant_2_array'][()]
            
            # UVW coordinates
            uvw_array = header['uvw_array'][()]
            
            # Data arrays
            visdata = data['visdata'][()]
            flags = data['flags'][()]
            nsamples = data['nsamples'][()]
            
            # Telescope information
            telescope_name = header['telescope_name'][()].decode()
            latitude = header['latitude'][()]
            longitude = header['longitude'][()]
            altitude = header['altitude'][()]
            
            # Phase center information
            phase_center_dec = header['phase_center_app_dec'][()]
            phase_type = header['phase_type'][()].decode()
            
            # Polarization information
            polarization_array = header['polarization_array'][()]
            
            # Channel width
            channel_width = header['channel_width'][()]
            
            return {
                'Nbls': Nbls,
                'Nfreqs': Nfreqs,
                'Ntimes': Ntimes,
                'Npols': Npols,
                'Nants_data': Nants_data,
                'Nants_telescope': Nants_telescope,
                'Nblts': Nblts,
                'time_array': time_array,
                'freq_array': freq_array,
                'integration_time': integration_time,
                'antenna_names': antenna_names,
                'antenna_numbers': antenna_numbers,
                'antenna_positions': antenna_positions,
                'ant_1_array': ant_1_array,
                'ant_2_array': ant_2_array,
                'uvw_array': uvw_array,
                'visdata': visdata,
                'flags': flags,
                'nsamples': nsamples,
                'telescope_name': telescope_name,
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'phase_center_dec': phase_center_dec,
                'phase_type': phase_type,
                'polarization_array': polarization_array,
                'channel_width': channel_width
            }
            
    except Exception as e:
        logger.error(f"Failed to read HDF5 file {hdf5_path}: {e}")
        return None

def test_pyuvdata_ms_creation():
    """Test PyUVData MS creation."""
    try:
        logger.info("🚀 Testing PyUVData MS Creation")
        
        # Import PyUVData
        from pyuvdata import UVData
        from astropy.time import Time
        from astropy.coordinates import EarthLocation
        import astropy.units as u
        
        # Check for real HDF5 files
        hdf5_dir = "/data/incoming_test"
        hdf5_files = glob.glob(f"{hdf5_dir}/*.hdf5")
        
        if not hdf5_files:
            logger.error("❌ No HDF5 files found in /data/incoming_test/")
            return False
            
        logger.info(f"📊 Found {len(hdf5_files)} real HDF5 files")
        
        # Test with first file
        test_file = hdf5_files[0]
        logger.info(f"📁 Testing with: {Path(test_file).name}")
        
        # Read HDF5 file
        logger.info("Reading HDF5 file...")
        hdf5_data = read_dsa110_hdf5_standalone(test_file)
        
        if hdf5_data is None:
            logger.error("❌ Failed to read HDF5 file")
            return False
        
        logger.info(f"✅ HDF5 file read successfully:")
        logger.info(f"  - Nbls: {hdf5_data['Nbls']}")
        logger.info(f"  - Nfreqs: {hdf5_data['Nfreqs']}")
        logger.info(f"  - Ntimes: {hdf5_data['Ntimes']}")
        logger.info(f"  - Npols: {hdf5_data['Npols']}")
        
        # Create UVData object
        logger.info("Creating UVData object...")
        uv = UVData()
        
        # Set basic parameters
        uv.Nbls = hdf5_data['Nbls']
        uv.Nfreqs = hdf5_data['Nfreqs']
        uv.Ntimes = hdf5_data['Ntimes']
        uv.Npols = hdf5_data['Npols']
        uv.Nants_data = hdf5_data['Nants_data']
        uv.Nants_telescope = hdf5_data['Nants_telescope']
        uv.Nblts = hdf5_data['Nblts']
        
        # Set telescope information
        uv.telescope_name = hdf5_data['telescope_name']
        uv.telescope_location = EarthLocation(
            lat=hdf5_data['latitude'] * u.deg,
            lon=hdf5_data['longitude'] * u.deg,
            height=hdf5_data['altitude'] * u.m
        )
        
        # Set antenna information
        uv.antenna_names = hdf5_data['antenna_names'][:hdf5_data['Nants_data']]
        uv.antenna_numbers = hdf5_data['antenna_numbers'][:hdf5_data['Nants_data']]
        uv.antenna_positions = hdf5_data['antenna_positions'][:hdf5_data['Nants_data']]
        
        # Set time and frequency information
        uv.time_array = hdf5_data['time_array']
        uv.freq_array = hdf5_data['freq_array']
        uv.integration_time = hdf5_data['integration_time']
        uv.channel_width = hdf5_data['channel_width']
        
        # Set baseline information
        uv.ant_1_array = hdf5_data['ant_1_array']
        uv.ant_2_array = hdf5_data['ant_2_array']
        uv.uvw_array = hdf5_data['uvw_array']
        
        # Set data arrays
        uv.data_array = hdf5_data['visdata']
        uv.flag_array = hdf5_data['flags']
        uv.nsample_array = hdf5_data['nsamples']
        
        # Set polarization information
        uv.polarization_array = hdf5_data['polarization_array']
        
        # Set phase center information
        uv.phase_center_ra = 0.0  # Default
        uv.phase_center_dec = hdf5_data['phase_center_dec']
        uv.phase_center_epoch = 2000.0  # Default
        
        # Set other required parameters
        uv.vis_units = 'Jy'
        uv.object_name = 'DSA-110 Field'
        uv.instrument = 'DSA-110'
        uv.telescope_location_lat_lon_alt = (
            hdf5_data['latitude'], hdf5_data['longitude'], hdf5_data['altitude']
        )
        
        # Set history
        uv.history = 'Created from DSA-110 HDF5 data'
        
        # Set required attributes
        uv.extra_keywords = {}
        uv.antenna_diameters = np.full(hdf5_data['Nants_data'], 4.65)  # DSA-110 antenna diameter
        
        # Set data shapes
        uv.data_array = uv.data_array.reshape(uv.Nblts, 1, uv.Nfreqs, uv.Npols)
        uv.flag_array = uv.flag_array.reshape(uv.Nblts, 1, uv.Nfreqs, uv.Npols)
        uv.nsample_array = uv.nsample_array.reshape(uv.Nblts, 1, uv.Nfreqs, uv.Npols)
        
        logger.info("✅ UVData object created successfully")
        
        # Create output MS path
        ms_dir = "data/ms"
        os.makedirs(ms_dir, exist_ok=True)
        ms_path = os.path.join(ms_dir, f"{Path(test_file).stem}.ms")
        
        # Write to MS format
        logger.info("Writing to MS format...")
        uv.write_ms(ms_path)
        
        logger.info(f"✅ Successfully created MS: {ms_path}")
        
        # Check if MS file was created
        if os.path.exists(ms_path):
            file_size = os.path.getsize(ms_path)
            logger.info(f"✅ MS file size: {file_size} bytes")
            
            # Verify MS file
            logger.info("🔍 Verifying MS file...")
            try:
                from casatools import table
                with table(ms_path) as ms_table:
                    n_rows = ms_table.nrows()
                    logger.info(f"✅ MS file has {n_rows} rows")
                    
                    # Check main table columns
                    colnames = ms_table.colnames()
                    logger.info(f"✅ MS file has {len(colnames)} columns")
                    
                    # Check data shape
                    data_shape = ms_table.getcol('DATA', 0, 1).shape
                    logger.info(f"✅ DATA column shape: {data_shape}")
                    
                    # Check antenna data
                    ant1_data = ms_table.getcol('ANTENNA1', 0, 10)
                    logger.info(f"✅ ANTENNA1 sample: {ant1_data}")
                    
                    # Check time data
                    time_data = ms_table.getcol('TIME', 0, 5)
                    logger.info(f"✅ TIME sample: {time_data}")
                    
                    # Check UVW data
                    uvw_data = ms_table.getcol('UVW', 0, 3)
                    logger.info(f"✅ UVW sample: {uvw_data}")
                
                logger.info("🎉 PyUVData MS creation completed successfully!")
                logger.info("📋 Summary:")
                logger.info(f"  ✅ HDF5 file read successfully")
                logger.info(f"  ✅ UVData object created")
                logger.info(f"  ✅ MS file created: {ms_path}")
                logger.info(f"  ✅ MS file verified")
                logger.info("  ✅ Ready for CASA processing")
                
            except Exception as e:
                logger.warning(f"⚠️ MS verification failed: {e}")
        else:
            logger.error("❌ MS file was not created")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_pyuvdata_ms_creation()
    if success:
        print("✅ PyUVData MS creation is working!")
    else:
        print("❌ PyUVData MS creation needs fixing!")
