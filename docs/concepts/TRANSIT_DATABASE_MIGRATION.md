# Transit Times Database Migration

## Summary

Transit times are now stored in a permanent database table
(`calibrator_transits`) in the products database, instead of using a temporary
cache table.

## Changes

### Table Name

- **Old**: `transit_cache` (temporary cache)
- **New**: `calibrator_transits` (permanent database table)

### Table Schema

```sql
CREATE TABLE calibrator_transits (
    calibrator_name TEXT NOT NULL,
    transit_mjd REAL NOT NULL,
    transit_iso TEXT NOT NULL,
    has_data INTEGER NOT NULL DEFAULT 0,
    group_id TEXT,
    group_mid_iso TEXT,
    delta_minutes REAL,
    pb_response REAL,
    dec_match INTEGER NOT NULL DEFAULT 0,
    calculated_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (calibrator_name, transit_mjd)
)
```

### Function Names

- **Old**: `get_cached_transits()` → **New**: `get_calibrator_transits()`
- **Old**: `invalidate_transit_cache()` → **New**:
  `delete_calibrator_transits()`
- **Old**: `ensure_transit_cache_table()` → **New**:
  `ensure_calibrator_transits_table()`

### Backward Compatibility

Aliases are provided for backward compatibility:

- `get_cached_transits` → points to `get_calibrator_transits`
- `invalidate_transit_cache` → points to `delete_calibrator_transits`

## Migration

If you have an existing `transit_cache` table, you can migrate the data:

```sql
-- Create new table
CREATE TABLE calibrator_transits AS
SELECT
    calibrator_name,
    transit_mjd,
    transit_iso,
    has_data,
    group_id,
    group_mid_iso,
    delta_minutes,
    pb_response,
    dec_match,
    calculated_at,
    calculated_at AS updated_at
FROM transit_cache;

-- Drop old table (after verification)
-- DROP TABLE transit_cache;
```

## Benefits

1. **Permanent Storage**: Transit times are now part of the main database schema
2. **Better Integration**: Works seamlessly with other database tables
3. **Data Persistence**: Data survives database restarts and is not treated as
   temporary
4. **Clearer Intent**: Table name reflects that this is permanent data, not a
   cache

## Usage

The API remains the same, but internally uses the new table:

```python
from dsa110_contimg.conversion.transit_precalc import get_calibrator_transits

# Get stored transit times
transits = get_calibrator_transits(
    products_db=products_db,
    calibrator_name="0834+555",
    max_days_back=60,
    only_with_data=True,
)
```
