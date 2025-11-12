# WABIFAT Tool Analysis

**Date:** 2025-11-12  
**Repository:** https://github.com/KasVeken/WABIFAT  
**Purpose:** Assess borrowable techniques for DSA-110 continuum imaging pipeline

---

## Executive Summary

**WABIFAT** (WSClean, Aegean, Bane Interaction to create fluxdensity versus Frequency And Time plots) is a Python tool for creating spectra and light curves from radio observation MS files (LOFAR). While the codebase is small and "not user friendly" according to the author, it contains several techniques that could enhance the DSA-110 pipeline's photometry capabilities.

**Key Finding:** WABIFAT's **adaptive channel binning** and **Aegean source fitting integration** could significantly improve the DSA-110 pipeline's forced photometry, especially for weak sources and multi-frequency analysis.

---

## WABIFAT Components

### 1. `WABIFAT_FINAL.py` - Adaptive Channel Binning

**Purpose:** Adaptively bins frequency channels to find detections or non-detections

**Algorithm Details (from code analysis):**

The adaptive binning algorithm implements an iterative, width-increasing strategy:

1. **Initialization:**
   - Start with `initial_check_width` (e.g., 5 channels for frequency, 325 scans for time)
   - Create list of all channels/scans to process
   - Initialize empty lists for detections, misfits, and results

2. **Main Loop (increasing check_width):**
   ```python
   for check_width in range(initial_check_width, max_width):
       # Find consecutive series of channels/scans
       # Split series into slices of check_width
       # Process each slice with WSClean + BANE + Aegean
       # If SNR < threshold: add channels back to pool
       # If SNR >= threshold: record as detection
   ```

3. **Consecutive Series Detection:**
   - Identifies consecutive channels/scans (e.g., [24, 25, 26, 27, ...])
   - Handles gaps by splitting into separate series
   - Uses modulo operation to handle remainder channels

4. **Slice Processing:**
   - Splits consecutive series into slices of `check_width` channels
   - Each slice processed independently:
     - WSClean imaging with channel range
     - BANE for RMS/background estimation
     - Aegean for source detection
     - SNR check (default: 5σ threshold)

5. **Misfit Handling:**
   - Channels that never meet SNR threshold become "misfits"
   - Final pass: tries combining adjacent misfits
   - If combined misfits meet threshold, they become detections

6. **Key Parameters:**
   - `SNR_accept = 5.0` (default SNR threshold)
   - `seedclip = 4.0` (Aegean seed clipping threshold)
   - `coord_margin = 0.5*0.3*0.002777` (3 arcsec search radius in degrees)
   - `misfitnumber = 2` (minimum misfits to retry)

**Key Technique:**
- Iterative width-increasing strategy (starts narrow, widens until detection)
- SNR-based detection threshold (5σ default)
- Misfit recovery mechanism (tries adjacent combinations)
- Works across frequency channels OR time intervals (same algorithm)

**Potential Value for DSA-110:**
- **Multi-frequency analysis**: DSA-110 processes 16 subbands (frequency channels)
- **Weak source detection**: Adaptive binning could improve detection of faint sources
- **SNR optimization**: Better flux measurements for sources near detection threshold

**Current DSA-110 Gap:**
- Current photometry (`photometry/forced.py`) uses simple peak measurement in a fixed box
- No adaptive binning or frequency-domain optimization
- No multi-frequency combination strategy

### 2. `FF_and_more.py` - Forced Fitting with Aegean

**Purpose:** 
- Forced fitting mechanism using Aegean's prioritized fitting option
- Calculates circular polarization fraction (Stokes V)
- Plots Stokes I, Stokes V, and fraction plots

**Algorithm Details (from code analysis):**

1. **Forced Fitting Workflow (`forced_fitter()` function):**
   ```python
   for each FITS image (detections + non-detections):
       # Run BANE for RMS/background
       os.system('BANE ' + fits_path)
       
       # Extract PSF parameters from FITS header
       bmaj = header['bmaj'] * 3600  # arcsec
       bmin = header['bmin'] * 3600
       bpa = header['bpa']
       
       # Create Aegean input table with source position
       create_fits_table(
           ra=target_ra,
           dec=target_dec,
           peak_flux=1.0,  # dummy value
           a=bmaj, b=bmin, pa=bpa,  # PSF parameters
           psf_a=bmaj, psf_b=bmin, psf_pa=bpa
       )
       
       # Run Aegean with prioritized fitting
       os.system('aegean --autoload --priorized 1 '
                 '--input input_table.fits '
                 '--floodclip -1 '
                 '--table output_table.fits '
                 '--noise rms.fits '
                 '--background bkg.fits '
                 'image.fits')
       
       # Extract results from Aegean output table
       peak_flux = table['peak_flux']
       err_peak_flux = table['err_peak_flux']
       local_rms = table['local_rms']
   ```

2. **Polarization Fraction Calculation (`polfrac_forced_plot()` function):**
   - Combines Stokes I and Stokes V forced-fit results
   - Matches frequency/time intervals between I and V
   - Calculates fraction: `polfrac = abs(V/I)`
   - Error propagation:
     ```python
     polfrac_err = polfrac * sqrt(
         (err_I/I)^2 + (err_V/V)^2
     )
     ```
   - Handles mismatched interval widths with scaling factors
   - Filters by SNR (requires SNR_I >= 3 AND SNR_V >= 3)

3. **Key Techniques:**
   - **Aegean integration**: Uses Aegean source finder for sophisticated source fitting
   - **Prioritized fitting**: `--priorized 1` flag for forced fitting at known positions
   - **PSF-aware fitting**: Uses image PSF parameters in input table
   - **Polarization analysis**: Stokes V (circular polarization) calculation with proper error propagation
   - **Interval matching**: Complex logic to match I and V intervals with different widths

**Potential Value for DSA-110:**
- **Better source fitting**: Aegean provides more accurate flux measurements than simple peak
- **Blended sources**: Prioritized fitting handles overlapping sources better
- **Polarization capability**: Adds Stokes V analysis (currently DSA-110 focuses on Stokes I)
- **Morphology handling**: Better for extended or resolved sources

**Current DSA-110 Gap:**
- Simple peak measurement (`measure_forced_peak`) - no source fitting
- No Aegean integration
- No polarization analysis (Stokes V)
- Limited handling of blended/extended sources

### 3. `plot.py` - FITS Creation and Plotting

**Purpose:**
- Creates input FITS files necessary for WABIFAT and FF_and_more
- Contains plotting functions for results

**Potential Value for DSA-110:**
- Plotting utilities for spectra and light curves
- FITS file preparation utilities

**Current DSA-110 Status:**
- Already has FITS export capabilities
- Has basic QA plotting (`qa/plotting.py`)
- Could benefit from enhanced light curve visualization

---

## Comparison: WABIFAT vs. DSA-110 Photometry

### Current DSA-110 Approach (`photometry/forced.py`)

**Strengths:**
- Simple, fast peak measurement
- Well-integrated with normalization pipeline
- Robust error estimation (sigma-clipped RMS in annulus)
- Works with PB-corrected images

**Limitations:**
- Fixed box size (5 pixels default)
- No adaptive binning
- No source fitting (just peak)
- No polarization analysis
- Limited handling of blended sources

### WABIFAT Approach

**Strengths:**
- Adaptive channel binning for SNR optimization
- Aegean integration for sophisticated source fitting
- Polarization analysis (Stokes V)
- Prioritized fitting for blended sources

**Limitations:**
- Code quality: "not user friendly" (per author)
- Small codebase (3 files, ~5 commits)
- LOFAR-specific (may need adaptation for DSA-110)
- No normalization pipeline (DSA-110's key strength)

---

## Borrowable Techniques

### 1. Adaptive Channel Binning ⭐ HIGH VALUE

**What it is:**
- Dynamically combines frequency channels to optimize SNR
- Adapts binning strategy based on source strength and noise characteristics

**How to adapt for DSA-110:**
- Apply to 16 subbands during conversion or imaging
- Create adaptive binning function that:
  - Starts with individual subbands
  - Combines adjacent subbands if SNR < threshold
  - Optimizes binning per source or per field
- Integrate into `photometry/forced.py` or create new `photometry/adaptive.py`

**Implementation Approach:**
```python
def adaptive_bin_channels(
    subband_ms_list: List[str],
    target_snr: float = 5.0,
    min_channels: int = 1,
    max_channels: int = 16,
) -> List[Tuple[int, int]]:
    """Determine optimal channel binning for SNR target.
    
    Returns list of (start_channel, end_channel) tuples.
    """
    # Measure SNR per subband
    # Combine until target SNR reached
    # Return binning strategy
```

**Benefits:**
- Better detection of weak sources
- Optimized SNR for photometry
- More robust flux measurements

**Integration Points:**
- `conversion/strategies/hdf5_orchestrator.py`: Apply during conversion
- `imaging/cli.py`: Apply during imaging (frequency-dependent imaging)
- `photometry/forced.py`: Apply during photometry measurement

### 2. Aegean Source Fitting Integration ⭐ HIGH VALUE

**What it is:**
- Uses Aegean source finder for sophisticated source fitting
- Handles extended sources, blended sources, complex morphologies
- Provides integrated flux (not just peak)

**How to adapt for DSA-110:**
- Add Aegean as optional dependency
- Create `photometry/aegean_fitting.py` module
- Integrate with existing forced photometry workflow
- Use Aegean for sources where simple peak measurement is insufficient

**Implementation Approach:**
```python
def measure_with_aegean(
    fits_path: str,
    ra_deg: float,
    dec_deg: float,
    *,
    search_radius_arcsec: float = 10.0,
    use_prioritized: bool = True,
) -> AegeanPhotometryResult:
    """Measure source using Aegean source finder.
    
    Returns integrated flux, peak flux, morphology parameters.
    """
    # Run Aegean on FITS image
    # Match source to catalog position
    # Extract flux and morphology
```

**Benefits:**
- More accurate flux for extended sources
- Better handling of blended sources
- Morphology information (size, shape)
- Integrated flux vs. peak flux option

**Dependencies:**
- Aegean source finder (Python package)
- May require additional system dependencies

**Integration Points:**
- `photometry/forced.py`: Add `measure_with_aegean()` function
- `photometry/cli.py`: Add `--use-aegean` flag
- `photometry/normalize.py`: Use Aegean results for normalization

### 3. Polarization Analysis ⭐ MEDIUM VALUE

**What it is:**
- Calculates circular polarization fraction (Stokes V)
- Plots Stokes I, Stokes V, and fraction

**How to adapt for DSA-110:**
- DSA-110 currently focuses on Stokes I (total intensity)
- Add Stokes V analysis for circular polarization
- Create `photometry/polarization.py` module

**Implementation Approach:**
```python
def measure_polarization(
    fits_path_stokes_i: str,
    fits_path_stokes_v: str,
    ra_deg: float,
    dec_deg: float,
) -> PolarizationResult:
    """Measure circular polarization fraction.
    
    Returns Stokes I, Stokes V, and fraction V/I.
    """
```

**Benefits:**
- Additional science capability (circular polarization)
- Better source characterization
- Potential for polarization-based ESE detection

**Considerations:**
- Requires Stokes V images (may need imaging pipeline changes)
- May not be priority for ESE detection (focus is on total intensity)

**Integration Points:**
- `imaging/cli.py`: Add Stokes V imaging option
- `photometry/polarization.py`: New module for polarization analysis
- `api/routes.py`: Add polarization endpoints

### 4. Prioritized Fitting ⭐ MEDIUM VALUE

**What it is:**
- Aegean's prioritized fitting option for handling blended sources
- Fits multiple sources simultaneously with proper deblending

**How to adapt for DSA-110:**
- Use Aegean's prioritized fitting mode
- Apply to crowded fields or blended sources
- Integrate with existing photometry workflow

**Benefits:**
- Better flux measurements in crowded fields
- Proper deblending of overlapping sources
- More accurate photometry for ESE detection

**Integration Points:**
- `photometry/aegean_fitting.py`: Use prioritized fitting mode
- `photometry/cli.py`: Add `--prioritized-fitting` flag

---

## Implementation Recommendations

### Phase 1: Adaptive Channel Binning (High Priority)

**Effort:** Medium (2-3 days)  
**Value:** High  
**Risk:** Low

**Steps:**
1. ✅ Study WABIFAT's adaptive binning algorithm (code analyzed)
2. Implement `photometry/adaptive_binning.py` module with iterative width-increasing strategy
3. Integrate with `photometry/forced.py` or imaging pipeline
4. Test on DSA-110 data (16 subbands)
5. Compare SNR improvements vs. current approach

**Algorithm Implementation:**
```python
def adaptive_bin_channels(
    subband_list: List[str],
    target_snr: float = 5.0,
    initial_width: int = 1,
    max_width: int = 16,
    coord_ra: float,
    coord_dec: float,
) -> List[Detection]:
    """Adaptive channel binning following WABIFAT algorithm.
    
    Returns list of detections with optimal binning.
    """
    all_channels = list(range(len(subband_list)))
    misfit_channels = []
    detections = []
    
    for check_width in range(initial_width, max_width + 1):
        new_all_channels = []
        
        # Find consecutive series
        series = find_consecutive_series(all_channels)
        
        for series_channels in series:
            # Split into slices of check_width
            slices = split_into_slices(series_channels, check_width)
            
            for slice_channels in slices:
                # Image combined channels
                image_path = image_channels(slice_channels)
                
                # Measure photometry
                flux, rms, snr = measure_photometry(
                    image_path, coord_ra, coord_dec
                )
                
                if snr >= target_snr:
                    detections.append(Detection(
                        channels=slice_channels,
                        flux=flux,
                        rms=rms,
                        snr=snr
                    ))
                else:
                    # Add back to pool for next iteration
                    new_all_channels.extend(slice_channels)
        
        all_channels = new_all_channels
        if not all_channels:
            break
    
    # Final pass: try adjacent misfits
    misfit_detections = try_adjacent_misfits(misfit_channels)
    detections.extend(misfit_detections)
    
    return detections
```

**Dependencies:**
- ✅ WABIFAT source code analyzed (cloned to `/data/dsa110-contimg/archive/references/WABIFAT`)
- Understanding of DSA-110 subband structure

### Phase 2: Aegean Integration (High Priority)

**Effort:** Medium-High (3-5 days)  
**Value:** High  
**Risk:** Medium (dependency management)

**Steps:**
1. Install Aegean source finder in casa6 environment
2. Create `photometry/aegean_fitting.py` module
3. Implement `measure_with_aegean()` function following WABIFAT pattern:
   ```python
   def measure_with_aegean(
       fits_path: str,
       rms_path: str,
       bkg_path: str,
       ra_deg: float,
       dec_deg: float,
       *,
       use_prioritized: bool = True,
   ) -> AegeanResult:
       """Measure source using Aegean forced fitting.
       
       Follows WABIFAT's forced_fitter() approach:
       1. Extract PSF from FITS header
       2. Create input table with source position + PSF
       3. Run Aegean with --priorized flag
       4. Extract peak_flux, err_peak_flux, local_rms
       """
       # Extract PSF parameters
       header = fits.getheader(fits_path)
       bmaj = header['bmaj'] * 3600  # arcsec
       bmin = header['bmin'] * 3600
       bpa = header['bpa']
       
       # Create input table
       table = create_aegean_input_table(
           ra=ra_deg,
           dec=dec_deg,
           peak_flux=1.0,  # dummy
           a=bmaj, b=bmin, pa=bpa,
           psf_a=bmaj, psf_b=bmin, psf_pa=bpa
       )
       
       # Run Aegean
       run_aegean(
           image=fits_path,
           noise=rms_path,
           background=bkg_path,
           input_table=table,
           prioritized=use_prioritized,
           output_table='aegean_output.fits'
       )
       
       # Extract results
       return extract_aegean_results('aegean_output.fits')
   ```
4. Add CLI flag `--use-aegean` to photometry CLI
5. Test on extended/blended sources
6. Compare flux accuracy vs. simple peak measurement

**Dependencies:**
- Aegean Python package
- System dependencies (may conflict with casa6)
- Testing on real DSA-110 data

### Phase 3: Polarization Analysis (Low Priority)

**Effort:** High (5-7 days)  
**Value:** Medium  
**Risk:** Medium (requires imaging pipeline changes)

**Steps:**
1. Add Stokes V imaging to `imaging/cli.py`
2. Create `photometry/polarization.py` module
3. Implement polarization fraction calculation
4. Add plotting utilities
5. Test on DSA-110 data

**Considerations:**
- May not be priority for ESE detection
- Requires imaging pipeline modifications
- Additional storage for Stokes V images

---

## Code Access and Analysis

**Status:** ✅ **COMPLETE** - WABIFAT repository cloned and analyzed

**Location:** `/data/dsa110-contimg/archive/references/WABIFAT`

**Files Analyzed:**
1. ✅ `WABIFAT_FINAL.py` (1,257 lines) - Adaptive binning algorithm fully documented
2. ✅ `FF_and_more.py` (1,377 lines) - Forced fitting and polarization analysis documented
3. ✅ `plot.py` (996 lines) - Plotting utilities reviewed
4. ✅ `README.md` - Project description reviewed

**Key Algorithms Extracted:**
- ✅ Adaptive channel binning algorithm (iterative width-increasing strategy)
- ✅ Forced fitting workflow (BANE + Aegean integration)
- ✅ Polarization fraction calculation (with error propagation)
- ✅ Misfit recovery mechanism (adjacent channel combination)

**Code Quality Notes:**
- Code is functional but has some quality issues (as author noted)
- Heavy use of `os.system()` calls (could be improved with subprocess)
- Hardcoded paths and parameters (needs refactoring for DSA-110)
- Good algorithm logic despite code style issues

---

## Compatibility Assessment

### Dependencies

**WABIFAT Dependencies (inferred):**
- WSClean (DSA-110 already uses)
- Aegean (would need to add)
- Bane (unknown - may be LOFAR-specific)
- Python standard libraries

**DSA-110 Compatibility:**
- ✅ WSClean: Already integrated
- ⚠️ Aegean: Would need installation in casa6 environment
- ❓ Bane: Unknown compatibility
- ✅ Python: Compatible (Python 3.11.13 in casa6)

### Data Format Compatibility

**WABIFAT Input:**
- MS files (compatible)
- FITS images (compatible)

**DSA-110 Output:**
- MS files ✅
- FITS images ✅
- PB-corrected images ✅

**Compatibility:** ✅ High - Both use standard radio astronomy formats

### Telescope-Specific Considerations

**WABIFAT:**
- Designed for LOFAR (low frequencies, wide FoV)
- May have LOFAR-specific assumptions

**DSA-110:**
- Higher frequencies (1.4 GHz vs. LOFAR's ~50-200 MHz)
- Different array configuration
- Different calibration approach

**Adaptation Required:**
- Frequency-dependent parameters may need adjustment
- Array-specific optimizations may not apply
- Core algorithms should be adaptable

---

## Risk Assessment

### Technical Risks

1. **Aegean Installation**: Medium risk
   - May conflict with casa6 dependencies
   - May require system-level packages
   - **Mitigation**: Test in isolated environment first

2. **Algorithm Adaptation**: Low-Medium risk
   - WABIFAT algorithms may be LOFAR-specific
   - Need to verify assumptions hold for DSA-110
   - **Mitigation**: Start with simple adaptations, test thoroughly

3. **Code Quality**: Low risk
   - WABIFAT code is "not user friendly" (per author)
   - May need significant refactoring
   - **Mitigation**: Extract algorithms, rewrite for DSA-110 standards

### Integration Risks

1. **Pipeline Disruption**: Low risk
   - Can add as optional features
   - Existing photometry remains unchanged
   - **Mitigation**: Feature flags, gradual rollout

2. **Performance Impact**: Low risk
   - Aegean fitting slower than simple peak
   - Adaptive binning may add overhead
   - **Mitigation**: Make optional, benchmark performance

---

## Conclusion

**WABIFAT offers valuable techniques** that could enhance the DSA-110 pipeline, particularly:

1. **Adaptive channel binning** - High value, low risk, medium effort
2. **Aegean source fitting** - High value, medium risk, medium-high effort
3. **Polarization analysis** - Medium value, medium risk, high effort

**Recommended Approach:**
1. **Start with adaptive binning** - Highest value-to-effort ratio
2. **Add Aegean integration** - Significant improvement for extended/blended sources
3. **Consider polarization** - Lower priority, evaluate science value first

**Next Steps:**
1. Clone WABIFAT repository and examine code
2. Document adaptive binning algorithm
3. Implement Phase 1 (adaptive binning) as proof of concept
4. Evaluate results before proceeding to Phase 2

**Key Insight:** WABIFAT's strength is in **sophisticated source fitting and adaptive optimization**, while DSA-110's strength is in **differential normalization and systematic error removal**. Combining both approaches could yield the best of both worlds.

---

## References

- **WABIFAT Repository**: https://github.com/KasVeken/WABIFAT
- **Aegean Source Finder**: https://github.com/PaulHancock/Aegean
- **DSA-110 Photometry**: `src/dsa110_contimg/photometry/`
- **DSA-110 Normalization**: `src/dsa110_contimg/photometry/normalize.py`

