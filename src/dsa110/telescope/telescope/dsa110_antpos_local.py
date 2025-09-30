"""
Local implementation of dsa110_antpos functionality for DSA-110 antenna positions.

This module provides the key functions needed to properly filter and convert
DSA-110 antenna positions using the active antenna list.
"""

import pandas as pd
import numpy as np
from astropy.coordinates import EarthLocation
import astropy.units as u
from pathlib import Path

def get_lonlat(csvfile, headerline=5, defaultheight=1182.6000):
    """Read positions of all antennas from DSA110 CSV file."""
    
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
    
    # Remove 200E and 200W stations if they exist
    for st_no in ['200E', '200W']:
        idx_to_drop = np.where(df['Station Number'] == st_no)[0]
        if len(idx_to_drop) > 0:
            df.drop(idx_to_drop[0], inplace=True)
    
    df = df.astype({'Station Number': np.int32})
    df.sort_values(by=['Station Number'], inplace=True)
    df.set_index('Station Number', inplace=True)
    return df

def get_itrf(csvfile, latlon_center=None, return_all_stations=True, stations_file=None):
    """Read positions of all antennas from DSA110 CSV file and convert to ITRF coordinates."""
    
    if latlon_center is None:
        # DSA-110 Tee center coordinates
        latcenter = 0.6498455107238486 * u.rad
        loncenter = -2.064427799136453 * u.rad
        heightcenter = 1188.0519 * u.m
    else:
        (latcenter, loncenter, heightcenter) = latlon_center

    df = get_lonlat(csvfile)
    center = EarthLocation(lat=latcenter, lon=loncenter, height=heightcenter)
    locations = EarthLocation(lat=df['Latitude'], lon=df['Longitude'], height=df['Height (m)']*u.m)
    df['x_m'] = locations.x.to_value(u.m)
    df['y_m'] = locations.y.to_value(u.m)
    df['z_m'] = locations.z.to_value(u.m)

    df['dx_m'] = (locations.x-center.x).to_value(u.m)
    df['dy_m'] = (locations.y-center.y).to_value(u.m)
    df['dz_m'] = (locations.z-center.z).to_value(u.m)

    if not return_all_stations and stations_file is not None:
        # Load active antenna list
        if isinstance(stations_file, str):
            # Read from file
            with open(stations_file, 'r') as f:
                line = f.readline().strip()
                idxs = [int(x) for x in line.split(',')]
        else:
            # Use provided list
            idxs = stations_file
        
        # Filter to active antennas only
        df = df.loc[idxs]

    return df

def get_active_antenna_list():
    """Get the list of active DSA-110 antennas."""
    # This is the list from ant_ids_mid.csv - all 66 active antennas
    return [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117]
