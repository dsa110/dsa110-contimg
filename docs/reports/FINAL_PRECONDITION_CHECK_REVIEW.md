# Final Precondition Check Review - "Measure Twice, Cut Once"

**Date:** 2025-11-02  
**Status:** Comprehensive review complete

## Summary of All Implemented Checks

### ✅ Conversion Pipeline (HDF5 → MS)

#### Entry Points Covered:
1. **Streaming Converter** (`streaming_converter.py`)
   - ✅ Input/output/scratch directory validation at startup
   - ✅ File readability validation before queuing
   - ✅ File size validation before queuing
   - ✅ HDF5 structure validation before queuing

2. **Batch Converter** (`hdf5_orchestrator.py`)
   - ✅ Input/output/scratch directory validation before processing
   - ✅ Time range validation (start < end)
   - ✅ File existence check before conversion
   - ✅ File readability validation before reading
   - ✅ Disk space check before conversion
   - ✅ Staging directory writability validation
   - ✅ Tmpfs writability validation (with fallback)
   - ✅ MS write validation after creation
   - ✅ Required columns validation
   - ✅ Partial MS cleanup on failure

3. **Direct-Subband Writer** (`direct_subband.py`)
   - ✅ Tmpfs writability validation before staging
   - ✅ Disk space check before staging
   - ✅ File readability validation before reading
   - ✅ Cleanup of partial staging files on failure

4. **API Job Runner** (`job_runner.py`)
   - ✅ Validation happens via orchestrator (subprocess)
   - ✅ Clear error messages logged to job log

### ✅ Calibration Pipeline

#### Entry Points Covered:
1. **Calibration CLI** (`calibration/cli.py`)
   - ✅ MS existence and readability validation
   - ✅ Field validation before processing
   - ✅ Reference antenna validation before processing
   - ✅ MODEL_DATA population success validation (hard error)
   - ✅ Fast subset MS validation
   - ✅ Catalog file validation

2. **Calibration Functions** (`calibration/calibration.py`)
   - ✅ MODEL_DATA existence/population check (K-calibration)
   - ✅ Field existence check
   - ✅ Reference antenna existence check
   - ✅ Unflagged data check
   - ✅ K-table validation before BP-calibration
   - ✅ K-table + BP-table validation before G-calibration

3. **Apply Calibration** (`calibration/applycal.py`)
   - ✅ Calibration table existence validation
   - ✅ Calibration table compatibility validation

### ✅ Validation Module (`calibration/validate.py`)

- ✅ Calibration table existence validation
- ✅ Antenna compatibility checks
- ✅ SPW compatibility checks
- ✅ Reference antenna validation (with outrigger suggestions)
- ✅ Enhanced error messages with actionable suggestions

## Remaining Considerations

### ⚠️ Low Priority - Nice to Have

1. **Writer Instantiation Failure Handling**
   - Current: Writer instantiation failures are caught by try/except
   - Enhancement: Could add explicit validation that required kwargs are present
   - Impact: Low - failures are caught and logged appropriately

2. **Standalone Converter** (`uvh5_to_ms.py`)
   - Current: Has file existence/readability checks (lines 463-474)
   - Status: Already has good precondition checks
   - Note: This is a different code path (single file conversion)

3. **Calibrator MS Service** (`calibrator_ms_service.py`)
   - Current: Has input validation (lines 743-751)
   - Status: Already validates inputs before conversion
   - Uses `write_ms_from_subbands()` which inherits validation from direct_subband writer

4. **Partial Staging File Cleanup**
   - Current: Cleanup happens in `finally` blocks (direct_subband.py:289-295)
   - Status: Partial files are cleaned up appropriately

5. **Exception Type Consistency**
   - Current: Mix of `ValueError`, `RuntimeError`, `FileNotFoundError`
   - Status: Appropriate exceptions for different failure modes
   - Note: Could standardize, but current approach is reasonable

### ✅ Fully Covered Areas

- **Directory validation**: All entry points validated
- **File validation**: Files checked before queuing, before reading, before conversion
- **Disk space**: Checked before conversion and staging
- **MS validation**: Validated after creation with cleanup on failure
- **Calibration preconditions**: All calibration steps validated
- **Time range**: Validated before processing
- **Staging directories**: Validated before use

## Conclusion

**All Priority 1 precondition checks are implemented.** The pipeline now follows "measure twice, cut once" throughout:

- ✅ All critical preconditions validated upfront
- ✅ Failures occur immediately with clear error messages
- ✅ Partial files cleaned up on failure
- ✅ Validation happens at all entry points
- ✅ Graceful degradation (e.g., tmpfs fallback)

**The pipeline is production-ready** with comprehensive precondition checking. Any remaining gaps are low-priority enhancements that would improve developer experience but don't address critical reliability issues.

## Recommendations

1. **Testing**: Test all validation paths with invalid inputs
2. **Monitoring**: Monitor validation failure rates to identify common issues
3. **Documentation**: Ensure error messages guide users to solutions
4. **Metrics**: Track validation failures to identify patterns

No critical gaps remain.

