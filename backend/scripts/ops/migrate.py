#!/usr/bin/env python3
"""
Database migration management script for DSA-110 Pipeline API.

This script provides a simple interface for managing Alembic migrations.

Usage:
    # Show current migration status
    python scripts/ops/migrate.py status
    
    # Apply all pending migrations
    python scripts/ops/migrate.py upgrade
    
    # Rollback last migration
    python scripts/ops/migrate.py downgrade
    
    # Create a new migration
    python scripts/ops/migrate.py create "Add new column to images"
    
    # Show migration history
    python scripts/ops/migrate.py history
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


# Paths
BACKEND_DIR = Path(__file__).parent.parent.parent
ALEMBIC_INI = BACKEND_DIR / "src" / "dsa110_contimg" / "alembic.ini"
MIGRATIONS_DIR = BACKEND_DIR / "src" / "dsa110_contimg" / "api" / "migrations"


def run_alembic(*args: str) -> int:
    """Run an alembic command."""
    cmd = ["alembic", "-c", str(ALEMBIC_INI), *args]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(BACKEND_DIR))


def cmd_status(args: argparse.Namespace) -> int:
    """Show current migration status."""
    print("\n=== Current Migration Status ===\n")
    return run_alembic("current")


def cmd_upgrade(args: argparse.Namespace) -> int:
    """Apply pending migrations."""
    revision = args.revision or "head"
    print(f"\n=== Upgrading to {revision} ===\n")
    return run_alembic("upgrade", revision)


def cmd_downgrade(args: argparse.Namespace) -> int:
    """Rollback migrations."""
    revision = args.revision or "-1"
    print(f"\n=== Downgrading to {revision} ===\n")
    
    if not args.force:
        confirm = input(f"This will rollback to {revision}. Are you sure? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return 1
    
    return run_alembic("downgrade", revision)


def cmd_create(args: argparse.Namespace) -> int:
    """Create a new migration."""
    message = args.message
    if not message:
        print("Error: Migration message is required")
        return 1
    
    print(f"\n=== Creating migration: {message} ===\n")
    
    if args.autogenerate:
        return run_alembic("revision", "--autogenerate", "-m", message)
    else:
        return run_alembic("revision", "-m", message)


def cmd_history(args: argparse.Namespace) -> int:
    """Show migration history."""
    print("\n=== Migration History ===\n")
    return run_alembic("history", "--verbose")


def cmd_heads(args: argparse.Namespace) -> int:
    """Show current heads."""
    print("\n=== Current Heads ===\n")
    return run_alembic("heads")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database migration management for DSA-110 Pipeline API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show current migration status")
    status_parser.set_defaults(func=cmd_status)
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Apply pending migrations")
    upgrade_parser.add_argument(
        "revision",
        nargs="?",
        default="head",
        help="Target revision (default: head)"
    )
    upgrade_parser.set_defaults(func=cmd_upgrade)
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Rollback migrations")
    downgrade_parser.add_argument(
        "revision",
        nargs="?",
        default="-1",
        help="Target revision (default: -1)"
    )
    downgrade_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )
    downgrade_parser.set_defaults(func=cmd_downgrade)
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument(
        "message",
        help="Migration description"
    )
    create_parser.add_argument(
        "-a", "--autogenerate",
        action="store_true",
        help="Auto-generate migration based on model changes"
    )
    create_parser.set_defaults(func=cmd_create)
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show migration history")
    history_parser.set_defaults(func=cmd_history)
    
    # Heads command
    heads_parser = subparsers.add_parser("heads", help="Show current heads")
    heads_parser.set_defaults(func=cmd_heads)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Check alembic.ini exists
    if not ALEMBIC_INI.exists():
        print(f"Error: alembic.ini not found at {ALEMBIC_INI}")
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
