# Developer Guide for dsa110_contimg

This guide provides information for developers working on the DSA-110 continuum imaging pipeline.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Code Organization](#code-organization)
3. [Development Workflow](#development-workflow)
4. [Testing](#testing)
5. [Error Handling](#error-handling)
6. [Type Hints and Documentation](#type-hints-and-documentation)
7. [Common Patterns](#common-patterns)

## Architecture Overview

The dsa110_contimg package is organized into several main stages:

- **Conversion**: UVH5 → CASA Measurement Set (MS)
- **Calibration**: Calibrator selection, bandpass/gain solving, application
- **Imaging**: MS → FITS images using WSClean or CASA
- **Mosaicking**: Combining multiple images into mosaics
- **API**: FastAPI-based monitoring and control interface

### Pipeline Framework

The package uses a declarative pipeline orchestration framework (`src/dsa110_contimg/pipeline/`):
- Dependency-based stage execution
- Retry policies and error recovery
- Immutable context passing
- Structured observability
- See `ARCHITECTURAL_ELEGANCE_BRAINSTORM.md` for design details

**Note:** Legacy subprocess-based execution has been removed. All pipeline execution now uses the new framework.

### Key Design Principles

1. **Scientific Rigor**: All TIME conversions use standardized utilities
2. **Single Source of Truth**: Physical constants (coordinates, epochs) come from `utils/constants.py`
3. **Consistent Error Handling**: All exceptions inherit from `DSA110Error` with context and suggestions
4. **Type Safety**: Public APIs have complete type hints

## Code Organization

### Module Structure

```
dsa110_contimg/
├── conversion/          # UVH5 → MS conversion
│   ├── strategies/      # Different conversion strategies
│   ├── helpers_*.py    # Helper modules (antenna, coordinates, etc.)
│   └── ms_utils.py     # MS configuration utilities
├── calibration/         # Calibration pipeline
│   ├── catalogs.py      # Calibrator catalogs
│   ├── calibration.py   # Core calibration functions
│   └── apply_service.py # Calibration application
├── imaging/             # Imaging pipeline
├── mosaic/              # Mosaicking
├── utils/               # Shared utilities
│   ├── constants.py     # Physical constants (single source of truth)
│   ├── time_utils.py    # TIME conversion utilities
│   ├── exceptions.py    # Unified exception hierarchy
│   └── validation.py   # Validation utilities
└── api/                 # FastAPI monitoring API
```

### Key Modules

#### `utils/constants.py`
**Single source of truth** for physical constants:
- `OVRO_LOCATION`: DSA-110 telescope coordinates
- `TSAMP`, `NINT`: Observation parameters

**Never hardcode coordinates or constants elsewhere!**

#### `utils/time_utils.py`
**Standardized TIME handling**:
- `extract_ms_time_range()`: Extract time range from MS (handles all formats)
- `casa_time_to_mjd()`: Convert CASA TIME to MJD
- `detect_casa_time_format()`: Auto-detect TIME format

**Always use these functions for TIME conversions!**

#### `utils/exceptions.py`
**Unified exception hierarchy**:
- `DSA110Error`: Base exception (all exceptions inherit from this)
- `ValidationError`: Validation failures
- `ConversionError`: Conversion failures
- `CalibrationError`: Calibration failures
- `ImagingError`: Imaging failures

**Always include context and suggestions when raising exceptions!**

## Development Workflow

### Setting Up Development Environment

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Set up CASA environment (see `utils/cli_helpers.py`)

### Making Changes

1. **Create a feature branch**
2. **Follow coding standards**:
   - Use type hints for all public functions
   - Add comprehensive docstrings with examples
   - Use the unified exception hierarchy
   - Never hardcode constants (use `utils/constants.py`)
3. **Run tests**:
   ```bash
   pytest tests/
   ```
4. **Run Codacy analysis**:
   ```bash
   codacy analyze
   ```
5. **Update documentation** if adding new features

### Code Review Checklist

- [ ] All public functions have type hints
- [ ] All public functions have docstrings with examples
- [ ] No hardcoded constants (use `utils/constants.py`)
- [ ] TIME conversions use `utils/time_utils.py`
- [ ] Exceptions include context and suggestions
- [ ] Tests pass
- [ ] Codacy analysis passes

## Testing

### Test Organization

Tests are organized in `tests/` directory:
- `tests/unit/`: Unit tests for individual functions
- `tests/integration/`: Integration tests for full pipelines
- `tests/README.md`: Testing documentation

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_time_utils.py

# Run with coverage
pytest --cov=dsa110_contimg tests/
```

### Writing Tests

1. **Use descriptive test names**: `test_function_name_scenario_expected_result`
2. **Test edge cases**: Empty inputs, boundary conditions, error cases
3. **Use fixtures** for common setup
4. **Mock external dependencies** (CASA, databases)

Example:
```python
def test_extract_ms_time_range_valid_ms_returns_mjd():
    """Test that extract_ms_time_range returns valid MJD for valid MS."""
    ms_path = "tests/data/valid_ms.ms"
    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
    
    assert start_mjd is not None
    assert end_mjd is not None
    assert mid_mjd is not None
    assert start_mjd < end_mjd
    assert abs(mid_mjd - (start_mjd + end_mjd) / 2) < 1e-6
```

## Error Handling

### Using the Unified Exception Hierarchy

**Always use exceptions from `utils/exceptions.py`:**

```python
from dsa110_contimg.utils.exceptions import ConversionError, ValidationError

# Good: Include context and suggestions
if not os.path.exists(ms_path):
    raise ConversionError(
        f"MS does not exist: {ms_path}",
        context={'ms_path': ms_path, 'operation': 'read'},
        suggestion='Check that the MS path is correct and the file exists'
    )

# Bad: Generic exception
if not os.path.exists(ms_path):
    raise RuntimeError(f"MS not found: {ms_path}")
```

### Exception Context

Always include:
- **context**: Dictionary with relevant information (paths, operation names, etc.)
- **suggestion**: Actionable suggestion for fixing the issue

Example:
```python
raise ValidationError(
    errors=[f"Field {field_id} not found"],
    error_types=['field_not_found'],
    error_details=[{'field': field_id, 'available': available_fields}],
    context={'ms_path': ms_path, 'operation': 'calibration'},
    suggestion='Use --auto-fields to auto-select fields'
)
```

## Type Hints and Documentation

### Type Hints

**All public functions must have complete type hints:**

```python
from typing import Optional, List, Tuple

def process_ms(
    ms_path: str,
    field: Optional[str] = None,
    refant: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """Process a Measurement Set."""
    ...
```

### Docstrings

**Use NumPy-style docstrings with examples:**

```python
def configure_ms_for_imaging(
    ms_path: str,
    *,
    ensure_columns: bool = True
) -> None:
    """
    Make a Measurement Set safe and ready for imaging.
    
    Parameters
    ----------
    ms_path : str
        Path to the Measurement Set (directory path).
    ensure_columns : bool, optional
        Ensure MODEL_DATA and CORRECTED_DATA columns exist.
        Default: True
        
    Raises
    ------
    ConversionError
        If MS path does not exist or is not readable.
        
    Examples
    --------
    >>> configure_ms_for_imaging("/path/to/observation.ms")
    
    Notes
    -----
    This function is idempotent (safe to call multiple times).
    """
```

## Common Patterns

### TIME Conversion

**Always use standardized utilities:**

```python
from dsa110_contimg.utils.time_utils import extract_ms_time_range, casa_time_to_mjd

# Extract time range from MS
start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)

# Convert CASA TIME to MJD
mjd = casa_time_to_mjd(time_sec)
```

### Physical Constants

**Always use constants from `utils/constants.py`:**

```python
from dsa110_contimg.utils.constants import OVRO_LOCATION

# Use telescope location
location = OVRO_LOCATION
lon_deg = OVRO_LOCATION.lon.to(u.deg).value
```

### Validation

**Use validation utilities:**

```python
from dsa110_contimg.utils.validation import validate_ms, validate_ms_for_calibration

# Basic MS validation
validate_ms(ms_path, check_empty=True, check_columns=['DATA', 'TIME'])

# Comprehensive validation for calibration
warnings = validate_ms_for_calibration(ms_path, field="0", refant="103")
if warnings:
    logger.warning(f"Validation warnings: {warnings}")
```

### Error Handling

**Use unified exceptions with context:**

```python
from dsa110_contimg.utils.exceptions import ConversionError

try:
    result = risky_operation()
except Exception as e:
    raise ConversionError(
        f"Operation failed: {e}",
        context={'input': input_path, 'operation': 'conversion'},
        suggestion='Check input file format and permissions'
    ) from e
```

## Additional Resources

- **Architecture Recommendations**: `ARCHITECTURE_OPTIMIZATION_RECOMMENDATIONS.md`
- **TIME Handling**: `TIME_HANDLING_ISSUES.md`
- **Testing Guide**: `tests/README.md`
- **API Documentation**: See docstrings in public modules

## Getting Help

- Check existing documentation in the repository
- Review similar code patterns in the codebase
- Ask questions in team channels
- Review `ARCHITECTURE_OPTIMIZATION_RECOMMENDATIONS.md` for design decisions

