#!/usr/bin/env python3
"""
Test script for FITS visualization functionality.

Tests FITSFile class, JS9 integration, and related functionality.
"""

from dsa110_contimg.qa.visualization import FITSFile, ls, init_js9, is_js9_available
import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Also add the project root for imports
project_root = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_fitsfile_basic():
    """Test basic FITSFile functionality."""
    print("Testing FITSFile basic functionality...")

    # Test with non-existent file (should handle gracefully)
    try:
        fits = FITSFile("/nonexistent/file.fits")
        assert not fits.exists
        print("✓ Non-existent file handling works")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test properties
    try:
        fits = FITSFile("/tmp/test.fits")
        assert fits.basename == "test.fits"
        assert fits.path == "/tmp/test.fits"
        print("✓ File properties work")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    print("✓ All basic FITSFile tests passed\n")
    return True


def test_fitsfile_header():
    """Test FITS header reading (if astropy available)."""
    print("Testing FITS header reading...")

    try:
        from astropy.io import fits
        import numpy as np

        # Create a test FITS file
        test_fits_path = "/tmp/test_fits_visualization.fits"
        data = np.random.randn(100, 100)
        hdu = fits.PrimaryHDU(data=data)
        hdu.header["NAXIS"] = 2
        hdu.header["NAXIS1"] = 100
        hdu.header["NAXIS2"] = 100
        hdu.header["CTYPE1"] = "RA---TAN"
        hdu.header["CTYPE2"] = "DEC--TAN"
        hdu.header["CDELT1"] = -0.001  # degrees
        hdu.header["CDELT2"] = 0.001
        hdu.writeto(test_fits_path, overwrite=True)

        # Test FITSFile with real file
        fits_file = FITSFile(test_fits_path)
        assert fits_file.exists
        print(f"✓ FITS file exists: {fits_file.exists}")

        # Test header reading
        header = fits_file.header
        assert header is not None
        print(f"✓ Header reading works (length: {len(header)} chars)")

        # Test shape
        shape = fits_file.shape
        assert shape == [100, 100]
        print(f"✓ Shape extraction works: {shape}")

        # Test summary
        summary = fits_file.summary
        assert summary is not None
        print(f"✓ Summary generation works: {summary[:50]}...")

        # Test summary items
        items = fits_file._get_summary_items()
        assert len(items) == 5
        print(f"✓ Summary items: {items}")

        # Cleanup
        os.remove(test_fits_path)
        print("✓ Test FITS file cleaned up")

    except ImportError:
        print("⚠ astropy not available, skipping header tests")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("✓ All FITS header tests passed\n")
    return True


def test_js9_integration():
    """Test JS9 integration."""
    print("Testing JS9 integration...")

    try:
        # Test JS9 availability check
        available = is_js9_available()
        print(f"✓ JS9 availability check: {available}")

        # Test JS9 initialization (won't actually initialize without IPython)
        # But we can test the function exists and doesn't crash
        try:
            result = init_js9()
            print(f"✓ JS9 initialization function works (result: {result})")
        except Exception as e:
            print(f"⚠ JS9 initialization error (expected without IPython): {type(e).__name__}")

        # Test get_js9_init_html
        from dsa110_contimg.qa.visualization.js9 import get_js9_init_html

        html = get_js9_init_html()
        assert html is not None
        print(f"✓ JS9 init HTML generation works (length: {len(html)} chars)")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("✓ All JS9 integration tests passed\n")
    return True


def test_fitsfile_integration():
    """Test FITSFile integration with file lists."""
    print("Testing FITSFile integration with file lists...")

    try:
        from dsa110_contimg.qa.visualization import FileList

        # Create actual test files for file type detection
        test_files = []
        for i, ext in enumerate([".fits", ".fits", ".png"]):
            test_file = f"/tmp/test_fits_integration_{i}{ext}"
            # Create minimal FITS file
            if ext == ".fits":
                with open(test_file, "w") as f:
                    f.write("SIMPLE  =                    T / FITS file\n")
            else:
                # Create dummy PNG (just empty file for test)
                with open(test_file, "w") as f:
                    f.write("PNG")
            test_files.append(test_file)

        filelist = FileList(content=test_files)
        print(f"✓ FileList created with {len(filelist)} items")

        # Test FITS filtering
        fits_files = filelist.fits
        assert len(fits_files) == 2, f"Expected 2 FITS files, got {len(fits_files)}"
        print(f"✓ FITS filtering works: {len(fits_files)} FITS files")

        # Verify they are FITSFile instances
        for fits_file in fits_files:
            assert isinstance(fits_file, FITSFile)
        print("✓ FITS files are FITSFile instances")

        # Cleanup test files
        for test_file in test_files:
            if os.path.exists(test_file):
                os.remove(test_file)

        # Test directory browsing with FITS files
        # Create a test directory with FITS files
        test_dir = "/tmp/test_fits_dir"
        os.makedirs(test_dir, exist_ok=True)

        # Create dummy FITS files
        for i in range(3):
            test_fits = os.path.join(test_dir, f"test_{i}.fits")
            with open(test_fits, "w") as f:
                f.write("SIMPLE  =                    T / FITS file\n")

        # Test ls() with FITS files
        dir_list = ls(test_dir)
        fits_in_dir = dir_list.fits
        print(f"✓ Directory browsing found {len(fits_in_dir)} FITS files")

        # Cleanup
        import shutil

        shutil.rmtree(test_dir)
        print("✓ Test directory cleaned up")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("✓ All integration tests passed\n")
    return True


def test_fitsfile_show():
    """Test FITSFile.show() method (without actual display)."""
    print("Testing FITSFile.show() method...")

    try:
        from astropy.io import fits
        import numpy as np

        # Create a test FITS file
        test_fits_path = "/tmp/test_show.fits"
        data = np.random.randn(50, 50)
        hdu = fits.PrimaryHDU(data=data)
        hdu.writeto(test_fits_path, overwrite=True)

        fits_file = FITSFile(test_fits_path)

        # Test that show() method exists and can be called
        # (won't actually display without IPython, but shouldn't crash)
        try:
            # This will fail gracefully without IPython
            fits_file.show()
            print("✓ show() method callable")
        except Exception as e:
            # Expected without IPython
            if "IPython" in str(e) or "display" in str(e).lower():
                print("✓ show() method exists (IPython not available, expected)")
            else:
                raise

        # Test HTML rendering methods
        summary_html = fits_file._render_summary_html()
        assert summary_html is not None
        assert len(summary_html) > 0
        print(f"✓ Summary HTML rendering works (length: {len(summary_html)} chars)")

        js9_html = fits_file._render_js9_html()
        assert js9_html is not None
        assert len(js9_html) > 0
        print(f"✓ JS9 HTML rendering works (length: {len(js9_html)} chars)")

        # Cleanup
        os.remove(test_fits_path)

    except ImportError:
        print("⚠ astropy not available, skipping show() tests")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("✓ All show() method tests passed\n")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("FITS Visualization Framework - Testing")
    print("=" * 60)
    print()

    tests = [
        ("Basic Functionality", test_fitsfile_basic),
        ("Header Reading", test_fitsfile_header),
        ("JS9 Integration", test_js9_integration),
        ("File List Integration", test_fitsfile_integration),
        ("Show Method", test_fitsfile_show),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Test '{name}' failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
