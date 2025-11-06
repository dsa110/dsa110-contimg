#!/usr/bin/env python3
"""
Create synthetic FITS images for SkyView testing.

Generates simple 2D FITS images with Gaussian noise and point sources,
then adds them to the products.sqlite3 database.
"""

import sys
import os
import sqlite3
import time
import random
import numpy as np
from pathlib import Path
from datetime import datetime
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.time import Time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.api.data_access import _connect

PRODUCTS_DB = Path(os.getenv("PIPELINE_PRODUCTS_DB", "/data/dsa110-contimg/state/products.sqlite3"))
IMAGES_DIR = Path("/data/dsa110-contimg/state/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def create_synthetic_fits(
    output_path: Path,
    ra_deg: float = 180.0,
    dec_deg: float = 35.0,
    image_size: int = 512,
    pixel_scale_arcsec: float = 2.0,
    noise_level_jy: float = 0.001,
    n_sources: int = 5,
    source_flux_range_jy: tuple = (0.01, 0.1),
) -> Path:
    """
    Create a synthetic FITS image with point sources and noise.
    
    Args:
        output_path: Path to output FITS file
        ra_deg: Right ascension of image center (degrees)
        dec_deg: Declination of image center (degrees)
        image_size: Image size in pixels (square)
        pixel_scale_arcsec: Pixel scale in arcseconds
        noise_level_jy: RMS noise level in Jy
        n_sources: Number of point sources to add
        source_flux_range_jy: (min, max) flux range for sources in Jy
    
    Returns:
        Path to created FITS file
    """
    # Create WCS
    w = WCS(naxis=2)
    w.wcs.crpix = [image_size / 2, image_size / 2]
    w.wcs.cdelt = [-pixel_scale_arcsec / 3600.0, pixel_scale_arcsec / 3600.0]  # Negative for RA
    w.wcs.crval = [ra_deg, dec_deg]
    w.wcs.ctype = ["RA---SIN", "DEC--SIN"]
    
    # Create image data with noise
    data = np.random.normal(0, noise_level_jy, (image_size, image_size))
    
    # Add point sources
    for _ in range(n_sources):
        # Random position (avoid edges)
        x = random.randint(image_size // 4, 3 * image_size // 4)
        y = random.randint(image_size // 4, 3 * image_size // 4)
        
        # Random flux
        flux_jy = random.uniform(*source_flux_range_jy)
        
        # Add Gaussian source (beam ~10 pixels FWHM)
        beam_fwhm_pix = 10.0
        sigma_pix = beam_fwhm_pix / 2.355
        
        # Create 2D Gaussian
        y_grid, x_grid = np.ogrid[:image_size, :image_size]
        gaussian = flux_jy * np.exp(
            -((x_grid - x) ** 2 + (y_grid - y) ** 2) / (2 * sigma_pix ** 2)
        )
        data += gaussian
    
    # Create FITS HDU
    hdu = fits.PrimaryHDU(data=data, header=w.to_header())
    
    # Add standard FITS keywords
    hdu.header['BUNIT'] = 'Jy/beam'
    hdu.header['BTYPE'] = 'Intensity'
    hdu.header['BSCALE'] = 1.0
    hdu.header['BZERO'] = 0.0
    hdu.header['BMAJ'] = beam_fwhm_pix * pixel_scale_arcsec / 3600.0  # degrees
    hdu.header['BMIN'] = beam_fwhm_pix * pixel_scale_arcsec / 3600.0
    hdu.header['BPA'] = 0.0
    hdu.header['DATE-OBS'] = Time.now().isot
    hdu.header['OBJECT'] = 'Synthetic Test Image'
    
    # Write FITS file
    hdu.writeto(output_path, overwrite=True)
    
    return output_path


def add_images_to_database(
    db_path: Path,
    image_paths: list[tuple[Path, str, bool, float, float]],
) -> None:
    """
    Add images to the products database.
    
    Args:
        db_path: Path to products.sqlite3 database
        image_paths: List of (path, type, pbcor, noise_jy, beam_major_arcsec) tuples
    """
    with _connect(db_path) as conn:
        cur = conn.cursor()
        
        now = time.time()
        
        for img_path, img_type, pbcor, noise_jy, beam_major in image_paths:
            # Extract MS path from image path (simulated)
            ms_name = img_path.stem.replace('.image', '').replace('.pbcor', '').replace('.pb', '')
            ms_path = f"/data/dsa110-contimg/state/ms/{ms_name}.ms"
            
            cur.execute("""
                INSERT INTO images (
                    path, ms_path, created_at, type, beam_major_arcsec,
                    noise_jy, pbcor
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(img_path),
                ms_path,
                now,
                img_type,
                beam_major,
                noise_jy,
                1 if pbcor else 0,
            ))
        
        conn.commit()


def main():
    """Generate synthetic images and add to database."""
    print("=" * 60)
    print("Synthetic Image Generation")
    print("=" * 60)
    print(f"Database: {PRODUCTS_DB}")
    print(f"Images directory: {IMAGES_DIR}")
    print()
    
    # Check database exists
    if not PRODUCTS_DB.exists():
        print(f"✗ Database not found: {PRODUCTS_DB}")
        print("  Run: python scripts/init_databases.py")
        return 1
    
    # Generate synthetic images
    print("Generating synthetic FITS images...")
    
    image_configs = [
        # (name_suffix, type, pbcor, ra, dec, noise_jy, beam_arcsec)
        ("2025-01-15T12:00:00.img.image", "5min", False, 180.0, 35.0, 0.001, 12.5),
        ("2025-01-15T12:00:00.img.pb", "5min", False, 180.0, 35.0, 0.0, 12.5),
        ("2025-01-15T12:00:00.img.image.pbcor", "5min", True, 180.0, 35.0, 0.001, 12.5),
        ("2025-01-15T12:05:00.img.image", "5min", False, 180.1, 35.1, 0.0012, 12.8),
        ("2025-01-15T12:05:00.img.image.pbcor", "5min", True, 180.1, 35.1, 0.0012, 12.8),
        ("2025-01-15T12:10:00.img.image", "5min", False, 180.2, 35.2, 0.0009, 12.3),
        ("2025-01-15T12:10:00.img.image.pbcor", "5min", True, 180.2, 35.2, 0.0009, 12.3),
        ("2025-01-15T12:15:00.img.image", "5min", False, 180.3, 35.3, 0.0011, 12.6),
        ("2025-01-15T12:15:00.img.image.pbcor", "5min", True, 180.3, 35.3, 0.0011, 12.6),
        ("2025-01-15T12:20:00.img.image", "5min", False, 180.4, 35.4, 0.001, 12.4),
        ("2025-01-15T12:20:00.img.image.pbcor", "5min", True, 180.4, 35.4, 0.001, 12.4),
    ]
    
    created_images = []
    
    for name, img_type, pbcor, ra, dec, noise, beam in image_configs:
        output_path = IMAGES_DIR / f"{name}.fits"
        
        print(f"  Creating: {output_path.name}")
        
        try:
            create_synthetic_fits(
                output_path=output_path,
                ra_deg=ra,
                dec_deg=dec,
                image_size=512,
                pixel_scale_arcsec=2.0,
                noise_level_jy=noise,
                n_sources=random.randint(3, 8),
                source_flux_range_jy=(0.005, 0.05),
            )
            
            created_images.append((output_path, img_type, pbcor, noise, beam))
            print(f"    ✓ Created {output_path.name}")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Add to database
    if created_images:
        print(f"\nAdding {len(created_images)} images to database...")
        try:
            add_images_to_database(PRODUCTS_DB, created_images)
            print(f"  ✓ Added {len(created_images)} images to database")
        except Exception as e:
            print(f"  ✗ Failed to add to database: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # Verify
    print("\nVerifying database entries...")
    with _connect(PRODUCTS_DB) as conn:
        cur = conn.execute("SELECT COUNT(*) FROM images")
        count = cur.fetchone()[0]
        print(f"  ✓ Total images in database: {count}")
    
    print("\n" + "=" * 60)
    print("✓ Synthetic image generation complete!")
    print("=" * 60)
    print(f"\nImages created in: {IMAGES_DIR}")
    print(f"Access SkyView at: http://localhost:5173/skyview")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

