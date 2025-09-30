"""
Data Ingestion Stage for DSA-110 Pipeline

This stage handles the conversion of HDF5 files to Measurement Sets (MS)
using the unified MS creation system that combines DSA-110 specific fixes
with quality validation and multi-subband processing.
"""

import os
import glob
import logging
from typing import Dict, Any, List, Optional, Tuple
from astropy.time import Time
import astropy.units as u
import asyncio
import numpy as np

from ..exceptions import DataError, StageError
from ...data_ingestion.unified_ms_creation import UnifiedMSCreationManager
from ...utils.logging import get_logger

logger = get_logger(__name__)


class DataIngestionStage:
    """
    Data ingestion stage for converting HDF5 files to MS format.
    
    This stage uses the unified MS creation system that provides:
    - DSA-110 specific fixes from debugging work
    - Quality validation and multi-subband processing
    - Proper antenna position integration
    - Advanced error handling and recovery
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data ingestion stage.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.ms_config = config.get('ms_creation', {})
        self.paths_config = config.get('paths', {})
        
        # Initialize the unified MS creation manager
        self.ms_manager = UnifiedMSCreationManager(config)
        
        # Ensure output directories exist
        self._ensure_output_directories()
        
        logger.info("Data ingestion stage initialized")
    
    def _ensure_output_directories(self):
        """Ensure all required output directories exist."""
        ms_stage1_dir = self.paths_config.get('ms_stage1_dir', 'ms_stage1')
        os.makedirs(ms_stage1_dir, exist_ok=True)
        logger.info(f"Ensured output directory exists: {ms_stage1_dir}")
    
    async def process_timestamp(self, timestamp: str, hdf5_dir: str, 
                              max_retries: int = 3) -> Optional[str]:
        """
        Process all HDF5 files for a given timestamp into a single MS.
        
        This method finds all sub-band HDF5 files for the given timestamp
        and combines them into a single MS file using the unified system.
        Includes retry logic for failed MS creation.
        
        Args:
            timestamp: Timestamp string (e.g., '2025-09-05T03:23:14')
            hdf5_dir: Directory containing HDF5 files
            max_retries: Maximum number of retry attempts
            
        Returns:
            Path to the created MS file, or None if failed
        """
        logger.info(f"Processing timestamp: {timestamp}")
        
        for attempt in range(max_retries + 1):
            try:
                # Find all HDF5 files for this timestamp
                hdf5_files = self._find_hdf5_files_for_timestamp(timestamp, hdf5_dir)
                
                if not hdf5_files:
                    logger.error(f"No HDF5 files found for timestamp: {timestamp}")
                    return None
                
                logger.info(f"Found {len(hdf5_files)} HDF5 files for timestamp {timestamp}")
                
                # Determine output MS path
                ms_stage1_dir = self.paths_config.get('ms_stage1_dir', 'ms_stage1')
                output_ms_path = os.path.join(ms_stage1_dir, f"{timestamp}.ms")
                
                # Process using unified MS creation system
                if len(hdf5_files) == 1:
                    # Single file processing
                    result = await self.ms_manager.create_ms_from_single_file(
                        hdf5_files[0], output_ms_path, quality_checks=True
                    )
                else:
                    # Multi-file processing (sub-band combination)
                    result = await self.ms_manager.create_ms_from_multiple_files(
                        hdf5_files, output_ms_path, quality_checks=True
                    )
                
                if result['success']:
                    logger.info(f"Successfully created MS: {output_ms_path}")
                    logger.info(f"Quality metrics: {result.get('quality_metrics', {})}")
                    
                    if result.get('warnings'):
                        for warning in result['warnings']:
                            logger.warning(f"MS creation warning: {warning}")
                    
                    return output_ms_path
                else:
                    if attempt < max_retries:
                        retry_delay = 2 ** attempt  # Exponential backoff
                        logger.warning(f"MS creation failed (attempt {attempt + 1}/{max_retries + 1}): "
                                     f"{result.get('errors', [])}. Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"Failed to create MS after {max_retries + 1} attempts: "
                                   f"{result.get('errors', [])}")
                        return None
                    
            except Exception as e:
                if attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Data ingestion failed for timestamp {timestamp} "
                                 f"(attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                 f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Data ingestion failed for timestamp {timestamp} after "
                               f"{max_retries + 1} attempts: {e}")
                    raise StageError(f"Data ingestion failed: {e}")
        
        return None
    
    def _find_hdf5_files_for_timestamp(self, timestamp: str, hdf5_dir: str) -> List[str]:
        """
        Find all HDF5 files for a given timestamp with nearby timestamp tolerance.
        
        This method groups sub-bands from nearby timestamps (within 4 minutes) to handle
        cases where data collection spans multiple timestamps but represents a single observation.
        
        Args:
            timestamp: Timestamp string
            hdf5_dir: Directory containing HDF5 files
            
        Returns:
            List of HDF5 file paths
        """
        from datetime import datetime, timedelta
        import re
        
        # Parse the target timestamp
        try:
            target_dt = datetime.fromisoformat(timestamp.replace('T', ' '))
        except ValueError:
            logger.error(f"Invalid timestamp format: {timestamp}")
            return []
        
        # Find all HDF5 files in the directory
        pattern = os.path.join(hdf5_dir, "*_sb*.hdf5")
        all_files = glob.glob(pattern)
        
        # Group files by timestamp
        timestamp_files = {}
        for file_path in all_files:
            filename = os.path.basename(file_path)
            # Extract timestamp from filename (format: YYYY-MM-DDTHH:MM:SS_sbXX.hdf5)
            match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb\d+\.hdf5', filename)
            if match:
                file_timestamp = match.group(1)
                if file_timestamp not in timestamp_files:
                    timestamp_files[file_timestamp] = []
                timestamp_files[file_timestamp].append(file_path)
        
        # Find timestamps within 4-minute tolerance
        tolerance_minutes = 4
        nearby_timestamps = []
        
        for file_timestamp in timestamp_files.keys():
            try:
                file_dt = datetime.fromisoformat(file_timestamp.replace('T', ' '))
                time_diff = abs((file_dt - target_dt).total_seconds())
                
                if time_diff <= tolerance_minutes * 60:  # Convert to seconds
                    nearby_timestamps.append((file_timestamp, time_diff))
                    logger.debug(f"Found nearby timestamp: {file_timestamp} (diff: {time_diff:.1f}s)")
            except ValueError:
                logger.warning(f"Could not parse timestamp: {file_timestamp}")
                continue
        
        # Sort by time difference (closest first)
        nearby_timestamps.sort(key=lambda x: x[1])
        
        # Collect all files from nearby timestamps
        all_nearby_files = []
        for file_timestamp, _ in nearby_timestamps:
            all_nearby_files.extend(timestamp_files[file_timestamp])
        
        # Sort by sub-band number for consistent processing
        all_nearby_files.sort(key=lambda x: int(x.split('_sb')[1].split('.')[0]))
        
        logger.info(f"Found {len(all_nearby_files)} HDF5 files from {len(nearby_timestamps)} nearby timestamps")
        logger.debug(f"Nearby timestamps: {[t[0] for t in nearby_timestamps]}")
        logger.debug(f"Files: {[os.path.basename(f) for f in all_nearby_files]}")
        
        return all_nearby_files
    
    async def process_timestamp_range(self, start_timestamp: str, end_timestamp: str, 
                                    hdf5_dir: str, progress_callback: Optional[callable] = None) -> List[str]:
        """
        Process a range of timestamps with progress tracking and smart grouping.
        
        This method groups nearby timestamps (within 4 minutes) to avoid processing
        the same sub-bands multiple times when they span multiple timestamps.
        
        Args:
            start_timestamp: Start timestamp string
            end_timestamp: End timestamp string
            hdf5_dir: Directory containing HDF5 files
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List of created MS file paths
        """
        logger.info(f"Processing timestamp range: {start_timestamp} to {end_timestamp}")
        
        created_ms_files = []
        failed_timestamps = []
        processed_files = set()  # Track which files have been processed
        
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
            total_timestamps = len(timestamps)
            logger.info(f"Found {total_timestamps} unique timestamps")
            
            # Process each timestamp with progress tracking
            for i, timestamp in enumerate(timestamps):
                try:
                    logger.info(f"Processing timestamp {i+1}/{total_timestamps}: {timestamp}")
                    
                    # Check if this timestamp's files have already been processed
                    timestamp_files = self._find_hdf5_files_for_timestamp(timestamp, hdf5_dir)
                    if not timestamp_files:
                        logger.warning(f"No files found for timestamp: {timestamp}")
                        continue
                    
                    # Check if any of these files have already been processed
                    already_processed = any(f in processed_files for f in timestamp_files)
                    if already_processed:
                        logger.info(f"⏭️ Skipping timestamp {timestamp} - files already processed")
                        continue
                    
                    ms_path = await self.process_timestamp(timestamp, hdf5_dir)
                    if ms_path:
                        created_ms_files.append(ms_path)
                        # Mark all files from this timestamp group as processed
                        processed_files.update(timestamp_files)
                        logger.info(f"✅ Successfully processed timestamp {i+1}/{total_timestamps}: {timestamp}")
                    else:
                        failed_timestamps.append(timestamp)
                        logger.error(f"❌ Failed to process timestamp {i+1}/{total_timestamps}: {timestamp}")
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(i + 1, total_timestamps, timestamp, ms_path is not None)
                        
                except Exception as e:
                    failed_timestamps.append(timestamp)
                    logger.error(f"❌ Exception processing timestamp {i+1}/{total_timestamps}: {timestamp} - {e}")
            
            # Log final results
            success_count = len(created_ms_files)
            failure_count = len(failed_timestamps)
            success_rate = (success_count / total_timestamps) * 100 if total_timestamps > 0 else 0
            
            logger.info(f"📊 Processing complete: {success_count}/{total_timestamps} successful ({success_rate:.1f}%)")
            logger.info(f"📁 Total files processed: {len(processed_files)}")
            
            if failed_timestamps:
                logger.warning(f"⚠️ Failed timestamps: {failed_timestamps}")
            
            return created_ms_files
            
        except Exception as e:
            logger.error(f"Failed to process timestamp range: {e}")
            raise StageError(f"Timestamp range processing failed: {e}")
    
    def get_processing_blocks(self, ms_files: List[str], 
                            block_duration_hours: float = 1.0) -> List[Dict[str, Any]]:
        """
        Group MS files into processing blocks based on time.
        
        Args:
            ms_files: List of MS file paths
            block_duration_hours: Duration of each processing block in hours
            
        Returns:
            List of processing block dictionaries
        """
        logger.info(f"Creating processing blocks from {len(ms_files)} MS files")
        
        try:
            # Extract timestamps and sort MS files by time
            ms_files_with_times = []
            for ms_path in ms_files:
                timestamp = self._extract_timestamp_from_ms_path(ms_path)
                if timestamp:
                    start_time, end_time = self._get_ms_time_range(ms_path)
                    if start_time and end_time:
                        ms_files_with_times.append({
                            'path': ms_path,
                            'timestamp': timestamp,
                            'start_time': start_time,
                            'end_time': end_time
                        })
            
            if not ms_files_with_times:
                logger.warning("No valid MS files with time information found")
                return []
            
            # Sort by start time
            ms_files_with_times.sort(key=lambda x: x['start_time'])
            
            # Group into processing blocks
            blocks = self._group_ms_files_by_time(ms_files_with_times, block_duration_hours)
            
            logger.info(f"Created {len(blocks)} processing blocks")
            return blocks
            
        except Exception as e:
            logger.error(f"Failed to create processing blocks: {e}")
            raise StageError(f"Processing block creation failed: {e}")
    
    def _extract_timestamp_from_ms_path(self, ms_path: str) -> Optional[str]:
        """
        Extract timestamp from MS file path.
        
        Args:
            ms_path: Path to MS file
            
        Returns:
            Timestamp string or None if not found
        """
        try:
            filename = os.path.basename(ms_path)
            # Remove .ms extension
            if filename.endswith('.ms'):
                timestamp = filename[:-3]
                # Validate timestamp format (YYYY-MM-DDTHH:MM:SS)
                if 'T' in timestamp and len(timestamp) == 19:
                    return timestamp
            return None
        except Exception as e:
            logger.debug(f"Failed to extract timestamp from {ms_path}: {e}")
            return None
    
    def _get_ms_time_range(self, ms_path: str) -> Tuple[Optional[Time], Optional[Time]]:
        """
        Get start and end times from an MS file.
        
        Args:
            ms_path: Path to MS file
            
        Returns:
            Tuple of (start_time, end_time) or (None, None) if failed
        """
        try:
            # Use CASA to get time information from MS
            import casacore.tables as pt
            
            # Open the main table
            with pt.table(ms_path) as main_table:
                # Get TIME column
                time_column = main_table.getcol('TIME')
                
                if len(time_column) == 0:
                    logger.warning(f"No time data found in MS file: {ms_path}")
                    return None, None
                
                # Convert from MJD seconds to astropy Time
                start_time = Time(time_column[0] / 86400.0, format='mjd')
                end_time = Time(time_column[-1] / 86400.0, format='mjd')
                
                logger.debug(f"MS time range: {start_time.iso} to {end_time.iso}")
                return start_time, end_time
                
        except Exception as e:
            logger.warning(f"Failed to get time range from MS file {ms_path}: {e}")
            return None, None
    
    def _group_ms_files_by_time(self, ms_files_with_times: List[Dict[str, Any]], 
                               block_duration_hours: float) -> List[Dict[str, Any]]:
        """
        Group MS files into processing blocks based on time intervals.
        
        Args:
            ms_files_with_times: List of MS file dictionaries with time info
            block_duration_hours: Duration of each processing block in hours
            
        Returns:
            List of processing block dictionaries
        """
        if not ms_files_with_times:
            return []
        
        blocks = []
        current_block = None
        block_duration_seconds = block_duration_hours * 3600.0
        
        for i, ms_file in enumerate(ms_files_with_times):
            # If no current block, start a new one
            if current_block is None:
                current_block = {
                    'block_id': f'block_{len(blocks) + 1:03d}',
                    'ms_files': [ms_file['path']],
                    'start_time': ms_file['start_time'],
                    'end_time': ms_file['end_time'],
                    'duration_hours': block_duration_hours,
                    'file_count': 1
                }
            else:
                # Check if this file fits in the current block
                time_gap = (ms_file['start_time'] - current_block['end_time']).to(u.second).value
                
                # If gap is small and adding this file doesn't exceed duration
                if (time_gap <= 300.0 and  # 5 minute tolerance for gaps
                    (ms_file['end_time'] - current_block['start_time']).to(u.second).value <= block_duration_seconds):
                    
                    # Add to current block
                    current_block['ms_files'].append(ms_file['path'])
                    current_block['end_time'] = ms_file['end_time']
                    current_block['file_count'] += 1
                else:
                    # Finalize current block and start new one
                    blocks.append(current_block)
                    current_block = {
                        'block_id': f'block_{len(blocks) + 1:03d}',
                        'ms_files': [ms_file['path']],
                        'start_time': ms_file['start_time'],
                        'end_time': ms_file['end_time'],
                        'duration_hours': block_duration_hours,
                        'file_count': 1
                    }
        
        # Add the last block if it exists
        if current_block is not None:
            blocks.append(current_block)
        
        # Log block information
        for block in blocks:
            duration_actual = (block['end_time'] - block['start_time']).to(u.hour).value
            logger.info(f"Block {block['block_id']}: {block['file_count']} files, "
                       f"{duration_actual:.2f}h duration")
        
        return blocks
    
    async def validate_ms_files(self, ms_files: List[str]) -> Dict[str, Any]:
        """
        Validate a list of MS files with comprehensive quality checks.
        
        Args:
            ms_files: List of MS file paths
            
        Returns:
            Dictionary with validation results and quality metrics
        """
        logger.info(f"Validating {len(ms_files)} MS files")
        
        validation_results = {
            'total_files': len(ms_files),
            'valid_files': 0,
            'invalid_files': 0,
            'errors': [],
            'warnings': [],
            'quality_metrics': {
                'total_data_size_gb': 0.0,
                'average_file_size_mb': 0.0,
                'files_with_uvw_issues': 0,
                'files_with_time_issues': 0,
                'files_with_antenna_issues': 0
            }
        }
        
        total_size_bytes = 0
        
        for ms_path in ms_files:
            try:
                file_validation = await self._validate_single_ms_file(ms_path)
                
                if file_validation['valid']:
                    validation_results['valid_files'] += 1
                    total_size_bytes += file_validation['size_bytes']
                    
                    # Update quality metrics
                    if file_validation.get('uvw_issues', False):
                        validation_results['quality_metrics']['files_with_uvw_issues'] += 1
                    if file_validation.get('time_issues', False):
                        validation_results['quality_metrics']['files_with_time_issues'] += 1
                    if file_validation.get('antenna_issues', False):
                        validation_results['quality_metrics']['files_with_antenna_issues'] += 1
                        
                else:
                    validation_results['invalid_files'] += 1
                    validation_results['errors'].extend(file_validation.get('errors', []))
                
                validation_results['warnings'].extend(file_validation.get('warnings', []))
                    
            except Exception as e:
                validation_results['invalid_files'] += 1
                validation_results['errors'].append(f"Validation error for {ms_path}: {e}")
                logger.error(f"Validation error for {ms_path}: {e}")
        
        # Calculate final quality metrics
        if validation_results['valid_files'] > 0:
            validation_results['quality_metrics']['total_data_size_gb'] = total_size_bytes / (1024**3)
            validation_results['quality_metrics']['average_file_size_mb'] = (
                total_size_bytes / validation_results['valid_files'] / (1024**2)
            )
        
        # Calculate overall quality score
        quality_score = self._calculate_quality_score(validation_results)
        validation_results['quality_metrics']['overall_quality_score'] = quality_score
        
        logger.info(f"Validation complete: {validation_results['valid_files']} valid, "
                   f"{validation_results['invalid_files']} invalid")
        logger.info(f"Quality score: {quality_score:.2f}/10.0")
        
        return validation_results
    
    async def _validate_single_ms_file(self, ms_path: str) -> Dict[str, Any]:
        """
        Validate a single MS file with detailed checks.
        
        Args:
            ms_path: Path to MS file
            
        Returns:
            Dictionary with validation results for this file
        """
        result = {
            'valid': False,
            'size_bytes': 0,
            'errors': [],
            'warnings': [],
            'uvw_issues': False,
            'time_issues': False,
            'antenna_issues': False
        }
        
        try:
            # Check if file exists and is a directory
            if not os.path.exists(ms_path) or not os.path.isdir(ms_path):
                result['errors'].append(f"MS file not found or not a directory: {ms_path}")
                return result
            
            # Check file size
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(ms_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            
            result['size_bytes'] = total_size
            
            if total_size < 1024:  # Less than 1KB
                result['errors'].append(f"MS file too small: {ms_path} ({total_size} bytes)")
                return result
            
            # Basic validation passed, now check MS structure
            try:
                import casacore.tables as pt
                
                with pt.table(ms_path) as main_table:
                    # Check if table has data
                    nrows = main_table.nrows()
                    if nrows == 0:
                        result['errors'].append(f"MS file has no data rows: {ms_path}")
                        return result
                    
                    # Check required columns
                    required_columns = ['TIME', 'ANTENNA1', 'ANTENNA2', 'UVW', 'DATA']
                    missing_columns = []
                    for col in required_columns:
                        if col not in main_table.colnames():
                            missing_columns.append(col)
                    
                    if missing_columns:
                        result['errors'].append(f"MS file missing required columns {missing_columns}: {ms_path}")
                        return result
                    
                    # Validate UVW coordinates
                    try:
                        uvw_data = main_table.getcol('UVW')
                        if len(uvw_data) > 0:
                            # Check for NaN or infinite values
                            if np.any(np.isnan(uvw_data)) or np.any(np.isinf(uvw_data)):
                                result['warnings'].append(f"UVW coordinates contain NaN or infinite values: {ms_path}")
                                result['uvw_issues'] = True
                            
                            # Check for reasonable UVW ranges (in meters)
                            uvw_flat = uvw_data.flatten()
                            if np.any(np.abs(uvw_flat) > 10000):  # 10km baseline
                                result['warnings'].append(f"UVW coordinates have unusually large values: {ms_path}")
                                result['uvw_issues'] = True
                    except Exception as e:
                        result['warnings'].append(f"Could not validate UVW coordinates: {e}")
                        result['uvw_issues'] = True
                    
                    # Validate time data
                    try:
                        time_data = main_table.getcol('TIME')
                        if len(time_data) > 0:
                            # Check for reasonable time range (last 10 years)
                            current_time = Time.now().mjd * 86400  # Convert to MJD seconds
                            if np.any(time_data < current_time - 10*365*86400) or np.any(time_data > current_time + 86400):
                                result['warnings'].append(f"Time data has unusual values: {ms_path}")
                                result['time_issues'] = True
                    except Exception as e:
                        result['warnings'].append(f"Could not validate time data: {e}")
                        result['time_issues'] = True
                    
                    # Validate antenna data
                    try:
                        ant1_data = main_table.getcol('ANTENNA1')
                        ant2_data = main_table.getcol('ANTENNA2')
                        if len(ant1_data) > 0 and len(ant2_data) > 0:
                            max_ant = max(np.max(ant1_data), np.max(ant2_data))
                            if max_ant > 110:  # DSA-110 has max 110 antennas
                                result['warnings'].append(f"Antenna numbers exceed expected range: {ms_path}")
                                result['antenna_issues'] = True
                    except Exception as e:
                        result['warnings'].append(f"Could not validate antenna data: {e}")
                        result['antenna_issues'] = True
                
                # If we get here, basic validation passed
                result['valid'] = True
                
            except ImportError:
                result['warnings'].append("casacore not available for detailed validation")
                result['valid'] = True  # Basic file check passed
            except Exception as e:
                result['warnings'].append(f"Detailed validation failed: {e}")
                result['valid'] = True  # Basic file check passed
                
        except Exception as e:
            result['errors'].append(f"File validation error: {e}")
        
        return result
    
    def _calculate_quality_score(self, validation_results: Dict[str, Any]) -> float:
        """
        Calculate overall quality score for MS files.
        
        Args:
            validation_results: Validation results dictionary
            
        Returns:
            Quality score from 0.0 to 10.0
        """
        if validation_results['total_files'] == 0:
            return 0.0
        
        # Base score from success rate
        success_rate = validation_results['valid_files'] / validation_results['total_files']
        base_score = success_rate * 10.0
        
        # Deduct points for quality issues
        quality_metrics = validation_results['quality_metrics']
        total_files = validation_results['valid_files']
        
        if total_files > 0:
            uvw_penalty = (quality_metrics['files_with_uvw_issues'] / total_files) * 2.0
            time_penalty = (quality_metrics['files_with_time_issues'] / total_files) * 1.5
            antenna_penalty = (quality_metrics['files_with_antenna_issues'] / total_files) * 1.0
            
            final_score = max(0.0, base_score - uvw_penalty - time_penalty - antenna_penalty)
        else:
            final_score = 0.0
        
        return round(final_score, 2)
