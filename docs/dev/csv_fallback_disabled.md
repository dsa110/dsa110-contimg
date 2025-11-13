# CSV Fallback Disabled - SQLite Required

## Summary

CSV fallback has been disabled by default. All catalog queries now require SQLite databases. CSV infrastructure remains available but must be explicitly enabled via `use_csv_fallback=True` parameter.

## Changes Made

### Default Behavior

- **Before**: Automatic CSV fallback when SQLite databases unavailable
- **After**: SQLite databases required; CSV fallback disabled by default

### New Parameter

All catalog query functions now accept `use_csv_fallback: bool = False`:

- `query_nvss_sources(..., use_csv_fallback=False)`
- `query_rax_sources(..., use_csv_fallback=False)`
- `query_vlass_sources(..., use_csv_fallback=False)`
- `query_catalog_sources(..., use_csv_fallback=False)`

## Behavior

### When SQLite Succeeds (Default Path)
- Query executes normally using SQLite database
- No fallback needed
- Fast performance (~7ms per query)

### When SQLite Fails and `use_csv_fallback=False` (Default)
- Returns empty DataFrame
- Logs error message
- Prints informational message about CSV availability
- **No automatic fallback**

### When SQLite Fails and `use_csv_fallback=True`
- Falls back to CSV catalog
- Logs warning about performance degradation
- Prints informational message
- Returns results from CSV (slower, ~1s per query)

## User Notification

When SQLite fails and CSV fallback is disabled, users see:

1. **Error log message**:
   ```
   ERROR: SQLite query failed (...). SQLite database required. 
   CSV fallback is available but disabled. Set use_csv_fallback=True to enable CSV fallback.
   ```

2. **Print statement**:
   ```
   Note: CSV catalog is available as an alternative. 
   Set use_csv_fallback=True to enable CSV fallback (slower, ~1s vs ~0.01s).
   ```

## Rationale

1. **Egalitarian Approach**: All catalogs (NVSS, RAX, VLASS) now rely equally on SQLite databases
2. **Performance**: Encourages use of optimized SQLite databases (~170× faster)
3. **Explicit Control**: Users must explicitly opt-in to CSV fallback
4. **Infrastructure Preservation**: CSV code remains available for emergency use

## Migration Guide

### For Code Using Catalog Queries

**No changes needed** - existing code continues to work, but will return empty DataFrames if SQLite databases are unavailable.

**To enable CSV fallback** (if needed):
```python
from dsa110_contimg.calibration.catalogs import query_nvss_sources

# Enable CSV fallback explicitly
df = query_nvss_sources(
    ra_deg=83.5,
    dec_deg=54.6,
    radius_deg=1.0,
    use_csv_fallback=True  # Explicitly enable CSV fallback
)
```

### For Building SQLite Databases

Ensure SQLite databases are built for commonly used declination strips:

```bash
# NVSS
python -m dsa110_contimg.catalog.builders build_nvss_strip_db \
    --dec-center 54.6 --dec-range 54.0 55.0

# RAX
python -m dsa110_contimg.catalog.builders build_rax_strip_db \
    --dec-center 54.6 --dec-range 54.0 55.0

# VLASS
python -m dsa110_contimg.catalog.builders build_vlass_strip_db \
    --dec-center 54.6 --dec-range 54.0 55.0
```

## Impact

- **Breaking Change**: Code that relied on automatic CSV fallback will now return empty DataFrames when SQLite databases are unavailable
- **Performance**: Encourages optimal performance by requiring SQLite databases
- **Consistency**: All catalogs now have equal treatment (SQLite-first, CSV opt-in)

## Related Documentation

- [Catalog Migration to SQLite](catalog_migration_to_sqlite.md) - Migration from CSV to SQLite-first architecture
- [Catalog Logging Migration](catalog_logging_migration.md) - Logging improvements for fallback notifications

