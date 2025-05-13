# -*- coding: utf-8 -*-
# Notebook Setup Cell

import argparse
import os

# point Casacore’s table cache to a real, writable directory
#os.environ['CASACORE_TABLE_PATH'] = '/data/jfaber/dsa110-contimg/tmp/casatables'
#os.makedirs(os.environ['CASACORE_TABLE_PATH'], exist_ok=True)

import sys
import glob
import time
import numpy as np
import pandas as pd
import yaml
from importlib import reload
from datetime import datetime, timedelta
import logging
from collections import defaultdict
from pickleshare import *

# Astropy imports
from astropy.time import Time, TimeDelta
from astropy.coordinates import SkyCoord, Angle, EarthLocation
import astropy.units as u
from astropy.table import Table
from astropy.io import fits
from astropy.wcs import WCS

# --- IMPORTANT: Adjust sys.path if needed ---
# If your notebook is NOT in the same directory as the 'pipeline' folder,
# add the parent directory to the path so Python can find the modules.
pipeline_parent_dir = '/data/jfaber/dsa110-contimg/' # ADJUST IF YOUR NOTEBOOK IS ELSEWHERE
if pipeline_parent_dir not in sys.path:
    sys.path.insert(0, pipeline_parent_dir)

from casatasks import (
        clearcal, delmod, rmtables, flagdata, bandpass, ft, mstransform, gaincal, applycal, listobs, split
    )
from casatools import componentlist, msmetadata, imager, ms, table

# Pipeline module imports
try:
    from pipeline import config_parser
    from pipeline import pipeline_utils
    from pipeline import ms_creation
    from pipeline import calibration
    from pipeline import skymodel
    from pipeline import imaging
    from pipeline import mosaicking
    from pipeline import photometry
    from pipeline import dsa110_utils # Needed for location
except ImportError as e:
    print(f"ERROR: Failed to import pipeline modules. Check sys.path.")
    print(f"Current sys.path: {sys.path}")
    raise e

# pyuvdata needed for reading header
try:
    import pyuvdata
    from pyuvdata import UVData
    print(f"PyUVData version: {pyuvdata.__version__}, Path: {pyuvdata.__file__}")
    pyuvdata_available = True
except ImportError:
     print("ERROR: pyuvdata is required to read HDF5 metadata.")
     pyuvdata_available = False # Script will likely fail later

# --- Define Paths and Parameters (modify as needed) ---
CONFIG_PATH = 'config/pipeline_config.yaml' # Relative path from notebook location
HDF5_DIR = '/data/incoming/' # Location of your HDF5 data chunks
BCAL_NAME_OVERRIDE = None # Optional: Force a specific BPCAL name for testing, e.g., '3C286', otherwise set to None
VERBOSE_LOGGING = True # Set True for DEBUG level, False for INFO

# --- Setup Logging ---
# Load config minimally just to get log path
try:
    with open(CONFIG_PATH, 'r') as f:
        temp_config_for_log = yaml.safe_load(f)
    log_dir_config = temp_config_for_log.get('paths', {}).get('log_dir', 'logs') #

    # Resolve log_dir relative to pipeline parent dir if log_dir_config is relative
    if not os.path.isabs(log_dir_config):
        # Assumes pipeline_utils.py is in 'pipeline_parent_dir/pipeline/'
        # and log_dir in config is relative to 'pipeline_parent_dir'
        # Example: config log_dir: ../logs -> resolved: pipeline_parent_dir/../logs
        # If log_dir is like 'logs/', it will be pipeline_parent_dir/logs/
        # The config_parser.py resolves log_dir relative to the parent of the script dir.
        # For consistency, let's assume pipeline_parent_dir is the project root.
        log_dir = os.path.abspath(os.path.join(pipeline_parent_dir, log_dir_config))
    else:
        log_dir = log_dir_config

    os.makedirs(log_dir, exist_ok=True)
    log_level = logging.DEBUG if VERBOSE_LOGGING else logging.INFO
    
    # Ensure CASA log is also set if casatasks is available
    logger = pipeline_utils.setup_logging(log_dir, config_name=f"notebook_test_{datetime.now().strftime('%H%M%S')}") #
    logger.setLevel(log_level)
    
    # Suppress overly verbose CASA logs if desired (from casatasks import casalog; casalog.filter('INFO'))
    logger.info("Setup cell executed.")
except Exception as e:
    print(f"ERROR during setup: {e}")
    # Stop execution if setup fails
    raise RuntimeError("Setup failed")

# Helper Function Definitions

from collections import defaultdict 

def collect_files_for_nominal_start_time(nominal_start_time_str, hdf5_dir, config):
    """
    Collects a complete set of HDF5 files for a nominal start time,
    respecting timestamp variations via same_timestamp_tolerance.
    Handles HDF5 filenames with timestamps like 'YYYY-MM-DDTHH:MM:SS_sbXX.hdf5'.
    """
    logger = logging.getLogger(__name__)
    
    # Format for the user-provided nominal start time string
    nominal_time_format = "%Y%m%dT%H%M%S" 
    # Format for timestamps found in the actual HDF5 filenames
    actual_file_time_format = "%Y-%m-%dT%H:%M:%S" # Corrected format

    try:
        # Parse the user-provided nominal start time
        nominal_dt_obj = datetime.strptime(nominal_start_time_str, nominal_time_format)
    except ValueError:
        logger.error(f"Invalid nominal_start_time_str format: {nominal_start_time_str}. Expected {nominal_time_format}.")
        return None

    tolerance_sec = config['ms_creation'].get('same_timestamp_tolerance', 30.0)
    expected_spws_set = set(config['ms_creation']['spws'])
    
    logger.info(f"Collecting files for nominal start time: {nominal_start_time_str} (parsed as {nominal_dt_obj}) in {hdf5_dir} with tolerance {tolerance_sec}s")
    logger.debug(f"Expected SPWs: {sorted(list(expected_spws_set))}")

    files_for_this_chunk = defaultdict(list)
    all_hdf5_files_in_dir = glob.glob(os.path.join(hdf5_dir, "20*.hdf5")) # Glob for files starting with "20"
    logger.debug(f"Found {len(all_hdf5_files_in_dir)} total HDF5 files in {hdf5_dir} to check.")

    found_any_for_nominal_time = False
    for f_path in all_hdf5_files_in_dir:
        try:
            f_name = os.path.basename(f_path)
            # Assuming filename format YYYY-MM-DDTHH:MM:SS_sbXX.hdf5
            ts_str_from_file = f_name.split('_')[0] 
            
            # Parse timestamp from the filename using the correct format
            file_dt_obj = datetime.strptime(ts_str_from_file, actual_file_time_format)
            
            time_diff_seconds = abs((file_dt_obj - nominal_dt_obj).total_seconds())
            
            if time_diff_seconds <= tolerance_sec:
                found_any_for_nominal_time = True
                spw_str_from_file = f_name.split('_')[1].replace('.hdf5', '')
                base_spw = spw_str_from_file # Since 'spl' is no longer used
                
                logger.debug(f"  File {f_name}: ActualTS={file_dt_obj}, time_diff={time_diff_seconds:.1f}s, parsed_spw='{base_spw}'")
                if base_spw in expected_spws_set:
                    files_for_this_chunk[base_spw].append(f_path)
                    logger.debug(f"    -> Matched expected SPW: '{base_spw}'")
                else:
                    logger.debug(f"    -> Parsed SPW '{base_spw}' not in expected_spws_set.")
            # else: # This else can be very verbose if many files are outside the tolerance
                # logger.debug(f"  File {f_name}: ActualTS={file_dt_obj}, time_diff={time_diff_seconds:.1f}s (OUTSIDE tolerance for {nominal_start_time_str})")

        except (IndexError, ValueError) as e_parse: # Catch errors from split or strptime
            logger.debug(f"Could not parse filename or timestamp for {f_name} (format expected: YYYY-MM-DDTHH:MM:SS_sbXX.hdf5): {e_parse}")
            continue
        except Exception as e_gen: # Catch any other unexpected errors for a file
            logger.debug(f"Unexpected error processing file {f_name}: {e_gen}")
            continue
            
    if not found_any_for_nominal_time:
        logger.warning(f"No HDF5 files found whose timestamps were within the {tolerance_sec}s tolerance window for nominal start time {nominal_start_time_str} ({nominal_dt_obj}).")

    collected_files_list = []
    is_complete = True
    missing_spws = []
    for spw_needed in sorted(list(expected_spws_set)): 
        if spw_needed in files_for_this_chunk and files_for_this_chunk[spw_needed]:
            files_for_this_chunk[spw_needed].sort() 
            collected_files_list.append(files_for_this_chunk[spw_needed][0]) 
        else:
            is_complete = False
            missing_spws.append(spw_needed)

    if not is_complete:
        logger.error(f"Incomplete HDF5 set for nominal time {nominal_start_time_str}: Missing SPW(s): {', '.join(missing_spws)}")
        return None # Return None if set is not complete
            
    if len(collected_files_list) == len(expected_spws_set): # Check if all expected SPWs were collected
        logger.info(f"Found complete set of {len(collected_files_list)} files for nominal start time {nominal_start_time_str}")
        return sorted(collected_files_list) 
    else:
        # This path should ideally be caught by "is_complete" check, but good for robustness
        logger.error(f"Failed to form a complete set for nominal start {nominal_start_time_str}. Expected {len(expected_spws_set)}, collected {len(collected_files_list)}. Missing: {', '.join(missing_spws)}")
        return None
        
def get_obs_declination(config, hdf5_dir):
    """Reads the fixed declination from an arbitrary HDF5 file's metadata."""
    if not pyuvdata_available: return None
    logging.info("Attempting to determine observation declination from HDF5 metadata...")
    try:
        pattern = os.path.join(hdf5_dir, "20*_sb00.hdf5")
        hdf5_files = glob.glob(pattern)
        if not hdf5_files:
            raise FileNotFoundError(f"No '*_sb00.hdf5' files found in {hdf5_dir} to read metadata.")
        uvd = UVData()
        logging.debug(f"Reading metadata from: {hdf5_files[0]}")
        uvd.read(hdf5_files[0], file_type='uvh5', run_check=False, read_data=False)
        fixed_dec_rad = uvd.extra_keywords['phase_center_dec']
        fixed_dec_deg = np.rad2deg(fixed_dec_rad) % 360.0
        logging.info(f"Determined observation Declination: {fixed_dec_deg:.4f} degrees")
        return fixed_dec_deg
    except KeyError:
        logging.error(f"Metadata key 'phase_center_dec' not found in {hdf5_files[0]}. Cannot determine Dec.")
        return None
    except Exception as e:
        logging.error(f"Failed to read HDF5 metadata to determine Declination: {e}", exc_info=True)
        return None

def select_bcal_for_test(config, fixed_dec_deg, bcal_name_override=None):
    """Reads BPCAL candidate catalog, filters by Dec, selects one for testing."""
    logger = pipeline_utils.get_logger(__name__)
    cal_config = config['calibration']
    # Path to the *filtered* candidate list
    bcal_catalog_path = cal_config['bcal_candidate_catalog'] # Assumes path is resolved
    # Use flux limits from config if not overridden for selection
    min_flux_jy = cal_config.get('bcal_min_flux_jy', 1.0)
    max_flux_jy = cal_config.get('bcal_max_flux_jy', 100.0)

    if not os.path.exists(bcal_catalog_path):
        logger.error(f"BPCAL candidate catalog not found: {bcal_catalog_path}")
        logger.error("Please run the catalog generation script first (e.g., filter_vla_catalog_for_bcal.py).")
        return None

    logger.info(f"Reading BPCAL candidates from: {bcal_catalog_path}")
    try:
        df = pd.read_csv(bcal_catalog_path, na_values=['None','NaN',''])
        if df.empty:
            logger.error(f"BPCAL candidate file '{bcal_catalog_path}' is empty.")
            logger.error(f"Check filtering criteria (Dec={fixed_dec_deg:.2f}, Flux={min_flux_jy}-{max_flux_jy}Jy) or generate the file.")
            return None

        # In case the loaded file wasn't generated for this exact Dec, filter again.
        beam_radius_deg = cal_config.get('bcal_search_beam_radius_deg', 1.5)
        dec_min = fixed_dec_deg - beam_radius_deg
        dec_max = fixed_dec_deg + beam_radius_deg
        df['dec_deg'] = df['dec_str'].apply(lambda x: Angle(x.replace('"',''), unit=u.deg).deg if pd.notna(x) else np.nan)
        dec_mask = (df['dec_deg'] >= dec_min) & (df['dec_deg'] <= dec_max) & (df['dec_deg'].notna())
        df_filtered = df[dec_mask].copy() # Use copy to avoid SettingWithCopyWarning later

        if df_filtered.empty:
             logger.error(f"No BPCAL candidates found in '{bcal_catalog_path}' within Dec range [{dec_min:.2f}, {dec_max:.2f}] deg.")
             return None

        # Ensure flux is numeric
        df_filtered['flux_num'] = pd.to_numeric(df_filtered['flux_jy'], errors='coerce')
        df_filtered = df_filtered.dropna(subset=['flux_num'])

        if df_filtered.empty:
             logger.error(f"No BPCAL candidates remain after converting flux to numeric.")
             return None

        # Select calibrator
        selected_cal = None
        if bcal_name_override:
            logger.info(f"Attempting to use specified BPCAL: {bcal_name_override}")
            selection = df_filtered[df_filtered['name'] == bcal_name_override]
            if not selection.empty:
                selected_cal = selection.iloc[0]
            else:
                logger.error(f"Specified BPCAL '{bcal_name_override}' not found in filtered list.")
                return None
        else:
            # Select the brightest one in the filtered list
            selected_cal = df_filtered.loc[df_filtered['flux_num'].idxmax()]
            logger.info(f"Selected brightest available BPCAL: {selected_cal['name']} (L-Flux: {selected_cal['flux_num']:.2f} Jy)")

        # Return info as a dictionary matching format needed by skymodel.create_calibrator_component_list
        cal_info = {
            'name': selected_cal['name'],
            'ra': selected_cal['ra_str'],
            'dec': selected_cal['dec_str'],
            'epoch': selected_cal.get('epoch', 'J2000'), # Default epoch if missing
            'flux_jy': selected_cal['flux_num'],
            'ref_freq_ghz': 1.4, # Assume L-band flux reference
            'spectral_index': None # Not available
        }
        return cal_info

    except Exception as e:
        logger.error(f"Failed to read or select from BPCAL catalog '{bcal_catalog_path}': {e}", exc_info=True)
        return None

def calculate_next_transit(bcal_info, telescope_loc):
    """Calculates the next transit time for the selected calibrator."""
    logger = pipeline_utils.get_logger(__name__)
    try:
        # Use SkyCoord for robust parsing and calculations
        cal_coord = SkyCoord(ra=bcal_info['ra'], dec=bcal_info['dec'], unit=(u.hourangle, u.deg), frame='icrs')
        logger.debug(f"BPCAL Coordinate: {cal_coord.to_string('hmsdms')}")

        current_time_utc = Time.now()
        # Calculate LST at current time
        current_lst = current_time_utc.sidereal_time('apparent', longitude=telescope_loc.lon)
        # Calculate HA of source now
        current_ha = (current_lst - cal_coord.ra).wrap_at(180 * u.deg)
        # Time until next transit (when HA = 0) is -HA / (rate of change of HA = Earth rotation rate)
        earth_rot_rate_approx = 360.9856 * u.deg / u.day # More precise rate
        time_to_transit = -current_ha / earth_rot_rate_approx

        next_transit_time = current_time_utc + time_to_transit

        # If time_to_transit is negative, it means transit already happened today,
        # so add one sidereal day (approx) to get the *next* one.
        if time_to_transit < TimeDelta(0 * u.s):
            next_transit_time += TimeDelta(1.0, format='jd', scale='tdb') * (1 * u.sday).to(u.day) # Add approx 1 sidereal day

        logger.info(f"Calculated next transit for {bcal_info['name']} at: {next_transit_time.iso}")
        return next_transit_time
    except Exception as e:
        logger.error(f"Failed to calculate transit time for {bcal_info['name']}: {e}", exc_info=True)
        return None

def find_hdf5_chunks_around_time(config, hdf5_dir, target_time):
    """Finds the HDF5 sets for the 5-min chunk containing target_time and the one before it."""
    logger = pipeline_utils.get_logger(__name__)
    ms_chunk_mins = config['services'].get('ms_chunk_duration_min', 5)
    tolerance_sec = config['ms_creation'].get('same_timestamp_tolerance', 30) # Use tolerance

    logger.info(f"Searching for HDF5 chunks around target transit time: {target_time.iso}")

    # Find all potential start times from filenames
    all_files = glob.glob(os.path.join(hdf5_dir, "20*_sb00.hdf5"))
    if not all_files:
         logger.error(f"No HDF5 files found in {hdf5_dir} matching pattern.")
         return None, None, None, None

    possible_start_times = []
    time_format = "%Y%m%dT%H%M%S"
    for f in all_files:
        try:
            ts_str = os.path.basename(f).split('_')[0]
            t = Time(datetime.strptime(ts_str, time_format), format='datetime', scale='utc')
            possible_start_times.append(t)
        except Exception as e:
            logger.warning(f"Could not parse time from {os.path.basename(f)}: {e}")
            continue

    if not possible_start_times:
        logger.error(f"No valid timestamps parsed from HDF5 files found in {hdf5_dir}.")
        return None, None, None, None

    possible_start_times = sorted(list(set(possible_start_times))) # Unique sorted times
    logger.debug(f"Found {len(possible_start_times)} unique potential start times.")

    # Find the chunk containing the target_time (transit)
    transit_chunk_start_time = None
    for i, t_start in enumerate(possible_start_times):
        # Consider a chunk valid if the target time is within +/- tolerance/2 of its midpoint?
        # Or simpler: find chunk where target_time falls between t_start and t_start + chunk_duration
        t_end = t_start + timedelta(minutes=ms_chunk_mins)
        if t_start <= target_time < t_end:
            transit_chunk_start_time = t_start
            logger.info(f"Found transit chunk starting at: {transit_chunk_start_time.iso}")
            break

    # Handle case where target time is not exactly within a chunk (pick closest start time before it)
    if transit_chunk_start_time is None:
         times_before = [t for t in possible_start_times if t <= target_time]
         if not times_before:
              logger.error(f"No HDF5 chunks found starting at or before the target transit time {target_time.iso}.")
              return None, None, None, None
         transit_chunk_start_time = times_before[-1] # Closest start time <= target time
         logger.warning(f"Target time {target_time.iso} not within a chunk's exact 5min window. Selecting closest preceding chunk: {transit_chunk_start_time.iso}")


    # Find the preceding chunk
    preceding_chunk_start_time = None
    transit_chunk_index = possible_start_times.index(transit_chunk_start_time)
    if transit_chunk_index > 0:
        preceding_chunk_start_time = possible_start_times[transit_chunk_index - 1]
        logger.info(f"Found preceding chunk starting at: {preceding_chunk_start_time.iso}")
    else:
        logger.error("Cannot find a chunk preceding the transit chunk. Need at least two chunks.")
        return None, None, None, None

    # Now find the actual complete file sets for these two timestamps using the tolerance
    ts1_dt = preceding_chunk_start_time.datetime
    ts2_dt = transit_chunk_start_time.datetime
    hdf5_sets = {}

    all_hdf5 = glob.glob(os.path.join(hdf5_dir, "20*.hdf5"))
    files_by_approx_ts = defaultdict(list)
    for f_path in all_hdf5:
         try:
             f_name = os.path.basename(f_path)
             ts_str = f_name.split('_')[0]
             file_dt = datetime.strptime(ts_str, time_format)
             # Group files that are close in time to the target start times
             if abs((file_dt - ts1_dt).total_seconds()) <= tolerance_sec:
                  files_by_approx_ts[ts1_dt.strftime(time_format)].append(f_path)
             elif abs((file_dt - ts2_dt).total_seconds()) <= tolerance_sec:
                  files_by_approx_ts[ts2_dt.strftime(time_format)].append(f_path)
         except Exception:
             continue # Ignore files with bad names

    # Check completeness for the two target timestamps
    expected_subbands = config['services']['hdf5_expected_subbands']
    spws_to_include = set(config['ms_creation']['spws'])
    ts1_str_exact = ts1_dt.strftime(time_format)
    ts2_str_exact = ts2_dt.strftime(time_format)

    for ts_key in [ts1_str_exact, ts2_str_exact]:
        found_files_for_ts = {}
        if ts_key in files_by_approx_ts:
            for f_path in files_by_approx_ts[ts_key]:
                try:
                    f_name = os.path.basename(f_path)
                    spw_str = f_name.split('_')[1].replace('.hdf5', '')
                    base_spw = spw_str.split('spl')[0]
                    if base_spw in spws_to_include:
                        found_files_for_ts[base_spw] = f_path
                except IndexError: continue
        if len(found_files_for_ts) == len(spws_to_include):
            logger.info(f"Found complete set for target time {ts_key}")
            sorted_filepaths = [found_files_for_ts[spw] for spw in sorted(list(spws_to_include))]
            hdf5_sets[ts_key] = sorted_filepaths
        else:
            logger.error(f"Incomplete HDF5 set found for target time {ts_key} ({len(found_files_for_ts)}/{len(spws_to_include)} required SPWs).")
            return None, None, None, None

    return hdf5_sets[ts1_str_exact], hdf5_sets[ts2_str_exact], preceding_chunk_start_time, transit_chunk_start_time

logging.info("Helper functions defined.")

# Load the main pipeline configuration
config = config_parser.load_config(CONFIG_PATH) 
if not config:
    raise ValueError("Failed to load configuration.")

config['services']['hdf5_post_handle'] = 'none' 
logging.info("Ensuring HDF5 post_handle is set to 'none' for this test run.")

# --- Stage 0: MANUAL HDF5 Chunk Selection by Nominal Start Time ---
logging.info("--- Stage 0: MANUAL HDF5 Chunk Selection by Nominal Start Time ---")

HDF5_DIR_MANUAL = config['paths']['hdf5_incoming'] # Or override: '/data/incoming/' 

# == Specify your desired NOMINAL start times for the two 5-minute chunks ==
# For your example (2025-05-07T00:04:06/07), a nominal start might be "20250507T000400" or "20250507T000405"
# The exact nominal value here helps center the search window defined by `same_timestamp_tolerance`.
# Let's assume the first 5-min block you want to process starts *nominally* around ts1_manual_nominal_str
ts1_manual_nominal_str = "20250507T000500"  # first chunk's nominal start time
ts2_manual_nominal_str = "20250507T001000"  # second chunk's nominal start time
# ==========================================================================

hdf5_files_1 = collect_files_for_nominal_start_time(ts1_manual_nominal_str, HDF5_DIR_MANUAL, config)
hdf5_files_2 = collect_files_for_nominal_start_time(ts2_manual_nominal_str, HDF5_DIR_MANUAL, config)

# The 'ts1_str' and 'ts2_str' should be the nominal timestamps used for collection,
# as these are used for directory/file naming in subsequent pipeline stages.
ts1_str = ts1_manual_nominal_str
ts2_str = ts2_manual_nominal_str

if not hdf5_files_1 or not hdf5_files_2:
    raise RuntimeError("Manual HDF5 file selection failed for one or both nominal start times. Check logs and HDF5_DIR.")

logging.info(f"Manually selected HDF5 chunk 1 (Nominal Start: {ts1_str}): Files: {list(map(os.path.basename, hdf5_files_1))}")
logging.info(f"Manually selected HDF5 chunk 2 (Nominal Start: {ts2_str}): Files: {list(map(os.path.basename, hdf5_files_2))}")

# --- You still need to select a BPCAL for calibration/imaging metadata ---
# Determine observation declination (can still be automatic or you can hardcode it)
# It will read one of the files from your HDF5_DIR_MANUAL to get the declination
fixed_dec_deg = get_obs_declination(config, HDF5_DIR_MANUAL) 
if fixed_dec_deg is None: 
    logging.warning("Failed to get observation declination automatically. Using a default or you might need to set it manually.")
    fixed_dec_deg = 67.0 # Example default value, adjust as needed
config['calibration']['fixed_declination_deg'] = fixed_dec_deg
logging.info(f"Observation Declination set to: {fixed_dec_deg:.4f} degrees for this run.")

selected_bcal_info = select_bcal_for_test(config, fixed_dec_deg, BCAL_NAME_OVERRIDE) 
if selected_bcal_info is None: 
    logging.warning(f"Failed to select BPCAL for test. Subsequent steps might be affected.")
    # Optionally, provide a default BPCAL dictionary here if needed for the test to proceed
    # selected_bcal_info = {'name': '3C286', 'ra': '13h31m08.288s', 'dec': '+30d30m32.96s', 
    #                       'epoch': 'J2000', 'flux_jy': 14.79, 'ref_freq_ghz': 1.4}

print(f"HDF5 files: {hdf5_files_1}")

logging.info("--- Stage 1: MS Creation ---")
ms_path_1 = ms_creation.process_hdf5_set(config, ts1_str, hdf5_files_1)
ms_path_2 = ms_creation.process_hdf5_set(config, ts2_str, hdf5_files_2)

if not ms_path_1 or not ms_path_2:
    raise RuntimeError("MS Creation failed for one or both chunks.")

logging.info(f"Created MS files: {os.path.basename(ms_path_1), os.path.basename(ms_path_2)}")
ms_files_to_process = [ms_path_1, ms_path_2]

