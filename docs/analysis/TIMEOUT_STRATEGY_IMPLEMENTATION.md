# Timeout Strategy Implementation

## Summary

Implemented timeout protection to prevent operations from hanging indefinitely.

## Changes Made

### 1. Database Connection Timeouts ✓

Added `timeout=30.0` to all SQLite connections:
- `src/dsa110_contimg/database/products.py`: `ensure_products_db()`
- `src/dsa110_contimg/database/schema_evolution.py`: All `sqlite3.connect()` calls
- `src/dsa110_contimg/database/registry_setup.py`: `sqlite3.connect()` call

**Impact**: Database operations will fail after 30 seconds if database is locked, preventing hangs.

### 2. Schema Evolution Timeout ✓

Schema evolution operations are now wrapped with timeout:
- Uses `timeout` command wrapper (60 seconds for schema evolution)
- Database connections have 30-second timeout

**Status**: Successfully migrated 11 rows from `images_all` to `images`

### 3. Mosaic Building Timeout (Partial)

Started adding timeout to `cmd_build()` function:
- Uses `stage_timeout()` from `pipeline.timeout` module
- Default timeout: 2 hours (7200 seconds)
- Needs proper indentation fix to wrap entire function body

**TODO**: Fix indentation in `cmd_build()` to properly wrap all operations in timeout context

## Current Database State

After running schema evolution:
- `images_all`: 11 rows
- `images`: 11 rows ✓ (data successfully migrated)

## Next Steps

1. **Fix mosaic timeout indentation** - Wrap entire `cmd_build()` function body in timeout context
2. **Test timeout behavior** - Verify timeouts work correctly
3. **Add timeout to other long operations**:
   - Image validation
   - Tile reading operations
   - CASA tool operations

## Timeout Values

- Database connections: 30 seconds
- Schema evolution: 60 seconds (command-level)
- Mosaic building: 7200 seconds (2 hours) - default
- Future: Make timeout configurable via CLI args

## Testing

To test timeout behavior:
```bash
# Test database timeout (should fail after 30s if locked)
timeout 60 python -c "from dsa110_contimg.database.products import ensure_products_db; ..."

# Test mosaic timeout (should fail after 2h if stuck)
dsa110-contimg mosaic build --name test --timeout 10  # 10 second test timeout
```

