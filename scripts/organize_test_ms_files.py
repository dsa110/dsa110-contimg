#!/usr/bin/env python3
"""
Organize Test MS Files

This script categorizes and moves test measurement set files to organized directories
based on their purpose and creation date.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def organize_test_ms_files():
    """Organize test MS files into categorized directories."""
    
    project_root = Path("/data/jfaber/dsa110-contimg")
    test_data_dir = project_root / "test_data"
    
    # Create subdirectories
    subdirs = {
        "uvw_testing": test_data_dir / "uvw_testing",
        "output_testing": test_data_dir / "output_testing", 
        "debugging": test_data_dir / "debugging",
        "archived": test_data_dir / "archived"
    }
    
    for subdir in subdirs.values():
        subdir.mkdir(exist_ok=True)
    
    # Define categorization rules
    categories = {
        "output_testing": [
            "test_output.ms",
            "test_original_output.ms", 
            "test_improved_output.ms"
        ],
        "uvw_testing": [
            "test_ms_uvw_preservation.ms",
            "test_ms_uvw_restoration.ms",
            "test_ms_uvw_restoration_fixed.ms",
            "test_ms_uvw_immediate.ms",
            "test_ms_uvw_recalc.ms",
            "test_ms_uvw_recalc_corrected.ms",
            "test_ms_uvw_recalc_final.ms",
            "test_ms_uvw_recalc_final_corrected.ms",
            "test_ms_uvw_recalc_fixed.ms",
            "test_ms_uvw_recalc_time_fixed.ms",
            "test_ms_uvw_recalc_time_fixed2.ms",
            "test_ms_simple_uvw_fix.ms"
        ],
        "debugging": [
            "test_ms_uvw_debug.ms",
            "test_ms_uvw_restoration_debug.ms",
            "test_ms_uvw_shape_debug.ms",
            "test_direct_mod.ms"
        ]
    }
    
    # Move files to appropriate categories
    moved_count = 0
    total_size = 0
    
    for category, files in categories.items():
        print(f"\n📁 Processing {category} files...")
        
        for filename in files:
            source_path = project_root / filename
            if source_path.exists():
                dest_path = subdirs[category] / filename
                
                # Get file size
                size_mb = sum(f.stat().st_size for f in source_path.rglob('*') if f.is_file()) / (1024*1024)
                total_size += size_mb
                
                # Move the file
                shutil.move(str(source_path), str(dest_path))
                print(f"  ✅ Moved: {filename} ({size_mb:.1f} MB)")
                moved_count += 1
            else:
                print(f"  ⚠️  Not found: {filename}")
    
    # Create a summary file
    summary_file = test_data_dir / "test_files_summary.md"
    with open(summary_file, 'w') as f:
        f.write("# Test MS Files Organization Summary\n\n")
        f.write(f"**Total files moved:** {moved_count}\n")
        f.write(f"**Total size:** {total_size:.1f} MB\n")
        f.write(f"**Organization date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## File Categories\n\n")
        for category, files in categories.items():
            f.write(f"### {category.replace('_', ' ').title()}\n")
            f.write(f"**Location:** `test_data/{category}/`\n")
            f.write(f"**Files:** {len(files)}\n\n")
            for filename in files:
                f.write(f"- {filename}\n")
            f.write("\n")
    
    print(f"\n🎉 Organization complete!")
    print(f"📊 Moved {moved_count} files ({total_size:.1f} MB)")
    print(f"📝 Summary saved to: {summary_file}")
    
    return moved_count, total_size

if __name__ == "__main__":
    organize_test_ms_files()
