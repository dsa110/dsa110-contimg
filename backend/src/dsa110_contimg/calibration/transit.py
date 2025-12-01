"""
Transit time calculations for DSA-110 calibrators.

Provides utilities for computing meridian transit times of sources
at the DSA-110 site. Used for scheduling observations and finding
optimal calibrator observation windows.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import astropy.units as u
from astropy.coordinates import Angle, EarthLocation
from astropy.time import Time

from dsa110_contimg.utils.constants import DSA110_LOCATION

# Sidereal day in solar days
SIDEREAL_RATE = 1.002737909350795  # sidereal days per solar day


def next_transit_time(
    ra_deg: float,
    start_time_mjd: float,
    location: EarthLocation = DSA110_LOCATION,
    max_iter: int = 4,
) -> Time:
    """Compute the next meridian transit (HA=0) after a given time.

    Uses iterative refinement to find when a source at the given RA
    crosses the local meridian.

    Args:
        ra_deg: Right ascension of the source in degrees
        start_time_mjd: Start time in MJD format
        location: Observatory location (default: DSA-110 site)
        max_iter: Number of iterations for convergence

    Returns:
        astropy Time object for the next transit
    """
    ra_hours = Angle(ra_deg, u.deg).to(u.hourangle).value
    t = Time(start_time_mjd, format="mjd", scale="utc", location=location)

    for _ in range(max_iter):
        lst = t.sidereal_time("apparent").hour
        delta_lst = (ra_hours - lst + 12) % 24 - 12  # wrap to [-12, +12]
        delta_utc_days = (delta_lst / 24.0) / SIDEREAL_RATE
        t = t + delta_utc_days * u.day

    # Ensure we return a time after start_time
    if t < Time(start_time_mjd, format="mjd", scale="utc"):
        t = t + (1.0 / SIDEREAL_RATE) * u.day

    return t


def previous_transits(
    ra_deg: float,
    *,
    start_time: Optional[Time] = None,
    n: int = 3,
    location: EarthLocation = DSA110_LOCATION,
) -> List[Time]:
    """Return the previous n meridian transits (UTC) for a source.

    The computation finds the next transit after ``start_time`` (default: now),
    then steps backward in 1 sidereal-day increments to list previous transits.

    Args:
        ra_deg: Right ascension of the source in degrees
        start_time: Reference time (default: now)
        n: Number of previous transits to return
        location: Observatory location (default: DSA-110 site)

    Returns:
        List of astropy Time objects for previous transits, most recent first
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


def upcoming_transits(
    ra_deg: float,
    *,
    start_time: Optional[Time] = None,
    n: int = 3,
    location: EarthLocation = DSA110_LOCATION,
) -> List[Time]:
    """Return the next n meridian transits (UTC) for a source.

    Args:
        ra_deg: Right ascension of the source in degrees
        start_time: Reference time (default: now)
        n: Number of upcoming transits to return
        location: Observatory location (default: DSA-110 site)

    Returns:
        List of astropy Time objects for upcoming transits
    """
    t0 = start_time or Time.now()
    tnext = next_transit_time(ra_deg, t0.mjd, location=location)
    sidereal_day = (1.0 / SIDEREAL_RATE) * u.day

    out: List[Time] = []
    cur = tnext

    for _ in range(max(0, n)):
        out.append(cur)
        cur = cur + sidereal_day

    return out


def observation_overlaps_transit(
    obs_start_iso: str,
    transit_time: Time,
    window_duration: u.Quantity = 5 * u.min,
    observation_length: u.Quantity = 15 * u.min,
) -> bool:
    """Check if an observation file overlaps a transit window.

    Determines whether a file starting at obs_start_iso (with given length)
    overlaps a window of +/- window_duration centered on transit_time.

    Args:
        obs_start_iso: Observation start time in ISO format
        transit_time: Transit time as astropy Time
        window_duration: Half-width of transit window (default: 5 min)
        observation_length: Length of observation file (default: 15 min)

    Returns:
        True if the observation overlaps the transit window
    """
    obs_start = Time(obs_start_iso, scale="utc")
    obs_end_mjd = (obs_start + observation_length).mjd
    obs_start_mjd = obs_start.mjd

    window_start_mjd = (transit_time - window_duration).mjd
    window_end_mjd = (transit_time + window_duration).mjd

    return (obs_start_mjd <= window_end_mjd) and (obs_end_mjd >= window_start_mjd)


def pick_best_observation(
    observations: List[Tuple[str, float, float]],
    transit_time: Time,
) -> Optional[Tuple[str, float, float]]:
    """Pick the observation whose midpoint is closest to transit.

    Args:
        observations: List of (obs_id, start_mjd, end_mjd) tuples
        transit_time: Target transit time

    Returns:
        Tuple of (obs_id, mid_mjd, delta_minutes) for best observation,
        or None if observations list is empty
    """
    if not observations:
        return None

    best = None
    best_dt = None

    for obs_id, mjd0, mjd1 in observations:
        mid = 0.5 * (mjd0 + mjd1)
        dt_min = abs((Time(mid, format="mjd") - transit_time).to(u.min).value)

        if (best_dt is None) or (dt_min < best_dt):
            best_dt = dt_min
            best = (obs_id, mid, dt_min)

    return best


def transit_time_for_local_time(
    ra_deg: float,
    local_hour: int,
    local_minute: int = 0,
    date_str: Optional[str] = None,
    location: EarthLocation = DSA110_LOCATION,
) -> Optional[Time]:
    """Find when a source with given RA transits at a specific local time.

    This is useful for finding calibrators that transit during specific
    observing windows (e.g., "which calibrators transit around 3 AM local?").

    Args:
        ra_deg: Right ascension of source in degrees
        local_hour: Target local hour (0-23)
        local_minute: Target local minute (0-59)
        date_str: Date in YYYY-MM-DD format (default: today)
        location: Observatory location

    Returns:
        Transit time if one occurs near the target time, or None
    """
    from datetime import datetime, timezone

    if date_str:
        base_date = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        base_date = datetime.now(timezone.utc)

    # Create target time (assume Pacific time, -8 hours from UTC in winter)
    # DSA-110 is in California
    target_utc_hour = (local_hour + 8) % 24  # Approximate UTC offset

    target_time = Time(
        f"{base_date.year}-{base_date.month:02d}-{base_date.day:02d}T{target_utc_hour:02d}:{local_minute:02d}:00",
        scale="utc",
    )

    # Find the nearest transit
    transit = next_transit_time(ra_deg, target_time.mjd - 0.5, location=location)

    # Check if it's within a few hours of target
    delta_hours = abs((transit - target_time).to(u.hour).value)
    if delta_hours < 12:
        return transit

    return None
