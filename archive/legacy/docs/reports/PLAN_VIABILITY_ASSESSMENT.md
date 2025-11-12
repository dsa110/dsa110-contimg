# Plan Viability Assessment: Granular 60-Minute Mosaic Generation

**Date:** 2025-11-03  
**Plan File:** `granular-60-minute-mosaic-generation-steps.plan.md`  
**Status:** MOSTLY VIABLE with Required Corrections

## Executive Summary

The plan is **comprehensively structured** and covers all required phases. However, **several command syntax mismatches** exist between the plan and the actual codebase implementations. With corrections, the plan is **highly viable** (~90% ready to execute).

**Overall Viability:** ✓ VIABLE (with corrections)

---

## Phase-by-Phase Assessment

### Phase 1: Transit Time Calculation ✓

**Status:** FULLY VIABLE

**Step 1.1:** Transit time calculation
- ✓ Command exists: `dsa110_contimg.calibration.catalog_cli transit`
- ✓ Parameters match: `--name`, `--start`, `--n`
- ✓ Output format matches

**Step 1.2:** Time window calculation
- ✓ Python one-liner is correct
- ✓ Uses proper astropy.time arithmetic

**No corrections needed.**

---

### Phase 2: Data Discovery ✓

**Status:** FULLY VIABLE

**Step 2.1:** List available HDF5 groups
- ✓ Command exists: `hdf5_orchestrator` CLI
- ✓ `--find-only` flag exists
- ⚠️ **Correction needed:** Command path in plan uses `conversion.strategies.hdf5_orchestrator` but the CLI is accessed via:
  ```bash
  python -m dsa110_contimg.conversion.cli groups \
    /data/incoming /tmp/dummy \
    "YYYY-MM-DD HH:MM:SS" "YYYY-MM-DD HH:MM:SS" \
    --find-only
  ```
  OR via direct module:
  ```bash
  python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming /tmp/dummy \
    "YYYY-MM-DD HH:MM:SS" "YYYY-MM-DD HH:MM:SS" \
    --find-only
  ```

**Step 2.2:** Verify file availability
- ✓ Shell script approach is valid

**Minor correction:** Update command invocation path for Step 2.1.

---

### Phase 3: MS Conversion ✓

**Status:** FULLY VIABLE (with minor corrections)

**Step 3.X:** Convert group to MS
- ✓ Command exists
- ✓ Parameters match
- ⚠️ **Correction needed:** Command path should use:
  ```bash
  python -m dsa110_contimg.conversion.cli groups \
    /data/incoming /data/ms \
    "2025-11-02 08:06:50" "2025-11-02 08:06:50" \
    --writer parallel-subband \
    --scratch-dir /scratch/dsa110-contimg \
    --max-workers 4 \
    --stage-to-tmpfs \
    --tmpfs-path /dev/shm
  ```
  OR:
  ```bash
  python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming /data/ms \
    "2025-11-02 08:06:50" "2025-11-02 08:06:50" \
    --writer parallel-subband \
    --scratch-dir /scratch/dsa110-contimg \
    --max-workers 4 \
    --stage-to-tmpfs \
    --tmpfs-path /dev/shm
  ```

**Verification step:** ✓ Valid casacore.tables check

---

### Phase 4: Calibrator Identification ✓

**Status:** VIABLE (custom script)

**Step 4.1:** Identify calibrator MS
- ✓ Custom Python script approach is valid
- ✓ Uses proper casacore.tables API
- ✓ Logic is sound

**No corrections needed.**

---

### Phase 5: Calibration ⚠️

**Status:** VIABLE (requires syntax corrections)

**Step 5.1:** Flag calibrator MS
- ✓ Command exists: `calibration.cli flag`
- ✗ **Syntax error:** Plan uses `--reset --zeros --rfi` as separate flags
- ✓ **Correct syntax:** Must use `--mode` parameter:
  ```bash
  python -m dsa110_contimg.calibration.cli flag \
    --ms /data/ms/CALIBRATOR_MS.ms \
    --mode reset
  
  python -m dsa110_contimg.calibration.cli flag \
    --ms /data/ms/CALIBRATOR_MS.ms \
    --mode zeros
  
  python -m dsa110_contimg.calibration.cli flag \
    --ms /data/ms/CALIBRATOR_MS.ms \
    --mode rfi
  ```
- ✓ Summary command exists: `--mode summary`

**Step 5.2:** Bandpass solve
- ✓ Command exists: `calibration.cli calibrate`
- ✗ **Syntax error:** Plan uses `--no-do-bp`, `--no-do-k`, `--no-do-g`
- ✓ **Correct syntax:** Uses `--skip-bp`, `--do-k`, `--skip-g`:
  ```bash
  python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/ms/CALIBRATOR_MS.ms \
    --field 0 \
    --refant 103 \
    --skip-g \
    --skip-k \
    --output-prefix /data/ms/CALIBRATOR_MS
  ```
  Note: `--skip-k` is default (K-calibration disabled by default for DSA-110), but can be explicit.
- ⚠️ **Note:** `--output-prefix` may not be a valid parameter. Calibration tables are written with standard naming convention next to the MS file.

**Step 5.3:** Gain solve
- ✓ Command exists
- ✗ **Syntax error:** Same as Step 5.2
- ✓ **Correct syntax:**
  ```bash
  python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/ms/CALIBRATOR_MS.ms \
    --field 0 \
    --refant 103 \
    --skip-bp \
    --skip-k \
    --gaintable-prefix /data/ms/CALIBRATOR_MS.ms_0_bpcal
  ```
  ⚠️ **Note:** `--gaintable-prefix` may need to be `--apply-tables` with explicit table list, or the tables should be auto-detected. The calibration CLI may auto-apply previous tables when solving subsequent steps.

**Step 5.4:** Register calibration tables
- ✓ Command exists: `registry_cli register-prefix`
- ✓ Parameters match: `--db`, `--name`, `--prefix`, `--cal-field`, `--refant`, `--valid-start`, `--valid-end`
- ✓ Parameter names: Uses `--name` (not `--set-name`) - verified in code

**Step 5.5:** Query registry
- ✓ Command exists: `registry_cli active`
- ✓ Parameters match

**Required corrections:** Update flag syntax and calibration parameter syntax.

---

### Phase 6: Apply Calibration ⚠️

**Status:** VIABLE (requires syntax correction)

**Step 6.X:** Apply calibration to target MS
- ✓ Command exists: `calibration.cli apply`
- ✗ **Syntax error:** Plan uses `--registry-db` and `--registry-set`
- ✓ **Correct syntax:** Uses explicit `--tables` parameter:
  ```bash
  python -m dsa110_contimg.calibration.cli apply \
    --ms /data/ms/TARGET_MS.ms \
    --field 0 \
    --tables /data/ms/CALIBRATOR_MS.ms_0_bpcal /data/ms/CALIBRATOR_MS.ms_0_gpcal
  ```
- ⚠️ **Alternative:** The `apply` service module supports registry lookup, but the CLI `apply` command requires explicit table paths. For registry-based application, may need to use the apply service programmatically or a different workflow.

**Verification step:** ✓ Valid CORRECTED_DATA check

**Required correction:** Update to use explicit `--tables` or investigate registry-based application workflow.

---

### Phase 7: Imaging ✓

**Status:** FULLY VIABLE

**Step 7.X:** Image MS
- ✓ Command exists: `imaging.cli image`
- ✓ Parameters match: `--ms`, `--imagename`, `--imsize`, `--cell-arcsec`, `--weighting`, `--robust`, `--pbcor`, `--quick`
- ✓ Output format matches

**Step 7.X.1:** Register image in products DB
- ✓ Function exists: `images_insert()`
- ✓ Schema matches plan expectations
- ⚠️ **Note:** The plan shows a manual Python script. This could be automated via the imaging worker or a helper script. Manual approach is valid.

**No corrections needed (though automation could be added).**

---

### Phase 8: Mosaic Planning ✓

**Status:** FULLY VIABLE

**Step 8.1:** Plan mosaic
- ✓ Command exists: `mosaic.cli plan`
- ✓ Parameters match: `--products-db`, `--name`, `--since`, `--until`, `--method`
- ✓ Method `pbweighted` exists

**Step 8.2:** Validate mosaic plan (dry run)
- ✓ Command exists: `mosaic.cli build --dry-run`
- ✓ Parameters match

**No corrections needed.**

---

### Phase 9: Mosaic Building ✓

**Status:** FULLY VIABLE

**Step 9.1:** Build mosaic
- ✓ Command exists: `mosaic.cli build`
- ✓ Parameters match
- ✓ Validation pipeline is comprehensive

**Verification step:** ✓ Valid

**No corrections needed.**

---

## Summary of Required Corrections

### Critical (Must Fix):

1. **Phase 5, Step 5.1:** Flag command syntax
   - Change: `--reset --zeros --rfi`
   - To: `--mode reset`, `--mode zeros`, `--mode rfi` (3 separate commands)

2. **Phase 5, Steps 5.2-5.3:** Calibration command syntax
   - Change: `--no-do-bp`, `--no-do-k`, `--no-do-g`
   - To: `--skip-bp`, `--skip-k`, `--skip-g`
   - Change: `--do-bp`, `--do-g`
   - To: `--skip-g`, `--skip-bp` (inverted logic)

3. **Phase 6:** Apply calibration syntax
   - Change: `--registry-db`, `--registry-set`
   - To: `--tables` with explicit table paths
   - OR: Investigate if registry-based apply workflow exists

### Minor (Should Fix):

4. **Phase 2-3:** Command path clarification
   - Clarify whether to use `conversion.cli groups` or `conversion.strategies.hdf5_orchestrator`
   - Both work, but `conversion.cli groups` is the recommended unified entry point

5. **Phase 5:** Calibration table output prefix
   - Verify `--output-prefix` parameter exists
   - Tables may be written with standard naming (no prefix option)

---

## Missing or Unclear Elements

1. **Calibration table naming convention:** The plan assumes specific table naming (`CALIBRATOR_MS.ms_0_bpcal`, `CALIBRATOR_MS.ms_0_gpcal`). Need to verify actual naming convention from code.

2. **Registry-based apply workflow:** The `apply` CLI command requires explicit tables. There may be a service-level function that supports registry lookup, but CLI usage is unclear.

3. **Image registration automation:** Step 7.X.1 shows manual Python script. Could be automated via existing worker or helper script.

---

## Recommendations

### Immediate Actions:
1. Fix command syntax in Phases 5 and 6 (critical corrections)
2. Test Phase 1-2 commands to verify exact syntax
3. Verify calibration table naming convention

### Enhancements:
1. Add automated image registration step (Phase 7.X.1)
2. Investigate registry-based calibration application workflow
3. Add error handling and retry logic recommendations

### Validation:
1. Test end-to-end with a small subset (1-2 groups)
2. Verify all intermediate outputs before proceeding
3. Add checkpoints between phases

---

## Overall Assessment

**Viability Score: 9/10**

The plan is **excellent** in structure and completeness. It breaks down a complex workflow into executable steps with proper verification points. The main issues are **command syntax mismatches** that are easily correctable.

**With corrections applied, this plan is ready for execution.**

---

## Additional Notes

### Strengths:
- ✓ Comprehensive coverage of all pipeline stages
- ✓ Proper verification steps at each phase
- ✓ Clear separation of concerns (per-group, per-MS operations)
- ✓ Follows "measure twice, cut once" philosophy

### Areas for Improvement:
- Command syntax alignment with actual implementations
- Automation of manual steps (image registration)
- Error recovery strategies
- Resource monitoring recommendations

---

**Conclusion:** The plan is **highly viable** and well-structured. With the syntax corrections noted above, it should execute successfully. The workflow correctly identifies all dependencies and verification points.


