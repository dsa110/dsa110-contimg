# generate_bcal_catalog_from_vla_list.py
# Updated: Yet another revision of flux line parsing logic

import argparse
import os
import sys
import csv
import re
import numpy as np
import yaml # Requires pip install pyyaml
from collections import defaultdict

# Astropy imports
try:
    from astropy.coordinates import SkyCoord, Angle
    import astropy.units as u
    astropy_available = True
except ImportError:
    print("ERROR: astropy library is required. Please install it (`pip install astropy`).")
    sys.exit(1)

# Astroquery import
try:
    from astroquery.vizier import Vizier
    Vizier.ROW_LIMIT = -1
    Vizier.TIMEOUT = 120
    astroquery_available = True
except ImportError:
    astroquery_available = False # Not needed for this script version

# Pipeline imports (assuming run from parent dir or pipeline in PYTHONPATH)
try:
    from pipeline.pipeline_utils import get_logger
except ImportError:
     # Simple fallback logger if utils not found (e.g., running script standalone)
     import logging
     logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
     logger = logging.getLogger(__name__)
     print("Warning: Could not import pipeline_utils logger, using basic logging.")


# --- Regular Expressions for Parsing ---
# Line 1: Name, J2000, PosCode, RA, Dec, Ref, AltName
re_j2000_line = re.compile(
    r"^(?P<iau_name>\S+)\s+"     # IAU Name (non-space)
    r"J2000\s+"                  # J2000 marker
    r"(?P<pos_code>[A-Z?])\s+"   # Position Code (A, B, C, T, ?)
    r"(?P<ra_str>\d{2}h\d{2}m\d{2}\.\d+s)\s+" # RA string
    r"(?P<dec_str>[+-]\d{2}d\d{2}'\d{2}\.\d+\")\s*" # Dec string
    r"(?P<pos_ref>\w+)?\s*"       # Optional Position Ref (e.g., Aug01)
    r"(?P<alt_name>\S+)?\s*$"     # Optional Alt Name (e.g., 3Cxxx, JVAS)
)
# Regex to find flux info: captures band code, 4 structure codes,
# and then searches the rest of the line for the first number.
re_flux_line_revised = re.compile(
    r"^\s*(?:\d+cm\s+)?(?P<band_code>[PLCXUKQ])\s+"      # Optional wavelength, MANDATORY Band Code
    r"(?P<a>[PSWCX?])\s+"                                 # Structure code A
    r"(?P<b>[PSWCX?])\s+"                                 # Structure code B
    r"(?P<c>[PSWCX?])\s+"                                 # Structure code C
    r"(?P<d>[PSWCX?])\s+"                                 # Structure code D
    r"(?P<rest_of_line>.*)$"                              # Capture everything after D code
)
# Regex to find the first float/int number in a string
re_first_number = re.compile(r"(\d+\.?\d*)")


def parse_vla_calibrator_file(vla_list_path):
    """Parses the vlacals.txt file and returns a list of source dictionaries."""
    logger.info(f"Parsing VLA calibrator list: {vla_list_path}")
    if not os.path.exists(vla_list_path):
        logger.error(f"Input VLA list file not found: {vla_list_path}")
        return None

    calibrators = []
    current_source = None
    in_flux_section = False # Flag to know if we are below the BAND ==== line

    try:
        with open(vla_list_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line_strip = line.strip()

                # Ignore blank lines, separators, source tags
                if not line_strip or line_strip.startswith("=") or line_strip.startswith("-") or line_strip.startswith("[source:"):
                    # Don't reset in_flux_section on separators within an entry
                    if not line_strip or line_strip.startswith("="): # Reset only on blank lines or ====
                         in_flux_section = False
                    continue

                # Check for BAND header line
                if line_strip.startswith("BAND"):
                    in_flux_section = True
                    continue

                # Try matching J2000 coordinate line (start of a new source)
                match_j2000 = re_j2000_line.match(line_strip)
                if match_j2000:
                    # If we were processing a source, finalize it before starting new one
                    if current_source:
                        calibrators.append(current_source)

                    # Start new source
                    data = match_j2000.groupdict()
                    current_source = {
                        'iau_name': data['iau_name'],
                        'ra_str': data['ra_str'],
                        'dec_str': data['dec_str'],
                        'pos_code': data['pos_code'],
                        'pos_ref': data.get('pos_ref'),
                        'alt_name': data.get('alt_name'),
                        'epoch': 'J2000',
                        'fluxes': {} # Dictionary to store fluxes by band code
                    }
                    in_flux_section = False # Wait for BAND header again
                    # logger.debug(f"Found source: {current_source['iau_name']}")
                    continue

                # If we are inside a source entry and in the flux section, try parsing flux lines
                if current_source and in_flux_section:
                    match_flux = re_flux_line_revised.match(line_strip)
                    if match_flux:
                        flux_data = match_flux.groupdict()
                        band_code = flux_data['band_code']
                        rest_of_line = flux_data['rest_of_line'].strip()

                        # Find the first number in the rest of the line
                        flux_val_match = re_first_number.search(rest_of_line)
                        flux_jy = None
                        if flux_val_match:
                            try:
                                flux_jy = float(flux_val_match.group(1))
                            except (ValueError, TypeError):
                                logger.warning(f"Found potential number '{flux_val_match.group(1)}' but failed float conversion on line {line_num}: '{line_strip}'")
                                flux_jy = None

                        if flux_jy is not None:
                            if band_code not in current_source['fluxes']:
                                current_source['fluxes'][band_code] = {
                                    'flux_jy': flux_jy,
                                    'struct_a': flux_data['a'],
                                    'struct_b': flux_data['b'],
                                    'struct_c': flux_data['c'],
                                    'struct_d': flux_data['d'],
                                }
                                logger.debug(f"  Parsed Flux: Band={band_code}, Flux={flux_jy:.4f}")
                            else:
                                logger.debug(f"  Duplicate band code {band_code} found for source {current_source['iau_name']} on line {line_num}. Keeping first value.")
                        else:
                            logger.warning(f"Could not find valid flux value on potential flux line {line_num}: '{line_strip}'")
                    # else: Line didn't match the expected flux line structure, ignore

            # Append the last source processed after EOF
            if current_source:
                calibrators.append(current_source)

        logger.info(f"Successfully parsed {len(calibrators)} calibrator entries.")
        return calibrators

    except Exception as e:
        logger.error(f"ERROR: Failed during parsing of {vla_list_path}: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return None


def write_intermediate_csv(calibrator_list, output_csv_path):
    """Writes the fully parsed calibrator list to a CSV file."""
    if not calibrator_list:
        logger.error("No calibrator data to write to intermediate CSV.")
        return False

    logger.info(f"Writing intermediate parsed data to: {output_csv_path}")
    # Define headers - include relevant bands explicitly
    headers = ['iau_name', 'ra_str', 'dec_str', 'pos_code', 'pos_ref', 'alt_name', 'epoch',
               'flux_P_jy', 'flux_L_jy', 'flux_C_jy', 'flux_X_jy',
               'flux_U_jy', 'flux_K_jy', 'flux_Q_jy',
               'struct_L_A', 'struct_L_B', 'struct_L_C', 'struct_L_D'] # Example structure codes for L band

    try:
        with open(output_csv_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore', quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()

            for source in calibrator_list:
                row_data = source.copy() # Start with basic info
                fluxes = row_data.pop('fluxes', {}) # Extract fluxes dict

                # Add flux for each band explicitly
                for band_code in ['P', 'L', 'C', 'X', 'U', 'K', 'Q']:
                    flux_info = fluxes.get(band_code, {})
                    flux_val = flux_info.get('flux_jy', '')
                    # Format as string, leave blank if missing or non-finite
                    row_data[f'flux_{band_code}_jy'] = f"{flux_val:.4f}" if isinstance(flux_val, (float, int)) and np.isfinite(flux_val) else ''

                    # Add structure codes if needed, e.g., for L band:
                    if band_code == 'L':
                         row_data['struct_L_A'] = flux_info.get('struct_a', '')
                         row_data['struct_L_B'] = flux_info.get('struct_b', '')
                         row_data['struct_L_C'] = flux_info.get('struct_c', '')
                         row_data['struct_L_D'] = flux_info.get('struct_d', '')
                writer.writerow(row_data)
        logger.info(f"Successfully wrote {len(calibrator_list)} sources to {output_csv_path}")
        return True
    except Exception as e:
        logger.error(f"ERROR: Failed to write intermediate CSV {output_csv_path}: {e}", exc_info=True)
        return False

def filter_and_write_bcal_candidates(config, intermediate_csv_path, output_bcal_csv_path, min_flux_override=None, dec_range_override=None):
    """Filters the intermediate VLA catalog and writes the final BPCAL candidate list."""
    if not os.path.exists(intermediate_csv_path):
        logger.error(f"ERROR: Intermediate CSV file not found: {intermediate_csv_path}")
        return False

    logger.info(f"Filtering calibrators from {intermediate_csv_path}...")
    try:
        cal_config = config['calibration']
        # Declination Range
        if dec_range_override:
            try:
                dec_min, dec_max = map(float, dec_range_override.split(':'))
                logger.info(f"Using overridden declination range: {dec_min} to {dec_max} deg")
            except Exception as e:
                logger.error(f"Invalid format for --dec-range-deg '{dec_range_override}'. Use MIN:MAX. {e}")
                return False
        else:
            if 'fixed_declination_deg' not in cal_config:
                 logger.error("Missing 'calibration:fixed_declination_deg' in config.")
                 return False
            fixed_dec_deg = cal_config['fixed_declination_deg']
            beam_radius_deg = cal_config.get('bcal_search_beam_radius_deg', 1.5)
            dec_min = fixed_dec_deg - beam_radius_deg
            dec_max = fixed_dec_deg + beam_radius_deg
            logger.info(f"Using declination range from config: {dec_min:.2f} to {dec_max:.2f} deg")

        # Flux Range (use L-band/20cm flux for filtering)
        min_flux_jy = min_flux_override if min_flux_override is not None else cal_config.get('bcal_min_flux_jy', 5.0)
        max_flux_jy = cal_config.get('bcal_max_flux_jy', 100.0) # Add max flux override if needed
        logger.info(f"Using L-band flux range: {min_flux_jy} to {max_flux_jy} Jy")

        filtered_candidates = []
        header = ['name', 'ra_str', 'dec_str', 'flux_jy', 'epoch'] # Output columns

        # Read intermediate CSV using standard csv reader
        with open(intermediate_csv_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            processed_count = 0
            filtered_count = 0
            if reader.fieldnames is None:
                 logger.error(f"Could not read headers from intermediate CSV: {intermediate_csv_path}")
                 return False

            for row in reader:
                processed_count += 1
                try:
                    # Convert Dec string (e.g., +DDdMM'SS.s") to degrees
                    dec_str_cleaned = row.get('dec_str','').replace('"', '')
                    if not dec_str_cleaned: continue # Skip if Dec is empty
                    dec_angle = Angle(dec_str_cleaned, unit=u.deg)
                    dec_deg = dec_angle.deg

                    # Check declination range
                    if not (dec_min <= dec_deg <= dec_max):
                        continue

                    # Check L-band flux
                    flux_l_str = row.get('flux_L_jy', '')
                    if not flux_l_str: # Skip if L-band flux is missing
                        continue
                    flux_l_jy = float(flux_l_str)

                    # Check flux range
                    if not (min_flux_jy <= flux_l_jy <= max_flux_jy):
                        continue

                    # If all checks pass, format for output
                    filtered_candidates.append({
                        'name': row['iau_name'],
                        'ra_str': row['ra_str'], # Keep original string format
                        'dec_str': row['dec_str'],# Keep original string format
                        'flux_jy': f"{flux_l_jy:.4f}", # Use L-band flux
                        'epoch': row['epoch']
                    })
                    filtered_count += 1
                except Exception as e:
                    logger.warning(f"Warning: Skipping row #{processed_count} due to parsing/filtering error: {row} - {e}", exc_info=True)
                    continue

        logger.info(f"Filtered down to {len(filtered_candidates)} BPCAL candidates from {processed_count} parsed sources.")

        # Write final CSV
        if not filtered_candidates:
             logger.warning("No candidates remain after filtering.")
             # Create empty file with header
             with open(output_bcal_csv_path, 'w', newline='') as csvfile:
                  writer = csv.DictWriter(csvfile, fieldnames=header)
                  writer.writeheader()
             logger.info(f"Created empty BPCAL candidate file: {output_bcal_csv_path}")
             return True

        logger.info(f"Writing final BPCAL candidate list to: {output_bcal_csv_path}")
        with open(output_bcal_csv_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=header)
            writer.writeheader()
            writer.writerows(filtered_candidates)

        logger.info(f"Successfully wrote {len(filtered_candidates)} candidates to {output_bcal_csv_path}")
        return True

    except KeyError as e:
        logger.error(f"ERROR: Missing required key in configuration file for filtering: {e}")
        return False
    except Exception as e:
        logger.error(f"ERROR: Failed during filtering or writing final CSV: {e}", exc_info=True)
        return False


# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate VLA BPCAL Candidate Catalog from Text List.")
    parser.add_argument("-c", "--config", required=True, help="Path to the main pipeline YAML config file.")
    parser.add_argument("--vla-list", required=True, help="Path to the input VLA calibrator text file (vlacals.txt).")
    parser.add_argument("--intermediate-csv", default="vla_calibrators_parsed.csv", help="Path for the intermediate CSV containing all parsed sources.")
    parser.add_argument("-o", "--output-file", default=None, help="Override final output BPCAL candidate CSV file path (default: path from config).")
    parser.add_argument("--min-flux", type=float, default=None, help="Override minimum L-band flux density in Jy (default: value from config).")
    parser.add_argument("--dec-range-deg", default=None, help="Override declination range 'MIN:MAX' in degrees (default: range from config).")

    args = parser.parse_args()

    # --- Step 1: Parse the input text file ---
    parsed_data = parse_vla_calibrator_file(args.vla_list)

    if parsed_data:
        # --- Step 2: Write the intermediate CSV ---
        if write_intermediate_csv(parsed_data, args.intermediate_csv):
            # --- Step 3: Filter and write the final candidate list ---
            try:
                # Load config *only* for filtering step
                with open(args.config, 'r') as f:
                     config_data = yaml.safe_load(f)
                if config_data is None: raise ValueError("Config file empty/invalid.")

                 # Determine final output path
                final_output_path = args.output_file
                if final_output_path is None:
                    paths_config = config_data['paths']
                    cal_config = config_data['calibration']
                    final_output_path = os.path.join(
                        paths_config['pipeline_base_dir'],
                        paths_config['cal_tables_dir'],
                        cal_config.get('bcal_candidate_catalog', 'bcal_candidates_vla.csv') # Default filename if key missing
                    )
                    # Resolve final output path if relative
                    if not os.path.isabs(final_output_path) and 'pipeline_base_dir' in paths_config:
                          base_dir = paths_config['pipeline_base_dir']
                          if not os.path.isabs(base_dir): base_dir = os.path.abspath(base_dir) # Resolve base if relative
                          final_output_path = os.path.join(base_dir, final_output_path)

                # Ensure output directory exists before filtering attempts writing
                os.makedirs(os.path.dirname(final_output_path), exist_ok=True)

                filter_and_write_bcal_candidates(
                    config_data,
                    args.intermediate_csv,
                    final_output_path,
                    min_flux_override=args.min_flux,
                    dec_range_override=args.dec_range_deg
                )
            except Exception as e:
                print(f"ERROR loading config or running filtering: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
        else:
             print("ERROR: Failed to write intermediate CSV, cannot proceed to filtering.")
             sys.exit(1)
    else:
        print("ERROR: Failed to parse VLA calibrator list.")
        sys.exit(1)

    print("\nCatalog generation process finished.")