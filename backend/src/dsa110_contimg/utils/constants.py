"""
Constants for DSA-110 continuum imaging pipeline.

Adapted from dsacalib.constants
"""

# pylint: disable=no-member  # astropy.units dynamic attributes

import astropy.units as u
import numpy as np
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

# Observatory coordinates for external use
DSA110_LATITUDE = 37.2314
DSA110_LONGITUDE = -118.2817