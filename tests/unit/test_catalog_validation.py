#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for catalog-based validation.

Tests the catalog_validation module functions for:
- Astrometry validation
- Flux scale validation
- Source count validation
- Source extraction
- Catalog overlay pixel conversion
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u

from dsa110_contimg.qa.catalog_validation import (
    CatalogValidationResult,
    validate_astrometry,
    validate_flux_scale,
    validate_source_counts,
    extract_sources_from_image,
    scale_flux_to_frequency,
    get_catalog_overlay_pixels,
    get_image_frequency,
)


class TestScaleFluxToFrequency:
    """Test flux frequency scaling."""

    def test_same_frequency(self):
        """Test scaling when frequencies are the same."""
        flux = scale_flux_to_frequency(1.0, 1.4e9, 1.4e9)
        assert flux == pytest.approx(1.0)

    def test_frequency_scaling(self):
        """Test power-law frequency scaling."""
        # Scale from 1.4 GHz to 3 GHz with α = -0.7
        flux_1_4 = 1.0  # 1 Jy at 1.4 GHz
        flux_3_0 = scale_flux_to_frequency(flux_1_4, 1.4e9, 3.0e9, spectral_index=-0.7)

        # Expected: S_3GHz = S_1.4GHz * (3.0/1.4)^(-0.7)
        expected = 1.0 * (3.0 / 1.4) ** (-0.7)
        assert flux_3_0 == pytest.approx(expected, rel=1e-3)

    def test_different_spectral_index(self):
        """Test scaling with different spectral index."""
        flux_1_4 = 1.0
        flux_3_0_flat = scale_flux_to_frequency(
            flux_1_4, 1.4e9, 3.0e9, spectral_index=0.0
        )
        assert flux_3_0_flat == pytest.approx(1.0)


class TestGetImageFrequency:
    """Test image frequency extraction."""

    def test_restfrq_keyword(self, tmp_path):
        """Test frequency extraction from RESTFRQ keyword."""
        hdu = fits.PrimaryHDU(data=np.zeros((10, 10)))
        hdu.header["RESTFRQ"] = 1.4  # GHz
        hdu.header["NAXIS1"] = 10
        hdu.header["NAXIS2"] = 10

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        freq = get_image_frequency(str(image_path))
        assert freq == pytest.approx(1.4e9)

    def test_freq_keyword(self, tmp_path):
        """Test frequency extraction from FREQ keyword."""
        hdu = fits.PrimaryHDU(data=np.zeros((10, 10)))
        hdu.header["FREQ"] = 3.0  # GHz
        hdu.header["NAXIS1"] = 10
        hdu.header["NAXIS2"] = 10

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        freq = get_image_frequency(str(image_path))
        assert freq == pytest.approx(3.0e9)

    def test_no_frequency_keyword(self, tmp_path):
        """Test when no frequency keyword is present."""
        hdu = fits.PrimaryHDU(data=np.zeros((10, 10)))
        hdu.header["NAXIS1"] = 10
        hdu.header["NAXIS2"] = 10

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        freq = get_image_frequency(str(image_path))
        assert freq is None


class TestExtractSourcesFromImage:
    """Test source extraction from images."""

    def test_no_sources(self, tmp_path):
        """Test extraction when no sources above threshold."""
        # Create image with only noise
        data = np.random.normal(0, 0.1, (100, 100))
        hdu = fits.PrimaryHDU(data=data)
        hdu.header["NAXIS1"] = 100
        hdu.header["NAXIS2"] = 100
        hdu.header["CRVAL1"] = 180.0
        hdu.header["CRVAL2"] = 0.0
        hdu.header["CDELT1"] = -0.001
        hdu.header["CDELT2"] = 0.001
        hdu.header["CRPIX1"] = 50.0
        hdu.header["CRPIX2"] = 50.0
        hdu.header["CTYPE1"] = "RA---TAN"
        hdu.header["CTYPE2"] = "DEC--TAN"

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        sources = extract_sources_from_image(str(image_path), min_snr=5.0)
        assert len(sources) == 0

    def test_sources_detected(self, tmp_path):
        """Test extraction when sources are present."""
        # Create image with a bright source
        data = np.random.normal(0, 0.1, (100, 100))
        data[50, 50] = 10.0  # Bright source (100σ)
        hdu = fits.PrimaryHDU(data=data)
        hdu.header["NAXIS1"] = 100
        hdu.header["NAXIS2"] = 100
        hdu.header["CRVAL1"] = 180.0
        hdu.header["CRVAL2"] = 0.0
        hdu.header["CDELT1"] = -0.001
        hdu.header["CDELT2"] = 0.001
        hdu.header["CRPIX1"] = 50.0
        hdu.header["CRPIX2"] = 50.0
        hdu.header["CTYPE1"] = "RA---TAN"
        hdu.header["CTYPE2"] = "DEC--TAN"

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        sources = extract_sources_from_image(str(image_path), min_snr=5.0)
        assert len(sources) > 0
        assert "ra_deg" in sources.columns
        assert "dec_deg" in sources.columns
        assert "flux_jy" in sources.columns


class TestGetCatalogOverlayPixels:
    """Test catalog overlay pixel conversion."""

    def test_pixel_conversion(self, tmp_path):
        """Test RA/Dec to pixel coordinate conversion."""
        # Create test image with WCS
        hdu = fits.PrimaryHDU(data=np.zeros((100, 100)))
        hdu.header["NAXIS1"] = 100
        hdu.header["NAXIS2"] = 100
        hdu.header["CRVAL1"] = 180.0
        hdu.header["CRVAL2"] = 0.0
        hdu.header["CDELT1"] = -0.001
        hdu.header["CDELT2"] = 0.001
        hdu.header["CRPIX1"] = 50.0
        hdu.header["CRPIX2"] = 50.0
        hdu.header["CTYPE1"] = "RA---TAN"
        hdu.header["CTYPE2"] = "DEC--TAN"

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        # Create catalog sources
        catalog_sources = pd.DataFrame(
            {"ra_deg": [180.0, 180.001], "dec_deg": [0.0, 0.001], "flux_jy": [1.0, 0.5]}
        )

        pixels = get_catalog_overlay_pixels(str(image_path), catalog_sources)

        assert len(pixels) == 2
        assert "x" in pixels[0]
        assert "y" in pixels[0]
        assert "ra" in pixels[0]
        assert "dec" in pixels[0]
        assert "flux_jy" in pixels[0]

    def test_missing_columns(self, tmp_path):
        """Test handling of missing catalog columns."""
        hdu = fits.PrimaryHDU(data=np.zeros((100, 100)))
        hdu.header["NAXIS1"] = 100
        hdu.header["NAXIS2"] = 100

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        catalog_sources = pd.DataFrame(
            {"ra": [180.0], "dec": [0.0]}  # Wrong column name
        )

        pixels = get_catalog_overlay_pixels(str(image_path), catalog_sources)
        assert len(pixels) == 0


class TestValidateAstrometry:
    """Test astrometry validation."""

    @patch("dsa110_contimg.qa.catalog_validation.query_sources")
    @patch("dsa110_contimg.qa.catalog_validation.extract_sources_from_image")
    def test_good_astrometry(self, mock_extract, mock_query, tmp_path):
        """Test astrometry validation with good matches."""
        # Create test image
        hdu = fits.PrimaryHDU(data=np.zeros((100, 100)))
        hdu.header["NAXIS1"] = 100
        hdu.header["NAXIS2"] = 100
        hdu.header["CRVAL1"] = 180.0
        hdu.header["CRVAL2"] = 0.0
        hdu.header["CDELT1"] = -0.001
        hdu.header["CDELT2"] = 0.001
        hdu.header["CRPIX1"] = 50.0
        hdu.header["CRPIX2"] = 50.0
        hdu.header["CTYPE1"] = "RA---TAN"
        hdu.header["CTYPE2"] = "DEC--TAN"

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        # Mock detected sources
        mock_extract.return_value = pd.DataFrame(
            {
                "ra_deg": [180.0, 180.001],
                "dec_deg": [0.0, 0.001],
                "flux_jy": [1.0, 0.5],
                "snr": [10.0, 8.0],
            }
        )

        # Mock catalog sources (same positions)
        mock_query.return_value = pd.DataFrame(
            {
                "ra_deg": [180.0, 180.001],
                "dec_deg": [0.0, 0.001],
                "flux_mjy": [1000.0, 500.0],
            }
        )

        result = validate_astrometry(
            str(image_path),
            catalog="nvss",
            search_radius_arcsec=10.0,
            max_offset_arcsec=5.0,
        )

        assert result.validation_type == "astrometry"
        assert result.n_matched > 0
        assert result.mean_offset_arcsec is not None
        assert result.has_issues == False  # Good astrometry

    @patch("dsa110_contimg.qa.catalog_validation.query_sources")
    @patch("dsa110_contimg.qa.catalog_validation.extract_sources_from_image")
    def test_no_sources_detected(self, mock_extract, mock_query, tmp_path):
        """Test validation when no sources are detected."""
        hdu = fits.PrimaryHDU(data=np.zeros((100, 100)))
        hdu.header["NAXIS1"] = 100
        hdu.header["NAXIS2"] = 100

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        mock_extract.return_value = pd.DataFrame(
            columns=["ra_deg", "dec_deg", "flux_jy", "snr"]
        )
        mock_query.return_value = pd.DataFrame(
            columns=["ra_deg", "dec_deg", "flux_mjy"]
        )

        result = validate_astrometry(str(image_path))

        assert result.n_detected == 0
        assert result.has_issues == True
        assert "No sources detected" in result.issues[0]


class TestValidateFluxScale:
    """Test flux scale validation."""

    @patch("dsa110_contimg.qa.catalog_validation.measure_forced_peak")
    @patch("dsa110_contimg.qa.catalog_validation.query_sources")
    @patch("dsa110_contimg.qa.catalog_validation.get_image_frequency")
    def test_good_flux_scale(self, mock_freq, mock_query, mock_forced_peak, tmp_path):
        """Test flux scale validation with good flux scale using forced photometry."""
        from dsa110_contimg.photometry.forced import ForcedPhotometryResult

        hdu = fits.PrimaryHDU(data=np.zeros((100, 100)))
        hdu.header["NAXIS1"] = 100
        hdu.header["NAXIS2"] = 100
        hdu.header["CRVAL1"] = 180.0
        hdu.header["CRVAL2"] = 0.0
        hdu.header["CDELT1"] = -0.001
        hdu.header["CDELT2"] = 0.001
        hdu.header["CRPIX1"] = 50.0
        hdu.header["CRPIX2"] = 50.0
        hdu.header["CTYPE1"] = "RA---TAN"
        hdu.header["CTYPE2"] = "DEC--TAN"

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        # Mock frequency
        mock_freq.return_value = 1.4e9  # 1.4 GHz

        # Mock catalog sources
        mock_query.return_value = pd.DataFrame(
            {
                "ra_deg": [180.0, 180.001],
                "dec_deg": [0.0, 0.001],
                "flux_mjy": [1000.0, 500.0],  # 1.0 Jy and 0.5 Jy
            }
        )

        # Mock forced photometry results (flux matches catalog)
        def mock_forced_peak_side_effect(image_path, ra, dec, **kwargs):
            # Return flux matching catalog (1.0 Jy and 0.5 Jy)
            if abs(ra - 180.0) < 0.0001:
                return ForcedPhotometryResult(
                    ra_deg=ra,
                    dec_deg=dec,
                    peak_jyb=1.0,
                    peak_err_jyb=0.05,  # 5% error
                    pix_x=50.0,
                    pix_y=50.0,
                )
            else:
                return ForcedPhotometryResult(
                    ra_deg=ra,
                    dec_deg=dec,
                    peak_jyb=0.5,
                    peak_err_jyb=0.025,  # 5% error
                    pix_x=51.0,
                    pix_y=51.0,
                )

        mock_forced_peak.side_effect = mock_forced_peak_side_effect

        result = validate_flux_scale(
            str(image_path), catalog="nvss", max_flux_ratio_error=0.2
        )

        assert result.validation_type == "flux_scale"
        assert result.mean_flux_ratio is not None
        assert result.n_matched == 2
        # Flux ratio should be close to 1.0 for good scale
        assert abs(result.mean_flux_ratio - 1.0) < 0.2


class TestValidateSourceCounts:
    """Test source count validation."""

    @patch("dsa110_contimg.qa.catalog_validation.extract_sources_from_image")
    @patch("dsa110_contimg.qa.catalog_validation.query_sources")
    def test_good_completeness(self, mock_query, mock_extract, tmp_path):
        """Test source count validation with good completeness."""
        hdu = fits.PrimaryHDU(data=np.zeros((100, 100)))
        hdu.header["NAXIS1"] = 100
        hdu.header["NAXIS2"] = 100

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        # Mock detected sources
        mock_extract.return_value = pd.DataFrame(
            {
                "ra_deg": [180.0, 180.001, 180.002],
                "dec_deg": [0.0, 0.001, 0.002],
                "flux_jy": [1.0, 0.5, 0.3],
                "snr": [10.0, 8.0, 6.0],
            }
        )

        # Mock catalog sources (4 sources, 3 detected = 75% completeness)
        mock_query.return_value = pd.DataFrame(
            {
                "ra_deg": [180.0, 180.001, 180.002, 180.003],
                "dec_deg": [0.0, 0.001, 0.002, 0.003],
                "flux_mjy": [1000.0, 500.0, 300.0, 200.0],
            }
        )

        result = validate_source_counts(
            str(image_path), catalog="nvss", completeness_threshold=0.7
        )

        assert result.validation_type == "source_counts"
        assert result.completeness == pytest.approx(0.75)
        assert result.has_issues == False  # Above threshold

    @patch("dsa110_contimg.qa.catalog_validation.extract_sources_from_image")
    @patch("dsa110_contimg.qa.catalog_validation.query_sources")
    def test_low_completeness(self, mock_query, mock_extract, tmp_path):
        """Test source count validation with low completeness."""
        hdu = fits.PrimaryHDU(data=np.zeros((100, 100)))
        hdu.header["NAXIS1"] = 100
        hdu.header["NAXIS2"] = 100

        image_path = tmp_path / "test.fits"
        hdu.writeto(image_path, overwrite=True)

        # Mock detected sources (only 1)
        mock_extract.return_value = pd.DataFrame(
            {"ra_deg": [180.0], "dec_deg": [0.0], "flux_jy": [1.0], "snr": [10.0]}
        )

        # Mock catalog sources (10 sources, 1 detected = 10% completeness)
        mock_query.return_value = pd.DataFrame(
            {
                "ra_deg": [180.0 + i * 0.001 for i in range(10)],
                "dec_deg": [0.0 + i * 0.001 for i in range(10)],
                "flux_mjy": [1000.0] * 10,
            }
        )

        result = validate_source_counts(
            str(image_path), catalog="nvss", completeness_threshold=0.7
        )

        assert result.completeness == pytest.approx(0.1)
        assert result.has_issues == True  # Below threshold
