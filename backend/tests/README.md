# Testing Documentation

This directory contains comprehensive tests for the DSA-110 Continuum Imaging
Pipeline.

## Test Categories

### 1. Smoke Tests (`test_smoke.py`)

**Purpose**: Quickly verify that all critical system components are operational.

**When to run**:

- Before starting work
- After major changes
- After environment updates
- As pre-deployment checks

**Run with**:

```bash
cd /data/dsa110-contimg
conda activate casa6
python -m pytest tests/test_smoke.py -v
```

**Expected time**: < 5 seconds

### 2. Unit Tests

**Purpose**: Test individual functions and classes in isolation.

#### Circular Import Tests (`conversion/test_circular_imports.py`)

Tests the lazy loading mechanism in `conversion.strategies.__init__.py` to
prevent infinite recursion.

```bash
python -m pytest tests/conversion/test_circular_imports.py -v
```

#### HDF5 Grouping Tests (`conversion/test_hdf5_grouping.py`)

Tests the proximity-based grouping algorithm for HDF5 files.

```bash
python -m pytest tests/conversion/test_hdf5_grouping.py -v
```

### 3. Integration Tests

**Purpose**: Test end-to-end workflows with real or realistic data.

_Coming soon_: MS conversion, calibrator generation, mosaic creation

## Running All Tests

```bash
# All tests
python -m pytest tests/ -v

# All tests with coverage
python -m pytest tests/ --cov=dsa110_contimg --cov-report=html

# Only smoke tests (fast)
python -m pytest tests/test_smoke.py -v

# Only unit tests
python -m pytest tests/ -k "not integration" -v

# Only tests that don't require production data
python -m pytest tests/ -m "not requires_data" -v
```

## Test Markers

- `@pytest.mark.skipif`: Skips test if condition is true (e.g., missing data)
- `@pytest.mark.slow`: Marks tests that take >10 seconds
- `@pytest.mark.requires_data`: Requires production data to be available

## Critical Tests

These tests verify the bugs we've fixed and must NEVER regress:

1. **Circular Import Prevention** (`test_circular_imports.py`)
   - Prevents `RecursionError` in `conversion.strategies` module
   - Fixed in commit: [reference your commit]

2. **HDF5 Proximity Grouping** (`test_hdf5_grouping.py`)
   - Ensures complete 16-subband groups are found despite timestamp jitter
   - Must find ~90% of sb00 files as complete groups

3. **FIELD Table Reading**
   (`test_smoke.py::TestCASAAvailability::test_can_read_ms_field_table`)
   - Verifies correct use of `casacore.tables.table()` to open subtables
   - Prevents `TypeError: string indices must be integers`

4. **HDF5 Grouping Rule Enforcement** (`test_smoke.py::TestRuleEnforcement`)
   - Ensures the rule file exists and contains critical instructions
   - **NEVER** manually group HDF5 files - always use `query_subband_groups()`

## Continuous Integration

Add these tests to your CI pipeline:

```yaml
test:
  script:
    - conda activate casa6
    - python -m pytest tests/test_smoke.py --junitxml=junit.xml
    - python -m pytest tests/ -k "not integration" --cov=dsa110_contimg
```

## Writing New Tests

### Template for Unit Tests

```python
"""Tests for <module_name>.

These tests ensure <critical functionality> works correctly.
"""

import pytest
from dsa110_contimg.<module> import <function>


class Test<Component>:
    """Test <component> functionality."""

    @pytest.fixture
    def mock_data(self):
        """Create mock data for testing."""
        # Setup
        yield data
        # Teardown

    def test_<specific_behavior>(self, mock_data):
        """Test that <expected behavior> occurs."""
        result = <function>(mock_data)
        assert result == expected
```

### Template for Integration Tests

```python
"""Integration tests for <workflow>.

These tests verify end-to-end functionality with realistic data.
"""

import pytest


@pytest.mark.slow
@pytest.mark.requires_data
class TestE2E<Workflow>:
    """Test complete <workflow> end-to-end."""

    def test_<workflow>_complete(self):
        """Test complete workflow from input to output."""
        # 1. Setup
        # 2. Execute
        # 3. Verify
        pass
```

## Troubleshooting

### Tests fail with "No module named 'dsa110_contimg'"

Ensure you've installed the package in development mode:

```bash
cd /data/dsa110-contimg/src
pip install -e .
```

### Tests fail with "casacore not available"

Ensure you're in the casa6 environment:

```bash
conda activate casa6
```

### Tests fail with missing data

Some tests require production data. Either:

1. Run only tests that don't require data: `pytest -k "not requires_data"`
2. Ensure data is available in `/data/incoming` and `/stage/dsa110-contimg`

## Contact

For questions about testing, consult the main project documentation or ask the
team.
