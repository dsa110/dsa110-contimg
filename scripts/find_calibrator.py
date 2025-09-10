#!/usr/bin/env python3
import argparse
from core.calibration.calibrator_finder import CalibratorFinder


def main():
    p = argparse.ArgumentParser(description='Find calibrators near a pointing (NVSS by default, supports FIRST, VLASS, TGSS).')
    p.add_argument('--ra', type=float, required=True, help='Pointing RA in deg (ICRS)')
    p.add_argument('--dec', type=float, required=True, help='Pointing Dec in deg (ICRS)')
    p.add_argument('--radius', type=float, default=3.0, help='Search radius in deg')
    p.add_argument('--min-flux', type=float, default=0.2, help='Minimum flux in Jy at 1.4 GHz')
    p.add_argument('--catalog', type=str, default=None, help='Single catalog ID (VizieR id or alias: nvss, first, vlass, tgss)')
    p.add_argument('--catalogs', type=str, nargs='*', default=['nvss','first','vlass','tgss'], help='Multiple catalogs to query and merge')
    p.add_argument('--cache-only', action='store_true', help='Do not query online; use local cache only')
    p.add_argument('--online', action='store_true', help='Force online query even if cache has results')
    p.add_argument('-n', '--top', type=int, default=10, help='Show top N results')
    args = p.parse_args()

    finder = CalibratorFinder(
        catalog=args.catalog or None,
        catalogs=args.catalogs,
        use_cache=(not args.online),
        allow_online_fallback=(not args.cache_only)
    )
    cands = finder.find_nearby(args.ra, args.dec, radius_deg=args.radius, min_flux_jy=args.min_flux)
    if not cands:
        print('No calibrators found.')
        return 1
    print('name,ra_deg,dec_deg,flux_jy_ref_1p4GHz,sep_deg,provenance')
    for c in cands[:args.top]:
        flux_str = f"{c.flux_jy_ref:.3f}" if c.flux_jy_ref is not None else ""
        print(f"{c.name},{c.ra_deg:.6f},{c.dec_deg:.6f},{flux_str},{c.separation_deg:.3f},{c.provenance}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
