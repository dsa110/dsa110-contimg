"""
Unit tests for calibration QA module.

Tests cover:
- QAThresholds dataclass
- CalibrationMetrics dataclass
- CalibrationQAResult dataclass
- compute_calibration_metrics function
- assess_calibration_quality function
- CalibrationQAStore persistence
- Edge cases and error handling
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from dsa110_contimg.calibration.qa import (
    DEFAULT_MAX_AMPLITUDE,
    DEFAULT_MAX_FLAG_FRACTION,
    DEFAULT_MAX_PHASE_SCATTER_DEG,
    DEFAULT_MIN_AMPLITUDE,
    DEFAULT_MIN_SNR,
    CalibrationMetrics,
    CalibrationQAResult,
    CalibrationQAStore,
    QAIssue,
    QAThresholds,
    assess_calibration_quality,
    close_qa_store,
    compute_calibration_metrics,
    get_qa_store,
)


# ============================================================================
# QAThresholds Tests
# ============================================================================


class TestQAThresholds:
    """Tests for QAThresholds dataclass."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        thresholds = QAThresholds()

        assert thresholds.min_snr == DEFAULT_MIN_SNR
        assert thresholds.max_flag_fraction == DEFAULT_MAX_FLAG_FRACTION
        assert thresholds.min_amplitude == DEFAULT_MIN_AMPLITUDE
        assert thresholds.max_amplitude == DEFAULT_MAX_AMPLITUDE
        assert thresholds.max_phase_scatter_deg == DEFAULT_MAX_PHASE_SCATTER_DEG

    def test_custom_thresholds(self):
        """Test custom threshold values."""
        thresholds = QAThresholds(
            min_snr=5.0,
            max_flag_fraction=0.2,
            min_amplitude=0.5,
            max_amplitude=5.0,
            max_phase_scatter_deg=15.0,
        )

        assert thresholds.min_snr == 5.0
        assert thresholds.max_flag_fraction == 0.2
        assert thresholds.min_amplitude == 0.5
        assert thresholds.max_amplitude == 5.0
        assert thresholds.max_phase_scatter_deg == 15.0


# ============================================================================
# CalibrationMetrics Tests
# ============================================================================


class TestCalibrationMetrics:
    """Tests for CalibrationMetrics dataclass."""

    def test_default_metrics(self):
        """Test default metric values."""
        metrics = CalibrationMetrics(caltable_path="/path/to/cal.bp", cal_type="bp")

        assert metrics.caltable_path == "/path/to/cal.bp"
        assert metrics.cal_type == "bp"
        assert metrics.n_solutions == 0
        assert metrics.n_flagged == 0
        assert metrics.flag_fraction == 0.0
        assert metrics.extraction_error is None

    def test_is_valid_property(self):
        """Test is_valid property."""
        # Valid metrics
        valid_metrics = CalibrationMetrics(
            caltable_path="/path/to/cal",
            cal_type="bp",
            n_solutions=100,
            extraction_error=None,
        )
        assert valid_metrics.is_valid is True

        # Invalid - no solutions
        no_solutions = CalibrationMetrics(
            caltable_path="/path/to/cal",
            cal_type="bp",
            n_solutions=0,
            extraction_error=None,
        )
        assert no_solutions.is_valid is False

        # Invalid - extraction error
        error_metrics = CalibrationMetrics(
            caltable_path="/path/to/cal",
            cal_type="bp",
            n_solutions=100,
            extraction_error="Failed to read table",
        )
        assert error_metrics.is_valid is False

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        metrics = CalibrationMetrics(
            caltable_path="/path/to/cal.g",
            cal_type="g",
            n_solutions=500,
            n_flagged=50,
            flag_fraction=0.1,
            mean_amplitude=1.05,
            std_amplitude=0.02,
            median_snr=15.5,
        )

        as_dict = metrics.to_dict()
        restored = CalibrationMetrics.from_dict(as_dict)

        assert restored.caltable_path == metrics.caltable_path
        assert restored.cal_type == metrics.cal_type
        assert restored.n_solutions == metrics.n_solutions
        assert restored.flag_fraction == metrics.flag_fraction
        assert restored.median_snr == metrics.median_snr


# ============================================================================
# QAIssue Tests
# ============================================================================


class TestQAIssue:
    """Tests for QAIssue dataclass."""

    def test_issue_creation(self):
        """Test creating QA issues."""
        issue = QAIssue(
            severity="warning",
            cal_type="bp",
            metric="flagging",
            value=0.35,
            threshold=0.3,
            message="BP table: High flagging (35% > 30%)",
        )

        assert issue.severity == "warning"
        assert issue.cal_type == "bp"
        assert issue.metric == "flagging"
        assert issue.value == 0.35
        assert issue.threshold == 0.3
        assert "High flagging" in issue.message


# ============================================================================
# CalibrationQAResult Tests
# ============================================================================


class TestCalibrationQAResult:
    """Tests for CalibrationQAResult dataclass."""

    def test_default_result(self):
        """Test default result values."""
        result = CalibrationQAResult(
            ms_path="/path/to/ms",
            passed=True,
            severity="success",
            overall_grade="excellent",
        )

        assert result.ms_path == "/path/to/ms"
        assert result.passed is True
        assert result.severity == "success"
        assert result.overall_grade == "excellent"
        assert result.issues == []
        assert result.metrics == []

    def test_warnings_and_errors_properties(self):
        """Test warnings and errors property methods."""
        result = CalibrationQAResult(
            ms_path="/path/to/ms",
            passed=False,
            severity="error",
            overall_grade="failed",
            issues=[
                QAIssue(
                    severity="error",
                    cal_type="bp",
                    metric="snr",
                    value=1.5,
                    threshold=3.0,
                    message="Low SNR",
                ),
                QAIssue(
                    severity="warning",
                    cal_type="g",
                    metric="flagging",
                    value=0.35,
                    threshold=0.3,
                    message="High flagging",
                ),
                QAIssue(
                    severity="warning",
                    cal_type="bp",
                    metric="amplitude",
                    value=0.05,
                    threshold=0.1,
                    message="Low amplitude",
                ),
            ],
        )

        assert len(result.errors) == 1
        assert "Low SNR" in result.errors[0]
        assert len(result.warnings) == 2

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        metrics = CalibrationMetrics(
            caltable_path="/path/to/cal.bp",
            cal_type="bp",
            n_solutions=100,
        )
        issue = QAIssue(
            severity="warning",
            cal_type="bp",
            metric="flagging",
            value=0.35,
            threshold=0.3,
            message="High flagging",
        )

        original = CalibrationQAResult(
            ms_path="/path/to/ms",
            passed=True,
            severity="warning",
            overall_grade="good",
            issues=[issue],
            metrics=[metrics],
            summary={"n_tables": 1, "n_warnings": 1},
            assessment_time_s=0.5,
            timestamp=1234567890.0,
        )

        as_dict = original.to_dict()
        restored = CalibrationQAResult.from_dict(as_dict)

        assert restored.ms_path == original.ms_path
        assert restored.passed == original.passed
        assert restored.severity == original.severity
        assert restored.overall_grade == original.overall_grade
        assert len(restored.issues) == 1
        assert len(restored.metrics) == 1
        assert restored.summary["n_tables"] == 1


# ============================================================================
# compute_calibration_metrics Tests
# ============================================================================


class TestComputeCalibrationMetrics:
    """Tests for compute_calibration_metrics function."""

    def test_nonexistent_file(self):
        """Test handling of nonexistent caltable."""
        metrics = compute_calibration_metrics("/nonexistent/path/to/cal.bp")

        assert metrics.is_valid is False
        assert "not found" in metrics.extraction_error

    def test_cal_type_auto_detection(self):
        """Test automatic cal_type detection from filename."""
        # K table
        metrics_k = compute_calibration_metrics("/path/to/test.kcal")
        assert metrics_k.cal_type == "k"

        # BP table
        metrics_bp = compute_calibration_metrics("/path/to/test.bpcal")
        assert metrics_bp.cal_type == "bp"

        # G table
        metrics_g = compute_calibration_metrics("/path/to/test.gpcal")
        assert metrics_g.cal_type == "g"

        # Unknown
        metrics_unknown = compute_calibration_metrics("/path/to/test.unknown")
        assert metrics_unknown.cal_type == "unknown"

    @patch("dsa110_contimg.calibration.qa._open_caltable")
    def test_complex_gains_extraction(self, mock_open):
        """Test extraction of complex gains (CPARAM)."""
        # Create mock table
        mock_table = MagicMock()
        mock_table.colnames.return_value = ["CPARAM", "FLAG", "SNR", "ANTENNA1", "SPECTRAL_WINDOW_ID"]

        # Generate test data
        n_ant = 10
        n_chan = 48
        n_pol = 2
        gains = np.ones((n_pol, n_chan, n_ant), dtype=complex) * (1.0 + 0.1j)
        flags = np.zeros_like(gains, dtype=bool)
        flags[:, :5, :] = True  # Flag first 5 channels
        snr_data = np.ones_like(gains, dtype=float) * 10.0

        mock_table.getcol.side_effect = lambda col: {
            "CPARAM": gains,
            "FLAG": flags,
            "SNR": snr_data,
            "ANTENNA1": np.arange(n_ant),
            "SPECTRAL_WINDOW_ID": np.zeros(n_ant, dtype=int),
        }[col]

        mock_open.return_value = mock_table

        with tempfile.NamedTemporaryFile(suffix=".bpcal") as tmp_file:
            # Create temp file so path exists check passes
            metrics = compute_calibration_metrics(tmp_file.name)

        assert metrics.is_valid is True
        assert metrics.n_solutions == n_pol * n_chan * n_ant
        # 5 channels flagged across all antennas and pols
        expected_flagged = n_pol * 5 * n_ant
        assert metrics.n_flagged == expected_flagged
        assert metrics.flag_fraction == pytest.approx(expected_flagged / (n_pol * n_chan * n_ant))
        assert metrics.median_snr == pytest.approx(10.0)

    @patch("dsa110_contimg.calibration.qa._open_caltable")
    def test_float_gains_extraction(self, mock_open):
        """Test extraction of float gains (FPARAM) for K tables."""
        mock_table = MagicMock()
        mock_table.colnames.return_value = ["FPARAM", "FLAG", "ANTENNA1"]

        n_ant = 10
        delays = np.random.uniform(-5, 5, (1, 1, n_ant))
        flags = np.zeros_like(delays, dtype=bool)

        mock_table.getcol.side_effect = lambda col: {
            "FPARAM": delays,
            "FLAG": flags,
            "ANTENNA1": np.arange(n_ant),
        }[col]

        mock_open.return_value = mock_table

        with tempfile.NamedTemporaryFile(suffix=".kcal") as tmp_file:
            metrics = compute_calibration_metrics(tmp_file.name, cal_type="k")

        assert metrics.is_valid is True
        assert metrics.cal_type == "k"
        assert metrics.n_solutions == n_ant

    @patch("dsa110_contimg.calibration.qa._open_caltable")
    def test_table_read_error(self, mock_open):
        """Test handling of table read errors."""
        mock_open.side_effect = RuntimeError("Failed to open table")

        with tempfile.NamedTemporaryFile(suffix=".bpcal") as tmp_file:
            metrics = compute_calibration_metrics(tmp_file.name)

        assert metrics.is_valid is False
        assert "Failed to open table" in metrics.extraction_error


# ============================================================================
# assess_calibration_quality Tests
# ============================================================================


class TestAssessCalibrationQuality:
    """Tests for assess_calibration_quality function."""

    @patch("dsa110_contimg.calibration.qa.compute_calibration_metrics")
    @patch("dsa110_contimg.calibration.caltables.discover_caltables")
    def test_missing_tables(self, mock_discover, mock_compute):
        """Test assessment when required tables are missing."""
        mock_discover.return_value = {"k": None, "bp": None, "g": None}

        result = assess_calibration_quality("/path/to/ms")

        assert result.passed is False
        assert result.severity == "error"
        assert result.overall_grade == "failed"
        assert len(result.errors) == 1
        assert "Missing required" in result.errors[0]

    @patch("dsa110_contimg.calibration.qa.compute_calibration_metrics")
    @patch("dsa110_contimg.calibration.caltables.discover_caltables")
    def test_excellent_quality(self, mock_discover, mock_compute):
        """Test assessment with excellent quality tables."""
        mock_discover.return_value = {
            "k": "/path/to/k.cal",
            "bp": "/path/to/bp.cal",
            "g": "/path/to/g.cal",
        }

        mock_compute.side_effect = lambda path, cal_type=None: CalibrationMetrics(
            caltable_path=path,
            cal_type=cal_type or "bp",
            n_solutions=1000,
            n_flagged=50,  # 5% flagging
            flag_fraction=0.05,
            mean_amplitude=1.0,
            std_amplitude=0.02,
            median_amplitude=1.0,
            max_amplitude=1.5,
            median_phase_deg=0.0,
            phase_scatter_deg=5.0,
            median_snr=20.0,
        )

        result = assess_calibration_quality("/path/to/ms")

        assert result.passed is True
        assert result.severity == "success"
        assert result.overall_grade == "excellent"
        assert len(result.issues) == 0

    @patch("dsa110_contimg.calibration.qa.compute_calibration_metrics")
    @patch("dsa110_contimg.calibration.caltables.discover_caltables")
    def test_low_snr_failure(self, mock_discover, mock_compute):
        """Test assessment with low SNR tables."""
        mock_discover.return_value = {
            "bp": "/path/to/bp.cal",
            "g": "/path/to/g.cal",
        }

        mock_compute.side_effect = lambda path, cal_type=None: CalibrationMetrics(
            caltable_path=path,
            cal_type=cal_type or "bp",
            n_solutions=1000,
            flag_fraction=0.05,
            mean_amplitude=1.0,
            max_amplitude=1.5,
            median_snr=1.5,  # Below threshold of 3.0
        )

        result = assess_calibration_quality("/path/to/ms")

        assert result.passed is False
        assert result.severity == "error"
        assert any("Low SNR" in e for e in result.errors)

    @patch("dsa110_contimg.calibration.qa.compute_calibration_metrics")
    @patch("dsa110_contimg.calibration.caltables.discover_caltables")
    def test_high_flagging_warning(self, mock_discover, mock_compute):
        """Test assessment with high flagging (warning level)."""
        mock_discover.return_value = {
            "bp": "/path/to/bp.cal",
            "g": "/path/to/g.cal",
        }

        mock_compute.side_effect = lambda path, cal_type=None: CalibrationMetrics(
            caltable_path=path,
            cal_type=cal_type or "bp",
            n_solutions=1000,
            flag_fraction=0.35,  # Above 0.3 threshold but below 0.5 error
            mean_amplitude=1.0,
            max_amplitude=1.5,
            median_snr=20.0,
        )

        result = assess_calibration_quality("/path/to/ms")

        assert result.passed is True  # Warning doesn't cause failure
        assert result.severity == "warning"
        assert len(result.warnings) > 0
        assert any("High flagging" in w for w in result.warnings)

    @patch("dsa110_contimg.calibration.qa.compute_calibration_metrics")
    @patch("dsa110_contimg.calibration.caltables.discover_caltables")
    def test_custom_thresholds(self, mock_discover, mock_compute):
        """Test assessment with custom thresholds."""
        mock_discover.return_value = {
            "bp": "/path/to/bp.cal",
            "g": "/path/to/g.cal",
        }

        mock_compute.side_effect = lambda path, cal_type=None: CalibrationMetrics(
            caltable_path=path,
            cal_type=cal_type or "bp",
            n_solutions=1000,
            flag_fraction=0.05,
            mean_amplitude=1.0,
            max_amplitude=1.5,
            median_snr=4.0,  # Would pass default (3.0) but fail custom (5.0)
        )

        custom_thresholds = QAThresholds(min_snr=5.0)
        result = assess_calibration_quality("/path/to/ms", thresholds=custom_thresholds)

        assert result.passed is False
        assert any("Low SNR" in e for e in result.errors)

    @patch("dsa110_contimg.calibration.qa.compute_calibration_metrics")
    def test_provided_caltables(self, mock_compute):
        """Test assessment with pre-provided caltables dict."""
        mock_compute.side_effect = lambda path, cal_type=None: CalibrationMetrics(
            caltable_path=path,
            cal_type=cal_type or "bp",
            n_solutions=1000,
            flag_fraction=0.05,
            mean_amplitude=1.0,
            max_amplitude=1.5,
            median_snr=20.0,
        )

        caltables = {
            "bp": "/custom/path/to/bp.cal",
            "g": "/custom/path/to/g.cal",
        }

        result = assess_calibration_quality("/path/to/ms", caltables=caltables)

        assert result.passed is True
        assert len(result.metrics) == 2


# ============================================================================
# CalibrationQAStore Tests
# ============================================================================


class TestCalibrationQAStore:
    """Tests for CalibrationQAStore persistence."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp_file:
            db_path = tmp_file.name

        yield db_path

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_init_creates_table(self, temp_db):
        """Test that initialization creates the required table."""
        store = CalibrationQAStore(db_path=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='calibration_qa'"
            )
            assert cursor.fetchone() is not None

    def test_save_and_get_result(self, temp_db):
        """Test saving and retrieving a QA result."""
        store = CalibrationQAStore(db_path=temp_db)

        result = CalibrationQAResult(
            ms_path="/path/to/test.ms",
            passed=True,
            severity="success",
            overall_grade="excellent",
            summary={"n_tables": 2, "n_warnings": 0, "n_errors": 0, "avg_flag_fraction": 0.05},
            assessment_time_s=0.5,
            timestamp=time.time(),
        )

        row_id = store.save_result(result)
        assert row_id > 0

        retrieved = store.get_result("/path/to/test.ms")
        assert retrieved is not None
        assert retrieved.ms_path == result.ms_path
        assert retrieved.passed == result.passed
        assert retrieved.overall_grade == result.overall_grade

    def test_list_recent(self, temp_db):
        """Test listing recent results."""
        store = CalibrationQAStore(db_path=temp_db)

        # Save multiple results
        for i in range(5):
            result = CalibrationQAResult(
                ms_path=f"/path/to/test_{i}.ms",
                passed=i % 2 == 0,
                severity="success" if i % 2 == 0 else "error",
                overall_grade="excellent" if i % 2 == 0 else "failed",
                summary={"n_warnings": 0, "n_errors": 0 if i % 2 == 0 else 1},
                assessment_time_s=0.1,
                timestamp=time.time() + i,
            )
            store.save_result(result)

        # List all recent
        all_results = store.list_recent(limit=10)
        assert len(all_results) == 5

        # List passed only
        passed_results = store.list_recent(limit=10, passed_only=True)
        assert len(passed_results) == 3
        assert all(r.passed for r in passed_results)

        # List failed only
        failed_results = store.list_recent(limit=10, failed_only=True)
        assert len(failed_results) == 2
        assert all(not r.passed for r in failed_results)

    def test_get_summary_stats(self, temp_db):
        """Test getting summary statistics."""
        store = CalibrationQAStore(db_path=temp_db)

        # Save test results
        grades = ["excellent", "good", "marginal", "poor", "failed"]
        for i, grade in enumerate(grades):
            result = CalibrationQAResult(
                ms_path=f"/path/to/test_{i}.ms",
                passed=grade != "failed",
                severity="success" if grade != "failed" else "error",
                overall_grade=grade,
                summary={"avg_flag_fraction": 0.1 * (i + 1)},
                assessment_time_s=0.1 * (i + 1),
            )
            store.save_result(result)

        stats = store.get_summary_stats()

        assert stats["total"] == 5
        assert stats["passed"] == 4
        assert stats["failed"] == 1
        assert "excellent" in stats["by_grade"]

    def test_cleanup_old_results(self, temp_db):
        """Test cleanup of old results."""
        store = CalibrationQAStore(db_path=temp_db)

        # Save old result (31 days ago)
        old_result = CalibrationQAResult(
            ms_path="/path/to/old.ms",
            passed=True,
            severity="success",
            overall_grade="excellent",
            timestamp=time.time() - (31 * 24 * 3600),
        )
        store.save_result(old_result)

        # Save recent result
        recent_result = CalibrationQAResult(
            ms_path="/path/to/recent.ms",
            passed=True,
            severity="success",
            overall_grade="excellent",
            timestamp=time.time(),
        )
        store.save_result(recent_result)

        # Cleanup
        deleted = store.cleanup_old_results(days=30)

        assert deleted == 1
        assert store.get_result("/path/to/old.ms") is None
        assert store.get_result("/path/to/recent.ms") is not None


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


class TestQAStoreSingleton:
    """Tests for QA store singleton pattern."""

    def test_get_qa_store_returns_singleton(self):
        """Test that get_qa_store returns same instance."""
        close_qa_store()  # Reset singleton

        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            store1 = get_qa_store(db_path)
            store2 = get_qa_store()

            assert store1 is store2
        finally:
            close_qa_store()
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_close_qa_store_resets_singleton(self):
        """Test that close_qa_store resets the singleton."""
        close_qa_store()

        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            store1 = get_qa_store(db_path)
            close_qa_store()
            store2 = get_qa_store(db_path)

            # After close, should get a new instance
            assert store1 is not store2
        finally:
            close_qa_store()
            if os.path.exists(db_path):
                os.unlink(db_path)
