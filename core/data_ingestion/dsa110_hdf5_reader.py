#!/usr/bin/env python3
"""
Custom HDF5 reader for DSA-110 data format.

This module provides a custom reader that can parse the DSA-110 HDF5 format
and convert it to PyUVData UVData objects for MS creation.
"""

import os
import h5py
import numpy as np
from typing import Dict, Any, Optional, Tuple
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u

from ..utils.logging import get_logger

logger = get_logger(__name__)


class DSA110HDF5Reader:
    """
    Custom HDF5 reader for DSA-110 data format.
    
    This class handles the specific HDF5 structure used by DSA-110
    and converts it to PyUVData-compatible format.
    """
    
    def __init__(self):
        """Initialize the DSA-110 HDF5 reader."""
        self.logger = logger
    
    def read_hdf5_file(self, hdf5_path: str) -> Optional[Dict[str, Any]]:
        """
        Read a DSA-110 HDF5 file and extract all necessary data.
        
        Args:
            hdf5_path: Path to the HDF5 file
            
        Returns:
            Dictionary containing UVData-compatible data, or None if failed
        """
        try:
            self.logger.info(f"Reading DSA-110 HDF5 file: {os.path.basename(hdf5_path)}")
            
            with h5py.File(hdf5_path, 'r') as f:
                # Read header information
                header = f['Header']
                
                # Extract basic dimensions
                Nblts = header['Nblts'][()]
                Nfreqs = header['Nfreqs'][()]
                Npols = header['Npols'][()]
                Nants_data = header['Nants_data'][()]
                
                self.logger.info(f"Data dimensions: Nblts={Nblts}, Nfreqs={Nfreqs}, Npols={Npols}, Nants_data={Nants_data}")
                
                # Read time and frequency arrays
                time_array = header['time_array'][()]
                freq_array = header['freq_array'][()]
                
                # Read telescope information
                telescope_name = header['telescope_name'][()].decode()
                lat = header['latitude'][()]
                lon = header['longitude'][()]
                alt = header['altitude'][()]
                
                # Read antenna information
                antenna_names = [name.decode() for name in header['antenna_names'][()]]
                antenna_numbers = header['antenna_numbers'][()]
                
                # Read data arrays
                data_group = f['Data']
                visdata = data_group['visdata'][()]
                flags = data_group['flags'][()]
                nsamples = data_group['nsamples'][()]
                
                # Read baseline information from Header
                ant_1_array = header['ant_1_array'][()]
                ant_2_array = header['ant_2_array'][()]
                
                self.logger.info(f"Read data: {visdata.shape}, flags: {flags.shape}, nsamples: {nsamples.shape}")
                
                # Convert to PyUVData-compatible format
                uv_data_dict = self._convert_to_uvdata_format(
                    visdata, flags, nsamples, time_array, freq_array,
                    ant_1_array, ant_2_array, antenna_names, antenna_numbers,
                    telescope_name, lat, lon, alt
                )
                
                return uv_data_dict
                
        except Exception as e:
            self.logger.error(f"Failed to read HDF5 file: {e}")
            return None
    
    def _convert_to_uvdata_format(self, visdata: np.ndarray, flags: np.ndarray, 
                                nsamples: np.ndarray, time_array: np.ndarray,
                                freq_array: np.ndarray, ant_1_array: np.ndarray,
                                ant_2_array: np.ndarray, antenna_names: list,
                                antenna_numbers: np.ndarray, telescope_name: str,
                                lat: float, lon: float, alt: float) -> Dict[str, Any]:
        """
        Convert DSA-110 data to PyUVData-compatible format.
        
        Args:
            visdata: Visibility data array
            flags: Flag array
            nsamples: Number of samples array
            time_array: Time array
            freq_array: Frequency array
            ant_1_array: Antenna 1 array
            ant_2_array: Antenna 2 array
            antenna_names: List of antenna names
            antenna_numbers: Array of antenna numbers
            telescope_name: Telescope name
            lat: Latitude in degrees
            lon: Longitude in degrees
            alt: Altitude in meters
            
        Returns:
            Dictionary with PyUVData-compatible data
        """
        try:
            # Convert data arrays to proper shapes
            # The data is already in the correct shape (Nblts, 1, Nfreqs, Npols)
            Nblts, _, Nfreqs, Npols = visdata.shape
            
            # Data is already in the correct shape, just convert to complex
            data_array = visdata.astype(complex)
            flag_array = flags
            nsample_array = nsamples
            
            # Set telescope location (convert to ECEF coordinates)
            telescope_location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=alt*u.m)
            telescope_location_xyz = telescope_location.to_geocentric()
            
            # Calculate baseline array
            baseline_array = ant_1_array * 1000 + ant_2_array
            
            # Calculate number of baselines
            Nbls = len(np.unique(baseline_array))
            
            # Calculate number of times
            Ntimes = len(np.unique(time_array))
            
            # Set antenna positions (simplified - would need actual positions)
            antenna_positions = np.zeros((len(antenna_names), 3))
            
            # Set polarization array (assuming linear polarizations)
            polarization_array = np.array([1, 2])  # XX, YY
            
            # Set spectral window array
            spw_array = np.array([0])
            
            # Set phase center information (from HDF5 header)
            phase_center_ra = 0.0  # Default value
            phase_center_dec = 0.0  # Default value
            
            # Create phase center catalog (required for MS writing)
            phase_center_catalog = {
                0: {
                    'cat_name': 'drift_ra0.0',
                    'cat_type': 'sidereal',
                    'cat_lon': phase_center_ra,
                    'cat_lat': phase_center_dec,
                    'cat_frame': 'icrs',
                    'cat_epoch': 2000.0,
                    'cat_times': time_array,
                    'cat_pm_ra': 0.0,
                    'cat_pm_dec': 0.0,
                    'cat_vrad': 0.0,
                    'cat_dist': 0.0
                }
            }
            
            # Create UVData-compatible dictionary
            uv_data_dict = {
                'data_array': data_array,
                'flag_array': flag_array,
                'nsample_array': nsample_array,
                'time_array': time_array,
                'freq_array': freq_array.reshape(1, -1),
                'ant_1_array': ant_1_array,
                'ant_2_array': ant_2_array,
                'baseline_array': baseline_array,
                'antenna_names': antenna_names,
                'antenna_numbers': antenna_numbers,
                'antenna_positions': antenna_positions,
                'telescope_name': telescope_name,
                'telescope_location': telescope_location_xyz,
                'uvw_array': np.zeros((Nblts, 3), dtype=np.float64),  # Will be calculated later
                'polarization_array': polarization_array,
                'spw_array': spw_array,
                'phase_type': 'phased',
                'phase_center_ra': phase_center_ra,
                'phase_center_dec': phase_center_dec,
                'phase_center_epoch': 2000.0,
                'phase_center_frame': 'icrs',
                'extra_keywords': {},  # Critical: must be a dict, not None
                'Nblts': Nblts,
                'Nfreqs': Nfreqs,
                'Npols': Npols,
                'Nants_data': len(antenna_names),
                'Nbls': Nbls,
                'Ntimes': Ntimes,
                'vis_units': 'Jy',
                'integration_time': np.full(Nblts, 1.0),  # 1 second integration
                'channel_width': np.full(Nfreqs, (freq_array.max() - freq_array.min()) / Nfreqs)
            }
            
            self.logger.info(f"Converted to UVData format: {Nblts} blts, {Nfreqs} freqs, {Npols} pols")
            return uv_data_dict
            
        except Exception as e:
            self.logger.error(f"Failed to convert to UVData format: {e}")
            return None
    
    def create_uvdata_object(self, hdf5_path: str):
        """
        Create a PyUVData UVData object from a DSA-110 HDF5 file.
        
        Args:
            hdf5_path: Path to the HDF5 file
            
        Returns:
            UVData object or None if failed
        """
        try:
            import pyuvdata
            
            # Read the HDF5 file
            data_dict = self.read_hdf5_file(hdf5_path)
            if data_dict is None:
                return None
            
            # Create UVData object
            uv_data = pyuvdata.UVData()
            
            # Set all the attributes
            uv_data.data_array = data_dict['data_array']
            uv_data.flag_array = data_dict['flag_array']
            uv_data.nsample_array = data_dict['nsample_array']
            uv_data.time_array = data_dict['time_array']
            uv_data.freq_array = data_dict['freq_array']
            uv_data.ant_1_array = data_dict['ant_1_array']
            uv_data.ant_2_array = data_dict['ant_2_array']
            uv_data.baseline_array = data_dict['baseline_array']
            uv_data.antenna_names = data_dict['antenna_names']
            uv_data.antenna_numbers = data_dict['antenna_numbers']
            uv_data.antenna_positions = data_dict['antenna_positions']
            uv_data.telescope_name = data_dict['telescope_name']
            uv_data.telescope_location = data_dict['telescope_location']
            uv_data.uvw_array = data_dict['uvw_array']
            uv_data.polarization_array = data_dict['polarization_array']
            uv_data.spw_array = data_dict['spw_array']
            uv_data.phase_type = data_dict['phase_type']
            uv_data.phase_center_ra = data_dict['phase_center_ra']
            uv_data.phase_center_dec = data_dict['phase_center_dec']
            uv_data.phase_center_epoch = data_dict['phase_center_epoch']
            uv_data.phase_center_frame = data_dict['phase_center_frame']
            uv_data.extra_keywords = data_dict['extra_keywords']
            
            # Set up phase center using PyUVData's method
            uv_data._add_phase_center(
                cat_name='drift_ra0.0',
                cat_type='sidereal', 
                cat_lon=data_dict['phase_center_ra'],
                cat_lat=data_dict['phase_center_dec'],
                cat_frame='icrs',
                cat_epoch=2000.0,
                cat_pm_ra=0.0,
                cat_pm_dec=0.0,
                cat_vrad=0.0,
                cat_dist=0.0
            )
            uv_data.Nblts = data_dict['Nblts']
            uv_data.Nfreqs = data_dict['Nfreqs']
            uv_data.Npols = data_dict['Npols']
            uv_data.Nants_data = data_dict['Nants_data']
            uv_data.Nbls = data_dict['Nbls']
            uv_data.Ntimes = data_dict['Ntimes']
            uv_data._Nspws = len(data_dict['spw_array'])  # Number of spectral windows
            uv_data.vis_units = data_dict['vis_units']
            uv_data.integration_time = data_dict['integration_time']
            uv_data.channel_width = data_dict['channel_width']
            
            self.logger.info(f"Successfully created UVData object from {os.path.basename(hdf5_path)}")
            return uv_data
            
        except ImportError:
            self.logger.error("PyUVData not available")
            return None
        except Exception as e:
            self.logger.error(f"Failed to create UVData object: {e}")
            return None
