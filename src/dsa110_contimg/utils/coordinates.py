"""
Coordinate and source utilities for DSA-110.

Adapted from dsacalib.utils
"""

import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
import casatools as cc

from . import constants as ct


class Direction:
    """
    Class for handling coordinate conversions.
    
    Parameters
    ----------
    epoch : str
        Coordinate epoch (e.g., 'J2000', 'HADEC')
    lon : astropy.units.Quantity
        Longitude coordinate
    lat : astropy.units.Quantity
        Latitude coordinate
    obstime : astropy.time.Time, optional
        Observation time
    observatory : str
        Observatory name for CASA (default: 'OVRO_MMA')
    """
    
    def __init__(self, epoch, lon, lat, obstime=None, observatory="OVRO_MMA"):
        self.epoch = epoch
        self.observatory = observatory
        
        # Handle lon/lat - can be Quantity objects or floats (assumed radians)
        if isinstance(lon, u.Quantity):
            self.lon = lon
        else:
            self.lon = lon * u.rad
        
        if isinstance(lat, u.Quantity):
            self.lat = lat
        else:
            self.lat = lat * u.rad
        
        # Handle obstime - can be Time object or float MJD
        if obstime is not None:
            if isinstance(obstime, Time):
                self.obstime = obstime
            else:
                # Assume it's a float MJD
                self.obstime = Time(obstime, format='mjd')
        else:
            self.obstime = None
        
        # Set up CASA tools
        self.me = cc.measures()
        self.qa = cc.quanta()
        
        if self.observatory is not None:
            self.me.doframe(self.me.observatory(self.observatory))
        
        if self.obstime is not None:
            self.me.doframe(self.me.epoch('UTC', self.qa.quantity(self.obstime.mjd, 'd')))
    
    def J2000(self, obstime=None, observatory=None):
        """
        Convert to J2000 coordinates.
        
        Parameters
        ----------
        obstime : astropy.time.Time, optional
            Observation time (overrides object obstime)
        observatory : str, optional
            Observatory name (overrides object observatory)
        
        Returns
        -------
        ra : astropy.units.Quantity
            Right Ascension in J2000
        dec : astropy.units.Quantity
            Declination in J2000
        """
        if obstime is not None:
            self.obstime = obstime
        if observatory is not None:
            self.observatory = observatory
        
        # Update reference frame
        if self.observatory is not None:
            self.me.doframe(self.me.observatory(self.observatory))
        if self.obstime is not None:
            self.me.doframe(self.me.epoch('UTC', self.qa.quantity(self.obstime.mjd, 'd')))
        
        # Convert to J2000
        direction = self.me.direction(
            self.epoch,
            self.qa.quantity(self.lon.to_value(u.rad), 'rad'),
            self.qa.quantity(self.lat.to_value(u.rad), 'rad')
        )
        
        j2000_dir = self.me.measure(direction, 'J2000')
        
        ra = j2000_dir['m0']['value'] * u.rad
        dec = j2000_dir['m1']['value'] * u.rad
        
        return ra, dec
    
    def hadec(self, obstime=None, observatory=None):
        """
        Convert to Hour Angle-Declination coordinates.
        
        Parameters
        ----------
        obstime : astropy.time.Time, optional
            Observation time (overrides object obstime)
        observatory : str, optional
            Observatory name (overrides object observatory)
        
        Returns
        -------
        ha : astropy.units.Quantity
            Hour Angle
        dec : astropy.units.Quantity
            Declination
        """
        if obstime is not None:
            self.obstime = obstime
        if observatory is not None:
            self.observatory = observatory
        
        # Update reference frame
        if self.observatory is not None:
            self.me.doframe(self.me.observatory(self.observatory))
        if self.obstime is not None:
            self.me.doframe(self.me.epoch('UTC', self.qa.quantity(self.obstime.mjd, 'd')))
        
        # Convert to HADEC
        direction = self.me.direction(
            self.epoch,
            self.qa.quantity(self.lon.to_value(u.rad), 'rad'),
            self.qa.quantity(self.lat.to_value(u.rad), 'rad')
        )
        
        hadec_dir = self.me.measure(direction, 'HADEC')
        
        ha = hadec_dir['m0']['value'] * u.rad
        dec = hadec_dir['m1']['value'] * u.rad
        
        return ha, dec


def generate_calibrator_source(name, ra, dec, flux=1.0, epoch="J2000",
                               pa=None, maj_axis=None, min_axis=None):
    """
    Generate a calibrator source object.
    
    Parameters
    ----------
    name : str
        Source name
    ra : astropy.units.Quantity
        Right Ascension
    dec : astropy.units.Quantity
        Declination
    flux : float
        Flux in Jy (default: 1.0)
    epoch : str
        Coordinate epoch (default: 'J2000')
    pa : astropy.units.Quantity, optional
        Position angle
    maj_axis : astropy.units.Quantity, optional
        Major axis size
    min_axis : astropy.units.Quantity, optional
        Minor axis size
    
    Returns
    -------
    source : SimpleNamespace
        Source object with attributes: name, ra, dec, flux, epoch, etc.
    """
    from types import SimpleNamespace
    
    source = SimpleNamespace()
    source.name = name
    source.ra = ra
    source.dec = dec
    source.flux = flux
    source.epoch = epoch
    source.pa = pa
    source.maj_axis = maj_axis
    source.min_axis = min_axis
    
    # Create SkyCoord for convenience
    source.coord = SkyCoord(ra=ra, dec=dec, frame='icrs')
    
    return source


def to_deg(string):
    """
    Convert a coordinate string to degrees.
    
    Parameters
    ----------
    string : str
        Coordinate string (e.g., '12:34:56.7')
    
    Returns
    -------
    float
        Coordinate in degrees
    """
    components = string.split(':')
    if len(components) == 3:
        deg = float(components[0])
        minutes = float(components[1])
        seconds = float(components[2])
        sign = 1 if deg >= 0 else -1
        return deg + sign * (minutes / 60.0 + seconds / 3600.0)
    else:
        return float(string)

