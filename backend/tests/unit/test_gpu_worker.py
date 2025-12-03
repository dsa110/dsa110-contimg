"""
Unit tests for GPU-enabled imaging worker (Phase 3.3).

Tests cover:
- GPU gridding integration in imaging worker
- GPU memory checks and fallback behavior
- Visibility reading and processing
- FITS output generation
"""

import os
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np
import pytest


class TestWorkerGPUHelpers:
    """Tests for imaging worker GPU helper functions."""

    def test_get_wavelength_from_ms_default(self):
        """Test wavelength default when SPECTRAL_WINDOW unavailable."""
        from dsa110_contimg.imaging.worker import _get_wavelength_from_ms

        with tempfile.TemporaryDirectory() as tmpdir:
            # Non-existent MS should return default wavelength
            wavelength = _get_wavelength_from_ms(f"{tmpdir}/nonexistent.ms")
            assert wavelength == pytest.approx(0.2142, rel=0.01)

    def test_average_polarizations_dual_pol(self):
        """Test polarization averaging with dual-pol data."""
        from dsa110_contimg.imaging.worker import _average_polarizations

        # Create test data with 2 polarizations
        n_rows, n_chan, n_pol = 100, 48, 2
        data = np.random.randn(n_rows, n_chan, n_pol) + 1j * np.random.randn(
            n_rows, n_chan, n_pol
        )
        flags = np.zeros((n_rows, n_chan, n_pol), dtype=bool)
        weights = np.ones((n_rows, n_chan, n_pol), dtype=np.float32)

        vis_avg, flag_avg, wt_avg = _average_polarizations(data, flags, weights)

        assert vis_avg.shape == (n_rows, n_chan)
        assert flag_avg.shape == (n_rows, n_chan)
        assert wt_avg.shape == (n_rows, n_chan)
        # Average should be (XX + YY) / 2
        expected = 0.5 * (data[:, :, 0] + data[:, :, -1])
        np.testing.assert_allclose(vis_avg, expected)

    def test_average_polarizations_single_pol(self):
        """Test polarization averaging with single-pol data."""
        from dsa110_contimg.imaging.worker import _average_polarizations

        n_rows, n_chan, n_pol = 100, 48, 1
        data = np.random.randn(n_rows, n_chan, n_pol) + 1j * np.random.randn(
            n_rows, n_chan, n_pol
        )
        flags = np.zeros((n_rows, n_chan, n_pol), dtype=bool)
        weights = np.ones((n_rows, n_chan, n_pol), dtype=np.float32)

        vis_avg, flag_avg, wt_avg = _average_polarizations(data, flags, weights)

        assert vis_avg.shape == (n_rows, n_chan)
        np.testing.assert_allclose(vis_avg, data[:, :, 0])

    def test_get_weights_from_table_ones(self):
        """Test weight extraction when no weights column exists."""
        from dsa110_contimg.imaging.worker import _get_weights_from_table

        # Mock table with no weight columns
        mock_tb = mock.MagicMock()
        mock_tb.colnames.return_value = ["DATA", "FLAG", "UVW"]

        data_shape = (100, 48, 2)
        weights = _get_weights_from_table(mock_tb, data_shape)

        assert weights.shape == data_shape
        assert weights.dtype == np.float32
        np.testing.assert_array_equal(weights, np.ones(data_shape, dtype=np.float32))

    def test_get_weights_from_table_weight_spectrum(self):
        """Test weight extraction from WEIGHT_SPECTRUM column."""
        from dsa110_contimg.imaging.worker import _get_weights_from_table

        data_shape = (100, 48, 2)
        expected_weights = np.random.rand(*data_shape).astype(np.float32)

        mock_tb = mock.MagicMock()
        mock_tb.colnames.return_value = ["DATA", "FLAG", "UVW", "WEIGHT_SPECTRUM"]
        mock_tb.getcol.return_value = expected_weights

        weights = _get_weights_from_table(mock_tb, data_shape)

        mock_tb.getcol.assert_called_once_with("WEIGHT_SPECTRUM")
        np.testing.assert_array_equal(weights, expected_weights)


class TestGPUDirtyImage:
    """Tests for GPU dirty imaging function."""

    def test_gpu_dirty_image_unavailable(self):
        """Test GPU dirty image returns None when GPU gridding unavailable."""
        import dsa110_contimg.imaging.worker as worker

        # Temporarily set GPU gridding unavailable
        original = worker.GPU_GRIDDING_AVAILABLE
        worker.GPU_GRIDDING_AVAILABLE = False

        try:
            result = worker.gpu_dirty_image(
                "/fake/path.ms", "/fake/output", image_size=512
            )
            assert result is None
        finally:
            worker.GPU_GRIDDING_AVAILABLE = original

    @mock.patch("dsa110_contimg.imaging.worker._read_ms_visibilities")
    @mock.patch("dsa110_contimg.imaging.worker._run_gridding")
    @mock.patch("dsa110_contimg.imaging.worker._save_dirty_fits")
    def test_gpu_dirty_image_success(
        self, mock_save, mock_gridding, mock_read
    ):
        """Test successful GPU dirty imaging."""
        import dsa110_contimg.imaging.worker as worker

        if not worker.GPU_GRIDDING_AVAILABLE:
            pytest.skip("GPU gridding not available")

        # Mock visibility reading
        n_vis = 1000
        uvw = np.random.randn(n_vis, 3)
        vis = np.random.randn(n_vis) + 1j * np.random.randn(n_vis)
        weights = np.ones(n_vis, dtype=np.float32)
        flags = np.zeros(n_vis, dtype=bool)
        mock_read.return_value = (uvw, vis, weights, flags)

        # Mock gridding result
        mock_result = mock.MagicMock()
        mock_result.error = None
        mock_result.image = np.zeros((512, 512), dtype=np.float32)
        mock_result.n_vis = n_vis
        mock_result.n_flagged = 0
        mock_result.weight_sum = float(n_vis)
        mock_result.processing_time_s = 0.5
        mock_gridding.return_value = (mock_result, True)

        # Mock FITS saving
        mock_save.return_value = "/fake/output.dirty.fits"

        result = worker.gpu_dirty_image(
            "/fake/path.ms", "/fake/output", image_size=512
        )

        assert result == "/fake/output.dirty.fits"
        mock_read.assert_called_once()
        mock_gridding.assert_called_once()
        mock_save.assert_called_once()


class TestApplyAndImage:
    """Tests for _apply_and_image function."""

    def test_setup_temp_environment_no_module(self):
        """Test temp environment setup handles missing module gracefully."""
        from dsa110_contimg.imaging.worker import _setup_temp_environment

        with tempfile.TemporaryDirectory() as tmpdir:
            # Should not raise even if prepare_temp_environment unavailable
            _setup_temp_environment(Path(tmpdir))


class TestProcessOnce:
    """Tests for process_once function."""

    def test_process_once_creates_output_dir(self):
        """Test that process_once creates output directory."""
        from dsa110_contimg.imaging.worker import process_once

        with tempfile.TemporaryDirectory() as tmpdir:
            ms_dir = Path(tmpdir) / "ms_input"
            out_dir = Path(tmpdir) / "output"
            registry_db = Path(tmpdir) / "registry.db"
            products_db = Path(tmpdir) / "products.db"

            ms_dir.mkdir()

            # Create empty registry DB
            import sqlite3
            conn = sqlite3.connect(registry_db)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS caltable_registry (
                    path TEXT PRIMARY KEY,
                    source TEXT,
                    type TEXT,
                    start_mjd REAL,
                    end_mjd REAL,
                    active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
            conn.close()

            # Should create output directory and return 0 (no MS files)
            result = process_once(ms_dir, out_dir, registry_db, products_db)

            assert out_dir.exists()
            assert result == 0


class TestRunGridding:
    """Tests for _run_gridding function."""

    def test_run_gridding_cpu_fallback(self):
        """Test gridding falls back to CPU when GPU unavailable."""
        import dsa110_contimg.imaging.worker as worker

        if not worker.GPU_GRIDDING_AVAILABLE:
            pytest.skip("GPU gridding not available")

        with mock.patch.object(worker, "is_gpu_available", return_value=False):
            with mock.patch.object(
                worker, "check_gpu_memory_available", return_value=(False, "No GPU")
            ):
                n_vis = 100
                uvw = np.random.randn(n_vis, 3).astype(np.float64)
                vis = (np.random.randn(n_vis) + 1j * np.random.randn(n_vis)).astype(
                    np.complex128
                )
                weights = np.ones(n_vis, dtype=np.float32)
                flags = np.zeros(n_vis, dtype=np.int32)

                config = worker.GriddingConfig(image_size=64, cell_size_arcsec=60.0)

                result, use_gpu = worker._run_gridding(
                    uvw, vis, weights, flags, config, gpu_id=0
                )

                assert use_gpu is False
                assert result is not None
