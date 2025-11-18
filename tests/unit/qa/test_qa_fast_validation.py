"""
Unit tests for fast validation module.
"""

from unittest.mock import patch

from dsa110_contimg.qa.config import get_default_config
from dsa110_contimg.qa.fast_validation import (
    TieredValidationResult,
    _run_tier1_validation,
    _run_tier2_validation,
    _run_tier3_validation,
    validate_pipeline_fast,
)


class TestTieredValidationResult:
    """Tests for TieredValidationResult."""

    def test_tiered_validation_result_defaults(self):
        """Test TieredValidationResult default initialization."""
        result = TieredValidationResult()
        assert result.passed is True
        assert result.tier1_results == {}
        assert result.tier2_results == {}
        assert result.tier3_results == {}
        assert result.errors == []
        assert result.warnings == []

    def test_tiered_validation_result_to_dict(self):
        """Test TieredValidationResult.to_dict()."""
        result = TieredValidationResult()
        result.tier1_results = {"passed": True}
        result.timing = {"tier1_seconds": 5.0}
        result_dict = result.to_dict()

        assert result_dict["passed"] is True
        assert result_dict["tier1_results"] == {"passed": True}
        assert result_dict["timing"]["tier1_seconds"] == 5.0


class TestTier1Validation:
    """Tests for Tier 1 validation (quick checks)."""

    @patch("dsa110_contimg.qa.fast_validation.quick_ms_check")
    @patch("dsa110_contimg.qa.fast_validation.quick_image_check")
    def test_tier1_validation_ms_only(self, mock_image_check, mock_ms_check):
        """Test Tier1 validation with MS only."""
        mock_ms_check.return_value = (True, "OK")

        result = _run_tier1_validation(
            ms_path="/fake/ms",
            caltables=None,
            image_paths=None,
            timeout=10.0,
        )

        assert result["passed"] is True
        assert len(result["errors"]) == 0
        mock_ms_check.assert_called_once_with("/fake/ms")

    @patch("dsa110_contimg.qa.fast_validation.quick_ms_check")
    def test_tier1_validation_ms_failure(self, mock_ms_check):
        """Test Tier1 validation with MS failure."""
        mock_ms_check.return_value = (False, "MS corrupted")

        result = _run_tier1_validation(
            ms_path="/fake/ms",
            caltables=None,
            image_paths=None,
            timeout=10.0,
        )

        assert result["passed"] is False
        assert result["critical_failure"] is True
        assert len(result["errors"]) > 0

    @patch("dsa110_contimg.qa.fast_validation.quick_image_check")
    def test_tier1_validation_images(self, mock_image_check):
        """Test Tier1 validation with images."""
        mock_image_check.return_value = (True, "OK")

        result = _run_tier1_validation(
            ms_path=None,
            caltables=None,
            image_paths=["/fake/img1.fits", "/fake/img2.fits"],
            timeout=10.0,
        )

        assert result["passed"] is True
        assert mock_image_check.call_count == 2


class TestTier2Validation:
    """Tests for Tier 2 validation (standard checks in parallel)."""

    @patch("dsa110_contimg.qa.fast_validation._check_ms_quality_fast")
    @patch("dsa110_contimg.qa.fast_validation._check_calibration_quality_fast")
    @patch("dsa110_contimg.qa.fast_validation._check_image_quality_fast")
    def test_tier2_validation_parallel(self, mock_img_check, mock_cal_check, mock_ms_check):
        """Test Tier2 validation runs checks in parallel."""
        mock_ms_check.return_value = {"passed": True}
        mock_cal_check.return_value = {"passed": True}
        mock_img_check.return_value = {"passed": True}

        config = get_default_config()
        fast_config = config.fast_validation

        result = _run_tier2_validation(
            ms_path="/fake/ms",
            caltables=["/fake/cal"],
            image_paths=["/fake/img.fits"],
            config=config,
            fast_config=fast_config,
            timeout=30.0,
        )

        assert result["passed"] is True
        assert "ms" in result
        assert "calibration" in result
        assert "image_0" in result


class TestTier3Validation:
    """Tests for Tier 3 validation (detailed checks)."""

    def test_tier3_validation_skipped_when_expensive_checks_disabled(self):
        """Test Tier3 validation is skipped when skip_expensive_checks=True."""
        config = get_default_config()
        fast_config = config.fast_validation
        fast_config.skip_expensive_checks = True

        result = _run_tier3_validation(
            ms_path=None,
            caltables=None,
            image_paths=None,
            config=config,
            fast_config=fast_config,
            timeout=60.0,
        )

        assert len(result["warnings"]) > 0
        assert "skipped" in result["warnings"][0].lower()


class TestValidatePipelineFast:
    """Tests for validate_pipeline_fast()."""

    def test_validate_pipeline_fast_missing_ms(self):
        """Test validation fails when MS is missing."""
        result = validate_pipeline_fast(
            ms_path="/nonexistent/ms",
            caltables=None,
            image_paths=None,
        )

        assert result.passed is False
        assert len(result.errors) > 0

    def test_validate_pipeline_fast_missing_images(self):
        """Test validation fails when images are missing."""
        result = validate_pipeline_fast(
            ms_path=None,
            caltables=None,
            image_paths=["/nonexistent/img.fits"],
        )

        assert result.passed is False
        assert len(result.errors) > 0

    @patch("dsa110_contimg.qa.fast_validation.Path.exists")
    @patch("dsa110_contimg.qa.fast_validation._run_tier1_validation")
    @patch("dsa110_contimg.qa.fast_validation._run_tier2_validation")
    @patch("dsa110_contimg.qa.fast_validation._run_tier3_validation")
    def test_validate_pipeline_fast_success(
        self,
        mock_tier3,
        mock_tier2,
        mock_tier1,
        mock_exists,
    ):
        """Test successful fast validation."""
        mock_exists.return_value = True
        mock_tier1.return_value = {"passed": True, "elapsed_seconds": 2.0}
        mock_tier2.return_value = {"passed": True, "elapsed_seconds": 15.0}
        mock_tier3.return_value = {"passed": True, "elapsed_seconds": 10.0}

        result = validate_pipeline_fast(
            ms_path="/fake/ms",
            caltables=["/fake/cal"],
            image_paths=["/fake/img.fits"],
        )

        assert result.passed is True
        assert "tier1_seconds" in result.timing
        assert "tier2_seconds" in result.timing
        assert "total_seconds" in result.timing

    @patch("dsa110_contimg.qa.fast_validation.Path.exists")
    @patch("dsa110_contimg.qa.fast_validation._run_tier1_validation")
    def test_validate_pipeline_fast_tier1_critical_failure(
        self,
        mock_tier1,
        mock_exists,
    ):
        """Test validation returns early on Tier1 critical failure."""
        mock_exists.return_value = True
        mock_tier1.return_value = {
            "passed": False,
            "critical_failure": True,
            "errors": ["Critical error"],
            "elapsed_seconds": 2.0,
        }

        result = validate_pipeline_fast(
            ms_path="/fake/ms",
            caltables=None,
            image_paths=None,
        )

        assert result.passed is False
        assert len(result.errors) > 0
        # Should not have tier2/tier3 results
        assert result.tier2_results == {}
        assert result.tier3_results == {}
