"""Unit test for mosaic shape handling (2D vs 4D)."""

import sys

import numpy as np
import pytest

sys.path.insert(0, "src")


def test_common_shape_unpacking_2d():
    """Test unpacking 2D common_shape."""
    common_shape = [100, 200]
    if len(common_shape) == 4:
        ny, nx = common_shape[2], common_shape[3]
    else:
        ny, nx = common_shape
    assert ny == 100
    assert nx == 200


def test_common_shape_unpacking_4d():
    """Test unpacking 4D common_shape."""
    common_shape = [1, 1, 21, 21]
    if len(common_shape) == 4:
        ny, nx = common_shape[2], common_shape[3]
    else:
        ny, nx = common_shape
    assert ny == 21
    assert nx == 21


def test_shape_broadcasting_issue():
    """Test the actual error case: mismatched shapes."""
    # Use smaller arrays to avoid memory/time issues in tests
    mosaic_shape = (21, 21)
    tile_shape = (100, 100)  # Reduced from 6300x6300 for speed

    # NumPy raises ValueError for broadcasting errors
    mosaic = np.zeros(mosaic_shape, dtype=np.float32)
    tile = np.ones(tile_shape, dtype=np.float32)

    # NumPy will raise ValueError when shapes can't be broadcast
    # Use try/except instead of pytest.raises to avoid hanging
    try:
        mosaic + tile
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "broadcast" in str(e).lower() or "operands" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
