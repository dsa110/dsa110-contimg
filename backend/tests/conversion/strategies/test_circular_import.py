"""
Unit tests for circular import fix in dsa110_contimg.conversion.strategies.

This test ensures the lazy loading mechanism works correctly and prevents
infinite recursion when importing conversion strategy modules.
"""

import sys

import pytest


def test_no_circular_import():
    """Test that importing strategies does not cause circular import."""
    # Remove module from cache if present
    module_name = "dsa110_contimg.conversion.strategies"
    if module_name in sys.modules:
        del sys.modules[module_name]

    # This should not raise RecursionError
    try:
        import dsa110_contimg.conversion.strategies as strategies

        assert strategies is not None
    except RecursionError:
        pytest.fail("Circular import detected - RecursionError raised")


def test_lazy_loading_hdf5_orchestrator():
    """Test that hdf5_orchestrator can be lazily loaded."""
    from dsa110_contimg.conversion.strategies import hdf5_orchestrator

    assert hdf5_orchestrator is not None
    assert hasattr(hdf5_orchestrator, "convert_subband_groups_to_ms")


def test_getattr_mechanism():
    """Test that the __getattr__ mechanism works correctly."""
    import dsa110_contimg.conversion.strategies as strategies

    # Test that accessing a valid submodule works
    hdf5_orch = strategies.hdf5_orchestrator
    assert hdf5_orch is not None

    # Test that accessing an invalid attribute raises AttributeError
    with pytest.raises(AttributeError):
        _ = strategies.nonexistent_module


def test_no_infinite_recursion_on_hasattr():
    """Test that hasattr() doesn't trigger infinite recursion."""
    import dsa110_contimg.conversion.strategies as strategies

    # This should not cause infinite recursion
    has_importing = hasattr(strategies, "_importing")
    assert isinstance(has_importing, bool)
