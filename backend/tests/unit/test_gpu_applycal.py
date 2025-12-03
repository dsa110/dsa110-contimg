"""
Unit tests for GPU-enabled calibration applycal (Phase 3.3).

Tests cover:
- GPU gain application integration
- Caltable reading and parsing
- MS data reading for GPU calibration
- CORRECTED_DATA verification
"""

import tempfile
from pathlib import Path
from unittest import mock

import numpy as np
import pytest


class TestVerifyCorrectedData:
    """Tests for CORRECTED_DATA verification functions."""

    def test_check_corrected_data_column_missing(self):
        """Test error when CORRECTED_DATA column is missing."""
        from dsa110_contimg.calibration.applycal import _check_corrected_data_column

        mock_tb = mock.MagicMock()
        mock_tb.colnames.return_value = ["DATA", "FLAG", "UVW"]

        with pytest.raises(RuntimeError, match="CORRECTED_DATA column not present"):
            _check_corrected_data_column(mock_tb, "/fake/path.ms")

    def test_check_corrected_data_column_zero_rows(self):
        """Test error when MS has zero rows."""
        from dsa110_contimg.calibration.applycal import _check_corrected_data_column

        mock_tb = mock.MagicMock()
        mock_tb.colnames.return_value = ["DATA", "CORRECTED_DATA", "FLAG", "UVW"]
        mock_tb.nrows.return_value = 0

        with pytest.raises(RuntimeError, match="MS has zero rows"):
            _check_corrected_data_column(mock_tb, "/fake/path.ms")

    def test_check_corrected_data_column_success(self):
        """Test successful CORRECTED_DATA column check."""
        from dsa110_contimg.calibration.applycal import _check_corrected_data_column

        mock_tb = mock.MagicMock()
        mock_tb.colnames.return_value = ["DATA", "CORRECTED_DATA", "FLAG", "UVW"]
        mock_tb.nrows.return_value = 1000

        # Should not raise
        _check_corrected_data_column(mock_tb, "/fake/path.ms")

    def test_verify_nonzero_fraction_all_flagged(self):
        """Test error when all data is flagged."""
        from dsa110_contimg.calibration.applycal import _verify_nonzero_fraction

        mock_tb = mock.MagicMock()
        mock_tb.nrows.return_value = 100
        mock_tb.getcol.side_effect = [
            np.zeros((100, 48, 2), dtype=np.complex128),  # CORRECTED_DATA
            np.ones((100, 48, 2), dtype=bool),  # FLAG - all flagged
        ]

        with pytest.raises(RuntimeError, match="All CORRECTED_DATA is flagged"):
            _verify_nonzero_fraction(mock_tb, "/fake/path.ms", min_fraction=0.01)

    def test_verify_nonzero_fraction_low_nonzero(self):
        """Test error when non-zero fraction is too low."""
        from dsa110_contimg.calibration.applycal import _verify_nonzero_fraction

        mock_tb = mock.MagicMock()
        mock_tb.nrows.return_value = 100

        # Create data that is mostly zeros
        corrected = np.zeros((100, 48, 2), dtype=np.complex128)
        corrected[0, 0, 0] = 1.0 + 0j  # Only one non-zero
        flags = np.zeros((100, 48, 2), dtype=bool)

        mock_tb.getcol.side_effect = [corrected, flags]

        with pytest.raises(RuntimeError, match="CORRECTED_DATA appears unpopulated"):
            _verify_nonzero_fraction(mock_tb, "/fake/path.ms", min_fraction=0.5)


class TestReadGainsFromCaltable:
    """Tests for _read_gains_from_caltable function."""

    def test_read_gains_3d_array(self):
        """Test reading gains from 3D array (n_rows, n_chan, n_pol)."""
        from dsa110_contimg.calibration.applycal import _read_gains_from_caltable

        n_ant = 10
        gains_3d = np.random.randn(n_ant, 48, 2) + 1j * np.random.randn(n_ant, 48, 2)
        ant_ids = np.arange(n_ant)
        flags = np.zeros((n_ant, 48, 2), dtype=bool)

        with mock.patch("casacore.tables.table") as mock_table:
            mock_tb = mock.MagicMock()
            mock_tb.__enter__ = mock.MagicMock(return_value=mock_tb)
            mock_tb.__exit__ = mock.MagicMock(return_value=False)
            mock_tb.getcol.side_effect = [gains_3d, ant_ids, flags]
            mock_table.return_value = mock_tb

            gains, ids = _read_gains_from_caltable("/fake/caltable")

            assert gains.shape == (n_ant, 2)
            np.testing.assert_array_equal(ids, ant_ids)

    def test_read_gains_with_flags(self):
        """Test that flagged gains are set to identity (1.0)."""
        from dsa110_contimg.calibration.applycal import _read_gains_from_caltable

        n_ant = 10
        gains_3d = np.random.randn(n_ant, 1, 2) + 1j * np.random.randn(n_ant, 1, 2)
        ant_ids = np.arange(n_ant)
        flags = np.zeros((n_ant, 1, 2), dtype=bool)
        flags[5, :, :] = True  # Flag antenna 5

        with mock.patch("casacore.tables.table") as mock_table:
            mock_tb = mock.MagicMock()
            mock_tb.__enter__ = mock.MagicMock(return_value=mock_tb)
            mock_tb.__exit__ = mock.MagicMock(return_value=False)
            mock_tb.getcol.side_effect = [gains_3d, ant_ids, flags]
            mock_table.return_value = mock_tb

            gains, ids = _read_gains_from_caltable("/fake/caltable")

            # Flagged antenna should have gain = 1.0
            assert gains[5, 0] == pytest.approx(1.0 + 0j)
            assert gains[5, 1] == pytest.approx(1.0 + 0j)


class TestReadMSForGPUCal:
    """Tests for _read_ms_for_gpu_cal function."""

    def test_read_ms_returns_correct_columns(self):
        """Test that MS reading returns vis, ant1, ant2."""
        from dsa110_contimg.calibration.applycal import _read_ms_for_gpu_cal

        n_rows = 1000
        n_chan = 48
        n_pol = 2
        expected_vis = np.random.randn(n_rows, n_chan, n_pol) + 1j * np.random.randn(
            n_rows, n_chan, n_pol
        )
        expected_ant1 = np.random.randint(0, 64, n_rows)
        expected_ant2 = np.random.randint(0, 64, n_rows)

        with mock.patch("casacore.tables.table") as mock_table:
            mock_tb = mock.MagicMock()
            mock_tb.__enter__ = mock.MagicMock(return_value=mock_tb)
            mock_tb.__exit__ = mock.MagicMock(return_value=False)
            mock_tb.getcol.side_effect = [expected_vis, expected_ant1, expected_ant2]
            mock_table.return_value = mock_tb

            vis, ant1, ant2 = _read_ms_for_gpu_cal("/fake/path.ms", "DATA")

            np.testing.assert_array_equal(vis, expected_vis)
            np.testing.assert_array_equal(ant1, expected_ant1)
            np.testing.assert_array_equal(ant2, expected_ant2)


class TestApplyGainsToMS:
    """Tests for apply_gains_to_ms function."""

    def test_apply_gains_unavailable(self):
        """Test apply_gains_to_ms returns None when GPU cal unavailable."""
        import dsa110_contimg.calibration.applycal as applycal

        original = applycal.GPU_CALIBRATION_AVAILABLE
        applycal.GPU_CALIBRATION_AVAILABLE = False

        try:
            result = applycal.apply_gains_to_ms("/fake/path.ms", "/fake/caltable")
            assert result is None
        finally:
            applycal.GPU_CALIBRATION_AVAILABLE = original

    @mock.patch("dsa110_contimg.calibration.applycal._read_gains_from_caltable")
    @mock.patch("dsa110_contimg.calibration.applycal._read_ms_for_gpu_cal")
    @mock.patch("dsa110_contimg.calibration.applycal._write_corrected_data")
    @mock.patch("dsa110_contimg.calibration.applycal.apply_gains")
    @mock.patch("dsa110_contimg.calibration.applycal.check_gpu_memory_available")
    @mock.patch("dsa110_contimg.calibration.applycal.is_gpu_available")
    def test_apply_gains_success(
        self,
        mock_gpu_avail,
        mock_mem_avail,
        mock_apply,
        mock_write,
        mock_read_ms,
        mock_read_gains,
    ):
        """Test successful GPU gain application."""
        import dsa110_contimg.calibration.applycal as applycal

        if not applycal.GPU_CALIBRATION_AVAILABLE:
            pytest.skip("GPU calibration not available")

        # Mock gains
        n_ant = 64
        gains = np.ones((n_ant, 2), dtype=np.complex128)
        gains[:, 0] = np.random.randn(n_ant) + 1j * np.random.randn(n_ant)
        mock_read_gains.return_value = (gains, np.arange(n_ant))

        # Mock MS data
        n_rows = 1000
        vis = np.random.randn(n_rows, 48, 2) + 1j * np.random.randn(n_rows, 48, 2)
        ant1 = np.random.randint(0, n_ant, n_rows)
        ant2 = np.random.randint(0, n_ant, n_rows)
        mock_read_ms.return_value = (vis, ant1, ant2)

        # Mock GPU availability
        mock_gpu_avail.return_value = True
        mock_mem_avail.return_value = (True, "OK")

        # Mock apply_gains result
        mock_result = mock.MagicMock()
        mock_result.n_vis_processed = vis.size
        mock_result.n_vis_calibrated = vis.size
        mock_result.n_vis_flagged = 0
        mock_result.processing_time_s = 0.1
        mock_apply.return_value = mock_result

        result = applycal.apply_gains_to_ms("/fake/path.ms", "/fake/caltable")

        assert result is not None
        assert result.n_vis_processed == vis.size
        mock_write.assert_called_once()


class TestApplyToTarget:
    """Tests for apply_to_target function."""

    def test_apply_to_target_empty_gaintables(self):
        """Test error when no gaintables provided."""
        from dsa110_contimg.calibration.applycal import apply_to_target

        with pytest.raises(ValueError, match="No calibration tables provided"):
            apply_to_target("/fake/path.ms", field="", gaintables=[])

    def test_apply_to_target_rejects_non_science(self):
        """Test rejection of NON_SCIENCE calibration tables."""
        from dsa110_contimg.calibration.applycal import apply_to_target

        with pytest.raises(ValueError, match="STRICT SEPARATION VIOLATION"):
            apply_to_target(
                "/fake/path.ms",
                field="",
                gaintables=["/path/NON_SCIENCE_test.bcal"],
            )
