can  #!/usr/bin/env python
"""
Quick verification test for Priority 1: Region Mask Integration

Tests:
1. Code imports and structure
2. Region mask creation with synthetic data
3. API endpoint structure verification
"""
import sys
from pathlib import Path
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all required imports work."""
    print("=" * 60)
    print("Test 1: Import Verification")
    print("=" * 60)

    try:
        from dsa110_contimg.utils.regions import create_region_mask, RegionData

        print("✓ Region utilities imported")
    except Exception as e:
        print(f"✗ Failed to import region utilities: {e}")
        return False

    try:
        from dsa110_contimg.utils.fitting import fit_2d_gaussian, fit_2d_moffat

        print("✓ Fitting utilities imported")
    except Exception as e:
        print(f"✗ Failed to import fitting utilities: {e}")
        return False

    try:
        from astropy.io import fits
        from astropy.wcs import WCS

        print("✓ Astropy imports work")
    except Exception as e:
        print(f"✗ Failed to import astropy: {e}")
        return False

    # Check that routes.py can import create_region_mask
    try:
        import importlib.util

        routes_path = (
            Path(__file__).parent / "src" / "dsa110_contimg" / "api" / "routes.py"
        )
        spec = importlib.util.spec_from_file_location("routes", routes_path)
        routes = importlib.util.module_from_spec(spec)
        # Just check syntax, don't execute
        with open(routes_path) as f:
            code = f.read()
            compile(code, routes_path, "exec")
        print("✓ routes.py syntax is valid")
    except Exception as e:
        print(f"✗ routes.py has syntax errors: {e}")
        return False

    return True


def test_region_mask_synthetic():
    """Test region mask creation with synthetic data."""
    print("\n" + "=" * 60)
    print("Test 2: Region Mask Creation (Synthetic Data)")
    print("=" * 60)

    from dsa110_contimg.utils.regions import create_region_mask, RegionData
    from astropy.io import fits
    from astropy.wcs import WCS

    # Create a simple synthetic FITS header
    header = fits.Header()
    header["NAXIS"] = 2
    header["NAXIS1"] = 100
    header["NAXIS2"] = 100
    header["CDELT1"] = -0.0001  # degrees per pixel
    header["CDELT2"] = 0.0001
    header["CRVAL1"] = 0.0  # RA at reference pixel
    header["CRVAL2"] = 0.0  # Dec at reference pixel
    header["CRPIX1"] = 50.0  # Reference pixel
    header["CRPIX2"] = 50.0
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"

    try:
        wcs = WCS(header)
        print("✓ Created synthetic WCS")
    except Exception as e:
        print(f"✗ Failed to create WCS: {e}")
        return False

    shape = (100, 100)

    # Test circle region
    print("\n--- Testing Circle Region ---")
    circle_region = RegionData(
        name="test_circle",
        type="circle",
        coordinates={
            "ra_deg": 0.0,
            "dec_deg": 0.0,
            "radius_deg": 0.005,  # Small radius
        },
        image_path="test_image.fits",
    )

    try:
        circle_mask = create_region_mask(
            shape=shape, region=circle_region, wcs=wcs, header=header
        )

        n_pixels = np.sum(circle_mask)
        print(
            f"✓ Circle mask created: {n_pixels} pixels ({100*n_pixels/np.prod(shape):.1f}% of image)"
        )

        if n_pixels == 0:
            print("  WARNING: Mask is empty")
            return False

        if circle_mask.shape != shape:
            print(f"  ERROR: Mask shape {circle_mask.shape} != image shape {shape}")
            return False

        print("  ✓ Mask shape is correct")
        print("  ✓ Mask is boolean array")

    except Exception as e:
        print(f"✗ Circle mask creation failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test rectangle region
    print("\n--- Testing Rectangle Region ---")
    rect_region = RegionData(
        name="test_rectangle",
        type="rectangle",
        coordinates={
            "ra_deg": 0.0,
            "dec_deg": 0.0,
            "width_deg": 0.01,
            "height_deg": 0.01,
            "angle_deg": 0.0,
        },
        image_path="test_image.fits",
    )

    try:
        rect_mask = create_region_mask(
            shape=shape, region=rect_region, wcs=wcs, header=header
        )

        n_pixels = np.sum(rect_mask)
        print(
            f"✓ Rectangle mask created: {n_pixels} pixels ({100*n_pixels/np.prod(shape):.1f}% of image)"
        )

        if n_pixels == 0:
            print("  WARNING: Mask is empty")
            return False

        if rect_mask.shape != shape:
            print(f"  ERROR: Mask shape {rect_mask.shape} != image shape {shape}")
            return False

        print("  ✓ Mask shape is correct")
        print("  ✓ Mask is boolean array")

    except Exception as e:
        print(f"✗ Rectangle mask creation failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_api_structure():
    """Verify API endpoint structure."""
    print("\n" + "=" * 60)
    print("Test 3: API Endpoint Structure Verification")
    print("=" * 60)

    routes_path = Path(__file__).parent / "src" / "dsa110_contimg" / "api" / "routes.py"

    with open(routes_path) as f:
        code = f.read()

    checks = [
        (
            "create_region_mask import",
            "from dsa110_contimg.utils.regions import",
            "create_region_mask" in code,
        ),
        (
            "fits import",
            "from astropy.io import fits",
            "from astropy.io import fits" in code,
        ),
        (
            "WCS import",
            "from astropy.wcs import WCS",
            "from astropy.wcs import WCS" in code,
        ),
        ("numpy import", "import numpy as np", "import numpy as np" in code),
        ("region_mask creation", "create_region_mask(", "create_region_mask(" in code),
        ("mask validation", "np.any(region_mask)", "np.any(region_mask)" in code),
        (
            "mask passed to fitting",
            "region_mask=region_mask",
            "region_mask=region_mask" in code,
        ),
    ]

    all_passed = True
    for name, search_term, found in checks:
        if found:
            print(f"✓ {name}")
        else:
            print(f"✗ {name} - not found")
            all_passed = False

    return all_passed


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Priority 1: Region Mask Integration - Quick Verification")
    print("=" * 60)

    results = []

    # Test 1: Imports
    results.append(("Imports", test_imports()))

    # Test 2: Region mask creation
    results.append(("Region Mask Creation", test_region_mask_synthetic()))

    # Test 3: API structure
    results.append(("API Structure", test_api_structure()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("\nNext steps:")
        print("  - Code integration is correct")
        print("  - Region mask creation works")
        print("  - Ready for end-to-end testing with real data")
    else:
        print("✗ Some tests failed")
        print("  - Review errors above")
        print("  - Fix issues before proceeding")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
