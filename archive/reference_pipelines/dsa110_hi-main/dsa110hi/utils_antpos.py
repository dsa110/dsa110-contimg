"""These functions access antenna position data from a file. 
This data is already written correctly in the file headers,
and so is not needed."""

import numpy as np
import pandas
from importlib.resources import files

from pyuvdata import UVData
from astropy.coordinates import EarthLocation
import astropy.units as u


# Make these paths work from anywhere
packagepath = files('dsa110hi')
antposfile = packagepath.joinpath('resources','DSA110_Station_Coordinates.csv')

def get_lonlat(csvfile=antposfile, headerline=5, defaultheight=1182.6000):
    """ Read positions of all antennas from DSA110 CSV file.
    """

    tab       = pandas.read_csv(csvfile, header=headerline)
    stations  = tab['Station Number']
    latitude  = tab['Latitude']
    longitude = tab['Longitude']
    height = tab['Elevation (meters)']

    df = pandas.DataFrame()
    df['Station Number'] = [int(station.split('-')[1]) for station in stations]
    df['Latitude'] = latitude
    df['Longitude'] = longitude
    df['Height (m)'] = height
    df['Height (m)'] = np.where(np.isnan(df['Height (m)']), defaultheight, df['Height (m)'])
    for st_no in ['200E', '200W']:
        idx_to_drop = np.where(df['Station Number'] == st_no)[0]
        if len(idx_to_drop > 0):
            df.drop(idx_to_drop[0], inplace=True)
    df = df.astype({'Station Number': np.int32})
    df.sort_values(by=['Station Number'], inplace=True)
    df.set_index('Station Number', inplace=True)
    return df

def get_itrf(telescope_pos, csvfile=antposfile,
             return_all_stations=True):
    """Read positions of all antennas from DSA110 CSV file and 
    convert to ITRF coordinates. Only provides active stations."""

    df = get_lonlat(csvfile)
    locations = EarthLocation(lat=df['Latitude']*u.degree, lon=df['Longitude']*u.degree, height=df['Height (m)']*u.m)
    df['x_m'] = locations.x.to_value(u.m)
    df['y_m'] = locations.y.to_value(u.m)
    df['z_m'] = locations.z.to_value(u.m)

    df['dx_m'] = (locations.x-telescope_pos.x).to_value(u.m)
    df['dy_m'] = (locations.y-telescope_pos.y).to_value(u.m)
    df['dz_m'] = (locations.z-telescope_pos.z).to_value(u.m)

    return df

def set_antenna_positions(uvdata: UVData, telescope_pos: EarthLocation) -> np.ndarray:
    """Set the antenna positions in uvdata.

    This is already done in the raw data - keeping it here because it's
    useful for testing and possible other applications.
    """

    # Get correct ITRF positions of all antennas
    df_itrf = get_itrf(telescope_pos)

    # Print message if length of poisitons array doesn't match uvdata antenna list
    # RPK: chaning this to be an error
    if len(df_itrf['x_m']) != uvdata.antenna_positions.shape[0]:
        message = 'Mismatch between antennas in current environment ' +\
            f'({len(df_itrf["x_m"])}) and correlator environment ' +\
            f'({uvdata.antenna_positions.shape[0]})'
        raise RuntimeError(message)

    # Antenna positions relative to ITRF coords of array center):
    uvdata.antenna_positions = np.array([
        df_itrf['dx_m'],
        df_itrf['dy_m'],
        df_itrf['dz_m']
    ]).T

    uvdata.telescope_location = np.array([telescope_pos.x.to_value(u.m),telescope_pos.y.to_value(u.m),telescope_pos.z.to_value(u.m)])
    uvdata.telescope_name = telescope_pos.info.name

    return uvdata
