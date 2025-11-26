"""Command-line interface for data registry publishing operations."""

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

from .data_registry import (  # noqa: E402
    ensure_data_registry_db,
    get_data,
    list_data,
    publish_data_manual,
    trigger_auto_publish,
)


def cmd_publish(args: argparse.Namespace) -> int:
    """Manually publish a data instance."""
    db_path = Path(args.db)
    conn = ensure_data_registry_db(db_path)

    record = get_data(conn, data_id=args.data_id)
    if not record:
        logger.error(f"Data {args.data_id} not found")
        return 1

    if record.status == "published":
        logger.warning(f"Data {args.data_id} is already published")
        print(json.dumps({"status": "already_published", "data_id": args.data_id}, indent=2))
        return 0

    success = publish_data_manual(conn, args.data_id, products_base=args.products_base)
    if not success:
        logger.error(f"Failed to publish {args.data_id}")
        return 1

    updated_record = get_data(conn, args.data_id)
    result = {
        "published": True,
        "data_id": args.data_id,
        "status": updated_record.status if updated_record else record.status,
        "published_path": updated_record.published_path if updated_record else None,
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Query publish status for a data instance."""
    db_path = Path(args.db)
    conn = ensure_data_registry_db(db_path)

    record = get_data(conn, data_id=args.data_id)
    if not record:
        logger.error(f"Data {args.data_id} not found")
        return 1

    result = {
        "data_id": record.data_id,
        "data_type": record.data_type,
        "status": record.status,
        "stage_path": record.stage_path,
        "published_path": record.published_path,
        "created_at": record.created_at,
        "published_at": getattr(record, "published_at", None),
        "publish_mode": getattr(record, "publish_mode", None),
        "publish_attempts": getattr(record, "publish_attempts", 0),
        "publish_error": getattr(record, "publish_error", None),
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_retry(args: argparse.Namespace) -> int:
    """Retry publishing a failed data instance."""
    db_path = Path(args.db)
    conn = ensure_data_registry_db(db_path)

    record = get_data(conn, data_id=args.data_id)
    if not record:
        logger.error(f"Data {args.data_id} not found")
        return 1

    if record.status == "published":
        logger.warning(f"Data {args.data_id} is already published")
        print(json.dumps({"status": "already_published", "data_id": args.data_id}, indent=2))
        return 0

    # Reset publish attempts before retry
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE data_registry
        SET publish_attempts = 0,
            publish_error = NULL,
            status = 'staging'
        WHERE data_id = ?
        """,
        (args.data_id,),
    )
    conn.commit()

    # Trigger auto-publish
    success = trigger_auto_publish(conn, args.data_id)

    if not success:
        updated_record = get_data(conn, args.data_id)
        error_msg = (
            updated_record.publish_error
            if updated_record and hasattr(updated_record, "publish_error")
            else "Unknown error"
        )
        logger.error(f"Failed to publish {args.data_id}: {error_msg}")
        result = {
            "retried": True,
            "published": False,
            "data_id": args.data_id,
            "error": error_msg,
        }
        print(json.dumps(result, indent=2))
        return 1

    updated_record = get_data(conn, args.data_id)
    result = {
        "retried": True,
        "published": True,
        "data_id": args.data_id,
        "status": updated_record.status if updated_record else record.status,
        "published_path": updated_record.published_path if updated_record else None,
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List data registry entries with optional filters."""
    db_path = Path(args.db)
    conn = ensure_data_registry_db(db_path)

    records, _ = list_data(conn, data_type=args.data_type, status=args.status)

    if args.json:
        result = []
        for record in records:
            result.append(
                {
                    "data_id": record.data_id,
                    "data_type": record.data_type,
                    "status": record.status,
                    "stage_path": record.stage_path,
                    "published_path": record.published_path,
                    "created_at": record.created_at,
                    "published_at": getattr(record, "published_at", None),
                }
            )
        print(json.dumps(result, indent=2))
    else:
        # Table format
        print(f"{'Data ID':<40} {'Type':<15} {'Status':<12} {'Stage Path':<60}")
        print("-" * 130)
        for record in records:
            print(
                f"{record.data_id:<40} {record.data_type:<15} {record.status:<12} "
                f"{str(record.stage_path)[:60]:<60}"
            )

    return 0


def main(argv: list = None) -> int:
    """Main function for the publishing CLI."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=(
            "DSA-110 Continuum Imaging Publishing CLI\n\n"
            "Manage data registry publishing operations.\n\n"
            "Examples:\n"
            "  # Publish a data instance\n"
            "  python -m dsa110_contimg.database.cli publish \\\n"
            "    --db state/db/products.sqlite3 --data-id mosaic_2025-11-12_10-00-00\n\n"
            "  # Check publish status\n"
            "  python -m dsa110_contimg.database.cli status \\\n"
            "    --db state/db/products.sqlite3 --data-id mosaic_2025-11-12_10-00-00\n\n"
            "  # Retry failed publish\n"
            "  python -m dsa110_contimg.database.cli retry \\\n"
            "    --db state/db/products.sqlite3 --data-id mosaic_2025-11-12_10-00-00\n\n"
            "  # List all staging data\n"
            "  python -m dsa110_contimg.database.cli list \\\n"
            "    --db state/db/products.sqlite3 --status staging\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Common arguments
    parser.add_argument(
        "--db",
        type=str,
        default="state/db/products.sqlite3",
        help="Path to products database",
    )

    # Add common logging arguments
    add_common_logging_args(parser)

    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to run")

    # Publish subcommand
    publish_parser = subparsers.add_parser(
        "publish",
        help="Manually publish a data instance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    publish_parser.add_argument(
        "data_id",
        type=str,
        help="Data instance ID to publish",
    )
    publish_parser.add_argument(
        "--products-base",
        type=Path,
        default=None,
        help="Base path for published products (default: /data/dsa110-contimg/products)",
    )
    publish_parser.set_defaults(func=cmd_publish)

    # Status subcommand
    status_parser = subparsers.add_parser(
        "status",
        help="Query publish status for a data instance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    status_parser.add_argument(
        "data_id",
        type=str,
        help="Data instance ID to query",
    )
    status_parser.set_defaults(func=cmd_status)

    # Retry subcommand
    retry_parser = subparsers.add_parser(
        "retry",
        help="Retry publishing a failed data instance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    retry_parser.add_argument(
        "data_id",
        type=str,
        help="Data instance ID to retry",
    )
    retry_parser.set_defaults(func=cmd_retry)

    # List subcommand
    list_parser = subparsers.add_parser(
        "list",
        help="List data registry entries",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    list_parser.add_argument(
        "--data-type",
        type=str,
        default=None,
        help="Filter by data type (e.g., 'mosaic', 'image', 'ms')",
    )
    list_parser.add_argument(
        "--status",
        type=str,
        default=None,
        choices=["staging", "publishing", "published"],
        help="Filter by status",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    list_parser.set_defaults(func=cmd_list)

    # Index HDF5 files subcommand
    from dsa110_contimg.database.hdf5_index import index_hdf5_files

    def cmd_index_hdf5(args: argparse.Namespace) -> int:
        """Index HDF5 files in input directory for fast queries."""

        input_dir = Path(args.input_dir)
        hdf5_db = Path(args.hdf5_db)

        if not input_dir.exists():
            print(f"Error: Input directory does not exist: {input_dir}")
            return 1

        print(f"Indexing HDF5 files in {input_dir}...")
        stats = index_hdf5_files(
            input_dir,
            hdf5_db,
            force_rescan=args.force,
            max_files=args.max_files,
        )

        print("\nIndexing complete:")
        print(f"  Total scanned: {stats['total_scanned']}")
        print(f"  New indexed: {stats['new_indexed']}")
        print(f"  Updated: {stats['updated']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Marked as not stored: {stats['deleted']}")
        print(f"  Errors: {stats['errors']}")

        return 0

    index_parser = subparsers.add_parser(
        "index-hdf5",
        help="Index HDF5 files in input directory for fast queries",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    index_parser.add_argument(
        "--input-dir",
        type=str,
        default=os.getenv("CONTIMG_INPUT_DIR", "/data/incoming"),
        help="Directory containing HDF5 files",
    )
    index_parser.add_argument(
        "--hdf5-db",
        type=str,
        default=os.getenv("HDF5_DB_PATH", "/data/dsa110-contimg/state/db/hdf5.sqlite3"),
        help="Path to HDF5 index database",
    )
    index_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing of all files",
    )
    index_parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum number of files to index (for testing)",
    )
    index_parser.set_defaults(func=cmd_index_hdf5)

    # Parse arguments
    args = parser.parse_args(argv)

    # Configure logging
    configure_logging_from_args(args)

    # Execute command
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
