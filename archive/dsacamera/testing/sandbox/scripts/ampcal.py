import os
import numpy as np
from astropy.coordinates import SkyCoord, match_coordinates_sky
from astroquery.vizier import Vizier

from casatasks import listobs, clearcal, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, fixvis, phaseshift, casalog, mstransform
from casatools import componentlist

# ---------------------------------
# CASA Script for flux calibration
# ---------------------------------

# Set path for CASA log files
casalog.setlogfile('/data/jfaber/dsa110-contimg/sandbox/2025-02-14T13-07/multifield/casa_logfile.log')

# ----------------------
# 0. Initial Inspection
# ----------------------

basepath = '/data/jfaber/dsa110-contimg/sandbox/2025-02-14T13-07/multifield'
msfile = '2025-02-14T13:07:27_ra224.004_dec+71.742.ms'
top_n = 100  # Number of sources to include in the component list
ra_str = f"{msfile.split('_')[1][2:5]}p{msfile.split('_')[1][6:9]}"
dec_str = f"{msfile.split('_')[2][4:6]}p{msfile.split('_')[2][7:10]}"
clfile = f'nvss_top{top_n}_{ra_str}_{dec_str}.cl'
cllabel = clfile.split('.')[0]
amp_table = f'{cllabel}.gcal.a'

#calibrator_coord = 'J2000 03h52m23.34s 67d58m27.80s'

# Clear any old MODEL_DATA, CORRECTED_DATA, etc.:
#print("Clearing old MODEL_DATA, CORRECTED_DATA, etc....")

#clearcal(vis=f'/data/jfaber/nsfrb_cand/calmsdir/ampcal/{msfile}')

#mstransform(vis=f'/data/jfaber/nsfrb_cand/calmsdir/ampcal/{msfile}',
#            outputvis=f'/data/jfaber/nsfrb_cand/calmsdir/ampcal/{msfileavg}',
#            datacolumn='all',   # or 'corrected' if you've already applied earlier calibration
#            chanaverage=True,
#            chanbin=48,
#            regridms=True)

# -----------------------------------------------------------------------
# 1. fixvis() and ft() to get set phase center to calibrator location
# -----------------------------------------------------------------------

#print('Inserting Sky Model...')

#ft(vis=os.path.join(basepath, msfilesb), 
#      complist=os.path.join(basepath, clfile), 
#      reffreq='1.4GHz',
#      usescratch=True)

#setjy(vis=msfile_fix,
#      field='',           # Replace with the name or ID of your calibrator field
#      standard='manual',                    # Indicates that you're providing your own model
#      fluxdensity=[0.7603, 0, 0, 0],          # [Stokes I, Q, U, V] flux in Jy
#      reffreq='1.4GHz')

#print('Shifting Phase Center to Brightest Source...')

#phaseshift(vis=f'/data/jfaber/nsfrb_cand/calmsdir/ampcal/{msfile}',
#       outputvis=f'/data/jfaber/nsfrb_cand/calmsdir/ampcal/{msfilefix}',
#       field='',  # or 'TargetField'
#       datacolumn='all',
#       phasecenter=calibrator_coord)  # your new calibrator coords

# ----------------------------
# 3. Gain Calibration (Phase)
# ----------------------------

print('Performing Gain (Amplitude-Only) Calibration...')

# Solve for amplitude, usually on a longer solint, in this case 'inf'.
gaincal(vis=os.path.join(basepath, msfile),
        field='',
        caltable=os.path.join(basepath, amp_table),
        solint='inf',
        refant='pad103',
        combine='scan, field',
        solnorm=True,
        calmode='a', # 'p' = phase-only
        gaintype='G',
        gaintable = [os.path.join(basepath, 'J1459_716.bcal')]
      ) 

# --------------------------------
# 5. Apply All Calibrations
# --------------------------------
#applycal(vis=f'/data/jfaber/nsfrb_cand/calmsdir/ampcal/{msfileavg}',
#         field='', # apply to all fields
#         gaintable=[
#            '/data/jfaber/nsfrb_cand/calmsdir/ampcal/nvss_top10_063p212_69p005.gcal.p'    
#         ],
#         interp=[
#            'nearest'    # phase
#         ],
#         applymode='calflag',
#         calwt=[False])  # Usually set to False for typical continuum