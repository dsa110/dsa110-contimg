#!/opt/miniforge/envs/casa6/bin/python
"""
Helper script to lookup calibrator coordinates from catalog and register them.

Usage:
    python3 -m dsa110_contimg.conversion.streaming.lookup_and_register_calibrator 0834+555
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dsa110_contimg.calibration.catalogs import get_calibrator_radec, load_vla_catalog
from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Lookup calibrator coordinates and register for bandpass calibration"
    )
    parser.add_argument(
        "calibrator_name",
        help="Calibrator name (e.g., '0834+555')",
    )
    parser.add_argument(
        "--ra-deg",
        type=float,
        help="RA in degrees (if not provided, will lookup from catalog)",
    )
    parser.add_argument(
        "--dec-deg",
        type=float,
        help="Dec in degrees (if not provided, will lookup from catalog)",
    )
    parser.add_argument(
        "--products-db",
        type=Path,
        default=Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3")),
        help="Path to products database",
    )
    parser.add_argument(
        "--registry-db",
        type=Path,
        default=Path(os.getenv("CAL_REGISTRY_DB", "state/db/cal_registry.sqlite3")),
        help="Path to calibration registry database",
    )
    parser.add_argument(
        "--ms-dir",
        type=Path,
        default=Path(os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/raw/ms")),
        help="Directory containing MS files",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path(os.getenv("CONTIMG_IMAGES_DIR", "/stage/dsa110-contimg/images")),
        help="Directory for images",
    )
    parser.add_argument(
        "--mosaic-dir",
        type=Path,
        default=Path(os.getenv("CONTIMG_MOSAIC_DIR", "/stage/dsa110-contimg/mosaics")),
        help="Directory for mosaics",
    )
    parser.add_argument(
        "--dec-tolerance",
        type=float,
        default=5.0,
        help="Dec tolerance in degrees (default: 5.0)",
    )

    args = parser.parse_args()

    # Validate calibrator name
    from dsa110_contimg.utils.naming import validate_calibrator_name

    is_valid, error = validate_calibrator_name(args.calibrator_name)
    if not is_valid:
        logger.error(f"Invalid calibrator name: {error}")
        return 1

    # Lookup coordinates if not provided
    if args.ra_deg is None or args.dec_deg is None:
        logger.info(f"Looking up coordinates for '{args.calibrator_name}' in catalog...")
        try:
            catalog = load_vla_catalog()
            ra_deg, dec_deg = get_calibrator_radec(catalog, args.calibrator_name)
            logger.info(f"Found in catalog: RA={ra_deg:.6f}°, Dec={dec_deg:.6f}°")
        except Exception as e:
            logger.error(f"Failed to lookup calibrator: {e}")
            logger.error("Please provide --ra-deg and --dec-deg manually")
            return 1
    else:
        ra_deg = args.ra_deg
        dec_deg = args.dec_deg
        logger.info(f"Using provided coordinates: RA={ra_deg:.6f}°, Dec={dec_deg:.6f}°")

    # Ensure databases exist
    args.products_db.parent.mkdir(parents=True, exist_ok=True)
    args.registry_db.parent.mkdir(parents=True, exist_ok=True)

    # Initialize manager and register
    logger.info("Registering bandpass calibrator...")
    manager = StreamingMosaicManager(
        products_db_path=args.products_db,
        registry_db_path=args.registry_db,
        ms_output_dir=args.ms_dir,
        images_dir=args.images_dir,
        mosaic_output_dir=args.mosaic_dir,
    )

    manager.register_bandpass_calibrator(
        calibrator_name=args.calibrator_name,
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        dec_tolerance=args.dec_tolerance,
        registered_by="lookup_and_register_calibrator",
    )

    logger.info(":check_mark: Calibrator registered successfully!")
    logger.info(f"  Name: {args.calibrator_name}")
    logger.info(f"  RA: {ra_deg:.6f}°")
    logger.info(f"  Dec: {dec_deg:.6f}°")
    logger.info(
        f"  Dec range: [{dec_deg - args.dec_tolerance:.2f}°, {dec_deg + args.dec_tolerance:.2f}°]"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
