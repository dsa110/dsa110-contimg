# Next Steps: Mosaic Creation Fixes

## Date: 2025-01-XX

## Summary of Completed Work

### 1. Chronological Ordering Fixes ✓
- Fixed `check_for_new_group()` to preserve chronological order (by `mid_mjd`)
- Fixed `check_for_sliding_window_group()` to preserve chronological order
- Updated `get_group_ms_paths()` to explicitly sort by observation time
- Added chronological validation in `create_mosaic()` with automatic re-sorting
- Added validation in `cmd_build()` CLI with error reporting

### 2. Mosaic Building Fixes ✓
- Fixed reference coordinate system consistency (always use `pb_paths[0]` as template)
- Improved image path construction with multiple fallback strategies
- Changed NaN threshold from absolute (`1e-10`) to relative (1% of max weight)
- Added detailed NaN pixel statistics logging

### 3. Database Consistency Fixes ✓
- Updated migration logic to keep `images` table (not rename to `images_all`)
- Added data migration from `images_all` → `images` if both exist
- Updated all migration code to prefer original table names

### 4. Code Organization Improvements ✓
- Renamed `migrations.py` → `schema_evolution.py` (more descriptive)
- Renamed `data_migrations.py` → `registry_setup.py` (more descriptive)
- Updated function names to reflect schema evolution vs. setup
- Maintained backwards compatibility with aliases

## Immediate Next Steps

### Step 1: Run Schema Evolution to Consolidate Database
**Priority: HIGH**

The database currently has both `images` and `images_all` tables. We need to run the updated migration to consolidate data.

```bash
# Run schema evolution to migrate data from images_all to images
cd /data/dsa110-contimg
/opt/miniforge/envs/casa6/bin/python -c "
from pathlib import Path
from dsa110_contimg.database.schema_evolution import evolve_all_schemas
evolve_all_schemas(Path('/data/dsa110-contimg/state'), verbose=True)
"
```

**Expected outcome:**
- Data from `images_all` copied to `images`
- Both tables may exist temporarily (can drop `images_all` after verification)

**Verification:**
```python
# Check row counts match
SELECT COUNT(*) FROM images;
SELECT COUNT(*) FROM images_all;  # Should match or be subset
```

### Step 2: Test Mosaic Creation with Fixed Code
**Priority: HIGH**

Create a new mosaic to verify:
1. Chronological ordering is enforced
2. Reference coordinate system is correct
3. NaN pixel percentage is improved (should be < 41.2%)
4. Image path lookup works correctly

```bash
# Plan a mosaic
dsa110-contimg mosaic plan --products-db state/products.sqlite3

# Build the mosaic with validation
dsa110-contimg mosaic build --products-db state/products.sqlite3 --method weighted
```

**Check for:**
- Validation messages showing chronological order confirmation
- NaN pixel statistics in logs (should be lower than before)
- Mosaic quality (visual inspection)
- Coordinate system correctness (astrometric validation)

### Step 3: Verify Database Consistency
**Priority: MEDIUM**

Ensure all image queries now find images correctly:

```python
# Test image queries
from dsa110_contimg.database.products import ensure_products_db
from pathlib import Path

with ensure_products_db(Path('state/products.sqlite3')) as conn:
    # Should find images in images table
    rows = conn.execute("SELECT COUNT(*) FROM images").fetchone()
    print(f"Total images: {rows[0]}")
    
    # Test mosaic planning query
    rows = conn.execute("""
        SELECT path FROM images 
        WHERE pbcor = 1 
        ORDER BY created_at ASC
        LIMIT 10
    """).fetchall()
    print(f"Found {len(rows)} images for mosaic")
```

### Step 4: Update Documentation
**Priority: MEDIUM**

Update any remaining references:
- [ ] Check `docs/reference/database_schema.md` for `images_all` references
- [ ] Update any API documentation that references old table names
- [ ] Update any scripts or examples that use old migration function names

### Step 5: Monitor Mosaic Quality
**Priority: ONGOING**

After fixes are deployed:
- Monitor NaN pixel percentages in new mosaics
- Check for chronological ordering warnings/errors in logs
- Verify astrometric accuracy of mosaics
- Compare mosaic quality before/after fixes

## Testing Checklist

- [ ] Run schema evolution - verify data migration works
- [ ] Create test mosaic - verify chronological ordering
- [ ] Check NaN pixel percentage - should be improved
- [ ] Verify coordinate system - astrometric validation
- [ ] Test image path lookup - verify fallback strategies work
- [ ] Check database queries - verify images table is used consistently
- [ ] Test backwards compatibility - old migration function names still work

## Potential Follow-up Work

### If Issues Persist:
1. **High NaN percentage**: Investigate primary beam coverage overlap
2. **Coordinate system issues**: Check tile regridding accuracy
3. **Missing images**: Verify image registration in products DB
4. **Performance**: Profile mosaic building for optimization opportunities

### Future Improvements:
1. Add unit tests for chronological ordering logic
2. Add integration tests for mosaic creation pipeline
3. Add monitoring/metrics for mosaic quality
4. Consider caching regridded images more aggressively
5. Add validation checks earlier in the pipeline

## Rollback Plan

If issues arise:
1. Old migration functions still work (backwards compatibility aliases)
2. Database can be restored from backup if needed
3. Code changes are isolated to mosaic building logic
4. Can revert to alphabetical sorting if needed (not recommended)

## Notes

- All fixes maintain backwards compatibility
- Migration is idempotent (safe to run multiple times)
- Chronological validation can be bypassed with `--ignore-validation` flag (not recommended)
- Database consolidation is one-way (images_all → images), but data is preserved

