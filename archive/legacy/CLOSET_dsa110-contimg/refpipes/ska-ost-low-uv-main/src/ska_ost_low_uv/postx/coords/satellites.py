"""satellites.py - Utilities for loading satellite positions."""

from __future__ import annotations

import json
import typing

import requests
from astropy import units as u
from astropy.coordinates import (
    ICRS,
    ITRS,
    TEME,
    AltAz,
    CartesianDifferential,
    CartesianRepresentation,
    SkyCoord,
)
from astropy.time import Time
from sgp4.api import Satrec

if typing.TYPE_CHECKING:  # pragma: no cover
    from ska_ost_low_uv.postx import ApertureArray


def compute_satellite_altaz(aa: ApertureArray, satellite: Satrec) -> AltAz:
    """Compute the ALT/AZ for a satellite viewed by an aperture array.

    Args:
        aa (ApertureArray): ApertureArray object
        satellite (Satrec): SGP4 Satrec ephemeris

    Returns:
        altaz (AltAz): Apparent satellite position in altitude-azimuth
    """
    t = aa.t[aa.idx['t']]

    error_code, teme_p, teme_v = satellite.sgp4(t.jd1, t.jd2)  # in km and km/s
    teme_p = CartesianRepresentation(teme_p * u.km)
    teme_v = CartesianDifferential(teme_v * u.km / u.s)
    teme = TEME(teme_p.with_differentials(teme_v), obstime=t)
    itrs_geo = teme.transform_to(ITRS(obstime=t))
    topo_itrs_repr = itrs_geo.cartesian.without_differentials() - aa.earthloc.get_itrs(t).cartesian

    itrs_topo = ITRS(topo_itrs_repr, obstime=t, location=aa.earthloc)
    altaz = itrs_topo.transform_to(AltAz(location=aa.earthloc, obstime=t))

    return altaz


def compute_satellite_radec(aa: ApertureArray, satellite: Satrec) -> SkyCoord:
    """Compute the RA/DEC for a satellite viewed by an aperture array.

    Args:
        aa (ApertureArray): ApertureArray object
        satellite (Satrec): SGP4 Satrec ephemeris

    Returns:
        radec (SkyCoord): Apparent satellite position in RA/DEC
    """
    t = aa.t[aa.idx['t']]
    altaz = compute_satellite_altaz(aa, satellite)
    # This next line seems necessary -- removes all other info apart from Alt/Az
    # I think this is needed to give 'apparent RA' instead of earth-centred?
    _altaz = AltAz(az=altaz.az, alt=altaz.alt, obstime=t, location=aa.earthloc)
    radec = SkyCoord(_altaz.transform_to(ICRS()))

    return radec


def load_tles(aa: ApertureArray, filename: str) -> dict:
    """Load the TLE data, assuming three lines per entry.

    Args:
        aa (ApertureArray): ApertureArray object
        filename (str): Name of file to read.

    Returns:
        satdict (dict): Dictionary of satellite SGP4 Satrec objects
    """
    with open(filename, 'r') as fh:
        lines = fh.readlines()
    satdict = {}

    for ii in range(len(lines) // 3):
        name = lines[3 * ii].strip()
        l1 = lines[3 * ii + 1].strip()
        l2 = lines[3 * ii + 2].strip()
        satdict[name] = Satrec.twoline2rv(l1, l2)
    return satdict


def satchecker_lookup_norad(aa: ApertureArray, name: str) -> str:
    """Search for NORAD ID for a given satellite.

    Args:
        aa (ApertureArray): ApertureArray object
        name (str): Name of the satellite.

    Returns:
        norad_id (str): NORAD ID of the satellite.

    Notes:
        https://satchecker.readthedocs.io/en/latest/tools_satellites.html#satellite-information
    """
    url = 'https://satchecker.cps.iau.org/tools/norad-ids-from-name/'
    params = {'name': name}
    r = requests.get(url, params=params)

    if len(r.json()) > 0:
        norad_id = r.json()[0]['norad_id']
        return norad_id
    else:
        debug = json.dumps(r.json(), indent=4)
        raise RuntimeError(f'Could not find NORAD ID: \n {debug}')


def satchecker_get_tle(aa: ApertureArray, t: Time, name: str = None, norad_id: str = None):
    """Get TLE record from satchecker.

    Requires either a name or a norad_id, and a time.

    Args:
        aa (ApertureArray): ApertureArray object
        t (Time): time of observation.
        name (str): Name of satellite.
        norad_id (str): NORAD ID of satellite.

    Returns:
        tle (Satrec): A SGP4 Satrec from the TLE data.

    Notes:
        https://satchecker.readthedocs.io/en/latest/tools_tle.html
    """
    if norad_id is None:
        norad_id = satchecker_lookup_norad(aa, name)

    url = 'https://satchecker.cps.iau.org/tools/get-nearest-tle/'
    epoch = t.jd

    params = {'id': norad_id, 'id_type': 'catalog', 'epoch': f'{epoch}'}

    r = requests.get(url, params=params)
    if len(r.json()) > 0:
        tle_data = r.json()[0]['tle_data'][0]
        tle = Satrec.twoline2rv(tle_data['tle_line1'], tle_data['tle_line2'])
        return tle
    else:
        debug = json.dumps(r.json(), indent=4)
        raise RuntimeError(f'Could not load TLE data: \n {debug}')


def satchecker_above_horizon(aa: ApertureArray, min_altitude: float = 30, **kwargs) -> dict[SkyCoord]:
    """Return list of satellites above the horizon.

    This returns the apparent sky coordinates as an astropy SkyCoord (not an SGP4.Satrec)

    Args:
        aa (ApertureArray):   Aperture array object to use.
        min_altitude (float): Minimum altitude above horizon to return, in degrees.
        kwargs (dict): Additional keyword arguments to pass to the request as parameters.

    Optional kwargs:
        min_range: Minimum range in kilometers. Default is 0.
        max_range: Maximum range in kilometers. Default is 1500000.
        illuminated_only: If True, only return satellites that are illuminated. Default is False.
        constellation: Name of the satellite constellation to filter by.

    Returns:
        sat_dict (SkyCoord): List of satellites, returned as SkyCoords
    """
    url = 'https://satchecker.cps.iau.org/fov/satellites-above-horizon/'
    params = {
        'latitude': aa.earthloc.geodetic.lat.value,
        'longitude': aa.earthloc.geodetic.lon.value,
        'elevation': aa.earthloc.geodetic.height.value,
        'julian_date': aa.t[aa.idx['t']].jd,
        'min_altitude': min_altitude,
    }
    params.update(kwargs)

    r = requests.get(url, params=params)

    sat_dict = {}
    for item in r.json()['data']:
        name = item['name']
        sc = SkyCoord(item['ra'], item['dec'], unit='deg')
        sat_dict[name] = sc

    return sat_dict
