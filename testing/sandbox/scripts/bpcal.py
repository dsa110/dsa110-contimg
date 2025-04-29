import os
import numpy as np
from astropy.coordinates import SkyCoord, match_coordinates_sky
from astroquery.vizier import Vizier

from casatasks import listobs, clearcal, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, fixvis, phaseshift, casalog, mstransform
from casatools import componentlist

# ----------------------------------------------
# CASA Script for calibrating and imaging field
# ----------------------------------------------

# Set path for CASA log files
casalog.setlogfile('/data/jfaber/dsa110-contimg/sandbox/2025-02-26$/casa_logfile.log')

# ----------------------
# 0. Initial Inspection
# ----------------------

basepath = '/data/jfaber/dsa110-contimg/sandbox/2025-02-26/'
msfile = '2025-02-26T19:31:53_ra332.0_dec+42.2.ms'
#msfilefix = '2025-01-30T07:56:37_ra130.686_dec+69.164_fix.ms'
#msfileavg = '2025-01-30T07:56:37_ra130.686_dec+69.164_avg.ms'
#calibrator_field = 'drift_ra8h41m20s'
ra_str = f"{msfile.split('_')[1][2:5]}p{msfile.split('_')[1][6:9]}"
dec_str = f"{msfile.split('_')[2][4:6]}p{msfile.split('_')[2][7:8]}"
clfile = 'J2202+422.cl'
bcalfile = 'J2202+422.bcal'
calibrator_coord = 'J2000 22h02m43.29s +42d16m40.1s'

#listobs(vis=msfile,
#        listfile=f'{msfile}.txt', overwrite=True)

# Clear any old MODEL_DATA, CORRECTED_DATA, etc.:
#print("Clearing old MODEL_DATA, CORRECTED_DATA, etc....")

#clearcal(vis=os.path.join(basepath, msfile), field='')

#mstransform(vis=f'/data/jfaber/nsfrb_cand/calmsdir/bpcal/J0841_708/{msfile}',
#            outputvis=f'/data/jfaber/nsfrb_cand/calmsdir/bpcal/J0841_708/{msfileavg}',
#            datacolumn='all',   # or 'corrected' if you've already applied earlier calibration
#            chanaverage=True,
#            chanbin=48,
#            regridms=True)

# Flag bad antennas
#flagdata(vis=msfile, mode='manual', antenna='pad71,pad93,pad101,pad103,pad104,pad105,pad106,pad107,pad109,pad115,pad116')

# -----------------------------------------------------------------------
# 1. fixvis() and ft() to get set phase center to calibrator location
# -----------------------------------------------------------------------

print('Generating Sky Model...')

if os.path.exists(os.path.join(basepath, clfile)):
      print(f"File '{clfile}' already exists. Skipping component creation.")
else:
      print(f"Creating new component list '{clfile}'...")

      cl = componentlist()

      cl.addcomponent(
            dir=calibrator_coord,
            flux=7.468,
            fluxunit='Jy',
            freq='1.4GHz')
            #shape='Gaussian',
            #majoraxis='30arcsec',
            #minoraxis='30arcsec',
            #positionangle='0deg')

      cl.rename(os.path.join(basepath, clfile))
      cl.close()

print('Inserting Sky Model...')

ft(vis=os.path.join(basepath, msfile), 
      complist=os.path.join(basepath, clfile), 
      field='',
      reffreq='1.4GHz',
      usescratch=True)

#phaseshift(vis=f'/data/jfaber/nsfrb_cand/calmsdir/bpcal/J0841_708/{msfile}',
#       outputvis=f'/data/jfaber/nsfrb_cand/calmsdir/bpcal/J0841_708/{msfilefix}',
#       phasecenter=calibrator_coord)  # your new calibrator coords

# --------------------------------
# 4. Bandpass Calibration
# --------------------------------
print('Performing Bandpass Calibration...')

bandpass(vis=os.path.join(basepath, msfile),
         field='',
         caltable=os.path.join(basepath, bcalfile),
         refant='pad103',
         solint='inf',
         bandtype='B',
         combine='scan, spw, field',
         solnorm=True,
         minsnr=3)

# --------------------------------
# 5. Apply All Calibrations
# --------------------------------
print('Apply calibration tables...')

applycal(vis=os.path.join(basepath, msfile),
         field='', # apply to all fields
         gaintable=[
            os.path.join(basepath, bcalfile)    # if performing bandpass
         ],
         interp=[
            'nearest'    # phase
         ],
         applymode='calflag',
         calwt=[False])  # Usually set to False for typical continuum

