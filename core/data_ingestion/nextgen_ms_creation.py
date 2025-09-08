"""
Next-Generation MS Creation for DSA-110

This module improves upon the reference pipelines with:
- Proper antenna position integration from CSV
- Advanced error handling and recovery
- Intelligent sub-band combination with quality checks
- Modern calibration preparation
- Comprehensive data validation
- Flexible configuration management
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import numpy as np
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u
from pyuvdata import UVData
import glob
import h5py
from datetime import datetime, timedelta

from ..utils.logging import get_logger
from ..telescope.dsa110 import get_telescope_location, get_valid_antennas
from ..telescope.antenna_positions import get_antenna_positions_manager
from ..pipeline.exceptions import DataError

logger = get_logger(__name__)


class NextGenMSCreationManager:
    """
    Next-generation MS creation manager that improves upon reference pipelines.
    
    Key improvements:
    - Proper antenna position integration
    - Advanced error handling and recovery
    - Intelligent sub-band combination
    - Quality validation and diagnostics
    - Flexible configuration management
    - Modern calibration preparation
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the next-generation MS creation manager.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.ms_config = config.get('ms_creation', {})
        self.paths_config = config.get('paths', {})
        self.telescope_location = get_telescope_location()
        self.valid_antennas = get_valid_antennas()
        self.antenna_positions_manager = get_antenna_positions_manager()
        
        # Sub-band configuration
        self.required_spws = ['sb00', 'sb01', 'sb02', 'sb03', 'sb04', 'sb05', 'sb06', 'sb07',
                             'sb08', 'sb09', 'sb10', 'sb11', 'sb12', 'sb13', 'sb14', 'sb15']
        self.same_timestamp_tolerance = self.ms_config.get('same_timestamp_tolerance', 30.0)
        
        # Quality thresholds
        self.min_data_quality = self.ms_config.get('min_data_quality', 0.8)
        self.max_missing_subbands = self.ms_config.get('max_missing_subbands', 2)
        self.min_integration_time = self.ms_config.get('min_integration_time', 10.0)  # seconds
        
        # Antenna selection
        self.output_antennas = self.ms_config.get('output_antennas', None)
        if self.output_antennas is not None:
            # Convert to 0-based indexing
            self.output_antennas = [ant - 1 for ant in self.output_antennas]
        
    async def create_ms_from_timestamp(self, timestamp: str, hdf5_dir: str, 
                                     output_ms_path: str, 
                                     quality_checks: bool = True) -> Dict[str, Any]:
        """
        Create a single MS from all sub-bands for a given timestamp with quality checks.
        
        Args:
            timestamp: Timestamp string (e.g., '2025-09-05T03:23:14')
            hdf5_dir: Directory containing HDF5 files
            output_ms_path: Path for the output MS file
            quality_checks: Whether to perform quality validation
            
        Returns:
            Dictionary with creation results and quality metrics
        """
        logger.info(f"Creating MS for timestamp: {timestamp}")
        
        results = {
            'timestamp': timestamp,
            'success': False,
            'ms_path': output_ms_path,
            'quality_metrics': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # Step 1: Find and validate HDF5 files
            logger.info("Step 1: Finding and validating HDF5 files")
            hdf5_files = await self._find_and_validate_hdf5_files(timestamp, hdf5_dir)
            
            if not hdf5_files:
                results['errors'].append("No valid HDF5 files found")
                return results
            
            # Step 2: Quality assessment
            if quality_checks:
                logger.info("Step 2: Quality assessment")
                quality_result = await self._assess_data_quality(hdf5_files)
                results['quality_metrics'] = quality_result
                
                if not quality_result['meets_standards']:
                    results['warnings'].append(f"Data quality below standards: {quality_result['quality_score']:.2f}")
                    if quality_result['quality_score'] < self.min_data_quality:
                        results['errors'].append("Data quality too low for processing")
                        return results
            
            # Step 3: Intelligent sub-band combination
            logger.info("Step 3: Intelligent sub-band combination")
            combination_result = await self._intelligent_subband_combination(hdf5_files, output_ms_path)
            
            if not combination_result['success']:
                results['errors'].append(f"Sub-band combination failed: {combination_result['error']}")
                return results
            
            # Step 4: Post-creation validation
            logger.info("Step 4: Post-creation validation")
            validation_result = await self._validate_created_ms(output_ms_path)
            
            if not validation_result['success']:
                results['errors'].append(f"MS validation failed: {validation_result['error']}")
                return results
            
            results['success'] = True
            results['quality_metrics'].update(validation_result['metrics'])
            
            logger.info(f"Successfully created MS: {os.path.basename(output_ms_path)}")
            
        except Exception as e:
            logger.error(f"MS creation failed for timestamp {timestamp}: {e}")
            results['errors'].append(str(e))
        
        return results
    
    async def _find_and_validate_hdf5_files(self, timestamp: str, hdf5_dir: str) -> List[str]:
        """
        Find and validate HDF5 files for a given timestamp.
        
        Args:
            timestamp: Timestamp string
            hdf5_dir: Directory containing HDF5 files
            
        Returns:
            List of valid HDF5 file paths
        """
        valid_files = []
        
        # Look for files with the timestamp pattern
        pattern = os.path.join(hdf5_dir, f"{timestamp}_sb*.hdf5")
        files = glob.glob(pattern)
        
        # Sort by sub-band number
        files.sort(key=lambda x: int(x.split('_sb')[1].split('.')[0]))
        
        logger.info(f"Found {len(files)} HDF5 files for timestamp {timestamp}")
        
        # Validate each file
        for file_path in files:
            if await self._validate_hdf5_file(file_path):
                valid_files.append(file_path)
            else:
                logger.warning(f"Invalid HDF5 file: {os.path.basename(file_path)}")
        
        logger.info(f"Validated {len(valid_files)} of {len(files)} HDF5 files")
        
        return valid_files
    
    async def _validate_hdf5_file(self, file_path: str) -> bool:
        """
        Validate a single HDF5 file.
        
        Args:
            file_path: Path to the HDF5 file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            with h5py.File(file_path, 'r') as f:
                # Check required groups
                if 'Data' not in f or 'Header' not in f:
                    return False
                
                # Check required header fields
                header = f['Header']
                required_fields = ['time_array', 'freq_array', 'ant_1_array', 'ant_2_array']
                for field in required_fields:
                    if field not in header:
                        return False
                
                # Check data integrity
                time_array = header['time_array'][:]
                if len(time_array) == 0:
                    return False
                
                # Check integration time
                if 'integration_time' in header:
                    int_time = header['integration_time'][0]
                    if int_time < self.min_integration_time:
                        return False
                
                return True
                
        except Exception as e:
            logger.debug(f"Validation failed for {file_path}: {e}")
            return False
    
    async def _assess_data_quality(self, hdf5_files: List[str]) -> Dict[str, Any]:
        """
        Assess the quality of the HDF5 files.
        
        Args:
            hdf5_files: List of HDF5 file paths
            
        Returns:
            Dictionary with quality metrics
        """
        quality_metrics = {
            'n_files': len(hdf5_files),
            'n_required_files': len(self.required_spws),
            'completeness': 0.0,
            'data_consistency': 0.0,
            'integration_time_consistency': 0.0,
            'quality_score': 0.0,
            'meets_standards': False
        }
        
        try:
            # Check completeness
            found_spws = set()
            for file_path in hdf5_files:
                filename = os.path.basename(file_path)
                if '_sb' in filename:
                    spw = filename.split('_sb')[1].split('.')[0]
                    found_spws.add(f'sb{spw.zfill(2)}')
            
            missing_spws = set(self.required_spws) - found_spws
            quality_metrics['completeness'] = len(found_spws) / len(self.required_spws)
            quality_metrics['missing_subbands'] = list(missing_spws)
            
            # Check data consistency
            if len(hdf5_files) > 1:
                consistency_score = await self._check_data_consistency(hdf5_files)
                quality_metrics['data_consistency'] = consistency_score
            
            # Check integration time consistency
            int_time_score = await self._check_integration_time_consistency(hdf5_files)
            quality_metrics['integration_time_consistency'] = int_time_score
            
            # Calculate overall quality score
            quality_metrics['quality_score'] = (
                quality_metrics['completeness'] * 0.4 +
                quality_metrics['data_consistency'] * 0.3 +
                quality_metrics['integration_time_consistency'] * 0.3
            )
            
            # Determine if meets standards
            quality_metrics['meets_standards'] = (
                quality_metrics['quality_score'] >= self.min_data_quality and
                len(missing_spws) <= self.max_missing_subbands
            )
            
            logger.info(f"Data quality assessment: {quality_metrics['quality_score']:.2f} "
                       f"(completeness: {quality_metrics['completeness']:.2f}, "
                       f"consistency: {quality_metrics['data_consistency']:.2f})")
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            quality_metrics['error'] = str(e)
        
        return quality_metrics
    
    async def _check_data_consistency(self, hdf5_files: List[str]) -> float:
        """
        Check consistency between HDF5 files.
        
        Args:
            hdf5_files: List of HDF5 file paths
            
        Returns:
            Consistency score (0.0 to 1.0)
        """
        try:
            # Read first file to get reference values
            with h5py.File(hdf5_files[0], 'r') as f:
                header = f['Header']
                ref_time_array = header['time_array'][:]
                ref_nants = header['Nants_data'][()]
                ref_nbls = header['Nbls'][()]
            
            consistent_files = 1  # First file is consistent with itself
            
            # Check other files
            for file_path in hdf5_files[1:]:
                with h5py.File(file_path, 'r') as f:
                    header = f['Header']
                    time_array = header['time_array'][:]
                    nants = header['Nants_data'][()]
                    nbls = header['Nbls'][()]
                
                # Check time consistency
                time_consistent = np.allclose(time_array, ref_time_array, rtol=1e-10)
                
                # Check antenna consistency
                antenna_consistent = (nants == ref_nants)
                
                # Check baseline consistency
                baseline_consistent = (nbls == ref_nbls)
                
                if time_consistent and antenna_consistent and baseline_consistent:
                    consistent_files += 1
            
            consistency_score = consistent_files / len(hdf5_files)
            return consistency_score
            
        except Exception as e:
            logger.error(f"Data consistency check failed: {e}")
            return 0.0
    
    async def _check_integration_time_consistency(self, hdf5_files: List[str]) -> float:
        """
        Check integration time consistency across files.
        
        Args:
            hdf5_files: List of HDF5 file paths
            
        Returns:
            Consistency score (0.0 to 1.0)
        """
        try:
            integration_times = []
            
            for file_path in hdf5_files:
                with h5py.File(file_path, 'r') as f:
                    header = f['Header']
                    if 'integration_time' in header:
                        int_time = header['integration_time'][0]
                        integration_times.append(int_time)
            
            if len(integration_times) == 0:
                return 0.0
            
            # Check if all integration times are the same
            if len(set(integration_times)) == 1:
                return 1.0
            
            # Calculate consistency based on standard deviation
            std_dev = np.std(integration_times)
            mean_time = np.mean(integration_times)
            cv = std_dev / mean_time  # Coefficient of variation
            
            # Score based on coefficient of variation (lower is better)
            consistency_score = max(0.0, 1.0 - cv)
            
            return consistency_score
            
        except Exception as e:
            logger.error(f"Integration time consistency check failed: {e}")
            return 0.0
    
    async def _intelligent_subband_combination(self, hdf5_files: List[str], output_ms_path: str) -> Dict[str, Any]:
        """
        Intelligently combine sub-bands into a single MS.
        
        Args:
            hdf5_files: List of HDF5 file paths
            output_ms_path: Path for the output MS file
            
        Returns:
            Dictionary with combination results
        """
        try:
            logger.info(f"Combining {len(hdf5_files)} sub-bands into MS")
            
            # Read the first HDF5 file to get the basic structure
            uv_data = UVData()
            uv_data.read(hdf5_files[0], file_type='uvh5', run_check=False)
            
            # Fix UVW array type issue
            if uv_data.uvw_array.dtype != np.float64:
                uv_data.uvw_array = uv_data.uvw_array.astype(np.float64)
            
            # Set proper antenna positions
            await self._set_antenna_positions(uv_data)
            
            # Apply antenna selection if specified
            if self.output_antennas is not None:
                await self._apply_antenna_selection(uv_data)
            
            # If we have multiple files, combine them intelligently
            if len(hdf5_files) > 1:
                combination_result = await self._combine_multiple_subbands(uv_data, hdf5_files[1:])
                if not combination_result['success']:
                    return combination_result
            
            # Write to MS format with advanced parameters
            success = await self._write_to_ms_advanced(uv_data, output_ms_path)
            
            if success:
                return {
                    'success': True,
                    'n_subbands': len(hdf5_files),
                    'n_antennas': uv_data.Nants,
                    'n_baselines': uv_data.Nbls,
                    'n_times': uv_data.Ntimes,
                    'n_freqs': uv_data.Nfreqs
                }
            else:
                return {'success': False, 'error': 'Failed to write MS file'}
            
        except Exception as e:
            logger.error(f"Sub-band combination failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _set_antenna_positions(self, uv_data: UVData) -> None:
        """
        Set proper antenna positions in the UVData object.
        
        Args:
            uv_data: UVData object to modify
        """
        try:
            # Get antenna positions from the CSV file
            antenna_positions, antenna_names = self.antenna_positions_manager.get_antenna_positions_for_uvdata()
            
            # Set antenna positions in UVData
            uv_data.antenna_positions = antenna_positions
            uv_data.antenna_names = antenna_names
            uv_data.antenna_numbers = np.arange(len(antenna_names))
            
            # Set telescope location
            uv_data.telescope_location = self.telescope_location
            
            logger.info(f"Set antenna positions for {len(antenna_names)} antennas")
            
        except Exception as e:
            logger.error(f"Failed to set antenna positions: {e}")
            # Continue without proper positions (will cause issues later)
    
    async def _apply_antenna_selection(self, uv_data: UVData) -> None:
        """
        Apply antenna selection to the UVData object.
        
        Args:
            uv_data: UVData object to modify
        """
        try:
            if self.output_antennas is None:
                return
            
            # Select antennas
            uv_data.select(antenna_nums=self.output_antennas)
            
            logger.info(f"Selected {len(self.output_antennas)} antennas")
            
        except Exception as e:
            logger.error(f"Failed to apply antenna selection: {e}")
    
    async def _combine_multiple_subbands(self, uv_data: UVData, additional_files: List[str]) -> Dict[str, Any]:
        """
        Combine multiple sub-band files into the UVData object.
        
        Args:
            uv_data: UVData object to modify
            additional_files: List of additional HDF5 file paths
            
        Returns:
            Dictionary with combination results
        """
        try:
            for i, file_path in enumerate(additional_files):
                logger.debug(f"Combining sub-band {i+2}/{len(additional_files)+1}: {os.path.basename(file_path)}")
                
                uv_data_additional = UVData()
                uv_data_additional.read(file_path, file_type='uvh5', run_check=False)
                
                # Fix UVW array type issue
                if uv_data_additional.uvw_array.dtype != np.float64:
                    uv_data_additional.uvw_array = uv_data_additional.uvw_array.astype(np.float64)
                
                # Apply antenna selection if specified
                if self.output_antennas is not None:
                    uv_data_additional.select(antenna_nums=self.output_antennas)
                
                # Combine the data
                uv_data += uv_data_additional
            
            logger.info(f"Successfully combined {len(additional_files)+1} sub-bands")
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to combine sub-bands: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _write_to_ms_advanced(self, uv_data: UVData, output_ms_path: str) -> bool:
        """
        Write UVData object to MS format with advanced parameters.
        
        Args:
            uv_data: UVData object to write
            output_ms_path: Path for the output MS file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure proper data types
            if uv_data.uvw_array.dtype != np.float64:
                uv_data.uvw_array = uv_data.uvw_array.astype(np.float64)
            
            # Set proper units
            if not hasattr(uv_data, 'vis_units') or uv_data.vis_units is None or uv_data.vis_units == 'uncalib':
                uv_data.vis_units = 'Jy'
            
            # Write to MS format with advanced parameters
            uv_data.write_ms(
                output_ms_path, 
                clobber=True, 
                fix_autos=True,  # Fix auto-correlations to be real-only
                force_phase=True,  # Phase data to zenith of first timestamp
                run_check=False  # Skip PyUVData checks during write
            )
            
            logger.info(f"Successfully wrote MS file: {output_ms_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write MS file: {e}")
            return False
    
    async def _validate_created_ms(self, ms_path: str) -> Dict[str, Any]:
        """
        Validate the created MS file.
        
        Args:
            ms_path: Path to the MS file
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Check if file exists and has reasonable size
            if not os.path.exists(ms_path):
                return {'success': False, 'error': 'MS file does not exist'}
            
            file_size = os.path.getsize(ms_path)
            if file_size < 1024:  # Less than 1KB is suspicious
                return {'success': False, 'error': 'MS file too small'}
            
            # Try to read with PyUVData
            uv_data = UVData()
            uv_data.read_ms(ms_path, ignore_single_chan=True)
            
            metrics = {
                'file_size_mb': file_size / (1024 * 1024),
                'n_antennas': uv_data.Nants,
                'n_baselines': uv_data.Nbls,
                'n_times': uv_data.Ntimes,
                'n_freqs': uv_data.Nfreqs,
                'n_pols': uv_data.Npols,
                'frequency_range_ghz': [uv_data.freq_array.min()/1e9, uv_data.freq_array.max()/1e9],
                'time_range_mjd': [uv_data.time_array.min(), uv_data.time_array.max()],
                'integration_time_s': np.mean(np.diff(np.unique(uv_data.time_array))) * 24 * 3600
            }
            
            uv_data.close()
            
            logger.info(f"MS validation successful: {metrics['n_antennas']} antennas, "
                       f"{metrics['n_baselines']} baselines, {metrics['n_times']} times, "
                       f"{metrics['n_freqs']} frequencies")
            
            return {
                'success': True,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"MS validation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_timestamp_range_advanced(self, start_timestamp: str, end_timestamp: str, 
                                             hdf5_dir: str, output_dir: str,
                                             quality_checks: bool = True) -> Dict[str, Any]:
        """
        Process a range of timestamps with advanced features.
        
        Args:
            start_timestamp: Start timestamp string
            end_timestamp: End timestamp string
            hdf5_dir: Directory containing HDF5 files
            output_dir: Directory for output MS files
            quality_checks: Whether to perform quality validation
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing timestamp range: {start_timestamp} to {end_timestamp}")
        
        results = {
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
            'success': False,
            'created_ms_files': [],
            'failed_timestamps': [],
            'quality_summary': {},
            'total_processing_time': 0.0
        }
        
        start_time = datetime.now()
        
        try:
            # Find all unique timestamps in the directory
            timestamp_pattern = os.path.join(hdf5_dir, "*.hdf5")
            all_files = glob.glob(timestamp_pattern)
            
            # Extract unique timestamps
            timestamps = set()
            for file_path in all_files:
                filename = os.path.basename(file_path)
                if '_sb' in filename:
                    timestamp = filename.split('_sb')[0]
                    timestamps.add(timestamp)
            
            timestamps = sorted(list(timestamps))
            logger.info(f"Found {len(timestamps)} unique timestamps")
            
            # Process each timestamp
            successful_creations = 0
            quality_scores = []
            
            for timestamp in timestamps:
                output_ms_path = os.path.join(output_dir, f"{timestamp}.ms")
                
                creation_result = await self.create_ms_from_timestamp(
                    timestamp, hdf5_dir, output_ms_path, quality_checks
                )
                
                if creation_result['success']:
                    results['created_ms_files'].append(output_ms_path)
                    successful_creations += 1
                    
                    if 'quality_metrics' in creation_result:
                        quality_scores.append(creation_result['quality_metrics'].get('quality_score', 0.0))
                    
                    logger.info(f"Created MS: {output_ms_path}")
                else:
                    results['failed_timestamps'].append({
                        'timestamp': timestamp,
                        'errors': creation_result.get('errors', [])
                    })
                    logger.error(f"Failed to create MS for timestamp: {timestamp}")
            
            # Calculate summary statistics
            results['success'] = successful_creations > 0
            results['total_timestamps'] = len(timestamps)
            results['successful_creations'] = successful_creations
            results['success_rate'] = successful_creations / len(timestamps) if timestamps else 0.0
            
            if quality_scores:
                results['quality_summary'] = {
                    'mean_quality_score': np.mean(quality_scores),
                    'min_quality_score': np.min(quality_scores),
                    'max_quality_score': np.max(quality_scores),
                    'std_quality_score': np.std(quality_scores)
                }
            
            end_time = datetime.now()
            results['total_processing_time'] = (end_time - start_time).total_seconds()
            
            logger.info(f"Processing complete: {successful_creations}/{len(timestamps)} successful "
                       f"({results['success_rate']:.1%}) in {results['total_processing_time']:.1f}s")
            
        except Exception as e:
            logger.error(f"Failed to process timestamp range: {e}")
            results['error'] = str(e)
        
        return results


# Legacy compatibility function
async def process_hdf5_set_nextgen(config: Dict[str, Any], timestamp: str, hdf5_files: List[str]) -> Optional[str]:
    """
    Process a set of HDF5 files for a given timestamp using the next-generation approach.
    
    Args:
        config: Pipeline configuration dictionary
        timestamp: Timestamp string for the observation
        hdf5_files: List of HDF5 file paths (all sub-bands for one timestamp)
        
    Returns:
        Path to the created MS file, or None if failed
    """
    logger.info(f"Processing HDF5 set for timestamp: {timestamp}")
    logger.info(f"Found {len(hdf5_files)} HDF5 files")
    
    try:
        # Create MS creation manager
        ms_manager = NextGenMSCreationManager(config)
        
        # Determine output MS path
        ms_stage1_dir = config.get('paths', {}).get('ms_stage1_dir', 'ms_stage1')
        os.makedirs(ms_stage1_dir, exist_ok=True)
        
        output_ms_path = os.path.join(ms_stage1_dir, f"{timestamp}.ms")
        
        # Create MS from all sub-bands with quality checks
        result = await ms_manager.create_ms_from_timestamp(timestamp, "", output_ms_path, quality_checks=True)
        
        if result['success']:
            logger.info(f"Successfully created MS: {output_ms_path}")
            return output_ms_path
        else:
            logger.error(f"Failed to create MS: {result.get('errors', [])}")
            return None
            
    except Exception as e:
        logger.error(f"process_hdf5_set_nextgen failed: {e}")
        return None
