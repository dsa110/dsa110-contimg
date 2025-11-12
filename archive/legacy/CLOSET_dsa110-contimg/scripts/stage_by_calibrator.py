#!/usr/bin/env python3
"""
Select and stage two consecutive 16-subband HDF5 groups around a suitable calibrator transit.

Read-only from /data/incoming; copy via reflink/fast copy to data/hdf5_staging/.

Calibrator shortlist (Dec-focused) uses common standards (3C286, 3C147, 3C48, 3C138).
Transit is estimated with astropy at the DSA-110 location.
"""

import os
import sys
import json
import glob
import shutil
import argparse
from datetime import datetime, timezone

def parse_iso(ts):
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None

def list_stable_hdf5(incoming, min_age_sec=600):
    now = datetime.now(timezone.utc).timestamp()
    out = []
    for p in glob.glob(os.path.join(incoming, "*.hdf5")):
        try:
            st = os.stat(p)
            if not os.path.isfile(p):
                continue
            if now - st.st_mtime >= min_age_sec:
                out.append(p)
        except Exception:
            continue
    return out

def group_by_timestamp(files):
    groups = {}
    for p in files:
        base = os.path.basename(p)
        if "_sb" not in base:
            continue
        prefix = base.split("_sb", 1)[0]
        groups.setdefault(prefix, []).append(p)
    # only groups that have sb00..sb15
    full = {}
    for pref, paths in groups.items():
        have = set()
        for p in paths:
            b = os.path.basename(p)
            try:
                sb = int(b.split("_sb",1)[1].split(".",1)[0])
                have.add(sb)
            except Exception:
                continue
        if all(i in have for i in range(16)):
            full[pref] = sorted(paths)
    return full

def read_dec_from_any(h5path):
    try:
        import h5py
    except Exception:
        return None
    try:
        with h5py.File(h5path, 'r') as f:
            hdr = f.get('Header')
            if hdr is None:
                return None
            for k in ('phase_center_app_dec','dec_app','dec','DEC','Dec'):
                if k in hdr:
                    v = hdr[k][()]
                    try:
                        return float(v)
                    except Exception:
                        try:
                            return float(getattr(v, 'item', lambda: v)())
                        except Exception:
                            pass
    except Exception:
        return None
    return None

def best_calibrator(dec_deg):
    # Minimal catalog with RA, Dec in degrees
    cals = [
        {"name":"3C286","ra": 202.784583, "dec": 30.513611},
        {"name":"3C147","ra":  85.445833, "dec": 49.852000},
        {"name":"3C48", "ra":  24.420417, "dec": 33.159722},
        {"name":"3C138","ra":  80.288750, "dec": 16.639444},
    ]
    if dec_deg is None:
        # default to 3C286
        return cals[0]
    cals.sort(key=lambda c: abs(c["dec"] - dec_deg))
    return cals[0]

def compute_transit_utc(ra_deg, date_hint_iso=None):
    # Use astropy to compute next transit near date_hint (or now)
    try:
        import astropy.units as u
        from astropy.time import Time
        from astropy.coordinates import EarthLocation, SkyCoord, AltAz
    except Exception:
        return None
    # DSA-110 (Owens Valley) approx location
    loc = EarthLocation(lat=37.2314*u.deg, lon=-118.2941*u.deg, height=1200*u.m)
    # Build a robust Time origin: prefer provided ISO (normalize '+00:00' to 'Z'), else now
    if date_hint_iso:
        iso = str(date_hint_iso).replace('+00:00', 'Z')
        try:
            t0 = Time(iso, format='isot', scale='utc')
        except Exception:
            t0 = Time.now()
    else:
        t0 = Time.now()
    src = SkyCoord(ra=ra_deg*u.deg, dec=0*u.deg)
    # Find when hour angle ~ 0 by scanning around t0
    dt_hours = [-4,-2,-1,-0.5,0,0.5,1,2,4]
    best = None
    best_alt = -1e9
    for dh in dt_hours:
        t = t0 + dh*u.hour
        altaz = src.transform_to(AltAz(obstime=t, location=loc))
        alt = altaz.alt.deg
        if alt > best_alt:
            best_alt = alt
            best = t
    return best.to_datetime(timezone=timezone.utc) if best else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--incoming', default='/data/incoming')
    ap.add_argument('--staging', default='data/hdf5_staging')
    ap.add_argument('--min-age-min', type=float, default=10.0)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    files = list_stable_hdf5(args.incoming, min_age_sec=int(args.min_age_min*60))
    groups = group_by_timestamp(files)
    if not groups:
        print(json.dumps({"success": False, "error": "No full 16-subband groups found"}))
        return 2
    # choose a reference file to read dec
    ref_file = sorted(files)[0]
    dec = read_dec_from_any(ref_file)
    cal = best_calibrator(dec)
    # parse available timestamps
    entries = []
    for pref, paths in groups.items():
        ts = parse_iso(pref)
        if ts is None:
            continue
        entries.append((ts, pref, paths))
    if not entries:
        print(json.dumps({"success": False, "error": "No parsable timestamp groups"}))
        return 2
    entries.sort()
    # approximate transit time (use only RA)
    tr = compute_transit_utc(cal["ra"]) if isinstance(cal, dict) else None
    # pick closest group to transit
    def tdsec(t):
        return abs((t - tr).total_seconds()) if (t is not None and tr is not None) else 0
    entries.sort(key=lambda e: tdsec(e[0]))
    pick = entries[0]
    # find the next chronological group (second set)
    idx = entries.index(pick)
    second = entries[idx+1] if idx+1 < len(entries) else None
    selected = [pick, second] if second else [pick]

    # Stage copies
    staged = []
    os.makedirs(args.staging, exist_ok=True)
    for (ts, pref, paths) in selected:
        dest_dir = os.path.join(args.staging, pref)
        if not args.dry_run:
            os.makedirs(dest_dir, exist_ok=True)
        out_paths = []
        for src in paths:
            dst = os.path.join(dest_dir, os.path.basename(src))
            out_paths.append(dst)
            if args.dry_run:
                continue
            try:
                # Try reflink copy
                os.system("cp --reflink=auto --preserve=mode,timestamps '"+src+"' '"+dst+"'")
            except Exception:
                shutil.copy2(src, dst)
        staged.append({"timestamp": pref, "dest_dir": dest_dir, "files": out_paths})

    print(json.dumps({
        "success": True,
        "reference_file": ref_file,
        "dec_deg": dec,
        "calibrator": cal,
        "transit_utc": tr.isoformat() if tr else None,
        "selected_groups": [{"timestamp": s[0].isoformat() if s[0] else None, "prefix": s[1]} for s in selected],
        "staged": staged,
        "note": "Source left untouched; copies placed under staging."
    }, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())


