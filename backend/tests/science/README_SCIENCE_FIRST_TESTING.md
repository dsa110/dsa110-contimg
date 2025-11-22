# Science-First Testing Strategy

## Overview

This testing strategy validates the **scientific correctness** of the
calibration pipeline, not just that code runs without errors. Tests are written
from the perspective of a **rigorous radio astronomer and CASA expert**.

## Philosophy

**The pipeline is in a DYSFUNCTIONAL STATE if it produces scientifically invalid
results, even if code runs successfully.**

### Key Principles

1. **Flux Scale Accuracy**: Calibrated fluxes must match known values
2. **Physical Reasonableness**: Solutions must be physically plausible
3. **CASA Standards**: Must follow NRAO/CASA best practices
4. **Scientific Validity**: Results must be publishable-quality
5. **Astronomical Correctness**: MS structure must be astronomically correct

## Test Categories

### 1. Flux Scale Validation

- **MODEL_DATA flux matches catalog**:\*\*
  - Known calibrator: 0834+555 = 2.5 Jy at 1.4 GHz
  - Tolerance: 4% (0.1 Jy)
  - **Failure indicates**: Model population error or catalog error

- **CORRECTED_DATA preserves flux scale:**
  - Ratio CORRECTED_DATA / MODEL_DATA should be ~1.0
  - Tolerance: 10%
  - **Failure indicates**: Calibration flux scale error

- **Bandpass normalization is correct:**
  - Bandpass median amplitude should be ~1.0 (solnorm=True)
  - Tolerance: 5%
  - **Failure indicates**: Bandpass normalization error

### 2. Phase Solution Physical Reasonableness

- **Phase solutions are continuous:**
  - No jumps > 180 degrees
  - Typical stability: < 45 degrees
  - **Failure indicates**: Solution errors or wrapping issues

- **Pre-bandpass phase reduces decorrelation:**
  - Without pre-bandpass: 30-60 deg scatter
  - With pre-bandpass: < 20 deg scatter
  - **Failure indicates**: Pre-bandpass not working correctly

- **Reference antenna phase is stable:**
  - Refant phase should be ~0 degrees (by definition)
  - Tolerance: 1 degree
  - **Failure indicates**: Reference antenna calibration error

### 3. Bandpass Shape Scientific Validity

- **Bandpass is smooth across frequency:**
  - No sharp discontinuities
  - Max channel-to-channel change: 10%
  - **Failure indicates**: Frequency ordering problems or bad solutions

- **Bandpass normalization is correct:**
  - Median amplitude ~1.0 (solnorm=True)
  - Tolerance: 5%
  - **Failure indicates**: Normalization error

- **Bandpass amplitude is reasonable:**
  - Range: 0.1 - 10.0
  - Values outside indicate calibration failure
  - **Failure indicates**: Calibration error or data quality issues

### 4. MS Structure Scientific Correctness

- **Phase center matches calibrator:**
  - REFERENCE_DIR must match source position
  - Separation < 1 arcmin
  - **Failure indicates**: MS phasing error (54.7 arcmin offset bug)

- **Field contains calibrator:**
  - Field center within primary beam
  - Or calibrator within field
  - **Failure indicates**: Field selection error

- **MODEL_DATA has correct phase structure:**
  - Phase scatter < 10 degrees
  - Indicates proper alignment
  - **Failure indicates**: MODEL_DATA population error

### 5. CASA Standards Compliance

- **Calibration table structure:**
  - Required columns: TIME, ANTENNA1, SPW, CHAN (BP), CPARAM, FLAG
  - CPARAM shape: (n_pols, n_solutions)
  - **Failure indicates**: Table structure error

- **Phase center format:**
  - ICRS frame, CASA-compliant format
  - REFERENCE_DIR matches PHASE_DIR
  - **Failure indicates**: MS phasing error

- **Calibration task parameters:**
  - Bandpass: bandtype='B', solnorm=True
  - Gain: calmode='p' (after bandpass)
  - **Failure indicates**: Parameter error

### 6. Solution Quality Metrics

- **Bandpass flagged fraction < 50%:**
  - > 50% indicates calibration failure
  - Target: < 30%
  - **Failure indicates**: Low SNR, poor data quality, or calibration error

- **Pre-bandpass phase flagged fraction < 30%:**
  - > 30% indicates problems
  - Target: < 20%
  - **Failure indicates**: Pre-bandpass parameter issues

- **Solutions have sufficient SNR:**
  - Bandpass: SNR >= 3.0
  - Pre-bandpass: SNR >= 3.0 (lowered from 5.0)
  - **Failure indicates**: Poor data quality or calibration error

### 7. Calibrator Selection

- **Calibrator flux is appropriate:**
  - Range: 0.5 - 10.0 Jy
  - Too faint: low SNR
  - Too bright: may saturate
  - **Failure indicates**: Poor calibrator selection

- **Calibrator within primary beam:**
  - PB response >= 0.3
  - Optimal: PB > 0.5
  - **Failure indicates**: Calibrator too far from beam center

- **Reference antenna is appropriate:**
  - Good data quality
  - Stable phase
  - Not flagged
  - **Failure indicates**: Poor refant selection

### 8. Subband Ordering Scientific Impact

- **Frequency channels in correct order:**
  - Subbands sorted by number (0-15)
  - **Failure indicates**: Frequency scrambling, incorrect bandpass

- **Subband ordering affects bandpass:**
  - Incorrect ordering produces incorrect bandpass
  - Discontinuous frequency response
  - **Failure indicates**: Subband sorting error

### 9. Calibration Workflow Scientific Correctness

- **Calibration sequence is correct:**
  - K (skip for DSA-110) -> BP -> G
  - **Failure indicates**: Wrong calibration order

- **Pre-bandpass phase before bandpass:**
  - Must be applied before bandpass
  - **Failure indicates**: Wrong application order

- **MODEL_DATA populated before calibration:**
  - Required for calibration solve
  - **Failure indicates**: Missing MODEL_DATA

## Running Science-First Tests

```bash
# Activate casa6 environment
source activate casa6  # or conda activate casa6

# Run all science-first tests
pytest tests/science/ -v

# Run specific test category
pytest tests/science/test_calibration_scientific_validation.py::TestFluxScaleAccuracy -v

# Run with detailed output
pytest tests/science/ -v -s

# Run with coverage
pytest tests/science/ --cov=src/dsa110_contimg/calibration --cov=src/dsa110_contimg/qa
```

## Integration with Existing Tests

Science-first tests complement existing tests:

- **Unit tests**: Validate code functionality
- **Integration tests**: Validate workflow execution
- **Science-first tests**: Validate scientific correctness

All three are necessary for a production-ready pipeline.

## Known Issues Validated

These tests validate fixes for known issues:

1. **MS Phasing (54.7 arcmin offset)**: Validates REFERENCE_DIR alignment
2. **Pre-bandpass phase parameters**: Validates solint and minsnr
3. **Subband ordering**: Validates frequency channel ordering
4. **MODEL_DATA population**: Validates model flux accuracy
5. **Bandpass normalization**: Validates solnorm correctness

## Future Enhancements

1. **Real Data Validation**: Test against known good calibrator observations
2. **Flux Scale Comparison**: Compare with VLA flux scale
3. **Imaging Quality**: Validate image flux scale and dynamic range
4. **Long-term Stability**: Validate calibration stability over time
5. **Cross-validation**: Compare with independent calibration software

## References

- **CASA Calibration Guide**: https://casa.nrao.edu/casadocs/
- **VLA Calibrator Manual**:
  https://science.nrao.edu/facilities/vla/docs/manuals/calguide/
- **Radio Astronomy Data Reduction**: Thompson, Moran, Swenson (2001)
- **CASA Best Practices**:
  https://science.nrao.edu/facilities/vla/docs/manuals/oss/performance
