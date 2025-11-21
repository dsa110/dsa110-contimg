#!/opt/miniforge/envs/casa6/bin/python
"""Benchmark NVSS query performance: SQLite vs CSV.

This script measures the performance improvement of using SQLite databases
instead of CSV files for NVSS catalog queries.
"""

# Add project root to path
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from dsa110_contimg.calibration.catalogs import (query_nvss_sources,
                                                 read_nvss_catalog)


def benchmark_query(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    min_flux_mjy: float = 10.0,
    n_iterations: int = 100,
):
    """Benchmark query_nvss_sources function."""
    print(f"Benchmarking NVSS query:")
    print(f"  Center: RA={ra_deg:.6f}, Dec={dec_deg:.6f}")
    print(f"  Radius: {radius_deg} deg")
    print(f"  Min flux: {min_flux_mjy} mJy")
    print(f"  Iterations: {n_iterations}")
    print()

    # Warm-up query (to populate cache)
    print("Warming up...")
    _ = query_nvss_sources(
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        radius_deg=radius_deg,
        min_flux_mjy=min_flux_mjy,
    )
    print(f"  Found {len(_)} sources")
    print()

    # Benchmark SQLite queries
    print("Benchmarking SQLite queries...")
    times_sqlite = []
    for i in range(n_iterations):
        start = time.perf_counter()
        df = query_nvss_sources(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            radius_deg=radius_deg,
            min_flux_mjy=min_flux_mjy,
        )
        elapsed = time.perf_counter() - start
        times_sqlite.append(elapsed)
        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1}/{n_iterations} queries")

    times_sqlite = np.array(times_sqlite)
    print()
    print("SQLite Performance:")
    print(f"  Mean: {times_sqlite.mean()*1000:.2f} ms")
    print(f"  Median: {np.median(times_sqlite)*1000:.2f} ms")
    print(f"  Min: {times_sqlite.min()*1000:.2f} ms")
    print(f"  Max: {times_sqlite.max()*1000:.2f} ms")
    print(f"  Std: {times_sqlite.std()*1000:.2f} ms")
    print()

    # Benchmark CSV fallback (force by using non-existent path)
    print("Benchmarking CSV fallback (forcing CSV mode)...")
    # Temporarily rename SQLite database to force CSV fallback
    db_path = Path("/data/dsa110-contimg/state/catalogs/nvss_dec+54.6.sqlite3")
    backup_path = db_path.with_suffix(".sqlite3.backup")
    db_exists = db_path.exists()

    if db_exists:
        import shutil

        shutil.move(str(db_path), str(backup_path))
        print("  Temporarily disabled SQLite database to test CSV fallback")

    try:
        times_csv = []
        for i in range(min(n_iterations, 10)):  # CSV is slower, fewer iterations
            start = time.perf_counter()
            df = query_nvss_sources(
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                radius_deg=radius_deg,
                min_flux_mjy=min_flux_mjy,
            )
            elapsed = time.perf_counter() - start
            times_csv.append(elapsed)
            if (i + 1) % 5 == 0:
                print(f"  Completed {i + 1}/{min(n_iterations, 10)} queries")

        times_csv = np.array(times_csv)
        print()
        print("CSV Performance:")
        print(f"  Mean: {times_csv.mean()*1000:.2f} ms")
        print(f"  Median: {np.median(times_csv)*1000:.2f} ms")
        print(f"  Min: {times_csv.min()*1000:.2f} ms")
        print(f"  Max: {times_csv.max()*1000:.2f} ms")
        print(f"  Std: {times_csv.std()*1000:.2f} ms")
        print()

        speedup = times_csv.mean() / times_sqlite.mean()
        print(f"Performance Improvement:")
        print(f"  Speedup: {speedup:.1f}× faster with SQLite")
        print(f"  Time saved: {(times_csv.mean() - times_sqlite.mean())*1000:.2f} ms per query")

    finally:
        # Restore SQLite database
        if db_exists:
            shutil.move(str(backup_path), str(db_path))
            print("  Restored SQLite database")


if __name__ == "__main__":
    # Test with a typical field center (around Dec +54.6 where we have a database)
    benchmark_query(
        ra_deg=83.5,
        dec_deg=54.6,
        radius_deg=1.0,
        min_flux_mjy=10.0,
        n_iterations=100,
    )
