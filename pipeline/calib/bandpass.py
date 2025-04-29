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
from astroquery.vizier import Vizier
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u

from casatasks import listobs, split, clearcal, delmod, rmtables, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, fixvis, phaseshift, casalog, mstransform, exportfits
from casatools import componentlist, msmetadata, imager, ms, table

# Set path for measurement set, analysis output, and CASA log files
basepath = '/data/jfaber/dsa110-contimg/sandbox/2025-03-18/'
casalog.setlogfile(f'{basepath}/casa_logfile.log')

sys.path.insert(0, '/data/jfaber/dsa110-contimg/pipeline/calib')
from calib_utils import sort_msfiles, gen_fieldnames, reset_msfile, flag_rfi, flag_general, downchan_msfile, apply_bandpass, phase_calib, apply_phase, bandpass_calib

sys.path.insert(0, '/data/jfaber/dsa110-contimg/pipeline/skymodel')
from skymodel_utils import make_skymodel, image_skymodel # type: ignore

# Identify MS containing J2253
msfile = '2025-03-18T01:30:21_ra080.4_dec+16.5.ms'
msdate = msfile.split('_')[0]

# Reset MS
reset_msfile(msfile, basepath)

msfile_avg = downchan_msfile(msfile, basepath, nchan=4)

# Flag RFI
flag_rfi(msfile_avg, basepath, diagnostic_plot=False)
flag_general(msfile_avg, basepath)

# Make skymodel with calibrator 
nvss_catalog, clfile, jname = make_skymodel(msfile_avg, basepath, sourcename='3C138', cfieldid=11, top_n=200, pbfrac=0.5)

phasecenter, nvss_coords, skymodel_image = image_skymodel(msfile_avg, basepath, nvss_catalog, clfile=clfile, cfieldid=11, phasecenter=jname)

bcalfile = bandpass_calib(msfile_avg, basepath, clfile, phasecenter)