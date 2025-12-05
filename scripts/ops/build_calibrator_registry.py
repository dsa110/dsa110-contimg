#!/usr/bin/env python3
"""Build production calibrator registry from VLA calibrator catalog.

This script builds the calibrator registry database from the VLA calibrator
catalog (vla_calibrators.sqlite3), which contains curated calibration sources
with quality codes and flux measurements.

Expected runtime: ~30 seconds
Output: /data/dsa110-contimg/state/db/calibrator_registry.sqlite3

NOTE: The registry is built from VLA calibrators (1,861 sources), NOT from
general sky surveys like NVSS. VLA calibrators are specifically vetted for
calibration purposes with quality codes for position, structure, etc.
"""

import os
import sqlite3
import sys
import time
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from dsa110_contimg.catalog.blacklist_sources import run_full_blacklist_update
from dsa110_contimg.catalog.build_vla_calibrators import query_calibrators_by_dec
from dsa110_contimg.catalog.calibrator_registry import (
    add_calibrator_to_registry,
    create_calibrator_registry,
    get_registry_statistics,
)

print("=" * 70)
print("PRODUCTION CALIBRATOR REGISTRY BUILD")
print("=" * 70)
print()

# Configuration
REGISTRY_DB = Path("/data/dsa110-contimg/state/db/calibrator_registry.sqlite3")
VLA_CATALOG_DB = Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3")
DEC_STRIPS = list(range(-40, 91, 10))  # -40° to +90° in 10° steps
MIN_FLUX_JY = 0.5  # Minimum flux at 20cm
DEC_RANGE = 10.0  # Degrees around each strip center

print("Configuration:")
print(f"  Registry output: {REGISTRY_DB}")
print(f"  VLA catalog: {VLA_CATALOG_DB}")
print(f"  Declination strips: {len(DEC_STRIPS)} ({DEC_STRIPS[0]}° to {DEC_STRIPS[-1]}°)")
print(f"  Min flux (20cm): {MIN_FLUX_JY} Jy")
print()

# Check VLA catalog exists
if not VLA_CATALOG_DB.exists():
    print(f"ERROR: VLA calibrator catalog not found: {VLA_CATALOG_DB}")
    print()
    print("Build it first with:")
    print("  python -m dsa110_contimg.catalog.build_vla_calibrators --download")
    sys.exit(1)

# Check how many calibrators in VLA catalog
with sqlite3.connect(VLA_CATALOG_DB) as conn:
    n_vla = conn.execute("SELECT COUNT(*) FROM calibrators").fetchone()[0]
    print(f"VLA catalog contains {n_vla} calibrators")
print()

# Check if registry already exists
if REGISTRY_DB.exists():
    response = input(f"Registry already exists at {REGISTRY_DB}. Overwrite? [y/N]: ")
    if response.lower() != "y":
        print("Aborted.")
        sys.exit(0)
    print(f"Removing existing registry: {REGISTRY_DB}")
    REGISTRY_DB.unlink()
    print()

# Step 1: Create registry database
print("Step 1: Creating registry database schema...")
start_time = time.time()
create_calibrator_registry(db_path=str(REGISTRY_DB))
print(f"   ✓ Registry schema created in {time.time() - start_time:.1f}s")
print()

# Step 2: Import VLA calibrators into registry
print("Step 2: Importing VLA calibrators into registry...")
start_time = time.time()

total_added = 0
for dec_strip in DEC_STRIPS:
    try:
        # Query VLA calibrators in this dec strip
        calibrators = query_calibrators_by_dec(
            dec_deg=dec_strip,
            max_separation=DEC_RANGE,
            min_flux_jy=MIN_FLUX_JY,
            band="20cm",
            db_path=VLA_CATALOG_DB,
        )
        
        strip_added = 0
        for cal in calibrators:
            record_id = add_calibrator_to_registry(
                source_name=cal["name"],
                ra_deg=cal["ra_deg"],
                dec_deg=cal["dec_deg"],
                flux_1400mhz_jy=cal["flux_jy"],
                dec_strip=dec_strip,
                catalog_source="VLA",
                notes=f"Quality: {cal.get('quality_codes', 'N/A')}",
                db_path=str(REGISTRY_DB),
            )
            if record_id:
                strip_added += 1
        
        total_added += strip_added
        print(f"   Dec {dec_strip:+3d}°: {strip_added} calibrators")
        
    except Exception as e:
        print(f"   Dec {dec_strip:+3d}°: ERROR - {e}")

elapsed = time.time() - start_time
print()
print(f"   ✓ Added {total_added} calibrators in {elapsed:.1f}s")
print()

# Step 3: Update blacklist (skip network queries by default)
print("Step 3: Updating blacklist with known variable sources...")
print("   (Set SKIP_ATNF_QUERY=0 to query ATNF catalog - slow)")
start_time = time.time()

# Default to skipping slow ATNF network query
if "SKIP_ATNF_QUERY" not in os.environ:
    os.environ["SKIP_ATNF_QUERY"] = "1"

try:
    results = run_full_blacklist_update(db_path=str(REGISTRY_DB))
    print(f"   ✓ Blacklisted {results['total']} sources in {time.time() - start_time:.1f}s")
    print(f"     - Pulsars: {results['pulsars']}")
    print(f"     - AGN: {results['agn']}")
    print(f"     - Extended: {results['extended']}")
except Exception as e:
    print(f"   ⚠ Warning: Blacklist update failed: {e}")
    print("   You can run blacklist update manually later")

print()

# Step 4: Registry statistics
print("Step 4: Registry statistics...")
try:
    stats = get_registry_statistics(db_path=str(REGISTRY_DB))
    print(f"   Total calibrators: {stats['total_calibrators']}")
    print(f"   Blacklisted sources: {stats['blacklisted_sources']}")

    if "by_dec_strip" in stats and stats["by_dec_strip"]:
        print(f"   Coverage: {len(stats['by_dec_strip'])} declination strips")

    if "flux_stats" in stats:
        print(
            f"   Flux range: {stats['flux_stats']['min_jy']:.2f} - "
            f"{stats['flux_stats']['max_jy']:.2f} Jy"
        )
        print(f"   Mean flux: {stats['flux_stats']['mean_jy']:.2f} Jy")

except Exception as e:
    print(f"   ⚠ Warning: Could not get statistics: {e}")

print()
print("=" * 70)
print("PRODUCTION REGISTRY BUILD COMPLETE")
print("=" * 70)
print()
print(f"Registry database: {REGISTRY_DB}")
print(f"Total VLA calibrators: {total_added}")
print()
print("Next steps:")
print(
    '  1. Test: python -c "from dsa110_contimg.catalog.calibrator_registry '
    'import get_best_calibrator; print(get_best_calibrator(30.0))"'
)
print("  2. The pipeline will automatically use this registry for fast calibrator selection")
print()
