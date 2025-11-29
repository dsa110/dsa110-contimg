#!/opt/miniforge/envs/casa6/bin/python
"""Find the earliest visibility data stored in the pipeline.

This script queries multiple data sources to determine the earliest
observation time with visibility data available.
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from astropy.time import Time

# Determine project root (needed for default paths even if package is installed)
repo_root = Path(__file__).parent.parent

# Try importing directly (works if package is installed)
try:
    from dsa110_contimg.api.data_access import fetch_observation_timeline
    from dsa110_contimg.database.products import ensure_products_db
except ImportError:
    # Fallback: add project root to path for development mode
    src_path = repo_root / "src"
    if src_path.exists():
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        from dsa110_contimg.api.data_access import fetch_observation_timeline
        from dsa110_contimg.database.products import ensure_products_db
    else:
        sys.stderr.write(
            f"ERROR: Cannot find project source directory: {src_path}\n"
            f"Please install the package with 'pip install -e .' or run from project root.\n"
        )
        sys.exit(1)


def query_earliest_ms(products_db: Path) -> dict | None:
    """Query products database for earliest MS file."""
    if not products_db.exists():
        return None

    conn = ensure_products_db(products_db)
    cursor = conn.cursor()

    # Query for earliest MS file by mid_mjd
    row = cursor.execute(
        """
        SELECT path, start_mjd, end_mjd, mid_mjd, processed_at, status, stage
        FROM ms_index
        WHERE mid_mjd IS NOT NULL
        ORDER BY mid_mjd ASC
        LIMIT 1
        """
    ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "path": row[0],
        "start_mjd": row[1],
        "end_mjd": row[2],
        "mid_mjd": row[3],
        "processed_at": row[4],
        "status": row[5],
        "stage": row[6],
    }


def query_earliest_ingest(ingest_db: Path) -> dict | None:
    """Query ingest queue for earliest observation group."""
    if not ingest_db.exists():
        return None

    conn = sqlite3.connect(str(ingest_db))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query for earliest group by received_at
    row = cursor.execute(
        """
        SELECT group_id, received_at, last_update, state, expected_subbands
        FROM ingest_queue
        WHERE received_at IS NOT NULL
        ORDER BY received_at ASC
        LIMIT 1
        """
    ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "group_id": row[0],
        "received_at": row[1],
        "last_update": row[2],
        "state": row[3],
        "expected_subbands": row[4],
    }


def find_earliest_hdf5(data_dir: Path) -> dict | None:
    """Scan HDF5 files in data directory for earliest timestamp."""
    timeline = fetch_observation_timeline(data_dir)

    if not timeline.earliest_time:
        return None

    return {
        "earliest_time": timeline.earliest_time,
        "latest_time": timeline.latest_time,
        "total_files": timeline.total_files,
        "unique_timestamps": timeline.unique_timestamps,
        "segments": len(timeline.segments),
    }


def format_mjd_to_datetime(mjd: float) -> str:
    """Convert MJD to ISO datetime string."""
    t = Time(mjd, format="mjd")
    return t.isot


def format_unix_to_datetime(unix_timestamp: float) -> str:
    """Convert Unix timestamp to ISO datetime string."""
    dt = datetime.fromtimestamp(unix_timestamp)
    return dt.isoformat()


def main():
    parser = argparse.ArgumentParser(description="Find earliest visibility data in the pipeline")
    parser.add_argument(
        "--products-db",
        type=Path,
        default=repo_root / "state" / "products.sqlite3",
        help="Path to products database",
    )
    parser.add_argument(
        "--ingest-db",
        type=Path,
        default=repo_root / "state" / "ingest.sqlite3",
        help="Path to ingest queue database",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("/data/incoming"),
        help="Directory containing HDF5 files",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Finding Earliest Visibility Data")
    print("=" * 70)
    print()

    # Query MS index (processed/converted data)
    print("1. Querying MS Index (processed/converted data)...")
    ms_data = query_earliest_ms(args.products_db)
    if ms_data:
        print(f"   :check: Earliest MS file found:")
        print(f"     Path: {ms_data['path']}")
        print(f"     Mid MJD: {ms_data['mid_mjd']:.6f}")
        print(f"     Mid Time: {format_mjd_to_datetime(ms_data['mid_mjd'])}")
        print(f"     Start MJD: {ms_data['start_mjd']:.6f}")
        print(f"     Start Time: {format_mjd_to_datetime(ms_data['start_mjd'])}")
        print(f"     Status: {ms_data['status']}")
        print(f"     Stage: {ms_data['stage']}")
    else:
        print("   :cross: No MS files found in products database")
    print()

    # Query ingest queue (raw observation groups)
    print("2. Querying Ingest Queue (raw observation groups)...")
    ingest_data = query_earliest_ingest(args.ingest_db)
    if ingest_data:
        print(f"   :check: Earliest observation group found:")
        print(f"     Group ID: {ingest_data['group_id']}")
        print(f"     Received At: {format_unix_to_datetime(ingest_data['received_at'])}")
        print(f"     State: {ingest_data['state']}")
        print(f"     Expected Subbands: {ingest_data['expected_subbands']}")

        # Parse group_id as timestamp if possible
        try:
            group_time = datetime.fromisoformat(ingest_data["group_id"])
            print(f"     Group Time: {group_time.isoformat()}")
        except ValueError:
            pass
    else:
        print("   :cross: No observation groups found in ingest queue")
    print()

    # Scan HDF5 files (raw visibility data)
    print("3. Scanning HDF5 Files (raw visibility data)...")
    hdf5_data = find_earliest_hdf5(args.data_dir)
    if hdf5_data:
        print(f"   :check: Earliest HDF5 file found:")
        print(f"     Earliest Time: {hdf5_data['earliest_time'].isoformat()}")
        print(f"     Latest Time: {hdf5_data['latest_time'].isoformat()}")
        print(f"     Total Files: {hdf5_data['total_files']}")
        print(f"     Unique Timestamps: {hdf5_data['unique_timestamps']}")
        print(f"     Timeline Segments: {hdf5_data['segments']}")
    else:
        print(f"   :cross: No HDF5 files found in {args.data_dir}")
    print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    earliest_times = []

    if ms_data:
        earliest_times.append(("MS Index", format_mjd_to_datetime(ms_data["start_mjd"])))

    if ingest_data:
        try:
            group_time = datetime.fromisoformat(ingest_data["group_id"])
            earliest_times.append(("Ingest Queue", group_time.isoformat()))
        except ValueError:
            earliest_times.append(
                ("Ingest Queue", format_unix_to_datetime(ingest_data["received_at"]))
            )

    if hdf5_data:
        earliest_times.append(("HDF5 Files", hdf5_data["earliest_time"].isoformat()))

    if earliest_times:
        # Sort by time
        earliest_times.sort(key=lambda x: x[1])
        print(f"\nEarliest data source: {earliest_times[0][0]}")
        print(f"Earliest time: {earliest_times[0][1]}")

        if len(earliest_times) > 1:
            print(f"\nAll sources:")
            for source, time_str in earliest_times:
                print(f"  - {source}: {time_str}")
    else:
        print("\nNo data found in any source.")

    print()


if __name__ == "__main__":
    main()
