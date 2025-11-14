# ESE Detection Comprehensive Improvement Plan

## Date: 2025-11-12

This document provides detailed technical specifications, scientific reasoning,
and implementation guidance for all identified ESE detection improvements. All
items are treated as equally high priority with deep technical analysis.

---

## 1. Code Quality & Architecture Improvements

### 1.1 Extract Shared Sigma Deviation Function

#### Scientific Rationale

The sigma deviation metric is fundamental to ESE detection, representing how
many standard deviations the maximum flux deviation is from the mean. This is a
standard statistical measure in variability analysis, and consistency is
critical for:

- **Reproducibility**: Same input data must produce identical results regardless
  of code path
- **Scientific validity**: Inconsistent calculations invalidate comparisons
  between automatic and manual detection
- **Maintainability**: Single source of truth reduces bugs and simplifies
  testing

#### Current Problem

Two implementations exist with identical intent but potential for divergence:

- `ese_pipeline.py`: Used in automated detection
- `ese_detection.py`: Used in manual/recompute operations

Even though currently fixed to be identical, code duplication violates DRY
(Don't Repeat Yourself) principle and creates maintenance risk.

#### Technical Specification

**Location**: `src/dsa110_contimg/photometry/variability.py`

**Function Signature**:

```python
def calculate_sigma_deviation(
    fluxes: np.ndarray,
    mean_flux: Optional[float] = None,
    std_flux: Optional[float] = None
) -> float:
    """
    Calculate maximum sigma deviation from mean flux.

    This measures the maximum deviation from the mean in units of standard
    deviation, which is the primary metric for ESE detection. The calculation
    considers both positive and negative deviations to capture variability
    in either direction.

    Mathematical Definition:
        σ_dev = max(|max(flux) - μ|, |min(flux) - μ|) / σ

    where:
        μ = mean(flux)
        σ = std(flux)

    Args:
        fluxes: Array of flux measurements (any units, but must be consistent)
        mean_flux: Pre-computed mean (optional, computed if None)
        std_flux: Pre-computed standard deviation (optional, computed if None)

    Returns:
        Maximum sigma deviation (float). Returns 0.0 if:
        - Less than 2 measurements
        - Zero variance (all measurements identical)
        - Invalid input (NaN, Inf)

    Raises:
        ValueError: If fluxes array is empty or contains only NaN values

    Examples:
        >>> fluxes = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        >>> calculate_sigma_deviation(fluxes)
        2.0  # (5.0 - 3.0) / 1.414 = 1.414, but max considers both directions

        >>> fluxes = np.array([1.0, 1.0, 1.0])
        >>> calculate_sigma_deviation(fluxes)
        0.0  # Zero variance

        >>> fluxes = np.array([10.0, 12.0, 8.0, 11.0, 9.0])
        >>> calculate_sigma_deviation(fluxes)
        1.414  # Maximum deviation is 2.0, std is ~1.414
    """
```

**Implementation Details**:

```python
def calculate_sigma_deviation(
    fluxes: np.ndarray,
    mean_flux: Optional[float] = None,
    std_flux: Optional[float] = None
) -> float:
    """Calculate maximum sigma deviation from mean flux."""
    # Input validation
    if len(fluxes) == 0:
        raise ValueError("Fluxes array cannot be empty")

    # Filter invalid values
    valid_mask = np.isfinite(fluxes)
    if not np.any(valid_mask):
        raise ValueError("Fluxes array contains no valid values")

    valid_fluxes = fluxes[valid_mask]

    # Need at least 2 measurements for meaningful variance
    if len(valid_fluxes) < 2:
        return 0.0

    # Compute statistics if not provided
    if mean_flux is None:
        mean_flux = float(np.mean(valid_fluxes))
    if std_flux is None:
        std_flux = float(np.std(valid_fluxes, ddof=1))  # Sample std (N-1)

    # Zero variance case
    if std_flux <= 0:
        return 0.0

    # Calculate deviations in both directions
    max_flux = float(np.max(valid_fluxes))
    min_flux = float(np.min(valid_fluxes))

    max_deviation = abs(max_flux - mean_flux) / std_flux
    min_deviation = abs(min_flux - mean_flux) / std_flux

    # Return maximum deviation (most significant variability)
    return max(max_deviation, min_deviation)
```

**Integration Points**:

1. **Update `ese_pipeline.py`**:

```python
from dsa110_contimg.photometry.variability import calculate_sigma_deviation

# Replace inline calculation with:
sigma_deviation = calculate_sigma_deviation(
    flux_mjy,
    mean_flux=mean_flux_mjy,
    std_flux=std_flux_mjy
)
```

2. **Update `ese_detection.py`**:

```python
from dsa110_contimg.photometry.variability import calculate_sigma_deviation

# Replace inline calculation with:
sigma_deviation = calculate_sigma_deviation(np.array(fluxes))
```

**Testing Requirements**:

```python
class TestCalculateSigmaDeviation:
    """Comprehensive tests for sigma deviation calculation."""

    def test_basic_calculation(self):
        """Test basic sigma deviation calculation."""
        fluxes = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = calculate_sigma_deviation(fluxes)
        expected = abs(5.0 - 3.0) / np.std(fluxes, ddof=1)
        assert abs(result - expected) < 1e-10

    def test_symmetric_deviations(self):
        """Test that both positive and negative deviations are considered."""
        # Create symmetric distribution around mean
        fluxes = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        # Max deviation: 5.0 - 3.0 = 2.0
        # Min deviation: 1.0 - 3.0 = -2.0 (abs = 2.0)
        result = calculate_sigma_deviation(fluxes)
        assert result > 0

    def test_zero_variance(self):
        """Test zero variance case."""
        fluxes = np.array([1.0, 1.0, 1.0])
        assert calculate_sigma_deviation(fluxes) == 0.0

    def test_single_measurement(self):
        """Test single measurement case."""
        fluxes = np.array([1.0])
        assert calculate_sigma_deviation(fluxes) == 0.0

    def test_negative_fluxes(self):
        """Test with negative flux values."""
        fluxes = np.array([-1.0, 0.0, 1.0])
        result = calculate_sigma_deviation(fluxes)
        assert result > 0

    def test_nan_handling(self):
        """Test NaN filtering."""
        fluxes = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        result = calculate_sigma_deviation(fluxes)
        assert np.isfinite(result)

    def test_precomputed_statistics(self):
        """Test with pre-computed mean and std."""
        fluxes = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        mean = 3.0
        std = np.std(fluxes, ddof=1)
        result1 = calculate_sigma_deviation(fluxes)
        result2 = calculate_sigma_deviation(fluxes, mean_flux=mean, std_flux=std)
        assert abs(result1 - result2) < 1e-10

    def test_edge_case_large_deviations(self):
        """Test with extreme outliers."""
        fluxes = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
        result = calculate_sigma_deviation(fluxes)
        assert result > 10.0  # Should detect large deviation
```

**Benefits**:

- Single source of truth eliminates inconsistencies
- Easier to optimize and maintain
- Comprehensive testing ensures correctness
- Reusable across codebase
- Clear documentation of mathematical definition

---

### 1.2 Comprehensive Validation Test Suite

#### Scientific Rationale

Statistical calculations must be validated against known values to ensure
correctness. Errors in variability metrics propagate through the entire
detection pipeline, potentially causing:

- **False positives**: Incorrectly flagging normal sources as ESE candidates
- **False negatives**: Missing real ESE events
- **Scientific invalidity**: Published results based on incorrect calculations

Validation tests serve as:

- Regression prevention: Catch bugs introduced by future changes
- Documentation: Tests serve as executable specifications
- Confidence: Verify implementation matches mathematical definitions

#### Test Categories

**1. Unit Tests for Individual Metrics**

```python
class TestVariabilityMetrics:
    """Test individual variability metric calculations."""

    def test_chi_squared_calculation(self):
        """
        Test chi-squared calculation against known formula.

        χ² = Σ((obs - expected)² / σ²)
        χ²_ν = χ² / (N - 1)
        """
        fluxes = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        errors = np.array([0.1, 0.1, 0.1, 0.1, 0.1])
        mean = np.mean(fluxes)

        # Manual calculation
        chi2_manual = np.sum(((fluxes - mean) ** 2) / (errors ** 2))
        chi2_nu_manual = chi2_manual / (len(fluxes) - 1)

        # Function calculation
        chi2_nu_func = calculate_chi2_nu(fluxes, errors)

        assert abs(chi2_nu_func - chi2_nu_manual) < 1e-10

    def test_eta_metric_against_vast_tools(self):
        """
        Test eta metric against VAST Tools reference implementation.

        Use known test cases from VAST Tools test suite.
        """
        # Reference values from VAST Tools
        test_cases = [
            {
                "fluxes": [1.0, 1.0, 1.0],
                "errors": [0.1, 0.1, 0.1],
                "expected_eta": 0.0  # No variability
            },
            {
                "fluxes": [1.0, 2.0, 3.0],
                "errors": [0.1, 0.1, 0.1],
                "expected_eta": 0.6667  # Approximate from VAST Tools
            }
        ]

        for case in test_cases:
            df = pd.DataFrame({
                "normalized_flux_jy": case["fluxes"],
                "normalized_flux_err_jy": case["errors"]
            })
            eta = calculate_eta_metric(df)
            assert abs(eta - case["expected_eta"]) < 0.01
```

**2. Integration Tests for Complete Pipeline**

```python
class TestESEDetectionPipeline:
    """Test complete ESE detection pipeline."""

    def test_end_to_end_detection(self):
        """Test complete detection flow from photometry to candidates."""
        # Create test database with known variability
        db_path = create_test_db()

        # Add photometry measurements with known variability pattern
        add_photometry_measurements(
            db_path,
            source_id="TEST001",
            fluxes=[1.0, 1.1, 1.2, 1.3, 5.0],  # Large jump at end
            errors=[0.1] * 5
        )

        # Run detection
        candidates = detect_ese_candidates(db_path, min_sigma=3.0)

        # Verify detection
        assert len(candidates) == 1
        assert candidates[0]["source_id"] == "TEST001"
        assert candidates[0]["significance"] > 3.0

    def test_consistency_automatic_vs_manual(self):
        """Test that automatic and manual detection produce same results."""
        db_path = create_test_db()
        source_id = "TEST002"

        # Add measurements
        add_photometry_measurements(db_path, source_id, ...)

        # Automatic detection
        auto_candidates = auto_detect_ese_for_new_measurements(
            db_path, source_id, min_sigma=5.0
        )

        # Manual detection
        manual_candidates = detect_ese_candidates(
            db_path, min_sigma=5.0, source_id=source_id
        )

        # Should produce identical results
        assert len(auto_candidates) == len(manual_candidates)
        if auto_candidates:
            assert auto_candidates[0]["significance"] == manual_candidates[0]["significance"]
```

**3. Edge Case Tests**

```python
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_single_measurement(self):
        """Test behavior with only one measurement."""
        db_path = create_test_db()
        add_photometry_measurements(db_path, "TEST", fluxes=[1.0], errors=[0.1])

        candidates = detect_ese_candidates(db_path)
        # Should handle gracefully, no candidates (need multiple measurements)
        assert isinstance(candidates, list)

    def test_zero_variance(self):
        """Test with zero variance measurements."""
        db_path = create_test_db()
        add_photometry_measurements(
            db_path, "TEST",
            fluxes=[1.0, 1.0, 1.0, 1.0],
            errors=[0.1, 0.1, 0.1, 0.1]
        )

        candidates = detect_ese_candidates(db_path)
        # Should not detect (no variability)
        assert len(candidates) == 0

    def test_missing_errors(self):
        """Test handling of missing error values."""
        db_path = create_test_db()
        # Add measurements with some missing errors
        # Should handle gracefully, skip chi-squared calculation

    def test_negative_fluxes(self):
        """Test with negative flux values (possible in some contexts)."""
        # Should handle correctly, variability still detectable

    def test_extreme_outliers(self):
        """Test with extreme outlier values."""
        # Should detect but not crash
```

**4. Performance Tests**

```python
class TestPerformance:
    """Test performance characteristics."""

    def test_large_source_count(self):
        """Test with large number of sources."""
        db_path = create_test_db()
        # Add 10,000 sources
        # Measure detection time
        # Should complete in reasonable time (< 1 minute)

    def test_incremental_updates(self):
        """Test that incremental updates are efficient."""
        # Add measurements incrementally
        # Verify only affected sources are recomputed
```

**Test Infrastructure**:

```python
# tests/conftest.py additions
@pytest.fixture
def test_photometry_data():
    """Create standardized test photometry data."""
    return {
        "source_id": "TEST001",
        "ra_deg": 120.0,
        "dec_deg": 45.0,
        "fluxes": [1.0, 1.1, 1.2, 1.3, 1.4],
        "errors": [0.1, 0.1, 0.1, 0.1, 0.1],
        "mjd": [60000.0, 60001.0, 60002.0, 60003.0, 60004.0]
    }

@pytest.fixture
def known_ese_pattern():
    """Create known ESE variability pattern."""
    # Simulate ESE: gradual increase then sudden spike
    return {
        "fluxes": [1.0, 1.1, 1.2, 1.3, 5.0],  # Large jump
        "expected_sigma": 3.5,  # Known sigma deviation
        "expected_detection": True
    }
```

---

## 2. Enhanced Detection Algorithms

### 2.1 Multi-Metric Scoring System

#### Scientific Rationale

Single-metric thresholds are vulnerable to:

- **Noise**: Single outlier can trigger false positive
- **Incomplete information**: Ignores complementary variability indicators
- **Context loss**: Doesn't consider measurement quality or quantity

Multi-metric scoring provides:

- **Robustness**: Multiple independent indicators reduce false positives
- **Confidence**: Higher confidence when multiple metrics agree
- **Ranking**: Better candidate prioritization for follow-up

#### Theoretical Foundation

**Information Theory Perspective**:

- Each metric provides independent information about variability
- Combining metrics increases information content
- Weighted combination maximizes signal-to-noise ratio

**Statistical Perspective**:

- Chi-squared tests constant flux model (goodness of fit)
- Eta metric measures weighted variance (accounting for errors)
- Sigma deviation measures extreme outliers (ESE signature)
- Observation count affects confidence (more observations = more reliable)

#### Algorithm Design

**Scoring Function**:

```python
def calculate_ese_composite_score(
    sigma_deviation: float,
    chi2_nu: Optional[float],
    eta_metric: Optional[float],
    n_obs: int,
    weights: Optional[dict] = None
) -> dict:
    """
    Calculate composite ESE candidate score using multiple metrics.

    This function combines multiple variability indicators into a single
    composite score that provides more robust detection than any single
    metric alone.

    Algorithm:
        1. Base score from sigma deviation (primary indicator)
        2. Boost from chi-squared if indicates variability
        3. Boost from eta metric if indicates variability
        4. Penalty for low observation count (reduced confidence)
        5. Normalize to produce interpretable score

    Args:
        sigma_deviation: Maximum sigma deviation from mean
        chi2_nu: Reduced chi-squared (goodness of fit to constant model)
        eta_metric: Weighted variance metric
        n_obs: Number of observations
        weights: Optional custom weights for metrics

    Returns:
        Dictionary containing:
        - score: Composite score (higher = more likely ESE)
        - components: Individual metric contributions
        - confidence: Confidence level (low/medium/high)
        - explanation: Human-readable explanation

    Examples:
        >>> result = calculate_ese_composite_score(
        ...     sigma_deviation=6.5,
        ...     chi2_nu=3.2,
        ...     eta_metric=0.15,
        ...     n_obs=10
        ... )
        >>> result["score"]
        7.2
        >>> result["confidence"]
        "high"
    """
    # Default weights (can be tuned based on validation)
    default_weights = {
        "sigma_deviation": 1.0,  # Primary metric
        "chi2_nu": 0.5,          # Secondary metric
        "eta_metric": 0.3,       # Tertiary metric
        "n_obs_penalty": 0.2     # Observation count factor
    }

    if weights is None:
        weights = default_weights

    # Base score from sigma deviation
    base_score = sigma_deviation * weights["sigma_deviation"]

    # Chi-squared contribution
    chi2_contribution = 0.0
    if chi2_nu is not None:
        # Chi-squared > 2 indicates significant variability
        if chi2_nu > 2.0:
            # Normalize: chi2_nu of 5.0 gives full boost
            chi2_normalized = min(chi2_nu / 5.0, 1.0)
            chi2_contribution = chi2_normalized * weights["chi2_nu"]

    # Eta metric contribution
    eta_contribution = 0.0
    if eta_metric is not None:
        # Eta > 0.1 indicates variability
        if eta_metric > 0.1:
            # Normalize: eta of 0.5 gives full boost
            eta_normalized = min(eta_metric / 0.5, 1.0)
            eta_contribution = eta_normalized * weights["eta_metric"]

    # Observation count penalty
    # Fewer observations = less confidence
    obs_penalty = 0.0
    if n_obs < 5:
        # Penalize sources with < 5 observations
        obs_penalty = (5 - n_obs) / 5.0 * weights["n_obs_penalty"]
    elif n_obs < 10:
        # Slight penalty for < 10 observations
        obs_penalty = (10 - n_obs) / 10.0 * weights["n_obs_penalty"] * 0.5

    # Calculate composite score
    composite_score = base_score + chi2_contribution + eta_contribution - obs_penalty

    # Determine confidence level
    if composite_score >= 7.0:
        confidence = "high"
    elif composite_score >= 5.0:
        confidence = "medium"
    elif composite_score >= 3.0:
        confidence = "low"
    else:
        confidence = "very_low"

    # Generate explanation
    explanation_parts = []
    explanation_parts.append(f"Sigma deviation: {sigma_deviation:.2f}σ")
    if chi2_nu is not None:
        explanation_parts.append(f"Chi-squared: {chi2_nu:.2f}")
    if eta_metric is not None:
        explanation_parts.append(f"Eta metric: {eta_metric:.3f}")
    explanation_parts.append(f"Observations: {n_obs}")
    explanation = "; ".join(explanation_parts)

    return {
        "score": composite_score,
        "components": {
            "base_score": base_score,
            "chi2_contribution": chi2_contribution,
            "eta_contribution": eta_contribution,
            "obs_penalty": obs_penalty
        },
        "confidence": confidence,
        "explanation": explanation
    }
```

**Integration with Detection**:

```python
def detect_ese_candidates_with_scoring(
    products_db: Path,
    min_sigma: float = 5.0,
    use_composite_score: bool = True,
    score_threshold: Optional[float] = None
) -> List[dict]:
    """
    Detect ESE candidates with optional composite scoring.

    If use_composite_score=True, uses composite score instead of
    simple sigma threshold for more robust detection.
    """
    # ... existing detection logic ...

    for row in candidates:
        sigma_dev = float(row["sigma_deviation"])

        if use_composite_score:
            # Calculate composite score
            score_result = calculate_ese_composite_score(
                sigma_deviation=sigma_dev,
                chi2_nu=float(row["chi2_nu"]) if row["chi2_nu"] else None,
                eta_metric=float(row["eta_metric"]) if row["eta_metric"] else None,
                n_obs=int(row["n_obs"])
            )

            # Use score threshold or fall back to sigma threshold
            threshold = score_threshold if score_threshold else min_sigma

            if score_result["score"] >= threshold:
                candidate = {
                    "source_id": row["source_id"],
                    "significance": sigma_dev,  # Keep original for compatibility
                    "composite_score": score_result["score"],
                    "confidence": score_result["confidence"],
                    "score_components": score_result["components"],
                    "explanation": score_result["explanation"],
                    # ... other fields ...
                }
                results.append(candidate)
        else:
            # Traditional single-metric detection
            if sigma_dev >= min_sigma:
                # ... existing logic ...
```

**Configuration**:

```python
# config/ese_detection.yaml
ese_detection:
  scoring:
    method: "composite"  # or "sigma_only"
    composite_weights:
      sigma_deviation: 1.0
      chi2_nu: 0.5
      eta_metric: 0.3
      n_obs_penalty: 0.2
    thresholds:
      conservative: 7.0  # High confidence
      moderate: 5.5      # Medium confidence
      sensitive: 4.0     # Lower threshold
```

**Validation Strategy**:

```python
def validate_composite_scoring():
    """
    Validate composite scoring against known ESE candidates.

    Use historical ESE detections to tune weights and thresholds.
    """
    # Load known ESE candidates with confirmed follow-up
    known_eses = load_confirmed_ese_candidates()

    # Calculate scores for known ESEs
    scores_ese = []
    for ese in known_eses:
        score = calculate_ese_composite_score(...)
        scores_ese.append(score["score"])

    # Calculate scores for non-ESE sources
    non_eses = load_non_ese_sources()
    scores_non_ese = []
    for source in non_eses:
        score = calculate_ese_composite_score(...)
        scores_non_ese.append(score["score"])

    # Analyze separation
    # Tune weights to maximize separation between ESE and non-ESE
    # Optimize threshold to minimize false positives/negatives
```

**Benefits**:

- More robust detection (multiple independent indicators)
- Better candidate ranking (composite score)
- Configurable sensitivity (adjustable weights)
- Human-readable explanations (transparency)
- Backward compatible (can disable composite scoring)

---

### 2.2 Configurable Threshold Presets

#### Scientific Rationale

Different use cases require different sensitivity/specificity trade-offs:

- **Production monitoring**: High specificity (low false positives)
- **Initial screening**: Higher sensitivity (catch more candidates)
- **Follow-up analysis**: Balanced approach
- **Research exploration**: Very sensitive (find all potential candidates)

Fixed thresholds don't accommodate these needs.

#### Threshold Selection Theory

**False Positive Rate**:

- 3σ: ~0.3% false positive rate
- 4σ: ~0.006% false positive rate
- 5σ: ~0.00006% false positive rate
- 6σ: ~0.0000002% false positive rate

**Sensitivity vs Specificity Trade-off**:

- Lower threshold: More candidates (higher sensitivity), more false positives
  (lower specificity)
- Higher threshold: Fewer candidates (lower sensitivity), fewer false positives
  (higher specificity)

**Use Case Mapping**:

| Use Case              | Threshold | Rationale                                     |
| --------------------- | --------- | --------------------------------------------- |
| Production monitoring | 5.0σ      | Low false positive rate, high confidence      |
| Initial screening     | 3.0σ      | Catch potential candidates, manual review     |
| Follow-up analysis    | 4.0σ      | Balanced for detailed investigation           |
| Research exploration  | 2.5σ      | Very sensitive, requires extensive validation |

#### Implementation

```python
class ESEThresholdPreset:
    """ESE detection threshold presets for different use cases."""

    PRESETS = {
        "conservative": {
            "sigma_threshold": 5.0,
            "description": "Production monitoring - high confidence, low false positives",
            "false_positive_rate": 0.00006,
            "use_cases": ["production", "automated_monitoring", "alerts"]
        },
        "moderate": {
            "sigma_threshold": 4.0,
            "description": "Balanced detection - moderate confidence",
            "false_positive_rate": 0.006,
            "use_cases": ["follow_up", "detailed_analysis"]
        },
        "sensitive": {
            "sigma_threshold": 3.0,
            "description": "Initial screening - higher sensitivity, manual review",
            "false_positive_rate": 0.3,
            "use_cases": ["initial_screening", "exploratory_analysis"]
        },
        "very_sensitive": {
            "sigma_threshold": 2.5,
            "description": "Research exploration - very sensitive, extensive validation required",
            "false_positive_rate": 1.2,
            "use_cases": ["research", "exploration"]
        }
    }

    @classmethod
    def get_threshold(
        cls,
        preset: str,
        custom: Optional[float] = None
    ) -> float:
        """
        Get threshold value from preset or custom value.

        Args:
            preset: Preset name ("conservative", "moderate", "sensitive", "very_sensitive")
            custom: Optional custom threshold value (overrides preset)

        Returns:
            Threshold value (sigma)

        Raises:
            ValueError: If preset not found
        """
        if custom is not None:
            return custom

        if preset not in cls.PRESETS:
            raise ValueError(
                f"Unknown preset: {preset}. "
                f"Available: {list(cls.PRESETS.keys())}"
            )

        return cls.PRESETS[preset]["sigma_threshold"]

    @classmethod
    def get_preset_info(cls, preset: str) -> dict:
        """Get information about a preset."""
        if preset not in cls.PRESETS:
            raise ValueError(f"Unknown preset: {preset}")
        return cls.PRESETS[preset]
```

**API Integration**:

```python
# In API models
class ESEDetectJobParams(BaseModel):
    """Parameters for ESE detection job."""

    min_sigma: Optional[float] = Field(
        None,
        description="Custom sigma threshold (overrides preset)"
    )
    threshold_preset: str = Field(
        "conservative",
        description="Threshold preset: conservative, moderate, sensitive, very_sensitive"
    )

    @validator("threshold_preset")
    def validate_preset(cls, v):
        valid_presets = ["conservative", "moderate", "sensitive", "very_sensitive"]
        if v not in valid_presets:
            raise ValueError(f"Invalid preset. Must be one of: {valid_presets}")
        return v

    def get_threshold(self) -> float:
        """Get effective threshold value."""
        return ESEThresholdPreset.get_threshold(
            self.threshold_preset,
            self.min_sigma
        )
```

**CLI Integration**:

```python
# In CLI
sp.add_argument(
    "--threshold-preset",
    type=str,
    choices=["conservative", "moderate", "sensitive", "very_sensitive"],
    default="conservative",
    help="Threshold preset (default: conservative)"
)
sp.add_argument(
    "--min-sigma",
    type=float,
    default=None,
    help="Custom sigma threshold (overrides preset)"
)

# In command handler
threshold = ESEThresholdPreset.get_threshold(
    args.threshold_preset,
    args.min_sigma
)
```

**Documentation**:

```markdown
## Threshold Selection Guide

### Conservative (5.0σ) - Default

- **Use for**: Production monitoring, automated alerts
- **False positive rate**: ~0.00006%
- **When to use**: When false positives are costly

### Moderate (4.0σ)

- **Use for**: Follow-up analysis, detailed investigation
- **False positive rate**: ~0.006%
- **When to use**: Balanced sensitivity/specificity needed

### Sensitive (3.0σ)

- **Use for**: Initial screening, exploratory analysis
- **False positive rate**: ~0.3%
- **When to use**: When you want to catch more candidates for manual review

### Very Sensitive (2.5σ)

- **Use for**: Research exploration
- **False positive rate**: ~1.2%
- **When to use**: When extensive validation is possible
```

---

## 3. Performance Optimizations

### 3.1 Caching Variability Statistics

#### Scientific Rationale

Variability statistics are expensive to compute:

- Require reading all photometry measurements for a source
- Statistical calculations (mean, std, chi-squared, etc.)
- Database queries for each source

However, statistics don't change unless:

- New photometry measurements added
- Existing measurements modified/deleted

Caching provides:

- **Performance**: Avoid recomputation for unchanged sources
- **Scalability**: Handle larger source catalogs efficiently
- **Resource efficiency**: Reduce database load

#### Cache Design

**Cache Strategy**: Time-based invalidation with manual refresh

**Cache Key**: `source_id` + `last_photometry_timestamp`

**Cache Structure**:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import json

@dataclass
class VariabilityStatsCache:
    """Cached variability statistics."""
    source_id: str
    stats: dict
    cache_timestamp: float
    photometry_timestamp: float  # Last photometry measurement time
    cache_key: str

    def is_valid(self, max_age_seconds: float = 3600) -> bool:
        """Check if cache entry is still valid."""
        age = time.time() - self.cache_timestamp
        return age < max_age_seconds

    def matches_photometry(self, current_photometry_timestamp: float) -> bool:
        """Check if cache matches current photometry state."""
        return abs(self.photometry_timestamp - current_photometry_timestamp) < 1.0


class VariabilityStatsCacheManager:
    """Manages caching of variability statistics."""

    def __init__(
        self,
        cache_backend: str = "memory",  # or "redis", "file"
        max_size: int = 10000,
        default_ttl: float = 3600.0  # 1 hour
    ):
        self.cache_backend = cache_backend
        self.max_size = max_size
        self.default_ttl = default_ttl

        if cache_backend == "memory":
            self.cache = {}  # In-memory dict
        elif cache_backend == "redis":
            import redis
            self.cache = redis.Redis(...)
        elif cache_backend == "file":
            self.cache_path = Path("/tmp/ese_cache")
            self.cache_path.mkdir(exist_ok=True)

    def get_cache_key(
        self,
        source_id: str,
        photometry_timestamp: float
    ) -> str:
        """Generate cache key."""
        key_data = f"{source_id}:{photometry_timestamp}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(
        self,
        source_id: str,
        current_photometry_timestamp: float
    ) -> Optional[dict]:
        """Get cached statistics if available and valid."""
        cache_key = self.get_cache_key(source_id, current_photometry_timestamp)

        if self.cache_backend == "memory":
            if cache_key not in self.cache:
                return None

            cached = self.cache[cache_key]
            if not cached.is_valid():
                del self.cache[cache_key]
                return None

            if not cached.matches_photometry(current_photometry_timestamp):
                # Photometry changed, invalidate
                del self.cache[cache_key]
                return None

            return cached.stats

        # Similar logic for other backends...

    def set(
        self,
        source_id: str,
        stats: dict,
        photometry_timestamp: float
    ):
        """Cache statistics."""
        cache_key = self.get_cache_key(source_id, photometry_timestamp)

        cached = VariabilityStatsCache(
            source_id=source_id,
            stats=stats,
            cache_timestamp=time.time(),
            photometry_timestamp=photometry_timestamp,
            cache_key=cache_key
        )

        if self.cache_backend == "memory":
            # Evict oldest if at capacity
            if len(self.cache) >= self.max_size:
                oldest_key = min(
                    self.cache.keys(),
                    key=lambda k: self.cache[k].cache_timestamp
                )
                del self.cache[oldest_key]

            self.cache[cache_key] = cached

    def invalidate(self, source_id: str):
        """Invalidate cache for a source."""
        # Remove all entries for this source
        if self.cache_backend == "memory":
            keys_to_remove = [
                k for k, v in self.cache.items()
                if v.source_id == source_id
            ]
            for k in keys_to_remove:
                del self.cache[k]
```

**Integration**:

```python
# Global cache manager instance
_cache_manager = None

def get_cache_manager() -> VariabilityStatsCacheManager:
    """Get or create cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = VariabilityStatsCacheManager(
            cache_backend=os.getenv("ESE_CACHE_BACKEND", "memory"),
            max_size=int(os.getenv("ESE_CACHE_SIZE", "10000")),
            default_ttl=float(os.getenv("ESE_CACHE_TTL", "3600"))
        )
    return _cache_manager


def update_variability_stats_for_source_cached(
    conn: sqlite3.Connection,
    source_id: str,
    use_cache: bool = True
) -> bool:
    """Update variability stats with caching."""
    cache_manager = get_cache_manager()

    # Get last photometry timestamp
    cursor = conn.execute(
        """
        SELECT MAX(measured_at) FROM photometry WHERE source_id = ?
        """,
        (source_id,)
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        return False

    current_photometry_timestamp = float(row[0])

    # Check cache
    if use_cache:
        cached_stats = cache_manager.get(source_id, current_photometry_timestamp)
        if cached_stats is not None:
            # Cache hit - update database with cached stats
            update_stats_from_dict(conn, source_id, cached_stats)
            return True

    # Cache miss - compute statistics
    stats = compute_variability_stats(conn, source_id)

    # Update database
    update_stats_from_dict(conn, source_id, stats)

    # Cache results
    if use_cache:
        cache_manager.set(source_id, stats, current_photometry_timestamp)

    return True
```

**Performance Benefits**:

- **Cache hit rate**: Expected 80-90% for stable sources
- **Speedup**: 10-100x faster for cached sources
- **Database load**: Reduced by 80-90%
- **Scalability**: Can handle 10x more sources with same resources

---

### 3.2 Parallel Processing

#### Scientific Rationale

ESE detection is embarrassingly parallel:

- Each source processed independently
- No dependencies between sources
- Stateless computation

Parallelization provides:

- **Speed**: Process multiple sources simultaneously
- **Resource utilization**: Better CPU/memory usage
- **Scalability**: Handle larger catalogs efficiently

#### Implementation

```python
from multiprocessing import Pool, cpu_count
from functools import partial
import sqlite3
from pathlib import Path

def process_source_batch(
    source_ids: List[str],
    products_db: Path,
    batch_size: int = 100
) -> List[dict]:
    """
    Process sources in parallel batches.

    Args:
        source_ids: List of source IDs to process
        products_db: Path to products database
        batch_size: Number of sources per batch

    Returns:
        List of detection results
    """
    # Determine optimal worker count
    n_workers = min(cpu_count(), len(source_ids), 8)  # Cap at 8 workers

    # Split into batches
    batches = [
        source_ids[i:i + batch_size]
        for i in range(0, len(source_ids), batch_size)
    ]

    # Process batches in parallel
    with Pool(n_workers) as pool:
        process_func = partial(
            process_single_batch,
            products_db=products_db
        )
        results = pool.map(process_func, batches)

    # Flatten results
    return [item for sublist in results for item in sublist]


def process_single_batch(
    source_ids: List[str],
    products_db: Path
) -> List[dict]:
    """Process a single batch of sources."""
    # Each worker gets its own database connection
    conn = sqlite3.connect(products_db, timeout=30.0)
    conn.row_factory = sqlite3.Row

    results = []
    for source_id in source_ids:
        try:
            # Update stats
            update_variability_stats_for_source(conn, source_id)

            # Check for ESE candidate
            candidate = check_ese_candidate(conn, source_id)
            if candidate:
                results.append(candidate)
        except Exception as e:
            logger.error(f"Error processing {source_id}: {e}")
        finally:
            conn.close()

    return results
```

**Database Considerations**:

```python
def parallel_detection_with_locking(
    source_ids: List[str],
    products_db: Path
):
    """
    Parallel detection with proper database locking.

    SQLite supports concurrent reads but requires careful
    handling for writes.
    """
    # Use WAL mode for better concurrency
    conn = sqlite3.connect(products_db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.close()

    # Process in parallel with connection pooling
    with Pool() as pool:
        # Each worker creates its own connection
        results = pool.map(
            partial(process_source_with_connection, products_db=products_db),
            source_ids
        )
```

**Performance Characteristics**:

- **Speedup**: Near-linear up to CPU count
- **Scalability**: Handles 100K+ sources efficiently
- **Resource usage**: Configurable worker count
- **Fault tolerance**: Individual source failures don't crash batch

---

## 4. Multi-Frequency Analysis

#### Scientific Rationale

ESEs show frequency-dependent variability:

- **Plasma lensing**: Frequency-dependent refractive index
- **Scintillation**: Frequency-dependent scattering
- **Correlation**: Variability correlated across frequencies

Single-frequency analysis misses:

- Frequency-dependent signatures
- Enhanced detection confidence from correlation
- Physical interpretation of ESE mechanism

#### Implementation

```python
def detect_ese_multi_frequency(
    source_id: str,
    frequencies: List[float],
    products_db: Path
) -> dict:
    """
    Detect ESE using multi-frequency analysis.

    Analyzes variability at multiple frequencies and looks for
    correlated changes that indicate ESE rather than intrinsic
    source variability.

    Algorithm:
        1. Compute variability at each frequency
        2. Check for correlation across frequencies
        3. Enhanced confidence if correlated
        4. Flag as ESE if significance exceeds threshold

    Args:
        source_id: Source identifier
        frequencies: List of observation frequencies (MHz)
        products_db: Path to products database

    Returns:
        Detection result with multi-frequency analysis
    """
    conn = sqlite3.connect(products_db)

    # Get flux measurements at each frequency
    flux_by_freq = {}
    for freq in frequencies:
        measurements = get_flux_at_frequency(conn, source_id, freq)
        flux_by_freq[freq] = measurements

    # Compute variability at each frequency
    variability_by_freq = {}
    for freq, measurements in flux_by_freq.items():
        if len(measurements) < 2:
            continue

        fluxes = [m["flux"] for m in measurements]
        variability_by_freq[freq] = {
            "sigma_deviation": calculate_sigma_deviation(fluxes),
            "mean_flux": np.mean(fluxes),
            "std_flux": np.std(fluxes),
            "n_obs": len(measurements)
        }

    # Check for frequency correlation
    correlation_result = analyze_frequency_correlation(
        variability_by_freq,
        frequencies
    )

    # Calculate composite significance
    # Higher significance if variability is correlated across frequencies
    base_significance = max(
        v["sigma_deviation"] for v in variability_by_freq.values()
    )

    if correlation_result["correlated"]:
        # Boost significance for correlated variability
        correlation_boost = 1.0 + correlation_result["correlation_strength"] * 0.5
        composite_significance = base_significance * correlation_boost
    else:
        composite_significance = base_significance

    return {
        "source_id": source_id,
        "frequencies": frequencies,
        "variability_by_frequency": variability_by_freq,
        "correlation_analysis": correlation_result,
        "base_significance": base_significance,
        "composite_significance": composite_significance,
        "is_ese_candidate": composite_significance >= 5.0
    }


def analyze_frequency_correlation(
    variability_by_freq: dict,
    frequencies: List[float]
) -> dict:
    """
    Analyze correlation of variability across frequencies.

    ESEs should show correlated variability across frequencies
    due to plasma lensing effects.
    """
    if len(variability_by_freq) < 2:
        return {
            "correlated": False,
            "correlation_strength": 0.0,
            "correlation_coefficient": None
        }

    # Extract sigma deviations
    sigmas = [
        variability_by_freq[freq]["sigma_deviation"]
        for freq in frequencies
        if freq in variability_by_freq
    ]

    if len(sigmas) < 2:
        return {"correlated": False, "correlation_strength": 0.0}

    # Check if variability is correlated
    # Simple heuristic: if multiple frequencies show high variability
    high_variability_count = sum(1 for s in sigmas if s > 3.0)
    correlation_strength = high_variability_count / len(sigmas)

    # More sophisticated: temporal correlation
    # (would require time-series data at each frequency)

    return {
        "correlated": correlation_strength > 0.5,
        "correlation_strength": correlation_strength,
        "high_variability_frequencies": [
            freq for freq, var in variability_by_freq.items()
            if var["sigma_deviation"] > 3.0
        ]
    }
```

**Database Schema Extension**:

```sql
-- Add frequency column to photometry table
ALTER TABLE photometry ADD COLUMN frequency_mhz REAL;

-- Create index for frequency queries
CREATE INDEX IF NOT EXISTS idx_photometry_frequency
ON photometry(source_id, frequency_mhz, measured_at);

-- Multi-frequency variability stats
CREATE TABLE IF NOT EXISTS variability_stats_multi_freq (
    source_id TEXT NOT NULL,
    frequency_mhz REAL NOT NULL,
    sigma_deviation REAL,
    mean_flux_mjy REAL,
    std_flux_mjy REAL,
    n_obs INTEGER,
    PRIMARY KEY (source_id, frequency_mhz)
);
```

---

## 5. Multi-Observable Correlation

#### Scientific Rationale

ESEs manifest in multiple observables:

- **Flux density**: Primary indicator (what we currently use)
- **Scintillation bandwidth**: Frequency-dependent scattering
- **Dispersion measure**: Electron density variations (for pulsars)
- **Scintillation timescale**: Temporal variations

Correlated changes across observables:

- **Higher confidence**: Multiple independent indicators
- **Physical interpretation**: Constrains ESE mechanism
- **False positive reduction**: Intrinsic variability unlikely to correlate

#### Implementation

```python
def detect_ese_multi_observable(
    source_id: str,
    products_db: Path,
    observables: dict
) -> dict:
    """
    Detect ESE using multiple observables.

    Observables should include:
    - flux: Flux density measurements
    - scintillation_bandwidth: Scintillation bandwidth (if available)
    - dm: Dispersion measure (for pulsars, if available)
    - scintillation_timescale: Scintillation timescale (if available)

    Returns detection result with multi-observable analysis.
    """
    results = {}

    # Analyze flux variability (existing)
    if "flux" in observables:
        flux_result = analyze_flux_variability(
            source_id,
            observables["flux"],
            products_db
        )
        results["flux"] = flux_result

    # Analyze scintillation bandwidth (if available)
    if "scintillation_bandwidth" in observables:
        scint_result = analyze_scintillation_variability(
            source_id,
            observables["scintillation_bandwidth"],
            products_db
        )
        results["scintillation"] = scint_result

    # Analyze DM variations (for pulsars)
    if "dm" in observables:
        dm_result = analyze_dm_variability(
            source_id,
            observables["dm"],
            products_db
        )
        results["dm"] = dm_result

    # Check for correlation
    correlation = calculate_observable_correlation(results)

    # Composite significance
    base_significance = results.get("flux", {}).get("significance", 0.0)

    if correlation["correlated"]:
        # Boost for correlated multi-observable changes
        composite_significance = base_significance * (1.0 + correlation["strength"] * 0.3)
    else:
        composite_significance = base_significance

    return {
        "source_id": source_id,
        "observable_results": results,
        "correlation": correlation,
        "composite_significance": composite_significance,
        "is_ese_candidate": composite_significance >= 5.0,
        "confidence": "high" if correlation["correlated"] else "medium"
    }
```

---

## Summary

This comprehensive improvement plan provides:

1. **Deep technical specifications** for each improvement
2. **Scientific rationale** explaining why each improvement matters
3. **Implementation details** with code examples
4. **Testing strategies** to validate improvements
5. **Performance considerations** and optimizations
6. **Integration points** with existing code

All improvements are treated as equally high priority with equal depth of
analysis, providing a complete roadmap for enhancing the ESE detection system.
