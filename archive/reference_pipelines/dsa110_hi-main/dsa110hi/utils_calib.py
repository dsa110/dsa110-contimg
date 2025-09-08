import os
from shutil import rmtree
import numpy as np
import matplotlib.pyplot as plt
from casatasks import rmtables, gaincal, bandpass, flagdata, flagmanager, applycal, concat
from casatools import table
# from casacore.tables import table

from importlib.resources import files
from dsa110hi.utils_msaccess import plot_delay, plot_bpass, zero_field_ids, restore_field_ids

tb = table()

def solve_delay(incoming_file,
                output_file_path,
                output_file_name='delay',output_file_overwrite=False,
                incoming_cal_tables=[],
                refant=None, minsnr=3, selection={}, # selection can be used for things like timerange - follow casa syntax for selectdata
                plot_solutions=True, plot_solutions_saveonly=True,
                ):
    """Find delay solutions
    
    Parameters
    ----------
    incoming_file : str
        Full path to MS files to use
    output_file_path : str
        Directory where calibration solutions will be stored
    output_file_name : str
        Name of the calibration table to be written
    output_file_overwrite : bool
        If False, an error is raised if the proposed file name already exists
    incoming_cal_tables : list
        Full paths to calibration tables to apply before solution
    refant : str
        Name of the reference antenna (of form 'padN')
    minsnr : float
        Minimum SNR for a solution to be accepted
    plot_solutions : bool
        Make a plot of the solutions (delay vs antenna) and save it as
        output_file_name+'_solution.png'
    plot_solutions_saveonly : bool
        If True the plot will be closed without display. If False it will be 
        left open such that a call to plt.show() will render the plot.    
    """

    # Check paths
    if not os.path.exists(output_file_path):
        os.mkdir(output_file_path)
    if os.path.exists(os.path.join(output_file_path,output_file_name)):
        if not output_file_overwrite:
            raise ValueError(f"{output_file_name} already exists")
        else:
            rmtables(os.path.join(output_file_path,output_file_name))

    # Do a delay solution
    gaincal(vis=incoming_file, 
            caltable=os.path.join(output_file_path,output_file_name),
            combine='scan,field', selectdata=True,
            refant=refant,
            minsnr=minsnr,
            solint='inf',
            gaintype='K',
            gaintable=incoming_cal_tables,
            **selection
            )
    
    # Plot solution if requested
    if plot_solutions:
        fig = plot_delay(os.path.join(output_file_path,output_file_name),os.path.join(output_file_path,output_file_name))
        if plot_solutions_saveonly:
            plt.close(fig[0])

def solve_bpass(incoming_file,
                output_file_path,
                output_file_name='bpass',output_file_overwrite=False,
                incoming_cal_tables=[],
                refant=None, minsnr=5, selection={}, # selection can be used for things like timerange - follow casa syntax for selectdata
                plot_solutions=True, plot_solutions_pols=None, plot_solutions_ants=None, plot_solutions_saveonly=True,
                ):
    """Find bandpass solutions
    
    Parameters
    ----------
    incoming_file : str
        Full paths to MS file to use
    output_file_path : str
        Directory where calibration solutions will be stored
    output_file_name : str
        Name of the calibration table to be written
    output_file_overwrite : bool
        If False, an error is raised if the proposed file name already exists
    incoming_cal_tables : list
        Full paths to calibration tables to apply before solution
    refant : str
        Name of the reference antenna (of form 'padN')
    minsnr : float
        Minimum SNR for a solution to be accepted
    plot_solutions : bool
        Make a plot of the solutions (phase, amp vs frequency for each antenna) and save it as
        output_file_name+'_solution.png'
    plot_solutions_pols : list
        List of ints (indices) of polarizations to plot. Defaults to [0,1].
    plot_solutions_ants : list
        List of strings (names) or ints (antenna indices) of antennas to plot.
        Defaults to the list of all valid antennas.
    plot_solutions_saveonly : bool
        If True the plot will be closed without display. If False it will be 
        left open such that a call to plt.show() will render the plot.    
    """

    # Check paths
    if not os.path.exists(output_file_path):
        os.mkdir(output_file_path)
    if os.path.exists(os.path.join(output_file_path,output_file_name)):
        if not output_file_overwrite:
            raise ValueError(f"{output_file_name} already exists")
        else:
            rmtables(os.path.join(output_file_path,output_file_name))

    # Do bandpass solution
    bandpass(vis=incoming_file, 
             caltable=os.path.join(output_file_path,output_file_name),
             refant=refant,
             minsnr=minsnr,
             solint='inf',
             bandtype='B',
             gaintable=incoming_cal_tables,
             combine='scan,field', selectdata=True,**selection
             )

    # Plot solutions if requested
    if plot_solutions:
        f1, f2 = plot_bpass(os.path.join(output_file_path,output_file_name),os.path.join(output_file_path,output_file_name),plot_solutions_pols,plot_solutions_ants)

        if plot_solutions_saveonly:
            for f in f1+f2:
                plt.close(f[0])

def flag(incoming_file, 
         reset_flags=False,
         flag_auto=True,
         flag_shadow=True,
         flag_zeros=True,
         flag_bad_ants=None,
         flag_uvrange=None,
         flag_tfcrop=False, tfcrop_pars={'timecutoff':3.5, 'freqcutoff':3, 'maxnpieces':1, 'growfreq':25, 'combinescans':True, 'ntime':'300s'},
         flag_aoflag=True, aoflagger_strategy=None,
         flag_merge_fields=True
         ):
    """Wrapper for standard flagging steps for the DSA-110 pipeline
    
    Parameters
    ----------
    incoming_file : str
        Path to file for flagging
    reset_flags : bool
        If True all prior flags will be deleted (default is False)
    flag_auto : bool
        Whether to flag autocorrelations (default is True)
    flag_shadow : bool
        Whether to flag shadowed antennas (default is True)
    flag_zeros : bool
        Whether to flag visibilities that are zero (default is True)
    flag_bad_ants : str
        String containing a comma separated list of antenna names to flag,
        e.g. 'pad1,pad101'
    flag_uvrange : str
        String specifying a uvrange to flag, for example '<250m' will remove
        baselines shorter than 250 meters.
    flag_tfcrop : bool
        Whether to run the CASA TFCrop routine (default is True)
    flag_merge_fields : bool
        Whether to treat all fields as a single observation when running
        TFCrop (default is True, apropriate for drift scans)
    """

    # Unflag all
    if reset_flags:
        flagdata(incoming_file, mode='unflag', flagbackup=False)
        if os.path.exists(incoming_file+'.flagversions'):
            rmtree(incoming_file+'.flagversions')

    # Basic flagging
    if flag_auto:
        flagdata(incoming_file, mode='manual', autocorr=True, flagbackup=False)
    if flag_shadow:
        flagdata(incoming_file, mode='shadow', tolerance=0.0, flagbackup=False)
    if flag_zeros:
        flagdata(incoming_file, mode='clip', clipzeros=True, flagbackup=False)

    # Flag antennas and/or baselines
    if flag_bad_ants is not None:
        flagdata(incoming_file, mode='manual', antenna=flag_bad_ants, flagbackup=False)
    if flag_uvrange is not None:
        flagdata(incoming_file, mode='manual', uvrange=flag_uvrange, flagbackup=False)

    flagmanager(incoming_file, mode='save', versionname='basic-cuts')

    # TF crop and AOFlagger don't work across field IDs, but we need them to
    # for the drift scan. The hacky solution to this is to manually change all 
    # of the field labels in the MS, flag, and then change them back.
    if flag_merge_fields:
        zero_field_ids(incoming_file,backend='casa')

    if flag_tfcrop:
        # Do flagging
        flagdata(incoming_file, mode='tfcrop', datacolumn='data', action='apply', display='none', flagbackup=False, **tfcrop_pars)
        flagmanager(incoming_file, mode='save', versionname='tfcrop')

    if flag_aoflag:
        if aoflagger_strategy is None:
            packagepath = files('dsa110hi')
            aoflagger_strategy = packagepath.joinpath('resources','aoflagger_default.lua')

        call = f'aoflagger -strategy {aoflagger_strategy} {incoming_file}'
        os.system(call)

    if flag_merge_fields:
        restore_field_ids(incoming_file, del_idfile=True, backend='casa')

def apply_cal(incoming_files, 
              incoming_cal_tables=[],
              output_file=os.path.join(os.sep,'pipeline','calibrated','calibrated.ms'), output_file_overwrite=False,
              ):
    """Given a list of measurement sets, concatenate them, apply calibration tables
    and save the calibrated MS
    
    Parameters
    ----------
    incoming_files : list
        List of paths for the individual MSes
    incoming_cal_tables : list
        List of pahts for the calibration tables to apply
    output_file : str
        Path where the concatenated, calibrated file should be saved
    output_file_overwrite : bool
        If True (default), any existing measurement set in the output_file
        path will be deleted and replaced.
    """

    if incoming_files == output_file:
        raise ValueError("Incoming and output files can't have the same name")
    if os.path.exists(output_file):
        if output_file_overwrite:
            rmtables(output_file)
        else:
            raise RuntimeError(output_file+' already exists')    

    if isinstance(incoming_files,list):
        concat(incoming_files, concatvis=output_file)
    else:
        os.system(f"cp -r {incoming_files} {output_file}")
    
    applycal(output_file, gaintable=incoming_cal_tables, calwt=False)




def solve_phase(incoming_file=[],
                incoming_cal_tables=[],
                output_file_path=os.path.join(os.sep,'pipeline','cal_solutions'),output_file_name='gain',output_file_overwrite=False,
                calmode='p',
                refant=None, solint='int', minsnr=5, selection={}, # selection can be used for things like timerange - follow casa syntax for selectdata
                plot_solutions=True, plot_solutions_ants=None, plot_solutions_saveonly=True,
                ):
    """Find gain solutions
    
    Parameters
    ----------
    incoming_file : list
        Full paths to MS files to use
    incoming_cal_tables : list
        Full paths to calibration tables to apply before solution
    output_file_path : str
        Directory where calibration solutions will be stored
    output_file_name : str
        Name of the calibration table to be written
    output_file_overwrite : bool
        If False, an error is raised if the proposed file name already exists
    calmode : 'a', 'p', or 'ap'
        Calibration mode to use 'a' for amplitude, 'p' for phase, 'ap' for both.
        Defaults to 'p'.
    refant : str
        Name of the reference antenna (of form 'padN')
    minsnr : float
        Minimum SNR for a solution to be accepted
    solint : str
        String specifying the time to use for solutions. 'int' for dump time, 'inf' for whole
        available time range, '30s' for 30 second time range, etc.
    plot_solutions : bool
        Make a plot of the solutions (phase, amp vs frequency for each antenna) and save it as
        output_file_name+'_solution.png'
    plot_solutions_ants : list
        List of floats (names) or ints (antenna indices) of antennas to plot.
        Defaults to the list of all valid antennas.
    plot_solutions_saveonly : bool
        If True the plot will be closed without display. If False it will be 
        left open such that a call to plt.show() will render the plot.    
    """

    # Check paths
    if not os.path.exists(output_file_path):
        os.mkdir(output_file_path)
    if os.path.exists(os.path.join(output_file_path,output_file_name)):
        if not output_file_overwrite:
            raise ValueError(f"{output_file_name} already exists")
        else:
            rmtables(os.path.join(output_file_path,output_file_name))

    # Do gain solution
    gaincal(vis=incoming_file,caltable=os.path.join(output_file_path,output_file_name),
            combine='scan,field', 
            solint=solint,refant=refant,gaintype='G',calmode=calmode,
            gaintable=incoming_cal_tables,
            interp=['','nearest'],
            selectdata=True,**selection)

    # Plot solutions if requested
    if plot_solutions:
        f1, f2 = plot_gain(os.path.join(output_file_path,output_file_name),os.path.join(output_file_path,output_file_name),plot_solutions_ants,solution_type=calmode)

        if plot_solutions_saveonly:
            for f in f1+f2:
                plt.close(f)