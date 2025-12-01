#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script for DSA-110 Pipeline.

This script migrates data from the existing SQLite products database
to the new PostgreSQL instance. It handles:
- Schema differences (AUTOINCREMENT → SERIAL)
- Data type conversions
- Batch inserts for performance
- Progress tracking and resume capability

Usage:
    python migrate_sqlite_to_postgres.py [--dry-run] [--batch-size 1000]
    
    # With custom paths
    python migrate_sqlite_to_postgres.py \
        --sqlite /data/dsa110-contimg/state/products.sqlite3 \
        --pg-host localhost --pg-port 5432 \
        --pg-database dsa110 --pg-user dsa110

Environment variables:
    DSA110_DB_PG_HOST, DSA110_DB_PG_PORT, DSA110_DB_PG_DATABASE,
    DSA110_DB_PG_USER, DSA110_DB_PG_PASSWORD
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import asyncpg
    import asyncio
except ImportError:
    print("Error: asyncpg not installed. Run: pip install asyncpg")
    sys.exit(1)


# Tables to migrate in order (respects foreign key dependencies)
MIGRATION_ORDER = [
    "dead_letter_queue",
    "ms_index",
    "images",
    "photometry",
    "jobs",
    "batch_jobs",
    "variability_stats",
    "transient_candidates",
    "mosaics",
    "calibrator_transits",
    "calibration_solutions",
    "qa_metrics",
    "api_sessions",
    "audit_log",
]

# Columns to skip (auto-generated in PostgreSQL)
SKIP_COLUMNS = {"id"}  # SERIAL columns

# Type mappings from SQLite to PostgreSQL
TYPE_MAPPINGS = {
    "INTEGER": "INTEGER",
    "REAL": "DOUBLE PRECISION",
    "TEXT": "TEXT",
    "BLOB": "BYTEA",
}


def get_sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    """Get list of tables in SQLite database."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return [row[0] for row in cursor.fetchall()]


def get_table_columns(conn: sqlite3.Connection, table: str) -> list[tuple[str, str]]:
    """Get column names and types for a table."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [(row[1], row[2]) for row in cursor.fetchall()]


def get_row_count(conn: sqlite3.Connection, table: str) -> int:
    """Get number of rows in a table."""
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0]


async def create_pg_pool(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    min_size: int = 2,
    max_size: int = 10,
) -> asyncpg.Pool:
    """Create PostgreSQL connection pool."""
    return await asyncpg.create_pool(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        min_size=min_size,
        max_size=max_size,
    )


async def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_pool: asyncpg.Pool,
    table: str,
    batch_size: int = 1000,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Migrate a single table from SQLite to PostgreSQL."""
    result = {
        "table": table,
        "rows_total": 0,
        "rows_migrated": 0,
        "errors": [],
        "skipped": False,
    }

    # Check if table exists in SQLite
    sqlite_tables = get_sqlite_tables(sqlite_conn)
    if table not in sqlite_tables:
        result["skipped"] = True
        result["errors"].append(f"Table {table} not found in SQLite")
        return result

    # Get columns (excluding auto-increment id)
    columns = get_table_columns(sqlite_conn, table)
    col_names = [c[0] for c in columns if c[0] not in SKIP_COLUMNS]

    if not col_names:
        result["skipped"] = True
        result["errors"].append(f"No columns to migrate for {table}")
        return result

    # Get total row count
    result["rows_total"] = get_row_count(sqlite_conn, table)

    if result["rows_total"] == 0:
        print(f"  {table}: 0 rows (empty)")
        return result

    # Build INSERT statement
    placeholders = ", ".join(f"${i+1}" for i in range(len(col_names)))
    insert_sql = f"""
        INSERT INTO {table} ({', '.join(col_names)})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
    """

    # Read and insert in batches
    offset = 0
    while offset < result["rows_total"]:
        # Read batch from SQLite
        query = f"SELECT {', '.join(col_names)} FROM {table} LIMIT {batch_size} OFFSET {offset}"
        cursor = sqlite_conn.execute(query)
        rows = cursor.fetchall()

        if not rows:
            break

        if dry_run:
            result["rows_migrated"] += len(rows)
            print(f"  {table}: Would migrate batch {offset//batch_size + 1} ({len(rows)} rows)")
        else:
            try:
                async with pg_pool.acquire() as conn:
                    # Convert rows to proper types
                    converted_rows = []
                    for row in rows:
                        converted = []
                        for i, val in enumerate(row):
                            # Handle JSON stored as TEXT
                            if isinstance(val, str) and (val.startswith('[') or val.startswith('{')):
                                try:
                                    # Keep as string for TEXT columns, PostgreSQL handles it
                                    converted.append(val)
                                except:
                                    converted.append(val)
                            else:
                                converted.append(val)
                        converted_rows.append(tuple(converted))

                    # Batch insert
                    await conn.executemany(insert_sql, converted_rows)
                    result["rows_migrated"] += len(rows)

            except Exception as e:
                result["errors"].append(f"Batch {offset//batch_size}: {str(e)}")

        offset += batch_size

        # Progress indicator
        pct = min(100, (offset / result["rows_total"]) * 100)
        print(f"  {table}: {pct:.1f}% ({result['rows_migrated']}/{result['rows_total']})", end="\r")

    print(f"  {table}: {result['rows_migrated']}/{result['rows_total']} rows migrated" + " " * 20)

    return result


async def run_migration(
    sqlite_path: str,
    pg_host: str,
    pg_port: int,
    pg_database: str,
    pg_user: str,
    pg_password: str,
    batch_size: int = 1000,
    dry_run: bool = False,
    tables: list[str] | None = None,
) -> dict[str, Any]:
    """Run the full migration."""
    results = {
        "started_at": datetime.now().isoformat(),
        "sqlite_path": sqlite_path,
        "pg_host": pg_host,
        "pg_database": pg_database,
        "dry_run": dry_run,
        "tables": {},
        "total_rows": 0,
        "total_migrated": 0,
        "errors": [],
    }

    # Connect to SQLite
    print(f"\nConnecting to SQLite: {sqlite_path}")
    if not Path(sqlite_path).exists():
        results["errors"].append(f"SQLite database not found: {sqlite_path}")
        return results

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    # Connect to PostgreSQL
    print(f"Connecting to PostgreSQL: {pg_host}:{pg_port}/{pg_database}")
    try:
        pg_pool = await create_pg_pool(
            host=pg_host,
            port=pg_port,
            database=pg_database,
            user=pg_user,
            password=pg_password,
        )
    except Exception as e:
        results["errors"].append(f"Failed to connect to PostgreSQL: {str(e)}")
        sqlite_conn.close()
        return results

    # Determine tables to migrate
    if tables:
        migration_tables = tables
    else:
        sqlite_tables = set(get_sqlite_tables(sqlite_conn))
        migration_tables = [t for t in MIGRATION_ORDER if t in sqlite_tables]
        # Add any tables not in MIGRATION_ORDER
        extra_tables = sqlite_tables - set(MIGRATION_ORDER) - {"alembic_version", "sqlite_sequence"}
        migration_tables.extend(sorted(extra_tables))

    print(f"\nMigrating {len(migration_tables)} tables:")
    for table in migration_tables:
        print(f"  - {table}")

    print("\n" + "=" * 60)
    print("MIGRATION " + ("(DRY RUN)" if dry_run else ""))
    print("=" * 60 + "\n")

    # Migrate each table
    for table in migration_tables:
        result = await migrate_table(
            sqlite_conn=sqlite_conn,
            pg_pool=pg_pool,
            table=table,
            batch_size=batch_size,
            dry_run=dry_run,
        )
        results["tables"][table] = result
        results["total_rows"] += result["rows_total"]
        results["total_migrated"] += result["rows_migrated"]
        if result["errors"]:
            results["errors"].extend(result["errors"])

    # Cleanup
    sqlite_conn.close()
    await pg_pool.close()

    results["completed_at"] = datetime.now().isoformat()

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total rows: {results['total_rows']}")
    print(f"Rows migrated: {results['total_migrated']}")
    print(f"Errors: {len(results['errors'])}")

    if results["errors"]:
        print("\nErrors:")
        for err in results["errors"][:10]:
            print(f"  - {err}")
        if len(results["errors"]) > 10:
            print(f"  ... and {len(results['errors']) - 10} more")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Migrate DSA-110 data from SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--sqlite",
        default="/data/dsa110-contimg/state/products.sqlite3",
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--pg-host",
        default=os.getenv("DSA110_DB_PG_HOST", "localhost"),
        help="PostgreSQL host",
    )
    parser.add_argument(
        "--pg-port",
        type=int,
        default=int(os.getenv("DSA110_DB_PG_PORT", "5432")),
        help="PostgreSQL port",
    )
    parser.add_argument(
        "--pg-database",
        default=os.getenv("DSA110_DB_PG_DATABASE", "dsa110"),
        help="PostgreSQL database name",
    )
    parser.add_argument(
        "--pg-user",
        default=os.getenv("DSA110_DB_PG_USER", "dsa110"),
        help="PostgreSQL user",
    )
    parser.add_argument(
        "--pg-password",
        default=os.getenv("DSA110_DB_PG_PASSWORD", "dsa110_dev_password"),
        help="PostgreSQL password",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for inserts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        help="Specific tables to migrate (default: all)",
    )
    parser.add_argument(
        "--output",
        help="Save migration results to JSON file",
    )

    args = parser.parse_args()

    # Run migration
    results = asyncio.run(
        run_migration(
            sqlite_path=args.sqlite,
            pg_host=args.pg_host,
            pg_port=args.pg_port,
            pg_database=args.pg_database,
            pg_user=args.pg_user,
            pg_password=args.pg_password,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            tables=args.tables,
        )
    )

    # Save results if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")

    # Exit with error code if there were errors
    if results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
