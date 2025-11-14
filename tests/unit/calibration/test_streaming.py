"""Unit tests for streaming calibration utilities."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from dsa110_contimg.calibration.streaming import has_calibrator, solve_calibration_for_ms


class TestHasCalibrator:
    """Test calibrator detection function."""

    @patch("dsa110_contimg.calibration.catalogs.load_vla_catalog")
    @patch("dsa110_contimg.pointing.utils.load_pointing")
    @patch("dsa110_contimg.utils.time_utils.extract_ms_time_range")
    @patch("dsa110_contimg.calibration.catalogs.calibrator_match")
    def test_has_calibrator_success(self, mock_match, mock_time, mock_pointing, mock_catalog):
        """Test successful calibrator detection."""
        # Setup mocks
        mock_catalog.return_value = Mock(empty=False)
        mock_pointing.return_value = {"dec_deg": 50.0}
        mock_time.return_value = (60000.0, 60001.0, 60000.5)
        mock_match.return_value = [{"name": "3C286", "ra_deg": 200.0, "dec_deg": 50.0}]

        result = has_calibrator("/path/to/test.ms")

        assert result is True
        mock_catalog.assert_called_once()
        mock_pointing.assert_called_once_with("/path/to/test.ms")
        mock_time.assert_called_once_with("/path/to/test.ms")
        mock_match.assert_called_once()

    @patch("dsa110_contimg.calibration.catalogs.load_vla_catalog")
    @patch("dsa110_contimg.pointing.utils.load_pointing")
    @patch("dsa110_contimg.utils.time_utils.extract_ms_time_range")
    @patch("dsa110_contimg.calibration.catalogs.calibrator_match")
    def test_has_calibrator_no_match(self, mock_match, mock_time, mock_pointing, mock_catalog):
        """Test when no calibrator match is found."""
        mock_catalog.return_value = Mock(empty=False)
        mock_pointing.return_value = {"dec_deg": 50.0}
        mock_time.return_value = (60000.0, 60001.0, 60000.5)
        mock_match.return_value = []

        result = has_calibrator("/path/to/test.ms")

        assert result is False

    @patch("dsa110_contimg.calibration.catalogs.load_vla_catalog")
    def test_has_calibrator_empty_catalog(self, mock_catalog):
        """Test when catalog is empty."""
        mock_catalog.return_value = Mock(empty=True)

        result = has_calibrator("/path/to/test.ms")

        assert result is False

    @patch("dsa110_contimg.calibration.catalogs.load_vla_catalog")
    @patch("dsa110_contimg.pointing.utils.load_pointing")
    def test_has_calibrator_no_pointing(self, mock_pointing, mock_catalog):
        """Test when pointing cannot be read."""
        mock_catalog.return_value = Mock(empty=False)
        mock_pointing.return_value = None

        result = has_calibrator("/path/to/test.ms")

        assert result is False

    @patch("dsa110_contimg.calibration.catalogs.load_vla_catalog")
    def test_has_calibrator_exception(self, mock_catalog):
        """Test exception handling."""
        mock_catalog.side_effect = Exception("Catalog load failed")

        result = has_calibrator("/path/to/test.ms")

        assert result is False


class TestSolveCalibrationForMs:
    """Test calibration solving function."""

    @patch("dsa110_contimg.calibration.cli.run_calibrator")
    @patch("dsa110_contimg.calibration.selection.select_bandpass_from_catalog")
    @patch("dsa110_contimg.calibration.refant_selection.get_default_outrigger_refants")
    def test_solve_calibration_success_with_auto_detect(self, mock_refant, mock_select, mock_run):
        """Test successful calibration solve with auto-detection."""
        mock_select.return_value = ("0~2", [0, 1, 2], Mock(), ("3C286", 200.0, 50.0, 10.0), 1)
        mock_refant.return_value = "104,105,106"
        mock_run.return_value = ["/path/to/bp.cal", "/path/to/g.cal"]

        success, error = solve_calibration_for_ms("/path/to/test.ms")

        assert success is True
        assert error is None
        mock_select.assert_called_once()
        mock_refant.assert_called_once()
        mock_run.assert_called_once_with(
            "/path/to/test.ms", "0~2", "104,105,106", do_flagging=True, do_k=False
        )

    @patch("dsa110_contimg.calibration.cli.run_calibrator")
    def test_solve_calibration_success_with_provided_params(self, mock_run):
        """Test successful calibration solve with provided parameters."""
        mock_run.return_value = ["/path/to/bp.cal", "/path/to/g.cal"]

        success, error = solve_calibration_for_ms("/path/to/test.ms", cal_field="0", refant="104")

        assert success is True
        assert error is None
        mock_run.assert_called_once_with(
            "/path/to/test.ms", "0", "104", do_flagging=True, do_k=False
        )

    @patch("dsa110_contimg.calibration.cli.run_calibrator")
    @patch("dsa110_contimg.calibration.selection.select_bandpass_from_catalog")
    @patch("dsa110_contimg.calibration.refant_selection.get_default_outrigger_refants")
    def test_solve_calibration_no_field_detected(self, mock_refant, mock_select, mock_run):
        """Test when calibrator field cannot be detected."""
        mock_select.return_value = ("", [], Mock(), ("", 0.0, 0.0, 0.0), -1)

        success, error = solve_calibration_for_ms("/path/to/test.ms")

        assert success is False
        assert error is not None
        assert "Could not auto-detect calibrator field" in error
        mock_run.assert_not_called()

    @patch("dsa110_contimg.calibration.cli.run_calibrator")
    @patch("dsa110_contimg.calibration.selection.select_bandpass_from_catalog")
    @patch("dsa110_contimg.calibration.refant_selection.get_default_outrigger_refants")
    def test_solve_calibration_no_tables_produced(self, mock_refant, mock_select, mock_run):
        """Test when calibration solve produces no tables."""
        mock_select.return_value = ("0", [0], Mock(), ("3C286", 200.0, 50.0, 10.0), 0)
        mock_refant.return_value = "104"
        mock_run.return_value = []

        success, error = solve_calibration_for_ms("/path/to/test.ms")

        assert success is False
        assert error is not None
        assert "no calibration tables were produced" in error

    @patch("dsa110_contimg.calibration.cli.run_calibrator")
    @patch("dsa110_contimg.calibration.selection.select_bandpass_from_catalog")
    @patch("dsa110_contimg.calibration.refant_selection.get_default_outrigger_refants")
    def test_solve_calibration_exception(self, mock_refant, mock_select, mock_run):
        """Test exception handling."""
        mock_select.side_effect = Exception("Selection failed")

        success, error = solve_calibration_for_ms("/path/to/test.ms")

        assert success is False
        assert error is not None
        assert (
            "Calibration solve failed" in error or "Failed to auto-detect calibrator field" in error
        )
        mock_select.assert_called_once()

    @patch("dsa110_contimg.calibration.cli.run_calibrator")
    def test_solve_calibration_with_k_calibration(self, mock_run):
        """Test calibration solve with K-calibration enabled."""
        mock_run.return_value = ["/path/to/k.cal", "/path/to/bp.cal", "/path/to/g.cal"]

        success, error = solve_calibration_for_ms(
            "/path/to/test.ms", cal_field="0", refant="104", do_k=True
        )

        assert success is True
        assert error is None
        mock_run.assert_called_once_with(
            "/path/to/test.ms", "0", "104", do_flagging=True, do_k=True
        )
