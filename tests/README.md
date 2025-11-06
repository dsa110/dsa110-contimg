# Test Suite Organization

This directory contains the unified test suite for the DSA-110 continuum imaging pipeline.

## Directory Structure

```
tests/
├── pytest.ini                    # Pytest configuration
├── README.md                     # This file
├── README_CALIBRATION_TESTING.md # Comprehensive calibration testing guide
├── unit/                          # Pytest unit tests
│   ├── api/                      # API route tests
│   │   └── test_routes.py
│   ├── simulation/               # Synthetic data validation tests
│   │   └── test_validate_synthetic.py
│   ├── test_calibration_comprehensive.py  # Comprehensive calibration tests
│   ├── test_subband_ordering.py  # Subband ordering tests
│   ├── test_cli_calibration_args.py
│   ├── test_imaging_mocked.py  # Imaging logic tests with mocking (see README_MOCKING_EXAMPLES.md)
│   ├── test_quality_tier.py  # Quality tier behavior tests
│   └── test_nvss_seeding.py  # NVSS seeding logic tests
├── integration/                  # Integration tests
│   ├── test_pipeline_end_to_end.sh  # End-to-end pipeline test (bash)
│   └── test_calibration_workflow.py  # Calibration workflow integration
├── scripts/                      # Standalone test/diagnostic scripts
│   ├── README.md                 # Documentation for standalone scripts
│   ├── test_suite_comprehensive.py
│   ├── test_qa_modules.py
│   ├── test_alerting.py
│   └── ... (other standalone scripts)
└── utils/                        # Test utilities and helpers
    ├── testing.py
    ├── testing_fast.py
    ├── testing_compare_writers.py
    └── ... (utility scripts)
```

## Running Tests

### Pytest Tests (Unit & Integration)

Pytest discovers and runs tests automatically:

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/api/test_routes.py

# Run with verbose output
pytest -v
```

### Standalone Test Scripts

These are run directly as Python scripts:

```bash
# Comprehensive test suite
python tests/scripts/test_suite_comprehensive.py

# QA module tests
python tests/scripts/test_qa_modules.py

# Alerting tests
python tests/scripts/test_alerting.py
```

### End-to-End Integration Test

The bash script for full pipeline testing:

```bash
# Run full end-to-end test
bash tests/integration/test_pipeline_end_to_end.sh

# Skip synthetic data generation (use existing)
bash tests/integration/test_pipeline_end_to_end.sh --skip-synthetic

# Use existing MS (skip conversion)
bash tests/integration/test_pipeline_end_to_end.sh --use-existing-ms /path/to/ms
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual modules and functions in isolation
- **Style**: Pytest with fixtures and assertions
- **Mocking Examples**: See `tests/unit/README_MOCKING_EXAMPLES.md` for comprehensive examples of unit testing with mocked dependencies
- **Fixtures**: Shared fixtures are defined in `tests/conftest.py` (mock tables, temporary directories, etc.)
- **Examples**: API routes, data validation, calibration components
- **New**: Comprehensive calibration tests (`test_calibration_comprehensive.py`, `test_subband_ordering.py`)

### Integration Tests (`tests/integration/`)
- **Purpose**: Test full pipeline workflows end-to-end
- **Style**: Pytest or standalone scripts
- **Examples**: Full pipeline execution, component integration, calibration workflow
- **New**: Calibration workflow integration tests (`test_calibration_workflow.py`)

### Standalone Scripts (`tests/scripts/`)
- **Purpose**: Diagnostic, validation, and comprehensive testing scripts
- **Style**: Direct execution with custom output
- **Examples**: Comprehensive test suites, module-specific validations
- **Note**: These scripts use `sys.path.insert()` to import from the main codebase

### Test Utilities (`tests/utils/`)
- **Purpose**: Helper scripts and utilities for testing
- **Style**: Reusable functions and demo scripts
- **Examples**: Testing helpers, writer comparisons, demo scripts

## Path References

All test scripts automatically find the source code:
- **Pytest tests**: Use `pythonpath = src` in `pytest.ini`
- **Standalone scripts**: Use `sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))`
- **Bash scripts**: Use `REPO_ROOT` calculated from script location

## Adding New Tests

### Adding a Pytest Test

1. Create test file in appropriate directory:
   - `tests/unit/<module>/test_*.py` for unit tests
   - `tests/integration/test_*.py` for integration tests
2. Follow pytest naming conventions (`test_*.py`, `def test_*()`)
3. Use pytest fixtures for setup/teardown

Example:
```python
# tests/unit/calibration/test_bandpass.py
def test_bandpass_solve():
    # Test code here
    pass
```

### Adding a Standalone Test Script

1. Create script in `tests/scripts/`
2. Include path setup:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))
   ```
3. Use descriptive name: `test_<feature>_<purpose>.py`

## Migration Notes

**2025-01-15**: Test directories consolidated:
- Moved from `scripts/tests/` → `tests/scripts/`
- Organized pytest tests into `tests/unit/` and `tests/integration/`
- Moved utilities to `tests/utils/`
- Updated all path references

