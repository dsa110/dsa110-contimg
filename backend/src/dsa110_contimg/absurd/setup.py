#!/usr/bin/env python3
"""
ABSURD database setup and initialization.

Run with: python -m dsa110_contimg.absurd.setup [command]

Commands:
    init    - Initialize the ABSURD schema (creates tables and functions)
    status  - Check current schema status
    reset   - Drop and recreate schema (WARNING: deletes all data)
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import asyncpg

from dsa110_contimg.absurd.config import AbsurdConfig
from dsa110_contimg.absurd.dependencies import ensure_dependencies_schema
from dsa110_contimg.absurd.scheduling import ensure_scheduled_tasks_table

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("absurd.setup")


def get_schema_sql() -> str:
    """Read the core schema SQL file."""
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    return schema_path.read_text()


async def check_schema_status(pool: asyncpg.Pool) -> dict:
    """Check the current status of the ABSURD schema."""
    status = {
        "schema_exists": False,
        "tables": [],
        "functions": [],
        "task_count": 0,
    }

    async with pool.acquire() as conn:
        # Check if schema exists
        schema_exists = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.schemata
                WHERE schema_name = 'absurd'
            )
        """)
        status["schema_exists"] = schema_exists

        if schema_exists:
            # List tables
            tables = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'absurd'
                ORDER BY table_name
            """)
            status["tables"] = [row["table_name"] for row in tables]

            # List functions
            functions = await conn.fetch("""
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_schema = 'absurd'
                ORDER BY routine_name
            """)
            status["functions"] = [row["routine_name"] for row in functions]

            # Count tasks if table exists
            if "tasks" in status["tables"]:
                task_count = await conn.fetchval("SELECT COUNT(*) FROM absurd.tasks")
                status["task_count"] = task_count

    return status


async def init_schema(config: AbsurdConfig, include_extensions: bool = True) -> None:
    """Initialize the ABSURD schema."""
    logger.info("Connecting to database...")

    pool = await asyncpg.create_pool(
        config.database_url,
        min_size=1,
        max_size=3,
        command_timeout=120,
    )

    try:
        # Check current status
        status = await check_schema_status(pool)

        if status["schema_exists"] and status["tables"]:
            logger.info("Schema already exists with tables: %s", status["tables"])
            logger.info("Use 'reset' command to drop and recreate.")
        else:
            # Apply core schema
            logger.info("Applying core ABSURD schema...")
            schema_sql = get_schema_sql()

            async with pool.acquire() as conn:
                await conn.execute(schema_sql)

            logger.info("Core schema applied successfully")

        if include_extensions:
            # Apply dependencies schema
            logger.info("Applying dependencies schema...")
            await ensure_dependencies_schema(pool)

            # Apply scheduling schema
            logger.info("Applying scheduling schema...")
            await ensure_scheduled_tasks_table(pool)

        # Verify
        status = await check_schema_status(pool)
        logger.info("=" * 50)
        logger.info("Schema Status:")
        logger.info("  Tables: %s", ", ".join(status["tables"]) or "(none)")
        logger.info("  Functions: %d", len(status["functions"]))
        logger.info("  Tasks: %d", status["task_count"])
        logger.info("=" * 50)

    finally:
        await pool.close()


async def reset_schema(config: AbsurdConfig) -> None:
    """Drop and recreate the ABSURD schema."""
    logger.warning("This will DELETE ALL ABSURD DATA!")

    pool = await asyncpg.create_pool(
        config.database_url,
        min_size=1,
        max_size=3,
        command_timeout=120,
    )

    try:
        async with pool.acquire() as conn:
            # Drop schema
            logger.info("Dropping absurd schema...")
            await conn.execute("DROP SCHEMA IF EXISTS absurd CASCADE")

        # Recreate
        logger.info("Recreating schema...")
        await init_schema(config, include_extensions=True)

    finally:
        await pool.close()


async def show_status(config: AbsurdConfig) -> None:
    """Show current schema status."""
    pool = await asyncpg.create_pool(
        config.database_url,
        min_size=1,
        max_size=2,
        command_timeout=30,
    )

    try:
        status = await check_schema_status(pool)

        print("\n" + "=" * 50)
        print("ABSURD Schema Status")
        print("=" * 50)
        print(f"Schema exists: {status['schema_exists']}")

        if status["schema_exists"]:
            print(f"\nTables ({len(status['tables'])}):")
            for table in status["tables"]:
                print(f"  - {table}")

            print(f"\nFunctions ({len(status['functions'])}):")
            for func in status["functions"]:
                print(f"  - {func}")

            print(f"\nTotal tasks: {status['task_count']}")
        else:
            print("\nSchema not initialized. Run 'init' to create.")

        print("=" * 50 + "\n")

    finally:
        await pool.close()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ABSURD database setup and initialization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m dsa110_contimg.absurd.setup init     # Initialize schema
    python -m dsa110_contimg.absurd.setup status   # Check status
    python -m dsa110_contimg.absurd.setup reset    # Reset schema (deletes data!)
        """,
    )

    parser.add_argument(
        "command",
        choices=["init", "status", "reset"],
        help="Command to run",
    )

    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts",
    )

    args = parser.parse_args()

    # Load configuration
    config = AbsurdConfig.from_env()

    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Set ABSURD_DATABASE_URL environment variable")
        return 1

    logger.info(
        f"Database: {config.database_url.split('@')[1] if '@' in config.database_url else 'localhost'}"
    )

    try:
        if args.command == "init":
            asyncio.run(init_schema(config))

        elif args.command == "status":
            asyncio.run(show_status(config))

        elif args.command == "reset":
            if not args.yes:
                confirm = input("This will DELETE ALL ABSURD DATA. Continue? [y/N]: ")
                if confirm.lower() != "y":
                    print("Aborted.")
                    return 0

            asyncio.run(reset_schema(config))

        return 0

    except asyncpg.PostgresError as e:
        logger.error(f"Database error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
