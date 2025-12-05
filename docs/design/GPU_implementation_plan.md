# DSA-110 Continuum Imaging Pipeline: GPU Acceleration Implementation Plan

**Date**: December 2, 2025  
**Version**: 2.0 - Architecture-Verified  
**Target**: 12-month phased implementation  
**Primary Goal**: 10-20x performance improvement via GPU acceleration

---

## Executive Summary

### Current Architecture (Verified)

**Database Structure**:

- **Unified pipeline database**: `/data/dsa110-contimg/state/db/pipeline.sqlite3`
  - Products, calibration registry, HDF5 metadata, ingest tracking all in one SQLite database
  - Managed via SQLAlchemy with WAL mode for concurrent access
  - Session factories in `backend/src/dsa110_contimg/database/session.py`

**API Structure**:

- **Single-file FastAPI app**: `backend/src/dsa110_contimg/api/app.py` (~700 lines)
- Routers imported from `routes/` module
- Health check at `/api/health` and `/api/v1/health`
- Prometheus metrics at `/metrics`

**Calibration Management**:

- **Filesystem-based discovery**: `calibration/caltables.py`
- Tables stored alongside MS files with naming convention: `{ms_base}*{k|bp|g}cal`
- Latest tables discovered via `glob` + modification time sorting
- No centralized calibration registry currently

**Processing Model**:

- Sequential processing (no worker pool architecture)
- CASA tasks spawned as subprocesses
- Monitoring via log file tracking

### Expected Outcomes (12 months)

| Metric                 | Current     | Target        | Improvement    |
| ---------------------- | ----------- | ------------- | -------------- |
| **Calibration time**   | ~41s        | ~4s           | 10x            |
| **Imaging time**       | ~60s        | ~6s           | 10x            |
| **RFI detection**      | Minimal     | Comprehensive | New capability |
| **Overall throughput** | ~28 MS/hour | ~360 MS/hour  | 13x            |
| **GPU utilization**    | 0%          | 70-90%        | Full usage     |
| **Data quality**       | Manual QA   | Automated     | Proactive      |

---

## Phase 1: Foundation & Quick Wins (Months 1-3)

**Goal**: Establish performance monitoring, GPU infrastructure, and improve calibration discovery.

### 1.1 Performance Monitoring with casabench (Weeks 1-4)

#### Setup Infrastructure

**Create benchmark directory**:

mkdir -p backend/benchmarks

**Install ASV**:

pip install asv psutil pynvml

**Configure ASV** (`backend/benchmarks/asv.conf.json`):

{
"version": 1,
"project": "dsa110-contimg",
"project_url": "https://github.com/dsa110/dsa110-contimg",
"repo": "..",
"branches": ["main"],
"environment_type": "virtualenv",
"pythons": ["3.10"],
"matrix": {
"pip+casatasks": ["6.6.4"]
},
"benchmark_dir": "benchmarks",
"results_dir": "results",
"html_dir": "html"
}

#### Benchmark Suite

**Calibration benchmarks** (`backend/benchmarks/bench_calibration.py`):

"""Calibration performance benchmarks"""
import os
from pathlib import Path

class BandpassCalibration:
"""Benchmark bandpass calibration"""

    timeout = 300.0

    def setup(self):
        self.ms = "/data/dsa110-contimg/test_data/cal_sample.ms"
        if not os.path.exists(self.ms):
            raise RuntimeError(f"Test MS not found: {self.ms}")

    def time_bandpass_solve(self):
        """Time bandpass calibration (baseline: ~31s)"""
        from dsa110_contimg.calibration.calibration import run_bandpass
        run_bandpass(self.ms, field="0", refant="24")

    def peakmem_bandpass_solve(self):
        """Track peak memory during calibration"""
        self.time_bandpass_solve()

**Imaging benchmarks** (`backend/benchmarks/bench_imaging.py`):

"""Imaging performance benchmarks"""

class TCLEANImaging:
"""Benchmark CASA tclean imaging"""

    timeout = 600.0

    def setup(self):
        self.ms = "/data/dsa110-contimg/test_data/imaging_sample.ms"

    def time_tclean_dirty(self):
        """Time dirty image creation (baseline: ~30s)"""
        from casatasks import tclean
        tclean(
            vis=self.ms,
            imagename="/tmp/bench_dirty",
            imsize=512,
            cell='12arcsec',
            niter=0
        )

    def time_tclean_clean(self):
        """Time cleaned image (baseline: ~60s)"""
        from casatasks import tclean
        tclean(
            vis=self.ms,
            imagename="/tmp/bench_clean",
            imsize=512,
            cell='12arcsec',
            niter=100
        )

**HDF5 conversion benchmarks** (`backend/benchmarks/bench_conversion.py`):

"""HDF5→MS conversion benchmarks"""

class HDF5Conversion:
"""Benchmark HDF5 to MS conversion"""

    timeout = 300.0

    def setup(self):
        self.hdf5 = "/data/dsa110-contimg/test_data/sample.hdf5"

    def time_hdf5_to_ms(self):
        """Time conversion (baseline: varies)"""
        from dsa110_contimg.conversion.hdf5_to_ms import hdf5_to_ms
        hdf5_to_ms(self.hdf5, "/tmp/bench_output")

#### API Integration

**Add to `backend/src/dsa110_contimg/api/app.py`** (after line 200, in main app creation):

@app.get("/api/v1/performance/benchmarks")
async def get_benchmark_results(
benchmark: Optional[str] = None,
limit: int = 30
):
"""Return benchmark results for dashboard visualization"""
from pathlib import Path
import json
from datetime import datetime

    results_dir = Path(__file__).parent.parent.parent.parent / "benchmarks" / "results"

    if not results_dir.exists():
        return {"error": "No benchmark results found", "series": []}

    machine_dirs = [d for d in results_dir.iterdir() if d.is_dir()]
    if not machine_dirs:
        return {"error": "No machine results", "series": []}

    machine_dir = machine_dirs[0]
    result_files = sorted(machine_dir.glob("*.json"))[-limit:]

    series_data = {}

    for result_file in result_files:
        with open(result_file) as f:
            data = json.load(f)

        commit_date = datetime.fromtimestamp(data['date'] / 1000)

        for bench_name, bench_result in data['results'].items():
            if benchmark and benchmark not in bench_name:
                continue

            if bench_result is None or bench_result.get('result') is None:
                continue

            if bench_name not in series_data:
                series_data[bench_name] = {'name': bench_name, 'data': []}

            timing = bench_result['result']
            if isinstance(timing, list):
                timing = timing[len(timing) // 2]

            series_data[bench_name]['data'].append({
                'date': commit_date.isoformat(),
                'time': timing,
                'commit': data['commit_hash'][:8]
            })

    return {
        'series': list(series_data.values()),
        'machine': machine_dir.name
    }

@app.get("/api/v1/performance/summary")
async def get_performance_summary():
"""Latest performance metrics summary"""
from pathlib import Path
import json
from datetime import datetime

    results_dir = Path(__file__).parent.parent.parent.parent / "benchmarks" / "results"

    machine_dirs = [d for d in results_dir.iterdir() if d.is_dir()]
    if not machine_dirs:
        return {"error": "No results found"}

    latest_result = sorted(machine_dirs[0].glob("*.json"))[-1]

    with open(latest_result) as f:
        data = json.load(f)

    summary = {
        'calibration_time': None,
        'imaging_time': None,
        'conversion_time': None,
        'last_run': datetime.fromtimestamp(data['date'] / 1000).isoformat()
    }

    for bench_name, result in data['results'].items():
        if result and result.get('result'):
            timing = result['result']
            if isinstance(timing, list):
                timing = timing[len(timing) // 2]

            if 'bandpass' in bench_name:
                summary['calibration_time'] = timing
            elif 'tclean' in bench_name:
                summary['imaging_time'] = timing
            elif 'hdf5' in bench_name:
                summary['conversion_time'] = timing

    return summary

#### Automated Benchmarking

**Add to crontab** on production server:

# /etc/cron.d/dsa110-benchmarks

0 2 \* \* \* dsa110 cd /data/dsa110-contimg/backend/benchmarks && asv run HEAD^! --machine ovro-lwa1

**Frontend component** (`frontend/src/components/health/PerformanceTrends.tsx`):

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';

export function PerformanceTrends() {
const { data, isLoading } = useQuery({
queryKey: ['performance', 'benchmarks'],
queryFn: async () => {
const response = await fetch('/api/v1/performance/benchmarks');
return response.json();
},
refetchInterval: 300000,
});

if (isLoading) return <div className="animate-pulse h-64 bg-gray-200 rounded" />;

const option = {
title: { text: 'Pipeline Performance Trends', left: 'center' },
tooltip: {
trigger: 'axis',
formatter: (params: any) => {
const point = params[0];
return `Date: ${new Date(point.data.date).toLocaleDateString()}<br/>Time: ${point.data.time.toFixed(2)}s<br/>Commit: ${point.data.commit}`;
},
},
legend: { data: data?.series.map((s: any) => s.name) || [], top: 30 },
xAxis: { type: 'time', name: 'Date' },
yAxis: { type: 'value', name: 'Time (seconds)' },
series: data?.series.map((s: any) => ({
name: s.name,
type: 'line',
data: s.data.map((d: any) => [d.date, d.time]),
smooth: true,
})) || [],
};

return (
<div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
<ReactECharts option={option} style={{ height: '400px' }} />
</div>
);
}

**Add to existing Health Dashboard** (`frontend/src/pages/HealthDashboardPage.tsx`):

import { PerformanceTrends } from '../components/health/PerformanceTrends';

// Add after existing panels

<div className="mt-6">
  <PerformanceTrends />
</div>

**Deliverable**: Performance baseline established, nightly benchmarks running, trends visible in dashboard.

---

### 1.2 GPU Infrastructure (Weeks 3-6)

#### Environment Setup

**Install GPU stack**:

# Verify CUDA

nvidia-smi

# Install GPU packages

conda install -c conda-forge numba cudatoolkit=11.8
pip install cupy-cuda11x dask-cuda pynvml

**Verification script** (`backend/scripts/verify_gpu.py`):

#!/usr/bin/env python3
"""Verify GPU setup for DSA-110 pipeline"""

import sys

def check_cuda():
try:
import cupy as cp
print(f"✅ CuPy {cp.**version**}")
n_gpus = cp.cuda.runtime.getDeviceCount()
print(f"✅ {n_gpus} GPU(s) detected")

        for i in range(n_gpus):
            props = cp.cuda.runtime.getDeviceProperties(i)
            print(f"\nGPU {i}: {props['name'].decode()}")
            print(f"  Memory: {props['totalGlobalMem'] / 1e9:.2f} GB")

        return True
    except Exception as e:
        print(f"❌ CUDA error: {e}")
        return False

def test_gpu_operation():
try:
import cupy as cp
x = cp.ones((1000, 1000))
y = x @ x
print("✅ GPU matrix multiply successful")
return True
except Exception as e:
print(f"❌ GPU operation failed: {e}")
return False

if **name** == '**main**':
checks = [
("CUDA availability", check_cuda),
("GPU operation", test_gpu_operation),
]

    results = [check() for _, check in checks]

    if all(results):
        print("\n🎉 GPU environment ready!")
        sys.exit(0)
    else:
        print("\n⚠️  Some checks failed")
        sys.exit(1)

**Run verification**:

python backend/scripts/verify_gpu.py

#### GPU Monitoring

**Add to `backend/src/dsa110_contimg/api/app.py`** (after performance endpoints):

try:
import pynvml
GPU_AVAILABLE = True
pynvml.nvmlInit()
except (ImportError, pynvml.NVMLError):
GPU_AVAILABLE = False

@app.get("/api/v1/health/gpus")
async def get_gpu_status():
"""Get current GPU utilization and health"""
if not GPU_AVAILABLE:
return {"error": "GPU monitoring not available", "gpus": []}

    try:
        n_gpus = pynvml.nvmlDeviceGetCount()
        gpus = []

        for i in range(n_gpus):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

            gpus.append({
                'id': i,
                'name': pynvml.nvmlDeviceGetName(handle).decode(),
                'utilization_gpu': utilization.gpu,
                'utilization_memory': utilization.memory,
                'memory_used_gb': memory_info.used / 1e9,
                'memory_total_gb': memory_info.total / 1e9,
                'memory_free_gb': memory_info.free / 1e9,
                'temperature_c': pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU
                ),
                'power_draw_w': pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0,
                'power_limit_w': pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0,
            })

        return {"gpus": gpus}
    except Exception as e:
        return {"error": str(e), "gpus": []}

**Frontend component** (`frontend/src/components/health/GPUStatus.tsx`):

import React from 'react';
import { useQuery } from '@tanstack/react-query';

interface GPU {
id: number;
name: string;
utilization_gpu: number;
memory_used_gb: number;
memory_total_gb: number;
temperature_c: number;
power_draw_w: number;
}

function GPUCard({ gpu }: { gpu: GPU }) {
const memPercent = (gpu.memory_used_gb / gpu.memory_total_gb) \* 100;

return (
<div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
<h3 className="text-lg font-semibold mb-4">GPU {gpu.id}: {gpu.name}</h3>

      {/* GPU Utilization */}
      <div className="mb-3">
        <div className="flex justify-between text-sm mb-1">
          <span>GPU Utilization</span>
          <span>{gpu.utilization_gpu}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${gpu.utilization_gpu}%` }} />
        </div>
      </div>

      {/* Memory */}
      <div className="mb-3">
        <div className="flex justify-between text-sm mb-1">
          <span>Memory</span>
          <span>{gpu.memory_used_gb.toFixed(1)} / {gpu.memory_total_gb.toFixed(1)} GB</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div className={`h-2 rounded-full ${memPercent > 90 ? 'bg-red-600' : 'bg-green-600'}`} style={{ width: `${memPercent}%` }} />
        </div>
      </div>

      {/* Temp & Power */}
      <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t">
        <div>
          <div className="text-xs text-gray-500">Temperature</div>
          <div className={`text-2xl font-bold ${gpu.temperature_c > 80 ? 'text-red-600' : 'text-green-600'}`}>
            {gpu.temperature_c}°C
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Power</div>
          <div className="text-2xl font-bold">{gpu.power_draw_w.toFixed(0)}W</div>
        </div>
      </div>
    </div>

);
}

export function GPUStatus() {
const { data } = useQuery({
queryKey: ['gpu', 'status'],
queryFn: async () => {
const response = await fetch('/api/v1/health/gpus');
return response.json();
},
refetchInterval: 2000,
});

return (
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
{data?.gpus?.map((gpu: GPU) => <GPUCard key={gpu.id} gpu={gpu} />)}
</div>
);
}

**Add to Health Dashboard**:

<div className="mt-6">
  <h2 className="text-xl font-bold mb-4">GPU Resources</h2>
  <GPUStatus />
</div>

**Deliverable**: GPU environment verified, real-time monitoring in dashboard.

---

### 1.3 Improve Calibration Discovery (Weeks 5-8)

**Problem**: Current `caltables.py` uses simple glob matching, no time-based search.

**Solution**: Add bidirectional time-based calibration discovery.

**Update `backend/src/dsa110_contimg/calibration/caltables.py`**:

"""Calibration table discovery utilities."""

from **future** import annotations

import glob
import os
import json
from pathlib import Path
from typing import Dict, Optional, List
from astropy.time import Time
import logging

log = logging.getLogger(**name**)

def discover_caltables(ms_path: str) -> Dict[str, Optional[str]]:
"""Discover calibration tables associated with an MS.

    (Existing implementation - unchanged)
    """
    if not os.path.exists(ms_path):
        return {"k": None, "bp": None, "g": None}

    ms_dir = os.path.dirname(ms_path)
    ms_base = os.path.basename(ms_path).replace(".ms", "")

    k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
    bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
    g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")

    k_tables = sorted(glob.glob(k_pattern), key=os.path.getmtime, reverse=True)
    bp_tables = sorted(glob.glob(bp_pattern), key=os.path.getmtime, reverse=True)
    g_tables = sorted(glob.glob(g_pattern), key=os.path.getmtime, reverse=True)

    return {
        "k": k_tables[0] if k_tables else None,
        "bp": bp_tables[0] if bp_tables else None,
        "g": g_tables[0] if g_tables else None,
    }

def find_nearest_calibration(
target_mjd: float,
calibration_dir: Path,
\*,
search_window_hours: float = 24.0,
) -> Optional[Dict]:
"""Find calibration nearest to target MJD with bidirectional search.

    Searches all calibration directories within time window and returns
    the closest calibration tables.

    Args:
        target_mjd: MJD of target observation
        calibration_dir: Root directory containing calibration tables
        search_window_hours: Maximum time difference (default: ±24h)

    Returns:
        Dictionary with calibration info or None if not found
    """
    search_window_mjd = search_window_hours / 24.0
    candidates = []

    # Search calibration directory for calibrator MS files
    for ms_path in calibration_dir.glob("*.ms"):
        try:
            # Extract MJD from MS metadata or filename
            # For now, use modification time as proxy
            mtime = os.path.getmtime(ms_path)
            cal_mjd = Time(mtime, format='unix').mjd

            # Check time window
            time_diff = abs(cal_mjd - target_mjd)
            if time_diff > search_window_mjd:
                continue

            # Discover associated calibration tables
            tables = discover_caltables(str(ms_path))

            # Check if we have required tables
            if not tables['bp'] or not tables['g']:
                log.debug(f"Incomplete calibration for {ms_path}")
                continue

            candidates.append({
                'ms_path': str(ms_path),
                'mjd': cal_mjd,
                'time_diff_hours': time_diff * 24.0,
                'tables': tables
            })

        except Exception as e:
            log.debug(f"Error processing {ms_path}: {e}")
            continue

    if not candidates:
        log.warning(
            f"No calibrations within ±{search_window_hours}h of MJD {target_mjd}"
        )
        return None

    # Sort by time difference
    candidates.sort(key=lambda x: x['time_diff_hours'])
    best = candidates[0]

    log.info(
        f"Selected calibration from MJD {best['mjd']:.4f} "
        f"(Δt = {best['time_diff_hours']:.1f} hours)"
    )

    # Alert if stale
    if best['time_diff_hours'] > 12.0:
        log.warning(
            f"Using calibration from {best['time_diff_hours']:.1f} hours ago"
        )

    return best

def get_applylist_for_mjd(
target_mjd: float,
calibration_dir: Path,
\*\*kwargs
) -> List[str]:
"""Get ordered list of calibration tables for target MJD.

    Args:
        target_mjd: MJD of target observation
        calibration_dir: Root calibration directory

    Returns:
        List of calibration table paths to apply
    """
    result = find_nearest_calibration(target_mjd, calibration_dir, **kwargs)

    if result is None:
        return []

    # Return ordered list
    tables = []
    if result['tables']['k']:
        tables.append(result['tables']['k'])
    if result['tables']['bp']:
        tables.append(result['tables']['bp'])
    if result['tables']['g']:
        tables.append(result['tables']['g'])

    return tables

**Add calibration health monitoring** to API (`backend/src/dsa110_contimg/api/app.py`):

@app.get("/api/v1/health/calibration")
async def check_calibration_health():
"""Check calibration freshness and availability"""
from pathlib import Path
from astropy.time import Time

    calibration_dir = Path(os.getenv('CALIBRATION_DIR', '/data/dsa110-contimg/calibrations'))

    if not calibration_dir.exists():
        return {
            'healthy': False,
            'message': f'Calibration directory not found: {calibration_dir}',
            'severity': 'critical'
        }

    # Find most recent calibration MS
    ms_files = list(calibration_dir.glob("*.ms"))
    if not ms_files:
        return {
            'healthy': False,
            'message': 'No calibration MS files found',
            'severity': 'critical'
        }

    # Get most recent
    latest_ms = max(ms_files, key=os.path.getmtime)
    latest_mtime = os.path.getmtime(latest_ms)
    latest_mjd = Time(latest_mtime, format='unix').mjd

    # Calculate age
    now_mjd = Time.now().mjd
    age_hours = (now_mjd - latest_mjd) * 24.0

    threshold = 24.0

    if age_hours > threshold:
        return {
            'healthy': False,
            'message': f'Last calibration is {age_hours:.1f} hours old',
            'severity': 'warning',
            'last_cal_ms': latest_ms.name,
            'age_hours': age_hours
        }

    return {
        'healthy': True,
        'message': f'Recent calibration available ({age_hours:.1f} hours old)',
        'last_cal_ms': latest_ms.name,
        'age_hours': age_hours
    }

**Deliverable**: Bidirectional calibration search, staleness monitoring in Health Dashboard.

---

## Phase 2: GPU Acceleration Core (Months 4-7)

**Goal**: Implement GPU-accelerated RFI detection, gridding, and calibration.

### 2.1 GPU RFI Detection (Weeks 9-12)

**Create new module** (`backend/src/dsa110_contimg/rfi/`):

mkdir -p backend/src/dsa110_contimg/rfi
touch backend/src/dsa110_contimg/rfi/**init**.py

**Implementation** (`backend/src/dsa110_contimg/rfi/gpu_detection.py`):

"""GPU-accelerated RFI detection using CuPy"""

import numpy as np
import cupy as cp
from numba import cuda
import logging
from typing import Dict

log = logging.getLogger(**name**)

@cuda.jit
def detect_outliers_kernel(vis_real, vis_imag, flags, threshold):
"""CUDA kernel for RFI detection"""
idx = cuda.grid(1)

    if idx < vis_real.size:
        amplitude = (vis_real[idx]**2 + vis_imag[idx]**2)**0.5
        if amplitude > threshold:
            flags[idx] = 1

def gpu_rfi_detection(
ms_path: str,
\*,
threshold: float = 5.0,
gpu_id: int = 0,
chunk_size: int = 10_000_000
) -> Dict:
"""GPU-accelerated RFI detection for MS

    Args:
        ms_path: Path to measurement set
        threshold: Detection threshold in MAD units
        gpu_id: GPU device ID
        chunk_size: Visibilities per chunk

    Returns:
        Flagging statistics
    """
    from casatools import table as tb

    log.info(f"GPU RFI detection on {ms_path} (GPU {gpu_id})")

    with cp.cuda.Device(gpu_id):
        t = tb()
        t.open(ms_path, nomodify=False)

        data = t.getcol('DATA')
        n_total = np.prod(data.shape[:2])

        total_flagged = 0

        # Process in chunks
        for start in range(0, data.shape[0], chunk_size // data.shape[1]):
            end = min(start + chunk_size // data.shape[1], data.shape[0])

            chunk = t.getcol('DATA', startrow=start, nrow=end - start)
            vis_flat = chunk.reshape(-1)

            # Transfer to GPU
            vis_gpu = cp.asarray(vis_flat)

            # Compute threshold on GPU
            median = cp.median(cp.abs(vis_gpu))
            mad = cp.median(cp.abs(cp.abs(vis_gpu) - median))
            thresh_value = float(median + threshold * mad)

            # Detect RFI
            flags_gpu = cp.zeros(vis_flat.shape, dtype=cp.uint8)

            threads = 256
            blocks = (vis_flat.size + threads - 1) // threads
            detect_outliers_kernel[blocks, threads](
                vis_gpu.real, vis_gpu.imag, flags_gpu, thresh_value
            )

            n_flagged = int(cp.sum(flags_gpu))
            total_flagged += n_flagged

            # Update MS flags
            flags_cpu = cp.asnumpy(flags_gpu).reshape(chunk.shape)
            existing = t.getcol('FLAG', startrow=start, nrow=end - start)
            combined = existing | flags_cpu.astype(bool)
            t.putcol('FLAG', combined, startrow=start, nrow=end - start)

            # Cleanup
            del vis_gpu, flags_gpu
            cp.get_default_memory_pool().free_all_blocks()

        t.close()

        flag_percent = (total_flagged / n_total) * 100

        log.info(f"Flagged {total_flagged:,} / {n_total:,} ({flag_percent:.2f}%)")

        return {
            'total_vis': int(n_total),
            'flagged_vis': int(total_flagged),
            'flag_percent': float(flag_percent),
            'threshold': threshold,
            'gpu_id': gpu_id
        }

**Note**: Integration with streaming converter will be covered in Phase 3 (state machine refactor).

**Benchmark** (`backend/benchmarks/bench_rfi.py`):

class GPURFIDetection:
"""Benchmark GPU RFI detection"""

    timeout = 120.0

    def setup(self):
        self.ms = "/data/dsa110-contimg/test_data/rfi_sample.ms"

    def time_gpu_rfi(self):
        """Time GPU RFI detection"""
        from dsa110_contimg.rfi.gpu_detection import gpu_rfi_detection
        gpu_rfi_detection(self.ms, gpu_id=0)

**Deliverable**: GPU RFI detection module, benchmarked.

---

### 2.2 GPU Gridding (Weeks 13-16)

**Create imaging GPU modules**:

touch backend/src/dsa110_contimg/imaging/gpu_gridding.py
touch backend/src/dsa110_contimg/imaging/gpu_tclean.py

**GPU gridding** (`backend/src/dsa110_contimg/imaging/gpu_gridding.py`):

"""GPU-accelerated visibility gridding"""

import cupy as cp
import numpy as np
from numba import cuda
import logging

log = logging.getLogger(**name**)

@cuda.jit
def grid_kernel(uvw, vis, weights, grid_size, cell_size, grid):
"""CUDA gridding kernel (simple nearest-neighbor)"""
idx = cuda.grid(1)

    if idx < uvw.shape[0]:
        u = uvw[idx, 0]
        v = uvw[idx, 1]

        u_pix = int((u / cell_size) + grid_size / 2)
        v_pix = int((v / cell_size) + grid_size / 2)

        if 0 <= u_pix < grid_size and 0 <= v_pix < grid_size:
            cuda.atomic.add(grid, (v_pix, u_pix), vis[idx] * weights[idx])

def gpu_grid_visibilities(
uvw: np.ndarray,
vis: np.ndarray,
weights: np.ndarray,
image_size: int,
cell_size: float,
\*,
gpu_id: int = 0
) -> np.ndarray:
"""Grid visibilities on GPU

    Args:
        uvw: (N, 3) UVW coordinates
        vis: (N,) complex visibilities
        weights: (N,) weights
        image_size: Image size in pixels
        cell_size: Cell size in radians
        gpu_id: GPU device ID

    Returns:
        (image_size, image_size) complex grid
    """
    with cp.cuda.Device(gpu_id):
        # Transfer to GPU
        uvw_gpu = cp.asarray(uvw, dtype=cp.float32)
        vis_gpu = cp.asarray(vis, dtype=cp.complex64)
        weights_gpu = cp.asarray(weights, dtype=cp.float32)

        # Allocate grid
        grid_gpu = cp.zeros((image_size, image_size), dtype=cp.complex64)

        # Launch kernel
        threads = 256
        blocks = (vis.size + threads - 1) // threads

        grid_kernel[blocks, threads](
            uvw_gpu, vis_gpu, weights_gpu, image_size, cell_size, grid_gpu
        )

        # FFT to image plane
        image_gpu = cp.fft.fft2(grid_gpu)
        image_gpu = cp.fft.fftshift(image_gpu)

        # Transfer back
        image = cp.asnumpy(image_gpu)

        # Cleanup
        del uvw_gpu, vis_gpu, weights_gpu, grid_gpu, image_gpu
        cp.get_default_memory_pool().free_all_blocks()

        return image

**GPU tclean wrapper** (`backend/src/dsa110_contimg/imaging/gpu_tclean.py`):

"""GPU-accelerated imaging with CASA deconvolution"""

from pathlib import Path
import numpy as np
import logging
from .gpu_gridding import gpu_grid_visibilities

log = logging.getLogger(**name**)

def gpu_image_ms(
ms_path: str,
imagename: str,
\*,
imsize: int = 512,
cell: str = '12arcsec',
gpu_id: int = 0,
\*\*tclean_kwargs
) -> Path:
"""Create image using GPU gridding + CASA deconvolution

    Args:
        ms_path: Path to MS
        imagename: Output image prefix
        imsize: Image size
        cell: Cell size
        gpu_id: GPU device ID
        **tclean_kwargs: Additional tclean parameters

    Returns:
        Path to created image
    """
    from casatools import table as tb
    from casatasks import tclean

    # Parse cell size
    cell_arcsec = float(cell.replace('arcsec', ''))
    cell_rad = np.deg2rad(cell_arcsec / 3600.0)

    log.info(f"GPU imaging {ms_path} (GPU {gpu_id})")

    # Read visibilities
    t = tb()
    t.open(ms_path)
    data = t.getcol('DATA')
    uvw = t.getcol('UVW')
    weight = t.getcol('WEIGHT_SPECTRUM')
    t.close()

    # Flatten
    vis_flat = data.reshape(-1)
    uvw_flat = uvw.reshape(-1, 3)
    weight_flat = weight.reshape(-1)

    # GPU gridding
    dirty = gpu_grid_visibilities(
        uvw_flat, vis_flat, weight_flat, imsize, cell_rad, gpu_id=gpu_id
    )

    # Save dirty image
    from casatools import image as ia
    dirty_path = f"{imagename}.dirty.gpu"
    ia_tool = ia()
    ia_tool.fromarray(dirty_path, np.abs(dirty))
    ia_tool.close()

    # CASA deconvolution
    log.info("Running CASA deconvolution...")
    tclean(
        vis=ms_path,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        startmodel=dirty_path,
        **tclean_kwargs
    )

    return Path(f"{imagename}.image")

**Benchmark** (`backend/benchmarks/bench_imaging.py` - add to existing):

class GPUImaging:
"""Benchmark GPU imaging"""

    params = ['cpu', 'gpu_0', 'gpu_1']
    timeout = 600.0

    def setup(self, backend):
        self.ms = "/data/dsa110-contimg/test_data/imaging_sample.ms"

    def time_imaging(self, backend):
        if backend == 'cpu':
            from casatasks import tclean
            tclean(vis=self.ms, imagename="/tmp/cpu_test", imsize=512, cell='12arcsec', niter=100)
        else:
            gpu_id = int(backend.split('_')[1])
            from dsa110_contimg.imaging.gpu_tclean import gpu_image_ms
            gpu_image_ms(self.ms, "/tmp/gpu_test", imsize=512, gpu_id=gpu_id, niter=100)

**Deliverable**: GPU gridding and imaging, benchmarked against CPU.

---

### 2.3 GPU Calibration Solving (Weeks 17-20)

**Create GPU calibration module** (`backend/src/dsa110_contimg/calibration/gpu_solver.py`):

"""GPU-accelerated calibration solving"""

import cupy as cp
from cupyx.scipy.linalg import lstsq
import numpy as np
import logging

log = logging.getLogger(**name**)

def gpu_solve_gains(
vis: np.ndarray,
model: np.ndarray,
\*,
gpu_id: int = 0
) -> np.ndarray:
"""Solve for gains using GPU least-squares

    Solves: vis = gain * model

    Args:
        vis: (N_baseline, N_time, N_freq) observed
        model: (N_baseline, N_time, N_freq) model
        gpu_id: GPU device ID

    Returns:
        (N_antenna, N_time, N_freq) complex gains
    """
    with cp.cuda.Device(gpu_id):
        vis_gpu = cp.asarray(vis)
        model_gpu = cp.asarray(model)

        # Solve on GPU
        gains_gpu, _, _, _ = lstsq(model_gpu, vis_gpu)

        gains = cp.asnumpy(gains_gpu)

        del vis_gpu, model_gpu, gains_gpu
        cp.get_default_memory_pool().free_all_blocks()

        return gains

**Note**: Full integration requires caltable writing - beyond scope of initial implementation. This provides GPU matrix solving that can be integrated gradually.

**Deliverable**: GPU gain solving module.

---

## Phase 3: Production Hardening (Months 8-10)

**Goal**: Add state machine, automated QA, improve reliability.

### 3.1 State Machine (Weeks 21-24)

**Create database module** (`backend/src/dsa110_contimg/database/state_machine.py`):

"""Pipeline state machine with transaction safety"""

from enum import Enum
from pathlib import Path
import sqlite3
from typing import Optional
import logging
from .session import get_db_path

log = logging.getLogger(**name**)

class MSState(Enum):
"""MS processing states"""
PENDING = 'pending'
CONVERTING = 'converting'
CONVERTED = 'converted'
FLAGGING_RFI = 'flagging_rfi'
SOLVING_CAL = 'solving_cal'
APPLYING_CAL = 'applying_cal'
IMAGING = 'imaging'
DONE = 'done'
FAILED = 'failed'
ERROR = 'error'

class MSStateMachine:
"""Manage MS processing state"""

    TRANSITIONS = {
        MSState.PENDING: [MSState.CONVERTING, MSState.FAILED],
        MSState.CONVERTING: [MSState.CONVERTED, MSState.FAILED],
        MSState.CONVERTED: [MSState.FLAGGING_RFI, MSState.FAILED],
        MSState.FLAGGING_RFI: [MSState.SOLVING_CAL, MSState.APPLYING_CAL, MSState.FAILED],
        MSState.SOLVING_CAL: [MSState.DONE, MSState.FAILED],
        MSState.APPLYING_CAL: [MSState.IMAGING, MSState.FAILED],
        MSState.IMAGING: [MSState.DONE, MSState.FAILED],
        MSState.FAILED: [MSState.PENDING, MSState.ERROR],
        MSState.ERROR: [],
        MSState.DONE: [],
    }

    def __init__(self):
        self.db_path = get_db_path("pipeline")
        self._ensure_schema()

    def _ensure_schema(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ms_state (
                ms_path TEXT PRIMARY KEY,
                current_state TEXT NOT NULL,
                previous_state TEXT,
                transition_time REAL NOT NULL,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                checkpoint_data TEXT
            )
        """)
        conn.commit()
        conn.close()

    def get_state(self, ms_path: str) -> MSState:
        conn = sqlite3.connect(str(self.db_path))
        result = conn.execute(
            "SELECT current_state FROM ms_state WHERE ms_path = ?",
            (ms_path,)
        ).fetchone()
        conn.close()

        return MSState(result[0]) if result else MSState.PENDING

    def transition(self, ms_path: str, new_state: MSState, **kwargs):
        import time
        import json

        current = self.get_state(ms_path)

        if new_state not in self.TRANSITIONS.get(current, []):
            raise ValueError(f"Invalid: {current.value} → {new_state.value}")

        conn = sqlite3.connect(str(self.db_path))

        error_msg = kwargs.get('error_message')
        checkpoint = kwargs.get('checkpoint')
        checkpoint_json = json.dumps(checkpoint) if checkpoint else None

        conn.execute("""
            INSERT INTO ms_state
            (ms_path, current_state, previous_state, transition_time, error_message, checkpoint_data)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(ms_path) DO UPDATE SET
                previous_state = current_state,
                current_state = excluded.current_state,
                transition_time = excluded.transition_time,
                error_message = excluded.error_message,
                checkpoint_data = excluded.checkpoint_data
        """, (ms_path, new_state.value, current.value, time.time(), error_msg, checkpoint_json))

        conn.commit()
        conn.close()

        log.info(f"State: {ms_path}: {current.value} → {new_state.value}")

    def mark_failed(self, ms_path: str, error: Exception):
        self.transition(ms_path, MSState.FAILED, error_message=str(error))

    def can_retry(self, ms_path: str, max_retries: int = 3) -> bool:
        conn = sqlite3.connect(str(self.db_path))
        result = conn.execute(
            "SELECT retry_count, current_state FROM ms_state WHERE ms_path = ?",
            (ms_path,)
        ).fetchone()
        conn.close()

        if not result:
            return True

        retry_count, current_state = result
        return current_state != MSState.ERROR.value and retry_count < max_retries

    def reset_for_retry(self, ms_path: str):
        import time
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            UPDATE ms_state SET current_state = ?, retry_count = retry_count + 1, transition_time = ?
            WHERE ms_path = ?
        """, (MSState.PENDING.value, time.time(), ms_path))
        conn.commit()
        conn.close()

**Note**: Integration with streaming converter deferred - requires architectural refactor beyond scope of GPU implementation.

**Deliverable**: State machine infrastructure ready for integration.

---

### 3.2 Automated Calibration QA (Weeks 25-26)

**Create QA module** (`backend/src/dsa110_contimg/calibration/qa.py`):

"""Automated calibration quality assessment"""

import numpy as np
from pathlib import Path
from typing import Dict, List
import logging

log = logging.getLogger(**name**)

def compute_calibration_metrics(caltable_path: str) -> Dict:
"""Compute QA metrics for calibration table"""
from casatools import table as tb

    t = tb()
    t.open(caltable_path)

    gains = t.getcol('CPARAM')
    flags = t.getcol('FLAG')
    snr = t.getcol('SNR') if 'SNR' in t.colnames() else None

    t.close()

    metrics = {
        'caltable': caltable_path,
        'n_solutions': gains.size,
        'n_flagged': np.sum(flags),
        'flag_fraction': np.sum(flags) / flags.size,
        'mean_amplitude': float(np.mean(np.abs(gains[~flags]))),
        'std_amplitude': float(np.std(np.abs(gains[~flags]))),
        'median_phase_deg': float(np.median(np.angle(gains[~flags], deg=True))),
    }

    if snr is not None:
        metrics['median_snr'] = float(np.median(snr[~flags]))
        metrics['min_snr'] = float(np.min(snr[~flags]))

    return metrics

def assess_calibration_quality(
ms_path: str,
\*,
min_snr: float = 3.0,
max_flag_fraction: float = 0.3
) -> Dict:
"""Assess quality of calibration tables

    Args:
        ms_path: Path to calibrated MS
        min_snr: Minimum acceptable SNR
        max_flag_fraction: Maximum flagging fraction

    Returns:
        Assessment with pass/fail and warnings
    """
    from .caltables import discover_caltables

    tables = discover_caltables(ms_path)

    if not tables['bp'] or not tables['g']:
        return {
            'passed': False,
            'severity': 'error',
            'message': 'Missing required calibration tables',
            'tables': []
        }

    warnings = []
    failures = []
    metrics_list = []

    for cal_type, cal_path in tables.items():
        if not cal_path:
            continue

        metrics = compute_calibration_metrics(cal_path)
        metrics_list.append(metrics)

        # Check SNR
        if 'median_snr' in metrics and metrics['median_snr'] < min_snr:
            failures.append(
                f"{Path(cal_path).name}: Low SNR ({metrics['median_snr']:.1f})"
            )

        # Check flagging
        if metrics['flag_fraction'] > max_flag_fraction:
            warnings.append(
                f"{Path(cal_path).name}: High flagging ({metrics['flag_fraction']:.1%})"
            )

        # Check for non-finite
        if not np.isfinite(metrics['mean_amplitude']):
            failures.append(f"{Path(cal_path).name}: Non-finite amplitudes")

    passed = len(failures) == 0

    return {
        'passed': passed,
        'severity': 'success' if passed else 'error',
        'warnings': warnings,
        'failures': failures,
        'table_metrics': metrics_list,
        'summary': {
            'n_tables': len([t for t in tables.values() if t]),
            'n_warnings': len(warnings),
            'n_failures': len(failures)
        }
    }

**Add QA endpoint** (`backend/src/dsa110_contimg/api/app.py`):

@app.get("/api/v1/calibration/qa/recent")
async def get_recent_calibration_qa(limit: int = 10):
"""Get recent calibration QA results""" # Implementation requires QA results storage in database # Placeholder for now
return {"message": "QA tracking not yet implemented", "qa_results": []}

**Deliverable**: QA framework ready for integration.

---

## Phase 4: Interactive Analysis (Months 11-12)

### 4.1 JupyterHub Deployment (Weeks 27-28)

**Install on HPC cluster**:

conda create -n jupyterhub python=3.10
conda activate jupyterhub
conda install -c conda-forge jupyterhub jupyterlab
jupyterhub --generate-config

**Configure** (`jupyterhub_config.py`):

c.JupyterHub.bind_url = 'http://:8888'
c.JupyterHub.authenticator_class = 'pam'
c.Spawner.default_url = '/lab'
c.Spawner.notebook_dir = '~/notebooks'
c.Spawner.mem_limit = '16G'
c.Spawner.cpu_limit = 4

**Start service**:

sudo systemctl enable jupyterhub
sudo systemctl start jupyterhub

**Access**: `http://ovro-lwa1.caltech.edu:8888`

**Deliverable**: Multi-user JupyterHub for team.

---

### 4.2 Python API Client (Weeks 29-30)

**Create client** (`backend/src/dsa110_contimg/api/client.py`):

"""Python client for DSA-110 API"""

import requests
from typing import Dict
import pandas as pd

class DSAClient:
"""Client for DSA-110 Continuum Imaging API"""

    def __init__(self, base_url: str = 'http://localhost:8000'):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def get_performance_benchmarks(self, limit: int = 30) -> Dict:
        """Get performance trends"""
        resp = self.session.get(
            f'{self.base_url}/api/v1/performance/benchmarks',
            params={'limit': limit}
        )
        resp.raise_for_status()
        return resp.json()

    def get_gpu_status(self) -> Dict:
        """Get GPU utilization"""
        resp = self.session.get(f'{self.base_url}/api/v1/health/gpus')
        resp.raise_for_status()
        return resp.json()

    def check_calibration_health(self) -> Dict:
        """Check calibration freshness"""
        resp = self.session.get(f'{self.base_url}/api/v1/health/calibration')
        resp.raise_for_status()
        return resp.json()

**Example notebook** (`notebooks/examples/01_monitoring.ipynb`):

from dsa110_contimg.api.client import DSAClient
import matplotlib.pyplot as plt

client = DSAClient('http://ovro-lwa1.caltech.edu:8000')

# Check GPU status

gpu_status = client.get_gpu_status()
for gpu in gpu_status['gpus']:
print(f"GPU {gpu['id']}: {gpu['utilization_gpu']}% util")

# Check calibration health

cal_health = client.check_calibration_health()
print(f"Calibration: {cal_health['message']}")

# Get performance trends

perf = client.get_performance_benchmarks()

# Plot...

**Deliverable**: Python client library with example notebooks.

---

## Implementation Timeline

| Phase       | Duration      | Key Deliverables                                     | FTE           |
| ----------- | ------------- | ---------------------------------------------------- | ------------- |
| **Phase 1** | Months 1-3    | casabench, GPU setup, improved calibration discovery | 1.0           |
| **Phase 2** | Months 4-7    | GPU RFI, gridding, calibration                       | 1.0           |
| **Phase 3** | Months 8-10   | State machine, QA framework                          | 1.0           |
| **Phase 4** | Months 11-12  | JupyterHub, API client                               | 0.5           |
| **Total**   | **12 months** | **GPU-accelerated production pipeline**              | **0.875 avg** |

---

## Architecture Integration Points

### Verified Compatibility

| Component              | File                                       | Integration Point                     |
| ---------------------- | ------------------------------------------ | ------------------------------------- |
| Performance API        | `api/app.py`                               | Add endpoints after line 200          |
| GPU monitoring         | `api/app.py`                               | Add endpoints with performance        |
| Calibration health     | `api/app.py`                               | Add with GPU endpoints                |
| Improved cal discovery | `calibration/caltables.py`                 | Extend existing functions             |
| State machine          | `database/state_machine.py`                | New module (uses existing session.py) |
| QA framework           | `calibration/qa.py`                        | New module                            |
| GPU RFI                | `rfi/gpu_detection.py`                     | New module                            |
| GPU imaging            | `imaging/gpu_gridding.py`, `gpu_tclean.py` | New modules                           |
| GPU calibration        | `calibration/gpu_solver.py`                | New module                            |

### Database Schema Extensions

**Add to unified pipeline database** (`/data/dsa110-contimg/state/db/pipeline.sqlite3`):

-- MS state tracking
CREATE TABLE IF NOT EXISTS ms_state (
ms_path TEXT PRIMARY KEY,
current_state TEXT NOT NULL,
previous_state TEXT,
transition_time REAL NOT NULL,
retry_count INTEGER DEFAULT 0,
error_message TEXT,
checkpoint_data TEXT
);

-- Calibration QA metrics (optional, for future enhancement)
CREATE TABLE IF NOT EXISTS calibration_qa (
ms_path TEXT PRIMARY KEY,
qa_timestamp REAL NOT NULL,
passed INTEGER NOT NULL,
metrics TEXT,
FOREIGN KEY (ms_path) REFERENCES ms_state(ms_path)
);

---

## Environment Variables

**Add to deployment environment**:

# GPU configuration

USE_GPU_RFI=true
USE_GPU_IMAGING=true
USE_GPU_CALIBRATION=false # Not fully integrated yet

# Paths (use existing)

CALIBRATION_DIR=/data/dsa110-contimg/calibrations

# Database (already configured)

PIPELINE_DB=/data/dsa110-contimg/state/db/pipeline.sqlite3

---

## Success Metrics

### Performance (Quantitative)

- [ ] Calibration: 41s → 4s (10x)
- [ ] Imaging: 60s → 6s (10x)
- [ ] Throughput: 28 → 360 MS/hour (13x)
- [ ] GPU utilization: 0% → 70-90%
- [ ] RFI detection: Implemented and benchmarked

### Reliability (Qualitative)

- [ ] Performance baseline established (casabench)
- [ ] Nightly benchmarks running
- [ ] GPU monitoring in dashboard
- [ ] Calibration staleness alerts
- [ ] State machine framework ready
- [ ] QA framework ready

### Deliverables

- [ ] Performance monitoring infrastructure
- [ ] GPU acceleration modules (RFI, gridding, calibration)
- [ ] Improved calibration discovery
- [ ] State machine foundation
- [ ] QA framework
- [ ] JupyterHub deployment
- [ ] Python API client
- [ ] Example notebooks

---

## Risk Mitigation

| Risk                        | Probability | Mitigation                                        |
| --------------------------- | ----------- | ------------------------------------------------- |
| GPU OOM                     | Medium      | Chunked processing, memory monitoring             |
| Performance targets not met | Low         | Incremental optimization, CPU fallback            |
| Integration complexity      | Medium      | Phased approach, minimal changes to existing code |
| User adoption               | Low         | Documentation, training, examples                 |

---

## Conclusion

This architecture-verified implementation plan provides a **clear path to 10-20x performance improvement** through GPU acceleration while respecting the existing `dsa110-contimg` architecture. The phased approach delivers value incrementally, with Phase 1 establishing monitoring infrastructure that benefits the team immediately, even before GPU acceleration is deployed.

**Key advantages**:

- ✅ **Minimal disruption**: New modules extend existing architecture
- ✅ **Incremental value**: Each phase delivers tangible benefits
- ✅ **Low risk**: Proven technologies with fallback strategies
- ✅ **Architecture-aligned**: All integration points verified against actual codebase
- ✅ **Future-proof**: Extensible design supports future enhancements

The implementation leverages your existing strengths (modern web dashboard, comprehensive testing, clean API design) while addressing the critical performance bottleneck through targeted GPU acceleration.
