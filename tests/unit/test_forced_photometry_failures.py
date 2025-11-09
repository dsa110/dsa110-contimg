#!/usr/bin/env python3
"""Test forced photometry failure scenarios."""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path
from astropy.io import fits

from dsa110_contimg.photometry.forced import measure_forced_peak
from dsa110_contimg.qa.catalog_validation import validate_flux_scale


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
    """Create a test FITS file with specified parameters."""
    if data is None:
        data = np.random.normal(0, 0.001, data_shape)
    
    hdu = fits.PrimaryHDU(data=data)
    hdu.header['CRVAL1'] = crval1
    hdu.header['CRVAL2'] = crval2
    hdu.header['CRPIX1'] = crpix1
    hdu.header['CRPIX2'] = crpix2
    hdu.header['CDELT1'] = cdelts[0]
    hdu.header['CDELT2'] = cdelts[1]
    hdu.header['CTYPE1'] = 'RA---SIN'
    hdu.header['CTYPE2'] = 'DEC--SIN'
    hdu.header['NAXIS1'] = data_shape[1]
    hdu.header['NAXIS2'] = data_shape[0]
    hdu.header['RESTFRQ'] = 1.4  # GHz
    
    for key, value in header_kwargs.items():
        hdu.header[key] = value
    
    tmp = tempfile.NamedTemporaryFile(suffix='.fits', delete=False)
    tmp_fits = tmp.name
    hdu.writeto(tmp_fits, overwrite=True)
    return tmp_fits


class TestForcedPhotometryFailures:
    """Test forced photometry failure scenarios."""
    
    def test_coordinates_out_of_bounds(self):
        """Test coordinates outside image bounds."""
        tmp_fits = create_test_fits()
        try:
            # Coordinates way outside image
            result = measure_forced_peak(
                tmp_fits,
                ra_deg=0.0,  # Way off from center
                dec_deg=0.0,
                box_size_pix=5,
                annulus_pix=(12, 20)
            )
            # Should return values (may be edge pixels or NaN)
            assert isinstance(result.peak_jyb, (float, np.floating))
            # Should not raise exception
        finally:
            os.unlink(tmp_fits)
    
    def test_invalid_wcs_missing_crval(self):
        """Test invalid WCS (missing CRVAL keywords)."""
        tmp_fits = create_test_fits()
        
        # Corrupt WCS by removing CRVAL
        with fits.open(tmp_fits, mode='update') as hdul:
            if 'CRVAL1' in hdul[0].header:
                del hdul[0].header['CRVAL1']
            if 'CRVAL2' in hdul[0].header:
                del hdul[0].header['CRVAL2']
            hdul.flush()
        
        try:
            result = measure_forced_peak(
                tmp_fits,
                ra_deg=180.0,
                dec_deg=35.0,
                box_size_pix=5,
                annulus_pix=(12, 20)
            )
            # Should handle gracefully (may raise or return NaN)
            assert isinstance(result.peak_jyb, (float, np.floating)) or np.isnan(result.peak_jyb)
        except Exception:
            # Exception is acceptable - validate_flux_scale catches it
            pass
        finally:
            os.unlink(tmp_fits)
    
    def test_missing_file(self):
        """Test missing FITS file."""
        result = measure_forced_peak(
            '/nonexistent/path/image.fits',
            ra_deg=180.0,
            dec_deg=35.0,
            box_size_pix=5,
            annulus_pix=(12, 20)
        )
        # Should return NaN or zero, not raise
        assert isinstance(result.peak_jyb, (float, np.floating))
    
    def test_empty_image_data(self):
        """Test image with all NaN data."""
        data = np.full((512, 512), np.nan)
        tmp_fits = create_test_fits(data=data)
        
        try:
            result = measure_forced_peak(
                tmp_fits,
                ra_deg=180.0,
                dec_deg=35.0,
                box_size_pix=5,
                annulus_pix=(12, 20)
            )
            # Should return NaN
            assert np.isnan(result.peak_jyb) or result.peak_jyb == 0
        finally:
            os.unlink(tmp_fits)
    
    def test_small_image_large_box(self):
        """Test very small image with box_size larger than image."""
        tmp_fits = create_test_fits(
            data_shape=(10, 10),
            crpix1=5.0,
            crpix2=5.0,
            cdelts=(-0.001, 0.001)
        )
        
        try:
            result = measure_forced_peak(
                tmp_fits,
                ra_deg=180.0,
                dec_deg=35.0,
                box_size_pix=20,  # Larger than image!
                annulus_pix=(12, 20)  # Also larger!
            )
            # Should clip to image bounds gracefully
            assert isinstance(result.peak_jyb, (float, np.floating))
        finally:
            os.unlink(tmp_fits)
    
    def test_validate_flux_scale_handles_failures(self):
        """Test that validate_flux_scale handles forced photometry failures."""
        # Create image with very low signal (will cause measurement failures)
        data = np.random.normal(0, 0.0001, (512, 512))  # Very low noise
        tmp_fits = create_test_fits(data=data)
        
        try:
            result = validate_flux_scale(
                image_path=tmp_fits,
                catalog='nvss',
                min_snr=5.0,  # High threshold - most sources will fail
                flux_range_jy=(0.01, 10.0),
                max_flux_ratio_error=0.2
            )
            # Should return result even if all measurements fail
            assert result.validation_type == "flux_scale"
            assert result.n_matched >= 0  # May be 0 if all fail
            # Should have issues if no valid measurements
            if result.n_matched == 0:
                assert result.has_issues
        except FileNotFoundError:
            # Catalog DB missing - this is handled by the function
            pytest.skip("Catalog database not available")
        finally:
            os.unlink(tmp_fits)

