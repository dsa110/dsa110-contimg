# Redundancy Analysis: ops/ Directory

**Date:** 2025-01-XX  
**Scope:** Analysis of redundant processes, routines, and scripts in `/data/dsa110-contimg/ops/`

---

## Executive Summary

The `ops/` directory contains deployment configurations and operational scripts. Several redundancies have been identified:

1. **Legacy systemd service file** - Duplicate streaming converter service
2. **Duplicate helper functions** - Repeated across multiple scripts (catalog loading, MS writing, group ID parsing)
3. **Overlapping cleanup routines** - Housekeeping and cleanup scripts with some overlap
4. **Similar calibrator processing scripts** - Two scripts with nearly identical code for calibrator group building

---

## 1. Systemd Service Files

### 1.1 Duplicate Streaming Converter Services

**Files:**
- `ops/pipeline/dsa110-streaming-converter.service` (legacy)
- `ops/systemd/contimg-stream.service` (current)

**Analysis:**

**Legacy file (`dsa110-streaming-converter.service`):**
- Hardcoded paths and environment variables
- Uses old path: `streaming/streaming_converter.py` (direct path, not module)
- Hardcoded Python path: `/opt/conda/envs/casa6/bin/python`
- Hardcoded user/group: `ubuntu:ubuntu`
- Hardcoded paths: `/data/incoming_data`, `/data/output/ms`
- Uses journal logging (systemd journal)
- Has checkpoint directory (not in current version)

**Current file (`contimg-stream.service`):**
- Uses environment file: `contimg.env` (configurable)
- Uses module path: `dsa110_contimg.conversion.streaming.streaming_converter`
- Uses system Python: `/usr/bin/python3`
- Uses environment variables for all paths
- Uses file logging: `state/logs/contimg-stream.out/err`
- Better resource limits (1048576 vs 65536)
- More modern configuration (Nice, IOScheduling)

**Recommendation:**
- **Remove or archive** `ops/pipeline/dsa110-streaming-converter.service`
- **Document** in `ops/systemd/INSTALL.md` that only `ops/systemd/contimg-stream.service` should be used
- **Add deprecation comment** to legacy file if kept for reference

**Action:**
```bash
# Move to archive or remove
mv ops/pipeline/dsa110-streaming-converter.service ops/pipeline/archive/
# Or remove if not needed
rm ops/pipeline/dsa110-streaming-converter.service
```

---

## 2. Duplicate Helper Functions

### 2.1 Catalog Loading Functions

**Location:** Multiple scripts have identical or near-identical functions:

**Files with duplicate functions:**
- `ops/pipeline/build_central_calibrator_group.py`
  - `_load_ra_dec_from_db()`
  - `_load_ra_dec()`
  - `_load_flux_jy_from_db()`
  - `_load_flux_jy()`
- `ops/pipeline/build_calibrator_transit_offsets.py`
  - `_load_ra_dec()` (simpler version, no DB support)
  - `_load_flux_jy()` (simpler version, no DB support)
- `ops/pipeline/image_groups_in_timerange.py`
  - `_load_ra_dec_from_db()`
  - `_load_ra_dec()`

**Code Duplication:**
- `_load_ra_dec()` appears in 3 files with slight variations
- `_load_flux_jy()` appears in 2 files with slight variations
- DB-aware versions exist in some files but not others

**Recommendation:**
1. **Create shared module**: `ops/pipeline/calibrator_helpers.py`
2. **Consolidate functions**:
   ```python
   # ops/pipeline/calibrator_helpers.py
   def load_ra_dec(name: str, catalogs: List[str], vla_db: Optional[str] = None) -> Tuple[float, float]:
       """Load RA/Dec from DB (preferred) or CSV catalogs."""
       # Consolidated logic from all three files
   
   def load_flux_jy(name: str, catalogs: List[str], band: str = '20cm', vla_db: Optional[str] = None) -> Optional[float]:
       """Load flux from DB (preferred) or CSV catalogs."""
       # Consolidated logic
   ```
3. **Update all scripts** to import from shared module

**Impact:** Reduces code duplication by ~200 lines across 3 files

### 2.2 MS Writing Functions

**Location:** Multiple scripts have `_write_ms_group_via_uvh5_to_ms()` functions:

**Files:**
- `ops/pipeline/build_central_calibrator_group.py` (lines 127-183)
- `ops/pipeline/build_calibrator_transit_offsets.py` (lines 98-139)
- `ops/pipeline/image_groups_in_timerange.py` (lines 90-130)
- `ops/pipeline/run_next_field_after_central.py` (lines 108-162)

**Code Similarity:**
All four functions:
- Convert subband UVH5 files to per-subband MS files
- Use `convert_single_file()` from `dsa110_contimg.conversion.uvh5_to_ms`
- Concatenate per-subband MS files using CASA `concat`
- Clean up intermediate part directories
- Handle imaging columns (with slight variations)

**Differences:**
- `build_central_calibrator_group.py`: More complex, handles imaging columns manually
- `build_calibrator_transit_offsets.py`: Uses `configure_ms_for_imaging()` helper
- `image_groups_in_timerange.py`: Uses `configure_ms_for_imaging()` helper
- `run_next_field_after_central.py`: Has additional flag/weight spectrum handling

**Recommendation:**
1. **Use orchestrator** instead of direct `uvh5_to_ms` calls:
   - All scripts should use `hdf5_orchestrator` CLI or its Python API
   - This is the recommended production path
2. **If keeping direct calls**, create shared helper:
   ```python
   # ops/pipeline/ms_conversion_helpers.py
   def convert_subband_group_to_ms(
       file_list: List[str],
       ms_out: Path,
       ensure_imaging_columns: bool = True
   ) -> None:
       """Convert subband group to MS using direct-subband approach."""
       # Consolidated logic
   ```
3. **Or better**: Refactor all scripts to use `hdf5_orchestrator` CLI

**Impact:** Reduces code duplication by ~300 lines across 4 files

### 2.3 Group ID Parsing

**Location:** Multiple scripts have `_group_id_from_path()` function:

**Files:**
- `ops/pipeline/build_central_calibrator_group.py` (line 122)
- `ops/pipeline/build_calibrator_transit_offsets.py` (line 93)
- `ops/pipeline/image_groups_in_timerange.py` (line 85)
- `ops/pipeline/curate_transit.py` (line 84)

**Code:**
All use identical logic:
```python
def _group_id_from_path(path: str) -> str:
    base = os.path.basename(path)
    return base.split('_sb', 1)[0]
```

**Recommendation:**
1. **Create shared utility**:
   ```python
   # ops/pipeline/group_helpers.py or src/dsa110_contimg/conversion/helpers.py
   def parse_group_id_from_path(path: str) -> str:
       """Extract group ID (timestamp) from UVH5 filename."""
       base = os.path.basename(path)
       return base.split('_sb', 1)[0]
   ```
2. **Update all scripts** to import from shared location

**Impact:** Minor, but improves consistency

---

## 3. Overlapping Cleanup Routines

### 3.1 Housekeeping vs. Cleanup Scripts

**Files:**
- `ops/pipeline/housekeeping.py` - Queue recovery and temp dir cleanup
- `ops/pipeline/cleanup_old_data.py` - MS file deletion and log compression
- `ops/pipeline/scheduler.py` - Calls housekeeping, also does mosaicking

**Analysis:**

**`housekeeping.py`:**
- Recovers stale `in_progress` groups → `pending`
- Marks stale `collecting` groups → `failed`
- Removes temp staging directories (`stream_*`)

**`cleanup_old_data.py`:**
- Deletes MS files older than N days
- Compresses log files older than N days
- Uses `get_active_applylist()` (but doesn't use it)

**`scheduler.py`:**
- Calls `housekeeping.py` periodically
- Also runs nightly mosaicking

**Overlap:**
- Both `housekeeping.py` and `cleanup_old_data.py` handle cleanup tasks
- `scheduler.py` calls `housekeeping.py` but not `cleanup_old_data.py`
- No coordination between cleanup scripts

**Recommendation:**
1. **Integrate `cleanup_old_data.py` into `housekeeping.py`**:
   ```python
   # Add to housekeeping.py
   def cleanup_old_ms_files(ms_dir: Path, days_to_keep: float) -> int:
       """Delete MS files older than specified days."""
       # From cleanup_old_data.py
   
   def compress_old_logs(log_dir: Path, days_to_keep: float) -> int:
       """Compress log files older than specified days."""
       # From cleanup_old_data.py
   ```
2. **Update `scheduler.py`** to call all cleanup functions
3. **Deprecate or remove** `cleanup_old_data.py` as standalone script
4. **Add CLI arguments** to `housekeeping.py` for MS/log cleanup:
   ```bash
   python ops/pipeline/housekeeping.py \
     --queue-db ... \
     --scratch-dir ... \
     --ms-dir /data/ms --ms-days-to-keep 30 \
     --log-dir state/logs --log-days-to-keep 90
   ```

**Impact:** Consolidates cleanup logic into single script

---

## 4. Similar Calibrator Processing Scripts

### 4.1 Central vs. Offset Calibrator Group Building

**Files:**
- `ops/pipeline/build_central_calibrator_group.py` (577 lines)
- `ops/pipeline/build_calibrator_transit_offsets.py` (519 lines)

**Analysis:**

**Similarities:**
- Both find calibrator transits using `previous_transits()`
- Both convert subband groups to MS using `_write_ms_group_via_uvh5_to_ms()`
- Both phase-shift MS to calibrator center
- Both populate MODEL_DATA with calibrator point source
- Both solve calibration (pre-phase, bandpass, phase gains)
- Both apply calibration and image
- Both record products in database
- Both generate NVSS overlays

**Differences:**
- `build_central_calibrator_group.py`: Single central group only
- `build_calibrator_transit_offsets.py`: Multiple groups in window, excludes central optionally

**Code Duplication:**
- ~400 lines of identical or near-identical code
- Calibration solving logic is identical
- MS conversion logic is identical
- Imaging logic is nearly identical

**Recommendation:**
1. **Extract shared calibration pipeline**:
   ```python
   # ops/pipeline/calibrator_pipeline.py
   def calibrate_and_image_group(
       ms_path: Path,
       calibrator_name: str,
       ra_deg: float,
       dec_deg: float,
       flux_jy: Optional[float],
       imsize: int = 2048,
       phasecenter: Optional[str] = None
   ) -> Tuple[Path, List[str]]:
       """Calibrate and image a calibrator group.
       
       Returns: (image_base_path, calibration_table_paths)
       """
       # Consolidated calibration + imaging logic
   ```
2. **Refactor both scripts** to use shared pipeline:
   - `build_central_calibrator_group.py`: Call pipeline once for central group
   - `build_calibrator_transit_offsets.py`: Call pipeline for each group in window
3. **Keep scripts as thin wrappers** that:
   - Find groups
   - Convert to MS (or use orchestrator)
   - Call shared pipeline
   - Record products

**Impact:** Reduces code duplication by ~400 lines, improves maintainability

---

## 5. Summary of Recommendations

### High Priority (Clear Redundancies)

1. **Remove legacy systemd service**
   - Archive or remove `ops/pipeline/dsa110-streaming-converter.service`
   - Document that `ops/systemd/contimg-stream.service` is current

2. **Consolidate helper functions**
   - Create `ops/pipeline/calibrator_helpers.py` for catalog loading
   - Create `ops/pipeline/group_helpers.py` for group ID parsing
   - Or better: Use existing `dsa110_contimg` modules where possible

3. **Merge cleanup scripts**
   - Integrate `cleanup_old_data.py` into `housekeeping.py`
   - Update `scheduler.py` to call all cleanup functions

### Medium Priority (Improves Maintainability)

4. **Refactor calibrator scripts**
   - Extract shared calibration pipeline
   - Keep scripts as thin wrappers

5. **Use orchestrator for MS conversion**
   - Refactor all scripts to use `hdf5_orchestrator` instead of direct `uvh5_to_ms` calls
   - This is the recommended production path

### Low Priority (Code Quality)

6. **Standardize MS writing**
   - If keeping direct calls, create shared `ms_conversion_helpers.py`
   - Prefer orchestrator approach

---

## 6. Implementation Plan

### Phase 1: Remove Legacy Files

1. Archive or remove `ops/pipeline/dsa110-streaming-converter.service`
2. Update `ops/systemd/INSTALL.md` to clarify which service file to use

### Phase 2: Consolidate Helpers

1. Create `ops/pipeline/calibrator_helpers.py`:
   - `load_ra_dec()` (with DB support)
   - `load_flux_jy()` (with DB support)
2. Create `ops/pipeline/group_helpers.py`:
   - `parse_group_id_from_path()`
3. Update all scripts to import from shared modules

### Phase 3: Merge Cleanup Scripts

1. Add MS/log cleanup functions to `housekeeping.py`
2. Update `scheduler.py` to call all cleanup functions
3. Deprecate `cleanup_old_data.py` (or remove if not used elsewhere)

### Phase 4: Refactor Calibrator Scripts

1. Extract shared calibration pipeline to `ops/pipeline/calibrator_pipeline.py`
2. Refactor both scripts to use shared pipeline
3. Test end-to-end workflows

---

## 7. Testing Considerations

After consolidation:
- Test all calibrator processing workflows
- Verify cleanup scripts work correctly
- Ensure no broken imports
- Test scheduler with integrated cleanup

---

## 8. Files to Review/Update

**Files to Remove/Archive:**
- `ops/pipeline/dsa110-streaming-converter.service` (legacy)
- `ops/pipeline/cleanup_old_data.py` (after merging into housekeeping.py)

**Files to Create:**
- `ops/pipeline/calibrator_helpers.py`
- `ops/pipeline/group_helpers.py` (or add to existing module)
- `ops/pipeline/calibrator_pipeline.py` (shared calibration pipeline)

**Files to Update:**
- `ops/pipeline/build_central_calibrator_group.py`
- `ops/pipeline/build_calibrator_transit_offsets.py`
- `ops/pipeline/image_groups_in_timerange.py`
- `ops/pipeline/curate_transit.py`
- `ops/pipeline/housekeeping.py`
- `ops/pipeline/scheduler.py`
- `ops/systemd/INSTALL.md`

---

**Next Steps:**
1. Review this analysis with team
2. Prioritize recommendations
3. Create implementation tickets
4. Execute consolidation phase by phase

