# ESE Detection Research Findings and Implementation Review

## Date: 2025-11-12

This document summarizes research findings on ESE detection methods and the
critical review of our implementation.

## Research Summary

### Literature Review (via Perplexity)

**Key Sources**:

1. Real-time detection of an extreme scattering event (2016) - Science
2. An Extreme Scattering Event Toward PSR J2313+4253 (2025) - arXiv
3. VAST Tools variability metrics documentation
4. Radio astronomy variability detection best practices

### Standard Practices

1. **Sigma Thresholds**:
   - **3σ**: Common for initial detection (0.3% false positive rate)
   - **5σ**: Gold standard for definitive discovery (0.00006% false positive
     rate)
   - Our default: **5.0σ** ✓ (Conservative, appropriate for production)

2. **Variability Metrics**:
   - **Chi-squared test**: Standard for testing constant flux model ✓
   - **Eta metric**: Weighted variance metric (from VAST Tools) ✓
   - **Multiple observables**: ESEs show correlated changes in flux,
     scintillation bandwidth, and DM
   - Our implementation: Uses chi-squared and eta metrics ✓

3. **Detection Methods**:
   - Real-time detection increasingly important ✓
   - Post-processing light curve analysis ✓
   - Our implementation: Both automated (real-time) and manual (post-processing)
     ✓

## Critical Issues Identified and Fixed

### ✅ FIXED: Inconsistent Sigma Deviation Calculation

**Problem**: Two different formulas existed for `sigma_deviation`:

- `ese_pipeline.py`: Correct formula (max deviation from mean / std)
- `ese_detection.py`: Incorrect formula (std / (mean / sqrt(n)))

**Fix Applied**: Updated `ese_detection.py` to use the same correct formula as
`ese_pipeline.py`

**Status**: ✅ Fixed (2025-11-12)

## Implementation Assessment

### Strengths

1. **Conservative Threshold**: 5.0σ default reduces false positives
2. **Multiple Metrics**: Uses chi-squared, eta metric, and sigma deviation
3. **Automated Pipeline**: Real-time detection integrated with photometry
4. **Well-Documented**: Comprehensive documentation and inline comments
5. **Error Handling**: Graceful degradation, non-fatal errors

### Limitations

1. **Single-Frequency Analysis**:
   - ESEs show frequency-dependent variability
   - We only analyze single-frequency flux
   - Acceptable given current observations

2. **No Multi-Observable Correlation**:
   - Research shows ESEs have correlated changes in flux, scintillation
     bandwidth, and DM
   - We only use flux variability
   - Future enhancement opportunity

3. **Conservative Threshold**:
   - 5.0σ may miss some real ESEs
   - Appropriate trade-off for production use
   - Configurable for different use cases

## Comparison with Best Practices

| Aspect              | Best Practice                   | Our Implementation    | Status        |
| ------------------- | ------------------------------- | --------------------- | ------------- |
| Sigma Threshold     | 3σ (initial), 5σ (confirmation) | 5.0σ default          | ✓ Appropriate |
| Chi-squared Test    | Standard practice               | Implemented           | ✓ Correct     |
| Eta Metric          | VAST Tools standard             | Implemented           | ✓ Correct     |
| Real-time Detection | Increasingly important          | Automated pipeline    | ✓ Implemented |
| Multi-frequency     | Recommended                     | Single-frequency only | ⚠️ Limitation |
| Multi-observable    | Recommended                     | Flux only             | ⚠️ Limitation |

## Recommendations

### Immediate (Completed)

1. ✅ Fix sigma_deviation calculation inconsistency
2. ✅ Document limitations and trade-offs

### Short-Term

3. **Add Validation Tests**:
   - Test sigma_deviation calculation against known values
   - Verify chi-squared calculation
   - Test edge cases (single measurement, zero variance)

4. **Consider Multi-Metric Scoring**:
   - Combine sigma_deviation, chi2_nu, and eta_metric
   - Weighted scoring system for candidate ranking
   - More robust than single-metric threshold

### Long-Term

5. **Multi-Frequency Analysis**:
   - When multi-frequency data available
   - Correlated variability across frequencies
   - Enhanced ESE detection confidence

6. **Multi-Observable Correlation**:
   - Include scintillation bandwidth (when available)
   - Include DM variations (for pulsars)
   - Enhanced detection confidence

7. **Real-Time Alerting**:
   - Alert on high-significance candidates
   - Integration with monitoring systems
   - Automated follow-up triggers

## Conclusion

Our ESE detection implementation is **well-designed and follows best practices**
for variability analysis. The critical bug (inconsistent sigma_deviation
calculation) has been **fixed**.

The implementation is:

- ✅ Statistically sound (uses standard metrics)
- ✅ Conservatively tuned (5.0σ threshold)
- ✅ Well-integrated (automated pipeline)
- ✅ Properly documented

**Limitations are acceptable** given current observational capabilities and
represent opportunities for future enhancement rather than critical flaws.

## References

1. Real-time detection of an extreme scattering event (2016) - Science
   - DOI: 10.1126/science.aac7673
   - Real-time detection methods

2. An Extreme Scattering Event Toward PSR J2313+4253 (2025) - arXiv
   - Multi-observable analysis
   - Scintillation bandwidth and DM variations

3. VAST Tools variability metrics
   - Eta metric implementation
   - Chi-squared testing

4. Radio astronomy variability detection best practices
   - Sigma threshold selection
   - False positive rate considerations
