# pipeline/ms_creation.py

import os
import shutil
import warnings
import glob
from fnmatch import fnmatch

import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import EarthLocation, SkyCoord, HADec, ICRS
from pyuvdata import UVData
from pyuvdata import utils as uvutils
from pyuvdata.uvdata.ms import tables
from importlib.resources import files as importlib_files # Renamed to avoid conflict

# Pipeline imports
from .pipeline_utils import get_logger
from . import dsa110_utils # Import DSA-110 specific constants/functions

# Get logger for this module
logger = get_logger(__name__)

# --- Core uvh5 to MS Conversion Logic (Adapted from utils_hdf5.py) ---

def _load_uvh5_file(fnames: list, antenna_list: list = None, telescope_pos: EarthLocation = None):
    """Loads specific antennas from a list of uvh5 files and concatenates them.

    Internal helper function.

    Args:
        fnames (list): List of full paths to the hdf5 files to load (assumed to be one time chunk).
        antenna_list (list, optional): Antennas numbers (1-based) to extract. Defaults to None (all).
        telescope_pos (EarthLocation, optional): Telescope location. Defaults to None.

    Returns:
        UVData: pyuvdata UVData object containing loaded and concatenated data.
    """
    if not fnames:
        logger.error("No filenames provided to _load_uvh5_file.")
        return None

    logger.info(f"Loading {len(fnames)} HDF5 files for one time chunk...")

    uvdata = UVData()

    # Convert antenna numbers to pyuvdata expected format (names/numbers) if needed
    # Assuming antenna_list contains integer numbers from config
    # pyuvdata read expects antenna *names* or *numbers* based on file content.
    # dsa110_utils maps indices (0-based) to names ('padX')
    antenna_names_to_load = None
    if antenna_list is not None:
        valid_indices = dsa110_utils.valid_antennas_dsa110 # 0-based indices
        valid_numbers = valid_indices + 1 # 1-based numbers often used in lists
        # Filter the provided list to only include valid antennas for DSA-110
        antennas_to_request = [a for a in antenna_list if a in valid_numbers]
        if len(antennas_to_request) < len(antenna_list):
            logger.warning(f"Filtered antenna list to {len(antennas_to_request)} valid antennas.")
        if not antennas_to_request:
            logger.error("No valid antennas specified in the filtered list.")
            return None
        # Convert 1-based numbers back to 0-based indices for name lookup
        antenna_indices = [a - 1 for a in antennas_to_request]
        antenna_names_to_load = dsa110_utils.ant_inds_to_names_dsa110(antenna_indices)
        logger.info(f"Requesting antennas: {list(antenna_names_to_load)}")


    # Read the first file
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
            warnings.filterwarnings("ignore", message=r".*Telescope .* is not in known_telescopes.*")
            uvdata.read(fnames[0], file_type='uvh5', antenna_names=antenna_names_to_load, keep_all_metadata=False, run_check=False)
        logger.debug(f"Successfully read {fnames[0]}")
    except Exception as e:
        logger.error(f"Failed to read HDF5 file {fnames[0]}: {e}", exc_info=True)
        return None

    # pyuvdata really wants uvw_array to be float64:
    uvdata.uvw_array = uvdata.uvw_array.astype(np.float64)

    # Need BLTs and frequencies to check compatibility before combining
    prec_t = -2 * np.floor(np.log10(uvdata._time_array.tols[-1])).astype(int)
    prec_b = 8 # Assume baseline numbers don't exceed 8 digits
    try:
        # Ensure time_array and baseline_array are available and non-empty
        if uvdata.time_array is None or uvdata.baseline_array is None or len(uvdata.time_array) == 0:
             raise ValueError("Time or baseline array is missing/empty in the first file.")
        ref_blts = np.array([f"{blt[1]:.{prec_t}f}_{blt[0]:0{prec_b}d}" for blt in zip(uvdata.baseline_array, uvdata.time_array)])
        ref_freq = np.copy(uvdata.freq_array)
    except Exception as e:
        logger.error(f"Error preparing baseline/time check arrays: {e}", exc_info=True)
        return None


    # Iterate over remaining files and load, checking compatibility
    uvdata_to_append = []
    for f in fnames[1:]:
        uvdataf = UVData()
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
                warnings.filterwarnings("ignore", message=r".*Telescope .* is not in known_telescopes.*")
                uvdataf.read(f, file_type='uvh5', antenna_names=antenna_names_to_load, keep_all_metadata=False, run_check=False)
            uvdataf.uvw_array = uvdataf.uvw_array.astype(np.float64)
            logger.debug(f"Successfully read {f}")

            # Compare baseline-time arrays
            if uvdataf.time_array is None or uvdataf.baseline_array is None or len(uvdataf.time_array) == 0:
                raise ValueError(f"Time or baseline array is missing/empty in file {f}.")
            add_blts = np.array([f"{blt[1]:.{prec_t}f}_{blt[0]:0{prec_b}d}" for blt in zip(uvdataf.baseline_array, uvdataf.time_array)])
            if not np.array_equal(add_blts, ref_blts):
                logger.error(f"Baseline-time arrays do not match between {fnames[0]} and {f}. Skipping file.")
                continue # Or raise error depending on desired robustness

            # Make sure we're adding unique frequencies
            if len(np.intersect1d(ref_freq, uvdataf.freq_array)) > 0:
                logger.error(f"File {f} appears to have overlapping frequencies with previous files. Skipping.")
                continue # Or raise error

            uvdata_to_append.append(uvdataf)
            ref_freq = np.concatenate((ref_freq, uvdataf.freq_array))

        except Exception as e:
            logger.error(f"Failed to read or process HDF5 file {f}: {e}", exc_info=True)
            # Decide whether to continue with partial data or fail the whole chunk
            return None # Fail for now

    # Concatenate frequency axis
    try:
        if uvdata_to_append:
            logger.info(f"Concatenating {len(uvdata_to_append)} additional frequency chunks.")
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
                # Note: strict_uvw_antpos_check=False might be needed if positions vary slightly across files
                uvdata.fast_concat(uvdata_to_append, axis='freq', inplace=True, run_check=False, check_extra=False, run_check_acceptability=False, strict_uvw_antpos_check=True)
    except Exception as e:
        logger.error(f"Failed during frequency concatenation: {e}", exc_info=True)
        return None

    # Update frequency ordering
    try:
        uvdata.reorder_freqs(channel_order='freq', run_check=False)
    except Exception as e:
        logger.error(f"Failed to reorder frequencies: {e}", exc_info=True)
        return None

    # Set telescope info
    if telescope_pos is not None:
        uvdata.telescope_name = telescope_pos.info.name
        uvdata.telescope_location = np.array([
                                        telescope_pos.itrs.x.to_value(u.m),
                                        telescope_pos.itrs.y.to_value(u.m),
                                        telescope_pos.itrs.z.to_value(u.m)
                                    ])
        
    else:
        # Try to use the default DSA-110 location if none provided
        uvdata.telescope_name = dsa110_utils.loc_dsa110.info.name
        uvdata.telescope_location = list(dsa110_utils.loc_dsa110.itrs.x.to_value(u.m), dsa110_utils.loc_dsa110.itrs.y.to_value(u.m), dsa110_utils.loc_dsa110.itrs.z.to_value(u.m))
        logger.warning("Using default DSA-110 location.")

    # Rename antennas from numbers (if needed) to 'padX' format for consistency
    # Note: pyuvdata read *should* preserve names if they exist, but let's enforce
    try:
        uvdata.antenna_names = ['pad'+str(n) for n in uvdata.antenna_numbers]
    except Exception as e:
        logger.error(f"Failed to rename antennas: {e}", exc_info=True)
        # Non-fatal, proceed but log error


    logger.info(f"Finished loading data. Nbls: {uvdata.Nbls}, Ntimes: {uvdata.Ntimes}, Nfreqs: {uvdata.Nfreqs}, Nants: {uvdata.Nants_data}")
    return uvdata


def _compute_pointing(uvdata: UVData, telescope_pos: EarthLocation):
    """Determine pointing RA/Dec for each visibility based on time and fixed Dec."""
    # Assuming fixed declination from header and HA=0 at transit
    try:
        pt_dec_rad = uvdata.extra_keywords['phase_center_dec']
        logger.debug(f"Using fixed declination from HDF5 header: {np.rad2deg(pt_dec_rad):.4f} deg")
        pt_dec = pt_dec_rad * u.rad

        # Use unique times for efficiency
        utime_jd, uind = np.unique(uvdata.time_array, return_inverse=True)
        utime = Time(utime_jd, format='jd')

        # Calculate LST for unique times
        lst = utime.sidereal_time('apparent', longitude=telescope_pos.lon)
        # RA = LST at HA=0
        pt_ra = lst.rad * u.rad

        # Expand back to all times
        vis_ras = pt_ra[uind]
        vis_decs = np.full(uvdata.Ntimes * uvdata.Nbls, pt_dec.value) * u.rad # Nbls*Ntimes = Nblts

        # Check dimensions - Nblts should match vis_ras length
        if len(vis_ras) != uvdata.Nblts:
             logger.warning(f"Calculated RA dimension ({len(vis_ras)}) doesn't match Nblts ({uvdata.Nblts}). There might be an issue.")
             # Attempt to resize if possible, otherwise error
             # This case needs careful handling depending on uvdata structure details
             if len(vis_ras) == uvdata.Ntimes: # Maybe only unique times were needed?
                 # Need to repeat RA per baseline - this is complex, better to rely on pyuvdata phasing
                 logger.error("Dimension mismatch in pointing calculation requires rethink.")
                 return None
             else: # Mismatch is unexpected
                  logger.error(f"Unexpected dimension mismatch ({len(vis_ras)} vs {uvdata.Nblts}).")
                  return None


        pt_coords = SkyCoord(ra=vis_ras, dec=vis_decs, frame='icrs') # Assuming ICRS for simplicity
        return pt_coords

    except KeyError:
        logger.error("HDF5 file missing 'phase_center_dec' in extra_keywords!")
        return None
    except Exception as e:
        logger.error(f"Error computing pointing coordinates: {e}", exc_info=True)
        return None


def _set_phase_centers(uvdata: UVData, field_name_base: str, telescope_pos: EarthLocation):
    """Set phase centers in UVData object based on calculated pointing for drift scan."""
    logger.info("Calculating and setting phase centers for drift scan.")

    if telescope_pos is None:
        telescope_pos = dsa110_utils.loc_dsa110
        logger.warning("Using default DSA-110 location for phase setting.")

    try:
        # Calculate apparent coordinates for each unique time
        unique_times, inverse_indices = np.unique(uvdata.time_array, return_inverse=True)
        unique_lsts = Time(unique_times, format='jd').sidereal_time('apparent', longitude=telescope_pos.lon)
        fixed_dec = uvdata.extra_keywords['phase_center_dec'] * u.rad

        # Create phase center entries for each unique LST/RA
        uvdata.phase_center_catalog = {} # Clear existing catalog if any
        unique_phase_center_ids = []
        for i, (t, lst) in enumerate(zip(unique_times, unique_lsts)):
            ra = lst # At HA=0, RA = LST
            cat_name = f"{field_name_base}_T{i:04d}_RA{np.rad2deg(ra.rad):.3f}"
            cat_id = uvdata._add_phase_center(
                cat_name=cat_name,
                cat_type='sidereal', # Use drift type
                cat_lon=ra.rad,
                cat_lat=fixed_dec.to_value(u.rad),
                cat_frame='icrs', # Assuming ICRS for base coords
                cat_epoch=2000.0, # J2000 epoch
                info_source='calculated',
                force_update=False # Don't update if name exists (shouldn't here)
            )
            unique_phase_center_ids.append(cat_id)
            logger.debug(f"Added phase center ID {cat_id}: {cat_name}")

        # Assign phase center ID to each visibility based on its unique time index
        uvdata.phase_center_id_array = np.array(unique_phase_center_ids)[inverse_indices]

        # Phase the data to the calculated centers
        # This recalculates UVW coordinates correctly for each visibility based on its assigned phase center ID
        uvdata.phase_to_time(Time(uvdata.time_array, format='jd'))

        logger.info(f"Phased data to {len(unique_phase_center_ids)} unique pointing centers.")
        return uvdata

    except Exception as e:
        logger.error(f"Failed to set phase centers: {e}", exc_info=True)
        return None


def _make_calib_model(uvdata: UVData, config: dict, telescope_pos: EarthLocation):
    """Make a model for calibrator source(s) if specified in config."""

    calib_info = config.get('ms_creation', {}).get('calibrator_model', None)
    if calib_info is None:
        logger.info("No calibrator model requested in config.")
        return None

    logger.info("Generating calibrator model...")

    # Extract calibrator details from config
    # Assuming config structure like:
    # ms_creation:
    #   calibrator_model:
    #     sources:
    #       - name: '3C286'
    #         ra: '13h31m08.288s' # Astropy readable format
    #         dec: '+30d30m32.95s'
    #         epoch: 'J2000'
    #         flux_jy: 14.79 # Flux at ref_freq
    #         ref_freq_ghz: 1.4
    #         spectral_index: -0.45 # Optional
    #       - name: '...'
    #         # ... other sources
    #     beam_function: 'gaussian' # or 'airy' or 'none'
    #     beam_diameter_m: 4.7 # DSA-110 default

    sources = calib_info.get('sources', [])
    if not sources:
        logger.warning("`calibrator_model` specified in config, but no `sources` listed.")
        return None

    # Make a copy for the model
    uvcalib = uvdata.copy()
    uvcalib.data_array[:] = 0.0 + 0.0j # Initialize model visibilities to zero

    beam_func_name = calib_info.get('beam_function', 'gaussian')
    beam_diameter = calib_info.get('beam_diameter_m', dsa110_utils.diam_dsa110)

    if telescope_pos is None:
        telescope_pos = dsa110_utils.loc_dsa110

    # --- Determine pointing centers for beam calculation ---
    # Recompute unique pointings for beam attenuation calculation
    try:
        unique_times, uind = np.unique(uvcalib.time_array, return_inverse=True)
        astropy_times = Time(unique_times, format='jd')
        fixed_dec_rad = uvcalib.extra_keywords['phase_center_dec']
        lsts = astropy_times.sidereal_time('apparent', longitude=telescope_pos.lon)
        pointing_coords = SkyCoord(ra=lsts, dec=fixed_dec_rad * u.rad, frame='icrs') # Pointing direction at each unique time
        logger.debug(f"Calculated {len(pointing_coords)} unique pointing coords for beam model.")
    except Exception as e:
        logger.error(f"Failed to get pointing coords for beam model: {e}", exc_info=True)
        return None # Cannot calculate beam attenuation

    # --- Iterate through specified calibrator sources ---
    for i, src in enumerate(sources):
        try:
            src_name = src.get('name', f'Calib{i}')
            src_coord = SkyCoord(ra=src['ra'], dec=src['dec'], frame='icrs', epoch=src.get('epoch', 'J2000')) # Use ICRS for now
            flux_jy = float(src['flux_jy'])
            ref_freq_ghz = float(src.get('ref_freq_ghz', 1.4)) # Default ref freq
            spectral_index = src.get('spectral_index', None) # Optional spectral index

            logger.info(f"Adding source {src_name} ({src_coord.to_string('hmsdms')}) to model.")

            # Calculate frequency scaling
            freq_array_ghz = uvcalib.freq_array.flatten() / 1e9
            if spectral_index is not None:
                freq_scale = (freq_array_ghz / ref_freq_ghz)**float(spectral_index)
            else:
                freq_scale = np.ones_like(freq_array_ghz)
            model_flux_vs_freq = flux_jy * freq_scale

            # Calculate beam attenuation for this source vs time
            if beam_func_name == 'gaussian':
                beam_func = dsa110_utils.pb_dsa110
            # Add other beam models if needed (e.g., airy disk)
            # elif beam_func_name == 'airy': ...
            elif beam_func_name == 'none':
                logger.warning("Beam function set to 'none', applying no attenuation.")
                beam_attenuation = np.ones(uvcalib.Nblts) # Apply no beam effect
            else: # Default to Gaussian
                logger.warning(f"Unknown beam_function '{beam_func_name}', defaulting to Gaussian.")
                beam_func = dsa110_utils.pb_dsa110

            if beam_func_name != 'none':
                 # Calculate separation between source and pointing center for each unique time
                separations = pointing_coords.separation(src_coord)
                # Calculate beam response at each unique time and frequency
                # pb_dsa110 expects dist in rad, freq in GHz
                beam_resp_unique_times = beam_func(separations.rad, freq_array_ghz, diameter=beam_diameter)
                # beam_resp_unique_times shape might be (Nunique_times, 1, Nfreqs, 1) -> average over pols if needed, result should be (Nunique_times, Nfreqs)
                beam_resp_unique_times = np.squeeze(beam_resp_unique_times) # Remove length-1 dims
                if beam_resp_unique_times.ndim != 2: # Should be Ntimes x Nfreqs
                    logger.error(f"Unexpected beam response dimension: {beam_resp_unique_times.shape}")
                    continue

                # Expand beam response back to all Nblts times
                # Need to handle the Nbls dimension correctly. Assuming beam same for all baselines at a given time.
                # beam_attenuation should have shape (Nblts, Nfreqs)
                beam_attenuation_full = beam_resp_unique_times[uind, :] # Shape (Nblts, Nfreqs)
            else:
                beam_attenuation_full = np.ones((uvcalib.Nblts, uvcalib.Nfreqs)) # Shape (Nblts, Nfreqs)

            # Calculate source visibility phase (geometric delay) vs pointing center
            # uvcalib is already phased to pointing centers, so a source offset by (du, dv)
            # from the pointing center has phase exp(-2*pi*j*(u*du + v*dv))
            # where du = src_ra - pointing_ra, dv = src_dec - pointing_dec (small angle approx)
            # Need to get source offset in UVW frame? More complex.
            # Alternative: Phase uvcalib to the source, add flux, phase back.

            # Phase uvcalib to the current source location temporarily
            temp_cat_name = f"temp_phase_cal_{i}"
            uvcalib.phase(src_coord.ra.rad, src_coord.dec.rad, epoch=src.get('epoch', 'J2000'), phase_frame='icrs', cat_name=temp_cat_name)

            # Add the attenuated flux*freq_scale to the model visibilities for this source
            # Need to reshape arrays to match uvcalib.data_array shape (Nblts, 1, Nfreqs, Npols)
            # Assuming Stokes I, so apply to first polarization (index 0)
            # model_flux: (Nfreqs,)
            # beam_attenuation: (Nblts, Nfreqs)
            # Combine: (Nblts, Nfreqs) -> reshape to (Nblts, 1, Nfreqs, 1)
            vis_to_add = beam_attenuation_full * model_flux_vs_freq[np.newaxis, :] # Element-wise multiplication -> (Nblts, Nfreqs)
            vis_to_add = vis_to_add.reshape(uvcalib.Nblts, 1, uvcalib.Nfreqs, 1) # Add axes for spw, pol

            # Add to the existing model data (allows multiple sources)
            # Assuming uvcalib has Npols=1 or we target pol 0. Adapt if needed.
            uvcalib.data_array[:, :, :, 0:1] += vis_to_add.astype(complex) # Add to first pol


            # Phase back to the original pointing centers
            # Need to carefully re-apply the original phasing using the original catalog
            # Easiest might be to store original phase center id array first?
            # This part is tricky and error prone.
            # Let's skip phasing back for now - assume model is generated WRT source
            # and MS writer handles the final phasing if needed? -- review pyuvdata write_ms
            # **Correction**: Best practice is likely to phase back immediately.
            # Use phase_to_time with the original time array to revert to original centers.
            uvcalib.phase_to_time(Time(uvdata.time_array, format='jd')) # Use original uvdata times for phasing back
            logger.debug(f"Phased back for source {src_name}")


        except KeyError as e:
            logger.error(f"Missing required key for source {i} in calibrator_model config: {e}")
            continue
        except Exception as e:
            logger.error(f"Failed to process source {i} ({src.get('name', 'N/A')}) for model: {e}", exc_info=True)
            continue

    # Final check: ensure the phase center catalog matches the original uvdata
    uvcalib.phase_center_catalog = uvdata.phase_center_catalog.copy()
    uvcalib.phase_center_id_array = uvdata.phase_center_id_array.copy()

    logger.info("Successfully generated calibrator model.")
    return uvcalib


def _write_ms(uvdata: UVData, uvcalib: UVData, ms_outfile_base: str, protect_files: bool):
    """Write UVData object (+ optional model) to Measurement Set."""

    ms_outfile = f'{ms_outfile_base}.ms'
    logger.info(f"Writing Measurement Set to: {ms_outfile}")

    if os.path.exists(ms_outfile):
        if protect_files:
            logger.error(f"MS file {ms_outfile} already exists and protect_files is True. Skipping.")
            raise FileExistsError(f"{ms_outfile} exists.")
        else:
            logger.warning(f"MS file {ms_outfile} already exists. Removing existing file.")
            try:
                shutil.rmtree(ms_outfile)
            except Exception as e:
                logger.error(f"Failed to remove existing MS {ms_outfile}: {e}", exc_info=True)
                raise

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r".*Writing in the MS file that the units of the data are uncalib.*")
            # force_phase=False assumes _set_phase_centers did the work correctly
            uvdata.write_ms(ms_outfile,
                            run_check=False,
                            force_phase=False,
                            run_check_acceptability=False,
                            strict_uvw_antpos_check=True) # Keep strict checks on write

        # Add model/corrected columns if calibrator model exists
        if uvcalib is not None:
            logger.info("Adding MODEL_DATA and CORRECTED_DATA columns.")
            try:
                tables.addImagingColumns(ms_outfile)
                with tables.table(ms_outfile, readonly=False, ack=False) as tb:
                    # Ensure model data shape matches table expectation (usually Nrows, Nchans, Npols)
                    # uvdata array shape: (Nblts, 1, Nfreqs, Npols) -> need (Nblts, Nfreqs, Npols) ?
                    # Squeeze out the spectral window axis (axis 1) if it's singular
                    model_data_to_write = np.squeeze(uvcalib.data_array, axis=1)
                    corrected_data_to_write = np.squeeze(uvdata.data_array, axis=1)

                    if tb.ncols() == 0: # Check if table is empty
                         raise RuntimeError("MS table appears empty after write_ms.")

                    # Check expected shape (get shape of DATA column)
                    data_shape = tb.getcell('DATA', 0).shape # Shape of a single row's data cell
                    expected_shape = (uvdata.Nblts, ) + data_shape # Expected shape for full column
                    current_model_shape = model_data_to_write.shape

                    # If shapes don't match, log error but maybe don't fail? Or try reshaping?
                    if current_model_shape != expected_shape:
                         logger.warning(f"Shape mismatch for MODEL_DATA: Expected {expected_shape}, Got {current_model_shape}. Attempting to write anyway.")
                         # Add potential reshaping logic here if needed and understood

                    tb.putcol('MODEL_DATA', model_data_to_write)
                    # Initialize CORRECTED_DATA as DATA initially
                    tb.putcol('CORRECTED_DATA', corrected_data_to_write)
                logger.info("MODEL_DATA and CORRECTED_DATA columns added.")
            except Exception as e:
                logger.error(f"Failed to add imaging columns or write model/corrected data: {e}", exc_info=True)
                # Decide if this failure should halt processing

        logger.info(f"Successfully wrote MS: {ms_outfile}")
        return ms_outfile

    except Exception as e:
        logger.error(f"Failed to write MS file {ms_outfile}: {e}", exc_info=True)
        # Clean up potentially incomplete MS file
        if os.path.exists(ms_outfile):
            try:
                shutil.rmtree(ms_outfile)
                logger.info(f"Removed incomplete MS file: {ms_outfile}")
            except Exception as e_clean:
                logger.error(f"Failed to remove incomplete MS file {ms_outfile}: {e_clean}")
        return None


# --- Orchestration Logic (Adapted from pipeline_msmaker.py) ---

def find_hdf5_sets(config: dict):
    """Finds complete sets of HDF5 files in the incoming directory."""
    incoming_path = config['paths']['hdf5_incoming']
    expected_subbands = config['services']['hdf5_expected_subbands']
    spws_to_include = config['ms_creation'].get('spws', [f'sb{i:02d}' for i in range(expected_subbands)])
    logger.info(f"Searching for HDF5 file sets in: {incoming_path}")
    logger.debug(f"Expecting {expected_subbands} subbands per set. Including SPWs: {spws_to_include}")

    if not os.path.isdir(incoming_path):
        logger.error(f"Incoming HDF5 directory not found: {incoming_path}")
        return {}

    # Find all potential HDF5 files
    try:
        all_files = [f for f in os.listdir(incoming_path) if fnmatch(f, '20*T*.hdf5')]
        # Parse timestamps and subband info
        # Filename format assumed: YYYY-MM-DDThh:mm:ss_sbXX[_spl].hdf5
        parsed_files = {}
        for f in all_files:
            try:
                parts = f.split('_')
                timestamp_str = parts[0]
                spw_str = parts[1].replace('.hdf5', '') # e.g., 'sb01' or 'sb01spl'

                # Check if this SPW should be included
                base_spw = spw_str.split('spl')[0] # Get 'sbXX' part
                if base_spw not in spws_to_include:
                    continue

                if timestamp_str not in parsed_files:
                    parsed_files[timestamp_str] = {}
                parsed_files[timestamp_str][spw_str] = os.path.join(incoming_path, f)
            except Exception as e:
                logger.warning(f"Could not parse filename {f}: {e}")
                continue

        # Identify complete sets (exactly the required SPWs/subbands for a given timestamp)
        complete_sets = {}
        required_spw_set = set(spws_to_include)
        for timestamp, files_dict in parsed_files.items():
             # Check if all *required* spws are present for this timestamp
            present_spw_set = set(files_dict.keys())
            # We need to handle the case where spws_to_include might contain base names e.g. 'sb01'
            # but the files might be 'sb01' or 'sb01spl'. Modify check accordingly if needed.
            # For now, assume exact match of spw names in config and files found.
            if present_spw_set == required_spw_set:
                # Sort files by SPW name for consistent order
                sorted_filenames = [files_dict[spw] for spw in sorted(list(required_spw_set))]
                complete_sets[timestamp] = sorted_filenames
                logger.debug(f"Found complete set for timestamp {timestamp} with {len(sorted_filenames)} files.")

        logger.info(f"Found {len(complete_sets)} complete HDF5 sets.")
        return complete_sets # Dict: {'timestamp_str': [list_of_full_paths_sorted]}

    except Exception as e:
        logger.error(f"Error finding HDF5 sets: {e}", exc_info=True)
        return {}


def process_hdf5_set(config: dict, timestamp: str, hdf5_files: list):
    """Processes a single complete set of HDF5 files into an MS file."""
    logger.info(f"Processing HDF5 set for timestamp: {timestamp}")

    paths_config = config['paths']
    ms_creation_config = config['ms_creation']
    output_ms_dir = os.path.join(paths_config['pipeline_base_dir'], paths_config['ms_stage1_dir'])
    os.makedirs(output_ms_dir, exist_ok=True)

    # Define output MS name (without .ms extension)
    # Use a descriptive name, e.g., based on timestamp or other identifier
    # Ensure filename uniqueness if needed
    output_ms_base = os.path.join(output_ms_dir, f"drift_{timestamp}")

    # --- Load Data ---
    antenna_list = ms_creation_config.get('output_antennas', None) # Get antenna list from config
    uvdata = _load_uvh5_file(hdf5_files, antenna_list=antenna_list, telescope_pos=dsa110_utils.loc_dsa110)
    if uvdata is None:
        logger.error(f"Failed to load HDF5 data for {timestamp}. Skipping.")
        return None # Indicate failure

    # --- Set Phase Centers ---
    # Assuming field name base can be simple like 'drift'
    field_name_base = "drift"
    uvdata = _set_phase_centers(uvdata, field_name_base, dsa110_utils.loc_dsa110)
    if uvdata is None:
        logger.error(f"Failed to set phase centers for {timestamp}. Skipping.")
        return None

    # --- Make Calibrator Model (Optional) ---
    uvcalib = _make_calib_model(uvdata, config, dsa110_utils.loc_dsa110)
    # Note: _make_calib_model returns None if no model is requested or fails

    # --- Write MS ---
    protect_files = False # Allow overwriting for now, maybe add config option
    ms_output_path = _write_ms(uvdata, uvcalib, output_ms_base, protect_files)

    # --- Handle Processed HDF5 Files ---
    if ms_output_path: # Only handle if MS write was successful
        post_handle_mode = config['services'].get('hdf5_post_handle', 'none').lower()
        if post_handle_mode == 'delete':
            logger.info(f"Deleting processed HDF5 files for {timestamp}...")
            for f in hdf5_files:
                try:
                    os.remove(f)
                    logger.debug(f"Deleted {f}")
                except Exception as e:
                    logger.error(f"Failed to delete {f}: {e}")
        elif post_handle_mode == 'move':
            processed_dir = paths_config.get('hdf5_processed', None)
            if processed_dir:
                os.makedirs(processed_dir, exist_ok=True)
                logger.info(f"Moving processed HDF5 files for {timestamp} to {processed_dir}...")
                for f in hdf5_files:
                    try:
                        shutil.move(f, os.path.join(processed_dir, os.path.basename(f)))
                        logger.debug(f"Moved {f}")
                    except Exception as e:
                        logger.error(f"Failed to move {f}: {e}")
            else:
                logger.warning("hdf5_post_handle is 'move' but paths:hdf5_processed not defined in config.")
        # Else: 'none' - do nothing

    return ms_output_path # Return path to created MS file or None if failed


# Note: The search_for_calibrator function from pipeline_msmaker.py used astroquery
# and seemed geared towards finding *a* calibrator near a pointing for potential separate processing.
# This is different from the BPCAL strategy or the gain cal using a field model.
# If needed later for specific calibrator processing, it can be added back, possibly in the skymodel.py module.