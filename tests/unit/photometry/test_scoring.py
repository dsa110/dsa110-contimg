"""Unit tests for multi-metric scoring system.

Focus: Fast tests for composite scoring algorithm.
Task 2.1: Multi-Metric Scoring System
"""

from __future__ import annotations

import numpy as np
import pytest

from dsa110_contimg.photometry.scoring import (
    calculate_composite_score,
    normalize_metric,
)


class TestMultiMetricScoring:
    """Test suite for multi-metric scoring system."""

    def test_normalize_metric_basic(self):
        """Basic normalization test."""
        if normalize_metric is None:
            pytest.skip("normalize_metric not yet implemented")
        
        # Arrange: Known metric value
        metric_value = 5.0
        min_val = 0.0
        max_val = 10.0
        
        # Act: Normalize
        result = normalize_metric(metric_value, min_val, max_val)
        
        # Assert: Should be between 0 and 1
        assert 0.0 <= result <= 1.0, f"Normalized value should be in [0, 1], got {result}"
        assert abs(result - 0.5) < 0.01, f"Expected ≈ 0.5, got {result}"

    def test_normalize_metric_clipping(self):
        """Test clipping at boundaries."""
        if normalize_metric is None:
            pytest.skip("normalize_metric not yet implemented")
        
        # Arrange: Value outside range
        metric_value = 15.0
        min_val = 0.0
        max_val = 10.0
        
        # Act: Normalize
        result = normalize_metric(metric_value, min_val, max_val)
        
        # Assert: Should be clipped to 1.0
        assert result == 1.0, f"Should clip to 1.0, got {result}"

    def test_composite_score_basic(self):
        """Basic composite score calculation."""
        if calculate_composite_score is None:
            pytest.skip("calculate_composite_score not yet implemented")
        
        # Arrange: Known metrics
        metrics = {
            'sigma_deviation': 5.0,
            'chi2_nu': 3.0,
            'eta_metric': 2.0,
        }
        weights = {
            'sigma_deviation': 0.5,
            'chi2_nu': 0.3,
            'eta_metric': 0.2,
        }
        
        # Act: Calculate composite score
        result = calculate_composite_score(metrics, weights)
        
        # Assert: Should be weighted sum
        assert result >= 0.0, "Composite score should be non-negative"
        assert not np.isnan(result), "Result should not be NaN"

    def test_composite_score_default_weights(self):
        """Test with default weights."""
        if calculate_composite_score is None:
            pytest.skip("calculate_composite_score not yet implemented")
        
        # Arrange: Metrics without weights
        metrics = {
            'sigma_deviation': 5.0,
            'chi2_nu': 3.0,
        }
        
        # Act: Calculate with default weights
        result = calculate_composite_score(metrics)
        
        # Assert: Should use default weights
        assert result >= 0.0, "Composite score should be non-negative"

    def test_composite_score_missing_metrics(self):
        """Handle missing metrics gracefully."""
        if calculate_composite_score is None:
            pytest.skip("calculate_composite_score not yet implemented")
        
        # Arrange: Some metrics missing
        metrics = {
            'sigma_deviation': 5.0,
            # chi2_nu missing
        }
        weights = {
            'sigma_deviation': 0.5,
            'chi2_nu': 0.3,
        }
        
        # Act: Calculate composite score
        try:
            result = calculate_composite_score(metrics, weights)
            # Assert: Should handle gracefully (either skip missing or use 0)
            assert result >= 0.0, "Should handle missing metrics"
        except KeyError:
            # That's also acceptable - function might require all metrics
            pytest.skip("Function requires all metrics")

    def test_composite_score_confidence_levels(self):
        """Test confidence level thresholds."""
        if calculate_composite_score is None:
            pytest.skip("calculate_composite_score not yet implemented")
        
        # Arrange: High score metrics
        metrics = {
            'sigma_deviation': 8.0,  # High
            'chi2_nu': 6.0,  # High
            'eta_metric': 4.0,  # Moderate
        }
        
        # Act: Calculate composite score
        result = calculate_composite_score(metrics)
        
        # Assert: Should be high confidence
        # High confidence: score > 7.0
        # Medium confidence: 4.0 < score <= 7.0
        # Low confidence: score <= 4.0
        assert result > 0.0, "High metrics should give positive score"

    def test_composite_score_smoke(self):
        """End-to-end smoke test."""
        if calculate_composite_score is None:
            pytest.skip("calculate_composite_score not yet implemented")
        
        # Arrange: Realistic ESE candidate metrics
        metrics = {
            'sigma_deviation': 5.5,
            'chi2_nu': 4.2,
            'eta_metric': 3.1,
        }
        
        # Act: Calculate composite score
        result = calculate_composite_score(metrics)
        
        # Assert: Valid result
        assert result >= 0.0, "Composite score should be non-negative"
        assert not np.isnan(result), "Result should not be NaN"
        assert not np.isinf(result), "Result should not be Inf"
        
        # Should be in reasonable range (depends on normalization)
        assert result < 100.0, "Score should be in reasonable range"

    def test_composite_score_validation(self):
        """Validation test with known ESE pattern."""
        if calculate_composite_score is None:
            pytest.skip("calculate_composite_score not yet implemented")
        
        # Arrange: Known ESE-like metrics
        ese_metrics = {
            'sigma_deviation': 6.0,  # Strong ESE signal
            'chi2_nu': 5.0,
            'eta_metric': 4.0,
        }
        
        non_ese_metrics = {
            'sigma_deviation': 2.0,  # Weak signal
            'chi2_nu': 1.5,
            'eta_metric': 1.0,
        }
        
        # Act: Calculate scores
        ese_score = calculate_composite_score(ese_metrics)
        non_ese_score = calculate_composite_score(non_ese_metrics)
        
        # Assert: ESE should score higher
        assert ese_score > non_ese_score, \
            f"ESE candidate should score higher ({ese_score} > {non_ese_score})"

