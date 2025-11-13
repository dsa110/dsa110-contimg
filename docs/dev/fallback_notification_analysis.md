# Fallback Notification Analysis

## Current State

### Catalog Query Fallbacks

When SQLite databases are unavailable and the system falls back to CSV, users are notified via Python's `warnings.warn()`:

```python
warnings.warn(
    f"SQLite query failed ({e}), falling back to CSV. "
    f"This will be slower (~1s vs ~0.01s).",
    UserWarning,
)
```

### Notification Mechanism

**Current Implementation:**
- Uses Python's standard `warnings.warn()` module
- Warnings are printed to `stderr` by default
- Format: `<filename>:<line>: UserWarning: <message>`
- Example output:
  ```
  /path/to/file.py:1147: UserWarning: SQLite query failed (...), falling back to CSV. This will be slower (~1s vs ~0.01s).
  ```

### Issues with Current Approach

1. **Visibility**: Warnings may be missed if:
   - Output is redirected to a log file
   - Running in background/daemon mode
   - Output is buffered
   - User is not monitoring stderr

2. **No Logging Integration**: Warnings are not automatically captured by the logging system unless explicitly configured

3. **No Structured Tracking**: Cannot easily track:
   - How often fallbacks occur
   - Which operations trigger fallbacks
   - Performance impact of fallbacks

4. **Inconsistent with Rest of Pipeline**: Most of the pipeline uses `logger.warning()` for warnings, but catalog fallbacks use `warnings.warn()`

## Comparison with Other Pipeline Warnings

### Standard Pattern (Used Throughout Pipeline)
```python
logger = logging.getLogger(__name__)
logger.warning("Message here")
```

### Catalog Fallback Pattern (Current)
```python
import warnings
warnings.warn("Message here", UserWarning)
```

## Recommendations

### Option 1: Use Logging (Recommended)

Replace `warnings.warn()` with `logger.warning()` for consistency:

```python
import logging

logger = logging.getLogger(__name__)

# In query functions:
try:
    # SQLite query
    ...
except Exception as e:
    logger.warning(
        f"SQLite query failed ({e}), falling back to CSV. "
        f"This will be slower (~1s vs ~0.01s)."
    )
    # Fallback to CSV
```

**Benefits:**
- Consistent with rest of pipeline
- Automatically captured in log files
- Can be filtered/configured via logging config
- Better visibility in production environments

### Option 2: Hybrid Approach

Use both logging and warnings:

```python
logger.warning("SQLite query failed, falling back to CSV")
warnings.warn("Performance degradation: using CSV fallback", UserWarning)
```

**Benefits:**
- Logging for production monitoring
- Warnings for immediate user feedback

### Option 3: Structured Fallback Tracking

Add metrics/telemetry for fallback events:

```python
from dsa110_contimg.utils.metrics import record_fallback

try:
    # SQLite query
    ...
except Exception as e:
    record_fallback(
        component="catalog_query",
        catalog_type="nvss",
        reason=str(e),
        fallback_to="csv"
    )
    logger.warning(f"SQLite query failed, falling back to CSV: {e}")
```

## Current Fallback Locations

1. **`query_nvss_sources()`** - Line ~1147
2. **`query_rax_sources()`** - Line ~1335
3. **`query_vlass_sources()`** - Line ~1542 (also warns if catalog not found)

## Action Items

1. **Immediate**: Replace `warnings.warn()` with `logger.warning()` in catalog query functions
2. **Short-term**: Ensure logging configuration captures warnings
3. **Long-term**: Add structured fallback tracking/metrics

## Testing Fallback Notifications

To test fallback notifications:

```python
# Force fallback by using non-existent database
from dsa110_contimg.calibration.catalogs import query_nvss_sources

# This should trigger warning
df = query_nvss_sources(
    ra_deg=83.5,
    dec_deg=54.6,
    radius_deg=1.0,
    catalog_path="/nonexistent/path.sqlite3"
)
```

Expected behavior:
- Warning should appear in logs
- Function should still return results (from CSV)
- Performance should be slower (~1s vs ~7ms)

