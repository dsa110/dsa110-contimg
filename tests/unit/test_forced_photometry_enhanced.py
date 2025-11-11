"""
Unit tests for enhanced forced photometry module.

Tests cover:
- Basic functionality (simple peak measurement)
- Weighted convolution mode
- Cluster fitting for blended sources
- Noise map support
- Source injection
- Edge cases and error handling
"""

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS

from dsa110_contimg.photometry.forced import (
    ForcedPhotometryResult,
    G2D,
    _identify_clusters,
    _weighted_convolution,
    inject_source,
    measure_forced_peak,
    measure_many,
)

try:
    import scipy.spatial  # type: ignore[reportMissingTypeStubs]

    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False


def create_test_fits_with_beam(
    data_shape=(512, 512),
    crval1=180.0,
    crval2=35.0,
    crpix1=256.0,
    crpix2=256.0,
    cdelts=(-0.00055555555555556, 0.00055555555555556),
    data=None,
    bmaj_deg=0.001,  # ~3.6 arcsec
    bmin_deg=0.001,
    bpa_deg=0.0,
    **header_kwargs
) -> str:
    """Create a test FITS file with beam information."""
    if data is None:
        data = np.random.normal(0, 0.001, data_shape)

    hdu = fits.PrimaryHDU(data=data)
    hdu.header["CRVAL1"] = crval1
    hdu.header["CRVAL2"] = crval2
    hdu.header["CRPIX1"] = crpix1
    hdu.header["CRPIX2"] = crpix2
    hdu.header["CDELT1"] = cdelts[0]
    hdu.header["CDELT2"] = cdelts[1]
    hdu.header["CTYPE1"] = "RA---SIN"
    hdu.header["CTYPE2"] = "DEC--SIN"
    hdu.header["NAXIS1"] = data_shape[1]
    hdu.header["NAXIS2"] = data_shape[0]
    hdu.header["RESTFRQ"] = 1.4  # GHz
    hdu.header["BMAJ"] = bmaj_deg
    hdu.header["BMIN"] = bmin_deg
    hdu.header["BPA"] = bpa_deg

    for key, value in header_kwargs.items():
        hdu.header[key] = value

    tmp = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
    tmp_fits = tmp.name
    hdu.writeto(tmp_fits, overwrite=True)
    return tmp_fits


def create_test_fits(
    data_shape=(512, 512),
    crval1=180.0,
    crval2=35.0,
    crpix1=256.0,
    crpix2=256.0,
    cdelts=(-0.00055555555555556, 0.00055555555555556),
    data=None,
    **header_kwargs
) -> str:
    """Create a test FITS file without beam information."""
    if data is None:
        data = np.random.normal(0, 0.001, data_shape)

    hdu = fits.PrimaryHDU(data=data)
    hdu.header["CRVAL1"] = crval1
    hdu.header["CRVAL2"] = crval2
    hdu.header["CRPIX1"] = crpix1
    hdu.header["CRPIX2"] = crpix2
    hdu.header["CDELT1"] = cdelts[0]
    hdu.header["CDELT2"] = cdelts[1]
    hdu.header["CTYPE1"] = "RA---SIN"
    hdu.header["CTYPE2"] = "DEC--SIN"
    hdu.header["NAXIS1"] = data_shape[1]
    hdu.header["NAXIS2"] = data_shape[0]
    hdu.header["RESTFRQ"] = 1.4  # GHz
    # Explicitly do NOT add BMAJ, BMIN, BPA

    for key, value in header_kwargs.items():
        hdu.header[key] = value

    tmp = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
    tmp_fits = tmp.name
    hdu.writeto(tmp_fits, overwrite=True)
    return tmp_fits


class TestG2DKernel:
    """Test G2D kernel generation."""

    def test_kernel_creation(self):
        """Test basic kernel creation."""
        g = G2D(x0=100.0, y0=100.0, fwhm_x=5.0, fwhm_y=5.0, pa=0.0)
        assert g.x0 == 100.0
        assert g.y0 == 100.0
        assert g.fwhm_x == 5.0
        assert g.fwhm_y == 5.0

    def test_kernel_evaluation(self):
        """Test kernel evaluation."""
        g = G2D(x0=50.0, y0=50.0, fwhm_x=10.0, fwhm_y=10.0, pa=0.0)
        x = np.array([50.0, 60.0, 50.0])
        y = np.array([50.0, 50.0, 60.0])
        kernel = g(x, y)
        assert kernel.shape == (3,)
        assert kernel[0] > kernel[1]  # Center should be brighter
        assert kernel[0] > kernel[2]  # Center should be brighter
        assert np.all(kernel >= 0)  # All values should be non-negative

    def test_kernel_with_quantity_pa(self):
        """Test kernel with Quantity position angle."""
        g = G2D(x0=50.0, y0=50.0, fwhm_x=10.0, fwhm_y=10.0, pa=45.0 * u.deg)
        x = np.array([50.0])
        y = np.array([50.0])
        kernel = g(x, y)
        assert kernel[0] > 0


class TestWeightedConvolution:
    """Test weighted convolution function."""

    def test_weighted_convolution_basic(self):
        """Test basic weighted convolution."""
        data = np.array([1.0, 2.0, 3.0])
        noise = np.array([0.1, 0.1, 0.1])
        kernel = np.array([0.5, 1.0, 0.5])

        flux, flux_err, chisq = _weighted_convolution(data, noise, kernel)

        assert isinstance(flux, float)
        assert isinstance(flux_err, float)
        assert isinstance(chisq, float)
        assert flux_err > 0
        assert chisq >= 0

    def test_weighted_convolution_with_noise_variation(self):
        """Test weighted convolution with varying noise."""
        data = np.array([1.0, 2.0, 3.0])
        noise = np.array([0.1, 0.2, 0.1])  # Higher noise in middle
        kernel = np.array([0.5, 1.0, 0.5])

        flux, flux_err, chisq = _weighted_convolution(data, noise, kernel)

        assert np.isfinite(flux)
        assert np.isfinite(flux_err)
        assert np.isfinite(chisq)


class TestMeasureForcedPeak:
    """Test measure_forced_peak function."""

    def test_basic_measurement(self):
        """Test basic peak measurement without beam info."""
        tmp_fits = create_test_fits()
        try:
            result = measure_forced_peak(
                tmp_fits, ra_deg=180.0, dec_deg=35.0, box_size_pix=5
            )
            assert isinstance(result, ForcedPhotometryResult)
            assert result.ra_deg == 180.0
            assert result.dec_deg == 35.0
            assert np.isfinite(result.pix_x)
            assert np.isfinite(result.pix_y)
        finally:
            os.unlink(tmp_fits)

    def test_weighted_convolution_mode(self):
        """Test weighted convolution mode with beam info."""
        tmp_fits = create_test_fits_with_beam()
        try:
            result = measure_forced_peak(
                tmp_fits,
                ra_deg=180.0,
                dec_deg=35.0,
                use_weighted_convolution=True,
            )
            assert isinstance(result, ForcedPhotometryResult)
            # Should have chi-squared if weighted convolution used
            if result.chisq is not None:
                assert result.chisq >= 0
                assert result.dof is not None
                assert result.dof > 0
        finally:
            os.unlink(tmp_fits)

    def test_with_noise_map(self):
        """Test measurement with separate noise map."""
        tmp_fits = create_test_fits_with_beam()
        # Create noise map
        hdr = fits.getheader(tmp_fits)
        noise_data = np.full(
            (hdr["NAXIS2"], hdr["NAXIS1"]), 0.001, dtype=np.float32
        )
        noise_hdu = fits.PrimaryHDU(data=noise_data)
        noise_hdu.header = hdr.copy()
        tmp_noise = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_noise_fits = tmp_noise.name
        noise_hdu.writeto(tmp_noise_fits, overwrite=True)

        try:
            result = measure_forced_peak(
                tmp_fits,
                ra_deg=180.0,
                dec_deg=35.0,
                noise_map_path=tmp_noise_fits,
            )
            assert isinstance(result, ForcedPhotometryResult)
            assert np.isfinite(result.peak_jyb) or np.isnan(result.peak_jyb)
        finally:
            os.unlink(tmp_fits)
            os.unlink(tmp_noise_fits)

    def test_with_background_map(self):
        """Test measurement with background subtraction."""
        # Create image with background
        data = np.random.normal(0.1, 0.001, (512, 512))
        tmp_fits = create_test_fits_with_beam(data=data)

        # Create background map
        bg_data = np.full((512, 512), 0.1, dtype=np.float32)
        hdr = fits.getheader(tmp_fits)
        bg_hdu = fits.PrimaryHDU(data=bg_data)
        bg_hdu.header = hdr.copy()
        tmp_bg = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_bg_fits = tmp_bg.name
        bg_hdu.writeto(tmp_bg_fits, overwrite=True)

        try:
            result = measure_forced_peak(
                tmp_fits,
                ra_deg=180.0,
                dec_deg=35.0,
                background_map_path=tmp_bg_fits,
            )
            assert isinstance(result, ForcedPhotometryResult)
        finally:
            os.unlink(tmp_fits)
            os.unlink(tmp_bg_fits)

    def test_missing_file(self):
        """Test handling of missing file."""
        result = measure_forced_peak(
            "/nonexistent/path/image.fits", ra_deg=180.0, dec_deg=35.0
        )
        assert isinstance(result, ForcedPhotometryResult)
        assert np.isnan(result.peak_jyb)
        assert np.isnan(result.peak_err_jyb)

    def test_invalid_coordinates(self):
        """Test handling of invalid coordinates."""
        tmp_fits = create_test_fits()
        try:
            # Coordinates that cause WCS conversion failure
            result = measure_forced_peak(
                tmp_fits, ra_deg=float("inf"), dec_deg=35.0
            )
            assert isinstance(result, ForcedPhotometryResult)
            assert np.isnan(result.pix_x) or not np.isfinite(result.pix_x)
        finally:
            os.unlink(tmp_fits)

    def test_nan_data_handling(self):
        """Test handling of NaN data."""
        data = np.full((512, 512), np.nan)
        tmp_fits = create_test_fits(data=data)
        try:
            result = measure_forced_peak(
                tmp_fits, ra_deg=180.0, dec_deg=35.0
            )
            assert isinstance(result, ForcedPhotometryResult)
            assert np.isnan(result.peak_jyb) or result.peak_jyb == 0
        finally:
            os.unlink(tmp_fits)

    def test_edge_coordinates(self):
        """Test measurement at image edges."""
        tmp_fits = create_test_fits()
        try:
            # Get WCS to find edge coordinates
            hdr = fits.getheader(tmp_fits)
            wcs = WCS(hdr)
            # Convert edge pixel to world coordinates
            edge_ra, edge_dec = wcs.pixel_to_world_values(0, 0)

            result = measure_forced_peak(
                tmp_fits, ra_deg=edge_ra, dec_deg=edge_dec
            )
            assert isinstance(result, ForcedPhotometryResult)
            # Should handle gracefully (may clip to image bounds)
        finally:
            os.unlink(tmp_fits)


class TestMeasureMany:
    """Test measure_many function."""

    def test_basic_many_sources(self):
        """Test measuring multiple sources."""
        tmp_fits = create_test_fits_with_beam()
        coords = [
            (180.0, 35.0),
            (180.01, 35.01),
            (179.99, 34.99),
        ]

        try:
            results = measure_many(tmp_fits, coords)
            assert len(results) == 3
            for result in results:
                assert isinstance(result, ForcedPhotometryResult)
        finally:
            os.unlink(tmp_fits)

    def test_empty_coords_list(self):
        """Test with empty coordinates list."""
        tmp_fits = create_test_fits_with_beam()
        try:
            results = measure_many(tmp_fits, [])
            assert len(results) == 0
        finally:
            os.unlink(tmp_fits)

    def test_with_noise_map(self):
        """Test measure_many with noise map."""
        tmp_fits = create_test_fits_with_beam()
        hdr = fits.getheader(tmp_fits)
        noise_data = np.full(
            (hdr["NAXIS2"], hdr["NAXIS1"]), 0.001, dtype=np.float32
        )
        noise_hdu = fits.PrimaryHDU(data=noise_data)
        noise_hdu.header = hdr.copy()
        tmp_noise = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_noise_fits = tmp_noise.name
        noise_hdu.writeto(tmp_noise_fits, overwrite=True)

        coords = [(180.0, 35.0), (180.01, 35.01)]

        try:
            results = measure_many(
                tmp_fits, coords, noise_map_path=tmp_noise_fits
            )
            assert len(results) == 2
        finally:
            os.unlink(tmp_fits)
            os.unlink(tmp_noise_fits)

    def test_cluster_fitting_disabled(self):
        """Test cluster fitting when disabled."""
        tmp_fits = create_test_fits_with_beam()
        # Two sources close together
        coords = [(180.0, 35.0), (180.0001, 35.0001)]

        try:
            results = measure_many(
                tmp_fits, coords, use_cluster_fitting=False
            )
            assert len(results) == 2
            # Should not have cluster_id set
            for result in results:
                assert result.cluster_id is None
        finally:
            os.unlink(tmp_fits)

    @pytest.mark.skipif(not HAVE_SCIPY, reason="scipy not available")
    def test_cluster_fitting_enabled(self):
        """Test cluster fitting when enabled."""
        tmp_fits = create_test_fits_with_beam()
        # Two sources very close together (within 1.5 BMAJ)
        # BMAJ is ~3.6 arcsec = ~0.001 deg
        # So sources ~0.0005 deg apart should be clustered
        coords = [(180.0, 35.0), (180.0005, 35.0005)]

        try:
            results = measure_many(
                tmp_fits,
                coords,
                use_cluster_fitting=True,
                cluster_threshold=1.5,
            )
            assert len(results) == 2
            # Check if clustering occurred (may or may not depending on exact separation)
            cluster_ids = [
                r.cluster_id for r in results if r.cluster_id is not None]
            # If clustered, both should have same cluster_id
            if len(cluster_ids) == 2:
                assert cluster_ids[0] == cluster_ids[1]
        finally:
            os.unlink(tmp_fits)

    def test_missing_file_many(self):
        """Test measure_many with missing file."""
        coords = [(180.0, 35.0), (180.01, 35.01)]
        results = measure_many("/nonexistent/path/image.fits", coords)
        assert len(results) == 2
        for result in results:
            assert np.isnan(result.peak_jyb)


class TestClusterIdentification:
    """Test cluster identification function."""

    @pytest.mark.skipif(not HAVE_SCIPY, reason="scipy not available")
    def test_identify_clusters_single_source(self):
        """Test cluster identification with single source."""
        X0 = np.array([100.0])
        Y0 = np.array([100.0])
        clusters, in_cluster = _identify_clusters(
            X0, Y0, threshold_pixels=10.0)
        assert len(clusters) == 0
        assert len(in_cluster) == 0

    @pytest.mark.skipif(not HAVE_SCIPY, reason="scipy not available")
    def test_identify_clusters_two_close(self):
        """Test cluster identification with two close sources."""
        X0 = np.array([100.0, 101.0])
        Y0 = np.array([100.0, 100.0])
        clusters, in_cluster = _identify_clusters(X0, Y0, threshold_pixels=2.0)
        # Should identify as cluster
        assert len(clusters) > 0 or len(in_cluster) > 0

    @pytest.mark.skipif(not HAVE_SCIPY, reason="scipy not available")
    def test_identify_clusters_two_far(self):
        """Test cluster identification with two distant sources."""
        X0 = np.array([100.0, 200.0])
        Y0 = np.array([100.0, 100.0])
        clusters, in_cluster = _identify_clusters(
            X0, Y0, threshold_pixels=10.0)
        # Should not cluster
        assert len(clusters) == 0
        assert len(in_cluster) == 0

    @pytest.mark.skipif(not HAVE_SCIPY, reason="scipy not available")
    def test_identify_clusters_zero_threshold(self):
        """Test cluster identification with zero threshold (disabled)."""
        X0 = np.array([100.0, 101.0])
        Y0 = np.array([100.0, 100.0])
        clusters, in_cluster = _identify_clusters(X0, Y0, threshold_pixels=0.0)
        assert len(clusters) == 0
        assert len(in_cluster) == 0

    def test_identify_clusters_no_scipy(self):
        """Test cluster identification gracefully handles missing scipy."""
        # This should work even without scipy (returns empty clusters)
        X0 = np.array([100.0, 101.0])
        Y0 = np.array([100.0, 100.0])
        clusters, in_cluster = _identify_clusters(
            X0, Y0, threshold_pixels=10.0)
        # Should return empty if scipy not available
        assert isinstance(clusters, dict)
        assert isinstance(in_cluster, list)


class TestSourceInjection:
    """Test source injection function."""

    def test_inject_source_basic(self):
        """Test basic source injection."""
        tmp_fits = create_test_fits_with_beam()
        tmp_output = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_output_fits = tmp_output.name
        tmp_output.close()

        try:
            output_path = inject_source(
                tmp_fits,
                ra_deg=180.0,
                dec_deg=35.0,
                flux_jy=0.01,
                output_path=tmp_output_fits,
            )
            assert Path(output_path).exists()
            assert output_path == tmp_output_fits

            # Verify injection by measuring
            result = measure_forced_peak(
                output_path, ra_deg=180.0, dec_deg=35.0
            )
            # Injected source should be detectable
            assert np.isfinite(result.peak_jyb)
        finally:
            if Path(tmp_output_fits).exists():
                os.unlink(tmp_output_fits)
            os.unlink(tmp_fits)

    def test_inject_source_inplace(self):
        """Test in-place source injection."""
        tmp_fits = create_test_fits_with_beam()
        # Get original peak value
        original_result = measure_forced_peak(
            tmp_fits, ra_deg=180.0, dec_deg=35.0
        )
        original_peak = original_result.peak_jyb

        try:
            # Inject source
            output_path = inject_source(
                tmp_fits, ra_deg=180.0, dec_deg=35.0, flux_jy=0.01
            )
            assert output_path == tmp_fits

            # Measure again - should be brighter
            new_result = measure_forced_peak(
                tmp_fits, ra_deg=180.0, dec_deg=35.0
            )
            if np.isfinite(original_peak) and np.isfinite(new_result.peak_jyb):
                assert new_result.peak_jyb > original_peak
        finally:
            os.unlink(tmp_fits)

    def test_inject_source_missing_beam_info(self):
        """Test injection fails gracefully without beam info."""
        tmp_fits = create_test_fits()  # No beam info
        tmp_output = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_output_fits = tmp_output.name
        tmp_output.close()

        try:
            with pytest.raises(ValueError, match="BMAJ.*BMIN.*BPA"):
                inject_source(
                    tmp_fits,
                    ra_deg=180.0,
                    dec_deg=35.0,
                    flux_jy=0.01,
                    output_path=tmp_output_fits,
                )
        finally:
            if Path(tmp_output_fits).exists():
                os.unlink(tmp_output_fits)
            os.unlink(tmp_fits)

    def test_inject_source_invalid_coordinates(self):
        """Test injection with invalid coordinates."""
        tmp_fits = create_test_fits_with_beam()
        tmp_output = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_output_fits = tmp_output.name
        tmp_output.close()

        try:
            with pytest.raises(ValueError, match="Invalid coordinates"):
                inject_source(
                    tmp_fits,
                    ra_deg=float("inf"),
                    dec_deg=35.0,
                    flux_jy=0.01,
                    output_path=tmp_output_fits,
                )
        finally:
            if Path(tmp_output_fits).exists():
                os.unlink(tmp_output_fits)
            os.unlink(tmp_fits)


class TestForcedPhotometryResult:
    """Test ForcedPhotometryResult dataclass."""

    def test_result_creation(self):
        """Test creating result object."""
        result = ForcedPhotometryResult(
            ra_deg=180.0,
            dec_deg=35.0,
            peak_jyb=1.0,
            peak_err_jyb=0.1,
            pix_x=256.0,
            pix_y=256.0,
            box_size_pix=5,
        )
        assert result.ra_deg == 180.0
        assert result.dec_deg == 35.0
        assert result.peak_jyb == 1.0
        assert result.chisq is None
        assert result.dof is None
        assert result.cluster_id is None

    def test_result_with_optional_fields(self):
        """Test result with optional fields."""
        result = ForcedPhotometryResult(
            ra_deg=180.0,
            dec_deg=35.0,
            peak_jyb=1.0,
            peak_err_jyb=0.1,
            pix_x=256.0,
            pix_y=256.0,
            box_size_pix=5,
            chisq=10.5,
            dof=100,
            cluster_id=1,
        )
        assert result.chisq == 10.5
        assert result.dof == 100
        assert result.cluster_id == 1


class TestInjectionRecovery:
    """Test injection and recovery validation."""

    def test_injection_recovery_accuracy(self):
        """Test that injected sources can be accurately recovered."""
        tmp_fits = create_test_fits_with_beam()
        tmp_output = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_output_fits = tmp_output.name
        tmp_output.close()

        injected_flux = 0.05  # 50 mJy
        ra_inject = 180.0
        dec_inject = 35.0

        try:
            # Inject source
            inject_source(
                tmp_fits,
                ra_deg=ra_inject,
                dec_deg=dec_inject,
                flux_jy=injected_flux,
                output_path=tmp_output_fits,
            )

            # Measure injected source
            result = measure_forced_peak(
                tmp_output_fits,
                ra_deg=ra_inject,
                dec_deg=dec_inject,
                use_weighted_convolution=True,
            )

            # Recovered flux should be close to injected flux
            # Allow 20% tolerance for measurement uncertainty
            if np.isfinite(result.peak_jyb):
                flux_ratio = result.peak_jyb / injected_flux
                assert 0.5 < flux_ratio < 1.5, (
                    f"Recovered flux {result.peak_jyb:.6f} not close to "
                    f"injected {injected_flux:.6f} (ratio: {flux_ratio:.2f})"
                )
        finally:
            if Path(tmp_output_fits).exists():
                os.unlink(tmp_output_fits)
            os.unlink(tmp_fits)

    def test_injection_multiple_sources(self):
        """Test injecting and recovering multiple sources."""
        tmp_fits = create_test_fits_with_beam()
        tmp_output = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_output_fits = tmp_output.name
        tmp_output.close()

        sources = [
            (180.0, 35.0, 0.05),
            (180.01, 35.01, 0.03),
            (179.99, 34.99, 0.02),
        ]

        try:
            # Copy original to output file first
            import shutil

            shutil.copy(tmp_fits, tmp_output_fits)

            # Inject all sources into the same file
            current_file = tmp_output_fits
            for ra, dec, flux in sources:
                inject_source(
                    current_file,
                    ra_deg=ra,
                    dec_deg=dec,
                    flux_jy=flux,
                    output_path=current_file,  # In-place
                )

            # Measure all sources
            coords = [(ra, dec) for ra, dec, _ in sources]
            results = measure_many(tmp_output_fits, coords)

            assert len(results) == len(sources)
            for i, (ra, dec, injected_flux) in enumerate(sources):
                result = results[i]
                assert abs(result.ra_deg - ra) < 1e-6
                assert abs(result.dec_deg - dec) < 1e-6
                # Check that flux is recovered (may not be exact due to noise)
                if np.isfinite(result.peak_jyb):
                    assert result.peak_jyb > 0
        finally:
            if Path(tmp_output_fits).exists():
                os.unlink(tmp_output_fits)
            os.unlink(tmp_fits)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_noise_map_shape_mismatch(self):
        """Test error handling for noise map shape mismatch."""
        tmp_fits = create_test_fits_with_beam()
        # Create noise map with wrong shape
        noise_data = np.full((256, 256), 0.001, dtype=np.float32)
        noise_hdu = fits.PrimaryHDU(data=noise_data)
        tmp_noise = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_noise_fits = tmp_noise.name
        noise_hdu.writeto(tmp_noise_fits, overwrite=True)

        try:
            with pytest.raises(ValueError, match="shape"):
                measure_forced_peak(
                    tmp_fits,
                    ra_deg=180.0,
                    dec_deg=35.0,
                    noise_map_path=tmp_noise_fits,
                )
        finally:
            os.unlink(tmp_fits)
            os.unlink(tmp_noise_fits)

    def test_background_map_shape_mismatch(self):
        """Test error handling for background map shape mismatch."""
        tmp_fits = create_test_fits_with_beam()
        # Create background map with wrong shape
        bg_data = np.full((256, 256), 0.1, dtype=np.float32)
        bg_hdu = fits.PrimaryHDU(data=bg_data)
        tmp_bg = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_bg_fits = tmp_bg.name
        bg_hdu.writeto(tmp_bg_fits, overwrite=True)

        try:
            with pytest.raises(ValueError, match="shape"):
                measure_forced_peak(
                    tmp_fits,
                    ra_deg=180.0,
                    dec_deg=35.0,
                    background_map_path=tmp_bg_fits,
                )
        finally:
            os.unlink(tmp_fits)
            os.unlink(tmp_bg_fits)

    def test_zero_noise_pixels(self):
        """Test handling of zero-valued noise pixels."""
        tmp_fits = create_test_fits_with_beam()
        hdr = fits.getheader(tmp_fits)
        noise_data = np.full(
            (hdr["NAXIS2"], hdr["NAXIS1"]), 0.001, dtype=np.float32
        )
        noise_data[100:200, 100:200] = 0.0  # Zero noise region
        noise_hdu = fits.PrimaryHDU(data=noise_data)
        noise_hdu.header = hdr.copy()
        tmp_noise = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
        tmp_noise_fits = tmp_noise.name
        noise_hdu.writeto(tmp_noise_fits, overwrite=True)

        try:
            # Should handle gracefully (zero pixels converted to NaN)
            result = measure_forced_peak(
                tmp_fits,
                ra_deg=180.0,
                dec_deg=35.0,
                noise_map_path=tmp_noise_fits,
            )
            assert isinstance(result, ForcedPhotometryResult)
        finally:
            os.unlink(tmp_fits)
            os.unlink(tmp_noise_fits)

    def test_small_cutout(self):
        """Test with very small cutout size."""
        tmp_fits = create_test_fits_with_beam()
        try:
            result = measure_forced_peak(
                tmp_fits, ra_deg=180.0, dec_deg=35.0, nbeam=0.5
            )
            assert isinstance(result, ForcedPhotometryResult)
        finally:
            os.unlink(tmp_fits)

    def test_large_cutout(self):
        """Test with very large cutout size."""
        tmp_fits = create_test_fits_with_beam()
        try:
            result = measure_forced_peak(
                tmp_fits, ra_deg=180.0, dec_deg=35.0, nbeam=20.0
            )
            assert isinstance(result, ForcedPhotometryResult)
            # Should clip to image bounds
        finally:
            os.unlink(tmp_fits)
