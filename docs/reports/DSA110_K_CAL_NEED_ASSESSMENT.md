# DSA-110 Specific Reasons NOT to Skip K-Calibration

**Investigated via Perplexity: 2025-11-02**

## Summary

**No DSA-110-specific reasons found to skip K-calibration.** The available literature indicates DSA-110 requires standard calibration procedures, including delay calibration, for continuum imaging.

## Investigation Results

### 1. **Correlator Automatic Delay Correction**

**Question:** Does DSA-110 correlator automatically correct delays in real-time?

**Answer:** **No information found** in available literature about:
- Real-time delay correction in DSA-110 correlator
- Automatic delay calibration during correlation
- Pre-calibrated delays in the correlator

**Implication:** Cannot assume delays are corrected automatically - standard offline K-calibration likely still needed.

### 2. **Special DSA-110 Characteristics**

**Question:** Does DSA-110 have special characteristics (common LO, synchronized clocks, etc.) that exempt it from delay calibration?

**Answer:** **No exemptions found.** Instead, DSA-110 documentation shows:

**Standard Calibration Requirements:**
- **Phase calibrator observations** before every observing session (3C48, 3C286, or 3C147)[5]
- **Bandpass calibration** using reference sources (e.g., 3C309.1)[2]
- **Complex gain calibration** derived at time of observation[2]
- **Astrometric calibration** using RFC calibrators and VLBI localizations[1]

**Finding:** DSA-110 follows standard radio interferometry calibration practices, not exemptions.

### 3. **Continuum Imaging Specific Considerations**

**Question:** Are there continuum imaging cases where delay calibration isn't needed?

**Answer:** **Delay calibration is important for continuum imaging.** However:

- If **very high dynamic range is not the aim**, calibration may be more straightforward but **still necessary**[1]
- Delay calibration is required when **averaging frequencies into continuum images** to avoid decorrelation[1]

**Key Point:** The literature suggests delay calibration is standard practice even for continuum observations, though the strictness may depend on dynamic range requirements.

## DSA-110 Calibration Evidence

From DSA-110 publications:

1. **FRB 20220319D observations**[2]:
   - Bandpass calibration performed using 3C309.1
   - Complex gain calibration derived at observation time
   - Standard calibration pipeline applied

2. **NSFRB Galactic Plane Survey**[1]:
   - Astrometric calibration using RFC calibrators
   - Alignment solutions to correct for deviations
   - Multiple calibration steps required

3. **Observing Procedures**[5]:
   - Phase calibrators observed before every session
   - Used to assess sensitivity and calibrate instrument
   - Standard interferometry practice

## Conclusion

**No DSA-110-specific reasons found to skip K-calibration:**

1. ✗ **No evidence** of automatic delay correction in correlator
2. ✗ **No exemptions** found - DSA-110 follows standard calibration practices
3. ✗ **No special characteristics** (common LO, synchronized clocks) documented
4. ✓ **Evidence** that DSA-110 requires standard calibration procedures

## Recommendation

**Perform K-calibration for DSA-110 continuum imaging** because:

1. Standard practice: DSA-110 documentation shows it follows standard interferometry calibration
2. Continuum decorrelation: Delay calibration prevents decorrelation when averaging frequencies
3. No exemptions documented: No special characteristics found that would eliminate the need
4. Dynamic range: Even if high dynamic range isn't the goal, delay calibration is still beneficial

## Limitations

- Limited technical documentation available about DSA-110 correlator architecture
- DSA-10 prototype mentioned "variable coarse delay correction" but not DSA-110
- Specific correlator design details not found in available literature

**Recommendation:** Consult DSA-110 technical documentation or correlator design papers for definitive answer about real-time delay correction capabilities.

## References

[1] DSA-110 NSFRB Galactic Plane Survey (arXiv:2510.18136v1)
[2] FRB 20220319D observations with DSA-110 (arXiv:2301.01000)
[3] DSA-110 Instrument Overview (deepsynoptic.org)
[4] DSA-10 Prototype Array (MNRAS 489, 919)
[5] DSA-110 observing procedures (MNRAS 527, 10425)
[6] NRAO VLA Observing Guide - Calibration

**Investigation Date:** 2025-11-02  
**Method:** Perplexity reasoning model with literature search

