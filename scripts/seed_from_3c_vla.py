#!/usr/bin/env python3
import argparse
import os
import pickle
from typing import List

from core.calibration.calibrator_cache import CalibratorCache, CachedSource, SEED_CSV


def load_3c(path: str) -> List[CachedSource]:
    rows: List[CachedSource] = []
    with open(path, 'rb') as f:
        data = pickle.load(f)
    # data: { '3C286': ['13h31m08.287984s','30d30\'32.958850"','1331+305'], ... }
    for name, vals in data.items():
        try:
            ra_str, dec_str, _ = vals
            # parse simple hms/dms strings via astropy
            from astropy.coordinates import Angle
            import astropy.units as u
            ra = Angle(ra_str).to(u.deg).value
            dec = Angle(dec_str).to(u.deg).value
            rows.append(CachedSource(
                name=name,
                ra_deg=ra,
                dec_deg=dec,
                flux_jy_ref=None,
                ref_freq_hz=None,
                spectral_index=None,
                catalog='3C'
            ))
        except Exception:
            continue
    return rows


def load_vla(path: str) -> List[CachedSource]:
    # VLA_cals appears to be a large pickle; if format differs, skip for now
    try:
        with open(path, 'rb') as f:
            _ = pickle.load(f)
    except Exception:
        return []
    return []


def main():
    p = argparse.ArgumentParser(description='Create seed.csv from 3C_VLA_cals and VLA_cals pickles.')
    p.add_argument('--threec', type=str, default='archive/reference_pipelines/radiotools/Radio_Astronomy/3C_VLA_cals')
    p.add_argument('--vla', type=str, default='archive/reference_pipelines/radiotools/Radio_Astronomy/VLA_cals')
    args = p.parse_args()

    cache = CalibratorCache()
    rows: List[CachedSource] = []
    if os.path.exists(args.threec):
        rows.extend(load_3c(args.threec))
    if os.path.exists(args.vla):
        rows.extend(load_vla(args.vla))

    cache.write_csv(SEED_CSV, rows)
    print(f"Wrote {len(rows)} seed rows to {SEED_CSV}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
