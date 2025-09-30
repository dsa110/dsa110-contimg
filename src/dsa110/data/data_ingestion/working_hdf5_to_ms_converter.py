#!/usr/bin/env python3
"""
Working HDF5 to MS Converter

This module provides a working implementation for converting DSA-110 HDF5 files
to CASA Measurement Sets (MS) using the correct CASA table API.
"""

import os
import logging
import numpy as np
import h5py
from typing import Dict, Any, Optional, List
from pathlib import Path

from ...utils.logging import get_logger

logger = get_logger(__name__)


class WorkingHDF5ToMSConverter:
    """
    Working converter for DSA-110 HDF5 files to CASA Measurement Sets.
    
    This class provides a working implementation using the correct CASA table API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the HDF5 to MS converter.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.paths_config = config.get('paths', {})
        
        # Ensure output directory exists
        ms_dir = self.paths_config.get('ms_dir', 'data/ms')
        os.makedirs(ms_dir, exist_ok=True)
    
    async def convert_hdf5_to_ms(self, hdf5_path: str, output_ms_path: str) -> Dict[str, Any]:
        """
        Convert a single HDF5 file to MS format.
        
        Args:
            hdf5_path: Path to the input HDF5 file
            output_ms_path: Path for the output MS file
            
        Returns:
            Dictionary containing conversion results
        """
        logger.info(f"Converting HDF5 to MS: {Path(hdf5_path).name}")
        
        try:
            # Read HDF5 data
            hdf5_data = self._read_hdf5_file(hdf5_path)
            if not hdf5_data:
                return {'success': False, 'error': 'Failed to read HDF5 file'}
            
            # Create MS using CASA tools
            ms_result = await self._create_ms_with_casa(hdf5_data, output_ms_path)
            if not ms_result['success']:
                return ms_result
            
            logger.info(f"Successfully converted HDF5 to MS: {Path(output_ms_path).name}")
            return {
                'success': True,
                'ms_path': output_ms_path,
                'hdf5_path': hdf5_path,
                'n_baselines': hdf5_data['n_baselines'],
                'n_times': hdf5_data['n_times'],
                'n_freqs': hdf5_data['n_freqs'],
                'n_pols': hdf5_data['n_pols']
            }
            
        except Exception as e:
            logger.error(f"HDF5 to MS conversion failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _read_hdf5_file(self, hdf5_path: str) -> Optional[Dict[str, Any]]:
        """
        Read and parse HDF5 file data.
        
        Args:
            hdf5_path: Path to the HDF5 file
            
        Returns:
            Dictionary containing parsed HDF5 data, or None if failed
        """
        try:
            with h5py.File(hdf5_path, 'r') as f:
                # Read header information
                header = f['Header']
                data = f['Data']
                
                # Extract basic dimensions
                n_baselines = header['Nbls'][()]
                n_times = header['Ntimes'][()]
                n_freqs = header['Nfreqs'][()]
                n_pols = header['Npols'][()]
                n_ants = header['Nants_data'][()]
                
                # Extract antenna information
                ant_1_array = header['ant_1_array'][:]
                ant_2_array = header['ant_2_array'][:]
                antenna_positions = header['antenna_positions'][:]
                antenna_names = [name.decode('utf-8') for name in header['antenna_names'][:]]
                antenna_numbers = header['antenna_numbers'][:]
                
                # Extract frequency information
                freq_array = header['freq_array'][:]  # Shape: (n_spws, n_freqs)
                channel_width = header['channel_width'][()]
                
                # Extract time information
                time_array = header['time_array'][:]
                integration_time = header['integration_time'][:]
                
                # Extract UVW coordinates
                uvw_array = header['uvw_array'][:]  # Shape: (n_baselines * n_times, 3)
                
                # Extract visibility data
                visdata = data['visdata'][:]  # Shape: (n_baselines * n_times, n_spws, n_freqs, n_pols)
                flags = data['flags'][:]
                nsamples = data['nsamples'][:]
                
                # Extract telescope information
                telescope_name = header['telescope_name'][()].decode('utf-8')
                latitude = header['latitude'][()]
                longitude = header['longitude'][()]
                altitude = header['altitude'][()]
                
                # Extract phase center information
                phase_center_dec = header['phase_center_app_dec'][()]
                # Convert from radians to degrees (DSA-110 HDF5 stores in radians)
                if abs(phase_center_dec) < 10.0:  # Likely radians if < 10 degrees
                    phase_center_dec = np.degrees(phase_center_dec)
                phase_type = header['phase_type'][()].decode('utf-8')
                
                # Extract polarization information
                polarization_array = header['polarization_array'][:]
                
                # Extract spectral window information
                spw_array = header['spw_array'][:]
                
                return {
                    'n_baselines': n_baselines,
                    'n_times': n_times,
                    'n_freqs': n_freqs,
                    'n_pols': n_pols,
                    'n_ants': n_ants,
                    'n_spws': len(spw_array),
                    'ant_1_array': ant_1_array,
                    'ant_2_array': ant_2_array,
                    'antenna_positions': antenna_positions,
                    'antenna_names': antenna_names,
                    'antenna_numbers': antenna_numbers,
                    'freq_array': freq_array,
                    'channel_width': channel_width,
                    'time_array': time_array,
                    'integration_time': integration_time,
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
                    'spw_array': spw_array
                }
                
        except Exception as e:
            logger.error(f"Failed to read HDF5 file {hdf5_path}: {e}")
            return None
    
    async def _create_ms_with_casa(self, hdf5_data: Dict[str, Any], ms_path: str) -> Dict[str, Any]:
        """
        Create MS using CASA tools with proper table structure.
        
        Args:
            hdf5_data: Parsed HDF5 data
            ms_path: Path for the output MS file
            
        Returns:
            Dictionary containing creation results
        """
        try:
            from casatools import table
            
            # Remove existing MS if it exists
            if os.path.exists(ms_path):
                import shutil
                shutil.rmtree(ms_path)
            
            # Get dimensions
            n_baselines = hdf5_data['n_baselines']
            n_times = hdf5_data['n_times']
            n_freqs = hdf5_data['n_freqs']
            n_pols = hdf5_data['n_pols']
            n_ants = hdf5_data['n_ants']
            n_spws = hdf5_data['n_spws']
            n_rows = n_baselines * n_times
            
            # Create MS directory
            os.makedirs(ms_path, exist_ok=True)
            
            # Create main table
            main_table_path = os.path.join(ms_path, "MAIN")
            main_table = table()
            
            # Create table descriptor using the correct CASA format
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
            await self._create_antenna_table(ms_path, hdf5_data)
            await self._create_spectral_window_table(ms_path, hdf5_data)
            await self._create_polarization_table(ms_path, hdf5_data)
            await self._create_field_table(ms_path, hdf5_data)
            await self._create_observation_table(ms_path, hdf5_data)
            await self._create_source_table(ms_path, hdf5_data)
            await self._create_history_table(ms_path, hdf5_data)
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to create MS with CASA: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _create_antenna_table(self, ms_path: str, hdf5_data: Dict[str, Any]):
        """Create the antenna table."""
        try:
            from casatools import table
            
            antenna_table_path = os.path.join(ms_path, 'ANTENNA')
            ant_table = table()
            
            n_ants = hdf5_data['n_ants']
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
    
    async def _create_spectral_window_table(self, ms_path: str, hdf5_data: Dict[str, Any]):
        """Create the spectral window table."""
        try:
            from casatools import table
            
            spw_table_path = os.path.join(ms_path, 'SPECTRAL_WINDOW')
            spw_table = table()
            
            n_freqs = hdf5_data['n_freqs']
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
    
    async def _create_polarization_table(self, ms_path: str, hdf5_data: Dict[str, Any]):
        """Create the polarization table."""
        try:
            from casatools import table
            
            pol_table_path = os.path.join(ms_path, 'POLARIZATION')
            pol_table = table()
            
            n_pols = hdf5_data['n_pols']
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
    
    async def _create_field_table(self, ms_path: str, hdf5_data: Dict[str, Any]):
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
            # Use actual phase center coordinates (RA=0 for drift scan, Dec from HDF5)
            field_table.putcol('PHASE_DIR', [[0.0, hdf5_data['phase_center_dec']]])
            field_table.putcol('REFERENCE_DIR', [[0.0, hdf5_data['phase_center_dec']]])
            field_table.putcol('FLAG_ROW', [False])
            field_table.close()
            
        except Exception as e:
            logger.error(f"Failed to create field table: {e}")
            raise
    
    async def _create_observation_table(self, ms_path: str, hdf5_data: Dict[str, Any]):
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
    
    async def _create_source_table(self, ms_path: str, hdf5_data: Dict[str, Any]):
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
    
    async def _create_history_table(self, ms_path: str, hdf5_data: Dict[str, Any]):
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
