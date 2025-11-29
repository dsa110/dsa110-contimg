#!/opt/miniforge/envs/casa6/bin/python
"""
Build NVSS SQLite database for a declination strip based on HDF5 file declination.

Usage:
    python -m dsa110_contimg.catalog.build_nvss_strip \
        --hdf5 /path/to/file.hdf5 \
        --dec-range 6.0  # ±6 degrees around the declination
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dsa110_contimg.catalog.builders import build_nvss_strip_db
from dsa110_contimg.pointing.utils import load_pointing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build NVSS SQLite database for declination strip from HDF5 file"
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

    # Build declination range
    dec_range = (dec_center - args.dec_range, dec_center + args.dec_range)
    print("Building NVSS catalog for declination strip:")
    print(f"  Center: {dec_center:.6f}°")
    print(f"  Range: {dec_range[0]:.6f}° to {dec_range[1]:.6f}°")
    print(f"  Width: {2 * args.dec_range:.1f}°")

    # Build database
    try:
        output_path = build_nvss_strip_db(
            dec_center=dec_center,
            dec_range=dec_range,
            output_path=args.output,
            min_flux_mjy=args.min_flux_mjy,
        )
        print("\n:check_mark: Successfully built NVSS declination strip database")
        print(f"  Database: {output_path}")
        return 0

    except Exception as e:
        print(f"\n:ballot_x: Error building database: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
