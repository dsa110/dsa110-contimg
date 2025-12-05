"""DEPRECATED: Command-line interface for DSA-110 conversion.

This CLI is deprecated. Please use:
    - For batch conversion: dsa110_contimg.conversion.hdf5_orchestrator.convert_subband_groups_to_ms()
    - For real-time ingestion: ABSURD pipeline (backend/src/dsa110_contimg/absurd/ingestion.py)

See docs/NEWCOMER_GUIDE.md for current usage patterns.
"""

import argparse
import warnings

# Flattened imports - use top-level module
from dsa110_contimg.conversion import convert_subband_groups_to_ms


def start_streaming_conversion(input_dir, output_dir, queue_db, registry_db, scratch_dir):
    """Wrapper to start streaming conversion (deprecated and non-functional)."""
    raise NotImplementedError(
        "start_streaming_conversion has been removed. "
        "Use ABSURD ingestion instead: dsa110_contimg.absurd.ingestion"
    )


def main():
    """Deprecated CLI entry point.

    .. deprecated::
        Use ABSURD pipelines instead. This CLI will be removed in a future version.
    """
    warnings.warn(
        "The conversion CLI is deprecated. Use ABSURD pipelines for conversion tasks. "
        "See docs/ARCHITECTURE.md for the recommended workflow.",
        DeprecationWarning,
        stacklevel=2,
    )

    parser = argparse.ArgumentParser(
        description="DEPRECATED: Command-line interface for DSA-110 conversion. "
        "Use ABSURD pipelines instead."
    )

    subparsers = parser.add_subparsers(dest="command")

    # Subparser for batch conversion
    batch_parser = subparsers.add_parser(
        "batch", help="(DEPRECATED) Convert subband groups to Measurement Sets"
    )
    batch_parser.add_argument("input_dir", type=str, help="Directory containing input HDF5 files")
    batch_parser.add_argument(
        "output_dir", type=str, help="Directory to save output Measurement Sets"
    )
    batch_parser.add_argument("start_time", type=str, help="Start time for conversion (ISO format)")
    batch_parser.add_argument("end_time", type=str, help="End time for conversion (ISO format)")

    # Subparser for streaming conversion
    stream_parser = subparsers.add_parser(
        "stream", help="(DEPRECATED) Start streaming conversion process"
    )
    stream_parser.add_argument(
        "--input-dir", type=str, required=True, help="Directory for incoming HDF5 files"
    )
    stream_parser.add_argument(
        "--output-dir", type=str, required=True, help="Directory for output Measurement Sets"
    )
    stream_parser.add_argument(
        "--queue-db", type=str, required=True, help="SQLite database for queue management"
    )
    stream_parser.add_argument(
        "--registry-db", type=str, required=True, help="SQLite database for calibration registry"
    )
    stream_parser.add_argument("--scratch-dir", type=str, help="Temporary directory for processing")

    args = parser.parse_args()

    if args.command == "batch":
        convert_subband_groups_to_ms(
            args.input_dir, args.output_dir, args.start_time, args.end_time
        )
    elif args.command == "stream":
        start_streaming_conversion(
            args.input_dir, args.output_dir, args.queue_db, args.registry_db, args.scratch_dir
        )


if __name__ == "__main__":
    main()
