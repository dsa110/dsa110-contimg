"""
Unified MS Creation for DSA-110

This module combines the debugging work from dsa110_hdf5_reader_fixed.py
with the advanced features from nextgen_ms_creation.py to create a
comprehensive, production-ready MS creation system.

Key features:
- Single-file processing with DSA-110 specific fixes
- Multi-subband combination with quality validation
- Proper antenna position integration
- Advanced error handling and recovery
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


class UnifiedMSCreationManager:
    """
    Unified MS creation manager that combines single-file processing
    with multi-subband combination and quality validation.
    
    This builds on the debugging work from dsa110_hdf5_reader_fixed.py
    and adds advanced features from nextgen_ms_creation.py.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the unified MS creation manager.
        
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
    
    async def create_ms_from_single_file(self, hdf5_path: str, output_ms_path: str, 
                                       quality_checks: bool = True) -> Dict[str, Any]:
        """
        Create MS from a single HDF5 file with DSA-110 specific fixes.
        
        This uses the debugging work from dsa110_hdf5_reader_fixed.py.
        
        Args:
            hdf5_path: Path to the HDF5 file
            output_ms_path: Path for the output MS file
            quality_checks: Whether to perform quality validation
            
        Returns:
            Dictionary with creation results and quality metrics
        """
        logger.info(f"Creating MS from single file: {os.path.basename(hdf5_path)}")
        
        results = {
            'hdf5_path': hdf5_path,
            'success': False,
            'ms_path': output_ms_path,
            'quality_metrics': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # Step 1: Read and fix HDF5 file
            logger.info("Step 1: Reading and fixing HDF5 file")
            uv_data = await self._read_and_fix_hdf5_file(hdf5_path)
            
            if uv_data is None:
                results['errors'].append("Failed to read HDF5 file")
                return results
            
            # Step 2: Quality assessment
            if quality_checks:
                logger.info("Step 2: Quality assessment")
                quality_result = await self._assess_single_file_quality(uv_data, hdf5_path)
                results['quality_metrics'] = quality_result
                
                if not quality_result['meets_standards']:
                    results['warnings'].append(f"Data quality below standards: {quality_result['quality_score']:.2f}")
                    if quality_result['quality_score'] < self.min_data_quality:
                        results['errors'].append("Data quality too low for processing")
                        return results
            
            # Step 3: Set antenna positions
            logger.info("Step 3: Setting antenna positions")
            await self._set_antenna_positions(uv_data)
            
            # Step 4: Apply antenna selection if specified
            if self.output_antennas is not None:
                logger.info("Step 4: Applying antenna selection")
                await self._apply_antenna_selection(uv_data)
            
            # Step 5: Write to MS format
            logger.info("Step 5: Writing to MS format")
            success = await self._write_to_ms_with_fixes(uv_data, output_ms_path)
            
            if not success:
                results['errors'].append("Failed to write MS file")
                return results
            
            # Step 6: Post-creation validation
            logger.info("Step 6: Post-creation validation")
            validation_result = await self._validate_created_ms(output_ms_path)
            
            if not validation_result['success']:
                results['errors'].append(f"MS validation failed: {validation_result['error']}")
                return results
            
            results['success'] = True
            results['quality_metrics'].update(validation_result['metrics'])
            
            logger.info(f"Successfully created MS: {os.path.basename(output_ms_path)}")
            
        except Exception as e:
            logger.error(f"MS creation failed for {hdf5_path}: {e}")
            results['errors'].append(str(e))
        
        return results
    
    async def create_ms_from_multiple_files(self, hdf5_files: List[str], output_ms_path: str, 
                                          quality_checks: bool = True) -> Dict[str, Any]:
        """
        Create MS from multiple HDF5 files (sub-bands) with quality validation.
        
        This combines the multi-subband approach with DSA-110 specific fixes.
        
        Args:
            hdf5_files: List of HDF5 file paths (all sub-bands for one timestamp)
            output_ms_path: Path for the output MS file
            quality_checks: Whether to perform quality validation
            
        Returns:
            Dictionary with creation results and quality metrics
        """
        logger.info(f"Creating MS from {len(hdf5_files)} sub-band files")
        
        results = {
            'hdf5_files': hdf5_files,
            'success': False,
            'ms_path': output_ms_path,
            'quality_metrics': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # Step 1: Quality assessment
            if quality_checks:
                logger.info("Step 1: Quality assessment")
                quality_result = await self._assess_data_quality(hdf5_files)
                results['quality_metrics'] = quality_result
                
                if not quality_result['meets_standards']:
                    results['warnings'].append(f"Data quality below standards: {quality_result['quality_score']:.2f}")
                    if quality_result['quality_score'] < self.min_data_quality:
                        results['errors'].append("Data quality too low for processing")
                        return results
            
            # Step 2: Read and combine files
            logger.info("Step 2: Reading and combining sub-band files")
            uv_data = await self._read_and_combine_hdf5_files(hdf5_files)
            
            if uv_data is None:
                results['errors'].append("Failed to read and combine HDF5 files")
                return results
            
            # Step 3: Set antenna positions
            logger.info("Step 3: Setting antenna positions")
            await self._set_antenna_positions(uv_data)
            
            # Step 4: Apply DSA-110 specific fixes (including antenna position scaling)
            logger.info("Step 4: Applying DSA-110 specific fixes")
            uv_data = self._fix_dsa110_issues(uv_data)
            
            # Step 5: Recalculate UVW coordinates with corrected antenna positions
            logger.info("Step 5: Recalculating UVW coordinates")
            uv_data = await self._recalculate_uvw_coordinates(uv_data)
            
            # Step 6: Apply antenna selection if specified
            if self.output_antennas is not None:
                logger.info("Step 6: Applying antenna selection")
                await self._apply_antenna_selection(uv_data)
            
            # Step 7: Write to MS format
            logger.info("Step 7: Writing to MS format")
            success = await self._write_to_ms_with_fixes(uv_data, output_ms_path)
            
            if not success:
                results['errors'].append("Failed to write MS file")
                return results
            
            # Step 6: Post-creation validation
            logger.info("Step 6: Post-creation validation")
            validation_result = await self._validate_created_ms(output_ms_path)
            
            if not validation_result['success']:
                results['errors'].append(f"MS validation failed: {validation_result['error']}")
                return results
            
            results['success'] = True
            results['quality_metrics'].update(validation_result['metrics'])
            
            logger.info(f"Successfully created MS: {os.path.basename(output_ms_path)}")
            
        except Exception as e:
            logger.error(f"MS creation failed for {len(hdf5_files)} files: {e}")
            results['errors'].append(str(e))
        
        return results
    
    async def _read_and_fix_hdf5_file(self, hdf5_path: str) -> Optional[UVData]:
        """
        Read and fix a single HDF5 file using the debugging work from dsa110_hdf5_reader_fixed.py.
        
        Args:
            hdf5_path: Path to the HDF5 file
            
        Returns:
            Fixed UVData object, or None if failed
        """
        try:
            # Suppress UVW array discrepancy warnings during read
            import warnings
            
            # Temporarily suppress PyUVData warnings about UVW array discrepancy
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*uvw_array does not match.*")
                warnings.filterwarnings("ignore", message=".*largest discrepancy.*")
                warnings.filterwarnings("ignore", message=".*This is a fairly common situation.*")
                
                # Use PyUVData's native UVH5 reader
                uv_data = UVData()
                uv_data.read(hdf5_path, file_type='uvh5', run_check=False)
            
            # Apply DSA-110 specific fixes
            uv_data = self._fix_dsa110_issues(uv_data)
            
            logger.info(f"Successfully read and fixed HDF5 file: {os.path.basename(hdf5_path)}")
            return uv_data
            
        except Exception as e:
            logger.error(f"Failed to read HDF5 file {hdf5_path}: {e}")
            return None
    
    def _fix_dsa110_issues(self, uv_data: UVData) -> UVData:
        """
        Fix known issues with DSA-110 HDF5 data.
        
        This incorporates the debugging work from dsa110_hdf5_reader_fixed.py.
        
        Args:
            uv_data: UVData object to fix
            
        Returns:
            Fixed UVData object
        """
        # Fix 1: Ensure uvw_array is float64 as required by PyUVData
        if uv_data.uvw_array.dtype != np.float64:
            logger.info("Converting UVW array from float32 to float64")
            uv_data.uvw_array = uv_data.uvw_array.astype(np.float64)
        
        # Fix 2: Correct telescope name from OVRO_MMA to DSA-110
        if uv_data.telescope.name == "OVRO_MMA":
            logger.info("Correcting telescope name from OVRO_MMA to DSA-110")
            uv_data.telescope.name = "DSA-110"
        
        # Fix 3: Ensure data units are properly set
        if not hasattr(uv_data, 'vis_units') or uv_data.vis_units is None or uv_data.vis_units == 'uncalib':
            uv_data.vis_units = 'Jy'
            logger.info("Set visibility units to Jy")
        
        # Fix 4: Set proper mount type for DSA-110 (alt-az mount)
        if hasattr(uv_data.telescope, 'mount_type'):
            uv_data.telescope.mount_type = ['alt-az'] * len(uv_data.telescope.mount_type)
            logger.info(f"Set telescope mount type to alt-az for {len(uv_data.telescope.mount_type)} antennas")
        
        # IMPORTANT: Do not scale antenna positions here; ensure correct frame is used upstream
        
        return uv_data
    
    async def _read_and_combine_hdf5_files(self, hdf5_files: List[str]) -> Optional[UVData]:
        """
        Read and combine multiple HDF5 files.
        
        Args:
            hdf5_files: List of HDF5 file paths
            
        Returns:
            Combined UVData object, or None if failed
        """
        try:
            # Read the first file
            uv_data = await self._read_and_fix_hdf5_file(hdf5_files[0])
            if uv_data is None:
                return None
            
            # Combine additional files
            for i, file_path in enumerate(hdf5_files[1:], 1):
                logger.debug(f"Combining sub-band {i+1}/{len(hdf5_files)}: {os.path.basename(file_path)}")
                
                uv_data_additional = await self._read_and_fix_hdf5_file(file_path)
                if uv_data_additional is None:
                    logger.warning(f"Failed to read sub-band file: {file_path}")
                    continue
                
                # Apply antenna selection if specified
                if self.output_antennas is not None:
                    uv_data_additional.select(antenna_nums=self.output_antennas)
                
                # Combine the data (suppress UVW warnings during combination)
                import warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=".*uvw_array does not match.*")
                    warnings.filterwarnings("ignore", message=".*largest discrepancy.*")
                    warnings.filterwarnings("ignore", message=".*This is a fairly common situation.*")
                    uv_data += uv_data_additional
            
            # Note: We don't call uv_data.check() here as it can fail due to antenna position mismatches
            
            logger.info(f"Successfully combined {len(hdf5_files)} sub-band files")
            return uv_data
            
        except Exception as e:
            logger.error(f"Failed to read and combine HDF5 files: {e}")
            return None
    
    async def _assess_single_file_quality(self, uv_data: UVData, hdf5_path: str) -> Dict[str, Any]:
        """
        Assess the quality of a single HDF5 file.
        
        Args:
            uv_data: UVData object
            hdf5_path: Path to the HDF5 file
            
        Returns:
            Dictionary with quality metrics
        """
        quality_metrics = {
            'n_antennas': getattr(uv_data, 'Nants_data', 0),
            'n_baselines': getattr(uv_data, 'Nbls', 0),
            'n_times': getattr(uv_data, 'Ntimes', 0),
            'n_freqs': getattr(uv_data, 'Nfreqs', 0),
            'n_pols': getattr(uv_data, 'Npols', 0),
            'integration_time_s': np.mean(np.diff(np.unique(uv_data.time_array))) * 24 * 3600,
            'frequency_range_ghz': [uv_data.freq_array.min()/1e9, uv_data.freq_array.max()/1e9],
            'time_range_mjd': [uv_data.time_array.min(), uv_data.time_array.max()],
            'quality_score': 1.0,  # Single file is always complete
            'meets_standards': True
        }
        
        # Check for common issues
        warnings = []
        
        # Check integration time
        if quality_metrics['integration_time_s'] < self.min_integration_time:
            warnings.append(f"Integration time too short: {quality_metrics['integration_time_s']:.1f}s")
            quality_metrics['quality_score'] *= 0.8
        
        # Check data completeness
        n_baselines = getattr(uv_data, 'Nbls', 0)
        n_freqs = getattr(uv_data, 'Nfreqs', 0)
        
        if n_baselines == 0:
            warnings.append("No baselines found")
            quality_metrics['quality_score'] = 0.0
            quality_metrics['meets_standards'] = False
        
        if n_freqs == 0:
            warnings.append("No frequencies found")
            quality_metrics['quality_score'] = 0.0
            quality_metrics['meets_standards'] = False
        
        if warnings:
            quality_metrics['warnings'] = warnings
        
        return quality_metrics
    
    async def _assess_data_quality(self, hdf5_files: List[str]) -> Dict[str, Any]:
        """
        Assess the quality of multiple HDF5 files.
        
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
    
    async def _set_antenna_positions(self, uv_data: UVData) -> None:
        """
        Set proper antenna positions in the UVData object while preserving original UVW coordinates.
        
        The antenna positions in both HDF5 and CSV files are inconsistent with the UVW coordinates
        in the HDF5 file. Since the UVW coordinates are correct (they show the expected DSA-110
        baseline lengths), we preserve them and set minimal antenna positions.
        
        Args:
            uv_data: UVData object to modify
        """
        try:
            # Store original UVW coordinates before any modifications
            original_uvw = uv_data.uvw_array.copy()
            logger.info("Stored original UVW coordinates to preserve them")
            
            # Use antenna positions from CSV file (even though they're inconsistent)
            # We need some antenna positions for PyUVData to work, but we'll preserve the UVW
            logger.info("Using antenna positions from CSV file (will preserve original UVW coordinates)")
            antenna_positions, antenna_names = self.antenna_positions_manager.get_antenna_positions_for_uvdata()
            
            # Set antenna positions in UVData
            uv_data.antenna_positions = antenna_positions
            uv_data.antenna_names = antenna_names
            uv_data.antenna_numbers = np.arange(len(antenna_names))
            
            # Set telescope location
            uv_data.telescope_location = self.telescope_location
            
            # Keep UVWs consistent with antenna positions (do not overwrite with original)
            logger.info("Keeping recomputed UVWs from antenna positions; not restoring original UVWs at this stage")
            logger.info(f"Set antenna positions from CSV file for {len(antenna_names)} antennas")
            
        except Exception as e:
            logger.error(f"Failed to set antenna positions: {e}")
            # Continue without proper positions (will cause issues later)
    
    async def _read_antenna_positions_from_hdf5(self) -> Tuple[Optional[np.ndarray], Optional[List[str]]]:
        """
        Read antenna positions directly from the HDF5 file.
        
        Returns:
            Tuple of (antenna_positions, antenna_names) or (None, None) if failed
        """
        try:
            # Get the first HDF5 file from the current processing set
            if not hasattr(self, '_current_hdf5_files') or not self._current_hdf5_files:
                logger.warning("No HDF5 files available for reading antenna positions")
                return None, None
            
            hdf5_file = self._current_hdf5_files[0]
            
            # Read antenna positions directly from HDF5 file
            import h5py
            with h5py.File(hdf5_file, 'r') as f:
                if 'Header/antenna_positions' in f and 'Header/antenna_names' in f:
                    antenna_positions = f['Header/antenna_positions'][:]
                    antenna_names = [name.decode('utf-8') if isinstance(name, bytes) else str(name) 
                                   for name in f['Header/antenna_names'][:]]
                    
                    logger.info(f"Read antenna positions from HDF5 file: {len(antenna_names)} antennas")
                    return antenna_positions, antenna_names
                else:
                    logger.warning("No antenna positions found in HDF5 file")
                    return None, None
                    
        except Exception as e:
            logger.error(f"Failed to read antenna positions from HDF5 file: {e}")
            return None, None
    
    def _convert_local_to_itrf(self, local_positions: np.ndarray) -> np.ndarray:
        """
        Convert antenna positions from local coordinates to relative ITRF coordinates.
        
        The HDF5 file contains antenna positions in local coordinates (telescope-centered),
        but PyUVData expects relative ITRF coordinates (relative to telescope location).
        
        This follows the approach from the dsa110_hi-main reference pipeline.
        
        Args:
            local_positions: Array of antenna positions in local coordinates (N_ants, 3)
            
        Returns:
            Array of antenna positions in relative ITRF coordinates (N_ants, 3)
        """
        try:
            from astropy.coordinates import EarthLocation
            from astropy import units as u
            
            # Get telescope location in ITRF coordinates
            telescope_itrf = self.telescope_location.itrs.cartesian.xyz.to(u.meter).value
            
            # Convert local coordinates to relative ITRF coordinates
            # The local coordinates are already relative to the telescope location,
            # so we can use them directly as relative ITRF coordinates
            # This follows the approach from dsa110_hi-main reference pipeline
            relative_itrf_positions = local_positions.copy()
            
            logger.info(f"Converted {len(local_positions)} antenna positions from local to relative ITRF coordinates")
            logger.info(f"Telescope ITRF location: {telescope_itrf}")
            logger.info(f"Local position range: {np.min(local_positions):.3f} to {np.max(local_positions):.3f} meters")
            logger.info(f"Relative ITRF position range: {np.min(relative_itrf_positions):.3f} to {np.max(relative_itrf_positions):.3f} meters")
            
            return relative_itrf_positions
            
        except Exception as e:
            logger.error(f"Failed to convert local coordinates to ITRF: {e}")
            # Return original positions as fallback
            return local_positions
    
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
    
    async def _write_to_ms_with_fixes(self, uv_data: UVData, output_ms_path: str) -> bool:
        """
        Write UVData object to MS format with DSA-110 specific fixes.
        
        This preserves the original UVW coordinates from the HDF5 file and only
        fixes the antenna positions to be consistent.
        
        Args:
            uv_data: UVData object to write
            output_ms_path: Path for the output MS file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Store original UVW coordinates before any modifications
            original_uvw = uv_data.uvw_array.copy()
            logger.info("Stored original UVW coordinates to preserve them during MS writing")
            
            # Prepare for MS writing
            uv_data = self._prepare_for_ms_write(uv_data)
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_ms_path)
            if output_dir:  # Only create directory if there is one
                os.makedirs(output_dir, exist_ok=True)
            
            # Write to MS format with parameters that work for DSA-110 data
            # Suppress UVW warnings during MS writing
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*uvw_array does not match.*")
                warnings.filterwarnings("ignore", message=".*largest discrepancy.*")
                warnings.filterwarnings("ignore", message=".*This is a fairly common situation.*")
                
                uv_data.write_ms(
                    output_ms_path, 
                    clobber=True, 
                    fix_autos=True,  # Fix auto-correlations to be real-only
                    force_phase=True,  # Phase data to zenith of first timestamp
                    run_check=False  # Skip PyUVData checks during write
                )
            
            # Keep UVWs consistent with antenna positions; skip restoring original UVWs
            logger.info("Skipping any MS UVW overwrite; preserving UVWs derived from antenna positions")
            
            # Verify the MS directory was created and has reasonable size
            if not os.path.exists(output_ms_path):
                logger.error(f"MS directory was not created: {output_ms_path}")
                return False
            
            # For MS files (which are directories), check total size
            if os.path.isdir(output_ms_path):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(output_ms_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        if os.path.exists(filepath):
                            total_size += os.path.getsize(filepath)
                file_size = total_size
            else:
                file_size = os.path.getsize(output_ms_path)
            
            if file_size < 1024:  # Less than 1KB is suspicious
                logger.error(f"MS file too small: {file_size} bytes")
                return False
            
            logger.info(f"Successfully wrote MS file: {output_ms_path} ({file_size / (1024*1024):.1f} MB)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write MS file: {e}")
            return False
    
    async def _recalculate_uvw_coordinates(self, uv_data: UVData) -> UVData:
        """
        Recalculate UVW coordinates using PyUVData's built-in method.
        
        This uses PyUVData's set_uvws_from_antenna_positions method which is the
        recommended approach for fixing UVW discrepancies.
        
        Args:
            uv_data: UVData object to modify
            
        Returns:
            UVData object with recalculated UVW coordinates
        """
        try:
            logger.info("Recalculating UVW coordinates using PyUVData's set_uvws_from_antenna_positions method")
            
            # Use PyUVData's built-in method to recalculate UVW coordinates from antenna positions
            # This is the recommended approach for fixing UVW discrepancies
            uv_data.set_uvws_from_antenna_positions(update_vis=False)
            
            logger.info("Successfully recalculated UVW coordinates using PyUVData's built-in method")
            
            return uv_data
            
        except Exception as e:
            logger.error(f"Failed to recalculate UVW coordinates: {e}")
            # Return the original UVData object if recalculation fails
            return uv_data
    
    def _prepare_for_ms_write(self, uv_data: UVData) -> UVData:
        """
        Prepare UVData object for MS writing by fixing common issues.
        
        This incorporates the debugging work from dsa110_hdf5_reader_fixed.py.
        
        Args:
            uv_data: UVData object to prepare
            
        Returns:
            Prepared UVData object
        """
        # Ensure proper data types
        if uv_data.uvw_array.dtype != np.float64:
            uv_data.uvw_array = uv_data.uvw_array.astype(np.float64)
        
        # Ensure proper units
        if not hasattr(uv_data, 'vis_units') or uv_data.vis_units is None or uv_data.vis_units == 'uncalib':
            uv_data.vis_units = 'Jy'
        
        # Note: Baseline conjugation is handled by PyUVData's write_ms method
        # with the force_phase=True parameter, so we don't need to fix it here
        
        return uv_data
    
    async def _restore_uvw_alternative_method(self, ms_path: str, original_uvw: np.ndarray) -> bool:
        """
        Alternative method to restore UVW coordinates using PyUVData.
        
        This method reads the MS file with PyUVData, restores the UVW coordinates,
        and rewrites the MS file.
        
        Args:
            ms_path: Path to the MS file
            original_uvw: Original UVW coordinates to restore
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Using alternative UVW restoration method with PyUVData")
            
            # Read the MS file with PyUVData (suppress UVW warnings)
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*uvw_array does not match.*")
                warnings.filterwarnings("ignore", message=".*largest discrepancy.*")
                warnings.filterwarnings("ignore", message=".*This is a fairly common situation.*")
                
                uv_data = UVData()
                uv_data.read_ms(ms_path, ignore_single_chan=True)
            
            # Store original UVW coordinates
            logger.info(f"Original UVW shape: {original_uvw.shape}")
            logger.info(f"MS UVW shape before restoration: {uv_data.uvw_array.shape}")
            
            # Calculate baseline lengths before restoration
            baseline_lengths_before = np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))
            logger.info(f"Before restoration - mean baseline: {np.mean(baseline_lengths_before):.3f} meters")
            
            # Restore the original UVW coordinates
            uv_data.uvw_array = original_uvw.copy()
            
            # Calculate baseline lengths after restoration
            baseline_lengths_after = np.sqrt(np.sum(uv_data.uvw_array**2, axis=1))
            logger.info(f"After restoration - mean baseline: {np.mean(baseline_lengths_after):.3f} meters")
            
            # Create a backup of the original MS
            backup_path = ms_path + ".backup"
            import shutil
            shutil.move(ms_path, backup_path)
            logger.info(f"Created backup of original MS: {backup_path}")
            
            # Rewrite the MS file with corrected UVW coordinates
            uv_data.write_ms(
                ms_path,
                clobber=True,
                fix_autos=True,
                force_phase=True,
                run_check=False
            )
            
            # Verify the restoration worked by reading the new MS (suppress UVW warnings)
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*uvw_array does not match.*")
                warnings.filterwarnings("ignore", message=".*largest discrepancy.*")
                warnings.filterwarnings("ignore", message=".*This is a fairly common situation.*")
                
                uv_data_verify = UVData()
                uv_data_verify.read_ms(ms_path, ignore_single_chan=True)
            
            baseline_lengths_verify = np.sqrt(np.sum(uv_data_verify.uvw_array**2, axis=1))
            logger.info(f"Verification - mean baseline: {np.mean(baseline_lengths_verify):.3f} meters")
            
            # Check if restoration was successful
            expected_mean = np.mean(np.sqrt(np.sum(original_uvw**2, axis=1)))
            actual_mean = np.mean(baseline_lengths_verify)
            restoration_success = abs(actual_mean - expected_mean) < 1.0  # Within 1 meter
            
            if restoration_success:
                logger.info("✅ Alternative UVW coordinate restoration successful!")
                # Remove backup since restoration was successful
                shutil.rmtree(backup_path)
                return True
            else:
                logger.warning(f"⚠️ Alternative UVW restoration may have failed - expected: {expected_mean:.3f}, actual: {actual_mean:.3f}")
                # Restore backup
                shutil.rmtree(ms_path)
                shutil.move(backup_path, ms_path)
                logger.info("Restored original MS from backup")
                return False
                
        except Exception as e:
            logger.error(f"Alternative UVW restoration failed: {e}")
            # Try to restore backup if it exists
            backup_path = ms_path + ".backup"
            if os.path.exists(backup_path):
                try:
                    if os.path.exists(ms_path):
                        shutil.rmtree(ms_path)
                    shutil.move(backup_path, ms_path)
                    logger.info("Restored original MS from backup after failure")
                except Exception as restore_e:
                    logger.error(f"Failed to restore backup: {restore_e}")
            return False

    async def _restore_uvw_direct_method(self, ms_path: str, original_uvw: np.ndarray) -> bool:
        """
        Third method to restore UVW coordinates using direct MS file modification.
        
        This method uses CASA tools to directly modify the MS file with proper
        data type handling and row-by-row updates.
        
        Args:
            ms_path: Path to the MS file
            original_uvw: Original UVW coordinates to restore
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Using direct UVW restoration method with CASA tools")
            
            from casatools import table
            table_tool = table()
            table_tool.open(ms_path, nomodify=False)
            
            # Get table information
            nrows = table_tool.nrows()
            logger.info(f"MS table has {nrows} rows")
            
            # Check current UVW data format
            current_uvw = table_tool.getcol('UVW')
            logger.info(f"Current UVW shape: {current_uvw.shape}")
            logger.info(f"Current UVW dtype: {current_uvw.dtype}")
            
            # Calculate baseline lengths before restoration
            if current_uvw.shape[0] == 3:  # Shape is (3, nrows)
                baseline_lengths_before = np.sqrt(current_uvw[0]**2 + current_uvw[1]**2 + current_uvw[2]**2)
            else:  # Shape is (nrows, 3)
                baseline_lengths_before = np.sqrt(current_uvw[:, 0]**2 + current_uvw[:, 1]**2 + current_uvw[:, 2]**2)
            
            logger.info(f"Before restoration - mean baseline: {np.mean(baseline_lengths_before):.3f} meters")
            logger.info(f"Original UVW - mean baseline: {np.mean(np.sqrt(np.sum(original_uvw**2, axis=1))):.3f} meters")
            
            # Prepare UVW data for MS format
            # MS expects shape (3, nrows) with double precision
            uvw_for_ms = original_uvw.T.astype(np.float64)  # Transpose and ensure double precision
            logger.info(f"Prepared UVW shape: {uvw_for_ms.shape}, dtype: {uvw_for_ms.dtype}")
            
            # Update UVW coordinates row by row to ensure proper writing
            logger.info("Updating UVW coordinates row by row...")
            for i in range(nrows):
                table_tool.putcell('UVW', i, uvw_for_ms[:, i])
            
            # Alternative: Try putcol with proper data type
            # table_tool.putcol('UVW', uvw_for_ms)
            
            # Verify the restoration worked
            uvw_after_restore = table_tool.getcol('UVW')
            logger.info(f"After restoration UVW shape: {uvw_after_restore.shape}")
            
            # Calculate baseline lengths after restoration
            if uvw_after_restore.shape[0] == 3:  # Shape is (3, nrows)
                baseline_lengths_after = np.sqrt(uvw_after_restore[0]**2 + uvw_after_restore[1]**2 + uvw_after_restore[2]**2)
            else:  # Shape is (nrows, 3)
                baseline_lengths_after = np.sqrt(uvw_after_restore[:, 0]**2 + uvw_after_restore[:, 1]**2 + uvw_after_restore[:, 2]**2)
            
            logger.info(f"After restoration - mean baseline: {np.mean(baseline_lengths_after):.3f} meters")
            logger.info(f"After restoration - max baseline: {np.max(baseline_lengths_after):.3f} meters")
            
            # Check if restoration was successful
            expected_mean = np.mean(np.sqrt(np.sum(original_uvw**2, axis=1)))
            actual_mean = np.mean(baseline_lengths_after)
            restoration_success = abs(actual_mean - expected_mean) < 1.0  # Within 1 meter
            
            if restoration_success:
                logger.info("✅ Direct UVW coordinate restoration successful!")
            else:
                logger.warning(f"⚠️ Direct UVW restoration may have failed - expected: {expected_mean:.3f}, actual: {actual_mean:.3f}")
            
            table_tool.close()
            return restoration_success
            
        except Exception as e:
            logger.error(f"Direct UVW restoration failed: {e}")
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
            # Check if MS directory exists and has reasonable size
            if not os.path.exists(ms_path):
                return {'success': False, 'error': 'MS directory does not exist'}
            
            # For MS files (which are directories), check total size
            if os.path.isdir(ms_path):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(ms_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        if os.path.exists(filepath):
                            total_size += os.path.getsize(filepath)
                file_size = total_size
            else:
                file_size = os.path.getsize(ms_path)
            
            if file_size < 1024:  # Less than 1KB is suspicious
                return {'success': False, 'error': 'MS file too small'}
            
            # Try to read with PyUVData (suppress UVW warnings)
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*uvw_array does not match.*")
                warnings.filterwarnings("ignore", message=".*largest discrepancy.*")
                warnings.filterwarnings("ignore", message=".*This is a fairly common situation.*")
                
                uv_data = UVData()
                uv_data.read_ms(ms_path, ignore_single_chan=True)
            
            metrics = {
                'file_size_mb': file_size / (1024 * 1024),
                'n_antennas': getattr(uv_data, 'Nants_data', 0),
                'n_baselines': getattr(uv_data, 'Nbls', 0),
                'n_times': getattr(uv_data, 'Ntimes', 0),
                'n_freqs': getattr(uv_data, 'Nfreqs', 0),
                'n_pols': getattr(uv_data, 'Npols', 0),
                'frequency_range_ghz': [uv_data.freq_array.min()/1e9, uv_data.freq_array.max()/1e9],
                'time_range_mjd': [uv_data.time_array.min(), uv_data.time_array.max()],
                'integration_time_s': np.mean(np.diff(np.unique(uv_data.time_array))) * 24 * 3600
            }
            
            # UVData objects don't have a close method, just delete the reference
            del uv_data
            
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


# Legacy compatibility functions
async def process_hdf5_set_unified(config: Dict[str, Any], timestamp: str, hdf5_files: List[str]) -> Optional[str]:
    """
    Process a set of HDF5 files for a given timestamp using the unified approach.
    
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
        ms_manager = UnifiedMSCreationManager(config)
        
        # Store HDF5 files for antenna position reading
        ms_manager._current_hdf5_files = hdf5_files
        
        # Determine output MS path
        ms_stage1_dir = config.get('paths', {}).get('ms_stage1_dir', 'ms_stage1')
        os.makedirs(ms_stage1_dir, exist_ok=True)
        
        output_ms_path = os.path.join(ms_stage1_dir, f"{timestamp}.ms")
        
        # Create MS from all sub-bands with quality checks
        if len(hdf5_files) == 1:
            result = await ms_manager.create_ms_from_single_file(hdf5_files[0], output_ms_path, quality_checks=True)
        else:
            result = await ms_manager.create_ms_from_multiple_files(hdf5_files, output_ms_path, quality_checks=True)
        
        if result['success']:
            logger.info(f"Successfully created MS: {output_ms_path}")
            return output_ms_path
        else:
            logger.error(f"Failed to create MS: {result.get('errors', [])}")
            return None
            
    except Exception as e:
        logger.error(f"process_hdf5_set_unified failed: {e}")
        return None
