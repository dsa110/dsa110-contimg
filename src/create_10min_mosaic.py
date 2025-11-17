#!/opt/miniforge/envs/casa6/bin/python
"""Create 12-minute mosaic with specified parameters.

Parameters:
- Calibrator: 0834+555
- Output: default (/stage/dsa110-contimg/mosaics/)
- Mosaic name: default (auto-generated)
- Method: pbweighted (default in orchestrator)
- Imaging: imsize=1024, robust=0, niter=1000
- Tile selection: default
- Validation: automatic
- Publishing: wait_for_published=False (stays in /stage/)

This script now supports:
- Interactive transit selection with quality metrics
- Time range override
- Quality-based filtering
- Batch processing
- Check for existing mosaics (requires --overwrite to overwrite)
- Enhanced preview mode
"""

import argparse
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from astropy.time import Time

from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

# Error log file location
ERROR_LOG = Path("/data/dsa110-contimg/src/mosaic_errors.log")
STATUS_FILE = Path("/data/dsa110-contimg/src/mosaic_status.txt")


def log_error(message, exception=None):
    """Log error to file with timestamp."""
    timestamp = datetime.now().isoformat()
    with open(ERROR_LOG, "a") as f:
        f.write(f"[{timestamp}] ERROR: {message}\n")
        if exception:
            f.write(f"Exception: {str(exception)}\n")
            f.write(f"Traceback:\n{traceback.format_exc()}\n")
        f.write("-" * 80 + "\n")
    print(f"ERROR: {message}", file=sys.stderr)
    if exception:
        print(traceback.format_exc(), file=sys.stderr)


def write_status(status, details=""):
    """Write status to file for monitoring."""
    timestamp = datetime.now().isoformat()
    with open(STATUS_FILE, "w") as f:
        f.write(f"Status: {status}\n")
        f.write(f"Timestamp: {timestamp}\n")
        if details:
            f.write(f"Details: {details}\n")


def check_transit_database(calibrator_name: str, products_db_path: Path) -> dict:
    """Check if transit times are stored in the database for the calibrator.

    Args:
        calibrator_name: Name of calibrator (e.g., "0834+555")
        products_db_path: Path to products database

    Returns:
        Dict with database status information
    """
    try:
        from dsa110_contimg.conversion.transit_precalc import \
          get_calibrator_transits

        products_db = ensure_products_db(products_db_path)
        stored_transits = get_calibrator_transits(
            products_db=products_db,
            calibrator_name=calibrator_name,
            max_days_back=60,
            only_with_data=True,
        )
        products_db.close()

        if stored_transits:
            return {
                "has_data": True,
                "count": len(stored_transits),
                "transits": stored_transits,
                "message": f"Found {len(stored_transits)} stored transit(s) with available data in database"
            }
        else:
            return {
                "has_data": False,
                "count": 0,
                "transits": [],
                "message": "No stored transit times found in database (will calculate on-demand)"
            }
    except Exception as e:
        return {
            "has_data": False,
            "count": 0,
            "transits": [],
            "message": f"Could not check database: {e} (will calculate on-demand)"
        }


def list_transits_interactive(
    orchestrator: MosaicOrchestrator,
    calibrator_name: str,
    min_pb_response: Optional[float] = None,
    min_ms_count: Optional[int] = None,
) -> Optional[int]:
    """List available transits and prompt user to select one.

    Returns:
        Selected transit index (0-based) or None if cancelled
    """
    print(f"\n📋 Listing available transits for {calibrator_name}...")
    transits = orchestrator.list_available_transits_with_quality(
        calibrator_name,
        max_days_back=60,
        min_pb_response=min_pb_response,
        min_ms_count=min_ms_count,
    )

    if not transits:
        print(f"✗ No transits found for {calibrator_name}")
        return None

    print(f"\n✓ Found {len(transits)} transit(s):\n")
    print(f"{'Index':<8} {'Transit Time':<25} {'PB Resp':<10} {'MS Count':<10} {'Days Ago':<10}")
    print("-" * 75)

    for i, transit in enumerate(transits):
        transit_time = transit.get("transit_time")
        if isinstance(transit_time, Time):
            transit_iso = transit_time.isot
        else:
            transit_iso = transit.get("transit_iso", "N/A")

        pb_response = transit.get("pb_response", 0.0)
        ms_count = transit.get("ms_count", 0)
        days_ago = transit.get("days_ago", 0.0)

        print(
            f"{i:<8} {transit_iso:<25} {pb_response:<10.3f} {ms_count:<10} {days_ago:<10.1f}"
        )

    print("\nSelect a transit by index (0-based), or 'q' to quit:")
    while True:
        try:
            choice = input("> ").strip()
            if choice.lower() == "q":
                return None
            idx = int(choice)
            if 0 <= idx < len(transits):
                return idx
            else:
                print(f"Invalid index. Please enter 0-{len(transits)-1} or 'q' to quit.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")
        except KeyboardInterrupt:
            return None


def main():
    """Main execution with error handling."""
    parser = argparse.ArgumentParser(
        description="Create 12-minute mosaic centered on calibrator 0834+555",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: use earliest transit
  python create_10min_mosaic.py

  # List transits and select interactively
  python create_10min_mosaic.py --list-transits

  # Select transit by index
  python create_10min_mosaic.py --transit-index 2

  # Use specific transit time
  python create_10min_mosaic.py --transit-time "2025-11-12T10:00:00"

  # Use explicit time range
  python create_10min_mosaic.py --start-time "2025-11-12T10:00:00" --end-time "2025-11-12T10:12:00"

  # Filter by quality
  python create_10min_mosaic.py --min-pb-response 0.8 --min-ms-count 3

  # Preview mode (dry run)
  python create_10min_mosaic.py --preview

  # Batch processing
  python create_10min_mosaic.py --all-transits
  python create_10min_mosaic.py --transit-range 0:5

  # Overwrite existing mosaic
  python create_10min_mosaic.py --overwrite
        """,
    )

    # Transit selection options
    transit_group = parser.add_mutually_exclusive_group()
    transit_group.add_argument(
        "--transit-time",
        type=str,
        default=None,
        help="Transit time in ISO format (e.g., '2025-11-12T10:00:00'). "
             "If not specified, uses earliest available transit (default).",
    )
    transit_group.add_argument(
        "--transit-index",
        type=int,
        default=None,
        help="Select transit by index (0-based) from list. Use --list-transits to see available transits.",
    )
    transit_group.add_argument(
        "--list-transits",
        action="store_true",
        help="List available transits with quality metrics and prompt for selection.",
    )

    # Time range override
    parser.add_argument(
        "--start-time",
        type=str,
        default=None,
        help="Explicit start time in ISO format (overrides transit-centered calculation). "
             "Must be used with --end-time.",
    )
    parser.add_argument(
        "--end-time",
        type=str,
        default=None,
        help="Explicit end time in ISO format (overrides transit-centered calculation). "
             "Must be used with --start-time.",
    )

    # Quality filtering
    parser.add_argument(
        "--min-pb-response",
        type=float,
        default=None,
        help="Minimum primary beam response (0.0-1.0). Note: For drift scans at constant Dec, "
             "PB response may be constant for a given calibrator.",
    )
    parser.add_argument(
        "--min-ms-count",
        type=int,
        default=None,
        help="Minimum number of MS files required in window.",
    )

    # Batch processing
    batch_group = parser.add_mutually_exclusive_group()
    batch_group.add_argument(
        "--all-transits",
        action="store_true",
        help="Create mosaics for all available transits (batch mode).",
    )
    batch_group.add_argument(
        "--transit-range",
        type=str,
        default=None,
        help="Create mosaics for transit range (e.g., '0:5' for first 5 transits).",
    )

    # Other options
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview mode: validate and plan without creating mosaic (same as --dry-run).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: validate and plan without creating mosaic.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing mosaics with same parameters.",
    )
    parser.add_argument(
        "--timespan-minutes",
        type=int,
        default=12,
        help="Mosaic timespan in minutes (default: 12).",
    )

    args = parser.parse_args()

    # Validate time range arguments
    if (args.start_time is None) != (args.end_time is None):
        parser.error("--start-time and --end-time must be used together")

    try:
        write_status("RUNNING", "Starting mosaic creation")

        calibrator_name = "0834+555"
        products_db_path = Path("state/products.sqlite3")

        # Set imaging parameters (applies to individual tiles)
        os.environ["IMG_IMSIZE"] = "1024"
        os.environ["IMG_ROBUST"] = "0.0"
        os.environ["IMG_NITER"] = "1000"

        # Initialize orchestrator
        write_status("RUNNING", "Initializing orchestrator")
        orchestrator = MosaicOrchestrator(products_db_path=products_db_path)

        # Handle batch processing
        if args.all_transits or args.transit_range:
            transit_indices = None
            if args.transit_range:
                try:
                    start_idx, end_idx = map(int, args.transit_range.split(":"))
                    transit_indices = list(range(start_idx, end_idx))
                except ValueError:
                    parser.error(
                        f"Invalid transit-range format: {args.transit_range}. "
                        "Expected format: 'start:end' (e.g., '0:5')"
                    )

            print(f"\n📊 Batch processing mosaics for {calibrator_name}")
            results = orchestrator.create_mosaics_batch(
                calibrator_name=calibrator_name,
                transit_indices=transit_indices,
                all_transits=args.all_transits,
                timespan_minutes=args.timespan_minutes,
                min_pb_response=args.min_pb_response,
                min_ms_count=args.min_ms_count,
                wait_for_published=False,
                overwrite=args.overwrite,
            )

            success_count = sum(1 for r in results if r["status"] == "success")
            print(f"\n✓ Batch processing complete: {success_count}/{len(results)} successful")
            write_status("SUCCESS", f"Batch processing: {success_count}/{len(results)} successful")
            return 0 if success_count > 0 else 1

        # Handle list-transits mode
        if args.list_transits:
            selected_idx = list_transits_interactive(
                orchestrator,
                calibrator_name,
                min_pb_response=args.min_pb_response,
                min_ms_count=args.min_ms_count,
            )
            if selected_idx is None:
                print("Cancelled by user.")
                return 0
            args.transit_index = selected_idx

        # Determine transit_time
        transit_time = None
        if args.transit_time:
            try:
                transit_time = Time(args.transit_time, format="isot", scale="utc")
                print(f"✓ Using user-specified transit time: {transit_time.isot}")
            except Exception as e:
                print(f"✗ Error parsing transit-time: {e}")
                return 1
        elif args.transit_index is not None:
            # Get transit by index
            transits = orchestrator.list_available_transits_with_quality(
                calibrator_name,
                max_days_back=60,
                min_pb_response=args.min_pb_response,
                min_ms_count=args.min_ms_count,
            )
            if args.transit_index < 0 or args.transit_index >= len(transits):
                print(f"✗ Transit index {args.transit_index} out of range (0-{len(transits)-1})")
                return 1
            transit = transits[args.transit_index]
            transit_time = transit.get("transit_time")
            if isinstance(transit_time, Time):
                print(f"✓ Using transit index {args.transit_index}: {transit_time.isot}")
            else:
                transit_time = Time(transit.get("transit_iso"))
                print(f"✓ Using transit index {args.transit_index}: {transit_time.isot}")

        # Parse time range override
        start_time = None
        end_time = None
        if args.start_time and args.end_time:
            try:
                start_time = Time(args.start_time, format="isot", scale="utc")
                end_time = Time(args.end_time, format="isot", scale="utc")
                print(f"✓ Using explicit time range: {start_time.isot} to {end_time.isot}")
            except Exception as e:
                print(f"✗ Error parsing time range: {e}")
                return 1

        # Determine dry_run mode
        dry_run = args.preview or args.dry_run
        if dry_run:
            print("\n🔍 PREVIEW MODE: Validating plan without creating mosaic\n")

        # Create mosaic
        write_status("RUNNING", "Creating mosaic")
        print(f"\n📊 Creating {args.timespan_minutes}-minute mosaic centered on {calibrator_name}")

        mosaic_path = orchestrator.create_mosaic_centered_on_calibrator(
            calibrator_name=calibrator_name,
            timespan_minutes=args.timespan_minutes,
            wait_for_published=False,
            dry_run=dry_run,
            transit_time=transit_time,
            start_time=start_time,
            end_time=end_time,
            overwrite=args.overwrite,
        )

        if mosaic_path:
            if mosaic_path == "DRY_RUN":
                success_msg = "Dry run completed successfully - mosaic plan validated"
                print(f"✓ {success_msg}")
                print(f"  Run without --preview/--dry-run to create the mosaic")
                write_status("SUCCESS", success_msg)
                return 0
            else:
                success_msg = f"Mosaic created successfully at: {mosaic_path}"
                print(f"✓ {success_msg}")
                print(f"  Location: /stage/dsa110-contimg/mosaics/")
                print(f"  Method: pbweighted (default)")
                write_status("SUCCESS", success_msg)
                return 0
        else:
            error_msg = "Failed to create mosaic (returned None)"
            log_error(error_msg)
            write_status("FAILED", error_msg)
            return 1

    except KeyboardInterrupt:
        error_msg = "Script interrupted by user"
        log_error(error_msg)
        write_status("INTERRUPTED", error_msg)
        return 130

    except Exception as e:
        error_msg = f"Unexpected error during mosaic creation: {str(e)}"
        log_error(error_msg, e)
        write_status("FAILED", error_msg)
        return 1


if __name__ == "__main__":
    sys.exit(main())
