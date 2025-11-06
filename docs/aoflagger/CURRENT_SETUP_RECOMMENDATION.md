# Current AOFlagger Setup Recommendation

**Date:** 2025-11-05  
**Status:** Wait on optimization, keep current setup with one optional enhancement

---

## Current Status

✅ **AOFlagger is working:**
- Docker integration successful
- Custom DSA-110 Lua strategy tested
- Results reasonable (2.18-2.32% flagged)
- Both generic and custom strategies functional

✅ **Current CASA flagging is working:**
- Two-stage approach (tfcrop + rflag)
- Conservative thresholds (4σ)
- Appropriate for calibrator data

---

## Recommendation: Wait on Full Optimization

**Why wait:**
1. **Need more data:** Optimization requires testing on multiple observations to find patterns
2. **Current setup works:** 2-3% flagging is reasonable, calibration quality is good
3. **Baseline not established:** Need to understand RFI patterns across different:
   - Times of day
   - Seasons/weather
   - Observing conditions
   - Different calibrators

**When to optimize:**
- After processing 20-50 observations
- When you see patterns in RFI that need addressing
- If flagging becomes a bottleneck (currently ~3 minutes is acceptable)
- If calibration quality degrades due to RFI

---

## Simple Enhancement: Flag Extension (Optional)

**One simple improvement worth considering now:**

Add a flag extension step after RFI flagging to grow flags to adjacent channels/times. This is a common practice because RFI often affects neighboring data points.

**Why it helps:**
- RFI often spills into adjacent channels (filter rolloff, cross-talk)
- RFI often affects multiple time samples (transient duration)
- Low risk: only extends flags that are already flagged
- High benefit: catches RFI that's slightly below threshold

**Implementation:**
```python
# After flag_rfi() in calibration pipeline
flag_extend(
    ms,
    flagnearfreq=True,  # Flag channels adjacent to flagged channels
    flagneartime=True,  # Flag times adjacent to flagged times
    extendpols=True    # Extend across polarizations
)
```

**Impact:**
- Typically adds 0.5-1% additional flagging
- Minimal risk of false positives (only extends existing flags)
- Better RFI cleanup

**Decision:**
- **Safe to add now** - low risk, proven practice
- **Or wait** - current setup is working fine

---

## What to Monitor

As you process more observations, track:

1. **Flagging statistics:**
   - Flagging percentage per observation
   - Flags per antenna/polarization
   - Flags per time/frequency

2. **Calibration quality:**
   - Bandpass SNR
   - Solution stability
   - Flagged solution percentage

3. **Image quality:**
   - Noise level
   - Dynamic range
   - Artifacts

4. **Patterns:**
   - Time-of-day RFI patterns
   - Frequency-dependent RFI
   - Site-specific interference

---

## When to Revisit Optimization

Optimize parameters when you see:

1. **Consistent issues:**
   - RFI visible in images after flagging
   - Calibration quality degrading
   - Flagging percentage inconsistent

2. **Performance needs:**
   - Flagging takes >10% of pipeline time
   - Processing many observations becomes slow

3. **Data-driven patterns:**
   - Clear RFI patterns that need different parameters
   - Site-specific interference sources identified

4. **Comparison needs:**
   - Want to match CASA results more closely
   - Want to optimize for specific use case

---

## Summary

**Current recommendation:**
1. ✅ **Keep current setup** - it's working well
2. ⚠️ **Consider flag extension** - simple, low-risk improvement
3. ⏸️ **Wait on optimization** - need more data to make informed decisions
4. 📊 **Monitor statistics** - track flagging patterns as you process more data

**The optimization guide (`PARAMETER_OPTIMIZATION_GUIDE.md`) is ready when you need it, but there's no rush to implement it now.**

