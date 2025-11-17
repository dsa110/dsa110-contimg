#!/opt/miniforge/envs/casa6/bin/python
"""Initialize the new directory structure.

This script creates all necessary directories for the redesigned structure
without migrating existing data. Use this before enabling the new structure.

Usage:
    python initialize_new_structure.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dsa110_contimg.database.data_config import (
    DATA_BASE,
    STAGE_BASE,
    STATE_BASE,
    ensure_staging_directories,
    get_products_dir,
)


def main():
    """Initialize new directory structure."""
    print("=" * 80)
    print("Initializing New Directory Structure")
    print("=" * 80)
    print()
    print(f"Stage base: {STAGE_BASE}")
    print(f"Data base: {DATA_BASE}")
    print(f"State base: {STATE_BASE}")
    print()

    # Ensure staging directories
    print("Creating staging directories...")
    try:
        ensure_staging_directories()
        print("✓ Staging directories created")
    except Exception as e:
        print(f"✗ Error creating staging directories: {e}")
        return 1

    # Ensure data directories
    print("\nCreating data directories...")
    data_dirs = [
        DATA_BASE / "incoming",
        DATA_BASE / "products",
        STATE_BASE,
    ]

    for directory in data_dirs:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✓ {directory}")
        except Exception as e:
            print(f"✗ Error creating {directory}: {e}")
            return 1

    # Create product subdirectories
    print("\nCreating product subdirectories...")
    product_subdirs = [
        "mosaics",
        "catalogs",
        "images",
        "ms",
        "caltables",
        "qa",
        "metadata",
    ]

    products_dir = DATA_BASE / "products"
    for subdir in product_subdirs:
        try:
            (products_dir / subdir).mkdir(parents=True, exist_ok=True)
            print(f"✓ {products_dir / subdir}")
        except Exception as e:
            print(f"✗ Error creating {products_dir / subdir}: {e}")
            return 1

    print("\n" + "=" * 80)
    print("✓ Directory structure initialized successfully!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Review the new structure")
    print("2. Run migration script: python migrate_to_new_structure.py --dry-run")
    print("3. Execute migration: python migrate_to_new_structure.py")
    print("4. Test pipeline with the consolidated structure")
    print("5. Remove legacy symlinks after verification, if any remain")

    return 0


if __name__ == "__main__":
    sys.exit(main())
