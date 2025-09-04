# core/telescope/dsa110.py
"""
DSA-110 telescope constants and utilities.

This module consolidates all DSA-110 specific constants and utilities
that were previously scattered across the codebase.
"""

import numpy as np
from astropy.coordinates import EarthLocation
import astropy.units as u


# DSA-110 Location (OVRO site)
OVRO_LON = -2.064427799136453  # radians
OVRO_LAT = 0.6498455107238486  # radians  
OVRO_ALT = 1188.0519  # meters

# Create EarthLocation object
loc_dsa110 = EarthLocation(lat=OVRO_LAT*u.rad, lon=OVRO_LON*u.rad, height=OVRO_ALT*u.m)

# Set telescope name for CASA compatibility
# Using CARMA as it's better supported than DSA-110 in CASA
loc_dsa110.info.name = 'CARMA'

# Dish diameter
diam_dsa110 = 4.7  # meters

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
    110, 111, 112, 113, 114, 115
], dtype=int)

# Generate antenna names
valid_antenna_names_dsa110 = np.array([f"pad{ind+1}" for ind in valid_antennas_dsa110])


def ant_inds_to_names_dsa110(inds):
    """
    Convert antenna indices to names.
    
    Args:
        inds: Array of antenna indices (0-based)
        
    Returns:
        Array of antenna names (pad001, pad002, etc.)
    """
    if np.any(inds < 0) or np.any(inds > 116):
        raise ValueError('Index too high/low (should be 0 to 116)')
    return np.array([f"pad{ind+1}" for ind in inds])


def ant_names_to_inds_dsa110(names):
    """
    Convert antenna names to indices.
    
    Args:
        names: Array of antenna names (pad001, pad002, etc.)
        
    Returns:
        Array of antenna indices (0-based)
    """
    if not np.any([n[:3] == 'pad' for n in names]):
        raise ValueError('Name not recognized - should be "pad#"')
    return np.array([int(n[3:])-1 for n in names], dtype=int)


def get_valid_antennas():
    """Get list of valid antenna indices."""
    return valid_antennas_dsa110.copy()


def get_valid_antenna_names():
    """Get list of valid antenna names."""
    return valid_antenna_names_dsa110.copy()


def is_valid_antenna(ant_index):
    """Check if an antenna index is valid."""
    return ant_index in valid_antennas_dsa110


def get_telescope_location():
    """Get the DSA-110 telescope location."""
    return loc_dsa110


def get_dish_diameter():
    """Get the DSA-110 dish diameter in meters."""
    return diam_dsa110
