# Testing Documentation

This directory contains all tests for the DSA-110 Continuum Imaging Pipeline.

## Directory Structure

```
tests/
├── calibration/      # Calibration module tests
├── conversion/       # UVH5/MS conversion tests
├── database/         # Database utility tests
├── e2e/              # End-to-end tests (including frontend)
├── fixtures/         # Shared test fixtures and mock data
├── integration/      # Integration tests
│   ├── absurd/       # Absurd workflow tests
│   ├── catalog/      # Catalog integration tests
│   └── transients/   # Transient detection tests
├── mosaic/           # Mosaic creation tests
├── performance/      # Performance benchmarks
├── science/          # Scientific validation tests
├── scripts/          # Script testing
├── smoke/            # Quick smoke tests
├── unit/             # Unit tests
│   ├── api/          # API endpoint tests
│   ├── calibration/  # Calibration unit tests
│   ├── catalog/      # Catalog unit tests
│   ├── imaging/      # Imaging unit tests
│   ├── mosaic/       # Mosaic unit tests
│   ├── photometry/   # Photometry unit tests
│   ├── pipeline/     # Pipeline stage tests
│   └── qa/           # QA module tests
├── utils/            # Test utilities
└── validation/       # Validation tests
```

## Running Tests

```bash
# Activate environment first
conda activate casa6
cd /data/dsa110-contimg/backend

# Run all tests
python -m pytest tests/ -v

# Smoke tests only (fast, <5 seconds)
python -m pytest tests/smoke/ -v

# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# With coverage
python -m pytest tests/ --cov=dsa110_contimg --cov-report=html

# Specific test file
python -m pytest tests/smoke/test_priority1_quick.py -v
```

## Test Categories

### Smoke Tests (`smoke/`)

Quick verification that critical components work. Run before starting work.

### Unit Tests (`unit/`)

Test individual functions in isolation with mocked dependencies.

### Integration Tests (`integration/`)

Test end-to-end workflows with realistic data.

### Science Tests (`science/`)

Validate scientific correctness (UVW transformations, calibration, etc.)

### Performance Tests (`performance/`)

Benchmark critical operations.

## Test Markers

```python
@pytest.mark.smoke       # Fast smoke tests
@pytest.mark.slow        # Tests taking >10 seconds
@pytest.mark.requires_data  # Requires production data
```

Run by marker:
```bash
python -m pytest -m smoke -v
python -m pytest -m "not slow" -v
```

## Writing New Tests

Place tests in the appropriate subdirectory:
- `unit/<module>/` for unit tests
- `integration/` for integration tests
- `smoke/` for quick verification tests

Use fixtures from `tests/fixtures/` for shared test data.

## Troubleshooting

**"No module named 'dsa110_contimg'"**: Install in dev mode:
```bash
pip install -e .
```

**"casacore not available"**: Activate casa6 environment:
```bash
conda activate casa6
```

**Missing data errors**: Run tests that don't require data:
```bash
python -m pytest -m "not requires_data" -v
```
