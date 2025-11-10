"""
Constants for DSA-110 continuum imaging pipeline.

Adapted from dsacalib.constants
"""

import numpy as np
import astropy.units as u
from astropy.coordinates import EarthLocation

# Observatory location (DSA-110)
# Coordinates from docs/reference/env.md (authoritative for DSA-110)
DSA110_LAT = 37.2314 * np.pi / 180  # radians
DSA110_LON = -118.2817 * np.pi / 180  # radians
DSA110_ALT = 1222.0  # meters

# Create EarthLocation object for DSA-110
DSA110_LOCATION = EarthLocation(
    lat=DSA110_LAT * u.rad, lon=DSA110_LON * u.rad, height=DSA110_ALT * u.m
)

# Legacy OVRO constants (deprecated - use DSA110_LOCATION instead)
OVRO_LAT = 37.233386982 * np.pi / 180  # radians
OVRO_LON = -118.283405115 * np.pi / 180  # radians
OVRO_ALT = 1188.0519  # meters

# Legacy OVRO_LOCATION (deprecated - use DSA110_LOCATION instead)
OVRO_LOCATION = EarthLocation(
    lat=OVRO_LAT * u.rad, lon=OVRO_LON * u.rad, height=OVRO_ALT * u.m
)

# Telescope parameters
NANTS = 117  # Total number of antennas
NANTS_DATA = 96  # Number of antennas with data
DISH_DIAMETER = 4.65  # meters

# Observation parameters
TSAMP = 0.134217728  # Sample time in seconds
NINT = 93  # Number of integrations
# Note: CASA_TIME_OFFSET removed - use time_utils.CASA_TIME_EPOCH_MJD instead

# Frequency parameters
NCHAN = 48  # Number of channels per subband
NSUBBAND = 16  # Number of subbands
FREQ_START = 1311.25  # MHz
FREQ_END = 1498.75  # MHz
CHANNEL_WIDTH = 0.244140625  # MHz

# Polarizations (MS CORR_TYPE codes: 5=XX, 6=YY)
NPOL = 2
POLARIZATION_ARRAY = np.array([5, 6], dtype=np.int32)

# Speed of light
C_MS = 299792458.0  # m/s
