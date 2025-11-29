#!/usr/bin/env python3
"""Build production calibrator registry from NVSS catalog.

This script builds the production calibrator registry database from
NVSS catalog for declinations -40° to +90° in 10° strips.

Expected runtime: ~10-15 minutes
Output: /data/dsa110-contimg/state/db/calibrator_registry.sqlite3
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "dsa110_contimg" / "src"))

from dsa110_contimg.catalog.blacklist_sources import run_full_blacklist_update
from dsa110_contimg.catalog.calibrator_registry import (
    build_calibrator_registry_from_catalog,
    create_calibrator_registry,
    get_registry_statistics,
)

print("=" * 70)
print("PRODUCTION CALIBRATOR REGISTRY BUILD")
print("=" * 70)
print()

# Configuration
DB_PATH = "/data/dsa110-contimg/state/db/calibrator_registry.sqlite3"
CATALOG_TYPE = "nvss"
DEC_STRIPS = list(range(-40, 91, 10))  # -40° to +90° in 10° steps
MIN_FLUX_JY = 0.5
MAX_SOURCES_PER_STRIP = 1000

print(f"Configuration:")
print(f"  Database: {DB_PATH}")
print(f"  Catalog: {CATALOG_TYPE.upper()}")
print(f"  Declination strips: {len(DEC_STRIPS)} ({DEC_STRIPS[0]}° to {DEC_STRIPS[-1]}°)")
print(f"  Min flux: {MIN_FLUX_JY} Jy")
print(f"  Max sources per strip: {MAX_SOURCES_PER_STRIP}")
print()

# Check if registry already exists
db_file = Path(DB_PATH)
if db_file.exists():
    response = input(f"Registry already exists at {DB_PATH}. Overwrite? [y/N]: ")
    if response.lower() != "y":
        print("Aborted.")
        sys.exit(0)
    print(f"Removing existing registry: {DB_PATH}")
    db_file.unlink()
    print()

# Step 1: Create registry database
print("Step 1: Creating registry database...")
start_time = time.time()
create_calibrator_registry(db_path=DB_PATH)
print(f"   :check: Registry created in {time.time() - start_time:.1f}s")
print()

# Step 2: Build calibrator registry from NVSS
print("Step 2: Building calibrator registry from NVSS catalog...")
print("This will take approximately 10-15 minutes...")
print()

start_time = time.time()
try:
    n_added = build_calibrator_registry_from_catalog(
        catalog_type=CATALOG_TYPE,
        dec_strips=DEC_STRIPS,
        min_flux_jy=MIN_FLUX_JY,
        max_sources_per_strip=MAX_SOURCES_PER_STRIP,
        db_path=DB_PATH,
    )

    elapsed = time.time() - start_time
    print()
    print(f"   :check: Added {n_added} calibrators in {elapsed/60:.1f} minutes")
    print(f"   :check: Average: {n_added/len(DEC_STRIPS):.0f} calibrators per strip")
    print(f"   :check: Rate: {n_added/elapsed:.1f} calibrators/second")

except Exception as e:
    print(f"   :cross: Error building registry: {e}")
    sys.exit(1)

print()

# Step 3: Update blacklist
print("Step 3: Updating blacklist with variable sources...")
start_time = time.time()
try:
    results = run_full_blacklist_update(db_path=DB_PATH)
    print(f"   :check: Blacklisted {results['total']} sources in {time.time() - start_time:.1f}s")
    print(f"     - Pulsars: {results['pulsars']}")
    print(f"     - AGN: {results['agn']}")
    print(f"     - Extended: {results['extended']}")
except Exception as e:
    print(f"   :warning: Warning: Blacklist update failed: {e}")
    print("   You can run blacklist update manually later")

print()

# Step 4: Registry statistics
print("Step 4: Registry statistics...")
try:
    stats = get_registry_statistics(db_path=DB_PATH)
    print(f"   Total calibrators: {stats['total_calibrators']}")
    print(f"   Blacklisted sources: {stats['blacklisted_sources']}")

    if "by_dec_strip" in stats and stats["by_dec_strip"]:
        print(f"   Coverage: {len(stats['by_dec_strip'])} declination strips")

    if "quality_distribution" in stats:
        print("   Quality distribution:")
        for quality, count in stats["quality_distribution"].items():
            print(f"     {quality}: {count}")

    if "flux_stats" in stats:
        print(
            f"   Flux range: {stats['flux_stats']['min_jy']:.2f} - {stats['flux_stats']['max_jy']:.2f} Jy"
        )
        print(f"   Mean flux: {stats['flux_stats']['mean_jy']:.2f} Jy")

except Exception as e:
    print(f"   :warning: Warning: Could not get statistics: {e}")

print()
print("=" * 70)
print("PRODUCTION REGISTRY BUILD COMPLETE")
print("=" * 70)
print()
print(f"Registry database: {DB_PATH}")
print(f"Total calibrators: {n_added}")
print()
print("Next steps:")
print(
    '  1. Test registry: python -c "from dsa110_contimg.catalog.calibrator_registry import get_best_calibrator; print(get_best_calibrator(30.0))"'
)
print("  2. Update pipeline to use fast selection: calibration/bandpass.py")
print("  3. Monitor performance in production")
print()
