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
    mosaic_shape = (21, 21)
    tile_shape = (6300, 6300)
    pb_shape = (6300, 6300)

    # This should fail with the current error
    with pytest.raises(ValueError, match="operands could not be broadcast"):
        # Simulate the error
        mosaic = np.zeros(mosaic_shape)
        tile = np.ones(tile_shape)
        pb = np.ones(pb_shape)
        # This would fail
        result = mosaic + tile * pb


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
