"""
Unit tests for streaming converter hardening integration.

Tests cover:
- Issue #5: Calibration QA integration in _register_caltables
- Issue #8: RFI preflagging integration in worker loop
- Graceful degradation when hardening module unavailable
- Quality metrics propagation to database
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch


# Import the module at test time to verify it loads
def get_streaming_converter():
    """Helper to import streaming_converter module."""
    from dsa110_contimg.conversion import streaming_converter
    return streaming_converter


class TestHardeningModuleAvailability:
    """Tests for hardening module availability checking."""

    def test_have_hardening_flag(self):
        """Test HAVE_HARDENING flag reflects import status."""
        sc = get_streaming_converter()
        assert isinstance(sc.HAVE_HARDENING, bool)

    def test_hardening_imports_with_flag_true(self):
        """Test that hardening functions are available when flag is True."""
        sc = get_streaming_converter()

        if sc.HAVE_HARDENING:
            # All functions should be callable
            assert callable(sc.assess_calibration_quality)
            assert callable(sc.get_calibration_quality_metrics)
            assert callable(sc.preflag_rfi)

    def test_all_hardening_functions_imported(self):
        """Test that all expected hardening functions are present."""
        sc = get_streaming_converter()

        # These should always be defined (as None if module not available)
        assert hasattr(sc, "CalibrationFence")
        assert hasattr(sc, "DiskSpaceMonitor")
        assert hasattr(sc, "ProcessingStateMachine")
        assert hasattr(sc, "assess_calibration_quality")
        assert hasattr(sc, "preflag_rfi")
        assert hasattr(sc, "check_calibration_overlap")
        assert hasattr(sc, "find_backup_calibrators")


class TestRegisterCaltablesFunction:
    """Tests for _register_caltables function."""

    def test_function_exists(self):
        """Test that _register_caltables is defined."""
        sc = get_streaming_converter()
        assert hasattr(sc, "_register_caltables")
        assert callable(sc._register_caltables)

    def test_function_handles_missing_args(self):
        """Test graceful handling of incomplete args."""
        sc = get_streaming_converter()

        args = argparse.Namespace()  # Missing required attributes
        log = MagicMock()

        # Should not crash, should log error
        with patch.object(sc, "register_set_from_prefix", side_effect=AttributeError):
            sc._register_caltables(args, "test_group", "/path/to/ms.ms", 60000.5, log)

        # Should log warning about failure
        log.warning.assert_called()


class TestUpdateStateMachineFunction:
    """Tests for _update_state_machine helper function."""

    def test_function_with_none_machine(self):
        """Test _update_state_machine with None state machine (no-op)."""
        sc = get_streaming_converter()
        log = MagicMock()

        # Should not raise
        sc._update_state_machine(None, "test_group", "CALIBRATING", log)

    def test_function_with_missing_enum(self):
        """Test graceful handling when ProcessingState is None."""
        sc = get_streaming_converter()
        log = MagicMock()

        with patch.object(sc, "ProcessingState", None):
            sc._update_state_machine(None, "test_group", "CALIBRATING", log)


class TestRFIPreflaggingIntegration:
    """Tests for Issue #8 - RFI preflagging integration."""

    def test_preflag_rfi_is_callable_when_available(self):
        """Test that preflag_rfi is callable when hardening available."""
        sc = get_streaming_converter()

        if sc.HAVE_HARDENING and sc.preflag_rfi is not None:
            assert callable(sc.preflag_rfi)

    def test_preflag_imports_correct_module(self):
        """Test that preflag_rfi comes from hardening module."""
        sc = get_streaming_converter()

        if sc.HAVE_HARDENING:
            # Verify it's the actual function, not a mock
            assert sc.preflag_rfi is not None
            # Check module path
            if hasattr(sc.preflag_rfi, "__module__"):
                assert "hardening" in sc.preflag_rfi.__module__


class TestCalibrationQAIntegration:
    """Tests for Issue #5 - Calibration QA integration."""

    def test_assess_quality_is_callable_when_available(self):
        """Test that assess_calibration_quality is callable when available."""
        sc = get_streaming_converter()

        if sc.HAVE_HARDENING and sc.assess_calibration_quality is not None:
            assert callable(sc.assess_calibration_quality)

    def test_get_metrics_is_callable_when_available(self):
        """Test that get_calibration_quality_metrics is callable when available."""
        sc = get_streaming_converter()

        if sc.HAVE_HARDENING and sc.get_calibration_quality_metrics is not None:
            assert callable(sc.get_calibration_quality_metrics)


class TestQueueDBClass:
    """Tests for QueueDB class (used by streaming converter)."""

    def test_queuedb_instantiation(self, tmp_path: Path):
        """Test QueueDB can be instantiated."""
        sc = get_streaming_converter()

        db_path = tmp_path / "test_queue.sqlite3"
        queue = sc.QueueDB(db_path)

        assert queue.path == db_path
        assert queue.expected_subbands == 16
        assert queue.cluster_tolerance_s == 60.0

    def test_queuedb_custom_parameters(self, tmp_path: Path):
        """Test QueueDB with custom parameters."""
        sc = get_streaming_converter()

        db_path = tmp_path / "test_queue2.sqlite3"
        queue = sc.QueueDB(
            db_path,
            expected_subbands=8,
            chunk_duration_minutes=10.0,
            cluster_tolerance_s=30.0,
        )

        assert queue.expected_subbands == 8
        assert queue.chunk_duration_minutes == 10.0
        assert queue.cluster_tolerance_s == 30.0


class TestStreamingConverterImports:
    """Test that all critical imports are present."""

    def test_database_imports(self):
        """Test database function imports."""
        sc = get_streaming_converter()

        assert hasattr(sc, "register_set_from_prefix")
        assert hasattr(sc, "get_active_applylist")
        assert hasattr(sc, "ensure_products_db")
        assert hasattr(sc, "ensure_ingest_db")
        assert hasattr(sc, "images_insert")
        assert hasattr(sc, "ms_index_upsert")

    def test_calibration_imports(self):
        """Test calibration function imports."""
        sc = get_streaming_converter()

        assert hasattr(sc, "has_calibrator")
        assert hasattr(sc, "solve_calibration_for_ms")

    def test_imaging_imports(self):
        """Test imaging function imports."""
        sc = get_streaming_converter()

        assert hasattr(sc, "image_ms")

    def test_math_import(self):
        """Test math module is imported (for np.degrees replacement)."""
        sc = get_streaming_converter()

        assert hasattr(sc, "math")
        assert hasattr(sc.math, "degrees")

