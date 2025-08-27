import os
from fnmatch import fnmatch

import numpy as np
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord

from importlib.resources import files

from utils_hdf5 import uvh5_to_ms
from utils_dsa110 import valid_antennas_dsa110

def search_for_calibrator(pointing_coords : SkyCoord, cal_search_radius : float, cal_catalog : str = None):
    """Do a radial search for calibrators near a specified set of coordinates
    
    If no calibrator is found, or if more than one are present in the field, will return
    None for all fields, otherwise returns the name, coordinates (SkyCoord object), flux
    spectral index, and frequency where the flux is specified for the matching calibrator

    Parameters
    ----------
    pointing_coords : SkyCoord instance
        An astropy.coordinates.SkyCoord instance containing the coordinates of the pointing center
    cal_search_radius : float
        The radius around pointing_coords to search for a calibrator - specified in degrees
    cal_catalog : str
        A string specifying the path for a catalog to use for coordinates. If none is given, a 
        default catalog will be used.
        The catalog itself should be a csv file with entries of the form "Object_name, HH:MM:SS.sss,
        ±DD:MM:SS.sss,J2000.0,flux (in Jy),None,None" - the final two values can either be none, or can be used
        to specify a spectral index, and the frequency (in GHz) at which the flux is specified.
    
    Returns
    -------
    name : str
        Name of the calibrator
    pos : SkyCoord instance
        An astropy.coordinates.SkyCoord instance containing the coordinates of the calibrator
    flux : float
        Flux of the calibrator in Jy. If the calibrator data is specified with a spectral index,
        this is the flux at spectral_index_f0
    spectral_index : float
        The spectral index for the calibrator. If no spectral index is listed in the catalog,
        this returns as None.
    spectral_index_f0 : float
        The frequency in GHz where the calibrator's flux is equal to the specified flux. If no 
        spectral index is listed in the catalog, this returns as None.
    """

    if cal_catalog is None:
        packagepath = files('dsa110hi')
        cal_catalog = packagepath.joinpath('resources','default_cal_catalog.csv')
    cat = np.genfromtxt(cal_catalog, dtype=[('name','U10'),('ra','U13'),('dec','U13'),('equinox','U7'),('flux','f'),('sidx','f'),('nu0','f')],delimiter=',',comments='#')

    coords = [SkyCoord(str(obj['ra'])+' '+str(obj['dec']),unit=[u.hour,u.degree],equinox=obj['equinox']) for obj in cat]
    distances = np.array([pointing_coords.separation(c).deg for c in coords])
    matches = np.nonzero(distances<=cal_search_radius)

    if len(matches[0])<1:
        return None, None, None, None, None, None
    
    elif len(matches[0])==1:
        cal = cat[matches][0]
        # should return name : str, pos : SkyCoords, flux : float, spectral_index : float (or none), spectral_index_f0 : float (or none)
        if np.isnan(cal['sidx']) or np.isnan(cal['nu0']):
            return cal['name'], coords[matches[0][0]].ra, coords[matches[0][0]].dec, cal['flux'], None, None
        else:
            return cal['name'], coords[matches[0][0]].ra, coords[matches[0][0]].dec, cal['flux'], cal['sidx'], cal['nu0']
        
    else:
        n,cr,cd,f,s,nu = [], [], [], [], [], []
        for i in range(len(cat[matches])):
            cal = cat[matches][i]
            n.append(cal['name'])
            cr.append(coords[matches[0][i]].ra)
            cd.append(coords[matches[0][i]].dec)
            f.append(cal['flux'])
            if np.isnan(cal['sidx']):
                s.append(None)
                nu.append(None)
            else:
                s.append(cal['sidx'])
                nu.append(cal['nu0'])
    
        return n,cr,cd,f,s,nu
            

def convert_to_ms(incoming_file_path=os.path.join(os.sep,'data','incoming'), incoming_file_names=None, 
                  tmin='2000-01-01T00:00:00', tmax='3000-01-01T23:59:59',
                  spw=['sb00','sb01','sb02','sb03','sb04','sb05','sb06','sb07','sb08','sb09','sb10','sb11','sb12','sb13','sb14','sb15'],
                  same_timestamp_tolerance=180.0,
                  output_file_path=os.path.join(os.sep,'data','pipeline','raw'), output_antennas=None, 
                  cal_do_search=False, cal_search_radius=1.0, cal_catalog=None,
                  cal_output_file_path=None,
                  post_handle='none', post_file_path=os.path.join(os.sep,'data','incoming','processed')):
    """Identify hdf5 files in a directory and convert them to MS format
    
    This program assumes files have names in the format YYYY-MM-DDThh:mm:ss_sbXX[_spl].hdf5
    (where XX is the zero-padded subband number from 0 to 15). It will combine any
    data from timestamps within 30s of eachother.

    Parameters
    ----------
    incoming_file_path : str
        Path to look for data in
    incoming_file_names : list of strings
        Can be used to restrict the script to only file names in the list - give only
        the file name, not the path.
    tmin, tmax : str
        String in the format YYYY-MM-DDThh:mm:ss (everything after year can be dropped if desired)
        specifying the minimum and maximum timestamps to include
    spw : list
        List of the spws to include - default is 'sb00' through 'sb15', which will ignore the
        high resolution spws ('sb00_spl' through 'sb15_spl')
    same_timestamp_tolerance : float
        The tolerance for considering timestamps equal (in seconds) - default is 30 seconds
    output_file_path : str
        Path to put new ms data
    output_antennas : list or None
        List of antennas to output - None will write all of the antennas. The list should be a 
        list of integers containing the (1-based indexing) antenna numbers to keep.
    cal_do_search : bool
        If True, will search for nearby calibrators at each timestamp and output a cal_pass.ms
        with a calibrator model when a pass is available
    cal_search_radius : float
        Radius within which to search for calibrators (in degrees)
    cal_catalog : str
        Path to catalog of calibrators
    cal_output_file_path : str
        Path to put calibrator ms data (if None output_file_path is used)
    post_handle : 'none', 'delete', 'move'
        What to do with hdf5 files after MS is created - options are 'none' (do nothing),
        'delete', or 'move' (move file to post_file_path)
    post_file_path : str
        Path to put hdf5 files after ms is created if post_handle is 'move'
    """

    if post_handle not in ['none', 'delete', 'move']:
        raise ValueError('post_handle option not recognized')
    
    if output_antennas is None:
        output_antennas = (1+valid_antennas_dsa110).astype(str)
    if cal_output_file_path is None:
        cal_output_file_path = output_file_path
    if incoming_file_names is None:
        incoming_file_names = os.listdir(os.path.join(incoming_file_path))
        incoming_file_names = [f for f in incoming_file_names if fnmatch(f,'20*T*.hdf5')]
    file_names = sorted(incoming_file_names)

    if tmin is not None:
        file_names = [f for f in file_names if f>=tmin]
    if tmax is not None:
        file_names = [f for f in file_names if f<=tmax]
    if len(file_names) == 0:
        print("No files found")
        return

    file_times = [f.split('_')[0] for f in file_names]
    file_names = np.array(file_names)
    file_times = Time(np.array(file_times))
    file_indices = np.arange(len(file_times))

    # Figure out which files are at a similar timestamp
    for i in range(len(file_times)):
        if file_indices[i] == i:
            matches = file_times[i].isclose(file_times[i:],atol=same_timestamp_tolerance*u.s)
            file_indices[i:][matches] = i

    file_groups = []
    file_group_times = []
    for i in np.unique(file_indices):
        file_groups.append(file_names[np.nonzero(file_indices==i)])
        file_group_times.append(file_times[np.nonzero(file_indices==i)].min())

    # Sort groups by time
    order = np.argsort(file_group_times)
    file_groups = [file_groups[o] for o in order]
    file_group_times = Time([file_group_times[o] for o in order])

    # Sort files within a group by subband
    for i, fg in enumerate(file_groups):
        fg_suffix = [f.split('_',1)[1].replace('.hdf5','') for f in fg]
        order = np.argsort(fg_suffix)
        fg = [fg[o] for o in order]
        fg_suffix = [fg_suffix[o] for o in order]
        fg = [fg[i] for i in range(len(fg)) if fg_suffix[i] in spw]
        file_groups[i] = fg

    # Add directory to file names
    for i in range(len(file_groups)):
        file_groups[i] = [os.path.join(incoming_file_path,f) for f in file_groups[i]]

    print(f'File Groups: {file_groups}')
    print(f'File Group Times: {file_group_times}')

    # Make the MSes
    if not os.path.exists(output_file_path):
        os.mkdir(output_file_path)
    if not os.path.exists(cal_output_file_path):
        os.mkdir(cal_output_file_path)
    if not os.path.exists(post_file_path) and post_handle=='move':
        os.mkdir(post_file_path)

    for fg, fg_time in zip(file_groups,file_group_times):
        print(f"Working on {fg_time.utc}")

        if len(fg) == 0:
            print(f"No files found for {fg_time.utc}")
            continue
        if len(fg) != len(spw):
            print(f"Not all SPWs found for {fg_time.utc}, skipping")
            continue

        msname = uvh5_to_ms(fg,
                            os.path.join(output_file_path,fg_time.strftime('%Y-%m-%dT%H:%M:%S')),
                            verbose=True,
                            antenna_list=output_antennas,
                            append_coords=True
                            )

        if cal_do_search:
            ra = msname.split('_')[-2].replace('ra','')
            dec = msname.split('_')[-1].replace('dec','')
            dec = dec.replace('.ms','')
            pointing_coords = SkyCoord(ra=float(ra)*u.deg, dec=float(dec)*u.deg)

            cal_name, calibrator_ra, calibrator_dec, calibrator_flux, calibrator_sidx, calibrator_sidx_f0 = search_for_calibrator(pointing_coords, cal_search_radius, cal_catalog)

            if cal_name is not None:
                # Now that we've found a calibrator within the search radius, look for 
                # all calibrators within a larger area, so that we can account for other
                # bright sources in the field
                cal_name, calibrator_ra, calibrator_dec, calibrator_flux, calibrator_sidx, calibrator_sidx_f0 = search_for_calibrator(pointing_coords, 3, cal_catalog)
                if isinstance(cal_name,list):
                    save_name = '_'.join(cal_name)
                else:
                    save_name = cal_name
                uvh5_to_ms(fg,
                           os.path.join(cal_output_file_path,save_name+'_'+fg_time.strftime('%Y-%m-%dT%H:%M:%S')),
                           verbose=True,
                           calib_ra=calibrator_ra, calib_dec=calibrator_dec, calib_flux_jy=calibrator_flux,
                           calib_sidx=calibrator_sidx, calib_sidx_f0_ghz=calibrator_sidx_f0,
                           antenna_list=output_antennas
                           )

        if post_handle == 'delete':
            for f in fg:
                os.remove(f)
        elif post_handle == 'move':
            for f in fg:
                os.rename(f,os.path.join(post_file_path,f.split(os.sep)[-1]))
