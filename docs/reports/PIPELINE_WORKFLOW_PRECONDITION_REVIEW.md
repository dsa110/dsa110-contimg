# Pipeline Workflow Review - "Measure Twice, Cut Once"

**Date:** 2025-11-02  
**Scope:** Complete pipeline from HDF5 ingestion through calibration

## Pipeline Stages Overview

### Stage 1: HDF5 File Ingestion & Discovery
**Entry Points:**
- `streaming_converter.py` - Real-time daemon watching `/data/incoming/`
- `hdf5_orchestrator.py` - Batch converter for time ranges
- `calibrator_ms_service.py` - Calibrator-specific MS generation

### Stage 2: File Grouping & Validation
**Process:** Group 16 subband files by timestamp (within 5-minute windows)

### Stage 3: Conversion (UVH5 → MS)
**Process:** Convert subband groups to CASA Measurement Sets

### Stage 4: Calibration
**Process:** K → BP → G calibration solve and apply

### Stage 5: Imaging
**Process:** Continuum imaging with tclean/WSClean

---

## Detailed Precondition Review

### Stage 1: HDF5 File Ingestion & Discovery

#### ✅ Current Checks

1. **File Pattern Matching** (`streaming_converter.py:55-69`)
   - Regex pattern: `(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb(?P<index>\d{2})\.hdf5$`
   - Validates filename format before processing

2. **Queue Database Schema** (`streaming_converter.py:126-180`)
   - Schema validation and migration
   - Tracks group completeness

#### ❌ Missing Precondition Checks

**1. File Readability Validation**
- **Location:** `streaming_converter.py:_record_file()` (line ~370)
- **Issue:** Files are recorded in queue without verifying they're readable/valid
- **Risk:** Corrupted files queued, conversion fails partway through
- **Fix Required:**
  ```python
  # Before recording file in queue, verify it's readable
  try:
      import h5py
      with h5py.File(filepath, 'r') as f:
          # Quick sanity check: verify file has required groups/keys
          if 'Header' not in f and 'Data' not in f:
              raise ValueError(f"Invalid HDF5 structure: {filepath}")
  except Exception as e:
      logger.error(f"File {filepath} is not readable: {e}")
      return  # Skip this file
  ```

**2. File Size Validation**
- **Location:** `streaming_converter.py:_record_file()`
- **Issue:** No check for zero-byte or suspiciously small files
- **Risk:** Empty/corrupted files cause conversion failures
- **Fix Required:**
  ```python
  file_size = os.path.getsize(filepath)
  if file_size == 0:
      logger.error(f"File {filepath} is empty (0 bytes)")
      return
  if file_size < 1024:  # Less than 1KB is suspicious
      logger.warning(f"File {filepath} is suspiciously small: {file_size} bytes")
  ```

**3. Input Directory Validation**
- **Location:** `streaming_converter.py:main()` (line ~616)
- **Issue:** No validation that input directory exists and is readable
- **Risk:** Service starts but fails silently when files arrive
- **Fix Required:**
  ```python
  if not os.path.exists(args.input_dir):
      p.error(f"Input directory does not exist: {args.input_dir}")
  if not os.path.isdir(args.input_dir):
      p.error(f"Input path is not a directory: {args.input_dir}")
  if not os.access(args.input_dir, os.R_OK):
      p.error(f"Input directory is not readable: {args.input_dir}")
  ```

**4. Output Directory Validation**
- **Location:** `streaming_converter.py:main()`
- **Issue:** No validation that output directory exists and is writable
- **Risk:** Conversion fails when writing MS files
- **Fix Required:**
  ```python
  os.makedirs(args.output_dir, exist_ok=True)
  if not os.access(args.output_dir, os.W_OK):
      p.error(f"Output directory is not writable: {args.output_dir}")
  ```

### Stage 2: File Grouping & Validation

#### ✅ Current Checks

1. **Group Completeness** (`hdf5_orchestrator.py:181`)
   - Verifies all 16 subbands present: `if set(subband_map.keys()) == set(spw)`
   - Only processes complete groups

#### ❌ Missing Precondition Checks

**1. File Existence Before Grouping**
- **Location:** `hdf5_orchestrator.py:find_subband_groups()` (line ~100)
- **Issue:** Groups files by timestamp without verifying files still exist
- **Risk:** Files deleted between discovery and conversion
- **Fix Required:**
  ```python
  # After grouping, verify all files exist
  for group in groups:
      missing_files = [f for f in group if not os.path.exists(f)]
      if missing_files:
          logger.error(f"Group has missing files: {missing_files}")
          groups.remove(group)  # Skip incomplete group
  ```

**2. File Consistency Check**
- **Location:** `hdf5_orchestrator.py:find_subband_groups()`
- **Issue:** No verification that files in group have consistent metadata
- **Risk:** Mixed observations grouped together
- **Fix Required:**
  ```python
  # After grouping, verify metadata consistency
  for group in groups:
      if not _verify_group_consistency(group):
          logger.error(f"Group files have inconsistent metadata: {group}")
          groups.remove(group)
  ```

**3. Timestamp Validation**
- **Location:** `streaming_converter.py:parse_subband_info()`
- **Issue:** No validation that timestamp is reasonable (not in future, not too old)
- **Risk:** Invalid timestamps cause grouping issues
- **Fix Required:**
  ```python
  # After parsing timestamp, validate it
  try:
      dt = datetime.fromisoformat(gid)
      now = datetime.now()
      if dt > now:
          logger.warning(f"File has future timestamp: {gid}")
      if dt < now - timedelta(days=365):
          logger.warning(f"File has very old timestamp: {gid}")
  except ValueError:
      logger.error(f"Invalid timestamp format: {gid}")
      return None
  ```

### Stage 3: Conversion (UVH5 → MS)

#### ✅ Current Checks

1. **UVData Validation** (`uvh5_to_ms.py:546-557`)
   - Calls `uvd.check()` after reading
   - Handles critical errors vs warnings

2. **Data Quality Assessment** (`uvh5_to_ms.py:560-565`)
   - Validates data quality after reading
   - Generates calibration recommendations

3. **MS QA Check** (`hdf5_orchestrator.py:377-388`)
   - Runs `check_ms_after_conversion()` after MS creation
   - Non-fatal (logs warning but continues)

#### ❌ Missing Precondition Checks

**1. File Readability Before Reading**
- **Location:** `hdf5_orchestrator.py:_load_and_merge_subbands()` (line ~197)
- **Issue:** Attempts to read files without verifying they're readable
- **Risk:** Conversion fails partway through reading files
- **Fix Required:**
  ```python
  for i, path in enumerate(file_list):
      # PRECONDITION CHECK: Verify file is readable before reading
      if not os.path.exists(path):
          raise FileNotFoundError(f"Subband file does not exist: {path}")
      if not os.access(path, os.R_OK):
          raise PermissionError(f"Subband file is not readable: {path}")
      
      # Quick HDF5 structure check
      try:
          import h5py
          with h5py.File(path, 'r') as f:
              if 'Header' not in f and 'Data' not in f:
                  raise ValueError(f"Invalid HDF5 structure: {path}")
      except Exception as e:
          raise ValueError(f"File {path} is not a valid HDF5 file: {e}") from e
      
      # Now read the file
      tmp.read(path, ...)
  ```

**2. Disk Space Check**
- **Location:** `hdf5_orchestrator.py:convert_subband_groups_to_ms()`
- **Issue:** No check for available disk space before conversion
- **Risk:** Conversion fails partway through, leaving partial MS
- **Fix Required:**
  ```python
  # Estimate MS size (rough: 2x input size for safety)
  total_input_size = sum(os.path.getsize(f) for f in file_list)
  estimated_ms_size = total_input_size * 2
  
  # Check available space
  import shutil
  free_space = shutil.disk_usage(output_dir).free
  if free_space < estimated_ms_size:
      raise RuntimeError(
          f"Insufficient disk space: need ~{estimated_ms_size/1e9:.1f}GB, "
          f"available {free_space/1e9:.1f}GB"
      )
  ```

**3. Staging Directory Validation**
- **Location:** `hdf5_orchestrator.py:convert_subband_groups_to_ms()`
- **Issue:** No validation that staging directory (tmpfs) exists and is writable
- **Risk:** Falls back to slower disk staging without warning
- **Fix Required:**
  ```python
  # Validate staging directory
  if staging_dir:
      if not os.path.exists(staging_dir):
          raise RuntimeError(f"Staging directory does not exist: {staging_dir}")
      if not os.access(staging_dir, os.W_OK):
          raise RuntimeError(f"Staging directory is not writable: {staging_dir}")
  ```

**4. Writer Selection Validation**
- **Location:** `hdf5_orchestrator.py:convert_subband_groups_to_ms()`
- **Issue:** No validation that selected writer is available/configured
- **Risk:** Writer fails unexpectedly
- **Fix Required:**
  ```python
  writer = get_writer(writer_name)
  if writer is None:
      raise ValueError(f"Writer '{writer_name}' not found or not configured")
  ```

**5. MS Write Success Validation**
- **Location:** `hdf5_orchestrator.py:convert_subband_groups_to_ms()`
- **Issue:** No verification that MS was written successfully before finalizing
- **Risk:** Partial/corrupted MS files marked as complete
- **Fix Required:**
  ```python
  # After MS creation, verify it's valid
  try:
      from casacore.tables import table
      with table(ms_path, readonly=True) as tb:
          if tb.nrows() == 0:
              raise RuntimeError(f"MS has no data rows: {ms_path}")
          # Verify required columns exist
          required_cols = ['DATA', 'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW']
          missing_cols = [c for c in required_cols if c not in tb.colnames()]
          if missing_cols:
              raise RuntimeError(f"MS missing required columns: {missing_cols}")
  except Exception as e:
      logger.error(f"MS validation failed: {e}")
      # Clean up partial MS
      shutil.rmtree(ms_path, ignore_errors=True)
      raise
  ```

### Stage 4: Calibration

#### ✅ Already Implemented (from previous review)

- MS existence and readability
- Field validation
- Reference antenna validation
- MODEL_DATA population success
- Calibration table validation

### Stage 5: Imaging

#### ⚠️ Potential Missing Checks (Not Reviewed in Detail)

- MS exists and is readable
- Calibration tables exist and are compatible
- Sufficient disk space for images
- Image parameters validated

---

## Summary Table

| Stage | Area | Risk Level | Impact | Fix Priority |
|-------|------|-----------|--------|--------------|
| Ingestion | File readability | High | Corrupted files queued | High |
| Ingestion | File size validation | Medium | Empty files cause failures | Medium |
| Ingestion | Directory validation | High | Service fails silently | High |
| Grouping | File existence | Medium | Files deleted between discovery/conversion | Medium |
| Grouping | Metadata consistency | Medium | Mixed observations grouped | Medium |
| Conversion | File readability | High | Conversion fails partway | High |
| Conversion | Disk space check | High | Partial MS files | High |
| Conversion | Staging directory | Medium | Performance degradation | Medium |
| Conversion | MS write validation | High | Corrupted MS marked complete | High |

---

## Recommended Implementation Order

### Priority 1: Critical Preconditions (Fail Fast)

1. **Input/Output directory validation** - Check at service startup
2. **File readability validation** - Check before queuing files
3. **File existence check** - Verify before conversion
4. **Disk space check** - Verify before conversion
5. **MS write validation** - Verify after MS creation

### Priority 2: Medium Preconditions (Prevent Issues)

6. **File size validation** - Check before queuing
7. **Metadata consistency** - Verify group consistency
8. **Staging directory validation** - Check before staging

### Priority 3: Low Preconditions (Better Error Messages)

9. **Timestamp validation** - Validate timestamp format/reasonableness
10. **Writer selection validation** - Verify writer available

---

## Impact

**Current State:** Pipeline may fail after expensive operations (file reading, conversion, staging), wasting time and resources.

**After Fixes:** All critical preconditions validated upfront, following "measure twice, cut once". Failures occur immediately with clear error messages.

The pipeline workflow will validate all prerequisites before expensive operations, preventing wasted time and ensuring consistent, reliable results.

