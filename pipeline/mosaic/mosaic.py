import os
import numpy as np
import matplotlib.pyplot as plt
from shutil import rmtree, copy, copytree
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.visualization import (PercentileInterval, LogStretch, PowerStretch, ManualInterval, ZScaleInterval, ImageNormalize)

from casatasks import listobs, split, clearcal, delmod, rmtables, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, fixvis, phaseshift, casalog, mstransform, exportfits
from casatools import linearmosaic, componentlist, msmetadata, imager, ms, table

# Set path for measurement set, analysis output, and CASA log files
basepath = '/data/jfaber/dsa110-contimg/sandbox/2025-03-18/'
casalog.setlogfile(f'{basepath}/casa_logfile.log')

file_start = [0, 9, 19, 29, 39, 49, 59, 69, 79, 89, 99, 109, 119]
file_pack = [11, 21, 31, 41, 51, 61, 71, 81, 91, 101, 111, 121, 126]

for i in range(len(file_start)):

    input_msfile_path = os.path.join(basepath, 'msfiles', 'base')
    input_msfiles = [file for file in os.listdir(input_msfile_path) if file.endswith('.ms')]
    input_msfiles_sorted = sorted(input_msfiles, key=lambda fname: float(fname.split("_ra")[1].split("_")[0]))
    input_msfiles_sorted = input_msfiles_sorted[file_start[i]:file_pack[i]]
    input_msfiles_fullpath = [os.path.join(basepath, 'msfiles', 'base', i) for i in input_msfiles_sorted]
    print('Input MS Files: \n')
    all_files = []
    for file in input_msfiles_sorted:
        all_files.append(file)
        print(file)
    start_time = all_files[0][11:19]
    end_time = all_files[-1][11:19]
    print(f'Mosaic time range: {start_time} - {end_time} UTC')
    print('\n')

    input_images_path = os.path.join(basepath, 'images')
    input_images = [file for file in os.listdir(input_images_path) if file.endswith('nitr10000.image')]
    input_images_sorted = sorted(input_images, key=lambda fname: float(fname.split("_ra")[1].split("_")[0]))
    input_images_sorted = input_images_sorted[file_start[i]:file_pack[i]]
    input_images_fullpath = [os.path.join(basepath, 'images', i) for i in input_images_sorted]
    #print(len(input_images_sorted))

    pb_images_path = os.path.join(basepath, 'images')
    pb_images = [file for file in os.listdir(pb_images_path) if file.endswith('nitr10000.pb')]
    pb_images_sorted = sorted(pb_images, key=lambda fname: float(fname.split("_ra")[1].split("_")[0]))
    pb_images_sorted = pb_images_sorted[file_start[i]:file_pack[i]]
    pb_images_fullpath = [os.path.join(basepath, 'images', i) for i in pb_images_sorted]
    #print(len(pb_images_sorted))

    #input_msfiles = [file for file in os.listdir(basepath) if file.endswith('_base.ms')]
    #input_images = [file for file in os.listdir(basepath) if file.endswith('nitr10000.image')]
    #input_images = [os.path.join(basepath, i) for i in input_images]
    #print('Input Images \n')
    #for file in input_msfiles:
    #    print(f'{file}')
    #pb_images = [file for file in os.listdir(basepath) if file.endswith('nitr10000.pb')]
    #pb_images = [os.path.join(basepath, i) for i in pb_images]
    #print(f'PB Images: {pb_images}')

    all_mean_ras = []
    all_mean_decs = []

    print(f'Finding phasecenter across {len(input_msfiles_sorted)} MS files...')

    for msfile in input_msfiles_sorted:
        msmd = msmetadata()
        msmd.open(os.path.join(basepath, 'msfiles', 'base', msfile))

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

        # Calculate the geometric mean center (central coordinate)
        center_ra = np.mean([coord[0] for coord in phase_centers_deg])
        center_dec = np.mean([coord[1] for coord in phase_centers_deg])
        all_mean_ras.append(center_ra)
        all_mean_decs.append(center_dec)

    ra_mean_deg = np.mean(all_mean_ras)
    dec_mean_deg = np.mean(all_mean_decs)

    center_coord = SkyCoord(ra_mean_deg, dec_mean_deg, unit='deg')

    ra_fixed = f'{round(center_coord.ra.hms.h)}h{round(center_coord.ra.hms.m)}m{round(center_coord.ra.hms.s, 4)}s'
    dec_fixed = f'{round(center_coord.dec.dms.d)}d{round(center_coord.dec.dms.m)}m{round(center_coord.dec.dms.s, 4)}s'

    phasecenter = f'J2000 {ra_fixed} {dec_fixed}'

    print('\n')
    print(f'Phase Center (deg): {ra_mean_deg, dec_mean_deg}')
    print(f'Phase Center (hms): {phasecenter}')
    print('\n')

    print('Making mosaic...')
    print('\n')

    lm = linearmosaic()

    lm.setlinmostype('optimal')

    first_ms = input_msfiles_sorted[0]
    last_ms = input_msfiles_sorted[-1]
    mosimagename = f"mosaic_{first_ms.split('_')[0]}_{last_ms.split('_')[0]}_ra{first_ms.split('_')[1][3:]}_{last_ms.split('_')[1][3:]}_dec{first_ms.split('_')[2][3:]}_{last_ms.split('_')[2][3:]}.linmos"
    weightmosname = f"weight_{first_ms.split('_')[0]}_{last_ms.split('_')[0]}_ra{first_ms.split('_')[1][3:]}_{last_ms.split('_')[1][3:]}_dec{first_ms.split('_')[2][3:]}_{last_ms.split('_')[2][3:]}.weightlinmos"

    if os.path.exists(os.path.join(basepath, 'mosaics', mosimagename)):
        print('Removing old mosaic!')
        print('\n')
        rmtree(os.path.join(basepath, 'mosaics', mosimagename))
    if os.path.exists(os.path.join(basepath, 'mosaics', weightmosname)):
        print('Removing old weight mosaic!')
        print('\n')
        rmtree(os.path.join(basepath, 'mosaics', weightmosname))

    lm.defineoutputimage(nx=28800, ny=4800, cellx='3arcsec', celly='3arcsec', \
            imagecenter=phasecenter, #01h37m41.299431s 33d09m35.132990s', #set to calibrator coordinates
            outputimage=os.path.join(basepath, 'mosaics', f'{mosimagename}'), \
            outputweight=os.path.join(basepath, 'mosaics', f'{weightmosname}'))

    lm.makemosaic(images=input_images_fullpath, weightimages=pb_images_fullpath)
    print('Mosaic done!')
    print('\n')

    print('Saving figure...')

    if os.path.exists(os.path.join(basepath, 'mosaics', mosimagename) + '.fits'):
        os.remove(os.path.join(basepath, 'mosaics', mosimagename) + '.fits')
        
    exportfits(os.path.join(basepath, 'mosaics', mosimagename), os.path.join(basepath, 'mosaics', mosimagename) + '.fits')
    # Load the FITS image
    #for fieldname in field_names:
    fits_file = os.path.join(basepath, 'mosaics', mosimagename) + '.fits'
    hdu = fits.open(fits_file)[0]
    freq_val = hdu.header['CRVAL3']  # Central frequency (e.g., 1.404882070235e+09 Hz)
    stokes_val = hdu.header['CRVAL4']  # Default Stokes parameter (e.g., 1)
    wcs = WCS(hdu.header)

    slices = (0, 0)  # Adjust this based on your FITS file (e.g., for time or frequency)
    wcs_2d = WCS(hdu.header, naxis=2)

    # Display the FITS image
    fig, ax = plt.subplots(subplot_kw={'projection': wcs_2d}, figsize = (20, 20))
    #norm = ImageNormalize(hdu.data[0, 0, :, :], interval=PercentileInterval(99), stretch=LogStretch())
    norm = ImageNormalize(hdu.data[0, 0, :, :], interval=ZScaleInterval(), stretch=PowerStretch(a=1))
    ax.imshow(hdu.data[0, 0, :, :], cmap='gray_r', norm=norm, origin='lower')
    #ax.imshow(hdu.data[0, 0, :, :], cmap='gray_r', origin='lower', vmax = 0.1*np.max(hdu.data[0, 0, :, :])) #norm=norm, origin='lower', vmax = 0.1*np.max(hdu.data[0, 0, :, :]))

    ax.set_xlabel('RA')
    ax.set_ylabel('Dec')

    # Show the plot
    plt.title(f'Mosaiced Clean Image ({start_time} - {end_time} UTC)')
    plt.grid(color='k', ls='dotted')
    fig.savefig(os.path.join(basepath, 'figures', f'{mosimagename}') + '.pdf')