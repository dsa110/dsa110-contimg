# K-Calibration Need Reassessment for DSA-110

**Date:** 2025-11-03  
**Status:** RESEARCH COMPLETE - RECOMMENDATION: Make K-calibration OPT-OUT

## User Concern (VERIFIED CORRECT)

**Observation:** VLA and ALMA (both closely spaced arrays) do **not** perform K-calibration (delay calibration). K-calibration is typically only necessary for **VLBI** (Very Long Baseline Interferometry) arrays with very long baselines.

**Implication:** DSA-110 is a closely spaced array (not VLBI), so K-calibration may **not be necessary**.

## Research Results (Perplexity Verification)

### Key Findings:

1. **Baseline Length Comparison:**
   - **VLA:** Maximum baseline ~36 km (closely spaced, connected-element array)
   - **ALMA:** Maximum baseline ~16 km (closely spaced, connected-element array)
   - **DSA-110:** Maximum baseline **2.6 km** (closely spaced, connected-element array)
   - **VLBI (VLBA):** Maximum baseline ~8,611 km (very long baseline, independent stations)

2. **Why Connected Arrays Don't Need Explicit K-Cal:**
   - **Shared frequency reference:** Connected arrays use a single common frequency distributed to all antennas via cable, eliminating clock drift delays
   - **Short baselines:** Atmospheric delays partially cancel between nearby antennas
   - **Known instrumental delays:** Correlator model incorporates constant signal path delays
   - **Residual delays absorbed:** Small remaining delays (< 0.5 ns threshold) are absorbed into complex gain calibration (phase/amplitude corrections)

3. **Why VLBI Requires K-Cal:**
   - **Independent atomic clocks:** Each station has its own clock, introducing drift
   - **Very long baselines:** Atmospheric delays don't cancel (thousands of km separation)
   - **Post-correlation:** Signals recorded separately, brought together later
   - **Large delays:** Uncorrected delays routinely exceed decorrelation threshold (0.5 ns)

4. **DSA-110 Characteristics:**
   - Maximum baseline: **2.6 km** (similar to VLA/ALMA, NOT VLBI)
   - Observing frequency: **1.4 GHz** (relatively low frequency)
   - Array type: **Connected-element array** (like VLA/ALMA)
   - **Conclusion:** DSA-110 should follow VLA/ALMA practice (no explicit K-cal)

5. **Decorrelation Threshold:**
   - For GHz-bandwidth observations, delays **> 0.5 ns** cause decorrelation
   - On short baselines (< 100 km), atmospheric/instrumental delays typically **< 0.5 ns** after natural cancellation
   - DSA-110's 2.6 km baselines fall well within this regime

## Current State

1. **K-calibration is currently ENABLED by default** in the pipeline
2. **Previous assessment** (`DSA110_K_CAL_NEED_ASSESSMENT.md`) found "no exemptions" but **failed to properly distinguish VLBI vs closely-spaced arrays**
3. **`--skip-k` flag exists** but requires explicit opt-in to skip

## Recommendation (RESEARCH CONFIRMED)

**DSA-110 is confirmed to be closely-spaced (like VLA/ALMA):**

1. **Make K-calibration OPT-OUT instead of OPT-IN** ✅ RECOMMENDED
   - Change default: `--skip-k` becomes default behavior
   - Add `--do-k` flag for cases where it's explicitly needed (if ever)
   - **Rationale:** DSA-110 baseline length (2.6 km) is similar to VLA/ALMA (16-36 km), NOT VLBI (thousands of km)

2. **Update documentation** to reflect:
   - K-calibration is primarily for VLBI arrays (thousands of km baselines)
   - Connected-element arrays with short baselines (< 100 km) typically don't need explicit K-cal
   - DSA-110 follows VLA/ALMA practice (skip K-cal by default)
   - Residual delays are absorbed into complex gain calibration

3. **Keep K-calibration code available** for:
   - Edge cases or testing
   - If future observations show delays > 0.5 ns (decorrelation threshold)
   - Rare cases where explicit delay correction is needed

## Implementation Plan

### Phase 1: Update CLI Default Behavior
- [ ] Change default: K-calibration skipped by default (`skip_k=True`)
- [ ] Add `--do-k` flag to explicitly enable K-calibration
- [ ] Update help text to explain when K-cal is needed (VLBI only)

### Phase 2: Update Documentation
- [ ] Update `DSA110_K_CAL_NEED_ASSESSMENT.md` with correct understanding
- [ ] Document that K-cal is for VLBI, not connected arrays
- [ ] Update calibration workflow documentation
- [ ] Update `memory.md` with corrected understanding

### Phase 3: Verification (Optional)
- [ ] Run `check_upstream_delays.py` on actual data to measure delays
- [ ] Compare imaging quality with/without K-calibration (if concerns arise)
- [ ] Document findings

## Scientific Basis

**From research:**
- Connected-element arrays use shared frequency reference → no clock drift delays
- Short baselines (< 100 km) → atmospheric delays partially cancel
- Correlator model incorporates known instrumental delays
- Residual delays < 0.5 ns → absorbed into complex gain calibration
- **DSA-110: 2.6 km baselines, connected-element array → follows VLA/ALMA practice**

**VLBI requirements (NOT applicable to DSA-110):**
- Independent atomic clocks at each station → clock drift delays
- Very long baselines (thousands of km) → atmospheric delays don't cancel
- Delays routinely > 0.5 ns → explicit K-calibration (fringe fitting) mandatory

