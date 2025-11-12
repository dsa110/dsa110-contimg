import os
import numpy as np
from shutil import rmtree, copy, copytree

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib import rcParams
from matplotlib.ticker import ScalarFormatter

from astropy.coordinates import SkyCoord, Angle, match_coordinates_sky
from astroquery.vizier import Vizier # type: ignore
from astropy.visualization import (PercentileInterval, LogStretch, PowerStretch, ManualInterval, ZScaleInterval, ImageNormalize)
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u


from casatasks import listobs, split, clearcal, delmod, rmtables, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, fixvis, phaseshift, casalog, mstransform, exportfits
from casatools import componentlist, imager, ms, table, msmetadata

def make_skymodel(msfile, basepath, sourcename=None, cfieldid=None, top_n=50, pbfrac=0.25):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))

    nvss_catalog = None
    clfile = None
    jname = None
    phasecenter = None
    center_ra = None
    center_dec = None

    if cfieldid is None:

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
        rad2deg = lambda x: ((x * 180.0 / np.pi) + 360) % 360  
        phase_centers_deg = [(rad2deg(ra), rad2deg(dec)) for ra, dec in phase_centers]
        #phase_centers_deg = (rad2deg(ra), rad2deg(dec))

        # Calculate the geometric mean center (central coordinate)
        center_ra = np.mean([coord[0] for coord in phase_centers_deg])
        center_dec = np.mean([coord[1] for coord in phase_centers_deg])

        print(f"Total fields: {num_fields}")
        print(f"Geometric center: RA = {center_ra:.6f} deg, Dec = {center_dec:.6f} deg")
        print('\n')

        # Close the msmd tool
        msmd.done()
    
    else:
        
        # Open the measurement set
        msmd = msmetadata()
        msmd.open(os.path.join(basepath, 'msfiles', 'avg', msfile))

        #fieldnames = np.array(msmd.fieldnames())
        #fieldid = np.where(fieldnames == fieldname)[0][0]

        # Retrieve phase centers for specified fields
        pc = msmd.phasecenter(cfieldid)
        ra = pc['m0']['value']  # RA in radians
        dec = pc['m1']['value']  # Dec in radians

        # Convert to degrees for easier interpretation
        rad2deg = lambda x: ((x * 180.0 / np.pi) + 360) % 360  
        center_ra = rad2deg(ra)
        center_dec = rad2deg(dec)

        # Close the msmd tool
        msmd.done()

    if sourcename is not None:

        print(f'Making a skymodel of just one source as a calibrator: {sourcename}')
        print('\n')

        clfile = f'{sourcename}.cl'
        cllabel = clfile.split('.')[0]

        #if os.path.exists(os.path.join(basepath, 'skymodels', clfile)):
        #    print(f"File '{clfile}' already exists. Skipping component creation.")
        #    print('\n')

        if os.path.exists(os.path.join(basepath, 'skymodels', clfile)):
            print(f"Deleting existing file {clfile}")
            rmtree(os.path.join(basepath, 'skymodels', clfile))

        print(f"Creating new component list '{clfile}'...")
        print('\n')
        cl = componentlist()

        # Query NVSS
        while True:
            try:
                nvss_result = Vizier.query_object(sourcename, catalog="VIII/65/nvss")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
        
        if nvss_result is None or len(nvss_result) == 0:
            print("Specified source was not found in the NVSS catalog.")
            print('\n')
        
        else:
            nvss_catalog = nvss_result[0]

            # Extract RA, Dec, Flux from NVSS
            ra_list = [source['RAJ2000'] for i, source in enumerate(nvss_catalog)]
            ra = ra_list[0]
            dec_list = [source['DEJ2000'] for i, source in enumerate(nvss_catalog)]
            dec = dec_list[0]
            flux_nvss_list = [source['S1.4'] for i, source in enumerate(nvss_catalog)]
            flux_nvss = flux_nvss_list[0] / 1000  # Convert mJy to Jy

            # Parse ra, dec to CASA-readable sexagesimal
            ra_parts = ra.split()
            dec_parts = dec.split()

            ra_fixed = f"{ra_parts[0]}h{ra_parts[1]}m{ra_parts[2]}s"
            dec_fixed = f"{dec_parts[0]}d{dec_parts[1]}m{dec_parts[2]}s"

            jname = f"J2000 {ra_fixed} {dec_fixed}"

            print('________________________________________________________________________________________')
            print(f'Calibrator Coordinates (J2000): {jname}')
            print(f'Calibrator Flux: {flux_nvss} Jy')
            print('\n')

            # Initialize float fallback values
            maj_val = 15.0
            min_val = 15.0
            pa_val  = 0.0

            if 'MajAxis' in nvss_catalog.colnames:
                raw_maj = nvss_catalog['MajAxis']
                if np.isnan(raw_maj) or np.isinf(raw_maj):
                    maj_val = 15.0  # fallback
                else:
                    maj_val = float(raw_maj) 

            if 'MinAxis' in nvss_catalog.colnames:
                raw_min = nvss_catalog['MinAxis']
                if np.isnan(raw_min) or np.isinf(raw_min):
                    min_val = 15.0
                else:
                    min_val = float(raw_min)

            if 'PA' in nvss_catalog.colnames:
                raw_pa = nvss_catalog['PA']
                if np.isnan(raw_pa) or np.isinf(raw_pa):
                    pa_val = 0.0
                else:
                    pa_val = float(raw_pa)

            if maj_val < min_val:
                temp = maj_val
                maj_val = min_val
                min_val = temp
                pa_val += 90.0

            major_axis_str = f"{maj_val}arcsec"
            minor_axis_str = f"{min_val}arcsec"
            pa_str         = f"{pa_val}deg"

            # Set the spectral index to be constant
            stype = 'Constant'
            idx_val = None

            print('Making component list...')
            print('\n')

            cl.addcomponent(
                dir=jname,
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

            cl.rename(os.path.join(basepath, 'skymodels', clfile))
            cl.close()
            print(f"Component list {clfile} created successfully with only {sourcename}")
            print('\n')

        print('NVSS Catalog:')
        print(f'{nvss_catalog}')
        print('\n')
        print(f'Component List: {clfile}')
        print('\n')
        print(f'J Name: {jname}')
        print('\n')

        return nvss_catalog, clfile, jname

    else:

        # Generate strings for filenames
        ra_str = f"{msfile.split('_')[1][2:5]}p{msfile.split('_')[1][6:9]}"
        dec_str = f"{msfile.split('_')[2][4:6]}p{msfile.split('_')[2][7:8]}"
        clfile = f'nvss_top{top_n}_{ra_str}_{dec_str}.cl'
        cllabel = clfile.split('.')[0]
        
        # Add primary beam size (optional)
        # Assume observing frequency = 1.4 GHz and dish diameter = 25 m (VLA example)
        frequency_hz = 1.4e9  # Hz
        dish_diameter_m = 4.65  # meters
        primary_beam_fwhm_deg = (1.02 * (3e8 / frequency_hz) / dish_diameter_m) * (180 / np.pi)

        # Adjust RA and Dec bounds by primary beam size
        min_ra_adjusted = center_ra - pbfrac*primary_beam_fwhm_deg
        max_ra_adjusted = center_ra + pbfrac*primary_beam_fwhm_deg
        min_dec_adjusted = center_dec - pbfrac*primary_beam_fwhm_deg
        max_dec_adjusted = center_dec + pbfrac*primary_beam_fwhm_deg

        print(f"Primary Beam FWHM ({primary_beam_fwhm_deg:.3f} degrees):")
        print(f"  RA:  {min_ra_adjusted:.6f} to {max_ra_adjusted:.6f}")
        print(f"  Dec: {min_dec_adjusted:.6f} to {max_dec_adjusted:.6f}")
        print('\n')

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
        print('\n')
        target_coord = SkyCoord(ra_deg, dec_deg, unit='deg')
        Vizier.ROW_LIMIT = -1  # no row limit
        Vizier.columns = ["*"]  # retrieve all columns

        while True:
            try:
                nvss_result = Vizier.query_region(
                    target_coord,
                    #adius=f"{search_radius}m",
                    width=f"{search_width}d",
                    height=f"{search_height}d",
                    catalog=nvss_cat_code,
                    frame='icrs'
                )
                break
            except Exception as e:
                print(f"An error occurred: {e}")

        nvss_catalog = nvss_result[0]
        #print(nvss_result[0])

        # Check for results
        if nvss_result is None or len(nvss_result) == 0:
            print("No sources found in the NVSS catalog.")
            print('\n')
        else:
            nvss_table = nvss_result[0]
            if nvss_flux_col not in nvss_table.colnames:
                print(f"Flux column '{nvss_flux_col}' not found in the NVSS catalog.")
                print('\n')
            else:
                # Filter and sort NVSS sources by flux
                nvss_table = nvss_table[~nvss_table[nvss_flux_col].mask]  # Remove masked (NaN) values
                nvss_sorted_table = nvss_table[np.argsort(nvss_table[nvss_flux_col].data)[::-1]]  # Sort descending by flux
                print(f'Found {len(nvss_sorted_table)} sources in the field!')
                print('\n')
                nvss_top_sources = nvss_sorted_table[:top_n]
                #print(nvss_top_sources)

                # Query the TGSS catalog for cross-matching
                print(f"Querying {tgss_cat_code} ...")
                print('\n')
                while True:
                    try:
                        tgss_result = Vizier.query_region(
                            target_coord,
                            #radius=f"{search_radius}m",
                            width=f"{search_width}d",
                            height=f"{search_height}d",
                            catalog=tgss_cat_code
                        )
                        break
                    except Exception as e:
                        print(f"An error occurred: {e}")

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
                    print('\n')

                # Create or append to component list
                if os.path.exists(os.path.join(basepath, 'skymodels', clfile)):
                    print(f"File '{clfile}' already exists. Skipping component creation.")
                    print('\n')
                else:
                    print(f"Creating new component list '{clfile}'...")
                    print('\n')
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

                        # Initialize float fallback values
                        maj_val = 15.0
                        min_val = 15.0
                        pa_val  = 0.0

                        if 'MajAxis' in source.colnames:
                            raw_maj = source['MajAxis']
                            if np.isnan(raw_maj) or np.isinf(raw_maj):
                                maj_val = 15.0  # fallback
                            else:
                                maj_val = float(raw_maj) 

                        if 'MinAxis' in source.colnames:
                            raw_min = source['MinAxis']
                            if np.isnan(raw_min) or np.isinf(raw_min):
                                min_val = 15.0
                            else:
                                min_val = float(raw_min)

                        if 'PA' in source.colnames:
                            raw_pa = source['PA']
                            if np.isnan(raw_pa) or np.isinf(raw_pa):
                                pa_val = 0.0
                            else:
                                pa_val = float(raw_pa)

                        if maj_val < min_val:
                            temp = maj_val
                            maj_val = min_val
                            min_val = temp
                            pa_val += 90.0

                        major_axis_str = f"{maj_val}arcsec"
                        minor_axis_str = f"{min_val}arcsec"
                        pa_str         = f"{pa_val}deg"

                        # Decide the spectral index or constant
                        if spectral_index is not None and np.isfinite(spectral_index):
                            stype = 'SpectralIndex'
                            idx_val = [spectral_index]
                        else:
                            stype = 'Constant'
                            idx_val = None

                        # Parse ra, dec to CASA-readable sexagesimal
                        ra_parts = ra.split()
                        dec_parts = dec.split()

                        ra_fixed = f"{ra_parts[0]}h{ra_parts[1]}m{ra_parts[2]}s"
                        dec_fixed = f"{dec_parts[0]}d{dec_parts[1]}m{dec_parts[2]}s"

                        dir_str = f"J2000 {ra_fixed} {dec_fixed}"
                        
                        #print(f'Coord: {dir_str}')
                        #print(f'Maj Axis: {major_axis_str}')
                        #print(f'Min Axis: {minor_axis_str}')

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

                    cl.rename(os.path.join(basepath, 'skymodels', clfile))
                    cl.close()
                    print(f"Component list '{clfile}' created successfully with {len(nvss_top_sources)} sources.")
                    print('\n')

        print('NVSS Catalog:')
        print(f'{nvss_catalog}')
        print('\n')
        print(f'Component List: {clfile}')
        print('\n')

        return nvss_catalog, clfile

def image_skymodel(msfile,
                   basepath, 
                   nvss_catalog,
                   clfile=None, 
                   cfieldid=11, 
                   top_n=50, 
                   nx=4800, 
                   ny=4800, 
                   cellx='3arcsec', 
                   celly='3arcsec', 
                   mode='mfs', 
                   phasecenter=None, 
                   make_image=True):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))
    
    print('Image Parameters')
    print('----------------')
    print(f'nx, ny: {nx, ny}')
    print(f'cellx, celly: {cellx, celly}')
    print(f'mode: {mode}')
    print('\n')

    if clfile is None:
        # Generate strings for filenames
        ra_str = f"{msfile.split('_')[1][2:5]}p{msfile.split('_')[1][6:9]}"
        dec_str = f"{msfile.split('_')[2][4:6]}p{msfile.split('_')[2][7:8]}"
        clfile = f'nvss_top{top_n}_{ra_str}_{dec_str}.cl'
        
    cllabel = clfile.split('.')[0]

    if phasecenter is None:
        # Open the measurement set
        msmd = msmetadata()
        msmd.open(os.path.join(basepath, 'msfiles', 'avg', msfile))

        # Get the total number of fields
        num_fields = msmd.nfields()
        field_names = msmd.fieldnames()

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
        center_ra = np.mean([coord[0] for coord in phase_centers_deg])
        center_dec = np.mean([coord[1] for coord in phase_centers_deg])

        # Find the closest field to the geometric center
        center_coord = SkyCoord(center_ra, center_dec, unit='deg')

        ra_fixed = f'{round(center_coord.ra.hms.h)}h{round(center_coord.ra.hms.m)}m{center_coord.ra.hms.s}s'
        dec_fixed = f'{round(center_coord.dec.dms.d)}d{round(center_coord.dec.dms.m)}m{center_coord.dec.dms.s}s'

        phasecenter = f"J2000 {ra_fixed} {dec_fixed}"
    else:
        phasecenter = phasecenter

    print(f'Phase Center: {phasecenter}')
    print('\n')

    # Create an imager tool instance
    im = imager()

    # Open your Measurement Set (any MS with correct coordinates,
    # but we won't really use the data, just the coordinate frame)
    print(f"MS Selected: {os.path.join(basepath, 'msfiles', 'avg', msfile)}")
    print('\n')

    im.open(os.path.join(basepath, 'msfiles', 'avg', msfile))

    # Select the central field
    im.selectvis(os.path.join(basepath, 'msfiles', 'avg', msfile), field=cfieldid, spw='*')

    # Define the image geometry: size, cell size, phasecenter, etc.
    # Adjust nx, ny, cell, etc. to fit the region of interest
    im.defineimage(nx=nx, ny=ny,
                   cellx=cellx, celly=celly,
                   mode=mode,
                   phasecenter=phasecenter
                   # or use imadvise or real MS coords
                   )

    # "Fourier transform" the component list only (ignore data)
    im.ft(complist=f"{os.path.join(basepath, 'skymodels', clfile)}")

    # Make an image of this model
    skymodel_image = f"{os.path.join(basepath, 'skymodels', cllabel)}.image"
    print(f'Sky model image name is located at {skymodel_image}')
    im.makeimage(type='model', image=skymodel_image)

    # Clean up
    im.close()
    im.done()

    if os.path.exists(f"{os.path.join(basepath, 'skymodels', cllabel)}.image.fits"):
        os.remove(f"{os.path.join(basepath, 'skymodels', cllabel)}.image.fits")
    
    exportfits(f"{os.path.join(basepath, 'skymodels', cllabel)}.image", f"{os.path.join(basepath, 'skymodels', cllabel)}.image.fits")

    fits_file = f"{os.path.join(basepath, 'skymodels', cllabel)}.image.fits"
    hdu = fits.open(fits_file)[0]
    freq_val = hdu.header['CRVAL3']  # Central frequency (e.g., 1.404882070235e+09 Hz)
    stokes_val = hdu.header['CRVAL4']  # Default Stokes parameter (e.g., 1)
    wcs = WCS(hdu.header)

    slices = (0, 0)  # Adjust this based on your FITS file (e.g., for time or frequency)
    wcs_2d = WCS(hdu.header, naxis=2)

    # Load NVSS catalog
    catalog = nvss_catalog

    bandpass_calibrator=False

    if len(catalog) == 1:
        nvss_flux_col = "S1.4"  # NVSS flux column
        catalog = catalog[~catalog[nvss_flux_col].mask]  # Remove masked (NaN) values
        catalog_top_sources = catalog
        bandpass_calibrator = True

    else:
        nvss_flux_col = "S1.4"  # NVSS flux column
        catalog = catalog[~catalog[nvss_flux_col].mask]  # Remove masked (NaN) values
        catalog_sorted_table = catalog[np.argsort(catalog[nvss_flux_col].data)[::-1]]  # Sort descending by flux
        catalog_top_sources = catalog_sorted_table[:top_n]
    #catalog = catalog[catalog['S1.4'] > 10]  # Filter sources brighter than 10 mJy

    # Convert NVSS RA/Dec to pixel coordinates
    nvss_coords = SkyCoord(ra=catalog_top_sources['RAJ2000'], dec=catalog_top_sources['DEJ2000'], frame='icrs', unit=(u.hourangle, u.deg))

    # Extract RA, Dec, and add constant frequency and Stokes
    ra_deg = nvss_coords.ra.deg
    dec_deg = nvss_coords.dec.deg
    freq_array = [freq_val] * len(ra_deg)  # Repeat frequency for all sources
    stokes_array = [stokes_val] * len(ra_deg)  # Repeat Stokes for all sources

    # Pass all 4 axes to wcs.world_to_pixel
    wcs_2d_coords_x, wcs_2d_coords_y = wcs_2d.world_to_pixel_values(ra_deg, dec_deg)
    nvss_coords_list = list(zip(wcs_2d_coords_x, wcs_2d_coords_y))
    print('\n')
    print(f'Sky model has {len(wcs_2d_coords_x)} sources...')
    print('\n')

    if make_image:
        # Display the FITS image
        fig, ax = plt.subplots(subplot_kw={'projection': wcs_2d}, figsize = (25, 25))
        #norm = ImageNormalize(hdu.data[0, 0, :, :], interval=PercentileInterval(99), stretch=LogStretch())
        norm = ImageNormalize(hdu.data[0, 0, :, :], interval=ZScaleInterval(), stretch=PowerStretch(a=1))
        ax.imshow(hdu.data[0, 0, :, :], cmap='gray_r', norm=norm, origin='lower')

        # Overlay circles around NVSS sources on the FITS image
        for xi, yi in nvss_coords_list:
            circle = Circle((xi, yi), radius=50, edgecolor='red', facecolor='none', lw=0.8, transform=ax.get_transform('pixel'))
            ax.add_patch(circle)

        if bandpass_calibrator:
            cal_ra_deg, cal_dec_deg = nvss_coords.ra.deg[0], nvss_coords.dec.deg[0]
            cal_coord_x, cal_coord_y = wcs_2d.world_to_pixel_values(cal_ra_deg, cal_dec_deg)
            ax.scatter(cal_coord_x, cal_coord_y, marker='*', s=1000, c='red', alpha=0.5, label = 'Bandpass Calibrator')
            ax.legend()

        ax.set_xlabel('RA')
        ax.set_ylabel('Dec')

        # Show the plot
        plt.title('Sky Model with NVSS Sources')
        plt.grid(color='k', ls='dotted')
        fig.savefig(os.path.join(basepath, 'figures', f'{cllabel}_image.pdf'))
        print(f'Sky model figure saved as {f"{cllabel}_image.pdf"}')
        print('\n')

    return phasecenter, nvss_coords_list, skymodel_image