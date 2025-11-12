"""
Unit tests for QA configuration system.
"""

import pytest
from dsa110_contimg.qa.config import (
    AstrometryConfig,
    FastValidationConfig,
    FluxScaleConfig,
    ImageQualityConfig,
    QAConfig,
    get_default_config,
    load_config_from_dict,
)


class TestConfigClasses:
    """Test configuration dataclasses."""

    def test_astrometry_config_defaults(self):
        """Test AstrometryConfig default values."""
        config = AstrometryConfig()
        assert config.max_offset_arcsec == 1.0
        assert config.max_rms_arcsec == 0.5
        assert config.min_match_fraction == 0.8
        assert config.match_radius_arcsec == 2.0

    def test_flux_scale_config_defaults(self):
        """Test FluxScaleConfig default values."""
        config = FluxScaleConfig()
        assert config.max_flux_ratio_deviation == 0.2
        assert config.min_match_fraction == 0.5
        assert config.match_radius_arcsec == 2.0
        assert config.flux_box_size_pix == 5

    def test_image_quality_config_defaults(self):
        """Test ImageQualityConfig default values."""
        config = ImageQualityConfig()
        assert config.max_rms_noise == 0.001
        assert config.min_dynamic_range == 100.0
        assert config.max_beam_major_arcsec == 10.0
        assert config.min_beam_minor_arcsec == 0.1


class TestQAConfig:
    """Test master QAConfig class."""

    def test_default_config(self):
        """Test default QAConfig initialization."""
        config = QAConfig()
        assert isinstance(config.astrometry, AstrometryConfig)
        assert isinstance(config.flux_scale, FluxScaleConfig)
        assert isinstance(config.image_quality, ImageQualityConfig)
        assert config.generate_html_report is True
        assert config.generate_plots is True
        assert config.verbose is False

    def test_get_default_config_singleton(self):
        """Test get_default_config returns singleton."""
        config1 = get_default_config()
        config2 = get_default_config()
        # Should be the same instance
        assert config1 is config2

    def test_config_to_dict(self):
        """Test config conversion to dictionary."""
        config = QAConfig()
        config_dict = config.to_dict()
        
        assert "astrometry" in config_dict
        assert "flux_scale" in config_dict
        assert "image_quality" in config_dict
        assert config_dict["generate_html_report"] is True
        assert config_dict["generate_plots"] is True

    def test_load_config_from_dict(self):
        """Test loading config from dictionary."""
        config_dict = {
            "astrometry": {
                "max_offset_arcsec": 2.0,
                "max_rms_arcsec": 1.0,
            },
            "generate_html_report": False,
        }
        
        config = load_config_from_dict(config_dict)
        assert config.astrometry.max_offset_arcsec == 2.0
        assert config.astrometry.max_rms_arcsec == 1.0
        assert config.generate_html_report is False
        # Other values should remain defaults
        assert config.astrometry.min_match_fraction == 0.8

    def test_fast_validation_config_in_qa_config(self):
        """Test that QAConfig includes FastValidationConfig."""
        config = get_default_config()
        assert hasattr(config, "fast_validation")
        assert isinstance(config.fast_validation, FastValidationConfig)
        assert config.fast_validation.ms_sample_fraction == 0.01
        assert config.fast_validation.parallel_workers == 4
        assert config.fast_validation.timeout_seconds == 60

    def test_fast_validation_in_config_dict(self):
        """Test that fast_validation is included in to_dict()."""
        config = QAConfig()
        config_dict = config.to_dict()
        assert "fast_validation" in config_dict
        assert config_dict["fast_validation"]["ms_sample_fraction"] == 0.01


class TestFastValidationConfig:
    """Tests for FastValidationConfig."""

    def test_fast_validation_config_defaults(self):
        """Test FastValidationConfig default values."""
        config = FastValidationConfig()
        assert config.ms_sample_fraction == 0.01
        assert config.image_sample_pixels == 10000
        assert config.catalog_max_sources == 50
        assert config.calibration_sample_fraction == 0.01
        assert config.skip_expensive_checks is True
        assert config.parallel_workers == 4
        assert config.timeout_seconds == 60
        assert config.tier1_timeout_seconds == 10.0
        assert config.tier2_timeout_seconds == 30.0
        assert config.tier3_timeout_seconds == 60.0
        assert config.skip_catalog_validation is False
        assert config.skip_photometry_validation is False
        assert config.skip_variability_validation is True
        assert config.skip_mosaic_validation is True
        assert config.use_cache is True
        assert config.cache_ttl_seconds == 3600

    def test_fast_validation_config_custom(self):
        """Test FastValidationConfig with custom values."""
        config = FastValidationConfig(
            ms_sample_fraction=0.005,
            parallel_workers=8,
            timeout_seconds=30,
            skip_catalog_validation=True,
        )
        assert config.ms_sample_fraction == 0.005
        assert config.parallel_workers == 8
        assert config.timeout_seconds == 30
        assert config.skip_catalog_validation is True

