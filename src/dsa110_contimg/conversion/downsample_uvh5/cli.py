#!/opt/miniforge/envs/casa6/bin/python
"""
Unified CLI for downsampling UVH5 files.

Subcommands:
  - single: reference implementation
  - fast: optimized single-file path
  - batch: directory batch driver (parallel), uses fast path under the hood
"""

import argparse
import sys
from pathlib import Path

from .downsample_hdf5 import downsample_uvh5
from .downsample_hdf5_batch import downsample_uvh5_batch
from .downsample_hdf5_fast import downsample_uvh5_fast


def add_single_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("input", help="Input UVH5 file")
    p.add_argument("output", help="Output UVH5 file")
    p.add_argument("--time-factor", type=int, default=1)
    p.add_argument("--freq-factor", type=int, default=1)
    p.add_argument("--method", choices=["average", "weighted"], default="average")
    p.add_argument("--chunk-size", type=int, default=1000)


def add_fast_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("input", help="Input UVH5 file")
    p.add_argument("output", help="Output UVH5 file")
    p.add_argument("--time-factor", type=int, default=1)
    p.add_argument("--freq-factor", type=int, default=1)
    p.add_argument("--method", choices=["average", "weighted"], default="average")
    p.add_argument("--chunk-size", type=int, default=10000)


def add_batch_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("input_dir", help="Directory of input UVH5 files")
    p.add_argument("output_dir", help="Directory for downsampled outputs")
    p.add_argument("--time-factor", type=int, default=1)
    p.add_argument("--freq-factor", type=int, default=1)
    p.add_argument("--method", choices=["average", "weighted"], default="average")
    p.add_argument("--chunk-size", type=int, default=10000)
    p.add_argument("--max-workers", type=int, default=None)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(prog="downsample", description="UVH5 downsampling toolkit")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_single = sub.add_parser("single", help="Reference single-file downsample")
    add_single_args(p_single)
    p_single.set_defaults(
        func=lambda a: downsample_uvh5(
            a.input, a.output, a.time_factor, a.freq_factor, a.method, a.chunk_size
        )
    )

    p_fast = sub.add_parser("fast", help="Optimized single-file downsample")
    add_fast_args(p_fast)
    p_fast.set_defaults(
        func=lambda a: downsample_uvh5_fast(
            a.input, a.output, a.time_factor, a.freq_factor, a.method, a.chunk_size
        )
    )

    p_batch = sub.add_parser("batch", help="Parallel directory downsample (uses fast path)")
    add_batch_args(p_batch)
    p_batch.set_defaults(
        func=lambda a: downsample_uvh5_batch(
            a.input_dir,
            a.output_dir,
            a.time_factor,
            a.freq_factor,
            a.method,
            a.chunk_size,
            a.max_workers,
        )
    )

    args = parser.parse_args(argv)

    # Basic validations for single/fast
    if args.cmd in ("single", "fast"):
        if not Path(args.input).exists():
            parser.error(f"Input file not found: {args.input}")
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    else:
        # batch validations
        if not Path(args.input_dir).exists():
            parser.error(f"Input dir not found: {args.input_dir}")
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Validate factors
    if getattr(args, "time_factor", 1) < 1:
        parser.error("time-factor must be >= 1")
    if getattr(args, "freq_factor", 1) < 1:
        parser.error("freq-factor must be >= 1")

    try:
        args.func(args)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
