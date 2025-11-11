# Deep Study Analysis: DSA-110 Continuum Imaging Pipeline

**Date:** 2025-01-XX  
**Repository:** `dsa110-contimg`  
**Package:** `dsa110_contimg`

---

## Executive Summary

The DSA-110 Continuum Imaging Pipeline is a production-grade radio astronomy data processing system designed for streaming, real-time processing of interferometric observations from the DSA-110 telescope array. The system transforms raw UVH5 (HDF5) subband files into calibrated, imaged radio continuum products through a sophisticated multi-stage workflow with dependency resolution, retry policies, and comprehensive monitoring.

**Key Characteristics:**
- **Streaming-first architecture**: Watches incoming data directories and processes complete subband groups automatically
- **Modular pipeline framework**: Declarative stage-based system with dependency resolution
- **Multi-database state management**: SQLite databases for queue, calibration registry, and products tracking
- **Production monitoring API**: FastAPI-based REST API with WebSocket support for real-time status
- **CASA integration**: Deep integration with CASA (Common Astronomy Software Applications) for calibration and imaging
- **Quality assurance**: Built-in QA checks, validation, and catalog-based flux scale verification

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

The system follows a **streaming pipeline architecture** with three main operational modes:

1. **Streaming Mode** (Production): Continuous daemon watching `/data/incoming/` for UVH5 files
2. **Batch Mode**: One-shot processing of time windows via CLI
3. **API-Driven Mode**: Job-based processing through REST API

### 1.2 Core Data Flow

```
UVH5 Files (16 subbands) → Queue Detection → Conversion (UVH5→MS) → 
Calibration Solving → Calibration Application → Imaging → Products DB
```

**Detailed Pipeline Stages:**
1. **File Detection**: Watchdog monitors `/data/incoming/` for `*_sb??.hdf5` files
2. **Group Formation**: Groups files by timestamp (expects 16 subbands per group)
3. **Queue Management**: SQLite queue tracks group state (collecting/pending/in_progress/completed/failed)
4. **Conversion**: UVH5 → CASA Measurement Set (MS) via strategy orchestrator
5. **Calibration Solving**: Solve K/BA/BP/GA/GP/2G tables on calibrator MS
6. **Calibration Application**: Apply active caltables to target MS
7. **Imaging**: Run tclean or WSClean to create continuum images
8. **Products Registration**: Update products database with MS and image metadata

### 1.3 Design Patterns

**Pipeline Orchestrator Pattern** (`pipeline/orchestrator.py`):
- Topological sorting for dependency resolution
- Retry policies with exponential backoff
- Stage validation and output verification
- Observability hooks for metrics and logging

**Strategy Pattern** (`conversion/strategies/`):
- Pluggable writers: `direct-subband`, `pyuvdata-monolithic`
- Writer selection based on performance characteristics
- Consistent interface via `base.py`

**Registry Pattern** (`database/registry.py`):
- Centralized calibration table registry
- Validity windows (MJD-based)
- Ordered apply lists
- Status tracking (active/retired/failed)

**Repository Pattern** (`database/products.py`):
- Centralized database schema management
- Helper functions for common operations
- Migration support

---

## 2. Core Modules Deep Dive

### 2.1 Conversion Module (`conversion/`)

**Purpose**: Convert UVH5 (HDF5) files to CASA Measurement Sets (MS)

**Key Components**:

1. **Streaming Converter** (`streaming/streaming_converter.py`):
   - Watches `/data/incoming/` for `*_sb??.hdf5` files
   - Groups files by timestamp (16 subbands expected)
   - Manages queue state in SQLite (`ingest_queue` table)
   - Invokes orchestrator writer for conversion
   - Handles calibrator matching and calibration solving
   - Applies calibration and runs imaging

2. **HDF5 Orchestrator** (`strategies/hdf5_orchestrator.py`):
   - Primary entry point for conversion
   - Discovers complete subband groups
   - Delegates to writer strategies
   - Handles MS finalization (antenna positions, phasing, imaging columns)

3. **Writer Strategies**:
   - **`direct_subband.py`**: Parallel per-subband writer (preferred, robust for CASA)
   - **`pyuvdata_monolithic.py`**: Single-shot writer via `UVData.write_ms`

4. **Helpers**:
   - `helpers.py`: Antenna positions, meridian phasing, model/weights
   - `helpers_antenna.py`: Antenna metadata and classification
   - `helpers_coordinates.py`: Coordinate transformations
   - `helpers_telescope.py`: Telescope identity and location

**Key Features**:
- Meridian phasing (time-dependent phase centers: RA=LST(t), Dec from UVH5)
- Antenna position setup (DSA-110 station coordinates)
- MODEL_DATA/CORRECTED_DATA initialization
- WEIGHT_SPECTRUM setup
- Frequency order validation
- UVW precision validation

### 2.2 Calibration Module (`calibration/`)

**Purpose**: Solve and apply calibration solutions for radio interferometry

**Calibration Types**:
- **K (Delay)**: Clock/geometric delays (optional for DSA-110)
- **BA (Bandpass Amplitude)**: Frequency-dependent amplitude corrections
- **BP (Bandpass Phase)**: Frequency-dependent phase corrections
- **GA (Gain Amplitude)**: Time-dependent amplitude gains
- **GP (Gain Phase)**: Time-dependent phase gains
- **2G**: Short-timescale atmospheric phase gains (optional)
- **FLUX**: Flux scale calibration (optional)

**Key Components**:

1. **Calibration Solving** (`calibration.py`):
   - `solve_delay()`: K-calibration (optional, not used for DSA-110)
   - `solve_bandpass()`: BP-calibration with model setup
   - `solve_gains()`: G-calibration (amp+phase or phase-only)
   - `solve_prebandpass_phase()`: Pre-BP phase correction

2. **Calibration Application** (`applycal.py`, `apply_service.py`):
   - `apply_to_target()`: Apply caltables to target fields
   - `verify_calibration_applied()`: Validate application success
   - CORRECTED_DATA population verification

3. **Calibrator Matching** (`selection.py`, `catalogs.py`):
   - VLA calibrator catalog integration (SQLite or CSV)
   - Beam-based matching with radius and top-N selection
   - Flux-weighted selection

4. **Registry Management** (`database/registry.py`):
   - Caltable registration with validity windows
   - Ordered apply lists (K → BA → BP → GA → GP → 2G → FLUX)
   - Status tracking (active/retired/failed)

5. **Experimental**: CubiCal integration (`cubical_experimental/`) for alternative calibration backend

**Calibration Workflow**:
1. Match calibrators in beam (VLA catalog)
2. Solve calibration tables (K/BA/BP/GA/GP)
3. Register caltables in registry DB with validity windows
4. Apply active caltables to target MS
5. Verify CORRECTED_DATA populated

### 2.3 Imaging Module (`imaging/`)

**Purpose**: Create radio continuum images from calibrated Measurement Sets

**Backends**:
- **WSClean** (default): Fast, GPU-accelerated imaging
- **CASA tclean**: Standard CASA imaging with full feature support

**Key Components**:

1. **Main Imaging Function** (`cli_imaging.py::image_ms()`):
   - Automatic datacolumn selection (CORRECTED_DATA preferred)
   - Quality tiers: `development`, `standard`, `high_precision`
   - NVSS-based masking (2-4x faster imaging)
   - Primary beam correction
   - FITS export

2. **WSClean Integration** (`cli_imaging.py::run_wsclean()`):
   - Command-line invocation
   - Parameter translation (CASA → WSClean)
   - Output validation

3. **CASA tclean Integration**:
   - Full CASA tclean support
   - Gridder options: `standard`, `wproject`, `mosaic`, `awproject`
   - Deconvolvers: `hogbom`, `multiscale`, `mtmfs`

4. **Image Export** (`export.py`):
   - CASA image → FITS conversion
   - Header metadata extraction
   - Beam information

**Imaging Features**:
- NVSS catalog seeding for model initialization
- NVSS-based masking (restricts cleaning to known sources)
- Primary beam correction (PB-corrected images)
- Quality tier presets (development/standard/high_precision)
- Catalog-based flux scale validation

### 2.4 Photometry Module (`photometry/`)

**Purpose**: Measure flux densities from images (forced photometry)

**Key Components**:

1. **Forced Photometry** (`forced.py`):
   - `measure_forced_peak()`: Peak flux measurement in pixel box
   - Local RMS estimation (sigma-clipped annulus)
   - WCS-based coordinate conversion

2. **Adaptive Photometry** (`adaptive_photometry.py`):
   - Adaptive binning for variable sources
   - Multi-SPW imaging and photometry

3. **Aegean Integration** (`aegean_fitting.py`):
   - Gaussian fitting via Aegean source finder
   - Extended source measurement

4. **Normalization** (`normalize.py`):
   - Differential photometry using reference sources
   - Ensemble correction for systematic removal
   - 1-2% relative precision vs 5-7% absolute

**Use Cases**:
- ESE (Extragalactic Scintillation Event) monitoring
- Variable source monitoring
- Flux scale validation

### 2.5 Pipeline Framework (`pipeline/`)

**Purpose**: Declarative pipeline orchestration with dependency resolution

**Key Components**:

1. **Pipeline Orchestrator** (`orchestrator.py`):
   - Topological sorting for stage dependencies
   - Retry policies (exponential backoff)
   - Stage execution with validation
   - Error handling and partial completion support

2. **Pipeline Stages** (`stages.py`, `stages_impl.py`):
   - **ConversionStage**: UVH5 → MS conversion
   - **CalibrationSolveStage**: Solve calibration tables
   - **CalibrationStage**: Apply calibration
   - **ImagingStage**: Create images
   - **OrganizationStage**: Organize MS files (science/calibrators/failed)

3. **Pipeline Context** (`context.py`):
   - Immutable context passed between stages
   - Inputs, outputs, metadata
   - Configuration reference

4. **Workflows** (`workflows.py`):
   - `standard_imaging_workflow()`: Convert → Solve → Apply → Image
   - `quicklook_workflow()`: Fast imaging without full calibration
   - `reprocessing_workflow()`: Re-image existing MS

5. **Configuration** (`config.py`):
   - Type-safe Pydantic models
   - Environment variable support
   - Path validation and health checks

**Pipeline Features**:
- Dependency resolution (topological sort)
- Retry policies with exponential backoff
- Stage validation (pre/post execution)
- Observability (metrics, logging)
- Resource management (timeouts, memory limits)

### 2.6 Database Module (`database/`)

**Purpose**: Centralized database schema and helper functions

**Databases**:

1. **Queue Database** (`ingest.sqlite3`):
   - `ingest_queue`: Group state (collecting/pending/in_progress/completed/failed)
   - `subband_files`: File arrivals tracking
   - `performance_metrics`: Writer type, timings

2. **Calibration Registry** (`cal_registry.sqlite3`):
   - `caltables`: Caltable metadata, validity windows, apply order
   - Status: active/retired/failed

3. **Products Database** (`products.sqlite3`):
   - `ms_index`: MS file index (path, time range, status, stage)
   - `images`: Image artifacts (path, MS path, beam, noise, pbcor)
   - `photometry`: Forced photometry results
   - `mosaics`: Mosaic plans and builds
   - `storage_locations`: Storage location registry for recovery

4. **Data Registry** (optional, `data_registry.sqlite3`):
   - `data_registry`: Data instance tracking (staging → published)
   - `data_relationships`: Parent-child relationships
   - `data_tags`: Tagging for organization

**Key Functions**:
- `ensure_products_db()`: Schema creation/migration
- `ms_index_upsert()`: Update MS index
- `images_insert()`: Register image artifacts
- `ensure_db()` (registry): Caltable registration
- `get_active_applylist()`: Get caltables for MJD

### 2.7 API Module (`api/`)

**Purpose**: FastAPI-based monitoring and control API

**Key Components**:

1. **Routes** (`routes.py`):
   - `/api/status`: Pipeline status, queue stats, recent groups
   - `/api/ms_index`: Filtered MS index queries
   - `/api/products`: Image products list
   - `/api/calibration`: Calibration sets and matches
   - `/api/jobs/*`: Job creation and management
   - `/api/ese/candidates`: ESE candidate detection
   - `/api/mosaics`: Mosaic queries
   - `/api/streaming/*`: Streaming service control

2. **Models** (`models.py`):
   - Pydantic models for request/response
   - Type-safe API contracts

3. **Job System** (`job_runner.py`, `job_adapters.py`):
   - Job queue management (SQLite)
   - Background task execution
   - Job status tracking

4. **WebSocket Manager** (`websocket_manager.py`):
   - Real-time status broadcasts
   - Client connection management

5. **Streaming Service** (`streaming_service.py`):
   - Streaming converter lifecycle management
   - Configuration updates
   - Health monitoring

**API Features**:
- RESTful endpoints with OpenAPI documentation
- WebSocket support for real-time updates
- Background job execution
- Authentication support (optional)
- CORS middleware

### 2.8 QA Module (`qa/`)

**Purpose**: Quality assurance checks and validation

**Key Components**:

1. **Pipeline Quality** (`pipeline_quality.py`):
   - MS quality checks after conversion
   - Calibration quality validation
   - Image quality metrics

2. **Calibration Quality** (`calibration_quality.py`):
   - Caltable SNR analysis
   - Solution stability metrics
   - Antenna coverage validation

3. **Image Quality** (`image_quality.py`):
   - Beam shape analysis
   - Noise estimation
   - Dynamic range calculation

4. **Catalog Validation** (`catalog_validation.py`):
   - Flux scale validation (NVSS/VLASS)
   - Source matching
   - Flux ratio analysis

5. **Fast Plots** (`fast_plots.py`):
   - Quick visualization for QA
   - Calibration plots
   - Image thumbnails

### 2.9 Mosaic Module (`mosaic/`)

**Purpose**: Combine multiple image tiles into larger mosaics

**Key Components**:

1. **Mosaic Planning** (`cli.py::cmd_plan()`):
   - Query products DB for tiles in time range
   - Validate tile consistency
   - Record mosaic plan

2. **Mosaic Building** (`cli.py::cmd_build()`):
   - Validate tiles (astrometry, calibration, PB)
   - Build weighted mosaic (CASA `immath`)
   - Primary beam weighting

3. **Validation** (`validation.py`):
   - Astrometric registration check
   - Calibration consistency
   - Primary beam consistency
   - Grid alignment

4. **Streaming Mosaic** (`streaming_mosaic.py`):
   - Real-time mosaic updates as tiles arrive
   - Incremental building

### 2.10 Utilities (`utils/`)

**Purpose**: Shared utilities across modules

**Key Utilities**:
- `time_utils.py`: Time conversions (MJD, Unix, CASA epochs)
- `ms_helpers.py`: CASA MS manipulation helpers
- `ms_organization.py`: MS file organization (science/calibrators/failed)
- `coordinates.py`: Coordinate transformations
- `angles.py`: Angle calculations
- `constants.py`: DSA-110 telescope constants
- `validation.py`: Input validation
- `error_context.py`: Error formatting with suggestions
- `performance.py`: Performance tracking decorators
- `logging.py`: Structured logging

---

## 3. Data Flow and State Management

### 3.1 Streaming Workflow

```
1. UVH5 files arrive in /data/incoming/
   └─> Format: YYYY-MM-DDTHH:MM:SS_sbXX.hdf5

2. Streaming converter detects files
   └─> Groups by timestamp (16 subbands expected)
   └─> Updates ingest_queue (state: collecting)

3. When group complete (16 subbands):
   └─> State: collecting → pending
   └─> Calibrator matching (optional)
   └─> Conversion invoked

4. Conversion Stage:
   └─> HDF5 orchestrator discovers group
   └─> Writer strategy converts subbands → MS
   └─> MS finalization (antenna positions, phasing, columns)
   └─> MS organized: science/calibrators/failed

5. Calibration Solve Stage (if calibrator matched):
   └─> Solve K/BA/BP/GA/GP tables
   └─> Register in cal_registry.sqlite3
   └─> Validity windows set

6. Calibration Apply Stage:
   └─> Get active caltables from registry
   └─> Apply to target MS
   └─> Verify CORRECTED_DATA populated

7. Imaging Stage:
   └─> Run tclean or WSClean
   └─> Primary beam correction
   └─> FITS export
   └─> Register in products.sqlite3

8. Products Database Update:
   └─> ms_index: MS path, time range, status, stage
   └─> images: Image path, MS path, beam, noise, pbcor
```

### 3.2 Database State Management

**Queue States**:
- `collecting`: Waiting for complete subband group
- `pending`: Ready for processing
- `in_progress`: Currently processing
- `completed`: Successfully processed
- `failed`: Processing failed

**MS Index Stages**:
- `converted`: MS created
- `calibrated`: Calibration applied
- `imaged`: Image created

**Calibration Registry**:
- `active`: Currently valid for application
- `retired`: Superseded by newer solutions
- `failed`: Calibration solution failed QA

---

## 4. Key Technologies and Dependencies

### 4.1 Core Dependencies

- **CASA (Common Astronomy Software Applications)**: Calibration and imaging
  - `casatasks`: CASA task interface
  - `casacore`: Low-level CASA core
  - `casatools`: CASA tools (vpmanager, msmetadata)

- **PyUVData**: UVH5 file I/O
  - `UVData.read_uvh5()`: Read UVH5 files
  - `UVData.write_ms()`: Write CASA MS

- **Astropy**: Astronomy utilities
  - `astropy.time`: Time conversions
  - `astropy.coordinates`: Coordinate transformations
  - `astropy.io.fits`: FITS file I/O
  - `astropy.wcs`: World Coordinate System

- **FastAPI**: API framework
  - REST endpoints
  - WebSocket support
  - OpenAPI documentation
  - Pydantic models

- **SQLite**: Database
  - Queue database
  - Calibration registry
  - Products database
  - WAL mode for concurrency

### 4.2 Optional Dependencies

- **WSClean**: Fast imaging backend
- **CubiCal**: Alternative calibration backend (experimental)
- **Aegean**: Source finding and Gaussian fitting
- **Watchdog**: Efficient file system watching

### 4.3 Environment

- **Python**: 3.8+
- **Conda**: Environment management (`casa6` environment)
- **Docker**: Containerization support
- **systemd**: Service management (production)

---

## 5. Configuration and Deployment

### 5.1 Environment Variables

**Core**:
- `PIPELINE_INPUT_DIR`: Input directory for UVH5 files
- `PIPELINE_OUTPUT_DIR`: Output directory for MS files
- `PIPELINE_SCRATCH_DIR`: Scratch directory for temporary files
- `PIPELINE_STATE_DIR`: State directory for databases (default: `state`)

**Database Paths**:
- `PIPELINE_PRODUCTS_DB`: Products database path
- `CAL_REGISTRY_DB`: Calibration registry path
- `PIPELINE_QUEUE_DB`: Queue database path

**Streaming**:
- `PIPELINE_POINTING_DEC_DEG`: Pointing declination (for calibrator matching)
- `VLA_CATALOG`: VLA calibrator catalog path (SQLite or CSV)
- `CAL_MATCH_RADIUS_DEG`: Calibrator match radius
- `CAL_MATCH_TOPN`: Top-N calibrators to consider

**Imaging**:
- `IMG_IMSIZE`: Image size (pixels)
- `IMG_ROBUST`: Briggs robust parameter
- `IMG_NITER`: Deconvolution iterations
- `IMG_THRESHOLD`: Deconvolution threshold

**Performance**:
- `OMP_NUM_THREADS`: OpenMP threads
- `MKL_NUM_THREADS`: MKL threads
- `HDF5_USE_FILE_LOCKING`: Disable HDF5 file locking (FALSE recommended)

### 5.2 Pipeline Configuration

Configuration via `PipelineConfig` (Pydantic model):
- `PathsConfig`: Input/output/scratch/state directories
- `ConversionConfig`: Writer strategy, workers, validation
- `CalibrationConfig`: SNR thresholds, solution intervals, refant
- `ImagingConfig`: Gridder, masking, catalog validation

### 5.3 Deployment Options

**Systemd Deployment** (Production):
- `contimg-stream.service`: Streaming converter daemon
- `contimg-api.service`: FastAPI monitoring API

**Docker Compose Deployment**:
- `stream`: Streaming worker
- `api`: FastAPI API server
- `scheduler`: Optional nightly mosaic + housekeeping

---

## 6. Testing Strategies

### 6.1 Test Structure

- **Unit Tests** (`tests/unit/`): Individual module testing
- **Integration Tests** (`tests/integration/`): End-to-end workflow testing
- **Science Tests** (`tests/science/`): Scientific validation
- **Validation Tests** (`tests/validation/`): Implementation validation

### 6.2 Testing Approaches

- **Synthetic Data Generation** (`simulation/`): PyUVSim-based test data
- **Mock Stages** (`tests/fixtures/mock_stages.py`): Pipeline stage mocks
- **QA Validation**: Built-in quality checks
- **Catalog Validation**: Flux scale verification

### 6.3 Quality Assurance

- **MS Quality Checks**: After conversion (frequency order, UVW precision, antenna positions)
- **Calibration Quality**: SNR analysis, solution stability, antenna coverage
- **Image Quality**: Beam shape, noise estimation, dynamic range
- **Catalog Validation**: Flux scale verification (NVSS/VLASS)

---

## 7. Code Quality and Engineering Practices

### 7.1 Code Organization

- **Modular Design**: Clear separation of concerns
- **Type Safety**: Pydantic models, type hints
- **Error Handling**: Unified exception hierarchy (`utils/exceptions.py`)
- **Logging**: Structured logging with context
- **Documentation**: Comprehensive docstrings and README files

### 7.2 Design Principles

- **Single Responsibility**: Each module has a clear purpose
- **Dependency Injection**: Configuration passed explicitly
- **Immutability**: Pipeline context is immutable
- **Observability**: Metrics and logging throughout
- **Resilience**: Retry policies and error recovery

### 7.3 Best Practices

- **Database Schema Management**: Centralized schema definitions
- **Migration Support**: Database migrations handled explicitly
- **Resource Management**: Automatic cleanup via context managers
- **Performance Tracking**: Decorators for performance monitoring
- **Validation**: Input validation at boundaries

---

## 8. Key Design Decisions

### 8.1 Pipeline Framework

**Decision**: Declarative pipeline with dependency resolution vs. imperative scripting

**Rationale**:
- Enables retry policies and error recovery
- Clear dependency tracking
- Testable stage isolation
- Observability hooks

**Implementation**: `pipeline/orchestrator.py` with topological sorting

### 8.2 Writer Strategy Pattern

**Decision**: Pluggable writers vs. single conversion path

**Rationale**:
- Performance optimization (parallel subband writing)
- Robustness (CASA compatibility)
- Flexibility (future writer implementations)

**Implementation**: `conversion/strategies/` with `base.py` interface

### 8.3 Calibration Registry

**Decision**: Centralized registry vs. file-based discovery

**Rationale**:
- Validity window tracking (MJD-based)
- Ordered apply lists
- Status management (active/retired/failed)
- Consistency across workers

**Implementation**: `database/registry.py` with SQLite

### 8.4 MS Organization

**Decision**: Organized directory structure vs. flat layout

**Rationale**:
- Clear separation: science/calibrators/failed
- Date-based subdirectories
- Easier data management
- Scalability

**Implementation**: `utils/ms_organization.py` with path mappers

### 8.5 Quality Tiers

**Decision**: Preset quality tiers vs. fine-grained parameters

**Rationale**:
- Prevents accidental low-quality production runs
- Clear trade-offs (development vs. standard vs. high_precision)
- User-friendly defaults

**Implementation**: `imaging/cli_imaging.py` with tier presets

### 8.6 NVSS Masking

**Decision**: NVSS-based masking for imaging vs. no masking

**Rationale**:
- 2-4x faster imaging
- Focuses cleaning on known sources
- Reduces artifacts

**Implementation**: `imaging/cli_imaging.py` with NVSS catalog integration

---

## 9. Future Considerations

### 9.1 Known Limitations

- **Single-node processing**: No distributed processing support
- **CASA dependency**: Tight coupling to CASA (mitigated by WSClean option)
- **SQLite scalability**: May need PostgreSQL for large-scale deployments

### 9.2 Potential Enhancements

- **Distributed processing**: Dask or Ray integration
- **Real-time alerting**: Alert system for ESE candidates
- **Advanced mosaicking**: Multi-scale mosaicking, outlier rejection
- **Machine learning**: Automated quality assessment, anomaly detection

---

## 10. Summary

The DSA-110 Continuum Imaging Pipeline is a sophisticated, production-grade system for processing radio astronomy interferometric data. Its architecture emphasizes:

1. **Streaming-first design**: Automatic processing of incoming data
2. **Modular pipeline framework**: Declarative stages with dependency resolution
3. **Robust state management**: Multi-database tracking of queue, calibration, and products
4. **Comprehensive monitoring**: FastAPI-based API with WebSocket support
5. **Quality assurance**: Built-in QA checks and validation
6. **Production readiness**: systemd and Docker deployment options

The codebase demonstrates strong software engineering practices with clear separation of concerns, type-safe configuration, comprehensive error handling, and extensive documentation. The system is designed for reliability, scalability, and maintainability in a production radio astronomy environment.

---

## Appendix: Key File References

**Entry Points**:
- `conversion/streaming/streaming_converter.py`: Streaming daemon
- `api/routes.py`: API endpoints
- `pipeline/workflows.py`: Pipeline workflow definitions

**Core Logic**:
- `conversion/strategies/hdf5_orchestrator.py`: Conversion orchestrator
- `calibration/calibration.py`: Calibration solving
- `imaging/cli_imaging.py`: Imaging functions
- `pipeline/orchestrator.py`: Pipeline execution engine

**Database**:
- `database/products.py`: Products database schema
- `database/registry.py`: Calibration registry schema
- `conversion/streaming/streaming_converter.py::QueueDB`: Queue database

**Configuration**:
- `pipeline/config.py`: Unified configuration system
- `api/config.py`: API configuration

**Testing**:
- `tests/unit/`: Unit tests
- `tests/integration/`: Integration tests
- `simulation/`: Synthetic data generation
