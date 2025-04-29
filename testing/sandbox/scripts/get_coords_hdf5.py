from time import process_time

import shutil
import os
import warnings

import numpy as np
import astropy.units as u
import astropy.constants as c
from astropy.time import Time
from pyuvdata import UVData
from pyuvdata import utils as uvutils
from pyuvdata.uvdata.ms import tables

from astropy.coordinates import EarthLocation, HADec, SkyCoord, ICRS, Angle
import astropy.units as u

def get_hdf5_coord(fname):

    # Location of DSA-110
    OVRO_LON = -2.064427799136453
    OVRO_LAT = 0.6498455107238486
    OVRO_ALT = 1188.0519
    loc_dsa110 = EarthLocation(lat=OVRO_LAT*u.rad, lon=OVRO_LON*u.rad, height=OVRO_ALT*u.m)

    uvdata = UVData()

    uvdata.read(fname, file_type='uvh5', keep_all_metadata=False, run_check=False)    

    # Get pointing information:
    pt_dec = uvdata.extra_keywords['phase_center_dec'] * u.rad

    # Do calculations on unique times - this is faster because of astropy overheads
    utime, uind = np.unique(uvdata.time_array, return_inverse=True)
    utime = Time(utime, format='jd')

    coords = [HADec(ha=0.*u.rad, dec=pt_dec, location=loc_dsa110, obstime=t) for t in utime]
    coords = [c.transform_to(ICRS()) for c in coords]

    pt_dec = np.array([c.dec.rad for c in coords]) * u.rad
    pt_ra = np.array([c.ra.rad for c in coords]) * u.rad

    # Converts back to covering all values
    pt_coords = SkyCoord(pt_ra[uind], pt_dec[uind], frame='icrs')
    pt_ras_deg_mean = np.mean([i.ra.deg for i in pt_coords])
    pt_decs_deg_mean = np.mean([i.dec.deg for i in pt_coords])
    print(f'Mean RA (deg): {pt_ras_deg_mean}')
    print(f'Mean DEC (deg): {pt_decs_deg_mean}')
    #pt_coords_arr = np.array([pt_ras_deg_mean, pt_decs_deg_mean])

    #pt_coords_mean = SkyCoord(pt_ras_deg_mean, pt_decs_deg_mean, unit='deg', frame='icrs')

    return