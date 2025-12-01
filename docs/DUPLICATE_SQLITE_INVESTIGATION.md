# SQLite Database Duplication Investigation Report

**Date:** 2025-01-XX  
**Location:** `/data/dsa110-contimg/`  
**Investigator:** BLACKBOXAI

## Executive Summary

Investigation of SQLite databases within `/data/dsa110-contimg/` has identified **33 total SQLite database files**, with **3 pairs of similarly-named databases** that warrant attention. While these are not byte-for-byte duplicates (different MD5 checksums), they represent potential redundancy between legacy and current systems.

## Complete Database Inventory

### Total Files Found: 33

#### Legacy Backend Databases (2 files)
- `/data/dsa110-contimg/legacy.backend/state/cal_registry.sqlite3`
- `/data/dsa110-contimg/legacy.backend/state/products.sqlite3`

#### Current State Databases (31 files)

**Main Database Directory (`state/db/`):**
- `calibrators.sqlite3`
- `calibrator_registry.sqlite3`
- `cal_registry.sqlite3` ⚠️
- `data_registry.sqlite3`
- `hdf5.sqlite3` ⚠️
- `ingest.sqlite3`
- `ingest_queue.sqlite3`
- `products.sqlite3` ⚠️

**Catalog Databases (`state/catalogs/`):**
- `atnf_dec+54.0.sqlite3`
- `first_dec+54.6.sqlite3`
- `master_sources.sqlite3`
- `nvss_dec+10.0.sqlite3`
- `nvss_dec+12.0.sqlite3`
- `nvss_dec+29.0.sqlite3`
- `nvss_dec+30.5.sqlite3`
- `nvss_dec+33.0.sqlite3`
- `nvss_dec+4.0.sqlite3`
- `nvss_dec+41.0.sqlite3`
- `nvss_dec+49.0.sqlite3`
- `nvss_dec+52.0.sqlite3`
- `nvss_dec+54.6.sqlite3`
- `nvss_dec+8.0.sqlite3`
- `nvss_dec-1.0.sqlite3`
- `nvss_dec-5.0.sqlite3`
- `rax_dec+30.5.sqlite3`
- `vlass_dec+54.0.sqlite3`
- `vla_calibrators.sqlite3`

**Documentation/Utility Databases (`state/`):**
- `docsearch.sqlite3`
- `docsearch_code.sqlite3`
- `embedding_cache.sqlite3`
- `hdf5.sqlite3` ⚠️
- `ragflow_sync.sqlite3`

## Duplicate Analysis

### 1. cal_registry.sqlite3 (DUPLICATE NAME)

**Locations:**
- `legacy.backend/state/cal_registry.sqlite3`
- `state/db/cal_registry.sqlite3`

**MD5 Checksums:**
- Legacy: `d41d8cd98f00b204e9800998ecf8427e` (empty file signature)
- Current: `195295585c1a5b96296347816079199c`

**Status:** ⚠️ **LEGACY FILE APPEARS EMPTY**

**Code References:** 273+ references found, primarily pointing to `state/db/cal_registry.sqlite3`

**Recommendation:** The legacy version appears to be an empty/placeholder file and can likely be safely removed.

---

### 2. products.sqlite3 (DUPLICATE NAME)

**Locations:**
- `legacy.backend/state/products.sqlite3`
- `state/db/products.sqlite3`

**MD5 Checksums:**
- Legacy: `a086606b74cc838d9531d80d901e0f9`
- Current: `5de203e146541c1cf0242691471ab781`

**Status:** ⚠️ **DIFFERENT CONTENT - BOTH ACTIVE**

**Code References:** Extensive usage throughout codebase
- Current system: `state/db/products.sqlite3` (primary)
- Legacy tests: `legacy.backend/state/products.sqlite3`

**Recommendation:** Verify if legacy version is still needed for backward compatibility or testing. If not, consider migration/removal.

---

### 3. hdf5.sqlite3 (DUPLICATE NAME)

**Locations:**
- `state/db/hdf5.sqlite3`
- `state/hdf5.sqlite3`

**MD5 Checksums:**
- DB version: `d9fb03639205770d313a32e69386026d`
- Root version: `b4a32f8542cddeae33c732521e89cc54`

**Status:** ⚠️ **DIFFERENT CONTENT - UNCLEAR PURPOSE**

**Code References:** Found in test files referencing both locations

**Recommendation:** Investigate which is the canonical version and consolidate.

---

## Additional Observations

### Potential Functional Duplicates

While not exact name matches, these databases may have overlapping purposes:

1. **Calibration Databases:**
   - `calibrators.sqlite3`
   - `calibrator_registry.sqlite3`
   - `cal_registry.sqlite3`
   
   **Recommendation:** Review if all three are necessary or if they can be consolidated.

2. **Ingest Databases:**
   - `ingest.sqlite3`
   - `ingest_queue.sqlite3`
   
   **Recommendation:** Verify if both are actively used or if one is deprecated.

### Catalog Databases (15 files)

The NVSS catalog is split across multiple declination bands:
