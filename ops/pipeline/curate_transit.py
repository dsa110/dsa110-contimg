#!/usr/bin/env python3
"""
Curate a transit subdirectory for a given calibrator by symlinking or copying
exact subband UVH5 files for the most recent transit window.

Layout:
  <curated_root>/<name>/<YYYY_MM_DD>/<group_ts>/
    <group_ts>_sb00.hdf5, ..., <group_ts>_sb15.hdf5

This avoids scanning the entire ingest tree by using date-prefixed globbing
and our built-in grouping function.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import astropy.units as u
from astropy.time import Time

from dsa110_contimg.calibration.schedule import previous_transits
from dsa110_contimg.calibration.catalogs import read_vla_parsed_catalog_csv
from dsa110_contimg.conversion.strategies.uvh5_to_ms_converter import find_subband_groups
from pyuvdata import UVData


@dataclass
class CuratedGroup:
    group_ts: str
    files: List[str]


@dataclass
class CuratedTransit:
    name: str
    ra_deg: float
    dec_deg: float
    transit_iso: str
    window_minutes: int
    start_iso: str
    end_iso: str
    curated_root: str
    curated_path: str
    groups: List[CuratedGroup]


def _load_ra_dec(name: str, catalogs: List[str]) -> Tuple[float, float]:
    for p in catalogs:
        try:
            df = read_vla_parsed_catalog_csv(p)
            if name in df.index:
                row = df.loc[name]
                try:
                    ra = float(row['ra_deg'].iloc[0])
                    dec = float(row['dec_deg'].iloc[0])
                except Exception:
                    ra = float(row['ra_deg'])
                    dec = float(row['dec_deg'])
                if np.isfinite(ra) and np.isfinite(dec):
                    return ra, dec
        except Exception:
            continue
    raise RuntimeError(f'Calibrator {name} not found in catalogs: {catalogs}')


def _iso_window(center: Time, minutes: int) -> Tuple[str, str]:
    half = minutes // 2
    t0 = center - half * u.min
    t1 = center + half * u.min
    return (
        t0.to_datetime().strftime('%Y-%m-%d %H:%M:%S'),
        t1.to_datetime().strftime('%Y-%m-%d %H:%M:%S'),
    )


def _group_ts(file_path: str) -> str:
    base = os.path.basename(file_path)
    return base.split('_sb', 1)[0]


def _group_matches_declination(glist: List[str], target_dec_deg: float, tol_deg: float) -> bool:
    """Return True if group's phase_center_dec is within tol of target.

    Reads a single subband UVH5 (first file) with UVData (run_check=False)
    and inspects ``phase_center_dec`` or ``extra_keywords['phase_center_dec']``.
    """
    if not glist:
        return False
    sb = glist[0]
    try:
        uvd = UVData()
        # Fast header-only read is not available; keep it minimal
        uvd.read(sb, file_type='uvh5', run_check=False, read_data=False)
        if hasattr(uvd, 'phase_center_dec') and uvd.phase_center_dec is not None:
            dec_rad = float(uvd.phase_center_dec)
        else:
            dec_rad = float(uvd.extra_keywords.get('phase_center_dec', np.nan))
        dec_deg = np.degrees(dec_rad)
        if not np.isfinite(dec_deg):
            return False
        return abs(dec_deg - target_dec_deg) <= tol_deg
    except Exception:
        return False


def curate_transit(
    name: str,
    input_dir: str,
    curated_root: str,
    *,
    catalogs: List[str],
    window_minutes: int = 60,
    max_days_back: int = 5,
    method: str = 'symlink',  # or 'copy'
    dec_tolerance_deg: float = 2.0,
) -> CuratedTransit:
    ra_deg, dec_deg = _load_ra_dec(name, catalogs)
    # Look back in transits
    transits = previous_transits(ra_deg, start_time=Time.now(), n=max_days_back)
    chosen = None
    groups: List[List[str]] = []
    for t in transits:
        start_iso, end_iso = _iso_window(t, window_minutes)
        g = find_subband_groups(input_dir, start_iso, end_iso)
        # Filter groups by declination proximity to target calibrator
        gf = [glist for glist in g if _group_matches_declination(glist, dec_deg, dec_tolerance_deg)] if g else []
        if gf:
            chosen = (t, start_iso, end_iso)
            groups = gf
            break
    if not chosen:
        raise RuntimeError('No suitable subband groups near recent transits (matching declination)')

    center_t, start_iso, end_iso = chosen
    day = center_t.datetime.strftime('%Y_%m_%d')
    name_s = name.replace('+', '_').replace(' ', '')
    curated_base = Path(curated_root) / name_s / day
    curated_base.mkdir(parents=True, exist_ok=True)

    curated_groups: List[CuratedGroup] = []
    for glist in groups:
        ts = _group_ts(glist[0])
        dest = curated_base / ts
        dest.mkdir(parents=True, exist_ok=True)
        staged: List[str] = []
        for src in glist:
            s = Path(src); d = dest / s.name
            if d.exists():
                staged.append(os.fspath(d)); continue
            if method == 'copy':
                shutil.copy2(s, d)
            else:
                try:
                    os.symlink(s, d)
                except FileExistsError:
                    pass
            staged.append(os.fspath(d))
        curated_groups.append(CuratedGroup(group_ts=ts, files=staged))

    curated = CuratedTransit(
        name=name,
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        transit_iso=center_t.isot,
        window_minutes=window_minutes,
        start_iso=start_iso,
        end_iso=end_iso,
        curated_root=os.fspath(Path(curated_root)),
        curated_path=os.fspath(curated_base),
        groups=curated_groups,
    )

    # Write manifest
    man = curated_base / 'manifest.json'
    with open(man, 'w', encoding='utf-8') as f:
        json.dump({
            'name': curated.name,
            'ra_deg': curated.ra_deg,
            'dec_deg': curated.dec_deg,
            'transit_iso': curated.transit_iso,
            'window_minutes': curated.window_minutes,
            'start_iso': curated.start_iso,
            'end_iso': curated.end_iso,
            'curated_root': curated.curated_root,
            'curated_path': curated.curated_path,
            'groups': [{'group_ts': g.group_ts, 'files': g.files} for g in curated.groups],
        }, f, indent=2)

    return curated


def main() -> int:
    ap = argparse.ArgumentParser(description='Curate transit subdir for a calibrator')
    ap.add_argument('--name', required=True, help='Calibrator name, e.g., 0834+555')
    ap.add_argument('--input-dir', default='/data/incoming')
    ap.add_argument('--curated-root', default='state/curated')
    ap.add_argument('--catalog', action='append', default=[
        '/data/dsa110-contimg/data-samples/catalogs/vla_calibrators_parsed.csv',
        'references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv'
    ])
    ap.add_argument('--window-minutes', type=int, default=60)
    ap.add_argument('--max-days-back', type=int, default=5)
    ap.add_argument('--method', choices=['symlink', 'copy'], default='symlink')
    ap.add_argument('--dec-tolerance-deg', type=float, default=2.0, help='Require group phase_center_dec within this of calibrator dec')
    args = ap.parse_args()

    cur = curate_transit(
        name=args.name,
        input_dir=args.input_dir,
        curated_root=args.curated_root,
        catalogs=args.catalog,
        window_minutes=args.window_minutes,
        max_days_back=args.max_days_back,
        method=args.method,
        dec_tolerance_deg=args.dec_tolerance_deg,
    )
    print(f'Curated: {cur.curated_path}')
    print(f'Window: {cur.start_iso} .. {cur.end_iso} (transit {cur.transit_iso})')
    print(f'Groups: {len(cur.groups)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
