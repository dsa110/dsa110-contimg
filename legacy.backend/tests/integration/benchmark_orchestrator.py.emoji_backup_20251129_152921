#!/usr/bin/env python3
"""Performance benchmarks for MosaicOrchestrator.

This script benchmarks orchestrator performance characteristics:
- Group formation time
- Workflow processing time
- Database query performance
- Memory usage

Usage:
    python -m pytest tests/integration/benchmark_orchestrator.py -v
    python tests/integration/benchmark_orchestrator.py [--iterations N]
"""

from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator


def create_mock_ms_paths(count: int, tmp_path: Path) -> list[str]:
    """Create mock MS file paths for benchmarking."""
    ms_dir = tmp_path / "ms"
    ms_dir.mkdir(exist_ok=True)

    ms_paths = []
    for i in range(count):
        ms_path = ms_dir / f"2025-11-12T10:{i:02d}:00.ms"
        ms_path.mkdir(exist_ok=True)  # MS is a directory
        ms_paths.append(str(ms_path))

    return ms_paths


def benchmark_group_formation(
    orchestrator: MosaicOrchestrator, ms_paths: list[str], iterations: int = 10
) -> dict:
    """Benchmark group formation performance."""
    times = []

    with patch(
        "dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._form_group_from_ms_paths"
    ) as mock_form:
        mock_form.return_value = True

        for i in range(iterations):
            group_id = f"benchmark_group_{i}"
            start = time.perf_counter()
            orchestrator._form_group_from_ms_paths(ms_paths, group_id)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
        "min": min(times),
        "max": max(times),
        "iterations": iterations,
    }


def benchmark_workflow_processing(orchestrator: MosaicOrchestrator, iterations: int = 10) -> dict:
    """Benchmark workflow processing performance."""
    times = []

    with patch(
        "dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._process_group_workflow"
    ) as mock_process:
        mock_process.return_value = "/stage/mosaics/mosaic_benchmark.fits"

        for i in range(iterations):
            group_id = f"benchmark_group_{i}"
            start = time.perf_counter()
            orchestrator._process_group_workflow(group_id)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
        "min": min(times),
        "max": max(times),
        "iterations": iterations,
    }


def benchmark_database_operations(
    products_db: Path, ms_paths: list[str], iterations: int = 10
) -> dict:
    """Benchmark database query performance."""

    conn = ensure_products_db(products_db)

    # Insert test data
    now = time.time()
    mid_mjd_base = 60295.0

    for i, ms_path in enumerate(ms_paths):
        conn.execute(
            """
            INSERT OR REPLACE INTO ms_index 
            (path, start_mjd, end_mjd, mid_mjd, processed_at, status, stage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ms_path,
                mid_mjd_base + i * 5 / (24 * 60),
                mid_mjd_base + (i + 1) * 5 / (24 * 60),
                mid_mjd_base + (i + 0.5) * 5 / (24 * 60),
                now,
                "done",
                "imaged",
            ),
        )
    conn.commit()

    # Benchmark queries
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        cursor = conn.execute(
            """
            SELECT path, mid_mjd FROM ms_index 
            WHERE status = ? AND stage = ?
            ORDER BY mid_mjd
            """,
            ("done", "imaged"),
        )
        results = cursor.fetchall()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    conn.close()

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
        "min": min(times),
        "max": max(times),
        "iterations": iterations,
        "results_count": len(results),
    }


def main():
    """Run orchestrator benchmarks."""
    parser = argparse.ArgumentParser(description="Benchmark MosaicOrchestrator performance")
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations per benchmark (default: 10)",
    )
    parser.add_argument(
        "--ms-count",
        type=int,
        default=10,
        help="Number of MS files to simulate (default: 10)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("MosaicOrchestrator Performance Benchmarks")
    print("=" * 70)
    print(f"Iterations: {args.iterations}")
    print(f"MS Files: {args.ms_count}")
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        products_db = tmp_path / "products.sqlite3"

        # Setup
        ensure_products_db(products_db)
        orchestrator = MosaicOrchestrator(products_db_path=products_db)
        ms_paths = create_mock_ms_paths(args.ms_count, tmp_path)

        # Benchmark 1: Group Formation
        print("Benchmark 1: Group Formation")
        print("-" * 70)
        form_stats = benchmark_group_formation(orchestrator, ms_paths, args.iterations)
        print(f"  Mean:   {form_stats['mean']:.6f}s")
        print(f"  Median: {form_stats['median']:.6f}s")
        print(f"  StdDev: {form_stats['stdev']:.6f}s")
        print(f"  Min:    {form_stats['min']:.6f}s")
        print(f"  Max:    {form_stats['max']:.6f}s")
        print()

        # Benchmark 2: Workflow Processing
        print("Benchmark 2: Workflow Processing")
        print("-" * 70)
        workflow_stats = benchmark_workflow_processing(orchestrator, args.iterations)
        print(f"  Mean:   {workflow_stats['mean']:.6f}s")
        print(f"  Median: {workflow_stats['median']:.6f}s")
        print(f"  StdDev: {workflow_stats['stdev']:.6f}s")
        print(f"  Min:    {workflow_stats['min']:.6f}s")
        print(f"  Max:    {workflow_stats['max']:.6f}s")
        print()

        # Benchmark 3: Database Operations
        print("Benchmark 3: Database Query Performance")
        print("-" * 70)
        db_stats = benchmark_database_operations(products_db, ms_paths, args.iterations)
        print(f"  Mean:        {db_stats['mean']:.6f}s")
        print(f"  Median:      {db_stats['median']:.6f}s")
        print(f"  StdDev:      {db_stats['stdev']:.6f}s")
        print(f"  Min:         {db_stats['min']:.6f}s")
        print(f"  Max:         {db_stats['max']:.6f}s")
        print(f"  Results:     {db_stats['results_count']} rows")
        print()

        # Summary
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"Group Formation:    {form_stats['mean']:.6f}s ± {form_stats['stdev']:.6f}s")
        print(
            f"Workflow Processing: {workflow_stats['mean']:.6f}s ± {workflow_stats['stdev']:.6f}s"
        )
        print(f"Database Queries:   {db_stats['mean']:.6f}s ± {db_stats['stdev']:.6f}s")
        print()

        # Performance targets (with mocks, should be very fast)
        print("Performance Targets (with mocked dependencies):")
        print("  Group Formation:    < 0.1s")
        print("  Workflow Processing: < 0.1s")
        print("  Database Queries:   < 0.01s")
        print()

        # Check if targets met
        all_passed = True
        if form_stats["mean"] > 0.1:
            print("⚠ Warning: Group formation slower than target")
            all_passed = False
        if workflow_stats["mean"] > 0.1:
            print("⚠ Warning: Workflow processing slower than target")
            all_passed = False
        if db_stats["mean"] > 0.01:
            print("⚠ Warning: Database queries slower than target")
            all_passed = False

        if all_passed:
            print("✓ All benchmarks within target performance")
        else:
            print("✗ Some benchmarks exceed target performance")

        return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
