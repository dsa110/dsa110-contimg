#!/usr/bin/env python3
"""
CLI utilities for calibrator catalog queries (transit times and in-beam matches).

Examples:
  # Previous 3 transits for a calibrator by name
  python -m dsa110_contimg.calibration.catalog_cli transit \
      --catalog references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv \
      --name 0834+555 --n 3

  # In-beam matches for a drift scan at pt_dec and time
  python -m dsa110_contimg.calibration.catalog_cli inbeam \
      --catalog references/dsa110-contimg-main-legacy/data/catalogs/vla_calibrators_parsed.csv \
      --pt-dec 55.0 --time "2025-10-07 15:22:00" --radius 1.0 --top 5
"""

import argparse
from astropy.time import Time
import astropy.units as u

from .catalogs import (
    read_vla_parsed_catalog_csv,
    get_calibrator_radec,
    calibrator_match,
    load_vla_catalog,
    resolve_vla_catalog_path,
)
from .schedule import previous_transits


def cmd_transit(args: argparse.Namespace) -> int:
    # Use centralized catalog resolution if --catalog not provided
    if args.catalog:
        df = read_vla_parsed_catalog_csv(args.catalog)
    else:
        df = load_vla_catalog()
    ra_deg, dec_deg = get_calibrator_radec(df, args.name)
    start = Time.now() if args.start is None else Time(args.start)
    times = previous_transits(ra_deg=ra_deg, start_time=start, n=args.n)
    print(f"Now: {Time.now().isot}")
    for i, t in enumerate(times, 1):
        print(f"Prev {i}: {t.isot}")
    return 0


def cmd_inbeam(args: argparse.Namespace) -> int:
    # Use centralized catalog resolution if --catalog not provided
    if args.catalog:
        df = read_vla_parsed_catalog_csv(args.catalog)
    else:
        df = load_vla_catalog()
    t = Time(args.time)
    pt_dec = float(args.pt_dec) * u.deg
    matches = calibrator_match(df, pt_dec, t.mjd, radius_deg=float(args.radius), top_n=int(args.top))
    if not matches:
        print("No calibrators in beam")
        return 1
    for m in matches:
        print(f"{m['name']} sep={m['sep_deg']:.3f} deg ra={m['ra_deg']:.6f} dec={m['dec_deg']:.6f} wflux={m['weighted_flux']:.3f}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Calibrator catalog utilities")
    sub = p.add_subparsers(dest='cmd', required=True)

    sp = sub.add_parser('transit', help='Previous N transits for a calibrator by name')
    sp.add_argument('--catalog', default=None, help='Catalog path (optional, uses automatic resolution if not provided)')
    sp.add_argument('--name', required=True)
    sp.add_argument('--n', type=int, default=3)
    sp.add_argument('--start', help='UTC start time (default: now)')
    sp.set_defaults(func=cmd_transit)

    sp = sub.add_parser('inbeam', help='List in-beam calibrator matches for a drift strip')
    sp.add_argument('--catalog', default=None, help='Catalog path (optional, uses automatic resolution if not provided)')
    sp.add_argument('--pt-dec', required=True, help='Pointing declination (deg)')
    sp.add_argument('--time', required=True, help='UTC time of group midpoint')
    sp.add_argument('--radius', default='1.0', help='Search radius (deg)')
    sp.add_argument('--top', default='3', help='Top N matches to show')
    sp.set_defaults(func=cmd_inbeam)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())

