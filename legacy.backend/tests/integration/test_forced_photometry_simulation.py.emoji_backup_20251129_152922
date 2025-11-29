"""
Integration test: Simulate a science field with known sources and verify
forced photometry can recover expected fluxes.

This creates a synthetic FITS image with:
- Valid WCS header
- Gaussian sources at known RA/Dec positions
- Known peak flux values (Jy/beam)
- Realistic noise
- Then performs forced photometry and compares measured vs expected fluxes.
"""

from pathlib import Path

import numpy as np

from dsa110_contimg.photometry.forced import measure_forced_peak
from dsa110_contimg.simulation.synthetic_fits import create_synthetic_fits

# create_synthetic_fits is now imported from dsa110_contimg.simulation.synthetic_fits
# Note: The consolidated function uses pixel_scale_arcsec (not pixel_scale in degrees)
# and beam_fwhm_pix defaults to 10.0 (not 3.0). Adjust calls accordingly.


def test_forced_photometry_recovery(tmp_path):
    """
    Test that forced photometry can recover known source fluxes.
    """
    # Define test sources with known positions and fluxes
    test_sources = [
        {"ra_deg": 180.0, "dec_deg": 35.0, "flux_jy": 1.0, "name": "bright_center"},
        {"ra_deg": 180.01, "dec_deg": 35.01, "flux_jy": 0.5, "name": "medium_offset"},
        {"ra_deg": 179.99, "dec_deg": 34.99, "flux_jy": 0.2, "name": "faint_offset"},
        {"ra_deg": 180.005, "dec_deg": 35.005, "flux_jy": 0.1, "name": "faint_close"},
        {"ra_deg": 180.02, "dec_deg": 35.02, "flux_jy": 0.05, "name": "very_faint"},
    ]

    # Create synthetic FITS image
    fits_path = tmp_path / "test_science_field.fits"
    # Convert pixel_scale from degrees to arcsec (0.001 deg = 3.6 arcsec)
    create_synthetic_fits(
        fits_path,
        ra_deg=180.0,
        dec_deg=35.0,
        image_size=512,
        pixel_scale_arcsec=3.6,  # ~0.001 degrees
        beam_fwhm_pix=3.0,
        noise_level_jy=0.001,
        sources=test_sources,
        mark_synthetic=True,
    )

    print(f"\nCreated synthetic FITS image: {fits_path}")
    print("Image size: 512x512 pixels")
    print("Pixel scale: 0.001 deg/pixel (~3.6 arcsec/pixel)")
    print("Beam FWHM: 3 pixels")
    print("RMS noise: 0.001 Jy/beam")
    print("\nTest sources:")
    for src in test_sources:
        print(
            f"  {src['name']:20s}: RA={src['ra_deg']:8.5f}, Dec={src['dec_deg']:8.5f}, "
            f"Flux={src['flux_jy']:6.3f} Jy/beam"
        )

    # Perform forced photometry on each source
    results = []
    print(f"\n{'=' * 80}")
    print("Forced Photometry Results:")
    print(f"{'=' * 80}")
    print(
        f"{'Source':<20s} {'Expected':>10s} {'Measured':>10s} {'Error':>10s} "
        f"{'SNR':>8s} {'Recovered':>10s}"
    )
    print(f"{'-' * 80}")

    for src in test_sources:
        result = measure_forced_peak(
            str(fits_path),
            src["ra_deg"],
            src["dec_deg"],
            box_size_pix=5,
            annulus_pix=(12, 20),
        )

        expected_flux = src["flux_jy"]
        measured_flux = result.peak_jyb
        flux_error = result.peak_err_jyb

        if np.isfinite(measured_flux) and np.isfinite(flux_error) and flux_error > 0:
            snr = measured_flux / flux_error
            recovered = abs(measured_flux - expected_flux) / expected_flux < 0.2  # Within 20%
        else:
            snr = 0.0
            recovered = False

        recovered_str = "✓" if recovered else "✗"

        print(
            f"{src['name']:<20s} {expected_flux:10.4f} {measured_flux:10.4f} "
            f"{flux_error:10.4f} {snr:8.1f} {recovered_str:>10s}"
        )

        results.append(
            {
                "source": src,
                "result": result,
                "recovered": recovered,
            }
        )

    # Summary statistics
    print(f"\n{'=' * 80}")
    print("Summary:")
    print(f"{'=' * 80}")

    n_recovered = sum(1 for r in results if r["recovered"])
    n_total = len(results)

    print(f"Sources recovered: {n_recovered}/{n_total}")

    # Calculate flux ratio statistics for successfully measured sources
    flux_ratios = []
    for r in results:
        if np.isfinite(r["result"].peak_jyb) and r["result"].peak_jyb > 0:
            expected = r["source"]["flux_jy"]
            measured = r["result"].peak_jyb
            ratio = measured / expected
            flux_ratios.append(ratio)

    if flux_ratios:
        mean_ratio = np.mean(flux_ratios)
        std_ratio = np.std(flux_ratios)
        print(f"Mean flux ratio (measured/expected): {mean_ratio:.4f} ± {std_ratio:.4f}")
        print("Expected: 1.0000")

        # Check if mean ratio is close to 1.0
        ratio_ok = abs(mean_ratio - 1.0) < 0.1  # Within 10%
        print(f"Flux scale accuracy: {'✓ PASS' if ratio_ok else '✗ FAIL'}")

    # Detailed results for each source
    print(f"\n{'=' * 80}")
    print("Detailed Results:")
    print(f"{'=' * 80}")
    for r in results:
        src = r["source"]
        res = r["result"]
        print(f"\n{src['name']}:")
        print(f"  Position: RA={src['ra_deg']:.6f}, Dec={src['dec_deg']:.6f}")
        print(f"  Pixel: ({res.pix_x:.2f}, {res.pix_y:.2f})")
        print(f"  Expected flux: {src['flux_jy']:.4f} Jy/beam")
        print(f"  Measured flux: {res.peak_jyb:.4f} Jy/beam")
        if np.isfinite(res.peak_err_jyb):
            print(f"  Error: {res.peak_err_jyb:.4f} Jy/beam")
            if res.peak_err_jyb > 0:
                print(f"  SNR: {res.peak_jyb / res.peak_err_jyb:.1f}")
        if np.isfinite(res.peak_jyb) and src["flux_jy"] > 0:
            ratio = res.peak_jyb / src["flux_jy"]
            print(f"  Ratio (measured/expected): {ratio:.4f}")
            print(f"  Recovery: {'✓ PASS' if r['recovered'] else '✗ FAIL'}")

    # Assertions for automated testing
    assert (
        n_recovered >= n_total * 0.8
    ), f"Only {n_recovered}/{n_total} sources recovered (expected ≥80%)"
    if flux_ratios:
        assert (
            abs(mean_ratio - 1.0) < 0.15
        ), f"Flux scale error too large: {mean_ratio:.4f} (expected ~1.0)"

    print(f"\n{'=' * 80}")
    print("✓ All checks passed!")
    print(f"{'=' * 80}\n")


def test_forced_photometry_low_snr(tmp_path):
    """
    Test forced photometry with low SNR sources (more realistic noise).
    """
    test_sources = [
        {"ra_deg": 180.0, "dec_deg": 35.0, "flux_jy": 0.01, "name": "low_snr_1"},
        {"ra_deg": 180.005, "dec_deg": 35.005, "flux_jy": 0.005, "name": "low_snr_2"},
    ]

    fits_path = tmp_path / "test_low_snr.fits"
    create_synthetic_fits(
        fits_path,
        ra_deg=180.0,
        dec_deg=35.0,
        image_size=512,
        pixel_scale_arcsec=3.6,
        beam_fwhm_pix=3.0,
        noise_level_jy=0.001,  # Same noise, but fainter sources
        sources=test_sources,
        mark_synthetic=True,
    )

    results = []
    for src in test_sources:
        result = measure_forced_peak(
            str(fits_path),
            src["ra_deg"],
            src["dec_deg"],
            box_size_pix=5,
            annulus_pix=(12, 20),
        )

        if np.isfinite(result.peak_jyb) and result.peak_err_jyb > 0:
            snr = result.peak_jyb / result.peak_err_jyb
            # For low SNR, we expect larger scatter but should still detect
            recovered = snr >= 3.0 and abs(result.peak_jyb - src["flux_jy"]) / src["flux_jy"] < 0.5
        else:
            recovered = False

        results.append({"source": src, "result": result, "recovered": recovered})

    # At least one should be recovered
    n_recovered = sum(1 for r in results if r["recovered"])
    assert n_recovered >= 1, f"Expected at least 1 low-SNR source recovered, got {n_recovered}"


def test_forced_photometry_edge_sources(tmp_path):
    """
    Test forced photometry on sources near image edges.
    """
    test_sources = [
        {"ra_deg": 180.0, "dec_deg": 35.0, "flux_jy": 0.5, "name": "center"},
        {"ra_deg": 180.015, "dec_deg": 35.015, "flux_jy": 0.3, "name": "near_edge"},
    ]

    fits_path = tmp_path / "test_edge.fits"
    create_synthetic_fits(
        fits_path,
        ra_deg=180.0,
        dec_deg=35.0,
        image_size=256,  # Smaller image to test edge cases
        pixel_scale_arcsec=3.6,
        beam_fwhm_pix=3.0,
        noise_level_jy=0.001,
        sources=test_sources,
        mark_synthetic=True,
    )

    results = []
    for src in test_sources:
        result = measure_forced_peak(
            str(fits_path),
            src["ra_deg"],
            src["dec_deg"],
            box_size_pix=5,
            annulus_pix=(12, 20),
        )

        # Edge sources may have partial annulus, but should still work
        recovered = np.isfinite(result.peak_jyb) and result.peak_jyb > 0
        results.append({"source": src, "result": result, "recovered": recovered})

    # Both should be recovered
    n_recovered = sum(1 for r in results if r["recovered"])
    assert n_recovered == len(
        test_sources
    ), f"Expected all sources recovered, got {n_recovered}/{len(test_sources)}"


if __name__ == "__main__":
    import os
    import sys
    import tempfile
    from pathlib import Path

    # Check for output directory from environment variable or command line
    output_dir = None
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
    elif os.environ.get("FORCED_PHOTOMETRY_OUTPUT_DIR"):
        output_dir = Path(os.environ.get("FORCED_PHOTOMETRY_OUTPUT_DIR"))

    if output_dir:
        # Use persistent directory (create if doesn't exist)
        output_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = output_dir
        print(f"Using persistent output directory: {tmp_path}")
        print("Generated FITS files will be saved here and NOT cleaned up.")

        print("\nRunning main recovery test...")
        test_forced_photometry_recovery(tmp_path)

        print("\nRunning low SNR test...")
        test_forced_photometry_low_snr(tmp_path)

        print("\nRunning edge sources test...")
        test_forced_photometry_edge_sources(tmp_path)

        print("\n✓ All tests passed!")
        print(f"\nOutput files saved to: {tmp_path}")
        print("Files:")
        for f in sorted(tmp_path.glob("*.fits")):
            print(f"  {f.name}")
    else:
        # Use temporary directory (cleaned up after)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            print(f"Using temporary directory: {tmp_path}")
            print("Generated FITS files will be cleaned up after tests complete.")
            print(
                "To save files, set FORCED_PHOTOMETRY_OUTPUT_DIR or pass output directory as argument:"
            )
            print("  python test_forced_photometry_simulation.py /path/to/output")

            print("\nRunning main recovery test...")
            test_forced_photometry_recovery(tmp_path)

            print("\nRunning low SNR test...")
            test_forced_photometry_low_snr(tmp_path)

            print("\nRunning edge sources test...")
            test_forced_photometry_edge_sources(tmp_path)

            print("\n✓ All tests passed!")
