"""Unified command-line interface for UVH5 to MS conversion."""

import argparse
import sys

from dsa110_contimg.utils.cli_helpers import (
    setup_casa_environment,
    add_common_logging_args,
    configure_logging_from_args,
)

from . import uvh5_to_ms
from .strategies import hdf5_orchestrator  # noqa: E402

# Set up CASA environment
setup_casa_environment()


def main(argv: list = None) -> int:
    """Main function for the unified conversion CLI."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="DSA-110 Continuum Imaging Conversion CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Add common logging arguments
    add_common_logging_args(parser)
    
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Subcommand to run"
    )

    # Subparser for the 'single' command
    single_parser = subparsers.add_parser(
        "single",
        help="Convert a single UVH5 file or a directory of loose files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    uvh5_to_ms.add_args(single_parser)
    single_parser.set_defaults(func=uvh5_to_ms.main)

    # Subparser for the 'groups' command
    groups_parser = subparsers.add_parser(
        "groups",
        help="Discover and convert complete subband groups in a time window.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    hdf5_orchestrator.add_args(groups_parser)
    groups_parser.set_defaults(func=hdf5_orchestrator.main)

    # Subparser for the 'validate' command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate UVH5 files without converting.",
        description=(
            "Validate HDF5 file structure, readability, and basic metadata.\n"
            "Useful for quick checks before committing to conversion.\n\n"
            "Example:\n"
            "  python -m dsa110_contimg.conversion.cli validate \\\n"
            "    --input-dir /data/incoming \\\n"
            "    --start-time '2025-10-30 10:00:00' \\\n"
            "    --end-time '2025-10-30 11:00:00' \\\n"
            "    --validate-calibrator 0834+555"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    validate_parser.add_argument("--input-dir", required=True, help="Directory containing UVH5 files")
    validate_parser.add_argument("--start-time", help="Start time (YYYY-MM-DD HH:MM:SS)")
    validate_parser.add_argument("--end-time", help="End time (YYYY-MM-DD HH:MM:SS)")
    validate_parser.add_argument("--validate-calibrator", type=str,
                                help="Validate calibrator transit (e.g., '0834+555')")
    validate_parser.add_argument("--dec-tolerance-deg", type=float, default=2.0,
                                help="Declination tolerance for calibrator matching (default: 2.0)")
    validate_parser.add_argument("--window-minutes", type=int, default=60,
                                help="Transit search window in minutes (default: 60)")
    validate_parser.add_argument("--max-days-back", type=int, default=30,
                                help="Maximum days to search back (default: 30)")
    
    # Subparser for the 'verify-ms' command
    verify_ms_parser = subparsers.add_parser(
        "verify-ms",
        help="Verify MS structure and quality.",
        description=(
            "Quick verification of MS file structure, columns, and basic quality metrics.\n\n"
            "Example:\n"
            "  python -m dsa110_contimg.conversion.cli verify-ms \\\n"
            "    --ms /data/ms/test.ms \\\n"
            "    --check-imaging-columns"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    verify_ms_parser.add_argument("--ms", required=True, help="Path to MS file")
    verify_ms_parser.add_argument("--check-imaging-columns", action="store_true",
                                  help="Verify imaging columns (CORRECTED_DATA, MODEL_DATA, etc.)")
    verify_ms_parser.add_argument("--check-field-structure", action="store_true",
                                  help="Verify FIELD table structure")
    verify_ms_parser.add_argument("--check-spw-structure", action="store_true",
                                  help="Verify SPECTRAL_WINDOW table structure")
    
    # Subparser for the 'smoke-test' command
    smoke_test_parser = subparsers.add_parser(
        "smoke-test",
        help="Quick end-to-end smoke test (< 1 minute).",
        description=(
            "Generate minimal synthetic data and convert to MS to verify\n"
            "the conversion pipeline is working. Fast sanity check.\n\n"
            "Example:\n"
            "  python -m dsa110_contimg.conversion.cli smoke-test \\\n"
            "    --output /tmp/smoke-test.ms"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    smoke_test_parser.add_argument("--output", default="/tmp/smoke-test.ms",
                                   help="Output MS path (default: /tmp/smoke-test.ms)")
    smoke_test_parser.add_argument("--cleanup", action="store_true",
                                   help="Clean up temporary synthetic data after test")
    
    # Subparser for the 'find-calibrators' command
    find_cal_parser = subparsers.add_parser(
        "find-calibrators",
        help="Find calibrator sources with available data.",
        description=(
            "Scan input directory and catalog to find which calibrators\n"
            "have observation data available.\n\n"
            "Example:\n"
            "  python -m dsa110_contimg.conversion.cli find-calibrators \\\n"
            "    --input-dir /data/incoming \\\n"
            "    --catalog /path/to/catalog.csv"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    find_cal_parser.add_argument("--input-dir", required=True, help="Directory containing UVH5 files")
    find_cal_parser.add_argument("--catalog", help="Path to calibrator catalog CSV")
    find_cal_parser.add_argument("--dec-tolerance-deg", type=float, default=2.0,
                                help="Declination tolerance for matching (default: 2.0)")
    find_cal_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Subparser for the 'create-test-ms' command
    test_ms_parser = subparsers.add_parser(
        "create-test-ms",
        help="Create a smaller test MS from a full MS for testing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    test_ms_parser.add_argument("--ms-in", required=True, help="Input MS path")
    test_ms_parser.add_argument("--ms-out", required=True, help="Output MS path")
    test_ms_parser.add_argument("--max-baselines", type=int, default=20,
                               help="Maximum number of baselines to include (default: 20)")
    test_ms_parser.add_argument("--max-times", type=int, default=100,
                               help="Maximum number of time integrations (default: 100)")
    test_ms_parser.add_argument("--timebin", type=str, default=None,
                               help="Optional time binning (e.g., '30s')")

    args = parser.parse_args(argv)

    # Configure logging using shared utility
    logger = configure_logging_from_args(args)

    if args.command == "validate":
        from .validation import (
            validate_hdf5_files,
            validate_calibrator_transit,
        )
        from .strategies.hdf5_orchestrator import find_subband_groups
        from pathlib import Path
        
        if args.validate_calibrator:
            # Validate calibrator transit
            result = validate_calibrator_transit(
                args.validate_calibrator,
                Path(args.input_dir),
                window_minutes=args.window_minutes,
                max_days_back=args.max_days_back,
                dec_tolerance_deg=args.dec_tolerance_deg,
            )
            
            if result.found:
                logger.info(f"✓ Transit found: {result.transit_time.iso}")
                logger.info(f"  Data available: {result.data_available}")
                logger.info(f"  Files: {len(result.files) if result.files else 0}")
                logger.info(f"  Declination match: {result.dec_match}")
                if result.dec_diff_deg is not None:
                    logger.info(f"  Dec difference: {result.dec_diff_deg:.2f}°")
                if result.errors:
                    for error in result.errors:
                        logger.error(f"  - {error}")
                    return 1
                if result.warnings:
                    for warning in result.warnings:
                        logger.warning(f"  - {warning}")
                return 0 if result.data_available else 1
            else:
                logger.error("✗ Transit not found")
                if result.errors:
                    for error in result.errors:
                        logger.error(f"  - {error}")
                return 1
        else:
            # Validate HDF5 files
            if not args.start_time or not args.end_time:
                logger.error("--start-time and --end-time required for file validation")
                return 1
            
            groups = find_subband_groups(
                args.input_dir,
                args.start_time,
                args.end_time
            )
            
            all_files = []
            for group in groups:
                all_files.extend(group)
            
            if not all_files:
                logger.warning("No files found to validate")
                return 1
            
            results = validate_hdf5_files(all_files)
            
            valid_count = sum(1 for r in results.values() if r.valid)
            total_count = len(results)
            
            logger.info(f"\nValidated {total_count} files: {valid_count} valid, {total_count - valid_count} invalid\n")
            
            for path, result in sorted(results.items()):
                if not result.valid:
                    logger.error(f"✗ {os.path.basename(path)}")
                    for error in result.errors:
                        logger.error(f"    {error}")
                elif result.warnings:
                    logger.warning(f"⚠ {os.path.basename(path)}")
                    for warning in result.warnings:
                        logger.warning(f"    {warning}")
                else:
                    logger.info(f"✓ {os.path.basename(path)}")
            
            return 0 if valid_count == total_count else 1
    
    elif args.command == "verify-ms":
        from dsa110_contimg.utils.validation import validate_ms, validate_corrected_data_quality
        from dsa110_contimg.utils.validation import ValidationError
        from casacore.tables import table
        
        try:
            check_columns = ['DATA', 'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW']
            if args.check_imaging_columns:
                check_columns.extend(['CORRECTED_DATA', 'MODEL_DATA', 'WEIGHT_SPECTRUM'])
            
            validate_ms(args.ms, check_empty=True, check_columns=check_columns)
            logger.info("✓ MS structure validation passed")
            
            if args.check_imaging_columns:
                warnings = validate_corrected_data_quality(args.ms)
                if warnings:
                    for warning in warnings:
                        logger.warning(f"⚠ {warning}")
            
            # Additional checks
            with table(args.ms, readonly=True) as tb:
                logger.info(f"\nMS Statistics:")
                logger.info(f"  Rows: {tb.nrows():,}")
                logger.info(f"  Columns: {len(tb.colnames())}")
            
            if args.check_field_structure:
                with table(f"{args.ms}::FIELD", readonly=True) as field_tb:
                    logger.info(f"  Fields: {field_tb.nrows()}")
            
            if args.check_spw_structure:
                with table(f"{args.ms}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
                    logger.info(f"  Spectral windows: {spw_tb.nrows()}")
            
            logger.info("\n✓ MS verification complete")
            return 0
            
        except ValidationError as e:
            logger.error("MS verification failed:")
            error_msg = e.format_with_suggestions()
            logger.error(error_msg)
            return 1
    
    elif args.command == "smoke-test":
        from .test_utils import create_minimal_test_ms
        success = create_minimal_test_ms(
            args.output,
            cleanup=args.cleanup
        )
        return 0 if success else 1
    
    elif args.command == "find-calibrators":
        from .validation import find_calibrator_sources_in_data
        from pathlib import Path
        import json
        
        catalog_path = Path(args.catalog) if args.catalog else None
        results = find_calibrator_sources_in_data(
            Path(args.input_dir),
            catalog_path=catalog_path,
            dec_tolerance_deg=args.dec_tolerance_deg,
        )
        
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            logger.info(f"Found {len(results)} calibrator(s) with available data:\n")
            for result in results:
                logger.info(f"  {result['calibrator']}")
                logger.info(f"    RA: {result['ra_deg']:.4f}°, Dec: {result['dec_deg']:.4f}°")
                logger.info(f"    Flux: {result['flux_jy']:.2f} Jy")
                logger.info(f"    Transit: {result['transit_time']}")
                logger.info(f"    Files: {len(result['files'])} subbands")
                logger.info(f"    Dec diff: {result['dec_diff_deg']:.2f}°")
                logger.info("")
        
        return 0 if results else 1
    
    elif args.command == "create-test-ms":
        from .test_utils import create_test_ms
        success = create_test_ms(
            args.ms_in, args.ms_out,
            max_baselines=args.max_baselines,
            max_times=args.max_times,
            timebin=args.timebin
        )
        return 0 if success else 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
