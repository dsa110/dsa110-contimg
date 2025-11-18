"""Tests for circular import prevention in conversion.strategies module.

These tests ensure the __getattr__ lazy loading mechanism works correctly
and doesn't cause infinite recursion.
"""

import pytest


class TestCircularImportPrevention:
    """Test that circular imports are properly prevented."""

    def test_import_convert_function(self):
        """Test importing convert function doesn't cause recursion."""
        from dsa110_contimg.conversion.strategies import (
            convert_subband_groups_to_ms,
        )

        assert callable(convert_subband_groups_to_ms)
        assert convert_subband_groups_to_ms.__name__ == "convert_subband_groups_to_ms"  # noqa: E501

    def test_import_module_directly(self):
        """Test importing the hdf5_orchestrator module directly."""
        from dsa110_contimg.conversion.strategies import hdf5_orchestrator

        assert hasattr(hdf5_orchestrator, "convert_subband_groups_to_ms")
        assert hasattr(hdf5_orchestrator, "find_subband_groups")

    def test_nonexistent_attribute_raises_error(self):
        """Test that accessing nonexistent attributes raises AttributeError."""
        import dsa110_contimg.conversion.strategies as strategies

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = strategies.nonexistent_function


class TestImportPerformance:
    """Test that imports are reasonably fast (no infinite loops)."""

    def test_import_completes_quickly(self):
        """Test that importing doesn't hang or take excessive time."""
        import time

        start = time.time()
        from dsa110_contimg.conversion.strategies import (
            convert_subband_groups_to_ms,
        )

        elapsed = time.time() - start

        # Should complete in under 1 second
        assert elapsed < 1.0, f"Import took {elapsed:.2f}s (too slow)"
        assert callable(convert_subband_groups_to_ms)
