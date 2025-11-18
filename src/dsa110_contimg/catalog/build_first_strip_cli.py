#!/opt/miniforge/envs/casa6/bin/python
"""
Build FIRST SQLite database for a declination strip based on HDF5 file declination.

Similar to build_nvss_strip_cli.py but for FIRST catalog.
"""

import argparse
from pathlib import Path

from dsa110_contimg.catalog.builders import build_first_strip_db
from dsa110_contimg.pointing.utils import load_pointing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build FIRST SQLite database for declination strip from HDF5 file"
    )
    ap.add_argument("--hdf5", required=True, help="Path to HDF5 file to read declination from")
    ap.add_argument(
        "--dec-range",
        type=float,
        default=6.0,
        help="Declination range (±degrees around center, default: 6.0)",
    )
    ap.add_argument("--output", help="Output SQLite database path (auto-generated if not provided)")
    ap.add_argument("--min-flux-mjy", type=float, help="Minimum flux threshold in mJy (optional)")
    ap.add_argument(
        "--first-catalog-path",
        help="Path to FIRST catalog file (CSV/FITS). If not provided, attempts to auto-download/cache.",
    )
    ap.add_argument(
        "--cache-dir",
        default=".cache/catalogs",
        help="Directory for caching catalog files (default: .cache/catalogs)",
    )

    args = ap.parse_args(argv)

    # Read declination from HDF5
    hdf5_path = Path(args.hdf5)
    if not hdf5_path.exists():
        print(f"Error: HDF5 file not found: {hdf5_path}")
        return 1

    try:
        info = load_pointing(str(hdf5_path))
        if "dec_deg" not in info:
            print(f"Error: Could not read declination from {hdf5_path}")
            print(f"Available keys: {list(info.keys())}")
            return 1

        dec_center = info["dec_deg"]
        print(f"Declination from {hdf5_path.name}: {dec_center:.6f} degrees")

    except Exception as e:
        print(f"Error reading HDF5 file: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Calculate declination range
    dec_min = dec_center - args.dec_range
    dec_max = dec_center + args.dec_range
    dec_range = (dec_min, dec_max)

    print("Building FIRST SQLite database for declination strip:")
    print(f"  Center: {dec_center:.6f} degrees")
    print(f"  Range: {dec_min:.6f} to {dec_max:.6f} degrees (±{args.dec_range}°)")

    try:
        output_path = build_first_strip_db(
            dec_center=dec_center,
            dec_range=dec_range,
            output_path=args.output,
            first_catalog_path=args.first_catalog_path,
            min_flux_mjy=args.min_flux_mjy,
            cache_dir=args.cache_dir,
        )

        print(f"\n✓ FIRST SQLite database created: {output_path}")
        return 0

    except Exception as e:
        print(f"\n✗ Error building FIRST database: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
