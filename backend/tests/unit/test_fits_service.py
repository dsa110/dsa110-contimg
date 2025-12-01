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
        
        # Create a proper mock header with __contains__ support
        header_data = {
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
        mock_header = MagicMock()
        mock_header.get.side_effect = lambda k, d=None: header_data.get(k, d)
        mock_header.__getitem__ = lambda s, k: header_data.get(k)
        mock_header.__contains__ = lambda s, k: k in header_data
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
        header_data = {"RESTFREQ": 1.4e9}
        header = MagicMock()
        header.get.side_effect = lambda k, d=None: header_data.get(k, d)
        header.__getitem__ = lambda s, k: header_data.get(k)
        header.__contains__ = lambda s, k: k in header_data
        
        freq = service._extract_frequency(header)
        assert freq == pytest.approx(1.4e9)
    
    def test_extract_frequency_from_crval3(self, service):
        """Test frequency extraction from CRVAL3 (spectral axis)."""
        header_data = {"CRVAL3": 1.5e9, "CTYPE3": "FREQ"}
        header = MagicMock()
        header.get.side_effect = lambda k, d=None: header_data.get(k, d)
        header.__getitem__ = lambda s, k: header_data.get(k)
        header.__contains__ = lambda s, k: k in header_data
        
        freq = service._extract_frequency(header)
        assert freq == pytest.approx(1.5e9)
    
    def test_extract_bandwidth(self, service):
        """Test bandwidth extraction."""
        header_data = {"BANDWIDTH": 2e8}
        header = MagicMock()
        header.get.side_effect = lambda k, d=None: header_data.get(k, d)
        header.__getitem__ = lambda s, k: header_data.get(k)
        header.__contains__ = lambda s, k: k in header_data
        
        bw = service._extract_bandwidth(header)
        assert bw == pytest.approx(2e8)
    
    def test_validate_fits_nonexistent(self, service):
        """Test validation of non-existent file."""
        result = service.validate_fits("/nonexistent/file.fits")
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        # Check for either "not found" or "does not exist"
        error_text = result["errors"][0].lower()
        assert "not" in error_text or "does" in error_text


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
    """Integration tests with FITS files."""
    
    @pytest.fixture
    def synthetic_fits_path(self, tmp_path):
        """Create a minimal valid FITS file for testing.
        
        This creates a proper FITS file with standard headers that can be
        parsed by the FITSParsingService. Using astropy to create the file
        ensures it's a valid FITS format.
        """
        try:
            from astropy.io import fits
            import numpy as np
            
            # Create a minimal 2D image with standard radio astronomy headers
            data = np.zeros((64, 64), dtype=np.float32)
            hdu = fits.PrimaryHDU(data)
            
            # Add standard WCS headers for radio astronomy imaging
            hdu.header['CTYPE1'] = 'RA---SIN'
            hdu.header['CTYPE2'] = 'DEC--SIN'
            hdu.header['CRPIX1'] = 32.0
            hdu.header['CRPIX2'] = 32.0
            hdu.header['CRVAL1'] = 180.0  # RA in degrees
            hdu.header['CRVAL2'] = 45.0   # Dec in degrees
            hdu.header['CDELT1'] = -0.001  # Cell size in degrees
            hdu.header['CDELT2'] = 0.001
            hdu.header['CUNIT1'] = 'deg'
            hdu.header['CUNIT2'] = 'deg'
            
            # Beam parameters (common in radio images)
            hdu.header['BMAJ'] = 0.005  # Beam major axis in degrees
            hdu.header['BMIN'] = 0.003  # Beam minor axis
            hdu.header['BPA'] = 45.0    # Beam position angle
            
            # Other useful metadata
            hdu.header['TELESCOP'] = 'DSA-110'
            hdu.header['INSTRUME'] = 'DSA-110 Correlator'
            hdu.header['DATE-OBS'] = '2025-01-15T12:00:00'
            hdu.header['BUNIT'] = 'JY/BEAM'
            
            fits_path = tmp_path / "test_image.fits"
            hdu.writeto(str(fits_path), overwrite=True)
            return str(fits_path)
        except ImportError:
            pytest.skip("astropy not available for creating test FITS file")
    
    def test_parse_synthetic_fits_file(self, synthetic_fits_path):
        """Test parsing a synthetic FITS file with realistic headers."""
        service = FITSParsingService()
        metadata = service.parse_header(synthetic_fits_path)
        
        # Basic file properties
        assert metadata.exists is True
        assert metadata.size_bytes > 0
        assert metadata.path == synthetic_fits_path
        
        # WCS properties should be extracted
        assert metadata.crval1 == pytest.approx(180.0)
        assert metadata.crval2 == pytest.approx(45.0)
        assert metadata.cdelt1 == pytest.approx(-0.001)
        
        # Derived properties
        assert metadata.cellsize_arcsec == pytest.approx(3.6)  # 0.001 deg = 3.6 arcsec
        
        # Beam properties
        assert metadata.bmaj == pytest.approx(0.005)
        assert metadata.bmin == pytest.approx(0.003)
        assert metadata.beam_major_arcsec == pytest.approx(18.0)  # 0.005 deg = 18 arcsec


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
