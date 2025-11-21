"""Unit tests for photometry helper functions."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dsa110_contimg.photometry.helpers import (
    get_field_center_from_fits,
    query_sources_for_fits,
    query_sources_for_mosaic,
)


class TestGetFieldCenterFromFits:
    """Test get_field_center_from_fits function."""

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            get_field_center_from_fits(Path("/nonexistent/file.fits"))

    @patch("dsa110_contimg.photometry.helpers.fits.open")
    @patch("dsa110_contimg.photometry.helpers.WCS")
    @patch("dsa110_contimg.photometry.helpers.Path.exists")
    def test_wcs_extraction_success(self, mock_exists, mock_wcs_class, mock_fits_open):
        """Test successful WCS-based extraction."""
        mock_exists.return_value = True

        # Setup mock FITS header
        mock_hdr = Mock()
        mock_hdr.get.side_effect = lambda key, default: {
            "NAXIS1": 100,
            "NAXIS2": 100,
            "NAXIS": 2,
        }.get(key, default)

        mock_wcs = Mock()
        mock_wcs.has_celestial = True
        mock_wcs.all_pix2world.return_value = (180.0, 45.0, 0.0)
        mock_wcs_class.return_value = mock_wcs

        mock_hdul = Mock()
        mock_hdul.__enter__ = Mock(return_value=[Mock(header=mock_hdr)])
        mock_hdul.__exit__ = Mock(return_value=None)
        mock_fits_open.return_value = mock_hdul

        fits_path = Path("/tmp/test.fits")
        ra, dec = get_field_center_from_fits(fits_path)

        assert ra == 180.0
        assert dec == 45.0
        mock_wcs.all_pix2world.assert_called_once_with(50.0, 50.0, 0)

    @patch("dsa110_contimg.photometry.helpers.fits.open")
    @patch("dsa110_contimg.photometry.helpers.WCS")
    @patch("dsa110_contimg.photometry.helpers.Path.exists")
    def test_crval_fallback(self, mock_exists, mock_wcs_class, mock_fits_open):
        """Test fallback to CRVAL1/CRVAL2 when WCS fails."""
        mock_exists.return_value = True

        # Setup mock FITS header
        mock_hdr = Mock()

        def header_get(key, default=None):
            header_dict = {
                "CRVAL1": 180.5,
                "CRVAL2": 45.5,
                "NAXIS1": 100,
                "NAXIS2": 100,
                "NAXIS": 2,
            }
            return header_dict.get(key, default)

        mock_hdr.get.side_effect = header_get

        # WCS fails
        mock_wcs_class.side_effect = ValueError("WCS error")

        mock_hdul = Mock()
        mock_hdul.__enter__ = Mock(return_value=[Mock(header=mock_hdr)])
        mock_hdul.__exit__ = Mock(return_value=None)
        mock_fits_open.return_value = mock_hdul

        fits_path = Path("/tmp/test.fits")
        ra, dec = get_field_center_from_fits(fits_path)

        assert ra == 180.5
        assert dec == 45.5

    @patch("dsa110_contimg.photometry.helpers.fits.open")
    @patch("dsa110_contimg.photometry.helpers.Path.exists")
    def test_no_valid_coordinates(self, mock_exists, mock_fits_open):
        """Test that ValueError is raised when no valid coordinates found."""
        mock_exists.return_value = True

        mock_hdr = Mock()
        mock_hdr.get.return_value = None

        mock_hdul = Mock()
        mock_hdul.__enter__ = Mock(return_value=[Mock(header=mock_hdr)])
        mock_hdul.__exit__ = Mock(return_value=None)
        mock_fits_open.return_value = mock_hdul

        fits_path = Path("/tmp/test.fits")
        with pytest.raises(ValueError, match="Cannot extract field center"):
            get_field_center_from_fits(fits_path)


class TestQuerySourcesForFits:
    """Test query_sources_for_fits function."""

    @patch("dsa110_contimg.photometry.helpers.query_sources")
    @patch("dsa110_contimg.photometry.helpers.get_field_center_from_fits")
    def test_successful_query(self, mock_get_center, mock_query):
        """Test successful source query."""
        mock_get_center.return_value = (180.0, 45.0)
        mock_df = Mock()
        mock_df.empty = False
        mock_df.to_dict.return_value = [
            {"ra": 180.0, "dec": 45.0, "flux_mjy": 10.0},
            {"ra": 180.1, "dec": 45.1, "flux_mjy": 20.0},
        ]
        mock_query.return_value = mock_df

        fits_path = Path("/tmp/test.fits")
        sources = query_sources_for_fits(fits_path, catalog="nvss", radius_deg=0.5)

        assert len(sources) == 2
        assert sources[0]["ra"] == 180.0
        mock_get_center.assert_called_once_with(fits_path)
        mock_query.assert_called_once_with(
            catalog_type="nvss",
            ra_center=180.0,
            dec_center=45.0,
            radius_deg=0.5,
            min_flux_mjy=None,
            max_sources=None,
            catalog_path=None,
        )

    @patch("dsa110_contimg.photometry.helpers.query_sources")
    @patch("dsa110_contimg.photometry.helpers.get_field_center_from_fits")
    def test_empty_results(self, mock_get_center, mock_query):
        """Test handling of empty query results."""
        mock_get_center.return_value = (180.0, 45.0)
        mock_df = Mock()
        mock_df.empty = True
        mock_query.return_value = mock_df

        fits_path = Path("/tmp/test.fits")
        sources = query_sources_for_fits(fits_path)

        assert sources == []
        mock_query.assert_called_once()

    @patch("dsa110_contimg.photometry.helpers.get_field_center_from_fits")
    def test_exception_handling(self, mock_get_center):
        """Test that exceptions are caught and empty list returned."""
        mock_get_center.side_effect = ValueError("FITS error")

        fits_path = Path("/tmp/test.fits")
        sources = query_sources_for_fits(fits_path)

        assert sources == []

    @patch("dsa110_contimg.photometry.helpers.query_sources")
    @patch("dsa110_contimg.photometry.helpers.get_field_center_from_fits")
    def test_with_parameters(self, mock_get_center, mock_query):
        """Test query with all parameters specified."""
        mock_get_center.return_value = (180.0, 45.0)
        mock_df = Mock()
        mock_df.empty = False
        mock_df.to_dict.return_value = []
        mock_query.return_value = mock_df

        fits_path = Path("/tmp/test.fits")
        catalog_path = Path("/tmp/catalog.db")
        query_sources_for_fits(
            fits_path,
            catalog="first",
            radius_deg=1.0,
            min_flux_mjy=5.0,
            max_sources=100,
            catalog_path=catalog_path,
        )

        mock_query.assert_called_once_with(
            catalog_type="first",
            ra_center=180.0,
            dec_center=45.0,
            radius_deg=1.0,
            min_flux_mjy=5.0,
            max_sources=100,
            catalog_path=str(catalog_path),
        )


class TestQuerySourcesForMosaic:
    """Test query_sources_for_mosaic function."""

    @patch("dsa110_contimg.photometry.helpers.query_sources")
    @patch("dsa110_contimg.photometry.helpers.get_field_center_from_fits")
    def test_successful_query(self, mock_get_center, mock_query):
        """Test successful source query for mosaic."""
        mock_get_center.return_value = (180.0, 45.0)
        mock_df = Mock()
        mock_df.empty = False
        mock_df.to_dict.return_value = [
            {"ra": 180.0, "dec": 45.0, "flux_mjy": 10.0},
        ]
        mock_query.return_value = mock_df

        mosaic_path = Path("/tmp/mosaic.fits")
        sources = query_sources_for_mosaic(mosaic_path, catalog="nvss", radius_deg=1.5)

        assert len(sources) == 1
        mock_get_center.assert_called_once_with(mosaic_path)
        # Verify default radius is 1.0 but can be overridden
        mock_query.assert_called_once_with(
            catalog_type="nvss",
            ra_center=180.0,
            dec_center=45.0,
            radius_deg=1.5,  # Overridden value
            min_flux_mjy=None,
            max_sources=None,
            catalog_path=None,
        )

    @patch("dsa110_contimg.photometry.helpers.query_sources")
    @patch("dsa110_contimg.photometry.helpers.get_field_center_from_fits")
    def test_default_radius(self, mock_get_center, mock_query):
        """Test that default radius is 1.0 for mosaics."""
        mock_get_center.return_value = (180.0, 45.0)
        mock_df = Mock()
        mock_df.empty = True
        mock_query.return_value = mock_df

        mosaic_path = Path("/tmp/mosaic.fits")
        query_sources_for_mosaic(mosaic_path)

        mock_query.assert_called_once()
        call_kwargs = mock_query.call_args[1]
        assert call_kwargs["radius_deg"] == 1.0  # Default for mosaics

    @patch("dsa110_contimg.photometry.helpers.get_field_center_from_fits")
    def test_exception_handling(self, mock_get_center):
        """Test that exceptions are caught and empty list returned."""
        mock_get_center.side_effect = ValueError("FITS error")

        mosaic_path = Path("/tmp/mosaic.fits")
        sources = query_sources_for_mosaic(mosaic_path)

        assert sources == []
