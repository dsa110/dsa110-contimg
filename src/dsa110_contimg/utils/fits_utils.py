"""
FITS file utilities for proper format compliance.

Ensures FITS headers conform to FITS standard format requirements.
"""
from astropy.io import fits
from typing import Optional, Dict, Any
import numpy as np


def format_fits_header_value(value: float, precision: int = 10) -> float:
    """
    Format a FITS header value to conform to FITS fixed format.
    
    FITS fixed format requires values to be written in a specific way.
    High-precision floating point values can cause warnings.
    
    Args:
        value: The numeric value to format
        precision: Number of decimal places (default: 10)
    
    Returns:
        Rounded value suitable for FITS header
    """
    if not isinstance(value, (int, float, np.number)):
        return value
    
    # Round to specified precision
    return round(float(value), precision)


def fix_cdelt_in_header(header: fits.Header) -> fits.Header:
    """
    Fix CDELT1 and CDELT2 values in FITS header to conform to FITS format.
    
    Rounds CDELT values to reasonable precision (10 decimal places).
    This prevents CASA warnings about non-conforming FITS format.
    
    Args:
        header: FITS header to fix
    
    Returns:
        Modified header (modifies in place, but returns for convenience)
    """
    for key in ['CDELT1', 'CDELT2']:
        if key in header:
            original_value = header[key]
            formatted_value = format_fits_header_value(original_value, precision=10)
            header[key] = formatted_value
    
    return header


def create_fits_hdu(
    data: np.ndarray,
    header: Optional[fits.Header] = None,
    fix_cdelt: bool = True
) -> fits.PrimaryHDU:
    """
    Create a FITS PrimaryHDU with properly formatted header.
    
    Args:
        data: Image data array
        header: Optional FITS header (will be created if None)
        fix_cdelt: If True, fix CDELT values in header (default: True)
    
    Returns:
        PrimaryHDU with properly formatted header
    """
    if header is None:
        header = fits.Header()
    
    if fix_cdelt:
        header = fix_cdelt_in_header(header)
    
    return fits.PrimaryHDU(data=data, header=header)


def write_fits(
    filename: str,
    data: np.ndarray,
    header: Optional[fits.Header] = None,
    overwrite: bool = False,
    fix_cdelt: bool = True
) -> None:
    """
    Write FITS file with properly formatted header.
    
    Args:
        filename: Output FITS filename
        data: Image data array
        header: Optional FITS header
        overwrite: Overwrite existing file (default: False)
        fix_cdelt: If True, fix CDELT values in header (default: True)
    """
    hdu = create_fits_hdu(data, header, fix_cdelt=fix_cdelt)
    hdu.writeto(filename, overwrite=overwrite)

