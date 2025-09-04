# DSA-110 Continuum Imaging Pipeline - New Architecture

## Overview

This document describes the new, improved architecture for the DSA-110 continuum imaging pipeline. The new architecture addresses the organizational issues identified in the original codebase and provides a more maintainable, scalable, and reliable system.

## Key Improvements

### 1. Unified Pipeline Orchestration

- **Single Source of Truth**: The `PipelineOrchestrator` class eliminates code duplication between batch processing and service-based processing
- **Consistent Processing**: All processing flows through the same, well-tested code path
- **Better Error Handling**: Comprehensive exception hierarchy and error reporting

### 2. Modular Architecture

- **Clear Separation of Concerns**: Each processing stage is implemented as a separate, testable module
- **Dependency Injection**: Configuration and dependencies are injected rather than hardcoded
- **Async/Await Support**: Modern Python async patterns for better performance

### 3. Environment-Specific Configuration

- **Development**: Optimized for testing with smaller data volumes
- **Production**: Full-scale processing with optimized performance
- **Testing**: Minimal data for fast test execution

### 4. Comprehensive Testing

- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: End-to-end pipeline testing
- **Test Fixtures**: Reusable test data and configurations

## Directory Structure

```
dsa110-contimg/
├── core/                           # Core pipeline functionality
│   ├── pipeline/                   # Pipeline orchestration
│   │   ├── orchestrator.py         # Main orchestrator
│   │   ├── exceptions.py           # Custom exceptions
│   │   └── stages/                 # Processing stages
│   │       ├── calibration_stage.py
│   │       ├── imaging_stage.py
│   │       ├── mosaicking_stage.py
│   │       └── photometry_stage.py
│   ├── utils/                      # Utility modules
│   │   ├── logging.py              # Enhanced logging
│   │   ├── monitoring.py           # Health checks & metrics
│   │   └── config_loader.py        # Configuration management
│   ├── telescope/                  # Telescope-specific code
│   │   ├── dsa110.py               # DSA-110 constants
│   │   └── beam_models.py          # Primary beam models
│   └── data_ingestion/             # Data processing
│       ├── ms_creation.py          # MS creation utilities
│       ├── skymodel.py             # Sky model management
│       └── photometry.py           # Photometry operations
├── config/                         # Configuration files
│   ├── environments/               # Environment-specific configs
│   │   ├── development.yaml
│   │   ├── production.yaml
│   │   └── testing.yaml
│   └── schemas/                    # Configuration schemas
├── services/                       # Service implementations
│   ├── hdf5_watcher/              # HDF5 file monitoring
│   ├── ms_processor/              # MS processing service
│   └── variability_analyzer/      # Variability analysis
├── tests/                          # Test suite
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── fixtures/                  # Test data
├── scripts/                        # Utility scripts
│   └── run_tests.py               # Test runner
├── examples/                       # Example usage
│   └── basic_pipeline_example.py  # Basic pipeline example
└── monitoring/                     # Monitoring & metrics
```

## Usage Examples

### Basic Pipeline Processing

```python
from core.pipeline import PipelineOrchestrator
from core.utils.config_loader import load_pipeline_config
from astropy.time import Time

# Load configuration
config = load_pipeline_config(environment="development")

# Initialize orchestrator
orchestrator = PipelineOrchestrator(config)

# Create processing block
block_end_time = Time('2023-01-01T01:00:00', format='isot', scale='utc')
ms_files = ['drift_20230101T000000_00.ms', 'drift_20230101T000500_00.ms']
block = orchestrator.create_processing_block(block_end_time, ms_files)

# Process the block
result = await orchestrator.process_block(block)

if result.success:
    print(f"Processing completed in {result.processing_time:.1f} seconds")
    print(f"Output files: {list(result.output_files.keys())}")
else:
    print(f"Processing failed: {result.errors}")
```

### Batch Processing

```python
# Find blocks for batch processing
blocks_dict = orchestrator.find_ms_blocks_for_batch(
    start_time_iso='2023-01-01T00:00:00',
    end_time_iso='2023-01-01T12:00:00'
)

# Process all blocks
for block_end_time, ms_files in blocks_dict.items():
    block = orchestrator.create_processing_block(block_end_time, ms_files)
    result = await orchestrator.process_block(block)
    print(f"Block {block.block_id}: {'success' if result.success else 'failed'}")
```

### Using the Unified Driver

```bash
# Single block processing
python pipeline/main_driver_unified.py --config config/environments/development.yaml \
    --mode single --block-end-time 2023-01-01T01:00:00 \
    --ms-files drift_20230101T000000_00.ms drift_20230101T000500_00.ms

# Batch processing
python pipeline/main_driver_unified.py --config config/environments/development.yaml \
    --mode batch --start-time 2023-01-01T00:00:00 --end-time 2023-01-01T12:00:00

# Health check
python pipeline/main_driver_unified.py --config config/environments/development.yaml \
    --mode health
```

## Configuration

### Environment-Specific Configuration

The pipeline supports three environments:

- **Development**: Optimized for testing and development
- **Production**: Full-scale processing with optimized performance
- **Testing**: Minimal data for fast test execution

### Configuration Structure

```yaml
# Example configuration structure
paths:
  log_dir: "logs"
  ms_stage1_dir: "data/ms_stage1"
  cal_tables_dir: "data/cal_tables"
  images_dir: "data/images"
  mosaics_dir: "data/mosaics"

services:
  mosaic_duration_min: 60
  mosaic_overlap_min: 10
  ms_chunk_duration_min: 5
  max_concurrent_blocks: 4

calibration:
  fixed_declination_deg: 37.0
  gcal_refant: "pad001"
  gcal_mode: "ap"
  gcal_solint: "30min"

imaging:
  deconvolver: "hogbom"
  gridder: "wproject"
  niter: 5000
  threshold: "1mJy"
  image_size: [4800, 4800]
  cell_size: "3arcsec"
```

## Testing

### Running Tests

```bash
# Run all tests
python scripts/run_tests.py

# Run specific test
python scripts/run_tests.py --test-path tests/unit/test_orchestrator.py

# Run with coverage
python scripts/run_tests.py --coverage

# Run in verbose mode
python scripts/run_tests.py --verbose
```

### Test Structure

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Test Fixtures**: Reusable test data and configurations

## Monitoring and Health Checks

### Health Checks

```python
from core.utils.monitoring import HealthChecker

health_checker = HealthChecker()
health_checks = health_checker.check_all_health(config)

for check in health_checks:
    print(f"{check.name}: {check.status}")
    if check.error_message:
        print(f"  Error: {check.error_message}")
```

### Metrics Collection

```python
from core.utils.monitoring import PipelineMetrics

metrics = PipelineMetrics()
metrics.record_block_processing(
    block_id="test_block",
    success=True,
    processing_time=120.5,
    ms_count=5,
    image_count=5
)

# Get recent metrics
recent_metrics = metrics.get_recent_metrics(hours=24)
success_rate = metrics.get_success_rate(hours=24)
avg_time = metrics.get_average_processing_time(hours=24)
```

## Migration from Old Architecture

### Key Changes

1. **Import Paths**: Update import statements to use the new `core` package structure
2. **Configuration**: Use environment-specific configuration files
3. **Processing**: Use the unified orchestrator instead of separate batch/service code
4. **Error Handling**: Use the new exception hierarchy

### Migration Steps

1. **Update Imports**: Change from `pipeline.module` to `core.pipeline.module`
2. **Load Configuration**: Use `load_pipeline_config()` instead of direct YAML loading
3. **Initialize Orchestrator**: Use `PipelineOrchestrator` instead of direct module calls
4. **Update Error Handling**: Catch specific exceptions from the new hierarchy

## Future Enhancements

### Phase 2: Async Services

- **Message Queues**: Implement Redis/RabbitMQ for service communication
- **Async Processing**: Non-blocking service operations
- **Distributed State**: Shared state management across services

### Phase 3: Advanced Features

- **Error Recovery**: Automatic retry and recovery mechanisms
- **Load Balancing**: Dynamic resource allocation
- **Advanced Monitoring**: Real-time dashboards and alerting

## Contributing

### Development Workflow

1. **Create Feature Branch**: `git checkout -b feature/new-feature`
2. **Write Tests**: Add unit tests for new functionality
3. **Implement Feature**: Follow the established patterns
4. **Run Tests**: Ensure all tests pass
5. **Update Documentation**: Update relevant documentation
6. **Submit Pull Request**: Include description of changes

### Code Standards

- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Include comprehensive docstrings for all public functions
- **Error Handling**: Use the custom exception hierarchy
- **Logging**: Use structured logging with appropriate levels
- **Testing**: Maintain high test coverage

## Support

For questions or issues with the new architecture:

1. **Check Documentation**: Review this README and inline documentation
2. **Run Examples**: Use the provided examples as reference
3. **Check Tests**: Look at test cases for usage patterns
4. **Create Issue**: Submit detailed issue reports with reproduction steps
