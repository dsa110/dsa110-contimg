# pipeline/ms_processor_service.py

import time
import os
import sys
import argparse
import json
import glob
import yaml
from datetime import datetime, timedelta
from astropy.time import Time

# Watchdog imports
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Pipeline imports
try:
    from .pipeline_utils import setup_logging, get_logger
    from . import calibration, skymodel, imaging, mosaicking, photometry
    # Import config parser logic if separate
except ImportError:
    sys.path.append(os.path.dirname(__file__))
    from pipeline_utils import setup_logging, get_logger
    import calibration, skymodel, imaging, mosaicking, photometry

# Globals
logger = None
config = None
# State file path (simple persistence)
state_file_path = "ms_processor_state.json"
# In-memory state (loaded/saved from state_file_path)
pipeline_state = {
    "last_block_end_time_mjd": None, # MJD of the end time of the last successfully processed block
    "processing_block_mjd": None # MJD of the block currently being processed (simple lock)
}

def load_state():
    """Loads pipeline state from JSON file."""
    global pipeline_state
    if os.path.exists(state_file_path):
        try:
            with open(state_file_path, 'r') as f:
                pipeline_state = json.load(f)
            logger.info(f"Loaded pipeline state: {pipeline_state}")
        except Exception as e:
            logger.error(f"Failed to load state file {state_file_path}, starting fresh: {e}")
            # Reset to default if load fails
            pipeline_state = {"last_block_end_time_mjd": None, "processing_block_mjd": None}
    else:
        logger.info("State file not found, starting fresh.")

def save_state():
    """Saves pipeline state to JSON file."""
    try:
        with open(state_file_path, 'w') as f:
            json.dump(pipeline_state, f, indent=4)
        logger.debug(f"Saved pipeline state: {pipeline_state}")
    except Exception as e:
        logger.error(f"Failed to save state file {state_file_path}: {e}")


class MSEventHandler(FileSystemEventHandler):
    """Handles filesystem events for Measurement Set files."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.ms_dir = os.path.join(config['paths']['pipeline_base_dir'], config['paths']['ms_stage1_dir'])
        self.mosaic_duration = timedelta(minutes=config['services']['mosaic_duration_min'])
        self.mosaic_overlap = timedelta(minutes=config['services']['mosaic_overlap_min'])
        self.ms_chunk_duration = timedelta(minutes=config['services']['ms_chunk_duration_min'])
        self.num_ms_per_block = int(self.mosaic_duration / self.ms_chunk_duration)

        if self.num_ms_per_block <= 0:
             raise ValueError("Calculated number of MS per block is zero or negative.")

        logger.info(f"MS Event Handler initialized. Watching: {self.ms_dir}")
        logger.info(f"Mosaic duration={self.mosaic_duration}, overlap={self.mosaic_overlap}, MS/block={self.num_ms_per_block}")

    def on_created(self, event):
        """Called when a file or directory is created."""
        if event.is_directory and event.src_path.endswith('.ms'):
            logger.info(f"New MS directory detected: {event.src_path}")
            # Trigger check for new mosaic block readiness
            # Use a short delay in case other related files are still being written
            time.sleep(5) # Small delay
            self.check_for_mosaicable_block()

    def check_for_mosaicable_block(self):
        """Checks if enough MS files exist for the next processing block."""
        global pipeline_state

        # Basic check: Don't start check if already processing
        if pipeline_state.get("processing_block_mjd") is not None:
             logger.debug(f"Already processing block ending {pipeline_state['processing_block_mjd']}. Skipping check.")
             return

        logger.debug("Checking for mosaicable block...")

        # Determine start time of the *next* block to look for
        last_end_mjd = pipeline_state.get("last_block_end_time_mjd", None)
        if last_end_mjd is None:
            # Find the earliest MS file to establish a starting point
            try:
                all_ms = sorted(glob.glob(os.path.join(self.ms_dir, "drift_*.ms")))
                if not all_ms:
                     logger.debug("No MS files found yet.")
                     return
                first_ms_name = os.path.basename(all_ms[0])
                # Assumes drift_YYYYMMDDTHHMMSS.ms format
                start_timestamp_str = first_ms_name.split('_')[1].replace('.ms','')
                start_time = Time(datetime.strptime(start_timestamp_str, "%Y%m%dT%H%M%S"), format='datetime', scale='utc')
                # Set the 'last end time' such that the first block starts near the first MS
                # First block covers T0 to T0 + duration
                # Effective "last end time" for this logic would be T0 + overlap
                last_end_time = start_time + self.mosaic_overlap
                last_end_mjd = last_end_time.mjd
                logger.info(f"First MS found at {start_time.iso}. Setting initial 'last block end' for logic to MJD {last_end_mjd:.6f}")

            except Exception as e:
                logger.error(f"Could not determine start time from MS files: {e}")
                return
        else:
            last_end_time = Time(last_end_mjd, format='mjd', scale='utc')


        # Calculate time range for the next block
        # Next block starts at (last_end - overlap) and ends at (last_end - overlap + duration)
        next_block_start_time = last_end_time - self.mosaic_overlap
        next_block_end_time = next_block_start_time + self.mosaic_duration
        next_block_end_mjd = next_block_end_time.mjd

        logger.info(f"Checking for MS files needed for block: {next_block_start_time.iso} to {next_block_end_time.iso}")

        # Find MS files within this time range
        required_ms_files = []
        try:
            all_ms_files = glob.glob(os.path.join(self.ms_dir, "drift_*.ms"))
            for ms_path in all_ms_files:
                ms_name = os.path.basename(ms_path)
                try:
                    # Extract time from filename (assuming drift_YYYYMMDDTHHMMSS.ms)
                    ts_str = ms_name.split('_')[1].replace('.ms', '')
                    ms_time = Time(datetime.strptime(ts_str, "%Y%m%dT%H%M%S"), format='datetime', scale='utc')
                    # Check if the MS *start* time is within the block range
                    # (A 5-min MS starting at 08:55 belongs to the 08:50-09:50 block)
                    if next_block_start_time <= ms_time < next_block_end_time:
                         required_ms_files.append(ms_path)
                except (IndexError, ValueError) as e_parse:
                     logger.warning(f"Could not parse timestamp from MS file {ms_name}: {e_parse}")
                     continue

            logger.debug(f"Found {len(required_ms_files)} MS files potentially in range.")

            # Check if we have the required number of files
            if len(required_ms_files) >= self.num_ms_per_block:
                # Found a complete block!
                # Sort them just in case glob order isn't guaranteed
                required_ms_files.sort()
                # Select exactly num_ms_per_block (handles case if >12 found somehow)
                block_ms_files = required_ms_files[:self.num_ms_per_block]
                logger.info(f"Found {len(block_ms_files)} MS files - sufficient for block ending {next_block_end_time.iso}. Triggering processing.")

                # --- Simple Lock and Process ---
                pipeline_state["processing_block_mjd"] = next_block_end_mjd
                save_state() # Mark as processing

                try:
                    # ** This is where the main pipeline sequence is called **
                    # This call can take a long time and will block the watcher
                    # A better implementation would use multiprocessing or task queues
                    success = self.run_processing_block(block_ms_files, next_block_start_time, next_block_end_time)

                    if success:
                         # Update state only if processing succeeded
                         pipeline_state["last_block_end_time_mjd"] = next_block_end_mjd
                         logger.info(f"Successfully processed block ending MJD {next_block_end_mjd:.6f}.")
                    else:
                         logger.error(f"Processing failed for block ending MJD {next_block_end_mjd:.6f}. State not updated.")

                except Exception as e:
                     logger.error(f"Unhandled exception during processing block {next_block_end_mjd}: {e}", exc_info=True)
                finally:
                     # --- Release Lock ---
                     pipeline_state["processing_block_mjd"] = None
                     save_state() # Save state (either updated last_time or just cleared processing lock)
            else:
                logger.debug(f"Block ending {next_block_end_time.iso} is incomplete ({len(required_ms_files)}/{self.num_ms_per_block} MS files found).")

        except Exception as e:
            logger.error(f"Error during MS block check: {e}", exc_info=True)


    def run_processing_block(self, block_ms_files: list, block_start_time: Time, block_end_time: Time):
        """Runs the full cal, imaging, mosaic, photometry chain for a block."""
        # Note: This function can take a long time and will block the watcher
        # in this simple implementation. Consider async/subprocess execution later.

        logger.info(f"--- Starting Processing Block: {block_start_time.iso} to {block_end_time.iso} ---")
        block_success = True # Assume success initially
        paths_config = self.config['paths']
        cal_tables_dir = os.path.join(paths_config['pipeline_base_dir'], paths_config['cal_tables_dir'])
        skymodels_dir = os.path.join(paths_config['pipeline_base_dir'], paths_config['skymodels_dir'])
        images_dir = os.path.join(paths_config['pipeline_base_dir'], paths_config['images_dir'])
        os.makedirs(cal_tables_dir, exist_ok=True)
        os.makedirs(skymodels_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)

        latest_bcal_table = None
        gcal_table_path = None
        cl_path = None
        mask_path = None
        template_image_path = None # For mask creation

        # --- Stage 1: Determine Calibration Inputs for the Block ---
        try:
            # 1a. Find latest Bandpass Calibrator Table
            bcal_files = sorted(glob.glob(os.path.join(cal_tables_dir, "*.bcal")))
            if not bcal_files:
                logger.error("No BPCAL tables found in {cal_tables_dir}. Cannot proceed.")
                return False # Critical error

            latest_bcal_table = bcal_files[-1] # Simplistic: assumes newest file is the one to use
            # TODO: Add check based on bcal_interval_hours and block_end_time? Trigger BPCAL if needed?
            # This check might better belong in check_for_mosaicable_block
            logger.info(f"Selected BPCAL table: {os.path.basename(latest_bcal_table)}")

            # 1b. Calculate Block Center and Generate Sky Model (for Gain Cal & Masking)
            block_center_time = block_start_time + (block_end_time - block_start_time) / 2.0
            block_center_mjd = block_center_time.mjd
            # Calculate center RA = LST at center time
            # Requires telescope location from dsa110_utils or config
            telescope_loc = dsa110_utils.loc_dsa110 # Assuming imported
            center_lst = block_center_time.sidereal_time('apparent', longitude=telescope_loc.lon)
            center_ra = center_lst.to(u.deg)
            # Get fixed declination - NEEDS configuration or reading from first MS header
            # Placeholder: Get from config if available, otherwise raise error or use default
            fixed_dec_deg = self.config.get('calibration', {}).get('fixed_declination_deg', None)
            if fixed_dec_deg is None:
                 logger.error("Fixed declination ('calibration:fixed_declination_deg') not set in config. Cannot determine block center.")
                 # Alternative: Try reading from block_ms_files[0] header here (adds complexity)
                 return False
            center_dec = fixed_dec_deg * u.deg
            center_coord = SkyCoord(ra=center_ra, dec=center_dec, frame='icrs')
            logger.info(f"Calculated block center coordinate: {center_coord.to_string('hmsdms')}")

            # Define CL path using block time
            cl_filename = f"sky_field_{block_start_time.strftime('%Y%m%dT%H%M%S')}.cl"
            cl_output_path = os.path.join(skymodels_dir, cl_filename)

            # Create the component list for the entire block
            cl_path, _ = skymodel.create_field_component_list(self.config, center_coord, cl_output_path)
            if not cl_path:
                logger.error("Failed to create field sky model component list for the block.")
                return False # Cannot proceed without sky model

            # 1c. Perform Gain Calibration for the Block
            time_segment_str = f"{block_start_time.strftime('%Y%m%dT%H%M%S')}_{block_end_time.strftime('%Y%m%dT%H%M%S')}"
            gcal_table_path = calibration.perform_gain_calibration(self.config, block_ms_files, cl_path, time_segment_str)
            if not gcal_table_path:
                logger.error("Gain calibration failed for the block.")
                return False # Cannot proceed without gain solutions

            # 1d. Create Clean Mask (if configured) - Needs a template image!
            # Simplification: Create mask based on the *first* MS file's structure before looping.
            # This assumes WCS doesn't change drastically across the 5-min MS files.
            use_mask_config = self.config.get('imaging',{}).get('use_clean_mask', False)
            if use_mask_config:
                logger.info("Preparing to create clean mask for the block.")
                # We need a template. Let's try using the first MS file to *define* an image structure.
                # A better way might be needed if tclean params change per MS.
                # For now, create a dummy template or use the first MS's metadata?
                # Let's defer mask creation until we have the first *real* image.
                logger.warning("Deferring mask creation until first image is made (template needed).")
                # Alternative: Define template parameters in config and use `imager` tool to make blank image? More complex.

        except Exception as e:
            logger.error(f"Failed during calibration setup stage for block: {e}", exc_info=True)
            return False

        # --- Stage 2: Process Each MS File in the Block ---
        processed_images = []
        processed_pbs = []
        template_image_path = None # Track template for mask creation

        for i, ms_path in enumerate(block_ms_files):
            logger.info(f"Processing MS {i+1}/{len(block_ms_files)}: {os.path.basename(ms_path)}")
            ms_base = os.path.splitext(os.path.basename(ms_path))[0]
            # Define base name for all outputs related to this MS
            image_base = os.path.join(images_dir, ms_base)

            # 2a. Flagging (Reset state might be needed depending on workflow)
            # if not calibration.reset_ms_state(ms_path): block_success = False; continue
            if not calibration.flag_rfi(self.config, ms_path): block_success = False; continue
            if not calibration.flag_general(self.config, ms_path): block_success = False; continue

            # 2b. Apply Calibration
            if not calibration.apply_calibration(self.config, ms_path, latest_bcal_table, [gcal_table_path]): # Pass GCAL table as list
                logger.error(f"Failed calibration application for {ms_path}. Skipping.")
                block_success = False
                continue

            ms_to_image = ms_path # Assume tclean uses CORRECTED column

            # 2c. Create Mask (if first image is done and mask needed)
            current_mask_path = None
            if use_mask_config and cl_path:
                if mask_path is None: # Only create mask once per block
                    if template_image_path is not None: # Check if template is available
                        mask_output_path = os.path.join(skymodels_dir, f"mask_{block_start_time.strftime('%Y%m%dT%H%M%S')}.mask")
                        mask_path = imaging.create_clean_mask(self.config, cl_path, template_image_path, mask_output_path)
                        if not mask_path:
                             logger.warning(f"Failed to create block mask using template {template_image_path}. Proceeding without mask.")
                             mask_path = None # Ensure it's None if failed
                        else:
                             logger.info(f"Using block mask: {mask_path}")
                    else:
                         logger.debug("Template image not yet available for mask creation.")
                current_mask_path = mask_path # Use the block mask if available

            # 2d. Imaging (tclean)
            logger.info(f"Running tclean for {ms_path}")
            # Pass cl_path for startmodel, current_mask_path for mask
            tclean_image_basename = imaging.run_tclean(self.config, ms_to_image, image_base, cl_path=cl_path, mask_path=current_mask_path)

            if tclean_image_basename:
                img_path = f"{tclean_image_basename}.image"
                pb_path = f"{tclean_image_basename}.pb"
                # Check essential outputs exist
                if os.path.exists(img_path) and os.path.exists(pb_path):
                    processed_images.append(img_path)
                    processed_pbs.append(pb_path)
                    logger.info(f"Successfully imaged {ms_path}")
                    if template_image_path is None: # Use first successfully created image as template for subsequent masks
                        template_image_path = img_path
                        logger.info(f"Set mask template image path to: {template_image_path}")
                else:
                    logger.error(f"tclean finished but output image or pb missing for {tclean_image_basename}")
                    block_success = False # Mark block as potentially incomplete
            else:
                logger.error(f"tclean failed for {ms_path}. Skipping.")
                block_success = False # Mark block as potentially incomplete

        # --- Stage 3: Mosaicking ---
        mosaic_img_path = None
        # Check if enough images were processed successfully
        min_images_needed = int(self.num_ms_per_block * 0.75) # Example threshold: 75%
        if len(processed_images) < min_images_needed:
            logger.error(f"Insufficient successful images ({len(processed_images)}/{self.num_ms_per_block}) generated for mosaicking.")
            block_success = False
        else:
            logger.info(f"Creating mosaic from {len(processed_images)} images...")
            mosaic_basename = f"mosaic_{block_start_time.strftime('%Y%m%dT%H%M%S')}_{block_end_time.strftime('%Y%m%dT%H%M%S')}"
            mosaic_img_path, _ = mosaicking.create_mosaic(self.config, processed_images, processed_pbs, mosaic_basename)
            if not mosaic_img_path:
                logger.error("Mosaicking failed.")
                block_success = False

        # --- Stage 4: Photometry ---
        if mosaic_img_path and block_success: # Only run photometry if mosaicking succeeded
            mosaic_fits_path = f"{os.path.splitext(mosaic_img_path)[0]}.linmos.fits"
            if os.path.exists(mosaic_fits_path):
                logger.info(f"Running photometry on mosaic: {mosaic_fits_path}")
                try:
                    targets, references = photometry.identify_sources(self.config, mosaic_fits_path)
                    if targets is not None and references is not None and len(targets) > 0:
                        phot_table = photometry.perform_aperture_photometry(self.config, mosaic_fits_path, targets, references)
                        if phot_table is not None:
                            rel_flux_table = photometry.calculate_relative_fluxes(self.config, phot_table)
                            if rel_flux_table is not None:
                                # Use block_end_time as the representative time for this data point
                                phot_success = photometry.store_photometry_results(self.config, block_end_time, rel_flux_table)
                                if not phot_success:
                                    logger.error("Failed to store photometry results.")
                                    block_success = False
                            else: logger.error("Relative flux calculation failed."); block_success = False
                        else: logger.error("Aperture photometry failed."); block_success = False
                    elif targets is None or len(targets) == 0:
                         logger.warning("No target sources identified or source identification failed. Skipping photometry storage.")
                         # Don't mark block as failed if no targets, just no photometry results
                    else: # references might be None or empty, but targets exist
                         logger.error("Source identification failed (targets or references missing).")
                         block_success = False # Mark as failure if ID failed
                except Exception as e_phot:
                    logger.error(f"Error during photometry stage: {e_phot}", exc_info=True)
                    block_success = False
            else:
                logger.error(f"Mosaic FITS file missing after export: {mosaic_fits_path}. Cannot run photometry.")
                block_success = False

        # --- Stage 5: Optional Cleanup ---
        # Add logic here to remove intermediate files (block_ms_files, individual images/pbs) if configured

        logger.info(f"--- Finished Processing Block: Success = {block_success} ---")
        return block_success


def run_ms_processor(config_path):
    """Main function to run the MS processor service."""
    global logger, config, state_file_path

    # --- Load Config ---
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if config is None: raise ValueError("Config file is empty or invalid YAML.")
        # Set state file path based on config if possible
        phot_dir = os.path.join(config['paths']['pipeline_base_dir'], config['paths']['photometry_dir'])
        state_file_path = os.path.join(phot_dir,"ms_processor_state.json")

    except Exception as e:
        print(f"FATAL: Could not load/parse config file {config_path}: {e}")
        sys.exit(1)

    # --- Setup Logging ---
    log_dir = config['paths'].get('log_dir', '../logs')
    if not os.path.isabs(log_dir):
         log_dir = os.path.join(os.path.dirname(__file__), log_dir)
    logger = setup_logging(log_dir, config_name="ms_processor")

    # --- Load Initial State ---
    load_state()
    # Clear processing lock on startup in case previous run crashed
    if pipeline_state.get("processing_block_mjd") is not None:
         logger.warning("Clearing processing lock found from previous run.")
         pipeline_state["processing_block_mjd"] = None
         save_state()


    # --- Initialize Watcher ---
    watch_path = os.path.join(config['paths']['pipeline_base_dir'], config['paths']['ms_stage1_dir'])
    if not os.path.isdir(watch_path):
        try: # Attempt to create directory
             os.makedirs(watch_path)
             logger.info(f"Created MS Stage 1 directory: {watch_path}")
        except Exception as e:
             logger.error(f"MS Stage 1 directory not found and could not be created: {watch_path}. Exiting: {e}")
             sys.exit(1)


    event_handler = MSEventHandler(config)
    observer = Observer()
    # Watch for directory creation events ('*.ms' are directories)
    observer.schedule(event_handler, watch_path, recursive=False)

    logger.info(f"Starting MS processor watcher on directory: {watch_path}")
    observer.start()

    # Also run an initial check in case files arrived before watcher started
    event_handler.check_for_mosaicable_block()

    try:
        while True:
            # Keep the main thread alive.
            # Could add periodic re-check call here instead of relying solely on events
            time.sleep(config['services'].get('ms_processor_poll_interval_sec', 120))
            logger.debug("MS Processor alive...")
            # Optionally, trigger check_for_mosaicable_block periodically too
            # event_handler.check_for_mosaicable_block()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping MS processor.")
    except Exception as e:
        logger.error(f"MS processor main loop encountered an error: {e}", exc_info=True)
    finally:
        logger.info("Stopping observer...")
        observer.stop()
        observer.join()
        logger.info("MS processor stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MS Processor Service for DSA-110 Pipeline")
    parser.add_argument("-c", "--config", required=True, help="Path to the pipeline YAML config file.")
    args = parser.parse_args()
    run_ms_processor(args.config)