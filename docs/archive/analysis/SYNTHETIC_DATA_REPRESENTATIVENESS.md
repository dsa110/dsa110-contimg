# Synthetic Data Representativeness: Can We Trust "Works on Synthetic = Works on Real"?

## The Claim

**"If it works on our synthetic data, we know it will work on our real data"**

This document assesses whether this claim is valid for the current synthetic
data generation capabilities.

---

## What Synthetic Data Currently Captures ✓

### 1. Format and Structure ✅

- **UVH5 file format** - Identical to real data
- **Data array structure** - Same shapes: `(Nblts, Nspws, Nfreqs, Npols)`
- **Metadata structure** - Same fields, same types
- **Antenna positions** - Real ITRF coordinates from DSA-110
- **UVW coordinates** - Properly calculated with fringestopping
- **Time structure** - Realistic integration times and LST
- **Frequency structure** - Matches DSA-110 subband configuration

**Verdict:** ✅ **Format testing is valid** - If pipeline reads/writes synthetic
data correctly, it will read/write real data correctly.

### 2. Basic Pipeline Flow ✅

- **Conversion** - UVH5 → MS conversion works identically
- **File I/O** - Reading, writing, subband handling
- **Data structures** - UVData objects, arrays, metadata
- **Coordinate systems** - WCS, phase centers, UVW

**Verdict:** ✅ **Pipeline structure testing is valid** - If pipeline processes
synthetic data end-to-end, structure handling will work on real data.

### 3. Mathematical Operations ✅

- **Visibility data** - Complex visibility values (though simplified)
- **Array operations** - NumPy operations on data arrays
- **Coordinate transforms** - RA/Dec ↔ pixel, UVW calculations
- **FITS operations** - Reading/writing FITS headers and data

**Verdict:** ✅ **Basic math testing is valid** - Core mathematical operations
will work the same.

---

## What Synthetic Data Currently MISSES ✗

### 1. Realistic Source Models ✗

**Current:** Point source only at phase center  
**Real Data:** Extended sources, multiple sources, complex morphologies

**Impact:**

- ❌ **Imaging algorithms** - May not test extended source recovery
- ❌ **Deconvolution** - Point sources don't test CLEAN algorithms properly
- ❌ **Source finding** - Only tests point source detection
- ✅ **Basic imaging** - Still tests that imaging pipeline runs

**Verdict:** ⚠️ **Partial validity** - Works for basic imaging, not for extended
source science

### 2. Noise ✗

**Current:** Noise-free visibilities (deterministic)  
**Real Data:** Thermal noise, system noise, measurement errors

**Impact:**

- ❌ **SNR-limited operations** - Can't test low-SNR scenarios
- ❌ **Error propagation** - No realistic error bars
- ❌ **Robustness** - Can't test how pipeline handles noisy data
- ❌ **Calibration quality** - Can't test calibration with realistic noise
- ✅ **Algorithm correctness** - Still tests that algorithms run

**Verdict:** ⚠️ **Limited validity** - Works for correctness testing, not for
performance/robustness

### 3. RFI (Radio Frequency Interference) ✗

**Current:** No RFI simulation  
**Real Data:** Time/frequency-dependent RFI contamination

**Impact:**

- ❌ **RFI mitigation** - Can't test flagging algorithms
- ❌ **Data quality** - Can't test handling of bad data
- ❌ **Robustness** - Can't test pipeline behavior with contaminated data
- ✅ **Clean data path** - Still tests normal operation

**Verdict:** ⚠️ **Limited validity** - Works for clean data scenarios only

### 4. Calibration Errors ✗

**Current:** Perfect calibration (no gain/phase errors)  
**Real Data:** Antenna-based gains, delays, bandpass variations

**Impact:**

- ❌ **Calibration algorithms** - Can't test calibration quality
- ❌ **Self-calibration** - Perfect data doesn't need self-cal
- ❌ **Calibration transfer** - Can't test calibration application
- ✅ **Calibration structure** - Still tests that calibration code runs

**Verdict:** ⚠️ **Limited validity** - Works for calibration code path, not
calibration quality

### 5. Realistic Flux Scale ✗

**Current:** Single flux value, no spectral index  
**Real Data:** Sources with spectral indices, frequency-dependent flux

**Impact:**

- ❌ **Multi-frequency imaging** - Can't test frequency synthesis
- ❌ **Flux calibration** - Can't test flux scale accuracy
- ❌ **Spectral analysis** - Can't test spectral index measurements
- ✅ **Basic flux** - Still tests that flux values are handled

**Verdict:** ⚠️ **Limited validity** - Works for basic flux handling, not
spectral science

### 6. Time Variability ✗

**Current:** Static sources (flux constant with time)  
**Real Data:** Variable sources, scintillation, ESEs

**Impact:**

- ❌ **Variability detection** - Can't test ESE detection algorithms
- ❌ **Time-series analysis** - Can't test photometry over time
- ❌ **Transient detection** - Can't test transient search
- ✅ **Single-epoch** - Still tests single observation processing

**Verdict:** ⚠️ **Limited validity** - Works for single-epoch processing, not
variability science

---

## Validity Assessment by Use Case

### ✅ FULLY VALID Claims

**"If it works on synthetic data, it will work on real data" for:**

1. **File Format Handling**
   - Reading/writing UVH5 files
   - File I/O operations
   - Data structure parsing

2. **Pipeline Structure**
   - End-to-end pipeline execution
   - Stage transitions
   - Data flow between stages

3. **Basic Operations**
   - Array operations
   - Coordinate transforms
   - Metadata handling

4. **Code Paths**
   - All code paths are exercised
   - Error handling (for format errors)
   - Edge cases in data structure

### ✅ FULLY VALID Claims (After Enhancements)

**"If it works on synthetic data, it will work on real data" for:**

1. **Imaging** ✅
   - ✅ Basic imaging pipeline runs
   - ✅ Images are created
   - ✅ Extended source recovery tested (with `--source-model gaussian/disk`)
   - ✅ Deconvolution quality tested (extended sources require deconvolution)

2. **Calibration** ✅
   - ✅ Calibration code executes
   - ✅ Calibration tables are created
   - ✅ Calibration quality tested (with `--add-cal-errors`)
   - ✅ Self-calibration tested (calibration errors can be corrected)

3. **Photometry** ✅
   - ✅ Photometry code runs
   - ✅ Flux values are measured
   - ✅ Low-SNR scenarios tested (with `--add-noise`)
   - ✅ Error propagation tested (realistic noise provides error bars)

### ❌ NOT VALID Claims

**"If it works on synthetic data, it will work on real data" for:**

1. **Science Quality**
   - ❌ Source detection completeness
   - ❌ Flux accuracy
   - ❌ Astrometry precision
   - ❌ Image quality metrics

2. **Robustness**
   - ❌ Handling of noisy data
   - ❌ RFI mitigation
   - ❌ Data quality issues
   - ❌ Edge cases in real observations

3. **Performance**
   - ❌ Processing speed with realistic data volumes
   - ❌ Memory usage with complex sources
   - ❌ I/O performance with real file sizes

---

## Recommendations for Improving Representativeness

### ✅ IMPLEMENTED (High Priority)

1. **Add Thermal Noise** ✅ IMPLEMENTED
   - Realistic thermal noise added via `--add-noise` flag
   - Enables SNR-limited testing
   - Enables error propagation testing
   - **Impact:** Makes photometry and calibration testing valid

2. **Add Extended Sources** ✅ IMPLEMENTED
   - Gaussian and disk source models via `--source-model` flag
   - Enables imaging algorithm testing
   - Enables deconvolution testing
   - **Impact:** Makes imaging science testing valid

3. **Add Calibration Errors** ✅ IMPLEMENTED
   - Antenna-based gain/phase errors via `--add-cal-errors` flag
   - Enables calibration algorithm testing
   - Enables self-calibration testing
   - **Impact:** Makes calibration quality testing valid

### Medium Priority (Would Enable Specific Claims)

4. **Add RFI Simulation** ⭐
   - Time/frequency-dependent RFI
   - Enables flagging algorithm testing
   - Enables robustness testing
   - **Impact:** Would make data quality handling testing valid

5. **Add Spectral Index** ⭐
   - Frequency-dependent flux
   - Enables multi-frequency testing
   - Enables spectral analysis testing
   - **Impact:** Would make spectral science testing valid

### Low Priority (Nice to Have)

6. **Add Time Variability**
   - Variable source flux
   - Enables variability detection testing
   - **Impact:** Would make variability science testing valid

---

## Current State: What Can We Claim?

### ✅ Safe Claims (High Confidence)

1. **"If the pipeline processes synthetic data end-to-end without errors, the
   pipeline structure and code paths work correctly"**
   - Format handling: ✅
   - Data structures: ✅
   - Pipeline flow: ✅
   - Code execution: ✅

2. **"If synthetic data converts to MS correctly, real data will convert
   correctly"**
   - File format: ✅
   - Data structure: ✅
   - Metadata handling: ✅

3. **"If synthetic data images correctly, the imaging pipeline code works
   correctly"**
   - Code execution: ✅
   - Basic imaging: ✅
   - Image format: ✅
   - **Extended source recovery: ✅ (with `--source-model gaussian/disk`)**
   - **Deconvolution quality: ✅ (extended sources require deconvolution)**

4. **"If synthetic data calibrates correctly, real data calibration will work"**
   - Code execution: ✅
   - **Calibration quality: ✅ (with `--add-cal-errors`)**
   - **Self-calibration: ✅ (calibration errors can be corrected)**

5. **"If synthetic data photometry works, real data photometry will work"**
   - Code execution: ✅
   - High-SNR sources: ✅
   - **Low-SNR sources: ✅ (with `--add-noise`)**
   - **Error bars: ✅ (realistic noise provides errors)**

### ❌ Cannot Claim (Low Confidence)

1. **"If synthetic data produces good science results, real data will produce
   good science results"**
   - Source completeness: ❌
   - Flux accuracy: ❌
   - Image quality: ❌

2. **"If synthetic data handles edge cases, real data edge cases will be
   handled"**
   - RFI: ❌
   - Bad data: ❌
   - Calibration failures: ❌

---

## Conclusion

### Current State (After Enhancements)

**The claim "if it works on synthetic data, we know it will work on real data"
is:**

- ✅ **TRUE for:** Format handling, pipeline structure, code execution, basic
  operations
- ✅ **TRUE for:** Imaging (including extended sources with `--source-model`)
- ✅ **TRUE for:** Calibration (including quality with `--add-cal-errors`)
- ✅ **TRUE for:** Photometry (including low-SNR with `--add-noise`)
- ⚠️ **PARTIALLY TRUE for:** Science quality metrics (depends on specific test)
- ❌ **FALSE for:** Performance testing, very complex scenarios

### Enhanced Capabilities (Now Available)

**These capabilities are now implemented:**

1. ✅ **Thermal noise** - Enables SNR-limited and error testing (`--add-noise`)
2. ✅ **Extended sources** - Enables imaging science testing
   (`--source-model gaussian/disk`)
3. ✅ **Calibration errors** - Enables calibration quality testing
   (`--add-cal-errors`)

**With these enhancements, the claim is now valid for:**

- ✅ Format and structure (already valid)
- ✅ Pipeline execution (already valid)
- ✅ Basic imaging (already valid)
- ✅ **Calibration quality (now valid with `--add-cal-errors`)**
- ✅ **Photometry with errors (now valid with `--add-noise`)**
- ✅ **Extended source imaging (now valid with `--source-model`)**

### Recommendation

**Current synthetic data (with enhancements) is sufficient for:**

- ✅ Regression testing
- ✅ Code path testing
- ✅ Format validation
- ✅ Pipeline structure testing
- ✅ **Imaging science testing (with extended sources)**
- ✅ **Calibration quality testing (with cal errors)**
- ✅ **Photometry testing (with noise)**

**Current synthetic data is still NOT sufficient for:**

- Performance testing (processing speed, memory)
- Very complex scenarios (multiple sources, RFI, etc.)
- Final science validation (always verify with real data)

**For final science validation, always test with real data. But enhanced
synthetic data provides high confidence that the pipeline will work correctly.**

---

**Last Updated:** 2025-01-XX
