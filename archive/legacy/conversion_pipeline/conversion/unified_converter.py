"""
Unified HDF5 to MS Converter for DSA-110 Continuum Imaging Pipeline.

This module provides a clean, unified interface for converting HDF5 files to CASA MS,
supporting both single file and multi-subband concatenation workflows.
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Union, Optional
import logging
import functools

import numpy as np
import astropy.units as u
from astropy.time import Time
from pyuvdata import UVData

from .uvh5_to_ms import uvh5_to_ms
from ...utils.ms_io import (
    compute_absolute_antenna_positions,
    write_uvdata_to_ms_via_uvfits,
    populate_unity_model,
)
from ...utils import logging as dsl


class UnifiedHDF5Converter:
    """
    Unified converter for HDF5 files to CASA Measurement Sets.
    
    This class provides a single, consistent interface for:
    - Single file conversion
    - Multi-subband concatenation and conversion
    - Batch processing
    - Metadata extraction
    - Progress monitoring
    
    Parameters
    ----------
    input_dir : str or Path, optional
        Default input directory for HDF5 files
    output_dir : str or Path, optional
        Default output directory for MS files
    logger : logging.Logger, optional
        Logger instance for tracking progress
    """
    
    def __init__(
        self,
        input_dir: Union[str, Path] = '/data/incoming_data',
        output_dir: Optional[Union[str, Path]] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.input_dir = Path(input_dir)
        if output_dir is None:
            output_dir = Path('/data/dsa110-contimg/processed/ms')
        self.output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logger
        if logger is None:
            self.logger = dsl.DsaSyslogger(subsystem_name='converter')
        else:
            self.logger = logger
        
        # Force unbuffered output for real-time progress
        self.print = functools.partial(print, flush=True)
    
    # ============================================================================
    # FILE DISCOVERY AND METADATA
    # ============================================================================
    
    def list_files(self, pattern: str = '*.hdf5', subdir: Optional[Path] = None) -> List[Path]:
        """
        List HDF5 files matching a pattern.
        
        Parameters
        ----------
        pattern : str
            Glob pattern to match files
        subdir : Path, optional
            Subdirectory to search (default: input_dir)
        
        Returns
        -------
        List[Path]
            Sorted list of matching file paths
        """
        search_dir = subdir or self.input_dir
        files = sorted(Path(search_dir).glob(pattern))
        self.logger.info(f"Found {len(files)} files matching '{pattern}' in {search_dir}")
        return files
    
    def get_file_info(self, filepath: Union[str, Path]) -> Dict:
        """
        Extract metadata from an HDF5 file.
        
        Parameters
        ----------
        filepath : str or Path
            Path to the HDF5 file
        
        Returns
        -------
        Dict
            Dictionary containing file metadata
        """
        filepath = self._resolve_path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        self.logger.info(f"Reading metadata from {filepath.name}")
        
        try:
            uvdata = UVData()
            uvdata.read(
                str(filepath),
                file_type='uvh5',
                read_data=False,
                check_extra=False,
                run_check=False,
                run_check_acceptability=False,
                strict_uvw_antpos_check=False,
                fix_old_proj=False,
                fix_use_ant_pos=False
            )
            
            info = {
                'filename': filepath.name,
                'filepath': str(filepath),
                'size_mb': filepath.stat().st_size / (1024 * 1024),
                'nants_data': getattr(uvdata, 'Nants_data', 'N/A'),
                'nants_telescope': getattr(uvdata, 'Nants_telescope', 'N/A'),
                'nbls': getattr(uvdata, 'Nbls', 'N/A'),
                'nblts': getattr(uvdata, 'Nblts', 'N/A'),
                'nfreqs': getattr(uvdata, 'Nfreqs', 'N/A'),
                'npols': getattr(uvdata, 'Npols', 'N/A'),
                'ntimes': getattr(uvdata, 'Ntimes', 'N/A'),
                'freq_range_GHz': (
                    uvdata.freq_array.min() / 1e9,
                    uvdata.freq_array.max() / 1e9
                ) if hasattr(uvdata, 'freq_array') and uvdata.freq_array is not None else 'N/A',
                'channel_width_MHz': uvdata.channel_width / 1e6 if hasattr(uvdata, 'channel_width') else 'N/A',
                'telescope_name': getattr(uvdata, 'telescope_name', 'N/A'),
                'instrument': getattr(uvdata, 'instrument', 'N/A'),
                'phase_type': getattr(uvdata, 'phase_type', 'N/A'),
            }
            
            # Extract timestamp from filename
            try:
                import re
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', filepath.name)
                info['timestamp'] = timestamp_match.group(1) if timestamp_match else 'N/A'
            except Exception:
                info['timestamp'] = 'N/A'
            
            return info
            
        except Exception as e:
            self.logger.error(f"Error reading {filepath.name}: {e}")
            raise
    
    # ============================================================================
    # SINGLE FILE CONVERSION
    # ============================================================================
    
    def convert_single(
        self,
        filepath: Union[str, Path],
        output_name: Optional[str] = None,
        ra: Optional[u.Quantity] = None,
        dec: Optional[u.Quantity] = None,
        dt: Optional[u.Quantity] = None,
        antenna_list: Optional[List[str]] = None,
        fringestop: bool = True,
        overwrite: bool = False
    ) -> Path:
        """
        Convert a single HDF5 file to MS.
        
        Parameters
        ----------
        filepath : str or Path
            Path to the HDF5 file
        output_name : str, optional
            Output MS name (without .ms extension)
        ra, dec : Quantity, optional
            Phase center coordinates
        dt : Quantity, optional
            Duration to extract
        antenna_list : List[str], optional
            Antennas to include
        fringestop : bool
            Whether to apply fringestopping
        overwrite : bool
            Whether to overwrite existing files
        
        Returns
        -------
        Path
            Path to the created MS file
        """
        filepath = self._resolve_path(filepath)
        output_path = self._get_output_path(filepath, output_name)
        ms_path = Path(str(output_path) + '.ms')
        
        if ms_path.exists() and not overwrite:
            self.logger.warning(f"Output exists: {ms_path.name}. Use overwrite=True to replace.")
            return ms_path
        
        self.logger.info(f"Converting single file: {filepath.name} -> {ms_path.name}")
        
        try:
            # Get reference MJD
            refmjd = self._get_reference_mjd(filepath)
            
            # Convert using uvh5_to_ms
            uvh5_to_ms(
                fname_or_uvdata=str(filepath),
                msname=str(output_path),
                refmjd=refmjd,
                ra=ra,
                dec=dec,
                dt=dt,
                antenna_list=antenna_list,
                flux=None,
                fringestop=fringestop,
                logger=self.logger
            )
            
            self.logger.info(f"✓ Successfully created {ms_path.name}")
            return ms_path
            
        except Exception as e:
            self.logger.error(f"✗ Conversion failed for {filepath.name}: {e}")
            raise
    
    # ============================================================================
    # MULTI-SUBBAND CONCATENATION AND CONVERSION
    # ============================================================================
    
    def convert_subbands(
        self,
        file_paths: List[Union[str, Path]],
        output_name: str,
        concatenated_hdf5: Optional[Union[str, Path]] = None,
        ra: Optional[u.Quantity] = None,
        dec: Optional[u.Quantity] = None,
        dt: Optional[u.Quantity] = None,
        antenna_list: Optional[List[str]] = None,
        fringestop: bool = True,
        overwrite: bool = False,
        strategy: str = "parallel-direct",
        workers: int = 4,
        **uvh5_to_ms_kwargs
    ) -> Dict:
        """Concatenate multiple sub-band files and convert to MS via UVFITS."""
        overall_start = time.time()
        result: Dict = {
            'success': False,
            'ms_path': None,
            'concatenated_hdf5': None,
            'elapsed': 0.0,
            'num_subbands': len(file_paths),
            'error': None
        }

        populate_model = uvh5_to_ms_kwargs.pop('populate_model', False)
        model_value = uvh5_to_ms_kwargs.pop('model_value', 1.0 + 0j)
        keep_uvfits = uvh5_to_ms_kwargs.pop('keep_uvfits', False)
        if uvh5_to_ms_kwargs:
            self.logger.debug(
                "Unused conversion kwargs ignored: %s", list(uvh5_to_ms_kwargs.keys())
            )

        if strategy not in {"concat-uvdata", "uvfits", "parallel-direct"}:
            self.logger.warning(
                "Unknown strategy '%s'; defaulting to parallel-direct conversion", strategy
            )
            strategy = "parallel-direct"

        if strategy == "parallel-direct":
            return self.convert_subbands_streaming(
                file_paths,
                output_name,
                ra=ra,
                dec=dec,
                dt=dt,
                antenna_list=antenna_list,
                fringestop=fringestop,
                overwrite=overwrite,
                workers=workers,
                **uvh5_to_ms_kwargs,
            )

        try:
            self.logger.info("=" * 70)
            self.logger.info("COMBINING SUB-BANDS VIA UVFITS PIPELINE")
            self.logger.info("=" * 70)

            # Step 1: read and merge all sub-band UVData objects
            uvdata_combined = self._concatenate_subbands(file_paths)

            if concatenated_hdf5:
                concatenated_hdf5 = Path(concatenated_hdf5)
                concatenated_hdf5.parent.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Saving concatenated UVH5 to {concatenated_hdf5}")
                uvdata_combined.write_uvh5(str(concatenated_hdf5), clobber=True, fix_autos=True)
                result['concatenated_hdf5'] = str(concatenated_hdf5)

            output_path = self.output_dir / output_name
            ms_path = Path(str(output_path) + '.ms')

            if ms_path.exists() and not overwrite:
                self.logger.warning(
                    f"Output exists: {ms_path.name}. Use overwrite=True to replace."
                )
                result['ms_path'] = str(ms_path)
                result['success'] = True
                result['elapsed'] = time.time() - overall_start
                return result

            # Step 2: derive absolute antenna positions and write via UVFITS
            antenna_positions = compute_absolute_antenna_positions(
                uvdata_combined,
                logger=self.logger,
            )

            write_uvdata_to_ms_via_uvfits(
                uvdata_combined,
                str(ms_path),
                antenna_positions=antenna_positions,
                overwrite=overwrite,
                keep_uvfits=keep_uvfits,
                logger=self.logger,
            )

            if populate_model:
                populate_unity_model(
                    ms_path,
                    uvdata_combined,
                    value=model_value,
                    logger=self.logger,
                )

            result['success'] = True
            result['ms_path'] = str(ms_path)
            result['elapsed'] = time.time() - overall_start

            self.logger.info("=" * 70)
            self.logger.info("CONVERSION SUCCESSFUL")
            self.logger.info("=" * 70)
            self.logger.info(f"Total elapsed time: {result['elapsed']:.2f} seconds")
            self.logger.info(f"Output MS: {result['ms_path']}")

        except Exception as e:
            result['error'] = str(e)
            result['elapsed'] = time.time() - overall_start
            self.logger.error(f"✗ Conversion failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return result
    
    def convert_subbands_streaming(
        self,
        file_paths: List[Union[str, Path]],
        output_name: str,
        ra: Optional[u.Quantity] = None,
        dec: Optional[u.Quantity] = None,
        dt: Optional[u.Quantity] = None,
        antenna_list: Optional[List[str]] = None,
        fringestop: bool = True,
        overwrite: bool = False,
        workers: int = 4,
        **uvh5_to_ms_kwargs
    ) -> Dict:
        """
        Convert sub-bands using a highly parallelized, direct-to-MS strategy.
        
        This method creates exactly one MS for all sub-bands without generating
        per-subband intermediate files. It parallelizes the CPU-intensive
        processing (reading, fringestopping) of each sub-band and then
        serially writes the results into a single, pre-allocated MS file.
        This approach is designed to be significantly faster and more memory-
        efficient than concatenating large UVData objects.
        
        Parameters
        ----------
        file_paths : List[Union[str, Path]]
            List of HDF5 file paths to convert
        output_name : str
            Output MS name (without .ms extension)
        ra, dec : Quantity, optional
            Phase center coordinates
        dt : Quantity, optional
            Duration to extract
        antenna_list : List[str], optional
            Antennas to include
        fringestop : bool
            Whether to apply fringestopping
        overwrite : bool
            Whether to overwrite existing files
        workers : int
            Number of parallel workers
        **uvh5_to_ms_kwargs
            Additional arguments passed to the conversion process
        
        Returns
        -------
        Dict
            Result dictionary with success status, paths, timing, etc.
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed
        import multiprocessing as mp
        
        overall_start = time.time()
        result: Dict = {
            'success': False,
            'ms_path': None,
            'elapsed': 0.0,
            'num_subbands': len(file_paths),
            'error': None,
            'strategy': 'parallel-direct'
        }
        
        try:
            self.logger.info("="*70)
            self.logger.info("PARALLEL DIRECT-TO-MS CONVERSION")
            self.logger.info("="*70)
            self.logger.info(f"Processing {len(file_paths)} sub-bands with {workers} workers")
            
            # Step 1: Preflight metadata validation from all sub-band headers
            self.logger.info("Step 1: Validating metadata across all sub-bands...")
            metadata = self._validate_subband_metadata(file_paths)
            
            # Step 2: Create a single, empty MS structure that can hold all sub-bands
            self.logger.info("Step 2: Pre-creating full MS structure...")
            output_path = self.output_dir / output_name
            ms_path = Path(str(output_path) + '.ms')
            
            if ms_path.exists() and not overwrite:
                self.logger.warning(f"Output exists: {ms_path.name}. Use overwrite=True to replace.")
                result['ms_path'] = str(ms_path)
                result['success'] = True
                result['elapsed'] = time.time() - overall_start
                return result
            
            # Create the full MS structure using the combined metadata
            self._create_ms_structure_full(
                str(output_path), metadata, ra, dec, antenna_list
            )
            
            # Step 3: Parallel preprocessing of sub-bands and serial writing to the MS
            self.logger.info("Step 3: Starting parallel sub-band processing...")
            self._process_subbands_parallel(
                file_paths, str(output_path), metadata, workers,
                ra, dec, dt, antenna_list, fringestop, **uvh5_to_ms_kwargs
            )
            
            result['success'] = True
            result['ms_path'] = str(ms_path)
            result['elapsed'] = time.time() - overall_start
            
            self.logger.info("="*70)
            self.logger.info("PARALLEL CONVERSION SUCCESSFUL")
            self.logger.info("="*70)
            self.logger.info(f"Total elapsed time: {result['elapsed']:.2f} seconds")
            self.logger.info(f"Output MS: {result['ms_path']}")
            
        except Exception as e:
            result['error'] = str(e)
            result['elapsed'] = time.time() - overall_start
            self.logger.error(f"✗ Parallel conversion failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        return result
    
    # ============================================================================
    # BATCH PROCESSING
    # ============================================================================
    
    def convert_batch(
        self,
        pattern: str = '*.hdf5',
        max_files: Optional[int] = None,
        subdir: Optional[Path] = None,
        **kwargs
    ) -> List[Path]:
        """
        Convert multiple files in batch.
        
        Parameters
        ----------
        pattern : str
            Glob pattern to match files
        max_files : int, optional
            Maximum number of files to process
        subdir : Path, optional
            Subdirectory to search
        **kwargs
            Additional arguments for convert_single
        
        Returns
        -------
        List[Path]
            List of created MS file paths
        """
        files = self.list_files(pattern, subdir)
        
        if max_files is not None:
            files = files[:max_files]
        
        self.logger.info(f"Batch converting {len(files)} files...")
        
        converted = []
        failed = []
        
        for i, filepath in enumerate(files, 1):
            try:
                self.logger.info(f"[{i}/{len(files)}] Processing {filepath.name}")
                ms_path = self.convert_single(filepath, **kwargs)
                converted.append(ms_path)
            except Exception as e:
                self.logger.error(f"✗ Failed to convert {filepath.name}: {e}")
                failed.append(filepath)
        
        self.logger.info(f"Batch conversion complete: {len(converted)} succeeded, {len(failed)} failed")
        
        if failed:
            self.logger.warning(f"Failed files: {[f.name for f in failed]}")
        
        return converted
    
    # ============================================================================
    # STREAMING STRATEGY HELPER METHODS
    # ============================================================================
    
    def _validate_subband_metadata(self, file_paths: List[Union[str, Path]]) -> Dict:
        """Validate metadata consistency across all sub-band files."""
        self.logger.info("Reading minimal headers for metadata validation...")
        
        metadata_list = []
        for i, fpath in enumerate(file_paths):
            fpath = self._resolve_path(fpath)
            self.logger.info(f"  Reading metadata from {fpath.name}...")
            
            uvdata = UVData()
            uvdata.read(
                str(fpath),
                file_type='uvh5',
                read_data=False,
                check_extra=False,
                run_check=False,
                run_check_acceptability=False,
                strict_uvw_antpos_check=False,
                fix_old_proj=False,
                fix_use_ant_pos=False
            )
            
            metadata = {
                'filepath': str(fpath),
                'filename': fpath.name,
                'nants_data': uvdata.Nants_data,
                'nants_telescope': uvdata.Nants_telescope,
                'nbls': uvdata.Nbls,
                'nblts': uvdata.Nblts,
                'nfreqs': uvdata.Nfreqs,
                'npols': uvdata.Npols,
                'ntimes': uvdata.Ntimes,
                'freq_array': uvdata.freq_array,
                'channel_width': float(uvdata.channel_width[0]) if hasattr(uvdata.channel_width, '__len__') and len(uvdata.channel_width) > 0 else float(uvdata.channel_width),
                'telescope_name': getattr(uvdata.telescope, 'name', 'DSA-110') if hasattr(uvdata, 'telescope') and uvdata.telescope else 'DSA-110',
                'instrument': getattr(uvdata, 'instrument', 'DSA-110'),
                'phase_type': getattr(uvdata, 'phase_type', 'drift'),
                'time_array': uvdata.time_array,
                'antenna_names': getattr(uvdata, 'antenna_names', []),
                'antenna_numbers': getattr(uvdata, 'antenna_numbers', []),
                'antenna_positions': getattr(uvdata, 'antenna_positions', np.array([])),
            }
            metadata_list.append(metadata)
        
        # Validate consistency
        self.logger.info("Validating metadata consistency...")
        ref_metadata = metadata_list[0]
        
        for i, metadata in enumerate(metadata_list[1:], 1):
            # Check critical parameters
            if metadata['nants_data'] != ref_metadata['nants_data']:
                raise ValueError(f"Sub-band {i}: Nants_data mismatch")
            if metadata['npols'] != ref_metadata['npols']:
                raise ValueError(f"Sub-band {i}: Npols mismatch")
            if metadata['ntimes'] != ref_metadata['ntimes']:
                raise ValueError(f"Sub-band {i}: Ntimes mismatch")
            if metadata['telescope_name'] != ref_metadata['telescope_name']:
                raise ValueError(f"Sub-band {i}: telescope_name mismatch")
        
        # Build combined frequency array
        freq_arrays = [m['freq_array'] for m in metadata_list]
        if freq_arrays[0].ndim == 1:
            # 1D frequency arrays
            combined_freq_array = np.concatenate(freq_arrays, axis=0)
            combined_freq_array = np.sort(combined_freq_array)
            # Reshape to 2D for consistency
            combined_freq_array = combined_freq_array.reshape(1, -1)
        else:
            # 2D frequency arrays
            combined_freq_array = np.concatenate(freq_arrays, axis=1)
            combined_freq_array = np.sort(combined_freq_array, axis=1)
        
        # Build combined metadata
        combined_metadata = ref_metadata.copy()
        combined_metadata['nfreqs'] = combined_freq_array.shape[1]
        combined_metadata['freq_array'] = combined_freq_array
        combined_metadata['channel_width'] = ref_metadata['channel_width']  # Should be same for all
        
        self.logger.info(f"✓ Metadata validation passed")
        self.logger.info(f"  Total frequencies: {combined_metadata['nfreqs']}")
        self.logger.info(f"  Frequency range: {combined_freq_array.min()/1e9:.3f} - {combined_freq_array.max()/1e9:.3f} GHz")
        
        return combined_metadata
    
    def _create_ms_structure_full(
        self, 
        ms_path: str, 
        metadata: Dict, 
        ra: Optional[u.Quantity] = None,
        dec: Optional[u.Quantity] = None,
        antenna_list: Optional[List[str]] = None
    ):
        """Create full MS structure with all 16 sub-bands."""
        from ...utils.ms_io import create_ms_structure_full
        
        self.logger.info(f"Creating MS structure: {ms_path}")
        
        # Calculate reference MJD
        refmjd = np.mean(Time(metadata['time_array'], format='jd').mjd)
        
        # Create MS structure
        create_ms_structure_full(
            ms_path=ms_path,
            nants=metadata['nants_telescope'],
            nfreqs=metadata['nfreqs'],
            npols=metadata['npols'],
            ntimes=metadata['ntimes'],
            freq_array=metadata['freq_array'],
            channel_width=metadata['channel_width'],
            antenna_names=metadata['antenna_names'],
            antenna_numbers=metadata['antenna_numbers'],
            antenna_positions=metadata['antenna_positions'],
            telescope_name=metadata['telescope_name'],
            refmjd=refmjd,
            ra=ra,
            dec=dec,
            antenna_list=antenna_list,
            logger=self.logger
        )
        
        self.logger.info("✓ MS structure created successfully")
    
    def _process_subbands_parallel(
        self,
        file_paths: List[Union[str, Path]],
        ms_path: str,
        metadata: Dict,
        workers: int,
        ra: Optional[u.Quantity] = None,
        dec: Optional[u.Quantity] = None,
        dt: Optional[u.Quantity] = None,
        antenna_list: Optional[List[str]] = None,
        fringestop: bool = True,
        **uvh5_to_ms_kwargs
    ):
        """Process sub-bands in parallel and write to single MS."""
        from concurrent.futures import ProcessPoolExecutor, as_completed
        import multiprocessing as mp
        
        self.logger.info(f"Starting parallel processing with {workers} workers...")
        
        # Sort files by sub-band number to process them in a predictable order
        sorted_paths = self._sort_by_subband(file_paths)
        
        # Calculate the reference MJD from the first sub-band, to be used by all workers
        refmjd = self._get_reference_mjd(sorted_paths[0])
        self.logger.info(f"Using reference MJD {refmjd} for all sub-bands.")
        
        # Prepare arguments for each worker process
        worker_args = []
        for i, fpath in enumerate(sorted_paths):
            args = (
                str(fpath),
                ra,
                dec,
                dt,
                antenna_list,
                fringestop,
                i,  # subband_index
                metadata['nfreqs'],
                metadata['freq_array'],
                refmjd, # Pass the reference MJD to each worker
            )
            worker_args.append(args)
        
        # Process in parallel using a ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks to the executor
            future_to_index = {
                executor.submit(self._preprocess_subband_worker, *args): i 
                for i, args in enumerate(worker_args)
            }
            
            # Collect results as they are completed
            results = [None] * len(worker_args)
            completed = 0
            
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                    completed += 1
                    self.logger.info(f"Completed sub-band {index+1}/{len(worker_args)}")
                except Exception as e:
                    self.logger.error(f"Sub-band {index+1} failed: {e}")
                    raise
            
            # After all workers are done, write the collected results to the MS
            self.logger.info("All sub-bands processed. Writing to MS...")
            self._write_results_to_ms(ms_path, results, metadata)

    def _preprocess_subband_worker(
        self,
        filepath: str,
        ra: Optional[u.Quantity],
        dec: Optional[u.Quantity],
        dt: Optional[u.Quantity],
        antenna_list: Optional[List[str]],
        fringestop: bool,
        subband_index: int,
        total_nfreqs: int,
        freq_array: np.ndarray,
        refmjd: float,
    ) -> Dict:
        """Worker function for preprocessing a single sub-band."""
        import os
        import numpy as np
        from pyuvdata import UVData
        from .uvh5_to_ms import load_uvh5_file, phase_visibilities, fix_descending_missing_freqs
        
        # Set thread limits for worker to avoid contention
        os.environ['OMP_NUM_THREADS'] = '1'
        os.environ['MKL_NUM_THREADS'] = '1'
        
        try:
            # Load the sub-band file
            uvdata, pt_dec, phase_ra, phase_dec = load_uvh5_file(
                filepath,
                antenna_list=antenna_list,
                dt=dt,
                phase_ra=ra,
                phase_dec=dec
            )
            
            # Fringestop and phase the data in-memory
            if fringestop:
                phase_visibilities(
                    uvdata,
                    phase_ra,
                    phase_dec,
                    fringestop=True,
                    interpolate_uvws=True, # Use faster, interpolated UVW calculation
                    refmjd=refmjd
                )
            
            # Ensure frequency axis is ascending and correct
            fix_descending_missing_freqs(uvdata)
            
            # Extract necessary data arrays and reshape for direct writing
            # The expected shape for writing is (nblts, npols, nfreqs)
            vis_data = uvdata.data_array.transpose(0, 2, 1) # (nblts, npols, nfreqs)
            flag_data = uvdata.flag_array.transpose(0, 2, 1)
            nsample_data = uvdata.nsample_array.transpose(0, 2, 1)
            
            # Determine the channel mapping for this sub-band
            subband_freqs = uvdata.freq_array.squeeze()
            channel_start = np.searchsorted(freq_array.squeeze(), subband_freqs[0])
            channel_count = len(subband_freqs)
            
            return {
                'subband_index': subband_index,
                'vis_data': vis_data,
                'channel_start': channel_start,
                'channel_count': channel_count,
                'time_array': uvdata.time_array,
                'uvw_array': uvdata.uvw_array,
                'flag_array': flag_data,
                'nsample_array': nsample_data,
                'ant_1_array': uvdata.ant_1_array,
                'ant_2_array': uvdata.ant_2_array,
            }
            
        except Exception as e:
            raise RuntimeError(f"Worker for {os.path.basename(filepath)} failed: {e}")
    
    def _write_results_to_ms(self, ms_path: str, results: List[Dict], metadata: Dict):
        """Write preprocessed results to MS in channel order."""
        from ...utils.ms_io import append_channels_to_ms
        
        self.logger.info("Writing results to MS in channel order...")
        
        # Sort results by channel_start to ensure proper ordering
        sorted_results = sorted(results, key=lambda x: x['channel_start'])
        
        for i, result in enumerate(sorted_results):
            self.logger.info(f"Writing sub-band {i+1}/{len(sorted_results)} "
                           f"(channels {result['channel_start']}-{result['channel_start']+result['channel_count']-1})")
            
            # Append channels to MS
            append_channels_to_ms(
                ms_path=ms_path,
                vis_chunk=result['vis_data'],
                chan_start=result['channel_start'],
                chan_count=result['channel_count'],
                time_array=result['time_array'],
                uvw_array=result['uvw_array'],
                flag_array=result['flag_array'],
                nsample_array=result['nsample_array'],
                ant_1_array=result['ant_1_array'],
                ant_2_array=result['ant_2_array'],
                logger=self.logger
            )
        
        self.logger.info("✓ All data written to MS successfully")
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def _merge_uvdata_subbands(self, uvdata_list: List[UVData]) -> UVData:
        """Merge multiple UVData sub-band objects along frequency axis."""
        if not uvdata_list:
            raise ValueError("No UVData objects provided for merging")

        combined = uvdata_list[0]

        def _flatten_freq(uvd: UVData) -> np.ndarray:
            freq = uvd.freq_array
            if freq.ndim == 2:
                if freq.shape[0] != 1:
                    raise ValueError("Expected each sub-band to have a single spectral window")
                freq = freq[0]
            return freq

        base_freq = _flatten_freq(combined)
        if not np.all(np.diff(base_freq) > 0):
            raise ValueError("Frequency axis of first sub-band must be strictly increasing")

        channel_width = np.median(np.diff(base_freq)) if base_freq.size > 1 else None

        base_time = combined.time_array
        base_ant1 = combined.ant_1_array
        base_ant2 = combined.ant_2_array
        base_npols = combined.Npols

        for idx, uvd in enumerate(uvdata_list[1:], start=1):
            freq = _flatten_freq(uvd)
            if not np.all(np.diff(freq) > 0):
                raise ValueError(f"Frequency axis in sub-band {idx} is not strictly increasing")

            if channel_width is not None and freq.size > 1:
                new_width = np.median(np.diff(freq))
                if not np.isclose(new_width, channel_width, rtol=1e-6, atol=1e3):
                    raise ValueError(
                        f"Channel width mismatch between sub-bands: {channel_width} vs {new_width}"
                    )

            if uvd.Npols != base_npols:
                raise ValueError("Polarization count differs across sub-bands")

            if uvd.time_array.shape != base_time.shape or not np.allclose(uvd.time_array, base_time):
                raise ValueError("Time arrays differ across sub-bands; cannot concatenate")

            if not np.array_equal(uvd.ant_1_array, base_ant1) or not np.array_equal(uvd.ant_2_array, base_ant2):
                raise ValueError("Baseline ordering differs across sub-bands")

            if base_freq[-1] >= freq[0]:
                raise ValueError("Sub-band frequencies overlap or are unsorted; expected strictly increasing order")

            combined = combined.fast_concat(
                uvd,
                axis='freq',
                inplace=False,
                run_check=False,
                check_extra=False,
                run_check_acceptability=False
            )
            base_freq = _flatten_freq(combined)

        return combined

    def _load_subband_uvdata(self, filepath: Path) -> UVData:
        """Load a UVH5 sub-band into a UVData instance with dtype normalization."""
        uvdata = UVData()
        cache_overrides = {
            'HDF5_CACHE_BYTES': str(64 * 1024 * 1024),  # 64 MiB chunk cache
            'HDF5_CACHE_NELEMS': '2048',
            'HDF5_CACHE_PREEMPTION': '0.75',
        }
        original_cache = {}

        try:
            for key, value in cache_overrides.items():
                if key not in os.environ:
                    original_cache[key] = None
                    os.environ[key] = value
                else:
                    original_cache[key] = os.environ[key]
                    os.environ[key] = value

            uvdata.read(
                str(filepath),
                file_type='uvh5',
                check_extra=False,
                run_check=False,
                run_check_acceptability=False,
                strict_uvw_antpos_check=False,
                fix_old_proj=False,
                fix_use_ant_pos=False,
                data_array_dtype=np.complex64,
                nsample_array_dtype=np.float32,
            )
        finally:
            for key, original in original_cache.items():
                if original is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original

        # Normalize dtypes for downstream processing consistency
        uvdata.uvw_array = uvdata.uvw_array.astype(np.float64, copy=False)
        uvdata.integration_time = uvdata.integration_time.astype(np.float64, copy=False)
        uvdata.data_array = uvdata.data_array.astype(np.complex64, copy=False)
        if uvdata.nsample_array is not None:
            uvdata.nsample_array = uvdata.nsample_array.astype(np.float32, copy=False)
        if uvdata.flag_array is not None:
            uvdata.flag_array = uvdata.flag_array.astype(np.bool_, copy=False)

        # Ensure frequency axis is ascending so concatenation checks succeed
        freq_array = uvdata.freq_array
        if freq_array.ndim == 2:
            freq_axis = freq_array[0]
            freq_axis_dim = 1
        else:
            freq_axis = freq_array
            freq_axis_dim = 0

        if freq_axis.size > 1:
            diffs = np.diff(freq_axis)
            if np.any(diffs <= 0):
                self.logger.debug(
                    f"Frequency axis not strictly increasing in {filepath.name}; sorting channels"
                )

                sorted_idx = np.argsort(freq_axis)

                uvdata.freq_array = np.take(freq_array, sorted_idx, axis=freq_axis_dim)

                channel_width = getattr(uvdata, 'channel_width', None)
                if channel_width is not None and np.ndim(channel_width) > 0:
                    uvdata.channel_width = np.take(channel_width, sorted_idx, axis=-1)

                def _reorder_on_freq(array):
                    if array is None:
                        return None
                    reordered = np.take(array, sorted_idx, axis=-2)
                    return reordered.copy()

                uvdata.data_array = _reorder_on_freq(uvdata.data_array)
                if uvdata.flag_array is not None:
                    uvdata.flag_array = _reorder_on_freq(uvdata.flag_array)
                if uvdata.nsample_array is not None:
                    uvdata.nsample_array = _reorder_on_freq(uvdata.nsample_array)

                freq_axis_sorted = (
                    uvdata.freq_array[0]
                    if uvdata.freq_array.ndim == 2
                    else uvdata.freq_array
                )
                if np.any(np.diff(freq_axis_sorted) <= 0):
                    raise ValueError(
                        f"Frequency axis contains duplicate or unsorted channels in {filepath.name}"
                    )

        return uvdata
    
    def _resolve_path(self, filepath: Union[str, Path]) -> Path:
        """Resolve file path relative to input_dir if not absolute."""
        filepath = Path(filepath)
        if not filepath.is_absolute():
            filepath = self.input_dir / filepath
        return filepath
    
    def _get_output_path(self, filepath: Path, output_name: Optional[str] = None) -> Path:
        """Get output path for MS file."""
        if output_name is None:
            output_name = filepath.stem
        return self.output_dir / output_name
    
    def _get_reference_mjd(self, filepath: Path) -> float:
        """Get reference MJD from HDF5 file."""
        uvdata = UVData()
        uvdata.read(
            str(filepath),
            file_type='uvh5',
            read_data=False,
            check_extra=False,
            run_check=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
            fix_old_proj=False,
            fix_use_ant_pos=False
        )
        return np.mean(Time(uvdata.time_array, format='jd').mjd)
    
    def _concatenate_subbands(self, file_paths: List[Union[str, Path]]) -> UVData:
        """
        Concatenate multiple sub-band files along frequency axis.
        
        Uses optimized pyuvdata multi-file reading with axis='freq'.
        """
        self.logger.info(f"Concatenating {len(file_paths)} sub-band files...")
        start_time = time.time()
        
        # Sort files by sub-band number
        file_paths_sorted = self._sort_by_subband(file_paths)
        
        # Read files individually with dtype fixes, then concatenate
        self.logger.info("Reading files individually with dtype fixes...")
        self.print("Starting file reading...")
        uvdata_list = []
        
        for i, fpath in enumerate(file_paths_sorted):
            fpath = self._resolve_path(fpath)
            self.print(f"Reading file {i+1}/{len(file_paths_sorted)}: {fpath.name}")

            uvd = self._load_subband_uvdata(fpath)
            uvdata_list.append(uvd)
            self.print(f"  ✓ File {i+1} read successfully")

        # Ensure sub-bands are ordered by increasing starting frequency
        freq_starts = []
        for idx, uvd in enumerate(uvdata_list):
            freq = uvd.freq_array
            if freq.ndim == 2:
                freq = freq[0]
            freq_starts.append((float(freq.min()), idx))

        order = [idx for _, idx in sorted(freq_starts)]
        if order != list(range(len(uvdata_list))):
            self.logger.info(
                "Detected non-monotonic sub-band frequency order; sorting by frequency"
            )
            uvdata_list = [uvdata_list[idx] for idx in order]
            file_paths_sorted = [file_paths_sorted[idx] for idx in order]
            self.logger.info("  Reordered sub-bands (low → high freq):")
            for rank, fpath in enumerate(file_paths_sorted, start=1):
                self.logger.info(f"    {rank:02d}: {fpath.name}")

        combined_uvdata = self._merge_uvdata_subbands(uvdata_list)

        elapsed = time.time() - start_time
        self.logger.info(f"Concatenation complete in {elapsed:.2f} seconds")
        self.logger.info("Final combined dataset:")
        self.logger.info(f"  Shape: {combined_uvdata.data_array.shape}")
        self.logger.info(f"  Nfreqs: {combined_uvdata.Nfreqs}")
        freq_min = combined_uvdata.freq_array.min() / 1e9
        freq_max = combined_uvdata.freq_array.max() / 1e9
        self.logger.info(f"  Freq range: {freq_min:.3f} - {freq_max:.3f} GHz")

        return combined_uvdata
    
    def _sort_by_subband(self, file_paths: List[Union[str, Path]]) -> List[Path]:
        """Sort file paths by sub-band number."""
        def extract_subband(path):
            """Extract sub-band number from filename like '2025-10-03T11:48:56_sb02.hdf5'"""
            name = Path(path).name
            try:
                sb_idx = name.index('_sb')
                sb_str = name[sb_idx+3:sb_idx+5]  # Get 2 digits
                return int(sb_str)
            except (ValueError, IndexError):
                self.logger.warning(f"Could not extract sub-band from {name}, using 0")
                return 0
        
        sorted_paths = sorted([Path(p) for p in file_paths], key=extract_subband)
        
        # Log the sorted order
        self.logger.info("Sub-band ordering:")
        for path in sorted_paths:
            sb = extract_subband(path)
            self.logger.info(f"  sb{sb:02d}: {path.name}")
        
        return sorted_paths
    
    def verify_ms(self, ms_path: Union[str, Path]) -> bool:
        """
        Verify that a Measurement Set was created correctly.
        
        Parameters
        ----------
        ms_path : str or Path
            Path to the MS file to verify
        
        Returns
        -------
        bool
            True if MS is valid, False otherwise
        """
        ms_path = Path(ms_path)
        
        if not ms_path.exists():
            self.logger.error(f"MS does not exist: {ms_path}")
            return False
        
        try:
            # Basic check: MS should be a directory with table structure
            if not ms_path.is_dir():
                self.logger.error(f"MS is not a directory: {ms_path}")
                return False
            
            # Check for essential tables
            required_tables = ['ANTENNA', 'DATA_DESCRIPTION', 'FEED', 
                             'FIELD', 'OBSERVATION', 'SPECTRAL_WINDOW']
            
            for table in required_tables:
                table_path = ms_path / table
                if not table_path.exists():
                    self.logger.error(f"Missing required table {table} in {ms_path}")
                    return False
            
            self.logger.info(f"✓ MS verification passed: {ms_path.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Error verifying MS {ms_path.name}: {e}")
            return False


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def convert_single_file(
    filepath: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    **kwargs
) -> Path:
    """
    Convenience function to convert a single file.
    
    Parameters
    ----------
    filepath : str or Path
        Path to the HDF5 file
    output_dir : str or Path, optional
        Output directory for MS file
    **kwargs
        Additional arguments for convert_single
    
    Returns
    -------
    Path
        Path to the created MS file
    """
    converter = UnifiedHDF5Converter(output_dir=output_dir)
    return converter.convert_single(filepath, **kwargs)


def convert_subband_group(
    file_paths: List[Union[str, Path]],
    output_name: str,
    output_dir: Optional[Union[str, Path]] = None,
    **kwargs
) -> Dict:
    """
    Convenience function to convert a group of sub-band files.
    
    Parameters
    ----------
    file_paths : List[Union[str, Path]]
        List of HDF5 file paths
    output_name : str
        Output MS name
    output_dir : str or Path, optional
        Output directory for MS file
    **kwargs
        Additional arguments for convert_subbands
    
    Returns
    -------
    Dict
        Result dictionary
    """
    converter = UnifiedHDF5Converter(output_dir=output_dir)
    return converter.convert_subbands(file_paths, output_name, **kwargs)
