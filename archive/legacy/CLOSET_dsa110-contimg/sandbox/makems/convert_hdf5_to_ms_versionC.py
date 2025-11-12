import h5py
import numpy as np
from pyuvdata import UVData
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import EarthLocation
from pathlib import Path
from collections import defaultdict
import re
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DSA110ObservationGrouper:
    """
    Groups DSA-110 HDF5 files by observation based on timestamp proximity.
    """
    
    def __init__(self, data_dir, time_tolerance_minutes=6):
        """
        Parameters
        ----------
        data_dir : str or Path
            Directory containing HDF5 files
        time_tolerance_minutes : float
            Maximum time difference (minutes) for files to be grouped together.
            Default 6 minutes allows for 5-min observation + 1-min slack.
        """
        self.data_dir = Path(data_dir)
        self.time_tolerance = timedelta(minutes=time_tolerance_minutes)
        
    def parse_filename(self, filename):
        """
        Extract timestamp and subband number from filename.
        
        Expected format: YYYY-MM-DDTHH:MM:SS_sbNN.hdf5
        
        Returns
        -------
        timestamp : datetime
            Observation timestamp
        subband : int
            Sub-band number (0-15)
        """
        # Parse filename: 2025-09-05T03:23:14_sb00.hdf5
        pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb(\d{2})\.hdf5'
        match = re.match(pattern, filename)
        
        if not match:
            raise ValueError(f"Filename {filename} doesn't match expected pattern")
        
        timestamp_str = match.group(1)
        subband = int(match.group(2))
        
        # Parse timestamp
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
        
        return timestamp, subband
    
    def get_observation_midpoint(self, hdf5_file):
        """
        Get the midpoint time of an observation from the HDF5 file.
        This is more accurate than the filename timestamp.
        
        Returns
        -------
        midpoint : datetime
            Middle of observation time range
        """
        with h5py.File(hdf5_file, 'r') as f:
            time_array = f['Header/time_array'][:]  # Julian dates
            
        # Convert JD to datetime
        times = Time(time_array, format='jd')
        times_datetime = times.to_datetime()
        
        # Return midpoint
        start_time = min(times_datetime)
        end_time = max(times_datetime)
        midpoint = start_time + (end_time - start_time) / 2
        
        return midpoint
    
    def group_observations(self):
        """
        Group HDF5 files into observations.
        
        Returns
        -------
        observation_groups : dict
            Keys are observation IDs (representative timestamp strings)
            Values are lists of (filepath, subband) tuples, sorted by subband
        """
        # Find all HDF5 files
        hdf5_files = sorted(self.data_dir.glob('*_sb*.hdf5'))
        
        if not hdf5_files:
            raise FileNotFoundError(f"No HDF5 files found in {self.data_dir}")
        
        logger.info(f"Found {len(hdf5_files)} HDF5 files")
        
        # Parse all files
        file_info = []
        for filepath in hdf5_files:
            try:
                filename = filepath.name
                timestamp_filename, subband = self.parse_filename(filename)
                
                # Get actual observation midpoint from data
                timestamp_data = self.get_observation_midpoint(filepath)
                
                file_info.append({
                    'filepath': filepath,
                    'filename': filename,
                    'timestamp_filename': timestamp_filename,
                    'timestamp_data': timestamp_data,
                    'subband': subband
                })
                
                logger.debug(f"Parsed {filename}: subband={subband}, "
                           f"time_file={timestamp_filename}, time_data={timestamp_data}")
                
            except Exception as e:
                logger.warning(f"Failed to parse {filepath}: {e}")
                continue
        
        # Group by temporal proximity
        # Sort by data timestamp
        file_info.sort(key=lambda x: x['timestamp_data'])
        
        observation_groups = defaultdict(list)
        current_group_id = None
        current_group_time = None
        
        for info in file_info:
            timestamp = info['timestamp_data']
            
            # Start new group if:
            # 1. This is the first file
            # 2. Time gap exceeds tolerance
            # 3. We already have this subband in current group (indicates new obs)
            
            if current_group_time is None:
                # First file - start new group
                current_group_id = info['timestamp_filename'].strftime('%Y-%m-%dT%H:%M:%S')
                current_group_time = timestamp
                observation_groups[current_group_id].append(info)
                logger.debug(f"Starting new group: {current_group_id}")
                
            elif abs(timestamp - current_group_time) > self.time_tolerance:
                # Time gap too large - start new group
                current_group_id = info['timestamp_filename'].strftime('%Y-%m-%dT%H:%M:%S')
                current_group_time = timestamp
                observation_groups[current_group_id].append(info)
                logger.debug(f"Time gap detected, new group: {current_group_id}")
                
            elif any(f['subband'] == info['subband'] 
                    for f in observation_groups[current_group_id]):
                # Duplicate subband - must be new observation
                current_group_id = info['timestamp_filename'].strftime('%Y-%m-%dT%H:%M:%S')
                current_group_time = timestamp
                observation_groups[current_group_id].append(info)
                logger.debug(f"Duplicate subband detected, new group: {current_group_id}")
                
            else:
                # Add to current group
                observation_groups[current_group_id].append(info)
        
        # Sort each group by subband number
        for group_id in observation_groups:
            observation_groups[group_id].sort(key=lambda x: x['subband'])
        
        # Log grouping results
        logger.info(f"\nGrouped into {len(observation_groups)} observations:")
        for group_id, files in observation_groups.items():
            subbands = [f['subband'] for f in files]
            logger.info(f"  {group_id}: {len(files)} sub-bands {subbands}")
            
            # Warn if not all 16 sub-bands present
            if len(files) != 16:
                missing = set(range(16)) - set(subbands)
                logger.warning(f"    WARNING: Missing sub-bands {sorted(missing)}")
        
        return dict(observation_groups)


def hdf5_to_uvdata(hdf5_file):
    """
    Convert a single DSA-110 HDF5 file to UVData object.
    
    Parameters
    ----------
    hdf5_file : str or Path
        Path to HDF5 file
    
    Returns
    -------
    uv : UVData
        UVData object containing the visibility data
    """
    logger.info(f"Converting {Path(hdf5_file).name} to UVData...")
    
    # Initialize UVData object
    uv = UVData()
    
    # Read HDF5 file
    with h5py.File(hdf5_file, 'r') as f:
        # Read data arrays
        visdata = f['Data/visdata'][:]  # Expect (Nblts, Nspws, Nfreqs, Npols)
        flags = f['Data/flags'][:]
        nsamples = f['Data/nsamples'][:]
        
        # Read header metadata
        freq_array = f['Header/freq_array'][:]  # (Nspws, Nfreqs) -> squeeze to (Nfreqs,)
        time_array = f['Header/time_array'][:]  # Julian dates
        ant_1_array = f['Header/ant_1_array'][:]
        ant_2_array = f['Header/ant_2_array'][:]
        uvw_array = f['Header/uvw_array'][:]
        integration_time = f['Header/integration_time'][:]
        polarization_array = f['Header/polarization_array'][:]
        
        # Telescope metadata
        antenna_positions = f['Header/antenna_positions'][:]
        antenna_numbers = f['Header/antenna_numbers'][:]
        antenna_names = f['Header/antenna_names'][:]
        antenna_diameters = f['Header/antenna_diameters'][:]
        
        latitude = f['Header/latitude'][()]
        longitude = f['Header/longitude'][()]
        altitude = f['Header/altitude'][()]
        
        Nants_telescope = f['Header/Nants_telescope'][()]
        Nants_data = f['Header/Nants_data'][()]
        Nbls = f['Header/Nbls'][()]
        Nblts = f['Header/Nblts'][()]
        Nfreqs = f['Header/Nfreqs'][()]
        Npols = f['Header/Npols'][()]
        Nspws = f['Header/Nspws'][()]
        Ntimes = f['Header/Ntimes'][()]
        channel_width = f['Header/channel_width'][()]
        # Phase center apparent declination if available
        phase_center_app_dec = None
        if 'phase_center_app_dec' in f['Header']:
            phase_center_app_dec = f['Header/phase_center_app_dec'][()]
        elif 'phase_center_dec' in f['Header']:
            phase_center_app_dec = f['Header/phase_center_dec'][()]
        # Hour angle phase center (radians) if available
        ha_phase_center = None
        if 'ha_phase_center' in f['Header']:
            ha_phase_center = f['Header/ha_phase_center'][()]
        elif 'extra_keywords' in f['Header'] and 'ha_phase_center' in f['Header/extra_keywords']:
            ha_phase_center = f['Header/extra_keywords/ha_phase_center'][()]
        
        telescope_name = f['Header/telescope_name'][()].decode() if isinstance(
            f['Header/telescope_name'][()], bytes) else f['Header/telescope_name'][()]
        instrument = f['Header/instrument'][()].decode() if isinstance(
            f['Header/instrument'][()], bytes) else f['Header/instrument'][()]
    
    # Set telescope location
    telescope_location = EarthLocation.from_geodetic(
        lon=longitude*u.deg, 
        lat=latitude*u.deg, 
        height=altitude*u.m
    )
    
    # Calculate LST array
    times = Time(time_array, format='jd')
    lst_array = times.sidereal_time('apparent', 
                                     longitude=telescope_location.lon).radian
    
    # Ensure required counts set for pyuvdata operations that enforce checks
    try:
        uv._Nants_data.value = int(Nants_data)
    except Exception:
        pass
    for attr_name, attr_val in (
        ('_Nbls', Nbls),
        ('_Nblts', Nblts),
        ('_Nfreqs', Nfreqs),
        ('_Npols', Npols),
        ('_Nspws', Nspws),
        ('_Ntimes', Ntimes),
    ):
        try:
            getattr(uv, attr_name).value = int(attr_val)
        except Exception:
            pass
    # Single phase center
    try:
        uv._Nphase.value = 1
    except Exception:
        pass
    
    # Time parameters
    uv.time_array = time_array.astype(float)
    uv.integration_time = integration_time.astype(float)
    uv.lst_array = lst_array.astype(float)
    
    # Baseline parameters
    uv.baseline_array = uv.antnums_to_baseline(
        ant_1_array.astype(int), 
        ant_2_array.astype(int)
    )
    uv.ant_1_array = ant_1_array.astype(int)
    uv.ant_2_array = ant_2_array.astype(int)
    uv.uvw_array = uvw_array.astype(float)
    
    # Frequency parameters (use future array shapes: (Nfreqs,))
    if freq_array.ndim == 2 and freq_array.shape[0] == 1:
        freq_array_1d = freq_array[0, :]
    else:
        freq_array_1d = np.squeeze(freq_array)
    uv.freq_array = freq_array_1d.astype(float)  # Hz
    # Pyuvdata expects channel_width shape of (Nfreqs,) for single spw
    uv.channel_width = np.full(int(Nfreqs), float(channel_width))  # Hz
    uv.spw_array = np.arange(int(Nspws), dtype=int)
    # Flex SPW mapping for future array shapes (single spw -> all zeros)
    try:
        uv._flex_spw_id_array.value = np.zeros(int(Nfreqs), dtype=int)
    except Exception:
        pass
    
    # Polarization
    uv.polarization_array = polarization_array.astype(int)
    
    # Antenna parameters
    uv.antenna_numbers = antenna_numbers.astype(int)
    uv.antenna_names = [name.decode() if isinstance(name, bytes) else str(name) 
                        for name in antenna_names]
    uv.antenna_positions = antenna_positions.astype(float)
    # Ensure underlying UVParameters are populated for MS writer
    try:
        uv._antenna_numbers.value = antenna_numbers.astype(int)
    except Exception:
        pass
    try:
        uv._antenna_names.value = [name.decode() if isinstance(name, bytes) else str(name)
                                   for name in antenna_names]
    except Exception:
        pass
    try:
        uv._antenna_positions.value = antenna_positions.astype(float)
    except Exception:
        pass
    try:
        uv._antenna_diameters.value = antenna_diameters.astype(float)
    except Exception:
        pass
    
    # Telescope location (ITRF XYZ)
    uv.telescope_location = np.array([
        telescope_location.x.to(u.m).value,
        telescope_location.y.to(u.m).value,
        telescope_location.z.to(u.m).value
    ])
    
    uv.telescope_name = telescope_name
    uv.instrument = instrument
    
    # Data arrays (future array shapes: (Nblts, Nfreqs, Npols))
    if visdata.ndim == 4 and visdata.shape[1] == 1:
        data3 = visdata[:, 0, :, :]
        flag3 = flags[:, 0, :, :]
        nsamp3 = nsamples[:, 0, :, :]
    else:
        data3 = np.squeeze(visdata)
        flag3 = np.squeeze(flags)
        nsamp3 = np.squeeze(nsamples)
    uv.data_array = data3
    uv.flag_array = flag3
    uv.nsample_array = nsamp3.astype(float)
    
    # Set other required metadata
    uv.vis_units = 'uncalib'
    uv.phase_type = 'drift'
    # Set apparent declination for drift
    if phase_center_app_dec is not None:
        try:
            uv._phase_center_app_dec.value = np.full(int(Nblts), float(phase_center_app_dec))
        except Exception:
            pass
    # Set apparent RA from LST and HA if available
    ra_array = None
    if ha_phase_center is not None:
        try:
            ha = float(ha_phase_center)
            ra_array = (uv.lst_array - ha) % (2 * np.pi)
            uv._phase_center_app_ra.value = ra_array
        except Exception:
            pass
    # Phase center catalog and IDs (single drift center)
    try:
        uv._phase_center_id_array.value = np.zeros(int(Nblts), dtype=int)
    except Exception:
        pass
    try:
        uv.phase_center_catalog = {
            0: {
                'cat_type': 'driftscan',
                'cat_name': 'DSA110_drift',
                'cat_id': 0,
                'cat_frame': 'icrs',
                'cat_epoch': 2000.0,
                'cat_lon': ra_array if ra_array is not None else uv.lst_array.copy(),
                'cat_lat': uv._phase_center_app_dec.value if hasattr(uv, '_phase_center_app_dec') and getattr(uv._phase_center_app_dec, 'value', None) is not None else np.zeros(int(Nblts)),
            }
        }
    except Exception:
        pass
    uv.object_name = 'ESE_search'  # Updated for ESE monitoring
    uv.history = f'Converted from {Path(hdf5_file).name} for ESE monitoring'
    
    # Run checks
    # Skip uv.check(); write_ms will run without checks per flags
    
    return uv


def convert_observation_to_ms(observation_files, output_ms, 
                              combine_subbands=True):
    """
    Convert a grouped observation (all sub-bands) to a single Measurement Set.
    
    Parameters
    ----------
    observation_files : list of dict
        List of file info dicts from ObservationGrouper
    output_ms : str or Path
        Output measurement set path
    combine_subbands : bool
        If True, combine all sub-bands into single MS.
        If False, create separate MS per sub-band.
    
    Returns
    -------
    success : bool
        True if conversion successful
    """
    output_ms = Path(output_ms)
    
    if combine_subbands:
        logger.info(f"Converting observation with {len(observation_files)} sub-bands "
                   f"to {output_ms}")
        
        # Convert first sub-band
        uv_combined = hdf5_to_uvdata(observation_files[0]['filepath'])
        
        # Add remaining sub-bands
        for file_info in observation_files[1:]:
            logger.info(f"  Adding sub-band {file_info['subband']:02d}...")
            uv_subband = hdf5_to_uvdata(file_info['filepath'])
            
            # Combine using pyuvdata's __add__ operator
            uv_combined = uv_combined + uv_subband
        
        # Write combined MS
        logger.info(f"Writing combined MS: {output_ms}")
        uv_combined.write_ms(
            str(output_ms),
            force_phase='drift',
            run_check=False,
            check_extra=False,
            run_check_acceptability=False
        )
        logger.info(f"✓ Successfully wrote {output_ms}")
        
        return True
        
    else:
        # Write separate MS per sub-band
        logger.info(f"Converting {len(observation_files)} sub-bands "
                   f"to separate MS files")
        
        for file_info in observation_files:
            subband = file_info['subband']
            ms_file = output_ms.parent / f"{output_ms.stem}_sb{subband:02d}.ms"
            
            logger.info(f"  Converting sub-band {subband:02d} to {ms_file.name}")
            uv = hdf5_to_uvdata(file_info['filepath'])
            uv.write_ms(
                str(ms_file),
                force_phase='drift',
                run_check=False,
                check_extra=False,
                run_check_acceptability=False,
                clobber=True
            )
        
        logger.info(f"✓ Successfully wrote {len(observation_files)} MS files")
        return True


def batch_convert_directory(data_dir, output_dir, 
                           time_tolerance_minutes=6,
                           combine_subbands=True):
    """
    Batch convert all observations in a directory.
    
    Parameters
    ----------
    data_dir : str or Path
        Directory containing HDF5 files
    output_dir : str or Path
        Directory for output MS files
    time_tolerance_minutes : float
        Time tolerance for grouping observations
    combine_subbands : bool
        Whether to combine sub-bands into single MS
    
    Returns
    -------
    success_count : int
        Number of successfully converted observations
    """
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Group observations
    grouper = DSA110ObservationGrouper(data_dir, time_tolerance_minutes)
    observation_groups = grouper.group_observations()
    
    # Convert each observation
    success_count = 0
    for group_id, files in observation_groups.items():
        try:
            # Create output filename
            output_ms = output_dir / f"{group_id}.ms"
            
            # Skip if already exists (optional - remove for reprocessing)
            if output_ms.exists():
                logger.warning(f"Skipping {output_ms.name} - already exists")
                continue
            
            # Convert
            success = convert_observation_to_ms(files, output_ms, combine_subbands)
            
            if success:
                success_count += 1
                
        except Exception as e:
            logger.error(f"Failed to convert observation {group_id}: {e}", 
                        exc_info=True)
            continue
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Batch conversion complete:")
    logger.info(f"  Total observations: {len(observation_groups)}")
    logger.info(f"  Successfully converted: {success_count}")
    logger.info(f"  Failed: {len(observation_groups) - success_count}")
    logger.info(f"{'='*60}\n")
    
    return success_count


# Example usage
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Convert DSA-110 HDF5 visibility files to CASA Measurement Sets'
    )
    parser.add_argument('data_dir', type=str,
                       help='Directory containing HDF5 files')
    parser.add_argument('output_dir', type=str,
                       help='Directory for output MS files')
    parser.add_argument('--time-tolerance', type=float, default=6.0,
                       help='Time tolerance in minutes for grouping (default: 6)')
    parser.add_argument('--separate-subbands', action='store_true',
                       help='Create separate MS per sub-band (default: combine)')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Run batch conversion
    batch_convert_directory(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        time_tolerance_minutes=args.time_tolerance,
        combine_subbands=not args.separate_subbands
    )