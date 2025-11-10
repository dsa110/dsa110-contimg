"""
Unit tests for parallel processing utilities.

Tests edge cases, error handling, and robustness of parallel processing
functions in dsa110_contimg.utils.parallel.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from dsa110_contimg.utils.parallel import (
    map_parallel,
    process_batch_parallel,
    process_parallel,
)


class TestProcessParallel:
    """Test process_parallel function."""

    def test_empty_list(self):
        """Test that empty list returns empty list."""

        def dummy_func(x):
            return x * 2

        result = process_parallel([], dummy_func, max_workers=4)
        assert result == []

    def test_single_item(self):
        """Test that single item is processed without parallelization."""

        def square(x):
            return x * x

        result = process_parallel([5], square, max_workers=4)
        assert result == [25]

    def test_successful_processing(self):
        """Test successful parallel processing."""

        def double(x):
            return x * 2

        items = [1, 2, 3, 4, 5]
        result = process_parallel(items, double, max_workers=2, show_progress=False)
        assert result == [2, 4, 6, 8, 10]

    def test_partial_failures(self):
        """Test that partial failures don't stop processing."""

        def failing_func(x):
            if x == 3:
                raise ValueError("Test error")
            return x * 2

        items = [1, 2, 3, 4, 5]
        result = process_parallel(
            items, failing_func, max_workers=2, show_progress=False
        )
        assert result[0] == 2  # 1 * 2
        assert result[1] == 4  # 2 * 2
        assert result[2] is None  # Failed
        assert result[3] == 8  # 4 * 2
        assert result[4] == 10  # 5 * 2

    def test_os_error_handling(self):
        """Test that OSError is caught and handled."""

        def os_error_func(x):
            raise OSError("File not found")

        items = [1, 2]
        result = process_parallel(
            items, os_error_func, max_workers=2, show_progress=False
        )
        assert result[0] is None
        assert result[1] is None

    def test_memory_error_handling(self):
        """Test that MemoryError is caught and handled."""

        def memory_error_func(x):
            raise MemoryError("Out of memory")

        items = [1]
        result = process_parallel(
            items, memory_error_func, max_workers=1, show_progress=False
        )
        assert result[0] is None

    def test_runtime_error_handling(self):
        """Test that RuntimeError is caught and handled."""

        def runtime_error_func(x):
            raise RuntimeError("Runtime error")

        items = [1]
        result = process_parallel(
            items, runtime_error_func, max_workers=1, show_progress=False
        )
        assert result[0] is None

    def test_unexpected_exception_handling(self):
        """Test that unexpected exceptions are caught and logged."""

        def unexpected_error_func(x):
            raise KeyError("Unexpected error")

        items = [1]
        result = process_parallel(
            items, unexpected_error_func, max_workers=1, show_progress=False
        )
        assert result[0] is None

    @patch("dsa110_contimg.utils.parallel.get_progress_bar")
    def test_progress_bar_failure(self, mock_progress_bar):
        """Test that progress bar failure doesn't stop processing."""
        mock_progress_bar.side_effect = OSError("Progress bar failed")

        def double(x):
            return x * 2

        items = [1, 2, 3]
        result = process_parallel(items, double, max_workers=2, show_progress=True)
        assert result == [2, 4, 6]

    @patch("dsa110_contimg.utils.parallel.get_progress_bar")
    def test_progress_bar_context_failure(self, mock_progress_bar):
        """Test that progress bar context manager failure is handled."""
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(side_effect=RuntimeError("Context failed"))
        mock_progress_bar.return_value = mock_context

        def double(x):
            return x * 2

        items = [1, 2]
        result = process_parallel(items, double, max_workers=2, show_progress=True)
        assert result == [2, 4]

    def test_thread_pool_executor(self):
        """Test that ThreadPoolExecutor works when use_processes=False."""

        def double(x):
            return x * 2

        items = [1, 2, 3]
        result = process_parallel(
            items,
            double,
            max_workers=2,
            use_processes=False,
            show_progress=False,
        )
        assert result == [2, 4, 6]

    def test_max_workers_one(self):
        """Test with max_workers=1 (sequential processing)."""

        def double(x):
            return x * 2

        items = [1, 2, 3]
        result = process_parallel(items, double, max_workers=1, show_progress=False)
        assert result == [2, 4, 6]

    def test_order_preservation(self):
        """Test that results are returned in the same order as input."""

        def identity(x):
            return x

        items = list(range(100))
        result = process_parallel(items, identity, max_workers=4, show_progress=False)
        assert result == items


class TestProcessBatchParallel:
    """Test process_batch_parallel function."""

    def test_empty_list(self):
        """Test that empty list returns empty list."""

        def dummy_func(x):
            return x * 2

        result = process_batch_parallel([], dummy_func, batch_size=10)
        assert result == []

    def test_single_batch(self):
        """Test processing with single batch."""

        def double(x):
            return x * 2

        items = [1, 2, 3, 4, 5]
        result = process_batch_parallel(
            items, double, batch_size=10, max_workers=2, show_progress=False
        )
        assert result == [2, 4, 6, 8, 10]

    def test_multiple_batches(self):
        """Test processing with multiple batches."""

        def double(x):
            return x * 2

        items = list(range(25))  # 25 items
        result = process_batch_parallel(
            items, double, batch_size=10, max_workers=2, show_progress=False
        )
        assert len(result) == 25
        assert result[0] == 0
        assert result[24] == 48

    def test_partial_batch(self):
        """Test processing with partial final batch."""

        def double(x):
            return x * 2

        items = [1, 2, 3, 4, 5, 6, 7]  # 7 items, batch_size=3
        result = process_batch_parallel(
            items, double, batch_size=3, max_workers=2, show_progress=False
        )
        assert len(result) == 7
        assert result == [2, 4, 6, 8, 10, 12, 14]

    def test_batch_with_failures(self):
        """Test that failures in one batch don't affect others."""

        def failing_func(x):
            if x == 3:
                raise ValueError("Test error")
            return x * 2

        items = [1, 2, 3, 4, 5]
        result = process_batch_parallel(
            items,
            failing_func,
            batch_size=2,
            max_workers=2,
            show_progress=False,
        )
        assert result[0] == 2
        assert result[1] == 4
        assert result[2] is None  # Failed
        assert result[3] == 8
        assert result[4] == 10


class TestMapParallel:
    """Test map_parallel function."""

    def test_no_iterables(self):
        """Test that ValueError is raised when no iterables provided."""

        def add(a, b):
            return a + b

        with pytest.raises(ValueError, match="At least one iterable"):
            map_parallel(add, max_workers=2)

    def test_empty_iterables(self):
        """Test that empty iterables return empty list."""

        def add(a, b):
            return a + b

        result = map_parallel(add, [], [], max_workers=2, show_progress=False)
        assert result == []

    def test_successful_mapping(self):
        """Test successful parallel mapping."""

        def add(a, b):
            return a + b

        a_list = [1, 2, 3]
        b_list = [4, 5, 6]
        result = map_parallel(add, a_list, b_list, max_workers=2, show_progress=False)
        assert result == [5, 7, 9]

    def test_three_iterables(self):
        """Test mapping with three iterables."""

        def multiply(a, b, c):
            return a * b * c

        a_list = [1, 2]
        b_list = [3, 4]
        c_list = [5, 6]
        result = map_parallel(
            multiply,
            a_list,
            b_list,
            c_list,
            max_workers=2,
            show_progress=False,
        )
        assert result == [15, 48]

    def test_different_length_iterables(self):
        """Test that zip truncates to shortest iterable."""

        def add(a, b):
            return a + b

        a_list = [1, 2, 3, 4]
        b_list = [5, 6]  # Shorter
        result = map_parallel(add, a_list, b_list, max_workers=2, show_progress=False)
        assert len(result) == 2
        assert result == [6, 8]

    def test_mapping_with_failures(self):
        """Test that failures are handled in mapping."""

        def failing_add(a, b):
            if a == 2:
                raise ValueError("Test error")
            return a + b

        a_list = [1, 2, 3]
        b_list = [4, 5, 6]
        result = map_parallel(
            failing_add, a_list, b_list, max_workers=2, show_progress=False
        )
        assert result[0] == 5
        assert result[1] is None  # Failed
        assert result[2] == 9

    def test_single_iterable(self):
        """Test mapping with single iterable."""

        def square(x):
            return x * x

        items = [1, 2, 3]
        result = map_parallel(square, items, max_workers=2, show_progress=False)
        assert result == [1, 4, 9]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_max_workers(self):
        """Test that zero max_workers uses default."""

        def double(x):
            return x * 2

        items = [1, 2]
        # Should not raise, but behavior depends on executor
        result = process_parallel(items, double, max_workers=0, show_progress=False)
        assert len(result) == 2

    def test_very_large_max_workers(self):
        """Test with very large max_workers value."""

        def double(x):
            return x * 2

        items = [1, 2, 3]
        result = process_parallel(items, double, max_workers=1000, show_progress=False)
        assert result == [2, 4, 6]

    def test_all_items_fail(self):
        """Test when all items fail."""

        def always_fail(x):
            raise RuntimeError("Always fails")

        items = [1, 2, 3]
        result = process_parallel(
            items, always_fail, max_workers=2, show_progress=False
        )
        assert result == [None, None, None]

    def test_mixed_success_failure(self):
        """Test mixed success and failure scenarios."""

        def conditional_func(x):
            if x % 2 == 0:
                raise ValueError("Even numbers fail")
            return x * 2

        items = [1, 2, 3, 4, 5]
        result = process_parallel(
            items, conditional_func, max_workers=2, show_progress=False
        )
        assert result[0] == 2  # 1 * 2
        assert result[1] is None  # Failed
        assert result[2] == 6  # 3 * 2
        assert result[3] is None  # Failed
        assert result[4] == 10  # 5 * 2

    def test_none_return_values(self):
        """Test that None return values are preserved."""

        def return_none(x):
            return None

        items = [1, 2, 3]
        result = process_parallel(
            items, return_none, max_workers=2, show_progress=False
        )
        assert result == [None, None, None]

    def test_large_input_list(self):
        """Test with large input list."""

        def identity(x):
            return x

        items = list(range(1000))
        result = process_parallel(items, identity, max_workers=4, show_progress=False)
        assert len(result) == 1000
        assert result == items
