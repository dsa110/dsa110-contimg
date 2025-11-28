# Unit Test Examples with Mocking

This directory contains comprehensive examples of unit testing with mocking for
the DSA-110 pipeline.

## Overview

These tests demonstrate how to test pipeline logic **without running actual
CASA/WSClean operations**, making tests fast and reliable.

## Test Files

### `test_imaging_mocked.py`

Examples of testing imaging functions with mocked dependencies:

- Quality tier behavior (development, standard, high_precision)
- Cell size modifications
- Iteration limits
- Datacolumn detection
- WSClean command structure

### `test_nvss_seeding.py`

Examples of testing NVSS seeding logic:

- Primary beam radius calculation
- NVSS radius limitation when pbcor is enabled
- Integration with mocked CASA operations

### `test_quality_tier.py`

Examples of testing quality tier logic:

- Development tier parameter modifications
- Standard tier behavior
- High precision tier settings

## Using the Fixtures

The `conftest.py` file provides reusable fixtures:

### `minimal_test_ms`

Creates a real minimal MS file (once per test session):

```python
def test_something(minimal_test_ms):
    ms_path = minimal_test_ms
    # Use ms_path in your test
```

### `mock_table_factory`

Provides mock CASA table structures based on table name in path:

```python
def test_something(mock_table_factory):
    with patch('casacore.tables.table', side_effect=mock_table_factory):
        # Your test code
        # Handles paths like "ms::FIELD", "ms::SPECTRAL_WINDOW", etc.
```

### `mock_ms_structure`

Provides a dictionary of mock MS table data:

```python
def test_something(mock_ms_structure):
    # Access mock data: mock_ms_structure['MAIN'], mock_ms_structure['FIELD'], etc.
```

### `temp_work_dir`

Provides a temporary directory for test outputs:

```python
def test_something(temp_work_dir):
    ms_path = str(temp_work_dir / "test.ms")
    # Use temp_work_dir for creating test files
```

### `sample_calibration_tables`

Provides mock calibration table paths:

```python
def test_something(sample_calibration_tables):
    bp_table = sample_calibration_tables['bandpass']
    gain_table = sample_calibration_tables['gain']
```

### `mock_wsclean_subprocess`

Mocks WSClean subprocess execution:

```python
def test_wsclean(mock_wsclean_subprocess):
    with patch('subprocess.run', side_effect=mock_wsclean_subprocess):
        # Your test code
```

### `mock_casa_tasks`

Mocks CASA tasks (tclean, exportfits):

```python
def test_imaging(mock_casa_tasks):
    with patch('casatasks.tclean', side_effect=mock_casa_tasks['tclean']):
        # Your test code
```

## Running the Tests

Run all unit tests:

```bash
pytest tests/unit/ -v
```

Run specific test file:

```bash
pytest tests/unit/test_imaging_mocked.py -v
```

Run only fast tests (exclude slow/integration):

```bash
pytest tests/unit/ -m "not slow" -v
```

## Key Patterns

### 1. Mocking CASA Tables

```python
def mock_table_with_data(path, readonly=True):
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=ctx)
    ctx.__exit__ = Mock(return_value=None)
    if "SPECTRAL_WINDOW" in path:
        ctx.getcol.return_value = np.array([[1.4e9, 1.41e9]])
    return ctx

with patch('casacore.tables.table', side_effect=mock_table_with_data):
    # Your test code
```

### 2. Mocking Subprocess Calls

```python
def mock_subprocess(cmd, *args, **kwargs):
    mock_result = Mock()
    mock_result.returncode = 0
    return mock_result

with patch('subprocess.run', side_effect=mock_subprocess):
    # Your test code
```

### 3. Testing Parameter Modifications

```python
with patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean:
    image_ms(ms_path, imagename=imagename, quality_tier="development")

    # Verify parameters were modified correctly
    call_args = mock_wsclean.call_args
    assert call_args[1]['cell_arcsec'] == 8.0  # 4x coarser
```

## Best Practices

1. **Isolate Dependencies**: Mock all external dependencies (CASA, WSClean, file
   I/O)
2. **Test Logic, Not Implementation**: Focus on business logic, not internal
   details
3. **Use Fixtures**: Reuse fixtures from `conftest.py` for consistency
4. **Fast Tests**: Unit tests should run in milliseconds, not minutes
5. **Clear Assertions**: Make it obvious what each test is verifying

## Adding New Tests

When adding new unit tests:

1. Use appropriate fixtures from `conftest.py`
2. Mock all external dependencies
3. Test one behavior per test function
4. Use descriptive test names
5. Add docstrings explaining what is being tested

Example:

```python
@pytest.mark.unit
class TestNewFeature:
    """Test new feature logic."""

    def test_feature_behavior(self, mock_table_factory):
        """Test that feature behaves correctly."""
        # Arrange
        with patch('casacore.tables.table', side_effect=mock_table_factory):
            # Act
            result = your_function()

            # Assert
            assert result == expected_value
```
