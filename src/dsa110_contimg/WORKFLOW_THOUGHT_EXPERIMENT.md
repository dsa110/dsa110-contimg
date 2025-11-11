# Complete Workflow Thought Experiment: HDF5 → Published Mosaic

## Workflow Stages

### Stage 1: File Ingestion & Registration
**Location**: `streaming_converter.py` → `bootstrap_directory()` / `_polling_loop()`

1. HDF5 files arrive in `/data/incoming/`
2. Files detected via polling or watchdog
3. `parse_subband_info()` extracts `(group_id, subband_idx)` from filename
4. `record_subband()` stores in `ingest.sqlite3`:
   - `subband_files` table: `(group_id, subband_idx, path)`
   - `ingest_queue` table: `(group_id, state, received_at, ...)`
5. Group ID normalized: `YYYY-MM-DDTHH:MM:SS`

**ICEBERG #1**: ✅ FIXED - Bootstrap now skips already-registered files
**ICEBERG #2**: ✅ FIXED - Polling uses database-backed persistence

---

### Stage 2: MS Conversion
**Location**: `streaming_converter.py` → `_worker_loop()` → `convert_subband_groups_to_ms()`

1. Worker picks group from `ingest_queue` where `state='pending'`
2. Updates state to `'processing'`
3. Calls `convert_subband_groups_to_ms()` with:
   - `start_time`, `end_time` derived from group_id
   - `path_mapper` to organize MS files
4. Conversion creates MS file: `<group_id>.ms`
5. MS file written to: `/stage/dsa110-contimg/ms/science/YYYY-MM-DD/<group_id>.ms/`
6. `ms_index_upsert()` records in `products.sqlite3`:
   - `ms_index` table: `(path, start_mjd, end_mjd, mid_mjd, status='converted', stage='converted')`
7. State updated to `'completed'`

**ICEBERG #3**: ✅ FIXED - MS file existence verified before processing
**ICEBERG #4**: ✅ FIXED - Phase centers fixed after concatenation

---

### Stage 3: Group Formation
**Location**: `streaming_mosaic.py` → `check_for_new_group()`

1. Queries `ms_index` for 10 MS files with `status='converted'`
2. Sorts by `mid_mjd` (chronological order)
3. Verifies MS files exist on disk
4. Creates entry in `mosaic_groups` table:
   - `(group_id, ms_paths, status='pending', created_at)`
5. Returns `group_id`

**ICEBERG #5**: ✅ FIXED - MS file existence verified before group formation

---

### Stage 4: Calibration Solving
**Location**: `streaming_mosaic.py` → `solve_calibration_for_group()`

1. Selects 5th MS (index 4) as calibration MS
2. **Bandpass Calibration**:
   - Queries `bandpass_calibrators` table for Dec range
   - Checks `cal_registry.sqlite3` for active BP tables
   - If not found, solves BP using calibration MS
   - Registers BP tables in `cal_registry.sqlite3` with validity window
3. **Gain Calibration**:
   - Checks registry for GP/2G tables valid for group time
   - If not found, solves GP/2G using calibration MS
   - Registers GP/2G tables in registry
4. Updates `mosaic_groups`: `bpcal_solved=1`, `calibration_ms_path`

**ICEBERG #6**: ✅ FIXED - Calibration table existence verified on disk
**ICEBERG #7**: ✅ FIXED - Registry checks verify files exist

---

### Stage 5: Calibration Application
**Location**: `streaming_mosaic.py` → `apply_calibration_to_group()`

1. Checks database: if `stage='calibrated'` and `cal_applied=1`, skip
2. Retrieves active calibration tables from registry for group time
3. Applies BP, GP, 2G tables to all 10 MS files
4. Updates `mosaic_groups`: `stage='calibrated'`, `cal_applied=1`, `calibrated_at`

**ICEBERG #8**: ✅ FIXED - Idempotent calibration application

---

### Stage 6: Imaging
**Location**: `streaming_mosaic.py` → `image_group()`

1. Checks database: if `stage='imaged'`, verify filesystem, skip if all exist
2. For each MS file:
   - Derives image basename: `<ms_stem>.img`
   - Checks if image already exists (pbcor_fits, pbcor, image)
   - If missing, calls `image_ms()` to create image
   - Records in `images` table: `(path, ms_path, created_at, type, ...)`
3. Updates `mosaic_groups`: `stage='imaged'`, `imaged_at`

**ICEBERG #9**: ✅ FIXED - Idempotent imaging with filesystem verification

---

### Stage 7: Mosaic Creation
**Location**: `streaming_mosaic.py` → `create_mosaic()`

1. Checks database: if `status='completed'` and `mosaic_path` exists, skip
2. Gets image paths for group (chronologically sorted)
3. Validates tiles consistency: `validate_tiles_consistency()`
4. Constructs mosaic ID: `mosaic_<group_id>_<timestamp>`
5. Creates mosaic: `<mosaic_output_dir>/<mosaic_id>.image` or `.fits`
6. Generates PNG visualization (optional)
7. Updates `mosaic_groups`: `status='completed'`, `mosaic_id`, `mosaicked_at`

**ICEBERG #10**: ✅ FIXED - Idempotent mosaic creation

---

### Stage 8: Cross-Matching (Optional)
**Location**: `streaming_mosaic.py` → `run_crossmatch_for_mosaic()`

1. If `config.crossmatch.enabled`:
   - Creates `PipelineContext` with mosaic path
   - Executes `CrossMatchStage`
   - Records cross-match results

**Status**: ✅ Implemented

---

### Stage 9: Registration & Publishing
**Location**: ❌ **MISSING - CRITICAL ICEBERG**

**Expected Flow**:
1. Register mosaic in `data_registry`:
   - `data_type='mosaic'`
   - `data_id=<mosaic_id>`
   - `stage_path=<mosaic_path>`
   - `status='staging'`
   - `auto_publish=True`
2. Finalize data:
   - Call `finalize_data()` with `qa_status='passed'`, `validation_status='validated'`
   - This triggers `trigger_auto_publish()` if criteria met
3. Auto-publish:
   - Move mosaic from `/stage/dsa110-contimg/mosaics/` to `/data/dsa110-contimg/products/mosaics/`
   - Update `data_registry`: `status='published'`, `published_path`, `published_at`

**ICEBERG #11**: ❌ **CRITICAL** - Mosaic is NEVER registered in `data_registry`
**ICEBERG #12**: ❌ **CRITICAL** - Mosaic is NEVER finalized
**ICEBERG #13**: ❌ **CRITICAL** - Mosaic is NEVER moved to `/data/`
**ICEBERG #14**: ❌ **CRITICAL** - No QA/validation status set before publish

---

## Additional Icebergs Found

### ICEBERG #15: Path Resolution Issues
- `mosaic_output_dir` might not be absolute path
- `published_path` construction uses `stage_path_obj.name` which might lose directory structure
- Need to verify paths are resolved before database storage

### ICEBERG #16: Database Transaction Consistency
- `create_mosaic()` updates `mosaic_groups` but doesn't register in `data_registry`
- If registration fails, mosaic exists but isn't tracked for publishing
- Need atomic transaction or rollback mechanism

### ICEBERG #17: QA Status Unknown
- Mosaic validation happens in `validate_tiles_consistency()` but status not stored
- `finalize_data()` requires `qa_status='passed'` for auto-publish
- Need to capture validation results and set QA status

### ICEBERG #18: Mosaic Metadata Missing
- `data_registry` stores `metadata_json` but mosaic metadata not populated
- Should include: `group_id`, `n_images`, `time_range`, `calibrator_name`, etc.

### ICEBERG #19: Error Recovery
- If auto-publish fails (disk full, permissions), mosaic stays in staging
- No retry mechanism or manual publish trigger
- Need error handling and recovery path

### ICEBERG #20: File Move Safety
- `shutil.move()` is atomic but if it fails mid-move, file might be lost
- Need to verify source exists before move
- Need to verify destination after move
- Need rollback if database update fails after move

### ICEBERG #21: Concurrent Access
- Multiple processes might try to publish same mosaic
- Need database-level locking or unique constraint on `data_id`
- Race condition: check status → move file → update DB (gap between steps)

### ICEBERG #22: Path Validation
- `stage_path` must be within `/stage/dsa110-contimg/`
- `published_path` must be within `/data/dsa110-contimg/products/`
- Need path validation before move operations

### ICEBERG #23: Mosaic Naming Consistency
- Mosaic ID constructed: `mosaic_<group_id>_<timestamp>`
- But `data_id` should match for tracking
- Need consistent naming between `mosaic_groups.mosaic_id` and `data_registry.data_id`

### ICEBERG #24: Missing Validation Status
- Mosaic validation happens but result not stored
- `finalize_data()` checks `validation_status='validated'` but it's never set
- Need to store validation result from `validate_tiles_consistency()`

---

## Summary of Critical Issues

1. **Mosaic never registered in `data_registry`** - No tracking for publishing
2. **Mosaic never finalized** - Auto-publish never triggered
3. **Mosaic never moved to `/data/`** - Stays in staging forever
4. **QA/Validation status never set** - Auto-publish criteria never met
5. **No error recovery** - Failed publishes leave mosaics orphaned
6. **Race conditions** - Concurrent publish attempts not handled
7. **Path validation missing** - No checks before file moves
8. **Metadata incomplete** - Mosaic metadata not stored in registry

---

## Required Fixes

1. Add `register_mosaic_in_data_registry()` after mosaic creation
2. Add `finalize_mosaic()` call with QA/validation status
3. Ensure auto-publish triggers correctly
4. Add error handling and retry logic
5. Add path validation before moves
6. Add database-level locking for concurrent access
7. Store validation results in metadata
8. Add monitoring/logging for publish failures

