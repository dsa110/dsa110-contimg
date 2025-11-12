# Investigation Plan: 100.1° Phase Scatter in Bandpass Calibration

**Date:** 2025-11-05  
**Status:** Investigation Plan  
**Goal:** Determine root cause of 100.1° phase scatter in bandpass solutions without running pipeline commands

---

## Investigation Strategy

### Phase 1: Understand What Phase Scatter Means

**1.1 Define Phase Scatter Metric**
- [ ] Review `validate_caltable_quality()` in `src/dsa110_contimg/qa/calibration_quality.py`
- [ ] Confirm: Phase scatter = `std(phases_deg)` after wrapping to [-180, 180)
- [ ] Understand: Does this measure scatter across antennas, channels, time, or all?
- [ ] Question: Is 100.1° the RMS scatter or standard deviation?
- [ ] Expected: Typical bandpass phase scatter should be < 30° for good data

**1.2 Research Expected Values**
- [ ] Search literature for typical bandpass phase scatter values
- [ ] Understand: What causes phase scatter in bandpass?
  - Frequency-dependent phase variations (normal)
  - Residual time-dependent phase errors (problematic)
  - Antenna-to-antenna variations (normal)
  - Channel-to-channel variations (normal)
- [ ] Question: Is 100.1° scatter across channels (expected) or across antennas/time (problematic)?

**1.3 Examine Phase Scatter Calculation**
- [ ] Read `src/dsa110_contimg/qa/calibration_quality.py` lines 259-265
- [ ] Verify: How are phases extracted from calibration table?
- [ ] Verify: Are phases wrapped correctly before computing std?
- [ ] Check: Does calculation include flagged solutions?
- [ ] Question: Is scatter computed per-channel, per-antenna, or globally?

---

### Phase 2: Trace the Calibration Chain

**2.1 Verify Pre-Bandpass Phase Calibration**

**Examine `solve_prebandpass_phase()`:**
- [ ] Read `src/dsa110_contimg/calibration/calibration.py` lines 413-564
- [ ] Understand: What does this step correct?
  - Expected: Time-dependent phase drifts (atmospheric, instrumental)
  - Expected: NOT frequency-dependent (that's bandpass)
- [ ] Verify: Is `combine='spw'` correctly combining all 16 SPWs?
- [ ] Check: Solution interval (`solint='30s'`) - is this appropriate?
- [ ] Question: Does combining SPWs create a phase solution that's frequency-independent?

**Verify Pre-Bandpass Phase Table Structure:**
- [ ] Document: How many solutions per antenna?
- [ ] Document: How many solutions per SPW? (Should be 1 if combined)
- [ ] Document: Time sampling of solutions
- [ ] Check: Are solutions phase-only (`calmode='p'`)?
- [ ] Verify: Are solutions averaged across frequency when `combine='spw'`?

**2.2 Verify Pre-Bandpass Phase Application**

**Examine `solve_bandpass()` pre-calibration application:**
- [ ] Read `src/dsa110_contimg/calibration/calibration.py` lines 738-753
- [ ] Verify: Is `spwmap` correctly set? (We added this fix)
- [ ] Verify: Is `interp=['linear']` appropriate for phase-only calibration?
- [ ] Check: Does CASA apply pre-bandpass phase BEFORE computing bandpass?
- [ ] Question: Does combining SPWs in pre-bandpass phase mean the solution is frequency-independent?

**Critical Question:**
- [ ] When `combine='spw'` is used for pre-bandpass phase, does CASA:
  - Average phase across all frequencies → single phase per antenna per time?
  - OR: Solve phase per frequency → then combine solutions?
- [ ] If averaged: Phase solution is frequency-independent (correct for phase-only)
- [ ] If per-frequency: Phase solution varies with frequency (may not be appropriate)

**2.3 Understand Bandpass Phase Structure**

**What Should Bandpass Phase Look Like?**
- [ ] Research: Bandpass phase should vary WITH frequency (it's frequency-dependent)
- [ ] Understand: Pre-bandpass phase should remove time-dependent phase (constant across frequency)
- [ ] Expected: After pre-bandpass phase correction, bandpass phase should show:
  - Smooth variation across frequency (bandpass shape)
  - Minimal variation across time (should be corrected)
  - Antenna-to-antenna variations (normal)
- [ ] Question: Does combining SPWs in bandpass solve create frequency-averaged phase?

---

### Phase 3: Investigate MODEL_DATA Phase Structure

**3.1 Verify MODEL_DATA Quality**

**Examine MODEL_DATA Population:**
- [ ] Read `src/dsa110_contimg/calibration/model.py`
- [ ] Check: Is MODEL_DATA populated using `ft()` or manual calculation?
- [ ] Verify: Does MODEL_DATA use correct phase center (`PHASE_DIR` vs `REFERENCE_DIR`)?
- [ ] Check: Are phase calculations correct? (cos(Dec) factor for RA offsets)

**Check Known Issues:**
- [ ] Review `docs/reports/MODEL_DATA_PHASE_STRUCTURE_ISSUE.md`
- [ ] Verify: Was MODEL_DATA phase structure issue fixed?
- [ ] Check: Does MODEL_DATA have correct phase structure for point source at phase center?
- [ ] Expected: MODEL_DATA phase scatter should be < 10° for point source at phase center

**3.2 Verify Phase Center Alignment**

**Examine MS Phase Center:**
- [ ] Review: MS was rephased to calibrator position
- [ ] Verify: `REFERENCE_DIR` matches calibrator position
- [ ] Verify: `PHASE_DIR` matches calibrator position after rephasing
- [ ] Check: Is MODEL_DATA calculated using correct phase center?

---

### Phase 4: Analyze Calibration Solve Process

**4.1 Understand Bandpass Solve with combine='spw'**

**Research combine='spw' Behavior:**
- [ ] Review CASA documentation: How does `combine='spw'` work in bandpass?
- [ ] Understand: Does combining SPWs average phase across frequency?
- [ ] Critical: When combining SPWs, what happens to frequency-dependent phase?
- [ ] Question: Can bandpass phase be averaged across SPWs if it's frequency-dependent?

**From CASA Documentation:**
> "When using combine='spw' in bandpass, all selected spws will effectively be averaged together to derive a single bandpass solution. The channel frequencies assigned to the solution will be a channel-by-channel average over spws of the input channel frequencies."

**Implications:**
- [ ] If SPWs have different frequencies, averaging creates intermediate frequencies
- [ ] Question: Does this averaging preserve frequency-dependent phase structure?
- [ ] Question: Or does averaging destroy frequency-dependent information?

**4.2 Verify Bandpass Solve Parameters**

**Examine `solve_bandpass()` call:**
- [ ] Read `src/dsa110_contimg/calibration/calibration.py` lines 723-754
- [ ] Verify: `solint='inf'` - correct for bandpass (per-channel solution)
- [ ] Verify: `bandtype='B'` - correct (per-channel, not polynomial)
- [ ] Verify: `combine='scan,field,spw'` - is combining SPWs appropriate?
- [ ] Check: Does combining SPWs reduce phase scatter or increase it?

**Critical Question:**
- [ ] When `combine='spw'` is used, does CASA:
  - Average phase across frequencies → single phase per channel (averaged frequency)?
  - OR: Solve phase per frequency → combine solutions somehow?
- [ ] If averaged: Phase scatter should be LOW (frequency-averaged)
- [ ] If per-frequency: Phase scatter should reflect frequency variations

**4.3 Check Solution Quality Metrics**

**Examine Calibration Table Structure:**
- [ ] Document: How many solutions in bandpass table?
- [ ] Document: How many SPWs in bandpass table? (Should be 1 if combined)
- [ ] Document: How many channels per solution?
- [ ] Check: Are solutions per-channel (bandtype='B') or frequency-averaged?

---

### Phase 5: Hypothesis Testing

**Hypothesis 1: Pre-Bandpass Phase Not Applied Correctly**
- [ ] Evidence: Warning about missing SPWs 1-15 (before spwmap fix)
- [ ] Test: Verify spwmap is now being set correctly (debug output shows this)
- [ ] Check: Does CASA actually apply pre-bandpass phase to all SPWs with spwmap?
- [ ] Verify: Is `interp=['linear']` correct for phase-only calibration?
- [ ] Expected: If fixed, phase scatter should reduce significantly

**Hypothesis 2: MODEL_DATA Has Incorrect Phase Structure**
- [ ] Evidence: Previous reports of MODEL_DATA phase scatter ~100°
- [ ] Test: Check if MODEL_DATA phase scatter issue was fixed
- [ ] Verify: Does MODEL_DATA use correct phase center?
- [ ] Check: Are phase calculations correct?
- [ ] Expected: If MODEL_DATA phase is wrong, bandpass solve will have wrong reference

**Hypothesis 3: Combining SPWs Destroys Frequency-Dependent Phase**
- [ ] Evidence: Phase scatter is large despite combining SPWs
- [ ] Test: Understand if combining SPWs averages phase across frequency
- [ ] Check: Does averaging phase destroy frequency-dependent information?
- [ ] Question: Should bandpass phase be frequency-dependent or averaged?
- [ ] Expected: If combining SPWs averages phase, scatter should be LOW (not high)

**Hypothesis 4: Data Quality Issues**
- [ ] Evidence: 44.2% flagged solutions, many antennas fully flagged
- [ ] Test: Is phase scatter computed only on unflagged solutions?
- [ ] Check: Are flagged solutions excluded from phase scatter calculation?
- [ ] Verify: Does flagging remove bad solutions or good solutions?
- [ ] Expected: If only good solutions remain, scatter should reflect true quality

**Hypothesis 5: Pre-Bandpass Phase Solve Quality**
- [ ] Evidence: Pre-bandpass phase solve also flagged many solutions
- [ ] Test: Check pre-bandpass phase solution quality
- [ ] Verify: Are pre-bandpass phase solutions correct?
- [ ] Check: Does combining SPWs create frequency-independent phase?
- [ ] Question: If pre-bandpass phase is wrong, bandpass will be wrong

---

### Phase 6: Expected vs. Actual Behavior

**6.1 Expected Phase Scatter Sources**

**Normal Sources (Expected):**
- Frequency-dependent bandpass phase (varies across channels) - EXPECTED
- Antenna-to-antenna variations (different bandpass shapes) - EXPECTED
- Small residual time-dependent phase (not fully corrected) - EXPECTED but should be small

**Problematic Sources (Not Expected):**
- Large time-dependent phase variations (pre-bandpass phase not applied) - PROBLEM
- Incorrect MODEL_DATA phase structure (wrong reference) - PROBLEM
- Poor SNR leading to noisy solutions (data quality) - PROBLEM
- Systematic phase errors (instrumental) - PROBLEM

**6.2 Calculate Expected Phase Scatter**

**For Frequency-Dependent Phase (Normal):**
- [ ] Calculate: Expected phase variation across 175 MHz bandwidth (1.3114 - 1.4872 GHz)
- [ ] For typical bandpass: Phase may vary by 10-30° across bandwidth
- [ ] If combining SPWs averages phase: Scatter should be LOW
- [ ] If NOT combining: Scatter reflects frequency variations

**For Time-Dependent Phase (Problematic):**
- [ ] Calculate: Expected phase drift over 5 minutes if uncorrected
- [ ] Atmospheric phase: Typically 5-20° over 5 minutes (depends on baseline)
- [ ] If pre-bandpass phase NOT applied: Scatter should match atmospheric drift
- [ ] If pre-bandpass phase applied correctly: Scatter should be << atmospheric drift

**6.3 Compare to Observed**

**Observed: 100.1° phase scatter**
- [ ] Is this scatter across channels? (Expected if frequency-dependent)
- [ ] Is this scatter across antennas? (Expected if antenna variations)
- [ ] Is this scatter across time? (Problematic if pre-bandpass phase applied)
- [ ] Is this scatter across SPWs? (Problematic if combining SPWs)

---

### Phase 7: Code Review for Logical Errors

**7.1 Review Pre-Bandpass Phase Solve**

**Check Logic:**
- [ ] Verify: Does `combine='spw'` create frequency-averaged phase?
- [ ] Check: Is phase solution frequency-independent after combining?
- [ ] Verify: Does `solint='30s'` capture time-dependent phase correctly?
- [ ] Question: Is 30s too short (noisy) or too long (misses variations)?

**7.2 Review Bandpass Solve**

**Check Logic:**
- [ ] Verify: Does `combine='spw'` average phase across frequencies?
- [ ] Check: If phase is averaged, does it preserve frequency-dependent structure?
- [ ] Verify: Is `solint='inf'` correct for per-channel bandpass?
- [ ] Question: Should bandpass phase be frequency-dependent or averaged?

**7.3 Review spwmap Application**

**Check Logic:**
- [ ] Verify: Does `spwmap=[0]*16` correctly map all SPWs to SPW 0?
- [ ] Check: Does `interp=['linear']` correctly interpolate phase-only calibration?
- [ ] Verify: Does CASA apply pre-bandpass phase BEFORE computing bandpass?
- [ ] Question: Is linear interpolation appropriate for frequency-independent phase?

---

### Phase 8: Cross-Reference with Documentation

**8.1 CASA Best Practices**

**Review CASA Documentation:**
- [ ] Confirm: What is typical phase scatter for bandpass solutions?
- [ ] Verify: Should pre-bandpass phase be frequency-independent?
- [ ] Check: Is combining SPWs appropriate for pre-bandpass phase?
- [ ] Verify: Is combining SPWs appropriate for bandpass?

**8.2 Radio Astronomy Literature**

**Research:**
- [ ] Find: Typical bandpass phase scatter values from literature
- [ ] Understand: What causes large phase scatter in bandpass?
- [ ] Verify: Expected phase scatter for DSA-110 array configuration
- [ ] Check: Are there known issues with combining SPWs for phase calibration?

---

### Phase 9: Synthesize Findings

**9.1 Identify Root Cause**

**Based on investigation:**
- [ ] Determine: Is phase scatter from frequency-dependent phase (normal)?
- [ ] Determine: Is phase scatter from time-dependent phase (problematic)?
- [ ] Determine: Is phase scatter from incorrect pre-calibration (problematic)?
- [ ] Determine: Is phase scatter from MODEL_DATA issues (problematic)?

**9.2 Formulate Answer**

**Answer the question:**
> "Why is there such large phase scatter?"

**Possible Answers:**
1. **Normal frequency-dependent phase variation** - Bandpass phase varies with frequency, and scatter reflects this (expected behavior)
2. **Pre-bandpass phase not applied correctly** - Despite spwmap fix, phase drifts not corrected
3. **MODEL_DATA phase structure error** - Incorrect phase reference causes systematic errors
4. **Data quality issues** - Poor SNR, flagging, or instrumental problems
5. **Inappropriate SPW combination** - Combining SPWs averages phase incorrectly

**9.3 Verify Answer**

**Test each hypothesis:**
- [ ] Can we verify frequency-dependent phase is the cause?
- [ ] Can we verify pre-bandpass phase is applied correctly?
- [ ] Can we verify MODEL_DATA phase structure is correct?
- [ ] Can we verify data quality is sufficient?
- [ ] Can we verify SPW combination is appropriate?

---

## Key Questions to Answer

1. **What does "phase scatter" measure?**
   - Scatter across what dimension? (channels, antennas, time, SPWs)
   - Is 100.1° scatter normal or problematic?

2. **What should bandpass phase scatter be?**
   - Expected values from literature
   - Expected values for frequency-dependent phase
   - Expected values after proper calibration

3. **Is pre-bandpass phase applied correctly?**
   - Does spwmap work correctly?
   - Is interp=['linear'] appropriate?
   - Does CASA apply phase correction before bandpass solve?

4. **Does combining SPWs affect phase scatter?**
   - Does combine='spw' average phase across frequency?
   - Should bandpass phase be frequency-dependent or averaged?
   - Does averaging destroy frequency-dependent information?

5. **Is MODEL_DATA phase structure correct?**
   - Was MODEL_DATA phase structure issue fixed?
   - Does MODEL_DATA use correct phase center?
   - Are phase calculations correct?

---

## Expected Outcomes

After completing this investigation, we should be able to answer:

1. ✅ **Is 100.1° phase scatter normal or problematic?**
2. ✅ **What is the root cause of the scatter?**
3. ✅ **Is the scatter from frequency-dependent phase (expected) or time-dependent errors (problematic)?**
4. ✅ **Are there code/logic errors causing the scatter?**
5. ✅ **What fixes, if any, are needed?**

---

## Investigation Order

1. **Start with Phase 1** - Understand what phase scatter means
2. **Then Phase 2** - Trace the calibration chain
3. **Then Phase 3** - Verify MODEL_DATA quality
4. **Then Phase 4** - Analyze calibration solve process
5. **Then Phase 5** - Test hypotheses systematically
6. **Then Phase 6** - Compare expected vs. actual
7. **Then Phase 7** - Review code for logical errors
8. **Then Phase 8** - Cross-reference with documentation
9. **Finally Phase 9** - Synthesize findings

---

## Notes

- This investigation focuses on **code examination** and **critical thinking**
- No pipeline commands required - only code reading and analysis
- Use web search to understand CASA behavior and expected values
- Use codebase search to find relevant implementations
- Document findings as we go

