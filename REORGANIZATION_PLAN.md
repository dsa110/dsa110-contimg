# DSA-110 Pipeline Reorganization Plan

## Executive Summary

This document outlines a comprehensive reorganization plan to transform the dsa110-contimg project from its current organic structure into a clean, intuitive, and maintainable codebase that follows modern Python project standards.

## Current Issues

### 1. Code Duplication and Confusion
- **8+ MS creation modules** in `core/data_ingestion/` with unclear relationships
- **Multiple orchestrators** (`orchestrator.py`, `enhanced_orchestrator.py`)
- **Scattered entry points** (`core/main.py`, `pipeline/main_driver_unified.py`)

### 2. Poor Data Organization
- **Output directories scattered** across root level (`images/`, `mosaics/`, `cal_tables/`)
- **Mixed data types** in same directories
- **No clear data lifecycle** management

### 3. Configuration Complexity
- **Multiple config formats** (YAML, Python modules)
- **Environment-specific configs** buried in subdirectories
- **Unclear precedence** between config sources

### 4. Testing Fragmentation
- **Tests scattered** between `tests/` and root level
- **Legacy tests** mixed with current tests
- **No clear test organization** by functionality

## Proposed Structure

```
dsa110-contimg/
├── README.md                     # Clear project overview
├── pyproject.toml               # Modern Python packaging
├── dsa110_pipeline              # Single CLI entry point
├── src/
│   └── dsa110/                  # Main package
│       ├── __init__.py
│       ├── cli/                 # Command-line interface
│       │   ├── __init__.py
│       │   ├── main.py          # CLI implementation
│       │   └── commands/        # Subcommands
│       ├── pipeline/            # Core pipeline
│       │   ├── __init__.py
│       │   ├── orchestrator.py  # Single orchestrator
│       │   ├── stages/          # Processing stages
│       │   │   ├── __init__.py
│       │   │   ├── ingestion.py
│       │   │   ├── calibration.py
│       │   │   ├── imaging.py
│       │   │   ├── mosaicking.py
│       │   │   └── photometry.py
│       │   └── exceptions.py
│       ├── data/                # Data processing
│       │   ├── __init__.py
│       │   ├── ms_creation.py   # Single MS creation
│       │   ├── hdf5_reader.py   # HDF5 handling
│       │   └── validation.py    # Data validation
│       ├── telescope/           # DSA-110 specific
│       │   ├── __init__.py
│       │   ├── constants.py
│       │   ├── antenna_positions.py
│       │   └── beam_models.py
│       ├── calibration/         # Calibration logic
│       │   ├── __init__.py
│       │   ├── bandpass.py
│       │   ├── gain.py
│       │   └── skymodel.py
│       ├── imaging/             # Imaging logic
│       │   ├── __init__.py
│       │   ├── clean.py
│       │   ├── mosaicking.py
│       │   └── photometry.py
│       ├── utils/               # Utilities
│       │   ├── __init__.py
│       │   ├── logging.py
│       │   ├── config.py
│       │   ├── monitoring.py
│       │   └── casa_interface.py
│       └── services/            # Background services
│           ├── __init__.py
│           ├── file_watcher.py
│           └── processor.py
├── config/
│   ├── default.yaml             # Single default config
│   └── environments/
│       ├── development.yaml
│       ├── testing.yaml
│       └── production.yaml
├── data/                        # All data organized
│   ├── input/                   # Input staging
│   │   └── hdf5/
│   ├── output/                  # All outputs
│   │   ├── ms/                  # Measurement sets
│   │   ├── images/              # Images and mosaics
│   │   ├── calibration/         # Calibration tables
│   │   ├── photometry/          # Photometry results
│   │   └── logs/                # All logs (pipeline + CASA)
│   ├── catalogs/                # Reference catalogs
│   │   ├── calibrators/
│   │   └── sources/
│   └── cache/                   # Temporary files
├── tests/
│   ├── unit/                    # Unit tests by module
│   │   ├── test_pipeline/
│   │   ├── test_data/
│   │   ├── test_calibration/
│   │   └── test_imaging/
│   ├── integration/             # Integration tests
│   ├── e2e/                     # End-to-end tests
│   ├── fixtures/                # Test data
│   └── conftest.py              # Pytest configuration
├── scripts/                     # Utility scripts
│   ├── setup_environment.py
│   ├── validate_installation.py
│   └── diagnostics/
├── docs/
│   ├── index.md
│   ├── quickstart.md
│   ├── user_guide/
│   ├── developer_guide/
│   └── api_reference/
├── examples/
│   ├── basic_usage.py
│   ├── batch_processing.py
│   └── advanced_features.py
└── archive/                     # Legacy code (read-only)
    ├── legacy_pipeline/
    ├── old_tests/
    └── reference_implementations/
```

## Implementation Strategy

### Phase 1: Core Consolidation (Week 1-2)

#### 1.1 Consolidate Data Ingestion
```python
# Single unified MS creation module
# src/dsa110/data/ms_creation.py

class MSCreator:
    """Unified MS creation with all DSA-110 fixes."""
    
    def __init__(self, config):
        self.config = config
        self.antenna_manager = AntennaPositionManager(config)
        
    async def create_ms_from_hdf5(self, hdf5_files, output_path):
        """Single method for HDF5 to MS conversion."""
        # Consolidate logic from all existing converters
        pass
```

#### 1.2 Single Entry Point
```python
# dsa110_pipeline (executable script)
#!/usr/bin/env python3

from src.dsa110.cli.main import main

if __name__ == "__main__":
    main()
```

#### 1.3 Unified Configuration
```yaml
# config/default.yaml
pipeline:
  name: "DSA-110 Continuum Imaging"
  version: "2.0.0"

paths:
  input_dir: "data/input"
  output_dir: "data/output"
  cache_dir: "data/cache"

processing:
  ms_creation:
    antenna_selection: null
    time_tolerance: 120.0
    coordinate_validation: true
  
  calibration:
    bandpass_interval_hours: 8.0
    gain_interval_hours: 1.0
    reference_antennas: ["pad103", "pad001"]
  
  imaging:
    cell_size: "3arcsec"
    image_size: [4800, 4800]
    weighting: "briggs"
    robust: 0.5
```

### Phase 2: Data Organization (Week 2-3)

#### 2.1 Migrate Output Directories
```bash
# Migration script
mkdir -p data/output/{ms,images,calibration,photometry,logs}

# Move existing data
mv images/* data/output/images/
mv mosaics/* data/output/images/mosaics/
mv cal_tables/* data/output/calibration/
mv logs/* casalogs/* data/output/logs/
```

#### 2.2 Implement Data Manager
```python
# src/dsa110/utils/data_manager.py

class DataManager:
    """Centralized data path management."""
    
    def __init__(self, config):
        self.config = config
        self.base_paths = self._setup_paths()
    
    def get_ms_path(self, timestamp):
        """Get standardized MS file path."""
        return self.base_paths['ms'] / f"{timestamp}.ms"
    
    def get_image_path(self, timestamp, image_type):
        """Get standardized image path."""
        return self.base_paths['images'] / image_type / f"{timestamp}.image"
```

### Phase 3: Interface Simplification (Week 3-4)

#### 3.1 Clean CLI Interface
```python
# src/dsa110/cli/main.py

import click

@click.group()
def cli():
    """DSA-110 Continuum Imaging Pipeline."""
    pass

@cli.command()
@click.argument('input_dir')
@click.option('--config', default='config/default.yaml')
@click.option('--output-dir', default='data/output')
def process(input_dir, config, output_dir):
    """Process HDF5 files to final images."""
    # Single command for end-to-end processing
    pass

@cli.command()
@click.argument('hdf5_dir')
def create_ms(hdf5_dir):
    """Convert HDF5 files to Measurement Sets."""
    pass

@cli.command()
@click.argument('ms_files', nargs=-1)
def calibrate(ms_files):
    """Calibrate Measurement Sets."""
    pass
```

#### 3.2 Simplified API
```python
# src/dsa110/__init__.py

from .pipeline.orchestrator import Pipeline
from .data.ms_creation import MSCreator
from .calibration import Calibrator
from .imaging import Imager

# Simple high-level API
def process_observation(hdf5_dir, output_dir=None, config=None):
    """Process complete observation from HDF5 to final products."""
    pipeline = Pipeline(config)
    return pipeline.process_directory(hdf5_dir, output_dir)

def create_measurement_sets(hdf5_files, output_dir=None):
    """Convert HDF5 files to Measurement Sets."""
    creator = MSCreator()
    return creator.batch_convert(hdf5_files, output_dir)
```

### Phase 4: Testing Reorganization (Week 4)

#### 4.1 Structured Test Organization
```
tests/
├── unit/
│   ├── test_pipeline/
│   │   ├── test_orchestrator.py
│   │   └── test_stages.py
│   ├── test_data/
│   │   ├── test_ms_creation.py
│   │   └── test_validation.py
│   └── test_calibration/
├── integration/
│   ├── test_hdf5_to_ms.py
│   ├── test_calibration_pipeline.py
│   └── test_imaging_pipeline.py
├── e2e/
│   └── test_complete_pipeline.py
└── fixtures/
    ├── sample_hdf5/
    ├── sample_ms/
    └── expected_outputs/
```

## Migration Benefits

### 1. **Clarity and Intuition**
- **Single entry point**: `dsa110_pipeline process /path/to/hdf5`
- **Clear data flow**: input → processing → output
- **Obvious file locations**: everything in logical directories

### 2. **Maintainability**
- **No code duplication**: single implementation per function
- **Clear dependencies**: explicit imports and interfaces
- **Modular design**: each component independently testable

### 3. **User Experience**
- **Simple installation**: `pip install .`
- **Clear documentation**: focused on actual usage
- **Predictable behavior**: consistent interfaces throughout

### 4. **Developer Experience**
- **Standard structure**: follows Python packaging conventions
- **Clear testing**: organized by functionality
- **Easy debugging**: centralized logging and error handling

## Implementation Timeline

### Week 1: Core Consolidation
- [ ] Create new directory structure
- [ ] Consolidate MS creation modules
- [ ] Implement single orchestrator
- [ ] Create unified configuration

### Week 2: Data Migration
- [ ] Set up data directory structure
- [ ] Migrate existing outputs
- [ ] Implement data manager
- [ ] Update path references

### Week 3: Interface Development
- [ ] Implement CLI interface
- [ ] Create high-level API
- [ ] Add configuration validation
- [ ] Update documentation

### Week 4: Testing and Validation
- [ ] Reorganize tests
- [ ] Add integration tests
- [ ] Validate migration
- [ ] Performance testing

### Week 5: Documentation and Polish
- [ ] Update all documentation
- [ ] Create migration guide
- [ ] Add examples
- [ ] Final validation

## Risk Mitigation

### 1. **Preserve Legacy Code**
- Keep all existing code in `archive/` directory
- Maintain ability to rollback if needed
- Document migration mapping

### 2. **Gradual Migration**
- Implement new structure alongside existing
- Migrate functionality incrementally
- Validate each step before proceeding

### 3. **Comprehensive Testing**
- Test all migrated functionality
- Compare outputs with legacy system
- Performance regression testing

## Success Metrics

### 1. **Code Quality**
- Reduce code duplication by >80%
- Achieve >90% test coverage
- Zero circular dependencies

### 2. **User Experience**
- Single command for common workflows
- <5 minute setup time for new users
- Clear error messages and debugging

### 3. **Maintainability**
- <50% of current lines of code
- Clear module boundaries
- Comprehensive documentation

This reorganization will transform the DSA-110 pipeline from a complex, organically-grown system into a clean, maintainable, and intuitive scientific software package that follows modern best practices.