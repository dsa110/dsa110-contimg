# Backend TODO

## Completed ✅

- [x] Async migration (all routes use async repositories/services)
- [x] Narrow exception handling (46 handlers across 15 files)
- [x] FITS parsing service tests (20 tests)
- [x] Transaction management (4 context managers, 12 tests)
- [x] Database migrations CLI (`scripts/ops/migrate.py`)
- [x] PostgreSQL migration prep (`db_adapters/` package, 58 tests)
- [x] TimeoutConfig centralization
- [x] Batch module tests (105 tests)
- [x] Services monitor tests (41 tests)
- [x] Remove deprecated routes.py
- [x] Implement job_queue pipeline rerun logic
- [x] **Remove Legacy errors.py** - Deleted api/errors.py and consolidated to
      exceptions.py
- [x] **Narrow API/Database Exception Handlers** - 19 handlers narrowed in
      api/ and database/ modules (api/database.py, api/routes/imaging.py,
      api/services/bokeh_sessions.py, database/products.py,
      database/calibrators.py, database/session.py)
- [x] **Connection Pooling** - Added SyncDatabasePool with connection reuse,
      get_sync_db_pool(), close_sync_db_pool(); 7 new tests
- [x] **Narrow Conversion Exception Handlers** - 35+ handlers narrowed in
      conversion/ module (helpers_telescope.py, helpers_coordinates.py,
      helpers_validation.py, helpers_model.py, merge_spws.py, ms_utils.py,
      strategies/direct_subband.py)
- [x] **Narrow Remaining Exception Handlers** - 100+ handlers narrowed across: - utils/ (~17 handlers: validation.py, time_utils.py, regions.py,
      ms_helpers.py, locking.py) - photometry/ (~15 handlers: worker.py, forced.py, aegean_fitting.py,
      adaptive_binning.py) - imaging/ (~14 handlers: worker.py, fast_imaging.py, nvss_tools.py,
      cli_utils.py, cli.py, cli_imaging.py) - calibration/ (~17 handlers: validate.py, skymodels.py, selection.py,
      model.py, flagging.py, calibration.py) - catalog/ (~17 handlers: query.py, multiwavelength.py, build_master.py) - absurd/ (2 handlers: worker.py, adapter.py) - pipeline/ (2 handlers: stages_impl.py) - streaming_converter.py (~20 handlers)
      All handlers now use specific exception types: sqlite3.Error, OSError,
      RuntimeError, ValueError, KeyError, TypeError, ImportError, IndexError,
      subprocess.SubprocessError, np.linalg.LinAlgError, json.JSONDecodeError
- [x] **Mosaicking Module** - Complete implementation of mature mosaicking system
      following architecture document (`mature-mosaicking-code.md`). Features: - Three-tier system: Quicklook (10 images, 5min), Science (100 images, 30min),
      Deep (1000 images, 120min) - ABSURD-governed pipeline: MosaicPlanningJob → MosaicBuildJob → MosaicQAJob - Unified database: 3 tables (mosaic_plans, mosaics, mosaic_qa) - FastAPI endpoints: `/api/mosaic/create`, `/api/mosaic/status/{name}` - MosaicOrchestrator for ABSURD adapter integration - Contract tests: 26 tests covering builder, QA, tiers, jobs, pipeline,
      schema, orchestrator, and API - Module: 9 files, ~2760 lines in `src/dsa110_contimg/mosaic/`

**Status**: 950 unit tests passing, 72% coverage, **0 broad exception handlers**

---

## Future Enhancements

### Medium Priority

- [x] **Service Layer Refactoring** - Move business logic from repositories to
      services. Created `api/business_logic.py` with `stage_to_qa_grade()`,
      `generate_image_qa_summary()`, `generate_ms_qa_summary()`, `generate_run_id()`.
      Removed duplicate methods from AsyncImageRepository, AsyncMSRepository,
      AsyncJobRepository. Added 28 unit tests for business logic module.
- [x] **PostgreSQL Testing** - Test with real PostgreSQL database. Verified
      PostgreSQL 16 container connectivity, adapter creation, and query execution.
      All 58 database adapter tests pass. 15 tables created via init.sql.
- [x] **N+1 Query Optimization** - Optimized `AsyncImageRepository.list_all()`
      to batch fetch QA grades from ms_index in a single query instead of N+1
      queries per image. Added 8 optimization tests in `test_query_optimization.py`.

### Low Priority

- [x] **WebSocket Improvements** - Added heartbeat tracking, reconnection tokens,
      and disconnect reasons. Added `DisconnectReason` enum, `ConnectionState` enum,
      `record_heartbeat()`, `check_heartbeat()`, `generate_reconnect_token()` methods.
      Updated `/ws/jobs` and `/ws/pipeline` endpoints with heartbeat monitoring.
      Added 14 new WebSocket tests (39 total).
- [x] **Cache Optimization** - Redis cache for expensive queries. Added comprehensive
      test suite for cache module with 41 tests covering: CacheManager, cache key
      generation, @cached decorator, TTL configuration, blacklist handling, error
      handling, and singleton pattern.
- [x] **Metrics Dashboard** - Grafana dashboard for Prometheus metrics. Added
      `ops/grafana/dsa110-pipeline-dashboard.json` with 20 panels covering pipeline
      overview, processing throughput, data quality, and pipeline stages. Added
      39 unit tests for the metrics module.

---

## Monitoring Implementation ✅ COMPLETE

**Status:** All monitoring capabilities implemented

### 1. Unified Health Dashboard API

- **`api/routes/health.py`** - Comprehensive health monitoring endpoints:
  - `GET /health/system` - Full system health report (Docker, systemd, HTTP)
  - `GET /health/docker/{container}` - Individual container health
  - `GET /health/systemd/{service}` - Individual service health
  - `GET /health/databases` - Database connectivity checks
  - `GET /health/validity-windows` - Active calibration validity windows
  - `GET /health/flux-monitoring` - Calibrator flux monitoring status
  - `GET /health/alerts` - Recent monitoring alerts

### 2. Flux Monitoring Scheduler (ABSURD Integration)

- **`monitoring/tasks.py`** - ABSURD task definitions:
  - `monitoring.flux_check` - Run flux monitoring check (hourly)
  - `monitoring.health_check` - System health check (5 minutes)
  - `monitoring.validity_check` - Validity window expiration check (15 minutes)
  - `monitoring.send_alert` - Send alerts via webhook/email/slack
- **Integration**: `register_monitoring_tasks()` and `setup_monitoring_schedules()`

### 3. Validity Window Visualization

- **API Endpoints**:
  - `GET /health/validity-windows` - Active windows by MJD
  - `GET /health/validity-windows/timeline` - Timeline view for visualization
- **Features**:
  - Query by MJD or ISO timestamp
  - Shows overlapping sets
  - Expiration warnings

### 4. Calibrator Monitoring Dashboard

- **Grafana panels** added to `ops/grafana/dsa110-pipeline-dashboard.json`:
  - Calibrator flux ratio over time
  - Flux stability alerts
  - Calibrator-specific metrics

### 5. Pointing Monitor Service

- **`pointing/monitor.py`** - Complete pointing module:
  - `calculate_lst()` - Current Local Sidereal Time
  - `predict_calibrator_transit()` - Transit time predictions
  - `get_active_calibrator()` - Currently transiting calibrator
  - `get_upcoming_transits()` - Future transit schedule
  - `PointingMonitor` class - Full monitoring daemon
- **`ops/systemd/contimg-pointing.service`** - Systemd service file

---

## Test Coverage Goals ✅ COMPLETE

**Status:** 1222 unit tests (18 new GPU safety tests)

All coverage targets have been achieved:

| Module                | Previous | Current | Target | Status |
| --------------------- | -------- | ------- | ------ | ------ |
| `batch/qa.py`         | 41%      | 97%     | 80%    | ✅     |
| `batch/thumbnails.py` | 53%      | 97%     | 80%    | ✅     |
| `websocket.py`        | 49%      | 84%     | 70%    | ✅     |
| `cache.py`            | 28%      | 89%     | 60%    | ✅     |
| `metrics.py`          | 33%      | 93%     | 60%    | ✅     |

---

## GPU Acceleration (Phase 1 - In Progress)

**Reference**: `GPU_implementation_plan.md`

### Phase 1 Completed ✅

- [x] **GPU Environment Assessment** - Verified 2x RTX 2080 Ti (CC 7.5, 11GB each),
      Driver 455.23.05, CUDA 11.1 max. Ubuntu 18.04 constraints documented.
- [x] **CuPy Installation** - CuPy 13.6.0 installed with cuda-nvrtc 11.8 workaround.
      Numba CUDA blocked due to PTX version mismatch (requires driver upgrade).
- [x] **Precision Validation** - FP32 vs FP64 comparison complete. 7/7 tests passed: - Complex multiply: 6.55e-07 error (threshold 1.57e-05) ✓ - Sum accumulation: 1.60e-07 relative error ✓ - Phase computation: 2.59e-05 degrees (threshold 0.01°) ✓ - Matrix solve: 1.22e-06 relative error ✓ - 2D FFT: 5.92e-08 relative error ✓ - Visibility simulation: 2.00e-07 relative error ✓ - GPU FFT (FP32): 5.74e-07 relative error ✓
- [x] **Resource Limiting Utilities** - `scripts/testing/resource_limits.py` with
      MemoryLimiter, ResourceLimitedRunner, safe_run(), pre-flight memory checks.
      Prevents runaway memory/CPU from crashing system.
- [x] **Production GPU Safety Module** - `utils/gpu_safety.py` (~900 lines):
  - **System RAM Protection**:
    - Hard limits: max 6GB per operation, always keep 2GB free
    - Pre-flight checks before allocations
    - Usage limit: never exceed 70% of system RAM
  - **GPU VRAM Protection**:
    - CuPy memory pool limits (9GB max per GPU)
    - Pre-flight checks before GPU allocations
    - Usage limit: never exceed 85% of GPU VRAM
  - **Safe Context Managers**:
    - `safe_memory_context()` - System RAM protection with timeout
    - `safe_gpu_context()` - GPU memory protection with pool limits
  - **Safe Decorators**:
    - `@memory_safe` - Wrap functions with RAM protection
    - `@gpu_safe` - Wrap functions with GPU memory protection
  - **Safe Allocation Functions**:
    - `safe_gpu_array()` - Pre-checked GPU array allocation
    - `safe_to_gpu()` - Pre-checked host-to-GPU transfer
  - **Estimation Utilities**:
    - `estimate_visibility_memory_gb()` - Critical for preventing OOM
    - `check_visibility_allocation_safe()` - Validates before allocating
  - **Integration**:
    - Connects to `monitoring/gpu.py` for alert callbacks
    - `initialize_gpu_safety()` sets up pools at startup
- [x] **GPU Safety Integration** - Production hardening to prevent Dec 2 crash scenario:
  - **Entry Points Protected**:
    - `imaging/worker.py` - `@memory_safe` on `_apply_and_image()`, `process_once()`
    - `imaging/fast_imaging.py` - `@gpu_safe` on `run_fast_imaging()`
    - `calibration/applycal.py` - `@memory_safe` on `apply_to_target()`
  - **Application Startup**: `api/app.py` calls `initialize_gpu_safety()` in lifespan
  - **System-level Protection**: `LimitAS=24G` in systemd services (absurd-worker,
    absurd-scheduler, pipeline-scheduler)
  - **Unit Tests**: 18 tests in `tests/unit/test_gpu_safety.py` covering:
    - System memory checks and rejection
    - `@memory_safe` and `@gpu_safe` decorators
    - Visibility memory estimation (including Dec 2 scenario: 96 ant × 768 chan)
    - OOM rejection before allocation
    - `safe_gpu_context` manager

### Precision Strategy Decision

**FP32 acceptable for:**

- Gain application (complex multiplication)
- FFT/imaging operations
- Basic accumulations
- GPU kernel operations

**FP64 required for:**

- Calibration solver inner loops (large accumulations)
- Iterative convergence tests
- Ill-conditioned matrix operations

### Next Steps (Phase 1 Remaining)

- [x] **Performance Monitoring with ASV Benchmarking** (Weeks 1-4)

  - ASV benchmarking infrastructure in `benchmarks/` directory
  - Created calibration/imaging/conversion/GPU benchmarks
  - Standalone benchmark runner at `benchmarks/run_benchmarks.py`
  - Performance API at `/api/v1/performance/*`:
    - `GET /benchmarks` - Latest benchmark results
    - `GET /benchmarks/history` - Historical results with filtering
    - `GET /summary` - Performance summary with GPU speedups
    - `GET /gpus` - GPU status and utilization (pynvml/CuPy)
    - `GET /gpus/{gpu_id}` - Individual GPU metrics
    - `GET /trends` - Performance trend analysis
  - Established baselines:
    - GPU FFT 2048: 4x faster than CPU (0.058s vs 0.233s)
    - GPU FFT 512: 7.8x faster (0.0011s vs 0.0086s)
    - GPU vis correction: 9.5x faster (0.0015s vs 0.0142s)

- [x] **GPU Monitoring Dashboard** (Weeks 3-6)

  - Created `monitoring/gpu.py` - Comprehensive GPU monitoring module:
    - `GPUMonitor` class with pynvml/CuPy backends
    - Real-time metrics collection (memory, utilization, temperature, power)
    - Historical metrics storage (1 hour rolling window)
    - Alert thresholds and callbacks
    - Health status determination (healthy, warning, critical)
  - Added GPU health API endpoints in `api/routes/health.py`:
    - `GET /health/gpus` - All GPU health status with alerts
    - `GET /health/gpus/{gpu_id}` - Individual GPU metrics
    - `GET /health/gpus/{gpu_id}/history` - Historical metrics (1-1440 min)
    - `GET /health/gpus/alerts/recent` - Recent GPU alerts with filtering
  - Added WebSocket real-time streaming in `api/websocket.py`:
    - `WS /ws/gpu-metrics` - Real-time GPU metrics stream (1s interval)
  - Created Grafana GPU dashboard `ops/grafana/dsa110-gpu-dashboard.json`:
    - GPU overview (health status, device info)
    - Memory utilization panel (time series)
    - GPU utilization panel (time series)
    - Temperature panel (time series)
    - Power consumption panel (time series)
    - Alerts panel with severity filtering
  - Add real-time memory/utilization charts

- [x] **Improved Calibration Discovery** (Weeks 5-8)
  - Rewrote `calibration/caltables.py` with comprehensive improvements (~550 lines):
    - `CalibrationCandidate` dataclass with MJD, age, source metadata
    - `CalibrationHealth` dataclass with staleness thresholds
    - `find_nearest_calibration()` - Bidirectional time-based search
    - `_search_registry()` - Database search with MJD windows
    - `_search_filesystem()` - Filesystem fallback search
    - `get_applylist_for_mjd()` - Ordered calibration table paths
    - `check_calibration_staleness()` - Health evaluation with thresholds
    - `get_calibration_timeline()` - Coverage timeline with gap analysis
  - Staleness thresholds: fresh (≤6h), aging (6-12h), stale (12-24h), critical (>24h)
  - Added calibration health API endpoints in `api/routes/health.py`:
    - `GET /health/calibration` - Calibration health status
    - `GET /health/calibration/nearest` - Find nearest calibration (bidirectional)
    - `GET /health/calibration/timeline` - Coverage timeline with gap analysis
    - `GET /health/calibration/applylist` - Ordered tables to apply

### Phase 1 COMPLETE ✅

All Phase 1 GPU Acceleration items completed. Ready for Phase 2: CUDA Kernel Development.

---

## GPU Acceleration (Phase 2 - COMPLETE) ✅

**Reference**: `GPU_implementation_plan.md`

### Phase 2.1: RFI Detection Module ✅

- [x] **RFI Detection Module Scaffold** - Created `src/dsa110_contimg/rfi/`:
  - **`__init__.py`** - Module exports (gpu_rfi_detection, RFIDetectionResult, RFIDetectionConfig)
  - **`gpu_detection.py`** (~420 lines) - CuPy-based GPU RFI detection:
    - `RFIDetectionConfig` dataclass - Detection parameters (threshold, gpu_id, chunk_size)
    - `RFIDetectionResult` dataclass - Detection results with stats and timing
    - `_detect_outliers_cupy()` - GPU MAD-based outlier detection using CuPy
    - `gpu_rfi_detection()` - Main entry point with chunked MS processing
    - `cpu_rfi_detection()` - CPU fallback for systems without GPU
    - Uses `safe_gpu_context` from gpu_safety module
- [x] **Unit Tests** - `tests/unit/test_rfi_detection.py` (12 tests):
  - RFIDetectionConfig defaults and custom values
  - RFIDetectionResult success/failure states
  - Mock CuPy setup for GPU testing
  - Missing file error handling
  - CuPy availability detection
  - MAD algorithm numerical validation
- [x] **Integration Tests** - `tests/integration/test_rfi_gpu_integration.py` (13 tests):
  - GPU safety initialization
  - Memory checking integration
  - RFI detection with mock MS structures
  - MAD algorithm numerical stability
  - End-to-end workflow testing

### Phase 2.2: Systemd Production Hardening ✅

- [x] **Systemd Services Deployed** - Installed to `/etc/systemd/system/`:
  - `absurd-worker.service` - MemoryMax=28G, LimitAS=32G
  - `absurd-scheduler.service` - Memory limits applied
  - `pipeline-scheduler.service` - Memory limits applied
  - Services reloaded with `systemctl daemon-reload`

### Phase 2.3: GPU Gridding Module ✅

- [x] **GPU Gridding with CuPy** - Created `src/dsa110_contimg/imaging/gpu_gridding.py` (~936 lines):
  - `GriddingConfig` dataclass - image_size, cell_size_arcsec, support, oversampling
  - `GriddingResult` dataclass - image, grid, sum_weights, n_vis_gridded, processing_time_s
  - `_compute_spheroidal_gcf()` - Gridding convolution function computation
  - `gpu_grid_visibilities()` - CuPy-based GPU gridding with integrated FFT
  - `cpu_grid_visibilities()` - NumPy CPU fallback with identical interface
  - Uses `safe_gpu_context` and memory estimation from gpu_safety module
- [x] **Unit Tests** - `tests/unit/test_gpu_gridding.py` (28 tests):
  - GriddingConfig/GriddingResult dataclass validation
  - Spheroidal GCF computation and normalization
  - Memory estimation scaling tests
  - CPU and GPU gridding with flags
  - Empty/invalid input handling
  - CuPy availability detection
- [x] **Integration Tests** - `tests/integration/test_gridding_gpu_integration.py` (19 tests):
  - GPU safety initialization for gridding
  - Memory estimation reasonable bounds
  - Mock MS structure handling
  - Point source and random visibility gridding
  - CPU/GPU consistency verification
  - GCF symmetry and normalization
  - Weighting schemes (uniform, varied, zero)
  - End-to-end workflow testing

### Phase 2.4: GPU Calibration Module ✅

- [x] **Calibration Gain Application** - Created `src/dsa110_contimg/calibration/gpu_calibration.py` (~795 lines):
  - `CalibrationConfig` dataclass - gpu_id, n_pol, chunk_size, tolerance, max_iterations
  - `GainSolutionResult` dataclass - gains, weights, n_iterations, converged, residual_rms
  - `ApplyCalResult` dataclass - n_vis_processed, n_vis_calibrated, n_vis_flagged
  - `apply_gains_gpu()` - CuPy kernel for g_i \* conj(g_j) correction
  - `apply_gains_cpu()` - NumPy CPU fallback
  - `solve_per_antenna_gains_gpu()` - Iterative GPU gain solver with reference antenna
  - `solve_per_antenna_gains_cpu()` - CPU fallback solver
  - `apply_gains()` / `solve_per_antenna_gains()` - Dispatch functions with GPU/CPU fallback
- [x] **Unit Tests** - `tests/unit/test_gpu_calibration.py` (19 tests):
  - CalibrationConfig defaults and custom values
  - GainSolutionResult/ApplyCalResult success properties
  - Memory estimation for apply and solve operations
  - Unit gains and constant gains application
  - Zero gains flagging behavior
  - Known gains recovery in solver
  - Noisy data gain solving
  - CPU/GPU dispatch testing
  - CuPy availability detection

### Phase 2.5: ASV Benchmarks ✅

- [x] **Benchmark Suite** - Updated `benchmarks/benchmarks/bench_gpu.py`:
  - `GPUGriddingTimeSuite` - CPU/GPU gridding benchmarks (512, 1024, 2048 images)
  - `GPUCalibrationTimeSuite` - CPU/GPU calibration benchmarks (5-110 antennas, 1K-100K vis)
  - Parameterized benchmarks for scaling analysis
  - All benchmarks verified working

### Phase 2 COMPLETE ✅

All Phase 2 GPU CUDA Kernel Development items completed:

- RFI Detection Module (12 unit + 13 integration tests)
- Systemd Production Hardening (memory limits deployed)
- GPU Gridding Module (28 unit + 19 integration tests)
- GPU Calibration Module (19 unit tests)
- ASV Benchmark Suite (gridding + calibration benchmarks)

---

### Files Created (Phase 2)

| File                                                 | Purpose                               |
| ---------------------------------------------------- | ------------------------------------- |
| `src/dsa110_contimg/rfi/__init__.py`                 | RFI module exports                    |
| `src/dsa110_contimg/rfi/gpu_detection.py`            | CuPy-based GPU RFI detection          |
| `src/dsa110_contimg/imaging/gpu_gridding.py`         | CuPy-based GPU visibility gridding    |
| `src/dsa110_contimg/calibration/gpu_calibration.py`  | CuPy-based GPU calibration            |
| `tests/unit/test_rfi_detection.py`                   | RFI unit tests (12 tests)             |
| `tests/unit/test_gpu_gridding.py`                    | GPU gridding unit tests (28 tests)    |
| `tests/unit/test_gpu_calibration.py`                 | GPU calibration unit tests (19 tests) |
| `tests/integration/test_rfi_gpu_integration.py`      | RFI integration tests (13 tests)      |
| `tests/integration/test_gridding_gpu_integration.py` | Gridding integration tests (19 tests) |

### Files Created (Phase 1)

| File                                              | Purpose                          |
| ------------------------------------------------- | -------------------------------- |
| `scripts/testing/resource_limits.py`              | Resource limiting utilities      |
| `scripts/testing/validate_fp32_precision_safe.py` | Safe FP32 validation             |
| `scripts/testing/validate_fp32_calibration.py`    | Original validation (deprecated) |
| `benchmarks/asv.conf.json`                        | ASV configuration                |
| `benchmarks/run_benchmarks.py`                    | Standalone benchmark runner      |
| `benchmarks/benchmarks/bench_calibration.py`      | Calibration benchmarks           |
| `benchmarks/benchmarks/bench_imaging.py`          | Imaging/gridding benchmarks      |
| `benchmarks/benchmarks/bench_gpu.py`              | GPU vs CPU comparison benchmarks |
| `benchmarks/benchmarks/bench_conversion.py`       | HDF5/MS conversion benchmarks    |
| `src/dsa110_contimg/api/routes/performance.py`    | Performance API endpoints        |
| `src/dsa110_contimg/monitoring/gpu.py`            | GPU monitoring module            |
| `ops/grafana/dsa110-gpu-dashboard.json`           | Grafana GPU dashboard            |
| `src/dsa110_contimg/calibration/caltables.py`     | Improved calibration discovery   |
| `src/dsa110_contimg/utils/gpu_safety.py`          | Production GPU/RAM safety guards |
| `tests/unit/test_gpu_safety.py`                   | GPU safety unit tests (18 tests) |

### Known Constraints

- **Driver 455.23.05**: Max CUDA 11.1, PTX 7.1 - blocks Numba CUDA
- **Ubuntu 18.04**: User cannot upgrade OS
- **CuPy-only approach**: Recommended until driver upgrade possible
- **FP64 performance**: ~20-30x slower than FP32 on RTX 2080 Ti (CC 7.5)

---

## Documentation

See `docs/` for:

- `ARCHITECTURE.md` - System architecture and design patterns
- `CHANGELOG.md` - Development history and milestones
- `ASYNC_PERFORMANCE_REPORT.md` - Async migration benchmarks
- `database-adapters.md` - Multi-database abstraction layer
