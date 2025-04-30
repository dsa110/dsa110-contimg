# test_pipeline_10min.py
# Updated: Dynamically finds Dec, selects BPCAL, finds transit time, selects data.
#          Performs gain cal only on BPCAL transit data.

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
    from pipeline import utils_dsa110
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__))) # Go up one level
    from pipeline import config_parser
    from pipeline import pipeline_utils
    from pipeline import ms_creation
    from pipeline import calibration
    from pipeline import skymodel
    from pipeline import imaging
    from pipeline import mosaicking
    from pipeline import photometry
    from pipeline import utils_dsa110

# CASA imports needed for metadata reading here
try:
    from casatools import msmetadata
    casa_available = True
except ImportError:
    print("Warning: casatools not found. Cannot read MS metadata.")
    casa_available = False

def get_obs_declination(config, hdf5_dir):
    """Reads the fixed declination from an arbitrary HDF5 file's metadata."""
    logger = pipeline_utils.get_logger(__name__)
    logger.info("Attempting to determine observation declination from HDF5 metadata...")
    try:
        # Find any sb00 file to read metadata from
        pattern = os.path.join(hdf5_dir, "20*_sb00.hdf5")
        hdf5_files = glob.glob(pattern)
        if not hdf5_files:
            raise FileNotFoundError(f"No '*_sb00.hdf5' files found in {hdf5_dir} to read metadata.")

        # Use pyuvdata to read header only
        from pyuvdata import UVData
        uvd = UVData()
        uvd.read(hdf5_files[0], file_type="uvh5", run_check=False, read_data=False)
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
    """Reads BPCAL catalog, filters by Dec, selects one for testing."""
    logger = pipeline_utils.get_logger(__name__)
    cal_config = config['calibration']
    bcal_catalog_path = cal_config['bcal_candidate_catalog'] # Assumes path is resolved
    beam_radius_deg = cal_config.get('bcal_search_beam_radius_deg', 1.5)
    min_flux_jy = cal_config.get('bcal_min_flux_jy', 1.0) # Lower default for testing?

    if not os.path.exists(bcal_catalog_path):
        logger.error(f"BPCAL candidate catalog not found: {bcal_catalog_path}")
        return None

    logger.info(f"Reading BPCAL candidates from: {bcal_catalog_path}")
    try:
        # Use pandas for easier filtering
        df = pd.read_csv(bcal_catalog_path, na_values=['None','NaN',''])
        if df.empty: raise ValueError("BPCAL candidate file is empty.")

        # Filter by declination
        dec_min = fixed_dec_deg - beam_radius_deg
        dec_max = fixed_dec_deg + beam_radius_deg
        df['dec_deg'] = df['dec_str'].apply(lambda x: Angle(x.replace('"',''), unit=u.deg).deg if pd.notna(x) else np.nan)
        dec_mask = (df['dec_deg'] >= dec_min) & (df['dec_deg'] <= dec_max) & (df['dec_deg'].notna())
        df_filtered = df[dec_mask]
        logger.info(f"Found {len(df_filtered)} candidates within Dec range [{dec_min:.2f}, {dec_max:.2f}] deg.")

        if df_filtered.empty:
            logger.error("No BPCAL candidates found within the observable declination range.")
            return None

        # Filter by flux (ensure flux_jy is numeric)
        df_filtered['flux_num'] = pd.to_numeric(df_filtered['flux_jy'], errors='coerce')
        flux_mask = (df_filtered['flux_num'] >= min_flux_jy) & (df_filtered['flux_num'].notna())
        df_filtered = df_filtered[flux_mask]
        logger.info(f"Found {len(df_filtered)} candidates also meeting flux > {min_flux_jy} Jy.")

        if df_filtered.empty:
            logger.error(f"No BPCAL candidates found meeting both Dec and Flux criteria (>{min_flux_jy} Jy).")
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
            logger.info(f"Selected brightest BPCAL in range: {selected_cal['name']} (Flux: {selected_cal['flux_num']:.2f} Jy)")

        # Return info as a dictionary matching format needed by skymodel.create_calibrator_component_list
        cal_info = {
            'name': selected_cal['name'],
            'ra': selected_cal['ra_str'],    # Pass strings
            'dec': selected_cal['dec_str'],
            'epoch': selected_cal['epoch'],
            'flux_jy': selected_cal['flux_num'],
            'ref_freq_ghz': 1.4, # Assume L-band flux reference from VLA list
            'spectral_index': None # Not available in this simple catalog
        }
        return cal_info

    except Exception as e:
        logger.error(f"Failed to read or filter BPCAL catalog: {e}", exc_info=True)
        return None


def calculate_next_transit(bcal_info, telescope_loc):
    """Calculates the next transit time for the selected calibrator."""
    logger = pipeline_utils.get_logger(__name__)
    try:
        cal_coord = SkyCoord(ra=bcal_info['ra'], dec=bcal_info['dec'], unit=(u.hourangle, u.deg), frame='icrs')
        current_time_utc = Time.now()
        # Calculate LST at current time
        current_lst = current_time_utc.sidereal_time('apparent', longitude=telescope_loc.lon)
        # Calculate HA of source now
        current_ha = (current_lst - cal_coord.ra).wrap_at(180 * u.deg)
        # Time until next transit (when HA = 0) is -HA / (rate of change of HA = Earth rotation rate)
        # Earth rotation rate is approx 360 deg / 23.9345 hours
        earth_rot_rate = 360 * u.deg / (23.9345 * u.hour)
        time_to_transit = -current_ha / earth_rot_rate

        next_transit_time = current_time_utc + time_to_transit

        # If time_to_transit is negative, it means transit already happened today,
        # so add one sidereal day to get the *next* one.
        if time_to_transit < TimeDelta(0 * u.s):
            next_transit_time += TimeDelta(23.9345 * u.hour)

        logger.info(f"Calculated next transit for {bcal_info['name']} at: {next_transit_time.iso}")
        return next_transit_time
    except Exception as e:
        logger.error(f"Failed to calculate transit time for {bcal_info['name']}: {e}", exc_info=True)
        return None

def find_hdf5_chunks_around_time(config, hdf5_dir, target_time):
    """Finds the HDF5 sets for the 5-min chunk containing target_time and the one before it."""
    logger = pipeline_utils.get_logger(__name__)
    ms_chunk_mins = config['services'].get('ms_chunk_duration_min', 5)
    tolerance_sec = config['ms_creation'].get('same_timestamp_tolerance', 30)

    logger.info(f"Searching for HDF5 chunks around target time: {target_time.iso}")

    # Find all potential start times from filenames
    all_files = glob.glob(os.path.join(hdf5_dir, "20*_sb00.hdf5")) # Look at sb00 only
    possible_start_times = []
    for f in all_files:
        try:
            ts_str = os.path.basename(f).split('_')[0]
            t = Time(datetime.strptime(ts_str, "%Y%m%dT%H%M%S"), format='datetime', scale='utc')
            possible_start_times.append(t)
        except Exception:
            continue

    if not possible_start_times:
        logger.error(f"No HDF5 files found in {hdf5_dir} to determine chunk times.")
        return None, None

    possible_start_times.sort()

    # Find the chunk containing the target_time
    transit_chunk_start_time = None
    for i, t_start in enumerate(possible_start_times):
        t_end = t_start + timedelta(minutes=ms_chunk_mins)
        if t_start <= target_time < t_end:
            transit_chunk_start_time = t_start
            logger.info(f"Found transit chunk starting at: {transit_chunk_start_time.iso}")
            break

    if transit_chunk_start_time is None:
        # Target time might be just after the last chunk ends
        if target_time >= possible_start_times[-1] + timedelta(minutes=ms_chunk_mins):
             logger.warning(f"Target time {target_time.iso} is after the last available chunk {possible_start_times[-1].iso}. Using last two chunks.")
             if len(possible_start_times) >= 2:
                  transit_chunk_start_time = possible_start_times[-1]
             else:
                  logger.error("Not enough chunks available to select two.")
                  return None, None
        else: # Target time likely falls between chunks, pick closest?
             time_diffs = np.array([(t - target_time).sec for t in possible_start_times])
             closest_idx = np.argmin(np.abs(time_diffs))
             transit_chunk_start_time = possible_start_times[closest_idx]
             logger.warning(f"Target time {target_time.iso} not within a chunk, selecting closest start time: {transit_chunk_start_time.iso}")


    # Find the preceding chunk
    preceding_chunk_start_time = None
    transit_chunk_index = possible_start_times.index(transit_chunk_start_time)
    if transit_chunk_index > 0:
        preceding_chunk_start_time = possible_start_times[transit_chunk_index - 1]
        # Basic check if the gap is roughly correct
        if (transit_chunk_start_time - preceding_chunk_start_time).to(u.minute).value > ms_chunk_mins + 1: # Allow 1 min tolerance
            logger.warning(f"Gap between selected chunks seems large: {preceding_chunk_start_time.iso} -> {transit_chunk_start_time.iso}")
        logger.info(f"Found preceding chunk starting at: {preceding_chunk_start_time.iso}")
    else:
        logger.error("Cannot find a chunk preceding the transit chunk.")
        return None, None

    # Now find the actual complete file sets for these two timestamps
    ts1_str = preceding_chunk_start_time.strftime("%Y%m%dT%H%M%S")
    ts2_str = transit_chunk_start_time.strftime("%Y%m%dT%H%M%S")
    hdf5_sets = find_specific_hdf5_sets(config, hdf5_dir, preceding_chunk_start_time, transit_chunk_start_time)

    if hdf5_sets and ts1_str in hdf5_sets and ts2_str in hdf5_sets:
        return hdf5_sets[ts1_str], hdf5_sets[ts2_str], preceding_chunk_start_time, transit_chunk_start_time
    else:
        logger.error("Could not find complete HDF5 sets for the selected preceding/transit timestamps.")
        return None, None, None, None


def run_test(config_path, hdf5_dir, bcal_name_override=None):
    """Runs the test pipeline workflow for two 5-minute chunks around a BPCAL transit."""

    # --- Load Config and Setup Logging ---
    config = config_parser.load_config(config_path)
    if not config: sys.exit(1)
    log_dir = config['paths'].get('log_dir', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    # Use a specific logger for this test run
    logger = pipeline_utils.setup_logging(log_dir, config_name=f"test_run_{datetime.now().strftime('%Y%m%dT%H%M%S')}")
    # Set level based on verbose maybe? For now set to INFO
    logger.setLevel(logging.INFO) # Adjust if needed, or use args.verbose

    logger.info("--- Starting Test Pipeline Run (Auto BPCAL Select) ---")
    logger.info(f"Using configuration: {config_path}")
    logger.info(f"Reading HDF5 from: {hdf5_dir}")

    # Override HDF5 handling to ensure no deletion/moving
    config['services']['hdf5_post_handle'] = 'none'
    logger.info("Ensuring HDF5 post_handle is set to 'none' for test.")

    # --- Ensure Output Dirs Exist ---
    paths_config = config['paths']
    for key in ['ms_stage1_dir', 'cal_tables_dir', 'skymodels_dir', 'images_dir', 'mosaics_dir', 'photometry_dir']:
        dir_path = paths_config.get(key)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        else:
            logger.error(f"Path key 'paths:{key}' not found in config.")
            sys.exit(1)

    # --- Stage 0: Determine Dec, Select BPCAL, Find Chunks ---
    fixed_dec_deg = get_obs_declination(config, hdf5_dir)
    if fixed_dec_deg is None: sys.exit(1)
    # Update config in memory
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

    if not ms_path_1 or not ms_path_2:
        logger.critical("MS Creation failed for one or both chunks. Aborting test.")
        sys.exit(1)
    logger.info(f"Created MS files: {os.path.basename(ms_path_1)}, {os.path.basename(ms_path_2)}")
    ms_files_to_process = [ms_path_1, ms_path_2]

    # --- Stage 2: Calibration and Imaging ---
    logger.info("--- Stage 2: Calibration and Imaging ---")
    processed_images = []
    processed_pbs = []
    block_mask_path = None
    template_image_path = None

    # 2a. Find latest BPCAL table
    try:
        cal_tables_dir = paths_config['cal_tables_dir']
        bcal_files = sorted(glob.glob(os.path.join(cal_tables_dir, "*.bcal")))
        if not bcal_files: raise RuntimeError(f"No BPCAL tables found in {cal_tables_dir}.")
        latest_bcal_table = bcal_files[-1]
        logger.info(f"Using BPCAL table: {os.path.basename(latest_bcal_table)}")
    except Exception as e:
        logger.critical(f"Failed to find BPCAL table: {e}. Aborting test.")
        sys.exit(1)

    # 2b. Generate Calibrator Model & Gain Cal Table (using transit chunk only)
    gcal_table_path = None
    cl_path_bcal = None
    try:
        skymodels_dir = paths_config['skymodels_dir']
        cl_bcal_filename = f"bcal_sky_{selected_bcal_info['name']}.cl"
        cl_bcal_output_path = os.path.join(skymodels_dir, cl_bcal_filename)
        cl_path_bcal, _ = skymodel.create_calibrator_component_list(config, selected_bcal_info, cl_bcal_output_path)
        if not cl_path_bcal: raise RuntimeError("Failed to create BPCAL sky model.")

        logger.info(f"Performing gain calibration on transit chunk: {os.path.basename(ms_path_2)}")
        gcal_time_str = f"bcal_{ts2_str}" # Use transit time for gain cal filename
        # Use solint='inf' since it's just one 5-min MS
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
        mask_output_path = os.path.join(skymodels_dir, f"mask_bcal_{selected_bcal_info['name']}.mask")
        logger.info(f"Will attempt to create mask: {mask_output_path}")
    else:
        logger.info("Masking disabled or BPCAL model missing, skipping mask.")


    # 2d. Loop through MS files for Flagging, ApplyCal, Imaging
    mask_created = False
    for i, ms_path in enumerate(ms_files_to_process):
        logger.info(f"Processing MS {i+1}/{len(ms_files_to_process)}: {os.path.basename(ms_path)}")
        ms_base = os.path.splitext(os.path.basename(ms_path))[0]
        image_base = os.path.join(images_dir, ms_base) # Basename for tclean outputs

        try:
            # Flagging
            logger.info("Running Flagging...")
            if not calibration.flag_rfi(config, ms_path): raise RuntimeError("RFI Flagging failed.")
            if not calibration.flag_general(config, ms_path): raise RuntimeError("General Flagging failed.")

            # Apply Calibration (BPCAL + GCAL from BPCAL file)
            logger.info("Running ApplyCal...")
            # Ensure gcal_table_path is a list for apply_calibration
            gcal_list = [gcal_table_path] if gcal_table_path and isinstance(gcal_table_path, str) else []
            if not calibration.apply_calibration(config, ms_path, latest_bcal_table, gcal_list):
                raise RuntimeError("ApplyCal failed.")

            ms_to_image = ms_path

            # Create Mask if needed and possible
            current_mask_path = None
            if use_mask_config and mask_output_path:
                if not mask_created:
                    if template_image_path: # Template exists from previous iteration
                        logger.info(f"Creating block mask {mask_output_path} using template {template_image_path}")
                        if imaging.create_clean_mask(config, cl_path_bcal, template_image_path, mask_output_path):
                             mask_created = True
                        else: logger.warning("Failed to create mask. Proceeding without.")
                    else: logger.debug("Template image not yet available for mask creation.")
                if mask_created: current_mask_path = mask_output_path # Use it if created

            # Imaging (no startmodel, use BPCAL mask if available)
            logger.info("Running tclean...")
            tclean_image_basename = imaging.run_tclean(config, ms_to_image, image_base, cl_path=None, mask_path=current_mask_path)

            if tclean_image_basename:
                img_path = f"{tclean_image_basename}.image"
                pb_path = f"{tclean_image_basename}.pb"
                if os.path.exists(img_path) and os.path.exists(pb_path):
                    processed_images.append(img_path)
                    processed_pbs.append(pb_path)
                    logger.info(f"Successfully imaged {ms_path}")
                    if template_image_path is None: template_image_path = img_path
                else: raise RuntimeError(f"tclean image/pb missing for {tclean_image_basename}")
            else: raise RuntimeError("tclean failed.")

        except Exception as e_ms:
             logger.error(f"Failed processing MS {ms_path}: {e_ms}", exc_info=True)
             logger.critical("Aborting test due to MS processing failure.")
             sys.exit(1) # Stop test on first MS failure

    # --- Stage 3: Mosaicking ---
    mosaic_img_path = None
    if len(processed_images) == 2:
        logger.info("--- Stage 3: Mosaicking ---")
        mosaic_basename = f"mosaic_test_{ts1_str}_{ts2_str}"
        try:
            mosaic_img_path, _ = mosaicking.create_mosaic(config, processed_images, processed_pbs, mosaic_basename)
            if not mosaic_img_path: raise RuntimeError("Mosaicking function returned None.")
            logger.info(f"Mosaic created: {mosaic_img_path}")
        except Exception as e_mosaic:
            logger.error(f"Mosaicking failed: {e_mosaic}", exc_info=True)
            logger.critical("Aborting test due to Mosaicking failure.")
            sys.exit(1)
    else:
        logger.error(f"Could not proceed to mosaicking: Only {len(processed_images)} images were successfully created.")
        sys.exit(1)

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
                # For the test, let's ensure the BPCAL itself is treated as a target if found
                if targets is not None and selected_bcal_info is not None:
                     if selected_bcal_info['name'] not in targets['name']: # Check if BPCAL is in targets
                          bcal_row = targets[0:0].copy() # Create empty row with same columns
                          # Fill with BPCAL info (need to convert coords)
                          try:
                               bcal_coord = SkyCoord(ra=selected_bcal_info['ra'], dec=selected_bcal_info['dec'], unit=(u.hourangle, u.deg), frame='icrs')
                               with fits.open(mosaic_fits_path) as hdul:
                                    wcs = WCS(hdul[0].header).celestial
                                    xpix, ypix = wcs.world_to_pixel(bcal_coord)
                                    # Populate row (some fields might be missing from bcal_info)
                                    bcal_row.add_row({
                                         'name': selected_bcal_info['name'],
                                         'RA_J2000': selected_bcal_info['ra'],
                                         'DEC_J2000': selected_bcal_info['dec'],
                                         'xpix': xpix, 'ypix': ypix
                                         # Add dummy values or NaN for other columns if needed by later steps
                                    })
                                    targets = pd.concat([pd.DataFrame(bcal_row), pd.DataFrame(targets)]).reset_index(drop=True)
                                    logger.info(f"Added BPCAL {selected_bcal_info['name']} to target list.")
                          except Exception as e_add:
                               logger.warning(f"Could not add BPCAL to target list: {e_add}")


                if targets is not None and not targets.empty and references is not None:
                    phot_table = photometry.perform_aperture_photometry(config, mosaic_fits_path, pd.DataFrame(targets), pd.DataFrame(references)) # Convert back to DF if needed
                    if phot_table is not None:
                        rel_flux_table = photometry.calculate_relative_fluxes(config, pd.DataFrame(phot_table)) # Convert back to DF if needed
                        if rel_flux_table is not None:
                            logger.info("Photometry successful. Relative flux results:")
                            print("\n--- Relative Photometry Results ---")
                            try:
                                # Convert back to astropy table for printing if needed
                                print_table = Table.from_pandas(rel_flux_table[['source_id', 'relative_flux', 'relative_flux_error', 'median_reference_flux', 'reference_source_ids']])
                                print(print_table)
                                # Save to a test CSV
                                test_output_csv = f"test_photometry_{ts1_str}_{ts2_str}.csv"
                                rel_flux_table.to_csv(test_output_csv, index=False, float_format='%.4f', na_rep='NaN')
                                logger.info(f"Saved test photometry results to: {test_output_csv}")
                            except Exception as e_print:
                                logger.error(f"Could not print/save photometry table: {e_print}")
                                print(rel_flux_table)
                        else: logger.error("Relative flux calculation failed.")
                    else: logger.error("Aperture photometry failed.")
                elif targets is None or targets.empty:
                     logger.warning("No target sources identified/valid for photometry.")
                else: # References might be empty/None
                     logger.error("Reference source identification failed.")
            except Exception as e_phot:
                logger.error(f"Photometry stage failed: {e_phot}", exc_info=True)
        else:
            logger.error(f"Mosaic FITS file missing: {mosaic_fits_path}. Cannot run photometry.")

    logger.info("--- Test Pipeline Run Finished ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DSA-110 Continuum Pipeline - Two Chunk Test Runner")
    parser.add_argument("-c", "--config", required=True, help="Path to the main pipeline YAML config file.")
    parser.add_argument("--hdf5-dir", required=True, help="Path to the directory containing the input HDF5 files.")
    parser.add_argument("--bcal-name", default=None, help="Optional: Force use of specific BPCAL name from catalog.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()

    run_test(
        config_path=args.config,
        hdf5_dir=args.hdf5_dir,
        bcal_name_override=args.bcal_name
    )