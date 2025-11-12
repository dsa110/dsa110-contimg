import os
import numpy as np
from astropy.coordinates import SkyCoord, Angle, match_coordinates_sky
from astroquery.vizier import Vizier

from casatasks import listobs, clearcal, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, casalog
from casatools import componentlist, msmetadata

# -----------------------
# 1. Component List Step
# -----------------------

# Set path for CASA log files
casalog.setlogfile('/data/jfaber/dsa110-contimg/sandbox/2025-02-14T13-07/multifield/casa_logfile.log')

# Path to the measurement set
basepath = '/data/jfaber/dsa110-contimg/sandbox/2025-02-14T13-07/multifield'
msfile = '2025-02-14T13:07:27_ra224.004_dec+71.742.ms'
top_n = 100  # Number of sources to include in the component list
ra_str = f"{msfile.split('_')[1][2:5]}p{msfile.split('_')[1][6:9]}"
dec_str = f"{msfile.split('_')[2][4:6]}p{msfile.split('_')[2][7:10]}"
clfile = f'nvss_top{top_n}_{ra_str}_{dec_str}.cl'
cllabel = clfile.split('.')[0]

#for ms_path in ms_paths:

# Open the measurement set
msmd = msmetadata()
msmd.open(os.path.join(basepath, msfile))

# Get the total number of fields
num_fields = msmd.nfields()

# Retrieve phase centers for all fields
phase_centers = []
for field_id in range(num_fields):
    pc = msmd.phasecenter(field_id)
    ra = pc['m0']['value']  # RA in radians
    dec = pc['m1']['value']  # Dec in radians
phase_centers.append((ra, dec))

# Convert to degrees for easier interpretation
rad2deg = lambda x: ((x * 180.0 / np.pi) + 360) % 360  
phase_centers_deg = [(rad2deg(ra), rad2deg(dec)) for ra, dec in phase_centers]
#phase_centers_deg = (rad2deg(ra), rad2deg(dec))

# Calculate the geometric mean center (central coordinate)
#center_ra = np.mean([coord[0] for coord in phase_centers_deg])
#center_dec = np.mean([coord[1] for coord in phase_centers_deg])
center_ra = phase_centers_deg[0]
center_dec = phase_centers_deg[1] #np.mean([coord[1] for coord in phase_centers_deg])

# Find the closest field to the geometric center
center_coord = SkyCoord(center_ra, center_dec, unit='deg')
#field_coords = SkyCoord([coord[0] for coord in phase_centers_deg],
#                        [coord[1] for coord in phase_centers_deg],
#                        unit='deg')
#field_coords = SkyCoord(center_ra, center_dec, unit='deg')
#separations = center_coord.separation(field_coords)

# Get the field ID closest to the central coordinate
#center_field_id = np.argmin(separations.arcsec)

print(f"Total fields: {num_fields}")
print(f"Geometric center: RA = {center_ra:.6f} deg, Dec = {center_dec:.6f} deg")
#print(f"Central field ID (closest to center): {center_field_id}")

#ra_values = [coord[0] for coord in phase_centers_deg]
#dec_values = [coord[1] for coord in phase_centers_deg]
#min_ra, max_ra = min(ra_values), max(ra_values)
#min_dec, max_dec = min(dec_values), max(dec_values)

# Calculate angular extent
#ra_extent = max_ra - min_ra
#dec_extent = max_dec - min_dec

# Add primary beam size (optional)
# Assume observing frequency = 1.4 GHz and dish diameter = 25 m (VLA example)
frequency_hz = 1.28e9  # Hz
dish_diameter_m = 4.65  # meters
primary_beam_fwhm_deg = (1.02 * (3e8 / frequency_hz) / dish_diameter_m) * (180 / np.pi)

# Adjust RA and Dec bounds by primary beam size
#min_ra_adjusted = min_ra - primary_beam_fwhm_deg / 2
#max_ra_adjusted = max_ra + primary_beam_fwhm_deg / 2
#min_dec_adjusted = min_dec - primary_beam_fwhm_deg / 2
#max_dec_adjusted = max_dec + primary_beam_fwhm_deg / 2

min_ra_adjusted = center_ra - primary_beam_fwhm_deg / 2
max_ra_adjusted = center_ra + primary_beam_fwhm_deg / 2
min_dec_adjusted = center_dec - primary_beam_fwhm_deg / 2
max_dec_adjusted = center_dec + primary_beam_fwhm_deg / 2

#print(f"Field Extent (Degrees):")
#print(f"  RA:  {min_ra:.6f} to {max_ra:.6f} (Extent: {ra_extent:.6f} degrees)")
#print(f"  Dec: {min_dec:.6f} to {max_dec:.6f} (Extent: {dec_extent:.6f} degrees)")

print(f"\nIncluding Primary Beam FWHM ({primary_beam_fwhm_deg:.3f} degrees):")
print(f"  RA:  {min_ra_adjusted:.6f} to {max_ra_adjusted:.6f}")
print(f"  Dec: {min_dec_adjusted:.6f} to {max_dec_adjusted:.6f}")

# Close the msmd tool
msmd.done()

ra_deg = center_ra
dec_deg = center_dec

#search_radius =  60 # arcminutes
search_width = max_ra_adjusted - min_ra_adjusted # degrees
search_height = max_dec_adjusted - min_dec_adjusted # degrees
nvss_flux_col = "S1.4"  # NVSS flux column
nvss_cat_code = "VIII/65/nvss/"  # NVSS catalog
tgss_flux_col = "Peak_flux"  # TGSS flux column (150 MHz)
tgss_cat_code = "J/other/A+A/598/A78/table3"  # TGSS ADR1 catalog

# Function to calculate spectral index
def calculate_spectral_index(flux_nvss, freq_nvss, flux_tgss, freq_tgss):
    return np.log(flux_nvss / flux_tgss) / np.log(freq_nvss / freq_tgss)

# Query the NVSS catalog
print(f"Querying {nvss_cat_code} ...")
target_coord = SkyCoord(ra_deg, dec_deg, unit='deg')
Vizier.ROW_LIMIT = -1  # no row limit
Vizier.columns = ["*"]  # retrieve all columns

nvss_result = Vizier.query_region(
    target_coord,
    #adius=f"{search_radius}m",
    width=f"{search_width}d",
    height=f"{search_height}d",
    catalog=nvss_cat_code,
    frame='icrs'
)

#print(nvss_result[0])

# Check for results
if nvss_result is None or len(nvss_result) == 0:
    print("No sources found in the NVSS catalog.")
else:
    nvss_table = nvss_result[0]
    if nvss_flux_col not in nvss_table.colnames:
        print(f"Flux column '{nvss_flux_col}' not found in the NVSS catalog.")
    else:
        # Filter and sort NVSS sources by flux
        nvss_table = nvss_table[~nvss_table[nvss_flux_col].mask]  # Remove masked (NaN) values
        nvss_sorted_table = nvss_table[np.argsort(nvss_table[nvss_flux_col].data)[::-1]]  # Sort descending by flux
        nvss_top_sources = nvss_sorted_table[:top_n]

        print(nvss_top_sources)

        # Query the TGSS catalog for cross-matching
        print(f"Querying {tgss_cat_code} ...")
        tgss_result = Vizier.query_region(
            target_coord,
            #radius=f"{search_radius}m",
            width=f"{search_width}d",
            height=f"{search_height}d",
            catalog=tgss_cat_code
        )

        tgss_available = tgss_result is not None and len(tgss_result) > 0

        if tgss_available:
            tgss_table = tgss_result[0]
            tgss_coords = SkyCoord(tgss_table['RAJ2000'], tgss_table['DEJ2000'], unit='deg')
            nvss_coords = SkyCoord(nvss_top_sources['RAJ2000'], nvss_top_sources['DEJ2000'], unit='deg')

            # Cross-match NVSS with TGSS
            idx, d2d, _ = match_coordinates_sky(nvss_coords, tgss_coords)
            matched_tgss = tgss_table[idx]
        else:
            print("No sources found in the TGSS ADR1 catalog.")

        # Create or append to component list
        if os.path.exists(os.path.join(basepath, clfile)):
            print(f"File '{clfile}' already exists. Skipping component creation.")
        else:
            print(f"Creating new component list '{clfile}'...")
            cl = componentlist()

            for i, source in enumerate(nvss_top_sources):
                ra = source['RAJ2000']
                dec = source['DEJ2000']
                flux_nvss = source[nvss_flux_col] / 1000  # Convert mJy to Jy

                if tgss_available and d2d[i].arcsec < 30:  # Match within 30 arcseconds
                    flux_tgss = matched_tgss[tgss_flux_col][i] / 1000.0  # convert to Jy
                    freq_nvss = 1.4e9  # Hz (NVSS frequency)
                    freq_tgss = 150e6  # Hz (TGSS frequency)
                    spectral_index = calculate_spectral_index(flux_nvss, freq_nvss, flux_tgss, freq_tgss)
                else:
                    spectral_index = None  # No spectral index if no match

                #major_axis = source['MajAxis'] if 'MajAxis' in source.colnames else '15arcsec'
                #minor_axis = source['MinAxis'] if 'MinAxis' in source.colnames else '15arcsec'
                #pa = source['PA'] if 'PA' in source.colnames else '0deg'

                #cl.addcomponent(
                #    dir=f'J2000 {ra} {dec}',
                #    flux=flux_nvss,
                #    fluxunit='Jy',
                #    freq='1.4GHz',
                #    shape='Gaussian',
                #    majoraxis=f'{major_axis}arcsec',
                #    minoraxis=f'{minor_axis}arcsec',
                #    positionangle=f'{pa}',
                #    spectrumtype='SpectralIndex' if spectral_index is not None else 'Constant',
                #    index=[spectral_index] if spectral_index is not None else None
                #)

                # Initialize float fallback values
                maj_val = 15.0
                min_val = 15.0
                pa_val  = 0.0

                # 1) Get raw float for MajAxis if present
                if 'MajAxis' in source.colnames:
                    raw_maj = source['MajAxis']
                    if np.isnan(raw_maj) or np.isinf(raw_maj):
                        maj_val = 15.0  # fallback
                    else:
                        maj_val = float(raw_maj)  # ensure it's a Python float
                # else: keep default 15.0

                # 2) Get raw float for MinAxis if present
                if 'MinAxis' in source.colnames:
                    raw_min = source['MinAxis']
                    if np.isnan(raw_min) or np.isinf(raw_min):
                        min_val = 15.0
                    else:
                        min_val = float(raw_min)
                # else: keep default 15.0

                # 3) Get raw float for PA if present
                if 'PA' in source.colnames:
                    raw_pa = source['PA']
                    if np.isnan(raw_pa) or np.isinf(raw_pa):
                        pa_val = 0.0
                    else:
                        pa_val = float(raw_pa)
                # else: keep default 0.0

                # 4) Enforce major >= minor
                #    If not, swap them and shift PA by 90 deg
                if maj_val < min_val:
                    temp = maj_val
                    maj_val = min_val
                    min_val = temp
                    pa_val += 90.0

                # 5) Convert floats to the required strings with units
                major_axis_str = f"{maj_val}arcsec"
                minor_axis_str = f"{min_val}arcsec"
                pa_str         = f"{pa_val}deg"

                # 6) Decide the spectral index or constant
                if spectral_index is not None and np.isfinite(spectral_index):
                    stype = 'SpectralIndex'
                    idx_val = [spectral_index]
                else:
                    stype = 'Constant'
                    idx_val = None

                #dir_val = f"J2000 {ra}deg {dec}deg"

                # Parse ra, dec to CASA-readable sexagesimal
                ra_parts = ra.split()
                dec_parts = dec.split()

                ra_fixed = f"{ra_parts[0]}h{ra_parts[1]}m{ra_parts[2]}s"
                dec_fixed = f"{dec_parts[0]}d{dec_parts[1]}m{dec_parts[2]}s"

                dir_str = f"J2000 {ra_fixed} {dec_fixed}"
                
                print(f'Coord: {dir_str}')
                print(f'Maj Axis: {major_axis_str}')
                print(f'Min Axis: {minor_axis_str}')

                cl.addcomponent(
                    dir=dir_str,
                    flux=flux_nvss,
                    fluxunit='Jy',
                    freq='1.4GHz',
                    shape='Gaussian',
                    majoraxis=major_axis_str,
                    minoraxis=minor_axis_str,
                    positionangle=pa_str,
                    spectrumtype=stype,
                    index=idx_val
                )

            cl.rename(os.path.join(basepath, clfile))
            cl.close()
            print(f"Component list '{clfile}' created successfully with {len(nvss_top_sources)} sources.")