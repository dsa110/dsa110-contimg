# Contract Testing Guide

## Overview

Contract testing is a cornerstone of the DSA-110 pipeline's testing strategy, 
introduced as part of the Phase 4 complexity reduction effort. Contract tests 
verify that components correctly implement their interfaces and produce expected
outputs.

## Philosophy

> **Contract tests verify actual behavior** with real data structures and minimal
> mocking. They ensure interfaces work correctly at integration boundaries.

Unlike unit tests with heavy mocking, contract tests:
- Use real (or synthetic) data
- Verify outputs, not implementation details
- Test at interface boundaries
- Provide confidence in actual system behavior

## Test Categories

### 1. Conversion Contracts (`test_conversion_contracts.py`)

Tests the UVH5 → MS conversion pipeline output:
- MS directory structure and required tables
- Antenna count and positions (ITRF coordinates)
- Spectral window configuration
- Data shape and type validation
- CASA compatibility checks

### 2. Database Contracts (`test_database_contracts.py`)

Tests unified database schema and operations:
- Schema creation with all required tables
- MS index operations (insert, query, update)
- Images table operations
- Calibration table operations
- Processing queue lifecycle
- Performance metrics recording

### 3. Imaging Contracts (`test_imaging_contracts.py`)

Tests FITS image output:
- File structure and readability
- WCS coordinates and pixel scale
- Synthesized beam parameters
- Data units (Jy/beam)
- Image quality metrics

### 4. Mosaic Contracts (`test_mosaic_contracts.py`)

Tests mosaic pipeline:
- Build operations with multiple inputs
- QA validation
- Tier selection (quicklook, science, deep)
- Job orchestration
- Database schema for mosaic tracking

### 5. Calibration Contracts (`test_calibration_contracts.py`)

Tests calibration operations:
- Caltable discovery
- Validation functions
- Transit time calculations
- Flagging operations
- Applycal API

### 6. API Contracts (`test_api_contracts.py`)

Tests REST API responses:
- Health endpoint schemas
- Error response formats
- Pagination handling
- Content-type headers
- OpenAPI schema availability

## Running Contract Tests

```bash
# Activate environment
conda activate casa6
cd /data/dsa110-contimg/backend

# Run all contract tests
python -m pytest tests/contract/ -v

# Run specific contract test file
python -m pytest tests/contract/test_conversion_contracts.py -v

# Run with warnings suppressed (for pyuvdata deprecation notices)
python -m pytest tests/contract/ -v -W ignore::DeprecationWarning

# Run with coverage
python -m pytest tests/contract/ --cov=src/dsa110_contimg --cov-report=term-missing
```

## Test Fixtures

Contract tests use fixtures defined in `tests/conftest.py`:

- `synthetic_ms_path`: Generated MS for conversion testing
- `synthetic_fits_path`: Generated FITS for imaging testing
- `test_pipeline_db`: Clean database instance
- `api_client`: FastAPI TestClient for API testing

## Adding New Contract Tests

When adding new contract tests:

1. **Identify the contract**: What interface/behavior are you testing?
2. **Use minimal mocking**: Prefer real data over mocked dependencies
3. **Test outputs**: Verify the result, not the implementation
4. **Add to appropriate file**: Choose the right category or create new

Example structure:
```python
class TestNewFeatureContract:
    """Contract tests for new feature."""

    def test_output_format(self, fixture):
        """Verify output has expected format."""
        result = feature_function(fixture)
        assert result.shape == expected_shape
        assert result.dtype == expected_dtype

    def test_handles_edge_case(self, fixture):
        """Verify edge case handling."""
        with pytest.raises(ValueError):
            feature_function(bad_input)
```

## CI Integration

Contract tests run in GitHub Actions as part of the `validation-tests.yml` workflow:

- **Job**: `contract-tests`
- **Trigger**: Push to master/master-dev, PRs
- **Environment**: Python 3.11, pytest

The contract test job runs independently of unit tests to provide fast feedback
on interface changes.

## Relationship to Other Tests

| Test Type | Purpose | Mocking | Speed |
|-----------|---------|---------|-------|
| Contract | Verify interfaces | Minimal | Fast |
| Unit | Test isolated logic | Heavy | Fast |
| Integration | End-to-end flow | None | Slow |
| Validation | Production checks | None | Slow |

Contract tests bridge the gap between fast unit tests and slow integration tests,
providing confidence in interface behavior without the overhead of full end-to-end
testing.

## Current Status

As of Phase 4 completion:
- **108 contract tests** across 6 files
- **Coverage**: Conversion, Database, Imaging, Mosaic, Calibration, API
- **CI Integration**: Dedicated job in validation-tests.yml
