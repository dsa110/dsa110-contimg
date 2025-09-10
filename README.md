# DSA-110 Continuum Imaging Pipeline

## **PRODUCTION-READY PIPELINE ARCHITECTURE**

A comprehensive, enterprise-grade continuum imaging pipeline for the DSA-110 radio telescope array with advanced error recovery, distributed state management, and real-time monitoring capabilities.

## **CRITICAL BUG FIXES**

### PyUVData Phase Center Bug (Fixed)
**Issue**: PyUVData's UVH5 reader fails to read phase center coordinates from DSA-110 HDF5 files, causing 36° declination errors in Measurement Sets.

**Root Cause**: PyUVData ignores HDF5 phase center data and falls back to default zenith phase center (90° declination), which gets transformed to incorrect apparent coordinates (~37° declination).

**Solution**: Implemented comprehensive phase center override in `core/data_ingestion/unified_ms_creation.py` that:
- Reads correct coordinates directly from HDF5 files
- Overrides PyUVData's incorrect default values
- Updates phase center catalog with correct coordinates
- Directly modifies MS FIELD table after creation

**Impact**: Ensures accurate field centers for calibration and imaging. See `docs/technical/PYUVDATA_PHASE_CENTER_BUG.md` for detailed analysis.

## **ORGANIZED DIRECTORY STRUCTURE**

```
dsa110-contimg/
├── core/                        # Core pipeline functionality
│   ├── pipeline/               # Pipeline orchestration
│   │   ├── orchestrator.py     # Basic orchestrator
│   │   ├── enhanced_orchestrator.py # Advanced orchestrator (Phase 3)
│   │   ├── exceptions.py       # Custom exception hierarchy
│   │   └── stages/             # Individual processing stages
│   │       ├── calibration_stage.py
│   │       ├── imaging_stage.py
│   │       ├── mosaicking_stage.py
│   │       └── photometry_stage.py
│   ├── utils/                  # Utility modules
│   │   ├── logging.py          # Enhanced logging
│   │   ├── monitoring.py       # Basic monitoring
│   │   ├── error_recovery.py   # Error recovery system (Phase 3)
│   │   ├── distributed_state.py # Distributed state management (Phase 3)
│   │   └── config_loader.py    # Configuration management
│   ├── telescope/              # Telescope-specific code
│   │   ├── dsa110.py          # DSA-110 constants
│   │   └── beam_models.py     # Primary beam models
│   ├── data_ingestion/         # Data processing
│   │   ├── unified_ms_creation.py # Unified MS creation (with phase center fix)
│   │   ├── skymodel.py        # Sky model management
│   │   └── photometry.py      # Photometry operations
│   ├── calibration/            # Calibration algorithms
│   │   └── calibrator_finder.py # Calibrator source finding
│   └── casa/                   # CASA tool wrappers
│       └── calibration_pipeline.py # CASA calibration interface
├── config/                     # Configuration management
│   ├── pipeline_config.yaml   # Base configuration
│   └── environments/          # Environment-specific configs
│       ├── development.yaml   # Development settings
│       ├── production.yaml    # Production settings
│       └── testing.yaml       # Testing settings
├── data/                       # Data files and catalogs
│   ├── catalogs/              # Source catalogs
│   ├── calibrators/           # Calibrator data
│   ├── ms/                    # Measurement Set files
│   ├── hdf5_staging/          # Staged HDF5 files
│   └── reference/             # Reference data
├── docs/                       # Documentation
│   ├── architecture/          # Architecture documentation
│   ├── development/           # Development guides
│   └── organization/          # Project organization
├── scripts/                    # Utility and operational scripts
│   ├── diagnostics/           # Diagnostic tools
│   └── [60+ operational scripts] # Setup, testing, monitoring
├── tools/                      # Analysis and utility tools
│   ├── utilities/             # Utility scripts
│   └── analysis/              # Analysis notebooks
├── tests/                      # Comprehensive test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   ├── e2e/                   # End-to-end tests
│   └── fixtures/              # Test data
├── examples/                   # Usage examples
│   ├── basic_pipeline_example.py      # Basic usage
│   └── advanced_pipeline_example.py   # Advanced features
├── services/                   # Service implementations
│   ├── hdf5_watcher/          # HDF5 file monitoring
│   ├── ms_processor/          # MS processing service
│   └── variability_analyzer/  # Variability analysis
├── logs/                       # Operational logs
│   ├── pipeline/              # Pipeline logs
│   └── casa/                  # CASA logs
├── test_data/                  # Test datasets
└── archive/                    # Legacy code preservation
    ├── legacy_pipeline/       # Original pipeline modules
    ├── testing/               # Legacy testing code
    └── [archived directories] # Historical code and data
```

## **KEY FEATURES**

### **Phase 1: Core Architecture** 
- **Unified Orchestrator**: Single source of truth for all processing
- **Modular Stages**: Clear separation of concerns
- **Consolidated MS Creation**: Unified data processing interface
- **Comprehensive Testing**: Unit and integration tests

### **Phase 2: Configuration & Services**
- **Environment-Specific Configs**: Development, production, testing
- **Enhanced Logging**: Structured logging with context
- **Health Monitoring**: System health checks and metrics
- **Unified Main Driver**: Single interface for all processing modes

### **Phase 3: Advanced Features**
- **Error Recovery**: Circuit breakers, retry mechanisms, failure analysis
- **Distributed State**: Redis-based state management and coordination
- **Message Queuing**: Inter-service communication and event handling
- **Advanced Monitoring**: Real-time metrics, alerting, and web dashboard

## **QUICK START**

### **Basic Usage**
```python
from core.pipeline import PipelineOrchestrator
from core.utils.config_loader import load_pipeline_config

# Load configuration
config = load_pipeline_config(environment="development")

# Initialize orchestrator
orchestrator = PipelineOrchestrator(config)

# Process a block
result = await orchestrator.process_block(block)
```

### **Advanced Usage (Phase 3)**
```python
from core.pipeline import EnhancedPipelineOrchestrator

# Initialize with advanced features
orchestrator = EnhancedPipelineOrchestrator(config)
await orchestrator.initialize_advanced_features()

# Process with error recovery
result = await orchestrator.process_block_with_recovery(block)
```

### **Command Line**
```bash
# Basic processing
python pipeline/main_driver_unified.py --config config/environments/development.yaml --mode batch

# Advanced monitoring
python examples/advanced_pipeline_example.py --example dashboard
```

## **MONITORING DASHBOARD**

Access the real-time monitoring dashboard at `http://localhost:8080`:
- **Health Status**: All services and their health
- **Active Alerts**: Current alerts with severity levels
- **Metrics**: Real-time performance metrics
- **Processing Status**: Current and recent processing blocks

## **DOCUMENTATION**

- **[Documentation Index](docs/README.md)**: Complete documentation overview
- **[Architecture](docs/architecture/README.md)**: Architecture and design documentation
- **[Organization](docs/organization/README.md)**: Project organization and directory structure
- **[Services](docs/services/README.md)**: Service architecture and usage
- **[Development](docs/development/ms_creation/README.md)**: Development and troubleshooting guides

## **INFRASTRUCTURE REQUIREMENTS**

### **Basic Requirements**
- Python 3.8+
- CASA (for radio astronomy processing)
- PyUVData (for HDF5 processing)

### **Phase 3 Requirements**
- Redis server (for distributed state and messaging)
- Additional Python packages: `redis`, `aiohttp`, `aiohttp-cors`

## **ARCHITECTURE BENEFITS**

### **Reliability**
- **Fault Tolerance**: Circuit breakers prevent cascading failures
- **Automatic Recovery**: Retry mechanisms handle transient failures
- **State Persistence**: Distributed state survives service restarts

### **Observability**
- **Real-Time Monitoring**: Live dashboard with key metrics
- **Comprehensive Alerting**: Proactive notification of issues
- **Failure Analysis**: Detailed failure tracking and analysis

### **Scalability**
- **Distributed Processing**: Scale across multiple instances
- **Message Queuing**: Decouple services for better scalability
- **State Management**: Shared state enables coordination

### **Maintainability**
- **Clean Organization**: Well-structured directory layout
- **Modular Design**: Clear separation of concerns
- **Comprehensive Testing**: Unit and integration test coverage
- **Documentation**: Extensive documentation and examples

## **TRANSFORMATION COMPLETE**

The DSA-110 pipeline has been transformed from a basic, monolithic system into a **production-ready, enterprise-grade platform** with advanced reliability, observability, and scalability capabilities.

## Docs Index

- Architecture
  - docs/architecture/README.md
  - docs/architecture/phase3_features.md
- Development (MS creation)
  - docs/development/ms_creation/README.md
  - docs/development/ms_creation/issues_and_fixes.md
- Organization
  - docs/organization/README.md
  - docs/organization/directory_structure.md
- Services
  - docs/services/README.md
- Test Data
  - test_data/README.md
  - test_data/test_files_summary.md

## UVW Geometry Validation Playbook

Use this playbook whenever you see messages like “the uvw_array does not match the expected values given the antenna positions …”.

Resolution adopted
- Do not scale antenna positions to “fit” UVW magnitudes.
- Set antenna positions and `telescope_location`, then recompute UVWs from positions.
- Do not overwrite UVWs after MS write; keep UVWs consistent with antenna positions.
- Write MS with: `fix_autos=True`, `force_phase=True`, `run_check=False`.

Generate MS (example)
```bash
python - << 'PY'
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.pipeline.orchestrator import PipelineOrchestrator

config = {
    'paths': {'ms_stage1_dir': 'data/ms', 'log_dir': 'logs'},
    'ms_creation': {
        'same_timestamp_tolerance': 30.0,
        'min_data_quality': 0.7,
        'max_missing_subbands': 6,
        'min_integration_time': 10.0,
    },
}

async def run():
    o = PipelineOrchestrator(config)
    ms_files = await o.process_hdf5_to_ms('/data/incoming_test')
    print(ms_files)

asyncio.run(run())
PY
```

Validate UVW geometry
```bash
python scripts/validate_uvw.py data/ms/2025-09-05T03:23:14.ms
```

Pass criteria
- `uvw_delta_max_m` ≈ 0.0 and `uvw_delta_rms_m` ≈ 0.0
- No critical errors; autos imag/real ratio ~ 0

What fixed prior issues
- Removed antenna position scaling in `core/data_ingestion/unified_ms_creation.py`.
- Removed post-write UVW restoration (no overwrite of recalculated UVWs).
- Ensured MS writing uses `fix_autos=True` and `force_phase=True`.

Troubleshooting
- If deltas are large: confirm antenna positions are in the expected frame relative to `telescope_location` (as required by PyUVData), and that `telescope_location` is correct.
- Recreate the MS and re-run the validator.