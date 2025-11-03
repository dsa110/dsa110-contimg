# Priority 1 Precondition Checks Implementation Summary

**Date:** 2025-11-02  
**Implementation:** All Priority 1 precondition checks from pipeline workflow review

## Implemented Checks

### ✅ 1. Input/Output Directory Validation

**Location:** `src/dsa110_contimg/conversion/streaming/streaming_converter.py:628-669`

**Checks:**
- Input directory exists and is readable
- Output directory exists and is writable (creates if needed)
- Scratch directory exists and is writable (if provided)

**Error Handling:** Returns exit code 1 with clear error messages

### ✅ 2. File Readability Validation Before Queuing

**Location:** `src/dsa110_contimg/conversion/streaming/streaming_converter.py:352-402`

**Checks:**
- File exists
- File is readable
- File size > 0 bytes
- File size > 1KB (warns if suspiciously small)
- File is valid HDF5/UVH5 structure (has Header or Data group)

**Error Handling:** Logs warnings and skips invalid files (doesn't crash service)

### ✅ 3. File Existence Check Before Conversion

**Location:** `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py:266-283`

**Checks:**
- All files in group exist
- All files in group are readable

**Error Handling:** Logs error and skips group if files missing/unreadable

### ✅ 4. File Readability Validation Before Reading

**Location:** `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py:198-214`

**Checks:**
- File exists
- File is readable
- File is valid HDF5 structure

**Error Handling:** Raises `FileNotFoundError`, `PermissionError`, or `ValueError` with clear messages

### ✅ 5. Disk Space Check Before Conversion

**Location:** `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py:294-327`

**Checks:**
- Estimates MS size as 2x input size
- Verifies sufficient space in output directory
- Verifies sufficient space in scratch directory (if provided, warns if limited)

**Error Handling:** Logs error and skips group if insufficient space; warns if scratch space limited

### ✅ 6. MS Write Validation After MS Creation

**Location:** `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py:421-457`

**Checks:**
- MS exists after write
- MS has data rows (nrows > 0)
- MS has required columns: DATA, ANTENNA1, ANTENNA2, TIME, UVW

**Error Handling:** Raises `RuntimeError` with clear message; cleans up partial MS on failure

## Impact

**Before:** Pipeline could fail after expensive operations (file reading, conversion, staging), wasting time and resources.

**After:** All critical preconditions validated upfront, following "measure twice, cut once". Failures occur immediately with clear error messages.

## Testing Recommendations

1. **Directory Validation:** Test with non-existent, non-readable, non-writable directories
2. **File Validation:** Test with corrupted, empty, or deleted HDF5 files
3. **Disk Space:** Test with insufficient disk space scenarios
4. **MS Validation:** Test with partial/corrupted MS files

## Next Steps

Priority 2 checks (from review):
- File size validation refinement
- Metadata consistency checks
- Staging directory validation
- Timestamp validation

These can be implemented incrementally as needed.

