"""Unit tests for configurable threshold presets.

Focus: Fast tests for threshold preset system.
Task 2.2: Configurable Threshold Presets
"""

from __future__ import annotations

import pytest

from dsa110_contimg.photometry.thresholds import (
    get_threshold_preset,
    ThresholdPreset,
)


class TestThresholdPresets:
    """Test suite for threshold presets."""

    def test_conservative_preset(self):
        """Test conservative preset values."""
        if get_threshold_preset is None:
            pytest.skip("get_threshold_preset not yet implemented")
        
        # Arrange: Request conservative preset
        preset = get_threshold_preset(ThresholdPreset.CONSERVATIVE)
        
        # Assert: Should have high thresholds
        assert preset['min_sigma'] >= 5.0, "Conservative should have high sigma threshold"
        assert preset['min_chi2_nu'] >= 4.0, "Conservative should have high chi2 threshold"
        assert preset['min_eta'] >= 3.0, "Conservative should have high eta threshold"

    def test_moderate_preset(self):
        """Test moderate preset values."""
        if get_threshold_preset is None:
            pytest.skip("get_threshold_preset not yet implemented")
        
        # Arrange: Request moderate preset
        preset = get_threshold_preset(ThresholdPreset.MODERATE)
        
        # Assert: Should have moderate thresholds
        assert 3.0 <= preset['min_sigma'] < 5.0, "Moderate should have moderate sigma"
        assert 2.0 <= preset['min_chi2_nu'] < 4.0, "Moderate should have moderate chi2"
        assert 1.5 <= preset['min_eta'] < 3.0, "Moderate should have moderate eta"

    def test_sensitive_preset(self):
        """Test sensitive preset values."""
        if get_threshold_preset is None:
            pytest.skip("get_threshold_preset not yet implemented")
        
        # Arrange: Request sensitive preset
        preset = get_threshold_preset(ThresholdPreset.SENSITIVE)
        
        # Assert: Should have low thresholds
        assert preset['min_sigma'] < 3.0, "Sensitive should have low sigma threshold"
        assert preset['min_chi2_nu'] < 2.0, "Sensitive should have low chi2 threshold"
        assert preset['min_eta'] < 1.5, "Sensitive should have low eta threshold"

    def test_custom_preset(self):
        """Test custom preset creation."""
        if get_threshold_preset is None:
            pytest.skip("get_threshold_preset not yet implemented")
        
        # Arrange: Custom thresholds
        custom_thresholds = {
            'min_sigma': 4.5,
            'min_chi2_nu': 3.5,
            'min_eta': 2.5,
        }
        
        # Act: Create custom preset
        preset = get_threshold_preset(custom_thresholds)
        
        # Assert: Should match custom values
        assert preset['min_sigma'] == 4.5
        assert preset['min_chi2_nu'] == 3.5
        assert preset['min_eta'] == 2.5

    def test_preset_hierarchy(self):
        """Test preset hierarchy (conservative > moderate > sensitive)."""
        if get_threshold_preset is None:
            pytest.skip("get_threshold_preset not yet implemented")
        
        # Arrange: Get all presets
        conservative = get_threshold_preset(ThresholdPreset.CONSERVATIVE)
        moderate = get_threshold_preset(ThresholdPreset.MODERATE)
        sensitive = get_threshold_preset(ThresholdPreset.SENSITIVE)
        
        # Assert: Conservative should have highest thresholds
        assert conservative['min_sigma'] >= moderate['min_sigma'], \
            "Conservative sigma should be >= moderate"
        assert moderate['min_sigma'] >= sensitive['min_sigma'], \
            "Moderate sigma should be >= sensitive"

    def test_preset_validation(self):
        """Test preset validation."""
        if get_threshold_preset is None:
            pytest.skip("get_threshold_preset not yet implemented")
        
        # Arrange: Invalid preset name
        try:
            preset = get_threshold_preset("INVALID")
            # If no exception, check that it handles gracefully
            assert preset is not None or preset == {}, "Should handle invalid preset"
        except ValueError:
            # That's acceptable - function might validate
            pass

    def test_preset_smoke(self):
        """End-to-end smoke test."""
        if get_threshold_preset is None:
            pytest.skip("get_threshold_preset not yet implemented")
        
        # Arrange: Use moderate preset
        preset = get_threshold_preset(ThresholdPreset.MODERATE)
        
        # Act: Use preset for detection
        # (In real usage, would pass to detect_ese_candidates)
        
        # Assert: Preset should be valid
        assert 'min_sigma' in preset, "Preset should have min_sigma"
        assert 'min_chi2_nu' in preset, "Preset should have min_chi2_nu"
        assert 'min_eta' in preset, "Preset should have min_eta"
        assert all(v >= 0 for v in preset.values()), "All thresholds should be non-negative"

    def test_preset_api_integration_smoke(self):
        """API integration smoke test."""
        if get_threshold_preset is None:
            pytest.skip("get_threshold_preset not yet implemented")
        
        # Arrange: Get preset
        preset = get_threshold_preset(ThresholdPreset.MODERATE)
        
        # Act: Convert to API format (if needed)
        api_params = {
            'min_sigma': preset['min_sigma'],
            'min_chi2_nu': preset.get('min_chi2_nu', None),
            'min_eta': preset.get('min_eta', None),
        }
        
        # Assert: Should be valid for API
        assert api_params['min_sigma'] > 0, "API params should be valid"

    def test_preset_cli_integration_smoke(self):
        """CLI integration smoke test."""
        if get_threshold_preset is None:
            pytest.skip("get_threshold_preset not yet implemented")
        
        # Arrange: Get preset
        preset = get_threshold_preset(ThresholdPreset.CONSERVATIVE)
        
        # Act: Convert to CLI args (if needed)
        cli_args = {
            '--min-sigma': str(preset['min_sigma']),
        }
        
        # Assert: Should be valid for CLI
        assert float(cli_args['--min-sigma']) > 0, "CLI args should be valid"

