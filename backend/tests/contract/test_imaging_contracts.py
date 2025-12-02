"""
Contract tests for FITS image validity.

These tests verify that generated FITS images comply with the FITS standard
and contain valid astronomical data that can be processed by standard tools.

Contract guarantees:
1. Valid FITS structure (headers, data units)
2. Proper WCS (World Coordinate System) information
3. Beam information present
4. Data units specified
5. Images can be opened by astropy.io.fits
6. Images can be displayed by standard visualization tools
"""

from pathlib import Path
from typing import Tuple

import numpy as np
import pytest


class TestFITSStructureContract:
    """Verify FITS file structure and headers."""

    def test_fits_file_exists(self, synthetic_fits_image: Path):
        """Contract: FITS file must exist."""
        assert synthetic_fits_image.exists(), f"FITS not created at {synthetic_fits_image}"
        assert synthetic_fits_image.is_file(), "FITS must be a file"

    def test_fits_readable_by_astropy(self, synthetic_fits_image: Path):
        """Contract: FITS must be readable by astropy."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            assert len(hdul) >= 1, "FITS must have at least one HDU"
            
            # Primary HDU should have data
            assert hdul[0].data is not None, "Primary HDU has no data"

    def test_fits_data_is_2d(self, synthetic_fits_image: Path):
        """Contract: Image data must be 2D array."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            data = hdul[0].data
            
            # May be (1,1,NY,NX) or (NY,NX) - squeeze extra dims
            data = np.squeeze(data)
            assert data.ndim == 2, f"Image should be 2D, got {data.ndim}D"

    def test_fits_data_not_all_zero(self, synthetic_fits_image: Path):
        """Contract: Image must contain non-zero data."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            data = np.squeeze(hdul[0].data)
            
            assert not np.allclose(data, 0), "Image is all zeros"
            assert not np.all(np.isnan(data)), "Image is all NaN"


class TestWCSContract:
    """Verify World Coordinate System information."""

    def test_wcs_present(self, synthetic_fits_image: Path):
        """Contract: FITS must have valid WCS."""
        from astropy.io import fits
        from astropy.wcs import WCS
        
        with fits.open(synthetic_fits_image) as hdul:
            header = hdul[0].header
            
            # These WCS keywords must be present
            required_wcs = ["CRPIX1", "CRPIX2", "CRVAL1", "CRVAL2", "CTYPE1", "CTYPE2"]
            for key in required_wcs:
                assert key in header, f"WCS keyword {key} missing"
            
            # WCS must be constructable
            wcs = WCS(header)
            assert wcs.has_celestial, "WCS must have celestial coordinates"

    def test_wcs_coordinates_valid(self, synthetic_fits_image: Path):
        """Contract: WCS must produce valid sky coordinates."""
        from astropy.io import fits
        from astropy.wcs import WCS
        
        with fits.open(synthetic_fits_image) as hdul:
            wcs = WCS(hdul[0].header)
            data = np.squeeze(hdul[0].data)
            
            # Center pixel should map to valid RA/Dec
            ny, nx = data.shape
            center_pix = (nx // 2, ny // 2)
            
            sky = wcs.pixel_to_world(*center_pix)
            ra = sky.ra.deg
            dec = sky.dec.deg
            
            # Valid ranges
            assert 0 <= ra <= 360, f"RA {ra} out of range"
            assert -90 <= dec <= 90, f"Dec {dec} out of range"

    def test_pixel_scale_reasonable(self, synthetic_fits_image: Path):
        """Contract: Pixel scale must be reasonable for radio images."""
        from astropy.io import fits
        from astropy.wcs import WCS
        import astropy.units as u
        
        with fits.open(synthetic_fits_image) as hdul:
            wcs = WCS(hdul[0].header)
            
            # Get pixel scale from CDELT or CD matrix
            if hasattr(wcs.wcs, "cdelt"):
                cdelt = np.abs(wcs.wcs.cdelt)
                # Convert to arcsec
                pixel_scale_arcsec = cdelt[0] * 3600
            elif hasattr(wcs.wcs, "cd"):
                cd = wcs.wcs.cd
                pixel_scale_arcsec = np.sqrt(cd[0, 0]**2 + cd[1, 0]**2) * 3600
            else:
                pytest.skip("Cannot determine pixel scale")
            
            # Reasonable range for DSA-110: 0.5" to 30"
            assert 0.5 <= pixel_scale_arcsec <= 30, \
                f"Pixel scale {pixel_scale_arcsec}\" out of expected range"


class TestBeamContract:
    """Verify beam/PSF information."""

    def test_beam_keywords_present(self, synthetic_fits_image: Path):
        """Contract: FITS must have beam information."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            header = hdul[0].header
            
            # Standard beam keywords
            beam_keywords = ["BMAJ", "BMIN", "BPA"]
            found_beam = any(key in header for key in beam_keywords)
            
            assert found_beam, "No beam keywords (BMAJ/BMIN/BPA) found"

    def test_beam_size_reasonable(self, synthetic_fits_image: Path):
        """Contract: Beam size must be reasonable for DSA-110."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            header = hdul[0].header
            
            if "BMAJ" in header:
                bmaj_deg = header["BMAJ"]
                bmin_deg = header.get("BMIN", bmaj_deg)
                
                bmaj_arcsec = bmaj_deg * 3600
                bmin_arcsec = bmin_deg * 3600
                
                # DSA-110 beam: roughly 10" to 60" depending on frequency
                assert 1 <= bmaj_arcsec <= 120, f"BMAJ {bmaj_arcsec}\" unreasonable"
                assert bmin_arcsec <= bmaj_arcsec, "BMIN > BMAJ"


class TestDataUnitsContract:
    """Verify data units and scaling."""

    def test_bunit_present(self, synthetic_fits_image: Path):
        """Contract: FITS must specify data units."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            header = hdul[0].header
            
            assert "BUNIT" in header, "BUNIT (data units) not specified"

    def test_bunit_is_jy_beam(self, synthetic_fits_image: Path):
        """Contract: Data units should be Jy/beam for continuum images."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            header = hdul[0].header
            
            bunit = header.get("BUNIT", "").lower()
            
            # Accept common variants
            valid_units = ["jy/beam", "jy beam-1", "jy.beam-1"]
            assert any(v in bunit for v in valid_units), \
                f"BUNIT '{bunit}' not recognized as Jy/beam"

    def test_data_values_reasonable(self, synthetic_fits_image: Path):
        """Contract: Pixel values must be physically reasonable."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            data = np.squeeze(hdul[0].data)
            
            # Remove NaN for statistics
            valid_data = data[~np.isnan(data)]
            
            if len(valid_data) == 0:
                pytest.fail("All data is NaN")
            
            data_max = np.max(np.abs(valid_data))
            data_rms = np.std(valid_data)
            
            # For DSA-110, peak should be < 100 Jy, RMS should be < 1 Jy
            assert data_max < 100, f"Peak {data_max} Jy unreasonably high"
            assert data_rms < 1, f"RMS {data_rms} Jy unreasonably high"


class TestProvenanceContract:
    """Verify image provenance metadata."""

    def test_date_obs_present(self, synthetic_fits_image: Path):
        """Contract: FITS should have observation date."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            header = hdul[0].header
            
            # DATE-OBS or DATE should be present
            has_date = "DATE-OBS" in header or "DATE" in header
            assert has_date, "No observation date found"

    def test_synthetic_marker_present(self, synthetic_fits_image: Path):
        """Contract: Synthetic images must be marked."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            header = hdul[0].header
            
            # Our synthetic_fits adds SYNTHETIC=True
            is_marked = (
                header.get("SYNTHETIC", False) or
                "synthetic" in header.get("OBJECT", "").lower() or
                "synthetic" in str(header.get("COMMENT", "")).lower()
            )
            
            assert is_marked, "Synthetic image not marked as synthetic"


class TestImageQualityContract:
    """Verify image quality metrics are calculable."""

    def test_rms_calculable(self, synthetic_fits_image: Path):
        """Contract: RMS noise should be measurable."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            data = np.squeeze(hdul[0].data)
            
            # Measure RMS in corner regions (away from sources)
            ny, nx = data.shape
            corner_size = min(nx, ny) // 4
            
            corners = [
                data[:corner_size, :corner_size],
                data[:corner_size, -corner_size:],
                data[-corner_size:, :corner_size],
                data[-corner_size:, -corner_size:],
            ]
            
            corner_data = np.concatenate([c.flatten() for c in corners])
            corner_data = corner_data[~np.isnan(corner_data)]
            
            if len(corner_data) > 0:
                rms = np.std(corner_data)
                assert rms > 0, "RMS is zero - data may be constant"
                assert np.isfinite(rms), "RMS is not finite"

    def test_dynamic_range_positive(self, synthetic_fits_image: Path):
        """Contract: Image should have positive dynamic range."""
        from astropy.io import fits
        
        with fits.open(synthetic_fits_image) as hdul:
            data = np.squeeze(hdul[0].data)
            valid_data = data[~np.isnan(data)]
            
            peak = np.max(valid_data)
            rms = np.std(valid_data)
            
            if rms > 0:
                snr = peak / rms
                assert snr > 1, f"Peak SNR {snr:.1f} too low"
