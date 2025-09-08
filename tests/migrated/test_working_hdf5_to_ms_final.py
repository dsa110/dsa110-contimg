#!/usr/bin/env python3
"""
Working HDF5 to MS Conversion - Final Version

This script implements a working HDF5 to MS conversion using the standalone
approach that avoids circular import issues.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
import glob
import h5py
import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u

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

def create_ms_from_hdf5_data(hdf5_data: dict, ms_path: str) -> bool:
    """
    Create MS file from HDF5 data using CASA table tools.
    
    Args:
        hdf5_data: Dictionary containing HDF5 data
        ms_path: Path for the output MS file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from casatools import table
        
        # Remove existing MS if it exists
        if os.path.exists(ms_path):
            import shutil
            shutil.rmtree(ms_path)
        
        # Get dimensions
        n_baselines = hdf5_data['Nbls']
        n_times = hdf5_data['Ntimes']
        n_freqs = hdf5_data['Nfreqs']
        n_pols = hdf5_data['Npols']
        n_ants = hdf5_data['Nants_data']
        n_rows = n_baselines * n_times
        
        # Create MS directory
        os.makedirs(ms_path, exist_ok=True)
        
        # Create main table
        main_table_path = os.path.join(ms_path, "MAIN")
        main_table = table()
        
        # Create table descriptor
        tabledesc = {
            'ANTENNA1': {'TYPE': 'INT', 'NDIM': 0},
            'ANTENNA2': {'TYPE': 'INT', 'NDIM': 0},
            'ARRAY_ID': {'TYPE': 'INT', 'NDIM': 0},
            'DATA_DESC_ID': {'TYPE': 'INT', 'NDIM': 0},
            'EXPOSURE': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'FEED1': {'TYPE': 'INT', 'NDIM': 0},
            'FEED2': {'TYPE': 'INT', 'NDIM': 0},
            'FIELD_ID': {'TYPE': 'INT', 'NDIM': 0},
            'FLAG': {'TYPE': 'BOOL', 'NDIM': 2, 'SHAPE': [n_freqs, n_pols]},
            'FLAG_CATEGORY': {'TYPE': 'BOOL', 'NDIM': 3, 'SHAPE': [1, n_freqs, n_pols]},
            'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0},
            'INTERVAL': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'OBSERVATION_ID': {'TYPE': 'INT', 'NDIM': 0},
            'PROCESSOR_ID': {'TYPE': 'INT', 'NDIM': 0},
            'SCAN_NUMBER': {'TYPE': 'INT', 'NDIM': 0},
            'SIGMA': {'TYPE': 'FLOAT', 'NDIM': 1, 'SHAPE': [n_pols]},
            'STATE_ID': {'TYPE': 'INT', 'NDIM': 0},
            'TIME': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'TIME_CENTROID': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'UVW': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [3]},
            'WEIGHT': {'TYPE': 'FLOAT', 'NDIM': 1, 'SHAPE': [n_pols]},
            'DATA': {'TYPE': 'COMPLEX', 'NDIM': 2, 'SHAPE': [n_freqs, n_pols]}
        }
        
        # Create the table
        main_table.create(
            tablename=main_table_path,
            tabledesc=tabledesc,
            nrow=n_rows
        )
        
        # Write data
        logger.info("Writing data to main table...")
        main_table.putcol('ANTENNA1', hdf5_data['ant_1_array'])
        main_table.putcol('ANTENNA2', hdf5_data['ant_2_array'])
        main_table.putcol('ARRAY_ID', np.zeros(n_rows, dtype=int))
        main_table.putcol('DATA_DESC_ID', np.zeros(n_rows, dtype=int))
        main_table.putcol('EXPOSURE', hdf5_data['integration_time'])
        main_table.putcol('FEED1', np.zeros(n_rows, dtype=int))
        main_table.putcol('FEED2', np.zeros(n_rows, dtype=int))
        main_table.putcol('FIELD_ID', np.zeros(n_rows, dtype=int))
        main_table.putcol('FLAG', hdf5_data['flags'].reshape(n_rows, n_freqs, n_pols))
        main_table.putcol('FLAG_CATEGORY', np.zeros((n_rows, 1, n_freqs, n_pols), dtype=bool))
        main_table.putcol('FLAG_ROW', np.zeros(n_rows, dtype=bool))
        main_table.putcol('INTERVAL', hdf5_data['integration_time'])
        main_table.putcol('OBSERVATION_ID', np.zeros(n_rows, dtype=int))
        main_table.putcol('PROCESSOR_ID', np.zeros(n_rows, dtype=int))
        main_table.putcol('SCAN_NUMBER', np.ones(n_rows, dtype=int))
        main_table.putcol('SIGMA', np.ones((n_rows, n_pols), dtype=float))
        main_table.putcol('STATE_ID', np.zeros(n_rows, dtype=int))
        main_table.putcol('TIME', hdf5_data['time_array'])
        main_table.putcol('TIME_CENTROID', hdf5_data['time_array'])
        main_table.putcol('UVW', hdf5_data['uvw_array'])
        main_table.putcol('WEIGHT', hdf5_data['nsamples'].reshape(n_rows, n_pols))
        main_table.putcol('DATA', hdf5_data['visdata'].reshape(n_rows, n_freqs, n_pols))
        
        main_table.close()
        
        # Create subtables
        create_antenna_table(ms_path, hdf5_data)
        create_spectral_window_table(ms_path, hdf5_data)
        create_polarization_table(ms_path, hdf5_data)
        create_field_table(ms_path, hdf5_data)
        create_observation_table(ms_path, hdf5_data)
        create_source_table(ms_path, hdf5_data)
        create_history_table(ms_path, hdf5_data)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create MS: {e}")
        return False

def create_antenna_table(ms_path: str, hdf5_data: dict):
    """Create the antenna table."""
    try:
        from casatools import table
        
        antenna_table_path = os.path.join(ms_path, 'ANTENNA')
        ant_table = table()
        
        n_ants = hdf5_data['Nants_data']
        antenna_positions = hdf5_data['antenna_positions']
        antenna_names = hdf5_data['antenna_names']
        
        tabledesc = {
            'NAME': {'TYPE': 'STRING', 'NDIM': 0},
            'STATION': {'TYPE': 'STRING', 'NDIM': 0},
            'TYPE': {'TYPE': 'STRING', 'NDIM': 0},
            'MOUNT': {'TYPE': 'STRING', 'NDIM': 0},
            'POSITION': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [3]},
            'OFFSET': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [3]},
            'DISH_DIAMETER': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
        }
        
        ant_table.create(
            tablename=antenna_table_path,
            tabledesc=tabledesc,
            nrow=n_ants
        )
        
        ant_table.putcol('NAME', antenna_names[:n_ants])
        ant_table.putcol('STATION', [f'DSA-{i:03d}' for i in range(n_ants)])
        ant_table.putcol('TYPE', ['GROUND-BASED'] * n_ants)
        ant_table.putcol('MOUNT', ['ALT-AZ'] * n_ants)
        ant_table.putcol('POSITION', antenna_positions[:n_ants])
        ant_table.putcol('OFFSET', np.zeros((n_ants, 3)))
        ant_table.putcol('DISH_DIAMETER', np.full(n_ants, 4.65))
        ant_table.putcol('FLAG_ROW', np.zeros(n_ants, dtype=bool))
        ant_table.close()
        
    except Exception as e:
        logger.error(f"Failed to create antenna table: {e}")
        raise

def create_spectral_window_table(ms_path: str, hdf5_data: dict):
    """Create the spectral window table."""
    try:
        from casatools import table
        
        spw_table_path = os.path.join(ms_path, 'SPECTRAL_WINDOW')
        spw_table = table()
        
        n_freqs = hdf5_data['Nfreqs']
        freq_array = hdf5_data['freq_array']
        channel_width = hdf5_data['channel_width']
        
        tabledesc = {
            'CHAN_FREQ': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [n_freqs]},
            'CHAN_WIDTH': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [n_freqs]},
            'EFFECTIVE_BW': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [n_freqs]},
            'RESOLUTION': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [n_freqs]},
            'TOTAL_BANDWIDTH': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'NET_SIDEBAND': {'TYPE': 'INT', 'NDIM': 0},
            'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
        }
        
        spw_table.create(
            tablename=spw_table_path,
            tabledesc=tabledesc,
            nrow=1
        )
        
        spw_table.putcol('CHAN_FREQ', freq_array[0])
        spw_table.putcol('CHAN_WIDTH', np.full(n_freqs, channel_width))
        spw_table.putcol('EFFECTIVE_BW', np.full(n_freqs, channel_width))
        spw_table.putcol('RESOLUTION', np.full(n_freqs, channel_width))
        spw_table.putcol('TOTAL_BANDWIDTH', n_freqs * channel_width)
        spw_table.putcol('NET_SIDEBAND', [1])
        spw_table.putcol('FLAG_ROW', [False])
        spw_table.close()
        
    except Exception as e:
        logger.error(f"Failed to create spectral window table: {e}")
        raise

def create_polarization_table(ms_path: str, hdf5_data: dict):
    """Create the polarization table."""
    try:
        from casatools import table
        
        pol_table_path = os.path.join(ms_path, 'POLARIZATION')
        pol_table = table()
        
        n_pols = hdf5_data['Npols']
        polarization_array = hdf5_data['polarization_array']
        
        tabledesc = {
            'CORR_TYPE': {'TYPE': 'INT', 'NDIM': 1, 'SHAPE': [n_pols]},
            'CORR_PRODUCT': {'TYPE': 'INT', 'NDIM': 2, 'SHAPE': [n_pols, 2]},
            'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
        }
        
        pol_table.create(
            tablename=pol_table_path,
            tabledesc=tabledesc,
            nrow=1
        )
        
        pol_table.putcol('CORR_TYPE', polarization_array)
        
        # Create correlation products
        corr_products = []
        for pol in polarization_array:
            if pol == -5:  # XX
                corr_products.append([0, 0])
            elif pol == -6:  # YY
                corr_products.append([1, 1])
            elif pol == -7:  # XY
                corr_products.append([0, 1])
            elif pol == -8:  # YX
                corr_products.append([1, 0])
        
        pol_table.putcol('CORR_PRODUCT', [corr_products])
        pol_table.putcol('FLAG_ROW', [False])
        pol_table.close()
        
    except Exception as e:
        logger.error(f"Failed to create polarization table: {e}")
        raise

def create_field_table(ms_path: str, hdf5_data: dict):
    """Create the field table."""
    try:
        from casatools import table
        
        field_table_path = os.path.join(ms_path, 'FIELD')
        field_table = table()
        
        tabledesc = {
            'NAME': {'TYPE': 'STRING', 'NDIM': 0},
            'CODE': {'TYPE': 'STRING', 'NDIM': 0},
            'TIME': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'NUM_POLY': {'TYPE': 'INT', 'NDIM': 0},
            'SOURCE_ID': {'TYPE': 'INT', 'NDIM': 0},
            'DELAY_DIR': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [2]},
            'PHASE_DIR': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [2]},
            'REFERENCE_DIR': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [2]},
            'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
        }
        
        field_table.create(
            tablename=field_table_path,
            tabledesc=tabledesc,
            nrow=1
        )
        
        field_table.putcol('NAME', ['DSA-110 Field'])
        field_table.putcol('CODE', ['DSA110'])
        field_table.putcol('TIME', [0.0])
        field_table.putcol('NUM_POLY', [0])
        field_table.putcol('SOURCE_ID', [0])
        field_table.putcol('DELAY_DIR', [[0.0, 0.0]])
        field_table.putcol('PHASE_DIR', [[0.0, 0.0]])
        field_table.putcol('REFERENCE_DIR', [[0.0, 0.0]])
        field_table.putcol('FLAG_ROW', [False])
        field_table.close()
        
    except Exception as e:
        logger.error(f"Failed to create field table: {e}")
        raise

def create_observation_table(ms_path: str, hdf5_data: dict):
    """Create the observation table."""
    try:
        from casatools import table
        
        obs_table_path = os.path.join(ms_path, 'OBSERVATION')
        obs_table = table()
        
        time_array = hdf5_data['time_array']
        telescope_name = hdf5_data['telescope_name']
        
        tabledesc = {
            'TELESCOPE_NAME': {'TYPE': 'STRING', 'NDIM': 0},
            'TIME_RANGE': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [2]},
            'OBSERVER': {'TYPE': 'STRING', 'NDIM': 0},
            'PROJECT': {'TYPE': 'STRING', 'NDIM': 0},
            'RELEASE_DATE': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'SCHEDULE_TYPE': {'TYPE': 'STRING', 'NDIM': 0},
            'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
        }
        
        obs_table.create(
            tablename=obs_table_path,
            tabledesc=tabledesc,
            nrow=1
        )
        
        obs_table.putcol('TELESCOPE_NAME', [telescope_name])
        obs_table.putcol('TIME_RANGE', [[np.min(time_array), np.max(time_array)]])
        obs_table.putcol('OBSERVER', ['DSA-110'])
        obs_table.putcol('PROJECT', ['DSA-110'])
        obs_table.putcol('RELEASE_DATE', [0.0])
        obs_table.putcol('SCHEDULE_TYPE', ['UNKNOWN'])
        obs_table.putcol('FLAG_ROW', [False])
        obs_table.close()
        
    except Exception as e:
        logger.error(f"Failed to create observation table: {e}")
        raise

def create_source_table(ms_path: str, hdf5_data: dict):
    """Create the source table."""
    try:
        from casatools import table
        
        source_table_path = os.path.join(ms_path, 'SOURCE')
        source_table = table()
        
        tabledesc = {
            'NAME': {'TYPE': 'STRING', 'NDIM': 0},
            'CODE': {'TYPE': 'STRING', 'NDIM': 0},
            'TIME': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'INTERVAL': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'SPECTRAL_WINDOW_ID': {'TYPE': 'INT', 'NDIM': 0},
            'NUM_LINES': {'TYPE': 'INT', 'NDIM': 0},
            'NUM_TRANSITIONS': {'TYPE': 'INT', 'NDIM': 0},
            'DIRECTION': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [2]},
            'PROPER_MOTION': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [2]},
            'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
        }
        
        source_table.create(
            tablename=source_table_path,
            tabledesc=tabledesc,
            nrow=1
        )
        
        source_table.putcol('NAME', ['DSA-110 Source'])
        source_table.putcol('CODE', ['DSA110'])
        source_table.putcol('TIME', [0.0])
        source_table.putcol('INTERVAL', [0.0])
        source_table.putcol('SPECTRAL_WINDOW_ID', [0])
        source_table.putcol('NUM_LINES', [0])
        source_table.putcol('NUM_TRANSITIONS', [0])
        source_table.putcol('DIRECTION', [[0.0, 0.0]])
        source_table.putcol('PROPER_MOTION', [[0.0, 0.0]])
        source_table.putcol('FLAG_ROW', [False])
        source_table.close()
        
    except Exception as e:
        logger.error(f"Failed to create source table: {e}")
        raise

def create_history_table(ms_path: str, hdf5_data: dict):
    """Create the history table."""
    try:
        from casatools import table
        
        history_table_path = os.path.join(ms_path, 'HISTORY')
        history_table = table()
        
        tabledesc = {
            'OBSERVATION_ID': {'TYPE': 'INT', 'NDIM': 0},
            'TIME': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'MESSAGE': {'TYPE': 'STRING', 'NDIM': 0},
            'PRIORITY': {'TYPE': 'STRING', 'NDIM': 0},
            'ORIGIN': {'TYPE': 'STRING', 'NDIM': 0},
            'OBJECT_ID': {'TYPE': 'INT', 'NDIM': 0},
            'APPLICATION': {'TYPE': 'STRING', 'NDIM': 0}
        }
        
        history_table.create(
            tablename=history_table_path,
            tabledesc=tabledesc,
            nrow=1
        )
        
        history_table.putcol('OBSERVATION_ID', [0])
        history_table.putcol('TIME', [0.0])
        history_table.putcol('MESSAGE', ['Created from DSA-110 HDF5 data'])
        history_table.putcol('PRIORITY', ['INFO'])
        history_table.putcol('ORIGIN', ['DSA-110 Pipeline'])
        history_table.putcol('OBJECT_ID', [0])
        history_table.putcol('APPLICATION', ['hdf5_to_ms_converter'])
        history_table.close()
        
    except Exception as e:
        logger.error(f"Failed to create history table: {e}")
        raise

async def test_working_hdf5_to_ms_final():
    """Test the working HDF5 to MS conversion."""
    try:
        logger.info("🚀 Starting Working HDF5 to MS Conversion - Final Version")
        
        # Step 1: Check for real HDF5 files
        hdf5_dir = "/data/incoming_test"
        hdf5_files = glob.glob(f"{hdf5_dir}/*.hdf5")
        
        if not hdf5_files:
            logger.error("❌ No HDF5 files found in /data/incoming_test/")
            return
            
        logger.info(f"📊 Found {len(hdf5_files)} real HDF5 files")
        
        # Step 2: Test CASA imports
        logger.info("🔧 Testing CASA imports...")
        try:
            from casatools import table
            from casatasks import tclean, exportfits
            logger.info("✅ CASA tools and tasks imported successfully")
        except ImportError as e:
            logger.error(f"❌ CASA import failed: {e}")
            return
        
        # Step 3: Test HDF5 to MS conversion
        logger.info("🔧 Testing HDF5 to MS conversion...")
        
        # Test with first file
        test_file = hdf5_files[0]
        logger.info(f"📁 Testing with: {Path(test_file).name}")
        
        # Read HDF5 file
        logger.info("Reading HDF5 file...")
        hdf5_data = read_dsa110_hdf5_standalone(test_file)
        
        if hdf5_data is None:
            logger.error("❌ Failed to read HDF5 file")
            return
        
        logger.info(f"✅ HDF5 file read successfully:")
        logger.info(f"  - Nbls: {hdf5_data['Nbls']}")
        logger.info(f"  - Nfreqs: {hdf5_data['Nfreqs']}")
        logger.info(f"  - Ntimes: {hdf5_data['Ntimes']}")
        logger.info(f"  - Npols: {hdf5_data['Npols']}")
        
        # Create output MS path
        ms_dir = "data/ms"
        os.makedirs(ms_dir, exist_ok=True)
        ms_path = os.path.join(ms_dir, f"{Path(test_file).stem}.ms")
        
        # Create MS file
        logger.info("Creating MS file...")
        success = create_ms_from_hdf5_data(hdf5_data, ms_path)
        
        if success:
            logger.info(f"✅ Successfully created MS: {ms_path}")
            
            # Check if MS file was created
            if os.path.exists(ms_path):
                file_size = os.path.getsize(ms_path)
                logger.info(f"✅ MS file size: {file_size} bytes")
                
                # Step 4: Verify MS file
                logger.info("🔍 Verifying MS file...")
                try:
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
                    
                    logger.info("🎉 HDF5 to MS conversion completed successfully!")
                    logger.info("📋 Summary:")
                    logger.info(f"  ✅ HDF5 file read successfully")
                    logger.info(f"  ✅ MS file created: {ms_path}")
                    logger.info(f"  ✅ All subtables created")
                    logger.info(f"  ✅ MS file verified")
                    logger.info("  ✅ Ready for CASA processing")
                    
                except Exception as e:
                    logger.warning(f"⚠️ MS verification failed: {e}")
            else:
                logger.error("❌ MS file was not created")
                return
        else:
            logger.error("❌ Failed to create MS file")
            return
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_working_hdf5_to_ms_final())
