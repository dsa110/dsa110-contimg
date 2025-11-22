import numpy as np
import pandas as pd
import pytest

from dsa110_contimg.photometry.variability import (
    calculate_eta_metric,
    calculate_m_metric,
    calculate_relative_flux,
    calculate_sigma_deviation,
    calculate_v_metric,
    calculate_vs_metric,
)


def test_eta_metric():
    """Test η metric calculation."""
    # Case 1: Constant flux, should be near 0
    df = pd.DataFrame(
        {"normalized_flux_jy": [1.0, 1.0, 1.0], "normalized_flux_err_jy": [0.1, 0.1, 0.1]}
    )
    eta = calculate_eta_metric(df)
    assert np.isclose(eta, 0.0)

    # Case 2: High variance
    df = pd.DataFrame(
        {"normalized_flux_jy": [1.0, 10.0, 1.0], "normalized_flux_err_jy": [0.1, 0.1, 0.1]}
    )
    eta = calculate_eta_metric(df)
    assert eta > 1.0

    # Case 3: Insufficient data
    df_short = df.iloc[:1]
    assert calculate_eta_metric(df_short) == 0.0


def test_vs_metric():
    """Test Vs metric calculation."""
    # Significant change
    vs = calculate_vs_metric(10.0, 5.0, 1.0, 1.0)
    # (10 - 5) / sqrt(1^2 + 1^2) = 5 / 1.414 = ~3.53
    assert np.isclose(vs, 3.5355, atol=0.001)

    # No change
    vs = calculate_vs_metric(10.0, 10.0, 1.0, 1.0)
    assert vs == 0.0

    # Invalid errors
    with pytest.raises(ValueError):
        calculate_vs_metric(10.0, 5.0, 0.0, 1.0)


def test_m_metric():
    """Test m metric calculation."""
    # 2 * (10 - 5) / (10 + 5) = 2 * 5 / 15 = 2/3
    m = calculate_m_metric(10.0, 5.0)
    assert np.isclose(m, 0.6666, atol=0.001)

    # Zero sum
    with pytest.raises(ValueError):
        calculate_m_metric(10.0, -10.0)


def test_v_metric():
    """Test V metric calculation."""
    fluxes = np.array([10.0, 12.0, 8.0])
    mean = 10.0
    std = np.std(fluxes)
    expected = std / mean
    assert np.isclose(calculate_v_metric(fluxes), expected)

    # Empty
    assert calculate_v_metric(np.array([])) == 0.0


def test_sigma_deviation():
    """Test sigma deviation."""
    fluxes = np.array([10.0, 10.0, 100.0])
    # Mean = 40, Std ~ 51.96
    # Max deviation = |100 - 40| / 51.96 = 60 / 51.96 ~ 1.15
    dev = calculate_sigma_deviation(fluxes)
    assert dev > 1.0

    # Single value
    assert calculate_sigma_deviation(np.array([10.0])) == 0.0


def test_relative_flux_basic():
    """Test basic relative flux calculation."""
    target = np.array([10.0, 20.0, 10.0])
    # Neighbor follows target perfectly (ratio 2.0)
    neighbor = np.array([5.0, 10.0, 5.0])

    rel_flux, mean, std = calculate_relative_flux(target, neighbor)

    expected = np.array([2.0, 2.0, 2.0])
    np.testing.assert_array_almost_equal(rel_flux, expected)
    assert np.isclose(std, 0.0)


def test_relative_flux_multiple_neighbors():
    """Test relative flux with multiple neighbors."""
    target = np.array([10.0, 10.0])
    # Two neighbors, average is 10.0
    neighbors = np.array([[5.0, 15.0], [5.0, 15.0]])

    rel_flux, mean, _ = calculate_relative_flux(target, neighbors)
    np.testing.assert_array_almost_equal(rel_flux, np.array([1.0, 1.0]))


def test_relative_flux_robust_outlier():
    """Test robust statistics rejection of outliers."""
    target = np.array([10.0, 10.0])
    # 3 neighbors
    # Epoch 0: All stable at 10
    # Epoch 1: One flares to 100
    neighbors = np.array([[10.0, 10.0, 10.0], [10.0, 10.0, 100.0]])

    # With robust stats (median), ensemble avg should be close to 10 for both epochs
    # Epoch 1 median of 10, 10, 100 is 10
    rel_flux, _, _ = calculate_relative_flux(target, neighbors, use_robust_stats=True)

    assert np.isclose(rel_flux[0], 1.0)
    assert np.isclose(rel_flux[1], 1.0)

    # With non-robust stats (mean), epoch 1 avg is (120)/3 = 40, so rel flux = 10/40 = 0.25
    rel_flux_mean, _, _ = calculate_relative_flux(target, neighbors, use_robust_stats=False)
    assert np.isclose(rel_flux_mean[1], 0.25)


def test_relative_flux_nans():
    """Test handling of NaNs in input."""
    target = np.array([10.0, 10.0])
    neighbors = np.array([[10.0, np.nan], [10.0, 10.0]])

    rel_flux, _, _ = calculate_relative_flux(target, neighbors)
    # Epoch 0: ignores NaN, avg=10. Ratio=1.0
    assert np.isclose(rel_flux[0], 1.0)


def test_relative_flux_weights():
    """Test weighted averaging."""
    target = np.array([10.0])
    neighbors = np.array([[10.0, 20.0]])
    # Weight 20.0 zero, so avg should be 10.0
    weights = np.array([1.0, 0.0])

    rel_flux, _, _ = calculate_relative_flux(
        target, neighbors, neighbor_weights=weights, use_robust_stats=False
    )
    assert np.isclose(rel_flux[0], 1.0)
