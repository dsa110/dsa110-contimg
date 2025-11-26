#!/opt/miniforge/envs/casa6/bin/python
"""
Reorganize MS directory structure to match pipeline conventions.

Moves files from flat structure to organized date-based subdirectories:
- MS files → ms/calibrators/YYYY-MM-DD/ or ms/science/YYYY-MM-DD/
- Calibration tables → ms/calibrators/YYYY-MM-DD/ (alongside MS)
- Image FITS files → images/ (should not be in ms/)
- Updates database paths

Usage:
    python scripts/reorganize_ms_directory.py [--dry-run] [--ms-dir /stage/dsa110-contimg/ms]
"""

import argparse
import re
import shutil
import sqlite3
# Use casa6 Python
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from casacore.tables import table  # type: ignore[import]


def extract_date_from_filename(filename: str) -> Optional[str]:
    """Extract YYYY-MM-DD date from filename."""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    return match.group(1) if match else None


def is_ms_directory(path: Path) -> bool:
    """Check if path is a CASA MS directory."""
    if not path.is_dir():
        return False
    # Check for CASA MS structure (MAIN_TABLE or ANTENNA table)
    return (path / "MAIN_TABLE").exists() or (path / "ANTENNA").exists()


def has_corrected_data(ms_path: Path) -> bool:
    """Check if MS has CORRECTED_DATA column (science-ready)."""
    try:
        with table(str(ms_path)) as tb:
            colnames = tb.colnames()
            return "CORRECTED_DATA" in colnames
    except Exception:
        return False


def find_calibration_tables(ms_dir: Path, ms_name: str) -> List[Path]:
    """Find calibration tables associated with an MS file."""
    tables = []
    patterns = [
        f"{ms_name}_*_bpcal",
        f"{ms_name}_*_gpcal",
        f"{ms_name}_*_2gcal",
        f"{ms_name}_*_prebp_phase",
        f"{ms_name}_bpcal",
        f"{ms_name}_gpcal",
        f"{ms_name}_2gcal",
    ]
    
    for pattern in patterns:
        matches = list(ms_dir.glob(pattern))
        for match in matches:
            if match.is_dir() and (match / "OBSERVATION").exists():
                tables.append(match)
    
    return tables


def determine_ms_type(ms_path: Path, ms_dir: Path) -> Tuple[str, List[Path]]:
    """
    Determine if MS is calibrator or science, and find associated calibration tables.
    
    Returns:
        (type, calibration_tables) where type is 'calibrator' or 'science'
    """
    ms_name = ms_path.stem
    
    # Find calibration tables
    cal_tables = find_calibration_tables(ms_dir, ms_name)
    
    # Check if MS has CORRECTED_DATA (science-ready)
    has_corrected = has_corrected_data(ms_path)
    
    # If MS has calibration tables AND no CORRECTED_DATA, it's a calibrator
    # (calibration tables were created from this MS but not yet applied to science MS)
    if cal_tables and not has_corrected:
        return "calibrator", cal_tables
    elif has_corrected:
        # Science MS with calibration applied
        return "science", []
    else:
        # Default: if no calibration tables and no CORRECTED_DATA, assume science
        # (could be uncalibrated science observation)
        return "science", []


def move_file_safely(src: Path, dst: Path, dry_run: bool = False) -> bool:
    """Move file/directory safely, creating parent directories if needed."""
    if src.resolve() == dst.resolve():
        return False  # Already in place
    
    if dst.exists():
        print(f"  WARNING: Target already exists: {dst}")
        return False
    
    if dry_run:
        print(f"  [DRY RUN] Would move: {src} → {dst}")
        return True
    
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        print(f"  Moved: {src.name} → {dst}")
        return True
    except Exception as e:
        print(f"  ERROR: Failed to move {src}: {e}")
        return False


def update_database_paths(
    products_db: Path,
    old_path: str,
    new_path: str,
    dry_run: bool = False
) -> None:
    """Update MS paths in products database."""
    if dry_run:
        print(f"  [DRY RUN] Would update database: {old_path} → {new_path}")
        return
    
    try:
        conn = sqlite3.connect(str(products_db))
        cursor = conn.cursor()
        
        # Update ms_index table
        cursor.execute(
            "UPDATE ms_index SET path = ? WHERE path = ?",
            (new_path, old_path)
        )
        
        # Update images table if ms_path references this MS
        cursor.execute(
            "UPDATE images SET ms_path = ? WHERE ms_path = ?",
            (new_path, old_path)
        )
        
        conn.commit()
        conn.close()
        print(f"  Updated database paths")
    except Exception as e:
        print(f"  WARNING: Failed to update database: {e}")


def update_cal_registry_paths(
    registry_db: Path,
    old_path: str,
    new_path: str,
    dry_run: bool = False
) -> None:
    """Update calibration table paths in registry database."""
    if dry_run:
        print(f"  [DRY RUN] Would update cal registry: {old_path} → {new_path}")
        return
    
    try:
        conn = sqlite3.connect(str(registry_db))
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE caltables SET path = ? WHERE path = ?",
            (new_path, old_path)
        )
        
        conn.commit()
        conn.close()
        print(f"  Updated cal registry paths")
    except Exception as e:
        print(f"  WARNING: Failed to update cal registry: {e}")


def reorganize_ms_directory(
    ms_dir: Path,
    images_dir: Path,
    products_db: Path,
    registry_db: Path,
    dry_run: bool = False
) -> None:
    """Reorganize MS directory structure."""
    
    print(f"Reorganizing MS directory: {ms_dir}")
    print(f"Images directory: {images_dir}")
    print(f"Dry run: {dry_run}")
    print()
    
    # Create organized subdirectories
    calibrators_dir = ms_dir / "calibrators"
    science_dir = ms_dir / "science"
    failed_dir = ms_dir / "failed"
    
    if not dry_run:
        calibrators_dir.mkdir(exist_ok=True)
        science_dir.mkdir(exist_ok=True)
        failed_dir.mkdir(exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all MS directories (exclude calibration tables)
    ms_files = []
    for item in ms_dir.iterdir():
        if item.is_dir() and is_ms_directory(item):
            # Skip if already in organized subdirectory
            if item.parent.name in ["calibrators", "science", "failed"]:
                continue
            # Skip calibration tables (they have _bpcal, _gpcal, _2gcal, etc. in name)
            if any(suffix in item.name for suffix in ["_bpcal", "_gpcal", "_2gcal", "_prebp_phase", "_kcal"]):
                continue
            ms_files.append(item)
    
    print(f"Found {len(ms_files)} MS files to organize")
    print()
    
    # Process MS files
    for ms_path in sorted(ms_files):
        print(f"Processing: {ms_path.name}")
        
        # Extract date
        date_str = extract_date_from_filename(ms_path.name)
        if not date_str:
            print(f"  WARNING: Could not extract date from {ms_path.name}, skipping")
            continue
        
        # Determine type and find calibration tables
        ms_type, cal_tables = determine_ms_type(ms_path, ms_dir)
        print(f"  Type: {ms_type}, Calibration tables: {len(cal_tables)}")
        
        # Determine target directory
        if ms_type == "calibrator":
            target_dir = calibrators_dir / date_str
        else:
            target_dir = science_dir / date_str
        
        # Move MS file
        target_ms_path = target_dir / ms_path.name
        moved = move_file_safely(ms_path, target_ms_path, dry_run)
        
        if moved or not dry_run:
            # Update database
            update_database_paths(
                products_db,
                str(ms_path),
                str(target_ms_path),
                dry_run
            )
        
        # Move associated calibration tables
        for cal_table in cal_tables:
            target_cal_path = target_dir / cal_table.name
            move_file_safely(cal_table, target_cal_path, dry_run)
            
            if not dry_run:
                update_cal_registry_paths(
                    registry_db,
                    str(cal_table),
                    str(target_cal_path),
                    dry_run
                )
        
        # Move .flagversions directory if it exists
        flagversions_path = ms_dir / f"{ms_path.name}.flagversions"
        if flagversions_path.exists():
            target_flagversions = target_dir / flagversions_path.name
            move_file_safely(flagversions_path, target_flagversions, dry_run)
        
        print()
    
    # Move image FITS files to images directory
    print("Moving image FITS files to images directory...")
    image_files = []
    for item in ms_dir.iterdir():
        if item.is_file() and item.suffix == ".fits":
            # Check if it's an image file (not a calibration table)
            if ".img-" in item.name or item.name.endswith(".fits"):
                image_files.append(item)
    
    print(f"Found {len(image_files)} image FITS files")
    
    for img_file in sorted(image_files):
        target_img_path = images_dir / img_file.name
        move_file_safely(img_file, target_img_path, dry_run)
    
    # Handle orphaned calibration tables (not associated with any MS)
    print("Handling orphaned calibration tables...")
    orphaned_cal_tables = []
    for item in ms_dir.iterdir():
        if item.is_dir() and any(suffix in item.name for suffix in ["_bpcal", "_gpcal", "_2gcal", "_prebp_phase", "_kcal"]):
            # Skip if already in organized subdirectory
            if item.parent.name in ["calibrators", "science", "failed"]:
                continue
            orphaned_cal_tables.append(item)
    
    print(f"Found {len(orphaned_cal_tables)} orphaned calibration tables")
    
    for cal_table in sorted(orphaned_cal_tables):
        print(f"Processing calibration table: {cal_table.name}")
        
        # Extract date and base MS name
        date_str = extract_date_from_filename(cal_table.name)
        if not date_str:
            print(f"  WARNING: Could not extract date, skipping")
            continue
        
        # Try to find associated MS to determine if calibrator or science
        # Extract base name (remove calibration suffixes)
        base_name = cal_table.name
        for suffix in ["_bpcal", "_gpcal", "_2gcal", "_prebp_phase", "_kcal", "_0~23_bpcal", "_0~23_gpcal", "_0~23_2gcal"]:
            base_name = base_name.replace(suffix, "")
        
        # Check if there's a corresponding MS in calibrators or science
        calibrator_ms = calibrators_dir / date_str / f"{base_name}.ms"
        science_ms = science_dir / date_str / f"{base_name}.ms"
        
        if calibrator_ms.exists():
            target_dir = calibrators_dir / date_str
            print(f"  Associated with calibrator MS, moving to calibrators")
        elif science_ms.exists():
            # Calibration tables can be in science directory if they were used for that science MS
            # But typically they should be in calibrators
            target_dir = calibrators_dir / date_str
            print(f"  Associated with science MS, but moving to calibrators (standard location)")
        else:
            # Default to calibrators (calibration tables are typically created from calibrator observations)
            target_dir = calibrators_dir / date_str
            print(f"  No associated MS found, defaulting to calibrators")
        
        target_cal_path = target_dir / cal_table.name
        move_file_safely(cal_table, target_cal_path, dry_run)
        
        if not dry_run:
            update_cal_registry_paths(
                registry_db,
                str(cal_table),
                str(target_cal_path),
                dry_run
            )
        print()
    
    print()
    print("Reorganization complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Reorganize MS directory structure"
    )
    parser.add_argument(
        "--ms-dir",
        type=Path,
        default=Path("/stage/dsa110-contimg/ms"),
        help="MS directory to reorganize"
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("/stage/dsa110-contimg/images"),
        help="Images directory"
    )
    parser.add_argument(
        "--products-db",
        type=Path,
        default=Path("/data/dsa110-contimg/state/db/products.sqlite3"),
        help="Products database path"
    )
    parser.add_argument(
        "--registry-db",
        type=Path,
        default=Path("/data/dsa110-contimg/state/db/cal_registry.sqlite3"),
        help="Calibration registry database path"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    if not args.ms_dir.exists():
        print(f"ERROR: MS directory does not exist: {args.ms_dir}")
        return 1
    
    if not args.products_db.exists():
        print(f"WARNING: Products database does not exist: {args.products_db}")
        print("  Database updates will be skipped")
    
    if not args.registry_db.exists():
        print(f"WARNING: Registry database does not exist: {args.registry_db}")
        print("  Registry updates will be skipped")
    
    reorganize_ms_directory(
        args.ms_dir,
        args.images_dir,
        args.products_db,
        args.registry_db,
        args.dry_run
    )
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

