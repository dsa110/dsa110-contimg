"""
Antenna position utilities for DSA-110.

Adapted from dsa110-antpos
"""

import pandas as pd
import numpy as np
from pathlib import Path
from astropy.coordinates import EarthLocation
import astropy.units as u

# Get the path to the antenna data file
_DATA_DIR = Path(__file__).parent / "data"
ANTPOS_FILE = _DATA_DIR / "DSA110_Station_Coordinates.csv"


def tee_centers():
    """Read positions of DSA110 Tee center and return as tuple."""
    tc_longitude = -2.064427799136453 * u.rad
    tc_latitude = 0.6498455107238486 * u.rad
    tc_height = 1188.0519 * u.m
    
    return (tc_latitude, tc_longitude, tc_height)


def get_lonlat(csvfile=None, headerline=5, defaultheight=1182.6000):
    """
    Read positions of all antennas from DSA110 CSV file.
    
    Parameters
    ----------
    csvfile : str or Path, optional
        Path to the antenna coordinates CSV file
    headerline : int
        Line number of the header in the CSV file
    defaultheight : float
        Default height in meters for antennas without specified height
    
    Returns
    -------
    pandas.DataFrame
        DataFrame with antenna positions
    """
    if csvfile is None:
        csvfile = ANTPOS_FILE
    
    tab = pd.read_csv(csvfile, header=headerline)
    stations = tab['Station Number']
    latitude = tab['Latitude']
    longitude = tab['Longitude']
    height = tab['Elevation (meters)']
    
    df = pd.DataFrame()
    df['Station Number'] = [int(station.split('-')[1]) for station in stations]
    df['Latitude'] = latitude
    df['Longitude'] = longitude
    df['Height (m)'] = height
    df['Height (m)'] = np.where(np.isnan(df['Height (m)']), defaultheight, df['Height (m)'])
    
    # Remove 200E and 200W stations if present
    for st_no in ['200E', '200W']:
        idx_to_drop = np.where(df['Station Number'] == st_no)[0]
        if len(idx_to_drop) > 0:
            df.drop(idx_to_drop[0], inplace=True)
    
    df = df.astype({'Station Number': np.int32})
    df.sort_values(by=['Station Number'], inplace=True)
    df.set_index('Station Number', inplace=True)
    
    return df


def get_itrf(csvfile=None, latlon_center=None, return_all_stations=True, stations=None):
    """
    Read positions of all antennas from DSA110 CSV file and convert to ITRF coordinates.
    
    Parameters
    ----------
    csvfile : str or Path, optional
        Path to the antenna coordinates CSV file
    latlon_center : tuple, optional
        (latitude, longitude, height) of array center
    return_all_stations : bool
        If True, return all stations; if False, filter by stations parameter
    stations : str or list, optional
        Path to file with station IDs or list of station IDs to include
    
    Returns
    -------
    pandas.DataFrame
        DataFrame with antenna positions in ITRF coordinates
    """
    if csvfile is None:
        csvfile = ANTPOS_FILE
    
    if latlon_center is None:
        (latcenter, loncenter, heightcenter) = tee_centers()
    else:
        (latcenter, loncenter, heightcenter) = latlon_center
    
    df = get_lonlat(csvfile)
    center = EarthLocation(lat=latcenter, lon=loncenter, height=heightcenter)
    locations = EarthLocation(
        lat=df['Latitude'],
        lon=df['Longitude'],
        height=df['Height (m)'] * u.m
    )
    
    df['x_m'] = locations.x.to_value(u.m)
    df['y_m'] = locations.y.to_value(u.m)
    df['z_m'] = locations.z.to_value(u.m)
    
    df['dx_m'] = (locations.x - center.x).to_value(u.m)
    df['dy_m'] = (locations.y - center.y).to_value(u.m)
    df['dz_m'] = (locations.z - center.z).to_value(u.m)
    
    if not return_all_stations and stations is not None:
        if isinstance(stations, str):
            idxs = np.genfromtxt(stations, dtype=np.int32, delimiter=',')
        else:
            idxs = np.array(stations, dtype=np.int32)
        df = df.loc[idxs]
    
    return df

