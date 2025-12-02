# Backend Directory Structure

## Overview

The `backend/` directory contains the DSA-110 Continuum Imaging Pipeline - a
Python-based system for converting radio telescope visibility data (UVH5 format)
into CASA Measurement Sets and processing them through calibration, imaging, and
source detection pipelines.

> **Detailed API Architecture**: See
> [`backend/docs/ARCHITECTURE.md`](../../backend/docs/ARCHITECTURE.md) for
> in-depth API layer documentation including design patterns, async
> implementation, and testing strategies.

## Directory Tree

```
backend/
├── 📄 Configuration & Setup
│   ├── pyproject.toml           # Project dependencies & metadata
│   ├── alembic.ini              # Database migration config
│   ├── README.md                # Project overview & quick start
│   └── TODO.md                  # Current status & future work
│
├── 📁 docs/                     # Backend-specific documentation
│   ├── ARCHITECTURE.md          # API architecture & design patterns
│   ├── CHANGELOG.md             # Development history & milestones
│   ├── ASYNC_PERFORMANCE_REPORT.md # Async migration benchmarks
│   └── database-adapters.md     # Multi-database abstraction layer
│
├── 📁 src/dsa110_contimg/       # Main Python package
│   │
│   ├── 🌐 api/                  # REST API Layer (FastAPI) - FULLY ASYNC
│   │   ├── app.py               # FastAPI application factory
│   │   ├── config.py            # Centralized configuration
│   │   ├── database.py          # Database connection pooling
│   │   ├── dependencies.py      # FastAPI dependency injection
│   │   ├── exceptions.py        # Custom exception hierarchy
│   │   ├── interfaces.py        # Repository Protocol interfaces
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── repositories.py      # Sync data access layer
│   │   ├── async_repositories.py # Async data access layer (aiosqlite)
│   │   ├── validation.py        # Input validation utilities
│   │   ├── security.py          # Authentication/authorization
│   │   ├── websocket.py         # WebSocket handlers
│   │   ├── job_queue.py         # Background job processing (RQ)
│   │   ├── cache.py             # Redis cache integration
│   │   ├── metrics.py           # Prometheus metrics
│   │   ├── rate_limit.py        # Rate limiting
│   │   ├── services_monitor.py  # External service health checks
│   │   │
│   │   ├── 📁 routes/           # API endpoint handlers (modular)
│   │   │   ├── images.py        # /api/v1/images/*
│   │   │   ├── sources.py       # /api/v1/sources/*
│   │   │   ├── jobs.py          # /api/v1/jobs/*
│   │   │   ├── ms.py            # /api/v1/ms/*
│   │   │   ├── qa.py            # /api/v1/qa/*
│   │   │   ├── cal.py           # /api/v1/cal/*
│   │   │   ├── stats.py         # /api/v1/stats/*
│   │   │   ├── logs.py          # /api/v1/logs/*
│   │   │   ├── queue.py         # /api/v1/queue/*
│   │   │   ├── cache.py         # /api/v1/cache/*
│   │   │   └── services.py      # /api/v1/services/*
│   │   │
│   │   ├── 📁 services/         # Business logic layer
│   │   │   ├── async_services.py # Async service implementations
│   │   │   ├── fits_service.py  # FITS file parsing
│   │   │   ├── qa_service.py    # QA calculations
│   │   │   └── stats_service.py # Statistics computation
│   │   │
│   │   ├── 📁 batch/            # Batch job processing
│   │   │   ├── jobs.py          # Job creation & management
│   │   │   ├── qa.py            # QA metric extraction
│   │   │   └── thumbnails.py    # Thumbnail generation
│   │   │
│   │   ├── 📁 db_adapters/      # Database adapters (SQLite)
│   │   │   ├── backend.py       # DatabaseAdapter Protocol
│   │   │   ├── query_builder.py # Query building utilities
│   │   │   └── adapters/
│   │   │       └── sqlite_adapter.py
│   │   │
│   │   └── 📁 middleware/       # HTTP middleware
│   │       └── exception_handler.py
│   │
│   ├── 🔄 conversion/           # UVH5 → Measurement Set Conversion
│   │   ├── cli.py               # Command-line interface
│   │   ├── helpers*.py          # Helper functions
│   │   ├── ms_utils.py          # MS utilities
│   │   ├── merge_spws.py        # Spectral window merging
│   │   ├── strategies/          # Conversion strategies
│   │   │   ├── writers.py       # Base writer classes
│   │   │   ├── direct_subband.py
│   │   │   └── hdf5_orchestrator.py
│   │   └── streaming/           # Streaming conversion
│   │
│   ├── 📡 calibration/          # Data Calibration
│   │   ├── calibration.py       # Core calibration logic
│   │   ├── applycal.py          # Apply calibration tables
│   │   ├── caltables.py         # Calibration table management
│   │   ├── flagging.py          # Data flagging
│   │   ├── refant_selection.py  # Reference antenna selection
│   │   ├── skymodels.py         # Sky model generation
│   │   ├── diagnostics.py       # Calibration diagnostics
│   │   └── validate.py          # Validation routines
│   │
│   ├── 🖼️ imaging/              # Radio Imaging
│   │   ├── cli.py               # Imaging CLI
│   │   ├── fast_imaging.py      # Fast imaging algorithms
│   │   ├── spw_imaging.py       # Spectral window imaging
│   │   ├── masks.py             # Image masking
│   │   └── export.py            # Image export
│   │
│   ├── 💾 database/             # Data Persistence
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── repositories.py      # Repository implementations
│   │   ├── session.py           # Database session management
│   │   ├── registry.py          # Data registry
│   │   ├── products.py          # Product management
│   │   ├── jobs.py              # Job tracking
│   │   └── hdf5_index.py        # HDF5 file indexing
│   │
│   ├── 📚 catalog/              # Source Catalogs
│   │   ├── query.py             # Catalog queries
│   │   ├── crossmatch.py        # Cross-matching sources
│   │   ├── calibrator_registry.py
│   │   └── external.py          # External catalog access
│   │
│   ├── 🔍 photometry/           # Source Photometry & Detection
│   │   ├── forced.py            # Forced photometry
│   │   ├── ese_detection.py     # Extended source extraction
│   │   ├── variability.py       # Variability analysis
│   │   └── scoring.py           # Source scoring
│   │
│   ├── ⚙️ pipeline/             # Pipeline Orchestration
│   │   └── stages_impl.py       # Pipeline stage implementations
│   │
│   ├── 🛠️ utils/                # Utility Functions
│   │   ├── logging_config.py    # Logging configuration
│   │   ├── coordinates.py       # Coordinate transformations
│   │   ├── fits_utils.py        # FITS utilities
│   │   ├── path_utils.py        # Path utilities
│   │   ├── time_utils.py        # Time utilities
│   │   └── constants.py         # Constants
│   │
│   ├── �� simulation/           # Simulation & Testing
│   │   └── generate_uvh5.py     # Generate synthetic UVH5 data
│   │
│   └── 🔄 migrations/           # Database Migrations (Alembic)
│       ├── env.py               # Migration environment
│       └── versions/            # Migration scripts
│
├── 🧪 tests/                    # Test Suite (782 tests, 72% coverage)
│   ├── conftest.py              # Pytest configuration & fixtures
│   ├── fixtures/                # Test fixtures
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
│
└── 📁 scripts/                  # Utility Scripts
    ├── ops/
    │   ├── run_api.py           # API server launcher
    │   ├── migrate.py           # Alembic CLI wrapper
    │   └── health_check.py      # Health check script
    ├── dev/
    │   └── fix_schemas.py       # Schema utilities
    └── testing/
        └── test_api_endpoints.sh
```

## Architecture Overview

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Routes Layer                      │
│              (routes/*.py - HTTP handlers)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Services Layer                            │
│         (services/*.py - Business logic)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Repositories Layer                          │
│       (async_repositories.py - aiosqlite)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               Database Abstraction Layer                     │
│            (db_adapters/ - SQLite adapters)                 │
└─────────────────────────────────────────────────────────────┘
```

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

## Key Features

### API Layer (Fully Async)

- **Protocol-based interfaces** for type-safe repository abstraction
- **Dependency injection** via FastAPI's `Depends()`
- **Custom exception hierarchy** with consistent JSON responses
- **Lazy configuration loading** for test compatibility
- **Centralized timeout configuration**

### Performance

- 782 tests passing
- 72% code coverage
- Async migration complete (all routes non-blocking)
- P99 latencies improved 10-33%

## Entry Points

1. **API Server**: `python scripts/ops/run_api.py` or
   `uvicorn dsa110_contimg.api.app:app`
2. **Database Migrations**: `python scripts/ops/migrate.py upgrade head`
3. **Conversion CLI**: `python -m dsa110_contimg.conversion.cli`
4. **Imaging CLI**: `python -m dsa110_contimg.imaging.cli`

## Configuration

| Variable            | Default                      | Description       |
| ------------------- | ---------------------------- | ----------------- |
| `DSA110_DB_BACKEND` | `sqlite`                     | Database backend  |
| `PRODUCTS_DB_PATH`  | `/data/.../products.sqlite3` | Products database |
| `REDIS_URL`         | `redis://localhost:6379/0`   | Redis connection  |
| `DSA110_LOG_LEVEL`  | `INFO`                       | Logging level     |

## Related Documentation

- **API Architecture**: [`backend/docs/ARCHITECTURE.md`](../../backend/docs/ARCHITECTURE.md)
- **Development History**: [`backend/docs/CHANGELOG.md`](../../backend/docs/CHANGELOG.md)
- **Performance Benchmarks**: [`backend/docs/ASYNC_PERFORMANCE_REPORT.md`](../../backend/docs/ASYNC_PERFORMANCE_REPORT.md)
- **Database Adapters**: [`backend/docs/database-adapters.md`](../../backend/docs/database-adapters.md)
- **API Reference**: [`reference/api.md`](../reference/api.md)
- **Security Guide**: [`reference/security.md`](../reference/security.md)
