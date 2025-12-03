"""
Integration tests for mosaicking with real DSA-110 data.

These tests are designed to run when real DSA-110 FITS images are available.
They validate:
- Weight map correctness
- Effective noise matches expected sqrt(N) improvement
- QA checks against radio catalogs (NVSS/FIRST)

Usage:
    # Run when DSA-110 images are available
    pytest tests/integration/test_mosaic_real_data.py -v

    # Skip if no real data (default behavior)
    pytest tests/integration/test_mosaic_real_data.py -v --skip-no-data

Configuration:
    Set DSA110_TEST_IMAGES_DIR environment variable to point to a directory
    containing real DSA-110 FITS images for integration testing.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
from astropy.io import fits

if TYPE_CHECKING:
    from numpy.typing import NDArray


# Path to real DSA-110 test images (set via environment variable)
TEST_IMAGES_DIR = os.environ.get(
    "DSA110_TEST_IMAGES_DIR",
    "/stage/dsa110-contimg/images"  # Default production path
)

# Minimum images needed for meaningful integration tests
MIN_IMAGES_FOR_TEST = 5


def get_real_images(
    max_images: int = 10,
    require_noise: bool = True,
) -> list[Path]:
    """
    Find real DSA-110 FITS images for testing.
    
    Args:
        max_images: Maximum number of images to return
        require_noise: If True, only return images with RMS noise in header
        
    Returns:
        List of Path objects to FITS images
    """
    images_dir = Path(TEST_IMAGES_DIR)
    if not images_dir.exists():
        return []
    
    # Find FITS files (excluding weight maps and thumbnails)
    patterns = ["*.fits", "*.FITS"]
    all_images = []
    for pattern in patterns:
        all_images.extend(images_dir.glob(pattern))
    
    # Filter out weight maps and other non-image files
    valid_images = []
    for img_path in all_images:
        if ".weights" in img_path.name:
            continue
        if ".thumb" in img_path.name:
            continue
        if require_noise:
            # Check for noise estimate in header
            try:
                with fits.open(str(img_path)) as hdul:
                    hdr = hdul[0].header
                    if "RMS" in hdr or "MEDRMS" in hdr or "NOISE" in hdr:
                        valid_images.append(img_path)
            except Exception:
                continue
        else:
            valid_images.append(img_path)
    
    # Sort by modification time (most recent first)
    valid_images.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    return valid_images[:max_images]


def has_real_data() -> bool:
    """Check if real DSA-110 data is available for testing."""
    return len(get_real_images()) >= MIN_IMAGES_FOR_TEST


# Skip marker for tests requiring real data
requires_real_data = pytest.mark.skipif(
    not has_real_data(),
    reason=f"Requires at least {MIN_IMAGES_FOR_TEST} real DSA-110 images in {TEST_IMAGES_DIR}"
)


@requires_real_data
class TestMosaicWithRealData:
    """Integration tests using real DSA-110 images."""
    
    @pytest.fixture
    def real_images(self) -> list[Path]:
        """Get real DSA-110 images for testing."""
        return get_real_images(max_images=10)
    
    def test_weight_map_correctness(
        self,
        real_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Verify weight map is correctly computed from input RMS values.
        
        Weight map should be inverse variance: w_i = 1/sigma_i^2
        Combined weight at each pixel should be sum of input weights.
        """
        from dsa110_contimg.mosaic import build_mosaic
        
        # Build mosaic with weight map
        output = tmp_path / "mosaic_weighttest.fits"
        result = build_mosaic(
            image_paths=real_images[:5],
            output_path=output,
            write_weight_map=True,
        )
        
        # Load weight map
        assert result.weight_map_path is not None
        assert result.weight_map_path.exists()
        
        with fits.open(str(result.weight_map_path)) as hdul:
            weight_map = hdul[0].data
        
        # Weight map should have valid values where coverage exists
        valid_mask = weight_map > 0
        assert np.any(valid_mask), "Weight map has no valid pixels"
        
        # Weight values should be positive and finite
        valid_weights = weight_map[valid_mask]
        assert np.all(np.isfinite(valid_weights)), "Weight map has non-finite values"
        assert np.all(valid_weights > 0), "Weight map has non-positive values"
        
        # Noise from weights should be 1/sqrt(weight)
        with fits.open(str(output)) as hdul:
            mosaic_data = hdul[0].data
        
        # Compute noise from weights and compare to mosaic noise
        noise_from_weights = 1.0 / np.sqrt(weight_map[valid_mask])
        median_noise_from_weights = np.median(noise_from_weights)
        
        # Should be consistent with reported effective noise
        assert result.effective_noise_jy is not None
        np.testing.assert_allclose(
            median_noise_from_weights,
            result.effective_noise_jy,
            rtol=0.1,  # 10% tolerance
            err_msg="Weight map noise inconsistent with reported effective noise"
        )
    
    def test_effective_noise_sqrt_n_improvement(
        self,
        real_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Verify effective noise improves as sqrt(N) with more images.
        
        For N images with uniform noise sigma, the combined noise should be
        approximately sigma/sqrt(N). This test validates the improvement.
        """
        from dsa110_contimg.mosaic import build_mosaic
        
        # Test with different numbers of images
        n_values = [2, 4, len(real_images)] if len(real_images) >= 4 else [2, len(real_images)]
        effective_noises = []
        
        for n in n_values:
            output = tmp_path / f"mosaic_n{n}.fits"
            result = build_mosaic(
                image_paths=real_images[:n],
                output_path=output,
                write_weight_map=False,
            )
            effective_noises.append((n, result.effective_noise_jy, result.median_rms))
        
        # Verify sqrt(N) improvement
        # For uniform noise: effective_noise ≈ median_rms / sqrt(N)
        for n, effective_noise, median_rms in effective_noises:
            if median_rms is None or effective_noise is None:
                continue
            
            expected_noise = median_rms / np.sqrt(n)
            
            # Allow 50% tolerance due to varying image quality and overlap
            # In practice, noise doesn't improve perfectly as sqrt(N)
            ratio = effective_noise / expected_noise
            assert 0.5 < ratio < 2.0, (
                f"Effective noise {effective_noise:.6f} Jy doesn't match "
                f"expected sqrt(N) improvement {expected_noise:.6f} Jy "
                f"(ratio={ratio:.2f}) for N={n}"
            )
    
    def test_qa_checks_against_catalogs(
        self,
        real_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Verify QA checks work against radio catalogs.
        
        Tests:
        - Astrometry check cross-matches against NVSS/FIRST
        - Photometry check measures dynamic range
        - Artifact detection runs without errors
        """
        from dsa110_contimg.mosaic import build_mosaic, run_qa_checks
        
        # Build mosaic
        output = tmp_path / "mosaic_qa_test.fits"
        result = build_mosaic(
            image_paths=real_images[:5],
            output_path=output,
            write_weight_map=True,
        )
        
        # Run QA checks
        qa_result = run_qa_checks(output, tier="science")
        
        # QA should complete without errors
        assert qa_result is not None
        
        # Status should be valid
        assert qa_result.status in ("PASS", "WARN", "FAIL")
        
        # Check individual components were computed
        # (values may be None if catalogs unavailable, but no exceptions)
        if qa_result.astrometry_rms is not None:
            assert qa_result.astrometry_rms >= 0, "Astrometry RMS should be non-negative"
        
        if qa_result.dynamic_range is not None:
            assert qa_result.dynamic_range > 0, "Dynamic range should be positive"
        
        if qa_result.artifact_score is not None:
            assert 0 <= qa_result.artifact_score <= 1, "Artifact score should be in [0, 1]"


@requires_real_data
class TestMosaicCatalogCrossmatch:
    """Tests for catalog cross-matching in QA checks."""
    
    def test_astrometry_with_nvss(
        self,
        tmp_path: Path,
    ) -> None:
        """Test astrometry check using NVSS catalog.
        
        This requires:
        - Real DSA-110 images in the test directory
        - NVSS catalog database (vla_calibrators.sqlite3 or nvss_dec*.sqlite3)
        """
        from dsa110_contimg.mosaic import build_mosaic
        from dsa110_contimg.mosaic.qa import check_astrometry
        
        real_images = get_real_images(max_images=5)
        if len(real_images) < 3:
            pytest.skip("Need at least 3 real images for astrometry test")
        
        # Build mosaic
        output = tmp_path / "mosaic_nvss_test.fits"
        build_mosaic(
            image_paths=real_images,
            output_path=output,
        )
        
        # Run astrometry check
        try:
            astrometry = check_astrometry(output)
            
            # Should have measured something
            assert astrometry is not None
            
            # If we got matches, check the results
            if astrometry.n_matches > 0:
                assert astrometry.rms_arcsec >= 0
                # Typical DSA-110 astrometry should be < 5 arcsec
                # (warning threshold, not hard failure)
                if astrometry.rms_arcsec > 5.0:
                    pytest.warns(
                        UserWarning,
                        match="Astrometry RMS.*exceeds threshold"
                    )
        except ImportError as e:
            pytest.skip(f"Catalog cross-match not available: {e}")
        except FileNotFoundError as e:
            pytest.skip(f"Catalog database not found: {e}")


class TestMosaicSyntheticValidation:
    """Validation tests using synthetic data with known properties."""
    
    @pytest.fixture
    def uniform_noise_images(self, tmp_path: Path) -> list[Path]:
        """Create synthetic images with known uniform noise.
        
        All images have:
        - Same WCS
        - Known Gaussian noise (sigma = 0.001 Jy)
        - A bright point source for reference
        """
        np.random.seed(42)
        
        images = []
        sigma = 0.001  # 1 mJy noise
        
        for i in range(8):
            # Create image with known noise
            data = np.random.normal(0, sigma, (256, 256)).astype(np.float32)
            
            # Add point source at center (for flux reference)
            y, x = 128, 128
            yy, xx = np.ogrid[-5:6, -5:6]
            psf = np.exp(-(xx**2 + yy**2) / (2 * 2**2))
            data[y-5:y+6, x-5:x+6] += 0.1 * psf  # 100 mJy source
            
            # Create WCS
            from astropy.wcs import WCS
            wcs = WCS(naxis=2)
            wcs.wcs.crpix = [128, 128]
            wcs.wcs.crval = [180.0, 40.0]
            wcs.wcs.cdelt = [0.001, 0.001]  # ~3.6 arcsec/pixel
            wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
            
            # Write FITS
            path = tmp_path / f"synth_uniform_{i}.fits"
            hdu = fits.PrimaryHDU(data=data, header=wcs.to_header())
            hdu.header['BUNIT'] = 'Jy/beam'
            hdu.header['RMS'] = sigma
            hdu.writeto(str(path))
            images.append(path)
        
        return images
    
    @staticmethod
    def _check_reproject_available() -> bool:
        """Check if reproject package is available."""
        try:
            from reproject import reproject_interp  # noqa: F401
            return True
        except ImportError:
            return False
    
    @pytest.mark.skipif(
        not _check_reproject_available.__func__(),  # type: ignore[attr-defined]
        reason="reproject package not available - required for weight map tests"
    )
    def test_sqrt_n_improvement_synthetic(
        self,
        uniform_noise_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Verify sqrt(N) improvement with perfectly uniform synthetic data.
        
        With 8 images of sigma=0.001 Jy noise, we expect:
        - N=1: effective_noise ≈ 0.001 Jy
        - N=4: effective_noise ≈ 0.0005 Jy (0.001/2)
        - N=8: effective_noise ≈ 0.00035 Jy (0.001/sqrt(8))
        """
        from dsa110_contimg.mosaic import build_mosaic
        
        sigma = 0.001  # Known input noise
        
        # Test progression
        test_cases = [
            (1, sigma),        # N=1: no improvement
            (4, sigma / 2),    # N=4: factor of 2
            (8, sigma / np.sqrt(8)),  # N=8: factor of sqrt(8)
        ]
        
        for n, expected_noise in test_cases:
            output = tmp_path / f"synth_mosaic_n{n}.fits"
            result = build_mosaic(
                image_paths=uniform_noise_images[:n],
                output_path=output,
                write_weight_map=True,
            )
            
            # Check effective noise matches expectation
            # Allow 20% tolerance for edge effects and interpolation
            assert result.effective_noise_jy is not None
            np.testing.assert_allclose(
                result.effective_noise_jy,
                expected_noise,
                rtol=0.2,
                err_msg=f"Effective noise for N={n} doesn't match sqrt(N) expectation"
            )
    
    @pytest.mark.skipif(
        not _check_reproject_available.__func__(),  # type: ignore[attr-defined]
        reason="reproject package not available - required for weight map tests"
    )
    def test_weight_map_sum(
        self,
        uniform_noise_images: list[Path],
        tmp_path: Path,
    ) -> None:
        """Verify weight map sums correctly for overlapping images.
        
        For N images with weight w_i = 1/sigma^2, the combined weight
        should be N * w_i in fully overlapping regions.
        """
        from dsa110_contimg.mosaic import build_mosaic
        
        sigma = 0.001
        expected_weight_per_image = 1.0 / sigma**2  # = 1e6
        
        # Build mosaic with 4 images
        output = tmp_path / "synth_mosaic_weight_test.fits"
        result = build_mosaic(
            image_paths=uniform_noise_images[:4],
            output_path=output,
            write_weight_map=True,
        )
        
        # Load weight map
        with fits.open(str(result.weight_map_path)) as hdul:
            weight_map = hdul[0].data
        
        # In fully overlapping central region, weight should be ~4 * w_i
        center = weight_map.shape[0] // 2
        # Sample a small central region
        central_weights = weight_map[center-10:center+10, center-10:center+10]
        
        # Should have valid weights
        valid_weights = central_weights[central_weights > 0]
        assert len(valid_weights) > 0, "No valid weights in center"
        
        median_weight = np.median(valid_weights)
        expected_combined_weight = 4 * expected_weight_per_image
        
        # Check combined weight (allow 30% tolerance for edge effects)
        np.testing.assert_allclose(
            median_weight,
            expected_combined_weight,
            rtol=0.3,
            err_msg="Combined weight doesn't match sum of individual weights"
        )
