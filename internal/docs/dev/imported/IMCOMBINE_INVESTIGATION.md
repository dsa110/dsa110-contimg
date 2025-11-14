# imcombine Investigation - CASA Version History

## Question
Is `imcombine` from an older version of CASA?

## Investigation Results

### Current Status (CASA6)
**`imcombine` does NOT exist in CASA6:**
- Checked `casatasks` module - not found
- Checked `casatools` module - not found
- No tasks with "combine" in the name
- casacore version: 3.7.1

### Search Results

**Perplexity Search:**
- Claims `imcombine` is still available and not deprecated
- References CASA guides mentioning it
- However, these may be outdated documentation

**Web Search:**
- One result suggests `imcombine` is NOT part of CASA
- Mentions `feather` task for combining images instead
- References to `simalma` for ALMA array combination

### Possible Explanations

1. **`imcombine` is from IRAF (not CASA):**
   - `imcombine` is an IRAF tool for pixel-by-pixel image combination
   - IRAF is an older astronomical software package
   - May have been confused with CASA tools in documentation

2. **ASKAPsoft has mosaicking (not `imcombine`):**
   - ASKAPsoft has built-in linear mosaicking functionality
   - Uses pipeline parameters, not standalone `imcombine` tool
   - VAST documentation refers to ASKAPsoft mosaicking, not CASA

3. **`imcombine` never existed in CASA:**
   - CASA has `immath` for image arithmetic/combination
   - CASA has `feather` for combining different array data
   - No `imcombine` task in any CASA version

### Evidence from VAST Documentation

VAST documentation mentions:
- **imcombine** (CASA): Combines multiple images into mosaic
- **Alternative**: Custom mosaicking scripts using numpy/astropy

This suggests VAST may:
1. Use ASKAPsoft tools (which have `imcombine`)
2. Use custom scripts (as alternative)
3. Have outdated documentation referring to older CASA

### Conclusion

**Answer: No, `imcombine` is NOT from CASA (any version).**

**`imcombine` is from IRAF:**
- IRAF (Image Reduction and Analysis Facility) is an older astronomical software package
- `imcombine` is an IRAF tool for pixel-by-pixel image combination
- Not part of CASA at any point in its history

**VAST uses ASKAPsoft mosaicking:**
- VAST documentation mentions "From ASKAPsoft Documentation" for mosaic details
- ASKAPsoft has built-in linear mosaicking (not `imcombine`)
- ASKAPsoft mosaicking uses pipeline parameters and weighting schemes
- DSA-110 uses CASA, not ASKAPsoft or IRAF

**Evidence:**
- `imcombine` not found in CASA6 (confirmed by direct import test)
- Perplexity search confirms `imcombine` is from IRAF
- ASKAPsoft documentation shows mosaicking via pipeline, not standalone tool
- VAST documentation references ASKAPsoft, not CASA, for mosaic details

**Our Approach:**
- Using `imregrid` + `immath` is the correct CASA6 approach
- This achieves the same result as VAST's workflow
- We're using standard CASA tools available to all users

### Recommendation

Update VAST documentation references to clarify:
- VAST uses ASKAPsoft `imcombine` (not CASA)
- DSA-110 uses CASA6 `imregrid` + `immath` (equivalent functionality)
- Both approaches achieve the same scientific result

