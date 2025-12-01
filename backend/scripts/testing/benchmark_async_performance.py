#!/usr/bin/env python3
"""
Performance Benchmark: Async vs Sync Response Times Under Load

This script benchmarks the async API performance by:
1. Sending concurrent requests to various endpoints
2. Measuring response times, throughput, and error rates
3. Comparing against baseline sync performance metrics

Usage:
    python scripts/testing/benchmark_async_performance.py [--url URL] [--concurrency N]
    
Example:
    python scripts/testing/benchmark_async_performance.py --url http://localhost:8888 --concurrency 50
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

# Try to import httpx for async HTTP, fall back to aiohttp
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

import requests


@dataclass
class RequestResult:
    """Result of a single request."""
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class BenchmarkResult:
    """Aggregated benchmark results for an endpoint."""
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    min_time_ms: float
    max_time_ms: float
    mean_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    std_dev_ms: float
    requests_per_second: float
    total_duration_s: float
    
    def to_dict(self) -> dict:
        return {
            "endpoint": self.endpoint,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "error_rate": f"{(self.failed_requests / self.total_requests * 100):.2f}%",
            "timing_ms": {
                "min": round(self.min_time_ms, 2),
                "max": round(self.max_time_ms, 2),
                "mean": round(self.mean_time_ms, 2),
                "median": round(self.median_time_ms, 2),
                "p95": round(self.p95_time_ms, 2),
                "p99": round(self.p99_time_ms, 2),
                "std_dev": round(self.std_dev_ms, 2),
            },
            "throughput": {
                "requests_per_second": round(self.requests_per_second, 2),
                "total_duration_seconds": round(self.total_duration_s, 2),
            }
        }


def percentile(data: List[float], p: float) -> float:
    """Calculate the p-th percentile of the data."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def calculate_benchmark_result(endpoint: str, results: List[RequestResult], duration: float) -> BenchmarkResult:
    """Calculate aggregate statistics from individual request results."""
    successful = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]
    
    times = [r.response_time_ms for r in successful]
    
    if not times:
        times = [0.0]
    
    return BenchmarkResult(
        endpoint=endpoint,
        total_requests=len(results),
        successful_requests=len(successful),
        failed_requests=len(failed),
        min_time_ms=min(times),
        max_time_ms=max(times),
        mean_time_ms=statistics.mean(times),
        median_time_ms=statistics.median(times),
        p95_time_ms=percentile(times, 95),
        p99_time_ms=percentile(times, 99),
        std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0.0,
        requests_per_second=len(results) / duration if duration > 0 else 0,
        total_duration_s=duration,
    )


class SyncBenchmark:
    """Synchronous benchmark using requests library with thread pool."""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def make_request(self, endpoint: str, method: str = "GET") -> RequestResult:
        """Make a single synchronous request."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.perf_counter()
        
        try:
            if method == "GET":
                response = self.session.get(url, timeout=self.timeout)
            elif method == "POST":
                response = self.session.post(url, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                error=None if response.ok else f"HTTP {response.status_code}",
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=elapsed_ms,
                error=str(e),
            )
    
    def run_benchmark(
        self,
        endpoint: str,
        num_requests: int,
        concurrency: int,
        method: str = "GET"
    ) -> BenchmarkResult:
        """Run synchronous benchmark with thread pool."""
        results: List[RequestResult] = []
        
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(self.make_request, endpoint, method)
                for _ in range(num_requests)
            ]
            results = [f.result() for f in futures]
        
        duration = time.perf_counter() - start_time
        
        return calculate_benchmark_result(endpoint, results, duration)
    
    def close(self):
        self.session.close()


class AsyncBenchmark:
    """Asynchronous benchmark using httpx or aiohttp."""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    async def make_request_httpx(
        self,
        client: "httpx.AsyncClient",
        endpoint: str,
        method: str = "GET"
    ) -> RequestResult:
        """Make a single async request using httpx."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.perf_counter()
        
        try:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                error=None if response.is_success else f"HTTP {response.status_code}",
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=elapsed_ms,
                error=str(e),
            )
    
    async def make_request_aiohttp(
        self,
        session: "aiohttp.ClientSession",
        endpoint: str,
        method: str = "GET"
    ) -> RequestResult:
        """Make a single async request using aiohttp."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.perf_counter()
        
        try:
            if method == "GET":
                async with session.get(url) as response:
                    await response.text()  # Consume response
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    status = response.status
            elif method == "POST":
                async with session.post(url) as response:
                    await response.text()
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    status = response.status
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=status,
                response_time_ms=elapsed_ms,
                error=None if 200 <= status < 300 else f"HTTP {status}",
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=elapsed_ms,
                error=str(e),
            )
    
    async def run_benchmark_httpx(
        self,
        endpoint: str,
        num_requests: int,
        concurrency: int,
        method: str = "GET"
    ) -> BenchmarkResult:
        """Run async benchmark using httpx with semaphore for concurrency control."""
        semaphore = asyncio.Semaphore(concurrency)
        results: List[RequestResult] = []
        
        async def bounded_request(client, endpoint, method):
            async with semaphore:
                return await self.make_request_httpx(client, endpoint, method)
        
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [
                bounded_request(client, endpoint, method)
                for _ in range(num_requests)
            ]
            results = await asyncio.gather(*tasks)
        
        duration = time.perf_counter() - start_time
        
        return calculate_benchmark_result(endpoint, results, duration)
    
    async def run_benchmark_aiohttp(
        self,
        endpoint: str,
        num_requests: int,
        concurrency: int,
        method: str = "GET"
    ) -> BenchmarkResult:
        """Run async benchmark using aiohttp with semaphore for concurrency control."""
        semaphore = asyncio.Semaphore(concurrency)
        results: List[RequestResult] = []
        
        async def bounded_request(session, endpoint, method):
            async with semaphore:
                return await self.make_request_aiohttp(session, endpoint, method)
        
        start_time = time.perf_counter()
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [
                bounded_request(session, endpoint, method)
                for _ in range(num_requests)
            ]
            results = await asyncio.gather(*tasks)
        
        duration = time.perf_counter() - start_time
        
        return calculate_benchmark_result(endpoint, results, duration)
    
    async def run_benchmark(
        self,
        endpoint: str,
        num_requests: int,
        concurrency: int,
        method: str = "GET"
    ) -> BenchmarkResult:
        """Run async benchmark using available library."""
        if HTTPX_AVAILABLE:
            return await self.run_benchmark_httpx(endpoint, num_requests, concurrency, method)
        elif AIOHTTP_AVAILABLE:
            return await self.run_benchmark_aiohttp(endpoint, num_requests, concurrency, method)
        else:
            raise RuntimeError("No async HTTP library available. Install httpx or aiohttp.")


def print_result(result: BenchmarkResult, label: str = ""):
    """Pretty print benchmark results."""
    prefix = f"[{label}] " if label else ""
    print(f"\n{prefix}Endpoint: {result.endpoint}")
    print(f"  Total Requests:    {result.total_requests}")
    print(f"  Successful:        {result.successful_requests}")
    print(f"  Failed:            {result.failed_requests} ({result.failed_requests/result.total_requests*100:.1f}%)")
    print(f"  Duration:          {result.total_duration_s:.2f}s")
    print(f"  Throughput:        {result.requests_per_second:.1f} req/s")
    print(f"  Response Times (ms):")
    print(f"    Min:    {result.min_time_ms:8.2f}")
    print(f"    Mean:   {result.mean_time_ms:8.2f}")
    print(f"    Median: {result.median_time_ms:8.2f}")
    print(f"    P95:    {result.p95_time_ms:8.2f}")
    print(f"    P99:    {result.p99_time_ms:8.2f}")
    print(f"    Max:    {result.max_time_ms:8.2f}")
    print(f"    StdDev: {result.std_dev_ms:8.2f}")


def compare_results(sync_result: BenchmarkResult, async_result: BenchmarkResult):
    """Compare and print sync vs async results."""
    print("\n" + "="*60)
    print("COMPARISON: Sync vs Async")
    print("="*60)
    
    # Calculate improvements
    throughput_improvement = (
        (async_result.requests_per_second - sync_result.requests_per_second) 
        / sync_result.requests_per_second * 100
    ) if sync_result.requests_per_second > 0 else 0
    
    mean_time_improvement = (
        (sync_result.mean_time_ms - async_result.mean_time_ms) 
        / sync_result.mean_time_ms * 100
    ) if sync_result.mean_time_ms > 0 else 0
    
    p95_improvement = (
        (sync_result.p95_time_ms - async_result.p95_time_ms) 
        / sync_result.p95_time_ms * 100
    ) if sync_result.p95_time_ms > 0 else 0
    
    print(f"\n{'Metric':<25} {'Sync':<15} {'Async':<15} {'Improvement':<15}")
    print("-" * 70)
    print(f"{'Throughput (req/s)':<25} {sync_result.requests_per_second:<15.1f} {async_result.requests_per_second:<15.1f} {throughput_improvement:+.1f}%")
    print(f"{'Mean Response (ms)':<25} {sync_result.mean_time_ms:<15.2f} {async_result.mean_time_ms:<15.2f} {mean_time_improvement:+.1f}%")
    print(f"{'Median Response (ms)':<25} {sync_result.median_time_ms:<15.2f} {async_result.median_time_ms:<15.2f}")
    print(f"{'P95 Response (ms)':<25} {sync_result.p95_time_ms:<15.2f} {async_result.p95_time_ms:<15.2f} {p95_improvement:+.1f}%")
    print(f"{'P99 Response (ms)':<25} {sync_result.p99_time_ms:<15.2f} {async_result.p99_time_ms:<15.2f}")
    print(f"{'Error Rate':<25} {sync_result.failed_requests/sync_result.total_requests*100:<15.1f}% {async_result.failed_requests/async_result.total_requests*100:<15.1f}%")


async def run_full_benchmark(
    base_url: str,
    num_requests: int,
    concurrency: int,
    endpoints: List[str],
) -> Dict[str, Any]:
    """Run full benchmark suite comparing sync vs async."""
    
    print(f"\n{'='*60}")
    print("API PERFORMANCE BENCHMARK")
    print(f"{'='*60}")
    print(f"Target URL:     {base_url}")
    print(f"Requests:       {num_requests} per endpoint")
    print(f"Concurrency:    {concurrency}")
    print(f"Endpoints:      {len(endpoints)}")
    print(f"Async Library:  {'httpx' if HTTPX_AVAILABLE else 'aiohttp' if AIOHTTP_AVAILABLE else 'none'}")
    print(f"Timestamp:      {datetime.now().isoformat()}")
    print(f"{'='*60}")
    
    # Check server is reachable
    try:
        response = requests.get(f"{base_url}/api/v1/health", timeout=5)
        print(f"\n✓ Server reachable: {response.status_code}")
    except Exception as e:
        print(f"\n✗ Server unreachable: {e}")
        print("Make sure the API server is running.")
        return {}
    
    sync_benchmark = SyncBenchmark(base_url)
    async_benchmark = AsyncBenchmark(base_url)
    
    all_results = {
        "metadata": {
            "base_url": base_url,
            "num_requests": num_requests,
            "concurrency": concurrency,
            "timestamp": datetime.now().isoformat(),
        },
        "sync_results": {},
        "async_results": {},
        "comparisons": {},
    }
    
    for endpoint in endpoints:
        print(f"\n\nBenchmarking: {endpoint}")
        print("-" * 40)
        
        # Run sync benchmark
        print("Running sync benchmark (threaded)...")
        sync_result = sync_benchmark.run_benchmark(endpoint, num_requests, concurrency)
        print_result(sync_result, "SYNC")
        all_results["sync_results"][endpoint] = sync_result.to_dict()
        
        # Small pause between tests
        await asyncio.sleep(0.5)
        
        # Run async benchmark
        print("\nRunning async benchmark...")
        async_result = await async_benchmark.run_benchmark(endpoint, num_requests, concurrency)
        print_result(async_result, "ASYNC")
        all_results["async_results"][endpoint] = async_result.to_dict()
        
        # Compare
        compare_results(sync_result, async_result)
        
        all_results["comparisons"][endpoint] = {
            "throughput_improvement_pct": round(
                (async_result.requests_per_second - sync_result.requests_per_second) 
                / sync_result.requests_per_second * 100, 2
            ) if sync_result.requests_per_second > 0 else 0,
            "mean_time_improvement_pct": round(
                (sync_result.mean_time_ms - async_result.mean_time_ms) 
                / sync_result.mean_time_ms * 100, 2
            ) if sync_result.mean_time_ms > 0 else 0,
        }
        
        # Pause between endpoints
        await asyncio.sleep(1)
    
    sync_benchmark.close()
    
    # Print summary
    print(f"\n\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    
    for endpoint, comparison in all_results["comparisons"].items():
        throughput_emoji = "🚀" if comparison["throughput_improvement_pct"] > 0 else "📉"
        latency_emoji = "⚡" if comparison["mean_time_improvement_pct"] > 0 else "🐢"
        print(f"\n{endpoint}:")
        print(f"  {throughput_emoji} Throughput: {comparison['throughput_improvement_pct']:+.1f}%")
        print(f"  {latency_emoji} Latency:    {comparison['mean_time_improvement_pct']:+.1f}%")
    
    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark async vs sync API performance"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8888",
        help="Base URL of the API server"
    )
    parser.add_argument(
        "--requests", "-n",
        type=int,
        default=100,
        help="Number of requests per endpoint"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=10,
        help="Number of concurrent requests"
    )
    parser.add_argument(
        "--endpoints",
        nargs="+",
        default=None,
        help="Specific endpoints to test"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output JSON file for results"
    )
    
    args = parser.parse_args()
    
    # Default endpoints to test
    endpoints = args.endpoints or [
        "/api/v1/health",
        "/api/v1/images",
        "/api/v1/sources",
        "/api/v1/jobs",
        "/api/v1/stats",
    ]
    
    # Check for async HTTP library
    if not HTTPX_AVAILABLE and not AIOHTTP_AVAILABLE:
        print("Error: No async HTTP library available.")
        print("Install one with: pip install httpx  OR  pip install aiohttp")
        sys.exit(1)
    
    # Run benchmark
    results = asyncio.run(run_full_benchmark(
        base_url=args.url,
        num_requests=args.requests,
        concurrency=args.concurrency,
        endpoints=endpoints,
    ))
    
    # Save results if output specified
    if args.output and results:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
