#!/usr/bin/env python3
"""
HDF5 to Measurement Set (MS) Converter

This module converts DSA-110 HDF5 files to CASA Measurement Sets (MS).
It handles the specific format used by the DSA-110 telescope array.
"""

import os
import logging
import numpy as np
import h5py
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u

from ...utils.logging import get_logger

logger = get_logger(__name__)


class HDF5ToMSConverter:
    """
    Converts DSA-110 HDF5 files to CASA Measurement Sets.
    
    This class handles the specific HDF5 format used by DSA-110 and
    creates properly formatted MS files for CASA processing.
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
            
            # Create MS structure
            ms_result = await self._create_ms_structure(hdf5_data, output_ms_path)
            if not ms_result['success']:
                return ms_result
            
            # Write MS data
            write_result = await self._write_ms_data(hdf5_data, output_ms_path)
            if not write_result['success']:
                return write_result
            
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
    
    async def _create_ms_structure(self, hdf5_data: Dict[str, Any], ms_path: str) -> Dict[str, Any]:
        """
        Create the basic MS structure using CASA tools.
        
        Args:
            hdf5_data: Parsed HDF5 data
            ms_path: Path for the output MS file
            
        Returns:
            Dictionary containing creation results
        """
        try:
            from casatools import ms
            
            # Create MS tool
            ms_tool = ms()
            
            # Get dimensions
            n_baselines = hdf5_data['n_baselines']
            n_times = hdf5_data['n_times']
            n_freqs = hdf5_data['n_freqs']
            n_pols = hdf5_data['n_pols']
            n_ants = hdf5_data['n_ants']
            n_spws = hdf5_data['n_spws']
            
            # Calculate total number of rows
            n_rows = n_baselines * n_times
            
            # Create MS
            ms_tool.create(
                msname=ms_path,
                nrow=n_rows,
                nspw=n_spws,
                nchan=n_freqs,
                ncorr=n_pols,
                nant=n_ants
            )
            
            # Set up main table columns
            self._setup_main_table(ms_tool, hdf5_data)
            
            # Set up antenna table
            self._setup_antenna_table(ms_tool, hdf5_data)
            
            # Set up spectral window table
            self._setup_spectral_window_table(ms_tool, hdf5_data)
            
            # Set up polarization table
            self._setup_polarization_table(ms_tool, hdf5_data)
            
            # Set up field table
            self._setup_field_table(ms_tool, hdf5_data)
            
            # Set up observation table
            self._setup_observation_table(ms_tool, hdf5_data)
            
            # Set up source table
            self._setup_source_table(ms_tool, hdf5_data)
            
            # Set up history table
            self._setup_history_table(ms_tool, hdf5_data)
            
            ms_tool.close()
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to create MS structure: {e}")
            return {'success': False, 'error': str(e)}
    
    def _setup_main_table(self, ms_tool, hdf5_data: Dict[str, Any]):
        """Set up the main MS table with visibility data."""
        # This is a simplified version - in practice, you'd use CASA table tools
        # to properly set up all the required columns
        pass
    
    def _setup_antenna_table(self, ms_tool, hdf5_data: Dict[str, Any]):
        """Set up the antenna table."""
        # Set up antenna positions, names, etc.
        pass
    
    def _setup_spectral_window_table(self, ms_tool, hdf5_data: Dict[str, Any]):
        """Set up the spectral window table."""
        # Set up frequency information
        pass
    
    def _setup_polarization_table(self, ms_tool, hdf5_data: Dict[str, Any]):
        """Set up the polarization table."""
        # Set up polarization information
        pass
    
    def _setup_field_table(self, ms_tool, hdf5_data: Dict[str, Any]):
        """Set up the field table."""
        # Set up field information
        pass
    
    def _setup_observation_table(self, ms_tool, hdf5_data: Dict[str, Any]):
        """Set up the observation table."""
        # Set up observation information
        pass
    
    def _setup_source_table(self, ms_tool, hdf5_data: Dict[str, Any]):
        """Set up the source table."""
        # Set up source information
        pass
    
    def _setup_history_table(self, ms_tool, hdf5_data: Dict[str, Any]):
        """Set up the history table."""
        # Set up history information
        pass
    
    async def _write_ms_data(self, hdf5_data: Dict[str, Any], ms_path: str) -> Dict[str, Any]:
        """
        Write the actual visibility data to the MS.
        
        Args:
            hdf5_data: Parsed HDF5 data
            ms_path: Path to the MS file
            
        Returns:
            Dictionary containing write results
        """
        try:
            from casatools import table
            
            # Open the main table
            with table(ms_path, readonly=False) as main_table:
                # Write visibility data
                main_table.putcol('DATA', hdf5_data['visdata'])
                main_table.putcol('FLAG', hdf5_data['flags'])
                main_table.putcol('WEIGHT', hdf5_data['nsamples'])
                
                # Write antenna information
                main_table.putcol('ANTENNA1', hdf5_data['ant_1_array'])
                main_table.putcol('ANTENNA2', hdf5_data['ant_2_array'])
                
                # Write time information
                main_table.putcol('TIME', hdf5_data['time_array'])
                main_table.putcol('INTERVAL', hdf5_data['integration_time'])
                
                # Write UVW coordinates
                main_table.putcol('UVW', hdf5_data['uvw_array'])
                
                # Write spectral window information
                main_table.putcol('SPECTRAL_WINDOW_ID', np.zeros(len(hdf5_data['time_array']), dtype=int))
                
                # Write field information
                main_table.putcol('FIELD_ID', np.zeros(len(hdf5_data['time_array']), dtype=int))
                
                # Write scan information
                main_table.putcol('SCAN_NUMBER', np.ones(len(hdf5_data['time_array']), dtype=int))
                
                # Write array information
                main_table.putcol('ARRAY_ID', np.zeros(len(hdf5_data['time_array']), dtype=int))
                
                # Write observation information
                main_table.putcol('OBSERVATION_ID', np.zeros(len(hdf5_data['time_array']), dtype=int))
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to write MS data: {e}")
            return {'success': False, 'error': str(e)}
    
    async def convert_multiple_hdf5_files(self, hdf5_files: List[str], 
                                        output_dir: str) -> Dict[str, Any]:
        """
        Convert multiple HDF5 files to MS format.
        
        Args:
            hdf5_files: List of HDF5 file paths
            output_dir: Output directory for MS files
            
        Returns:
            Dictionary containing conversion results
        """
        logger.info(f"Converting {len(hdf5_files)} HDF5 files to MS format")
        
        results = {
            'successful': [],
            'failed': [],
            'total_processed': 0,
            'total_successful': 0,
            'total_failed': 0
        }
        
        os.makedirs(output_dir, exist_ok=True)
        
        for hdf5_file in hdf5_files:
            try:
                # Generate output MS path
                hdf5_name = Path(hdf5_file).stem
                ms_path = os.path.join(output_dir, f"{hdf5_name}.ms")
                
                # Convert HDF5 to MS
                result = await self.convert_hdf5_to_ms(hdf5_file, ms_path)
                
                results['total_processed'] += 1
                
                if result['success']:
                    results['successful'].append(result)
                    results['total_successful'] += 1
                    logger.info(f"Successfully converted: {Path(hdf5_file).name}")
                else:
                    results['failed'].append({
                        'hdf5_file': hdf5_file,
                        'error': result['error']
                    })
                    results['total_failed'] += 1
                    logger.error(f"Failed to convert: {Path(hdf5_file).name} - {result['error']}")
                    
            except Exception as e:
                results['total_processed'] += 1
                results['total_failed'] += 1
                results['failed'].append({
                    'hdf5_file': hdf5_file,
                    'error': str(e)
                })
                logger.error(f"Exception converting {Path(hdf5_file).name}: {e}")
        
        success_rate = (results['total_successful'] / results['total_processed']) * 100 if results['total_processed'] > 0 else 0
        
        logger.info(f"HDF5 to MS conversion complete: {results['total_successful']}/{results['total_processed']} "
                   f"successful ({success_rate:.1f}%)")
        
        return results
