# Additional Safeguards Needed - Streaming Test Run Analysis

**Date:** 2025-11-10  
**Based on:** Review of streaming test run chat log and ICEBERG analysis

---

## Issues Identified That Need Safeguards

### 1. Group ID Collision Risk

**Problem:**
- Group IDs generated using `f"group_{int(time.time())}"` 
- If two groups are created in the same second, they'll have the same ID
- This causes database constraint violations or overwrites

**Location:**
- `streaming_mosaic.py` line 496: `group_id = f"group_{int(time.time())}"`
- `streaming_mosaic.py` line 2325: Same pattern in sliding window group

**Impact:**
- Database errors when inserting duplicate group_id
- Potential data loss if one group overwrites another
- Race condition in concurrent processing

**Safeguard Needed:**
- Use UUID or include microseconds: `f"group_{int(time.time() * 1000000)}"`
- Or use hash of ms_paths: `f"group_{hashlib.md5(ms_paths_str.encode()).hexdigest()[:12]}"`
- Add unique constraint on `group_id` in database schema
- Check for existing group_id before insert, retry with new ID if collision

---

### 2. Duplicate Group Detection Gap

**Problem:**
- Current check: `SELECT group_id FROM mosaic_groups WHERE ms_paths = ? AND status != 'completed'`
- This prevents duplicate groups with same MS paths
- BUT: What if same MS files are processed twice due to:
  - Database corruption/recovery
  - Manual intervention
  - State reset
  - Race condition where two processes check simultaneously

**Location:**
- `streaming_mosaic.py` lines 485-491: Duplicate check before group creation

**Impact:**
- Same MS files could be processed multiple times
- Wasted computation
- Potential inconsistencies

**Safeguard Needed:**
- Add check for MS files already in ANY group (not just non-completed)
- Add database-level unique constraint on `ms_paths` column
- Add validation that MS files aren't already in another active group
- Log warning if duplicate detected and skip

---

### 3. Missing Validation for Large Gaps in Observations

**Problem:**
- Current validation checks consecutive files are < 6 minutes apart
- BUT: What if there's a 1-hour gap between file 5 and file 6?
- The group would still pass validation (each consecutive pair is < 6 min)
- But the overall observation span would be too large for a coherent mosaic

**Location:**
- `streaming_mosaic.py` `_validate_sequential_5min_chunks()` method

**Impact:**
- Mosaics created from non-contiguous observations
- Poor quality mosaics with large time gaps
- Scientific validity compromised

**Safeguard Needed:**
- Add validation for total time span: 10 files × 5 minutes = 50 minutes max
- Add tolerance: total span should be < 60 minutes (allowing for small gaps)
- Reject groups with total span > 60 minutes
- Log warning if span is > 50 minutes but < 60 minutes

---

### 4. Error Recovery for Failed Publishes (ICEBERG #19)

**Problem:**
- If auto-publish fails (disk full, permissions, network error), mosaic stays in staging
- No retry mechanism
- No manual recovery path
- Mosaics orphaned forever

**Location:**
- `streaming_mosaic.py` `_register_mosaic_for_publishing()` method
- `data_registry` auto-publish logic

**Impact:**
- Mosaics never reach production
- Storage waste in staging
- No visibility into failed publishes

**Safeguard Needed:**
- Add retry logic with exponential backoff
- Add `publish_attempts` counter in `data_registry`
- Add `publish_error` field to store error messages
- Add monitoring/alerting for failed publishes
- Add manual publish trigger via API
- Add cleanup job to retry failed publishes periodically

---

### 5. Concurrent Access Race Conditions (ICEBERG #21)

**Problem:**
- Multiple processes might try to publish same mosaic simultaneously
- Race condition: check status → move file → update DB (gap between steps)
- No database-level locking
- No unique constraint on `data_id`

**Location:**
- `data_registry` publish logic
- `trigger_auto_publish()` function

**Impact:**
- Duplicate publish attempts
- File system conflicts
- Database inconsistencies
- Potential data loss

**Safeguard Needed:**
- Add database-level locking (SELECT FOR UPDATE)
- Add unique constraint on `data_id` in `data_registry` table
- Use atomic transaction for check → move → update
- Add `publishing` status to prevent concurrent attempts
- Add retry logic with backoff if lock acquisition fails

---

### 6. Path Validation Missing (ICEBERG #22)

**Problem:**
- `stage_path` must be within `/stage/dsa110-contimg/`
- `published_path` must be within `/data/dsa110-contimg/products/`
- No validation before move operations
- Path traversal vulnerability possible

**Location:**
- `trigger_auto_publish()` function
- `_register_mosaic_for_publishing()` method

**Impact:**
- Files could be moved outside allowed directories
- Security vulnerability (path traversal)
- Data loss if moved to wrong location

**Safeguard Needed:**
- Validate `stage_path` is within `/stage/dsa110-contimg/` before move
- Validate `published_path` is within `/data/dsa110-contimg/products/` after move
- Use `Path.resolve()` to resolve absolute paths
- Check that resolved path is within allowed directory
- Raise `ValueError` if path validation fails
- Add unit tests for path validation

---

### 7. Missing Validation: MS Files Already Processed

**Problem:**
- No check if MS files are already in another completed group
- Same MS files could be used in multiple mosaics
- This might be intentional (sliding window), but should be explicit

**Location:**
- `check_for_new_group()` method
- `check_for_sliding_window_group()` method

**Impact:**
- Unclear if duplicate use is intentional or error
- Potential confusion in data lineage
- Wasted computation if unintentional

**Safeguard Needed:**
- For non-sliding-window groups: Check if MS files are in any completed group
- For sliding-window groups: Allow overlap but log it explicitly
- Add `ms_files_used` tracking in `mosaic_groups` table
- Add validation query to check MS file usage history

---

### 8. Missing Validation: MS Files Have Required Stage

**Problem:**
- `check_for_new_group()` queries for `stage='converted' AND status='converted'`
- But doesn't verify MS files are actually ready for mosaic creation
- Should also check:
  - MS files have been calibrated (`cal_applied=1`)
  - MS files have been imaged (`stage='imaged'` or images exist)

**Location:**
- `check_for_new_group()` line 437: `WHERE stage = 'converted' AND status = 'converted'`

**Impact:**
- Groups formed from unconverted/uncalibrated MS files
- Mosaic creation fails later
- Wasted computation

**Safeguard Needed:**
- Update query to check `stage IN ('imaged', 'done')` instead of `'converted'`
- Or add separate validation that images exist for all MS files
- Verify images exist before group formation
- Log warning if MS files not fully processed

---

### 9. Missing Validation: Calibration Tables Exist Before Application

**Problem:**
- `apply_calibration_to_group()` retrieves calibration tables from registry
- But doesn't verify tables exist on filesystem before applying
- If tables are missing, calibration fails silently or crashes

**Location:**
- `apply_calibration_to_group()` method
- `get_active_applylist()` function

**Impact:**
- Calibration application fails
- MS files left in inconsistent state
- Mosaic creation fails

**Safeguard Needed:**
- Verify all calibration tables exist on filesystem before applying
- Check table directories exist and are readable
- Validate table structure (check for required files)
- Raise `FileNotFoundError` if tables missing
- Log error with table paths for debugging

---

### 10. Missing Validation: Image Files Exist Before Mosaic Creation

**Problem:**
- `create_mosaic()` gets image paths but doesn't verify they all exist
- If some images are missing, mosaic creation fails or creates incomplete mosaic

**Location:**
- `create_mosaic()` method
- Image path retrieval logic

**Impact:**
- Mosaic creation fails mid-process
- Incomplete mosaics
- Wasted computation

**Safeguard Needed:**
- Verify all image files exist before mosaic creation
- Check for PB-corrected FITS files specifically
- Validate image files are readable
- Raise `FileNotFoundError` if any images missing
- Log which images are missing for debugging

---

## Recommended Implementation Priority

### High Priority (Critical for Autonomous Runs)

1. **Group ID Collision Risk** - Could cause database errors
2. **Missing Validation: MS Files Have Required Stage** - Prevents wasted computation
3. **Missing Validation: Calibration Tables Exist** - Prevents silent failures
4. **Missing Validation: Image Files Exist** - Prevents mosaic creation failures

### Medium Priority (Important for Robustness)

5. **Error Recovery for Failed Publishes** - Prevents orphaned mosaics
6. **Concurrent Access Race Conditions** - Prevents data corruption
7. **Path Validation Missing** - Security and data integrity

### Low Priority (Nice to Have)

8. **Duplicate Group Detection Gap** - Edge case, but good to prevent
9. **Missing Validation for Large Gaps** - Quality improvement
10. **Missing Validation: MS Files Already Processed** - Data lineage clarity

---

## Implementation Notes

### Group ID Generation Fix

```python
import hashlib
import time

# Option 1: Include microseconds
group_id = f"group_{int(time.time() * 1000000)}"

# Option 2: Use hash of MS paths (deterministic, prevents duplicates)
ms_paths_hash = hashlib.md5(ms_paths_str.encode()).hexdigest()[:12]
group_id = f"group_{ms_paths_hash}_{int(time.time())}"

# Option 3: Use UUID (most robust)
import uuid
group_id = f"group_{uuid.uuid4().hex[:12]}"
```

### Total Time Span Validation

```python
def _validate_total_time_span(self, ms_paths_with_time: List[Tuple[float, str]]) -> bool:
    """Validate total time span is reasonable for mosaic."""
    if len(ms_paths_with_time) < 2:
        return True
    
    first_time = ms_paths_with_time[0][0]
    last_time = ms_paths_with_time[-1][0]
    total_span_days = last_time - first_time
    total_span_minutes = total_span_days * 24.0 * 60.0
    
    # 10 files × 5 minutes = 50 minutes ideal, allow up to 60 minutes
    max_span_minutes = 60.0
    
    if total_span_minutes > max_span_minutes:
        logger.debug(
            f"Total time span too large: {total_span_minutes:.2f} minutes "
            f"(max: {max_span_minutes:.2f} minutes)"
        )
        return False
    
    return True
```

### Path Validation Helper

```python
def validate_path_within_allowed(
    path: Path, 
    allowed_base: Path, 
    path_type: str = "path"
) -> Path:
    """Validate path is within allowed base directory.
    
    Raises:
        ValueError: If path is outside allowed directory
    """
    resolved_path = path.resolve()
    resolved_base = allowed_base.resolve()
    
    try:
        resolved_path.relative_to(resolved_base)
    except ValueError:
        raise ValueError(
            f"{path_type} {resolved_path} is outside allowed directory {resolved_base}"
        )
    
    return resolved_path
```

---

## Related Documentation

- **Full Review:** `docs/reports/streaming_test_run_review_2025-11-10.md`
- **ICEBERG Analysis:** See chat log sections 56520-56650
- **Existing Safeguards:** See review document for fixes already applied

---

**Status:** Analysis complete, ready for implementation  
**Next Steps:** Implement high-priority safeguards before next test run

