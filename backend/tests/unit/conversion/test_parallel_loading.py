"""
Unit tests for Issue #9: Parallel I/O for subband loading.

Tests cover:
1. _load_single_subband() - individual file loading
2. _load_and_combine_subbands() - parallel vs sequential loading
3. _load_subbands_sequential() - fallback sequential loading
4. Error handling for missing/corrupt files
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# =============================================================================
# Test fixtures
# =============================================================================


@pytest.fixture
def mock_uvdata():
    """Create a mock UVData object for testing."""
    mock_uv = MagicMock()
    mock_uv.Nfreqs = 1024
    mock_uv.Npols = 4
    mock_uv.Nbls = 2145  # 66 * 65 / 2 for DSA-110
    mock_uv.data_array = np.ones((100, 1024, 4), dtype=np.complex64)
    return mock_uv


@pytest.fixture
def mock_subband_files(tmp_path):
    """Create mock subband file paths."""
    files = []
    for i in range(16):
        f = tmp_path / f"2025-01-15T12:30:00_sb{i:02d}.hdf5"
        f.touch()
        files.append(str(f))
    return files


# =============================================================================
# Tests for _load_single_subband()
# =============================================================================


class TestLoadSingleSubband:
    """Tests for _load_single_subband() function."""

    def test_successful_load(self, tmp_path, mock_uvdata):
        """Test successful loading of a single subband."""
        test_file = tmp_path / "test_sb00.hdf5"
        test_file.touch()

        with (
            patch(
                "dsa110_contimg.conversion.hdf5_orchestrator.FastMeta"
            ) as mock_fast_meta,
            patch(
                "dsa110_contimg.conversion.hdf5_orchestrator.pyuvdata.UVData"
            ) as mock_uvdata_cls,
        ):
            # Setup mocks
            mock_meta = MagicMock()
            mock_meta.__enter__ = MagicMock(return_value=mock_meta)
            mock_meta.__exit__ = MagicMock(return_value=False)
            mock_meta.time_array = np.array([60000.0])
            mock_fast_meta.return_value = mock_meta

            mock_uvdata_cls.return_value = mock_uvdata

            from dsa110_contimg.conversion.hdf5_orchestrator import (
                _load_single_subband,
            )

            result = _load_single_subband(str(test_file), "test_group")

            assert result is not None
            mock_uvdata.read.assert_called_once()

    def test_file_not_found(self, tmp_path):
        """Test error handling for missing file."""
        from dsa110_contimg.utils.exceptions import UVH5ReadError

        with (
            patch(
                "dsa110_contimg.conversion.hdf5_orchestrator.FastMeta"
            ) as mock_fast_meta,
        ):
            mock_fast_meta.side_effect = FileNotFoundError("Not found")

            from dsa110_contimg.conversion.hdf5_orchestrator import (
                _load_single_subband,
            )

            with pytest.raises(UVH5ReadError, match="File not found"):
                _load_single_subband("/nonexistent/file.hdf5", "test_group")


# =============================================================================
# Tests for _load_and_combine_subbands() - parallel loading
# =============================================================================


class TestLoadAndCombineSubbands:
    """Tests for parallel and sequential subband loading."""

    def test_parallel_loading_enabled(self, mock_subband_files, mock_uvdata):
        """Test that parallel loading uses ThreadPoolExecutor."""
        with patch(
            "dsa110_contimg.conversion.hdf5_orchestrator._load_single_subband"
        ) as mock_load:
            # Each call returns a fresh mock that supports +=
            def create_mock_uv(*args, **kwargs):
                mock = MagicMock()
                mock.__iadd__ = MagicMock(return_value=mock)
                return mock

            mock_load.side_effect = create_mock_uv

            from dsa110_contimg.conversion.hdf5_orchestrator import (
                _load_and_combine_subbands,
            )

            # Use 4 files to trigger parallel path (n_files > 2)
            files = mock_subband_files[:4]

            result = _load_and_combine_subbands(
                files, "test_group", parallel=True, max_workers=2
            )

            # Verify all files were loaded
            assert mock_load.call_count == 4
            assert result is not None

    def test_sequential_fallback_for_small_groups(
        self, mock_subband_files, mock_uvdata
    ):
        """Test that small groups use sequential loading."""
        with patch(
            "dsa110_contimg.conversion.hdf5_orchestrator._load_subbands_sequential"
        ) as mock_seq:
            mock_seq.return_value = mock_uvdata

            from dsa110_contimg.conversion.hdf5_orchestrator import (
                _load_and_combine_subbands,
            )

            # Only 2 files - should use sequential
            _load_and_combine_subbands(
                mock_subband_files[:2], "test_group", parallel=True, max_workers=4
            )

            mock_seq.assert_called_once()

    def test_parallel_disabled_uses_sequential(self, mock_subband_files, mock_uvdata):
        """Test that parallel=False uses sequential loading."""
        with patch(
            "dsa110_contimg.conversion.hdf5_orchestrator._load_subbands_sequential"
        ) as mock_seq:
            mock_seq.return_value = mock_uvdata

            from dsa110_contimg.conversion.hdf5_orchestrator import (
                _load_and_combine_subbands,
            )

            _load_and_combine_subbands(
                mock_subband_files[:4], "test_group", parallel=False, max_workers=4
            )

            mock_seq.assert_called_once()

    def test_empty_group_raises_error(self):
        """Test that empty group raises ConversionError."""
        from dsa110_contimg.conversion.hdf5_orchestrator import (
            _load_and_combine_subbands,
        )
        from dsa110_contimg.utils.exceptions import ConversionError

        with pytest.raises(ConversionError, match="No subband files"):
            _load_and_combine_subbands([], "test_group")


# =============================================================================
# Tests for _load_subbands_sequential()
# =============================================================================


class TestLoadSubbandsSequential:
    """Tests for sequential subband loading (fallback)."""

    def test_sequential_load_combines_in_order(self, mock_subband_files, mock_uvdata):
        """Test that sequential loading combines subbands in order."""
        call_order = []

        def mock_load(file_path, group_id):
            call_order.append(file_path)
            mock = MagicMock()
            mock.__iadd__ = MagicMock(return_value=mock)
            return mock

        with patch(
            "dsa110_contimg.conversion.hdf5_orchestrator._load_single_subband",
            side_effect=mock_load,
        ):
            from dsa110_contimg.conversion.hdf5_orchestrator import (
                _load_subbands_sequential,
            )

            _load_subbands_sequential(
                sorted(mock_subband_files[:4]), "test_group"
            )

            # Verify files were loaded in sorted order
            assert call_order == sorted(mock_subband_files[:4])


# =============================================================================
# Tests for settings integration
# =============================================================================


class TestSettingsIntegration:
    """Tests for settings.conversion integration."""

    def test_settings_have_parallel_loading_fields(self):
        """Test that ConversionSettings has parallel loading fields."""
        from dsa110_contimg.config import settings

        # Check that settings exist and have correct defaults
        assert hasattr(settings.conversion, "parallel_loading")
        assert hasattr(settings.conversion, "io_max_workers")
        assert settings.conversion.parallel_loading is True
        assert settings.conversion.io_max_workers == 4
