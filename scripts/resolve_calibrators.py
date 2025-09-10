#!/usr/bin/env python3
"""
Resolve in-beam calibrators for DSA-110 given either an HDF5 file (to read declination)
or an explicit declination. Uses CalibratorFinder (cache-first, optional online fallback),
computes source visibility (rise/set/transit) at DSA-110, estimates flux at 1.4 GHz,
and writes a structured JSON summary suitable for provenance.
"""

import os
import sys
import json
import argparse
from typing import Optional, Dict, Any, List, Tuple


def _read_header_scalar(hdr, key: str) -> Optional[float]:
    if key in hdr:
        v = hdr[key][()]
        try:
            return float(v)
        except Exception:
            try:
                return float(getattr(v, 'item', lambda: v)())
            except Exception:
                return None
    return None


def read_dec_from_hdf5(h5path: str) -> Optional[float]:
    try:
        import h5py
    except Exception:
        return None
    try:
        with h5py.File(h5path, 'r') as f:
            hdr = f.get('Header')
            if hdr is None:
                return None
            # Prefer explicit app dec if present
            for k in ('phase_center_app_dec', 'dec_app', 'dec', 'DEC', 'Dec'):
                val = _read_header_scalar(hdr, k)
                if val is None:
                    continue
                # Heuristic: values with abs < 10 likely in radians; convert to degrees
                return float(val if abs(val) > 10.0 else (val * 180.0 / 3.141592653589793))
    except Exception:
        return None
    return None


def read_time_from_hdf5(h5path: str) -> Optional[float]:
    """Return a representative time as JD (float) if available."""
    try:
        import h5py
    except Exception:
        return None
    try:
        with h5py.File(h5path, 'r') as f:
            hdr = f.get('Header')
            if hdr is None:
                return None
            if 'time_array' in hdr:
                arr = hdr['time_array'][:]
                if arr is None or len(arr) == 0:
                    return None
                t = float(arr[len(arr)//2])
                # Detect JD vs MJD: JD ~ 2.4e6+, MJD typically < 1e6
                if t > 2.4e6:
                    return t
                else:
                    return t + 2400000.5
    except Exception:
        return None
    return None


def compute_ra_from_hdf5_or_default(h5path: Optional[str], ra_cli_deg: float) -> Tuple[float, str]:
    """Compute RA center degrees.

    If CLI RA is provided and non-zero, use it. Otherwise, derive from HDF5 time_array
    (interpreted as JD) and DSA-110 longitude using apparent sidereal time.
    Returns (ra_deg, source_str).
    """
    if ra_cli_deg and ra_cli_deg != 0.0:
        return float(ra_cli_deg), 'cli:ra'
    try:
        from astropy.time import Time
        import astropy.units as u
        from astropy.coordinates import EarthLocation
    except Exception:
        return 0.0, 'default:0'
    jd = read_time_from_hdf5(h5path) if h5path else None
    if jd is None:
        return 0.0, 'default:0'
    # DSA-110 approximate location (same as used for visibility below)
    loc = EarthLocation(lat=37.2314*u.deg, lon=-118.2941*u.deg, height=1200*u.m)
    t = Time(jd, format='jd', scale='utc')
    lst = t.sidereal_time('apparent', longitude=loc.lon)
    ra_deg = float(lst.to(u.deg).value) % 360.0
    return ra_deg, 'derived:lst_from_hdf5_time'


def find_candidates(ra_deg: float, dec_deg: float, radius_deg: float, min_flux_jy: float) -> List[Dict[str, Any]]:
    from core.calibration.calibrator_finder import CalibratorFinder
    # Query all supported catalogs online (NVSS, FIRST, TGSS, VLASS), with cache-first
    cf = CalibratorFinder(
        catalogs=['nvss', 'first', 'tgss', 'vlass'],
        use_cache=True,
        allow_online_fallback=True,
    )
    cands = cf.find_nearby(ra_deg=ra_deg, dec_deg=dec_deg, radius_deg=radius_deg, min_flux_jy=min_flux_jy)
    # Convert dataclass-like to dicts
    out: List[Dict[str, Any]] = []
    for c in cands:
        out.append({
            'name': c.name,
            'ra_deg': c.ra_deg,
            'dec_deg': c.dec_deg,
            'flux_jy_ref': c.flux_jy_ref,
            'ref_freq_hz': c.ref_freq_hz,
            'spectral_index': c.spectral_index,
            'separation_deg': c.separation_deg,
            'provenance': c.provenance,
        })
    return out


def visibility_for(cands: List[Dict[str, Any]], date_iso: Optional[str]) -> List[Dict[str, Any]]:
    try:
        import astropy.units as u
        from astropy.time import Time
        from astropy.coordinates import SkyCoord, EarthLocation, AltAz
    except Exception:
        # Return without visibility if astropy unavailable
        return [dict(c, transit_utc=None, max_alt_deg=None) for c in cands]

    loc = EarthLocation(lat=37.2314*u.deg, lon=-118.2941*u.deg, height=1200*u.m)
    t0 = Time(date_iso) if date_iso else Time.now()
    out: List[Dict[str, Any]] = []
    for c in cands:
        sc = SkyCoord(ra=c['ra_deg']*u.deg, dec=c['dec_deg']*u.deg, frame='icrs')
        # Simple coarse scan around t0 to approximate transit
        hours = [-6,-4,-2,-1,-0.5,0,0.5,1,2,4,6]
        best_t = None
        best_alt = -1e9
        for h in hours:
            t = t0 + h*u.hour
            alt = sc.transform_to(AltAz(obstime=t, location=loc)).alt.deg
            if alt > best_alt:
                best_alt = alt
                best_t = t
        out.append({**c, 'transit_utc': best_t.to_datetime().isoformat() if best_t else None, 'max_alt_deg': best_alt})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description='Resolve in-beam calibrators and visibility for DSA-110')
    ap.add_argument('--hdf5', help='Path to an HDF5 file to read pointing declination')
    ap.add_argument('--dec-deg', type=float, help='Declination in degrees (fallback if no HDF5)')
    ap.add_argument('--ra-deg', type=float, default=0.0, help='RA center deg (drift scan tolerant)')
    ap.add_argument('--radius-deg', type=float, default=5.0, help='Search radius deg')
    ap.add_argument('--min-flux-jy', type=float, default=0.2, help='Minimum reference flux (Jy)')
    ap.add_argument('--date-iso', help='ISO date for visibility window (defaults to now)')
    args = ap.parse_args()

    dec = None
    src = 'unspecified'
    if args.hdf5:
        dec = read_dec_from_hdf5(args.hdf5)
        src = 'hdf5:Header' if dec is not None else 'hdf5:Header(unavailable)'
    if dec is None and args.dec_deg is not None:
        dec = args.dec_deg
        src = 'cli:dec'

    if dec is None:
        print(json.dumps({'success': False, 'error': 'Declination unavailable; provide --hdf5 or --dec-deg'}))
        return 2

    ra_deg, ra_src = compute_ra_from_hdf5_or_default(args.hdf5, args.ra_deg)
    cands = find_candidates(ra_deg=ra_deg, dec_deg=dec, radius_deg=args.radius_deg, min_flux_jy=args.min_flux_jy)
    vis = visibility_for(cands, args.date_iso)
    # Best: highest max_alt and brightest
    def score(c):
        return (c.get('flux_jy_ref') or 0.0) + 0.01*(c.get('max_alt_deg') or 0.0)
    best = sorted(vis, key=score, reverse=True)[:10]

    print(json.dumps({
        'success': True,
        'declination_deg': dec,
        'declination_source': src,
        'search_center_ra_deg': ra_deg,
        'ra_source': ra_src,
        'search_radius_deg': args.radius_deg,
        'min_flux_jy': args.min_flux_jy,
        'top_candidates': best,
        'count_total': len(vis)
    }, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())


