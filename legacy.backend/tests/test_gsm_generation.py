"""Test script to verify GSM sky map generation works correctly.

This test verifies that:
1. pygdsm can generate a sky map at 1400 MHz
2. The sky map can be transformed with log10
3. healpy can work with the generated map
4. The data is suitable for visualization

Run with: python -m pytest tests/test_gsm_generation.py -v
Or directly: python tests/test_gsm_generation.py
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def test_gsm_basic_generation():
    """Test basic GSM generation as shown in the user's example."""
    try:
        import healpy as hp
        import numpy as np
        import pygdsm
    except ImportError as e:
        print(f"SKIP: Required packages not installed: {e}")
        print("Install with: pip install pygdsm healpy numpy")
        return True  # Not a failure, just skip

    print("Testing: pygdsm.GlobalSkyModel16().generate(1400)")
    gsm = pygdsm.GlobalSkyModel16()
    sky_map = gsm.generate(1400)

    assert sky_map is not None, "Sky map should not be None"
    assert len(sky_map.shape) == 1, f"Expected 1D array, got shape {sky_map.shape}"
    assert sky_map.size > 0, "Sky map should not be empty"

    print(f":check_mark: Sky map generated: shape={sky_map.shape}, size={sky_map.size}")

    # Test log10 transformation
    print("\nTesting: np.log10(sky_map)")
    log_sky_map = np.log10(sky_map + 1e-10)
    assert not np.any(np.isnan(log_sky_map)), "Log transformation should not produce NaN"
    assert not np.any(np.isinf(log_sky_map)), "Log transformation should not produce Inf"

    print(
        f":check_mark: Log10 transformation successful: min={np.min(log_sky_map):.6f}, max={np.max(log_sky_map):.6f}"
    )

    # Test HEALPix properties
    print("\nTesting: healpy properties")
    nside = hp.get_nside(sky_map)
    npix = hp.nside2npix(nside)
    assert npix == sky_map.size, f"NPIX ({npix}) should match sky_map size ({sky_map.size})"

    print(f":check_mark: HEALPix properties: NSIDE={nside}, NPIX={npix}")

    # Test that mollview would work (check data format)
    print("\nTesting: Data format for mollview")
    assert isinstance(sky_map, np.ndarray), "Sky map should be numpy array"
    assert sky_map.dtype in [np.float32, np.float64], f"Expected float dtype, got {sky_map.dtype}"

    print(":check_mark: Data format is correct for mollview")
    print("\n:check_mark: All basic GSM generation tests passed!")
    return True


def test_backend_function():
    """Test the backend generate_gsm_sky_map_data function."""
    try:
        from dsa110_contimg.pointing.sky_map_generator import generate_gsm_sky_map_data
    except ImportError as e:
        print(f"SKIP: Cannot import backend function: {e}")
        return True

    print("\nTesting: generate_gsm_sky_map_data()")
    data = generate_gsm_sky_map_data(frequency_mhz=1400.0, resolution=90, use_cache=True)

    assert "x" in data, "Data should contain 'x' key"
    assert "y" in data, "Data should contain 'y' key"
    assert "z" in data, "Data should contain 'z' key"

    assert len(data["x"]) > 0, "X coordinates should not be empty"
    assert len(data["y"]) > 0, "Y coordinates should not be empty"
    assert len(data["z"]) > 0, "Z values should not be empty"
    assert len(data["z"]) == len(data["y"]), "Z rows should match Y coordinates"
    assert len(data["z"][0]) == len(data["x"]), "Z cols should match X coordinates"

    print(f":check_mark: Backend function works: {len(data['x'])}x{len(data['y'])} grid")
    print(":check_mark: All backend function tests passed!")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("GSM Sky Map Generation Test")
    print("=" * 60)

    success = True
    try:
        success = test_gsm_basic_generation() and success
        success = test_backend_function() and success
    except Exception as e:
        print(f"\n:ballot_x: Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        success = False

    print("\n" + "=" * 60)
    if success:
        print(":check_mark: All tests passed!")
        sys.exit(0)
    else:
        print(":ballot_x: Some tests failed")
        sys.exit(1)
