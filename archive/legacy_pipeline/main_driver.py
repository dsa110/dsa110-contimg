# pipeline/main_driver.py

import argparse
import os
import sys
import glob
from datetime import datetime, timedelta
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u

# Pipeline module imports
try:
    from . import config_parser
    from . import pipeline_utils
    from . import ms_creation # Maybe for re-processing specific times?
    from . import calibration
    from . import skymodel
    from . import imaging
    from . import mosaicking
    from . import photometry
    from . import variability_analyzer
    from . import utils_dsa110 # Needed for location
except ImportError:
    # Allow running script directly for testing, adjust paths
    sys.path.append(os.path.dirname(os.path.dirname(__file__))) # Go up one level
    from pipeline import config_parser
    from pipeline import pipeline_utils
    from pipeline import ms_creation
    from pipeline import calibration
    from pipeline import skymodel
    from pipeline import imaging
    from pipeline import mosaicking
    from pipeline import photometry
    from pipeline import variability_analyzer
    from pipeline import utils_dsa110


def find_ms_blocks_for_batch(config, start_time_iso=None, end_time_iso=None):
    """
    Identifies blocks of MS files suitable for batch processing based on time.
    Finds existing MS files and groups them into overlapping blocks.
    """
    logger = pipeline_utils.get_logger(__name__)
    paths_config = config.get('paths', {})
    ms_dir = paths_config.get('ms_stage1_dir')
    if not ms_dir:
         logger.error("Config missing 'paths:ms_stage1_dir'. Cannot find MS files.")
         return {}

    services_config = config.get('services', {})
    duration = timedelta(minutes=services_config.get('mosaic_duration_min', 60))
    overlap = timedelta(minutes=services_config.get('mosaic_overlap_min', 10))
    ms_chunk = timedelta(minutes=services_config.get('ms_chunk_duration_min', 5))
    num_ms_per_block = int(duration / ms_chunk)

    if num_ms_per_block <= 0:
         logger.error("Invalid timing configuration: num_ms_per_block <= 0.")
         return {}

    if not os.path.isdir(ms_dir):
        logger.error(f"MS Stage 1 directory not found: {ms_dir}")
        return {}

    all_ms = sorted(glob.glob(os.path.join(ms_dir, "drift_*.ms")))
    if not all_ms:
        logger.warning(f"No MS files found in {ms_dir} matching 'drift_*.ms'")
        return {}

    # Parse timestamps and store paths
    ms_times = {}
    for ms_path in all_ms:
        ms_name = os.path.basename(ms_path)
        try:
            # Assuming drift_YYYYMMDDTHHMMSS.ms format
            ts_str = ms_name.split('_')[1].replace('.ms', '')
            ms_start_time = Time(datetime.strptime(ts_str, "%Y%m%dT%H%M%S"), format='datetime', scale='utc')
            # Use MJD as key for easier comparison, store time object too
            ms_times[ms_start_time.mjd] = {'path': ms_path, 'time': ms_start_time}
        except Exception as e:
            logger.warning(f"Could not parse time from {ms_name}. Skipping. Error: {e}")
            continue

    if not ms_times:
        logger.error("No valid MS files found after time parsing.")
        return {}

    # Sort by MJD
    sorted_mjds = sorted(ms_times.keys())
    sorted_times = [ms_times[mjd]['time'] for mjd in sorted_mjds]

    # Determine processing range
    first_ms_time = sorted_times[0]
    last_ms_time = sorted_times[-1] # Start time of the last MS

    proc_start_time = Time(start_time_iso) if start_time_iso else first_ms_time
    # Effective end time is the start of the last MS plus its duration
    proc_end_time_limit = Time(end_time_iso) if end_time_iso else (last_ms_time + ms_chunk)

    logger.info(f"Batch Processing Range: {proc_start_time.iso} to {proc_end_time_limit.iso}")

    # Group MS files into overlapping blocks
    blocks = {} # Key: block_end_time (astropy Time), Value: list of MS paths
    # Start searching from the first MS time
    current_search_start_time = first_ms_time

    while True:
         # Define the end time for the block we are trying to build
         current_block_end_time = current_search_start_time + duration
         # Define the start time for this block
         current_block_start_time = current_block_end_time - duration

         # Ensure the block we are trying to build ends within the overall processing limit
         if current_block_end_time > proc_end_time_limit + overlap: # Allow for overlap on last block
              logger.debug(f"Block ending {current_block_end_time.iso} is beyond process end time limit {proc_end_time_limit.iso}. Stopping block search.")
              break

         # Find MS files whose *start* times fall within this block
         block_files_dict = {} # Use dict to handle potential duplicates, key=MJD
         for mjd, data in ms_times.items():
              if current_block_start_time <= data['time'] < current_block_end_time:
                   block_files_dict[mjd] = data['path']

         # Check if we have enough *unique* MS files for this block
         if len(block_files_dict) >= num_ms_per_block:
              # Sort the found MS files by time
              block_mjds_sorted = sorted(block_files_dict.keys())
              # Take exactly num_ms_per_block required
              final_block_mjds = block_mjds_sorted[:num_ms_per_block]
              final_block_files = [block_files_dict[mjd] for mjd in final_block_mjds]

              # Check if this block overlaps significantly with the requested start time
              # i.e., does the block end *after* the requested start time?
              if block_end_time >= proc_start_time:
                   blocks[block_end_time] = final_block_files # Use block end time as key
                   logger.debug(f"Identified block ending {block_end_time.iso} with {len(blocks[block_end_time])} files.")

         # Advance the search start time for the next potential block
         # Step forward by the non-overlapping part of a block
         current_search_start_time += (duration - overlap)

    logger.info(f"Identified {len(blocks)} processing blocks for batch run.")
    return blocks


def process_block_batch(config, block_ms_files: list, block_start_time: Time, block_end_time: Time):
    """
    Orchestrates the processing for a single block in batch mode.
    Similar to run_processing_block in the watcher, but callable directly.
    Returns True on success, False on failure.
    """
    logger = pipeline_utils.get_logger(__name__)
    logger.info(f"--- Starting Batch Processing Block: {block_start_time.iso} to {block_end_time.iso} ---")
    block_success = True
    paths_config = config['paths']
    cal_tables_dir = paths_config['cal_tables_dir']
    skymodels_dir = paths_config['skymodels_dir']
    images_dir = paths_config['images_dir']
    # Ensure output directories exist
    os.makedirs(cal_tables_dir, exist_ok=True)
    os.makedirs(skymodels_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(paths_config['mosaics_dir'], exist_ok=True) # Ensure mosaic dir exists
    os.makedirs(paths_config['photometry_dir'], exist_ok=True) # Ensure photometry dir exists


    latest_bcal_table = None
    gcal_table_path = None
    cl_path = None
    mask_path = None
    template_image_path = None # Track template for mask creation

    # --- Stage 1: Calibration Setup ---
    try:
        # Find latest BPCAL (same logic as in run_processing_block)
        bcal_files = sorted(glob.glob(os.path.join(cal_tables_dir, "*.bcal")))
        if not bcal_files: raise RuntimeError(f"No BPCAL tables found in {cal_tables_dir}.")
        valid_bcals = [b for b in bcal_files if os.path.getmtime(b) <= block_end_time.unix]
        if not valid_bcals:
             logger.warning(f"No BPCAL table found created before block end {block_end_time.iso}. Using newest overall: {os.path.basename(bcal_files[-1])}")
             latest_bcal_table = bcal_files[-1]
        else:
             latest_bcal_table = valid_bcals[-1]
        logger.info(f"Using BPCAL table: {os.path.basename(latest_bcal_table)}")

        # Generate Sky Model and Gain Cal (same logic as in run_processing_block)
        block_center_time = block_start_time + (block_end_time - block_start_time) / 2.0
        telescope_loc = utils_dsa110.loc_dsa110
        center_lst = block_center_time.sidereal_time('apparent', longitude=telescope_loc.lon)
        center_ra = center_lst.to(u.deg)
        fixed_dec_deg = config['calibration']['fixed_declination_deg'] # Assumes valid
        center_dec = fixed_dec_deg * u.deg
        center_coord = SkyCoord(ra=center_ra, dec=center_dec, frame='icrs')
        logger.info(f"Calculated block center coordinate: {center_coord.to_string('hmsdms')}")

        cl_filename = f"sky_field_{block_start_time.strftime('%Y%m%dT%H%M%S')}.cl"
        cl_output_path = os.path.join(skymodels_dir, cl_filename)
        cl_path, _ = skymodel.create_field_component_list(config, center_coord, cl_output_path)
        if not cl_path: raise RuntimeError("Failed to create field sky model.")

        time_segment_str = f"{block_start_time.strftime('%Y%m%dT%H%M%S')}_{block_end_time.strftime('%Y%m%dT%H%M%S')}"
        gcal_table_path = calibration.perform_gain_calibration(config, block_ms_files, cl_path, time_segment_str)
        if not gcal_table_path: raise RuntimeError("Gain calibration failed.")

        # Prepare for Mask Creation (defer actual creation until template exists)
        use_mask_config = config.get('imaging',{}).get('use_clean_mask', False)
        if use_mask_config and cl_path:
            mask_output_path = os.path.join(skymodels_dir, f"mask_{block_start_time.strftime('%Y%m%dT%H%M%S')}.mask")
        else:
            mask_output_path = None

    except Exception as e:
        logger.error(f"Failed during calibration setup stage for block: {e}", exc_info=True)
        return False # Critical failure for the block

    # --- Stage 2: Process MS Files ---
    processed_images = []
    processed_pbs = []
    mask_created = False # Flag to track if mask was made

    for i, ms_path in enumerate(block_ms_files):
        logger.info(f"Processing MS {i+1}/{len(block_ms_files)}: {os.path.basename(ms_path)}")
        ms_base = os.path.splitext(os.path.basename(ms_path))[0]
        image_base = os.path.join(images_dir, ms_base)

        try:
            # Flagging
            if not calibration.flag_rfi(config, ms_path): raise RuntimeError("RFI Flagging failed.")
            if not calibration.flag_general(config, ms_path): raise RuntimeError("General Flagging failed.")

            # Apply Calibration
            if not calibration.apply_calibration(config, ms_path, latest_bcal_table, [gcal_table_path]):
                raise RuntimeError("ApplyCal failed.")

            ms_to_image = ms_path

            # Create Mask (if needed and template available)
            current_mask_path = None
            if use_mask_config and cl_path and mask_output_path:
                if not mask_created:
                    if template_image_path is None: # First image, need template
                         # TODO: Implement a way to get template info before first tclean
                         # e.g., dummy image creation or read metadata from ms_to_image
                         logger.warning("Template image needed for mask creation, but none exists yet. Skipping mask for first image.")
                    else: # We have a template from previous image in block
                        logger.info(f"Creating block mask {mask_output_path} using template {template_image_path}")
                        if imaging.create_clean_mask(config, cl_path, template_image_path, mask_output_path):
                             mask_created = True
                             logger.info(f"Using block mask: {mask_output_path}")
                        else:
                             logger.warning("Failed to create block mask. Proceeding without.")
                if mask_created:
                     current_mask_path = mask_output_path

            # Imaging
            logger.info(f"Running tclean for {ms_path}")
            tclean_image_basename = imaging.run_tclean(config, ms_to_image, image_base, cl_path=cl_path, mask_path=current_mask_path)

            if tclean_image_basename:
                img_path = f"{tclean_image_basename}.image"
                pb_path = f"{tclean_image_basename}.pb"
                if os.path.exists(img_path) and os.path.exists(pb_path):
                    processed_images.append(img_path)
                    processed_pbs.append(pb_path)
                    logger.info(f"Successfully imaged {ms_path}")
                    if template_image_path is None: template_image_path = img_path # Set template
                else:
                    raise RuntimeError(f"tclean image/pb missing for {tclean_image_basename}")
            else:
                raise RuntimeError("tclean failed.")

        except Exception as e_ms:
             logger.error(f"Failed processing MS {ms_path}: {e_ms}", exc_info=True)
             block_success = False
             # Decide whether to stop block or continue? Stop for now in batch mode.
             break

    # --- Stage 3: Mosaicking ---
    mosaic_img_path = None
    min_images_needed = int(len(block_ms_files) * 0.75)
    if block_success and len(processed_images) >= min_images_needed:
        logger.info(f"Creating mosaic from {len(processed_images)} images...")
        mosaic_basename = f"mosaic_{block_start_time.strftime('%Y%m%dT%H%M%S')}_{block_end_time.strftime('%Y%m%dT%H%M%S')}"
        try:
            mosaic_img_path, _ = mosaicking.create_mosaic(config, processed_images, processed_pbs, mosaic_basename)
            if not mosaic_img_path: raise RuntimeError("Mosaicking function returned None.")
        except Exception as e_mosaic:
            logger.error(f"Mosaicking failed: {e_mosaic}", exc_info=True)
            block_success = False
    elif block_success:
         logger.error(f"Skipping mosaicking: Insufficient successful images ({len(processed_images)}/{len(block_ms_files)})")
         block_success = False

    # --- Stage 4: Photometry ---
    if mosaic_img_path and block_success:
        mosaic_fits_path = f"{os.path.splitext(mosaic_img_path)[0]}.linmos.fits"
        if os.path.exists(mosaic_fits_path):
            logger.info(f"Running photometry on mosaic: {mosaic_fits_path}")
            try:
                targets, references = photometry.identify_sources(config, mosaic_fits_path)
                if targets is not None and references is not None and len(targets) > 0:
                    phot_table = photometry.perform_aperture_photometry(config, mosaic_fits_path, targets, references)
                    if phot_table is not None:
                        rel_flux_table = photometry.calculate_relative_fluxes(config, phot_table)
                        if rel_flux_table is not None:
                            if not photometry.store_photometry_results(config, block_end_time, rel_flux_table):
                                raise RuntimeError("Failed to store photometry results.")
                        else: raise RuntimeError("Relative flux calculation failed.")
                    else: raise RuntimeError("Aperture photometry failed.")
                elif targets is None or len(targets) == 0:
                     logger.info("No target sources identified. Skipping photometry storage.")
                else: raise RuntimeError("Source identification failed (targets or references missing).")
            except Exception as e_phot:
                logger.error(f"Photometry stage failed: {e_phot}", exc_info=True)
                block_success = False
        else:
            logger.error(f"Mosaic FITS file missing: {mosaic_fits_path}. Cannot run photometry.")
            block_success = False

    # --- Stage 5: Optional Cleanup ---
    # TODO: Add cleanup logic based on config flag

    logger.info(f"--- Finished Processing Block: Success = {block_success} ---")
    return block_success


def main():
    """Parses arguments and runs the main pipeline driver."""
    parser = argparse.ArgumentParser(description="DSA-110 Continuum Pipeline - Batch Runner")
    parser.add_argument("-c", "--config", required=True, help="Path to the pipeline YAML config file.")
    parser.add_argument("--start-time", default=None, help="ISO timestamp (YYYY-MM-DDTHH:MM:SS) to start processing from (optional). Default: first available MS.")
    parser.add_argument("--end-time", default=None, help="ISO timestamp (YYYY-MM-DDTHH:MM:SS) to end processing at (optional). Default: last available MS.")
    parser.add_argument("--run-variability", action='store_true', help="Run variability analysis after processing blocks.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    # Add other args as needed (e.g., --force-reprocess, --skip-steps='cal,img')

    args = parser.parse_args()

    # --- Load Config and Setup Logging ---
    config = config_parser.load_config(args.config)
    if not config:
        sys.exit(1) # Error logged by parser

    log_dir = config['paths'].get('log_dir', 'logs') # Default to 'logs' if not in config
    # Ensure log dir exists
    os.makedirs(log_dir, exist_ok=True)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = pipeline_utils.setup_logging(log_dir, config_name="main_pipeline") # Use pipeline_utils setup
    logger.setLevel(log_level) # Ensure level is set based on args

    logger.info("--- Starting Main Pipeline Batch Run ---")
    logger.info(f"Using configuration: {args.config}")

    # --- Identify Blocks ---
    processing_blocks = find_ms_blocks_for_batch(config, args.start_time, args.end_time)
    if not processing_blocks:
         logger.info("No processing blocks identified in the specified range/directory. Exiting.")
         sys.exit(0)

    # --- Process Blocks ---
    total_blocks = len(processing_blocks)
    success_count = 0
    fail_count = 0
    for i, (block_end_time, block_ms_files) in enumerate(sorted(processing_blocks.items())):
        logger.info(f"===== Processing Block {i+1}/{total_blocks} (End Time: {block_end_time.iso}) =====")
        # Note: Duplicating the core logic from run_processing_block for now.
        # Ideally, refactor run_processing_block to be callable from here and the watcher.
        if process_block_batch(config, block_ms_files, block_end_time - timedelta(minutes=config['services']['mosaic_duration_min']), block_end_time):
             success_count += 1
        else:
             fail_count += 1
        logger.info(f"===== Finished Block {i+1}/{total_blocks} =====")


    logger.info(f"--- Batch Run Summary ---")
    logger.info(f"Total Blocks Found: {total_blocks}")
    logger.info(f"Successfully Processed: {success_count}")
    logger.info(f"Failed/Skipped: {fail_count}")

    # --- Variability Analysis ---
    if args.run_variability:
        logger.info("--- Running Variability Analysis ---")
        try:
            variability_analyzer.analyze_variability(config)
            logger.info("--- Variability Analysis Finished ---")
        except Exception as e_var:
            logger.error(f"Variability analysis failed: {e_var}", exc_info=True)
    else:
        logger.info("Skipping variability analysis as per arguments.")

    logger.info("--- Main Pipeline Batch Run Finished ---")


if __name__ == "__main__":
    main()