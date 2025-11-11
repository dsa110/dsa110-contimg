# Error Handling & Logging Improvements

**Date:** 2025-11-11  
**Status:** Complete  
**Scope:** API Router Error Handling

---

## Overview

Comprehensive improvements to error handling and logging in API routers, eliminating silent failures and improving observability.

---

## Issues Fixed

### 1. Silent Exception Swallowing

**Problem:** Multiple `except Exception: pass` blocks silently ignored errors, making debugging difficult.

**Locations Fixed:**
- `src/dsa110_contimg/api/routers/photometry.py` (5 locations)
- `src/dsa110_contimg/api/routers/images.py` (4 locations)

**Solution:** Replaced all silent exception handlers with proper logging:
- `logger.warning()` for recoverable errors
- `logger.error()` for unexpected errors  
- `logger.debug()` for non-critical failures

### 2. Test Band-Aid

**Problem:** Test accepted both 200 and 404 status codes, masking mock issues.

**Location:** `tests/unit/api/test_routers.py::test_get_source_detail_success`

**Solution:** Fixed test to properly expect 200 with detailed error message on failure.

### 3. FITS Header Reading Exception Handling

**Problem:** Broad `except Exception: pass` silently failed when reading FITS files.

**Location:** `src/dsa110_contimg/api/routers/images.py`

**Solution:** 
- Specific exception handling for WCS parsing (ValueError, TypeError, AttributeError, KeyError)
- Specific exception handling for FITS I/O (OSError, IOError, KeyError)
- Proper logging at appropriate levels

### 4. Observation Timeline Bug

**Problem:** Used `os.walk()` pattern with `Path.rglob()` which returns Path objects, not tuples.

**Location:** `src/dsa110_contimg/api/data_access.py::fetch_observation_timeline`

**Solution:** Fixed iteration to work with Path objects directly.

---

## Logging Patterns Established

### Warning Level
For recoverable errors that should be monitored:
```python
except Exception as e:
    logger.warning(
        f"Failed to calculate variability metrics for source {source_id}: {e}",
        exc_info=True
    )
```

### Error Level
For unexpected errors:
```python
except Exception as e:
    logger.error(
        f"Unexpected error reading FITS header for image {image_id}: {e}",
        exc_info=True
    )
```

### Debug Level
For non-critical failures:
```python
except (ValueError, TypeError, OSError) as e:
    logger.debug(
        f"Could not parse measured_at timestamp for detection {row.get('id', 'unknown')}: {e}"
    )
```

---

## Specific Exception Types

Instead of broad `except Exception`, we now catch specific exceptions:

**WCS Parsing:**
- `ValueError` - Invalid coordinate values
- `TypeError` - Type mismatches
- `AttributeError` - Missing attributes
- `KeyError` - Missing header keys

**FITS I/O:**
- `OSError` - File system errors
- `IOError` - I/O operation errors
- `KeyError` - Missing FITS header keys

**Timestamp Parsing:**
- `ValueError` - Invalid timestamp format
- `TypeError` - Type mismatches
- `OSError` - System-level errors

---

## Test Improvements

### Observation Timeline Tests
Added 5 comprehensive tests:
1. `test_fetch_observation_timeline_success` - Basic functionality
2. `test_fetch_observation_timeline_empty_dir` - Empty directory handling
3. `test_fetch_observation_timeline_nonexistent_dir` - Nonexistent directory handling
4. `test_fetch_observation_timeline_invalid_filenames` - Invalid filename filtering
5. `test_fetch_observation_timeline_custom_gap_threshold` - Custom gap threshold logic

### Source Detail Test
Fixed to properly validate success case instead of accepting both 200/404.

---

## Results

**Before:**
- 62 tests passing
- 1 test skipped
- Multiple silent exception handlers
- Test band-aids accepting multiple outcomes

**After:**
- 67 tests passing
- 0 tests skipped
- All exception handlers have proper logging
- Tests properly validate expected behavior

---

## Files Modified

1. `src/dsa110_contimg/api/routers/photometry.py`
   - Added logging import
   - Replaced 5 silent exception handlers with logging
   - Specific exception types for timestamp parsing

2. `src/dsa110_contimg/api/routers/images.py`
   - Added logging import
   - Replaced 4 silent exception handlers with logging
   - Specific exception types for WCS and FITS reading

3. `src/dsa110_contimg/api/data_access.py`
   - Fixed `rglob` iteration bug
   - Changed from tuple unpacking to Path object iteration

4. `tests/unit/api/test_routers.py`
   - Fixed source detail test to expect 200
   - Added proper assertions

5. `tests/unit/api/test_data_access.py`
   - Added 5 observation timeline tests
   - Removed skip marker

---

## Related Documentation

- **Error Handling Guide:** `docs/concepts/dashboard_error_handling.md`
- **Code Quality Guide:** `docs/reports/CODE_QUALITY_IMPROVEMENTS_GUIDE.md`
- **Unit Test Summary:** `docs/testing/unit_test_suite_summary.md`

---

**Status:** Complete  
**Impact:** Improved observability, no silent failures, better debugging capabilities

