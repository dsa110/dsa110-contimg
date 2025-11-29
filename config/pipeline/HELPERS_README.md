# Ops Pipeline Shared Helpers

**Date:** 2025-11-05  
**Purpose:** Consolidate duplicate helper functions from multiple pipeline
scripts

## Created Modules

### `helpers_catalog.py`

Consolidates catalog loading functions:

- `load_ra_dec_from_db()` - Load RA/Dec from SQLite database
- `load_ra_dec()` - Load RA/Dec from database or catalog files
- `load_flux_jy_from_db()` - Load flux from SQLite database
- `load_flux_jy()` - Load flux from database or catalog files

### `helpers_group.py`

Consolidates group ID parsing:

- `group_id_from_path()` - Extract group ID from file path

### `helpers_ms_conversion.py`

Consolidates MS conversion:

- `write_ms_group_via_uvh5_to_ms()` - Convert subband UVH5 files to MS via
  concat

## Migration

**Old (duplicate in each file):**

```python
def _load_ra_dec(name: str, catalogs: List[str], vla_db: Optional[str] = None):
    # ... duplicate code ...
```

**New (shared):**

```python
from helpers_catalog import load_ra_dec
ra, dec = load_ra_dec(name, catalogs, vla_db=vla_db)
```

## Files Updated

1. :check: `build_central_calibrator_group.py` - Updated to use shared helpers
2. :check: `build_calibrator_transit_offsets.py` - Updated to use shared helpers
3. :check: `image_groups_in_timerange.py` - Updated to use shared helpers
4. :check: `curate_transit.py` - Updated to use shared helpers
5. :check: `run_next_field_after_central.py` - Updated to use shared helpers

**All ops pipeline scripts now use shared helpers!**

## Benefits

- **Reduced duplication:** ~500+ lines of duplicate code consolidated
- **Easier maintenance:** Fix bugs in one place
- **Consistent behavior:** All scripts use same logic
