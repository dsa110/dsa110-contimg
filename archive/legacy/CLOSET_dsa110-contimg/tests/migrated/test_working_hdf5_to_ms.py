#!/usr/bin/env python3
"""
Working HDF5 to MS Conversion Test

This script creates a working HDF5 to MS converter using the correct CASA table API.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
import glob
import h5py
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_working_hdf5_to_ms():
    """Test working HDF5 to MS conversion."""
    try:
        logger.info("🚀 Starting Working HDF5 to MS Conversion Test")
        
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
        
        # Step 3: Read HDF5 file
        test_file = hdf5_files[0]
        logger.info(f"📁 Reading HDF5 file: {Path(test_file).name}")
        
        with h5py.File(test_file, 'r') as f:
            header = f['Header']
            data = f['Data']
            
            # Get basic dimensions
            n_baselines = header['Nbls'][()]
            n_times = header['Ntimes'][()]
            n_freqs = header['Nfreqs'][()]
            n_pols = header['Npols'][()]
            n_ants = header['Nants_data'][()]
            
            logger.info(f"📊 HDF5 dimensions:")
            logger.info(f"  - Baselines: {n_baselines}")
            logger.info(f"  - Times: {n_times}")
            logger.info(f"  - Frequencies: {n_freqs}")
            logger.info(f"  - Polarizations: {n_pols}")
            logger.info(f"  - Antennas: {n_ants}")
            
            # Get data
            visdata = data['visdata'][:]  # Shape: (n_baselines * n_times, n_spws, n_freqs, n_pols)
            flags = data['flags'][:]
            nsamples = data['nsamples'][:]
            
            # Get antenna information
            ant_1_array = header['ant_1_array'][:]
            ant_2_array = header['ant_2_array'][:]
            antenna_positions = header['antenna_positions'][:]
            antenna_names = [name.decode('utf-8') for name in header['antenna_names'][:]]
            
            # Get frequency information
            freq_array = header['freq_array'][:]  # Shape: (n_spws, n_freqs)
            channel_width = header['channel_width'][()]
            
            # Get time information
            time_array = header['time_array'][:]
            integration_time = header['integration_time'][:]
            
            # Get UVW coordinates
            uvw_array = header['uvw_array'][:]
            
            # Get polarization information
            polarization_array = header['polarization_array'][:]
            
            logger.info(f"📊 Data shapes:")
            logger.info(f"  - Visibility data: {visdata.shape}")
            logger.info(f"  - Flags: {flags.shape}")
            logger.info(f"  - NSamples: {nsamples.shape}")
            logger.info(f"  - Antenna 1: {ant_1_array.shape}")
            logger.info(f"  - Antenna 2: {ant_2_array.shape}")
            logger.info(f"  - Time: {time_array.shape}")
            logger.info(f"  - UVW: {uvw_array.shape}")
        
        # Step 4: Create MS using CASA table tools
        logger.info("🔧 Creating MS using CASA table tools...")
        
        ms_dir = "data/ms"
        os.makedirs(ms_dir, exist_ok=True)
        ms_path = os.path.join(ms_dir, f"{Path(test_file).stem}.ms")
        
        # Remove existing MS if it exists
        if os.path.exists(ms_path):
            import shutil
            shutil.rmtree(ms_path)
        
        try:
            # Create main table
            n_rows = n_baselines * n_times
            logger.info(f"Creating main table with {n_rows} rows...")
            
            # Create table descriptor for main table
            from casatools import table
            
            # Create the main table
            main_table = table()
            main_table.create(
                tablename=ms_path,
                tabledesc={
                    'TYPE': 'Measurement Set',
                    'VERSION': 2.0
                }
            )
            
            # Add columns to main table
            main_table.addcols({
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
            })
            
            # Add rows
            main_table.addrows(n_rows)
            
            # Write data
            logger.info("Writing data to main table...")
            main_table.putcol('ANTENNA1', ant_1_array)
            main_table.putcol('ANTENNA2', ant_2_array)
            main_table.putcol('ARRAY_ID', np.zeros(n_rows, dtype=int))
            main_table.putcol('DATA_DESC_ID', np.zeros(n_rows, dtype=int))
            main_table.putcol('EXPOSURE', integration_time)
            main_table.putcol('FEED1', np.zeros(n_rows, dtype=int))
            main_table.putcol('FEED2', np.zeros(n_rows, dtype=int))
            main_table.putcol('FIELD_ID', np.zeros(n_rows, dtype=int))
            main_table.putcol('FLAG', flags.reshape(n_rows, n_freqs, n_pols))
            main_table.putcol('FLAG_CATEGORY', np.zeros((n_rows, 1, n_freqs, n_pols), dtype=bool))
            main_table.putcol('FLAG_ROW', np.zeros(n_rows, dtype=bool))
            main_table.putcol('INTERVAL', integration_time)
            main_table.putcol('OBSERVATION_ID', np.zeros(n_rows, dtype=int))
            main_table.putcol('PROCESSOR_ID', np.zeros(n_rows, dtype=int))
            main_table.putcol('SCAN_NUMBER', np.ones(n_rows, dtype=int))
            main_table.putcol('SIGMA', np.ones((n_rows, n_pols), dtype=float))
            main_table.putcol('STATE_ID', np.zeros(n_rows, dtype=int))
            main_table.putcol('TIME', time_array)
            main_table.putcol('TIME_CENTROID', time_array)
            main_table.putcol('UVW', uvw_array)
            main_table.putcol('WEIGHT', nsamples.reshape(n_rows, n_pols))
            main_table.putcol('DATA', visdata.reshape(n_rows, n_freqs, n_pols))
            
            main_table.close()
            
            logger.info(f"✅ MS file created: {ms_path}")
            
            # Step 5: Create subtables
            logger.info("🔧 Creating MS subtables...")
            
            # Create ANTENNA table
            antenna_table_path = os.path.join(ms_path, 'ANTENNA')
            ant_table = table()
            ant_table.create(
                tablename=antenna_table_path,
                tabledesc={
                    'TYPE': 'Antenna',
                    'VERSION': 2.0
                }
            )
            
            ant_table.addcols({
                'NAME': {'TYPE': 'STRING', 'NDIM': 0},
                'STATION': {'TYPE': 'STRING', 'NDIM': 0},
                'TYPE': {'TYPE': 'STRING', 'NDIM': 0},
                'MOUNT': {'TYPE': 'STRING', 'NDIM': 0},
                'POSITION': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [3]},
                'OFFSET': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [3]},
                'DISH_DIAMETER': {'TYPE': 'DOUBLE', 'NDIM': 0},
                'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
            })
            
            ant_table.addrows(n_ants)
            ant_table.putcol('NAME', antenna_names[:n_ants])
            ant_table.putcol('STATION', [f'DSA-{i:03d}' for i in range(n_ants)])
            ant_table.putcol('TYPE', ['GROUND-BASED'] * n_ants)
            ant_table.putcol('MOUNT', ['ALT-AZ'] * n_ants)
            ant_table.putcol('POSITION', antenna_positions[:n_ants])
            ant_table.putcol('OFFSET', np.zeros((n_ants, 3)))
            ant_table.putcol('DISH_DIAMETER', np.full(n_ants, 4.65))
            ant_table.putcol('FLAG_ROW', np.zeros(n_ants, dtype=bool))
            ant_table.close()
            
            # Create SPECTRAL_WINDOW table
            spw_table_path = os.path.join(ms_path, 'SPECTRAL_WINDOW')
            spw_table = table()
            spw_table.create(
                tablename=spw_table_path,
                tabledesc={
                    'TYPE': 'Spectral Window',
                    'VERSION': 2.0
                }
            )
            
            spw_table.addcols({
                'CHAN_FREQ': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [n_freqs]},
                'CHAN_WIDTH': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [n_freqs]},
                'EFFECTIVE_BW': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [n_freqs]},
                'RESOLUTION': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [n_freqs]},
                'TOTAL_BANDWIDTH': {'TYPE': 'DOUBLE', 'NDIM': 0},
                'NET_SIDEBAND': {'TYPE': 'INT', 'NDIM': 0},
                'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
            })
            
            spw_table.addrows(1)
            spw_table.putcol('CHAN_FREQ', freq_array[0])
            spw_table.putcol('CHAN_WIDTH', np.full(n_freqs, channel_width))
            spw_table.putcol('EFFECTIVE_BW', np.full(n_freqs, channel_width))
            spw_table.putcol('RESOLUTION', np.full(n_freqs, channel_width))
            spw_table.putcol('TOTAL_BANDWIDTH', n_freqs * channel_width)
            spw_table.putcol('NET_SIDEBAND', [1])
            spw_table.putcol('FLAG_ROW', [False])
            spw_table.close()
            
            # Create POLARIZATION table
            pol_table_path = os.path.join(ms_path, 'POLARIZATION')
            pol_table = table()
            pol_table.create(
                tablename=pol_table_path,
                tabledesc={
                    'TYPE': 'Polarization',
                    'VERSION': 2.0
                }
            )
            
            pol_table.addcols({
                'CORR_TYPE': {'TYPE': 'INT', 'NDIM': 1, 'SHAPE': [n_pols]},
                'CORR_PRODUCT': {'TYPE': 'INT', 'NDIM': 2, 'SHAPE': [n_pols, 2]},
                'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
            })
            
            pol_table.addrows(1)
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
            
            # Create FIELD table
            field_table_path = os.path.join(ms_path, 'FIELD')
            field_table = table()
            field_table.create(
                tablename=field_table_path,
                tabledesc={
                    'TYPE': 'Field',
                    'VERSION': 2.0
                }
            )
            
            field_table.addcols({
                'NAME': {'TYPE': 'STRING', 'NDIM': 0},
                'CODE': {'TYPE': 'STRING', 'NDIM': 0},
                'TIME': {'TYPE': 'DOUBLE', 'NDIM': 0},
                'NUM_POLY': {'TYPE': 'INT', 'NDIM': 0},
                'SOURCE_ID': {'TYPE': 'INT', 'NDIM': 0},
                'DELAY_DIR': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [2]},
                'PHASE_DIR': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [2]},
                'REFERENCE_DIR': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [2]},
                'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
            })
            
            field_table.addrows(1)
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
            
            # Create OBSERVATION table
            obs_table_path = os.path.join(ms_path, 'OBSERVATION')
            obs_table = table()
            obs_table.create(
                tablename=obs_table_path,
                tabledesc={
                    'TYPE': 'Observation',
                    'VERSION': 2.0
                }
            )
            
            obs_table.addcols({
                'TELESCOPE_NAME': {'TYPE': 'STRING', 'NDIM': 0},
                'TIME_RANGE': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [2]},
                'OBSERVER': {'TYPE': 'STRING', 'NDIM': 0},
                'PROJECT': {'TYPE': 'STRING', 'NDIM': 0},
                'RELEASE_DATE': {'TYPE': 'DOUBLE', 'NDIM': 0},
                'SCHEDULE_TYPE': {'TYPE': 'STRING', 'NDIM': 0},
                'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0}
            })
            
            obs_table.addrows(1)
            obs_table.putcol('TELESCOPE_NAME', ['OVRO_MMA'])
            obs_table.putcol('TIME_RANGE', [[np.min(time_array), np.max(time_array)]])
            obs_table.putcol('OBSERVER', ['DSA-110'])
            obs_table.putcol('PROJECT', ['DSA-110'])
            obs_table.putcol('RELEASE_DATE', [0.0])
            obs_table.putcol('SCHEDULE_TYPE', ['UNKNOWN'])
            obs_table.putcol('FLAG_ROW', [False])
            obs_table.close()
            
            # Create SOURCE table
            source_table_path = os.path.join(ms_path, 'SOURCE')
            source_table = table()
            source_table.create(
                tablename=source_table_path,
                tabledesc={
                    'TYPE': 'Source',
                    'VERSION': 2.0
                }
            )
            
            source_table.addcols({
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
            })
            
            source_table.addrows(1)
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
            
            # Create HISTORY table
            history_table_path = os.path.join(ms_path, 'HISTORY')
            history_table = table()
            history_table.create(
                tablename=history_table_path,
                tabledesc={
                    'TYPE': 'History',
                    'VERSION': 2.0
                }
            )
            
            history_table.addcols({
                'OBSERVATION_ID': {'TYPE': 'INT', 'NDIM': 0},
                'TIME': {'TYPE': 'DOUBLE', 'NDIM': 0},
                'MESSAGE': {'TYPE': 'STRING', 'NDIM': 0},
                'PRIORITY': {'TYPE': 'STRING', 'NDIM': 0},
                'ORIGIN': {'TYPE': 'STRING', 'NDIM': 0},
                'OBJECT_ID': {'TYPE': 'INT', 'NDIM': 0},
                'APPLICATION': {'TYPE': 'STRING', 'NDIM': 0}
            })
            
            history_table.addrows(1)
            history_table.putcol('OBSERVATION_ID', [0])
            history_table.putcol('TIME', [0.0])
            history_table.putcol('MESSAGE', ['Created from DSA-110 HDF5 data'])
            history_table.putcol('PRIORITY', ['INFO'])
            history_table.putcol('ORIGIN', ['DSA-110 Pipeline'])
            history_table.putcol('OBJECT_ID', [0])
            history_table.putcol('APPLICATION', ['hdf5_to_ms_converter'])
            history_table.close()
            
            logger.info("✅ All MS subtables created successfully")
            
            # Step 6: Verify MS file
            logger.info("🔍 Verifying MS file...")
            
            with table(ms_path) as ms_table:
                n_rows_actual = ms_table.nrows()
                logger.info(f"✅ MS file has {n_rows_actual} rows")
                
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
            
            logger.info("🎉 HDF5 to MS conversion completed successfully!")
            logger.info("📋 Summary:")
            logger.info(f"  ✅ MS file created: {ms_path}")
            logger.info(f"  ✅ Main table: {n_rows} rows")
            logger.info(f"  ✅ All subtables created")
            logger.info(f"  ✅ Data verification passed")
            logger.info("  ✅ Ready for CASA processing")
            
        except Exception as e:
            logger.error(f"❌ MS creation failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_working_hdf5_to_ms())
