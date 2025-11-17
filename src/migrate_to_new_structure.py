#!/opt/miniforge/envs/casa6/bin/python
"""Migration script to move from legacy to new directory structure.

This script implements Phase 1 of the migration:
- Creates new directory structure
- Moves data from old locations to new locations
- Updates database references
- Creates symlinks for backward compatibility

Usage:
    # Dry run (show what would be moved)
    python migrate_to_new_structure.py --dry-run

    # Execute migration
    python migrate_to_new_structure.py

    # Enable new structure after migration
    export CONTIMG_USE_NEW_STRUCTURE=1
"""

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dsa110_contimg.database.data_config import (DATA_BASE, STAGE_BASE,
                                                 ensure_staging_directories,
                                                 get_calibrated_ms_dir,
                                                 get_calibration_tables_dir,
                                                 get_raw_ms_dir)


def get_legacy_paths() -> Dict[str, Path]:
    """Get legacy directory paths."""
    return {
        "ms": STAGE_BASE / "ms",
        "calib_ms": STAGE_BASE / "calib_ms",
        "caltables": STAGE_BASE / "caltables",
        "images": STAGE_BASE / "images",
        "mosaics": STAGE_BASE / "mosaics",
        "catalogs": STAGE_BASE / "catalogs",
        "qa": STAGE_BASE / "qa",
        "metadata": STAGE_BASE / "metadata",
    }


def get_new_paths() -> Dict[str, Path]:
    """Get new directory paths."""
    return {
        "raw_ms": STAGE_BASE / "raw" / "ms",
        "calibrated_ms": STAGE_BASE / "calibrated" / "ms",
        "calibration_tables": STAGE_BASE / "calibrated" / "tables",
        "images": STAGE_BASE / "images",  # Same location
        "mosaics": STAGE_BASE / "mosaics",  # Same location
        "catalogs": STAGE_BASE / "products" / "catalogs",
        "qa": STAGE_BASE / "products" / "qa",
        "metadata": STAGE_BASE / "products" / "metadata",
    }


def analyze_migration(dry_run: bool = True) -> Dict:
    """Analyze what needs to be migrated."""
    legacy = get_legacy_paths()
    new = get_new_paths()
    
    analysis = {
        "ms_files": [],
        "calibration_tables": [],
        "images": [],
        "mosaics": [],
        "catalogs": [],
        "qa": [],
        "metadata": [],
        "errors": [],
    }
    
    # Analyze MS files
    legacy_ms = legacy["ms"]
    if legacy_ms.exists():
        # Find science MS files
        science_dir = legacy_ms / "science"
        if science_dir.exists():
            for date_dir in science_dir.iterdir():
                if date_dir.is_dir():
                    for ms_file in date_dir.iterdir():
                        if ms_file.is_dir() and ms_file.name.endswith(".ms"):
                            new_path = new["raw_ms"] / "science" / date_dir.name / ms_file.name
                            analysis["ms_files"].append({
                                "old": ms_file,
                                "new": new_path,
                                "type": "science",
                            })
        
        # Find calibrator MS files
        calibrators_dir = legacy_ms / "calibrators"
        if calibrators_dir.exists():
            for date_dir in calibrators_dir.iterdir():
                if date_dir.is_dir():
                    for ms_file in date_dir.iterdir():
                        if ms_file.is_dir() and ms_file.name.endswith(".ms"):
                            new_path = new["raw_ms"] / "calibrators" / date_dir.name / ms_file.name
                            analysis["ms_files"].append({
                                "old": ms_file,
                                "new": new_path,
                                "type": "calibrator",
                            })
    
    # Analyze calibration tables
    legacy_caltables = legacy["caltables"]
    if legacy_caltables.exists():
        for item in legacy_caltables.iterdir():
            if item.is_dir():
                # Try to extract date from path or use current structure
                # For now, move to new location preserving structure
                new_path = new["calibration_tables"] / item.name
                analysis["calibration_tables"].append({
                    "old": item,
                    "new": new_path,
                })
    
    # Analyze images (same location, but verify)
    legacy_images = legacy["images"]
    if legacy_images.exists():
        for item in legacy_images.iterdir():
            if item.is_dir():
                new_path = new["images"] / item.name
                if item.resolve() != new_path.resolve():
                    analysis["images"].append({
                        "old": item,
                        "new": new_path,
                    })
    
    # Analyze mosaics (same location, but verify)
    legacy_mosaics = legacy["mosaics"]
    if legacy_mosaics.exists():
        for item in legacy_mosaics.iterdir():
            if item.is_file() or item.is_dir():
                new_path = new["mosaics"] / item.name
                if item.resolve() != new_path.resolve():
                    analysis["mosaics"].append({
                        "old": item,
                        "new": new_path,
                    })
    
    return analysis


def migrate_data(analysis: Dict, dry_run: bool = True) -> Tuple[int, int]:
    """Migrate data based on analysis."""
    moved = 0
    errors = 0
    
    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"MS files to migrate: {len(analysis['ms_files'])}")
    print(f"Calibration tables to migrate: {len(analysis['calibration_tables'])}")
    print(f"Images to migrate: {len(analysis['images'])}")
    print(f"Mosaics to migrate: {len(analysis['mosaics'])}")
    print()
    
    if dry_run:
        print("DRY RUN MODE - No files will be moved")
        print()
    
    # Migrate MS files
    for item in analysis["ms_files"]:
        old_path = item["old"]
        new_path = item["new"]
        
        try:
            if not dry_run:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_path), str(new_path))
                print(f"✓ Moved {old_path.name} → {new_path}")
            else:
                print(f"  Would move {old_path.name} → {new_path}")
            moved += 1
        except Exception as e:
            print(f"✗ Error moving {old_path}: {e}")
            errors += 1
    
    # Migrate calibration tables
    for item in analysis["calibration_tables"]:
        old_path = item["old"]
        new_path = item["new"]
        
        try:
            if not dry_run:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_path), str(new_path))
                print(f"✓ Moved {old_path.name} → {new_path}")
            else:
                print(f"  Would move {old_path.name} → {new_path}")
            moved += 1
        except Exception as e:
            print(f"✗ Error moving {old_path}: {e}")
            errors += 1
    
    # Migrate images and mosaics (if needed)
    for item_type in ["images", "mosaics"]:
        for item in analysis[item_type]:
            old_path = item["old"]
            new_path = item["new"]
            
            try:
                if not dry_run:
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_path), str(new_path))
                    print(f"✓ Moved {old_path.name} → {new_path}")
                else:
                    print(f"  Would move {old_path.name} → {new_path}")
                moved += 1
            except Exception as e:
                print(f"✗ Error moving {old_path}: {e}")
                errors += 1
    
    return moved, errors


def create_symlinks(dry_run: bool = True) -> None:
    """Create symlinks for backward compatibility."""
    legacy = get_legacy_paths()
    new = get_new_paths()
    
    symlinks = [
        (legacy["ms"], new["raw_ms"]),
        (legacy["calib_ms"], new["calibrated_ms"]),
        (legacy["caltables"], new["calibration_tables"]),
    ]
    
    print("\n" + "=" * 80)
    print("CREATING SYMLINKS FOR BACKWARD COMPATIBILITY")
    print("=" * 80)
    
    for old_path, new_path in symlinks:
        if old_path.exists() and not old_path.is_symlink():
            # Move remaining files first
            if list(old_path.iterdir()):
                print(f"⚠ {old_path} still has files, skipping symlink")
                continue
        
        try:
            if not dry_run:
                if old_path.exists() and not old_path.is_symlink():
                    old_path.rmdir()  # Remove empty directory
                if not old_path.exists():
                    old_path.symlink_to(new_path)
                    print(f"✓ Created symlink {old_path} → {new_path}")
                else:
                    print(f"  {old_path} already exists, skipping")
            else:
                print(f"  Would create symlink {old_path} → {new_path}")
        except Exception as e:
            print(f"✗ Error creating symlink {old_path}: {e}")


def update_database_references(dry_run: bool = True) -> int:
    """Update database references to new paths."""
    db_path = DATA_BASE / "state" / "data_registry.sqlite3"
    
    if not db_path.exists():
        print(f"⚠ Database not found: {db_path}")
        return 0
    
    print("\n" + "=" * 80)
    print("UPDATING DATABASE REFERENCES")
    print("=" * 80)
    
    updated = 0
    
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        
        # Get all records with stage_path
        cur.execute("SELECT data_id, stage_path FROM data_registry WHERE stage_path IS NOT NULL")
        rows = cur.fetchall()
        
        legacy_base = str(STAGE_BASE)
        new_base = str(STAGE_BASE)
        
        path_mappings = [
            (f"{legacy_base}/ms/", f"{new_base}/raw/ms/"),
            (f"{legacy_base}/calib_ms/", f"{new_base}/calibrated/ms/"),
            (f"{legacy_base}/caltables/", f"{new_base}/calibrated/tables/"),
        ]
        
        for data_id, old_path in rows:
            if not old_path:
                continue
            
            new_path = old_path
            for old_prefix, new_prefix in path_mappings:
                if old_path.startswith(old_prefix):
                    new_path = old_path.replace(old_prefix, new_prefix, 1)
                    break
            
            if new_path != old_path:
                if not dry_run:
                    cur.execute(
                        "UPDATE data_registry SET stage_path = ? WHERE data_id = ?",
                        (new_path, data_id),
                    )
                    print(f"✓ Updated {data_id}: {old_path} → {new_path}")
                else:
                    print(f"  Would update {data_id}: {old_path} → {new_path}")
                updated += 1
        
        if not dry_run:
            conn.commit()
        
        conn.close()
        
    except Exception as e:
        print(f"✗ Error updating database: {e}")
    
    return updated


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate to new directory structure")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip database updates",
    )
    parser.add_argument(
        "--skip-symlinks",
        action="store_true",
        help="Skip symlink creation",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("DSA-110 Pipeline Directory Structure Migration")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Stage base: {STAGE_BASE}")
    print(f"Data base: {DATA_BASE}")
    print()
    
    # Ensure new directories exist
    print("Creating new directory structure...")
    if not args.dry_run:
        ensure_staging_directories()
        print("✓ Directory structure created")
    else:
        print("  Would create directory structure")
    
    # Analyze migration
    print("\nAnalyzing data to migrate...")
    analysis = analyze_migration(dry_run=args.dry_run)
    
    # Migrate data
    moved, errors = migrate_data(analysis, dry_run=args.dry_run)
    
    # Create symlinks
    if not args.skip_symlinks:
        create_symlinks(dry_run=args.dry_run)
    
    # Update database
    if not args.skip_db:
        updated = update_database_references(dry_run=args.dry_run)
        print(f"\n✓ Updated {updated} database references")
    
    # Summary
    print("\n" + "=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Files moved: {moved}")
    print(f"Errors: {errors}")
    
    if args.dry_run:
        print("\nThis was a dry run. To execute migration, run without --dry-run")
    else:
        print("\n✓ Migration complete!")
        print("\nNext steps:")
        print("1. Verify data in new locations")
        print("2. Test pipeline with new structure")
        print("3. Enable new structure: export CONTIMG_USE_NEW_STRUCTURE=1")
        print("4. Monitor for issues")
        print("5. Remove symlinks after verification (Phase 4)")
    
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

