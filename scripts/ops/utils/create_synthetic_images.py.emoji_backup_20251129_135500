#!/opt/miniforge/envs/casa6/bin/python
"""
Create synthetic FITS images for SkyView testing.

Generates simple 2D FITS images with Gaussian noise and point sources,
then adds them to the products.sqlite3 database.
"""

import os
import random
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS

from dsa110_contimg.api.data_access import _connect
from dsa110_contimg.simulation.synthetic_fits import create_synthetic_fits

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


PRODUCTS_DB = Path(os.getenv("PIPELINE_PRODUCTS_DB", "/data/dsa110-contimg/state/db/products.sqlite3"))
# Use synthetic data directory for test/synthetic images
SYNTHETIC_DIR = Path(os.getenv("PIPELINE_SYNTHETIC_DIR", "/data/dsa110-contimg/state/synth"))
IMAGES_DIR = SYNTHETIC_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


# create_synthetic_fits is now imported from dsa110_contimg.simulation.synthetic_fits


def add_images_to_database(
    db_path: Path,
    image_paths: list[tuple[Path, str, bool, float, float]],
) -> None:
    """
    Add images to the products database with automatic synthetic tagging.

    Args:
        db_path: Path to products.sqlite3 database
        image_paths: List of (path, type, pbcor, noise_jy, beam_major_arcsec) tuples
    """
    with _connect(db_path) as conn:
        cur = conn.cursor()

        now = time.time()

        for img_path, img_type, pbcor, noise_jy, beam_major in image_paths:
            # Extract MS path from image path (simulated)
            # Use synthetic MS directory
            ms_name = img_path.stem.replace(".image", "").replace(".pbcor", "").replace(".pb", "")
            ms_path = str(SYNTHETIC_DIR / "ms" / f"{ms_name}.ms")

            # Insert image record
            cur.execute(
                """
                INSERT INTO images (
                    path, ms_path, created_at, type, beam_major_arcsec,
                    noise_jy, pbcor
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(img_path),
                    ms_path,
                    now,
                    img_type,
                    beam_major,
                    noise_jy,
                    1 if pbcor else 0,
                ),
            )

            # Get the inserted image ID
            image_id = cur.lastrowid

            # Automatically tag as synthetic
            cur.execute(
                """
                INSERT OR IGNORE INTO data_tags (data_id, tag, created_at)
                VALUES (?, ?, ?)
            """,
                (str(image_id), "synthetic", now),
            )

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
        print(f":cross: Database not found: {PRODUCTS_DB}")
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
            print(f"    :check: Created {output_path.name}")
        except Exception as e:
            print(f"    :cross: Failed: {e}")
            import traceback

            traceback.print_exc()

    # Add to database
    if created_images:
        print(f"\nAdding {len(created_images)} images to database...")
        try:
            add_images_to_database(PRODUCTS_DB, created_images)
            print(f"  :check: Added {len(created_images)} images to database")
        except Exception as e:
            print(f"  :cross: Failed to add to database: {e}")
            import traceback

            traceback.print_exc()
            return 1

    # Verify
    print("\nVerifying database entries...")
    with _connect(PRODUCTS_DB) as conn:
        cur = conn.execute("SELECT COUNT(*) FROM images")
        count = cur.fetchone()[0]
        print(f"  :check: Total images in database: {count}")

    print("\n" + "=" * 60)
    print(":check: Synthetic image generation complete!")
    print("=" * 60)
    print(f"\nImages created in: {IMAGES_DIR}")
    print(f"Access SkyView at: http://localhost:5173/skyview")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
