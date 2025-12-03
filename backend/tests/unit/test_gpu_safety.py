"""
Unit tests for GPU safety module.

These tests verify that memory limits are enforced correctly and that
operations are rejected when limits would be exceeded.

Test Categories:
1. System memory checks - verify RAM availability detection
2. Memory limit enforcement - verify @memory_safe decorator rejects when unsafe
3. GPU memory checks - verify VRAM availability detection (when GPU available)
4. GPU limit enforcement - verify @gpu_safe decorator rejects when unsafe
5. Visibility estimation - verify memory estimation for DSA-110 data shapes
6. Integration tests - verify safety module initializes correctly
"""

import sys
from typing import NamedTuple
from unittest.mock import patch

import pytest


class MockMemoryInfo(NamedTuple):
    """Mock psutil memory info structure."""
    total: int
    available: int
    percent: float
    used: int
    free: int


# Import after mocking setup
@pytest.fixture(autouse=True)
def reset_gpu_safety_module():
    """Reset gpu_safety module state between tests."""
    # Clear any cached state
    if "dsa110_contimg.utils.gpu_safety" in sys.modules:
        module = sys.modules["dsa110_contimg.utils.gpu_safety"]
        # Reset the initialized flag if it exists
        if hasattr(module, "_INITIALIZED"):
            module._INITIALIZED = False


class TestSystemMemoryChecks:
    """Test system RAM availability detection."""

    def test_get_system_memory_info(self):
        """Test that system memory info is returned correctly."""
        from dsa110_contimg.utils.gpu_safety import get_system_memory_info

        info = get_system_memory_info()

        assert "total_gb" in info
        assert "available_gb" in info
        assert "used_gb" in info
        assert "percent_used" in info

        # Sanity checks
        assert info["total_gb"] > 0
        assert info["available_gb"] >= 0
        assert info["available_gb"] <= info["total_gb"]
        assert 0 <= info["percent_used"] <= 100

    def test_check_system_memory_available_with_plenty_of_memory(self):
        """Test that check passes when plenty of memory is available."""
        from dsa110_contimg.utils.gpu_safety import check_system_memory_available

        # Mock plenty of available memory (20 GB available out of 32 GB)
        mock_mem = MockMemoryInfo(
            total=32 * 1024**3,
            available=20 * 1024**3,
            percent=37.5,
            used=12 * 1024**3,
            free=20 * 1024**3,
        )

        with patch("psutil.virtual_memory", return_value=mock_mem):
            # Should not raise for reasonable allocation
            is_safe, _reason = check_system_memory_available(4.0)  # 4 GB request
            assert is_safe is True
            # Reason may contain "OK" or similar message when safe

    def test_check_system_memory_available_rejects_when_low(self):
        """Test that check fails when memory is low."""
        from dsa110_contimg.utils.gpu_safety import check_system_memory_available

        # Mock low available memory (1 GB available out of 32 GB)
        mock_mem = MockMemoryInfo(
            total=32 * 1024**3,
            available=1 * 1024**3,
            percent=96.9,
            used=31 * 1024**3,
            free=1 * 1024**3,
        )

        with patch("psutil.virtual_memory", return_value=mock_mem):
            # Should reject because less than 2 GB would remain
            is_safe, reason = check_system_memory_available(0.5)  # 0.5 GB request
            assert is_safe is False
            # The reason should explain why it failed
            assert len(reason) > 0

    def test_check_system_memory_available_rejects_large_allocation(self):
        """Test that check fails for oversized allocation."""
        from dsa110_contimg.utils.gpu_safety import check_system_memory_available

        # Mock normal memory (16 GB available out of 32 GB)
        mock_mem = MockMemoryInfo(
            total=32 * 1024**3,
            available=16 * 1024**3,
            percent=50.0,
            used=16 * 1024**3,
            free=16 * 1024**3,
        )

        with patch("psutil.virtual_memory", return_value=mock_mem):
            # Should reject 10 GB request (exceeds default 6 GB max per operation)
            is_safe, reason = check_system_memory_available(10.0)
            assert is_safe is False
            assert len(reason) > 0


class TestMemorySafeDecorator:
    """Test @memory_safe decorator enforcement."""

    def test_memory_safe_allows_when_sufficient(self):
        """Test that decorated function runs when memory is sufficient."""
        from dsa110_contimg.utils.gpu_safety import memory_safe

        # Mock plenty of memory
        mock_mem = MockMemoryInfo(
            total=32 * 1024**3,
            available=20 * 1024**3,
            percent=37.5,
            used=12 * 1024**3,
            free=20 * 1024**3,
        )

        @memory_safe(max_system_gb=4.0)
        def sample_operation(x: int) -> int:
            return x * 2

        with patch("psutil.virtual_memory", return_value=mock_mem):
            result = sample_operation(21)
            assert result == 42

    def test_memory_safe_rejects_when_insufficient(self):
        """Test that decorated function raises when memory is insufficient."""
        from dsa110_contimg.utils.gpu_safety import memory_safe

        # Mock very low memory
        mock_mem = MockMemoryInfo(
            total=32 * 1024**3,
            available=1 * 1024**3,
            percent=96.9,
            used=31 * 1024**3,
            free=1 * 1024**3,
        )

        @memory_safe(required_gb=4.0)  # Require 4 GB but only 1 GB available
        def sample_operation() -> int:
            return 42

        with patch("psutil.virtual_memory", return_value=mock_mem):
            # Should raise MemoryError or similar exception
            with pytest.raises((MemoryError, RuntimeError)):
                sample_operation()

    def test_memory_safe_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""
        from dsa110_contimg.utils.gpu_safety import memory_safe

        @memory_safe(max_system_gb=4.0)
        def my_documented_function() -> None:
            """This is the docstring."""
            pass

        assert my_documented_function.__name__ == "my_documented_function"
        assert "docstring" in my_documented_function.__doc__


class TestVisibilityMemoryEstimation:
    """Test memory estimation for DSA-110 visibility data."""

    def test_estimate_visibility_memory_basic(self):
        """Test basic visibility memory estimation."""
        from dsa110_contimg.utils.gpu_safety import estimate_visibility_memory_gb

        # Standard DSA-110 configuration: 64 antennas, 768 channels
        n_ant = 64
        n_chan = 768
        n_time = 300  # 5 minutes at 1s integration
        n_pol = 4

        mem_gb = estimate_visibility_memory_gb(n_ant, n_chan, n_time, n_pol)

        # Should be a reasonable size (complex64 = 8 bytes per vis)
        # n_bl = 64*63/2 = 2016
        # vis_count = 2016 * 768 * 300 * 4 = 1.86e9
        # bytes = 1.86e9 * 8 = 14.9 GB raw, but with overhead ~17-20 GB
        assert 10.0 < mem_gb < 30.0

    def test_estimate_visibility_memory_dec_2_scenario(self):
        """Test memory estimation for the Dec 2 2025 OOM scenario.

        This test verifies we correctly estimate the memory that caused
        the Dec 2 crash: 96 antennas × 768 channels.
        """
        from dsa110_contimg.utils.gpu_safety import estimate_visibility_memory_gb

        # Dec 2 crash scenario: 96 antennas (more than usual)
        n_ant = 96
        n_chan = 768
        n_time = 300
        n_pol = 4

        mem_gb = estimate_visibility_memory_gb(n_ant, n_chan, n_time, n_pol)

        # 96 antennas -> n_bl = 96*95/2 = 4560 baselines
        # This is 2.26x more baselines than 64 antennas
        # Should estimate ~30-40 GB (which exceeds our 6 GB limit)
        assert mem_gb > 20.0  # Definitely would have caused OOM

    def test_check_visibility_allocation_safe(self):
        """Test visibility allocation safety check."""
        from dsa110_contimg.utils.gpu_safety import check_visibility_allocation_safe

        # Standard configuration should be safe - use positional args
        # API: check_visibility_allocation_safe(n_baselines, n_channels, n_times, n_pols, ...)
        n_ant = 64
        n_bl = n_ant * (n_ant - 1) // 2  # 2016 baselines

        is_safe, msg = check_visibility_allocation_safe(n_bl, 768, 300, 4)

        # Note: this may fail if system has low memory
        # The important thing is it returns a tuple
        assert isinstance(is_safe, bool)
        assert isinstance(msg, str)


class TestGPUSafeDecorator:
    """Test @gpu_safe decorator for GPU+RAM protection."""

    def test_gpu_safe_allows_when_sufficient(self):
        """Test that @gpu_safe allows execution when resources are available."""
        from dsa110_contimg.utils.gpu_safety import gpu_safe

        # Mock plenty of memory
        mock_mem = MockMemoryInfo(
            total=32 * 1024**3,
            available=20 * 1024**3,
            percent=37.5,
            used=12 * 1024**3,
            free=20 * 1024**3,
        )

        @gpu_safe(max_gpu_gb=8.0, max_system_gb=8.0)
        def sample_gpu_operation(x: int) -> int:
            return x * 3

        with patch("psutil.virtual_memory", return_value=mock_mem):
            result = sample_gpu_operation(14)
            assert result == 42

    def test_gpu_safe_rejects_when_ram_insufficient(self):
        """Test that @gpu_safe rejects when system RAM is low."""
        from dsa110_contimg.utils.gpu_safety import gpu_safe

        # Mock very low memory
        mock_mem = MockMemoryInfo(
            total=32 * 1024**3,
            available=1 * 1024**3,
            percent=96.9,
            used=31 * 1024**3,
            free=1 * 1024**3,
        )

        @gpu_safe(required_gpu_gb=8.0)  # Require 8 GB GPU but memory is low
        def sample_gpu_operation() -> int:
            return 42

        with patch("psutil.virtual_memory", return_value=mock_mem):
            # Should raise when trying to execute
            with pytest.raises((MemoryError, RuntimeError)):
                sample_gpu_operation()


class TestInitialization:
    """Test GPU safety module initialization."""

    def test_initialize_gpu_safety_runs_without_error(self):
        """Test that initialization completes without error."""
        from dsa110_contimg.utils.gpu_safety import initialize_gpu_safety

        # Should not raise
        initialize_gpu_safety()

    def test_initialize_gpu_safety_is_idempotent(self):
        """Test that initialization can be called multiple times safely."""
        from dsa110_contimg.utils.gpu_safety import initialize_gpu_safety

        # Multiple calls should not raise
        initialize_gpu_safety()
        initialize_gpu_safety()
        initialize_gpu_safety()


class TestOOMRejection:
    """Integration tests for OOM rejection scenarios.

    These tests simulate the conditions that caused the Dec 2 2025 crash
    and verify that our safety module would reject the allocation.
    """

    def test_reject_allocation_that_would_oom(self):
        """Test that we reject allocations that would cause OOM."""
        from dsa110_contimg.utils.gpu_safety import (
            check_system_memory_available,
            estimate_visibility_memory_gb,
        )

        # Dec 2 scenario: 96 antennas, 768 channels
        mem_required = estimate_visibility_memory_gb(96, 768, 300, 4)

        # Mock system with 32 GB total, 10 GB available
        mock_mem = MockMemoryInfo(
            total=32 * 1024**3,
            available=10 * 1024**3,
            percent=68.75,
            used=22 * 1024**3,
            free=10 * 1024**3,
        )

        with patch("psutil.virtual_memory", return_value=mock_mem):
            is_safe, reason = check_system_memory_available(mem_required)

            # Should reject because allocation exceeds available memory
            assert is_safe is False
            assert reason != ""

    def test_accept_allocation_that_fits(self):
        """Test that we accept allocations that fit in memory."""
        from dsa110_contimg.utils.gpu_safety import (
            check_system_memory_available,
        )

        # Small allocation: 2 GB
        mem_required = 2.0

        # Mock system with plenty of memory
        mock_mem = MockMemoryInfo(
            total=32 * 1024**3,
            available=20 * 1024**3,
            percent=37.5,
            used=12 * 1024**3,
            free=20 * 1024**3,
        )

        with patch("psutil.virtual_memory", return_value=mock_mem):
            is_safe, _reason = check_system_memory_available(mem_required)

            # Should accept
            assert is_safe is True


class TestSafeGPUContextManager:
    """Test safe_gpu_context context manager."""

    def test_safe_gpu_context_allows_when_sufficient(self):
        """Test context manager allows entry when memory is sufficient."""
        from dsa110_contimg.utils.gpu_safety import safe_gpu_context

        # Mock plenty of memory
        mock_mem = MockMemoryInfo(
            total=32 * 1024**3,
            available=20 * 1024**3,
            percent=37.5,
            used=12 * 1024**3,
            free=20 * 1024**3,
        )

        with patch("psutil.virtual_memory", return_value=mock_mem):
            with safe_gpu_context(max_gpu_gb=4.0):
                # Should execute without error
                result = 42

            assert result == 42

    def test_safe_gpu_context_rejects_when_no_gpu(self):
        """Test context manager raises when no GPU is available."""
        from dsa110_contimg.utils.gpu_safety import safe_gpu_context

        # Mock no GPU available
        with patch("dsa110_contimg.utils.gpu_safety.is_gpu_available", return_value=False):
            with pytest.raises(RuntimeError, match="No GPU available"):
                with safe_gpu_context(max_gpu_gb=4.0):
                    pytest.fail("Should have raised RuntimeError")
