# test_pipeline_10min.py
# Runs core pipeline steps on two 5-min chunks selected around a BPCAL transit.
# Determines Dec automatically, selects BPCAL, finds data chunks.
# Performs BPCAL + limited GCAL (on calibrator only).

import argparse
import os
import sys
import glob
import time
import numpy as np
import pandas as pd
import yaml
from datetime import datetime, timedelta

# Astropy imports
from astropy.time import Time, TimeDelta
from astropy.coordinates import SkyCoord, Angle, EarthLocation
import astropy.units as u
from astropy.table import Table
from astropy.io import fits # Needed if checking FITS output here
from astropy.wcs import WCS # Needed if checking FITS output here

# Pipeline module imports
try:
    # Assumes script is run from the parent directory of 'pipeline/'
    from dsa110.pipeline import config_parser
    from dsa110.pipeline import pipeline_utils
    from dsa110.pipeline import ms_creation
    from dsa110.pipeline import calibration
    from dsa110.pipeline import skymodel
    from dsa110.pipeline import imaging
    from dsa110.pipeline import mosaicking
    from dsa110.pipeline import photometry
    from dsa110.pipeline import utils_dsa110 # Needed for location
except ImportError:
    print("ERROR: Ensure this script is run from the parent directory containing")
    print("       the 'pipeline' module directory, or adjust PYTHONPATH.")
    sys.path.append(os.path.dirname(os.path.dirname(__file__))) # Go up one level
    from dsa110.pipeline import config_parser
    from dsa110.pipeline import pipeline_utils
    from dsa110.pipeline import ms_creation
    from dsa110.pipeline import calibration
    from dsa110.pipeline import skymodel
    from dsa110.pipeline import imaging
    from dsa110.pipeline import mosaicking
    from dsa110.pipeline import photometry
    from dsa110.pipeline import utils_dsa110

# pyuvdata needed for reading header
try:
    from pyuvdata import UVData
    pyuvdata_available = True
except ImportError:
     print("ERROR: pyuvdata is required to read HDF5 metadata.")
     pyuvdata_available = False


def get_obs_declination(config, hdf5_dir):
    """Reads the fixed declination from an arbitrary HDF5 file's metadata."""
    if not pyuvdata_available: return None
    logger = pipeline_utils.get_logger(__name__)
    logger.info("Attempting to determine observation declination from HDF5 metadata...")
    try:
        # Find any sb00 file to read metadata from
        pattern = os.path.join(hdf5_dir, "20*_sb00.hdf5")
        hdf5_files = glob.glob(pattern)
        if not hdf5_files:
            raise FileNotFoundError(f"No '*_sb00.hdf5' files found in {hdf5_dir} to read metadata.")

        uvd = UVData()
        logger.debug(f"Reading metadata from: {hdf5_files[0]}")
        uvd.read(hdf5_files[0], filetype='uvf5', run_check=False, read_data=False)
        fixed_dec_rad = uvd.extra_keywords['phase_center_dec']
        fixed_dec_deg = np.rad2deg(fixed_dec_rad) % 360
        logger.info(f"Determined observation Declination: {fixed_dec_deg:.4f} degrees")
        return fixed_dec_deg
    except KeyError:
        logger.error(f"Metadata key 'phase_center_dec' not found in {hdf5_files[0]}. Cannot determine Dec.")
        return None
    except Exception as e:
        logger.error(f"Failed to read HDF5 metadata to determine Declination: {e}", exc_info=True)
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


def run_test(config_path, hdf5_dir, bcal_name_override=None, verbose=False):
    """Runs the test pipeline workflow for two 5-minute chunks around a BPCAL transit."""

    # --- Load Config and Setup Logging ---
    config = config_parser.load_config(config_path)
    if not config: sys.exit(1)
    log_dir = config['paths'].get('log_dir', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_level = logging.DEBUG if verbose else logging.INFO
    logger = pipeline_utils.setup_logging(log_dir, config_name=f"test_run_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    logger.setLevel(log_level)

    logger.info("--- Starting Test Pipeline Run (Auto BPCAL Select) ---")
    logger.info(f"Using configuration: {config_path}")
    logger.info(f"Reading HDF5 from: {hdf5_dir}")

    config['services']['hdf5_post_handle'] = 'none'
    logger.info("Ensuring HDF5 post_handle is set to 'none' for test.")

    # --- Ensure Output Dirs Exist ---
    paths_config = config['paths']
    for key in ['ms_stage1_dir', 'cal_tables_dir', 'skymodels_dir', 'images_dir', 'mosaics_dir', 'photometry_dir']:
        dir_path = paths_config.get(key)
        if dir_path: os.makedirs(dir_path, exist_ok=True)
        else: logger.error(f"Path key 'paths:{key}' not found in config."); sys.exit(1)

    # --- Stage 0: Determine Dec, Select BPCAL, Find Chunks ---
    fixed_dec_deg = get_obs_declination(config, hdf5_dir)
    if fixed_dec_deg is None: sys.exit(1)
    config['calibration']['fixed_declination_deg'] = fixed_dec_deg

    selected_bcal_info = select_bcal_for_test(config, fixed_dec_deg, bcal_name_override)
    if selected_bcal_info is None: sys.exit(1)

    transit_time = calculate_next_transit(selected_bcal_info, utils_dsa110.loc_dsa110)
    if transit_time is None: sys.exit(1)

    hdf5_files_1, hdf5_files_2, start_time_1, start_time_2 = find_hdf5_chunks_around_time(config, hdf5_dir, transit_time)
    if not hdf5_files_1 or not hdf5_files_2: sys.exit(1)
    ts1_str = start_time_1.strftime("%Y%m%dT%H%M%S")
    ts2_str = start_time_2.strftime("%Y%m%dT%H%M%S") # This is the transit chunk

    # --- Stage 1: MS Creation ---
    logger.info("--- Stage 1: MS Creation ---")
    ms_path_1 = ms_creation.process_hdf5_set(config, ts1_str, hdf5_files_1)
    ms_path_2 = ms_creation.process_hdf5_set(config, ts2_str, hdf5_files_2)

    if not ms_path_1 or not ms_path_2: logger.critical("MS Creation failed. Aborting test."); sys.exit(1)
    logger.info(f"Created MS files: {os.path.basename(ms_path_1)}, {os.path.basename(ms_path_2)}")
    ms_files_to_process = [ms_path_1, ms_path_2]

    # --- Stage 2: Calibration and Imaging ---
    logger.info("--- Stage 2: Calibration and Imaging ---")
    processed_images = []
    processed_pbs = []
    block_mask_path = None
    template_image_path = None
    gcal_table_path = None
    cl_path_bcal = None

    # 2a. Find latest BPCAL table
    try:
        cal_tables_dir = paths_config['cal_tables_dir']
        bcal_files = sorted(glob.glob(os.path.join(cal_tables_dir, "*.bcal")))
        if not bcal_files: raise RuntimeError(f"No BPCAL tables (*.bcal) found in {cal_tables_dir}.")
        latest_bcal_table = bcal_files[-1]
        logger.info(f"Using BPCAL table: {os.path.basename(latest_bcal_table)}")
    except Exception as e: logger.critical(f"Failed to find BPCAL table: {e}. Aborting test."); sys.exit(1)

    # 2b. Generate Calibrator Model & Gain Cal Table (using transit chunk only)
    try:
        skymodels_dir = paths_config['skymodels_dir']
        cl_bcal_filename = f"bcal_sky_{selected_bcal_info['name']}.cl"
        cl_bcal_output_path = os.path.join(skymodels_dir, cl_bcal_filename)
        cl_path_bcal, _ = skymodel.create_calibrator_component_list(config, selected_bcal_info, cl_bcal_output_path)
        if not cl_path_bcal: raise RuntimeError("Failed to create BPCAL sky model.")

        logger.info(f"Performing gain calibration on transit chunk: {os.path.basename(ms_path_2)}")
        gcal_time_str = f"bcal_test_{ts2_str}"
        gcal_table_path = calibration.perform_gain_calibration(config, [ms_path_2], cl_path_bcal, gcal_time_str, solint='inf')
        if not gcal_table_path: raise RuntimeError("Gain calibration on BPCAL failed.")
        logger.info(f"Gain table generated: {os.path.basename(gcal_table_path)}")
    except Exception as e:
        logger.error(f"Failed during gain calibration setup stage: {e}", exc_info=True)
        logger.warning("Proceeding without gain calibration solutions.")
        gcal_table_path = [] # Set to empty list if failed

    # 2c. Prepare Mask (using BPCAL model, defer creation until template exists)
    use_mask_config = config.get('imaging',{}).get('use_clean_mask', False)
    mask_output_path = None
    if use_mask_config and cl_path_bcal:
        mask_output_path = os.path.join(skymodels_dir, f"mask_bcal_test_{selected_bcal_info['name']}.mask")
        logger.info(f"Will attempt to create mask: {mask_output_path}")
    else: logger.info("Masking disabled or BPCAL model missing, skipping mask.")
    mask_created = False # Reset flag

    # 2d. Loop through MS files for Flagging, ApplyCal, Imaging
    for i, ms_path in enumerate(ms_files_to_process):
        logger.info(f"Processing MS {i+1}/{len(ms_files_to_process)}: {os.path.basename(ms_path)}")
        ms_base = os.path.splitext(os.path.basename(ms_path))[0]
        image_base = os.path.join(images_dir, f"{ms_base}_test") # Add suffix to avoid overwrite

        try:
            if not calibration.flag_rfi(config, ms_path): raise RuntimeError("RFI Flagging failed.")
            if not calibration.flag_general(config, ms_path): raise RuntimeError("General Flagging failed.")

            gcal_list = [gcal_table_path] if gcal_table_path and isinstance(gcal_table_path, str) else []
            if not calibration.apply_calibration(config, ms_path, latest_bcal_table, gcal_list):
                raise RuntimeError("ApplyCal failed.")

            ms_to_image = ms_path
            current_mask_path = None
            if use_mask_config and mask_output_path:
                if not mask_created:
                    if template_image_path:
                        logger.info(f"Creating block mask {mask_output_path} using template {template_image_path}")
                        if imaging.create_clean_mask(config, cl_path_bcal, template_image_path, mask_output_path):
                             mask_created = True
                        else: logger.warning("Failed to create mask. Proceeding without.")
                    else: logger.debug("Template image not yet available for mask creation.")
                if mask_created: current_mask_path = mask_output_path

            logger.info("Running tclean...")
            tclean_image_basename = imaging.run_tclean(config, ms_to_image, image_base, cl_path=None, mask_path=current_mask_path)

            if tclean_image_basename:
                img_path = f"{tclean_image_basename}.image"
                pb_path = f"{tclean_image_basename}.pb"
                if os.path.exists(img_path) and os.path.exists(pb_path):
                    processed_images.append(img_path); processed_pbs.append(pb_path)
                    logger.info(f"Successfully imaged {ms_path}")
                    if template_image_path is None: template_image_path = img_path
                else: raise RuntimeError(f"tclean image/pb missing for {tclean_image_basename}")
            else: raise RuntimeError("tclean failed.")

        except Exception as e_ms:
             logger.error(f"Failed processing MS {ms_path}: {e_ms}", exc_info=True)
             logger.critical("Aborting test due to MS processing failure.")
             sys.exit(1)

    # --- Stage 3: Mosaicking ---
    mosaic_img_path = None
    if len(processed_images) == 2:
        logger.info("--- Stage 3: Mosaicking ---")
        mosaic_basename = f"mosaic_test_{ts1_str}_{ts2_str}"
        try:
            mosaic_img_path, _ = mosaicking.create_mosaic(config, processed_images, processed_pbs, mosaic_basename)
            if not mosaic_img_path: raise RuntimeError("Mosaicking function returned None.")
            logger.info(f"Mosaic created: {mosaic_img_path}")
        except Exception as e_mosaic: logger.critical(f"Mosaicking failed: {e_mosaic}. Aborting.", exc_info=True); sys.exit(1)
    else: logger.critical(f"Could not proceed to mosaicking: Only {len(processed_images)} images were created."); sys.exit(1)

    # --- Stage 4: Photometry ---
    if mosaic_img_path:
        logger.info("--- Stage 4: Photometry ---")
        mosaic_fits_path = f"{os.path.splitext(mosaic_img_path)[0]}.linmos.fits"
        if not os.path.exists(mosaic_fits_path):
             logger.warning(f"Mosaic FITS {mosaic_fits_path} not found, attempting export...")
             mosaic_fits_path = imaging.export_image_to_fits(config, mosaic_img_path, suffix='.linmos')

        if mosaic_fits_path and os.path.exists(mosaic_fits_path):
            logger.info(f"Running photometry on mosaic: {mosaic_fits_path}")
            try:
                targets, references = photometry.identify_sources(config, mosaic_fits_path)
                # Add BPCAL to targets list if not already there
                phot_targets_df = pd.DataFrame(targets) if targets is not None else pd.DataFrame()
                if selected_bcal_info and selected_bcal_info['name'] not in phot_targets_df['name'].values:
                     try:
                          bcal_coord = SkyCoord(ra=selected_bcal_info['ra'], dec=selected_bcal_info['dec'], unit=(u.hourangle, u.deg), frame='icrs')
                          with fits.open(mosaic_fits_path) as hdul:
                               wcs = WCS(hdul[0].header).celestial
                               xpix, ypix = wcs.world_to_pixel(bcal_coord)
                          bcal_row = {'name': selected_bcal_info['name'], 'source_id':selected_bcal_info['name'], # Add source_id too
                                        'RA_J2000': selected_bcal_info['ra'], 'DEC_J2000': selected_bcal_info['dec'],
                                        'xpix': xpix, 'ypix': ypix}
                          # Add other columns as NaN if needed by photometry functions
                          for col in phot_targets_df.columns:
                              if col not in bcal_row: bcal_row[col] = np.nan
                          phot_targets_df = pd.concat([phot_targets_df, pd.DataFrame([bcal_row])], ignore_index=True)
                          logger.info(f"Added BPCAL {selected_bcal_info['name']} to target list for photometry.")
                     except Exception as e_add: logger.warning(f"Could not add BPCAL to target list: {e_add}")

                if not phot_targets_df.empty and references is not None:
                    phot_table = photometry.perform_aperture_photometry(config, mosaic_fits_path, phot_targets_df, pd.DataFrame(references)) # Use pandas DF
                    if phot_table is not None:
                        rel_flux_table = photometry.calculate_relative_fluxes(config, phot_table)
                        if rel_flux_table is not None:
                            logger.info("Photometry successful. Relative flux results:")
                            print("\n--- Relative Photometry Results ---")
                            try:
                                rel_flux_table_final = Table.from_pandas(rel_flux_table[['source_id', 'relative_flux', 'relative_flux_error', 'median_reference_flux', 'reference_source_ids']])
                                print(rel_flux_table_final)
                                test_output_csv = os.path.join(config['paths']['photometry_dir'], f"test_photometry_{ts1_str}_{ts2_str}.csv")
                                rel_flux_table_final.write(test_output_csv, format='csv', overwrite=True)
                                logger.info(f"Saved test photometry results to: {test_output_csv}")
                            except Exception as e_print: logger.error(f"Could not print/save photometry table: {e_print}")
                        else: logger.error("Relative flux calculation failed.")
                    else: logger.error("Aperture photometry failed.")
                elif phot_targets_df.empty: logger.warning("No target sources identified/valid for photometry.")
                else: logger.error("Reference source identification failed.")
            except Exception as e_phot: logger.error(f"Photometry stage failed: {e_phot}", exc_info=True)
        else: logger.error(f"Mosaic FITS file missing: {mosaic_fits_path}. Cannot run photometry.")

    logger.info("--- Test Pipeline Run Finished ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DSA-110 Continuum Pipeline - Two Chunk Test Runner")
    parser.add_argument("-c", "--config", required=True, help="Path to the main pipeline YAML config file.")
    parser.add_argument("--hdf5-dir", required=True, help="Path to the directory containing the input HDF5 files.")
    parser.add_argument("--bcal-name", default=None, help="Optional: Force use of specific BPCAL name from catalog.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()

    # Basic check for BPCAL file existence before starting
    temp_config = config_parser.load_config(args.config)
    if not temp_config: sys.exit(1)
    bcal_list_path = temp_config.get('calibration',{}).get('bcal_candidate_catalog')
    if not bcal_list_path or not os.path.exists(bcal_list_path):
         print(f"ERROR: BPCAL candidate list specified in config not found: {bcal_list_path}")
         print(f"       Please run the catalog generation script first.")
         sys.exit(1)
    del temp_config # Avoid confusion

    run_test(
        config_path=args.config,
        hdf5_dir=args.hdf5_dir,
        bcal_name_override=args.bcal_name,
        verbose=args.verbose
    )