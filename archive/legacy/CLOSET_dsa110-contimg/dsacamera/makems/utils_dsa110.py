import numpy as np
from astropy.coordinates import EarthLocation
import astropy.units as u

# Location of the telescope (these are just the MMA data taken from CASA):
OVRO_LON = -2.064427799136453
OVRO_LAT = 0.6498455107238486
OVRO_ALT = 1188.0519
loc_dsa110 = EarthLocation(lat=OVRO_LAT*u.rad, lon=OVRO_LON*u.rad, height=OVRO_ALT*u.m)

# Setting as CARMA for now, since CASA seems to handle it better
# DSA-110/DSA-2000/DSA/whatever aren't recognized which breaks things like listobs
# OVRO-MMA is recognized, but the coordinates seem to be wrong, which breaks plotants and listobs
loc_dsa110.info.name = 'CARMA' 

# Diameter of the dish
diam_dsa110 = 4.7 # m

import numpy as np

# Valid antennas - zero indexed indices, one indexed name strings
valid_antennas_dsa110 = np.array([  
            0,   1,   2,   3,    4,   5,   6,   7,   8,  
            10,  11,  12,  13,  14,  15,  16,  17,  18,  19,  
            23,  24,  25,  26,  27,  28,  29,
            30,  31,  32,  33,  34,  35,  36,  37,  38,  39,  
            40,  41,  42,  43,  44,  45,  46,  47,  48,  49,  
            50,  
            67,  68,  69,  
            70,  71,  72,  73,  74,  75,  76,  77,  78,  79,  
            80,  81,  82,  83,  84,  85,  86,  87,  88,  89,  
            90,  91,  92,  93,  94,  95,  96,  97,  98,  99, 
            100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 
            110, 111, 112, 113, 114, 115], dtype=int)
valid_antenna_names_dsa110 = np.array([f"pad{ind+1}" for ind in valid_antennas_dsa110])

def ant_inds_to_names_dsa110(inds):
    if np.any(inds<0) or np.any(inds>116):
        raise ValueError('Index too high/low (should be 0 to 116)')
    return np.array([f"pad{ind+1}" for ind in inds])
def ant_names_to_inds_dsa110(names):
    if not np.any([n[:3]!='pad' for n in names]):
        raise ValueError('Name not recognized - should be "pad#"')
    return np.array([int(n[3:])-1 for n in names], dtype=int)


# Primary beam
def pb_dsa110(dist, freq, diameter=diam_dsa110):
    """Calculate the primary beam response at for an array of boresight offsets and frequencies
    
    Returns the response in an array of shape (N_distances, 1, N_frequencies, 1), which is what
    is needed for the MS maker

    Assumes a simple Gaussian beam with a 1.2 λ/D FWHM.

    Parameters
    ----------
    dist : ndarray
        Array of angular offsets from the pointing direction of the telescope, in radians
    freq : ndarray
        Array of frequencies at which to calculate the beam response, in GHz
    diameter : float
        Dish diameter in meters
    """

    wl = 0.299792458 / freq
    fwhm = 1.2 * wl / diameter
    sigma = fwhm / 2.355
    pb = np.exp(-0.5 * (dist.reshape(-1,1,1,1) / sigma.reshape(1,1,-1,1))**2)
    return pb

