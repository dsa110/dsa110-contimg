import os
from shutil import rmtree
import numpy as np
import matplotlib.pyplot as plt
from casatasks import rmtables, gaincal, bandpass, flagdata, flagmanager, applycal, concat
from casatools import table
# from casacore.tables import table

from dsa110hi.utils_dsa110 import valid_antennas_dsa110

tb = table()

def plot_delay(file,save=None,polarizations=[0,1]):
    """Plots the delay solutions for each antenna
    
    Parameters
    ----------
    file : str
        Path to the file to be plotted
    save : str or None
        If given, the image will be saved to this path
    polarizations : list
        List containing the indices of the polarizations to plot (defaults to 
        [0,1] which gives both polarizations for the DSA-110)
    
    Returns
    -------
    fig, axis
        Matplotlib Figure and Axis objects for the plot - can be used in other scripts
        to make further additions/modifications to the plot.
    """

    # Set up plot
    fig, ax = plt.subplots()
    ax.set(xlabel='Antenna', ylabel='Delay')

    # Get the data
    tb.open(file)
    x = tb.getcol('ANTENNA1')
    y = tb.getcol('FPARAM')
    mask = tb.getcol('FLAG')
    tb.close()

    # Plot the data
    markers = ['o','x','^','+']
    for i_pol in polarizations:
        i_pol = int(i_pol)
        ax.plot(x[~mask[i_pol,0,:]],y[i_pol,0,:][~mask[i_pol,0,:]],marker=markers[i_pol],ls='none',label=f'Pol{i_pol}')
    
    ax.legend()

    # Save and return
    if save is not None:
        fig.savefig(save+'_solution.png')
    return fig, ax

def plot_bpass(file,save=None,polarizations=[0,1],antennas=None):
    """Plots the bandpass solutions for each antenna
    
    Parameters
    ----------
    file : str
        Path to the file to be plotted
    save : str or None
        If given, the image will be saved to this path
    polarizations : list
        List containing the indices of the polarizations to plot (defaults to 
        [0,1] which gives both polarizations for the DSA-110)
    antennas : list
        List containing the indices of the antennas to plot (defaults to 
        the list of used DSA-110 pads)
    
    Returns
    -------
    figs_amp, figs_phase
        Lists of tuples Matplotlib Figure and Axis objects for each plot - can be used in other scripts
        to make further additions/modifications to the plots.
    """

    # Determine which antennas to plot
    if antennas is None:
        antennas = valid_antennas_dsa110
    if polarizations is None:
        polarizations = [0,1]
    nplots = len(antennas)//20+1

    # Get data from table
    tb.open(file)
    ant = tb.getcol('ANTENNA1')
    amp = np.abs(tb.getcol('CPARAM'))
    phase = np.angle(tb.getcol('CPARAM'),deg=True)
    mask = tb.getcol('FLAG')
    tb.close()

    tb.open(os.path.join(file,'ANTENNA'))
    antname=tb.getcol('NAME')
    tb.close()

    tb.open(os.path.join(file,'SPECTRAL_WINDOW'))
    freq=tb.getcol('CHAN_FREQ')
    tb.close()

    # Iterate through antennas and make the plots
    i_ant = 0
    figs_amp = []
    figs_phase = []
    markers = ['o','x','^','+']
    for i_plot in range(nplots):
        fig_amp, axes_amp = plt.subplots(4,5,figsize=(10,8),sharex=True,sharey=True)
        fig_amp.subplots_adjust(hspace=0,wspace=0)
        for ax in axes_amp[-1,:]:
            ax.set(xlabel='Frequency [MHz]')
        for ax in axes_amp[:,0]:
            ax.set(ylabel='Amplitude')
        for ax in axes_amp[:-1,:].flatten():
            plt.setp(ax.get_xticklabels(),visible=False)
        for ax in axes_amp[:,1:].flatten():
            plt.setp(ax.get_yticklabels(),visible=False)
        axes_amp[0,0].set(ylim=(0,1.1*np.max(amp[~mask])))

        fig_phase, axes_phase = plt.subplots(4,5,figsize=(10,8),sharex=True,sharey=True)
        fig_phase.subplots_adjust(hspace=0,wspace=0)
        for ax in axes_phase[-1,:]:
            ax.set(xlabel='Frequency [MHz]')
        for ax in axes_phase[:,0]:
            ax.set(ylabel='Phase [degrees]')
        for ax in axes_phase[:-1,:].flatten():
            plt.setp(ax.get_xticklabels(),visible=False)
        for ax in axes_phase[:,1:].flatten():
            plt.setp(ax.get_yticklabels(),visible=False)
        axes_phase[0,0].set(ylim=(-180,180))

        while i_ant < 20*(i_plot+1) and i_ant<len(antennas):
            ant_inds = antennas[i_ant]
            data_ind = np.nonzero(ant==ant_inds)[0][0]

            ax = axes_amp.flatten()[i_ant-20*i_plot]
            ax.text(0.05,0.95,antname[data_ind],ha='left',va='top',transform=ax.transAxes)
            for i_pol in polarizations:
                i_pol = int(i_pol)
                ax.plot(freq[~mask[i_pol,:,data_ind]]/1e6,amp[i_pol,:,data_ind][~mask[i_pol,:,data_ind]],markersize=3,marker=markers[i_pol],ls='none',label=f'Pol{i_pol}')

            ax = axes_phase.flatten()[i_ant-20*i_plot]
            ax.text(0.05,0.95,antname[data_ind],ha='left',va='top',transform=ax.transAxes)
            for i_pol in polarizations:
                i_pol = int(i_pol)
                ax.plot(freq[~mask[i_pol,:,data_ind]]/1e6,phase[i_pol,:,data_ind][~mask[i_pol,:,data_ind]],markersize=3,marker=markers[i_pol],ls='none',label=f'Pol{i_pol}')

            i_ant+=1
        
        axes_amp[0,0].legend(loc='lower right')
        axes_phase[0,0].legend(loc='lower right')

        if save is not None:
            fig_amp.savefig(save+f'_solution_amp_{i_plot}.png')
            fig_phase.savefig(save+f'_solution_phase_{i_plot}.png')
        figs_amp.append((fig_amp,axes_amp))
        figs_phase.append((fig_phase,axes_phase))

    return figs_amp, figs_phase

def plot_gain(file,save=None,polarizations=[0,1],antennas=None,solution_type='ap'):
    """Plots the gain solutions for each antenna as a function of time
    
    Parameters
    ----------
    file : str
        Path to the file to be plotted
    save : str or None
        If given, the image will be saved to this path
    polarizations : list
        List containing the indices of the polarizations to plot (defaults to 
        [0,1] which gives both polarizations for the DSA-110)
    antennas : list
        List containing the indices of the antennas to plot (defaults to 
        the list of used DSA-110 pads)
    solution_type : 'a', 'p', 'ap'
        'a' for amplitude, 'p' for phase, 'ap' for both.
        Defaults to 'p'.
    
    Returns
    -------
    figs_amp, figs_phase
        Lists of tuples Matplotlib Figure and Axis objects for each plot - can be used in other scripts
        to make further additions/modifications to the plots.
    """
    pass



def solve_delay(incoming_file=[],
                incoming_cal_tables=[],
                output_file_path=os.path.join(os.sep,'pipeline','cal_solutions'),output_file_name='delay',output_file_overwrite=False,
                refant=None, minsnr=5, selection={}, # selection can be used for things like timerange - follow casa syntax for selectdata
                plot_solutions=True, plot_solutions_saveonly=True,
                ):
    """Find delay solutions
    
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

def solve_bpass(incoming_file=[],
                incoming_cal_tables=[],
                output_file_path=os.path.join(os.sep,'pipeline','cal_solutions'),output_file_name='bpass',output_file_overwrite=False,
                refant=None, minsnr=5, selection={}, # selection can be used for things like timerange - follow casa syntax for selectdata
                plot_solutions=True, plot_solutions_pols=None, plot_solutions_ants=None, plot_solutions_saveonly=True,
                ):
    """Find bandpass solutions
    
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

def flag(incoming_file=[], 
         reset_flags=False,
         flag_auto=True,
         flag_shadow=True,
         flag_zeros=True,
         flag_bad_ants=None,
         flag_uvrange=None,
         flag_tfcrop=True, flag_tfcrop_merge_fields=True):
    """Wrapper for standard flagging steps for the DSA-110 pipeline
    
    Could be improved by adding greater control over tfcrop parameters 
    and/or replacing tfcrop with an external call to AOFlagger
    
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
    flag_tfcrop_merge_fields : bool
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

    if flag_bad_ants is not None:
        flagdata(incoming_file, mode='manual', antenna=flag_bad_ants, flagbackup=False)
    if flag_uvrange is not None:
        flagdata(incoming_file, mode='manual', uvrange=flag_uvrange, flagbackup=False)

    # TF crop
    flagmanager(incoming_file, mode='save', versionname='basic-cuts')

    if flag_tfcrop:
        # TF crop (and AOFlagger) don't work across field IDs, but we need them to
        # for the drift scan. The hacky solution to this is to manually change all 
        # of the field labels in the MS, flag, and then change them back.
        if flag_tfcrop_merge_fields:
            # Tfcrop - first backup the field ids...
            tb.open(incoming_file,nomodify=False)
            ids = tb.getcol('FIELD_ID')
            ids_backup = np.copy(ids)
            if np.any(ids > 0):
                np.save(incoming_file+'.field_id_backup.npy', ids)
            ids[:] = 0
            tb.putcol('FIELD_ID', ids)
            tb.close()

        # Do flagging
        flagdata(incoming_file, mode='tfcrop', spw='', timecutoff=3.5, freqcutoff=3, maxnpieces=1, growfreq=25,
            datacolumn='data', action='apply', display='none', 
            combinescans=True, ntime='300s',
            flagbackup=False)

        # Restore old fields
        if flag_tfcrop_merge_fields:
            tb.open(incoming_file,nomodify=False)
            tb.putcol('FIELD_ID', ids_backup)
            tb.close()
            flagmanager(incoming_file, mode='save', versionname='tfcrop')
            os.remove(incoming_file+'.field_id_backup.npy')

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