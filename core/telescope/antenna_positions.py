"""
DSA-110 Antenna Position Management

This module handles loading and managing DSA-110 antenna positions
from the CSV file and converting them to the appropriate coordinate systems.
"""

import os
import pandas as pd
import numpy as np
from astropy.coordinates import EarthLocation
import astropy.units as u
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from .dsa110 import get_telescope_location
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DSA110AntennaPositions:
    """
    Manages DSA-110 antenna positions and coordinate conversions.
    """
    
    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize antenna position manager.
        
        Args:
            csv_path: Path to the DSA110_Station_Coordinates.csv file
        """
        if csv_path is None:
            # Default path to the CSV file in the reference pipeline
            csv_path = Path(__file__).parent.parent.parent / "archive" / "reference_pipelines" / "dsa110_hi-main" / "dsa110hi" / "resources" / "DSA110_Station_Coordinates.csv"
        
        self.csv_path = csv_path
        self.telescope_location = get_telescope_location()
        self._positions_df = None
        self._itrf_positions = None
        
    def load_positions(self) -> pd.DataFrame:
        """
        Load antenna positions from CSV file.
        
        Returns:
            DataFrame with antenna positions
        """
        if self._positions_df is not None:
            return self._positions_df
            
        try:
            if not os.path.exists(self.csv_path):
                raise FileNotFoundError(f"Antenna positions CSV not found: {self.csv_path}")
            
            # Read CSV file (header is on line 5)
            self._positions_df = pd.read_csv(self.csv_path, header=5)
            
            # Clean up the data
            self._positions_df = self._positions_df.dropna(subset=['Station Number'])
            
            # Convert station numbers to integers (handle 'DSA-001' format)
            def extract_station_number(station_str):
                if isinstance(station_str, str) and station_str.startswith('DSA-'):
                    return int(station_str.split('-')[1])
                return int(station_str)
            
            self._positions_df['Station Number'] = self._positions_df['Station Number'].apply(extract_station_number)
            
            # Set index to station number
            self._positions_df.set_index('Station Number', inplace=True)
            
            logger.info(f"Loaded antenna positions for {len(self._positions_df)} stations")
            
            return self._positions_df
            
        except Exception as e:
            logger.error(f"Failed to load antenna positions: {e}")
            raise
    
    def get_itrf_positions(self) -> np.ndarray:
        """
        Get antenna positions in ITRF coordinates.
        
        Returns:
            Array of ITRF positions (N_antennas, 3) in meters
        """
        if self._itrf_positions is not None:
            return self._itrf_positions
            
        try:
            # Load positions if not already loaded
            if self._positions_df is None:
                self.load_positions()
            
            # Convert to ITRF coordinates
            locations = EarthLocation(
                lat=self._positions_df['Latitude'] * u.degree,
                lon=self._positions_df['Longitude'] * u.degree,
                height=self._positions_df['Elevation (meters)'] * u.m
            )
            
            # Get ITRF coordinates
            x = locations.x.to_value(u.m)
            y = locations.y.to_value(u.m)
            z = locations.z.to_value(u.m)
            
            # Store as array
            self._itrf_positions = np.column_stack([x, y, z])
            
            logger.info(f"Converted {len(self._positions_df)} antenna positions to ITRF coordinates")
            
            return self._itrf_positions
            
        except Exception as e:
            logger.error(f"Failed to convert antenna positions to ITRF: {e}")
            raise
    
    def get_relative_positions(self) -> np.ndarray:
        """
        Get antenna positions relative to the telescope center.
        
        Returns:
            Array of relative positions (N_antennas, 3) in meters
        """
        try:
            # Get ITRF positions
            itrf_positions = self.get_itrf_positions()
            
            # Get telescope center in ITRF
            telescope_xyz = np.array([
                self.telescope_location.x.to_value(u.m),
                self.telescope_location.y.to_value(u.m),
                self.telescope_location.z.to_value(u.m)
            ])
            
            # Calculate relative positions
            relative_positions = itrf_positions - telescope_xyz
            
            logger.info(f"Calculated relative positions for {len(relative_positions)} antennas")
            
            return relative_positions
            
        except Exception as e:
            logger.error(f"Failed to calculate relative positions: {e}")
            raise
    
    def get_antenna_positions_for_uvdata(self, antenna_numbers: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get antenna positions in the format required by PyUVData.
        
        Args:
            antenna_numbers: Array of antenna numbers to include (0-based)
            
        Returns:
            Tuple of (antenna_positions, antenna_names)
        """
        try:
            # Load positions if not already loaded
            if self._positions_df is None:
                self.load_positions()
            
            # Get relative positions
            relative_positions = self.get_relative_positions()
            
            # Filter by antenna numbers if provided
            if antenna_numbers is not None:
                # Convert 0-based antenna numbers to 1-based station numbers
                station_numbers = antenna_numbers + 1
                
                # Find indices of requested antennas
                valid_indices = []
                for i, station_num in enumerate(self._positions_df.index):
                    if station_num in station_numbers:
                        valid_indices.append(i)
                
                if len(valid_indices) != len(antenna_numbers):
                    logger.warning(f"Only found {len(valid_indices)} of {len(antenna_numbers)} requested antennas")
                
                relative_positions = relative_positions[valid_indices]
                antenna_names = [f"pad{station_num}" for station_num in self._positions_df.index[valid_indices]]
            else:
                # Use all antennas
                antenna_names = [f"pad{station_num}" for station_num in self._positions_df.index]
            
            logger.info(f"Prepared antenna positions for {len(relative_positions)} antennas")
            
            return relative_positions, antenna_names
            
        except Exception as e:
            logger.error(f"Failed to prepare antenna positions for UVData: {e}")
            raise
    
    def get_antenna_info(self) -> Dict[str, Any]:
        """
        Get comprehensive antenna information.
        
        Returns:
            Dictionary with antenna information
        """
        try:
            # Load positions if not already loaded
            if self._positions_df is None:
                self.load_positions()
            
            # Get relative positions
            relative_positions = self.get_relative_positions()
            
            # Calculate baseline lengths
            n_antennas = len(relative_positions)
            baseline_lengths = []
            for i in range(n_antennas):
                for j in range(i+1, n_antennas):
                    baseline_length = np.linalg.norm(relative_positions[i] - relative_positions[j])
                    baseline_lengths.append(baseline_length)
            
            baseline_lengths = np.array(baseline_lengths)
            
            info = {
                'n_antennas': n_antennas,
                'station_numbers': self._positions_df.index.tolist(),
                'antenna_names': [f"pad{station_num}" for station_num in self._positions_df.index],
                'max_baseline': np.max(baseline_lengths),
                'min_baseline': np.min(baseline_lengths),
                'mean_baseline': np.mean(baseline_lengths),
                'positions_loaded': True,
                'csv_path': str(self.csv_path)
            }
            
            logger.info(f"Antenna info: {n_antennas} antennas, "
                       f"baseline range: {info['min_baseline']:.1f} - {info['max_baseline']:.1f} m")
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get antenna info: {e}")
            return {
                'n_antennas': 0,
                'positions_loaded': False,
                'error': str(e)
            }


def get_antenna_positions_manager() -> DSA110AntennaPositions:
    """
    Get a DSA110AntennaPositions manager instance.
    
    Returns:
        DSA110AntennaPositions instance
    """
    return DSA110AntennaPositions()
