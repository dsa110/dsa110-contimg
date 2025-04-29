# pipeline/main_driver.py

import argparse
import os
import sys
import glob
from datetime import datetime
from astropy.time import Time

# Pipeline module imports
try:
    from . import config_parser
    from . import pipeline_utils
    from . import ms_creation # Although unlikely used directly in batch mode? Maybe for reprocessing?
    from . import calibration
    from . import skymodel
    from . import imaging
    from . import mosaicking
    from . import photometry
    from . import variability_analyzer
    from . import dsa110_utils # Needed for location if calculating coords
except ImportError:
    # Allow running script directly for testing, adjust paths
    sys.path.append(os.path.dirname(__file__))
    import config_parser
    import pipeline_utils
    import ms_creation
    import calibration
    import skymodel
    import imaging
    import mosaicking
    import photometry
    import variability_analyzer
    import dsa110_utils


def find_ms_blocks_for_batch(config, start_time_iso=None, end_time_iso=None):
    """Identifies blocks of MS files suitable for batch processing."""
    logger = pipeline_utils.get_logger(__name__)
    ms_dir = config['paths']['ms_stage1_dir']
    duration = timedelta(minutes=config['services']['mosaic_duration_min'])
    overlap = timedelta(minutes=config['services']['mosaic_overlap_min'])
    ms_chunk = timedelta(minutes=config['services']['ms_chunk_duration_min'])
    num_ms_per_block = int(duration / ms_chunk)

    if not os.path.isdir(ms_dir):
        logger.error(f"MS Stage 1 directory not found: {ms_dir}")
        return {}

    all_ms = sorted(glob.glob(os.path.join(ms_dir, "drift_*.ms")))
    if not all_ms:
        logger.warning("No MS files found in {ms_dir} for batch processing.")
        return {}

    # Parse timestamps
    ms_times = {}
    for ms_path in all_ms:
        ms_name = os.path.basename(ms_path)
        try:
            ts_str = ms_name.split('_')[1].replace('.ms', '')
            ms_start_time = Time(datetime.strptime(ts_str, "%Y%m%dT%H%M%S"), format='datetime', scale='utc')
            ms_times[ms_start_time] = ms_path
        except Exception:
            logger.warning(f"Could not parse time from {ms_name}. Skipping.")
            continue

    if not ms_times:
        logger.error("No valid MS files found after time parsing.")
        return {}

    # Determine processing range
    first_ms_time = min(ms_times.keys())
    last_ms_time = max(ms_times.keys())

    proc_start_time = Time(start_time_iso) if start_time_iso else first_ms_time
    # End time for *inclusion*, block end time can be later
    proc_end_time = Time(end_time_iso) if end_time_iso else (last_ms_time + ms_chunk)

    logger.info(f"Processing MS files from {proc_start_time.iso} up to {proc_end_time.iso}")

    # Group MS files into overlapping blocks
    blocks = {} # Key: block_end_time (astropy Time), Value: list of MS paths
    current_block_start = proc_start_time
    while current_block_start < proc_end_time:
        block_end = current_block_start + duration
        block_files = []
        # Find all MS files whose *start* time falls within this block definition
        for t_start, ms_path in ms_times.items():
            if current_block_start <= t_start < block_end:
                block_files.append(ms_path)

        # Only consider blocks that *start* within the requested range
        # and have enough files
        if len(block_files) >= num_ms_per_block:
            block_files.sort()
            # Ensure block end time doesn't exceed overall end time significantly?
            # Use precise end time for key
            blocks[block_end] = block_files[:num_ms_per_block] # Take exactly the needed number
            logger.debug(f"Identified block ending {block_end.iso} with {len(blocks[block_end])} files.")

        # Advance start time for next block search (step by duration - overlap)
        current_block_start += (duration - overlap)

    logger.info(f"Identified {len(blocks)} potential processing blocks for batch run.")
    return blocks


def run_main_pipeline(config_path, args):
    """Main pipeline execution logic for batch mode."""

    # --- Load Config and Setup Logging ---
    config = config_parser.load_config(config_path)
    if not config:
        # Error already logged by load_config
        sys.exit(1)
    logger = pipeline_utils.setup_logging(config['paths']['log_dir'], config_name="main_pipeline")
    logger.info("--- Starting Main Pipeline Batch Run ---")
    logger.info(f"Using configuration: {config_path}")
    # Log key parameters?

    # --- Identify Blocks to Process ---
    # TODO: Add logic to check for already processed blocks based on state/outputs?
    # For now, process all blocks found in the time range.
    processing_blocks = find_ms_blocks_for_batch(config, args.start_time, args.end_time)
    if not processing_blocks:
         logger.info("No processing blocks identified. Exiting.")
         return

    # --- Process Blocks Sequentially ---
    # Re-use the processing logic from the MS processor service (needs slight adaptation?)
    # We need an instance of the handler or replicate the logic here.
    # Let's replicate/adapt run_processing_block here for simplicity in batch mode.
    # Note: This duplicates logic, ideally refactor run_processing_block to be callable from both.

    for block_end_time, block_ms_files in sorted(processing_blocks.items()):
        # Calculate block start time based on end time and duration
        block_start_time = block_end_time - timedelta(minutes=config['services']['mosaic_duration_min'])

        logger.info(f"--- Starting Processing Block: {block_start_time.iso} to {block_end_time.iso} ---")
        block_success = True # Assume success initially
        paths_config = config['paths']
        cal_tables_dir = paths_config['cal_tables_dir']
        skymodels_dir = paths_config['skymodels_dir']
        images_dir = paths_config['images_dir']

        latest_bcal_table = None
        gcal_table_path = None
        cl_path = None
        mask_path = None
        template_image_path = None

        # --- Stage 1: Calibration Setup ---
        try:
            # Find BPCAL (same logic as in run_processing_block)
            bcal_files = sorted(glob.glob(os.path.join(cal_tables_dir, "*.bcal")))
            if not bcal_files: raise RuntimeError("No BPCAL tables found.")
            # Find the latest one created *before* this block ends
            valid_bcals = [b for b in bcal_files if os.path.getmtime(b) <= block_end_time.unix] # Check modification time
            if not valid_bcals:
                 logger.warning(f"No BPCAL table found created before {block_end_time.iso}. Using newest overall: {bcal_files[-1]}")
                 latest_bcal_table = bcal_files[-1]
            else:
                 latest_bcal_table = valid_bcals[-1]
            logger.info(f"Using BPCAL table: {os.path.basename(latest_bcal_table)}")

            # Generate Sky Model and Gain Cal (same logic as in run_processing_block)
            block_center_time = block_start_time + (block_end_time - block_start_time) / 2.0
            telescope_loc = dsa110_utils.loc_dsa110
            center_lst = block_center_time.sidereal_time('apparent', longitude=telescope_loc.lon)
            center_ra = center_lst.to(u.deg)
            fixed_dec_deg = config.get('calibration', {}).get('fixed_declination_deg', None)
            if fixed_dec_deg is None: raise ValueError("fixed_declination_deg not set.")
            center_dec = fixed_dec_deg * u.deg
            center_coord = SkyCoord(ra=center_ra, dec=center_dec, frame='icrs')

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
                 mask_output_path = None # No mask will be created/used

        except Exception as e:
            logger.error(f"Failed during calibration setup stage for block: {e}", exc_info=True)
            block_success = False
            # Continue to next block if setup fails
            logger.info(f"--- Skipping Failed Block: {block_start_time.iso} to {block_end_time.iso} ---")
            continue

        # --- Stage 2: Process MS Files ---
        processed_images = []
        processed_pbs = []
        mask_created = False # Flag to track if mask was made

        for i, ms_path in enumerate(block_ms_files):
            if not block_success: break # Stop processing MS if block setup failed
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
                if use_mask_config and mask_output_path: # Check if mask is desired and path defined
                    if not mask_created and template_image_path is not None: # Check if template ready & mask not yet made
                        logger.info("Creating block mask using template...")
                        if imaging.create_clean_mask(config, cl_path, template_image_path, mask_output_path):
                             mask_created = True
                             logger.info(f"Using block mask: {mask_output_path}")
                        else:
                             logger.warning("Failed to create block mask. Proceeding without.")
                    if mask_created: # Use the mask if it was successfully created
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
                        if template_image_path is None: # Set template after first success
                            template_image_path = img_path
                    else:
                        raise RuntimeError(f"tclean image/pb missing for {tclean_image_basename}")
                else:
                    raise RuntimeError("tclean failed.")

            except Exception as e_ms:
                 logger.error(f"Failed processing MS {ms_path}: {e_ms}", exc_info=True)
                 block_success = False
                 # Optionally break loop or continue to try other MS files? Continue for now.

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
        elif block_success: # Not enough images, but previous steps didn't fail block
             logger.error(f"Skipping mosaicking: Insufficient successful images ({len(processed_images)}/{len(block_ms_files)})")
             block_success = False # Mark block as failed if mosaicking skipped

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
                    else: raise RuntimeError("Source identification failed.")
                except Exception as e_phot:
                    logger.error(f"Photometry stage failed: {e_phot}", exc_info=True)
                    block_success = False
            else:
                logger.error(f"Mosaic FITS file missing: {mosaic_fits_path}. Cannot run photometry.")
                block_success = False

        logger.info(f"--- Finished Processing Block: Success = {block_success} ---")

    # --- Final Step: Variability Analysis ---
    if args.run_variability:
        logger.info("--- Running Variability Analysis ---")
        try:
            variability_analyzer.analyze_variability(config)
        except Exception as e_var:
            logger.error(f"Variability analysis failed: {e_var}", exc_info=True)
    else:
        logger.info("Skipping variability analysis as per arguments.")

    logger.info("--- Main Pipeline Batch Run Finished ---")


def main():
    """Parses arguments and runs the main pipeline."""
    parser = argparse.ArgumentParser(description="DSA-110 Continuum Pipeline - Batch Runner")
    parser.add_argument("-c", "--config", required=True, help="Path to the pipeline YAML config file.")
    parser.add_argument("--start-time", default=None, help="ISO timestamp (YYYY-MM-DDTHH:MM:SS) to start processing from (optional). Default: first available MS.")
    parser.add_argument("--end-time", default=None, help="ISO timestamp (YYYY-MM-DDTHH:MM:SS) to end processing at (optional). Default: last available MS.")
    parser.add_argument("--run-variability", action='store_true', help="Run variability analysis after processing blocks.")
    # Add other args as needed (e.g., --force-reprocess)

    args = parser.parse_args()

    # Basic check for config file existence before calling main logic
    if not os.path.exists(args.config):
         print(f"ERROR: Config file not found at {args.config}")
         sys.exit(1)

    run_main_pipeline(args.config, args)

if __name__ == "__main__":
    main()