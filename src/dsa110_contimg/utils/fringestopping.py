"""
Fringestopping utilities for DSA-110.

Adapted from dsamfs and dsacalib
"""

import astropy.units as u

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

import casatools as cc
import numpy as np
from astropy.coordinates import angular_separation
from numba import jit
from scipy.special import j1

from . import constants as ct


def calc_uvw_blt(blen, tobs, src_epoch, src_lon, src_lat, obs="OVRO_MMA"):
    """
    Calculate uvw coordinates for baseline-time pairs.

    Uses CASA to calculate the u,v,w coordinates of the baselines towards a
    source or phase center at the specified times and observatory.

    Parameters
    ----------
    blen : ndarray
        The ITRF coordinates of the baselines. Shape (nblt, 3), units of meters.
    tobs : ndarray
        Array of times in MJD for which to calculate uvw coordinates, shape (nblt).
    src_epoch : str
        The epoch of the source or phase-center, e.g. 'J2000' or 'HADEC'
    src_lon : astropy.units.Quantity
        The longitude of the source or phase-center
    src_lat : astropy.units.Quantity
        The latitude of the source or phase-center
    obs : str
        The name of the observatory in CASA (default: 'OVRO_MMA')

    Returns
    -------
    buvw : ndarray
        The uvw values for each baseline-time. Shape (nblt, 3), units of meters.
    """
    nblt = tobs.shape[0]
    buvw = np.zeros((nblt, 3))

    # Define the reference frame
    me = cc.measures()
    qa = cc.quanta()

    if obs is not None:
        me.doframe(me.observatory(obs))

    if not isinstance(src_lon.ndim, float) and src_lon.ndim > 0:
        assert src_lon.ndim == 1
        assert src_lon.shape[0] == nblt
        assert src_lat.shape[0] == nblt
        direction_set = False
    else:
        if (src_epoch == "HADEC") and (nblt > 1):
            raise TypeError(
                "HA and DEC must be specified at each baseline-time in tobs."
            )
        me.doframe(
            me.direction(
                src_epoch,
                qa.quantity(src_lon.to_value(u.deg), "deg"),
                qa.quantity(src_lat.to_value(u.deg), "deg"),
            )
        )
        direction_set = True

    contains_nans = False
    for i in range(nblt):
        me.doframe(me.epoch("UTC", qa.quantity(tobs[i], "d")))
        if not direction_set:
            me.doframe(
                me.direction(
                    src_epoch,
                    qa.quantity(src_lon[i].to_value(u.deg), "deg"),
                    qa.quantity(src_lat[i].to_value(u.deg), "deg"),
                )
            )
        bl = me.baseline(
            "itrf",
            qa.quantity(blen[i, 0], "m"),
            qa.quantity(blen[i, 1], "m"),
            qa.quantity(blen[i, 2], "m"),
        )
        # Get the uvw coordinates
        try:
            buvw[i, :] = me.touvw(bl)[1]["value"]
        except KeyError:
            contains_nans = True
            buvw[i, :] = np.ones(3) * np.nan

    if contains_nans:
        print("Warning: some solutions not found for u, v, w coordinates")

    return buvw


def calc_uvw(blen, tobs, src_epoch, src_lon, src_lat, obs="OVRO_MMA"):
    """
    Calculate uvw coordinates for baselines and times.

    Uses CASA to calculate the u,v,w coordinates of baselines towards a
    source or phase center at the specified times.

    Parameters
    ----------
    blen : ndarray
        The ITRF coordinates of the baselines. Shape (nbaselines, 3), units of meters.
    tobs : ndarray or float
        Array of times in MJD or single time value
    src_epoch : str
        The epoch of the source or phase-center, e.g. 'J2000' or 'HADEC'
    src_lon : astropy.units.Quantity
        The longitude of the source or phase-center
    src_lat : astropy.units.Quantity
        The latitude of the source or phase-center
    obs : str
        The name of the observatory in CASA (default: 'OVRO_MMA')

    Returns
    -------
    bu : ndarray
        The u-value for each time and baseline, in meters. Shape (nbaselines, ntimes).
    bv : ndarray
        The v-value for each time and baseline, in meters. Shape (nbaselines, ntimes).
    bw : ndarray
        The w-value for each time and baseline, in meters. Shape (nbaselines, ntimes).
    """
    # Ensure tobs is array
    if not hasattr(tobs, "__len__"):
        tobs = np.array([tobs])
    else:
        tobs = np.asarray(tobs)

    nt = tobs.shape[0]
    nb = blen.shape[0]
    bu = np.zeros((nt, nb))
    bv = np.zeros((nt, nb))
    bw = np.zeros((nt, nb))

    # Define the reference frame
    me = cc.measures()
    qa = cc.quanta()
    if obs is not None:
        me.doframe(me.observatory(obs))

    if not isinstance(src_lon.ndim, float) and src_lon.ndim > 0:
        assert src_lon.ndim == 1
        assert src_lon.shape[0] == nt
        assert src_lat.shape[0] == nt
        direction_set = False
    else:
        if (src_epoch == "HADEC") and (nt > 1):
            raise TypeError("HA and DEC must be specified at each time in tobs.")
        me.doframe(
            me.direction(
                src_epoch,
                qa.quantity(src_lon.to_value(u.deg), "deg"),
                qa.quantity(src_lat.to_value(u.deg), "deg"),
            )
        )
        direction_set = True

    contains_nans = False

    for i in range(nt):
        me.doframe(me.epoch("UTC", qa.quantity(tobs[i], "d")))
        if not direction_set:
            me.doframe(
                me.direction(
                    src_epoch,
                    qa.quantity(src_lon[i].to_value(u.deg), "deg"),
                    qa.quantity(src_lat[i].to_value(u.deg), "deg"),
                )
            )
        for j in range(nb):
            bl = me.baseline(
                "itrf",
                qa.quantity(blen[j, 0], "m"),
                qa.quantity(blen[j, 1], "m"),
                qa.quantity(blen[j, 2], "m"),
            )
            # Get the uvw coordinates
            try:
                uvw = me.touvw(bl)[1]["value"]
                bu[i, j], bv[i, j], bw[i, j] = uvw[0], uvw[1], uvw[2]
            except KeyError:
                contains_nans = True
                bu[i, j], bv[i, j], bw[i, j] = np.nan, np.nan, np.nan

    if contains_nans:
        print("Warning: some solutions not found for u, v, w coordinates")

    return bu.T, bv.T, bw.T


def calc_uvw_interpolate(blen, tobs, epoch, lon, lat):
    """
    Calculate uvw coordinates with linear interpolation.

    Parameters
    ----------
    blen : ndarray
        The ITRF coordinates of the baselines. Shape (nbaselines, 3), units of meters.
    tobs : astropy.time.Time
        Array of times
    epoch : str
        The epoch of the source or phase-center
    lon : astropy.units.Quantity
        The longitude of the source or phase-center
    lat : astropy.units.Quantity
        The latitude of the source or phase-center

    Returns
    -------
    buvw : ndarray
        The uvw coordinates. Shape (ntimes, nbaselines, 3).
    """
    ntimebins = len(tobs)
    buvw_start = calc_uvw(blen, tobs.mjd[0], epoch, lon, lat)
    buvw_start = np.array(buvw_start).T

    buvw_end = calc_uvw(blen, tobs.mjd[-1], epoch, lon, lat)
    buvw_end = np.array(buvw_end).T

    buvw = (
        buvw_start
        + ((buvw_end - buvw_start) / (ntimebins - 1))
        * np.arange(ntimebins)[:, np.newaxis, np.newaxis]
    )

    return buvw


def amplitude_sky_model(source, ant_ra, pt_dec, fobs, dish_dia=4.65, spind=0.7):
    """
    Calculate amplitude primary beam response for a source.

    Parameters
    ----------
    source : object
        Source object with ra, dec, and flux attributes
    ant_ra : astropy.units.Quantity
        Antenna RA (or HA)
    pt_dec : astropy.units.Quantity
        Pointing declination
    fobs : ndarray
        Observed frequencies in GHz
    dish_dia : float
        Dish diameter in meters
    spind : float
        Spectral index

    Returns
    -------
    famps : ndarray
        Flux amplitudes accounting for primary beam
    """
    # Calculate angular separation
    sep = angular_separation(
        ant_ra.to_value(u.rad),
        pt_dec.to_value(u.rad),
        source.ra.to_value(u.rad),
        source.dec.to_value(u.rad),
    )

    # Primary beam response (Airy disk)
    x = (np.pi * dish_dia * np.sin(sep)) / (ct.C_MS / (fobs * 1e9))
    pb = (2 * j1(x) / x) ** 2
    pb[x == 0] = 1.0

    # Apply spectral index
    famps = source.flux * pb * ((fobs / 1.4) ** spind)  # Reference freq 1.4 GHz

    return famps
