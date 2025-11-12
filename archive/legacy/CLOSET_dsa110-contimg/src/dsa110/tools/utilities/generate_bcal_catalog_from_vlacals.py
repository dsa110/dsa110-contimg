# generate_bcal_catalog_from_vla_list.py

import argparse
import os
import sys
import csv
import re
import numpy as np
import yaml # Requires pip install pyyaml
import pandas as pd
#import logging

# Astropy imports
try:
    from astropy.coordinates import SkyCoord, Angle
    import astropy.units as u
    astropy_available = True
except ImportError:
    print("ERROR: astropy library is required. Please install it (`pip install astropy`).")
    sys.exit(1)

def parse_vla_list_to_dataframe(vla_list_path):
    """
    Parses the vlacals.txt file
    and returns a pandas DataFrame.
    """
    print(f"Parsing VLA calibrator list using provided logic: {vla_list_path}")
    if not os.path.exists(vla_list_path):
        print(f"Input VLA list file not found: {vla_list_path}")
        return None

    # Define month prefixes
    months = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}

    try:
        with open(vla_list_path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Failed to read VLA list file {vla_list_path}: {e}", exc_info=True)
        return None

    records = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        parts = re.split(r"\s+", line)
        # Identify J2000 line by structure
        if len(parts) >= 5 and parts[1] == "J2000":
            j2000_name = parts[0]
            pc_j2000 = parts[2]
            ra = parts[3]
            dec = parts[4]
            extras = parts[5:]
            # Determine POS_REF and ALT_NAME 
            if len(extras) >= 2:
                pos_ref = extras[0]
                alt_name = extras[1]
            elif len(extras) == 1:
                if extras[0][:3] in months:
                    pos_ref = extras[0]
                    alt_name = "None"
                else:
                    pos_ref = "None"
                    alt_name = extras[0]
            else:
                pos_ref = "None"
                alt_name = "None"

            # Next line: B1950 (advance i)
            i += 1
            if i >= len(lines): break # Avoid index error at end of file
            bline = lines[i].strip()
            bparts = re.split(r"\s+", bline)
            if len(bparts) < 5 or bparts[1] != "B1950":
                # This means B1950 line wasn't found where expected,
                # reset and continue searching from next line
                print(f"Expected B1950 line after J2000 line {i}, but found '{bline}'. Skipping source {j2000_name}.")
                # Important: Need to make sure 'i' advances correctly even if B1950 is missing
                i += 1 # Advance past the unexpected line
                continue

            b1950_name = bparts[0]
            pc_b1950 = bparts[2]

            # Skip to band table 
            while i < len(lines) and not lines[i].startswith("BAND"):
                i += 1
            if i >= len(lines): break # EOF reached

            # Skip header underline 
            while i < len(lines) and re.match(r"^[= ]+$", lines[i]):
                i += 1
            if i >= len(lines): break # EOF reached

            # Parse bands 
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("-"):
                row = lines[i].strip()
                parts = re.split(r"\s+", row)
                # Ensure the first part looks like a band identifier (e.g., "20cm" or "L")
                # This check prevents misinterpreting lines if format is odd
                if parts and (re.match(r"^\d+\.?\d*cm$", parts[0]) or (len(parts[0])==1 and parts[0] in "PLCXUKQ")):
                    band_id = parts[0] # Could be '20cm' or just 'L' etc.
                    # Try to find the standard single letter code
                    band_code = "None"
                    codes = ["None"] * 4
                    flux = "None"
                    uvm_min = "None"
                    uvm_max = "None"

                    code_search_start_idx = 0
                    if band_id.endswith('cm'):
                         code_search_start_idx = 1

                    if len(parts) > code_search_start_idx and len(parts[code_search_start_idx])==1 and parts[code_search_start_idx] in "PLCXUKQ":
                         band_code = parts[code_search_start_idx]
                         struct_code_start_idx = code_search_start_idx + 1
                         if len(parts) >= struct_code_start_idx + 4:
                             codes = parts[struct_code_start_idx : struct_code_start_idx + 4]
                             # Extract numeric values for flux, uvm_min, uvm_max
                             nums = [p for p in parts[struct_code_start_idx + 4:] if re.match(r"^\d*\.?\d+$", p)]
                             if nums:
                                 flux = nums[0]
                                 if len(nums) > 1: uvm_min = nums[1]
                                 if len(nums) > 2: uvm_max = nums[2]

                    records.append({
                        "J2000_NAME": j2000_name, "B1950_NAME": b1950_name,
                        "PC_J2000": pc_j2000, "PC_B1950": pc_b1950,
                        "RA_J2000": ra, "DEC_J2000": dec,
                        "POS_REF": pos_ref, "ALT_NAME": alt_name,
                        "BAND": band_id, # Store band identifier
                        "BAND_CODE": band_code, # Store single letter code if found
                        "A": codes[0], "B": codes[1], "C": codes[2], "D": codes[3],
                        "FLUX_JY": flux, "UVMIN_kL": uvm_min, "UVMAX_kL": uvm_max
                    })
                else:
                     print(f"Line {i+1} skipped, doesn't look like a band data line: '{row}'")
                i += 1
            continue # Continue outer loop after processing bands
        i += 1

    # Build DataFrame
    if not records:
         print("No records parsed from VLA list.")
         return None

    df = pd.DataFrame(records)
    # Fill NA added by DataFrame creation if columns mismatch, although records should be consistent
    df = df.fillna("None")
    print(f"Successfully created DataFrame with {len(df)} band entries.")
    return df


def write_intermediate_csv(calibrator_df, output_csv_path):
    """Writes the fully parsed calibrator DataFrame to a CSV file."""
    if calibrator_df is None or calibrator_df.empty:
        print("No calibrator data to write to intermediate CSV.")
        return False
    print(f"Writing intermediate parsed data ({len(calibrator_df)} rows) to: {output_csv_path}")
    try:
        # Use pandas to_csv for simplicity
        df_to_write = calibrator_df.replace("None", np.nan) # Write actual NaNs for missing values
        df_to_write.to_csv(output_csv_path, index=False, na_rep='NaN', float_format='%.4f')
        print(f"Successfully wrote intermediate CSV: {output_csv_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to write intermediate CSV {output_csv_path}: {e}", exc_info=True)
        return False

def filter_and_write_bcal_candidates(config, intermediate_csv_path, output_bcal_csv_path, min_flux_override=None, dec_range_override=None):
    """Filters the intermediate VLA catalog and writes the final BPCAL candidate list."""
    if not os.path.exists(intermediate_csv_path):
        print(f"ERROR: Intermediate CSV file not found: {intermediate_csv_path}")
        return False

    print(f"Filtering calibrators from {intermediate_csv_path}...")
    try:
        # Load intermediate CSV using pandas
        df = pd.read_csv(intermediate_csv_path, na_values=['None', 'NaN', '']) # Read blank/None/NaN as NaN

        if df.empty:
             print("Intermediate CSV is empty. Cannot filter.")
             return False

        cal_config = config['calibration']
        # Declination Range
        if dec_range_override:
            try:
                dec_min, dec_max = map(float, dec_range_override.split(':'))
                print(f"Using overridden declination range: {dec_min} to {dec_max} deg")
            except Exception as e:
                print(f"Invalid format for --dec-range-deg '{dec_range_override}'. Use MIN:MAX. {e}")
                return False
        else:
            if 'fixed_declination_deg' not in cal_config:
                 print("Missing 'calibration:fixed_declination_deg' in config.")
                 return False
            fixed_dec_deg = cal_config['fixed_declination_deg']
            beam_radius_deg = cal_config.get('bcal_search_beam_radius_deg', 1.5)
            dec_min = fixed_dec_deg - beam_radius_deg
            dec_max = fixed_dec_deg + beam_radius_deg
            print(f"Using declination range from config: {dec_min:.2f} to {dec_max:.2f} deg")

        # Flux Range (use L-band/20cm flux for filtering)
        min_flux_jy = min_flux_override if min_flux_override is not None else cal_config.get('bcal_min_flux_jy', 5.0)
        max_flux_jy = cal_config.get('bcal_max_flux_jy', 100.0)
        print(f"Using L-band (20cm or L code) flux range: {min_flux_jy} to {max_flux_jy} Jy")

        # --- Filtering ---
        filtered_candidates = []
        processed_count = 0

        # Convert DEC_J2000 to degrees
        valid_dec_mask = df['DEC_J2000'].notna()
        df_valid = df[valid_dec_mask].copy() # Work on rows with valid Dec strings
        try:
            df_valid['dec_deg'] = df_valid['DEC_J2000'].apply(lambda x: Angle(x.replace('"',''), unit=u.deg).deg)
        except Exception as e:
             print(f"Failed to parse DEC_J2000 column: {e}. Check intermediate CSV format.")
             return False

        # Filter by Declination
        dec_mask = (df_valid['dec_deg'] >= dec_min) & (df_valid['dec_deg'] <= dec_max)
        df_dec_filtered = df_valid[dec_mask]
        print(f"{len(df_dec_filtered)} sources within declination range.")

        # Filter by L-band (check BAND_CODE == 'L' OR BAND == '20cm') and Flux
        # Convert flux to numeric, coercing errors
        df_dec_filtered = df_valid[dec_mask].copy()
        df_dec_filtered['flux_num'] = pd.to_numeric(df_dec_filtered['FLUX_JY'], errors='coerce')

        l_band_mask = (df_dec_filtered['BAND_CODE'] == 'L') | (df_dec_filtered['BAND'] == '20cm')
        flux_mask = (df_dec_filtered['flux_num'] >= min_flux_jy) & \
                    (df_dec_filtered['flux_num'] <= max_flux_jy) & \
                    (df_dec_filtered['flux_num'].notna())

        final_mask = l_band_mask & flux_mask
        filtered_df = df_dec_filtered[final_mask]

        print(f"Filtered down to {len(filtered_df)} BPCAL candidates matching L-band and flux criteria.")

        # --- Format Output ---
        header = ['name', 'ra_str', 'dec_str', 'flux_jy', 'epoch']
        output_rows = []
        for _, row in filtered_df.iterrows():
             output_rows.append({
                 'name': row['J2000_NAME'],
                 'ra_str': row['RA_J2000'], # Keep string format
                 'dec_str': row['DEC_J2000'],# Keep string format
                 'flux_jy': f"{row['flux_num']:.4f}", # Use L-band flux
                 'epoch': 'J2000'
             })

        # Write final CSV
        if not output_rows:
             print("No candidates remain after filtering.")
             with open(output_bcal_csv_path, 'w', newline='') as csvfile:
                  writer = csv.DictWriter(csvfile, fieldnames=header)
                  writer.writeheader()
             print(f"Created empty BPCAL candidate file: {output_bcal_csv_path}")
             return True

        print(f"Writing final BPCAL candidate list to: {output_bcal_csv_path}")
        with open(output_bcal_csv_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=header)
            writer.writeheader()
            writer.writerows(output_rows)

        print(f"Successfully wrote {len(output_rows)} candidates to {output_bcal_csv_path}")
        return True

    except KeyError as e:
        print(f"ERROR: Missing required key in configuration file or intermediate CSV: {e}", exc_info=True)
        return False
    except Exception as e:
        print(f"ERROR: Failed during filtering or writing final CSV: {e}", exc_info=True)
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
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()

    # --- Setup Basic Logging ---
    log_level = print if args.verbose else print
    #logging.basicConfig(level=log_level, format='%(asctime)s [%(levelname)-7s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S', handlers=[logging.StreamHandler(sys.stdout)])

    # --- Step 1: Parse the input text file ---
    parsed_df = parse_vla_list_to_dataframe(args.vla_list)

    if parsed_df is not None and not parsed_df.empty:
        # --- Step 2: Write the intermediate CSV ---
        if write_intermediate_csv(parsed_df, args.intermediate_csv):
            # --- Step 3: Filter and write the final candidate list ---
            try:
                # Load config *only* for filtering step
                with open(args.config, 'r') as f:
                     config_data = yaml.safe_load(f)
                if config_data is None: raise ValueError("Config file empty/invalid.")

                # Determine final output path from config or override
                final_output_path = args.output_file
                if final_output_path is None:
                    paths_config = config_data.get('paths', {})
                    cal_config = config_data.get('calibration', {})
                    base_dir_path = paths_config.get('pipeline_base_dir')
                    cal_tables_subdir = paths_config.get('cal_tables_dir')
                    bcal_catalog_filename = cal_config.get('bcal_candidate_catalog', 'bcal_candidates_vla.csv') # Default name

                    if not all([base_dir_path, cal_tables_subdir, bcal_catalog_filename]):
                         raise KeyError("Config file missing required keys: paths.pipeline_base_dir, paths.cal_tables_dir, calibration.bcal_candidate_catalog")

                    final_output_path = os.path.join(base_dir_path, cal_tables_subdir, bcal_catalog_filename)
                    # Resolve final output path if relative
                    if not os.path.isabs(final_output_path):
                          if not os.path.isabs(base_dir_path): base_dir_path = os.path.abspath(base_dir_path)
                          # Construct carefully, ensure intermediate directories exist
                          final_output_path = os.path.abspath(os.path.join(base_dir_path, cal_tables_subdir, bcal_catalog_filename))

                # Ensure output directory exists before filtering attempts writing
                os.makedirs(os.path.dirname(final_output_path), exist_ok=True)

                filter_and_write_bcal_candidates(
                    config_data, args.intermediate_csv, final_output_path,
                    min_flux_override=args.min_flux, dec_range_override=args.dec_range_deg
                )
            except Exception as e:
                print(f"ERROR loading config or running filtering: {e}", exc_info=True)
                sys.exit(1)
        else:
             print("ERROR: Failed to write intermediate CSV, cannot proceed to filtering.")
             sys.exit(1)
    elif parsed_df is not None and parsed_df.empty:
         print("Parsing succeeded but produced no records.")
    else: # parsed_data is None
        print("ERROR: Failed to parse VLA calibrator list.")
        sys.exit(1)

    print("\nCatalog generation process finished.")