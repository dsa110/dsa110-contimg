"""
Unit tests for validation mode selection.
"""

import pytest
from dsa110_contimg.qa.fast_validation import (
    ValidationMode,
    get_fast_config_for_mode,
    validate_pipeline_fast,
)


class TestValidationMode:
    """Tests for ValidationMode enum."""

    def test_validation_mode_values(self):
        """Test ValidationMode enum values."""
        assert ValidationMode.FAST.value == "fast"
        assert ValidationMode.STANDARD.value == "standard"
        assert ValidationMode.COMPREHENSIVE.value == "comprehensive"

    def test_validation_mode_enumeration(self):
        """Test ValidationMode enum members."""
        modes = list(ValidationMode)
        assert len(modes) == 3
        assert ValidationMode.FAST in modes
        assert ValidationMode.STANDARD in modes
        assert ValidationMode.COMPREHENSIVE in modes


class TestGetFastConfigForMode:
    """Tests for get_fast_config_for_mode()."""

    def test_fast_mode_config(self):
        """Test FAST mode configuration."""
        config = get_fast_config_for_mode(ValidationMode.FAST)
        
        assert config.ms_sample_fraction == 0.005
        assert config.image_sample_pixels == 5000
        assert config.catalog_max_sources == 25
        assert config.timeout_seconds == 30
        assert config.skip_expensive_checks is True
        assert config.skip_photometry_validation is True
        assert config.skip_variability_validation is True
        assert config.skip_mosaic_validation is True

    def test_standard_mode_config(self):
        """Test STANDARD mode configuration."""
        config = get_fast_config_for_mode(ValidationMode.STANDARD)
        
        assert config.ms_sample_fraction == 0.01
        assert config.image_sample_pixels == 10000
        assert config.catalog_max_sources == 50
        assert config.timeout_seconds == 60
        assert config.skip_expensive_checks is False
        assert config.skip_photometry_validation is False
        assert config.skip_variability_validation is True
        assert config.skip_mosaic_validation is True

    def test_comprehensive_mode_config(self):
        """Test COMPREHENSIVE mode configuration."""
        config = get_fast_config_for_mode(ValidationMode.COMPREHENSIVE)
        
        assert config.ms_sample_fraction == 0.1
        assert config.image_sample_pixels is None
        assert config.catalog_max_sources is None
        assert config.timeout_seconds == 300
        assert config.skip_expensive_checks is False
        assert config.skip_photometry_validation is False
        assert config.skip_variability_validation is False
        assert config.skip_mosaic_validation is False


class TestValidatePipelineFastWithMode:
    """Tests for validate_pipeline_fast() with mode parameter."""

    @pytest.mark.parametrize("mode", [ValidationMode.FAST, ValidationMode.STANDARD, ValidationMode.COMPREHENSIVE])
    def test_validate_pipeline_fast_with_mode(self, mode):
        """Test validate_pipeline_fast() accepts mode parameter."""
        from unittest.mock import patch
        
        with patch("dsa110_contimg.qa.fast_validation.Path.exists", return_value=True):
            with patch("dsa110_contimg.qa.fast_validation._run_tier1_validation") as mock_tier1:
                with patch("dsa110_contimg.qa.fast_validation._run_tier2_validation") as mock_tier2:
                    with patch("dsa110_contimg.qa.fast_validation._run_tier3_validation") as mock_tier3:
                        mock_tier1.return_value = {"passed": True, "elapsed_seconds": 2.0}
                        mock_tier2.return_value = {"passed": True, "elapsed_seconds": 15.0}
                        mock_tier3.return_value = {"passed": True, "elapsed_seconds": 10.0}
                        
                        result = validate_pipeline_fast(
                            ms_path="/fake/ms",
                            caltables=None,
                            image_paths=None,
                            mode=mode,
                        )
                        
                        assert result.passed is True
                        # Verify mode-specific config was used
                        if mode == ValidationMode.FAST:
                            assert result.timing.get("total_seconds", 0) < 30
                        elif mode == ValidationMode.STANDARD:
                            assert result.timing.get("total_seconds", 0) < 60

