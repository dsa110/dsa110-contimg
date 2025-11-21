#!/opt/miniforge/envs/casa6/bin/python
import argparse
import os
import sys
from typing import Optional

from dsa110_contimg.beam.vp_builder import build_vp_table


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description=("Build a CASA VP table from a DSA-110 H5 beam model"))
    p.add_argument("--h5", required=True, help="Path to DSA-110 H5 beam file")
    p.add_argument(
        "--out",
        required=True,
        help="Output VP table path (directory will be created if needed)",
    )
    p.add_argument(
        "--telescope",
        default=None,
        help="Optional telescope name to bind as default (e.g., DSA_110)",
    )
    p.add_argument(
        "--freq-hz",
        type=float,
        default=None,
        help="Preferred frequency (Hz) slice from H5 (default: mid-band)",
    )
    args = p.parse_args(argv)

    out_dir = os.path.dirname(args.out)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    try:
        vp = build_vp_table(
            args.h5,
            out_vp_table=args.out,
            telescope=args.telescope,
            prefer_freq_hz=args.freq_hz,
        )  # noqa: E501
    except Exception as e:
        print(f"ERROR: failed to build VP: {e}", file=sys.stderr)
        return 1

    print(f"VP written: {vp}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
