# ESE Detection Future Improvements

## Date: 2025-11-12

This document catalogs all improvements identified during the critical review
that were deferred for future implementation.

## Short-Term Improvements (1-3 months)

### 1. Code Quality & Testing

#### Extract Shared Sigma Deviation Function

**Priority**: Medium  
**Effort**: 1-2 hours

**Current State**:

- Sigma deviation calculation duplicated in `ese_pipeline.py` and
  `ese_detection.py`
- Risk of future inconsistencies

**Improvement**:

```python
# Create shared function in variability.py
def calculate_sigma_deviation(fluxes: np.ndarray) -> float:
    """Calculate maximum sigma deviation from mean."""
    if len(fluxes) < 2:
        return 0.0
    mean_flux = np.mean(fluxes)
    std_flux = np.std(fluxes)
    if std_flux <= 0:
        return 0.0
    max_dev = abs(np.max(fluxes) - mean_flux) / std_flux
    min_dev = abs(np.min(fluxes) - mean_flux) / std_flux
    return max(max_dev, min_dev)
```

**Benefits**:

- Single source of truth
- Prevents future inconsistencies
- Easier to test and maintain

#### Add Validation Tests

**Priority**: High  
**Effort**: 2-4 hours

**Current State**:

- No unit tests verifying sigma_deviation calculation correctness
- No tests for edge cases

**Improvements Needed**:

- Test sigma_deviation against known values
- Verify chi-squared calculation
- Test edge cases:
  - Single measurement
  - Zero variance
  - All measurements identical
  - Missing error values
  - Negative fluxes

**Test Cases**:

```python
def test_sigma_deviation_known_values():
    """Test against manually calculated values."""
    fluxes = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    expected = 2.0 / np.std(fluxes)  # max deviation = 2.0
    assert abs(calculate_sigma_deviation(fluxes) - expected) < 1e-6

def test_sigma_deviation_edge_cases():
    """Test edge cases."""
    # Single measurement
    assert calculate_sigma_deviation(np.array([1.0])) == 0.0
    # Zero variance
    assert calculate_sigma_deviation(np.array([1.0, 1.0, 1.0])) == 0.0
    # Negative fluxes
    assert calculate_sigma_deviation(np.array([-1.0, 1.0])) > 0
```

### 2. Enhanced Detection Algorithms

#### Multi-Metric Scoring System

**Priority**: Medium  
**Effort**: 1-2 days

**Current State**:

- Uses single metric (sigma_deviation) for threshold
- Other metrics (chi2_nu, eta_metric) computed but not used in scoring

**Improvement**:

```python
def calculate_ese_score(
    sigma_deviation: float,
    chi2_nu: Optional[float],
    eta_metric: Optional[float],
    n_obs: int
) -> float:
    """Calculate composite ESE candidate score.

    Combines multiple metrics for more robust detection.
    """
    # Base score from sigma deviation
    score = sigma_deviation

    # Boost score if chi-squared indicates variability
    if chi2_nu is not None and chi2_nu > 2.0:
        score += 0.5 * min(chi2_nu / 5.0, 1.0)

    # Boost score if eta metric indicates variability
    if eta_metric is not None and eta_metric > 0.1:
        score += 0.3 * min(eta_metric / 0.5, 1.0)

    # Penalize low observation count
    if n_obs < 5:
        score *= 0.8

    return score
```

**Benefits**:

- More robust detection
- Reduces false positives
- Better candidate ranking
- Uses all available information

**Configuration**:

```python
{
    "ese_scoring": "multi_metric",  # or "sigma_only"
    "ese_score_threshold": 5.5,    # Combined score threshold
    "ese_metric_weights": {
        "sigma_deviation": 1.0,
        "chi2_nu": 0.5,
        "eta_metric": 0.3
    }
}
```

#### Configurable Threshold Per Use Case

**Priority**: Low  
**Effort**: 1-2 hours

**Current State**:

- Fixed 5.0σ default threshold
- Can be overridden but not easily configured per use case

**Improvement**:

- Add threshold presets:
  - "conservative": 5.0σ (default, production)
  - "moderate": 4.0σ (balanced)
  - "sensitive": 3.0σ (initial screening)
  - "custom": user-specified value

**Implementation**:

```python
ESE_THRESHOLD_PRESETS = {
    "conservative": 5.0,
    "moderate": 4.0,
    "sensitive": 3.0,
}

def get_threshold(preset: str, custom: Optional[float] = None) -> float:
    """Get threshold value from preset or custom value."""
    if custom is not None:
        return custom
    return ESE_THRESHOLD_PRESETS.get(preset, 5.0)
```

### 3. Documentation Enhancements

#### Document Threshold Selection Guidelines

**Priority**: Low  
**Effort**: 1 hour

**Current State**:

- Threshold rationale mentioned but not detailed
- No guidance on when to use different thresholds

**Improvement**:

- Add section to user guide explaining:
  - When to use 3σ vs 5σ
  - False positive rate implications
  - Sensitivity vs specificity trade-offs
  - Examples of threshold selection

## Medium-Term Improvements (3-6 months)

### 4. Performance Optimizations

#### Caching Variability Statistics

**Priority**: Medium  
**Effort**: 2-3 days

**Current State**:

- Variability stats recomputed on every detection
- Database queries for every source

**Improvement**:

- Cache computed statistics in memory
- Invalidate cache when new photometry added
- Reduce database load for repeated queries

**Implementation**:

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1000)
def get_cached_variability_stats(
    source_id: str,
    cache_timestamp: float
) -> Optional[dict]:
    """Get cached variability stats if recent."""
    # Check cache age
    age = time.time() - cache_timestamp
    if age > 3600:  # 1 hour cache
        return None
    # Return cached value
    ...
```

#### Parallel Processing for Batch Operations

**Priority**: Medium  
**Effort**: 3-5 days

**Current State**:

- Sequential processing of sources
- No parallelization

**Improvement**:

- Use multiprocessing for batch operations
- Process multiple sources simultaneously
- Configurable worker pool size

**Implementation**:

```python
from multiprocessing import Pool

def process_sources_parallel(source_ids: List[str], n_workers: int = 4):
    """Process sources in parallel."""
    with Pool(n_workers) as pool:
        results = pool.map(update_variability_stats_for_source, source_ids)
    return results
```

### 5. Enhanced Monitoring & Alerting

#### Real-Time Alerting for High-Significance Candidates

**Priority**: Medium  
**Effort**: 2-3 days

**Current State**:

- Candidates logged but no alerts
- No integration with monitoring systems

**Improvement**:

- Alert on candidates above configurable threshold (e.g., 7.0σ)
- Integration with email/Slack/webhooks
- Rate limiting to prevent alert spam

**Configuration**:

```python
{
    "ese_alerting": {
        "enabled": True,
        "threshold": 7.0,  # Alert on 7σ+ candidates
        "channels": ["email", "slack"],
        "rate_limit": "1_per_hour_per_source"
    }
}
```

#### Detection Success/Failure Rate Tracking

**Priority**: Low  
**Effort**: 1-2 days

**Current State**:

- No tracking of detection performance
- No metrics on success/failure rates

**Improvement**:

- Track detection statistics:
  - Number of candidates detected
  - Average significance
  - Detection rate over time
  - False positive rate (if follow-up data available)

**Database Schema Addition**:

```sql
CREATE TABLE ese_detection_stats (
    date TEXT PRIMARY KEY,
    candidates_detected INTEGER,
    avg_significance REAL,
    max_significance REAL,
    sources_processed INTEGER
);
```

## Long-Term Enhancements (6+ months)

### 6. Multi-Frequency Analysis

**Priority**: High (when multi-frequency data available)  
**Effort**: 1-2 weeks

**Current State**:

- Single-frequency flux analysis only
- Cannot detect frequency-dependent ESE signatures

**Improvement**:

- Analyze variability across multiple frequencies
- Correlated frequency-dependent changes
- Enhanced detection confidence

**Requirements**:

- Multi-frequency photometry data
- Frequency metadata in database
- Cross-frequency correlation analysis

**Implementation**:

```python
def detect_ese_multi_frequency(
    source_id: str,
    frequencies: List[float]
) -> dict:
    """Detect ESE using multi-frequency analysis."""
    # Get flux measurements at each frequency
    flux_by_freq = get_flux_by_frequency(source_id, frequencies)

    # Check for correlated variability
    correlation = check_frequency_correlation(flux_by_freq)

    # Enhanced confidence if correlated
    if correlation > 0.7:
        confidence_boost = 1.5
    else:
        confidence_boost = 1.0

    return {
        "source_id": source_id,
        "correlation": correlation,
        "confidence_boost": confidence_boost
    }
```

### 7. Multi-Observable Correlation

**Priority**: High (when additional observables available)  
**Effort**: 1-2 weeks

**Current State**:

- Flux variability only
- No scintillation bandwidth or DM analysis

**Improvement**:

- Include scintillation bandwidth variations
- Include DM variations (for pulsars)
- Correlated multi-observable analysis

**Research Finding**: ESEs show correlated changes in:

- Flux density
- Scintillation bandwidth
- Dispersion measure (for pulsars)

**Implementation**:

```python
def detect_ese_multi_observable(
    source_id: str,
    flux_data: List[dict],
    scintillation_data: Optional[List[dict]] = None,
    dm_data: Optional[List[dict]] = None
) -> dict:
    """Detect ESE using multiple observables."""
    # Analyze flux variability
    flux_variability = analyze_flux_variability(flux_data)

    # Analyze scintillation if available
    scint_variability = None
    if scintillation_data:
        scint_variability = analyze_scintillation_variability(scintillation_data)

    # Analyze DM if available (pulsars)
    dm_variability = None
    if dm_data:
        dm_variability = analyze_dm_variability(dm_data)

    # Check for correlation
    correlation_score = calculate_correlation_score(
        flux_variability, scint_variability, dm_variability
    )

    # Enhanced confidence if multiple observables correlate
    return {
        "source_id": source_id,
        "flux_significance": flux_variability["significance"],
        "correlation_score": correlation_score,
        "multi_observable": scint_variability is not None or dm_variability is not None
    }
```

### 8. Advanced Analysis Features

#### Lightcurve Visualization

**Priority**: Low  
**Effort**: 3-5 days

**Current State**:

- No visualization tools
- Users must query database manually

**Improvement**:

- Generate lightcurve plots for ESE candidates
- Show variability metrics visually
- Export plots for reports

#### Candidate Ranking & Prioritization

**Priority**: Medium  
**Effort**: 2-3 days

**Current State**:

- Simple threshold-based detection
- No ranking or prioritization

**Improvement**:

- Rank candidates by:
  - Significance (sigma_deviation)
  - Multi-metric score
  - Observation count
  - Recency
- Prioritize for follow-up observations

#### Follow-Up Tracking

**Priority**: Low  
**Effort**: 2-3 days

**Current State**:

- No tracking of candidate follow-up
- No integration with observation scheduling

**Improvement**:

- Track candidate investigation status
- Schedule follow-up observations
- Link to observation planning system

## Implementation Priority Summary

### High Priority (Implement Soon)

1. ✅ Extract shared sigma deviation function
2. ✅ Add validation tests
3. Multi-metric scoring system

### Medium Priority (Next Quarter)

4. Caching variability statistics
5. Parallel processing
6. Real-time alerting

### Low Priority (Future)

7. Multi-frequency analysis (when data available)
8. Multi-observable correlation (when data available)
9. Lightcurve visualization
10. Follow-up tracking

## Notes

- All improvements are optional enhancements
- Current implementation is production-ready
- Improvements should be prioritized based on:
  - User needs
  - Data availability
  - Resource constraints
  - Scientific priorities

## Related Documentation

- [ESE Detection Critical Review](ese_detection_critical_review.md)
- [ESE Detection Research Findings](ese_detection_research_findings.md)
- [ESE Detection Architecture](../../concepts/ese_detection_architecture.md)
