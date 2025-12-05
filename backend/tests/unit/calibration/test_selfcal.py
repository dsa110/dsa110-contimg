"""
Unit tests for self-calibration module.

Tests cover:
- SelfCalConfig configuration
- SelfCalResult dataclasses
- Image statistics measurement
- Individual selfcal iteration logic
- Full selfcal_ms workflow (mocked)
- New features: per-antenna SNR, chi-squared, gain smoothness, drift-scan mode
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from dsa110_contimg.calibration.selfcal import (
    SelfCalMode,
    SelfCalStatus,
    SelfCalConfig,
    SelfCalIterationResult,
    SelfCalResult,
    _measure_image_stats,
    _get_flagged_fraction,
    _parse_solint_seconds,
    _result_to_dict,
    selfcal_iteration,
    selfcal_ms,
    DEFAULT_PHASE_SOLINTS,
    DEFAULT_AMP_SOLINT,
    DEFAULT_PHASE_ANTENNA_SNR,
    DEFAULT_AMP_ANTENNA_SNR,
    DEFAULT_MAX_PHASE_SCATTER_DEG,
    DEFAULT_MAX_AMP_SCATTER_FRAC,
    DEFAULT_MIN_BEAM_RESPONSE,
)


# =============================================================================
# SelfCalConfig Tests
# =============================================================================


class TestSelfCalConfig:
    """Tests for SelfCalConfig dataclass."""

    def test_default_values(self):
        """Default configuration should have sensible defaults."""
        config = SelfCalConfig()

        assert config.max_iterations == 5
        assert config.min_snr_improvement == 1.05
        assert config.stop_on_divergence is True
        assert config.phase_solints == DEFAULT_PHASE_SOLINTS
        assert config.phase_minsnr == 3.0
        assert config.do_amplitude is True
        assert config.amp_solint == DEFAULT_AMP_SOLINT
        assert config.amp_minsnr == 5.0
        assert config.imsize == 1024
        assert config.backend == "wsclean"
        assert config.min_initial_snr == 5.0

    def test_default_solints_start_long(self):
        """Default phase solution intervals should start long (5min) for L-band."""
        # Perplexity recommendation: start LONG for stable bootstrap
        assert DEFAULT_PHASE_SOLINTS[0] == "300s"  # 5 minutes
        assert DEFAULT_PHASE_SOLINTS[1] == "120s"  # 2 minutes
        assert DEFAULT_PHASE_SOLINTS[2] == "60s"  # 1 minute

    def test_new_config_fields_defaults(self):
        """New configuration fields should have correct defaults."""
        config = SelfCalConfig()

        # Per-antenna SNR thresholds
        assert config.phase_antenna_snr == DEFAULT_PHASE_ANTENNA_SNR
        assert config.amp_antenna_snr == DEFAULT_AMP_ANTENNA_SNR

        # Quality checks enabled by default
        assert config.check_antenna_snr is True
        assert config.check_gain_smoothness is True
        assert config.use_chi_squared is True

        # Gain smoothness thresholds
        assert config.max_phase_scatter_deg == DEFAULT_MAX_PHASE_SCATTER_DEG
        assert config.max_amp_scatter_frac == DEFAULT_MAX_AMP_SCATTER_FRAC

        # Subband and drift-scan
        assert config.combine_spw_phase is False
        assert config.drift_scan_mode is False
        assert config.min_beam_response == DEFAULT_MIN_BEAM_RESPONSE

    def test_custom_values(self):
        """Custom configuration values should be stored correctly."""
        config = SelfCalConfig(
            max_iterations=10,
            min_snr_improvement=1.10,
            phase_solints=["120s", "60s"],
            do_amplitude=False,
            imsize=2048,
            backend="tclean",
            refant="103",
            field="1",
        )

        assert config.max_iterations == 10
        assert config.min_snr_improvement == 1.10
        assert config.phase_solints == ["120s", "60s"]
        assert config.do_amplitude is False
        assert config.imsize == 2048
        assert config.backend == "tclean"
        assert config.refant == "103"
        assert config.field == "1"

    def test_drift_scan_config(self):
        """Drift-scan specific config should be stored correctly."""
        config = SelfCalConfig(
            drift_scan_mode=True,
            min_beam_response=0.7,
            combine_spw_phase=True,
        )

        assert config.drift_scan_mode is True
        assert config.min_beam_response == 0.7
        assert config.combine_spw_phase is True

    def test_phase_solints_independence(self):
        """Default phase_solints should be independent between instances."""
        config1 = SelfCalConfig()
        config2 = SelfCalConfig()

        config1.phase_solints.append("15s")

        assert "15s" not in config2.phase_solints


# =============================================================================
# SelfCalMode and SelfCalStatus Tests
# =============================================================================


class TestSelfCalEnums:
    """Tests for SelfCalMode and SelfCalStatus enums."""

    def test_selfcal_mode_values(self):
        """SelfCalMode should have correct string values."""
        assert SelfCalMode.PHASE.value == "phase"
        assert SelfCalMode.AMPLITUDE_PHASE.value == "ap"

    def test_selfcal_status_values(self):
        """SelfCalStatus should have correct string values."""
        assert SelfCalStatus.SUCCESS.value == "success"
        assert SelfCalStatus.CONVERGED.value == "converged"
        assert SelfCalStatus.MAX_ITERATIONS.value == "max_iterations"
        assert SelfCalStatus.DIVERGED.value == "diverged"
        assert SelfCalStatus.FAILED.value == "failed"
        assert SelfCalStatus.NO_IMPROVEMENT.value == "no_improvement"
        # New status values
        assert SelfCalStatus.LOW_ANTENNA_SNR.value == "low_antenna_snr"
        assert SelfCalStatus.NOISY_GAINS.value == "noisy_gains"


# =============================================================================
# SelfCalIterationResult Tests
# =============================================================================


class TestSelfCalIterationResult:
    """Tests for SelfCalIterationResult dataclass."""

    def test_default_values(self):
        """Iteration result should have correct defaults."""
        result = SelfCalIterationResult(
            iteration=0,
            mode=SelfCalMode.PHASE,
            solint="60s",
            success=False,
        )

        assert result.iteration == 0
        assert result.mode == SelfCalMode.PHASE
        assert result.solint == "60s"
        assert result.success is False
        assert result.snr == 0.0
        assert result.rms == 0.0
        assert result.peak_flux == 0.0
        # New fields should default to 0.0
        assert result.chi_squared == 0.0
        assert result.antenna_snr_median == 0.0
        assert result.antenna_snr_min == 0.0
        assert result.phase_scatter_deg == 0.0
        assert result.amp_scatter_frac == 0.0
        assert result.gaintable is None
        assert result.image_path is None
        assert result.message == ""

    def test_successful_iteration_with_new_metrics(self):
        """Successful iteration should store all metrics including new ones."""
        result = SelfCalIterationResult(
            iteration=2,
            mode=SelfCalMode.AMPLITUDE_PHASE,
            solint="inf",
            success=True,
            snr=150.0,
            rms=1e-5,
            peak_flux=1.5e-3,
            chi_squared=0.95,
            antenna_snr_median=12.5,
            antenna_snr_min=5.2,
            phase_scatter_deg=8.5,
            amp_scatter_frac=0.12,
            gaintable="/data/iter2.cal",
            image_path="/data/iter2.image",
            message="Completed: SNR=150.0",
        )

        assert result.success is True
        assert result.snr == 150.0
        assert result.chi_squared == 0.95
        assert result.antenna_snr_median == 12.5
        assert result.antenna_snr_min == 5.2
        assert result.phase_scatter_deg == 8.5
        assert result.amp_scatter_frac == 0.12

    def test_successful_iteration(self):
        """Successful iteration should store all metrics."""
        result = SelfCalIterationResult(
            iteration=2,
            mode=SelfCalMode.AMPLITUDE_PHASE,
            solint="inf",
            success=True,
            snr=150.0,
            rms=1e-5,
            peak_flux=1.5e-3,
            gaintable="/data/iter2.cal",
            image_path="/data/iter2.image",
            message="Completed: SNR=150.0",
        )

        assert result.success is True
        assert result.snr == 150.0
        assert result.rms == 1e-5
        assert result.peak_flux == 1.5e-3


# =============================================================================
# SelfCalResult Tests
# =============================================================================


class TestSelfCalResult:
    """Tests for SelfCalResult dataclass."""

    def test_default_values(self):
        """Result should have correct defaults."""
        result = SelfCalResult(status=SelfCalStatus.FAILED)

        assert result.status == SelfCalStatus.FAILED
        assert result.iterations_completed == 0
        assert result.initial_snr == 0.0
        assert result.initial_chi_squared == 0.0
        assert result.best_snr == 0.0
        assert result.final_chi_squared == 0.0
        assert result.improvement_factor == 1.0
        assert result.chi_squared_improvement == 1.0
        assert result.iterations == []
        assert result.final_gaintables == []

    def test_successful_result(self):
        """Successful result should store all data."""
        result = SelfCalResult(
            status=SelfCalStatus.SUCCESS,
            iterations_completed=3,
            initial_snr=50.0,
            initial_chi_squared=1.5,
            best_snr=150.0,
            final_snr=150.0,
            final_chi_squared=0.5,
            improvement_factor=3.0,
            chi_squared_improvement=3.0,
            best_iteration=2,
            final_image="/data/final.image",
            final_gaintables=["/data/iter0.cal", "/data/iter1.cal", "/data/iter2.cal"],
            message="success: 3.00x improvement in 3 iterations",
        )

        assert result.status == SelfCalStatus.SUCCESS
        assert result.improvement_factor == 3.0
        assert len(result.final_gaintables) == 3


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestMeasureImageStats:
    """Tests for _measure_image_stats function."""

    def test_fits_image_stats(self):
        """Should measure stats from FITS image."""
        # Create a simple test image
        with tempfile.NamedTemporaryFile(suffix=".fits", delete=False) as f:
            fits_path = f.name

        try:
            from astropy.io import fits

            # Create image with known peak and noise
            nx, ny = 256, 256
            data = np.random.normal(0, 1e-5, (ny, nx))  # Noise with std=1e-5
            data[ny // 2, nx // 2] = 1e-3  # Peak at center

            hdu = fits.PrimaryHDU(data)
            hdu.writeto(fits_path, overwrite=True)

            peak, rms, snr = _measure_image_stats(fits_path)

            assert peak > 0
            assert rms > 0
            assert snr > 0
            # Peak should be approximately our injected value
            assert abs(peak - 1e-3) / 1e-3 < 0.01  # Within 1%

        except ImportError:
            pytest.skip("astropy not available")
        finally:
            Path(fits_path).unlink(missing_ok=True)

    def test_nonexistent_file(self):
        """Should return zeros for nonexistent file."""
        peak, rms, snr = _measure_image_stats("/nonexistent/path.fits")

        assert peak == 0.0
        assert rms == 0.0
        assert snr == 0.0


class TestGetFlaggedFraction:
    """Tests for _get_flagged_fraction function."""

    def test_mock_flagged_fraction(self):
        """Should return flagged fraction from MS."""
        # Create mock table context
        mock_table = MagicMock()
        mock_flags = np.array([[[True, False], [False, False]]])  # 25% flagged
        mock_table.__enter__ = MagicMock(return_value=mock_table)
        mock_table.__exit__ = MagicMock(return_value=False)
        mock_table.getcol = MagicMock(return_value=mock_flags)

        with patch("casacore.tables.table", return_value=mock_table):
            frac = _get_flagged_fraction("/test/ms.ms")
            assert frac == 0.25

    def test_nonexistent_ms(self):
        """Should return 0 for errors."""
        frac = _get_flagged_fraction("/nonexistent/ms.ms")
        assert frac == 0.0


class TestParseSolintSeconds:
    """Tests for _parse_solint_seconds function."""

    def test_seconds_suffix(self):
        """Should parse seconds with 's' suffix."""
        assert _parse_solint_seconds("60s") == 60.0
        assert _parse_solint_seconds("30s") == 30.0
        assert _parse_solint_seconds("300s") == 300.0

    def test_minutes_suffix(self):
        """Should parse minutes with 'min' suffix."""
        assert _parse_solint_seconds("5min") == 300.0
        assert _parse_solint_seconds("2min") == 120.0

    def test_hours_suffix(self):
        """Should parse hours with 'h' suffix."""
        assert _parse_solint_seconds("1h") == 3600.0

    def test_inf_values(self):
        """Should return -1 for infinite solution intervals."""
        assert _parse_solint_seconds("inf") == -1.0
        assert _parse_solint_seconds("INF") == -1.0
        assert _parse_solint_seconds("infinite") == -1.0

    def test_bare_number(self):
        """Should parse bare number as seconds."""
        assert _parse_solint_seconds("120") == 120.0

    def test_whitespace(self):
        """Should handle whitespace."""
        assert _parse_solint_seconds(" 60s ") == 60.0


class TestResultToDict:
    """Tests for _result_to_dict function."""

    def test_empty_result(self):
        """Should serialize empty result."""
        result = SelfCalResult(status=SelfCalStatus.FAILED)
        d = _result_to_dict(result)

        assert d["status"] == "failed"
        assert d["iterations_completed"] == 0
        assert d["iterations"] == []
        # New fields should be present
        assert d["initial_chi_squared"] == 0.0
        assert d["final_chi_squared"] == 0.0
        assert d["chi_squared_improvement"] == 1.0

    def test_full_result(self):
        """Should serialize complete result."""
        iter_result = SelfCalIterationResult(
            iteration=0,
            mode=SelfCalMode.PHASE,
            solint="60s",
            success=True,
            snr=100.0,
            chi_squared=0.8,
            antenna_snr_median=8.5,
            antenna_snr_min=4.2,
            phase_scatter_deg=12.0,
            amp_scatter_frac=0.15,
        )

        result = SelfCalResult(
            status=SelfCalStatus.SUCCESS,
            iterations_completed=1,
            initial_snr=50.0,
            initial_chi_squared=1.2,
            best_snr=100.0,
            final_chi_squared=0.8,
            chi_squared_improvement=1.5,
            iterations=[iter_result],
        )

        d = _result_to_dict(result)

        assert d["status"] == "success"
        assert d["initial_snr"] == 50.0
        assert d["initial_chi_squared"] == 1.2
        assert d["chi_squared_improvement"] == 1.5
        assert len(d["iterations"]) == 1
        assert d["iterations"][0]["mode"] == "phase"
        assert d["iterations"][0]["snr"] == 100.0
        # New iteration fields
        assert d["iterations"][0]["chi_squared"] == 0.8
        assert d["iterations"][0]["antenna_snr_median"] == 8.5
        assert d["iterations"][0]["antenna_snr_min"] == 4.2
        assert d["iterations"][0]["phase_scatter_deg"] == 12.0
        assert d["iterations"][0]["amp_scatter_frac"] == 0.15


# =============================================================================
# Selfcal Iteration Tests (Mocked)
# =============================================================================


class TestSelfcalIteration:
    """Tests for selfcal_iteration function with mocks."""

    @patch("dsa110_contimg.calibration.selfcal._run_imaging")
    @patch("dsa110_contimg.calibration.selfcal._measure_image_stats")
    @patch("dsa110_contimg.calibration.selfcal._predict_model_wsclean")
    @patch("dsa110_contimg.calibration.selfcal._run_gaincal")
    @patch("dsa110_contimg.calibration.selfcal._apply_calibration")
    def test_successful_iteration(
        self,
        mock_apply,
        mock_gaincal,
        mock_predict,
        mock_stats,
        mock_imaging,
    ):
        """Successful iteration should return success with metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mocks
            mock_imaging.return_value = f"{tmpdir}/iter0.image"
            mock_stats.return_value = (1e-3, 1e-5, 100.0)  # peak, rms, snr
            mock_predict.return_value = True
            mock_gaincal.return_value = True
            mock_apply.return_value = True

            config = SelfCalConfig(backend="wsclean")

            result = selfcal_iteration(
                ms_path="/test/ms.ms",
                output_dir=tmpdir,
                iteration=0,
                mode=SelfCalMode.PHASE,
                solint="60s",
                config=config,
            )

            assert result.success is True
            assert result.snr == 100.0
            assert result.iteration == 0
            assert result.mode == SelfCalMode.PHASE

    @patch("dsa110_contimg.calibration.selfcal._run_imaging")
    def test_failed_imaging(self, mock_imaging):
        """Failed imaging should return failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_imaging.return_value = None

            config = SelfCalConfig()

            result = selfcal_iteration(
                ms_path="/test/ms.ms",
                output_dir=tmpdir,
                iteration=0,
                mode=SelfCalMode.PHASE,
                solint="60s",
                config=config,
            )

            assert result.success is False
            assert "Imaging failed" in result.message

    @patch("dsa110_contimg.calibration.selfcal._run_imaging")
    @patch("dsa110_contimg.calibration.selfcal._measure_image_stats")
    @patch("dsa110_contimg.calibration.selfcal._predict_model_wsclean")
    @patch("dsa110_contimg.calibration.selfcal._run_gaincal")
    def test_failed_gaincal(
        self,
        mock_gaincal,
        mock_predict,
        mock_stats,
        mock_imaging,
    ):
        """Failed gaincal should return failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_imaging.return_value = f"{tmpdir}/iter0.image"
            mock_stats.return_value = (1e-3, 1e-5, 100.0)
            mock_predict.return_value = True
            mock_gaincal.return_value = False

            config = SelfCalConfig()

            result = selfcal_iteration(
                ms_path="/test/ms.ms",
                output_dir=tmpdir,
                iteration=0,
                mode=SelfCalMode.PHASE,
                solint="60s",
                config=config,
            )

            assert result.success is False
            assert "Gaincal failed" in result.message


# =============================================================================
# Full Selfcal Tests (Mocked)
# =============================================================================


class TestSelfcalMs:
    """Tests for selfcal_ms function with mocks."""

    @patch("dsa110_contimg.calibration.selfcal._get_flagged_fraction")
    @patch("dsa110_contimg.calibration.selfcal._apply_calibration")
    @patch("dsa110_contimg.calibration.selfcal._run_imaging")
    @patch("dsa110_contimg.calibration.selfcal._measure_image_stats")
    @patch("dsa110_contimg.calibration.selfcal.selfcal_iteration")
    def test_successful_selfcal(
        self,
        mock_iteration,
        mock_stats,
        mock_imaging,
        mock_apply,
        mock_flagged,
    ):
        """Successful selfcal should return improvement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mocks
            mock_flagged.return_value = 0.1  # 10% flagged
            mock_apply.return_value = True
            mock_imaging.return_value = f"{tmpdir}/initial.image"
            mock_stats.return_value = (1e-3, 1e-5, 100.0)  # Initial SNR=100

            # Each iteration improves SNR
            mock_iteration.side_effect = [
                SelfCalIterationResult(
                    iteration=0,
                    mode=SelfCalMode.PHASE,
                    solint="60s",
                    success=True,
                    snr=120.0,
                    gaintable=f"{tmpdir}/iter0.cal",
                    image_path=f"{tmpdir}/iter0.image",
                ),
                SelfCalIterationResult(
                    iteration=1,
                    mode=SelfCalMode.PHASE,
                    solint="30s",
                    success=True,
                    snr=140.0,
                    gaintable=f"{tmpdir}/iter1.cal",
                    image_path=f"{tmpdir}/iter1.image",
                ),
                SelfCalIterationResult(
                    iteration=2,
                    mode=SelfCalMode.PHASE,
                    solint="inf",
                    success=True,
                    snr=150.0,
                    gaintable=f"{tmpdir}/iter2.cal",
                    image_path=f"{tmpdir}/iter2.image",
                ),
                SelfCalIterationResult(
                    iteration=3,
                    mode=SelfCalMode.AMPLITUDE_PHASE,
                    solint="inf",
                    success=True,
                    snr=160.0,
                    gaintable=f"{tmpdir}/iter3.cal",
                    image_path=f"{tmpdir}/iter3.image",
                ),
            ]

            config = SelfCalConfig(
                phase_solints=["60s", "30s", "inf"],
                do_amplitude=True,
            )

            success, summary = selfcal_ms(
                ms_path="/test/ms.ms",
                output_dir=tmpdir,
                config=config,
            )

            assert success is True
            assert summary["status"] == "success"
            assert summary["improvement_factor"] > 1.0
            assert summary["iterations_completed"] == 4

    @patch("dsa110_contimg.calibration.selfcal._get_flagged_fraction")
    def test_too_much_flagging(self, mock_flagged):
        """Should fail if too much data is flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_flagged.return_value = 0.9  # 90% flagged

            config = SelfCalConfig(max_flagged_fraction=0.5)

            success, summary = selfcal_ms(
                ms_path="/test/ms.ms",
                output_dir=tmpdir,
                config=config,
            )

            assert success is False
            assert "flagged" in summary["message"].lower()

    @patch("dsa110_contimg.calibration.selfcal._get_flagged_fraction")
    @patch("dsa110_contimg.calibration.selfcal._apply_calibration")
    @patch("dsa110_contimg.calibration.selfcal._run_imaging")
    @patch("dsa110_contimg.calibration.selfcal._measure_image_stats")
    def test_low_initial_snr(
        self,
        mock_stats,
        mock_imaging,
        mock_apply,
        mock_flagged,
    ):
        """Should fail if initial SNR is too low."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_flagged.return_value = 0.1
            mock_apply.return_value = True
            mock_imaging.return_value = f"{tmpdir}/initial.image"
            mock_stats.return_value = (1e-5, 1e-5, 1.0)  # SNR=1, too low

            config = SelfCalConfig(min_initial_snr=5.0)

            success, summary = selfcal_ms(
                ms_path="/test/ms.ms",
                output_dir=tmpdir,
                config=config,
            )

            assert success is False
            assert "snr" in summary["message"].lower()

    @patch("dsa110_contimg.calibration.selfcal._get_flagged_fraction")
    @patch("dsa110_contimg.calibration.selfcal._apply_calibration")
    @patch("dsa110_contimg.calibration.selfcal._run_imaging")
    @patch("dsa110_contimg.calibration.selfcal._measure_image_stats")
    @patch("dsa110_contimg.calibration.selfcal.selfcal_iteration")
    def test_divergence_stops_selfcal(
        self,
        mock_iteration,
        mock_stats,
        mock_imaging,
        mock_apply,
        mock_flagged,
    ):
        """Should stop if SNR diverges."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_flagged.return_value = 0.1
            mock_apply.return_value = True
            mock_imaging.return_value = f"{tmpdir}/initial.image"
            mock_stats.return_value = (1e-3, 1e-5, 100.0)  # Initial SNR=100

            # First iteration improves, second diverges, then amplitude (but won't be called)
            mock_iteration.side_effect = [
                SelfCalIterationResult(
                    iteration=0,
                    mode=SelfCalMode.PHASE,
                    solint="60s",
                    success=True,
                    snr=120.0,
                    gaintable=f"{tmpdir}/iter0.cal",
                    image_path=f"{tmpdir}/iter0.image",
                ),
                SelfCalIterationResult(
                    iteration=1,
                    mode=SelfCalMode.PHASE,
                    solint="30s",
                    success=True,
                    snr=80.0,  # SNR decreased!
                    gaintable=f"{tmpdir}/iter1.cal",
                    image_path=f"{tmpdir}/iter1.image",
                ),
                # Won't be called due to divergence stop
                SelfCalIterationResult(
                    iteration=2,
                    mode=SelfCalMode.PHASE,
                    solint="inf",
                    success=True,
                    snr=90.0,
                    gaintable=f"{tmpdir}/iter2.cal",
                    image_path=f"{tmpdir}/iter2.image",
                ),
                SelfCalIterationResult(
                    iteration=3,
                    mode=SelfCalMode.AMPLITUDE_PHASE,
                    solint="inf",
                    success=True,
                    snr=100.0,
                    gaintable=f"{tmpdir}/iter3.cal",
                    image_path=f"{tmpdir}/iter3.image",
                ),
            ]

            config = SelfCalConfig(
                phase_solints=["60s", "30s", "inf"],
                stop_on_divergence=True,
                do_amplitude=False,  # Disable amplitude to avoid extra iterations
            )

            success, summary = selfcal_ms(
                ms_path="/test/ms.ms",
                output_dir=tmpdir,
                config=config,
            )

            # Should have stopped after detecting divergence
            # Note: iterations_completed tracks loop counter when break occurs
            # which is 1 (started at 0, incremented once before detecting divergence)
            assert summary["status"] == "diverged"
            assert summary["iterations_completed"] >= 1  # At least one iteration ran


# =============================================================================
# Integration with Pipeline Stage
# =============================================================================


class TestSelfCalibrationStageIntegration:
    """Test that SelfCalibrationStage can import and use selfcal module."""

    def test_stage_imports(self):
        """SelfCalibrationStage should be importable."""
        from dsa110_contimg.pipeline.stages_impl import SelfCalibrationStage

        assert SelfCalibrationStage is not None

    def test_stage_get_name(self):
        """Stage should return correct name."""
        from dsa110_contimg.pipeline.stages_impl import SelfCalibrationStage
        from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig

        paths = PathsConfig(
            output_dir="/tmp/test",
            uvh5_dir="/tmp/uvh5",
            ms_dir="/tmp/ms",
            input_dir="/tmp/input",
        )
        config = PipelineConfig(paths=paths)

        stage = SelfCalibrationStage(config)
        assert stage.get_name() == "selfcal"


# =============================================================================
# Module Export Tests
# =============================================================================


class TestModuleExports:
    """Test that all exports are available."""

    def test_calibration_module_exports(self):
        """All selfcal classes should be exported from calibration module."""
        from dsa110_contimg.calibration import (
            SelfCalMode,
            SelfCalStatus,
            SelfCalConfig,
            SelfCalIterationResult,
            SelfCalResult,
            selfcal_iteration,
            selfcal_ms,
        )

        assert SelfCalMode is not None
        assert SelfCalStatus is not None
        assert SelfCalConfig is not None
        assert SelfCalIterationResult is not None
        assert SelfCalResult is not None
        assert selfcal_iteration is not None
        assert selfcal_ms is not None
