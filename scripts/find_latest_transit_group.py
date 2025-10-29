#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
from typing import List, Optional, Tuple

import numpy as np
import astropy.units as u  # type: ignore
from astropy.time import Time  # type: ignore
from pyuvdata import UVData  # type: ignore

from dsa110_contimg.calibration.schedule import previous_transits
from dsa110_contimg.calibration.catalogs import read_vla_parsed_catalog_csv
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import find_subband_groups


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


def _group_ts(file_path: str) -> str:
    base = os.path.basename(file_path)
    return base.split('_sb', 1)[0]


def _group_mid_time(file_list: List[str]) -> Time:
    return Time(_group_ts(file_list[0]))


def _group_dec_deg(file_list: List[str]) -> Optional[float]:
    if not file_list:
        return None
    sb = file_list[0]
    try:
        uvd = UVData()
        uvd.read(sb, file_type='uvh5', run_check=False, read_data=False)
        if getattr(uvd, 'phase_center_dec', None) is not None:
            dec_rad = float(uvd.phase_center_dec)
        else:
            dec_rad = float(uvd.extra_keywords.get('phase_center_dec', np.nan))
        dec_deg = np.degrees(dec_rad)
        return dec_deg if np.isfinite(dec_deg) else None
    except Exception:
        return None


def find_latest_transit_group(name: str,
                              input_dir: str,
                              catalogs: List[str],
                              *,
                              window_minutes: int = 60,
                              max_days_back: int = 14,
                              dec_tolerance_deg: float = 2.0) -> dict:
    ra_deg, dec_deg = _load_radec(name, catalogs)
    transits = previous_transits(ra_deg, start_time=Time.now(), n=max_days_back)

    for t in transits:
        half = window_minutes // 2
        t0 = (t - half * u.min).to_datetime().strftime('%Y-%m-%d %H:%M:%S')
        t1 = (t + half * u.min).to_datetime().strftime('%Y-%m-%d %H:%M:%S')
        groups = find_subband_groups(input_dir, t0, t1)
        if not groups:
            continue
        # Prefer groups whose mid-time is closest to transit, and whose Dec matches target
        candidates = []
        for g in groups:
            mid = _group_mid_time(g)
            dt_min = abs((mid - t).to(u.min)).value
            gdec = _group_dec_deg(g)
            dec_ok = (gdec is not None) and (abs(gdec - dec_deg) <= dec_tolerance_deg)
            candidates.append((dt_min, dec_ok, g, mid))
        # Sort by (time proximity, dec match priority)
        candidates.sort(key=lambda x: (x[0], 0 if x[1] else 1))
        if candidates:
            dt_min, dec_ok, gbest, mid = candidates[0]
            # Require a full 16-subband group
            sb_codes = sorted(os.path.basename(p).rsplit('_sb', 1)[1].split('.')[0] for p in gbest)
            full = len(gbest) == 16 and all(code.startswith('sb') for code in sb_codes)
            if full:
                return {
                    'name': name,
                    'transit_iso': t.isot,
                    'start_iso': t0,
                    'end_iso': t1,
                    'group_id': _group_ts(gbest[0]),
                    'mid_iso': mid.isot,
                    'delta_minutes': dt_min,
                    'dec_match': bool(dec_ok),
                    'files': sorted(gbest),
                }
    return {
        'name': name,
        'error': 'No 16-subband group found near recent transits',
    }


def main() -> int:
    ap = argparse.ArgumentParser(description='Find most recent 16-file UVH5 group around calibrator transit')
    ap.add_argument('--name', required=True)
    ap.add_argument('--input-dir', default='/data/incoming')
    ap.add_argument('--catalog', action='append', default=[
        '/data/dsa110-contimg/data-samples/catalogs/vla_calibrators_parsed.csv',
        '/data/dsa110-contimg/sim-data-samples/catalogs/vla_calibrators_parsed.csv',
    ])
    ap.add_argument('--window-minutes', type=int, default=60)
    ap.add_argument('--max-days-back', type=int, default=14)
    ap.add_argument('--dec-tolerance-deg', type=float, default=2.0)
    args = ap.parse_args()

    res = find_latest_transit_group(
        args.name,
        args.input_dir,
        catalogs=args.catalog,
        window_minutes=args.window_minutes,
        max_days_back=args.max_days_back,
        dec_tolerance_deg=args.dec_tolerance_deg,
    )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
