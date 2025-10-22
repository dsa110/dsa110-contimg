"""Unified command-line interface for UVH5 to MS conversion."""

import argparse
import logging
import sys

from . import uvh5_to_ms
from .strategies import hdf5_orchestrator


def main(argv: list = None) -> int:
    """Main function for the unified conversion CLI."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="DSA-110 Continuum Imaging Conversion CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Subcommand to run"
    )

    # Subparser for the 'single' command
    single_parser = subparsers.add_parser(
        "single",
        help="Convert a single UVH5 file or a directory of loose files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    uvh5_to_ms.add_args(single_parser)
    single_parser.set_defaults(func=uvh5_to_ms.main)

    # Subparser for the 'groups' command
    groups_parser = subparsers.add_parser(
        "groups",
        help="Discover and convert complete subband groups in a time window.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    hdf5_orchestrator.add_args(groups_parser)
    groups_parser.set_defaults(func=hdf5_orchestrator.main)

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
