"""
Tests for the FITS parsing service.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.api.services.fits_service import (
    FITSParsingService,
    FITSMetadata,
    get_fits_service,
    parse_fits_header,
)
from dsa110_contimg.api.exceptions import FITSParsingError, FileNotAccessibleError


class TestFITSMetadata:
    """Tests for FITSMetadata dataclass."""
    
    def test_cellsize_arcsec_from_cdelt(self):
        """Test cell size calculation from cdelt."""
        metadata = FITSMetadata(path="/test.fits", cdelt1=-0.001)
        assert metadata.cellsize_arcsec == pytest.approx(3.6)
    
    def test_cellsize_arcsec_positive_cdelt(self):
        """Test cell size with positive cdelt."""
        metadata = FITSMetadata(path="/test.fits", cdelt1=0.0005)
        assert metadata.cellsize_arcsec == pytest.approx(1.8)
    
    def test_cellsize_arcsec_none_without_cdelt(self):
        """Test cell size is None when cdelt not set."""
        metadata = FITSMetadata(path="/test.fits")
        assert metadata.cellsize_arcsec is None
    
    def test_beam_major_arcsec_from_bmaj(self):
        """Test beam size in arcseconds."""
        metadata = FITSMetadata(
            path="/test.fits",
            bmaj=0.01,  # degrees
            bmin=0.005,
        )
        assert metadata.beam_major_arcsec == pytest.approx(36.0)
        assert metadata.beam_minor_arcsec == pytest.approx(18.0)
    
    def test_beam_major_arcsec_none_without_bmaj(self):
        """Test beam size is None when bmaj not set."""
        metadata = FITSMetadata(path="/test.fits")
        assert metadata.beam_major_arcsec is None
    
    def test_default_values(self):
        """Test default values for metadata."""
        metadata = FITSMetadata(path="/test.fits")
        assert metadata.exists is True
        assert metadata.size_bytes == 0
        assert metadata.object_name is None
        assert metadata.ra_deg is None
        assert metadata.dec_deg is None


class TestFITSParsingService:
    """Tests for FITSParsingService class."""
    
    @pytest.fixture
    def service(self):
        """Create a FITS parsing service instance."""
        return FITSParsingService()
    
    def test_file_not_found_raises_error(self, service):
        """Test that parsing non-existent file raises FileNotAccessibleError."""
        with pytest.raises(FileNotAccessibleError):
            service.parse_header("/nonexistent/path/to/file.fits")
    
    def test_parse_header_file_not_accessible(self, service):
        """Test FileNotAccessibleError for non-existent paths."""
        # Use a path that definitely doesn't exist (no permission issues)
        with pytest.raises(FileNotAccessibleError) as exc_info:
            service.parse_header("/tmp/nonexistent_dir_12345/nonexistent_file.fits")
        assert "nonexistent" in str(exc_info.value).lower()
    
    @patch("dsa110_contimg.api.services.fits_service.FITSParsingService._get_fits_module")
    def test_parse_header_with_mock_fits(self, mock_get_fits, service, tmp_path):
        """Test parse_header with mocked FITS module."""
        # Create a dummy file
        test_file = tmp_path / "test.fits"
        test_file.write_bytes(b"SIMPLE  = T" + b" " * 2870)  # Minimal FITS header
        
        # Mock the FITS module
        mock_fits = MagicMock()
        mock_hdul = MagicMock()
        mock_header = {
            "OBJECT": "Test Source",
            "NAXIS1": 1024,
            "NAXIS2": 1024,
            "CRVAL1": 180.0,
            "CRVAL2": 45.0,
            "CDELT1": -0.001,
            "CDELT2": 0.001,
            "BMAJ": 0.01,
            "BMIN": 0.005,
            "BPA": 30.0,
            "BUNIT": "Jy/beam",
            "RESTFREQ": 1.4e9,
        }
        mock_header.get = lambda k, d=None: mock_header.get(k, d)
        mock_hdul[0].header = mock_header
        mock_hdul[0].data = None
        mock_fits.open.return_value.__enter__ = MagicMock(return_value=mock_hdul)
        mock_fits.open.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_fits.return_value = mock_fits
        
        # Parse the file
        metadata = service.parse_header(str(test_file))
        
        assert metadata.path == str(test_file)
        assert metadata.exists is True
    
    @patch("dsa110_contimg.api.services.fits_service.FITSParsingService._get_fits_module")
    def test_parse_header_extracts_wcs(self, mock_get_fits, service, tmp_path):
        """Test WCS coordinate extraction."""
        test_file = tmp_path / "test.fits"
        test_file.write_bytes(b"SIMPLE  = T" + b" " * 2870)
        
        mock_fits = MagicMock()
        mock_hdul = MagicMock()
        mock_header = MagicMock()
        mock_header.get.side_effect = lambda k, d=None: {
            "CRVAL1": 180.0,
            "CRVAL2": -45.0,
            "CRPIX1": 512.0,
            "CRPIX2": 512.0,
            "CDELT1": -0.0001,
            "CDELT2": 0.0001,
            "CTYPE1": "RA---SIN",
            "CTYPE2": "DEC--SIN",
        }.get(k, d)
        mock_header.__getitem__ = lambda s, k: mock_header.get(k)
        mock_header.__contains__ = lambda s, k: k in ["CRVAL1", "CRVAL2", "CRPIX1", "CRPIX2", "CDELT1", "CDELT2", "CTYPE1", "CTYPE2"]
        mock_hdul[0].header = mock_header
        mock_hdul[0].data = None
        mock_fits.open.return_value.__enter__ = MagicMock(return_value=mock_hdul)
        mock_fits.open.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_fits.return_value = mock_fits
        
        metadata = service.parse_header(str(test_file))
        
        # Should extract WCS
        assert metadata.ctype1 == "RA---SIN"
        assert metadata.ctype2 == "DEC--SIN"
    
    def test_extract_frequency_from_restfreq(self, service):
        """Test frequency extraction from RESTFREQ."""
        header = MagicMock()
        header.get.side_effect = lambda k, d=None: {
            "RESTFREQ": 1.4e9,
        }.get(k, d)
        
        freq = service._extract_frequency(header)
        assert freq == pytest.approx(1.4e9)
    
    def test_extract_frequency_from_crval3(self, service):
        """Test frequency extraction from CRVAL3 (spectral axis)."""
        header = MagicMock()
        header.get.side_effect = lambda k, d=None: {
            "CRVAL3": 1.5e9,
            "CTYPE3": "FREQ",
        }.get(k, d)
        
        freq = service._extract_frequency(header)
        assert freq == pytest.approx(1.5e9)
    
    def test_extract_bandwidth(self, service):
        """Test bandwidth extraction."""
        header = MagicMock()
        header.get.side_effect = lambda k, d=None: {
            "BANDWIDTH": 2e8,
        }.get(k, d)
        
        bw = service._extract_bandwidth(header)
        assert bw == pytest.approx(2e8)
    
    def test_validate_fits_nonexistent(self, service):
        """Test validation of non-existent file."""
        result = service.validate_fits("/nonexistent/file.fits")
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0].lower()


class TestModuleFunctions:
    """Tests for module-level convenience functions."""
    
    def test_get_fits_service_singleton(self):
        """Test that get_fits_service returns singleton."""
        service1 = get_fits_service()
        service2 = get_fits_service()
        assert service1 is service2
    
    def test_parse_fits_header_convenience(self, tmp_path):
        """Test convenience function for parsing headers."""
        # This should raise FileNotAccessibleError for non-existent file
        with pytest.raises(FileNotAccessibleError):
            parse_fits_header("/nonexistent/file.fits")


class TestFITSParsingIntegration:
    """Integration tests with real FITS files (if available)."""
    
    @pytest.fixture
    def sample_fits_path(self):
        """Return path to a sample FITS file if available."""
        # Check common locations for test FITS files
        test_paths = [
            "/data/dsa110-contimg/state/images/test.fits",
            "/tmp/test.fits",
        ]
        for path in test_paths:
            if os.path.exists(path):
                return path
        return None
    
    @pytest.mark.skipif(
        not os.path.exists("/data/dsa110-contimg/state/images"),
        reason="No sample FITS files available"
    )
    def test_parse_real_fits_file(self, sample_fits_path):
        """Test parsing a real FITS file."""
        if sample_fits_path is None:
            pytest.skip("No sample FITS file found")
        
        service = FITSParsingService()
        metadata = service.parse_header(sample_fits_path)
        
        assert metadata.exists is True
        assert metadata.size_bytes > 0
        assert metadata.path == sample_fits_path


class TestFITSParsingErrors:
    """Tests for error handling in FITS parsing."""
    
    @pytest.fixture
    def service(self):
        return FITSParsingService()
    
    def test_corrupt_fits_raises_parsing_error(self, service, tmp_path):
        """Test that corrupt FITS file raises FITSParsingError."""
        corrupt_file = tmp_path / "corrupt.fits"
        corrupt_file.write_bytes(b"This is not a FITS file")
        
        with pytest.raises(FITSParsingError):
            service.parse_header(str(corrupt_file))
    
    def test_empty_file_raises_parsing_error(self, service, tmp_path):
        """Test that empty file raises FITSParsingError."""
        empty_file = tmp_path / "empty.fits"
        empty_file.write_bytes(b"")
        
        with pytest.raises(FITSParsingError):
            service.parse_header(str(empty_file))
    
    def test_truncated_fits_raises_parsing_error(self, service, tmp_path):
        """Test that truncated FITS file raises FITSParsingError."""
        truncated_file = tmp_path / "truncated.fits"
        # Start of valid FITS header but truncated
        truncated_file.write_bytes(b"SIMPLE  =                    T / conforms to FITS standard")
        
        with pytest.raises(FITSParsingError):
            service.parse_header(str(truncated_file))
