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

#for file in os.listdir(basepath):
#    if file.endswith('.ms'):
#        file_prefix = file.split('.ms')[0]
#        file_copy = f'{file_prefix}_base.ms'
#        os.system(f'scp -r {os.path.join(basepath, file)} {os.path.join(basepath, file_copy)}')
#        print(f'Made copy: {file_copy}')

# Identify the base measurement sets and sorted them in time
msfiles = [file for file in os.listdir(basepath) if file.endswith('_base.ms')]
msfiles_sorted = sorted(msfiles, key=lambda fname: float(fname.split("_ra")[1].split("_")[0]))
print(msfiles_sorted)
msfile = msfiles_sorted[2]

#for msfile in msfiles:
print('\n')
print(f'Base MS File: {msfile}')
print('\n')

#idx = 3
msdate = msfile.split('_')[0]
chanstoavg = 8 #set to 4 later
field_image_idx = 11
field_cal_idx0, field_cal_idx1 = 0, 23
uvrange = '0.3klambda'
refant = 'pad103'

print('\n')
print(f'Observation Date: {msdate}')
print(f'No. Channels to Average: {chanstoavg}')
print(f'Central Field: Field {field_image_idx}')
print(f'Fields to Calibrate Over: Field {field_cal_idx0} to Field {field_cal_idx1}')
print('\n')

msfile_image = msfile.split(".ms")[0][:-5]+f'_image_sb{chanstoavg}.ms'

print(f'Imaging MS File: {msfile_image}')
print('\n')

if os.path.exists(os.path.join(basepath, msfile_image)):
    rmtree(os.path.join(basepath, msfile_image))
    #copytree(os.path.join(basepath, msfile_image), os.path.join(basepath, msfile_image))
split(vis=os.path.join(basepath, msfile), outputvis=os.path.join(basepath, msfile_image), datacolumn='all', width=chanstoavg)

msfile_bcal = msfile.split(".ms")[0][:-5]+f'_bcal_sb{chanstoavg}.ms'

print(f'MS File to rephase to bandpass calibrator: {msfile_bcal}')
print('\n')

if os.path.exists(os.path.join(basepath, msfile_bcal)):
    rmtree(os.path.join(basepath, msfile_bcal))
    #copytree(os.path.join(basepath, msfile_image), os.path.join(basepath, msfile_bcal))
split(vis=os.path.join(basepath, msfile), outputvis=os.path.join(basepath, msfile_bcal), datacolumn='all', width=chanstoavg)

msmd = msmetadata()
msmd.open(os.path.join(basepath, msfile))
fieldnames = msmd.fieldnames()

fieldname_image = fieldnames[field_image_idx]
fieldname_cal_list = fieldnames[field_cal_idx0: field_cal_idx1]
fieldname_cal = ', '.join(fieldname_cal_list)

print(f'Field Name (Image): {fieldname_image}')
print(f'Field Names (Calibration): {fieldname_cal}')
print('\n')

print('Reset base MS...')
print('\n')
print('Clear any old MODEL_DATA, CORRECTED_DATA, etc...')
clearcal(vis=os.path.join(basepath, msfile))
print('Delete Sky Model')
delmod(vis=os.path.join(basepath, msfile))
print('Removing Residual Tables')
for ext in ['.image','.mask','.model','.image.pbcor','.psf','.residual','.pb','.sumwt']:
    rmtables(os.path.join(basepath, msfile) + ext)
print('Removing Flags')
flagdata(vis=os.path.join(basepath, msfile), mode='unflag', flagbackup=False)
if os.path.exists(os.path.join(basepath, msfile)+'.flagversions'):
    rmtree(os.path.join(basepath, msfile)+'.flagversions')
print('\n')

print('Reset imaging MS...')
print('\n')
print('Clear any old MODEL_DATA, CORRECTED_DATA, etc...')
clearcal(vis=os.path.join(basepath, msfile_image))
print('Delete Sky Model')
delmod(vis=os.path.join(basepath, msfile_image))
print('Removing Residual Tables')
for ext in ['.image','.mask','.model','.image.pbcor','.psf','.residual','.pb','.sumwt']:
    rmtables(os.path.join(basepath, msfile_image) + ext)
print('Removing Flags')
flagdata(vis=os.path.join(basepath, msfile_image), mode='unflag', flagbackup=False)
if os.path.exists(os.path.join(basepath, msfile_image)+'.flagversions'):
    rmtree(os.path.join(basepath, msfile_image)+'.flagversions')
print('\n')

print('Reset bcal MS...')
print('\n')
print('Clear any old MODEL_DATA, CORRECTED_DATA, etc...')
clearcal(vis=os.path.join(basepath, msfile_bcal))
print('Delete Sky Model')
delmod(vis=os.path.join(basepath, msfile_bcal))
print('Removing Residual Tables')
for ext in ['.image','.mask','.model','.image.pbcor','.psf','.residual','.pb','.sumwt']:
    rmtables(os.path.join(basepath, msfile_bcal) + ext)
print('Removing Flags')
flagdata(vis=os.path.join(basepath, msfile_bcal), mode='unflag', flagbackup=False)
if os.path.exists(os.path.join(basepath, msfile_bcal)+'.flagversions'):
    rmtree(os.path.join(basepath, msfile_bcal)+'.flagversions')
print('\n')

fieldtoflag = fieldname_cal

print('Flagging Data for RFI in imaging MS...')
print('\n')
tfcrop_pars = {'timecutoff':3, 'freqcutoff':3, 'maxnpieces':1, 'growfreq':25, 'combinescans':True, 'ntime':'300s'}
flagdata(vis=os.path.join(basepath, msfile_image), field=fieldtoflag, mode='tfcrop', datacolumn='data', action='apply', flagbackup=False, **tfcrop_pars)

print('Flagging Data for RFI in calibration MS...')
print('\n')
tfcrop_pars = {'timecutoff':3, 'freqcutoff':3, 'maxnpieces':1, 'growfreq':25, 'combinescans':True, 'ntime':'300s'}
flagdata(vis=os.path.join(basepath, msfile_bcal), field=fieldtoflag, mode='tfcrop', datacolumn='data', action='apply', flagbackup=False, **tfcrop_pars)

# Open the measurement set
print('Producing RFI flagging diagnostic plot...')
print('\n')
ms_tool = ms()
ms_tool.open(os.path.join(basepath, msfile_bcal))
ms_tool.msselect({'field':fieldname_cal})
# Retrieve the data and flag columns
data = ms_tool.getdata(['data', 'flag'])
flags = data['flag'] # boolean flags
vis = data['data'] # complex visibilities
ms_tool.close()

# If there are multiple polarizations, average them to get a fraction flagged.
# Note: flags are boolean, so averaging converts them to a fractional value.
if flags.shape[0] > 1:
    flag_avg = np.mean(flags, axis=0)
else:
    flag_avg = flags[0]

# Compute the amplitude of the visibilities.
amp = np.abs(vis)  # shape: (npol, nchan, nrow)

# If there are multiple polarizations, combine them.
if amp.shape[0] > 1:
    # For flags, consider a sample flagged if any polarization is flagged.
    flag_mask = np.any(flags, axis=0)  # shape: (nchan, nrow)
    # Average the amplitude over polarizations.
    amp_avg = np.mean(amp, axis=0)       # shape: (nchan, nrow)
else:
    amp_avg = amp[0]
    flag_mask = flags[0]

# Create a masked array that masks out flagged samples.
masked_amp = np.ma.array(amp_avg, mask=flag_mask, fill_value=0.)
# Now, compute the bandpass by averaging over time (axis=1) for each frequency channel,
# ignoring the masked (flagged) samples.
bandpass_arr = np.mean(masked_amp, axis=1)
bandpass_norm = bandpass_arr/np.max(bandpass_arr)
bandpass_uncorr = np.mean(amp_avg, axis=1)
bandpass_uncorr_norm = bandpass_uncorr/np.max(bandpass_uncorr)

# Waterfall Plot

# Set new fontsize
rcParams['font.size'] = 10

# Open the measurement set
print('Producing RFI flagging diagnostic plot...')
print('\n')
ms_tool = ms()
ms_tool.open(os.path.join(basepath, msfile_bcal))
ms_tool.msselect({'field':fieldname_cal})
# Retrieve the data and flag columns
data = ms_tool.getdata(['data', 'flag'])
flags = data['flag'] # boolean flags
vis = data['data'] # complex visibilities
ms_tool.close()

# If there are multiple polarizations, average them to get a fraction flagged.
# Note: flags are boolean, so averaging converts them to a fractional value.
if flags.shape[0] > 1:
    flag_avg = np.mean(flags, axis=0)
else:
    flag_avg = flags[0]

# Compute the amplitude of the visibilities.
amp = np.abs(vis)  # shape: (npol, nchan, nrow)

# If there are multiple polarizations, combine them.
if amp.shape[0] > 1:
    # For flags, consider a sample flagged if any polarization is flagged.
    flag_mask = np.any(flags, axis=0)  # shape: (nchan, nrow)
    # Average the amplitude over polarizations.
    amp_avg = np.mean(amp, axis=0)       # shape: (nchan, nrow)
else:
    amp_avg = amp[0]
    flag_mask = flags[0]

# Create a masked array that masks out flagged samples.
masked_amp = np.ma.array(amp_avg, mask=flag_mask, fill_value=np.nan)
# Now, compute the bandpass by averaging over time (axis=1) for each frequency channel,
# ignoring the masked (flagged) samples.
bandpass_arr_mean = np.mean(masked_amp, axis=1)
bandpass_arr_sum = np.sum(masked_amp, axis=1) #/np.max(bandpass_arr)
bandpass_uncorr_mean = np.mean(amp_avg, axis=1)
bandpass_uncorr_sum = np.sum(amp_avg, axis=1) #/np.max(bandpass_uncorr)

# Waterfall Plot

# Set new fontsize
rcParams['font.size'] = 10

fig, (ax0, ax1, ax2, ax3, ax4) = plt.subplots(nrows=1, ncols=5,
                                    figsize=(30, 5))
im = ax0.imshow(flag_avg, aspect='auto', origin='lower', cmap='binary')
ax0.set_xlabel('Time Index')
ax0.set_ylabel('Frequency Channel')
ax0.set_title('Waterfall Plot of Flag Column')
plt.colorbar(im, ax=ax0, label='Fraction Flagged')

# Fraction of flagged data per frequency channel (averaged over time)
flag_fraction = np.mean(flag_avg, axis=1)
ax1.plot(flag_fraction, drawstyle='steps-mid', c='k')
ax1.set_xlabel('Frequency Channel')
ax1.set_ylabel('Fraction of Flagged Data')
#ax1.set_xlim(350, 400)
ax1.set_title('Fraction of Flagged Data per Frequency Channel')

amp_mean = np.nanmean(masked_amp)
amp_std = np.nanstd(masked_amp)
im = ax2.imshow(masked_amp, vmin=amp_mean-1*amp_std, vmax=amp_mean+1*amp_std, aspect='auto', origin='lower')
ax2.set_xlabel('Time Index')
ax2.set_ylabel('Frequency Channel')
ax2.set_title('Corrected Waterfall Plot')
plt.colorbar(im, ax=ax2)

# Plot the corrected bandpass
ax3.plot(bandpass_uncorr_mean/np.max(bandpass_uncorr_mean), drawstyle='steps-mid', c='k', label='Mean')
#ax3.plot(bandpass_uncorr_sum/np.max(bandpass_uncorr_sum), drawstyle='steps-mid', c='r', label='Sum')
ax3.set_xlabel('Frequency Channel')
ax3.set_ylabel('Mean Amplitude')
#ax2.set_xlim(350, 400)
ax3.set_title('Uncorrected Bandpass')
ax3.legend()

# Plot the corrected bandpass
ax4.plot(bandpass_arr_mean/np.max(bandpass_arr_mean), drawstyle='steps-mid', c='k', label='Mean')
ax4.plot(bandpass_arr_sum/np.max(bandpass_arr_sum), drawstyle='steps-mid', c='r', label='Sum')
ax4.set_xlabel('Frequency Channel')
ax4.set_ylabel('Mean Amplitude')
#ax2.set_xlim(350, 400)
ax4.set_title('Corrected Bandpass')
ax4.legend()

fig.savefig(os.path.join(basepath, f'{msfile_bcal.split(".ms")[0]}_RFI_diagnostic_f{field_cal_idx0}f{field_cal_idx1}.pdf'))
print('RFI flagging diagnostic plot saved!')
print('\n')

# Revert fontsize
rcParams['font.size'] = 30

print('Finding a bandpass calibrator in the field...')
print('\n')

while True:
    try:
        sys.path.insert(0, '/data/jfaber/dsa110-contimg/sandbox/scripts')
        import find_calibrators
        importlib.reload(find_calibrators)
        from find_calibrators import find_calibrator

        calibrator_name, calibrator_coord_hms, calibrator_coord_deg, flux_nvss = find_calibrator(basepath, msfile_bcal, fieldname=fieldname_image, top_n=1, pbfrac=0.25)
        print('________________________________________________________________________________________')
        print(f'Calibrator: {calibrator_name}')
        print(f'Calibrator Coordinates (hms): {calibrator_coord_hms}')
        print(f'Calibrator Coordinates (deg): {calibrator_coord_deg}')
        print(f'Calibrator Flux: {flux_nvss} Jy')
        break
    except Exception as e:
        print(f"An error occurred: {e}")

while True:
    try:
        sys.path.insert(0, '/data/jfaber/dsa110-contimg/sandbox/scripts')
        import make_skymodel_cl_mf
        importlib.reload(make_skymodel_cl_mf)
        from make_skymodel_cl_mf import make_skymodel

        # Number of bright sources to include in the sky model
        top_n = 200

        print(f'Generating a sky model with the top {top_n} brightest NVSS sources...')

        # Define filename strings
        ra_str = f"{msfile.split('_')[1][2:5]}p{msfile.split('_')[1][6:9]}"
        dec_str = f"{msfile.split('_')[2][4:6]}p{msfile.split('_')[2][7:8]}"
        clfile = f'nvss_top{top_n}_{ra_str}_{dec_str}.cl'
        cllabel = clfile.split('.')[0]

        if os.path.exists(os.path.join(basepath, f'nvss_top{top_n}_{ra_str}_{dec_str}.cl')):
            rmtree(os.path.join(basepath, f'nvss_top{top_n}_{ra_str}_{dec_str}.cl'))

        nvss_catalog = make_skymodel(basepath, msfile_bcal, fieldname=fieldname_image, top_n=top_n, pbfrac=0.5)
        break
    except Exception as e:
        print(f"Server disconnected, trying again!")

print('\n')

sys.path.insert(0, '/data/jfaber/dsa110-contimg/sandbox/scripts')
import image_skymodel_cl
importlib.reload(image_skymodel_cl)
from image_skymodel_cl import image_skymodel

print('Imaging the sky model and saving plot...')

wcs_2d_coords_x, wcs_2d_coords_y, phasecenter = image_skymodel(basepath, msfile_bcal, fieldname_image, nvss_catalog, top_n=top_n, nx=4800, ny=4800, cellx='3arcsec', celly='3arcsec', mode='mfs', phasecenter=None)
startmodel_nvss = cllabel + '.image'
print(f'Phase center of the total field: {phasecenter}')
print('\n')

# Load the FITS image
fitsfile = cllabel + '.image.fits'
fits_file = os.path.join(basepath, fitsfile)
hdu = fits.open(fits_file)[0]
print(f'Image Shape: {hdu.data[0, 0, :, :].shape}')
freq_val = hdu.header['CRVAL3']  # Central frequency (e.g., 1.404882070235e+09 Hz)
stokes_val = hdu.header['CRVAL4']  # Default Stokes parameter (e.g., 1)
wcs = WCS(hdu.header)

slices = (0, 0)  # Adjust this based on your FITS file (e.g., for time or frequency)
wcs_2d = WCS(hdu.header, naxis=2)

# Display the FITS image
fig, ax = plt.subplots(subplot_kw={'projection': wcs_2d}, figsize = (25, 25))
#norm = ImageNormalize(hdu.data[0, 0, :, :], interval=PercentileInterval(99), stretch=LogStretch())
norm = ImageNormalize(hdu.data[0, 0, :, :], interval=ZScaleInterval(), stretch=PowerStretch(a=1))
ax.imshow(hdu.data[0, 0, :, :], cmap='gray_r', norm=norm, origin='lower')

# Overlay circles around NVSS sources on the FITS image
for xi, yi in zip(wcs_2d_coords_x, wcs_2d_coords_y):
    circle = Circle((xi, yi), radius=50, edgecolor='red', facecolor='none', lw=0.8, transform=ax.get_transform('pixel'))
    ax.add_patch(circle)

cal_ra_deg, cal_dec_deg = calibrator_coord_deg
cal_coord_x, cal_coord_y = wcs_2d.world_to_pixel_values(cal_ra_deg, cal_dec_deg)
ax.scatter(cal_coord_x, cal_coord_y, marker='*', s=1000, c='red', alpha=0.5, label = 'Bandpass Calibrator')

ax.set_xlabel('RA')
ax.set_ylabel('Dec')
ax.legend()

# Show the plot
plt.title('Sky Model with NVSS Sources')
plt.grid(color='k', ls='dotted')
fig.savefig(os.path.join(basepath, f'{cllabel}_image.pdf'))
print('\n')

#bcalfield = fieldname
bcalfield = fieldname_cal
bcalfile = 'J2253+1608_2025-03-18T19:00:04_f0f23.bcal'

print(f'Not calculating bandpass solutions! Using previously calculated solution table {bcalfile}...')
print('\n')

#if bcalfield is None:
#    bcalfile = f'{calibrator_name}_{msdate}_allfields.bcal'
#
#else:
#    bcalfile = f'{calibrator_name}_{msdate}_f{field_cal_idx0}f{field_cal_idx1}.bcal'

    
#if os.path.exists(os.path.join(basepath, bcalfile)):
#    rmtree(os.path.join(basepath, bcalfile))
#
#if bcalfield is None:
#
#    bandpass(vis=os.path.join(basepath, msfile_bcal_cntrd),
#            field='',
#            caltable=os.path.join(basepath, bcalfile),
#            refant=refant,
#            solint='inf',
#            bandtype='B',
#            combine='scan, obs, field',
#            uvrange='>' + uvrange)
#
#else:
#
#    bandpass(vis=os.path.join(basepath, msfile_bcal_cntrd),
#            field=bcalfield,
#            caltable=os.path.join(basepath, bcalfile),
#            refant=refant,
#            solint='inf',
#            bandtype='B',
#            combine='scan, obs, field',
#            uvrange='>' + uvrange)

#print('Checking for bad antennas so we know which to flag before imaging...')
#print('\n')
#
#sys.path.insert(0, '/data/jfaber/dsa110-contimg/sandbox/scripts')
#import check_ants
#importlib.reload(check_ants)
#from check_ants import compute_antenna_quality
#
## Run the improved quality check on the calibration table
##cal_table = os.path.join(basepath, bcalfile)
#ant_stats, bad_antennas = compute_antenna_quality(os.path.join(basepath, bcalfile))
##print(f"\nIdentified {len(bad_antennas)} bad antennas: {bad_antennas}")
#ant_add_pad = ['pad' + str(i+1) for i in bad_antennas]
#ant_names = ', '.join(ant_add_pad)
#print(f'\nIdentified {len(bad_antennas)} bad antennas: {ant_names}')

print('Applying bandpass solutions to non-centered MS...')
print('\n')

#applycal(vis=os.path.join(basepath, msfile_bcal_cntrd),
#        field=fieldname_cal,
#        gaintable=os.path.join(basepath, bcalfile))

applycal(vis=os.path.join(basepath, msfile_bcal),
        field=fieldname_cal,
        gaintable=os.path.join(basepath, bcalfile))

print('Copying non-centered bandpass-corrected MS for next steps...')
msfile_bcal_corr = msfile_bcal.split(".ms")[0] + '_corr.ms'
split(vis=os.path.join(basepath, msfile_bcal), outputvis=os.path.join(basepath, msfile_bcal_corr), datacolumn='corrected', width=chanstoavg)

print('Placing the sky model in the MODEL column of the non-centered MS...')
print('\n')

#for fieldname in field_names:      
#ft(vis=os.path.join(basepath, msfile_bcal_cntrd), 
#    field=fieldname_cal,
#    complist=os.path.join(basepath, clfile), 
#    reffreq='1.4GHz',
#    usescratch=True)

ft(vis=os.path.join(basepath, msfile_bcal_corr), 
    field=fieldname_cal,
    complist=os.path.join(basepath, clfile), 
    reffreq='1.4GHz',
    usescratch=True)

#print(f'Copy the MS and place the phasecenter on the {calibrator_name}...')
print(f'Copy the MS and place the phasecenter for all columns on the center of the total field at {phasecenter}...')
print('\n')

msfile_bcal_cntrd = msfile_bcal_corr.split(".ms")[0]+'_cntrd.ms'

#channelstoavg=16
if os.path.exists(os.path.join(basepath, msfile_bcal_cntrd)):
    rmtree(os.path.join(basepath, msfile_bcal_cntrd))
    rmtree(os.path.join(basepath, msfile_bcal_cntrd.split(".ms")[0]+'.flagversions'))

#mstransform(vis=os.path.join(basepath, msfile_bcal), outputvis=os.path.join(basepath, msfile_bcal_cntrd), phasecenter=calibrator_coord_hms)
mstransform(vis=os.path.join(basepath, msfile_bcal_corr), outputvis=os.path.join(basepath, msfile_bcal_cntrd), phasecenter=phasecenter, datacolumn='all')

print('Performing phase-only gain calibration on non-centered MS...')
print('\n')

#bcalfield = fieldname
pcalfield = fieldname_cal

if pcalfield is None:
    pcalfile = f'{calibrator_name}_{msdate}_allfields.pcal'
else:
    pcalfile = f'{calibrator_name}_{msdate}_f{field_cal_idx0}f{field_cal_idx1}.pcal'

if os.path.exists(os.path.join(basepath, pcalfile)):
    rmtree(os.path.join(basepath, pcalfile))

if pcalfield is None:

    gaincal(vis=os.path.join(basepath, msfile_bcal_cntrd),
            field='',
            caltable=os.path.join(basepath, pcalfile),
            refant=refant,
            solint='inf',
            calmode='p',
            gaintype='G',
            minsnr=3,
            #gaintable = ['J1132+1628_2025-03-02T08:43:06_f0f23.bcal'],
            combine='scan, obs, field',
            uvrange='>'+uvrange)

else:

    gaincal(vis=os.path.join(basepath, msfile_bcal_cntrd),
            field=pcalfield,
            caltable=os.path.join(basepath, pcalfile),
            refant=refant,
            solint='inf',
            calmode='p',
            gaintype='G',
            minsnr=3,
            #gaintable = ['J1132+1628_2025-03-02T08:43:06_f0f23.bcal'],
            combine='scan, obs, field',
            uvrange='>'+uvrange)

"""
print('Applying phase-only gain solutions to centered and non-centered MS...')
print('\n')

applycal(vis=os.path.join(basepath, msfile_bcal_cntrd),
        field=fieldname_cal,
        gaintable=os.path.join(basepath, pcalfile))

applycal(vis=os.path.join(basepath, msfile_bcal),
        field=fieldname_cal,
        gaintable=os.path.join(basepath, pcalfile))

print('Flagging antennas based on bandpass solutions, autocorrelating, shadowing, clipping, on centered and non-centered MS...')
print('\n')

flagdata(vis=os.path.join(basepath, msfile_image), mode='manual', antenna=ant_names)
flagdata(vis=os.path.join(basepath, msfile_image), mode='manual', autocorr=True, flagbackup=False)
flagdata(vis=os.path.join(basepath, msfile_image), mode='shadow', tolerance=0.0, flagbackup=False)
flagdata(vis=os.path.join(basepath, msfile_image), mode='clip', clipzeros=True, flagbackup=False)

flagdata(vis=os.path.join(basepath, msfile_bcal_cntrd), mode='manual', antenna=ant_names)
flagdata(vis=os.path.join(basepath, msfile_bcal_cntrd), mode='manual', autocorr=True, flagbackup=False)
flagdata(vis=os.path.join(basepath, msfile_bcal_cntrd), mode='shadow', tolerance=0.0, flagbackup=False)
flagdata(vis=os.path.join(basepath, msfile_bcal_cntrd), mode='clip', clipzeros=True, flagbackup=False)

flagdata(vis=os.path.join(basepath, msfile_bcal), mode='manual', antenna=ant_names)
flagdata(vis=os.path.join(basepath, msfile_bcal), mode='manual', autocorr=True, flagbackup=False)
flagdata(vis=os.path.join(basepath, msfile_bcal), mode='shadow', tolerance=0.0, flagbackup=False)
flagdata(vis=os.path.join(basepath, msfile_bcal), mode='clip', clipzeros=True, flagbackup=False)

print('\n')
print('Imaging with tclean...')
print('\n')

os.chdir(basepath)
#for fieldname in field_names[11]:
imsize_x, imsize_y = 4800, 4800
cell_res = '3arcsec'
weighttype = 'natural'
niter = 10000
weight = 0.5
uvrange = '1klambda'
imagetype = 'clean'
imageparams = f'{imagetype}_{weighttype}{weight}_uv{uvrange}_{imsize_x}x{cell_res[:4]}_nitr{niter}'
imagename = f'{msfile_bcal.split(".ms")[0]}_f{field_cal_idx0}f{field_cal_idx1}_{imageparams}'
tclean(vis=os.path.join(basepath, msfile_bcal),
    field=fieldname_cal,            
    imagename=os.path.join(basepath, imagename),
    specmode='mfs',
    deconvolver='hogbom',
    gridder='wproject',
    wprojplanes=-1,  # auto (if using wproject)
    niter=niter,             
    threshold='0.005Jy',
    interactive=False,
    imsize=[imsize_x, imsize_y],
    cell=[cell_res], 
    weighting=weighttype,
    robust=weight,
    pblimit=0.25,
    psfcutoff=0.5,
    uvrange='>'+uvrange,
    phasecenter=phasecenter,
    #startmodel=startmodel_nvss
    )

print(f'Saving clean image {os.path.join(basepath, imagename)}...')
print('\n')

from astropy.wcs.utils import skycoord_to_pixel

if os.path.exists(os.path.join(basepath, imagename) + '.image.fits'):
    os.remove(os.path.join(basepath, imagename) + '.image.fits')
exportfits(os.path.join(basepath, imagename) + '.image', os.path.join(basepath, imagename) + '.image.fits')

# Load the FITS image
fits_file = os.path.join(basepath, imagename) + '.image.fits'
hdu = fits.open(fits_file)[0]
freq_val = hdu.header['CRVAL3']  # Central frequency (e.g., 1.404882070235e+09 Hz)
stokes_val = hdu.header['CRVAL4']  # Default Stokes parameter (e.g., 1)
wcs = WCS(hdu.header)

slices = (0, 0)  # Adjust this based on your FITS file (e.g., for time or frequency)
wcs_2d = WCS(hdu.header, naxis=2)

# Display the FITS image
fig, ax = plt.subplots(subplot_kw={'projection': wcs_2d}, figsize = (25, 25))
#norm = ImageNormalize(hdu.data[0, 0, :, :], interval=PercentileInterval(99), stretch=LogStretch())
norm = ImageNormalize(hdu.data[0, 0, :, :], interval=ZScaleInterval(), stretch=PowerStretch(a=4))
ax.imshow(hdu.data[0, 0, :, :], cmap='gray_r', norm=norm, origin='lower')
#ax.imshow(hdu.data[0, 0, :, :], cmap='gray_r', origin='lower', vmax = 0.1*np.max(hdu.data[0, 0, :, :])) #norm=norm, origin='lower', vmax = 0.1*np.max(hdu.data[0, 0, :, :]))

# Overlay circles around NVSS sources on the FITS image
for xi, yi in zip(wcs_2d_coords_x, wcs_2d_coords_y):
    circle = Circle((xi, yi), radius=50, edgecolor='red', facecolor='none', lw=0.8, transform=ax.get_transform('pixel'))
    ax.add_patch(circle)

# Define the sky coordinate for the magnetar (J2000 is equivalent to ICRS)
mag_coord = SkyCoord('05:01:06.76', '+45:16:33.92', unit=(u.hourangle, u.deg), frame='icrs')
# Convert the sky coordinate to pixel coordinates using your 2D WCS
x_mag, y_mag = skycoord_to_pixel(mag_coord, wcs_2d)
circle_mag_1 = Circle((x_mag, y_mag), radius=50, edgecolor='purple', facecolor='none', lw=1.2, transform=ax.get_transform('pixel'))
ax.add_patch(circle_mag_1)
circle_mag_2 = Circle((x_mag, y_mag), radius=60, edgecolor='purple', facecolor='none', lw=1.2, transform=ax.get_transform('pixel'))
ax.add_patch(circle_mag_2)
circle_mag_3 = Circle((x_mag, y_mag), radius=70, edgecolor='purple', facecolor='none', lw=1.2, transform=ax.get_transform('pixel'))
ax.add_patch(circle_mag_3)
circle_mag_4 = Circle((x_mag, y_mag), radius=80, edgecolor='purple', facecolor='none', lw=1.2, transform=ax.get_transform('pixel'))
ax.add_patch(circle_mag_4)

ax.set_xlabel('RA')
ax.set_ylabel('Dec')

# Show the plot
plt.title('Clean Image')
plt.grid(color='k', ls='dotted')
fig.savefig(os.path.join(basepath, f'{imagename}.image.pdf'))
plt.show()
"""