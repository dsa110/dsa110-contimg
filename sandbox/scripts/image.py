import os
import argparse
import numpy as np
from astropy.coordinates import SkyCoord, match_coordinates_sky
from astroquery.vizier import Vizier

from casatasks import listobs, clearcal, setjy, gaincal, bandpass, applycal, tclean, flagdata, ft, delmod
from casatools import componentlist

# ----------------------------------------------
# CASA Script for calibrating and imaging field
# ----------------------------------------------

# ----------------------
# 0. Initial Inspection
# ----------------------

#parser = argparse.ArgumentParser()
#parser.add_argument("--ms", type=str, help="Name of the ms file you'd like to image", default="None")
#msfile_arg = parser.parse_args()
#msfile = msfile_arg.ms
#print(f'MS File: {msfile}')
#ra_str = f"{msfile.split('_')[1][2:5]}p{msfile.split('_')[1][6:9]}"
#dec_str = f"{msfile.split('_')[2][4:6]}p{msfile.split('_')[2][7:10]}"
#clfile = f'nvss_top100_{ra_str}_{dec_str}.cl'
#cllabel = clfile.split('.')[0]
basepath = '/data/jfaber/dsa110-contimg/sandbox/2025-02-14T13-07/multifield'
msfile = '2025-02-14T13:07:27_ra224.004_dec+71.742.ms'
#msfilesb = '2025-02-07T13:37:47_ra224.714_dec+71.740_sb.ms'
imagename = '2025-02-14T13:07:27_ra224.004_dec+71.742_clean'
top_n = 100  # Number of sources to include in the component list
ra_str = f"{msfile.split('_')[1][2:5]}p{msfile.split('_')[1][6:9]}"
dec_str = f"{msfile.split('_')[2][4:6]}p{msfile.split('_')[2][7:8]}"
clfile = f'nvss_top{top_n}_{ra_str}_{dec_str}.cl'
cllabel = clfile.split('.')[0]
fieldname = '' #'drift_ra15h01m00s'
bcalfile = 'J1459_716.bcal'
phasecalfile = 'nvss_top100_224p004_71p742.gcal.p'
ampcalfile = 'nvss_top100_224p004_71p742.gcal.a'

#listobs(vis=f'./msdir/{msfile}',
#        listfile=f'{msfile}.txt', overwrite=True)

# Clear any old MODEL_DATA, CORRECTED_DATA, etc.:
#print('Clearing any old MODEL_DATA, CORRECTED_DATA, etc...')
#clearcal(vis=os.path.join(basepath, msfile))

# Flag bad antennas
#allants = np.arange(116)
# Identified good antennas based on bandpass solutions (see check_bcal.py)
#goodants = [90, 88, 87, 85, 84, 83, 82, 81, 80, 79, 78, 77, 76, 74, 73, 72, 71, 69, 68, 67, 50, 49, 48, 46, 45, 44, 43, 42, 40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30]
#badants = np.setdiff1d(allants, goodants)
#badants = badants + 1 #indexing is 1
#badants_pad = []
#for i in badants:
#    badants_pad.append(f'pad{i}')
#badant_pad_str = ",".join(badants_pad)

print('Flagging Data...')
flagdata(vis=os.path.join(basepath, msfile), mode='manual', antenna='pad4, pad5, pad6, pad7, pad8, pad10, pad21, pad22, pad23, pad25, pad26, pad27, pad28, pad30, pad31, pad32, pad33, pad34, pad35, pad36, pad37, pad48, pad52, pad53, pad54, pad55, pad56, pad57, pad58, pad59, pad60, pad61, pad62, pad63, pad64, pad65, pad66, pad67, pad117')
#flagdata(vis=os.path.join(basepath, msfile), mode='manual', antenna='5, 7, 8, 10, 21, 22, 23, 35, 36, 48, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 109, 117')

#print('Inserting Sky Model...')
#ft(vis=os.path.join(basepath, msfile), 
#      complist=os.path.join(basepath, clfile), 
#      reffreq='1.4GHz',
#      usescratch=True)

#print('Remove Sky Model')
#delmod(vis=os.path.join(basepath, msfile))

# --------------------------------
# 5. Apply All Calibrations
# --------------------------------
#print('Applying Calibrations...')
#applycal(vis=os.path.join(basepath, msfile),
#         field='', # apply to all fields
#         gaintable=[
#            os.path.join(basepath, bcalfile),
#            os.path.join(basepath, phasecalfile),
#            os.path.join(basepath, ampcalfile)
#         ],    # if performing bandpass#         ],
#         interp = [
#            'nearest',     # bp
#            'nearest',
#            'nearest'
#         ],
#         applymode=['calflag', 'calflag', 'calflag'],
#         calwt=[False, False, False])  # Usually set to False for typical continuum
#applycal(vis=f'/data/jfaber/nsfrb_cand/msdir/2025_01_30T03h_15m_45m_avg/{msfile}',
#         field='', # apply to all fields
#         gaintable=[
#            f'/data/jfaber/nsfrb_cand/calmsdir/phasecal/nvss_top10_063p212_69p005.gcal.p', 
#            f'/data/jfaber/nsfrb_cand/calmsdir/ampcal/nvss_top10_063p212_69p005.gcal.a',
#            f'/data/jfaber/nsfrb_cand/calmsdir/bpcal/J0841_708.bcal'    # if performing bandpass
#         ],
#         interp=[
#            'nearest',     # phase
#            'nearest',      # amp/phase
#            'nearest'      # bandpass, if used
#         ],
#         applymode='calflag',
#         calwt=[False, False, False])  # Usually set to False for typical continuum
#
# -------------------------------
# 6. Imaging Field
# -------------------------------
print(f'Imaging with tclean for field {fieldname}...')

os.chdir('/data/jfaber/dsa110-contimg/sandbox/2025-02-14T13-07/multifield')

tclean(vis=os.path.join(basepath, msfile),
       field=fieldname,            
       imagename=os.path.join(basepath, imagename),
       specmode='mfs',
       deconvolver='hogbom',
       gridder='wproject',
       wprojplanes=-1,  # auto (if using wproject)
       niter=10000,             
       threshold='0.01Jy',
       interactive=False,
       imsize=[4800, 4800],
       cell=['3arcsec'], 
       weighting='briggs',
       robust=-2,
       pblimit=0.25,
       psfcutoff=0.5)
