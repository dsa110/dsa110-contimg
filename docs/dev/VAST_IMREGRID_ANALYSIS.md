# VAST Use of imregrid - Analysis

## Question
Does VAST use `imregrid` for mosaicking?

## Answer
**No, VAST does not explicitly use `imregrid`**, but **`imcombine` doesn't exist in CASA6**.

## Evidence

### From VAST Documentation
According to `docs/analysis/VAST_MOSAIC_AND_ANALYSIS_WORKFLOW.md`:

**VAST Mosaic Creation Tools:**
- **immath** (CASA): Mathematical operations on images (PB correction, scaling)
- **imcombine** (CASA): Combines multiple images into mosaic *(Note: Not available in CASA6)*
- **Alternative**: Custom mosaicking scripts using numpy/astropy

### CASA6 Reality Check
**`imcombine` does not exist in CASA6:**
- Checked `casatasks` module - no `imcombine` function
- Available image tasks: `immath`, `imregrid`, `importfits`, `exportfits`, etc.
- No mosaic-specific combination task

**Implications:**
- VAST documentation may refer to older CASA versions or ASKAPsoft tools
- VAST likely uses custom scripts or `immath` for combination
- Our `imregrid` + `immath` approach is appropriate for CASA6

**VAST Workflow:**
```
Individual Beam Images
    ↓
Primary Beam Correction (per beam)
    ↓
Convolution to Common Resolution
    ↓
Linear Mosaicking (immath/imcombine)
```

### Key Finding
VAST uses **`imcombine`** which likely handles coordinate system alignment automatically, rather than explicitly calling `imregrid` beforehand.

## DSA-110 Implementation

### Current Approach
Our VAST-like implementation uses:
1. **`imregrid`**: Explicitly regrids tiles to a common template coordinate system
2. **`immath`**: Performs PB weighting and combination

**Why we use `imregrid`:**
- More explicit control over coordinate system alignment
- Allows us to use first tile as template
- Handles edge cases (e.g., "All output pixels are masked") explicitly
- More transparent workflow

### Comparison

| Aspect | VAST | DSA-110 |
|--------|------|---------|
| Regridding | `imcombine` handles automatically | Explicit `imregrid` call |
| Combination | `imcombine` | `immath` with manual weighting |
| Control | Less explicit | More explicit |
| Error Handling | Handled by `imcombine` | Manual try/except blocks |

## Implications

### Advantages of VAST's Approach
- Simpler workflow (one tool does both regridding and combination)
- Less code to maintain
- CASA handles edge cases internally

### Advantages of DSA-110's Approach
- More explicit control over coordinate system
- Better error handling and reporting
- Can skip problematic tiles explicitly
- More transparent about what's happening

## Recommendation

**Current DSA-110 approach is acceptable** because:
1. We have explicit error handling for `imregrid` failures
2. We can skip tiles that fail regridding
3. We have more control over the process
4. The workflow is more transparent

**Potential Future Improvement:**
Consider testing `imcombine` as an alternative to see if it:
- Handles regridding automatically
- Provides better error handling
- Simplifies the code
- Produces equivalent results

## Conclusion

**VAST does not use `imregrid` explicitly**, but **`imcombine` doesn't exist in CASA6**, so VAST likely:
1. Uses custom mosaicking scripts (as mentioned in documentation)
2. Uses `immath` for combination (similar to our approach)
3. May use ASKAPsoft tools (not available to DSA-110)

**Our `imregrid` + `immath` approach is:**
- Appropriate for CASA6 (no `imcombine` available)
- Provides explicit control over coordinate system alignment
- Handles edge cases explicitly
- Follows the same general pattern as VAST (regrid then combine)

**This validates our implementation approach** - we're using the tools available in CASA6 to achieve the same result as VAST's workflow.

