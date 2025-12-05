"""
Command-line interface for the unified execution module.

This CLI provides access to the execution infrastructure for UVH5 to MS
conversion with support for both in-process and subprocess execution modes.

Part of Issue #11: Subprocess vs In-Process Execution Consistency.

Example usage:
    # Convert with auto-selected execution mode (default)
    python -m dsa110_contimg.execution.cli convert \\
        --input-dir /data/incoming \\
        --output-dir /stage/ms \\
        --start-time "2025-06-01T00:00:00" \\
        --end-time "2025-06-01T01:00:00"

    # Force subprocess execution for isolation
    python -m dsa110_contimg.execution.cli convert \\
        --execution-mode subprocess \\
        --input-dir /data/incoming \\
        --output-dir /stage/ms \\
        --start-time "2025-06-01T00:00:00" \\
        --end-time "2025-06-01T01:00:00"

    # With resource limits
    python -m dsa110_contimg.execution.cli convert \\
        --execution-mode inprocess \\
        --memory-mb 8192 \\
        --omp-threads 4 \\
        --input-dir /data/incoming \\
        --output-dir /stage/ms \\
        --start-time "2025-06-01T00:00:00" \\
        --end-time "2025-06-01T01:00:00"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from dsa110_contimg.execution import (
    ExecutionTask,
    get_executor,
)
from dsa110_contimg.execution.resources import get_recommended_limits
from dsa110_contimg.execution.task import ResourceLimits

logger = logging.getLogger(__name__)


def setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbosity: 0=WARNING, 1=INFO, 2+=DEBUG
    """
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="dsa110_contimg.execution.cli",
        description="Unified execution interface for UVH5 to MS conversion.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion with auto mode
  python -m dsa110_contimg.execution.cli convert \\
      --input-dir /data/incoming --output-dir /stage/ms \\
      --start-time "2025-06-01T00:00:00" --end-time "2025-06-01T01:00:00"

  # Subprocess execution for isolation
  python -m dsa110_contimg.execution.cli convert \\
      --execution-mode subprocess --timeout 3600 \\
      --input-dir /data/incoming --output-dir /stage/ms \\
      --start-time "2025-06-01T00:00:00" --end-time "2025-06-01T01:00:00"

  # With resource limits
  python -m dsa110_contimg.execution.cli convert \\
      --memory-mb 8192 --omp-threads 4 \\
      --input-dir /data/incoming --output-dir /stage/ms \\
      --start-time "2025-06-01T00:00:00" --end-time "2025-06-01T01:00:00"
""",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (can be repeated: -v for INFO, -vv for DEBUG)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Convert command
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert UVH5 subband groups to Measurement Sets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required arguments
    convert_parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing HDF5 subband files",
    )
    convert_parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for output Measurement Sets",
    )
    convert_parser.add_argument(
        "--start-time",
        type=str,
        required=True,
        help="Start time for conversion window (ISO format)",
    )
    convert_parser.add_argument(
        "--end-time",
        type=str,
        required=True,
        help="End time for conversion window (ISO format)",
    )

    # Execution mode
    convert_parser.add_argument(
        "--execution-mode",
        type=str,
        choices=["auto", "inprocess", "subprocess"],
        default="auto",
        help="Execution mode: 'auto' (default), 'inprocess', or 'subprocess'",
    )

    # Optional arguments
    convert_parser.add_argument(
        "--scratch-dir",
        type=Path,
        default=None,
        help="Scratch directory for temporary files (default: output-dir/scratch)",
    )
    convert_parser.add_argument(
        "--writer",
        type=str,
        choices=["auto", "parallel-subband", "direct-subband"],
        default="auto",
        help="MS writer type (default: auto)",
    )
    convert_parser.add_argument(
        "--group-id",
        type=str,
        default=None,
        help="Specific group ID to convert (optional)",
    )

    # Resource limits
    resource_group = convert_parser.add_argument_group("resource limits")
    resource_group.add_argument(
        "--memory-mb",
        type=int,
        default=None,
        help="Memory limit in MB (default: auto-detect)",
    )
    resource_group.add_argument(
        "--omp-threads",
        type=int,
        default=None,
        help="Number of OpenMP threads (default: auto-detect)",
    )
    resource_group.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum parallel I/O workers (default: 4)",
    )
    resource_group.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout in seconds for subprocess mode",
    )

    # Output options
    output_group = convert_parser.add_argument_group("output options")
    output_group.add_argument(
        "--result-file",
        type=Path,
        default=None,
        help="Write JSON result to file (for subprocess integration)",
    )
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON to stdout",
    )
    output_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and show what would be done without executing",
    )

    return parser


def cmd_convert(args: argparse.Namespace) -> int:
    """Execute the convert command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Determine scratch directory
    scratch_dir = args.scratch_dir
    if scratch_dir is None:
        scratch_dir = args.output_dir / "scratch"

    # Build resource limits
    recommended = get_recommended_limits()

    limits = ResourceLimits(
        memory_mb=args.memory_mb or recommended["memory_mb"],
        omp_threads=args.omp_threads or recommended["omp_threads"],
        max_workers=args.max_workers or recommended["max_workers"],
        timeout_seconds=args.timeout,
    )

    # Determine group ID
    group_id = args.group_id or f"cli-{args.start_time}"

    # Create task
    task = ExecutionTask(
        group_id=group_id,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        scratch_dir=scratch_dir,
        start_time=args.start_time,
        end_time=args.end_time,
        writer=args.writer,
        resource_limits=limits,
    )

    # Dry run - just validate and show config
    if args.dry_run:
        logger.info("Dry run - validating configuration...")

        try:
            task.validate()
            logger.info("✓ Task validation passed")
        except ValueError as e:
            logger.error(f"✗ Task validation failed: {e}")
            return 1

        print("\nExecution Configuration:")
        print(f"  Mode: {args.execution_mode}")
        print(f"  Input: {args.input_dir}")
        print(f"  Output: {args.output_dir}")
        print(f"  Scratch: {scratch_dir}")
        print(f"  Time window: {args.start_time} to {args.end_time}")
        print(f"  Writer: {args.writer}")
        print("\nResource Limits:")
        print(f"  Memory: {limits.memory_mb} MB")
        print(f"  OMP threads: {limits.omp_threads}")
        print(f"  Max workers: {limits.max_workers}")
        if limits.timeout_seconds:
            print(f"  Timeout: {limits.timeout_seconds}s")

        return 0

    # Get executor
    executor = get_executor(
        mode=args.execution_mode,
        timeout_seconds=args.timeout,
    )

    logger.info(f"Starting conversion with {args.execution_mode} executor...")
    logger.info(f"Input: {args.input_dir}")
    logger.info(f"Output: {args.output_dir}")
    logger.info(f"Time window: {args.start_time} to {args.end_time}")

    # Execute
    result = executor.run(task)

    # Output result
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    elif args.result_file:
        with open(args.result_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        logger.info(f"Result written to {args.result_file}")

    # Log result
    if result.success:
        logger.info("✓ Conversion completed successfully")
        if result.ms_path:
            logger.info(f"  Output: {result.ms_path}")
        if result.metrics:
            metrics = result.metrics
            if metrics.total_time_s:
                logger.info(f"  Total time: {metrics.total_time_s:.1f}s")
            if metrics.files_processed:
                logger.info(f"  Files processed: {metrics.files_processed}")
        return 0
    else:
        logger.error(f"✗ Conversion failed: {result.error_code}")
        if result.error_message:
            logger.error(f"  Error: {result.error_message}")
        return result.return_code or 1


def main(argv: Optional[list] = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments (default: sys.argv[1:])

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    setup_logging(args.verbose)

    if args.command == "convert":
        return cmd_convert(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
