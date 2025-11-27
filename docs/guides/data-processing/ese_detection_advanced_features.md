# ESE Detection Advanced Features

This guide covers the advanced features available for ESE (Extreme Scattering
Event) detection, including multi-metric scoring, threshold presets, caching,
parallel processing, and multi-frequency/multi-observable analysis.

## Table of Contents

1. [Threshold Presets](#threshold-presets)
2. [Multi-Metric Composite Scoring](#multi-metric-composite-scoring)
3. [Caching](#caching)
4. [Parallel Processing](#parallel-processing)
5. [Multi-Frequency Analysis](#multi-frequency-analysis)
6. [Multi-Observable Correlation](#multi-observable-correlation)

## Threshold Presets

Instead of manually specifying `min_sigma` values, you can use predefined
threshold presets:

### Available Presets

- **conservative** (min_sigma=5.0): High confidence, fewer false positives
- **moderate** (min_sigma=3.5): Balanced detection
- **sensitive** (min_sigma=3.0): More candidates, may include false positives

### Usage

**CLI:**

```bash
photometry ese-detect --preset moderate
```

**API:**

```json
{
  "params": {
    "preset": "moderate"
  }
}
```

**Python:**

```python
from dsa110_contimg.photometry.thresholds import get_threshold_preset

thresholds = get_threshold_preset("moderate")
min_sigma = thresholds["min_sigma"]  # 3.5
```

## Multi-Metric Composite Scoring

Composite scoring combines multiple variability metrics (sigma_deviation,
chi2_nu, eta_metric) into a single confidence score.

### Benefits

- More robust detection by considering multiple indicators
- Confidence levels: "high", "medium", "low"
- Customizable weights for different metrics

### Usage

**CLI:**

```bash
photometry ese-detect --use-composite-scoring
```

**API:**

```json
{
  "params": {
    "min_sigma": 5.0,
    "use_composite_scoring": true,
    "scoring_weights": {
      "sigma_deviation": 0.5,
      "chi2_nu": 0.3,
      "eta_metric": 0.2
    }
  }
}
```

**Python:**

```python
from dsa110_contimg.photometry.ese_detection import detect_ese_candidates

candidates = detect_ese_candidates(
    products_db=products_db,
    min_sigma=5.0,
    use_composite_scoring=True,
    scoring_weights={"sigma_deviation": 0.5, "chi2_nu": 0.3}
)

for candidate in candidates:
    print(f"{candidate['source_id']}: score={candidate.get('composite_score')}, "
          f"confidence={candidate.get('confidence_level')}")
```

### Confidence Levels

- **high**: composite_score >= 7.0
- **medium**: 4.0 <= composite_score < 7.0
- **low**: composite_score < 4.0

## Caching

Variability statistics are cached to improve performance for frequently accessed
sources.

### Features

- Automatic cache invalidation when stats are updated
- Configurable TTL (time-to-live)
- Cache statistics tracking (hits, misses, expired)

### Usage

**Python:**

```python
from dsa110_contimg.photometry.caching import (
    get_cached_variability_stats,
    invalidate_cache,
    CacheStats
)

# Get cached stats (or fetch from DB if not cached)
stats = get_cached_variability_stats(
    source_id="J120000+450000",
    products_db=products_db,
    ttl_seconds=3600  # 1 hour
)

# Invalidate cache when stats change
invalidate_cache("J120000+450000")

# Check cache performance
print(f"Cache hits: {CacheStats.hits}, misses: {CacheStats.misses}")
```

## Parallel Processing

Process multiple sources in parallel for faster batch detection.

### Usage

**API:**

```json
{
  "params": {
    "source_ids": ["J120000+450000", "J120001+450001", "J120002+450002"],
    "use_parallel": true,
    "min_sigma": 5.0
  }
}
```

**Python:**

```python
from dsa110_contimg.photometry.parallel import detect_ese_parallel

candidates = detect_ese_parallel(
    source_ids=["J120000+450000", "J120001+450001"],
    products_db=products_db,
    min_sigma=5.0,
    num_workers=4  # Optional: specify worker count
)
```

### Performance

- Automatically determines optimal worker count based on CPU cores
- Significant speedup for large batches (>10 sources)
- Thread-safe database access

## Multi-Frequency Analysis

Detect ESEs by correlating variability across different observing frequencies.

### Usage

**Python:**

```python
from dsa110_contimg.photometry.multi_frequency import (
    analyze_frequency_correlation,
    detect_ese_multi_frequency
)

# Analyze correlation across frequencies
result = analyze_frequency_correlation(
    source_id_base="J120000+450000",
    frequencies_mhz=[1400, 2000, 3000],
    products_db=products_db,
    min_sigma_threshold=3.0
)

print(f"Correlation strength: {result['strength']}")
print(f"Is correlated: {result['is_correlated']}")

# Detect ESE using multi-frequency analysis
candidates = detect_ese_multi_frequency(
    source_id_base="J120000+450000",
    frequencies_mhz=[1400, 2000, 3000],
    products_db=products_db
)
```

## Multi-Observable Correlation

Correlate ESE detection with other observables (scintillation, DM variations).

### Usage

**Python:**

```python
from dsa110_contimg.photometry.multi_observable import (
    analyze_scintillation_variability,
    analyze_dm_variability,
    detect_ese_multi_observable
)

# Analyze scintillation variability
scint_result = analyze_scintillation_variability(
    source_id="J120000+450000",
    products_db=products_db
)

# Analyze DM variability
dm_result = analyze_dm_variability(
    source_id="J120000+450000",
    products_db=products_db
)

# Detect ESE with multi-observable correlation
candidates = detect_ese_multi_observable(
    source_id="J120000+450000",
    products_db=products_db
)
```

## Combining Features

You can combine multiple features for optimal detection:

**API Example:**

```json
{
  "params": {
    "preset": "moderate",
    "use_composite_scoring": true,
    "use_parallel": true,
    "source_ids": ["J120000+450000", "J120001+450001"]
  }
}
```

**CLI Example:**

```bash
photometry ese-detect --preset moderate --use-composite-scoring
```

## Performance Considerations

- **Caching**: Reduces database queries by ~50-80% for frequently accessed
  sources
- **Parallel Processing**: 2-4x speedup for batches with >10 sources
- **Composite Scoring**: Adds ~10-20% overhead but improves detection quality
- **Multi-frequency/Multi-observable**: Adds significant overhead, use
  selectively

## Best Practices

1. Use **threshold presets** for consistent detection across projects
2. Enable **composite scoring** for production pipelines to improve confidence
3. Use **caching** for frequently accessed sources (default enabled)
4. Enable **parallel processing** for batch jobs with >10 sources
5. Use **multi-frequency/multi-observable** analysis for high-priority
   candidates only

## Related Documentation

- [ESE Detection Architecture](../../architecture/science/ese_detection_architecture.md)
- ESE Detection CLI Reference
- ESE Detection API Reference
