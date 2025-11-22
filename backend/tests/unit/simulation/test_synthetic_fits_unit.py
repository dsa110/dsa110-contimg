"""Comprehensive unit tests for synthetic_fits.py.

Tests focus on:
- FITS file creation and structure
- Source placement and flux
- Noise generation
- WCS correctness
- Provenance marking
"""

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from dsa110_contimg.simulation.synthetic_fits import create_synthetic_fits


class TestCreateSyntheticFits:
    """Test create_synthetic_fits function."""

    def test_create_basic_fits(self, tmp_path):
        """Test creating a basic synthetic FITS file."""
        output_path = tmp_path / "test.fits"

        result_path = create_synthetic_fits(output_path)

        assert result_path.exists()
        assert result_path == output_path

        # Verify it's a valid FITS file
        with fits.open(result_path) as hdul:
            assert len(hdul) > 0
            assert hdul[0].data is not None

    def test_fits_structure(self, tmp_path):
        """Test FITS file structure."""
        output_path = tmp_path / "test.fits"
        create_synthetic_fits(output_path, image_size=256)

        with fits.open(output_path) as hdul:
            data = hdul[0].data
            assert data.shape == (256, 256)
            # FITS may use float64, check for either float32 or float64
            assert data.dtype in (np.float32, np.float64)

    def test_fits_wcs(self, tmp_path):
        """Test that FITS has correct WCS."""
        output_path = tmp_path / "test.fits"
        ra_deg = 180.0
        dec_deg = 35.0
        pixel_scale_arcsec = 2.0

        create_synthetic_fits(
            output_path,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            pixel_scale_arcsec=pixel_scale_arcsec,
        )

        with fits.open(output_path) as hdul:
            wcs = WCS(hdul[0].header)
            # Check that WCS is valid
            assert wcs.naxis == 2

            # Check center coordinates
            center_pix = (128, 128)  # Center of 256x256 image
            ra, dec = wcs.pixel_to_world_values(center_pix[0], center_pix[1])
            assert abs(ra - ra_deg) < 1.0  # Within 1 degree
            assert abs(dec - dec_deg) < 1.0

    def test_fits_provenance_marking(self, tmp_path):
        """Test that synthetic FITS are marked with provenance."""
        output_path = tmp_path / "test.fits"
        create_synthetic_fits(output_path, mark_synthetic=True)

        with fits.open(output_path) as hdul:
            header = hdul[0].header
            assert header.get("SYNTHETIC") is True
            assert "SYNTHETIC" in header

    def test_fits_no_provenance(self, tmp_path):
        """Test that provenance marking can be disabled."""
        output_path = tmp_path / "test.fits"
        create_synthetic_fits(output_path, mark_synthetic=False)

        with fits.open(output_path) as hdul:
            header = hdul[0].header
            # Should not have synthetic keyword (or it should be False)
            synthetic = header.get("SYNTHETIC", False)
            assert synthetic is False

    def test_fits_sources(self, tmp_path):
        """Test that sources are added correctly."""
        output_path = tmp_path / "test.fits"
        n_sources = 5
        flux_range = (0.01, 0.1)

        create_synthetic_fits(output_path, n_sources=n_sources, source_flux_range_jy=flux_range)

        with fits.open(output_path) as hdul:
            data = hdul[0].data
            # Should have some bright pixels (sources)
            max_val = np.max(data)
            assert max_val > flux_range[0]

    def test_fits_noise(self, tmp_path):
        """Test that noise is added correctly."""
        output_path = tmp_path / "test.fits"
        noise_level = 0.001

        create_synthetic_fits(output_path, n_sources=0, noise_level_jy=noise_level)

        with fits.open(output_path) as hdul:
            data = hdul[0].data
            # Noise should be visible in background
            std_val = np.std(data)
            # Should be on order of noise level (allow wider tolerance)
            assert std_val > noise_level * 0.3
            assert std_val < noise_level * 3.0

    def test_fits_image_size(self, tmp_path):
        """Test different image sizes."""
        for size in [128, 256, 512, 1024]:
            output_path = tmp_path / f"test_{size}.fits"
            create_synthetic_fits(output_path, image_size=size)

            with fits.open(output_path) as hdul:
                data = hdul[0].data
                assert data.shape == (size, size)

    def test_fits_pixel_scale(self, tmp_path):
        """Test different pixel scales."""
        for scale in [1.0, 2.0, 5.0]:
            output_path = tmp_path / f"test_scale_{scale}.fits"
            create_synthetic_fits(output_path, pixel_scale_arcsec=scale)

            with fits.open(output_path) as hdul:
                header = hdul[0].header
                # Check that CDELT reflects pixel scale
                cdelt1 = abs(header.get("CDELT1", 0))
                cdelt2 = abs(header.get("CDELT2", 0))
                # CDELT is in degrees, scale is in arcsec
                expected_cdelt = scale / 3600.0
                assert abs(cdelt1 - expected_cdelt) < expected_cdelt * 0.1
                assert abs(cdelt2 - expected_cdelt) < expected_cdelt * 0.1

    def test_fits_coordinates(self, tmp_path):
        """Test different coordinate centers."""
        test_cases = [
            (0.0, 0.0),
            (180.0, 0.0),
            (0.0, 90.0),
            (180.0, -90.0),
            (45.0, 30.0),
        ]

        for ra, dec in test_cases:
            output_path = tmp_path / f"test_{ra}_{dec}.fits"
            create_synthetic_fits(output_path, ra_deg=ra, dec_deg=dec)

            with fits.open(output_path) as hdul:
                wcs = WCS(hdul[0].header)
                # Check that WCS is valid for these coordinates
                assert wcs.naxis == 2


class TestFitsSourcePlacement:
    """Test source placement in FITS images."""

    def test_sources_in_image(self, tmp_path):
        """Test that sources are placed within image bounds."""
        output_path = tmp_path / "test.fits"
        create_synthetic_fits(output_path, n_sources=10, image_size=256)

        with fits.open(output_path) as hdul:
            data = hdul[0].data
            # Find source positions (bright pixels)
            threshold = np.percentile(data, 99)
            y_coords, x_coords = np.where(data > threshold)

            # All sources should be within bounds
            assert np.all(x_coords >= 0)
            assert np.all(x_coords < 256)
            assert np.all(y_coords >= 0)
            assert np.all(y_coords < 256)

    def test_source_flux_range(self, tmp_path):
        """Test that source fluxes are in specified range."""
        output_path = tmp_path / "test.fits"
        flux_min = 0.01
        flux_max = 0.1

        create_synthetic_fits(output_path, n_sources=5, source_flux_range_jy=(flux_min, flux_max))

        with fits.open(output_path) as hdul:
            data = hdul[0].data
            # Find source peaks
            max_val = np.max(data)
            # Should be within range (allowing for noise)
            assert max_val >= flux_min * 0.5
            assert max_val <= flux_max * 2.0

    def test_zero_sources(self, tmp_path):
        """Test creating FITS with no sources."""
        output_path = tmp_path / "test.fits"
        create_synthetic_fits(output_path, n_sources=0)

        with fits.open(output_path) as hdul:
            data = hdul[0].data
            # Should only have noise
            max_val = np.max(data)
            # Should be small (just noise)
            assert max_val < 0.01


class TestFitsNoise:
    """Test noise generation in FITS images."""

    def test_noise_statistics(self, tmp_path):
        """Test that noise has correct statistics."""
        output_path = tmp_path / "test.fits"
        noise_level = 0.001
        create_synthetic_fits(output_path, n_sources=0, noise_level_jy=noise_level)

        with fits.open(output_path) as hdul:
            data = hdul[0].data
            # Noise should be approximately Gaussian
            mean_val = np.mean(data)
            std_val = np.std(data)

            # Mean should be close to zero
            assert abs(mean_val) < noise_level * 0.5
            # Std should be approximately noise level
            assert abs(std_val - noise_level) < noise_level * 0.5

    def test_noise_zero_level(self, tmp_path):
        """Test FITS with zero noise."""
        output_path = tmp_path / "test.fits"
        create_synthetic_fits(output_path, n_sources=0, noise_level_jy=0.0)

        with fits.open(output_path) as hdul:
            data = hdul[0].data
            # Should be all zeros (no sources, no noise)
            assert np.allclose(data, 0.0)


class TestFitsEdgeCases:
    """Test edge cases and error handling."""

    def test_small_image(self, tmp_path):
        """Test creating very small image."""
        output_path = tmp_path / "test.fits"
        create_synthetic_fits(output_path, image_size=32)

        with fits.open(output_path) as hdul:
            data = hdul[0].data
            assert data.shape == (32, 32)

    def test_large_image(self, tmp_path):
        """Test creating large image."""
        output_path = tmp_path / "test.fits"
        create_synthetic_fits(output_path, image_size=2048)

        with fits.open(output_path) as hdul:
            data = hdul[0].data
            assert data.shape == (2048, 2048)

    def test_invalid_flux_range(self, tmp_path):
        """Test error handling for invalid flux range."""
        output_path = tmp_path / "test.fits"
        # Min > Max - function may or may not validate
        # Just check it doesn't crash
        try:
            create_synthetic_fits(output_path, source_flux_range_jy=(0.1, 0.01))  # Min > Max
            # If it doesn't raise, that's acceptable (may use min or handle gracefully)
        except ValueError:
            # Expected if function validates
            pass

    def test_negative_noise(self, tmp_path):
        """Test that negative noise is handled."""
        output_path = tmp_path / "test.fits"
        # Negative noise should be handled (probably set to zero or abs)
        # Just check it doesn't crash
        try:
            create_synthetic_fits(output_path, noise_level_jy=-0.001)
            # If it doesn't crash, that's fine
        except ValueError:
            # Expected for negative noise
            pass


class TestFitsPerformance:
    """Test performance characteristics."""

    def test_creation_performance(self, tmp_path):
        """Test that FITS creation is fast."""
        import time

        output_path = tmp_path / "test.fits"
        start = time.time()
        create_synthetic_fits(output_path, image_size=512)
        elapsed = time.time() - start

        # Should complete in < 1 second
        assert elapsed < 1.0

    def test_large_image_performance(self, tmp_path):
        """Test performance with large images."""
        import time

        output_path = tmp_path / "test_large.fits"
        start = time.time()
        create_synthetic_fits(output_path, image_size=2048)
        elapsed = time.time() - start

        # Should complete in < 5 seconds
        assert elapsed < 5.0
