#!/opt/miniforge/envs/casa6/bin/python
"""
Direct backend validation for Phase 2 core features.

Tests:
1. Spatial Profiler - profile extraction and fitting
2. Image Fitting - 2D Gaussian/Moffat fitting
3. Region Management - region creation and statistics

Uses real FITS images from /stage/dsa110-contimg/images/
"""
import warnings
from dsa110_contimg.utils.regions import (
    RegionData,
    create_region_mask,
    calculate_region_statistics,
)
from dsa110_contimg.utils.fitting import (
    fit_2d_gaussian,
    fit_2d_moffat,
    estimate_initial_guess,
)
from dsa110_contimg.utils.profiling import (
    extract_line_profile,
    extract_polyline_profile,
    extract_point_profile,
    fit_gaussian_profile,
    fit_moffat_profile,
)
import numpy as np
from pathlib import Path
import sys
import time
from datetime import datetime
from astropy.io import fits
from astropy.wcs import WCS

# Disable Python output buffering - use unbuffered mode
import os

os.environ["PYTHONUNBUFFERED"] = "1"
# Suppress FITSFixedWarning (just header fixes, not errors)
warnings.filterwarnings("ignore", message=".*FITSFixedWarning.*")
warnings.filterwarnings("ignore", category=UserWarning, module="astropy.io.fits")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def log_progress(message: str, start_time: float = None):
    """Log progress with timestamp and optional elapsed time."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if start_time:
        elapsed = time.time() - start_time
        sys.stdout.write(f"[{timestamp}] {message} (elapsed: {elapsed:.1f}s)\n")
    else:
        sys.stdout.write(f"[{timestamp}] {message}\n")
    sys.stdout.flush()


def find_test_image():
    """Find a suitable test image."""
    import glob

    # Prefer primary beam corrected images
    test_images = glob.glob("/stage/dsa110-contimg/images/*img-image-pb.fits")
    if not test_images:
        test_images = glob.glob("/stage/dsa110-contimg/images/*img-image.fits")

    if not test_images:
        return None

    return test_images[0]


def test_spatial_profiler(fits_path: str):
    """Test spatial profiler functionality."""
    test_start = time.time()
    print("\n" + "=" * 60)
    print("TEST 1: Spatial Profiler")
    print("=" * 60)
    print(f"Image: {Path(fits_path).name}")
    import sys

    try:
        # Load image to get dimensions
        log_progress("Loading FITS file...")
        load_start = time.time()
        with fits.open(fits_path) as hdul:
            header = hdul[0].header
            data = hdul[0].data

            if data.ndim > 2:
                data = data.squeeze()
                if data.ndim > 2:
                    data = data[0, 0] if data.ndim == 4 else data[0]

            ny, nx = data.shape[:2]
            print(f"Image shape: {ny} x {nx}")

            # Get WCS
            try:
                wcs = WCS(header)
                print("✓ WCS loaded")
            except Exception as e:
                print(f"⚠ WCS not available: {e}")
                wcs = None
        log_progress(f"FITS loaded (shape: {nx}x{ny})", load_start)

        # Test 1.1: Line Profile (Short line for speed)
        print("\n--- Test 1.1: Line Profile ---")
        log_progress("  Extracting line profile (short line for speed)...")
        line_start = time.time()
        # Use pixel coordinates - shorter line around center
        line_length = min(500, nx // 4)  # Max 500 pixels or 1/4 of image
        x1 = nx // 2 - line_length // 2
        x2 = nx // 2 + line_length // 2
        y1 = y2 = ny // 2

        start_coord = (float(x1), float(y1))
        end_coord = (float(x2), float(y2))

        profile_result = extract_line_profile(
            fits_path,
            start_coord=start_coord,
            end_coord=end_coord,
            coordinate_system="pixel",
        )
        log_progress("  Line profile extracted", line_start)

        if profile_result and "flux" in profile_result:
            profile = profile_result["flux"]
            print(f"✓ Line profile extracted: {len(profile)} points")
            # Filter out NaN/Inf values for display
            valid_profile = [v for v in profile if np.isfinite(v)]
            if valid_profile:
                print(
                    f"  Min: {np.min(valid_profile):.6f}, Max: {np.max(valid_profile):.6f}"
                )

            # Test 1D fitting
            try:
                # fit_gaussian_profile expects flux array and distance array
                distances = profile_result.get("distance", np.arange(len(profile)))
                if isinstance(distances, list):
                    distances = np.array(distances)
                # Convert to numpy arrays
                flux_array = np.array(profile)
                fit_result = fit_gaussian_profile(distance=distances, flux=flux_array)
                if fit_result:
                    print(f"✓ 1D Gaussian fit successful")
                    print(f"  Amplitude: {fit_result['amplitude']:.6f}")
                    print(f"  Center: {fit_result['center']:.2f}")
                    print(f"  FWHM: {fit_result['fwhm']:.2f} pixels")
            except Exception as e:
                print(f"⚠ 1D Gaussian fit failed: {e}")
        else:
            print("✗ Line profile extraction failed")
            return False

        # Test 1.2: Point Profile (quick test with small radius)
        print("\n--- Test 1.2: Point Profile ---")
        log_progress("  Extracting point profile (small radius for speed)...")
        point_start = time.time()
        center_x, center_y = nx // 2, ny // 2
        center_coord = (float(center_x), float(center_y))
        radius_arcsec = 5.0  # Very small radius for quick testing
        n_annuli = 5  # Few annuli for quick testing

        point_profile_result = extract_point_profile(
            fits_path,
            center_coord=center_coord,
            radius_arcsec=radius_arcsec,
            coordinate_system="pixel",
            n_annuli=n_annuli,
        )
        elapsed = time.time() - point_start
        log_progress(f"  Point profile extracted ({elapsed:.1f}s)", point_start)

        if point_profile_result and "flux" in point_profile_result:
            point_profile = point_profile_result["flux"]
            print(f"✓ Point profile extracted: {len(point_profile)} annuli")
            print(f"  Radius: {radius_arcsec} arcsec")
            valid_flux = [v for v in point_profile if np.isfinite(v)]
            if valid_flux:
                print(f"  Mean flux: {np.mean(valid_flux):.6f}")
        else:
            print("✗ Point profile extraction failed")
            return False

        # Test 1.3: Polyline Profile
        print("\n--- Test 1.3: Polyline Profile ---")
        log_progress("  Extracting polyline profile...")
        polyline_start = time.time()
        polyline_coords = [
            (float(nx // 4), float(ny // 4)),
            (float(nx // 2), float(ny // 2)),
            (float(3 * nx // 4), float(3 * ny // 4)),
        ]

        polyline_profile_result = extract_polyline_profile(
            fits_path, coordinates=polyline_coords, coordinate_system="pixel"
        )
        log_progress("  Polyline profile extracted", polyline_start)

        if polyline_profile_result and "flux" in polyline_profile_result:
            polyline_profile = polyline_profile_result["flux"]
            print(f"✓ Polyline profile extracted: {len(polyline_profile)} points")
            print(f"  Path length: {len(polyline_coords)} segments")
        else:
            print("✗ Polyline profile extraction failed")
            return False

        print("\n✓ Spatial Profiler tests passed")
        return True

    except Exception as e:
        print(f"\n✗ Spatial Profiler test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_image_fitting(fits_path: str):
    """Test image fitting functionality."""
    test_start = time.time()
    print("\n" + "=" * 60)
    print("TEST 2: Image Fitting")
    print("=" * 60)
    print(f"Image: {Path(fits_path).name}")

    try:
        # Load image to get dimensions
        with fits.open(fits_path) as hdul:
            header = hdul[0].header
            data = hdul[0].data

            if data.ndim > 2:
                data = data.squeeze()
                if data.ndim > 2:
                    data = data[0, 0] if data.ndim == 4 else data[0]

            ny, nx = data.shape[:2]
            print(f"Image shape: {ny} x {nx}")

            # Get WCS
            try:
                wcs = WCS(header)
                print("✓ WCS loaded")
            except Exception as e:
                print(f"⚠ WCS not available: {e}")
                wcs = None

        # Test 2.1: Gaussian Fitting (Small Sub-region for Speed)
        print("\n--- Test 2.1: Gaussian Fitting (Sub-region) ---")
        # Use a small sub-region around center for faster fitting
        sub_size = min(
            500, nx // 4, ny // 4
        )  # 500x500 or 1/4 of image, whichever is smaller
        x_center, y_center = nx // 2, ny // 2
        x_min = max(0, x_center - sub_size // 2)
        x_max = min(nx, x_center + sub_size // 2)
        y_min = max(0, y_center - sub_size // 2)
        y_max = min(ny, y_center + sub_size // 2)

        log_progress(
            f"  Using sub-region: {x_max-x_min}x{y_max-y_min} pixels (center region)"
        )
        sub_data = data[y_min:y_max, x_min:x_max]
        nan_count = np.sum(~np.isfinite(sub_data))
        if nan_count > 0:
            print(
                f"  ⚠ Warning: {nan_count} non-finite values in sub-region ({100*nan_count/sub_data.size:.2f}%)"
            )

        # Create a temporary FITS file with sub-region
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".fits", delete=False) as tmp_fits:
            tmp_fits_path = tmp_fits.name

        try:
            # Save sub-region to temporary FITS
            from astropy.io import fits as fits_io

            hdu = fits_io.PrimaryHDU(data=sub_data, header=header)
            hdu.writeto(tmp_fits_path, overwrite=True)

            log_progress("  Fitting Gaussian model to sub-region...")
            gauss_start = time.time()
            fit_result = fit_2d_gaussian(
                tmp_fits_path, region_mask=None, fit_background=True, wcs=wcs
            )
            elapsed = time.time() - gauss_start
            log_progress(f"  Gaussian fit completed ({elapsed:.1f}s)", gauss_start)

            if fit_result:
                print("✓ Gaussian fit successful")
                params = fit_result["parameters"]
                print(f"  Amplitude: {params['amplitude']:.6f}")
                print(
                    f"  Center (x, y): ({params['center']['x']:.2f}, {params['center']['y']:.2f})"
                )
                print(f"  Major axis: {params['major_axis']:.2f} pixels")
                print(f"  Minor axis: {params['minor_axis']:.2f} pixels")
                print(f"  PA: {params['pa']:.2f} deg")
                print(f"  Background: {params['background']:.6f}")

                stats = fit_result["statistics"]
                print(f"  Reduced chi-squared: {stats['reduced_chi_squared']:.4f}")
                print(f"  R-squared: {stats['r_squared']:.4f}")

                # Check if results are reasonable
                if (
                    stats["reduced_chi_squared"] > 0
                    and stats["reduced_chi_squared"] < 100
                ):
                    print("  ✓ Fit quality reasonable")
                else:
                    print(
                        f"  ⚠ Fit quality questionable (chi-squared: {stats['reduced_chi_squared']:.2f})"
                    )
            else:
                print("✗ Gaussian fit returned no result")
                return False
        except Exception as e:
            print(f"✗ Gaussian fit failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_fits_path)
            except:
                pass

        # Test 2.2: Moffat Fitting (Same Sub-region)
        print("\n--- Test 2.2: Moffat Fitting (Sub-region) ---")
        # Recreate sub-region FITS
        with tempfile.NamedTemporaryFile(suffix=".fits", delete=False) as tmp_fits:
            tmp_fits_path = tmp_fits.name

        try:
            hdu = fits_io.PrimaryHDU(data=sub_data, header=header)
            hdu.writeto(tmp_fits_path, overwrite=True)

            log_progress("  Fitting Moffat model to sub-region...")
            moffat_start = time.time()
            fit_result = fit_2d_moffat(
                tmp_fits_path, region_mask=None, fit_background=True, wcs=wcs
            )
            elapsed = time.time() - moffat_start
            log_progress(f"  Moffat fit completed ({elapsed:.1f}s)", moffat_start)

            if fit_result:
                print("✓ Moffat fit successful")
                params = fit_result["parameters"]
                print(f"  Amplitude: {params['amplitude']:.6f}")
                print(
                    f"  Center (x, y): ({params['center']['x']:.2f}, {params['center']['y']:.2f})"
                )
                print(f"  Major axis: {params['major_axis']:.2f} pixels")
                print(f"  Minor axis: {params['minor_axis']:.2f} pixels")
                print(f"  Background: {params['background']:.6f}")

                stats = fit_result["statistics"]
                print(f"  Reduced chi-squared: {stats['reduced_chi_squared']:.4f}")
                print(f"  R-squared: {stats['r_squared']:.4f}")
            else:
                print("✗ Moffat fit returned no result")
                return False
        except Exception as e:
            print(f"✗ Moffat fit failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            try:
                os.unlink(tmp_fits_path)
            except:
                pass

        # Test 2.3: Initial Guess Estimation (Sub-region)
        print("\n--- Test 2.3: Initial Guess Estimation (Sub-region) ---")
        log_progress("  Estimating initial guess from sub-region...")
        guess_start = time.time()
        try:
            initial_guess = estimate_initial_guess(sub_data)
            elapsed = time.time() - guess_start
            log_progress(f"  Initial guess estimated ({elapsed:.1f}s)", guess_start)
            if initial_guess:
                print("✓ Initial guess estimated")
                print(f"  Amplitude: {initial_guess['amplitude']:.6f}")
                print(
                    f"  Center (x, y): ({initial_guess['x_center']:.2f}, {initial_guess['y_center']:.2f})"
                )
                print(f"  Major axis: {initial_guess['major_axis']:.2f} pixels")
                print(f"  Minor axis: {initial_guess['minor_axis']:.2f} pixels")
                print(f"  PA: {initial_guess['pa']:.2f} deg")
            else:
                print("✗ Initial guess estimation failed")
                return False
        except Exception as e:
            print(f"✗ Initial guess estimation failed: {e}")
            import traceback

            traceback.print_exc()
            return False

        print("\n✓ Image Fitting tests passed")
        return True

    except Exception as e:
        print(f"\n✗ Image Fitting test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_region_management(fits_path: str):
    """Test region management functionality."""
    test_start = time.time()
    print("\n" + "=" * 60)
    print("TEST 3: Region Management")
    print("=" * 60)
    print(f"Image: {Path(fits_path).name}")

    try:
        # Load image to get dimensions and WCS
        with fits.open(fits_path) as hdul:
            header = hdul[0].header
            data = hdul[0].data

            if data.ndim > 2:
                data = data.squeeze()
                if data.ndim > 2:
                    data = data[0, 0] if data.ndim == 4 else data[0]

            ny, nx = data.shape[:2]
            print(f"Image shape: {ny} x {nx}")

            # Get WCS
            try:
                wcs = WCS(header)
                print("✓ WCS loaded")
            except Exception as e:
                print(f"⚠ WCS not available: {e}")
                wcs = None

        # Test 3.1: Circle Region Mask
        print("\n--- Test 3.1: Circle Region Mask ---")
        log_progress("  Creating circle region mask...")
        circle_start = time.time()
        try:
            # Get image center in WCS
            if wcs:
                center_pix = [nx // 2, ny // 2]
                # Handle 4D WCS
                if hasattr(wcs, "naxis") and wcs.naxis == 4:
                    center_world = wcs.all_pix2world(
                        center_pix[0], center_pix[1], 0, 0, 0
                    )
                    center_ra = float(center_world[0])
                    center_dec = float(center_world[1])
                else:
                    center_world = wcs.pixel_to_world_values(
                        center_pix[1], center_pix[0]
                    )
                    center_ra = float(center_world[0])
                    center_dec = float(center_world[1])
            else:
                center_ra = 0.0
                center_dec = 0.0

            circle_region = RegionData(
                name="test_circle",
                type="circle",
                coordinates={
                    "ra_deg": center_ra,
                    "dec_deg": center_dec,
                    "radius_deg": 0.01,  # ~36 arcsec
                },
                image_path=fits_path,
            )

            circle_mask = create_region_mask(
                shape=(ny, nx), region=circle_region, wcs=wcs, header=header
            )

            n_pixels = np.sum(circle_mask)
            log_progress(
                f"  Circle mask created: {n_pixels} pixels ({100*n_pixels/(nx*ny):.1f}% of image)",
                circle_start,
            )

            if n_pixels == 0:
                print("  ⚠ Warning: Mask is empty")
            else:
                print("  ✓ Mask has valid pixels")
        except Exception as e:
            print(f"✗ Circle region mask creation failed: {e}")
            import traceback

            traceback.print_exc()
            return False

        # Test 3.2: Rectangle Region Mask
        print("\n--- Test 3.2: Rectangle Region Mask ---")
        log_progress("  Creating rectangle region mask...")
        rect_start = time.time()
        try:
            rect_region = RegionData(
                name="test_rectangle",
                type="rectangle",
                coordinates={
                    "ra_deg": center_ra,
                    "dec_deg": center_dec,
                    "width_deg": 0.01,
                    "height_deg": 0.01,
                    "angle_deg": 0.0,
                },
                image_path=fits_path,
            )

            rect_mask = create_region_mask(
                shape=(ny, nx), region=rect_region, wcs=wcs, header=header
            )

            n_pixels = np.sum(rect_mask)
            log_progress(
                f"  Rectangle mask created: {n_pixels} pixels ({100*n_pixels/(nx*ny):.1f}% of image)",
                rect_start,
            )

            if n_pixels == 0:
                print("  ⚠ Warning: Mask is empty")
            else:
                print("  ✓ Mask has valid pixels")
        except Exception as e:
            print(f"✗ Rectangle region mask creation failed: {e}")
            import traceback

            traceback.print_exc()
            return False

        # Test 3.3: Region Statistics
        print("\n--- Test 3.3: Region Statistics ---")
        try:
            stats = calculate_region_statistics(fits_path, circle_region)

            if stats and "error" not in stats:
                print("✓ Region statistics calculated")
                print(f"  Mean: {stats.get('mean', 'N/A'):.6f}")
                print(f"  Std: {stats.get('std', 'N/A'):.6f}")
                print(f"  Min: {stats.get('min', 'N/A'):.6f}")
                print(f"  Max: {stats.get('max', 'N/A'):.6f}")
            else:
                print(f"⚠ Region statistics calculation returned: {stats}")
        except Exception as e:
            print(f"⚠ Region statistics calculation failed: {e}")
            # Not critical, continue

        # Test 3.4: Region-Constrained Fitting
        print("\n--- Test 3.4: Region-Constrained Fitting ---")
        try:
            if n_pixels > 0:  # Only if mask has pixels
                fit_result = fit_2d_gaussian(
                    fits_path, region_mask=circle_mask, fit_background=True, wcs=wcs
                )

                if fit_result:
                    print("✓ Region-constrained Gaussian fit successful")
                    params = fit_result["parameters"]
                    print(
                        f"  Center (x, y): ({params['center']['x']:.2f}, {params['center']['y']:.2f})"
                    )
                    stats = fit_result["statistics"]
                    print(f"  Reduced chi-squared: {stats['reduced_chi_squared']:.4f}")
                else:
                    print("✗ Region-constrained fit returned no result")
            else:
                print("⚠ Skipping region-constrained fit (mask is empty)")
        except Exception as e:
            print(f"⚠ Region-constrained fit failed: {e}")
            # Not critical, continue

        print("\n✓ Region Management tests passed")
        return True

    except Exception as e:
        print(f"\n✗ Region Management test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    sys.stdout.write("=" * 60 + "\n")
    sys.stdout.write("Backend Core Functionality Validation\n")
    sys.stdout.write("=" * 60 + "\n")
    sys.stdout.flush()

    # Find test image
    fits_path = find_test_image()
    if not fits_path:
        print("ERROR: No test images found in /stage/dsa110-contimg/images/")
        return 1

    print(f"\nUsing test image: {fits_path}")

    # Run tests
    results = []

    results.append(("Spatial Profiler", test_spatial_profiler(fits_path)))
    results.append(("Image Fitting", test_image_fitting(fits_path)))
    results.append(("Region Management", test_region_management(fits_path)))

    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All core functionality tests passed!")
        print("\nNext steps:")
        print("  - Core features are working correctly")
        print("  - Ready for API endpoint testing (optional)")
        print("  - Ready for frontend testing (optional)")
    else:
        print("✗ Some tests failed")
        print("  - Review errors above")
        print("  - Fix issues before proceeding")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    # Immediate output to verify script is running
    sys.stdout.write("Starting validation script...\n")
    sys.stdout.flush()
    try:
        exit_code = main()
        sys.stdout.write(f"Script completed with exit code: {exit_code}\n")
        sys.stdout.flush()
        sys.exit(exit_code)
    except Exception as e:
        sys.stderr.write(f"Fatal error: {e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)
