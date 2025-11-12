import os
import sys
import json
import numpy as np
import pandas as pd
import importlib # type: ignore
from shutil import rmtree, copy, copytree
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib import rcParams
from matplotlib.ticker import ScalarFormatter

rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['DejaVu Serif']
rcParams['mathtext.fontset'] = 'dejavuserif'
rcParams['font.size'] = 30
rcParams['axes.formatter.use_mathtext'] = True
rcParams['axes.unicode_minus'] = True
rcParams['mathtext.default'] = 'regular'
rcParams['text.usetex'] = False

from astropy.coordinates import SkyCoord, match_coordinates_sky
from astropy.visualization import (PercentileInterval, LogStretch, PowerStretch, ManualInterval, ZScaleInterval, ImageNormalize)
from astroquery.vizier import Vizier # type: ignore
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import skycoord_to_pixel
import astropy.units as u

from casatasks import immath, listobs, split, clearcal, delmod, rmtables, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, fixvis, phaseshift, casalog, mstransform, exportfits
from casatools import componentlist, msmetadata, imager, ms, table

def measure_relative_fluxes(msfile,
                            basepath,
                            clean_imagename,
                            pbfile,
                            print_results=False):
    
    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))

    # Open the measurement set
    msmd = msmetadata()
    msmd.open(os.path.join(basepath, 'msfiles', 'avg', msfile))

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
    phase_centers_deg = [(np.degrees(ra), np.degrees(dec)) for ra, dec in phase_centers]

    # Calculate the geometric mean center (central coordinate)
    center_ra = np.mean([coord[0] for coord in phase_centers_deg])
    center_dec = np.mean([coord[1] for coord in phase_centers_deg])

    # Find the closest field to the geometric center
    center_coord = SkyCoord(center_ra, center_dec, unit='deg')
    field_coords = SkyCoord([coord[0] for coord in phase_centers_deg],
                            [coord[1] for coord in phase_centers_deg],
                            unit='deg')
    separations = center_coord.separation(field_coords)

    # Get the field ID closest to the central coordinate
    center_field_id = np.argmin(separations.arcsec)

    print(f"Total fields: {num_fields}")
    print(f"Geometric center: RA = {center_ra:.6f} deg, Dec = {center_dec:.6f} deg")
    print(f"Central field ID (closest to center): {center_field_id}")

    ra_values = [coord[0] for coord in phase_centers_deg]
    dec_values = [coord[1] for coord in phase_centers_deg]
    min_ra, max_ra = min(ra_values), max(ra_values)
    min_dec, max_dec = min(dec_values), max(dec_values)

    # Calculate angular extent
    ra_extent = max_ra - min_ra
    dec_extent = max_dec - min_dec

    # Add primary beam size (optional)
    # Assume observing frequency = 1.4 GHz and dish diameter = 25 m (VLA example)
    frequency_hz = 1.28e9  # Hz
    dish_diameter_m = 4.65  # meters
    primary_beam_fwhm_deg = (1.02 * (3e8 / frequency_hz) / dish_diameter_m) * (180 / np.pi)

    # Adjust RA and Dec bounds by primary beam size
    min_ra_adjusted = min_ra - primary_beam_fwhm_deg / 2
    max_ra_adjusted = max_ra + primary_beam_fwhm_deg / 2
    min_dec_adjusted = min_dec - primary_beam_fwhm_deg / 2
    max_dec_adjusted = max_dec + primary_beam_fwhm_deg / 2

    print(f"Field Extent (Degrees):")
    print(f"  RA:  {min_ra:.6f} to {max_ra:.6f} (Extent: {ra_extent:.6f} degrees)")
    print(f"  Dec: {min_dec:.6f} to {max_dec:.6f} (Extent: {dec_extent:.6f} degrees)")

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
    nvss_cat_code = "VIII/65/nvss"  # NVSS catalog

    # Query the NVSS catalog
    print(f"Querying {nvss_cat_code} ...")
    target_coord = SkyCoord(ra_deg, dec_deg, unit='deg')
    Vizier.ROW_LIMIT = -1  # no row limit
    Vizier.columns = ["*"]  # retrieve all columns


    while True:
        try:
            nvss_result = Vizier.query_region(
                target_coord,
                width=f"{search_width}d",
                height=f"{search_height}d",
                catalog=nvss_cat_code,
                frame='icrs'
            )
            break
        except Exception as e:
            print(f"An error occurred: {e}")

    nvss_catalog = nvss_result[0].to_pandas()

    catalog = nvss_catalog #pd.read_csv("nvss_catalog.csv")
    catalog = catalog[catalog['S1.4'] > 10]  # Filter sources brighter than 10 mJy

    # Function to parse NVSS RA/Dec strings into SkyCoord
    def parse_nvss_coords(ra_str, dec_str):
        # Parse RA (format: 'HH MM SS.SS')
        ra_hms = ra_str.split()
        ra = (float(ra_hms[0]) + float(ra_hms[1])/60 + float(ra_hms[2])/3600) * 15  # Convert to degrees
        # Parse Dec (format: '±DD MM SS.S')
        dec_dms = dec_str.split()
        dec_sign = -1 if dec_dms[0].startswith('-') else 1
        dec = dec_sign * (abs(float(dec_dms[0])) + float(dec_dms[1])/60 + float(dec_dms[2])/3600)
        return SkyCoord(ra, dec, unit='deg')

    # Precompute coordinates for all NVSS sources
    catalog['coords'] = catalog.apply(
        lambda row: parse_nvss_coords(row['RAJ2000'], row['DEJ2000']), axis=1
    )

    # Open the primary beam image ONCE before processing sources
    ia = image()
    try:
        ia.open(f'{pbfile}')  # Replace with actual PB filename (e.g., 'nvss_top_clean.pb')
    except Exception as e:  
        print(f"Error opening PB image: {str(e)}")
        exit()

    results = []
    for i, src in catalog.iterrows():
        coord = src['coords']
        # Generate region string from SkyCoord
        region_str = f"circle[[{coord.ra.to_string('hms', precision=2)}," \
                    f"{coord.dec.to_string('dms', precision=1)}], 30arcsec]"
        
        try:
            # Get PEAK flux (using 'max' statistic)
            statres = imstat(imagename=f'{clean_imagename}', region=region_str)
            if statres and 'max' in statres:
                peak_flux = statres['max'][0] * 1e3  # Convert to mJy
                flux_ratio = peak_flux / src['S1.4']
            else:
                peak_flux = flux_ratio = None
        except RuntimeError:
            peak_flux = flux_ratio = None
        
        results.append((i, src['NVSS'], src['S1.4'], peak_flux, flux_ratio, src['coords']))

    # Convert results to DataFrame
    flux_df = pd.DataFrame(results, 
        columns=['index','name','flux_nvss','peak_flux','flux_ratio','coords'])

    # Calculate relative fluxes using 10 nearest neighbors
    relative_fluxes = []
    for _, target_row in flux_df.iterrows():
        # Calculate separations to all sources
        separations = target_row['coords'].separation(flux_df['coords']).arcsec
        
        # Find indices of 10 nearest non-target sources
        nearest_idx = np.argsort(separations)[1:11]  # Exclude self (index 0)
        
        # Get valid reference fluxes
        ref_fluxes = flux_df.iloc[nearest_idx]['peak_flux'].dropna()
        median_ref = np.median(ref_fluxes) if len(ref_fluxes) > 0 else np.nan
        
        # Calculate relative flux
        if target_row['peak_flux'] and median_ref and median_ref != 0:
            rel_flux = target_row['peak_flux'] / median_ref
        else:
            rel_flux = np.nan
        
        relative_fluxes.append(rel_flux)

    flux_df['relative_flux'] = relative_fluxes

    # Print results with relative fluxes
    if print_results:
        for _, row in flux_df.iterrows():
            print(f"{row['index']} {row['name']} | NVSS: {row['flux_nvss']:.1f} mJy | "
                f"Measured: {row['peak_flux']:.1f} mJy | Ratio: {row['flux_ratio']:.2f} | "
                f"Rel Flux: {row['relative_flux']:.2f}")
            
    # Convert SkyCoord objects to serializable format
    def coord_to_dict(coord):
        if isinstance(coord, SkyCoord):
            return {
                'ra_deg': coord.ra.deg,
                'dec_deg': coord.dec.deg,
                'ra_str': coord.ra.to_string(unit='hour', precision=2),
                'dec_str': coord.dec.to_string(unit='deg', precision=2)
            }
        return coord

    # Convert DataFrame to dictionary with coordinate handling
    results_dict = flux_df.applymap(coord_to_dict).to_dict(orient='records')

    # Custom serialization for numpy types and other special cases
    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.float32, np.float64)):
                return float(obj)
            if isinstance(obj, np.int64):
                return int(obj)
            return super().default(obj)

    # Save to JSON file
    with open('relative_photometry_results.json', 'w') as f:
        json.dump(results_dict, f, 
                indent=2, 
                cls=CustomEncoder,
                ensure_ascii=False)

    print("Results saved to relative_photometry_results.json")

    return results_dict