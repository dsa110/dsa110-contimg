"""
Product registration with metadata extraction.

This module provides functions to register images and measurement sets
in the database with full metadata extraction from FITS headers.
"""
import sqlite3
from pathlib import Path
from astropy.io import fits
import logging
import time

logger = logging.getLogger(__name__)

def register_image_with_metadata(filepath: str, ms_path: str = "unknown", db_path: str = None):
    """
    Register an image in the database with full metadata extraction.
    
    Args:
        filepath: Path to FITS image
        ms_path: Path to parent MS (if known)
        db_path: Path to products database (default: state/products.sqlite3)
        
    Returns:
        int: Image ID if successful, None otherwise
    """
    if db_path is None:
        db_path = "/data/dsa110-contimg/state/products.sqlite3"
    
    filepath = Path(filepath)
    if not filepath.exists():
        logger.error(f"Image not found: {filepath}")
        return None
    
    try:
        # Extract metadata from FITS header
        with fits.open(filepath) as hdul:
            header = hdul[0].header
            
            ra = header.get("CRVAL1")
            dec = header.get("CRVAL2")
            noise_jy = header.get("RMS") or header.get("NOISE")
            freq_hz = header.get("CRVAL3")
            freq_ghz = freq_hz / 1e9 if freq_hz else None
            beam_maj = header.get("BMAJ")
            beam_min = header.get("BMIN")
            beam_pa = header.get("BPA")
            
            # Convert beam from degrees to arcseconds
            beam_maj_arcsec = beam_maj * 3600 if beam_maj else None
            beam_min_arcsec = beam_min * 3600 if beam_min else None
            
            img_type = determine_image_type(filepath.name)
            pbcor = 1 if 'pbcor' in filepath.name.lower() else 0
        
        # Insert into database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO images 
            (path, ms_path, created_at, type, beam_major_arcsec, beam_minor_arcsec,
             beam_pa_deg, noise_jy, pbcor, center_ra_deg, center_dec_deg, freq_ghz)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(filepath),
            ms_path,
            time.time(),
            img_type,
            beam_maj_arcsec,
            beam_min_arcsec,
            beam_pa,
            noise_jy,
            pbcor,
            ra,
            dec,
            freq_ghz,
        ))
        
        image_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Registered image {image_id}: {filepath.name}")
        return image_id
        
    except Exception as e:
        logger.error(f"Error registering image {filepath}: {e}")
        import traceback
        traceback.print_exc()
        return None

def determine_image_type(filename: str) -> str:
    """Determine image type from filename."""
    filename_lower = filename.lower()
    
    if 'pbcor' in filename_lower:
        return 'pbcor'
    elif '.pb.' in filename_lower or 'pb.fits' in filename_lower:
        return 'pb'
    elif 'residual' in filename_lower:
        return 'residual'
    elif 'model' in filename_lower:
        return 'model'
    elif 'psf' in filename_lower:
        return 'psf'
    elif 'image' in filename_lower:
        return 'image'
    else:
        return 'unknown'
