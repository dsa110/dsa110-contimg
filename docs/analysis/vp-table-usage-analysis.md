# VP Table Usage Analysis

## Current State

**We are NOT using the VP table for calibrator matching PB calculations.**

### What We're Currently Using

The calibrator matching code (`src/dsa110_contimg/calibration/catalogs.py`) uses `airy_primary_beam_response()`, which is a **simple Airy pattern approximation**:

```python
def airy_primary_beam_response(
    ant_ra: float, ant_dec: float, src_ra: float, src_dec: float, 
    freq_GHz: float, dish_dia_m: float = 4.7
) -> float:
    """Approximate primary beam response using an Airy pattern."""
    # Uses formula: (2 * J1(x) / x)^2 where x = π * D * sin(θ) / λ
    # Assumes circular aperture with diameter D = 4.7m
```

**Limitations:**
- Assumes perfect circular aperture (Airy pattern)
- Single frequency (1.4 GHz hardcoded)
- No polarization dependence
- No frequency-dependent beam shape
- No off-axis beam distortion
- No actual measured beam model

### What We Have Available

1. **VP Table**: `/stage/dsa110-contimg/dsa110-beam/dsa110_vp.tbl`
   - Built from actual DSA-110 H5 beam model
   - Contains complex E-field patterns (Jones matrices)
   - Frequency-dependent (though VP table typically uses single frequency slice)
   - Polarization-dependent (XX, XY, YX, YY)
   - Used by CASA imaging tasks (`tclean`, `wsclean` with `--vptable`)

2. **VP Table Infrastructure**:
   - `src/dsa110_contimg/beam/vp_builder.py` - Builds VP tables from H5
   - `src/dsa110_contimg/imaging/cli_imaging.py` - Uses VP tables for imaging
   - VP tables are registered with CASA's `vpmanager` for imaging tasks

### Why We're Not Using VP Table

**CASA's `vpmanager` is designed for imaging tasks, not direct PB evaluation:**

- `vpmanager` doesn't expose a `getpbresponse(ra, dec, freq)` API
- VP tables are complex images (Jones matrices) that CASA uses internally during imaging
- To evaluate PB response from a VP table, we would need to:
  1. Load the VP table image
  2. Convert source coordinates to antenna frame (AZ/EL)
  3. Interpolate the Jones matrix at that position
  4. Calculate power response from Jones matrix
  5. Handle frequency interpolation if needed

This is **significantly more complex** than the current Airy approximation.

### Should We Use VP Table?

**YES, but with caveats:**

#### Advantages:
1. **More Accurate**: Uses actual measured DSA-110 beam model, not theoretical Airy pattern
2. **Polarization-Aware**: Can account for polarization-dependent beam response
3. **Frequency-Dependent**: Can handle different frequencies (though VP table is typically single-frequency)
4. **Off-Axis Accuracy**: Better handles off-axis beam distortion

#### Disadvantages:
1. **Complexity**: Requires coordinate transformations (ICRS → AZ/EL)
2. **Performance**: Image interpolation is slower than analytical formula
3. **Frequency Limitation**: VP table is typically built for one frequency (1.4 GHz)
4. **API Limitation**: CASA doesn't provide direct PB evaluation API

### Recommended Approach

**Option 1: Use H5 Beam Model Directly (Best Accuracy)**
- Load H5 beam model directly (not via VP table)
- Interpolate Jones matrices at source positions
- More accurate than VP table (full frequency coverage)
- More complex to implement

**Option 2: Use VP Table Image (Good Accuracy)**
- Load VP table as CASA image
- Convert source coordinates to AZ/EL frame
- Interpolate Jones matrix from image
- Calculate power response
- Moderate complexity

**Option 3: Enhanced Airy Approximation (Quick Fix)**
- Keep Airy approximation but:
  - Use actual dish diameter (4.65m, not 4.7m)
  - Add frequency dependence
  - Add empirical corrections from beam measurements
- Simplest to implement
- Less accurate but may be sufficient for calibrator matching

**Option 4: Hybrid Approach (Recommended)**
- Use Airy approximation for **fast** calibrator matching (current)
- Use VP table/H5 model for **accurate** PB correction during imaging
- Add flag/option to use accurate PB for critical calibrator selection

### Current Impact

For **calibrator matching** (finding candidates), the Airy approximation is probably **sufficient**:
- We're looking for sources within ~1.5° radius
- Airy pattern is reasonably accurate within ~1° of boresight
- Speed is important for catalog searches
- Exact PB response isn't critical for matching (just ranking)

For **imaging and calibration**, we **should** use the VP table:
- PB correction accuracy matters for science
- VP table is already integrated into imaging pipeline
- This is where accuracy is critical

### Recommendation

**Keep Airy approximation for calibrator matching**, but:
1. **Document** that it's an approximation
2. **Add option** to use H5 beam model for critical cases
3. **Ensure** VP table is used for imaging (already done)
4. **Consider** adding a "PB accuracy" indicator in the dashboard

**Priority: Medium** - Current approach works, but using actual beam model would be more accurate for edge cases.

