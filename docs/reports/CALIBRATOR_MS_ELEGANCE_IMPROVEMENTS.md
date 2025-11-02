# Further Elegance Improvements for CalibratorMSGenerator

## Current State Analysis

### What's Good ✅
- Service-oriented architecture
- Database integration
- Progress reporting
- Configuration-driven

### What Could Be Better 🔧

1. **Query Existing MS by Transit Time**: Currently only checks by path, but could query database by calibrator/transit time
2. **Better Error Types**: Generic errors instead of custom exceptions
3. **Validation Layer**: Validate inputs before processing
4. **Query Methods**: Check if MS already exists before generating
5. **Separation of Concerns**: Transit finding and group discovery are mixed
6. **Context Manager**: For resource cleanup
7. **Retry Logic**: For transient failures
8. **Caching**: Cache transit calculations
9. **Builder Pattern**: For complex configurations
10. **Better Integration**: Query database for existing MS files by calibrator

## Proposed Improvements

### 1. Query Existing MS by Transit Time

**Current**: Only checks filesystem and database by exact path

**Improved**: Query database by calibrator name and transit time

```python
def find_existing_ms_for_transit(
    self,
    calibrator_name: str,
    transit_time: Time,
    *,
    tolerance_minutes: float = 5.0
) -> Optional[dict]:
    """Find existing MS for calibrator transit in database.
    
    Queries products DB for MS files matching:
    - Transit time within tolerance
    - Calibrator name (from MS path or metadata)
    
    Returns:
        Dict with ms_path, status, stage, or None if not found
    """
    conn = ensure_products_db(self.products_db)
    
    transit_mjd = transit_time.mjd
    tol_mjd = tolerance_minutes / (24 * 60)
    
    # Query by time range
    rows = conn.execute(
        """
        SELECT path, status, stage, mid_mjd
        FROM ms_index
        WHERE mid_mjd BETWEEN ? AND ?
        ORDER BY ABS(mid_mjd - ?) ASC
        LIMIT 10
        """,
        (transit_mjd - tol_mjd, transit_mjd + tol_mjd, transit_mjd)
    ).fetchall()
    
    conn.close()
    
    # Filter by calibrator name in path
    for row in rows:
        path, status, stage, mid_mjd = row
        if calibrator_name.replace('+', '_').replace('-', '_') in Path(path).stem:
            return {
                "ms_path": Path(path),
                "status": status,
                "stage": stage,
                "mid_mjd": mid_mjd
            }
    
    return None
```

### 2. Custom Exceptions

```python
class CalibratorMSError(Exception):
    """Base exception for calibrator MS generation."""
    pass

class TransitNotFoundError(CalibratorMSError):
    """Raised when no transit is found."""
    pass

class GroupNotFoundError(CalibratorMSError):
    """Raised when no subband group is found."""
    pass

class ConversionError(CalibratorMSError):
    """Raised when conversion fails."""
    pass

class CalibratorNotFoundError(CalibratorMSError):
    """Raised when calibrator not found in catalogs."""
    pass
```

### 3. Input Validation

```python
def _validate_inputs(
    self,
    calibrator_name: str,
    transit_time: Optional[Time],
    window_minutes: int,
    max_days_back: int
) -> None:
    """Validate input parameters."""
    if not calibrator_name or not calibrator_name.strip():
        raise ValueError("Calibrator name cannot be empty")
    
    if window_minutes <= 0:
        raise ValueError("window_minutes must be positive")
    
    if max_days_back <= 0:
        raise ValueError("max_days_back must be positive")
    
    if transit_time is not None and transit_time > Time.now():
        raise ValueError("transit_time cannot be in the future")
    
    if not self.input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {self.input_dir}")
```

### 4. Query Methods

```python
def has_ms_for_transit(
    self,
    calibrator_name: str,
    transit_time: Time,
    *,
    tolerance_minutes: float = 5.0
) -> bool:
    """Check if MS already exists for this transit."""
    existing = self.find_existing_ms_for_transit(
        calibrator_name,
        transit_time,
        tolerance_minutes=tolerance_minutes
    )
    return existing is not None

def list_ms_for_calibrator(
    self,
    calibrator_name: str,
    *,
    limit: int = 10
) -> List[dict]:
    """List all MS files for a calibrator."""
    conn = ensure_products_db(self.products_db)
    
    # Search for calibrator name in path
    cal_pattern = f"%{calibrator_name.replace('+', '_').replace('-', '_')}%"
    
    rows = conn.execute(
        """
        SELECT path, status, stage, mid_mjd, processed_at
        FROM ms_index
        WHERE path LIKE ?
        ORDER BY processed_at DESC
        LIMIT ?
        """,
        (cal_pattern, limit)
    ).fetchall()
    
    conn.close()
    
    return [
        {
            "ms_path": Path(row[0]),
            "status": row[1],
            "stage": row[2],
            "mid_mjd": row[3],
            "processed_at": row[4]
        }
        for row in rows
    ]
```

### 5. Context Manager for Resource Cleanup

```python
class CalibratorMSGenerator:
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Cleanup if needed
        pass
```

### 6. Retry Logic

```python
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec('P')
T = TypeVar('T')

def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for retrying operations."""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise
            raise last_error
        return wrapper
    return decorator
```

### 7. Transit Caching

```python
from functools import lru_cache
from typing import Dict, Tuple

class CalibratorMSGenerator:
    def __init__(self, ...):
        ...
        self._transit_cache: Dict[Tuple[str, float], dict] = {}
    
    @lru_cache(maxsize=100)
    def _get_transit_times(
        self,
        calibrator_name: str,
        max_days_back: int
    ) -> Tuple[Time, ...]:
        """Cache transit time calculations."""
        ra_deg, _ = self._load_radec(calibrator_name)
        transits = previous_transits(ra_deg, start_time=Time.now(), n=max_days_back)
        return tuple(transits)
```

### 8. Builder Pattern for Complex Configurations

```python
class CalibratorMSBuilder:
    """Builder for calibrator MS generation."""
    
    def __init__(self, generator: CalibratorMSGenerator):
        self.generator = generator
        self.calibrator_name: Optional[str] = None
        self.transit_time: Optional[Time] = None
        self.window_minutes: int = 60
        self.max_days_back: int = 14
        self.output_name: Optional[str] = None
        self.configure_for_imaging: bool = True
        self.register_in_db: bool = True
    
    def for_calibrator(self, name: str) -> CalibratorMSBuilder:
        """Set calibrator name."""
        self.calibrator_name = name
        return self
    
    def at_transit(self, transit_time: Time) -> CalibratorMSBuilder:
        """Set specific transit time."""
        self.transit_time = transit_time
        return self
    
    def with_window(self, minutes: int) -> CalibratorMSBuilder:
        """Set search window."""
        self.window_minutes = minutes
        return self
    
    def output_to(self, name: str) -> CalibratorMSBuilder:
        """Set output filename."""
        self.output_name = name
        return self
    
    def build(self) -> CalibratorMSResult:
        """Generate MS."""
        if not self.calibrator_name:
            raise ValueError("Calibrator name must be set")
        
        return self.generator.generate_from_transit(
            self.calibrator_name,
            transit_time=self.transit_time,
            window_minutes=self.window_minutes,
            max_days_back=self.max_days_back,
            output_name=self.output_name,
            configure_for_imaging=self.configure_for_imaging,
            register_in_db=self.register_in_db
        )
```

### 9. Integration with Future Services

```python
def generate_from_transit(
    self,
    calibrator_name: str,
    *,
    use_transit_matcher: bool = False,  # Future: use TransitDataMatcher
    use_group_discovery: bool = False,   # Future: use SubbandGroupDiscovery
    ...
) -> CalibratorMSResult:
    """Generate MS with optional service integration."""
    
    # Future: Use TransitDataMatcher if available
    if use_transit_matcher:
        # Will use TransitDataMatcher service when implemented
        transit_info = self.transit_matcher.get_latest_transit_with_data(
            calibrator_name,
            max_days_back=max_days_back
        )
    else:
        # Current implementation
        transit_info = self.find_transit(...)
```

### 10. Better Metrics Collection

```python
@dataclass
class CalibratorMSMetrics:
    """Structured metrics for MS generation."""
    transit_found: bool
    transit_search_time: float
    group_found: bool
    group_lookup_time: float
    conversion_time: float
    configuration_time: float
    registration_time: float
    total_time: float
    subbands_count: int
    ms_size_bytes: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "transit_found": self.transit_found,
            "transit_search_time_seconds": self.transit_search_time,
            "group_found": self.group_found,
            "group_lookup_time_seconds": self.group_lookup_time,
            "conversion_time_seconds": self.conversion_time,
            "configuration_time_seconds": self.configuration_time,
            "registration_time_seconds": self.registration_time,
            "total_time_seconds": self.total_time,
            "subbands_count": self.subbands_count,
            "ms_size_bytes": self.ms_size_bytes,
        }
```

## Refactored Example

```python
# Elegant usage with all improvements

from dsa110_contimg.conversion import CalibratorMSGenerator, CalibratorMSConfig

config = CalibratorMSConfig.from_env()
generator = CalibratorMSGenerator.from_config(config)

# Check if MS already exists
if generator.has_ms_for_transit("0834+555", transit_time):
    print("MS already exists!")
    existing = generator.find_existing_ms_for_transit("0834+555", transit_time)
    print(f"Found: {existing['ms_path']}")

# Use builder pattern for complex configuration
result = (generator.builder()
    .for_calibrator("0834+555")
    .with_window(120)
    .output_to("custom_0834.ms")
    .build())

# Or use with context manager
with generator:
    result = generator.generate_from_transit("0834+555")

# List all MS for calibrator
all_ms = generator.list_ms_for_calibrator("0834+555", limit=20)
```

## Priority Recommendations

### High Priority (Immediate Impact)
1. ✅ **Query existing MS by transit time** - Prevents duplicate work
2. ✅ **Custom exceptions** - Better error handling
3. ✅ **Input validation** - Fail fast with clear errors
4. ✅ **Query methods** - Better database integration

### Medium Priority (Nice to Have)
5. **Builder pattern** - For complex configurations
6. **Context manager** - Resource cleanup
7. **Better metrics** - Performance tracking

### Low Priority (Future)
8. **Retry logic** - For transient failures
9. **Caching** - Performance optimization
10. **Service integration** - When TransitDataMatcher exists

## Implementation Impact

- **Lines of code**: +200-300 lines
- **Complexity**: Slightly higher, but better organized
- **Maintainability**: Much better (separation of concerns)
- **Usability**: Significantly better (query methods, builder pattern)
- **Performance**: Better (caching, query optimization)

## Conclusion

These improvements would make the service:
- **More discoverable**: Query methods show what's possible
- **More robust**: Better error handling and validation
- **More flexible**: Builder pattern for complex cases
- **More integrated**: Better database queries
- **More maintainable**: Clear separation of concerns

The improvements are **additive** - they don't break existing code, just enhance it.

