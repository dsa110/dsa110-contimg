
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
basepath = '/data/jfaber/dsa110-contimg/sandbox/2025-03-18_trial1/'
casalog.setlogfile(f'{basepath}/casa_logfile.log')

fits_file = '/data/jfaber/dsa110-contimg/sandbox/2025-03-18_trial1/mosaics/mosaic_2025-03-18T07:02:34_2025-03-18T08:05:53_ra63.7_79.6_dec+16.6.ms_+16.6.ms.linmos.fits'
hdu = fits.open(fits_file)[0]
freq_val = hdu.header['CRVAL3']  # Central frequency (e.g., 1.404882070235e+09 Hz)
stokes_val = hdu.header['CRVAL4']  # Default Stokes parameter (e.g., 1)
wcs = WCS(hdu.header)

slices = (0, 0)  # Adjust this based on your FITS file (e.g., for time or frequency)
wcs_2d = WCS(hdu.header, naxis=2)

# Display the FITS image
fig, ax = plt.subplots(subplot_kw={'projection': wcs_2d}, figsize = (20, 20))
#norm = ImageNormalize(hdu.data[0, 0, :, :], interval=PercentileInterval(99), stretch=LogStretch())
norm = ImageNormalize(hdu.data[0, 0, :, :], interval=ZScaleInterval(), stretch=PowerStretch(a=4))
ax.imshow(hdu.data[0, 0, :, :], cmap='gray_r', norm=norm, origin='lower')
#ax.imshow(hdu.data[0, 0, :, :], cmap='gray_r', origin='lower', vmax = 0.1*np.max(hdu.data[0, 0, :, :])) #norm=norm, origin='lower', vmax = 0.1*np.max(hdu.data[0, 0, :, :]))

ax.set_xlabel('RA')
ax.set_ylabel('Dec')

# Show the plot
plt.title('Mosaiced Clean Image (7:55:35 - 8:58:58 UTC)')
plt.grid(color='k', ls='dotted')
fig.savefig('test_mosaic.pdf')