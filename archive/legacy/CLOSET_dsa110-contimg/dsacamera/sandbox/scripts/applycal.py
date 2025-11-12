import os
import numpy as np
from astropy.coordinates import SkyCoord, match_coordinates_sky
from astroquery.vizier import Vizier

from casatasks import listobs, clearcal, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, fixvis, phaseshift, casalog, mstransform
from casatools import componentlist

# --------------------------------
# Apply All Calibrations
# --------------------------------

#bpcal = True
#phasecal = False
#ampcal = False

#f bpcal:
#   msfile = 

basepath = '/data/jfaber/dsa110-contimg/sandbox/2025-02-14T13-07/multifield'
msfile = '2025-02-14T13:07:27_ra224.004_dec+71.742.ms'

applycal(vis=os.path.join(basepath, msfile),
         field='', # apply to all fields
         #gaintable=os.path.join(basepath, 'J1459_716.bcal'),
         gaintable=os.path.join(basepath, 'nvss_top100_224p004_71p742.gcal.a'),
         interp='linear',
         applymode='calflag',
         calwt=False)  # Usually set to False for typical continuum