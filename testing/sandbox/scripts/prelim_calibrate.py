import os
import numpy as np
from astropy.coordinates import SkyCoord, match_coordinates_sky
from astroquery.vizier import Vizier

from casatasks import listobs, clearcal, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, fixvis
from casatools import componentlist

# ----------------------------------------------
# CASA Script for calibrating and imaging field
# ----------------------------------------------

# ----------------------
# 0. Initial Inspection
# ----------------------

basepath = './bpcal/split_ms/'
amppath = './ampcal'
bppath = './bpcal'
msfilename = 'field_3C309.1.ms'
msfile = os.path.join(basepath, msfilename)
msfilename_fix = 'field_3C309.1_fix.ms'
msfile_fix = os.path.join(basepath, msfilename_fix)
calibrator_coord = 'J2000 14h59m07.583867s 71d40m19.867740s'

#listobs(vis=msfile,
#        listfile=f'{msfile}.txt', overwrite=True)

# Clear any old MODEL_DATA, CORRECTED_DATA, etc.:
clearcal(vis=msfile)

# Flag bad antennas
#flagdata(vis=msfile, mode='manual', antenna='pad71,pad93,pad101,pad103,pad104,pad105,pad106,pad107,pad109,pad115,pad116')

# -----------------------------------------------------------------------
# 1. fixvis() and setjy() to get set phase center to calibrator location
# -----------------------------------------------------------------------

fixvis(vis=msfile,
       outputvis=os.path.join(basepath, msfilename_fix),
       field='3C309.1',  # or 'TargetField'
       phasecenter=calibrator_coord)  # your new calibrator coords

setjy(vis=msfile_fix, 
      field='3C309.1', 
      standard='Perley-Butler 2017')

# ---------------------------
# 2. Gain Calibration (Phase)
# ---------------------------
# Solve for phase gains on short timescales (e.g., per integration).
# Setting reference antenna to 'pad8' (as per R. Keenan)
#gaincal(vis=msfile,
#        field='3C309.1',
#        caltable='3C309.1.gcal.phase',
#        solint='int',
#        refant='pad60',    # stable antenna
#        calmode='p')      # 'p' = phase-only

# ----------------------------
# 3. Gain Calibration (Amp)
# ----------------------------
# Solve for amplitude, usually on a longer solint, in this case 'inf'.
gaincal(vis=msfile_fix,
        field='3C309.1',
        caltable=os.path.join(amppath, '3C309.1.gcal.ap'),
        solint='inf',
        refant='pad60',
        calmode='ap') # 'ap' = amplitude-only

# --------------------------------
# 4. Bandpass Calibration
# --------------------------------
bandpass(vis=msfile_fix,
         field='3C309.1',
         caltable=os.path.join(bppath, '3C309.1.bcal'),
         refant='pad60',
         solint='inf',
         bandtype='B',
         gaintable=[os.path.join(amppath,'3C309.1.gcal.ap')])

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
