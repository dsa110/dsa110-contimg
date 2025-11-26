#!/usr/bin/env python
"""Run astrometric calibration on existing mosaics.

This script processes existing mosaic FITS files and applies astrometric refinement
using the FIRST catalog as a reference. It can be used for:
- Initial batch processing of existing mosaics
- Re-processing mosaics with updated calibration parameters
- Testing astrometric calibration on specific mosaics

Usage:
    python scripts/run_astrometry_calibration.py [OPTIONS]

Arguments:
    --mosaic-path PATH       Path to single mosaic FITS file to process
    --mosaic-dir PATH        Directory containing mosaic FITS files to process
    --mosaic-id ID           Database mosaic ID to process
    --apply-correction       Apply WCS correction to FITS files (default: False)
    --match-radius ARCSEC    Cross-match radius in arcsec (default: 5.0)
    --min-matches N          Minimum matches required (default: 10)
    --reference-catalog CAT  Reference catalog (default: FIRST)
    --db-path PATH           Database path (default: state/products.sqlite3)
    --max-files N            Maximum files to process (default: unlimited)
    --pattern GLOB           Glob pattern for mosaic files (default: *_mosaic.fits)
    --dry-run                Show what would be processed without doing it
    --verbose                Enable verbose logging

Examples:
    # Process single mosaic (test mode, no WCS correction)
    python scripts/run_astrometry_calibration.py --mosaic-path mosaic_001.fits

    # Process single mosaic and apply WCS correction
    python scripts/run_astrometry_calibration.py \\
        --mosaic-path mosaic_001.fits \\
        --apply-correction

    # Process all mosaics in directory (test mode)
    python scripts/run_astrometry_calibration.py \\
        --mosaic-dir /data/mosaics \\
        --pattern "*_15min_mosaic.fits"

    # Batch process with correction applied
    python scripts/run_astrometry_calibration.py \\
        --mosaic-dir /data/mosaics \\
        --apply-correction \\
        --max-files 100

    # Process by database ID
    python scripts/run_astrometry_calibration.py \\
        --mosaic-id 12345 \\
        --apply-correction

    # Dry run to see what would be processed
    python scripts/run_astrometry_calibration.py \\
        --mosaic-dir /data/mosaics \\
        --dry-run

Exit codes:
    0: Success
    1: Error during processing
    2: No mosaics found to process
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src" / "dsa110_contimg" / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))
else:
    # Try alternative path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from dsa110_contimg.mosaic.astrometric_integration import apply_astrometric_refinement
except ImportError as e:
    print(f"ERROR: Could not import Phase 3 modules: {e}")
    print("Please ensure you are in the dsa110-contimg environment")
    print(f"Search paths tried: {sys.path[:3]}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_mosaic_id_from_db(db_path: Path, fits_path: Path) -> Optional[int]:
    """Get mosaic ID from database by FITS path.

    Args:
        db_path: Database path
        fits_path: FITS file path

    Returns:
        Mosaic ID if found, None otherwise
    """
    try:
        conn = sqlite3.connect(str(db_path), timeout=60.0)
        cursor = conn.cursor()

        # Query products table
        cursor.execute(
            "SELECT id FROM products WHERE filepath = ? AND type = 'mosaic'", (str(fits_path),)
        )

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    except sqlite3.Error as e:
        logger.warning(f"Database query failed: {e}")
        return None


def get_mosaic_path_from_id(db_path: Path, mosaic_id: int) -> Optional[Path]:
    """Get FITS path from database by mosaic ID.

    Args:
        db_path: Database path
        mosaic_id: Mosaic ID

    Returns:
        FITS path if found, None otherwise
    """
    try:
        conn = sqlite3.connect(str(db_path), timeout=60.0)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT filepath FROM products WHERE id = ? AND type = 'mosaic'", (mosaic_id,)
        )

        result = cursor.fetchone()
        conn.close()

        return Path(result[0]) if result else None

    except sqlite3.Error as e:
        logger.error(f"Database query failed: {e}")
        return None


def find_mosaic_files(
    mosaic_dir: Path, pattern: str = "*_mosaic.fits", max_files: Optional[int] = None
) -> List[Path]:
    """Find mosaic FITS files in directory.

    Args:
        mosaic_dir: Directory to search
        pattern: Glob pattern for files
        max_files: Maximum files to return

    Returns:
        List of FITS file paths
    """
    if not mosaic_dir.exists():
        logger.error(f"Directory not found: {mosaic_dir}")
        return []

    files = sorted(mosaic_dir.glob(pattern))

    if max_files:
        files = files[:max_files]

    return files


def process_mosaic(
    fits_path: Path,
    mosaic_id: Optional[int],
    reference_catalog: str,
    match_radius_arcsec: float,
    min_matches: int,
    apply_correction: bool,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Process single mosaic for astrometric calibration.

    Args:
        fits_path: Path to mosaic FITS file
        mosaic_id: Optional mosaic database ID
        reference_catalog: Reference catalog name
        match_radius_arcsec: Cross-match radius
        min_matches: Minimum required matches
        apply_correction: Apply WCS correction
        dry_run: If True, don't actually process

    Returns:
        Result dictionary with status and metrics
    """
    result = {"fits_path": str(fits_path), "mosaic_id": mosaic_id, "success": False, "error": None}

    if dry_run:
        logger.info(f"[DRY RUN] Would process: {fits_path}")
        result["success"] = True
        return result

    if not fits_path.exists():
        result["error"] = "File not found"
        logger.error(f"File not found: {fits_path}")
        return result

    logger.info(f"Processing: {fits_path}")
    logger.info(f"  Mosaic ID: {mosaic_id if mosaic_id else 'None'}")
    logger.info(f"  Reference catalog: {reference_catalog}")
    logger.info(f'  Match radius: {match_radius_arcsec}"')
    logger.info(f"  Min matches: {min_matches}")
    logger.info(f"  Apply correction: {apply_correction}")

    try:
        # Run astrometric refinement
        astrometry_result = apply_astrometric_refinement(
            mosaic_fits_path=str(fits_path),
            mosaic_id=mosaic_id,
            reference_catalog=reference_catalog,
            match_radius_arcsec=match_radius_arcsec,
            min_matches=min_matches,
            apply_correction=apply_correction,
        )

        if astrometry_result:
            result["success"] = True
            result["n_matches"] = astrometry_result.get("n_matches")
            result["ra_offset_mas"] = astrometry_result.get("ra_offset_mas")
            result["dec_offset_mas"] = astrometry_result.get("dec_offset_mas")
            result["rms_residual_mas"] = astrometry_result.get("rms_residual_mas")
            result["solution_id"] = astrometry_result.get("solution_id")

            logger.info(f"✓ Success:")
            logger.info(f"    Matches: {result['n_matches']}")
            logger.info(f"    RA offset: {result['ra_offset_mas']:.1f} mas")
            logger.info(f"    Dec offset: {result['dec_offset_mas']:.1f} mas")
            logger.info(f"    RMS residual: {result['rms_residual_mas']:.1f} mas")

            if apply_correction:
                logger.info(f"    WCS correction applied to {fits_path}")
        else:
            result["error"] = "Insufficient matches or processing failed"
            logger.warning(f"✗ Failed: {result['error']}")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"✗ Error processing {fits_path}: {e}")

    return result


def run_batch_calibration(
    mosaic_paths: List[Path],
    db_path: Path,
    reference_catalog: str,
    match_radius_arcsec: float,
    min_matches: int,
    apply_correction: bool,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Run astrometric calibration on multiple mosaics.

    Args:
        mosaic_paths: List of FITS file paths
        db_path: Database path
        reference_catalog: Reference catalog
        match_radius_arcsec: Match radius
        min_matches: Minimum matches
        apply_correction: Apply corrections
        dry_run: Dry run mode

    Returns:
        Summary statistics dictionary
    """
    summary = {
        "total": len(mosaic_paths),
        "success": 0,
        "failed": 0,
        "mean_rms_mas": None,
        "results": [],
    }

    logger.info(f"Processing {len(mosaic_paths)} mosaics...")

    rms_values = []

    for i, fits_path in enumerate(mosaic_paths, 1):
        logger.info(f"\n[{i}/{len(mosaic_paths)}] {fits_path.name}")

        # Get mosaic ID from database
        mosaic_id = get_mosaic_id_from_db(db_path, fits_path)

        # Process
        result = process_mosaic(
            fits_path=fits_path,
            mosaic_id=mosaic_id,
            reference_catalog=reference_catalog,
            match_radius_arcsec=match_radius_arcsec,
            min_matches=min_matches,
            apply_correction=apply_correction,
            dry_run=dry_run,
        )

        summary["results"].append(result)

        if result["success"]:
            summary["success"] += 1
            if result.get("rms_residual_mas"):
                rms_values.append(result["rms_residual_mas"])
        else:
            summary["failed"] += 1

    # Calculate mean RMS
    if rms_values:
        summary["mean_rms_mas"] = sum(rms_values) / len(rms_values)

    return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run astrometric calibration on mosaics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--mosaic-path", type=Path, help="Path to single mosaic FITS file")
    input_group.add_argument("--mosaic-dir", type=Path, help="Directory containing mosaic files")
    input_group.add_argument("--mosaic-id", type=int, help="Database mosaic ID to process")

    # Processing options
    parser.add_argument(
        "--apply-correction", action="store_true", help="Apply WCS correction to FITS files"
    )
    parser.add_argument(
        "--match-radius",
        type=float,
        default=5.0,
        help="Cross-match radius in arcsec (default: 5.0)",
    )
    parser.add_argument(
        "--min-matches", type=int, default=10, help="Minimum matches required (default: 10)"
    )
    parser.add_argument(
        "--reference-catalog", default="FIRST", help="Reference catalog (default: FIRST)"
    )

    # Batch options
    parser.add_argument("--max-files", type=int, help="Maximum files to process")
    parser.add_argument(
        "--pattern",
        default="*_mosaic.fits",
        help="Glob pattern for mosaic files (default: *_mosaic.fits)",
    )

    # Database
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("state/products.sqlite3"),
        help="Database path (default: state/products.sqlite3)",
    )

    # Modes
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be processed without doing it"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Build mosaic list
    mosaic_paths = []

    if args.mosaic_path:
        mosaic_paths = [args.mosaic_path]
    elif args.mosaic_dir:
        mosaic_paths = find_mosaic_files(args.mosaic_dir, args.pattern, args.max_files)
    elif args.mosaic_id:
        fits_path = get_mosaic_path_from_id(args.db_path, args.mosaic_id)
        if fits_path:
            mosaic_paths = [fits_path]
        else:
            logger.error(f"Mosaic ID {args.mosaic_id} not found in database")
            return 1

    if not mosaic_paths:
        logger.error("No mosaics found to process")
        return 2

    logger.info(f"Found {len(mosaic_paths)} mosaic(s) to process")

    if args.dry_run:
        logger.info("[DRY RUN MODE - No changes will be made]")

    # Process
    summary = run_batch_calibration(
        mosaic_paths=mosaic_paths,
        db_path=args.db_path,
        reference_catalog=args.reference_catalog,
        match_radius_arcsec=args.match_radius,
        min_matches=args.min_matches,
        apply_correction=args.apply_correction,
        dry_run=args.dry_run,
    )

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total processed: {summary['total']}")
    logger.info(f"Success: {summary['success']}")
    logger.info(f"Failed: {summary['failed']}")

    if summary["mean_rms_mas"]:
        logger.info(f"Mean RMS residual: {summary['mean_rms_mas']:.1f} mas")

    if summary["failed"] > 0:
        logger.info("\nFailed mosaics:")
        for result in summary["results"]:
            if not result["success"]:
                logger.info(f"  {result['fits_path']}: {result['error']}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
