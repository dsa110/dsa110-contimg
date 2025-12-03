"""
Performance monitoring API routes.

Provides endpoints for:
- Benchmark results from ASV/custom benchmarks
- Performance trend visualization data
- GPU status and utilization
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])


# ============================================================================
# Pydantic Models
# ============================================================================


class BenchmarkTiming(BaseModel):
    """Timing result for a single benchmark."""

    name: str
    min: float
    max: float
    mean: float
    median: Optional[float] = None
    runs: int = 1
    unit: str = "seconds"


class BenchmarkSuite(BaseModel):
    """Results from a benchmark suite."""

    name: str
    benchmarks: List[BenchmarkTiming]


class BenchmarkResult(BaseModel):
    """Complete benchmark result with system info."""

    timestamp: str
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    platform: Optional[str] = None
    python_version: Optional[str] = None
    suites: Dict[str, Any]


class GPUInfo(BaseModel):
    """GPU device information."""

    id: int
    name: str
    memory_total_gb: float
    memory_used_gb: float
    memory_free_gb: float
    utilization_gpu: int = 0
    utilization_memory: int = 0
    temperature_c: int = 0
    power_draw_w: Optional[float] = None


class GPUStatus(BaseModel):
    """Status of all GPUs."""

    available: bool
    gpus: List[GPUInfo] = Field(default_factory=list)
    error: Optional[str] = None


class PerformanceSummary(BaseModel):
    """Summary of latest performance metrics."""

    last_run: Optional[str] = None
    git_commit: Optional[str] = None

    # Key benchmarks (in seconds)
    fft_cpu_512: Optional[float] = None
    fft_gpu_512: Optional[float] = None
    fft_cpu_2048: Optional[float] = None
    fft_gpu_2048: Optional[float] = None
    gridding_cpu: Optional[float] = None
    visibility_correction_cpu: Optional[float] = None
    visibility_correction_gpu: Optional[float] = None

    # GPU speedups
    fft_512_speedup: Optional[float] = None
    fft_2048_speedup: Optional[float] = None
    vis_correction_speedup: Optional[float] = None


# ============================================================================
# Helper Functions
# ============================================================================


def get_benchmark_results_dir() -> Path:
    """Get the benchmark results directory."""
    # Check for custom path from environment
    custom_path = os.environ.get("DSA110_BENCHMARK_DIR")
    if custom_path:
        return Path(custom_path)

    # Default: backend/benchmarks/results
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    return backend_dir / "benchmarks" / "results"


def load_latest_benchmark() -> Optional[Dict[str, Any]]:
    """Load the most recent benchmark results."""
    results_dir = get_benchmark_results_dir()
    latest_file = results_dir / "latest.json"

    if latest_file.exists():
        try:
            with open(latest_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load latest benchmark: {e}")
            return None

    # Fall back to most recent timestamped file
    result_files = sorted(results_dir.glob("benchmark_*.json"))
    if result_files:
        try:
            with open(result_files[-1], encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    return None


def extract_timing(
    data: Dict[str, Any], suite: str, cls: str, method: str
) -> Optional[float]:
    """Extract a specific timing from benchmark data."""
    try:
        return data["benchmarks"][suite][cls][method]["mean"]
    except (KeyError, TypeError):
        return None


# ============================================================================
# Import for GPU monitoring (lazy)
# ============================================================================

import os


# ============================================================================
# Routes
# ============================================================================


@router.get("/benchmarks", response_model=Dict[str, Any])
async def get_benchmark_results(
    limit: int = Query(default=10, ge=1, le=100),
    suite: Optional[str] = None,
):
    """Get recent benchmark results.

    Returns historical benchmark data for trend visualization.
    """
    results_dir = get_benchmark_results_dir()

    if not results_dir.exists():
        return {"error": "No benchmark results found", "results": []}

    # Get timestamped result files
    result_files = sorted(results_dir.glob("benchmark_*.json"))[-limit:]

    results = []
    for result_file in result_files:
        try:
            with open(result_file, encoding="utf-8") as f:
                data = json.load(f)

            # Filter by suite if specified
            if suite and suite in data.get("benchmarks", {}):
                filtered_data = {
                    "system": data.get("system", {}),
                    "benchmarks": {suite: data["benchmarks"][suite]},
                }
                results.append(filtered_data)
            elif not suite:
                results.append(data)

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load {result_file}: {e}")

    return {
        "results": results,
        "count": len(results),
        "results_dir": str(results_dir),
    }


@router.get("/summary", response_model=PerformanceSummary)
async def get_performance_summary():
    """Get summary of latest performance metrics.

    Returns key benchmark timings and GPU speedups.
    """
    data = load_latest_benchmark()

    if not data:
        return PerformanceSummary()

    summary = PerformanceSummary(
        last_run=data.get("system", {}).get("timestamp"),
        git_commit=data.get("system", {}).get("git_commit"),
    )

    # Extract key timings
    summary.fft_cpu_512 = extract_timing(data, "gpu", "GPUTimeSuite", "time_fft2_cpu_512")
    summary.fft_gpu_512 = extract_timing(data, "gpu", "GPUTimeSuite", "time_fft2_gpu_512")
    summary.fft_cpu_2048 = extract_timing(data, "gpu", "GPUTimeSuite", "time_fft2_cpu_2048")
    summary.fft_gpu_2048 = extract_timing(data, "gpu", "GPUTimeSuite", "time_fft2_gpu_2048")
    summary.gridding_cpu = extract_timing(
        data, "imaging", "SyntheticTimeSuite", "time_gridding_vectorized_cpu"
    )
    summary.visibility_correction_cpu = extract_timing(
        data, "gpu", "GPUTimeSuite", "time_vis_correction_cpu"
    )
    summary.visibility_correction_gpu = extract_timing(
        data, "gpu", "GPUTimeSuite", "time_vis_correction_gpu"
    )

    # Calculate speedups
    if summary.fft_cpu_512 and summary.fft_gpu_512 and summary.fft_gpu_512 > 0:
        summary.fft_512_speedup = round(summary.fft_cpu_512 / summary.fft_gpu_512, 1)

    if summary.fft_cpu_2048 and summary.fft_gpu_2048 and summary.fft_gpu_2048 > 0:
        summary.fft_2048_speedup = round(summary.fft_cpu_2048 / summary.fft_gpu_2048, 1)

    if (
        summary.visibility_correction_cpu
        and summary.visibility_correction_gpu
        and summary.visibility_correction_gpu > 0
    ):
        summary.vis_correction_speedup = round(
            summary.visibility_correction_cpu / summary.visibility_correction_gpu, 1
        )

    return summary


@router.get("/gpus", response_model=GPUStatus)
async def get_gpu_status():
    """Get current GPU utilization and health.

    Returns memory usage, utilization, temperature for all GPUs.
    """
    try:
        import pynvml

        pynvml.nvmlInit()
    except (ImportError, Exception) as e:
        # Try CuPy as fallback for basic info
        try:
            import cupy as cp

            n_gpus = cp.cuda.runtime.getDeviceCount()
            gpus = []
            for i in range(n_gpus):
                with cp.cuda.Device(i):
                    mem_info = cp.cuda.Device(i).mem_info
                    props = cp.cuda.runtime.getDeviceProperties(i)
                    name = props["name"]
                    if isinstance(name, bytes):
                        name = name.decode()

                    gpus.append(
                        GPUInfo(
                            id=i,
                            name=name,
                            memory_total_gb=round(mem_info[1] / 1e9, 2),
                            memory_free_gb=round(mem_info[0] / 1e9, 2),
                            memory_used_gb=round((mem_info[1] - mem_info[0]) / 1e9, 2),
                        )
                    )

            return GPUStatus(available=True, gpus=gpus)

        except Exception as e2:
            return GPUStatus(available=False, error=str(e2))

    try:
        n_gpus = pynvml.nvmlDeviceGetCount()
        gpus = []

        for i in range(n_gpus):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode()

            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )

            try:
                power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # mW to W
            except pynvml.NVMLError:
                power = None

            gpus.append(
                GPUInfo(
                    id=i,
                    name=name,
                    memory_total_gb=round(mem.total / 1e9, 2),
                    memory_used_gb=round(mem.used / 1e9, 2),
                    memory_free_gb=round(mem.free / 1e9, 2),
                    utilization_gpu=util.gpu,
                    utilization_memory=util.memory,
                    temperature_c=temp,
                    power_draw_w=round(power, 1) if power else None,
                )
            )

        pynvml.nvmlShutdown()
        return GPUStatus(available=True, gpus=gpus)

    except Exception as e:
        return GPUStatus(available=False, error=str(e))


@router.get("/trends")
async def get_performance_trends(
    metric: str = Query(default="fft_gpu_2048"),
    limit: int = Query(default=30, ge=1, le=100),
):
    """Get performance trends for a specific metric over time.

    Returns data suitable for time series visualization.
    """
    results_dir = get_benchmark_results_dir()

    if not results_dir.exists():
        return {"error": "No benchmark results found", "data": []}

    result_files = sorted(results_dir.glob("benchmark_*.json"))[-limit:]

    # Metric mapping to data path
    metric_paths = {
        "fft_cpu_512": ("gpu", "GPUTimeSuite", "time_fft2_cpu_512"),
        "fft_gpu_512": ("gpu", "GPUTimeSuite", "time_fft2_gpu_512"),
        "fft_cpu_2048": ("gpu", "GPUTimeSuite", "time_fft2_cpu_2048"),
        "fft_gpu_2048": ("gpu", "GPUTimeSuite", "time_fft2_gpu_2048"),
        "gridding_cpu": ("imaging", "SyntheticTimeSuite", "time_gridding_vectorized_cpu"),
        "vis_correction_cpu": ("gpu", "GPUTimeSuite", "time_vis_correction_cpu"),
        "vis_correction_gpu": ("gpu", "GPUTimeSuite", "time_vis_correction_gpu"),
        "calibration_fft": ("calibration", "SyntheticTimeSuite", "time_fft_channelization"),
    }

    if metric not in metric_paths:
        return {
            "error": f"Unknown metric: {metric}",
            "available_metrics": list(metric_paths.keys()),
        }

    suite, cls, method = metric_paths[metric]
    data_points = []

    for result_file in result_files:
        try:
            with open(result_file, encoding="utf-8") as f:
                data = json.load(f)

            timestamp = data.get("system", {}).get("timestamp")
            value = extract_timing(data, suite, cls, method)

            if value is not None:
                data_points.append(
                    {
                        "timestamp": timestamp,
                        "value": value,
                        "commit": data.get("system", {}).get("git_commit"),
                    }
                )

        except (json.JSONDecodeError, OSError):
            continue

    return {
        "metric": metric,
        "unit": "seconds",
        "data": data_points,
    }
