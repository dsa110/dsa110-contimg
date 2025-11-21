# Unit Test Suite Guide

## Objective

Develop a comprehensive suite of unit tests with an emphasis on speed and
efficiency, minimizing prolonged test durations.

## Checklist

- [ ] **Test Structure**: Organize tests by module/package, mirroring source
      code structure
- [ ] **Test Coverage**: Cover core functionality, edge cases, and error
      conditions
- [ ] **Mocking**: Use mocks for external dependencies (CASA, file I/O, network)
- [ ] **Speed**: Keep tests fast (<1s per test when possible)
- [ ] **Isolation**: Each test should be independent and not rely on other tests
- [ ] **Validation**: Verify expected behavior, not implementation details
- [ ] **Documentation**: Clear test names and docstrings explaining what is
      being tested

## Test Design

Before implementing each unit test:

1. **Target Functionality**: Ensure the test accurately targets the intended
   functionality and validates the predicted behavior.
2. **Minimize Overhead**: Confirm that each test is effective while keeping
   computational overhead as low as possible.

### Test Structure

```python
"""
Unit tests for [module name].

Tests [what this module does].
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from dsa110_contimg.module import function_to_test


class TestFunctionName:
    """Test [function name] function."""

    def test_basic_functionality(self):
        """Test basic successful case."""
        # Arrange
        input_data = "test_input"

        # Act
        result = function_to_test(input_data)

        # Assert
        assert result == expected_output

    def test_error_handling(self):
        """Test error handling for invalid input."""
        # Arrange
        invalid_input = None

        # Act & Assert
        with pytest.raises(ValidationInputError):
            function_to_test(invalid_input)
```

## Error Handling

Integrate mechanisms to detect and handle faults immediately as they occur,
enabling rapid identification and resolution of issues.

### Error Testing Patterns

```python
def test_missing_file_error(self, tmp_path):
    """Test error when file doesn't exist."""
    file_path = tmp_path / "nonexistent.fits"

    with pytest.raises(ValidationInputError) as exc_info:
        validate_image_quality(str(file_path))

    assert "not found" in str(exc_info.value).lower()

def test_invalid_input_error(self):
    """Test error for invalid input."""
    with pytest.raises(ValidationInputError):
        validate_astrometry(image_path="", catalog="invalid")
```

## Validation

After adding or editing tests, briefly validate their effectiveness and make any
necessary self-corrections based on failures or unexpected outcomes.

### Running Tests

```bash
# Run all unit tests
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/ -v

# Run specific test file
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/test_qa_base.py -v

# Run specific test
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/test_qa_base.py::TestValidationResult::test_to_dict -v

# Run with coverage
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/ --cov=dsa110_contimg.qa --cov-report=html
```

### Test Validation Checklist

- [ ] All tests pass independently
- [ ] Tests run quickly (<1s per test)
- [ ] Tests are isolated (no shared state)
- [ ] Error cases are covered
- [ ] Edge cases are covered
- [ ] Mocks are used for external dependencies

## Current Test Coverage

### QA System Tests

- ✅ **Base Classes** (`test_qa_base.py`)
  - `ValidationContext` initialization
  - `ValidationResult` functionality
  - Exception hierarchy
  - 8 tests, all passing

- ✅ **Configuration** (`test_qa_config.py`)
  - Config class defaults
  - `get_default_config()` singleton
  - `load_config_from_dict()`
  - 7 tests, all passing

- ✅ **Photometry Validation** (`test_qa_photometry_validation.py`)
  - Basic structure created
  - Error handling tests
  - Needs expansion

### Existing Tests

- `test_catalog_validation.py` - Catalog validation tests
- `test_crossmatch.py` - Cross-matching tests
- `test_calibration_comprehensive.py` - Calibration tests
- `test_casa_lazy_imports.py` - CASA import tests
- And more...

## Best Practices

### 1. Use Fixtures for Common Setup

```python
@pytest.fixture
def sample_image_path(tmp_path):
    """Create a sample image file for testing."""
    image_path = tmp_path / "test.fits"
    image_path.touch()
    return str(image_path)

def test_with_fixture(sample_image_path):
    """Test using fixture."""
    result = validate_image_quality(sample_image_path)
    assert result is not None
```

### 2. Mock External Dependencies

```python
@patch("dsa110_contimg.qa.image_quality.casaimage")
def test_with_mock(mock_casaimage):
    """Test with mocked CASA dependency."""
    mock_image = Mock()
    mock_image.shape.return_value = (100, 100)
    mock_casaimage.return_value = mock_image

    result = validate_image_quality("test.fits")
    assert result.nx == 100
```

### 3. Test Edge Cases

```python
def test_empty_input(self):
    """Test with empty input."""
    result = validate_astrometry(image_path="test.fits", catalog_sources=[])
    assert result.n_matched == 0

def test_zero_sources(self):
    """Test with zero detected sources."""
    result = validate_astrometry(image_path="test.fits", catalog_sources=[...])
    assert result.passed is False
```

### 4. Keep Tests Fast

```python
# Good: Fast test with minimal setup
def test_config_defaults(self):
    """Test config defaults."""
    config = get_default_config()
    assert config.astrometry.max_offset_arcsec == 1.0

# Avoid: Slow test with real file I/O
def test_slow_real_file(self):
    """Avoid: This reads real files."""
    result = validate_image_quality("/path/to/real/large/file.fits")  # Slow!
```

## Test Organization

```
tests/unit/
├── test_qa_base.py              # Base classes
├── test_qa_config.py            # Configuration
├── test_qa_photometry_validation.py
├── test_qa_variability_validation.py
├── test_qa_mosaic_validation.py
├── test_qa_streaming_validation.py
├── test_qa_database_validation.py
├── test_catalog_validation.py
├── test_image_quality.py
├── test_ms_quality.py
└── ...
```

## Continuous Improvement

- Regularly review test coverage
- Add tests for new features immediately
- Refactor tests when code changes
- Remove obsolete tests
- Keep test execution time low

## See Also

- [Unit Test Checklist](UNIT_TEST_CHECKLIST.md)
- [Mocking Examples](README_MOCKING_EXAMPLES.md)
- [Testing Strategy](../../docs/AUTOMATED_TESTING_STRATEGY.md)
