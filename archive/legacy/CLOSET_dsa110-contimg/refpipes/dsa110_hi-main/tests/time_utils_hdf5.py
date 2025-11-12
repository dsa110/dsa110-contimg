"""Simple timing for uvh5 operations"""
import os
import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord

from time import process_time

from dsa110hi.utils_hdf5 import load_uvh5_file, set_phases, make_calib_model, loc_dsa110

time_loading_by_n = False
time_16 = True

files = [f'/data/pipeline/package_test_data/h5/test_sb{i:02}.hdf5' for i in range(16)]

def timer(func, *args, **kwargs):
    t=process_time()
    v=func(*args, **kwargs)
    dt=process_time()-t
    print(f"{func.__name__} took {dt:.4f} seconds")
    return v

# Time to load 16 files is quite variable, but should be around 30±10 seconds
if time_loading_by_n:
    # Time loading 1 file
    print("Loading 1 file")
    uvdata = timer(load_uvh5_file,files[0])

    # Time loading 2 files
    print("Loading 2 files")
    uvdata = timer(load_uvh5_file,files[:2])
    print(uvdata.data_array.shape)

    print("Loading 4 files")
    uvdata = timer(load_uvh5_file,files[:4])
    print(uvdata.data_array.shape)

    print("Loading 8 files")
    uvdata = timer(load_uvh5_file,files[:8])
    print(uvdata.data_array.shape)

    # Time loading 16 files
    print("Loading 16 files")
    uvdata = timer(load_uvh5_file,files)

# Time to load 16 files is quite variable, but should be around 30±10 seconds
# Time to make the calibrator model should be about 25 seconds
if time_16:
    # Time loading 16 files
    print("Loading 16 files")
    uvdata = timer(load_uvh5_file,files)

    # Time setting uvw coords 16 files
    print("Pointing 16 files")
    uvdata, ucoord = timer(set_phases, uvdata, 'test', loc_dsa110, False)

    # Time phasing
    cal = SkyCoord(0,0,unit='deg')
    print("Models for 16 files")
    uvcalib = timer(make_calib_model, uvdata, cal.ra, cal.dec, 1)