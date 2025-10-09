from typing import List, Tuple

import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation, Angle
import astropy.units as u


OVRO = EarthLocation.from_geodetic(lon=Angle(-118.2817, u.deg), lat=Angle(37.2314, u.deg), height=1222 * u.m)
SIDEREAL_RATE = 1.002737909350795  # sidereal days per solar day


def next_transit_time(ra_deg: float, start_time_mjd: float, location: EarthLocation = OVRO, max_iter: int = 4) -> Time:
    """Compute next transit (HA=0) after start_time_mjd for a source with RA=ra_deg."""
    ra_hours = Angle(ra_deg, u.deg).to(u.hourangle).value
    t = Time(start_time_mjd, format="mjd", scale="utc", location=location)
    for _ in range(max_iter):
        lst = t.sidereal_time("apparent").hour
        delta_lst = (ra_hours - lst + 12) % 24 - 12  # wrap to [-12, +12]
        delta_utc_days = (delta_lst / 24.0) / SIDEREAL_RATE
        t = t + delta_utc_days * u.day
    if t < Time(start_time_mjd, format="mjd", scale="utc"):
        t = t + (1.0 / SIDEREAL_RATE) * u.day
    return t


def previous_transits(
    ra_deg: float,
    *,
    start_time: Time | None = None,
    n: int = 3,
    location: EarthLocation = OVRO,
) -> List[Time]:
    """Return the previous n meridian transits (UTC) for a source with RA=ra_deg.

    The computation finds the next transit after ``start_time`` (default: now),
    then steps backward in 1 sidereal-day increments to list previous transits.
    """
    t0 = start_time or Time.now()
    tnext = next_transit_time(ra_deg, t0.mjd, location=location)
    sidereal_day = (1.0 / SIDEREAL_RATE) * u.day
    out: List[Time] = []
    if tnext < t0:
        # Next transit already occurred; include it as the first "previous"
        cur = tnext
    else:
        # Back up one sidereal day from the upcoming transit
        cur = tnext - sidereal_day
    for _ in range(max(0, n)):
        out.append(cur)
        cur = cur - sidereal_day
    return out


def cal_in_datetime(dt_start_iso: str, transit_time: Time, duration: u.Quantity = 5 * u.min, filelength: u.Quantity = 15 * u.min) -> bool:
    """Return True if a file starting at dt_start_iso overlaps the desired window around transit.

    A file of length `filelength` starting at `dt_start_iso` overlaps a window of +/- duration around `transit_time`.
    """
    mjd0 = Time(dt_start_iso, scale="utc").mjd
    mjd1 = (Time(dt_start_iso, scale="utc") + filelength).mjd
    window0 = (transit_time - duration).mjd
    window1 = (transit_time + duration).mjd
    return (mjd0 <= window1) and (mjd1 >= window0)


def pick_best_observation(observations: List[Tuple[str, float, float]], transit_time: Time) -> Tuple[str, float, float]:
    """Pick observation whose midpoint is closest to transit.

    observations: list of (obs_id, start_mjd, end_mjd)
    returns: (obs_id, mid_mjd, delta_minutes)
    """
    best = None
    best_dt = None
    for obs_id, mjd0, mjd1 in observations:
        mid = 0.5 * (mjd0 + mjd1)
        dt_min = abs((Time(mid, format="mjd") - transit_time).to(u.min).value)
        if (best_dt is None) or (dt_min < best_dt):
            best_dt = dt_min
            best = (obs_id, mid, dt_min)
    return best

