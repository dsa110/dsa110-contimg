# Catalog Implementation Comparison: NVSS vs VLASS vs RACS/RAX

## Summary

**No, VLASS and RACS (RAX) are NOT implemented equivalently to NVSS.**

NVSS has the most complete implementation with dedicated optimized query functions, while VLASS and RAX have partial implementations.

## Implementation Status

### NVSS (Most Complete)

**Query Functions:**
- ✅ `query_nvss_sources()` in `calibration/catalogs.py` - **Optimized SQLite query function**
- ✅ `query_sources(catalog_type="nvss")` in `catalog/query.py` - Generic query interface
- ✅ CSV fallback support

**Database Builders:**
- ✅ `build_nvss_strip_db()` in `catalog/builders.py`
- ✅ SQLite databases with spatial indexing
- ✅ Per-declination strip databases

**Performance:**
- ✅ **170× faster** with SQLite (7ms vs 1200ms)
- ✅ Optimized spatial queries with indexes
- ✅ Production databases available

**Usage:**
```python
from dsa110_contimg.calibration.catalogs import query_nvss_sources

# Fast SQLite query (auto-falls back to CSV)
df = query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=1.0, min_flux_mjy=10.0)
```

### RACS/RAX (Partially Implemented)

**Query Functions:**
- ❌ **NO dedicated `query_rax_sources()` function**
- ✅ `query_sources(catalog_type="rax")` in `catalog/query.py` - Generic query interface only
- ⚠️ No CSV fallback (SQLite only)

**Database Builders:**
- ✅ `build_rax_strip_db()` in `catalog/builders.py`
- ✅ SQLite databases with spatial indexing
- ✅ Per-declination strip databases

**Performance:**
- ✅ Fast SQLite queries (similar to NVSS)
- ⚠️ No CSV fallback (fails if SQLite DB not found)

**Usage:**
```python
from dsa110_contimg.catalog.query import query_sources

# Generic query interface (no dedicated function)
df = query_sources(catalog_type="rax", ra_deg=83.5, dec_deg=54.6, radius_deg=1.0)
```

**Missing:**
- Dedicated `query_rax_sources()` function in `calibration/catalogs.py`
- CSV fallback support
- Equivalent optimization to NVSS

### VLASS (Minimal Implementation)

**Query Functions:**
- ❌ **NO dedicated query function**
- ❌ **NOT supported in `query_sources()` generic interface**
- ❌ No SQLite query support

**Database Builders:**
- ❌ **NO `build_vlass_strip_db()` function**
- ❌ No SQLite databases

**Usage:**
- ⚠️ Only used in master catalog crossmatching (`build_master.py`)
- ⚠️ Must provide CSV/FITS file path directly
- ⚠️ No optimized query interface

**Current Usage:**
```python
# Only available in master catalog builder
from dsa110_contimg.catalog.build_master import build_master_catalog

# VLASS is only used as input to crossmatching, not for direct queries
build_master_catalog(
    nvss_path="...",
    vlass_path="/path/to/vlass.csv",  # Must provide path
    ...
)
```

**Missing:**
- Dedicated query function
- SQLite database builder
- Query interface support
- CSV fallback
- All optimization features

## Detailed Comparison Table

| Feature | NVSS | RAX | VLASS |
|---------|------|-----|-------|
| **Dedicated Query Function** | ✅ `query_nvss_sources()` | ❌ | ❌ |
| **Generic Query Support** | ✅ `query_sources("nvss")` | ✅ `query_sources("rax")` | ❌ |
| **SQLite Builder** | ✅ `build_nvss_strip_db()` | ✅ `build_rax_strip_db()` | ❌ |
| **CSV Fallback** | ✅ | ❌ | ❌ |
| **Spatial Indexing** | ✅ | ✅ | ❌ |
| **Performance Optimization** | ✅ 170× faster | ✅ Fast (SQLite) | ❌ |
| **Production Databases** | ✅ Available | ⚠️ Must build | ❌ |
| **CLI Tool** | ✅ `build_nvss_strip_cli.py` | ✅ `build_rax_strip_cli.py` | ❌ |

## Recommendations

### For RAX/RACS

To make RAX equivalent to NVSS:

1. **Add dedicated query function:**
   ```python
   def query_rax_sources(
       ra_deg: float,
       dec_deg: float,
       radius_deg: float,
       min_flux_mjy: Optional[float] = None,
       max_sources: Optional[int] = None,
       catalog_path: Optional[str | os.PathLike[str]] = None,
   ) -> pd.DataFrame:
       """Query RAX catalog (equivalent to query_nvss_sources)."""
       # Similar implementation to query_nvss_sources()
   ```

2. **Add CSV fallback support** in `query_sources()` for RAX

3. **Update documentation** to show RAX usage patterns

### For VLASS

To make VLASS equivalent to NVSS:

1. **Add SQLite builder:**
   ```python
   def build_vlass_strip_db(
       dec_center: float,
       dec_range: Tuple[float, float],
       vlass_catalog_path: Optional[str] = None,
       ...
   ) -> Path:
       """Build SQLite database for VLASS sources."""
   ```

2. **Add query support** in `query_sources()`:
   ```python
   elif catalog_type == "vlass":
       # VLASS catalog schema
       ...
   ```

3. **Add dedicated query function** (optional but recommended):
   ```python
   def query_vlass_sources(...) -> pd.DataFrame:
       """Query VLASS catalog."""
   ```

4. **Add CSV fallback** support

## Current Production Status

**Available SQLite Databases:**
- ✅ `nvss_dec+54.6.sqlite3` (17MB, 129k sources)
- ❌ No RAX databases (must build)
- ❌ No VLASS databases

**Usage in Pipeline:**
- NVSS: ✅ Used extensively for validation, seeding, photometry
- RAX: ⚠️ Supported but requires database building
- VLASS: ⚠️ Only used in master catalog crossmatching

## Related Files

- **NVSS Implementation:**
  - `src/dsa110_contimg/calibration/catalogs.py` - `query_nvss_sources()`
  - `src/dsa110_contimg/catalog/builders.py` - `build_nvss_strip_db()`
  - `src/dsa110_contimg/catalog/query.py` - Generic query support

- **RAX Implementation:**
  - `src/dsa110_contimg/catalog/builders.py` - `build_rax_strip_db()`
  - `src/dsa110_contimg/catalog/query.py` - Generic query support
  - `src/dsa110_contimg/catalog/build_rax_strip_cli.py` - CLI tool

- **VLASS Implementation:**
  - `src/dsa110_contimg/catalog/build_master.py` - Crossmatching only
  - No query functions or SQLite builders

## Conclusion

NVSS has the most complete and optimized implementation. RAX has partial support (SQLite builder, generic query), but lacks the dedicated optimized query function and CSV fallback. VLASS has minimal support and is only used for crossmatching in the master catalog builder.

To achieve feature parity, RAX needs a dedicated query function and CSV fallback, while VLASS needs a complete implementation from scratch.

