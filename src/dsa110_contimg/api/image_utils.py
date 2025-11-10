"""Utilities for image handling in the API layer."""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

LOG = logging.getLogger(__name__)


def resolve_image_path(image_id: str | int, db_path: Optional[Path] = None) -> str:
    """
    Resolve image ID to file path.

    Args:
        image_id: Either an integer (database ID) or string (file path)
        db_path: Optional path to products database (uses config if None)

    Returns:
        Resolved image file path

    Raises:
        HTTPException: If image not found or path invalid
    """
    from dsa110_contimg.api.config import ApiConfig
    from dsa110_contimg.api.data_access import _connect

    # If integer, query database
    if isinstance(image_id, int):
        if db_path is None:
            cfg = ApiConfig()
            db_path = cfg.products_db

        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        with _connect(db_path) as conn:
            row = conn.execute(
                "SELECT path FROM images WHERE id = ?", (image_id,)
            ).fetchone()

            if not row:
                raise HTTPException(
                    status_code=404, detail=f"Image {image_id} not found"
                )

            image_path = row["path"]
    else:
        # String: treat as path (may be URL-encoded)
        image_path = image_id
        # Decode URL encoding if present
        if "%" in image_path:
            from urllib.parse import unquote

            image_path = unquote(image_path)
        # Ensure absolute path
        if not image_path.startswith("/"):
            image_path = f"/{image_path}"

    # Verify path exists
    if not Path(image_path).exists():
        raise HTTPException(
            status_code=404, detail=f"Image file not found: {image_path}"
        )

    return image_path


def get_fits_path(image_path: str) -> Optional[str]:
    """Get FITS file path for an image.

    Checks if FITS file exists, or if CASA image exists and can be converted.

    Args:
        image_path: Path to image (CASA directory or FITS file)

    Returns:
        Path to FITS file if available, None otherwise
    """
    image_path_obj = Path(image_path)

    # If it's already a FITS file, return it
    if image_path.endswith(".fits") and image_path_obj.exists():
        return str(image_path_obj.resolve())

    # Check if corresponding FITS file exists
    fits_path = str(image_path_obj) + ".fits"
    if Path(fits_path).exists():
        return fits_path

    # Check if it's a CASA image directory
    if image_path_obj.is_dir():
        # CASA images are directories, try to export to FITS
        fits_path = str(image_path_obj) + ".fits"
        if convert_casa_to_fits(str(image_path_obj), fits_path):
            return fits_path

    return None


def convert_casa_to_fits(casa_image_path: str, fits_output_path: str) -> bool:
    """Convert a CASA image to FITS format.

    Args:
        casa_image_path: Path to CASA image directory
        fits_output_path: Output FITS file path

    Returns:
        True if conversion successful, False otherwise
    """
    try:
        from casatasks import exportfits  # type: ignore
    except ImportError:
        LOG.warning(
            "casatasks.exportfits not available - cannot convert CASA image to FITS"
        )
        return False

    if not os.path.isdir(casa_image_path):
        LOG.warning(f"CASA image path is not a directory: {casa_image_path}")
        return False

    try:
        exportfits(
            imagename=casa_image_path, fitsimage=fits_output_path, overwrite=True
        )
        LOG.info(f"Converted CASA image to FITS: {fits_output_path}")
        return True
    except Exception as e:
        LOG.error(f"Failed to convert CASA image {casa_image_path} to FITS: {e}")
        return False


def is_casa_image(path: str) -> bool:
    """Check if a path is a CASA image directory.

    Args:
        path: Path to check

    Returns:
        True if path is a CASA image directory
    """
    path_obj = Path(path)
    if not path_obj.is_dir():
        return False

    # CASA images are directories that typically contain image data
    # Check for common CASA image files
    casa_files = ["imageinfo", "table.dat", "table.f0"]
    return any((path_obj / f).exists() for f in casa_files)
