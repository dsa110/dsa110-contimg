# DSA-110 Pipeline - Directory Organization Guide

## Overview

This document describes the organized directory structure of the DSA-110 continuum imaging pipeline. The reorganization separates concerns, improves maintainability, and provides clear locations for different types of files.

## **DIRECTORY STRUCTURE**

### **Root Directory**
```
dsa110-contimg/
├── README.md                    # Main project documentation
├── docs/                        # Comprehensive documentation
│   ├── README.md               # Documentation index
│   ├── architecture/           # Architecture documentation
│   ├── organization/           # Organization guides
│   ├── services/               # Services documentation
│   └── development/            # Development documentation
├── dsa_contimg_env.yml          # Conda environment specification
└── [configuration and core directories]
```

### **Core Pipeline (`core/`)**
```
core/
├── pipeline/                    # Pipeline orchestration
│   ├── orchestrator.py         # Basic orchestrator
│   ├── enhanced_orchestrator.py # Advanced orchestrator with Phase 3 features
│   ├── exceptions.py           # Custom exception hierarchy
│   └── stages/                 # Individual processing stages
│       ├── calibration_stage.py
│       ├── imaging_stage.py
│       ├── mosaicking_stage.py
│       └── photometry_stage.py
├── utils/                      # Utility modules
│   ├── logging.py              # Enhanced logging
│   ├── monitoring.py           # Basic monitoring
│   ├── error_recovery.py       # Error recovery system
│   ├── distributed_state.py    # Distributed state management
│   └── config_loader.py        # Configuration management
├── telescope/                  # Telescope-specific code
│   ├── dsa110.py              # DSA-110 constants
│   └── beam_models.py         # Primary beam models
├── data_ingestion/             # Data processing
│   ├── ms_creation.py         # MS creation utilities
│   ├── skymodel.py            # Sky model management
│   └── photometry.py          # Photometry operations
└── messaging/                  # Message queue system
    └── message_queue.py       # Redis-based messaging
```

### **Configuration (`config/`)**
```
config/
├── pipeline_config.yaml        # Base configuration
├── environments/               # Environment-specific configs
│   ├── development.yaml       # Development settings
│   ├── production.yaml        # Production settings
│   └── testing.yaml           # Testing settings
└── schemas/                   # Configuration schemas
```

### **Data Files (`data/`)**
```
data/
├── catalogs/                   # Source catalogs and reference data
│   ├── bcal_candidates_vla.csv
│   ├── cals_94.csv
│   ├── vla_calibrators_parsed.csv
│   └── vlacals.csv
├── calibrators/               # Calibrator data
│   └── vlacals.txt
└── reference/                 # Reference data and templates
```

### **Tools (`tools/`)**
```
tools/
├── utilities/                  # Utility scripts
│   ├── generate_bcal_catalog_from_vlacals.py
│   ├── generate_bcal_catalog_from_vlacals_wlogging.py
│   ├── makems_manual.py
│   └── uvw_diagnostic.py
└── analysis/                  # Analysis notebooks and scripts
    └── inspect_hdf5s.ipynb
```

### **Testing (`tests/`)**
```
tests/
├── unit/                      # Unit tests
│   ├── test_orchestrator.py
│   └── test_telescope.py
├── integration/               # Integration tests
├── fixtures/                  # Test data and fixtures
└── [legacy test files]        # Moved from root directory
    ├── test_ms_creation_10min.py
    ├── test_ms_creation_fix.py
    └── test_pipeline_10min.py
```

### **Examples (`examples/`)**
```
examples/
├── basic_pipeline_example.py      # Basic usage example
└── advanced_pipeline_example.py   # Advanced features example
```

### **Scripts (`scripts/`)**
```
scripts/
└── run_tests.py               # Test runner script
```

### **Monitoring (`monitoring/`)**
```
monitoring/
├── advanced_monitoring.py     # Advanced monitoring system
└── __init__.py
```

### **Services (`services/`)**
```
services/
├── hdf5_watcher/             # HDF5 file monitoring service
├── ms_processor/             # MS processing service
└── variability_analyzer/     # Variability analysis service
```

### **Pipeline (`pipeline/`)**
```
pipeline/
├── main_driver_unified.py    # Unified main driver (current)
└── __init__.py
```

### **Archive (`archive/`)**
```
archive/
├── legacy_pipeline/          # Legacy pipeline code
│   ├── calibration.py
│   ├── imaging.py
│   ├── mosaicking.py
│   ├── photometry.py
│   ├── skymodel.py
│   ├── ms_creation.py
│   ├── ms_creation_v0.py
│   ├── ms_creation_v1.py
│   ├── ms_creation_v2.4.2_backup.py
│   ├── ms_creation_strictcheck.py
│   ├── pipeline_utils.py
│   ├── dsa110_utils.py
│   ├── config_parser.py
│   ├── hdf5_watcher_service.py
│   ├── ms_processor_service.py
│   ├── variability_analyzer.py
│   └── main_driver.py
└── old_scripts/              # Legacy utility scripts
```

### **Testing Directory (`testing/`)**
```
testing/                      # Legacy testing and development code
├── calib/                    # Calibration testing
├── catalog/                  # Catalog generation
├── fluxes/                   # Photometry testing
├── image/                    # Imaging testing
├── makems/                   # MS creation testing
├── mosaic/                   # Mosaicking testing
├── sandbox/                  # Development sandbox
└── skymodel/                 # Sky model testing
```

## **ORGANIZATION PRINCIPLES**

### **1. Separation of Concerns**
- **Core Logic**: All pipeline logic in `core/`
- **Configuration**: Environment-specific configs in `config/`
- **Data**: Reference data and catalogs in `data/`
- **Tools**: Utility scripts in `tools/`
- **Tests**: All tests in `tests/`

### **2. Clear Naming Conventions**
- **Descriptive Names**: Directories and files have clear, descriptive names
- **Consistent Structure**: Similar files grouped in appropriate directories
- **Version Control**: Legacy code preserved in `archive/`

### **3. Easy Navigation**
- **Logical Grouping**: Related files grouped together
- **Clear Hierarchy**: Nested structure reflects relationships
- **Documentation**: README files explain each major directory

## **FILE LOCATION GUIDE**

### **Where to Find Things**

#### **Pipeline Code**
- **Current Pipeline**: `core/pipeline/`
- **Legacy Pipeline**: `archive/legacy_pipeline/`
- **Main Driver**: `pipeline/main_driver_unified.py`

#### **Configuration**
- **Base Config**: `config/pipeline_config.yaml`
- **Environment Configs**: `config/environments/`
- **Environment Setup**: `dsa_contimg_env.yml`

#### **Data Files**
- **Source Catalogs**: `data/catalogs/`
- **Calibrator Data**: `data/calibrators/`
- **Reference Data**: `data/reference/`

#### **Utility Scripts**
- **General Utilities**: `tools/utilities/`
- **Analysis Notebooks**: `tools/analysis/`
- **Test Runner**: `scripts/run_tests.py`

#### **Tests**
- **Unit Tests**: `tests/unit/`
- **Integration Tests**: `tests/integration/`
- **Legacy Tests**: `tests/` (moved from root)

#### **Examples**
- **Basic Examples**: `examples/basic_pipeline_example.py`
- **Advanced Examples**: `examples/advanced_pipeline_example.py`

#### **Documentation**
- **Main README**: `README.md`
- **Documentation Index**: `docs/README.md`
- **Architecture**: `docs/architecture/README.md`
- **Organization**: `docs/organization/README.md`
- **Services**: `docs/services/README.md`
- **Development**: `docs/development/ms_creation/README.md`

## **USAGE PATTERNS**

### **Development Workflow**
1. **Core Development**: Work in `core/` directory
2. **Configuration**: Modify files in `config/environments/`
3. **Testing**: Add tests to `tests/unit/` or `tests/integration/`
4. **Utilities**: Add utility scripts to `tools/utilities/`

### **Production Deployment**
1. **Configuration**: Use `config/environments/production.yaml`
2. **Main Driver**: Use `pipeline/main_driver_unified.py`
3. **Monitoring**: Access dashboard via `monitoring/advanced_monitoring.py`

### **Data Management**
1. **Reference Data**: Store in `data/catalogs/` or `data/calibrators/`
2. **Generated Data**: Store in appropriate subdirectories
3. **Backup**: Archive old data in `archive/`

## **MAINTENANCE**

### **Adding New Files**
- **Core Logic**: Add to appropriate `core/` subdirectory
- **Configuration**: Add to `config/` or `config/environments/`
- **Tests**: Add to `tests/unit/` or `tests/integration/`
- **Utilities**: Add to `tools/utilities/`
- **Documentation**: Add to root directory with descriptive name

### **Moving Files**
- **Legacy Code**: Move to `archive/legacy_pipeline/`
- **Old Scripts**: Move to `archive/old_scripts/`
- **Test Files**: Move to `tests/`
- **Data Files**: Move to appropriate `data/` subdirectory

### **Cleaning Up**
- **Remove Duplicates**: Keep only current versions in active directories
- **Archive Old Code**: Move deprecated code to `archive/`
- **Update Documentation**: Keep README files current

## **BENEFITS OF THIS ORGANIZATION**

### **1. Improved Maintainability**
- **Clear Structure**: Easy to find and modify files
- **Separation of Concerns**: Different types of files in appropriate locations
- **Version Control**: Legacy code preserved but not cluttering active directories

### **2. Better Development Experience**
- **Logical Grouping**: Related files grouped together
- **Easy Navigation**: Clear directory structure
- **Consistent Patterns**: Similar files in similar locations

### **3. Production Readiness**
- **Clean Root**: Root directory contains only essential files
- **Clear Entry Points**: Main drivers and examples easily found
- **Organized Data**: Reference data properly organized

### **4. Team Collaboration**
- **Standard Structure**: Consistent organization across team
- **Clear Ownership**: Different directories for different types of work
- **Easy Onboarding**: New team members can quickly understand structure

This organization provides a clean, maintainable, and scalable structure for the DSA-110 pipeline project.
