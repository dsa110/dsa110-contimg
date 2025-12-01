#!/usr/bin/env python3
"""
Database Connection Pool Efficiency Benchmark

Compares different connection strategies:
1. Single shared connection (current implementation)
2. Connection-per-request (no pooling)
3. Proper connection pool (proposed improvement)

Usage:
    python scripts/testing/benchmark_db_pool.py [--requests 1000] [--concurrency 50]
"""

import argparse
import asyncio
import json
import os
import sqlite3
import statistics
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional

import aiosqlite


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    strategy: str
    total_requests: int
    concurrency: int
    total_duration_seconds: float
    requests_per_second: float
    timing_ms: dict
    errors: int = 0


@dataclass
class ConnectionPoolStats:
    """Stats for connection pool efficiency."""
    connections_created: int = 0
    connections_reused: int = 0
    peak_active: int = 0
    current_active: int = 0


# Strategy 1: Single Shared Connection (current implementation)
class SingleConnectionPool:
    """Current implementation - single shared connection."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self.stats = ConnectionPoolStats()
        self._lock = asyncio.Lock()
    
    async def _ensure_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path, timeout=30.0)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode=WAL")
            self.stats.connections_created += 1
        else:
            self.stats.connections_reused += 1
        return self._conn
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[aiosqlite.Connection]:
        async with self._lock:
            conn = await self._ensure_connection()
            self.stats.current_active += 1
            self.stats.peak_active = max(self.stats.peak_active, self.stats.current_active)
            try:
                yield conn
            finally:
                self.stats.current_active -= 1
    
    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None


# Strategy 2: Connection-per-Request (no pooling)
class NoPooling:
    """Create new connection for each request."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.stats = ConnectionPoolStats()
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[aiosqlite.Connection]:
        conn = await aiosqlite.connect(self.db_path, timeout=30.0)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        self.stats.connections_created += 1
        self.stats.current_active += 1
        self.stats.peak_active = max(self.stats.peak_active, self.stats.current_active)
        try:
            yield conn
        finally:
            self.stats.current_active -= 1
            await conn.close()
    
    async def close(self):
        pass


# Strategy 3: Proper Connection Pool
class ProperConnectionPool:
    """
    Connection pool with configurable min/max connections.
    
    Maintains a pool of reusable connections to avoid
    connection overhead while allowing true concurrency.
    """
    
    def __init__(self, db_path: str, min_size: int = 2, max_size: int = 10):
        self.db_path = db_path
        self.min_size = min_size
        self.max_size = max_size
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._size = 0
        self._lock = asyncio.Lock()
        self.stats = ConnectionPoolStats()
        self._initialized = False
    
    async def _create_connection(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path, timeout=30.0)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        self.stats.connections_created += 1
        return conn
    
    async def _initialize(self):
        """Pre-create minimum connections."""
        if self._initialized:
            return
        async with self._lock:
            if self._initialized:
                return
            for _ in range(self.min_size):
                conn = await self._create_connection()
                await self._pool.put(conn)
                self._size += 1
            self._initialized = True
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[aiosqlite.Connection]:
        await self._initialize()
        
        conn = None
        try:
            # Try to get from pool (non-blocking)
            try:
                conn = self._pool.get_nowait()
                self.stats.connections_reused += 1
            except asyncio.QueueEmpty:
                # Pool empty, create new if under max
                async with self._lock:
                    if self._size < self.max_size:
                        conn = await self._create_connection()
                        self._size += 1
                    else:
                        # Wait for available connection
                        conn = await self._pool.get()
                        self.stats.connections_reused += 1
            
            self.stats.current_active += 1
            self.stats.peak_active = max(self.stats.peak_active, self.stats.current_active)
            yield conn
            
        finally:
            self.stats.current_active -= 1
            if conn:
                # Return to pool
                try:
                    self._pool.put_nowait(conn)
                except asyncio.QueueFull:
                    await conn.close()
                    async with self._lock:
                        self._size -= 1
    
    async def close(self):
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                await conn.close()
            except asyncio.QueueEmpty:
                break
        self._size = 0
        self._initialized = False


async def run_query(pool, query: str) -> float:
    """Run a query and return execution time in ms."""
    start = time.perf_counter()
    try:
        async with pool.acquire() as conn:
            cursor = await conn.execute(query)
            await cursor.fetchall()
        return (time.perf_counter() - start) * 1000
    except Exception as e:
        return -1  # Error marker


async def benchmark_strategy(
    pool,
    strategy_name: str,
    num_requests: int,
    concurrency: int,
    query: str
) -> BenchmarkResult:
    """Benchmark a connection strategy."""
    print(f"\n{'='*60}")
    print(f"Testing: {strategy_name}")
    print(f"Requests: {num_requests}, Concurrency: {concurrency}")
    print(f"{'='*60}")
    
    semaphore = asyncio.Semaphore(concurrency)
    timings = []
    errors = 0
    
    async def bounded_query():
        async with semaphore:
            return await run_query(pool, query)
    
    start_time = time.perf_counter()
    results = await asyncio.gather(*[bounded_query() for _ in range(num_requests)])
    total_duration = time.perf_counter() - start_time
    
    for timing in results:
        if timing < 0:
            errors += 1
        else:
            timings.append(timing)
    
    if timings:
        timing_stats = {
            "min": round(min(timings), 2),
            "max": round(max(timings), 2),
            "mean": round(statistics.mean(timings), 2),
            "median": round(statistics.median(timings), 2),
            "p95": round(sorted(timings)[int(len(timings) * 0.95)], 2),
            "p99": round(sorted(timings)[int(len(timings) * 0.99)], 2),
            "std_dev": round(statistics.stdev(timings) if len(timings) > 1 else 0, 2),
        }
    else:
        timing_stats = {}
    
    result = BenchmarkResult(
        strategy=strategy_name,
        total_requests=num_requests,
        concurrency=concurrency,
        total_duration_seconds=round(total_duration, 3),
        requests_per_second=round(num_requests / total_duration, 1),
        timing_ms=timing_stats,
        errors=errors,
    )
    
    # Print results
    print(f"\nResults for {strategy_name}:")
    print(f"  Duration:     {result.total_duration_seconds:.2f}s")
    print(f"  Throughput:   {result.requests_per_second:.1f} req/s")
    print(f"  Mean Latency: {timing_stats.get('mean', 'N/A')}ms")
    print(f"  P95 Latency:  {timing_stats.get('p95', 'N/A')}ms")
    print(f"  P99 Latency:  {timing_stats.get('p99', 'N/A')}ms")
    print(f"  Errors:       {errors}")
    
    # Print pool stats
    print(f"\n  Connection Stats:")
    print(f"    Connections Created: {pool.stats.connections_created}")
    print(f"    Connections Reused:  {pool.stats.connections_reused}")
    print(f"    Peak Active:         {pool.stats.peak_active}")
    
    return result


def create_test_database(db_path: str, num_rows: int = 1000):
    """Create a test database with sample data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_data (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value REAL,
            created_at TEXT
        )
    """)
    
    # Insert test data
    cursor.executemany(
        "INSERT OR REPLACE INTO test_data (id, name, value, created_at) VALUES (?, ?, ?, ?)",
        [(i, f"item_{i}", i * 1.5, datetime.now().isoformat()) for i in range(num_rows)]
    )
    
    conn.commit()
    conn.close()


async def main():
    parser = argparse.ArgumentParser(description="Database Connection Pool Benchmark")
    parser.add_argument("--requests", type=int, default=1000, help="Number of requests")
    parser.add_argument("--concurrency", type=int, default=50, help="Concurrent requests")
    parser.add_argument("--db-path", type=str, help="Path to test database")
    parser.add_argument("-o", "--output", type=str, help="Output JSON file")
    args = parser.parse_args()
    
    # Create test database
    if args.db_path:
        db_path = args.db_path
    else:
        # Use temp database
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_benchmark.db")
    
    print(f"Creating test database: {db_path}")
    create_test_database(db_path, num_rows=5000)
    
    # Test query (simulates typical API query)
    test_query = """
        SELECT id, name, value, created_at 
        FROM test_data 
        WHERE value > 100 AND value < 500
        ORDER BY created_at DESC
        LIMIT 50
    """
    
    results = []
    
    # Test Strategy 1: Single Shared Connection
    pool1 = SingleConnectionPool(db_path)
    try:
        result1 = await benchmark_strategy(
            pool1, 
            "Single Shared Connection (Current)", 
            args.requests, 
            args.concurrency,
            test_query
        )
        results.append(result1)
    finally:
        await pool1.close()
    
    # Test Strategy 2: No Pooling (connection per request)
    pool2 = NoPooling(db_path)
    try:
        result2 = await benchmark_strategy(
            pool2,
            "No Pooling (New Connection Each Request)",
            args.requests,
            args.concurrency,
            test_query
        )
        results.append(result2)
    finally:
        await pool2.close()
    
    # Test Strategy 3: Proper Connection Pool (small)
    pool3 = ProperConnectionPool(db_path, min_size=2, max_size=5)
    try:
        result3 = await benchmark_strategy(
            pool3,
            "Connection Pool (2-5 connections)",
            args.requests,
            args.concurrency,
            test_query
        )
        results.append(result3)
    finally:
        await pool3.close()
    
    # Test Strategy 4: Proper Connection Pool (larger)
    pool4 = ProperConnectionPool(db_path, min_size=5, max_size=20)
    try:
        result4 = await benchmark_strategy(
            pool4,
            "Connection Pool (5-20 connections)",
            args.requests,
            args.concurrency,
            test_query
        )
        results.append(result4)
    finally:
        await pool4.close()
    
    # Summary comparison
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    baseline = results[0].requests_per_second
    
    print(f"\n{'Strategy':<45} {'Throughput':>12} {'Improvement':>12} {'P99':>10}")
    print("-" * 80)
    
    for result in results:
        improvement = ((result.requests_per_second / baseline) - 1) * 100
        sign = "+" if improvement >= 0 else ""
        print(
            f"{result.strategy:<45} "
            f"{result.requests_per_second:>10.1f}/s "
            f"{sign}{improvement:>10.1f}% "
            f"{result.timing_ms.get('p99', 'N/A'):>8}ms"
        )
    
    # Recommendation
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    best = max(results, key=lambda r: r.requests_per_second)
    print(f"\nBest performing strategy: {best.strategy}")
    print(f"Throughput: {best.requests_per_second:.1f} req/s")
    
    if best.strategy != results[0].strategy:
        improvement = ((best.requests_per_second / results[0].requests_per_second) - 1) * 100
        print(f"Improvement over current: +{improvement:.1f}%")
    
    # Save results
    if args.output:
        output_data = {
            "metadata": {
                "db_path": db_path,
                "num_requests": args.requests,
                "concurrency": args.concurrency,
                "timestamp": datetime.now().isoformat(),
            },
            "results": [
                {
                    "strategy": r.strategy,
                    "throughput": r.requests_per_second,
                    "timing_ms": r.timing_ms,
                    "errors": r.errors,
                }
                for r in results
            ],
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
