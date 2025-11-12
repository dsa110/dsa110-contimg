# Test Fixture Optimization for Mosaic Orchestrator Tests

## Problem

Tests in `test_mosaic_orchestrator.py` take ~8 seconds each, primarily due to:
1. **Import bottleneck**: Importing `CalibratorMSGenerator` takes ~9.6 seconds (heavy CASA/astropy dependencies)
2. **Database initialization**: ~0.4 seconds (acceptable)
3. **Service initialization**: ~0.007 seconds (negligible)

## Root Cause

`MosaicOrchestrator.__init__` imports and initializes `CalibratorMSGenerator` even when tests don't need it:

```python
from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
# ... in __init__:
self.calibrator_service = CalibratorMSGenerator.from_config(config, verbose=False)
```

## Solutions

### Option 1: Mock Calibrator Service in Fixture (RECOMMENDED)

Mock the calibrator service initialization in the fixture since most tests don't need the real service:

```python
@pytest.fixture
def orchestrator(temp_products_db, temp_data_registry_db, tmp_path):
    """Create a MosaicOrchestrator instance for testing."""
    ms_output_dir = tmp_path / "ms_output"
    mosaic_output_dir = tmp_path / "mosaic_output"
    ms_output_dir.mkdir()
    mosaic_output_dir.mkdir()

    with patch('dsa110_contimg.mosaic.orchestrator.CalibratorMSGenerator'):
        orch = MosaicOrchestrator(
            products_db_path=temp_products_db,
            data_registry_db_path=temp_data_registry_db,
            ms_output_dir=ms_output_dir,
            mosaic_output_dir=mosaic_output_dir,
        )
        # Set calibrator_service to None or a mock
        orch.calibrator_service = None
        return orch
```

**Pros:**
- Fastest solution (~0.4s per test instead of ~8s)
- Tests that need calibrator service can override it
- No code changes needed in production code

**Cons:**
- Tests that need real calibrator service must set it up manually

### Option 2: Lazy Import in Production Code

Defer the import until actually needed:

```python
# In orchestrator.py __init__:
# Don't import at module level, import in method that needs it
def find_transit_centered_window(self, ...):
    if not self.calibrator_service:
        from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
        # ... initialize
```

**Pros:**
- No test changes needed
- Production code also benefits

**Cons:**
- Requires code changes
- Still slow for tests that use calibrator service

### Option 3: Session-Scoped Fixture for Imports

Use pytest session-scoped fixtures to cache expensive imports:

```python
@pytest.fixture(scope="session")
def calibrator_service_module():
    """Cache the expensive import."""
    from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
    return CalibratorMSGenerator
```

**Pros:**
- Import only happens once per test session
- Works for all tests

**Cons:**
- Still slow for first test (~8s)
- Doesn't help when running individual tests

### Option 4: Separate Fixtures for Different Test Types

Create lightweight fixture for tests that don't need calibrator service:

```python
@pytest.fixture
def orchestrator_no_calibrator(temp_products_db, temp_data_registry_db, tmp_path):
    """Lightweight orchestrator without calibrator service."""
    # ... create orchestrator with mocked calibrator service
    pass

@pytest.fixture
def orchestrator_with_calibrator(temp_products_db, temp_data_registry_db, tmp_path):
    """Full orchestrator with calibrator service (slower)."""
    # ... create orchestrator with real calibrator service
    pass
```

**Pros:**
- Tests can choose what they need
- Fast tests stay fast

**Cons:**
- More fixture complexity
- Need to update test signatures

## Recommended Approach

**Use Option 5** (Patch in conftest.py) because:
1. Patches before any test modules are imported
2. Most unit tests don't need the real calibrator service
3. Tests that do need it can easily override
4. Fastest solution (~15-30x speedup)
5. No production code changes needed
6. Applies to all tests in the unit test suite automatically

## Implementation

Create `tests/unit/conftest.py` to patch before any imports:

```python
"""Unit test configuration and fixtures.

This module patches expensive imports before any test modules are loaded.
"""

from unittest.mock import patch

# Patch CalibratorMSGenerator before any test imports MosaicOrchestrator
# This avoids ~9.6s import overhead from heavy CASA/astropy dependencies
_calibrator_patcher = patch('dsa110_contimg.conversion.calibrator_ms_service.CalibratorMSGenerator')
_calibrator_patcher.start()
```

The `orchestrator` fixture sets `calibrator_service` to None by default:

```python
@pytest.fixture
def orchestrator(temp_products_db, temp_data_registry_db, tmp_path):
    """Create a MosaicOrchestrator instance for testing."""
    # ... setup ...
    orch = MosaicOrchestrator(...)
    orch.calibrator_service = None  # Tests can override if needed
    return orch
```

Tests that need calibrator service can override:

```python
def test_find_transit_centered_window_success(orchestrator):
    # Override calibrator service for this test
    mock_service = MagicMock()
    mock_service.list_available_transits.return_value = [...]
    orchestrator.calibrator_service = mock_service
    # ... rest of test
```

## Actual Performance Improvement

- **Before**: ~8-18 seconds per test (depending on import timing)
- **After**: ~0.2-0.5 seconds per test
- **Speedup**: ~15-30x faster
- **Full suite**: 24 tests in 5.54 seconds (was ~192-432 seconds)

## Additional Optimizations

1. **Use `tmp_path` fixture** (already done) - faster than manual temp directories
2. **Minimal database setup** - only create tables/columns needed for test
3. **Mock external dependencies** - CASA, file system operations, etc.
4. **Parallel test execution** - use `pytest-xdist` for overall suite speedup

