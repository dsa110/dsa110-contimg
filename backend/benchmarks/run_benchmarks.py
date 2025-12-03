#!/usr/bin/env python3
"""
DSA-110 Pipeline Benchmark Runner

A standalone benchmark runner that doesn't require full ASV setup.
Runs benchmarks and stores results in JSON format for tracking.

Usage:
    python run_benchmarks.py                    # Run all benchmarks
    python run_benchmarks.py --suite gpu        # Run GPU benchmarks only
    python run_benchmarks.py --quick            # Quick mode (fewer iterations)
    python run_benchmarks.py --output results/  # Specify output directory

Results are stored in JSON format with timestamps for trend analysis.
"""

import argparse
import gc
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Add parent src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import resource limits for safety
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "testing"))
try:
    from resource_limits import ResourceLimitedRunner, check_available_memory
    HAS_RESOURCE_LIMITS = True
except ImportError:
    HAS_RESOURCE_LIMITS = False


def get_system_info() -> Dict[str, Any]:
    """Gather system information for benchmark context."""
    import platform

    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
        "timestamp": datetime.now().isoformat(),
    }

    # Memory info
    try:
        import psutil
        mem = psutil.virtual_memory()
        info["memory_total_gb"] = round(mem.total / 1e9, 1)
        info["memory_available_gb"] = round(mem.available / 1e9, 1)
    except ImportError:
        pass

    # CPU info
    try:
        info["cpu_count"] = os.cpu_count()
    except Exception:
        pass

    # GPU info
    try:
        import cupy as cp
        n_gpus = cp.cuda.runtime.getDeviceCount()
        gpus = []
        for i in range(n_gpus):
            props = cp.cuda.runtime.getDeviceProperties(i)
            gpus.append({
                "id": i,
                "name": props["name"].decode() if isinstance(props["name"], bytes) else props["name"],
                "memory_gb": round(props["totalGlobalMem"] / 1e9, 1),
                "compute_capability": f"{props['major']}.{props['minor']}",
            })
        info["gpus"] = gpus
    except Exception:
        info["gpus"] = []

    # Git info
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        if result.returncode == 0:
            info["git_commit"] = result.stdout.strip()[:12]

        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        if result.returncode == 0:
            info["git_branch"] = result.stdout.strip()
    except Exception:
        pass

    return info


def time_function(
    func: Callable,
    setup: Optional[Callable] = None,
    repeat: int = 3,
    number: int = 1,
) -> Dict[str, Any]:
    """Time a function with multiple repeats.

    Returns timing statistics.
    """
    times = []

    for _ in range(repeat):
        if setup:
            setup()

        gc.collect()
        gc.disable()

        try:
            start = time.perf_counter()
            for _ in range(number):
                func()
            end = time.perf_counter()
            times.append((end - start) / number)
        finally:
            gc.enable()

    if not times:
        return {"error": "No successful runs"}

    times.sort()
    return {
        "min": times[0],
        "max": times[-1],
        "mean": sum(times) / len(times),
        "median": times[len(times) // 2],
        "runs": len(times),
    }


def run_benchmark_class(cls, quick: bool = False) -> Dict[str, Any]:
    """Run all benchmarks in a class."""
    results = {}

    # Instantiate
    try:
        instance = cls()
    except Exception as e:
        return {"error": f"Failed to instantiate: {e}"}

    # Run setup if exists
    if hasattr(instance, "setup"):
        try:
            instance.setup()
        except Exception as e:
            return {"error": f"Setup failed: {e}"}

    # Find benchmark methods
    methods = [m for m in dir(instance) if m.startswith("time_") or m.startswith("peakmem_")]

    repeat = 2 if quick else getattr(cls, "repeat", 3)

    for method_name in methods:
        method = getattr(instance, method_name)

        print(f"    {method_name}...", end=" ", flush=True)

        try:
            if method_name.startswith("time_"):
                result = time_function(method, repeat=repeat)
                if "error" not in result:
                    print(f"{result['mean']:.4f}s (±{result['max']-result['min']:.4f}s)")
                else:
                    print(f"ERROR: {result['error']}")
            else:
                # Memory benchmark - just run once
                start = time.perf_counter()
                mem_result = method()
                elapsed = time.perf_counter() - start
                result = {"value": mem_result, "time": elapsed}
                print(f"{mem_result} ({elapsed:.2f}s)")

            results[method_name] = result

        except Exception as e:
            results[method_name] = {"error": str(e)}
            print(f"ERROR: {e}")

    return results


def run_calibration_benchmarks(quick: bool = False) -> Dict[str, Any]:
    """Run calibration benchmarks."""
    print("\n=== Calibration Benchmarks ===")

    results = {}

    # Import benchmark classes
    try:
        from benchmarks.bench_calibration import SyntheticTimeSuite
        print("  SyntheticTimeSuite:")
        results["SyntheticTimeSuite"] = run_benchmark_class(SyntheticTimeSuite, quick)
    except Exception as e:
        results["SyntheticTimeSuite"] = {"error": str(e)}
        print(f"  ERROR: {e}")

    try:
        from benchmarks.bench_calibration import TimeSuite
        print("  TimeSuite:")
        results["TimeSuite"] = run_benchmark_class(TimeSuite, quick)
    except Exception as e:
        results["TimeSuite"] = {"error": str(e)}

    return results


def run_imaging_benchmarks(quick: bool = False) -> Dict[str, Any]:
    """Run imaging benchmarks."""
    print("\n=== Imaging Benchmarks ===")

    results = {}

    try:
        from benchmarks.bench_imaging import SyntheticTimeSuite
        print("  SyntheticTimeSuite:")
        results["SyntheticTimeSuite"] = run_benchmark_class(SyntheticTimeSuite, quick)
    except Exception as e:
        results["SyntheticTimeSuite"] = {"error": str(e)}
        print(f"  ERROR: {e}")

    return results


def run_gpu_benchmarks(quick: bool = False) -> Dict[str, Any]:
    """Run GPU benchmarks."""
    print("\n=== GPU Benchmarks ===")

    results = {}

    try:
        from benchmarks.bench_gpu import GPUTimeSuite
        print("  GPUTimeSuite:")
        results["GPUTimeSuite"] = run_benchmark_class(GPUTimeSuite, quick)
    except Exception as e:
        results["GPUTimeSuite"] = {"error": str(e)}
        print(f"  ERROR: {e}")

    return results


def run_conversion_benchmarks(quick: bool = False) -> Dict[str, Any]:
    """Run conversion benchmarks."""
    print("\n=== Conversion Benchmarks ===")

    results = {}

    try:
        from benchmarks.bench_conversion import SyntheticTimeSuite
        print("  SyntheticTimeSuite:")
        results["SyntheticTimeSuite"] = run_benchmark_class(SyntheticTimeSuite, quick)
    except Exception as e:
        results["SyntheticTimeSuite"] = {"error": str(e)}
        print(f"  ERROR: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="DSA-110 Pipeline Benchmark Runner"
    )
    parser.add_argument(
        "--suite",
        choices=["all", "calibration", "imaging", "gpu", "conversion"],
        default="all",
        help="Benchmark suite to run",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode (fewer iterations)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--memory-limit",
        type=float,
        default=16.0,
        help="Memory limit in GB (default: 16)",
    )

    args = parser.parse_args()

    # Change to benchmarks directory
    os.chdir(Path(__file__).parent)

    print("=" * 60)
    print("  DSA-110 Pipeline Benchmarks")
    print("=" * 60)

    # Gather system info
    print("\nGathering system information...")
    system_info = get_system_info()
    print(f"  Platform: {system_info.get('platform', 'unknown')}")
    print(f"  Python: {system_info.get('python_version', 'unknown')}")
    print(f"  Memory: {system_info.get('memory_available_gb', '?')}/{system_info.get('memory_total_gb', '?')} GB")
    if system_info.get("gpus"):
        for gpu in system_info["gpus"]:
            print(f"  GPU {gpu['id']}: {gpu['name']} ({gpu['memory_gb']} GB)")
    else:
        print("  GPU: None detected")

    # Run benchmarks
    all_results = {
        "system": system_info,
        "benchmarks": {},
    }

    benchmark_runners = {
        "calibration": run_calibration_benchmarks,
        "imaging": run_imaging_benchmarks,
        "gpu": run_gpu_benchmarks,
        "conversion": run_conversion_benchmarks,
    }

    if args.suite == "all":
        suites = ["calibration", "imaging", "gpu", "conversion"]
    else:
        suites = [args.suite]

    for suite in suites:
        runner = benchmark_runners[suite]
        try:
            all_results["benchmarks"][suite] = runner(quick=args.quick)
        except Exception as e:
            all_results["benchmarks"][suite] = {"error": str(e)}
            traceback.print_exc()

    # Save results
    args.output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = args.output / f"benchmark_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"Results saved to: {output_file}")

    # Also update latest.json
    latest_file = args.output / "latest.json"
    with open(latest_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"Latest results: {latest_file}")

    # Print summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")

    for suite, results in all_results["benchmarks"].items():
        print(f"\n{suite.upper()}:")
        if isinstance(results, dict) and "error" not in results:
            for cls_name, cls_results in results.items():
                if isinstance(cls_results, dict) and "error" not in cls_results:
                    for method, timing in cls_results.items():
                        if isinstance(timing, dict) and "mean" in timing:
                            print(f"  {method}: {timing['mean']:.4f}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
