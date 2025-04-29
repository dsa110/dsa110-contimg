import os
import numpy as np
from shutil import rmtree
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u
from casatools import imager, msmetadata
from casatasks import exportfits, casalog

def image_skymodel(basepath, msfile, fieldname, nvss_catalog, top_n=10, nx=600, ny=600, cellx='24arcsec', celly='24arcsec', mode='mfs', phasecenter=None):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))
    
    print('Image Parameters')
    print('----------------')
    print(f'nx, ny: {nx, ny}')
    print(f'cellx, celly: {cellx, celly}')
    print(f'mode: {mode}')

    # Generate strings for filenames
    ra_str = f"{msfile.split('_')[1][2:5]}p{msfile.split('_')[1][6:9]}"
    dec_str = f"{msfile.split('_')[2][4:6]}p{msfile.split('_')[2][7:8]}"
    clfile = f'nvss_top{top_n}_{ra_str}_{dec_str}.cl'
    cllabel = clfile.split('.')[0]

    if phasecenter is None:
        # Open the measurement set
        msmd = msmetadata()
        msmd.open(os.path.join(basepath, msfile))

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

    # Create an imager tool instance
    im = imager()

    # Open your Measurement Set (any MS with correct coordinates,
    # but we won't really use the data, just the coordinate frame)
    print(f'MS Selected: {os.path.join(basepath, msfile)}')

    im.open(os.path.join(basepath, msfile))

    # Select the central field
    im.selectvis(os.path.join(basepath, msfile), field=fieldname, spw='*')

    # Define the image geometry: size, cell size, phasecenter, etc.
    # Adjust nx, ny, cell, etc. to fit the region of interest
    im.defineimage(nx=nx, ny=ny,
                cellx=cellx, celly=celly,
                mode=mode,
                phasecenter=phasecenter
                # or use imadvise or real MS coords
                )

    # "Fourier transform" the component list only (ignore data)
    im.ft(complist=f'{os.path.join(basepath, clfile)}')

    # Make an image of this model
    im.makeimage(type='model', image=f'{os.path.join(basepath, cllabel)}.image')

    # Clean up
    im.close()
    im.done()

    if os.path.exists(f'{os.path.join(basepath, cllabel)}.image.fits'):
        os.remove(f'{os.path.join(basepath, cllabel)}.image.fits')
    
    exportfits(f'{os.path.join(basepath, cllabel)}.image', f'{os.path.join(basepath, cllabel)}.image.fits')

    fits_file = f'{os.path.join(basepath, cllabel)}.image.fits'
    hdu = fits.open(fits_file)[0]
    freq_val = hdu.header['CRVAL3']  # Central frequency (e.g., 1.404882070235e+09 Hz)
    stokes_val = hdu.header['CRVAL4']  # Default Stokes parameter (e.g., 1)
    wcs = WCS(hdu.header)

    slices = (0, 0)  # Adjust this based on your FITS file (e.g., for time or frequency)
    wcs_2d = WCS(hdu.header, naxis=2)

    # Load NVSS catalog
    catalog = nvss_catalog
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

    return wcs_2d_coords_x, wcs_2d_coords_y, phasecenter