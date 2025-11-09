# Architecture Optimization Recommendations for dsa110_contimg

## Executive Summary

This document provides recommendations to optimize the dsa110_contimg architecture for **scientific rigor, precision, correctness, and ease of use**. The analysis is based on a comprehensive review of the codebase structure, documented issues, and architectural patterns.

## Key Findings

### Critical Issues (Affecting Scientific Correctness)
1. **TIME format inconsistencies** - Multiple implementations with different assumptions
2. **RA calculation dependencies** - Correctness depends on TIME conversion accuracy
3. **Code duplication** - Three different `_ms_time_range()` implementations
4. **Unused constants** - `CASA_TIME_OFFSET` defined but never used
5. **Hardcoded values** - Observatory coordinates duplicated across modules

### Moderate Issues (Affecting Maintainability & Ease of Use)
1. **Inconsistent error handling** - Mix of exception types and patterns
2. **Type hints incomplete** - Many functions lack proper type annotations
3. **Configuration scattered** - Defaults in multiple locations
4. **Documentation gaps** - Some modules lack docstrings
5. **Testing coverage** - Could be more comprehensive

---

## Recommendations by Category

### 1. Scientific Rigor & Precision

#### 1.1 Standardize TIME Handling (CRITICAL)

**Current State:**
- Multiple implementations of `_ms_time_range()` with different assumptions
- Inconsistent CASA TIME epoch handling (51544.0 vs 0)
- Format detection logic only in one place

**Recommendation:**
- **Complete migration to `utils/time_utils.py`**: Replace ALL TIME conversions with standardized functions
- **Remove duplicate implementations**: Consolidate `_ms_time_range()` variants in:
  - `database/products.py:324-377`
  - `calibration/apply_service.py:45-87`
  - `imaging/worker.py:39-78`
- **Add validation at boundaries**: Every function that accepts TIME should validate using `validate_time_mjd()`

**Implementation:**
```python
# Replace all manual TIME conversions with:
from dsa110_contimg.utils.time_utils import extract_ms_time_range, casa_time_to_mjd

# Instead of:
t0 = float(times.min()) / 86400.0  # WRONG - no epoch offset

# Use:
start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
```

**Priority:** CRITICAL - Directly affects RA calculations and phase center accuracy

---

#### 1.2 Centralize Physical Constants

**Current State:**
- Observatory coordinates hardcoded in multiple places:
  - `utils/constants.py` (OVRO_LAT, OVRO_LON, OVRO_ALT)
  - `conversion/helpers_coordinates.py:35-38` (duplicated)
  - `conversion/strategies/hdf5_orchestrator.py:116` (default lon)
- `CASA_TIME_OFFSET = 2400000.5` defined but never used

**Recommendation:**
- **Single source of truth**: Use `utils/constants.py` exclusively
- **Remove unused constants**: Delete `CASA_TIME_OFFSET` (replaced by `time_utils.CASA_TIME_EPOCH_MJD`)
- **Import pattern**: All modules should import from `utils.constants`
- **Add validation**: Ensure constants match actual telescope configuration

**Implementation:**
```python
# In all modules, use:
from dsa110_contimg.utils.constants import OVRO_LOCATION

# Remove hardcoded coordinates like:
# lon_deg = -118.2817  # DSA-110 default  ❌
# Use: OVRO_LOCATION.lon.to(u.deg).value  ✓
```

**Priority:** HIGH - Prevents inconsistencies in coordinate calculations

---

#### 1.3 Strengthen Coordinate System Validation

**Current State:**
- RA calculations depend on correct TIME conversion
- Phase center coherence validation exists but could be more comprehensive
- No validation of coordinate frame consistency

**Recommendation:**
- **Add coordinate frame validation**: Ensure all coordinates use consistent frames (ICRS)
- **Validate phase center coherence**: Strengthen `validate_phase_center_coherence()` to check:
  - RA tracks LST within tolerance
  - Phase center IDs match time-dependent phase centers
  - FIELD table PHASE_DIR matches actual phase centers
- **Add unit consistency checks**: Ensure all angles are in radians, frequencies in Hz, etc.

**Implementation:**
```python
# Add to conversion/helpers_validation.py:
def validate_coordinate_consistency(uvdata: UVData) -> List[str]:
    """Validate coordinate system consistency."""
    warnings = []
    
    # Check all phase centers use ICRS frame
    for pc_id, pc in uvdata.phase_center_catalog.items():
        if pc.get('cat_frame') != 'icrs':
            warnings.append(f"Phase center {pc_id} uses frame {pc['cat_frame']}, expected ICRS")
    
    # Check RA tracks LST for meridian phasing
    if uvdata.extra_keywords.get('phase_type') == 'meridian':
        # Validate RA = LST(time) for each phase center
        ...
    
    return warnings
```

**Priority:** HIGH - Ensures scientific correctness of coordinate transformations

---

### 2. Correctness & Reliability

#### 2.1 Eliminate Code Duplication

**Current State:**
- Three implementations of `_ms_time_range()` with different fallback strategies
- Multiple TIME conversion patterns scattered across codebase
- Similar validation logic in multiple modules

**Recommendation:**
- **Create shared utilities module**: `utils/ms_utils.py` for MS-specific operations
- **Consolidate TIME extraction**: Use single `extract_ms_time_range()` from `time_utils`
- **Shared validation functions**: Move common validation to `utils/validation.py`
- **Strategy pattern for MS operations**: Use consistent patterns for MS table access

**Implementation:**
```python
# Create utils/ms_utils.py:
def get_ms_time_range(ms_path: str) -> Tuple[float, float, float]:
    """Standardized MS time range extraction."""
    return extract_ms_time_range(ms_path)

def get_ms_field_ids(ms_path: str) -> List[int]:
    """Get all field IDs from MS."""
    ...

# Replace all _ms_time_range() implementations with:
from dsa110_contimg.utils.ms_utils import get_ms_time_range
start_mjd, end_mjd, mid_mjd = get_ms_time_range(ms_path)
```

**Priority:** HIGH - Reduces bugs from inconsistent implementations

---

#### 2.2 Strengthen Type Safety

**Current State:**
- Many functions lack type hints
- `# type: ignore` comments used frequently
- No mypy configuration visible
- Inconsistent use of `Optional`, `Union`, etc.

**Recommendation:**
- **Add comprehensive type hints**: All public functions should have complete type annotations
- **Use `typing.Protocol` for interfaces**: Define protocols for MS writers, validators, etc.
- **Add type stubs for CASA**: Create `.pyi` files for casacore/casatools if needed
- **Enable strict mypy checking**: Add `mypy.ini` with strict settings
- **Use `dataclasses` consistently**: Replace dict-based configs with dataclasses

**Implementation:**
```python
# Example improvement:
# Before:
def configure_ms_for_imaging(ms_path: str, *, ensure_columns: bool = True):
    ...

# After:
from typing import Protocol
from pathlib import Path

class MSWriter(Protocol):
    """Protocol for MS writer implementations."""
    def write(self, uvdata: UVData, output_path: Path) -> None: ...
    def validate(self) -> List[str]: ...

def configure_ms_for_imaging(
    ms_path: Path | str,
    *,
    ensure_columns: bool = True,
    ensure_flag_and_weight: bool = True,
    do_initweights: bool = True,
) -> None:
    """Configure MS for imaging with full type safety."""
    ...
```

**Priority:** MEDIUM - Improves correctness through static analysis

---

#### 2.3 Improve Error Handling Consistency

**Current State:**
- Mix of exception types: `ValidationError`, `MosaicError`, generic `Exception`
- Some functions return `(bool, Optional[Dict])` tuples
- Inconsistent error context (some have suggestions, some don't)

**Recommendation:**
- **Standardize exception hierarchy**: Create base exception classes
- **Use result types**: Consider `Result[T, E]` pattern for operations that can fail
- **Consistent error context**: All exceptions should include context and suggestions
- **Fail-fast validation**: Validate inputs early with clear error messages

**Implementation:**
```python
# Create utils/exceptions.py:
class DSA110Error(Exception):
    """Base exception for dsa110_contimg."""
    def __init__(self, message: str, context: Optional[Dict] = None, 
                 suggestion: Optional[str] = None):
        super().__init__(message)
        self.context = context or {}
        self.suggestion = suggestion

class ValidationError(DSA110Error):
    """Raised when validation fails."""
    pass

class ConversionError(DSA110Error):
    """Raised when conversion fails."""
    pass

# Use consistently:
if not ms_path.exists():
    raise ValidationError(
        f"MS not found: {ms_path}",
        context={'ms_path': str(ms_path), 'operation': 'read'},
        suggestion='Check file path and permissions'
    )
```

**Priority:** MEDIUM - Improves debuggability and user experience

---

### 3. Ease of Use

#### 3.1 Centralize Configuration Management

**Current State:**
- Defaults in `utils/defaults.py`
- Constants in `utils/constants.py`
- Config classes in `conversion/config.py`, `api/config.py`
- Environment variable handling scattered

**Recommendation:**
- **Single configuration system**: Use Pydantic models for all configuration
- **Hierarchical config**: Support config files, environment variables, CLI args
- **Validation at load time**: Validate all config values on initialization
- **Documentation generation**: Auto-generate config docs from models

**Implementation:**
```python
# Create utils/config.py:
from pydantic import BaseModel, Field, validator
from pathlib import Path
from typing import Optional

class PipelineConfig(BaseModel):
    """Centralized pipeline configuration."""
    
    # Paths
    input_dir: Path = Field(..., description="Input directory for UVH5 files")
    output_dir: Path = Field(..., description="Output directory for MS files")
    products_db: Path = Field(default_factory=lambda: Path("state/products.sqlite3"))
    
    # Conversion
    writer_strategy: str = Field(default="auto", description="MS writer strategy")
    max_workers: int = Field(default=4, ge=1, le=32)
    stage_to_tmpfs: bool = Field(default=True)
    
    # Calibration
    cal_bp_minsnr: float = Field(default=3.0, ge=1.0, le=10.0)
    cal_gain_solint: str = Field(default="inf")
    
    @validator('writer_strategy')
    def validate_writer(cls, v):
        allowed = ['auto', 'parallel-subband', 'pyuvdata']
        if v not in allowed:
            raise ValueError(f"writer_strategy must be one of {allowed}")
        return v
    
    @classmethod
    def from_env(cls) -> 'PipelineConfig':
        """Load from environment variables."""
        ...
    
    @classmethod
    def from_file(cls, path: Path) -> 'PipelineConfig':
        """Load from YAML/JSON file."""
        ...

# Usage:
config = PipelineConfig.from_env()
# or
config = PipelineConfig.from_file(Path("config.yaml"))
```

**Priority:** HIGH - Dramatically improves ease of use and configuration management

---

#### 3.2 Improve API Design & Documentation

**Current State:**
- Some modules lack comprehensive docstrings
- CLI arguments not always well-documented
- No clear entry point documentation
- API models exist but could be more comprehensive

**Recommendation:**
- **Comprehensive docstrings**: All public functions should have:
  - Clear description
  - Parameter documentation
  - Return value documentation
  - Examples
  - Raises section
- **API documentation**: Generate docs from docstrings (Sphinx)
- **CLI help improvements**: Add examples to argparse help text
- **Type hints in docstrings**: Use NumPy or Google style consistently

**Implementation:**
```python
def extract_ms_time_range(
    ms_path: str,
    year_range: Tuple[int, int] = DEFAULT_YEAR_RANGE
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Extract time range from MS using astropy for validation.
    
    This is a robust, standardized implementation that:
    1. Uses msmetadata.timerangeforobs() (most reliable, returns MJD directly)
    2. Falls back to msmetadata.timesforscans() (with proper epoch conversion)
    3. Falls back to main table TIME column (with proper epoch conversion)
    4. Falls back to OBSERVATION table TIME_RANGE (with proper epoch conversion)
    5. Validates all extracted times using astropy
    
    Parameters
    ----------
    ms_path : str
        Path to Measurement Set
    year_range : tuple of int, optional
        Expected year range for validation (default: (2000, 2100))
        
    Returns
    -------
    tuple of (Optional[float], Optional[float], Optional[float])
        (start_mjd, end_mjd, mid_mjd) or (None, None, None) if unavailable
        
    Raises
    ------
    ValidationError
        If MS path is invalid or MS cannot be read
        
    Examples
    --------
    >>> start, end, mid = extract_ms_time_range('observation.ms')
    >>> if mid is not None:
    ...     t = Time(mid, format='mjd')
    ...     print(f"Observation time: {t.isot}")
    """
    ...
```

**Priority:** MEDIUM - Improves developer experience and maintainability

---

#### 3.3 Enhance Testing & Validation

**Current State:**
- Good test structure (unit, integration, science tests)
- Some modules have comprehensive tests
- Validation functions exist but could be more systematic

**Recommendation:**
- **Property-based testing**: Use Hypothesis for TIME conversion, coordinate transformations
- **Scientific validation tests**: Expand `tests/science/` with more validation cases
- **Integration test coverage**: Ensure all pipeline stages have integration tests
- **Validation at module boundaries**: Add validation decorators for critical functions
- **Test data management**: Centralize test data and fixtures

**Implementation:**
```python
# Add property-based tests:
from hypothesis import given, strategies as st

@given(
    time_sec=st.floats(min_value=0, max_value=1e10),
    year_range=st.tuples(st.integers(2000, 2100), st.integers(2000, 2100))
)
def test_casa_time_conversion_properties(time_sec, year_range):
    """Property-based test for TIME conversion."""
    needs_offset, mjd = detect_casa_time_format(time_sec, year_range)
    
    # Property 1: Result should be valid MJD
    assert validate_time_mjd(mjd, year_range)
    
    # Property 2: Round-trip conversion should work
    if needs_offset:
        casa_time_back = mjd_to_casa_time(mjd)
        mjd_back = casa_time_to_mjd(casa_time_back)
        assert abs(mjd - mjd_back) < 1e-6

# Add validation decorators:
from functools import wraps

def validate_ms_path(func):
    """Decorator to validate MS path before function execution."""
    @wraps(func)
    def wrapper(ms_path: str, *args, **kwargs):
        validate_file_path(ms_path, must_exist=True, must_readable=True)
        return func(ms_path, *args, **kwargs)
    return wrapper

@validate_ms_path
def extract_ms_time_range(ms_path: str, ...):
    ...
```

**Priority:** MEDIUM - Improves confidence in correctness

---

#### 3.4 Improve Developer Experience

**Current State:**
- Good logging infrastructure
- Error messages could be more actionable
- Some operations are complex to understand

**Recommendation:**
- **Structured logging**: Use structured logging with context
- **Progress indicators**: Consistent progress bars/indicators
- **Debugging tools**: Add debugging utilities for common issues
- **Clear error messages**: All errors should include:
  - What went wrong
  - Why it might have happened
  - How to fix it
- **Development tools**: Add pre-commit hooks, linting, formatting

**Implementation:**
```python
# Structured logging:
import structlog

logger = structlog.get_logger()

logger.info(
    "Converting subband group",
    group_id=group_id,
    n_files=len(file_list),
    output_path=str(output_path),
    writer=writer_name
)

# Better error messages:
class ConversionError(DSA110Error):
    def __str__(self):
        msg = super().__str__()
        if self.suggestion:
            msg += f"\n\nSuggestion: {self.suggestion}"
        if self.context:
            msg += f"\n\nContext: {self.context}"
        return msg
```

**Priority:** LOW - Nice to have, but not critical

---

## Implementation Priority

### Phase 1: Critical Scientific Correctness (Immediate)
1. Complete TIME handling standardization
2. Centralize physical constants
3. Eliminate code duplication in TIME extraction

### Phase 2: Reliability & Maintainability (Short-term)
1. Strengthen type safety
2. Improve error handling consistency
3. Centralize configuration management

### Phase 3: Developer Experience (Medium-term)
1. Improve API documentation
2. Enhance testing coverage
3. Improve developer tools

---

## Specific Code Changes

### High-Impact Quick Wins

1. **Remove unused constant**:
   ```python
   # utils/constants.py:31
   # DELETE: CASA_TIME_OFFSET = 2400000.5  # Unused, replaced by time_utils
   ```

2. **Replace hardcoded coordinates**:
   ```python
   # conversion/strategies/hdf5_orchestrator.py:116
   # BEFORE:
   lon_deg = -118.2817  # DSA-110 default
   
   # AFTER:
   from dsa110_contimg.utils.constants import OVRO_LOCATION
   lon_deg = OVRO_LOCATION.lon.to(u.deg).value
   ```

3. **Consolidate TIME extraction**:
   ```python
   # Replace all _ms_time_range() implementations with:
   from dsa110_contimg.utils.time_utils import extract_ms_time_range
   start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
   ```

---

## Metrics for Success

### Scientific Rigor
- [ ] All TIME conversions use standardized functions
- [ ] All physical constants come from single source
- [ ] Coordinate transformations validated at boundaries
- [ ] Zero hardcoded coordinate values

### Correctness
- [ ] Zero duplicate implementations of critical functions
- [ ] 100% type hint coverage for public APIs
- [ ] All exceptions include context and suggestions
- [ ] Property-based tests for critical transformations

### Ease of Use
- [ ] Single configuration system
- [ ] All public functions have comprehensive docstrings
- [ ] CLI help includes examples
- [ ] Clear error messages with actionable suggestions

---

## References

- TIME handling issues: `TIME_HANDLING_ISSUES.md`
- RA calculation issues: `RA_CALCULATION_ISSUE.md`
- Test documentation: `tests/README.md`
- Calibration testing: `tests/README_CALIBRATION_TESTING.md`

