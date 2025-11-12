import os
import sys
import numpy as np
import pandas as pd
import importlib
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
import astropy.units as u

from casatasks import listobs, split, clearcal, delmod, rmtables, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, fixvis, phaseshift, casalog, mstransform, exportfits
from casatools import componentlist, msmetadata, imager, ms, table

import time

class Timer:
    def __init__(self, label="Elapsed time"):
        self.label = label

    def __enter__(self):
        self.start = time.perf_counter()  # More precise than time.time()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.elapsed = self.end - self.start
        print(f"{self.label}: {self.elapsed:.3f} seconds")


# Set path for measurement set, analysis output, and CASA log files
basepath = '/data/jfaber/dsa110-contimg/sandbox/2025-03-18/'
casalog.setlogfile(f'{basepath}/casa_logfile.log')

sys.path.insert(0, '/data/jfaber/dsa110-contimg/pipeline/calib')
from calib_utils import sort_msfiles, gen_fieldnames, reset_msfile, flag_rfi, flag_general, downchan_msfile, apply_bandpass, phase_calib, apply_phase

sys.path.insert(0, '/data/jfaber/dsa110-contimg/pipeline/skymodel')
from skymodel_utils import make_skymodel, image_skymodel # type: ignore

sys.path.insert(0, '/data/jfaber/dsa110-contimg/pipeline/image')
from image_utils import image_tclean # type: ignore

remove_splits = False

if remove_splits:
    for ext in ['bcorr','bpcorr', 'flagversions']:
        if os.path.exists(os.path.join(basepath, 'msfiles', 'avg', ext)):
            print(f'Changing directory to: {os.path.join(basepath, "msfiles", "avg", ext)}')
            os.chdir(os.path.join(basepath, 'msfiles', 'avg', ext))
            os.system(f'rm -r *{ext}*')

# Define MS files (sorted)
#msfiles_sorted = sort_msfiles(os.path.join(basepath, 'msfiles', 'base'))
# Rerunning for calibrator 3C138, no need to re-do averaging
msfiles_sorted = sort_msfiles(os.path.join(basepath, 'msfiles', 'avg'))

pcalpack_idxs = np.arange(0, 126, 5)
msfiles_pcalpacks = []
for i in pcalpack_idxs:
    if i < 119:
        msfiles_pcalpacks.append(msfiles_sorted[i:i+5])
    else:
        msfiles_pcalpacks.append(msfiles_sorted[i:i+6])

# Define baseband calibration table
bcalfile = '3C138_2025-03-18T01:30:21_f0f23.bcal'
#bcalfile = '3C454.3_2025-03-18T19:00:04_f0f23.bcal'
# Define number of sources from NVSS field to include in the sky model
top_n = 50
# Define field range covered within each MS at a time
start_fields = (0,23)
#pcalfile = 'nvss_top200_343p6_16p4_2025-03-18T19:00:04_f0f23.pcal'

for msfiles_ppack in msfiles_pcalpacks:

    start_msfile = msfiles_ppack[0]
    print(f'Starting MS file: {start_msfile}')
    start_msdate = start_msfile.split('_')[0]
    start_ra_str = f"{start_msfile.split('_')[1][2:5]}p{start_msfile.split('_')[1][6:9]}"
    start_dec_str = f"{start_msfile.split('_')[2][4:6]}p{start_msfile.split('_')[2][7:8]}"
    start_first_field, start_last_field = start_fields
    pcalfile = f'nvss_top200_{start_ra_str}_{start_dec_str}_{start_msdate}_f{start_first_field}f{start_last_field}.pcal' # note top_n is hardcoded here!!!
    print(f'Associated phase calibration table: {pcalfile}')

    #for msfile in msfiles_ppack:
    for msfile_avg in msfiles_ppack:

        # Define date/time of observation
        #msdate = msfile.split('_')[0]
        msdate = msfile_avg.split('_')[0]

        # Reset MS
        #reset_msfile(msfile, basepath)
        with Timer("Resetting MS file..."):
            reset_msfile(msfile_avg, basepath, filetype='avg')

        # Downchannelize MS
        #msfile_avg = downchan_msfile(msfile, basepath, nchan=4)

        # Flag RFI, shadowing, autocorr, etc.
        with Timer("Flagging MS file... \n"):
            flag_rfi(msfile_avg, basepath, diagnostic_plot=False)
            flag_general(msfile_avg, basepath)

        # Make skymodel with 250 brightest NVSS sources 
        with Timer("Making sky model... \n"):
            nvss_catalog, clfile = make_skymodel(msfile_avg, basepath, sourcename=None, cfieldid=11, top_n=top_n, pbfrac=0.5)

        # Image skymodel
        with Timer("Imaging sky model... \n"):
            phasecenter, nvss_coords, skymodel_image = image_skymodel(msfile_avg, basepath, nvss_catalog, clfile=clfile, cfieldid=11, top_n=top_n, phasecenter=None, make_image=False)

        # Apply bandpass solutions
        with Timer("Applying bandpass solutions... \n"):
            msfile_bcorr = apply_bandpass(msfile_avg, basepath, bcalfile, fields=(0,23))

        # Perform phase calibration
        #pcalfile = phase_calib(msfile_bcorr, basepath, clfile, phasecenter, fields=(0,23))

        # Apply phase solutions from phase calibration tables
        with Timer("Applying phase solutions... \n"):
            msfile_bpcorr = apply_phase(msfile_bcorr, basepath, pcalfile, fields=(0,23))

        # Image phase and bandpass calibrated measurement set
        with Timer("Making image with tclean... \n"):
            image_tclean(msfile_bpcorr, basepath, phasecenter, nvss_coords, skymodel_image, save_fits=True, plot_fits=True)
