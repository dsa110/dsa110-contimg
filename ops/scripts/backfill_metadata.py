#!/usr/bin/env python3
"""
Backfill missing metadata in images and ms_index tables.
"""
import logging
import sqlite3
import sys
from pathlib import Path

from astropy.io import fits

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DB_PATH = "/data/dsa110-contimg/state/products.sqlite3"
IMAGES_DIR = Path("/stage/dsa110-contimg/images")
MS_DIR = Path("/stage/dsa110-contimg/ms")


def backfill_images():
    """Backfill missing metadata for images."""
    if not Path(DB_PATH).exists():
        logger.error(f"Database not found: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get images with missing metadata
    cursor.execute(
        """
        SELECT id, filepath FROM images 
        WHERE name IS NULL OR ra_deg IS NULL OR dec_deg IS NULL
    """
    )

    rows = cursor.fetchall()
    logger.info(f"Found {len(rows)} images with missing metadata")

    updated = 0
    errors = 0

    for image_id, filepath in rows:
        filepath = Path(filepath)
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            continue

        try:
            # Extract metadata from FITS header
            with fits.open(filepath) as hdul:
                header = hdul[0].header

                name = filepath.name
                ra_deg = header.get("CRVAL1")
                dec_deg = header.get("CRVAL2")

                # Determine type
                if "pbcor" in name.lower():
                    img_type = "pbcor"
                elif "pb.fits" in name.lower():
                    img_type = "pb"
                elif "residual" in name.lower():
                    img_type = "residual"
                elif "image" in name.lower():
                    img_type = "image"
                else:
                    img_type = "unknown"

                # Update database
                cursor.execute(
                    """
                    UPDATE images 
                    SET name = ?, type = ?, ra_deg = ?, dec_deg = ?
                    WHERE id = ?
                """,
                    (name, img_type, ra_deg, dec_deg, image_id),
                )

                logger.info(f"Updated image {image_id}: {name} (RA={ra_deg}, Dec={dec_deg})")
                updated += 1

        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    logger.info(f"Images metadata backfill complete: {updated} updated, {errors} errors")
    return errors == 0


def backfill_ms():
    """Backfill missing metadata for measurement sets."""
    if not Path(DB_PATH).exists():
        logger.error(f"Database not found: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get MS entries with missing metadata
    cursor.execute(
        """
        SELECT id, filepath FROM ms_index 
        WHERE name IS NULL OR scan_id IS NULL
    """
    )

    rows = cursor.fetchall()
    logger.info(f"Found {len(rows)} MS with missing metadata")

    updated = 0
    errors = 0

    for ms_id, filepath in rows:
        filepath = Path(filepath)
        if not filepath.exists():
            logger.warning(f"MS not found: {filepath}")
            continue

        try:
            # For now, just extract name from filepath
            # Full MS table reading requires casacore which may not be available
            name = filepath.name

            # Try to extract scan ID from filename
            # Expected format: YYYYMMDD_HHMMSS.ms or similar
            scan_id = None
            if "_" in name:
                parts = name.split("_")
                if len(parts) >= 2:
                    scan_id = f"{parts[0]}_{parts[1].replace('.ms', '')}"

            # Update database
            cursor.execute(
                """
                UPDATE ms_index 
                SET name = ?, scan_id = ?
                WHERE id = ?
            """,
                (name, scan_id, ms_id),
            )

            logger.info(f"Updated MS {ms_id}: {name} (scan_id={scan_id})")
            updated += 1

        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    logger.info(f"MS metadata backfill complete: {updated} updated, {errors} errors")
    return errors == 0


if __name__ == "__main__":
    logger.info("Starting metadata backfill...")

    images_ok = backfill_images()
    ms_ok = backfill_ms()

    if images_ok and ms_ok:
        logger.info("Metadata backfill completed successfully")
        sys.exit(0)
    else:
        logger.error("Metadata backfill completed with errors")
        sys.exit(1)
