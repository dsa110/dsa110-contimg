# generate_bcal_catalog.py

import argparse
import os
import sys
import csv
import numpy as np
import yaml # Requires pip install pyyaml

# Astropy imports
from astropy.coordinates import SkyCoord
import astropy.units as u

# Astroquery import
try:
    from astroquery.vizier import Vizier
    # Configure Vizier query settings
    Vizier.ROW_LIMIT = -1 # No row limit
    Vizier.TIMEOUT = 120 # Increase timeout for potentially large queries
    astroquery_available = True
except ImportError:
    print("ERROR: astroquery library is required. Please install it (`pip install astroquery`).")
    sys.exit(1)


def generate_catalog(config_path, output_file_override=None, min_flux_override=None, dec_range_override=None):
    """Generates the BPCAL candidate catalog by querying NVSS."""

    print(f"Loading configuration from: {config_path}")
    if not os.path.exists(config_path):
        print(f"ERROR: Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if config is None:
             raise ValueError("Config file is empty or invalid YAML.")
    except Exception as e:
        print(f"ERROR: Could not load/parse config file {config_path}: {e}")
        sys.exit(1)

    # --- Get Parameters ---
    try:
        # Output path
        paths_config = config['paths']
        cal_config = config['calibration']
        phot_config = config.get('photometry', {}) # For target flux, avoid selecting BPCALs too faint

        output_file = output_file_override or os.path.join(
            paths_config['pipeline_base_dir'],
            paths_config['cal_tables_dir'], # Store alongside other cal tables? Or separate dir?
            cal_config.get('bcal_candidate_catalog', 'bcal_candidates_nvss.csv') # Get filename from config
        )
        # Resolve output path if relative
        if not os.path.isabs(output_file) and 'pipeline_base_dir' in paths_config:
             # Assume relative to base dir if not absolute
             output_file = os.path.join(paths_config['pipeline_base_dir'], output_file)
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)


        # Declination Range
        if dec_range_override:
            try:
                dec_min, dec_max = map(float, dec_range_override.split(':'))
                print(f"Using overridden declination range: {dec_min} to {dec_max} deg")
            except Exception as e:
                print(f"ERROR: Invalid format for --dec-range-deg '{dec_range_override}'. Use MIN:MAX. {e}")
                sys.exit(1)
        else:
            fixed_dec_deg = cal_config.get('fixed_declination_deg', None)
            if fixed_dec_deg is None:
                print("ERROR: 'calibration:fixed_declination_deg' must be set in config.")
                sys.exit(1)
            # Use approximate beam size (e.g., 3 deg FWHM -> +/- 1.5 deg range)
            beam_radius_deg = cal_config.get('bcal_search_beam_radius_deg', 1.5)
            dec_min = fixed_dec_deg - beam_radius_deg
            dec_max = fixed_dec_deg + beam_radius_deg
            print(f"Using declination range from config: {dec_min:.2f} to {dec_max:.2f} deg (Center {fixed_dec_deg:.2f} +/- {beam_radius_deg:.2f})")


        # Minimum Flux
        min_flux_jy = min_flux_override or cal_config.get('bcal_min_flux_jy', 5.0) # Default 5 Jy
        min_flux_mjy = min_flux_jy * 1000.0
        print(f"Using minimum flux density threshold: {min_flux_jy} Jy ({min_flux_mjy} mJy)")

        # Maximum Flux (optional, avoid extremely bright/resolved sources like Cas A, Cyg A if needed)
        max_flux_jy = cal_config.get('bcal_max_flux_jy', 100.0) # e.g., avoid > 100 Jy sources
        max_flux_mjy = max_flux_jy * 1000.0
        print(f"Using maximum flux density threshold: {max_flux_jy} Jy ({max_flux_mjy} mJy)")

        # NVSS Catalog Details (can be made configurable later if needed)
        nvss_code = 'VIII/65/nvss'
        nvss_flux_col = 'S1.4'
        nvss_ra_col = 'RAJ2000' # HMS format
        nvss_dec_col = 'DEJ2000' # DMS format
        nvss_name_col = 'NVSS' # NVSS designation

    except KeyError as e:
        print(f"ERROR: Missing required key in configuration file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error processing configuration: {e}")
        sys.exit(1)


    # --- Query Vizier (NVSS) ---
    print(f"\nQuerying Vizier ({nvss_code}) for potential calibrators...")
    # Define columns to retrieve explicitly
    # Need RA, Dec, Flux, Name, maybe error flags or Maj/Min axis for compactness check?
    # Let's get common ones: Name, RA, Dec, Flux, MajAxis, MinAxis, PA
    vizier_columns = [nvss_name_col, nvss_ra_col, nvss_dec_col, nvss_flux_col, 'MajAxis', 'MinAxis', 'PA', 'Field']

    # Construct constraint string for Vizier query
    # Query full RA range, filter by Dec and Flux
    constraints = {
        nvss_dec_col: f'{dec_min}..{dec_max}', # Vizier range syntax
        nvss_flux_col: f'>{min_flux_mjy}',      # Flux in mJy
        # Add constraint to filter out very bright sources if needed
        # nvss_flux_col: f'{min_flux_mjy} .. {max_flux_mjy}'
    }
    # Add morphology filter if desired (e.g., NVSS 'Type' == 'S' for point source - check if available)

    try:
        print(f"Applying constraints: {constraints}")
        result_table = Vizier(columns=vizier_columns).query_constraints(
            catalog=nvss_code,
            cache=True, # Use local cache if available
            **constraints
        )[0] # Get the first table from the result list

        print(f"Found {len(result_table)} sources matching criteria.")

        if len(result_table) == 0:
            print("No suitable BPCAL candidates found with current criteria.")
            # Create empty file? Or exit? Let's create empty for now.
            open(output_file, 'w').close()
            print(f"Created empty catalog file: {output_file}")
            return

    except Exception as e:
        print(f"ERROR: Vizier query failed: {e}")
        sys.exit(1)


    # --- Format and Write CSV ---
    print(f"Formatting and writing results to: {output_file}")
    header = ['name', 'ra_str', 'dec_str', 'flux_jy', 'epoch', 'maj_axis_arcsec', 'min_axis_arcsec', 'pa_deg']
    rows_written = 0
    try:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header) # Write header

            for row in result_table:
                 # Construct name (prefer NVSS name, fallback to coord-based)
                 name = f"NVSS_{row[nvss_name_col]}" if row[nvss_name_col] else f"NVSS_{row[nvss_ra_col]}_{row[nvss_dec_col]}".replace(':','').replace('.','p').replace('+','p').replace('-','m')
                 ra_str = row[nvss_ra_col]
                 dec_str = row[nvss_dec_col]
                 flux_mjy = row[nvss_flux_col]
                 flux_jy = flux_mjy / 1000.0
                 epoch = 'J2000' # NVSS coordinates are J2000

                 # Handle potentially masked shape parameters
                 maj_axis = row['MajAxis'] if not hasattr(row['MajAxis'],'mask') or not row['MajAxis'].mask else np.nan
                 min_axis = row['MinAxis'] if not hasattr(row['MinAxis'],'mask') or not row['MinAxis'].mask else np.nan
                 pa_deg = row['PA'] if not hasattr(row['PA'],'mask') or not row['PA'].mask else np.nan

                 # Optional: Add compactness check here?
                 # e.g., if maj_axis > threshold, skip? NVSS beam is 45", so check relative to that.
                 # Point sources often have MajAxis==MinAxis==45.0 or slightly larger.
                 # Skip sources much larger than the beam? E.g. MajAxis > 60?

                 writer.writerow([
                     name,
                     ra_str,   # Keep string format from Vizier (HMS/DMS)
                     dec_str,
                     f"{flux_jy:.4f}",
                     epoch,
                     f"{maj_axis:.2f}" if np.isfinite(maj_axis) else "",
                     f"{min_axis:.2f}" if np.isfinite(min_axis) else "",
                     f"{pa_deg:.1f}" if np.isfinite(pa_deg) else ""
                 ])
                 rows_written += 1

        print(f"Successfully wrote {rows_written} calibrator candidates to {output_file}")

    except Exception as e:
        print(f"ERROR: Failed to write CSV file {output_file}: {e}")
        # Clean up potentially partial file
        if os.path.exists(output_file): os.remove(output_file)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Bandpass Calibrator Candidate Catalog for DSA-110 Pipeline from NVSS.")
    parser.add_argument("-c", "--config", required=True, help="Path to the main pipeline YAML config file.")
    parser.add_argument("-o", "--output-file", default=None, help="Override output CSV file path (default: path from config).")
    parser.add_argument("--min-flux", type=float, default=None, help="Override minimum flux density in Jy (default: value from config).")
    parser.add_argument("--dec-range-deg", default=None, help="Override declination range 'MIN:MAX' in degrees (default: range from config).")

    args = parser.parse_args()

    generate_catalog(
        config_path=args.config,
        output_file_override=args.output_file,
        min_flux_override=args.min_flux,
        dec_range_override=args.dec_range_deg
    )
    print("Catalog generation finished.")