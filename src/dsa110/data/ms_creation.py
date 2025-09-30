# pipeline/ms_creation.py - Updated for PyUVData 3.2.1

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

# Pipeline imports
from .pipeline_utils import get_logger 
from . import dsa110_utils 

# Get logger for this module
logger = get_logger(__name__)

# PyUVData imports - Updated for 3.x
import pyuvdata 
from pyuvdata import UVData
from pyuvdata import utils as uvutils
from pyuvdata.uvdata.ms import tables

# Updated imports for PyUVData 3.x
try:
    from pyuvdata.utils.phasing import calc_app_coords, calc_frame_pos_angle, calc_uvw
    PHASING_MODULE_SOURCE = "pyuvdata.utils.phasing"
    logger.info("Successfully imported phasing utilities from pyuvdata.utils.phasing")
except ImportError:
    #try:
    #    # Fallback for different 3.x versions
    #    from pyuvdata.coordinates import calc_app_coords, calc_frame_pos_angle, calc_uvw
    #    PHASING_MODULE_SOURCE = "pyuvdata.coordinates"
    #    logger.info("Imported phasing utilities from pyuvdata.coordinates")
    #except ImportError as e:
    logger.error(f"CRITICAL ERROR: Could not import phasing utilities: {e}")
    print(f"CRITICAL ERROR: Could not import phasing utilities: {e}")
    calc_app_coords, calc_frame_pos_angle, calc_uvw = None, None, None
    PHASING_MODULE_SOURCE = "NONE - IMPORT FAILED"

from importlib.resources import files as importlib_files 
import inspect 

# --- Core uvh5 to MS Conversion Logic ---
def _load_uvh5_file(fnames: list, antenna_list: list = None, telescope_pos: EarthLocation = None):
    """
    Loads specific antennas from a list of uvh5 files and concatenates them.
    Updated for PyUVData 3.2.1 with proper telescope object handling.
    """
    if not fnames:
        logger.error("No filenames provided to _load_uvh5_file.")
        return None

    logger.info(f"Loading {len(fnames)} HDF5 files for one time chunk...")
    print(f"Loading {len(fnames)} HDF5 files for one time chunk...")
    uvdata_obj = UVData() 

    # Step 1: Determine antennas that actually have data in ALL files
    logger.info("Step 1: Determining antennas with actual data in ALL files...")
    all_file_active_antennas = []
    
    for fname in fnames:
        try:
            temp_uvd = UVData()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
                warnings.filterwarnings("ignore", message=r".*Telescope .* is not in known_telescopes.*")
                warnings.filterwarnings("ignore", message=r".*uvw_array does not match.*")
                temp_uvd.read(fname, file_type='uvh5', run_check=False)
            
            print(temp_uvd.ant_1_array)
            print(temp_uvd.ant_2_array)

            active_antenna_numbers = np.unique(np.concatenate([temp_uvd.ant_1_array, temp_uvd.ant_2_array]))
            
            # Updated for PyUVData 3.x: telescope object
            if hasattr(temp_uvd, 'telescope') and hasattr(temp_uvd.telescope, 'antenna_names'):
                ant_num_to_name = {}
                for i, (num, name) in enumerate(zip(temp_uvd.telescope.antenna_numbers, temp_uvd.telescope.antenna_names)):
                    ant_num_to_name[num] = name
                
                active_antenna_names = []
                for ant_num in active_antenna_numbers:
                    if ant_num in ant_num_to_name:
                        name = ant_num_to_name[ant_num]
                        if name.isdigit():
                            name = f"pad{name}"
                        active_antenna_names.append(name)
                
                file_active_antennas = set(active_antenna_names)
                all_file_active_antennas.append(file_active_antennas)
                logger.debug(f"File {os.path.basename(fname)}: {len(file_active_antennas)} antennas with data")
                print(f"File {os.path.basename(fname)}: {len(file_active_antennas)} antennas with data")    
            else:
                logger.error(f"Missing telescope/antenna metadata in {fname}")
                print(f"Missing telescope/antenna metadata in {fname}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to read antenna data from {fname}: {e}")
            print(f"Failed to read antenna data from {fname}: {e}")
            return None
    
    if all_file_active_antennas:
        common_active_antennas = set.intersection(*all_file_active_antennas)
        logger.info(f"Found {len(common_active_antennas)} antennas with data in all {len(fnames)} files")
        print(f"Found {len(common_active_antennas)} antennas with data in all {len(fnames)} files") 

        if len(common_active_antennas) == 0:
            logger.error("No antennas have data in all frequency files!")
            print("No antennas have data in all frequency files!")
            return None
    else:
        logger.error("Failed to determine active antennas from any files")
        print("Failed to determine active antennas from any files")
        return None

    # Step 2: Apply user antenna selection
    if antenna_list is not None:
        valid_indices = dsa110_utils.valid_antennas_dsa110 
        valid_numbers = valid_indices + 1
        antennas_to_request = [a for a in antenna_list if a in valid_numbers]
        
        if len(antennas_to_request) < len(antenna_list):
            logger.warning(f"Filtered antenna list to {len(antennas_to_request)} valid antennas.")
            print(f"Filtered antenna list to {len(antennas_to_request)} valid antennas.")
        if not antennas_to_request:
            logger.error("No valid antennas specified in the filtered list.")
            print("No valid antennas specified in the filtered list.")
            return None
            
        requested_antenna_names = set([f"pad{a}" for a in antennas_to_request])
        final_antenna_names = list(common_active_antennas.intersection(requested_antenna_names))
        
        excluded_by_availability = requested_antenna_names - common_active_antennas
        if excluded_by_availability:
            logger.warning(f"Requested antennas without data in all files: {sorted(list(excluded_by_availability))}")
            print(f"Requested antennas without data in all files: {sorted(list(excluded_by_availability))}")

        if not final_antenna_names:
            logger.error("No requested antennas have data in all frequency files!")
            print("No requested antennas have data in all frequency files!")
            return None
            
        logger.info(f"Will select {len(final_antenna_names)} antennas: {sorted(final_antenna_names)[:10]}...")
        print(f"Will select {len(final_antenna_names)} antennas: {sorted(final_antenna_names)[:10]}...")
    else:
        final_antenna_names = list(common_active_antennas)
        logger.info(f"Will use all {len(final_antenna_names)} antennas with data")
        print(f"Will use all {len(final_antenna_names)} antennas with data")

    # Step 3: Read and process first file with comprehensive fixes
    try:
        logger.info(f"Step 3: Reading first file: {fnames[0]}")
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
            warnings.filterwarnings("ignore", message=r".*Telescope .* is not in known_telescopes.*")
            warnings.filterwarnings("ignore", message=r".*uvw_array does not match.*")
            uvdata_obj.read(
                fnames[0], 
                file_type='uvh5', 
                antenna_names=None,
                keep_all_metadata=True, 
                run_check=False
            ) 

        # CRITICAL FIX 1: Standardize telescope name IMMEDIATELY
        standard_telescope_name = "DSA-110"
        original_name = getattr(uvdata_obj.telescope, 'name', 'UNKNOWN')
        uvdata_obj.telescope.name = standard_telescope_name
        logger.info(f"Standardized telescope name: '{original_name}' -> '{standard_telescope_name}'")
        print(f"Standardized telescope name: '{original_name}' -> '{standard_telescope_name}'")

        # CRITICAL FIX 2: Set correct telescope location
        if telescope_pos is not None:
            try:
                # For PyUVData 3.x, use EarthLocation directly
                uvdata_obj.telescope.location = telescope_pos
            except:
                # Fallback if direct assignment doesn't work
                uvdata_obj.telescope.location = EarthLocation.from_geocentric(
                    telescope_pos.itrs.x, telescope_pos.itrs.y, telescope_pos.itrs.z
                )
        else:
            # Use DSA-110 default
            uvdata_obj.telescope.location = dsa110_utils.loc_dsa110

        # Check current telescope location
        if hasattr(uvdata_obj.telescope, 'location') and uvdata_obj.telescope.location is not None:
            current_loc = uvdata_obj.telescope.location
            logger.info(f"Telescope location set: {current_loc}")
            print(f"Telescope location set: {current_loc}")
        
        # CRITICAL FIX 3: Fix antenna positions coordinate system
        if hasattr(uvdata_obj.telescope, 'antenna_positions') and uvdata_obj.telescope.antenna_positions is not None:
            max_ant_dist = np.sqrt(np.sum(uvdata_obj.telescope.antenna_positions**2, axis=1)).max()
            logger.info(f"Max antenna distance from center: {max_ant_dist:.1f} m")
            print(f"Max antenna distance from center: {max_ant_dist:.1f} m")
            
            # Check if positions are in absolute ECEF coordinates
            if max_ant_dist > 1e6:  # > 1000 km suggests absolute coordinates
                logger.warning("🚨 FIXING: Antenna positions are in absolute ECEF coordinates!")
                print("🚨 FIXING: Antenna positions are in absolute ECEF coordinates!")
                # Get telescope location in ITRS XYZ
                tel_xyz = np.array([
                    uvdata_obj.telescope.location.itrs.x.value,
                    uvdata_obj.telescope.location.itrs.y.value,
                    uvdata_obj.telescope.location.itrs.z.value
                ])
                uvdata_obj.telescope.antenna_positions = uvdata_obj.telescope.antenna_positions - tel_xyz
                new_max_dist = np.sqrt(np.sum(uvdata_obj.telescope.antenna_positions**2, axis=1)).max()
                logger.info(f"✅ After fix: max antenna distance = {new_max_dist:.1f} m")
                print(f"✅ After fix: max antenna distance = {new_max_dist:.1f} m") 

            # Final check on antenna positions
            final_max_dist = np.sqrt(np.sum(uvdata_obj.telescope.antenna_positions**2, axis=1)).max()
            if final_max_dist > 50000:  # Still > 50 km
                logger.error(f"Antenna positions still problematic after fix: {final_max_dist:.1f} m")
                print(f"Antenna positions still problematic after fix: {final_max_dist:.1f} m")
                return None

        # CRITICAL FIX 4: Fix antenna naming consistency
        if hasattr(uvdata_obj.telescope, 'antenna_names') and all(name.isdigit() for name in uvdata_obj.telescope.antenna_names):
            uvdata_obj.telescope.antenna_names = np.array([f"pad{name}" for name in uvdata_obj.telescope.antenna_names])
            logger.info("Fixed antenna naming to pad### format")
            print("Fixed antenna naming to pad### format")

        # Convert UVW array to float64
        if hasattr(uvdata_obj, 'uvw_array') and uvdata_obj.uvw_array is not None:
            if uvdata_obj.uvw_array.dtype != np.float64:
                uvdata_obj.uvw_array = uvdata_obj.uvw_array.astype(np.float64)

        # Apply antenna selection
        logger.info(f"Selecting antennas: {sorted(final_antenna_names)}")
        print(f"Selecting antennas: {sorted(final_antenna_names)}")
        uvdata_obj.select(antenna_names=final_antenna_names)
        logger.info(f"Selected {uvdata_obj.Nants_data} antennas from first file")
        print(f"Selected {uvdata_obj.Nants_data} antennas from first file")

        # Run check with automatic conjugation fix
        logger.info("Running uvdata check with automatic conjugation correction...")
        print("Running uvdata check with automatic conjugation correction...")
        try:
            uvdata_obj.check(check_extra=False, run_check_acceptability=False, allow_flip_conj=True)
            logger.info("✅ UVData check passed (with automatic conjugation correction if needed)")
            print("✅ UVData check passed (with automatic conjugation correction if needed)")
        except Exception as e_check:
            logger.warning(f"⚠️  UVData check failed: {e_check}")
            print(f"⚠️  UVData check failed: {e_check}")
            logger.info("Continuing anyway...")
            print("Continuing anyway...")
        
    except Exception as e:
        logger.error(f"Failed processing first file {fnames[0]}: {e}", exc_info=True)
        print(f"Failed processing first file {fnames[0]}: {e}")
        return None
    
    # Prepare for concatenation
    prec_t = -2 * np.floor(np.log10(uvdata_obj._time_array.tols[-1])).astype(int)
    prec_b = 8 
    try:
        ref_blts = np.array([f"{blt[1]:.{prec_t}f}_{blt[0]:0{prec_b}d}" for blt in zip(uvdata_obj.baseline_array, uvdata_obj.time_array)])
        ref_freq = np.copy(uvdata_obj.freq_array)
    except Exception as e:
        logger.error(f"Error preparing reference arrays: {e}", exc_info=True)
        print(f"Error preparing reference arrays: {e}")
        return None

    # Process remaining files
    uvdata_to_append = []
    for f_idx, f in enumerate(fnames[1:]):
        uvdataf = UVData()
        try:
            logger.debug(f"Reading subsequent file {f_idx+1}: {f}")
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
                warnings.filterwarnings("ignore", message=r".*Telescope .* is not in known_telescopes.*")
                warnings.filterwarnings("ignore", message=r".*uvw_array does not match.*")
                uvdataf.read(f, file_type='uvh5', antenna_names=None, keep_all_metadata=False, run_check=False) 

            # APPLY SAME FIXES TO EACH FILE
            uvdataf.telescope.name = standard_telescope_name
            uvdataf.telescope.location = uvdata_obj.telescope.location  # Use same location

            # Fix antenna positions if needed
            if hasattr(uvdataf.telescope, 'antenna_positions') and uvdataf.telescope.antenna_positions is not None:
                max_dist_check = np.sqrt(np.sum(uvdataf.telescope.antenna_positions**2, axis=1)).max()
                if max_dist_check > 1e6:  # Fix absolute coordinates
                    tel_xyz = np.array([
                        uvdataf.telescope.location.itrs.x.value,
                        uvdataf.telescope.location.itrs.y.value,
                        uvdataf.telescope.location.itrs.z.value
                    ])
                    uvdataf.telescope.antenna_positions = uvdataf.telescope.antenna_positions - tel_xyz

            # Fix antenna naming
            if hasattr(uvdataf.telescope, 'antenna_names') and all(name.isdigit() for name in uvdataf.telescope.antenna_names):
                uvdataf.telescope.antenna_names = np.array([f"pad{name}" for name in uvdataf.telescope.antenna_names])

            if hasattr(uvdataf, 'uvw_array') and uvdataf.uvw_array is not None:
                uvdataf.uvw_array = uvdataf.uvw_array.astype(np.float64)

            uvdataf.select(antenna_names=final_antenna_names)

            # Check baseline-time consistency
            #add_blts = np.array([f"{blt[1]:.{prec_t}f}_{blt[0]:0{prec_b}d}" for blt in zip(uvdataf.baseline_array, uvdataf.time_array)])
            add_blts = np.array(["{1:.{0}f}_".format(prec_t, blt[0])+str(blt[1]).zfill(prec_b) for blt in zip(uvdataf.time_array, uvdataf.baseline_array)])
            if not np.array_equal(add_blts, ref_blts):
                logger.error(f"Baseline-time arrays do not match. Skipping {f}")
                print(f"Baseline-time arrays do not match. Skipping {f}")
                continue 

            if len(np.intersect1d(ref_freq, uvdataf.freq_array)) > 0:
                logger.error(f"Overlapping frequencies detected. Skipping {f}")
                print(f"Overlapping frequencies detected. Skipping {f}")
                continue 

            uvdata_to_append.append(uvdataf)
            ref_freq = np.concatenate((ref_freq, uvdataf.freq_array))

        except Exception as e:
            logger.error(f"Failed processing {f}: {e}", exc_info=True)
            print(f"Failed processing {f}: {e}")
            return None 

    # Concatenate and finalize
    try:
        if uvdata_to_append:
            logger.info(f"Concatenating {len(uvdata_to_append)} frequency chunks...")
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=r".*key .* is longer than 8 characters.*")
                warnings.filterwarnings("ignore", message=r".*Telescope .* is not in known_telescopes.*")
                warnings.filterwarnings("ignore", message=r".*uvw_array does not match.*")
                
                uvdata_obj.fast_concat(
                    uvdata_to_append, 
                    axis='freq', 
                    inplace=True, 
                    verbose_history=True,
                    run_check=False, 
                    check_extra=False, 
                    run_check_acceptability=False, 
                    strict_uvw_antpos_check=False,
                    ignore_name=True
                )
            
            logger.info("Concatenation completed successfully.")
            print("Concatenation completed successfully.")
            
            # Run a more lenient final check with automatic conjugation fix
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=r".*uvw_array does not match.*")
                    uvdata_obj.check(check_extra=False, run_check_acceptability=False, allow_flip_conj=True)
                logger.info("✅ Final check passed (with automatic conjugation correction if needed)")
            except Exception as e_check:
                logger.warning(f"⚠️  Final check failed but continuing: {e_check}")

        # Reorder frequencies
        uvdata_obj.reorder_freqs(channel_order='freq', run_check=False)

        logger.info(f"Successfully loaded data. Nbls: {uvdata_obj.Nbls}, Ntimes: {uvdata_obj.Ntimes}, Nfreqs: {uvdata_obj.Nfreqs}, Nants: {uvdata_obj.Nants_data}")
        
        # Final coordinate validation
        if hasattr(uvdata_obj, 'uvw_array') and uvdata_obj.uvw_array is not None:
            final_uvw_max = np.max(np.abs(uvdata_obj.uvw_array))
            final_ant_max = np.sqrt(np.sum(uvdata_obj.telescope.antenna_positions**2, axis=1)).max()
            logger.info(f"Final validation - UVW max: {final_uvw_max:.1f} m, Antenna max: {final_ant_max:.1f} m")
            print(f"Final validation - UVW max: {final_uvw_max:.1f} m, Antenna max: {final_ant_max:.1f} m") 
            if final_uvw_max > 20 * final_ant_max:
                logger.warning(f"Large UVW/antenna ratio detected, but proceeding...")
                print(f"Large UVW/antenna ratio detected, but proceeding...")

        return uvdata_obj

    except Exception as e:
        logger.error(f"Failed during final processing: {e}", exc_info=True)
        return None

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
    Set phase centers and recalculate UVW coordinates for a drift scan.
    Updated for PyUVData 3.2.1.
    """
    logger.info("Setting phase centers and recalculating UVWs manually for drift scan.")
    logger.info(f"_set_phase_centers - PyUVData version: {pyuvdata.__version__}")

    # Improved telescope location handling for PyUVData 3.x
    if telescope_pos is None:
        telescope_pos = dsa110_utils.loc_dsa110
        logger.warning("Using default DSA-110 location for LST calculation in _set_phase_centers.")
    
    # Ensure telescope location is correctly set in uvdata_obj
    if not hasattr(uvdata_obj.telescope, 'location') or uvdata_obj.telescope.location is None:
        logger.error("CRITICAL: uvdata_obj.telescope has no location!")
        return None
    
    tel_earthloc = uvdata_obj.telescope.location
    logger.debug(f"Telescope location: {tel_earthloc}")
    
    # Compare with expected location
    try:
        expected_xyz = np.array([
            telescope_pos.itrs.x.value, 
            telescope_pos.itrs.y.value, 
            telescope_pos.itrs.z.value
        ])
        current_xyz = np.array([
            tel_earthloc.itrs.x.value,
            tel_earthloc.itrs.y.value, 
            tel_earthloc.itrs.z.value
        ])
        location_diff = np.sqrt(np.sum((current_xyz - expected_xyz)**2))
        if location_diff > 100:
            logger.warning(f"Large telescope location discrepancy: {location_diff:.1f} m")
    except Exception as e:
        logger.warning(f"Could not compare telescope locations: {e}")
    
    # Get effective telescope location in lat/lon/alt format for UVW calculation
    effective_telescope_loc_lat_lon_alt = (
        tel_earthloc.lat.rad, 
        tel_earthloc.lon.rad, 
        tel_earthloc.height.to_value(u.m)
    )
    
    # Check antenna names are available (PyUVData 3.x)
    if not (hasattr(uvdata_obj.telescope, 'antenna_names') and uvdata_obj.telescope.antenna_names is not None):
        logger.error("CRITICAL: UVData object missing telescope.antenna_names!")
        return None 
    
    # Better antenna position validation (PyUVData 3.x)
    if not (hasattr(uvdata_obj.telescope, 'antenna_positions') and uvdata_obj.telescope.antenna_positions is not None):
        logger.error("CRITICAL: UVData object missing telescope.antenna_positions!")
        return None
    
    # Verify antenna positions are reasonable
    ant_pos = uvdata_obj.telescope.antenna_positions
    max_distance = np.sqrt(np.sum(ant_pos**2, axis=1)).max()
    logger.debug(f"Max antenna distance from center: {max_distance:.1f} m")
    
    if max_distance > 50000:  # > 50 km suggests wrong coordinate system
        logger.error(f"Antenna positions seem wrong (max distance: {max_distance:.1f} m)")
        logger.error("This will cause large UVW discrepancies!")
        return None
    elif max_distance < 100:  # < 100 m suggests very small array or wrong units
        logger.warning(f"Antenna positions seem small (max distance: {max_distance:.1f} m)")

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
        
        common_epoch = Time(2000.0, format="jyear")

        for i, center_coord in enumerate(unique_pointing_skycoords):
            cat_name_str = f"{field_name_base}_T{i:04d}_RA{center_coord.ra.deg:.3f}"
            cat_id = uvdata_obj._add_phase_center(
                cat_name=cat_name_str,
                cat_type='sidereal',
                cat_lon=center_coord.ra.rad,  
                cat_lat=center_coord.dec.rad, 
                cat_frame='icrs',
                cat_epoch=common_epoch.jyear
            )
            logger.debug(f"Added phase center ID {cat_id}: {cat_name_str}")
            
            selection_mask_for_this_center = (blt_to_unique_time_map == i)
            new_phase_center_ids[selection_mask_for_this_center] = cat_id
            
            # More robust UVW calculation
            try:
                app_ra, app_dec = calc_app_coords(
                    lon_coord=center_coord.ra.rad, 
                    lat_coord=center_coord.dec.rad, 
                    coord_frame='icrs', 
                    coord_epoch=common_epoch.jyear,
                    time_array=Time(uvdata_obj.time_array[selection_mask_for_this_center], format='jd', scale='utc'),
                    lst_array=uvdata_obj.lst_array[selection_mask_for_this_center],
                    telescope_loc=effective_telescope_loc_lat_lon_alt, 
                    telescope_frame='itrs' 
                )
                
                frame_pa = calc_frame_pos_angle(
                    time_array=uvdata_obj.time_array[selection_mask_for_this_center], 
                    app_ra=app_ra,
                    app_dec=app_dec,
                    telescope_loc=effective_telescope_loc_lat_lon_alt, 
                    telescope_frame='itrs', 
                    ref_frame='icrs',
                    ref_epoch=common_epoch.jyear 
                )
                
                # KEY FIX: Use telescope object attributes for PyUVData 3.x
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
                
                # Validate UVW calculation results
                uvw_max = np.max(np.abs(uvw_new))
                logger.debug(f"Phase center {i}: max UVW = {uvw_max:.1f} m")
                
                if uvw_max > 10 * max_distance:
                    logger.warning(f"UVW values seem very large compared to antenna positions!")
                    logger.warning(f"UVW max: {uvw_max:.1f} m, Antenna max: {max_distance:.1f} m")
                
                uvdata_obj.uvw_array[selection_mask_for_this_center, :] = uvw_new
                uvdata_obj.phase_center_app_ra[selection_mask_for_this_center] = app_ra
                uvdata_obj.phase_center_app_dec[selection_mask_for_this_center] = app_dec
                uvdata_obj.phase_center_frame_pa[selection_mask_for_this_center] = frame_pa
                
            except Exception as e_uvw:
                logger.error(f"UVW calculation failed for phase center {i}: {e_uvw}")
                return None
            
        uvdata_obj.phase_center_id_array = new_phase_center_ids
        uvdata_obj._clear_unused_phase_centers() 

        logger.info(f"Manually re-phased and updated UVWs for {len(unique_pointing_skycoords)} unique pointing centers.")
        
        # Final validation
        final_uvw_max = np.max(np.abs(uvdata_obj.uvw_array))
        logger.info(f"Final UVW range: max = {final_uvw_max:.1f} m")
        
        if final_uvw_max > 20 * max_distance:
            logger.error(f"LARGE UVW DISCREPANCY LIKELY!")
            logger.error(f"UVW max ({final_uvw_max:.1f} m) >> antenna baseline max ({max_distance:.1f} m)")
            logger.error("Check telescope location and antenna position coordinate systems!")
        
        return uvdata_obj

    except Exception as e:
        logger.error(f"Failed to set phase centers using manual UVW calculation: {e}", exc_info=True)
        return None


def _make_calib_model(uvdata_obj: UVData, config: dict, telescope_pos: EarthLocation):
    """
    Generates a calibration model based on the provided configuration.
    Updated for PyUVData 3.x.
    """
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
    """
    Writes UVData object to an MS file using a subprocess to avoid casacore conflicts.
    Updated for PyUVData 3.x.
    """
    ms_outfile = f'{ms_outfile_base}.ms'
    logger.info(f"Writing Measurement Set to: {ms_outfile}")

    if os.path.exists(ms_outfile):
        if protect_files:
            logger.error(f"MS file {ms_outfile} already exists and protect_files is True. Skipping.")
            return None
        else:
            logger.warning(f"MS file {ms_outfile} already exists. Removing existing file.")
            try:
                import shutil
                shutil.rmtree(ms_outfile)
                logger.info(f"Removed existing MS file with shutil.rmtree: {ms_outfile}")
            except Exception as e_rmtree:
                logger.error(f"Failed to remove existing MS: {e_rmtree}. MS creation will likely fail.")
                return None
    
    # Conjugate baselines
    try: 
        logger.info("Conjugating baselines...")
        uvdata_obj.conjugate_bls(convention="ant2<ant1")
    except Exception as e_conjugate:
        logger.error(f"Failed to conjugate baselines: {e_conjugate}", exc_info=True)
        return None
    
    # Run final check with automatic conjugation correction
    try:
        logger.info("Running final pyuvdata check on uvdata_obj before writing MS...")
        uvdata_obj.check(check_extra=False, run_check_acceptability=False, allow_flip_conj=True)
        logger.info("Final pyuvdata check passed for uvdata_obj.")
        
        if uvcalib is not None:
            logger.info("Running final pyuvdata check on uvcalib (model) object...")
            uvcalib.check(check_extra=False, run_check_acceptability=False, allow_flip_conj=True) 
            logger.info("Final pyuvdata check passed for uvcalib (model) object.")
    except Exception as e_final_check:
        logger.error(f"Final pyuvdata check FAILED before MS write: {e_final_check}", exc_info=True)
        return None
    
    # Write the MS file
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r".*Writing in the MS file that the units of the data are uncalib.*")
            uvdata_obj.write_ms(ms_outfile,
                            run_check=False, 
                            force_phase=False, 
                            run_check_acceptability=False, 
                            strict_uvw_antpos_check=False)
        
        # If there is a calibration model, add it in a separate subprocess
        if uvcalib is not None:
            logger.info("Need to add MODEL_DATA, will use subprocess...")
            
            # Use subprocess to add MODEL_DATA so it doesn't conflict with pyuvdata
            import pickle
            import tempfile
            import subprocess
            
            # Create temp files
            with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
                calib_pickle_path = f.name
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
                script_path = f.name
            
            try:
                # Pickle calibration model
                with open(calib_pickle_path, 'wb') as f:
                    pickle.dump(uvcalib, f)
                
                # Create script
                script = f"""
import pickle
import sys
from pyuvdata.uvdata.ms import tables

try:
    # Load the calibration model
    print("Loading calibration model...")
    with open('{calib_pickle_path}', 'rb') as f:
        uvcalib = pickle.load(f)
    
    # Add imaging columns to MS
    print("Adding imaging columns to {ms_outfile}...")
    tables.addImagingColumns('{ms_outfile}')
    
    # Add model data
    print("Writing MODEL_DATA...")
    with tables.table('{ms_outfile}', readonly=False, ack=False) as tb:
        model_data = uvcalib.data_array.squeeze(axis=1)
        tb.putcol('MODEL_DATA', model_data)
        
        # Add CORRECTED_DATA (copy of DATA)
        data = tb.getcol('DATA')
        tb.putcol('CORRECTED_DATA', data)
    
    print("Successfully added MODEL_DATA and CORRECTED_DATA columns")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: Failed to add model data: {{e}}")
    sys.exit(1)
"""
                
                # Write script
                with open(script_path, 'w') as f:
                    f.write(script)
                
                # Run subprocess
                result = subprocess.run(
                    [sys.executable, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info("Successfully added MODEL_DATA columns")
                else:
                    logger.warning(f"Failed to add MODEL_DATA: {result.stderr}")
            finally:
                # Clean up
                try:
                    os.unlink(calib_pickle_path)
                    os.unlink(script_path)
                except:
                    pass
        
        return ms_outfile
    except Exception as e:
        logger.error(f"Failed to write MS file {ms_outfile}: {e}", exc_info=True)
        return None

def find_hdf5_sets(config: dict):
    """
    Finds complete sets of HDF5 files in the incoming directory.
    Returns a dictionary with timestamps as keys and lists of file paths as values.
    """
    logger.info("Finding complete sets of HDF5 files...")
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
    """
    Processes a single complete set of HDF5 files into an MS file.
    Updated for PyUVData 3.x.
    """
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

    # Add coordinate system check (now using telescope object)
    print("=== QUICK COORDINATE SYSTEM CHECK ===")
    print(f"Telescope location: {uvdata_obj.telescope.location}")
    
    if hasattr(uvdata_obj.telescope, 'antenna_positions') and uvdata_obj.telescope.antenna_positions is not None:
        max_ant_dist = np.sqrt(np.sum(uvdata_obj.telescope.antenna_positions**2, axis=1)).max()
        print(f"Max antenna distance from center: {max_ant_dist:.1f} m")
        
        if max_ant_dist > 1e5:  # > 100 km = absolute coordinates
            print("🚨 PROBLEM FOUND: Antenna positions are in ABSOLUTE ECEF coordinates!")
            print("🔧 APPLYING FIX: Converting to relative coordinates...")
            
            # Apply the fix (using telescope object)
            tel_xyz = np.array([
                uvdata_obj.telescope.location.itrs.x.value,
                uvdata_obj.telescope.location.itrs.y.value,
                uvdata_obj.telescope.location.itrs.z.value
            ])
            uvdata_obj.telescope.antenna_positions = uvdata_obj.telescope.antenna_positions - tel_xyz
            
            new_max_dist = np.sqrt(np.sum(uvdata_obj.telescope.antenna_positions**2, axis=1)).max()
            print(f"After fix, max antenna distance: {new_max_dist:.1f} m")
            
            if new_max_dist < 10000:  # Should be reasonable now
                print("✅ Fix successful! UVW discrepancy should be resolved.")
            else:
                print("❌ Fix didn't work as expected.")
        else:
            print(f"✅ Antenna positions look reasonable ({max_ant_dist:.1f} m)")
    print("=== END QUICK CHECK ===")

    field_name_base = "drift"
    
    # Try multiple phasing approaches in order of preference
    phasing_methods = [
        #("simple", _set_phase_centers_simple),
        #("manual", _set_phase_centers),  
        ("builtin", _set_phase_centers_builtin)
    ]
    
    uvdata_obj_phased = None
    for method_name, method_func in phasing_methods:
        logger.info(f"Attempting {method_name} phasing method...")
        print(f"Attempting {method_name} phasing method...")
        try:
            uvdata_obj_phased = method_func(uvdata_obj, field_name_base, dsa110_utils.loc_dsa110)
            if uvdata_obj_phased is not None:
                logger.info(f"Successfully used {method_name} phasing method")
                print(f"Successfully used {method_name} phasing method")
                break
            else:
                logger.warning(f"{method_name} phasing method returned None")
                print(f"{method_name} phasing method returned None")
        except Exception as e:
            logger.warning(f"{method_name} phasing method failed: {e}")
            print(f"{method_name} phasing method failed: {e}")
            continue
    
    if uvdata_obj_phased is None:
        logger.error(f"All phasing methods failed for {timestamp}. Skipping.")
        print(f"All phasing methods failed for {timestamp}. Skipping.")
        return None

    uvmodel_for_ms = _make_calib_model(uvdata_obj_phased, config, dsa110_utils.loc_dsa110) 
    protect_files = False 
    
    ms_output_path = _write_ms(uvdata_obj_phased, uvmodel_for_ms, output_ms_base, protect_files)
    if not ms_output_path:
        logger.error("MS writing failed.")
        return None
    else:
        logger.info(f"Successfully wrote MS: {ms_output_path}.")

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

# Note: You'll also need to implement _set_phase_centers_simple and _set_phase_centers_builtin
# or remove the references to them in process_hdf5_set
def _set_phase_centers_simple(uvdata_obj: UVData, field_name_base: str, telescope_pos: EarthLocation):
    """
    Simplified phasing that just sets phase centers without recalculating UVWs
    """
    logger.info("Using simplified phase center setting (keeping original UVWs)")
    
    try:
        vis_coords = _compute_pointing_per_visibility(uvdata_obj, telescope_pos)
        if vis_coords is None:
            raise ValueError("Failed to compute per-visibility pointing coordinates.")
        
        unique_jd_times, unique_time_indices, blt_to_unique_time_map = np.unique(
            uvdata_obj.time_array, return_index=True, return_inverse=True
        )
        unique_pointing_skycoords = vis_coords[unique_time_indices]
        
        logger.info(f"Found {len(unique_pointing_skycoords)} unique pointing centers.")

        uvdata_obj.phase_center_catalog = {} 
        new_phase_center_ids = np.zeros(uvdata_obj.Nblts, dtype=int) 
        
        common_epoch = Time(2000.0, format="jyear")

        for i, center_coord in enumerate(unique_pointing_skycoords):
            cat_name_str = f"{field_name_base}_T{i:04d}_RA{center_coord.ra.deg:.3f}"
            cat_id = uvdata_obj._add_phase_center(
                cat_name=cat_name_str,
                cat_type='sidereal',
                cat_lon=center_coord.ra.rad,  
                cat_lat=center_coord.dec.rad, 
                cat_frame='icrs',
                cat_epoch=common_epoch.jyear
            )
            logger.debug(f"Added phase center ID {cat_id}: {cat_name_str}")
            
            selection_mask_for_this_center = (blt_to_unique_time_map == i)
            new_phase_center_ids[selection_mask_for_this_center] = cat_id
            
        uvdata_obj.phase_center_id_array = new_phase_center_ids
        uvdata_obj._clear_unused_phase_centers() 

        # Keep original UVWs - don't recalculate
        logger.info(f"Set phase centers for {len(unique_pointing_skycoords)} unique pointings (keeping original UVWs)")
        return uvdata_obj

    except Exception as e:
        logger.error(f"Failed to set phase centers (simple method): {e}", exc_info=True)
        return None

def _set_phase_centers_builtin(uvdata_obj: UVData, field_name_base: str, telescope_pos: EarthLocation):
    """
    Use pyuvdata's built-in phasing instead of manual UVW calculation
    """
    logger.info("Attempting to use pyuvdata built-in phasing method")
    
    # Calculate pointing coordinates
    vis_coords = _compute_pointing_per_visibility(uvdata_obj, telescope_pos)
    if vis_coords is None:
        logger.warning("Could not compute pointing coordinates, falling back to manual method")
        return _set_phase_centers(uvdata_obj, field_name_base, telescope_pos)
    
    # Use pyuvdata's phase_to_time method instead of manual calc
    try:
        # Use unique times instead of full time array
        unique_times = np.unique(uvdata_obj.time_array)
        logger.info(f"Phasing to {len(unique_times)} unique times")
        
        # Phase to each unique time
        for i, unique_time in enumerate(unique_times):
            time_obj = Time(unique_time, format='jd')
            logger.debug(f"Phasing to time {i+1}/{len(unique_times)}: {time_obj.iso}")
            
            # This creates a phase center for this specific time
            uvdata_obj.phase_to_time(time_obj)
            
        logger.info("Successfully used pyuvdata built-in phasing method")
        return uvdata_obj
        
    except Exception as e:
        logger.warning(f"Built-in phasing failed: {e}, falling back to manual method")
        return _set_phase_centers(uvdata_obj, field_name_base, telescope_pos)