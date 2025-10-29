#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import astropy.units as u  # type: ignore
from astropy.time import Time  # type: ignore

from dsa110_contimg.calibration.schedule import previous_transits, cal_in_datetime
from dsa110_contimg.calibration.catalogs import read_vla_parsed_catalog_csv
from dsa110_contimg.conversion.strategies import hdf5_orchestrator as orch

SB_RE = re.compile(r"_sb(\d{2})\.hdf5$")


@dataclass
class GroupInfo:
    group_id: str
    files: List[str]
    mid_mjd: Optional[float]  # may be None if missing
    pt_dec_deg: Optional[float]


def _is_uvh5(path: str) -> bool:
    return path.endswith(".hdf5") and "_sb" in os.path.basename(path)


def _group_id_from_path(path: str) -> Optional[str]:
    base = os.path.basename(path)
    if "_sb" not in base:
        return None
    return base.split("_sb", 1)[0]


def _sb_code_from_path(path: str) -> Optional[str]:
    m = SB_RE.search(path)
    if not m:
        return None
    return f"sb{m.group(1)}"


def _peek_dec_mid(path: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        pt_dec, mid_mjd = orch._peek_uvh5_phase_and_midtime(path)  # type: ignore[attr-defined]
        pt_dec_deg = float(pt_dec.to_value(u.deg)) if pt_dec is not None else None
        mid = float(mid_mjd) if mid_mjd else None
        return pt_dec_deg, mid
    except Exception:
        return None, None


def _load_radec(name: str, catalogs: List[str]) -> Tuple[float, float]:
    for p in catalogs:
        if not os.path.exists(p):
            continue
        try:
            df = read_vla_parsed_catalog_csv(p)
            if name in df.index:
                row = df.loc[name]
                try:
                    ra = float(getattr(row, 'ra_deg').iloc[0])
                    dec = float(getattr(row, 'dec_deg').iloc[0])
                except Exception:
                    ra = float(row['ra_deg'])
                    dec = float(row['dec_deg'])
                if np.isfinite(ra) and np.isfinite(dec):
                    return ra, dec
        except Exception:
            continue
    raise RuntimeError(f"Calibrator {name} not found in catalogs: {catalogs}")


def _scan_groups_recursive(root: str) -> Dict[str, List[str]]:
    acc: Dict[str, Dict[str, str]] = defaultdict(dict)
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith('.hdf5'):
                continue
            if '_sb' not in fn:
                continue
            full = os.path.join(dirpath, fn)
            gid = _group_id_from_path(fn)
            sb = _sb_code_from_path(fn)
            if gid and sb:
                acc[gid][sb] = full
    groups: Dict[str, List[str]] = {}
    for gid, mp in acc.items():
        # Require exactly 16 subbands, sb00..sb15
        expected = [f"sb{idx:02d}" for idx in range(16)]
        if all(k in mp for k in expected):
            groups[gid] = [mp[k] for k in expected]
    return groups


def find_daily_transit_groups(name: str,
                              input_dir: str,
                              catalogs: List[str],
                              *,
                              dec_tolerance_deg: float = 2.0) -> List[dict]:
    ra_deg, dec_deg = _load_radec(name, catalogs)

    groups = _scan_groups_recursive(input_dir)
    if not groups:
        return []

    out: List[dict] = []
    sidereal_day = (1.0 / 1.002737909350795) * u.day

    for gid, files in groups.items():
        # Peek a single subband for dec + mid time
        pt_dec_deg, mid_mjd = _peek_dec_mid(files[0])
        if pt_dec_deg is None or mid_mjd is None:
            continue
        dec_ok = abs(pt_dec_deg - dec_deg) <= dec_tolerance_deg

        # Compute previous transit relative to group midpoint
        mid_t = Time(mid_mjd, format='mjd')
        prev_tr = previous_transits(ra_deg, start_time=mid_t, n=1)[0]
        next_tr = prev_tr + sidereal_day

        # Check if the daily transit (prev or next) falls inside the 5-minute group interval
        # We only know group start from gid timestamp; assume 5-minute length
        try:
            contains_prev = cal_in_datetime(gid, prev_tr, duration=0 * u.min, filelength=5 * u.min)
            contains_next = cal_in_datetime(gid, next_tr, duration=0 * u.min, filelength=5 * u.min)
        except Exception:
            contains_prev = False
            contains_next = False

        if contains_prev or contains_next:
            tr = prev_tr if contains_prev else next_tr
            out.append({
                'name': name,
                'group_id': gid,
                'transit_iso': tr.isot,
                'mid_iso': mid_t.isot,
                'delta_minutes': abs((mid_t - tr).to(u.min).value),
                'pt_dec_deg': pt_dec_deg,
                'target_dec_deg': dec_deg,
                'dec_match': bool(dec_ok),
                'files': files,
            })

    # Sort by transit time descending (most recent first)
    out.sort(key=lambda r: r['transit_iso'], reverse=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description='Find all 16-file groups exactly containing daily transit times')
    ap.add_argument('--name', required=True)
    ap.add_argument('--input-dir', default='/data/incoming')
    ap.add_argument('--catalog', action='append', default=[
        '/data/dsa110-contimg/data-samples/catalogs/vla_calibrators_parsed.csv',
        '/data/dsa110-contimg/sim-data-samples/catalogs/vla_calibrators_parsed.csv',
    ])
    ap.add_argument('--dec-tolerance-deg', type=float, default=2.0)
    args = ap.parse_args()

    res = find_daily_transit_groups(
        args.name,
        args.input_dir,
        catalogs=args.catalog,
        dec_tolerance_deg=args.dec_tolerance_deg,
    )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
