#!/usr/bin/env python3
import argparse
import os
from typing import List, Optional

from astropy.coordinates import SkyCoord
from astropy import units as u
from astroquery.vizier import Vizier

from core.calibration.calibrator_cache import CalibratorCache, CachedSource, NVSS_CSV, VLASS_CSV


NVSS_ID = "VIII/65/nvss"
VLASS_ID = "VIII/106"


def fetch_nvss_region(ra_deg: float, dec_deg: float, radius_deg: float) -> List[CachedSource]:
    Vizier.ROW_LIMIT = -1
    viz = Vizier(columns=['*'])
    center = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame='icrs')
    out: List[CachedSource] = []
    try:
        res = viz.query_region(center, radius=radius_deg * u.deg, catalog=NVSS_ID)
        if not res:
            return out
        tab = res[0]
        for row in tab:
            try:
                ra = float(row['RAJ2000'])
                dec = float(row['DEJ2000'])
                name = str(row['NVSS']) if 'NVSS' in tab.colnames else f"NVSS_{ra:.5f}_{dec:.5f}"
                flux_jy = float(row['S1.4']) / 1000.0 if 'S1.4' in tab.colnames else None
                out.append(CachedSource(
                    name=name,
                    ra_deg=ra,
                    dec_deg=dec,
                    flux_jy_ref=flux_jy,
                    ref_freq_hz=1.4e9,
                    spectral_index=None,
                    catalog='NVSS',
                ))
            except Exception:
                continue
    except Exception:
        return out
    return out


def fetch_nvss_allsky_coarse() -> List[CachedSource]:
    Vizier.ROW_LIMIT = -1
    viz = Vizier(columns=['*'])
    tiles = [(-40, -10), (-10, 20), (20, 50), (50, 90)]
    out: List[CachedSource] = []
    for decmin, decmax in tiles:
        try:
            res = viz.query_constraints(catalog=NVSS_ID, DEJ2000=f">{decmin}&<{decmax}")
            if not res:
                continue
            tab = res[0]
            for row in tab:
                try:
                    ra = float(row['RAJ2000'])
                    dec = float(row['DEJ2000'])
                    name = str(row['NVSS']) if 'NVSS' in tab.colnames else f"NVSS_{ra:.5f}_{dec:.5f}"
                    flux_jy = float(row['S1.4']) / 1000.0 if 'S1.4' in tab.colnames else None
                    out.append(CachedSource(
                        name=name,
                        ra_deg=ra,
                        dec_deg=dec,
                        flux_jy_ref=flux_jy,
                        ref_freq_hz=1.4e9,
                        spectral_index=None,
                        catalog='NVSS',
                    ))
                except Exception:
                    continue
        except Exception:
            continue
    return out


def fetch_vlass_region(ra_deg: float, dec_deg: float, radius_deg: float) -> List[CachedSource]:
    # Placeholder implementation
    return []


def main():
    p = argparse.ArgumentParser(description='Refresh local calibrator catalogs (NVSS/VLASS) to CSV cache.')
    p.add_argument('--nvss', action='store_true', help='Refresh NVSS cache')
    p.add_argument('--vlass', action='store_true', help='Refresh VLASS cache')
    p.add_argument('--ra', type=float, help='Center RA deg (ICRS) for regional refresh')
    p.add_argument('--dec', type=float, help='Center Dec deg (ICRS) for regional refresh')
    p.add_argument('--radius', type=float, default=5.0, help='Radius deg for regional refresh')
    args = p.parse_args()

    cache = CalibratorCache()

    regional = args.ra is not None and args.dec is not None

    if args.nvss or (not args.nvss and not args.vlass):
        if regional:
            rows = fetch_nvss_region(args.ra, args.dec, args.radius)
        else:
            rows = fetch_nvss_allsky_coarse()
        cache.write_csv(NVSS_CSV, rows)
        print(f"Wrote {len(rows)} NVSS rows to {NVSS_CSV}")

    if args.vlass:
        rows = fetch_vlass_region(args.ra, args.dec, args.radius) if regional else []
        cache.write_csv(VLASS_CSV, rows)
        print(f"Wrote {len(rows)} VLASS rows to {VLASS_CSV}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
