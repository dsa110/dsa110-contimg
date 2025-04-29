import os
import numpy as np
from astropy.coordinates import SkyCoord, match_coordinates_sky
from astroquery.vizier import Vizier

from casatasks import listobs, clearcal, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft
from casatools import componentlist

# ----------------------------------------------
# CASA Script for calibrating and imaging field
# ----------------------------------------------

# ----------------------
# 0. Initial Inspection
# ----------------------

msfile = '2024-11-10T16:23:20_ra178.174_dec+30.642.ms'

listobs(vis=msfile,
        listfile=f'{msfile}.txt', overwrite=True)

# Clear any old MODEL_DATA, CORRECTED_DATA, etc.:
clearcal(vis=msfile)

# Flag bad antennas
#flagdata(vis=msfile, mode='manual', antenna='pad71,pad93,pad101,pad103,pad104,pad105,pad106,pad107,pad109,pad115,pad116')

# -----------------------------------------------------------------------
# 1. fixvis() and setjy() to get set phase center to calibrator location
# -----------------------------------------------------------------------

fixvis(vis=msfile,
       outputvis='3C309.1.ms',
       field='',  # or 'TargetField'
       phasecenter='J2000 14h59m07.583867s 71d40m19.867740s')  # your new calibrator coords

# Suppose the flux from NVSS is 500 mJy at 1.4 GHz
setjy(vis=msfile, 


# ---------------------------
# 2. Gain Calibration (Phase)
# ---------------------------
# Solve for phase gains on short timescales (e.g., per integration).
# Setting reference antenna to 'pad8' (as per R. Keenan)
#gaincal(vis=msfile,
#        field='',
#        caltable='nsfrb.gcal.phase',
#        solint='int',
#        refant='pad8',    # stable antenna
#        calmode='p')      # 'p' = phase-only

# ----------------------------
# 3. Gain Calibration (Amp)
# ----------------------------
# Solve for amplitude, usually on a longer solint, in this case 'inf'.
gaincal(vis=msfile,
        field='',
        caltable='nsfrb.gcal.ap',
        solint='inf',
        refant='pad60',
        calmode='ap')

# --------------------------------
# 4. Bandpass Calibration
# --------------------------------
bandpass(vis=msfile,
         field='',
         caltable='nvss_top.bcal',
         refant='pad60',
         solint='inf',
         bandtype='B',
         gaintable=['nvss_top.gcal.ap'])

# --------------------------------
# 5. Apply All Calibrations
# --------------------------------
#applycal(vis=msfile,
#         field='', # apply to all fields
#         gaintable=[
#            'nvss_top.gcal.phase', 
#            'nvss_top.gcal.ap',
#            'nvss_top.bcal'    # if performing bandpass
#         ],
#         interp=[
#            'nearest',     # phase
#            'nearest',      # amp/phase
#            'nearest'      # bandpass, if used
#         ],
#         applymode='calonly',
#         calwt=[False, False, False])  # Usually set to False for typical continuum
#
