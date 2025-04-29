from casatasks import listobs, clearcal, setjy, gaincal, bandpass, applycal, tclean, flagdata

# ---------------------------------------------------------
# CASA Script for 2024-11-02T06:43:34_ra024.908_dec+33.025.ms
# ---------------------------------------------------------

# ----------------------
# 0. Initial Inspection
# ----------------------
listobs(vis='2024-11-02T06:43:34_ra024.908_dec+33.025.ms',
        listfile='listobs_2024-11-02T06:43:34_ra024.908_dec+33.025.txt', overwrite=True)

# Clear any old MODEL_DATA, CORRECTED_DATA, etc.:
clearcal(vis='2024-11-02T06:43:34_ra024.908_dec+33.025.ms')

# Flag bad antennas
flagdata(vis='2024-11-02T06:43:34_ra024.908_dec+33.025.ms', mode='manual', antenna='pad71,pad93,pad101,pad103,pad104,pad105,pad106,pad107,pad109,pad115,pad116')

# --------------
# 1. Setjy Step
# --------------
# Manually set '3C48' as the calibrator field name for field 2 in this MS, so it's recognized by CASA:

#from casatools import table
#tb = table()
#tb.open('my.ms/FIELD', nomodify=False)
#names = tb.getcol('NAME')
#names[2] = '3C48'  # rename field ID=2
#tb.putcol('NAME', names)
#tb.close()

setjy(vis='2024-11-02T06:43:34_ra024.908_dec+33.025.ms',
      field='3C48',
      standard='Perley-Butler 2017')

# This populates the MODEL_DATA column for 3C48 with the known flux/structure model.

# ---------------------------
# 2. Gain Calibration (Phase)
# ---------------------------
# Solve for phase gains on short timescales (e.g., per integration).
# Setting reference antenna to 'pad8' (as per R. Keenan)
gaincal(vis='2024-11-02T06:43:34_ra024.908_dec+33.025.ms',
        field='3C48',
        caltable='3C48.gcal.phase',
        solint='int',
        refant='pad8',    # stable antenna
        calmode='p')      # 'p' = phase-only

# ----------------------------
# 3. Gain Calibration (Amp/Phase)
# ----------------------------
# Solve for amplitude+phase, usually on a longer solint, in this case 'inf'.
gaincal(vis='2024-11-02T06:43:34_ra024.908_dec+33.025.ms',
        field='3C48',
        caltable='3C48.gcal.ap',
        solint='inf',
        refant='pad8',
        calmode='ap',
        gaintable=['3C48.gcal.phase'])  # Apply the phase solution while solving for amp+phase

# --------------------------------
# 4. Bandpass Calibration
# --------------------------------
bandpass(vis='2024-11-02T06:43:34_ra024.908_dec+33.025.ms',
         field='3C48',
         caltable='3C48.bcal',
         refant='pad8',
         solint='inf',
         bandtype='B',
         gaintable=['3C48.gcal.phase', '3C48.gcal.ap'])

# --------------------------------
# 5. Apply All Calibrations
# --------------------------------
# Modify the CORRECTED_DATA column in the MS for 3C48.
applycal(vis='2024-11-02T06:43:34_ra024.908_dec+33.025.ms',
         #field='',  # or '' for all fields if we want to apply to all
         gaintable=[
            '3C48.gcal.phase', 
            '3C48.gcal.ap',
            '3C48.bcal'    # if performing bandpass
         ],
         interp=[
            'nearest',     # phase
            'nearest',      # amp/phase
            'nearest'      # bandpass, if used
         ],
         applymode='calonly',
         calwt=[False, False, False])  # Usually set to False for typical continuum

# -------------------------------
# 6. Imaging 3C48
# -------------------------------
tclean(vis='2024-11-02T06:43:34_ra024.908_dec+33.025.ms',
       #field='3C48',            
       imagename='3C48_cleaned',
       specmode='mfs',
       gridder='wproject',
       wprojplanes=-1,          # auto (if using wproject)
       niter=10000,             
       threshold='0.1Jy',
       interactive=False,
       imsize=[4800, 4800],
       cell=['3arcsec'], 
       weighting='briggs',
       #phasecenter='J2000 01h37m41.299431s 33d09m35.132990s',
       robust=-2,
       pblimit=0.25,
       psfcutoff=0.5)
