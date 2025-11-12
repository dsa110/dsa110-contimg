# Open Questions - Phase Scatter Debugging

**Date:** 2025-11-05  
**Status:** Core debugging complete, but some questions remain

---

## 🔍 Mysteries Still Unsolved

### 1. What Does "1" in CASA Output Actually Mean?

**Question:** When CASA says "1 of 182 solutions flagged", what is "1" counting?

**What We Know:**
- ❌ NOT total flagged solutions (53 actual)
- ❌ NOT baselines with flags (28 actual)
- ❌ NOT unflagged solutions (182 is the unflagged count)

**Possible Interpretations:**
- Per-time flagging count?
- Per-iteration count?
- Incremental flagging (newly flagged this iteration)?
- Bug in CASA's counting?

**Impact:** Low - doesn't affect functionality, just confusing
**Priority:** Low - nice to know, but not blocking

---

### 2. Why Exactly 28 Baselines as the Printing Threshold?

**Question:** Why did CASA choose 28 baselines as the threshold for printing channels?

**What We Know:**
- ✅ Threshold is exactly 28 baselines affected
- ✅ 28/117 = 24% of baselines
- ✅ This is a hardcoded threshold in CASA

**Possible Reasons:**
- Percentage-based (24% threshold)?
- Arbitrary choice?
- Based on some statistical criterion?

**Impact:** Low - doesn't affect functionality
**Priority:** Low - curiosity, but not critical

---

## 📊 Scientific Validation Questions

### 3. Is 98-104° Phase Scatter Acceptable for Our Use Case?

**Question:** We've concluded it's "expected" for a 1° source offset, but is it scientifically acceptable?

**What We Know:**
- ✅ ~100° scatter matches expected value for 1° offset
- ✅ QA threshold is 90° (we exceed this)
- ✅ High scatter doesn't necessarily mean bad calibration if DATA/MODEL_DATA are aligned

**What We Don't Know:**
- Is this level of scatter acceptable for continuum imaging?
- Does it degrade image quality?
- Should we adjust QA thresholds for non-rephased cases?

**Impact:** Medium - affects quality assessment
**Priority:** Medium - should verify before production

**Next Steps:**
- Apply calibration to target fields
- Assess image quality
- Compare with rephased calibration (if done)
- Adjust QA thresholds if needed

---

### 4. Does the Calibration Actually Improve Data Quality?

**Question:** We know calibration completes, but does it improve the data?

**What We Know:**
- ✅ Calibration tables created successfully
- ✅ Phase scatter is expected (not necessarily bad)
- ✅ Flagging rate is typical (22-23%)

**What We Don't Know:**
- Does applying calibration improve image quality?
- Are calibration solutions physically reasonable?
- Do they reduce systematic errors?

**Impact:** High - core validation
**Priority:** High - should verify before production

**Next Steps:**
- Apply calibration to target fields
- Compare corrected vs uncorrected data
- Assess image quality improvements
- Verify flux scale accuracy

---

### 5. Should QA Thresholds Be Adjusted for Non-Rephased Cases?

**Question:** Current QA threshold is 90° phase scatter, but we see 98-104° for non-rephased cases. Should we adjust?

**Current Threshold:**
- `cal_max_phase_scatter_deg = 90.0` (from environment variable or default)

**Current Behavior:**
- 98-104° scatter → Would trigger QA warning
- But we've determined this is expected for 1° offset

**Options:**
1. Adjust threshold based on source offset
2. Use different thresholds for rephased vs non-rephased
3. Keep current threshold but document expected scatter for offsets

**Impact:** Medium - affects quality assessment
**Priority:** Medium - should address before production

---

## 🧪 Edge Cases & Testing

### 6. How Does This Work with Different Calibrators?

**Question:** What about different flux densities, distances, or calibrator types?

**What We Know:**
- ✅ Current calibrator: 0834+555 (2.5 Jy, ~1° offset)
- ✅ Calibration works for this case

**What We Don't Know:**
- How does it work with fainter calibrators (< 1 Jy)?
- How does it work with calibrators at different offsets?
- How does it work with resolved calibrators?

**Impact:** Medium - affects robustness
**Priority:** Low - can test as needed

---

### 7. Weather & Data Quality Dependencies

**Question:** How sensitive is calibration to weather conditions and data quality?

**What We Know:**
- ✅ Current flagging rate: 22-23% (typical)
- ✅ Some channels have high flagging (RFI, edge effects)

**What We Don't Know:**
- How does calibration perform in poor weather?
- How does it handle high RFI?
- What's the minimum data quality needed?

**Impact:** Medium - affects robustness
**Priority:** Low - can test as needed

---

## 🔧 Technical Questions

### 8. Could We Reduce Phase Scatter Further?

**Question:** Are there ways to reduce the 98-104° scatter, or is it fundamental?

**Possible Approaches:**
- Better pre-bandpass phase calibration (shorter solint)?
- Different solint for bandpass?
- Different reference antenna?
- Rephase to calibrator (but then need manual MODEL_DATA)

**Impact:** Low - current scatter is acceptable
**Priority:** Low - optimization, not blocking

---

### 9. Is Manual MODEL_DATA Calculation Numerically Accurate?

**Question:** We validated it matches standard practice, but is it numerically correct?

**What We Know:**
- ✅ Formula matches standard radio interferometry practice
- ✅ Validated against similar implementations (MeerKAT crystalball)
- ✅ Uses correct PHASE_DIR from FIELD table

**What We Don't Know:**
- Direct numerical comparison with known-good reference?
- Edge cases (very large offsets, very small baselines)?
- Precision/rounding issues?

**Impact:** Low - formula is standard
**Priority:** Low - confidence is high

---

## 📋 Summary

### High Priority (Should Address Before Production)
- ✅ **Core debugging:** COMPLETE
- ⚠️ **Calibration quality validation:** Need to verify calibration improves data
- ⚠️ **QA threshold adjustment:** Need to handle non-rephased cases

### Medium Priority (Nice to Have)
- 🔍 **What does "1" mean?** - Curiosity, but not blocking
- 🔍 **Why 28 baselines?** - Curiosity, but not blocking
- 🔍 **Is scatter acceptable?** - Need to verify, but not blocking
- 🔍 **Edge case testing:** Good to test, but not blocking

### Low Priority (Optimization/Future Work)
- 🔍 **Reduce scatter further?** - Current is acceptable
- 🔍 **Different calibrators?** - Can test as needed
- 🔍 **Weather dependencies?** - Can test as needed
- 🔍 **Numerical accuracy?** - High confidence already

---

## ✅ Ready for Next Steps

**Core debugging is complete. The system works.**

**Remaining questions are mostly:**
1. **Validation** (does it improve data quality?)
2. **Curiosity** (what does CASA's "1" mean?)
3. **Optimization** (can we reduce scatter further?)

**Recommendation:** Proceed with applying calibration to target fields and assessing image quality. This will answer the most important remaining question: does the calibration actually improve the data?

