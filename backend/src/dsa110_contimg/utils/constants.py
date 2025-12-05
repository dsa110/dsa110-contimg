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

# Legacy alias (deprecated - use DSA110_LOCATION instead)
# Note: Previously used slightly different OVRO coordinates, now unified to DSA110_LOCATION
OVRO_LOCATION = DSA110_LOCATION

# Observatory coordinates for external use
DSA110_LATITUDE = 37.2314
DSA110_LONGITUDE = -118.2817
