"""Unit tests for variability metric calculations.

Focus: Fast tests for sigma deviation calculation and related variability metrics.
Task 1.1: Extract Shared Sigma Deviation Function
"""

from __future__ import annotations

import numpy as np
import pytest

from dsa110_contimg.photometry.variability import calculate_sigma_deviation


class TestCalculateSigmaDeviation:
    """Test suite for calculate_sigma_deviation function."""

    def test_basic_calculation(self):
        """Verify against manual calculation."""
        if calculate_sigma_deviation is None:
            pytest.skip("calculate_sigma_deviation not yet implemented")

        # Arrange: Simple flux array
        fluxes = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        # Act: Calculate sigma deviation
        result = calculate_sigma_deviation(fluxes)

        # Assert: Manual calculation
        # mean = 3.0, std ≈ 1.414, max_deviation = |5.0 - 3.0| = 2.0
        # sigma_deviation = 2.0 / 1.414 ≈ 1.414
        expected = abs(5.0 - 3.0) / np.std(fluxes, ddof=1)
        assert abs(
            result - expected) < 0.01, f"Expected ≈ {expected}, got {result}"

    def test_symmetric_deviations(self):
        """Both positive and negative deviations."""
        if calculate_sigma_deviation is None:
            pytest.skip("calculate_sigma_deviation not yet implemented")

        # Arrange: Symmetric distribution around mean
        fluxes = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        # Act
        result = calculate_sigma_deviation(fluxes)

        # Assert: Should capture maximum deviation (both directions)
        mean_flux = np.mean(fluxes)
        std_flux = np.std(fluxes, ddof=1)
        max_pos_dev = abs(5.0 - mean_flux) / std_flux
        max_neg_dev = abs(1.0 - mean_flux) / std_flux
        expected = max(max_pos_dev, max_neg_dev)

        assert abs(
            result - expected) < 0.01, f"Expected ≈ {expected}, got {result}"

    def test_zero_variance(self):
        """Returns 0.0 for identical values."""
        if calculate_sigma_deviation is None:
            pytest.skip("calculate_sigma_deviation not yet implemented")

        # Arrange: All identical values
        fluxes = np.array([1.0, 1.0, 1.0])

        # Act
        result = calculate_sigma_deviation(fluxes)

        # Assert: Zero variance should return 0.0
        assert result == 0.0, f"Expected 0.0 for identical values, got {result}"

    def test_single_measurement(self):
        """Returns 0.0 for single value."""
        if calculate_sigma_deviation is None:
            pytest.skip("calculate_sigma_deviation not yet implemented")

        # Arrange: Single measurement
        fluxes = np.array([1.0])

        # Act
        result = calculate_sigma_deviation(fluxes)

        # Assert: Need multiple measurements for variance
        assert result == 0.0, f"Expected 0.0 for single measurement, got {result}"

    def test_negative_fluxes(self):
        """Handles negative values correctly."""
        if calculate_sigma_deviation is None:
            pytest.skip("calculate_sigma_deviation not yet implemented")

        # Arrange: Negative and positive fluxes
        fluxes = np.array([-1.0, 0.0, 1.0])

        # Act
        result = calculate_sigma_deviation(fluxes)

        # Assert: Should handle negative values
        assert result >= 0.0, f"Sigma deviation should be non-negative, got {result}"
        assert not np.isnan(result), "Result should not be NaN"

    def test_nan_handling(self):
        """Filters NaN values."""
        if calculate_sigma_deviation is None:
            pytest.skip("calculate_sigma_deviation not yet implemented")

        # Arrange: Fluxes with NaN
        fluxes = np.array([1.0, 2.0, np.nan, 4.0, 5.0])

        # Act
        result = calculate_sigma_deviation(fluxes)

        # Assert: NaN should be filtered, valid result
        assert not np.isnan(result), "Result should not be NaN"
        assert not np.isinf(result), "Result should not be Inf"
        # Should calculate based on valid values [1.0, 2.0, 4.0, 5.0]
        valid_fluxes = np.array([1.0, 2.0, 4.0, 5.0])
        expected = max(
            abs(5.0 - np.mean(valid_fluxes)) / np.std(valid_fluxes, ddof=1),
            abs(1.0 - np.mean(valid_fluxes)) / np.std(valid_fluxes, ddof=1)
        )
        assert abs(
            result - expected) < 0.1, f"Expected ≈ {expected}, got {result}"

    def test_precomputed_statistics(self):
        """Works with provided mean/std."""
        # Arrange: Fluxes and pre-computed statistics
        fluxes = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        # Compute actual mean and std for accurate comparison
        actual_mean = np.mean(fluxes)
        actual_std = np.std(fluxes, ddof=1)

        # Act: Try with precomputed stats
        result_with_stats = calculate_sigma_deviation(
            fluxes, mean=actual_mean, std=actual_std)
        result_auto = calculate_sigma_deviation(fluxes)

        # Assert: Should give same result
        assert abs(result_with_stats - result_auto) < 0.01, \
            f"Precomputed stats should give same result: {result_with_stats} vs {result_auto}"

    def test_edge_case_large_deviations(self):
        """Handles extreme outliers."""
        # Arrange: Extreme outlier
        fluxes = np.array([1.0, 2.0, 3.0, 4.0, 100.0])

        # Act
        result = calculate_sigma_deviation(fluxes)

        # Assert: Should detect large deviation (relative to the distribution)
        # With this data: mean=22, std≈39.4, max_deviation≈1.98
        # The test should verify it's larger than a normal distribution would produce
        assert result > 1.0, f"Expected significant sigma deviation for outlier, got {result}"
        assert not np.isnan(result), "Result should not be NaN"
        assert not np.isinf(result), "Result should not be Inf"

    def test_empty_array(self):
        """Raises ValueError for empty input."""
        if calculate_sigma_deviation is None:
            pytest.skip("calculate_sigma_deviation not yet implemented")

        # Arrange: Empty array
        fluxes = np.array([])

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="empty|Empty|at least"):
            calculate_sigma_deviation(fluxes)

    def test_all_nan(self):
        """Raises ValueError for all NaN."""
        if calculate_sigma_deviation is None:
            pytest.skip("calculate_sigma_deviation not yet implemented")

        # Arrange: All NaN
        fluxes = np.array([np.nan, np.nan, np.nan])

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="NaN|nan|valid"):
            calculate_sigma_deviation(fluxes)

    def test_sigma_deviation_smoke(self):
        """End-to-end integration test."""
        if calculate_sigma_deviation is None:
            pytest.skip("calculate_sigma_deviation not yet implemented")

        # Arrange: Realistic flux measurements
        fluxes = np.array([10.5, 11.2, 10.8, 12.1, 15.3, 10.9])

        # Act: Calculate sigma deviation
        result = calculate_sigma_deviation(fluxes)

        # Assert: Valid result
        assert result >= 0.0, "Sigma deviation should be non-negative"
        assert not np.isnan(result), "Result should not be NaN"
        assert not np.isinf(result), "Result should not be Inf"

        # Verify it's reasonable (should detect the 15.3 outlier)
        mean_flux = np.mean(fluxes)
        std_flux = np.std(fluxes, ddof=1)
        expected_max_dev = abs(15.3 - mean_flux) / std_flux
        assert abs(result - expected_max_dev) < 0.1, \
            f"Expected ≈ {expected_max_dev}, got {result}"
