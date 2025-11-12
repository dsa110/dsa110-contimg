import os
import sys
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

sys.path.insert(0, '/data/jfaber/dsa110-contimg/pipeline/calib')
from calib_utils import gen_fieldnames # type: ignore

def image_tclean(msfile, 
                 basepath,
                 phasecenter,
                 nvss_coords,
                 skymodel_image=None,
                 mask_image=None,
                 fields=(0,23),
                 imsize=(4800, 4800), 
                 cell_res='3arcsec', 
                 weighttype='briggs', 
                 niter=10000, 
                 weight=0.5, 
                 uvrange='>1klambda', 
                 imagetype='clean',
                 use_skymodel=False, 
                 use_mask=False,
                 save_fits=True,
                 plot_fits=True):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))

    if use_skymodel:
        startmodel = skymodel_image
    else:
        startmodel = ''

    if use_mask:
        usemask = 'user'
        mask = mask_image
    else:
        usemask = ''
        mask = ''
    
    imsize_x, imsize_y = imsize
    fieldnames, first_field, last_field = gen_fieldnames(msfile, basepath, fields)
    imageparams_str = f'{imagetype}_{weighttype}{weight}_uv{uvrange[1:]}_{imsize_x}x{cell_res[:4]}_nitr{niter}'
    imagename_str = f'{msfile.split(".ms")[0]}_f{first_field}f{last_field}_{imageparams_str}'
    print(f'Image Name: {imagename_str}.image')
    print(f'Full Image path: {os.path.join(basepath, "images", imagename_str)}.image')
    tclean(vis=os.path.join(basepath, 'msfiles', 'avg', msfile),
           field=fieldnames,            
           imagename=os.path.join(basepath, 'images', imagename_str),
           specmode='mfs',
           deconvolver='hogbom',
           gridder='wproject',
           wprojplanes=-1,  # auto (if using wproject)
           niter=niter,             
           threshold='0.005Jy',
           interactive=False,
           imsize=[imsize_x, imsize_y],
           cell=[cell_res], 
           weighting=weighttype,
           robust=weight,
           pblimit=0.25,
           pbcor=True,
           psfcutoff=0.5,
           uvrange=uvrange,
           phasecenter=phasecenter,
           usemask=usemask,
           mask=mask,
           startmodel=startmodel,
           savemodel='modelcolumn'
           )

    print(f'Done cleaning image {imagename_str}.image')
    print('\n')

    if save_fits:
        print(f'Saving fits file: {imagename_str}.image.fits')
        if os.path.exists(os.path.join(basepath, 'images', imagename_str) + '.image.fits'):
            print('Fits file already exists! This will be deleted and remade...')
            print('\n')
            os.remove(os.path.join(basepath, 'images', imagename_str) + '.image.fits')

        exportfits(os.path.join(basepath, 'images', imagename_str) + '.image', os.path.join(basepath, 'images', imagename_str) + '.image.fits')
        print('Fits file saved!')
        print('\n')

        if plot_fits:
            print('Plotting fits file...')
            # Load the FITS image
            fits_file = os.path.join(basepath, 'images', imagename_str) + '.image.fits'
            hdu = fits.open(fits_file)[0]
            freq_val = hdu.header['CRVAL3']  # Central frequency (e.g., 1.404882070235e+09 Hz)
            stokes_val = hdu.header['CRVAL4']  # Default Stokes parameter (e.g., 1)
            wcs = WCS(hdu.header)

            slices = (0, 0)  # Adjust this based on your FITS file (e.g., for time or frequency)
            wcs_2d = WCS(hdu.header, naxis=2)

            # Display the FITS image
            fig, ax = plt.subplots(subplot_kw={'projection': wcs_2d}, figsize = (25, 25))
            norm = ImageNormalize(hdu.data[0, 0, :, :], interval=ZScaleInterval(), stretch=PowerStretch(a=4))
            ax.imshow(hdu.data[0, 0, :, :], cmap='gray_r', norm=norm, origin='lower')

            # Overlay circles around NVSS sources on the FITS image
            for xi, yi in nvss_coords:
                circle = Circle((xi, yi), radius=50, edgecolor='red', facecolor='none', lw=0.8, transform=ax.get_transform('pixel'))
                ax.add_patch(circle)

            # Define the sky coordinate for the magnetar (J2000 is equivalent to ICRS)
            #mag_coord = SkyCoord('05:01:06.76', '+45:16:33.92', unit=(u.hourangle, u.deg), frame='icrs')
            # Convert the sky coordinate to pixel coordinates using your 2D WCS
            #x_mag, y_mag = skycoord_to_pixel(mag_coord, wcs_2d)
            #circle_mag_1 = Circle((x_mag, y_mag), radius=50, edgecolor='purple', facecolor='none', lw=1.2, transform=ax.get_transform('pixel'))
            #ax.add_patch(circle_mag_1)
            #circle_mag_2 = Circle((x_mag, y_mag), radius=60, edgecolor='purple', facecolor='none', lw=1.2, transform=ax.get_transform('pixel'))
            #ax.add_patch(circle_mag_2)
            #circle_mag_3 = Circle((x_mag, y_mag), radius=70, edgecolor='purple', facecolor='none', lw=1.2, transform=ax.get_transform('pixel'))
            #ax.add_patch(circle_mag_3)
            #circle_mag_4 = Circle((x_mag, y_mag), radius=80, edgecolor='purple', facecolor='none', lw=1.2, transform=ax.get_transform('pixel'))
            #ax.add_patch(circle_mag_4)

            ax.set_xlabel('RA')
            ax.set_ylabel('Dec')

            # Show the plot
            plt.title(f'Clean Image: {msfile.split("_")[0]}')
            plt.grid(color='k', ls='dotted')
            fig.savefig(os.path.join(basepath, 'figures', f'{imagename_str}.image.pdf'))
            print(f'Fits image is saved as PDF: {imagename_str}.image.pdf')
            print('\n')
    
    return

def make_mask(basepath,
              skymodel_image,
              maskfile
              ):
    
    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))
    
    # Threshold the model to create a mask (adjust threshold as needed)
    immath(
        imagename=os.path.join(basepath, 'skymodels', 'mask_skymodels', skymodel_image),
        expr='iif(IM0 >= 1e-6, 1.0, 0.0)',  # Threshold: values > 1µJy become 1
        outfile=maskfile,
        overwrite=True
    )

    return