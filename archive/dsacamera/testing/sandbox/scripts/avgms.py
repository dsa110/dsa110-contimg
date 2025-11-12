import os
import shutil
import numpy as np
from astropy.coordinates import SkyCoord, match_coordinates_sky
from astroquery.vizier import Vizier

from casatasks import listobs, clearcal, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, fixvis, phaseshift, casalog, mstransform
from casatools import componentlist

# ---------------------------------
# CASA Script for flux calibration
# ---------------------------------

# Set path for CASA log files
casalog.setlogfile('/data/jfaber/nsfrb_cand/casa_logfile.log')

# ----------------------
# 0. Initial Inspection
# ----------------------

msfiles = os.listdir('/data/jfaber/nsfrb_cand/msdir/2025_01_30T03h_15m_45m_avg')

for msfile in msfiles:

    # Clear any old MODEL_DATA, CORRECTED_DATA, etc.:
    print("Clearing old MODEL_DATA, CORRECTED_DATA, etc....")

    clearcal(vis=f'/data/jfaber/nsfrb_cand/msdir/2025_01_30T03h_15m_45m_avg/{msfile}')

    mstransform(vis=f'/data/jfaber/nsfrb_cand/msdir/2025_01_30T03h_15m_45m_avg/{msfile}',
                outputvis=f'/data/jfaber/nsfrb_cand/msdir/2025_01_30T03h_15m_45m_avg/{msfile[:-3]}_avg.ms',
                datacolumn='all',   # or 'corrected' if you've already applied earlier calibration
                chanaverage=True,
                chanbin=48,
                regridms=True)

    shutil.rmtree(f'/data/jfaber/nsfrb_cand/msdir/2025_01_30T03h_15m_45m_avg/{msfile}')