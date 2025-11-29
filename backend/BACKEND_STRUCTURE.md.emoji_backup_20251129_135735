# Backend Directory Structure

## Overview

The `backend/` directory contains the DSA-110 Continuum Imaging Pipeline - a Python-based system for converting radio telescope visibility data (UVH5 format) into CASA Measurement Sets and processing them through calibration, imaging, and source detection pipelines.

## Directory Tree

```
backend/
├── 📄 Configuration & Setup
│   ├── pyproject.toml          # Project dependencies & metadata
│   ├── setup.py                 # Package installation script
│   ├── README.md                # Project overview & quick start
│   └── .gitignore               # Git ignore rules
│
├── 📁 src/dsa110_contimg/       # Main Python package
│   │
│   ├── 🌐 api/                  # REST API Layer (FastAPI)
│   │   ├── app.py               # FastAPI application setup
│   │   ├── routes.py            # API endpoint definitions
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── repositories.py      # Database access layer
│   │   ├── errors.py            # Error handling & error envelopes
│   │   ├── cache.py             # Caching utilities
│   │   ├── metrics.py           # Performance metrics
│   │   └── batch_jobs.py        # Batch job management
│   │
│   ├── 🔄 conversion/           # UVH5 → Measurement Set Conversion
│   │   ├── cli.py               # Command-line interface
│   │   ├── helpers*.py          # Helper functions (antenna, coordinates, etc.)
│   │   ├── ms_utils.py          # MS utilities
│   │   ├── merge_spws.py        # Spectral window merging
│   │   ├── strategies/          # Conversion strategies
│   │   │   ├── writers.py       # Base writer classes
│   │   │   ├── direct_subband.py # Direct subband writer
│   │   │   └── hdf5_orchestrator.py # HDF5 orchestration
│   │   └── streaming/           # Streaming conversion
│   │       └── streaming_converter.py
│   │
│   ├── 📡 calibration/         # Data Calibration
│   │   ├── calibration.py       # Core calibration logic
│   │   ├── applycal.py          # Apply calibration tables
│   │   ├── caltables.py         # Calibration table management
│   │   ├── flagging.py          # Data flagging
│   │   ├── refant_selection.py  # Reference antenna selection
│   │   ├── selection.py         # Data selection
│   │   ├── skymodels.py         # Sky model generation
│   │   ├── diagnostics.py       # Calibration diagnostics
│   │   ├── plotting.py          # Calibration plots
│   │   ├── validate.py          # Validation routines
│   │   └── streaming.py         # Streaming calibration
│   │
│   ├── 🖼️ imaging/             # Radio Imaging
│   │   ├── cli.py               # Imaging CLI
│   │   ├── cli_imaging.py       # Imaging commands
│   │   ├── cli_utils.py         # CLI utilities
│   │   ├── fast_imaging.py      # Fast imaging algorithms
│   │   ├── spw_imaging.py       # Spectral window imaging
│   │   ├── masks.py             # Image masking
│   │   ├── export.py            # Image export
│   │   ├── nvss_tools.py        # NVSS catalog tools
│   │   └── worker.py             # Imaging worker processes
│   │
│   ├── 💾 database/            # Data Persistence
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── repositories.py      # Repository pattern implementations
│   │   ├── session.py           # Database session management
│   │   ├── registry.py          # Data registry
│   │   ├── data_registry.py     # Data registration
│   │   ├── products.py          # Product management
│   │   ├── jobs.py              # Job tracking
│   │   ├── provenance.py        # Provenance tracking
│   │   ├── calibrators.py       # Calibrator catalog
│   │   └── hdf5_index.py        # HDF5 file indexing
│   │
│   ├── 📚 catalog/             # Source Catalogs
│   │   ├── query.py             # Catalog queries
│   │   ├── crossmatch.py        # Cross-matching sources
│   │   ├── calibrator_registry.py # Calibrator registry
│   │   ├── calibrator_integration.py # Calibrator integration
│   │   ├── external.py         # External catalog access
│   │   ├── builders.py         # Catalog builders
│   │   ├── build_*.py          # Catalog build scripts (ATNF, FIRST, NVSS, etc.)
│   │   ├── astrometric_calibration.py # Astrometric calibration
│   │   ├── flux_monitoring.py   # Flux monitoring
│   │   ├── spectral_index.py    # Spectral index calculations
│   │   ├── transient_detection.py # Transient detection
│   │   ├── multiwavelength.py   # Multi-wavelength analysis
│   │   └── coverage.py          # Coverage analysis
│   │
│   ├── 🔍 photometry/          # Source Photometry & Detection
│   │   ├── forced.py            # Forced photometry
│   │   ├── ese_detection.py     # Extended source extraction
│   │   ├── ese_detection_enhanced.py # Enhanced ESE
│   │   ├── ese_pipeline.py      # ESE pipeline
│   │   ├── adaptive_photometry.py # Adaptive photometry
│   │   ├── adaptive_binning.py  # Adaptive binning
│   │   ├── multi_frequency.py   # Multi-frequency analysis
│   │   ├── multi_observable.py  # Multi-observable analysis
│   │   ├── variability.py        # Variability analysis
│   │   ├── scoring.py            # Source scoring
│   │   ├── thresholds.py        # Detection thresholds
│   │   ├── aegean_fitting.py    # Aegean source fitting
│   │   ├── caching.py           # Caching utilities
│   │   ├── normalize.py         # Normalization
│   │   ├── manager.py           # Photometry manager
│   │   ├── source.py            # Source models
│   │   ├── worker.py            # Worker processes
│   │   ├── parallel.py          # Parallel processing
│   │   └── cli.py               # CLI interface
│   │
│   ├── ⚙️ pipeline/            # Pipeline Orchestration
│   │   └── stages_impl.py       # Pipeline stage implementations
│   │
│   ├── 🛠️ utils/               # Utility Functions
│   │   ├── logging.py           # Logging configuration
│   │   ├── logging_config.py    # Log config
│   │   ├── graphiti_logging.py  # Graphiti logging
│   │   ├── coordinates.py       # Coordinate transformations
│   │   ├── angles.py            # Angle utilities
│   │   ├── ms_helpers.py        # MS helper functions
│   │   ├── ms_locking.py        # MS file locking
│   │   ├── ms_organization.py   # MS organization
│   │   ├── hdf5_io.py           # HDF5 I/O
│   │   ├── fits_utils.py        # FITS utilities
│   │   ├── path_utils.py        # Path utilities
│   │   ├── path_validation.py   # Path validation
│   │   ├── time_utils.py        # Time utilities
│   │   ├── time_validation.py   # Time validation
│   │   ├── validation.py        # General validation
│   │   ├── exceptions.py        # Custom exceptions
│   │   ├── error_context.py     # Error context
│   │   ├── error_messages.py    # Error messages
│   │   ├── constants.py         # Constants
│   │   ├── defaults.py          # Default values
│   │   ├── naming.py            # Naming conventions
│   │   ├── regions.py           # Region handling
│   │   ├── fringestopping.py    # Fringe stopping
│   │   ├── fitting.py           # Fitting routines
│   │   ├── parallel.py          # Parallel processing
│   │   ├── numba_accel.py       # Numba acceleration
│   │   ├── gpu_utils.py         # GPU utilities
│   │   ├── performance.py       # Performance utilities
│   │   ├── profiling.py         # Profiling
│   │   ├── progress.py          # Progress tracking
│   │   ├── tempdirs.py          # Temporary directories
│   │   ├── locking.py           # File locking
│   │   ├── fast_meta.py         # Fast metadata
│   │   ├── casa_init.py         # CASA initialization
│   │   ├── cli_helpers.py       # CLI helpers
│   │   ├── python_version_guard.py # Python version checks
│   │   ├── runtime_safeguards.py # Runtime safeguards
│   │   └── antpos_local/        # Antenna position data
│   │
│   ├── 🧪 simulation/          # Simulation & Testing
│   │   └── generate_uvh5.py     # Generate synthetic UVH5 data
│   │
│   ├── 📖 docsearch/            # Documentation Search
│   │   └── cli.py               # Documentation search CLI
│   │
│   └── 🔄 migrations/           # Database Migrations (Alembic)
│       ├── env.py               # Migration environment
│       └── versions/            # Migration scripts
│           └── 0001_baseline.py
│
├── 🧪 tests/                    # Test Suite
│   ├── conftest.py              # Pytest configuration & fixtures
│   ├── fixtures/                # Test fixtures
│   │   └── writers.py           # Writer fixtures
│   ├── unit/                    # Unit Tests
│   │   ├── test_routes.py       # API route tests
│   │   ├── test_repositories_orm.py # Repository tests
│   │   ├── test_database_orm.py # Database ORM tests
│   │   ├── test_errors.py       # Error handling tests
│   │   ├── test_exceptions.py   # Exception tests
│   │   ├── test_logging_config.py # Logging tests
│   │   ├── test_conversion_errors.py # Conversion error tests
│   │   └── conversion/          # Conversion tests
│   │       └── test_helpers.py
│   └── integration/             # Integration Tests
│       └── (integration test files)
│
├── 📁 scripts/                  # Utility Scripts
│   ├── run_api.py               # API server launcher
│   ├── run_api.sh               # API server shell script
│   ├── health_check.py          # Health check script
│   ├── ensure_port.py           # Port availability check
│   └── fix_schemas.py           # Schema fixer
│
├── 📁 docs/                     # Documentation
│   ├── README.md                # Documentation index
│   └── runbooks/                # Operational runbooks
│       └── troubleshooting_common_scenarios.md
│
└── 📄 Project Files
    ├── API_IMPLEMENTATION_SUMMARY.md # API implementation notes
    ├── NEXT_STEPS.md             # Next steps document
    ├── test_api_endpoints.sh     # API endpoint test script
    └── .coverage                 # Test coverage data
```

## Module Relationships

### Data Flow
```
UVH5 Files → conversion/ → Measurement Sets → calibration/ → Calibrated MS
                                                                    ↓
                                                              imaging/ → Images
                                                                    ↓
                                                          photometry/ → Sources
                                                                    ↓
                                                           catalog/ → Catalog
```

### API Layer
```
FastAPI (api/app.py)
    ↓
Routes (api/routes.py)
    ↓
Repositories (api/repositories.py)
    ↓
Database (database/)
```

### Pipeline Orchestration
```
pipeline/stages_impl.py
    ├──→ conversion/
    ├──→ calibration/
    ├──→ imaging/
    └──→ photometry/
```

## Key Concepts

### 1. **Conversion** (`conversion/`)
- Converts UVH5 (HDF5) visibility data to CASA Measurement Sets
- Supports multiple strategies (direct subband, streaming)
- Handles antenna coordinates, telescope models, validation

### 2. **Calibration** (`calibration/`)
- Applies calibration solutions to data
- Manages calibration tables
- Performs flagging and reference antenna selection
- Generates sky models for self-calibration

### 3. **Imaging** (`imaging/`)
- Creates radio images from calibrated Measurement Sets
- Supports fast imaging and spectral window imaging
- Handles image masking and export

### 4. **Photometry** (`photometry/`)
- Detects sources in images (forced photometry, ESE)
- Performs variability analysis
- Multi-frequency and multi-observable analysis

### 5. **Catalog** (`catalog/`)
- Manages source catalogs (ATNF, FIRST, NVSS, etc.)
- Cross-matches sources across catalogs
- Calibrator registry and integration
- Astrometric calibration

### 6. **Database** (`database/`)
- SQLAlchemy ORM models for all data products
- Repository pattern for data access
- Tracks jobs, products, provenance

### 7. **API** (`api/`)
- FastAPI REST API
- Provides access to images, MS, sources, jobs
- Includes QA endpoints and calibration info

## Entry Points

1. **API Server**: `python -m uvicorn dsa110_contimg.api.app:app`
2. **Conversion CLI**: `python -m dsa110_contimg.conversion.cli`
3. **Imaging CLI**: `python -m dsa110_contimg.imaging.cli`
4. **Photometry CLI**: `python -m dsa110_contimg.photometry.cli`

## Testing Strategy

- **Unit Tests** (`tests/unit/`): Fast, isolated tests with mocks
- **Integration Tests** (`tests/integration/`): End-to-end tests with real data
- **Fixtures** (`tests/fixtures/`): Reusable test data and mocks

## Configuration

- **Dependencies**: `pyproject.toml` (Poetry-style)
- **Database**: SQLite databases in `/data/dsa110-contimg/state/`
- **Logging**: Configured in `utils/logging_config.py`

## Quick Navigation

- **Start here**: `README.md` for overview
- **API docs**: `API_IMPLEMENTATION_SUMMARY.md`
- **Architecture**: `docs/` directory
- **Run API**: `scripts/run_api.py`
- **Test API**: `test_api_endpoints.sh`
