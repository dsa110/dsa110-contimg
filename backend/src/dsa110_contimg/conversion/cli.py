"""DEPRECATED: Command-line interface for DSA-110 conversion.

This CLI is deprecated. Please use the ABSURD pipeline instead:
    - For batch conversion: Use pipeline scheduler with ConversionJob
    - For streaming: Use the AbsurdStreamingBridge

See docs/ARCHITECTURE.md for migration guide.
"""

import argparse
import warnings

# Flattened imports - use top-level module
from dsa110_contimg.conversion import convert_subband_groups_to_ms
from dsa110_contimg.conversion.streaming_converter import main as streaming_main


def start_streaming_conversion(input_dir, output_dir, queue_db, registry_db, scratch_dir):
    """Wrapper to start streaming conversion (deprecated)."""
    warnings.warn(
        "start_streaming_conversion is deprecated. Use AbsurdStreamingBridge instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Fall back to streaming module's main entry point
    import sys

    sys.argv = [
        "streaming",
        "--input-dir",
        input_dir,
        "--output-dir",
        output_dir,
        "--queue-db",
        queue_db,
        "--registry-db",
        registry_db,
    ]
    if scratch_dir:
        sys.argv.extend(["--scratch-dir", scratch_dir])
    streaming_main()


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
