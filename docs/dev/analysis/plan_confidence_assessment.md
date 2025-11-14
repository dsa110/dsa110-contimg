# Plan Confidence Assessment - Final Review

**Date:** 2025-11-12  
**Purpose:** Final assessment of implementation plan against actual codebase

---

## Key Findings from Code Review

### Task 1: Batch Conversion API

**Confidence:** 95% → **90%** (minor adjustment needed)

**Finding:** `create_batch_job()` expects `ms_paths: List[str]`, but conversion
uses `time_windows`. Need conversion-specific batch tracking.

**Solution:** Create `create_batch_conversion_job()` helper that tracks time
windows instead of MS paths.

---

### Task 2: Mosaic Creation API

**Confidence:** 90% → **85%** (needs orchestrator method)

**Findings:**

1. `create_job()` requires `ms_path TEXT NOT NULL` - will use first MS path from
   group
2. `create_mosaic_in_time_window()` doesn't exist - need to create it
3. Pattern exists: use `ensure_ms_files_in_window()` →
   `_form_group_from_ms_paths()` → `_process_group_workflow()`

**Solution:** Create `create_mosaic_in_time_window()` method following
`create_mosaic_centered_on_calibrator()` pattern.

---

### Task 3: Publishing CLI

**Confidence:** 85% → **90%** (straightforward, functions exist)

**Finding:** All required functions exist and are well-documented.

---

### Task 4: Photometry API Execution

**Confidence:** 85% → **90%** (better than expected)

**Finding:** Underlying functions `measure_forced_peak()` and `measure_many()`
exist in `photometry/forced.py` and return data structures directly (not just
print JSON). Can call these directly instead of CLI wrappers.

**Solution:** Call underlying functions directly, not CLI wrappers.

---

### Task 5: Unified QA CLI

**Confidence:** 75% (unchanged)

**Finding:** QA functions exist in multiple modules. Need to locate and verify
signatures.

---

### Task 6: Coordinated Group Imaging

**Confidence:** 75% → **80%** (clearer integration point)

**Findings:**

1. Integration point is clear: after `image_ms()` call in `_worker_loop()`
   (around line 891-978)
2. Need to extract `mid_mjd` using `extract_ms_time_range()` from
   `utils/time_utils.py`
3. Query `ms_index` table for MS files in time window
4. Check `DEFAULT_MS_PER_MOSAIC` constant for group size

**Solution:** Use existing time extraction utilities and database queries.

---

### Task 7: Streaming Mosaic/QA/Publishing

**Confidence:** 80% → **85%** (more automation exists than expected)

**Findings:**

1. `StreamingMosaicManager.create_mosaic()` already registers in `data_registry`
2. `finalize_data()` triggers QA pipeline automatically
3. `trigger_auto_publish()` runs automatically when QA passes

**Solution:** Verify that `create_mosaic()` calls `finalize_data()`, then
integration is straightforward.

---

### Task 8: End-to-End Integration Testing

**Confidence:** 75% (unchanged)

**Finding:** Test infrastructure exists, synthetic data generation patterns
exist.

---

## Overall Confidence Assessment

**Ready to Proceed:** ✅ **YES**

**Confidence Levels:**

- Tasks 1, 3, 4: 90% confidence (minor adjustments needed)
- Task 2: 85% confidence (need to create orchestrator method)
- Task 5: 75% confidence (need to locate QA functions)
- Task 6: 80% confidence (clear integration point)
- Task 7: 85% confidence (verify existing automation)
- Task 8: 75% confidence (standard testing)

**Risks Identified:**

1. **Low Risk:** Batch conversion needs custom tracking (Task 1)
2. **Low Risk:** Mosaic API needs new orchestrator method (Task 2)
3. **Low Risk:** QA CLI needs function discovery (Task 5)

**Mitigation:**

- All risks are low and have clear solutions
- Patterns exist for all tasks
- No blocking dependencies

---

## Recommended Adjustments to Plan

1. **Task 1:** Create conversion-specific batch tracking instead of using
   `create_batch_job()`
2. **Task 2:** Create `create_mosaic_in_time_window()` method in orchestrator
3. **Task 4:** Call underlying photometry functions directly, not CLI wrappers
4. **Task 6:** Use `extract_ms_time_range()` for time extraction
5. **Task 7:** Verify `create_mosaic()` already calls `finalize_data()`

---

## Conclusion

Plan is **sound and ready for implementation**. All tasks have clear patterns to
follow, and identified risks are low with straightforward solutions. Proceed
with confidence.
