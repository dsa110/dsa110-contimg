"""Unified Quality Assessment CLI for DSA-110 pipeline.

This CLI consolidates QA functionality from across the pipeline:
- Calibration QA (caltables, delay verification)
- Image QA (MS validation, visibility statistics)
- Mosaic QA (tile quality, consistency checks)
- Comprehensive QA reports
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dsa110_contimg.utils.cli_helpers import (
    add_common_logging_args,
    configure_logging_from_args,
    setup_casa_environment,
)

# Set up CASA environment
setup_casa_environment()

logger = logging.getLogger(__name__)


def cmd_calibration(args: argparse.Namespace) -> int:
    """Run calibration QA on a Measurement Set."""
    from dsa110_contimg.qa.calibration_quality import validate_caltable_quality
    from dsa110_contimg.qa.casa_ms_qa import (
        flag_summary,
        generate_plots,
        inventory_and_provenance,
        listobs_dump,
        structural_validation,
        vis_statistics,
    )

    ms_path = Path(args.ms_path)
    if not ms_path.exists():
        logger.error(f"MS path does not exist: {ms_path}")
        return 1

    qa_output_dir = Path(args.output_dir) if args.output_dir else ms_path.parent / "qa"
    qa_output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Running calibration QA on {ms_path}")

    try:
        # MS structural validation
        logger.info("Running structural validation...")
        struct_results = structural_validation(str(ms_path))
        struct_file = qa_output_dir / "structural_validation.json"
        with open(struct_file, "w") as f:
            json.dump(struct_results, f, indent=2)
        logger.info(f"Structural validation results: {struct_file}")

        # Inventory and provenance
        logger.info("Generating inventory and provenance...")
        inv_file = inventory_and_provenance(str(ms_path), str(qa_output_dir))
        logger.info(f"Inventory: {inv_file}")

        # Listobs dump
        logger.info("Running listobs...")
        listobs_file = listobs_dump(str(ms_path), str(qa_output_dir))
        logger.info(f"Listobs output: {listobs_file}")

        # Flag summary
        logger.info("Generating flag summary...")
        flag_file = flag_summary(str(ms_path), str(qa_output_dir))
        logger.info(f"Flag summary: {flag_file}")

        # Visibility statistics
        logger.info("Computing visibility statistics...")
        vis_stats = vis_statistics(str(ms_path), str(qa_output_dir))
        logger.info(f"Visibility statistics: {vis_stats}")

        # Generate plots
        if not args.skip_plots:
            logger.info("Generating visibility plots...")
            plot_files = generate_plots(str(ms_path), str(qa_output_dir))
            logger.info(f"Generated {len(plot_files)} plots")

        # Calibration table QA (if caltables exist)
        if args.check_caltables:
            logger.info("Checking calibration tables...")
            # Look for caltables in MS directory
            ms_dir = ms_path.parent
            ms_stem = ms_path.stem

            for caltype in ["K", "BP", "G"]:
                caltable_pattern = f"{ms_stem}*.{caltype.lower()}cal"
                import glob

                caltables = glob.glob(str(ms_dir / caltable_pattern))
                for caltable in caltables:
                    try:
                        cal_qa = validate_caltable_quality(caltable)
                        cal_file = qa_output_dir / f"{Path(caltable).stem}_qa.json"
                        with open(cal_file, "w") as f:
                            json.dump(cal_qa.model_dump(), f, indent=2)
                        logger.info(f"Calibration QA for {caltable}: {cal_file}")
                    except Exception as e:
                        logger.warning(f"Failed to validate caltable {caltable}: {e}")

        logger.info(f"Calibration QA complete. Results in: {qa_output_dir}")
        return 0

    except Exception as e:
        logger.exception(f"Calibration QA failed: {e}")
        return 1


def cmd_image(args: argparse.Namespace) -> int:
    """Run image QA on a FITS image."""
    from dsa110_contimg.qa.catalog_validation import validate_flux_scale

    image_path = Path(args.image_path)
    if not image_path.exists():
        logger.error(f"Image path does not exist: {image_path}")
        return 1

    logger.info(f"Running image QA on {image_path}")

    try:
        # Catalog-based flux scale validation
        if args.validate_flux_scale:
            logger.info("Running catalog-based flux scale validation...")
            result = validate_flux_scale(
                image_path=str(image_path),
                catalog=args.catalog or "nvss",
                min_snr=args.min_snr or 5.0,
                flux_range_jy=(args.min_flux or 0.01, args.max_flux or 10.0),
                max_flux_ratio_error=args.max_flux_error or 0.2,
            )

            qa_output_dir = Path(args.output_dir) if args.output_dir else image_path.parent / "qa"
            qa_output_dir.mkdir(parents=True, exist_ok=True)

            result_file = qa_output_dir / f"{image_path.stem}_qa.json"
            with open(result_file, "w") as f:
                from dataclasses import asdict

                json.dump(asdict(result), f, indent=2)

            logger.info(f"Image QA complete. Results: {result_file}")
            logger.info(
                f"  Matched sources: {result.n_matched}\n"
                f"  Flux ratio: {result.mean_flux_ratio:.3f}±{result.rms_flux_ratio:.3f}\n"
                f"  Scale error: {result.flux_scale_error * 100:.1f}%"
            )

            if result.has_issues:
                logger.warning(f"Issues detected: {', '.join(result.issues)}")
                return 1

        return 0

    except Exception as e:
        logger.exception(f"Image QA failed: {e}")
        return 1


def cmd_mosaic(args: argparse.Namespace) -> int:
    """Run mosaic QA on a mosaic."""
    from dsa110_contimg.mosaic.validation import (
        check_calibration_consistency,
        check_primary_beam_consistency,
        validate_tile_quality,
        validate_tiles_consistency,
        verify_astrometric_registration,
    )

    mosaic_id = args.mosaic_id
    logger.info(f"Running mosaic QA on {mosaic_id}")

    try:
        # Query mosaic from database
        from dsa110_contimg.database.products import ensure_products_db

        products_db_path = Path(
            args.products_db or os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3")
        )
        conn = ensure_products_db(products_db_path)

        cursor = conn.execute("SELECT path FROM mosaics WHERE id = ?", (mosaic_id,))
        row = cursor.fetchone()
        if not row:
            logger.error(f"Mosaic {mosaic_id} not found")
            return 1

        mosaic_path = Path(row[0])
        if not mosaic_path.exists():
            logger.error(f"Mosaic path does not exist: {mosaic_path}")
            return 1

        qa_output_dir = Path(args.output_dir) if args.output_dir else mosaic_path.parent / "qa"
        qa_output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        # Tile quality validation
        logger.info("Validating tile quality...")
        try:
            tile_qa = validate_tile_quality(str(mosaic_path))
            results["tile_quality"] = (
                tile_qa.model_dump() if hasattr(tile_qa, "model_dump") else str(tile_qa)
            )
        except Exception as e:
            logger.warning(f"Tile quality validation failed: {e}")
            results["tile_quality"] = {"error": str(e)}

        # Tiles consistency
        logger.info("Checking tiles consistency...")
        try:
            consistency = validate_tiles_consistency(str(mosaic_path))
            results["tiles_consistency"] = (
                consistency.model_dump() if hasattr(consistency, "model_dump") else str(consistency)
            )
        except Exception as e:
            logger.warning(f"Tiles consistency check failed: {e}")
            results["tiles_consistency"] = {"error": str(e)}

        # Astrometric registration
        if args.check_astrometry:
            logger.info("Verifying astrometric registration...")
            try:
                astro = verify_astrometric_registration(str(mosaic_path))
                results["astrometry"] = (
                    astro.model_dump() if hasattr(astro, "model_dump") else str(astro)
                )
            except Exception as e:
                logger.warning(f"Astrometric verification failed: {e}")
                results["astrometry"] = {"error": str(e)}

        # Calibration consistency
        if args.check_calibration:
            logger.info("Checking calibration consistency...")
            try:
                cal_consistency = check_calibration_consistency(str(mosaic_path))
                results["calibration_consistency"] = (
                    cal_consistency.model_dump()
                    if hasattr(cal_consistency, "model_dump")
                    else str(cal_consistency)
                )
            except Exception as e:
                logger.warning(f"Calibration consistency check failed: {e}")
                results["calibration_consistency"] = {"error": str(e)}

        # Primary beam consistency
        if args.check_primary_beam:
            logger.info("Checking primary beam consistency...")
            try:
                pb_consistency = check_primary_beam_consistency(str(mosaic_path))
                results["primary_beam_consistency"] = (
                    pb_consistency.model_dump()
                    if hasattr(pb_consistency, "model_dump")
                    else str(pb_consistency)
                )
            except Exception as e:
                logger.warning(f"Primary beam consistency check failed: {e}")
                results["primary_beam_consistency"] = {"error": str(e)}

        # Write results
        result_file = qa_output_dir / f"{mosaic_id}_qa.json"
        with open(result_file, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Mosaic QA complete. Results: {result_file}")
        return 0

    except Exception as e:
        logger.exception(f"Mosaic QA failed: {e}")
        return 1


def cmd_report(args: argparse.Namespace) -> int:
    """Generate comprehensive QA report for a data product."""
    import os

    data_id = args.data_id
    logger.info(f"Generating comprehensive QA report for {data_id}")

    try:
        from dsa110_contimg.database.data_registry import (
            ensure_data_registry_db,
            get_data,
        )

        products_db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3"))
        registry_conn = ensure_data_registry_db(products_db_path)

        record = get_data(registry_conn, data_id)
        if not record:
            logger.error(f"Data {data_id} not found in registry")
            return 1

        qa_output_dir = (
            Path(args.output_dir) if args.output_dir else Path(record.stage_path).parent / "qa"
        )
        qa_output_dir.mkdir(parents=True, exist_ok=True)

        report = {
            "data_id": data_id,
            "data_type": record.data_type,
            "status": record.status,
            "stage_path": record.stage_path,
            "published_path": record.published_path,
            "qa_results": {},
        }

        # Run appropriate QA based on data type
        if record.data_type == "ms" or record.data_type == "calib_ms":
            # Run calibration QA
            logger.info("Running MS QA...")
            ms_args = argparse.Namespace()
            ms_args.ms_path = record.stage_path
            ms_args.output_dir = str(qa_output_dir)
            ms_args.check_caltables = True
            ms_args.skip_plots = args.skip_plots
            cmd_calibration(ms_args)
            report["qa_results"]["ms_qa"] = "completed"

        elif record.data_type == "image":
            # Run image QA
            logger.info("Running image QA...")
            img_args = argparse.Namespace()
            img_args.image_path = record.stage_path
            img_args.output_dir = str(qa_output_dir)
            img_args.validate_flux_scale = True
            img_args.catalog = args.catalog
            img_args.min_snr = args.min_snr
            img_args.min_flux = args.min_flux
            img_args.max_flux = args.max_flux
            img_args.max_flux_error = args.max_flux_error
            cmd_image(img_args)
            report["qa_results"]["image_qa"] = "completed"

        elif record.data_type == "mosaic":
            # Run mosaic QA
            logger.info("Running mosaic QA...")
            mosaic_args = argparse.Namespace()
            mosaic_args.mosaic_id = data_id
            mosaic_args.products_db = str(products_db_path)
            mosaic_args.output_dir = str(qa_output_dir)
            mosaic_args.check_astrometry = True
            mosaic_args.check_calibration = True
            mosaic_args.check_primary_beam = True
            cmd_mosaic(mosaic_args)
            report["qa_results"]["mosaic_qa"] = "completed"

        # Write comprehensive report
        report_file = qa_output_dir / f"{data_id}_comprehensive_qa.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Comprehensive QA report: {report_file}")
        return 0

    except Exception as e:
        logger.exception(f"QA report generation failed: {e}")
        return 1


def main(argv: list = None) -> int:
    """Main function for unified QA CLI."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=(
            "DSA-110 Unified Quality Assessment CLI\n\n"
            "Consolidated QA functionality for calibration, images, and mosaics.\n\n"
            "Examples:\n"
            "  # Calibration QA on MS\n"
            "  python -m dsa110_contimg.qa.cli calibration \\\n"
            "    --ms-path /stage/ms/observation.ms --output-dir /stage/qa\n\n"
            "  # Image QA\n"
            "  python -m dsa110_contimg.qa.cli image \\\n"
            "    --image-path /stage/images/image.fits --validate-flux-scale\n\n"
            "  # Mosaic QA\n"
            "  python -m dsa110_contimg.qa.cli mosaic \\\n"
            "    --mosaic-id mosaic_2025-11-12_10-00-00\n\n"
            "  # Comprehensive QA report\n"
            "  python -m dsa110_contimg.qa.cli report \\\n"
            "    --data-id mosaic_2025-11-12_10-00-00"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    add_common_logging_args(parser)

    subparsers = parser.add_subparsers(dest="command", required=True, help="QA subcommand")

    # Calibration QA subcommand
    cal_parser = subparsers.add_parser(
        "calibration",
        help="Run calibration QA on a Measurement Set",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cal_parser.add_argument("ms_path", type=str, help="Path to Measurement Set")
    cal_parser.add_argument("--output-dir", type=str, help="Output directory for QA results")
    cal_parser.add_argument(
        "--check-caltables",
        action="store_true",
        help="Also validate calibration tables",
    )
    cal_parser.add_argument("--skip-plots", action="store_true", help="Skip plot generation")
    cal_parser.set_defaults(func=cmd_calibration)

    # Image QA subcommand
    img_parser = subparsers.add_parser(
        "image",
        help="Run image QA on a FITS image",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    img_parser.add_argument("image_path", type=str, help="Path to FITS image")
    img_parser.add_argument("--output-dir", type=str, help="Output directory for QA results")
    img_parser.add_argument(
        "--validate-flux-scale",
        action="store_true",
        help="Run catalog-based flux scale validation",
    )
    img_parser.add_argument("--catalog", type=str, default="nvss", help="Catalog for validation")
    img_parser.add_argument(
        "--min-snr", type=float, default=5.0, help="Minimum SNR for catalog matching"
    )
    img_parser.add_argument(
        "--min-flux", type=float, default=0.01, help="Minimum flux (Jy) for validation"
    )
    img_parser.add_argument(
        "--max-flux", type=float, default=10.0, help="Maximum flux (Jy) for validation"
    )
    img_parser.add_argument(
        "--max-flux-error",
        type=float,
        default=0.2,
        help="Maximum flux ratio error",
    )
    img_parser.set_defaults(func=cmd_image)

    # Mosaic QA subcommand
    mosaic_parser = subparsers.add_parser(
        "mosaic",
        help="Run mosaic QA on a mosaic",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    mosaic_parser.add_argument("mosaic_id", type=str, help="Mosaic ID")
    mosaic_parser.add_argument("--products-db", type=str, help="Path to products database")
    mosaic_parser.add_argument("--output-dir", type=str, help="Output directory for QA results")
    mosaic_parser.add_argument(
        "--check-astrometry",
        action="store_true",
        help="Verify astrometric registration",
    )
    mosaic_parser.add_argument(
        "--check-calibration",
        action="store_true",
        help="Check calibration consistency",
    )
    mosaic_parser.add_argument(
        "--check-primary-beam",
        action="store_true",
        help="Check primary beam consistency",
    )
    mosaic_parser.set_defaults(func=cmd_mosaic)

    # Report subcommand
    report_parser = subparsers.add_parser(
        "report",
        help="Generate comprehensive QA report",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    report_parser.add_argument("data_id", type=str, help="Data instance ID")
    report_parser.add_argument("--output-dir", type=str, help="Output directory for QA results")
    report_parser.add_argument("--skip-plots", action="store_true", help="Skip plot generation")
    report_parser.add_argument(
        "--catalog", type=str, default="nvss", help="Catalog for image validation"
    )
    report_parser.add_argument(
        "--min-snr", type=float, default=5.0, help="Minimum SNR for catalog matching"
    )
    report_parser.add_argument("--min-flux", type=float, default=0.01, help="Minimum flux (Jy)")
    report_parser.add_argument("--max-flux", type=float, default=10.0, help="Maximum flux (Jy)")
    report_parser.add_argument(
        "--max-flux-error",
        type=float,
        default=0.2,
        help="Maximum flux ratio error",
    )
    report_parser.set_defaults(func=cmd_report)

    # Parse arguments
    args = parser.parse_args(argv)

    # Configure logging
    configure_logging_from_args(args)

    # Execute command
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
