# WABIFAT Techniques Compatibility Assessment

**Date:** 2025-01-XX  
**Purpose:** Verify DSA-110 data products are compatible with WABIFAT techniques before implementation

---

## Executive Summary

**Status:** ⚠️ **PARTIAL COMPATIBILITY** - Some techniques require pipeline modifications

**Findings:**
- ✅ **Phase 2 (Aegean Integration)**: Compatible - FITS images should have PSF headers
- ⚠️ **Phase 1 (Adaptive Binning)**: Requires verification - subbands merged into single MS
- ❌ **Phase 3 (Polarization)**: Not compatible - Only Stokes I produced

---

## Phase 1: Adaptive Channel Binning

### Requirements
- Multiple frequency channels/subbands that can be imaged separately or combined
- Ability to select specific frequency ranges during imaging
- SNR measurement capability per frequency bin

### DSA-110 Current State

**Subband Structure:**
- ✅ **16 subbands** (NSUBBAND = 16) confirmed in `constants.py`
- ✅ Subbands cover frequency range: 1311.25 - 1498.75 MHz
- ✅ Each subband has 48 channels (NCHAN = 48)
- ✅ Subbands identified by codes: `sb00` (highest freq) to `sb15` (lowest freq)

**Current Imaging Approach:**
- ⚠️ **Subbands are MERGED into single MS** before imaging
- ⚠️ Default imaging uses **all subbands together** (MFS mode)
- ⚠️ `spw` parameter exists in `image_ms()` but typically empty (all SPWs)
- ⚠️ No evidence of per-subband imaging in current pipeline

**Code Evidence:**
```python
# From conversion/strategies/direct_subband.py
# Subbands are concatenated into single MS:
casa_concat(vis=parts, concatvis=ms_stage_path, ...)

# From imaging/cli_imaging.py
# Default imaging uses all SPWs:
spw: str = "",  # Empty = all spectral windows
stokes="I",     # Only Stokes I
specmode="mfs", # Multi-frequency synthesis (all frequencies combined)
```

### Compatibility Assessment

**Status:** ✅ **VERIFIED** - SPW selection works

**Verification Results:**
- ✅ MS contains 16 SPWs (subbands preserved)
- ✅ Each SPW has 48 channels
- ✅ SPW selection via `spw="0"` parameter works
- ✅ Frequency ranges: 1311.39 - 1498.75 MHz

**Potential Solutions:**

1. **Option A: Image Subbands Separately** (Recommended)
   - Modify imaging to support per-subband imaging
   - Use `spw` parameter to select individual spectral windows
   - Requires MS to maintain subband separation (currently merged)
   - **Effort:** Medium (2-3 days)
   - **Impact:** Enables adaptive binning, but changes imaging workflow

2. **Option B: Channel Selection During Imaging**
   - Use WSClean `-channels-out` and `-channel-range` options
   - Select frequency ranges from merged MS
   - **Effort:** Low (1 day)
   - **Impact:** Minimal pipeline changes, but less flexible

3. **Option C: Pre-Imaging Subband Selection**
   - Split MS back into subbands before imaging
   - Image each subband separately
   - **Effort:** High (3-5 days)
   - **Impact:** Significant workflow changes

**Recommendation:** Verify if `spw` parameter can select individual subbands from merged MS. If yes, Option B is simplest. If no, Option A required.

**Verification Needed:**
- [ ] Check if merged MS maintains subband SPW separation
- [ ] Test `spw="0"` (or similar) to image single subband
- [ ] Verify WSClean supports `-channel-range` for frequency selection
- [ ] Test SNR measurement on per-subband images

---

## Phase 2: Aegean Integration

### Requirements
- FITS images with PSF parameters in headers (BMAJ, BMIN, BPA)
- Ability to run BANE for RMS/background estimation
- Source coordinates for forced fitting

### DSA-110 Current State

**FITS Export:**
- ✅ Images exported to FITS via CASA `exportfits`
- ✅ FITS files created: `.image.fits`, `.image.pbcor.fits`, `.residual.fits`, `.psf.fits`
- ✅ Standard FITS format with WCS headers

**PSF Parameters:**
- ⚠️ **Not explicitly verified** in codebase
- ⚠️ CASA `exportfits` typically preserves beam parameters, but not guaranteed
- ⚠️ No code explicitly checks for BMAJ/BMIN/BPA in headers

**Code Evidence:**
```python
# From imaging/export.py
exportfits(imagename=p, fitsimage=fits_out, overwrite=True)

# From imaging/cli_imaging.py
# Beam information extracted from CASA images (not FITS):
beam_major = header.get('beammajor')  # CASA format
beam_minor = header.get('beamminor')
beam_pa = header.get('beampa')
```

**BANE Compatibility:**
- ✅ BANE is standard tool (should work with any FITS image)
- ⚠️ Not currently used in DSA-110 pipeline
- ⚠️ Would need to be installed/available

**Source Coordinates:**
- ✅ Available from catalog (photometry uses catalog positions)
- ✅ RA/Dec coordinates standard format

### Compatibility Assessment

**Status:** ✅ **VERIFIED** - FITS headers complete

**Verification Results:**
- ✅ BMAJ present: ~0.0163 deg (~58-59 arcsec)
- ✅ BMIN present: ~0.0050 deg (~18 arcsec)
- ✅ BPA present: ~110-111 deg
- ✅ BUNIT: JY/BEAM (correct)
- ✅ BTYPE: Intensity (correct)
- ✅ Verified on 3 different FITS images

**Compatibility:**
- ✅ CASA `exportfits` preserves beam parameters as BMAJ/BMIN/BPA
- ✅ Units in degrees (standard FITS) - Aegean converts to arcsec
- ✅ BANE should work with these FITS images
- ✅ All required headers present for Aegean forced fitting

**Risk:** Very Low - Standard FITS format, all headers verified

---

## Phase 3: Polarization Analysis

### Requirements
- Stokes V (circular polarization) images
- Ability to calculate V/I fraction
- Matching frequency/time intervals between I and V

### DSA-110 Current State

**Stokes Parameters:**
- ❌ **Only Stokes I produced** - hardcoded in imaging
- ❌ No Stokes V imaging capability
- ❌ No polarization products in pipeline

**Code Evidence:**
```python
# From imaging/cli_imaging.py line 566
stokes="I",  # Hardcoded - only Stokes I

# From imaging/cli_imaging.py line 238 (WSClean)
cmd.extend(["-pol", "I"])  # Only Stokes I
```

**Data Availability:**
- ✅ MS contains XX and YY correlations (from `constants.py`: POLARIZATION_ARRAY = [5, 6])
- ✅ Could potentially produce Stokes V from XX/YY
- ❌ Current pipeline doesn't extract or image Stokes V

### Compatibility Assessment

**Status:** ❌ **NOT COMPATIBLE** - Requires pipeline modifications

**Required Changes:**
1. **Add Stokes V Imaging:**
   - Modify `image_ms()` to support `stokes="V"`
   - Update WSClean command to include `-pol V`
   - Add Stokes V image products to pipeline

2. **Polarization Calculation:**
   - Calculate V from XX/YY: `V = (XX - YY) / 2`
   - Or use CASA `polconvert` if available
   - Image Stokes V separately

3. **Workflow Integration:**
   - Add Stokes V imaging stage
   - Store Stokes V images in database
   - Add polarization analysis module

**Effort:** High (5-7 days)
- Imaging modifications: 2-3 days
- Pipeline integration: 2-3 days
- Testing and validation: 1 day

**Recommendation:** **Defer Phase 3** - Not priority for ESE detection (focus is Stokes I)

---

## Summary Table

| Phase | Technique | Compatibility | Verification Status | Effort if Incompatible |
|-------|-----------|---------------|-------------------|------------------------|
| **Phase 1** | Adaptive Binning | ✅ **VERIFIED** | ✅ Complete | Medium (3-4 days) |
| **Phase 2** | Aegean Integration | ✅ **VERIFIED** | ✅ Complete | Low-Medium (2-3 days) |
| **Phase 3** | Polarization | ❌ No | N/A | High (5-7 days) |

**Verification Date:** 2025-01-XX  
**See:** `WABIFAT_VERIFICATION_RESULTS.md` for detailed verification results

---

## Recommended Verification Steps

### Before Phase 1 Implementation:

1. **Test SPW Selection:**
   ```python
   # Test if individual subbands can be imaged
   image_ms(ms_path, imagename="test_sb0", spw="0")  # First subband
   image_ms(ms_path, imagename="test_sb1", spw="1")  # Second subband
   ```

2. **Check MS Structure:**
   ```python
   # Verify SPW table structure
   from casacore.tables import table
   with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
       nspw = len(spw)
       print(f"Number of SPWs: {nspw}")  # Should be 16 if subbands preserved
   ```

3. **Test WSClean Channel Selection:**
   ```bash
   # Test frequency range selection
   wsclean -channel-range 0 48 -channels-out 1 ms_path
   ```

### Before Phase 2 Implementation:

1. **Check FITS Headers:**
   ```python
   from astropy.io import fits
   hdu = fits.open("example_image.pbcor.fits")
   header = hdu[0].header
   print("BMAJ:", header.get('BMAJ'))
   print("BMIN:", header.get('BMIN'))
   print("BPA:", header.get('BPA'))
   ```

2. **Test BANE:**
   ```bash
   # Test BANE on DSA-110 FITS image
   BANE example_image.pbcor.fits --out=test_bane
   ```

### Phase 3: Not Recommended
- Requires significant pipeline changes
- Not priority for ESE detection
- Defer until polarization science case established

---

## Conclusion

**Confidence Levels:**

1. **Phase 2 (Aegean):** ✅ **HIGH CONFIDENCE** - Standard FITS format, beam parameters typically preserved
2. **Phase 1 (Adaptive Binning):** ⚠️ **MEDIUM CONFIDENCE** - Requires verification of SPW selection capability
3. **Phase 3 (Polarization):** ❌ **NOT RECOMMENDED** - Requires major pipeline changes, not priority

**Recommended Approach:**

1. **Start with Phase 2** (Aegean) - Highest confidence, immediate value
2. **Verify Phase 1** compatibility before implementation
3. **Defer Phase 3** until polarization science case is established

**Next Steps:**
1. Verify FITS headers contain BMAJ/BMIN/BPA (quick check)
2. Test SPW selection for adaptive binning (1-2 hours)
3. Proceed with Phase 2 implementation if headers verified
4. Implement Phase 1 after SPW verification

---

## References

- **DSA-110 Constants**: `src/dsa110_contimg/utils/constants.py`
- **Imaging Code**: `src/dsa110_contimg/imaging/cli_imaging.py`
- **FITS Export**: `src/dsa110_contimg/imaging/export.py`
- **Subband Conversion**: `src/dsa110_contimg/conversion/strategies/direct_subband.py`

