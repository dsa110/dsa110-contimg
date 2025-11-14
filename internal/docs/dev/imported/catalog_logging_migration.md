# Catalog Query Logging Migration

## Summary

Migrated catalog query fallback notifications from `warnings.warn()` to
`logger.warning()` for better consistency with the rest of the pipeline and
improved visibility in production environments.

## Changes Made

### File: `src/dsa110_contimg/calibration/catalogs.py`

1. **Added logging import and logger setup**:

   ```python
   import logging
   ...
   logger = logging.getLogger(__name__)
   ```

2. **Replaced 4 instances of `warnings.warn()` with `logger.warning()`**:
   - `query_nvss_sources()` - SQLite fallback warning
   - `query_rax_sources()` - SQLite fallback warning
   - `query_vlass_sources()` - SQLite fallback warning
   - `query_vlass_sources()` - Catalog not found warning

## Before

```python
import warnings

warnings.warn(
    f"SQLite query failed ({e}), falling back to CSV. "
    f"This will be slower (~1s vs ~0.01s).",
    UserWarning,
)
```

## After

```python
logger.warning(
    f"SQLite query failed ({e}), falling back to CSV. "
    f"This will be slower (~1s vs ~0.01s)."
)
```

## Benefits

1. **Consistency**: Matches the logging pattern used throughout the rest of the
   pipeline
2. **Visibility**: Automatically captured in log files and production monitoring
3. **Configurability**: Can be filtered/configured via standard logging
   configuration
4. **Production-Ready**: Better integration with logging infrastructure

## Notification Locations

All fallback warnings now use `logger.warning()`:

1. **Line 1148**: `query_nvss_sources()` - SQLite query failure fallback
2. **Line 1333**: `query_rax_sources()` - SQLite query failure fallback
3. **Line 1537**: `query_vlass_sources()` - SQLite query failure fallback
4. **Line 1561**: `query_vlass_sources()` - Catalog file not found

## Testing

To verify fallback notifications work correctly:

```python
import logging

# Configure logging to see warnings
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

from dsa110_contimg.calibration.catalogs import query_nvss_sources

# Force fallback by using non-existent database
df = query_nvss_sources(
    ra_deg=83.5,
    dec_deg=54.6,
    radius_deg=1.0,
    catalog_path="/nonexistent/path.sqlite3"
)
# Should see: WARNING: SQLite query failed (...), falling back to CSV...
```

## Verification

- ✓ All `warnings.warn()` calls replaced with `logger.warning()`
- ✓ Logging module imported and logger configured
- ✓ File compiles successfully
- ✓ Logger properly configured and accessible

## Related Documentation

- [Fallback Notification Analysis](fallback_notification_analysis.md) - Analysis
  of fallback notification mechanisms
- [Catalog Migration to SQLite](catalog_migration_to_sqlite.md) - Migration from
  CSV to SQLite-first architecture
