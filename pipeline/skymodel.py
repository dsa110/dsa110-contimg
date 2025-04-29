# pipeline/skymodel.py
# Updated: Removed top_n source selection, now uses flux limit only.

import os
import numpy as np
from shutil import rmtree
import warnings

# Astropy imports
from astropy.coordinates import SkyCoord, Angle, match_coordinates_sky
import astropy.units as u
from astropy.table import Table, vstack

# Astroquery import
try:
    from astroquery.vizier import Vizier
    # Configure Vizier query settings
    Vizier.ROW_LIMIT = -1 # No row limit
    Vizier.columns = ["*"] # Retrieve all columns by default
    astroquery_available = True
except ImportError:
    print("Warning: astroquery not found. Sky model generation will be limited.")
    astroquery_available = False

# CASA imports
try:
    from casatasks import exportfits # For imaging model if needed
    from casatools import componentlist, msmetadata, imager
    casa_available = True
except ImportError:
    print("Warning: CASA tools not found. Component list creation functionality will be limited.")
    # Only set to False if it wasn't already False from casatasks import
    if 'casa_available' not in locals() or casa_available:
        casa_available = False


# Pipeline imports
from .pipeline_utils import get_logger

logger = get_logger(__name__)

# --- Helper Functions ---

def _calculate_spectral_index(flux1, freq1, flux2, freq2):
    """Calculate spectral index alpha, where S ~ nu^alpha."""
    # Avoid log(0) or division by zero
    if flux1 <= 0 or flux2 <= 0:
        return None
    try:
        # Ensure inputs are floats
        flux1, freq1, flux2, freq2 = map(float, [flux1, freq1, flux2, freq2])
        log_flux_ratio = np.log(flux1 / flux2)
        log_freq_ratio = np.log(freq1 / freq2)
        if log_freq_ratio == 0:
            return None # Same frequency
        return log_flux_ratio / log_freq_ratio
    except (ValueError, TypeError, ZeroDivisionError):
        return None

def _format_casa_source_dict(source_row, nvss_cat_info, tgss_cat_info=None, tgss_match=None):
    """Formats data for one source into a dictionary for cl.addcomponent."""
    nvss_flux_col = nvss_cat_info['flux_col']
    nvss_freq_hz = nvss_cat_info['freq_hz']
    tgss_flux_col = tgss_cat_info.get('flux_col', None) if tgss_cat_info else None
    tgss_freq_hz = tgss_cat_info.get('freq_hz', None) if tgss_cat_info else None

    # Basic Info from NVSS
    # RA/Dec should be strings in 'HH:MM:SS.s'/'DD:MM:SS.s' format from Vizier query result
    ra_str = source_row['RAJ2000']
    dec_str = source_row['DEJ2000']
    # Convert to CASA format string: J2000 HHhMMmSS.ss +DDdMMmSS.ss
    try:
        # Use SkyCoord to parse and format robustly
        temp_coord = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg), frame='icrs')
        direction = f"J2000 {temp_coord.ra.to_string(unit=u.hour, sep='hms', precision=4)} {temp_coord.dec.to_string(unit=u.deg, sep='dms', precision=3, alwayssign=True)}"
    except Exception as e:
        logger.warning(f"Could not parse coordinates {ra_str}, {dec_str} for component list: {e}. Skipping source.")
        return None

    flux_nvss_mjy = source_row[nvss_flux_col]
    flux_jy = flux_nvss_mjy / 1000.0
    if not np.isfinite(flux_jy) or flux_jy <= 0:
         logger.warning(f"Invalid flux ({flux_jy} Jy) for source at {direction}. Skipping.")
         return None
    freq_str = f"{nvss_freq_hz / 1e9:.3f}GHz" # e.g., 1.400GHz

    # Gaussian Shape (use defaults or NVSS values if they exist)
    maj_val = source_row.get('MajAxis', 15.0) # Default 15 arcsec
    min_val = source_row.get('MinAxis', 15.0) # Default 15 arcsec
    pa_val = source_row.get('PA', 0.0)       # Default 0 deg
    if not isinstance(maj_val, (int, float)) or not np.isfinite(maj_val) or maj_val <= 0: maj_val = 15.0
    if not isinstance(min_val, (int, float)) or not np.isfinite(min_val) or min_val <= 0: min_val = 15.0
    if not isinstance(pa_val, (int, float)) or not np.isfinite(pa_val): pa_val = 0.0

    # Ensure major >= minor
    if maj_val < min_val:
        maj_val, min_val = min_val, maj_val
        pa_val += 90.0

    major_axis_str = f"{maj_val:.4f}arcsec"
    minor_axis_str = f"{min_val:.4f}arcsec"
    pa_str = f"{pa_val:.2f}deg"

    # Spectral Index (optional, requires TGSS match)
    spectral_index = None
    spectrum_type = 'Constant' # Default
    if tgss_match is not None and tgss_flux_col and tgss_freq_hz:
        flux_tgss_mjy = tgss_match[tgss_flux_col]
        # Check for valid TGSS flux
        if isinstance(flux_tgss_mjy, (int, float)) and np.isfinite(flux_tgss_mjy):
             spectral_index = _calculate_spectral_index(flux_jy, nvss_freq_hz, flux_tgss_mjy / 1000.0, tgss_freq_hz)
             if spectral_index is not None and np.isfinite(spectral_index):
                  spectrum_type = 'Spectral Index'
             else:
                  spectral_index = None # Reset if calculation failed

    # Get unique source label if possible
    source_label = f"NVSS_{ra_str}_{dec_str}".replace(':','').replace('.','p').replace('+','p').replace('-','m')
    if 'NVSS' in source_row.colnames and source_row['NVSS']: # Use NVSS identifier if available
         source_label = f"NVSS_{source_row['NVSS']}"


    source_dict = {
        'label': source_label,
        'direction': direction,
        'flux': flux_jy,
        'fluxunit': 'Jy',
        'freq': freq_str,
        'shape': 'Gaussian',
        'majoraxis': major_axis_str,
        'minoraxis': minor_axis_str,
        'positionangle': pa_str,
        'spectrumtype': spectrum_type,
    }
    if spectrum_type == 'Spectral Index':
        source_dict['index'] = spectral_index # CASA expects single float for index

    return source_dict

# --- Main Functions ---

def create_field_component_list(config: dict, center_coord: SkyCoord, output_cl_path: str):
    """Creates a CASA component list from NVSS/TGSS sources above a flux limit around a center coord."""
    if not casa_available:
        logger.error("CASA tools not available, cannot create component list.")
        return None, None
    if not astroquery_available:
        logger.error("astroquery not available, cannot query catalogs.")
        return None, None

    logger.info(f"Creating field component list around {center_coord.to_string('hmsdms')} -> {output_cl_path}")

    skymodel_config = config.get('skymodel', {})
    paths_config = config['paths']
    os.makedirs(os.path.dirname(output_cl_path), exist_ok=True)

    # Catalog Query Parameters
    radius_deg = skymodel_config.get('nvss_query_radius_deg', 2.0) # Search radius
    flux_limit_jy = skymodel_config.get('nvss_flux_limit_jy', 0.005) # Min flux in model (e.g., 5 mJy)
    # top_n = skymodel_config.get('nvss_top_n', 100) # <<< REMOVED PARAMETER USAGE >>>

    # Define Catalogs (could move to config)
    nvss_cat_info = {'name': 'NVSS', 'code': 'VIII/65/nvss', 'flux_col': 'S1.4', 'freq_hz': 1.4e9}
    tgss_cat_info = {'name': 'TGSS ADR1', 'code': 'J/A+A/598/A78/table3', 'flux_col': 'Peak_flux', 'freq_hz': 150e6}

    # --- Query NVSS ---
    logger.info(f"Querying {nvss_cat_info['name']} within {radius_deg} deg...")
    try:
        nvss_result = Vizier.query_region(center_coord, radius=radius_deg * u.deg, catalog=nvss_cat_info['code'])
        if not nvss_result:
            logger.warning("No NVSS sources found in the specified region.")
            return None, None # Or create empty CL?
        nvss_table = nvss_result[0]
        logger.info(f"Found {len(nvss_table)} NVSS sources initially.")
        # Filter out sources with masked/invalid flux
        nvss_table = nvss_table[~nvss_table[nvss_cat_info['flux_col']].mask]
        nvss_table = nvss_table[nvss_table[nvss_cat_info['flux_col']] > 0] # Ensure positive flux
        logger.info(f"Found {len(nvss_table)} NVSS sources with valid flux.")
        if not nvss_table: return None, None

    except Exception as e:
        logger.error(f"NVSS Vizier query failed: {e}", exc_info=True)
        return None, None

    # --- Query TGSS (Optional) ---
    tgss_table = None
    tgss_matches = None # Will store matched TGSS entry for each NVSS source
    use_spectral_indices = tgss_cat_info is not None # Check if TGSS configured
    if use_spectral_indices:
        logger.info(f"Querying {tgss_cat_info['name']} within {radius_deg} deg for spectral indices...")
        try:
            # Use larger box query for TGSS if necessary to ensure matches near edge
            tgss_result = Vizier.query_region(center_coord, radius=(radius_deg + 0.1) * u.deg, catalog=tgss_cat_info['code'])
            if tgss_result:
                tgss_table = tgss_result[0]
                # Filter TGSS for valid flux
                tgss_table = tgss_table[~tgss_table[tgss_cat_info['flux_col']].mask]
                tgss_table = tgss_table[tgss_table[tgss_cat_info['flux_col']] > 0]
                logger.info(f"Found {len(tgss_table)} TGSS sources with valid flux.")
            else:
                logger.warning("No TGSS sources found in the region.")
                tgss_table = None
        except Exception as e:
            logger.warning(f"TGSS Vizier query failed: {e}. Proceeding without spectral indices.")
            tgss_table = None

    # --- Filter NVSS Sources by Flux Limit ---
    # Apply flux limit (convert config Jy to mJy for comparison)
    flux_limit_mjy = flux_limit_jy * 1000.0
    selected_nvss_table = nvss_table[nvss_table[nvss_cat_info['flux_col']] >= flux_limit_mjy]
    logger.info(f"{len(selected_nvss_table)} NVSS sources selected after flux cut >= {flux_limit_mjy:.1f} mJy.")

    # --- REMOVED Sorting by flux ---
    # nvss_table.sort(nvss_cat_info['flux_col'], reverse=True)

    # --- REMOVED Selection of top N brightest ---
    # if len(nvss_table) > top_n:
    #     logger.info(f"Selecting top {top_n} brightest sources.")
    #     nvss_table = nvss_table[:top_n]

    if not selected_nvss_table:
        logger.warning("No sources selected after filtering. Cannot create component list.")
        return None, selected_nvss_table # Return empty table

    # --- Cross-match with TGSS (if available) ---
    if tgss_table is not None and len(tgss_table) > 0:
        logger.info("Cross-matching selected NVSS sources with TGSS...")
        # Ensure selected_nvss_table is not empty before accessing coordinates
        if len(selected_nvss_table) > 0:
            nvss_coords = SkyCoord(selected_nvss_table['RAJ2000'], selected_nvss_table['DEJ2000'], unit=(u.hourangle, u.deg), frame='icrs')
            tgss_coords = SkyCoord(tgss_table['RAJ2000'], tgss_table['DEJ2000'], unit=(u.deg, u.deg), frame='icrs') # TGSS usually in degrees

            max_separation = 15 * u.arcsec # Matching radius (configurable?)
            idx, d2d, _ = match_coordinates_sky(nvss_coords, tgss_coords)

            # Create a placeholder table for matches, initially None
            tgss_matches = Table([None] * len(selected_nvss_table), names=['matched_tgss'], dtype=[object])

            matched_count = 0
            for i_nvss, (i_tgss, sep) in enumerate(zip(idx, d2d)):
                if sep <= max_separation:
                    tgss_matches['matched_tgss'][i_nvss] = tgss_table[i_tgss] # Store the matched row
                    matched_count += 1
            logger.info(f"Found {matched_count} cross-matches within {max_separation.to('arcsec').value} arcsec.")
        else:
             logger.info("No NVSS sources to cross-match.")
             tgss_matches = None


    # --- Create Component List ---
    if os.path.exists(output_cl_path):
        logger.warning(f"Component list {output_cl_path} already exists. Removing.")
        try:
            rmtree(output_cl_path)
        except Exception as e:
            logger.error(f"Failed to remove existing component list: {e}")
            return None, None

    try:
        cl = componentlist()
        source_count = 0
        for i, nvss_source in enumerate(selected_nvss_table):
            tgss_match = tgss_matches['matched_tgss'][i] if tgss_matches is not None else None
            source_dict = _format_casa_source_dict(nvss_source, nvss_cat_info, tgss_cat_info, tgss_match)
            if source_dict:
                # Use addcomponent arguments explicitly
                cl.addcomponent(
                    label=source_dict.get('label', f'Comp{i}'),
                    dir=source_dict['direction'],
                    flux=source_dict['flux'],
                    fluxunit=source_dict['fluxunit'],
                    freq=source_dict['freq'],
                    shape=source_dict['shape'],
                    majoraxis=source_dict['majoraxis'],
                    minoraxis=source_dict['minoraxis'],
                    positionangle=source_dict['positionangle'],
                    spectrumtype=source_dict['spectrumtype'],
                    index=source_dict.get('index', 0.0) # Provide default index if needed by CASA? Typically only needed if type='Spectral Index'
                 )
                source_count += 1
            else:
                # Warning already logged in _format_casa_source_dict
                pass

        if source_count > 0:
            cl.rename(output_cl_path)
            cl.close()
            logger.info(f"Successfully created component list {output_cl_path} with {source_count} sources.")
            return output_cl_path, selected_nvss_table # Return path and table of sources included
        else:
            logger.warning("No sources added to component list.")
            cl.close()
            return None, selected_nvss_table

    except Exception as e:
        logger.error(f"Failed to create or save component list {output_cl_path}: {e}", exc_info=True)
        if 'cl' in locals() and cl.isopen():
            cl.close()
        if os.path.exists(output_cl_path): rmtree(output_cl_path) # Clean up partial file
        return None, None


def create_calibrator_component_list(config: dict, cal_info: dict, output_cl_path: str):
    """Creates a component list for a single specified calibrator."""
    if not casa_available:
        logger.error("CASA tools not available, cannot create component list.")
        return None, None

    logger.info(f"Creating component list for single calibrator {cal_info.get('name', 'UNKNOWN')} -> {output_cl_path}")
    os.makedirs(os.path.dirname(output_cl_path), exist_ok=True)

    # Extract info provided in cal_info dictionary
    # Example keys: name, ra, dec, epoch, flux_jy, ref_freq_ghz, spectral_index (optional)
    try:
        # Format direction string (ensure RA/Dec have units or are hmsdms strings)
        coord = SkyCoord(ra=cal_info['ra'], dec=cal_info['dec'], frame='icrs', epoch=cal_info.get('epoch', 'J2000'))
        # direction = f"J2000 {coord.ra.to_string(unit=u.hour, sep='hms', precision=4)} {coord.dec.to_string(unit=u.deg, sep='dms', precision=3)}" # Original format
        # Let's use a slightly more standard CASA format string if possible
        direction = f"{cal_info.get('epoch', 'J2000')} {coord.ra.to_string(unit=u.hour, sep=':', pad=True, precision=6)} {coord.dec.to_string(unit=u.deg, sep=':', pad=True, precision=5, alwayssign=True)}"


        flux_jy = float(cal_info['flux_jy'])
        if not np.isfinite(flux_jy) or flux_jy <= 0:
            raise ValueError(f"Invalid flux provided: {flux_jy}")
        ref_freq_ghz = float(cal_info.get('ref_freq_ghz', 1.4))
        freq_str = f"{ref_freq_ghz:.3f}GHz"

        spec_idx = cal_info.get('spectral_index', None)
        if spec_idx is not None:
            try:
                 index_val = float(spec_idx)
                 if np.isfinite(index_val):
                     spectrum_type = 'Spectral Index'
                 else:
                      raise ValueError("Spectral index must be finite")
            except (ValueError, TypeError):
                 logger.warning(f"Invalid spectral index '{spec_idx}' for {cal_info.get('name', '')}. Using Constant.")
                 spectrum_type = 'Constant'
                 index_val = 0.0
        else:
             spectrum_type = 'Constant'
             index_val = 0.0

        # Assume point source for calibrators unless shape info provided
        shape = cal_info.get('shape', 'point') # Default to point
        major_axis = cal_info.get('major_axis', '0arcsec')
        minor_axis = cal_info.get('minor_axis', '0arcsec')
        pa = cal_info.get('pa', '0deg')

    except KeyError as e:
        logger.error(f"Missing required key in cal_info dictionary for CL creation: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Error parsing calibrator info: {e}", exc_info=True)
        return None, None


    # --- Create Component List ---
    if os.path.exists(output_cl_path):
        logger.warning(f"Component list {output_cl_path} already exists. Removing.")
        try:
            rmtree(output_cl_path)
        except Exception as e:
            logger.error(f"Failed to remove existing component list: {e}")
            return None, None

    try:
        cl = componentlist()
        cl.addcomponent(
            label=cal_info.get('name', 'Calibrator'),
            dir=direction,
            flux=flux_jy,
            fluxunit='Jy',
            freq=freq_str,
            shape=shape,
            majoraxis=major_axis,
            minoraxis=minor_axis,
            positionangle=pa,
            spectrumtype=spectrum_type,
            index=index_val
        )
        cl.rename(output_cl_path)
        cl.close()
        logger.info(f"Successfully created single-source component list: {output_cl_path}")
        # Return path and maybe a minimal table representing the source
        cal_table = Table([cal_info]) # Make a simple table
        return output_cl_path, cal_table

    except Exception as e:
        logger.error(f"Failed to create or save component list {output_cl_path}: {e}", exc_info=True)
        if 'cl' in locals() and cl.isopen():
            cl.close()
        if os.path.exists(output_cl_path): rmtree(output_cl_path)
        return None, None

# Optional: Image Sky Model (Adapted from skymodel_utils.py)
# Needs significant refactoring to fit the new structure (config, logging)
# Might be better placed in imaging.py as a diagnostic function if needed.
# def image_skymodel(config: dict, cl_path: str, template_ms: str, output_image_base: str): ...