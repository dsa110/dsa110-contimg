#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for optimization features.

Tests the following optimizations:
1. Batch subband loading (memory efficiency)
2. MS metadata caching (cache hit/miss behavior)
3. Flag validation caching (cache invalidation)
4. Parallel processing utilities (error handling, progress)
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import numpy as np
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestBatchSubbandLoading:
    """Test batch subband loading optimization."""

    def test_batch_loading_behavior(self):
        """Verify batch loading processes files in batches."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _load_and_merge_subbands,
        )

        # Create mock file list (16 subbands)
        file_list = [f"subband_sb{i:02d}.uvh5" for i in range(16)]

        # Mock UVData and file reading
        with patch(
            "dsa110_contimg.conversion.strategies.hdf5_orchestrator.UVData"
        ) as MockUVData:
            mock_uv = Mock()
            mock_uv.fast_concat = Mock()
            mock_uv.reorder_freqs = Mock()
            MockUVData.return_value = mock_uv

            # Mock file reading to count calls
            read_calls = []

            def mock_read(*args, **kwargs):
                read_calls.append(1)
                return mock_uv

            with patch.object(mock_uv.__class__, "read", mock_read):
                # Test with batch_size=4 (should process 4 batches of 4)
                result = _load_and_merge_subbands(
                    file_list, batch_size=4, show_progress=False
                )

                # Verify batching occurred (should have multiple concat calls)
                # With batch_size=4 and 16 files, we expect 4 batches
                assert mock_uv.fast_concat.call_count >= 3  # At least 3 batches merged
                assert mock_uv.reorder_freqs.called

    def test_batch_loading_single_batch(self):
        """Verify single-batch loading when files <= batch_size."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            _load_and_merge_subbands,
        )

        # Create small file list (2 subbands)
        file_list = ["subband_sb00.uvh5", "subband_sb01.uvh5"]

        with patch(
            "dsa110_contimg.conversion.strategies.hdf5_orchestrator.UVData"
        ) as MockUVData:
            mock_uv = Mock()
            mock_uv.fast_concat = Mock()
            mock_uv.reorder_freqs = Mock()
            MockUVData.return_value = mock_uv

            result = _load_and_merge_subbands(
                file_list, batch_size=4, show_progress=False
            )

            # With 2 files and batch_size=4, should use single-batch path
            # (no batching needed)
            assert result is not None


class TestMSMetadataCaching:
    """Test MS metadata caching optimization."""

    def test_cache_hit(self):
        """Verify cache is used on second call."""
        from dsa110_contimg.utils.ms_helpers import (
            get_ms_metadata,
            clear_ms_metadata_cache,
            get_ms_metadata_cached,
        )

        # Clear cache first
        clear_ms_metadata_cache()

        # Create a temporary mock MS path
        with tempfile.TemporaryDirectory() as tmpdir:
            ms_path = os.path.join(tmpdir, "test.ms")
            os.makedirs(ms_path)

            # Mock casacore.tables
            mock_table = MagicMock()
            mock_table.__enter__ = Mock(return_value=mock_table)
            mock_table.__exit__ = Mock(return_value=None)
            mock_table.getcol.side_effect = [
                np.array([1.0e9, 1.1e9, 1.2e9]),  # CHAN_FREQ
                np.array([[[0.0, 0.0]]]),  # PHASE_DIR
                np.array(["FIELD0"]),  # NAME
                np.array(["ANT0", "ANT1"]),  # NAME (antennas)
            ]
            mock_table.colnames.return_value = ["CHAN_FREQ", "PHASE_DIR", "NAME"]
            mock_table.nrows.return_value = 1

            with patch(
                "dsa110_contimg.utils.ms_helpers.table", return_value=mock_table
            ):
                # First call - should read from table
                result1 = get_ms_metadata(ms_path)

                # Second call - should use cache (no additional table reads)
                call_count_before = mock_table.getcol.call_count
                result2 = get_ms_metadata(ms_path)
                call_count_after = mock_table.getcol.call_count

                # Verify cache was used (no additional table reads)
                assert call_count_after == call_count_before
                assert result1 == result2

    def test_cache_invalidation_on_file_modification(self):
        """Verify cache invalidates when file modification time changes."""
        from dsa110_contimg.utils.ms_helpers import (
            get_ms_metadata,
            clear_ms_metadata_cache,
            get_ms_metadata_cached,
        )

        clear_ms_metadata_cache()

        with tempfile.TemporaryDirectory() as tmpdir:
            ms_path = os.path.join(tmpdir, "test.ms")
            os.makedirs(ms_path)

            # Mock table
            mock_table = MagicMock()
            mock_table.__enter__ = Mock(return_value=mock_table)
            mock_table.__exit__ = Mock(return_value=None)
            mock_table.getcol.side_effect = [
                np.array([1.0e9, 1.1e9, 1.2e9]),
                np.array([[[0.0, 0.0]]]),
                np.array(["FIELD0"]),
                np.array(["ANT0", "ANT1"]),
            ]
            mock_table.colnames.return_value = ["CHAN_FREQ", "PHASE_DIR", "NAME"]
            mock_table.nrows.return_value = 1

            with patch(
                "dsa110_contimg.utils.ms_helpers.table", return_value=mock_table
            ):
                # First call
                result1 = get_ms_metadata(ms_path)
                call_count_1 = mock_table.getcol.call_count

                # Simulate file modification by changing mtime
                time.sleep(0.1)  # Ensure mtime changes
                os.utime(ms_path, None)  # Update modification time

                # Second call - should invalidate cache and re-read
                result2 = get_ms_metadata(ms_path)
                call_count_2 = mock_table.getcol.call_count

                # Verify cache was invalidated (additional table reads)
                assert call_count_2 > call_count_1


class TestFlagValidationCaching:
    """Test flag validation caching optimization."""

    def test_flag_validation_cache_hit(self):
        """Verify flag validation cache is used on second call."""
        from dsa110_contimg.utils.ms_helpers import (
            validate_ms_unflagged_fraction,
            clear_flag_validation_cache,
            _validate_ms_unflagged_fraction_cached,
        )

        clear_flag_validation_cache()

        with tempfile.TemporaryDirectory() as tmpdir:
            ms_path = os.path.join(tmpdir, "test.ms")
            os.makedirs(ms_path)

            # Mock table
            mock_table = MagicMock()
            mock_table.__enter__ = Mock(return_value=mock_table)
            mock_table.__exit__ = Mock(return_value=None)
            mock_table.nrows.return_value = 10000
            mock_table.colnames.return_value = ["FLAG"]

            # Mock flag data (50% unflagged)
            flags = np.zeros((10000, 4, 128), dtype=bool)
            flags[:5000] = True  # First half flagged
            mock_table.getcol.return_value = flags

            with patch(
                "dsa110_contimg.utils.ms_helpers.table", return_value=mock_table
            ):
                # First call
                result1 = validate_ms_unflagged_fraction(ms_path, sample_size=1000)
                call_count_1 = mock_table.getcol.call_count

                # Second call - should use cache
                result2 = validate_ms_unflagged_fraction(ms_path, sample_size=1000)
                call_count_2 = mock_table.getcol.call_count

                # Verify cache was used (same result, no additional reads)
                assert result1 == result2
                assert call_count_2 == call_count_1

    def test_flag_validation_cache_invalidation(self):
        """Verify cache invalidates on file modification."""
        from dsa110_contimg.utils.ms_helpers import (
            validate_ms_unflagged_fraction,
            clear_flag_validation_cache,
        )

        clear_flag_validation_cache()

        with tempfile.TemporaryDirectory() as tmpdir:
            ms_path = os.path.join(tmpdir, "test.ms")
            os.makedirs(ms_path)

            mock_table = MagicMock()
            mock_table.__enter__ = Mock(return_value=mock_table)
            mock_table.__exit__ = Mock(return_value=None)
            mock_table.nrows.return_value = 10000
            mock_table.colnames.return_value = ["FLAG"]

            flags = np.zeros((10000, 4, 128), dtype=bool)
            mock_table.getcol.return_value = flags

            with patch(
                "dsa110_contimg.utils.ms_helpers.table", return_value=mock_table
            ):
                # First call
                result1 = validate_ms_unflagged_fraction(ms_path)
                call_count_1 = mock_table.getcol.call_count

                # Simulate file modification
                time.sleep(0.1)
                os.utime(ms_path, None)

                # Second call - should invalidate cache
                result2 = validate_ms_unflagged_fraction(ms_path)
                call_count_2 = mock_table.getcol.call_count

                # Verify cache was invalidated
                assert call_count_2 > call_count_1


class TestParallelProcessing:
    """Test parallel processing utilities."""

    def test_parallel_processing_basic(self):
        """Verify parallel processing works correctly."""
        from dsa110_contimg.utils.parallel import process_parallel

        def square(x: int) -> int:
            return x * x

        items = [1, 2, 3, 4, 5]
        results = process_parallel(items, square, max_workers=2, show_progress=False)

        assert len(results) == 5
        assert results == [1, 4, 9, 16, 25]

    def test_parallel_processing_error_handling(self):
        """Verify errors are handled gracefully in parallel processing."""
        from dsa110_contimg.utils.parallel import process_parallel

        def fails_on_three(x: int) -> int:
            if x == 3:
                raise ValueError(f"Error processing {x}")
            return x * x

        items = [1, 2, 3, 4, 5]

        # Should log error and continue (returns None for failed items)
        results = process_parallel(
            items, fails_on_three, max_workers=2, show_progress=False
        )

        # Results should include None for failed item
        assert len(results) == 5
        assert results[0] == 1  # 1^2
        assert results[1] == 4  # 2^2
        assert results[2] is None  # Failed
        assert results[3] == 16  # 4^2
        assert results[4] == 25  # 5^2

    def test_parallel_processing_empty_list(self):
        """Verify parallel processing handles empty list."""
        from dsa110_contimg.utils.parallel import process_parallel

        def identity(x):
            return x

        results = process_parallel([], identity, max_workers=2, show_progress=False)
        assert results == []

    def test_parallel_processing_single_item(self):
        """Verify parallel processing works with single item."""
        from dsa110_contimg.utils.parallel import process_parallel

        def double(x: int) -> int:
            return x * 2

        results = process_parallel([5], double, max_workers=2, show_progress=False)
        assert results == [10]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
