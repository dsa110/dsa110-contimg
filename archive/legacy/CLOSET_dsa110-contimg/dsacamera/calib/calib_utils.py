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

def sort_msfiles(basepath):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))
    
    msfiles = [file for file in os.listdir(basepath) if file.endswith('.ms')]
    msfiles_sorted = sorted(msfiles, key=lambda fname: float(fname.split("_ra")[1].split("_")[0]))

    return msfiles_sorted

def gen_fieldnames(msfile, basepath, fields=(0,23)):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))

    msmd = msmetadata()
    msmd.open(os.path.join(basepath, 'msfiles', 'avg', msfile))
    fieldnames_msmd = msmd.fieldnames()
    first_field, last_field = fields
    print(f'Specified field range goes from {first_field} to {last_field}')
    print('\n')
    fieldnames_list = fieldnames_msmd[first_field:last_field]
    fieldnames = ', '.join(fieldnames_list)

    return fieldnames, first_field, last_field

def downchan_msfile(msfile, 
                    basepath, 
                    nchan=4
                    ):
    
    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))

    msfile_avg = f"{msfile.split('.ms')[0]}_sb{nchan}.ms"

    if os.path.exists(os.path.join(basepath, 'msfiles', 'avg', msfile_avg)):
        print('Downchannelized file already exists! This will be deleted and remade...')
        print('\n')
        rmtree(os.path.join(basepath, 'msfiles', 'avg', msfile_avg))
    if os.path.exists(os.path.join(basepath, 'msfiles', 'avg', msfile_avg)+'.flagversions'):
        rmtree(os.path.join(basepath, 'msfiles', 'avg', msfile_avg)+'.flagversions')

    #else:
    print(f'Averaging over every {nchan} channels in MS: {msfile}')
    print('\n')

    split(vis=os.path.join(basepath, 'msfiles', 'base', msfile), outputvis=os.path.join(basepath, 'msfiles', 'avg', msfile_avg), datacolumn='all', width=nchan)

    print(f'Downchannelized MS: {msfile_avg}')
    print('\n')

    return msfile_avg

def reset_msfile(msfile, 
                 basepath,
                 filetype='avg'
                 ):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))
    
    print(f'Resetting model/corrected columns, tables, and flags in {msfile}...')
    print('\n')
    print('Clear any old MODEL_DATA, CORRECTED_DATA, etc...')
    clearcal(vis=os.path.join(basepath, 'msfiles', f'{filetype}', msfile))
    print('Delete Sky Model')
    delmod(vis=os.path.join(basepath, 'msfiles', f'{filetype}', msfile))
    print('Removing Residual Tables')
    for ext in ['.image','.mask','.model','.image.pbcor','.psf','.residual','.pb','.sumwt']:
        rmtables(os.path.join(basepath, 'msfiles', f'{filetype}', msfile) + ext)
    print('Removing Flags')
    flagdata(vis=os.path.join(basepath, 'msfiles', f'{filetype}', msfile), mode='unflag', flagbackup=False)
    if os.path.exists(os.path.join(basepath, 'msfiles', f'{filetype}', msfile)+'.flagversions'):
        rmtree(os.path.join(basepath, 'msfiles', f'{filetype}', msfile)+'.flagversions')
    print('\n')

    return

def flag_rfi(msfile, 
             basepath, 
             fields=(0, 23), 
             calmode='tfcrop', 
             calcolumn='data', 
             timecutoff=3, 
             freqcutoff=3, 
             maxnpieces=1, 
             growfreq=25, 
             combinescans=True, 
             ntime='300s', 
             diagnostic_plot=False
             ):
    
    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))

    #msmd = msmetadata()
    #msmd.open(os.path.join(basepath, 'msfiles', 'avg', msfile))
    #fieldnames_msmd = msmd.fieldnames()
    #first_field, last_field = fields
    #print(f'First field flagged is {first_field}, last field flagged is {last_field}')
    #print('\n')
    #fieldnames_list = fieldnames_msmd[first_field:last_field]
    #fieldnames = ', '.join(fieldnames_list)
    fieldnames, first_field, last_field = gen_fieldnames(msfile, basepath, fields)

    print(f'Flagging RFI in {msfile}...')
    print('\n')
    flagdata(vis=os.path.join(basepath, 'msfiles', 'avg', msfile), 
             field=fieldnames, 
             mode=calmode, 
             datacolumn=calcolumn, 
             action='apply', 
             timecutoff=timecutoff, 
             freqcutoff=freqcutoff, 
             maxnpieces=maxnpieces, 
             growfreq=growfreq, 
             combinescans=combinescans, 
             ntime=ntime
             )
    
    if diagnostic_plot:

        print('Producing RFI flagging diagnostic plot...')
        print('\n')
        ms_tool = ms()
        ms_tool.open(os.path.join(basepath, 'msfiles', 'avg', msfile))
        ms_tool.msselect({'field':fieldnames})
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
        rcParams['font.size'] = 10 # Set new fontsize

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
        ax3.plot(bandpass_uncorr_sum/np.max(bandpass_uncorr_sum), drawstyle='steps-mid', c='r', label='Sum')
        ax3.set_xlabel('Frequency Channel')
        ax3.set_ylabel('Mean Amplitude')
        ax3.set_title('Uncorrected Bandpass')
        ax3.legend()

        # Plot the corrected bandpass
        ax4.plot(bandpass_arr_mean/np.max(bandpass_arr_mean), drawstyle='steps-mid', c='k', label='Mean')
        ax4.plot(bandpass_arr_sum/np.max(bandpass_arr_sum), drawstyle='steps-mid', c='r', label='Sum')
        ax4.set_xlabel('Frequency Channel')
        ax4.set_ylabel('Mean Amplitude')
        ax4.set_title('Corrected Bandpass')
        ax4.legend()

        figname = f'{msfile.split(".ms")[0]}_RFI_diagnostic_f{first_field}f{last_field}.pdf'
        fig.savefig(os.path.join(basepath, 'figures', 'rfi_diagnostic_figs', figname))
        print('RFI flagging diagnostic plot saved!')

    return

def flag_general(msfile, basepath):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))

    print('Flagging antennas based on bandpass solutions, autocorrelating, shadowing, clipping, on centered and non-centered MS...')
    print('\n')

    flagdata(vis=os.path.join(basepath, 'msfiles', 'avg', msfile), mode='manual', autocorr=True, flagbackup=False)
    flagdata(vis=os.path.join(basepath, 'msfiles', 'avg', msfile), mode='shadow', tolerance=0.0, flagbackup=False)
    flagdata(vis=os.path.join(basepath, 'msfiles', 'avg', msfile), mode='clip', clipzeros=True, flagbackup=False)

    return

def bandpass_calib(msfile,
                   basepath, 
                   clfile, 
                   phasecenter,  
                   fields=(0,23),
                   refant='pad103', 
                   uvrange='>1klambda'
                   ):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))
    
    msdate = msfile.split('_')[0]
    #msmd = msmetadata()
    #msmd.open(os.path.join(basepath, 'msfiles', 'avg', msfile))
    #fieldnames_msmd = msmd.fieldnames()
    #first_field, last_field = fields
    #fieldnames_list = fieldnames_msmd[first_field:last_field]
    #fieldnames = ', '.join(fieldnames_list)
    fieldnames, first_field, last_field = gen_fieldnames(msfile, basepath, fields)

    print(f'FT calibrator component list {clfile} into the MODEL column')

    ft(vis=os.path.join(basepath,  'msfiles', 'avg', msfile), 
       field=fieldnames,
       complist=os.path.join(basepath, 'skymodels', clfile), 
       reffreq='1.4GHz',
       usescratch=True)

    print(f'Copying the MS and placing the phasecenter on the calibrator {clfile.split(".ms")[0]}...')
    print('\n')

    msfile_cntrd = msfile.split('.ms')[0]+f'_cntrd.ms'

    if os.path.exists(os.path.join(basepath, 'msfiles', 'avg', msfile_cntrd)):
        rmtree(os.path.join(basepath, 'msfiles', 'avg', msfile_cntrd))

    mstransform(vis=os.path.join(basepath, 'msfiles', 'avg', msfile), outputvis=os.path.join(basepath, 'msfiles', 'avg', msfile_cntrd), phasecenter=phasecenter, datacolumn='all')

    print('Solving the bandpass on centered MS...')
    print('\n')

    bcalfile = f'{clfile.split(".cl")[0]}_{msdate}_f{first_field}f{last_field}.bcal'
        
    if os.path.exists(os.path.join(basepath, 'bcalfiles', bcalfile)):
        rmtree(os.path.join(basepath, 'bcalfiles', bcalfile))

    bandpass(vis=os.path.join(basepath, 'msfiles', 'avg', msfile_cntrd),
            field=fieldnames,
            caltable=os.path.join(basepath, 'bcalfiles', bcalfile),
            refant=refant,
            solint='inf',
            bandtype='B',
            combine='scan, obs, field',
            uvrange=uvrange)
    
    print(f'Bandpass solutions stored in {bcalfile}...')
    print('\n')

    #print(f'Applying bandpass solutions in table {bcalfile}')
    #applycal(vis=os.path.join(basepath, 'msfiles', 'avg', msfile),
    #        field=fieldnames,
    #        gaintable=os.path.join(basepath, 'bcalfiles', bcalfile))

    #msfile_corr = msfile_cntrd.split('.ms')[0] + '_corr.ms'

    #if os.path.exists(os.path.join(basepath, 'msfiles', 'avg', msfile_corr)):
    #    rmtree(os.path.join(basepath, 'msfiles', 'avg', msfile_corr))
    #    rmtree(os.path.join(basepath, 'msfiles', 'avg', msfile_corr.split('.ms')[0]+'.flagversions'))

    #print(f'Copying non-centered (bandpass) corrected MS to {msfile_corr}')
    #print('\n')

    #split(vis=os.path.join(basepath, 'msfiles', 'avg', msfile), outputvis=os.path.join(basepath, 'msfiles', 'avg', msfile_corr), datacolumn='corrected')
    #
    #print(f'Bandpass calibration solutions are ready! The calibrated file is {msfile_corr}')
    #print('\n')

    return bcalfile

def apply_bandpass(msfile, 
                   basepath,
                   bcalfile,
                   fields=(0,23)
                   ):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))

    fieldnames, first_field, last_field = gen_fieldnames(msfile, basepath, fields)
    
    print(f'Applying bandpass solutions in table {bcalfile}')
    print('\n')

    applycal(vis=os.path.join(basepath, 'msfiles', 'avg', msfile),
            field=fieldnames,
            gaintable=os.path.join(basepath, 'bcalfiles', bcalfile))
    
    print(f'Bandpass solutions applied!')
    print('\n')

    msfile_bcorr = msfile.split('.ms')[0] + '_bcorr.ms'

    if os.path.exists(os.path.join(basepath, 'msfiles', 'avg', msfile_bcorr)):
        print('Bandpass-corrected MS file already exists! This will be deleted and remade..')
        print('\n')
        rmtree(os.path.join(basepath, 'msfiles', 'avg', msfile_bcorr))
    if os.path.exists(os.path.join(basepath, 'msfiles', 'avg', msfile_bcorr)+'.flagversions'):
        rmtree(os.path.join(basepath, 'msfiles', 'avg', msfile_bcorr)+'.flagversions')

    print(f'Split off corrected column of bandpass-corrected MS {msfile} to {msfile_bcorr}')
    print('\n')

    split(vis=os.path.join(basepath, 'msfiles', 'avg', msfile), outputvis=os.path.join(basepath, 'msfiles', 'avg', msfile_bcorr), datacolumn='corrected')

    return msfile_bcorr


def phase_calib(msfile, 
                basepath, 
                clfile, 
                phasecenter,  
                fields=(0,23),
                refant='pad103', 
                uvrange='>1klambda'
                ):

    # Set path for CASA log files
    casalog.setlogfile(os.path.join(basepath, 'casa_logfile.log'))
    
    msdate = msfile.split('_')[0]
    #msmd = msmetadata()
    #msmd.open(os.path.join(basepath, 'msfiles', 'avg', msfile))
    #fieldnames_msmd = msmd.fieldnames()
    #first_field, last_field = fields
    #fieldnames_list = fieldnames_msmd[first_field:last_field]
    #fieldnames = ', '.join(fieldnames_list)
    fieldnames, first_field, last_field = gen_fieldnames(msfile, basepath, fields)

    print(f'FT skymodel as component list {clfile} into the MODEL column')
    print('\n')

    ft(vis=os.path.join(basepath,  'msfiles', 'avg', msfile), 
       field=fieldnames,
       complist=os.path.join(basepath, 'skymodels', 'pcal_skymodels', clfile), 
       reffreq='1.4GHz',
       usescratch=True)

    print(f'Copying the MS and placing the phasecenter on center of the full field (at boresight): {phasecenter}')
    print('\n')

    msfile_bcorr_cntrd = msfile.split('.ms')[0]+f'_cntrd.ms'

    if os.path.exists(os.path.join(basepath, 'msfiles', 'avg', msfile_bcorr_cntrd)):
        print('Phase-centered bandpass-corrected MS already exists! This will be deleted and remade...')
        print('\n')
        rmtree(os.path.join(basepath, 'msfiles', 'avg', msfile_bcorr_cntrd))

    mstransform(vis=os.path.join(basepath, 'msfiles', 'avg', msfile), outputvis=os.path.join(basepath, 'msfiles', 'avg', msfile_bcorr_cntrd), phasecenter=phasecenter, datacolumn='all')

    print('Solving the phase on centered MS...')
    print('\n')

    pcalfile = f'{clfile.split(".cl")[0]}_{msdate}_f{first_field}f{last_field}.pcal'
        
    if os.path.exists(os.path.join(basepath, 'pcalfiles', pcalfile)):
        print('Phase solutions table exists! This will be deleted and remade...')
        print('\n')
        rmtree(os.path.join(basepath, 'pcalfiles', pcalfile))

    gaincal(vis=os.path.join(basepath, 'msfiles', 'avg', msfile_bcorr_cntrd),
            field=fieldnames,
            caltable=os.path.join(basepath, 'pcalfiles', pcalfile),
            refant=refant,
            solint='inf',
            calmode='p',
            gaintype='G',
            minsnr=3,
            combine='scan, obs, field',
            uvrange=uvrange)

    return pcalfile

def apply_phase(msfile,
                basepath,
                pcalfile,
                fields=(0,23)
                ):

    fieldnames, first_field, last_field = gen_fieldnames(msfile, basepath, fields)

    print(f'Applying phase solutions in table {pcalfile}')
    print('\n')
    applycal(vis=os.path.join(basepath, 'msfiles', 'avg', msfile),
            field=fieldnames,
            gaintable=os.path.join(basepath, 'pcalfiles', pcalfile))

    print('Phase solutions applied!')
    print('\n')

    msfile_bpcorr = msfile.split('_bcorr.ms')[0] + '_bpcorr.ms'

    if os.path.exists(os.path.join(basepath, 'msfiles', 'avg', msfile_bpcorr)):
        print('Non-centered (phase and bandpass) corrected MS exists! This will be deleted and remade...')
        print('\n')
        rmtree(os.path.join(basepath, 'msfiles', 'avg', msfile_bpcorr))
    if os.path.exists(os.path.join(basepath, 'msfiles', 'avg', msfile_bpcorr)+'.flagversions'):
        rmtree(os.path.join(basepath, 'msfiles', 'avg', msfile_bpcorr)+'.flagversions')

    print(f'Splitting off non-centered (phase and bandpass) corrected MS {msfile_bpcorr}...')
    print('\n')

    split(vis=os.path.join(basepath, 'msfiles', 'avg', msfile), outputvis=os.path.join(basepath, 'msfiles', 'avg', msfile_bpcorr), datacolumn='all')
    
    print(f'The bandpass and phase calibrated MS is {msfile_bpcorr}')
    print('\n')

    return msfile_bpcorr