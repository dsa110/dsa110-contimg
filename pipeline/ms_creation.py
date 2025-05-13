# pipeline/ms_creation.py

import os
import shutil
import warnings
import glob
from fnmatch import fnmatch
from datetime import datetime 

import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import EarthLocation, SkyCoord, HADec, ICRS, Angle
import pyuvdata 
from pyuvdata import UVData

# Attempt to import phasing utilities
# Based on user feedback, pyuvdata.utils.phasing is the path that works in their environment.
# This might indicate an older pyuvdata structure or a mixed environment.
try:
    from pyuvdata.utils.phasing import calc_app_coords, calc_frame_pos_angle, calc_uvw
    # Logger will be initialized after this block, so print for now
    print("INFO: Successfully imported phasing utilities from pyuvdata.utils.phasing")
    PHASING_MODULE_SOURCE = "pyuvdata.utils.phasing"
except ImportError:
    try:
        from pyuvdata.coordinates import calc_app_coords, calc_frame_pos_angle, calc_uvw
        print("INFO: Imported phasing utilities from pyuvdata.coordinates (standard for pyuvdata >=2.2)")
        PHASING_MODULE_SOURCE = "pyuvdata.coordinates"
    except ImportError as e:
        print(f"CRITICAL ERROR: Could not import phasing utilities: {e}")
        calc_app_coords, calc_frame_pos_angle, calc_uvw = None, None, None # Define to prevent NameErrors
        PHASING_MODULE_SOURCE = "NONE - IMPORT FAILED"


from pyuvdata.uvdata.ms import tables
from importlib.resources import files as importlib_files 
import inspect 

# Attempt to import and get casacore version
try:
    import casacore
    import casacore.tables
    casacore_version_str = casacore.__version__
except ImportError:
    casacore_version_str = "casacore not found"
except Exception as e:
    casacore_version_str = f"Error getting casacore version: {e}"


# Pipeline imports
from .pipeline_utils import get_logger 
from . import dsa110_utils 

# Get logger for this module
logger = get_logger(__name__)
logger.info(f"Phasing utilities will be used from: {PHASING_MODULE_SOURCE}")
if PHASING_MODULE_SOURCE == "NONE - IMPORT FAILED":
    logger.error("CRITICAL: Phasing utilities could not be imported. MS creation will likely fail.")


# --- Core uvh5 to MS Conversion Logic ---

def _load_uvh5_file(fnames: list, antenna_list: list = None, telescope_pos: EarthLocation = None):
    """Loads specific antennas from a list of uvh5 files and concatenates them."""
    if not fnames:
        logger.error("No filenames provided to _load_uvh5_file.")
        return None

    logger.info(f"Loading {len(fnames)} HDF5 files for one time chunk...")
    uvdata_obj = UVData() 

    user_requested_antenna_names = None
    if antenna_list is not None:
        valid_indices = dsa110_utils.valid_antennas_dsa110 
        valid_numbers = valid_indices + 1 
        antennas_to_request = [a for a in antenna_list if a in valid_numbers]
        if len(antennas_to_request) < len(antenna_list):
            logger.warning(f"Filtered antenna list to {len(antennas_to_request)} valid antennas.")
        if not antennas_to_request:
            logger.error("No valid antennas specified in the filtered list.")
            return None
        antenna_indices = [a - 1 for a in antennas_to_request]
        user_requested_antenna_names = dsa110_utils.ant_inds_to_names_dsa110(antenna_indices)
        logger.info(f"User requested antennas for selection: {list(user_requested_antenna_names) if user_requested_antenna_names is not None else 'all'}")

    try:
        logger.info(f"Attempting to read first file: {fnames[0]}")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
            warnings.filterwarnings("ignore", message=r".*Telescope .* is not in known_telescopes.*")
            uvdata_obj.read(fnames[0], file_type='uvh5', keep_all_metadata=True, run_check=False) 
        logger.debug(f"Successfully executed read command for {fnames[0]}")

        if hasattr(uvdata_obj, 'uvw_array') and uvdata_obj.uvw_array is not None:
            if uvdata_obj.uvw_array.dtype != np.float64:
                logger.debug(f"Original uvw_array dtype from {fnames[0]}: {uvdata_obj.uvw_array.dtype}. Converting to float64.")
                uvdata_obj.uvw_array = uvdata_obj.uvw_array.astype(np.float64)
        else:
            logger.warning(f"uvw_array not present or is None after reading {fnames[0]}.")

        logger.info(f"Running pyuvdata check on first file data ({fnames[0]})...")
        uvdata_obj.check(check_extra=True, run_check_acceptability=True)
        logger.info(f"pyuvdata check passed for first file data ({fnames[0]}).")
        
        if hasattr(uvdata_obj, 'telescope') and hasattr(uvdata_obj.telescope, 'antenna_names'):
            logger.debug(f"Telescope antenna names after first read: {uvdata_obj.telescope.antenna_names}")
        elif hasattr(uvdata_obj, 'antenna_names'): 
             logger.debug(f"Top-level antenna names after first read: {uvdata_obj.antenna_names}")
        else:
            logger.warning("antenna_names attribute still MISSING after first read and check!")

        if user_requested_antenna_names is not None:
            logger.info(f"Applying antenna selection: {list(user_requested_antenna_names)}")
            select_names = [str(name) for name in user_requested_antenna_names]
            uvdata_obj.select(antenna_names=select_names)
            logger.info("Antenna selection applied.")
            if hasattr(uvdata_obj, 'telescope') and hasattr(uvdata_obj.telescope, 'antenna_names'):
                 logger.debug(f"Telescope antenna names after selection: {uvdata_obj.telescope.antenna_names}")
            elif hasattr(uvdata_obj, 'antenna_names'):
                 logger.debug(f"Top-level antenna names after selection: {uvdata_obj.antenna_names}")
            else:
                logger.error("CRITICAL ERROR: antenna_names attribute MISSING after select() call!")
                return None
        
    except Exception as e:
        logger.error(f"Failed during initial read, uvw_conversion, check, or selection of HDF5 file {fnames[0]}: {e}", exc_info=True)
        return None

    if hasattr(uvdata_obj, 'uvw_array') and uvdata_obj.uvw_array is not None and uvdata_obj.uvw_array.dtype != np.float64:
        logger.warning("Re-converting main uvdata_obj.uvw_array to float64 as a safeguard.")
        uvdata_obj.uvw_array = uvdata_obj.uvw_array.astype(np.float64)

    prec_t = -2 * np.floor(np.log10(uvdata_obj._time_array.tols[-1])).astype(int)
    prec_b = 8 
    try:
        if uvdata_obj.time_array is None or uvdata_obj.baseline_array is None or len(uvdata_obj.time_array) == 0:
             raise ValueError("Time or baseline array is missing/empty in the first file after processing.")
        ref_blts = np.array([f"{blt[1]:.{prec_t}f}_{blt[0]:0{prec_b}d}" for blt in zip(uvdata_obj.baseline_array, uvdata_obj.time_array)])
        ref_freq = np.copy(uvdata_obj.freq_array)
    except Exception as e:
        logger.error(f"Error preparing baseline/time check arrays: {e}", exc_info=True)
        return None

    uvdata_to_append = []
    for f_idx, f in enumerate(fnames[1:]):
        uvdataf = UVData()
        try:
            logger.debug(f"Reading subsequent file {f_idx+1}: {f}")
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
                warnings.filterwarnings("ignore", message=r".*Telescope .* is not in known_telescopes.*")
                uvdataf.read(f, file_type='uvh5', keep_all_metadata=False, run_check=False)
            
            if hasattr(uvdataf, 'uvw_array') and uvdataf.uvw_array is not None:
                if uvdataf.uvw_array.dtype != np.float64:
                    logger.debug(f"Converting uvw_array for {f} to float64.")
                    uvdataf.uvw_array = uvdataf.uvw_array.astype(np.float64)
            else:
                logger.warning(f"uvw_array not present or is None after reading {f}.")

            if user_requested_antenna_names is not None:
                select_names_f = [str(name) for name in user_requested_antenna_names]
                uvdataf.select(antenna_names=select_names_f)
            
            logger.debug(f"Successfully read and processed subsequent file {f}")

            if uvdataf.time_array is None or uvdataf.baseline_array is None or len(uvdataf.time_array) == 0:
                raise ValueError(f"Time or baseline array is missing/empty in file {f}.")
            add_blts = np.array([f"{blt[1]:.{prec_t}f}_{blt[0]:0{prec_b}d}" for blt in zip(uvdataf.baseline_array, uvdataf.time_array)])
            if not np.array_equal(add_blts, ref_blts):
                logger.error(f"Baseline-time arrays do not match between {fnames[0]} and {f}. Skipping file.")
                continue 

            if len(np.intersect1d(ref_freq, uvdataf.freq_array)) > 0:
                logger.error(f"File {f} appears to have overlapping frequencies with previous files. Skipping.")
                continue 

            uvdata_to_append.append(uvdataf)
            ref_freq = np.concatenate((ref_freq, uvdataf.freq_array))

        except Exception as e:
            logger.error(f"Failed to read or process HDF5 file {f}: {e}", exc_info=True)
            return None 

    try:
        if uvdata_to_append:
            logger.info(f"Concatenating {len(uvdata_to_append)} additional frequency chunks.")
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
                uvdata_obj.fast_concat(uvdata_to_append, axis='freq', inplace=True, run_check=False, check_extra=False, run_check_acceptability=False, strict_uvw_antpos_check=True)
            logger.info("Concatenation complete. Running pyuvdata check...")
            try:
                uvdata_obj.check(check_extra=True, run_check_acceptability=True)
                logger.info("pyuvdata check passed after concatenation.")
            except Exception as e_check:
                logger.error(f"pyuvdata check FAILED after concatenation: {e_check}", exc_info=True)
                return None 
    except Exception as e:
        logger.error(f"Failed during frequency concatenation: {e}", exc_info=True)
        return None

    try:
        uvdata_obj.reorder_freqs(channel_order='freq', run_check=False)
    except Exception as e:
        logger.error(f"Failed to reorder frequencies: {e}", exc_info=True)
        return None

    if telescope_pos is not None:
        uvdata_obj.telescope_name = telescope_pos.info.name
        uvdata_obj.telescope.location = EarthLocation.from_geocentric(
           telescope_pos.itrs.x,
           telescope_pos.itrs.y,
           telescope_pos.itrs.z
           )
    else:
        uvdata_obj.telescope_name = dsa110_utils.loc_dsa110.info.name
        uvdata_obj.telescope.location = EarthLocation.from_geocentric(
           dsa110_utils.loc_dsa110.itrs.x,
           dsa110_utils.loc_dsa110.itrs.y,
           dsa110_utils.loc_dsa110.itrs.z
           )

        logger.warning("Using default DSA-110 location.")

    if hasattr(uvdata_obj, 'telescope') and hasattr(uvdata_obj.telescope, 'antenna_names'):
        logger.debug(f"Final telescope antenna names in _load_uvh5_file: {uvdata_obj.telescope.antenna_names}")
    elif hasattr(uvdata_obj, 'antenna_names'):
        logger.debug(f"Final top-level antenna names in _load_uvh5_file: {uvdata_obj.antenna_names}")
    else:
        logger.error("CRITICAL ERROR: antenna_names attribute MISSING (both top-level and telescope.antenna_names) before returning from _load_uvh5_file!")
    
    if hasattr(uvdata_obj, 'antenna_numbers'):
        logger.debug(f"Final antenna numbers (0-indexed internal IDs): {uvdata_obj.antenna_numbers}")

    logger.info(f"Finished loading data. Nbls: {uvdata_obj.Nbls}, Ntimes: {uvdata_obj.Ntimes}, Nfreqs: {uvdata_obj.Nfreqs}, Nants: {uvdata_obj.Nants_data}")
    return uvdata_obj


def _compute_pointing_per_visibility(uvdata_obj: UVData, telescope_pos: EarthLocation):
    """
    Determine where the telescope was pointed in RA/Dec for each visibility.
    """
    try:
        fixed_dec_rad = uvdata_obj.extra_keywords['phase_center_dec']
        pt_dec = fixed_dec_rad * u.rad 
        logger.debug(f"Using fixed declination from HDF5 header: {pt_dec.to_string(unit=u.deg)}")

        unique_jd_times, unique_indices = np.unique(uvdata_obj.time_array, return_inverse=True)
        astropy_unique_times = Time(unique_jd_times, format='jd', scale='utc')

        lst_unique = astropy_unique_times.sidereal_time('apparent', longitude=telescope_pos.lon)
        lst_array_rad = lst_unique.rad[unique_indices] 
        
        pointing_coords = SkyCoord(ra=lst_array_rad*u.rad, dec=pt_dec, frame='icrs')
        
        if len(pointing_coords) != uvdata_obj.Nblts:
            logger.error(f"Dimension mismatch in pointing_coords: len {len(pointing_coords)} vs Nblts {uvdata_obj.Nblts}.")
            return None
            
        logger.debug(f"Computed pointing coordinates for {len(pointing_coords)} visibilities.")
        return pointing_coords

    except KeyError:
        logger.error("HDF5 file missing 'phase_center_dec' in extra_keywords!")
        return None
    except Exception as e:
        logger.error(f"Error computing pointing coordinates: {e}", exc_info=True)
        return None


def _set_phase_centers(uvdata_obj: UVData, field_name_base: str, telescope_pos: EarthLocation):
    """
    Set phase centers and recalculate UVW coordinates for a drift scan,
    mimicking the colleague's manual UVW calculation approach.
    """
    logger.info("Setting phase centers and recalculating UVWs manually for drift scan.")
    logger.info(f"_set_phase_centers - PyUVData version: {pyuvdata.__version__}, Path: {pyuvdata.__file__}")

    # --- Start Diagnostics for telescope.location ---
    logger.debug(f"Type of uvdata_obj entering _set_phase_centers: {type(uvdata_obj)}")

    # Define telescope attribute for clarity
    tel = uvdata_obj.telescope

    if hasattr(tel, 'location'):
        logger.debug(f"uvdata_obj.telescope.location (XYZ) value: {tel.location}")
        logger.debug(f"uvdata_obj.telescope.location type: {type(tel.location)}")
        if tel.location is None:
            logger.error("CRITICAL: uvdata_obj.telescope.location is None at start of _set_phase_centers!")
    else:
        logger.error("CRITICAL: uvdata_obj has NO telescope.location attribute at start of _set_phase_centers!")
        return None 
    
    effective_telescope_loc_lat_lon_alt = None
    if hasattr(tel, 'location_lat_lon_alt') and tel.location_lat_lon_alt is not None:
        logger.debug(f"uvdata_obj.telescope.location_lat_lon_alt exists. Value: {tel.location_lat_lon_alt}")
        effective_telescope_loc_lat_lon_alt = tel.location_lat_lon_alt
    else:
        logger.warning("uvdata_obj.telescope.location_lat_lon_alt is missing or None.")
        if tel.location is not None:
            try:
                logger.warning("Attempting to manually derive lat/lon/alt from telescope.location (XYZ).")
                el = tel.location
                manual_lat_lon_alt = (el.lat.rad, el.lon.rad, el.height.to_value(u.m))
                logger.info(f"Manually derived lat/lon/alt: {manual_lat_lon_alt}")
                effective_telescope_loc_lat_lon_alt = manual_lat_lon_alt
            except Exception as e_manual_conv:
                logger.error(f"Failed to manually derive lat/lon/alt: {e_manual_conv}", exc_info=True)
                return None
        else:
            logger.error("Cannot derive lat/lon/alt because telescope.location (XYZ) is also None.")
            return None
            
    if effective_telescope_loc_lat_lon_alt is None:
        logger.error("Could not obtain effective telescope lat/lon/alt. Aborting phase setting.")
        return None

    if not (hasattr(uvdata_obj, 'antenna_names') or \
            (hasattr(uvdata_obj, 'telescope') and hasattr(tel, 'antenna_names'))):
        logger.error("CRITICAL: UVData object passed to _set_phase_centers is missing 'antenna_names'. Aborting phase setting.")
        return None 
    # --- End Diagnostics ---


    if telescope_pos is None: 
        telescope_pos = dsa110_utils.loc_dsa110 
        logger.warning("Using default DSA-110 location for LST calculation in _set_phase_centers.")

    try:
        vis_coords = _compute_pointing_per_visibility(uvdata_obj, telescope_pos)
        if vis_coords is None:
            raise ValueError("Failed to compute per-visibility pointing coordinates.")
        
        unique_jd_times, unique_time_indices, blt_to_unique_time_map = np.unique(
            uvdata_obj.time_array, return_index=True, return_inverse=True
        )
        unique_pointing_skycoords = vis_coords[unique_time_indices]
        
        logger.info(f"Found {len(unique_pointing_skycoords)} unique pointing centers for catalog.")

        uvdata_obj.phase_center_catalog = {} 
        new_phase_center_ids = np.zeros(uvdata_obj.Nblts, dtype=int) 
        
        if uvdata_obj.lst_array is None or \
           (isinstance(uvdata_obj.lst_array, np.ndarray) and uvdata_obj.lst_array.size == 0):
             logger.info("LST array not set or empty, calculating from time_array.")
             uvdata_obj.set_lsts_from_time_array()
        
        common_epoch = Time(2000.0, format="jyear") # Astropy Time object for epoch

        for i, center_coord in enumerate(unique_pointing_skycoords):
            cat_name_str = f"{field_name_base}_T{i:04d}_RA{center_coord.ra.deg:.3f}"
            cat_id = uvdata_obj._add_phase_center(
                cat_name=cat_name_str,
                cat_type='sidereal',
                cat_lon=center_coord.ra.rad,  
                cat_lat=center_coord.dec.rad, 
                cat_frame='icrs',
                cat_epoch=common_epoch, 
                info_source='calculated'
            )
            logger.debug(f"Added phase center ID {cat_id}: {cat_name_str}")
            
            selection_mask_for_this_center = (blt_to_unique_time_map == i)
            new_phase_center_ids[selection_mask_for_this_center] = cat_id
            
            # Corrected call to calc_app_coords based on pyuvdata 3.2.1 signature
            # (lon_coord, lat_coord are keyword-only)
            app_ra, app_dec = calc_app_coords(
                lon_coord=center_coord.ra.rad,
                lat_coord=center_coord.dec.rad,
                coord_frame='icrs', 
                coord_epoch=common_epoch.jyear, # Pass float JYear
                time_array=Time(uvdata_obj.time_array[selection_mask_for_this_center], format='jd', scale='utc'),
                lst_array=uvdata_obj.lst_array[selection_mask_for_this_center],
                telescope_loc=effective_telescope_loc_lat_lon_alt, 
                telescope_frame='itrs' 
            )
            
            # Corrected call to calc_frame_pos_angle (ref_frame instead of phase_frame)
            frame_pa = calc_frame_pos_angle(
                time_array=uvdata_obj.time_array[selection_mask_for_this_center], 
                app_ra=app_ra,
                app_dec=app_dec,
                telescope_loc=effective_telescope_loc_lat_lon_alt, 
                telescope_frame='itrs', 
                ref_frame='icrs', # Corrected from phase_frame
                ref_epoch=common_epoch.jyear 
            )
            
            uvw_new = calc_uvw(
                app_ra=app_ra,
                app_dec=app_dec,
                frame_pa=frame_pa,
                lst_array=uvdata_obj.lst_array[selection_mask_for_this_center],
                use_ant_pos=True, 
                antenna_positions=uvdata_obj.telescope.antenna_positions,
                antenna_numbers=uvdata_obj.telescope.antenna_numbers, 
                ant_1_array=uvdata_obj.ant_1_array[selection_mask_for_this_center],
                ant_2_array=uvdata_obj.ant_2_array[selection_mask_for_this_center],
                telescope_lat=effective_telescope_loc_lat_lon_alt[0], 
                telescope_lon=effective_telescope_loc_lat_lon_alt[1]  
            )
            
            uvdata_obj.uvw_array[selection_mask_for_this_center, :] = uvw_new
            uvdata_obj.phase_center_app_ra[selection_mask_for_this_center] = app_ra
            uvdata_obj.phase_center_app_dec[selection_mask_for_this_center] = app_dec
            uvdata_obj.phase_center_frame_pa[selection_mask_for_this_center] = frame_pa
            
        uvdata_obj.phase_center_id_array = new_phase_center_ids
        uvdata_obj._clear_unused_phase_centers() 

        logger.info(f"Manually re-phased and updated UVWs for {len(unique_pointing_skycoords)} unique pointing centers.")
        return uvdata_obj

    except Exception as e:
        logger.error(f"Failed to set phase centers using manual UVW calculation: {e}", exc_info=True)
        return None


def _make_calib_model(uvdata_obj: UVData, config: dict, telescope_pos: EarthLocation):
    calib_info = config.get('ms_creation', {}).get('calibrator_model', None)
    if calib_info is None:
        logger.info("No calibrator model requested in config.")
        return None
    logger.info("Generating calibrator model...")
    sources = calib_info.get('sources', [])
    if not sources:
        logger.warning("`calibrator_model` specified in config, but no `sources` listed.")
        return None
    uvmodel = uvdata_obj.copy()
    uvmodel.data_array = np.zeros_like(uvmodel.data_array, dtype=complex) 
    beam_func_name = calib_info.get('beam_function', 'gaussian')
    beam_diameter = calib_info.get('beam_diameter_m', dsa110_utils.diam_dsa110)
    if telescope_pos is None:
        telescope_pos = dsa110_utils.loc_dsa110 
    try:
        unique_times_model, uind_model = np.unique(uvmodel.time_array, return_inverse=True)
        astropy_times_model = Time(unique_times_model, format='jd')
        fixed_dec_val_model = uvmodel.extra_keywords['phase_center_dec']
        fixed_dec_rad_quantity_model = fixed_dec_val_model * u.rad
        lsts_model = astropy_times_model.sidereal_time('apparent', longitude=telescope_pos.lon)
        drift_pointing_coords_unique = SkyCoord(ra=lsts_model, dec=fixed_dec_rad_quantity_model, frame='icrs')
        drift_pointing_coords_all = drift_pointing_coords_unique[uind_model]
        logger.debug(f"Calculated {len(drift_pointing_coords_unique)} unique drift pointing coords for model generation.")
    except Exception as e:
        logger.error(f"Failed to get drift pointing coords for model generation: {e}", exc_info=True)
        return None
    for i, src_params in enumerate(sources):
        try:
            src_name = src_params.get('name', f'Calib{i}')
            src_epoch_str = src_params.get('epoch', 'J2000')
            src_epoch_time = Time(float(src_epoch_str), format='jyear') if src_epoch_str != 'J2000' and src_epoch_str is not None else Time("J2000")
            src_coord = SkyCoord(ra=src_params['ra'], dec=src_params['dec'], frame='icrs', epoch=src_epoch_time)
            flux_jy = float(src_params['flux_jy'])
            ref_freq_ghz = float(src_params.get('ref_freq_ghz', 1.4))
            spectral_index = src_params.get('spectral_index', None)
            logger.info(f"Adding source {src_name} ({src_coord.to_string('hmsdms')}) to model.")
            freq_array_ghz = uvmodel.freq_array.flatten() / 1e9
            if spectral_index is not None:
                freq_scale = (freq_array_ghz / ref_freq_ghz)**float(spectral_index)
            else:
                freq_scale = np.ones_like(freq_array_ghz)
            model_flux_vs_freq = flux_jy * freq_scale 
            separations = drift_pointing_coords_all.separation(src_coord) 
            if beam_func_name == 'gaussian':
                beam_func = dsa110_utils.pb_dsa110
            elif beam_func_name == 'none':
                beam_func = None
                logger.warning("Beam function set to 'none', applying no attenuation.")
            else:
                logger.warning(f"Unknown beam_function '{beam_func_name}', defaulting to Gaussian.")
                beam_func = dsa110_utils.pb_dsa110
            beam_attenuation_values = np.ones((uvmodel.Nblts, uvmodel.Nfreqs)) 
            if beam_func is not None:
                beam_resp_raw = beam_func(separations.rad, freq_array_ghz, diameter=beam_diameter)
                beam_attenuation_values = np.squeeze(beam_resp_raw) 
                if beam_attenuation_values.shape != (uvmodel.Nblts, uvmodel.Nfreqs):
                    logger.error(f"Unexpected beam attenuation dimension: {beam_attenuation_values.shape}, expected ({uvmodel.Nblts}, {uvmodel.Nfreqs})")
                    beam_attenuation_values = np.ones((uvmodel.Nblts, uvmodel.Nfreqs))
            src_amplitude_vis_blt_freq = beam_attenuation_values * model_flux_vs_freq[np.newaxis, :]
            src_amplitude_vis_reshaped = src_amplitude_vis_blt_freq.reshape(uvmodel.Nblts, 1, uvmodel.Nfreqs, 1)
            uv_temp_for_phase = uvmodel.copy()
            uv_temp_for_phase.data_array = np.ones_like(uv_temp_for_phase.data_array, dtype=complex)
            uv_temp_for_phase.phase(src_coord.ra.rad, src_coord.dec.rad,
                                    epoch=src_epoch_time, 
                                    phase_frame='icrs',
                                    cat_name=f"temp_src_phaser_{i}") 
            phase_factors = uv_temp_for_phase.data_array 
            phased_src_vis = src_amplitude_vis_reshaped * phase_factors
            uvmodel.data_array += phased_src_vis
            logger.debug(f"Visibilities for source {src_name} added to uvmodel.")
        except KeyError as e:
            logger.error(f"Missing required key for source {i} in calibrator_model config: {e}")
            continue
        except Exception as e:
            logger.error(f"Failed to process source {i} ({src_name}) for model: {e}", exc_info=True)
            continue
    logger.info("Successfully generated calibrator model object (uvmodel).")
    return uvmodel

def _write_ms(uvdata_obj: UVData, uvcalib: UVData, ms_outfile_base: str, protect_files: bool): 
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
        logger.info("Running final pyuvdata check on uvdata_obj before writing MS...")
        uvdata_obj.check(check_extra=True, run_check_acceptability=True)
        logger.info("Final pyuvdata check passed for uvdata_obj.")
        if uvcalib is not None:
            logger.info("Running final pyuvdata check on uvcalib (model) object before writing MS...")
            uvcalib.check(check_extra=True, run_check_acceptability=True) 
            logger.info("Final pyuvdata check passed for uvcalib (model) object.")
    except Exception as e_final_check:
        logger.error(f"Final pyuvdata check FAILED before MS write: {e_final_check}", exc_info=True)
        return None 

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r".*Writing in the MS file that the units of the data are uncalib.*")
            uvdata_obj.write_ms(ms_outfile,
                            run_check=False, 
                            force_phase=False, 
                            run_check_acceptability=False, 
                            strict_uvw_antpos_check=False) 

        if uvcalib is not None: 
            logger.info("Adding MODEL_DATA and CORRECTED_DATA columns.")
            try:
                tables.addImagingColumns(ms_outfile)
                with tables.table(ms_outfile, readonly=False, ack=False) as tb:
                    model_data_to_write = np.squeeze(uvcalib.data_array, axis=1)
                    corrected_data_to_write = np.squeeze(uvdata_obj.data_array, axis=1)
                    if tb.ncols() == 0: 
                         raise RuntimeError("MS table appears empty after write_ms.")
                    tb.putcol('MODEL_DATA', model_data_to_write)
                    tb.putcol('CORRECTED_DATA', corrected_data_to_write)
                logger.info("MODEL_DATA and CORRECTED_DATA columns added.")
            except Exception as e:
                logger.error(f"Failed to add imaging columns or write model/corrected data: {e}", exc_info=True)

        logger.info(f"Successfully wrote MS: {ms_outfile}")
        return ms_outfile
    except Exception as e:
        logger.error(f"Failed to write MS file {ms_outfile}: {e}", exc_info=True)
        if os.path.exists(ms_outfile):
            try:
                shutil.rmtree(ms_outfile)
                logger.info(f"Removed incomplete MS file: {ms_outfile}")
            except Exception as e_clean:
                logger.error(f"Failed to remove incomplete MS file {ms_outfile}: {e_clean}")
        return None

def find_hdf5_sets(config: dict):
    incoming_path = config['paths']['hdf5_incoming']
    expected_subbands = config['services']['hdf5_expected_subbands']
    spws_to_include = config['ms_creation'].get('spws', [f'sb{i:02d}' for i in range(expected_subbands)])
    logger.info(f"Searching for HDF5 file sets in: {incoming_path}")
    logger.debug(f"Expecting {expected_subbands} subbands per set. Including SPWs: {spws_to_include}")
    if not os.path.isdir(incoming_path):
        logger.error(f"Incoming HDF5 directory not found: {incoming_path}")
        return {}
    try:
        all_files = [f for f in os.listdir(incoming_path) if fnmatch(f, '20*T*.hdf5')]
        parsed_files = {}
        filename_time_format = "%Y-%m-%dT%H:%M:%S" 
        for f in all_files:
            try:
                parts = f.split('_')
                timestamp_str_from_file = parts[0]
                Time(datetime.strptime(timestamp_str_from_file, filename_time_format)) 
                spw_str = parts[1].replace('.hdf5', '') 
                base_spw = spw_str
                if base_spw not in spws_to_include:
                    continue
                if timestamp_str_from_file not in parsed_files: 
                    parsed_files[timestamp_str_from_file] = {}
                parsed_files[timestamp_str_from_file][base_spw] = os.path.join(incoming_path, f)
            except ValueError: 
                logger.warning(f"Filename {f} has unexpected timestamp format. Skipping.")
                continue
            except Exception as e:
                logger.warning(f"Could not parse filename {f}: {e}")
                continue
        complete_sets = {}
        required_spw_set = set(spws_to_include)
        for timestamp_key, files_dict_for_ts in parsed_files.items():
            present_spw_set = set(files_dict_for_ts.keys())
            if present_spw_set == required_spw_set:
                sorted_filenames = [files_dict_for_ts[spw] for spw in sorted(list(required_spw_set))]
                dt_obj = datetime.strptime(timestamp_key, filename_time_format)
                compact_timestamp_key = dt_obj.strftime("%Y%m%dT%H%M%S")
                complete_sets[compact_timestamp_key] = sorted_filenames
                logger.debug(f"Found complete set for nominal timestamp {timestamp_key} (key: {compact_timestamp_key}) with {len(sorted_filenames)} files.")
        logger.info(f"Found {len(complete_sets)} complete HDF5 sets.")
        return complete_sets 
    except Exception as e:
        logger.error(f"Error finding HDF5 sets: {e}", exc_info=True)
        return {}

def process_hdf5_set(config: dict, timestamp: str, hdf5_files: list):
    """Processes a single complete set of HDF5 files into an MS file."""
    logger.info(f"MS_CREATION - PyUVData version: {pyuvdata.__version__}, Path: {pyuvdata.__file__}, Casacore version: {casacore_version_str}")
    
    logger.info(f"Processing HDF5 set for timestamp: {timestamp}") 
    paths_config = config['paths']
    ms_creation_config = config['ms_creation']
    output_ms_dir = paths_config['ms_stage1_dir'] 
    os.makedirs(output_ms_dir, exist_ok=True)
    output_ms_base = os.path.join(output_ms_dir, f"drift_{timestamp}")
 
    antenna_list = ms_creation_config.get('output_antennas', None) 
    uvdata_obj = _load_uvh5_file(hdf5_files, antenna_list=antenna_list, telescope_pos=dsa110_utils.loc_dsa110)
    if uvdata_obj is None:
        logger.error(f"Failed to load HDF5 data for {timestamp}. Skipping.")
        return None 

    field_name_base = "drift"
    uvdata_obj = _set_phase_centers(uvdata_obj, field_name_base, dsa110_utils.loc_dsa110)
    if uvdata_obj is None:
        logger.error(f"Failed to set phase centers for {timestamp}. Skipping.")
        return None

    uvmodel_for_ms = _make_calib_model(uvdata_obj, config, dsa110_utils.loc_dsa110) 
    protect_files = False 
    
    ms_output_path = _write_ms(uvdata_obj, uvmodel_for_ms, output_ms_base, protect_files) 

    if ms_output_path: 
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
    return ms_output_path
