# Mermaid Diagram Workflow Review Findings

**Date:** 2025-01-15  
**Purpose:** Verify diagram accuracy against actual codebase implementation

## Summary

After thorough code review, several inconsistencies were identified between the
diagrams and actual implementation. This document details findings and
recommended corrections.

---

## Critical Issues Found

### 1. MS Preparation Timing (Stage 3)

**Issue:** Stage 3 (MS Preparation) is shown as a separate stage after
conversion, but it actually happens **during** Stage 2 (Conversion).

**Evidence:**

- `configure_ms_for_imaging()` is called at line 1062 in `hdf5_orchestrator.py`
  immediately after MS creation
- This happens within `convert_subband_groups_to_ms()` function
- MS preparation (MODEL_DATA, CORRECTED_DATA, WEIGHT_SPECTRUM initialization) is
  part of the conversion process

**Current Diagram Flow:**

```
Stage 2: Conversion → MS
Stage 3: MS Preparation (Validate → Config → Flag)
```

**Actual Flow:**

```
Stage 2: Conversion → (includes MS configuration) → MS ready for calibration
```

**Recommendation:**

- Merge Stage 3 into Stage 2 as a sub-process
- Show MS configuration happening during conversion finalization
- Keep RFI flagging separate (happens before calibration)

---

### 2. RFI Flagging Location

**Issue:** RFI flagging is shown in Stage 3 (MS Preparation), but it actually
happens **before calibration** as part of the calibration workflow.

**Evidence:**

- `cli_calibrate.py` line 1329-1338: Flagging happens at "[2/6]" step, before
  model population
- Flagging is part of calibration CLI workflow, not conversion
- In streaming mode, flagging may not happen explicitly (calibration applied
  from registry)

**Current Diagram Flow:**

```
Stage 3: MS Preparation → Flag (RFI Flagging)
Stage 4: Calibration
```

**Actual Flow:**

```
Stage 2: Conversion → MS (configured)
Stage 4: Calibration → Flag (pre-calibration) → Model → Solve
```

**Recommendation:**

- Move RFI flagging to Stage 4 (Calibration) as a pre-calibration step
- Show it as optional (depends on calibration mode)
- Note that streaming mode may skip explicit flagging if using existing
  caltables

---

### 3. Writer Selection Threshold

**Issue:** Diagram shows ">2 subbands" vs "<=2 subbands" threshold, but code
uses "<=2" for pyuvdata.

**Evidence:**

- `hdf5_orchestrator.py` line 821: `if n_sb and n_sb <= 2:` selects pyuvdata
- Line 829: Otherwise selects "parallel-subband"
- Threshold is correct: <=2 for testing, >2 for production

**Current Diagram:** ✓ Correct

- Shows ">2 subbands" → parallel-subband
- Shows "<=2 subbands" → pyuvdata

**Status:** No change needed

---

### 4. Calibration Flow - K-Calibration Skip

**Issue:** Diagram correctly shows K-Calibration skipped by default, but the
flow could be clearer.

**Evidence:**

- `cli_calibrate.py`: K-calibration only runs if `--do-k` flag is provided
- Default behavior: Skip K → BP → G
- With `--do-k`: K → BP → G

**Current Diagram:** ✓ Mostly correct

- Shows K-Calibration with "--do-k" branch
- Shows Skip K-Cal as default

**Recommendation:**

- Make the default path more prominent
- Add note that K-cal is skipped for DSA-110 short baselines

---

### 5. Apply Calibration Stage Separation

**Issue:** Stage 5 (Apply Calibration) is shown separately, but in some
workflows it's integrated into calibration.

**Evidence:**

- `cli_calibrate.py`: Calibration solve and apply are separate steps
- `streaming_converter.py`: Apply happens after conversion (line 684)
- Some workflows apply immediately after solving

**Current Diagram:** ✓ Correct

- Shows calibration solve (Stage 4) → apply (Stage 5) → imaging (Stage 6)

**Status:** No change needed, but could add note about integrated workflows

---

## Minor Issues

### 6. State Machine Diagram

**Issue:** State transitions look correct, but could verify against actual state
machine implementation.

**Evidence:**

- `streaming_converter.py`: States match diagram
- `collecting` → `pending` → `in_progress` → `processing_fresh`/`resuming` →
  `completed`/`failed`

**Status:** ✓ Correct

---

### 7. Database Interactions

**Issue:** Diagram shows correct database flow, but timing could be clearer.

**Evidence:**

- Queue DB updated during ingest
- Products DB updated after conversion (line 650-662 in streaming_converter.py)
- Cal registry updated after calibration solve

**Status:** ✓ Correct

---

## Recommended Diagram Corrections

### Main End-to-End Flow

1. **Merge Stage 3 into Stage 2:**
   - Show MS configuration as part of conversion finalization
   - Remove separate "Stage 3: MS Preparation" box
   - Keep validation/configuration steps but within Stage 2

2. **Move RFI Flagging to Stage 4:**
   - Show flagging as pre-calibration step
   - Make it optional (depends on calibration mode)
   - Note: May be skipped in streaming mode when using existing caltables

3. **Clarify Calibration Flow:**
   - Make default path (skip K) more prominent
   - Show K-calibration as optional branch
   - Add note about DSA-110 short baseline rationale

### Detailed Stage Breakdowns

1. **Stage 2 Detail:**
   - Add MS configuration step after concat
   - Show: Concat → Configure MS → Validate → Ready MS

2. **Stage 4 Detail:**
   - Add pre-calibration flagging step
   - Show: MS → Flag (optional) → Check Calibrator → Solve

---

## Verification Checklist

- [x] Writer selection logic matches code
- [x] State machine transitions match implementation
- [x] Database interactions are accurate
- [ ] MS preparation timing corrected
- [ ] RFI flagging location corrected
- [ ] Calibration flow clarified

---

## Next Steps

1. Update main end-to-end flow diagram
2. Update Stage 2 detail diagram
3. Update Stage 4 detail diagram
4. Add notes about workflow variations (streaming vs batch)
5. Verify all diagrams render correctly after changes
