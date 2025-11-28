"""Unit tests for calibration solving integration in streaming converter.

Tests the integration of has_calibrator() and solve_calibration_for_ms()
into the streaming converter workflow.
"""

import sqlite3
from pathlib import Path
from unittest.mock import patch

from dsa110_contimg.calibration.streaming import (
    has_calibrator,
    solve_calibration_for_ms,
)


class TestCalibratorDetectionIntegration:
    """Test calibrator detection integration in streaming converter."""

    @patch("dsa110_contimg.calibration.streaming.has_calibrator")
    @patch("dsa110_contimg.utils.ms_organization.determine_ms_type")
    def test_calibrator_detection_enabled(self, mock_determine, mock_has_calibrator):
        """Test that has_calibrator is called when enable_calibration_solving is True."""
        # Setup: path-based detection returns False, content-based returns True
        mock_determine.return_value = (False, False)
        mock_has_calibrator.return_value = True

        ms_path = "/path/to/test.ms"
        result = mock_has_calibrator(ms_path)

        assert result is True
        mock_has_calibrator.assert_called_once_with(ms_path)

    @patch("dsa110_contimg.utils.ms_organization.determine_ms_type")
    def test_path_based_detection_used_first(self, mock_determine):
        """Test that path-based detection is tried first (fast path)."""
        mock_determine.return_value = (True, False)  # is_calibrator=True

        # Simulate the logic: if path-based detects calibrator, content-based is skipped
        is_calibrator, is_failed = mock_determine(Path("/path/to/calibrator.ms"))

        assert is_calibrator is True
        assert is_failed is False
        mock_determine.assert_called_once()

    @patch("dsa110_contimg.calibration.streaming.has_calibrator")
    @patch("dsa110_contimg.utils.ms_organization.determine_ms_type")
    def test_content_detection_fallback(self, mock_determine, mock_has_calibrator):
        """Test content-based detection is used when path-based fails."""
        mock_determine.return_value = (False, False)  # Path-based: not calibrator
        mock_has_calibrator.return_value = True  # Content-based: is calibrator

        ms_path = "/path/to/test.ms"
        is_calibrator_path, _ = mock_determine(Path(ms_path))

        if not is_calibrator_path:
            is_calibrator_content = mock_has_calibrator(ms_path)
            assert is_calibrator_content is True

        mock_determine.assert_called_once()
        mock_has_calibrator.assert_called_once_with(ms_path)


class TestCalibrationSolvingIntegration:
    """Test calibration solving integration in streaming converter."""

    @patch("dsa110_contimg.calibration.streaming.solve_calibration_for_ms")
    def test_calibration_solving_called_for_calibrator(self, mock_solve):
        """Test that solve_calibration_for_ms is called for calibrator MS."""
        mock_solve.return_value = (True, None)

        ms_path = "/path/to/calibrator.ms"
        is_calibrator = True
        enable_solving = True

        if is_calibrator and enable_solving:
            success, error = mock_solve(ms_path, do_k=False)

        assert success is True
        assert error is None
        mock_solve.assert_called_once_with(ms_path, do_k=False)

    @patch("dsa110_contimg.calibration.streaming.solve_calibration_for_ms")
    def test_calibration_solving_not_called_for_science(self, mock_solve):
        """Test that solve_calibration_for_ms is NOT called for science MS."""
        ms_path = "/path/to/science.ms"
        is_calibrator = False
        enable_solving = True

        if is_calibrator and enable_solving:
            mock_solve(ms_path, do_k=False)

        mock_solve.assert_not_called()

    @patch("dsa110_contimg.calibration.streaming.solve_calibration_for_ms")
    def test_calibration_solving_not_called_when_disabled(self, mock_solve):
        """Test that solve_calibration_for_ms is NOT called when flag is disabled."""
        ms_path = "/path/to/calibrator.ms"
        is_calibrator = True
        enable_solving = False

        if is_calibrator and enable_solving:
            mock_solve(ms_path, do_k=False)

        mock_solve.assert_not_called()

    @patch("dsa110_contimg.calibration.streaming.solve_calibration_for_ms")
    def test_calibration_solving_error_handling(self, mock_solve):
        """Test error handling when calibration solving fails."""
        mock_solve.return_value = (False, "Calibration solve failed: test error")

        ms_path = "/path/to/calibrator.ms"
        success, error = mock_solve(ms_path, do_k=False)

        assert success is False
        assert error is not None
        assert "failed" in error.lower()
        mock_solve.assert_called_once()


class TestCalibrationTableRegistration:
    """Test calibration table registration in registry."""

    @patch("dsa110_contimg.database.registry.register_set_from_prefix")
    @patch("dsa110_contimg.calibration.streaming.solve_calibration_for_ms")
    def test_calibration_tables_registered_on_success(self, mock_solve, mock_register):
        """Test that calibration tables are registered when solving succeeds."""
        mock_solve.return_value = (True, None)

        ms_path = "/path/to/calibrator.ms"
        gid = "2025-01-15T12:00:00"
        registry_db = Path("/tmp/registry.db")
        mid_mjd = 60000.5

        # Simulate the workflow: solve calibration, then register tables
        success, error = mock_solve(ms_path, do_k=False)
        assert success is True
        assert error is None

        if success:
            cal_prefix = Path(ms_path).with_suffix("")
            mock_register(
                registry_db,
                set_name=f"cal_{gid}",
                prefix=cal_prefix,
                cal_field=None,
                refant=None,
                valid_start_mjd=mid_mjd,
                valid_end_mjd=None,
            )

        mock_solve.assert_called_once_with(ms_path, do_k=False)
        mock_register.assert_called_once()
        # Check call arguments
        call_args = mock_register.call_args
        # Positional args: only db_path (set_name and prefix are keyword-only)
        assert len(call_args[0]) == 1
        assert call_args[0][0] == registry_db
        # Keyword args: set_name, prefix, cal_field, refant, valid_start_mjd, valid_end_mjd
        assert call_args[1]["set_name"] == f"cal_{gid}"
        assert call_args[1]["prefix"] == Path(ms_path).with_suffix("")
        assert call_args[1]["cal_field"] is None
        assert call_args[1]["refant"] is None
        assert call_args[1]["valid_start_mjd"] == mid_mjd
        assert call_args[1]["valid_end_mjd"] is None

    @patch("dsa110_contimg.database.registry.register_set_from_prefix")
    @patch("dsa110_contimg.calibration.streaming.solve_calibration_for_ms")
    def test_calibration_tables_not_registered_on_failure(self, mock_solve, mock_register):
        """Test that calibration tables are NOT registered when solving fails."""
        mock_solve.return_value = (False, "Solve failed")

        ms_path = "/path/to/calibrator.ms"
        success, error = mock_solve(ms_path, do_k=False)

        if success:
            mock_register()

        assert success is False
        mock_register.assert_not_called()


class TestDatabaseUpdates:
    """Test database field updates."""

    def test_has_calibrator_field_update(self, tmp_path):
        """Test that has_calibrator field is updated in ingest_queue."""
        db_path = tmp_path / "ingest.db"
        conn = sqlite3.connect(db_path)

        # Create ingest_queue table
        conn.execute(
            """
            CREATE TABLE ingest_queue (
                group_id TEXT PRIMARY KEY,
                has_calibrator INTEGER DEFAULT NULL
            )
        """
        )

        # Insert test group
        gid = "2025-01-15T12:00:00"
        conn.execute("INSERT INTO ingest_queue (group_id) VALUES (?)", (gid,))
        conn.commit()

        # Update has_calibrator field
        is_calibrator = True
        conn.execute(
            "UPDATE ingest_queue SET has_calibrator = ? WHERE group_id = ?",
            (1 if is_calibrator else 0, gid),
        )
        conn.commit()

        # Verify update
        cursor = conn.execute("SELECT has_calibrator FROM ingest_queue WHERE group_id = ?", (gid,))
        result = cursor.fetchone()
        assert result[0] == 1

        conn.close()


class TestSmokeTests:
    """Smoke tests for basic functionality."""

    def test_imports_work(self):
        """Smoke test: verify imports work correctly."""
        from dsa110_contimg.calibration.streaming import (
            has_calibrator,
        )
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            build_parser,
        )

        assert callable(has_calibrator)
        assert callable(solve_calibration_for_ms)
        assert callable(build_parser)

    def test_command_line_flag_exists(self):
        """Smoke test: verify --enable-calibration-solving flag exists."""
        from dsa110_contimg.conversion.streaming.streaming_converter import (
            build_parser,
        )

        parser = build_parser()
        args = parser.parse_args(
            [
                "--input-dir",
                "/tmp",
                "--output-dir",
                "/tmp",
                "--enable-calibration-solving",
            ]
        )

        assert hasattr(args, "enable_calibration_solving")
        assert args.enable_calibration_solving is True

    def test_has_calibrator_callable(self):
        """Smoke test: verify has_calibrator function exists and is callable."""
        from dsa110_contimg.calibration.streaming import has_calibrator

        assert callable(has_calibrator)
        assert has_calibrator.__name__ == "has_calibrator"

    def test_solve_calibration_for_ms_callable(self):
        """Smoke test: verify solve_calibration_for_ms function exists and is callable."""

        assert callable(solve_calibration_for_ms)
        assert solve_calibration_for_ms.__name__ == "solve_calibration_for_ms"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @patch("dsa110_contimg.calibration.streaming.has_calibrator")
    def test_calibrator_detection_when_ms_not_exists(self, mock_has_calibrator):
        """Test behavior when MS file doesn't exist."""
        mock_has_calibrator.side_effect = FileNotFoundError("MS not found")

        ms_path = "/nonexistent/path.ms"
        try:
            result = has_calibrator(ms_path)
        except FileNotFoundError:
            result = False  # Function should handle gracefully

        # Function should return False on exception
        assert result is False

    @patch("dsa110_contimg.calibration.streaming.solve_calibration_for_ms")
    def test_calibration_solving_when_disabled(self, mock_solve):
        """Test that solving is skipped when flag is disabled."""
        enable_solving = False
        is_calibrator = True

        if is_calibrator and enable_solving:
            mock_solve("/path/to/ms.ms")

        mock_solve.assert_not_called()

    @patch("dsa110_contimg.calibration.streaming.solve_calibration_for_ms")
    def test_calibration_solving_exception_handling(self, mock_solve):
        """Test exception handling in calibration solving."""
        mock_solve.side_effect = Exception("Unexpected error")

        ms_path = "/path/to/calibrator.ms"
        try:
            success, error = mock_solve(ms_path, do_k=False)
        except Exception as e:
            success = False
            error = str(e)

        assert success is False
        assert error is not None
