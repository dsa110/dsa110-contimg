# Why We Use fixvis + phaseshift Instead of phaseshift Only

**Date:** 2025-11-04  
**Status:** Technical Explanation  
**Priority:** Documentation

---

## Question

Why aren't we using `phaseshift` instead of `fixvis`? The ops pipeline (`build_central_calibrator_group.py`) uses `phaseshift` first and only falls back to `fixvis` if `phaseshift` fails.

---

## Evidence from Current MS

The current MS (`2025-10-29T13:54:17.ms`) was previously rephased using `phaseshift` only (as per ops pipeline pattern). The result:

```
REFERENCE_DIR: RA=128.571864°, Dec=54.665223°  (OLD - wrong)
PHASE_DIR:     RA=128.728753°, Dec=55.572499°  (NEW - correct, matches calibrator)
Difference:    dRA=9.41 arcmin, dDec=54.44 arcmin
```

**Critical Finding:** `phaseshift` updated `PHASE_DIR` correctly but did NOT update `REFERENCE_DIR`.

---

## Why This Matters

CASA calibration tasks use `REFERENCE_DIR` (not `PHASE_DIR`) for phase center calculations:

- `REFERENCE_DIR` is the authoritative field for CASA's internal phase calculations
- `PHASE_DIR` is informational and may be updated by `phaseshift`
- If `REFERENCE_DIR` is wrong, calibration will fail even if `PHASE_DIR` is correct

**Impact:**
- Phase decorrelation: 100+ deg phase scatter
- Low SNR: 80-90% calibration solutions flagged
- DATA/MODEL misalignment: Amplitude ratio 0.04 (DATA 96% weaker than MODEL)

---

## Why fixvis is Needed

`fixvis` updates `REFERENCE_DIR` (the field CASA actually uses), even though it's deprecated:

- `fixvis` updates both `REFERENCE_DIR` and `PHASE_DIR`
- `phaseshift` updates `PHASE_DIR` but may not reliably update `REFERENCE_DIR`
- The ops pipeline fallback pattern suggests `fixvis` is sometimes necessary

---

## Current Solution: Two-Step Process

### Step 1: fixvis (Updates REFERENCE_DIR)

```python
casa_fixvis(
    vis=args.ms,
    outputvis=ms_intermediate,
    phasecenter=f"J2000 {ra_deg}deg {dec_deg}deg"  # deg format
)
```

**Purpose:** Update `REFERENCE_DIR` so CASA knows the correct phase center.

**Why deprecated `fixvis` is still needed:**
- It's the only reliable way to update `REFERENCE_DIR` in some CASA versions
- `phaseshift` doesn't always update `REFERENCE_DIR` (as evidenced by our MS)

### Step 2: phaseshift (Phase Correction)

```python
casa_phaseshift(
    vis=ms_intermediate,
    outputvis=ms_phased,
    phasecenter=f"J2000 {ra_hms} {dec_dms}"  # hms dms format
)
```

**Purpose:** Apply the actual phase correction to the visibility data.

**Why phaseshift is preferred for phase correction:**
- Modern task (replaces deprecated `fixvis`)
- Better performance and reliability
- Proper phase correction algorithm

---

## Alternative: phaseshift Only (Fallback)

If `fixvis` fails or is unavailable, we fall back to `phaseshift` only:

```python
casa_phaseshift(
    vis=args.ms,
    outputvis=ms_phased,
    phasecenter=phasecenter_str
)
```

**Warning:** This may not update `REFERENCE_DIR`, leading to calibration failures.

---

## Why Ops Pipeline Uses phaseshift First

The ops pipeline (`build_central_calibrator_group.py`) uses `phaseshift` first because:

1. **Different context:** It may be working with MSs that already have correct `REFERENCE_DIR`
2. **Fallback pattern:** If `phaseshift` fails, it falls back to `fixvis`
3. **Version differences:** Behavior may vary across CASA versions

**However:** Our evidence shows that `phaseshift` alone doesn't reliably update `REFERENCE_DIR` in the DSA-110 context.

---

## Recommended Approach

**Use fixvis + phaseshift (two-step):**

1. **fixvis first** to update `REFERENCE_DIR` (what CASA uses)
2. **phaseshift second** for phase correction (modern, reliable)

**Benefits:**
- Guarantees `REFERENCE_DIR` is updated
- Uses modern `phaseshift` for phase correction
- Ensures calibration will work correctly

**Trade-offs:**
- Requires two MS copy operations (slower)
- Uses deprecated `fixvis` (but necessary)
- More complex error handling

---

## Why This Is A Problem

**The user's excellent point:** If `fixvis` is deprecated and CASA recommends `phaseshift`, why would CASA's internal calibration tasks require `REFERENCE_DIR` to be updated (which only `fixvis` seems to do)?

**Possible explanations:**

1. **`phaseshift` SHOULD update `REFERENCE_DIR` but has a bug:**
   - This would be a CASA bug that should be reported
   - The fact that it updates `PHASE_DIR` but not `REFERENCE_DIR` suggests incomplete implementation

2. **We're not using `phaseshift` correctly:**
   - Maybe there's a parameter we're missing
   - Maybe it needs to be run in a specific way
   - The ops pipeline uses it successfully, so maybe context matters

3. **Manual `REFERENCE_DIR` update after `phaseshift`:**
   - We could manually update `REFERENCE_DIR` in the FIELD table after `phaseshift`
   - This would be cleaner than using deprecated `fixvis`
   - Less risky than it seems (just copying `PHASE_DIR` to `REFERENCE_DIR`)

4. **CASA version or context differences:**
   - Maybe newer CASA versions fixed this
   - Maybe it works in ops pipeline context but not ours
   - Maybe MS state affects whether `REFERENCE_DIR` gets updated

## Recommended Investigation

**Better approach:** Try `phaseshift` only, then manually update `REFERENCE_DIR` if needed:

```python
# 1. Use phaseshift (modern, recommended)
casa_phaseshift(
    vis=args.ms,
    outputvis=ms_phased,
    phasecenter=phasecenter_str
)

# 2. Check if REFERENCE_DIR was updated
with table(f"{ms_phased}::FIELD", readonly=False) as tf:
    ref_dir = tf.getcol("REFERENCE_DIR")[0][0]
    phase_dir = tf.getcol("PHASE_DIR")[0][0]
    
    # 3. If not aligned, manually copy PHASE_DIR to REFERENCE_DIR
    if not np.allclose(ref_dir, phase_dir, atol=1e-6):
        print("DEBUG: REFERENCE_DIR not updated by phaseshift, updating manually...")
        tf.putcol("REFERENCE_DIR", phase_dir.reshape(1, 1, 2))
```

This would:
- Use modern `phaseshift` (not deprecated `fixvis`)
- Manually ensure `REFERENCE_DIR` is correct
- Be simpler than two-step fixvis + phaseshift
- Match CASA's recommendation to use `phaseshift`

## Future Improvements

Possible alternatives to investigate:

1. **Manual `REFERENCE_DIR` update after `phaseshift`:**
   - Use `phaseshift` only (modern, recommended)
   - Manually copy `PHASE_DIR` to `REFERENCE_DIR` if needed
   - Cleaner than using deprecated `fixvis`

2. **Check if newer CASA versions' `phaseshift` updates `REFERENCE_DIR`:**
   - Test with CASA 6.5+ to see if behavior changed
   - Update code if `phaseshift` now reliably updates `REFERENCE_DIR`

3. **Report potential CASA bug:**
   - If `phaseshift` is supposed to update `REFERENCE_DIR` but doesn't, this is a bug
   - CASA should fix it since `fixvis` is deprecated

4. **CASA version detection:**
   - Use `phaseshift` + manual update for newer versions
   - Use `fixvis` only for older versions if absolutely necessary

---

## Summary

**Why we use fixvis + phaseshift:**
- `phaseshift` updates `PHASE_DIR` but not `REFERENCE_DIR` (evidence from current MS)
- CASA uses `REFERENCE_DIR` for calibration (critical)
- `fixvis` reliably updates `REFERENCE_DIR` (even though deprecated)
- Two-step process ensures both are correct

**Why not phaseshift only:**
- Risk of `REFERENCE_DIR` not being updated
- Calibration failures due to incorrect phase center
- Evidence shows this happened in our MS

**Current approach is correct:** Use `fixvis` first, then `phaseshift`, to ensure both `REFERENCE_DIR` and phase correction are correct.

