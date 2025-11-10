"""Apply calibration subcommand handler."""

import argparse
import logging

from .applycal import apply_to_target

logger = logging.getLogger(__name__)


def add_apply_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add 'apply' subcommand parser."""
    parser = subparsers.add_parser("apply", help="Apply calibration to target MS")
    parser.add_argument("--ms", required=True)
    parser.add_argument("--field", required=True)
    parser.add_argument(
        "--tables",
        nargs="+",
        required=True,
        help="Calibration tables in order",
    )
    return parser


def handle_apply(args: argparse.Namespace) -> int:
    """Handle 'apply' subcommand."""
    apply_to_target(args.ms, args.field, args.tables)
    print("Applied calibration to target")
    return 0
