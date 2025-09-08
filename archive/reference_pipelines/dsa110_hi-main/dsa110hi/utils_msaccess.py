import os
import numpy as np
import matplotlib.pyplot as plt

from dsa110hi.utils_dsa110 import valid_antennas_dsa110

#################################################################
### MS loading with flexible choice between CASA and CASACore ###
#################################################################

def _check_backend(backend):
    """Check that a casa backend is recognized"""

    if backend not in ["casa", "casacore"]:
        raise ValueError("backend must be 'casa' or 'casacore'")

def get_pars(ms, subtab, col, backend="casa"):

    _check_backend(backend)

    # Check that we know how to find the requested stuff
    singlemode=False
    if isinstance(subtab,(list,np.ndarray,tuple)):
        if not isinstance(col, (list,np.ndarray,tuple)):
            raise ValueError("giving a list of subtabs but only a single col is not supported")
        elif len(subtab) != len(col):
            raise ValueError("len(subtab) must equal len(col)")
    elif isinstance(col,(list,np.ndarray,tuple)):
        subtab = [subtab for _ in range(len(col))]
    else:
        subtab = [subtab]
        col = [col]
        singlemode=True
    subtab = [s if s is not None else '' for s in subtab]

    values = [[] for _ in col]
    
    if backend == "casa":
        from casatools import table
        tb = table()
        for st in np.unique(subtab):
            tb.open(os.path.join(ms,st))
            inds = np.nonzero(np.array(subtab)==st)[0]
            for i in inds:
                values[i] = np.array(tb.getcol(col[i]))
        tb.close()

    if backend == "casacore":
        from casacore.tables import table
        for st in np.unique(subtab):
            with table(os.path.join(ms,st)) as tb:
                inds = np.nonzero(np.array(subtab)==st)[0]
                for i in inds:
                    values[i] = np.array(tb.getcol(col[i])).T

    if singlemode:
        return values[0]
    else:
        return values

def get_info(ms, backend="casa"):

    _check_backend(backend)

    if backend == "casa":
        from casatools import table
        tb = table()
        tb.open(ms)
        info = tb.info()
        tb.close()

    if backend == "casacore":
        from casacore.tables import table
        with table(ms) as tb:
            info = tb.info()

    return info



############################################
### Butcher and MS to make flagging work ###
############################################

# TF crop (and AOFlagger) don't work across field IDs, but we need them to
# for the drift scan. The hacky solution to this is to manually change all 
# of the field labels in the MS, flag, and then change them back.
def zero_field_ids(ms, idfile=None, backend="casa"):

    _check_backend(backend)

    # Where to save flags
    if idfile is None:
        idfile = ms+'.field_id_backup.npy'

    if backend == "casa":
        from casatools import table
        tb = table()
        tb.open(ms, nomodify=False)

        ids = tb.getcol('FIELD_ID')
        
        ids_backup = np.copy(ids)
        if np.any(ids_backup > 0) or not os.path.exists(idfile):
            np.save(idfile, ids_backup)

        ids[:] = 0
        tb.putcol('FIELD_ID', ids)
        tb.close()

    if backend == "casacore":
        from casacore.tables import table
        with table(ms,readonly=False) as tb:
            ids = tb.getcol('FIELD_ID')
            
            ids_backup = np.copy(ids)
            if np.any(ids_backup > 0) or not os.path.exists(idfile):
                np.save(idfile, ids_backup)

            ids[:] = 0
            tb.putcol('FIELD_ID', ids)

def restore_field_ids(ms, idfile=None, del_idfile=False, backend="casa"):

    _check_backend(backend)

    if idfile is None:
        idfile = ms+'.field_id_backup.npy'
    if not os.path.exists(idfile):
        raise ValueError(f"Original flags not found at {idfile}")

    ids = np.load(idfile)

    if backend == "casa":
        from casatools import table
        tb = table()

        tb.open(ms, nomodify=False)
        tb.putcol('FIELD_ID', ids)
        tb.close()

    if backend == "casacore":
        from casacore.tables import table
        with table(ms,readonly=False) as tb:
            tb.putcol('FIELD_ID', ids)
    
    if del_idfile:
        os.remove(idfile)




################
### Plotting ###
################

pol_markers = ['o','x','^','+']
pol_colors = [f'C{i}' for i in range(len(pol_markers))]

def plot_delay(file,save=None,polarizations=[0,1],backend="casa"):
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
    backend : 'casa' or 'casacore'
        The casa backend to use - note that casatools (casa) and casacore 
        cannot be imported in the same python process. Default is 'casa'
    
    Returns
    -------
    fig, axis
        Matplotlib Figure and Axis objects for the plot - can be used in other scripts
        to make further additions/modifications to the plot.
    """

    # Get data
    info = get_info(file,backend=backend)
    if info['type'] != 'Calibration' or info['subType'] != 'K Jones':
        raise ValueError("file is not of type 'Calibration' and subtype 'K Jones'")

    antid, delay, flag, antnames = get_pars(file, ['','','','ANTENNA'],['ANTENNA1','FPARAM','FLAG','NAME'],backend=backend)
    delay[flag] = np.nan

    # Check polarization selection
    if polarizations is None:
        polarizations = [0,1]
    if np.any(polarizations) >= delay.shape[0]:
        raise ValueError(f"Some polarizations not found - file information for {delay.shape[0]} pols")

    # Set up plot
    fig, ax = plt.subplots()
    ax.set(xlabel='Antenna', ylabel='Delay')

    # Plot the data
    for i_pol in polarizations:
        i_pol = int(i_pol)
        # ax.plot(antid[~mask[i_pol,0,:]],y[i_pol,0,:][~mask[i_pol,0,:]],marker=markers[i_pol],ls='none',label=f'Pol{i_pol}')
        ax.plot(antid,delay[i_pol,0,:],marker=pol_markers[i_pol],color=pol_colors[i_pol],ls='none',label=f'Pol{i_pol}')
    
    ax.legend()

    # Save and return
    if save is not None:
        fig.savefig(save+'_solution.png')
    return fig, ax

def plot_bpass(file,save=None,polarizations=None,antennas=None,backend='casa'):
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
    backend : 'casa' or 'casacore'
        The casa backend to use - note that casatools (casa) and casacore 
        cannot be imported in the same python process. Default is 'casa'

    Returns
    -------
    figs_amp, figs_phase
        Lists of tuples Matplotlib Figure and Axis objects for each plot - can be used in other scripts
        to make further additions/modifications to the plots.
    """

    # Get data
    info = get_info(file,backend=backend)
    if info['type'] != 'Calibration' or info['subType'] != 'B Jones':
        raise ValueError("file is not of type 'Calibration' and subtype 'B Jones'")

    antid, bpass, flag, antnames, frequencies = get_pars(file, ['','','','ANTENNA','SPECTRAL_WINDOW'],['ANTENNA1','CPARAM','FLAG','NAME','CHAN_FREQ'],backend=backend)
    
    bpass_amp = np.abs(bpass)
    bpass_phase = np.angle(bpass, deg=True)
    
    bpass[flag] = np.nan
    bpass_amp[flag] = np.nan
    bpass_phase[flag] = np.nan

    # Determine which antennas to plot
    if antennas is None:
        antennas = valid_antennas_dsa110
    nplots = len(antennas)//20+1

    # Determine which polarizations to plot
    if polarizations is None:
        polarizations = [0,1]
    if np.any(polarizations) >= bpass.shape[0]:
        raise ValueError(f"Some polarizations not found - file information for {bpass.shape[0]} pols")

    # Iterate through antennas and make the plots
    i_ant = 0
    figs_amp = []
    figs_phase = []
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
        axes_amp[0,0].set(ylim=(0,1.1*np.nanmax(bpass_amp)))

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
            data_ind = np.nonzero(antid==ant_inds)[0][0]

            ax = axes_amp.flatten()[i_ant-20*i_plot]
            ax.text(0.05,0.95,antnames[data_ind],ha='left',va='top',transform=ax.transAxes)
            for i_pol in polarizations:
                i_pol = int(i_pol)
                ax.plot(frequencies/1e6,bpass_amp[i_pol,:,data_ind],markersize=3,marker=pol_markers[i_pol],color=pol_colors[i_pol],ls='none',label=f'Pol{i_pol}')

            ax = axes_phase.flatten()[i_ant-20*i_plot]
            ax.text(0.05,0.95,antnames[data_ind],ha='left',va='top',transform=ax.transAxes)
            for i_pol in polarizations:
                i_pol = int(i_pol)
                ax.plot(frequencies/1e6,bpass_phase[i_pol,:,data_ind],markersize=3,marker=pol_markers[i_pol],color=pol_colors[i_pol],ls='none',label=f'Pol{i_pol}')

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

