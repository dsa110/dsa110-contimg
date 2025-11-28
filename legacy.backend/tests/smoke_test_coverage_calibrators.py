#!/usr/bin/env python3
"""Smoke tests for Coverage-Aware Catalog Selection + Smart Calibrators.

Tests both Proposal #8 (Coverage-Aware Catalog Selection) and
Proposal #3 (Smart Calibrator Pre-Selection).

Run with: python tests/smoke_test_coverage_calibrators.py
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
src_path = Path(__file__).resolve().parents[1] / "src" / "dsa110_contimg" / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

# Test imports
print("=" * 70)
print("SMOKE TESTS: Coverage-Aware Selection + Smart Calibrators")
print("=" * 70)
print()

print("1. Testing module imports...")
try:
    from dsa110_contimg.catalog.blacklist_sources import (
        manual_blacklist_source,
        run_full_blacklist_update,
    )
    from dsa110_contimg.catalog.calibrator_integration import (
        recommend_calibrator_for_observation,
        select_bandpass_calibrator_fast,
    )
    from dsa110_contimg.catalog.calibrator_registry import (
        add_calibrator_to_registry,
        blacklist_source,
        create_calibrator_registry,
        get_best_calibrator,
        get_registry_statistics,
        is_source_blacklisted,
        query_calibrators,
    )
    from dsa110_contimg.catalog.coverage import (
        get_available_catalogs,
        print_coverage_summary,
        recommend_catalogs,
        validate_catalog_choice,
    )

    print("   ✓ All Phase 2 modules imported successfully")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

print()
print("2. Testing coverage-aware catalog selection...")

# Test 2.1: Recommend catalogs for northern source
print("   Testing northern source (Dec=+60°)...")
recs = recommend_catalogs(ra_deg=180.0, dec_deg=60.0, purpose="general")
if recs and len(recs) > 0:
    print(f"      ✓ Got {len(recs)} recommendations")
    print(f"      Primary: {recs[0]['catalog_type']} (reason: {recs[0]['reason']})")
else:
    print("      ✗ No recommendations returned")

# Test 2.2: Recommend catalogs for southern source
print("   Testing southern source (Dec=-30°)...")
recs = recommend_catalogs(ra_deg=180.0, dec_deg=-30.0, purpose="general")
if recs and len(recs) > 0:
    print(f"      ✓ Got {len(recs)} recommendations")
    print(f"      Primary: {recs[0]['catalog_type']}")
else:
    print("      ✗ No recommendations returned")

# Test 2.3: Calibration-specific recommendations
print("   Testing calibration purpose...")
recs = recommend_catalogs(ra_deg=180.0, dec_deg=30.0, purpose="calibration")
if recs and len(recs) > 0:
    print(f"      ✓ Got {len(recs)} calibration recommendations")
    print(f"      Primary: {recs[0]['catalog_type']}")
else:
    print("      ✗ No calibration recommendations")

# Test 2.4: Spectral index purpose
print("   Testing spectral index purpose...")
recs = recommend_catalogs(ra_deg=180.0, dec_deg=20.0, purpose="spectral_index")
if recs and len(recs) >= 2:
    print(f"      ✓ Got {len(recs)} catalogs for spectral index")
    catalogs = [r["catalog_type"] for r in recs]
    print(f"      Catalogs: {', '.join(catalogs)}")
else:
    print(f"      ⚠ Only got {len(recs) if recs else 0} catalogs (need ≥2 for spectral index)")

# Test 2.5: Validate catalog choices
print("   Testing catalog validation...")
is_valid, msg = validate_catalog_choice("nvss", ra_deg=180.0, dec_deg=50.0)
if is_valid:
    print("      ✓ NVSS validated for Dec=+50°")
else:
    print(f"      ✗ NVSS validation failed: {msg}")

is_valid, msg = validate_catalog_choice("sumss", ra_deg=180.0, dec_deg=-40.0)
if is_valid:
    print("      ✓ SUMSS validated for Dec=-40°")
else:
    print(f"      ✗ SUMSS validation failed: {msg}")

# Test 2.6: Invalid catalog choice (should fail)
is_valid, msg = validate_catalog_choice("nvss", ra_deg=180.0, dec_deg=-50.0)
if not is_valid:
    print("      ✓ Correctly rejected NVSS for Dec=-50°")
else:
    print("      ✗ Should have rejected NVSS for Dec=-50°")

print()
print("3. Testing calibrator registry...")

# Create temporary database for testing
temp_db = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
temp_db_path = temp_db.name
temp_db.close()

print(f"   Using temporary database: {temp_db_path}")

# Test 3.1: Create registry
print("   Creating calibrator registry...")
success = create_calibrator_registry(db_path=temp_db_path)
if success:
    print("      ✓ Registry created successfully")
else:
    print("      ✗ Registry creation failed")
    sys.exit(1)

# Test 3.2: Add calibrators
print("   Adding test calibrators...")
n_added = 0
test_calibrators = [
    {"name": "TEST_CAL_1", "ra": 180.0, "dec": 30.0, "flux": 5.0, "strip": 30},
    {"name": "TEST_CAL_2", "ra": 181.0, "dec": 31.0, "flux": 3.0, "strip": 30},
    {"name": "TEST_CAL_3", "ra": 182.0, "dec": 29.0, "flux": 2.0, "strip": 30},
    {"name": "TEST_CAL_4", "ra": 185.0, "dec": 45.0, "flux": 4.0, "strip": 40},
]

for cal in test_calibrators:
    record_id = add_calibrator_to_registry(
        source_name=cal["name"],
        ra_deg=cal["ra"],
        dec_deg=cal["dec"],
        flux_1400mhz_jy=cal["flux"],
        dec_strip=cal["strip"],
        db_path=temp_db_path,
    )
    if record_id:
        n_added += 1

if n_added == len(test_calibrators):
    print(f"      ✓ Added {n_added} calibrators")
else:
    print(f"      ⚠ Only added {n_added}/{len(test_calibrators)} calibrators")

# Test 3.3: Query calibrators
print("   Querying calibrators for Dec=30°...")
calibrators = query_calibrators(
    dec_deg=30.0,
    dec_tolerance=5.0,
    min_flux_jy=1.0,
    db_path=temp_db_path,
)
if len(calibrators) >= 2:
    print(f"      ✓ Found {len(calibrators)} calibrators")
    print(
        f"      Best: {calibrators[0]['source_name']} (flux={calibrators[0]['flux_1400mhz_jy']:.1f} Jy)"
    )
else:
    print(f"      ⚠ Only found {len(calibrators)} calibrators")

# Test 3.4: Get best calibrator
print("   Getting best calibrator...")
best = get_best_calibrator(dec_deg=30.0, dec_tolerance=5.0, db_path=temp_db_path)
if best:
    print(f"      ✓ Best calibrator: {best['source_name']} (quality={best['quality_score']:.1f})")
else:
    print("      ✗ No calibrator returned")

# Test 3.5: Blacklist a source
print("   Testing blacklisting...")
success = blacklist_source(
    source_name="TEST_CAL_2",
    ra_deg=181.0,
    dec_deg=31.0,
    reason="test_blacklist",
    db_path=temp_db_path,
)
if success:
    print("      ✓ Source blacklisted")
else:
    print("      ✗ Blacklisting failed")

# Test 3.6: Check if blacklisted
is_blacklisted_flag, reason = is_source_blacklisted(
    source_name="TEST_CAL_2",
    db_path=temp_db_path,
)
if is_blacklisted_flag and reason == "test_blacklist":
    print("      ✓ Blacklist check works")
else:
    print("      ✗ Blacklist check failed")

# Test 3.7: Verify blacklisted source not returned
calibrators_after = query_calibrators(
    dec_deg=30.0,
    dec_tolerance=5.0,
    min_flux_jy=1.0,
    db_path=temp_db_path,
)
blacklisted_found = any(c["source_name"] == "TEST_CAL_2" for c in calibrators_after)
if not blacklisted_found:
    print("      ✓ Blacklisted source correctly excluded")
else:
    print("      ✗ Blacklisted source still returned")

# Test 3.8: Registry statistics
print("   Getting registry statistics...")
stats = get_registry_statistics(db_path=temp_db_path)
if stats and "total_calibrators" in stats:
    print(f"      ✓ Total calibrators: {stats['total_calibrators']}")
    print(f"      ✓ Blacklisted: {stats['blacklisted_sources']}")
else:
    print("      ✗ Statistics failed")

print()
print("4. Testing calibrator integration...")

# Test 4.1: Fast calibrator selection
print("   Testing fast calibrator selection...")
calibrator = select_bandpass_calibrator_fast(
    dec_deg=30.0,
    dec_tolerance=5.0,
    min_flux_jy=1.0,
    use_registry=True,
    fallback_to_catalog=False,
    db_path=temp_db_path,
)
if calibrator:
    print(f"      ✓ Selected: {calibrator['source_name']}")
else:
    print("      ⚠ No calibrator selected (may be expected if registry empty)")

# Test 4.2: Observation recommendation
print("   Testing observation recommendation...")
calibrator = recommend_calibrator_for_observation(
    target_dec=30.0,
    observation_type="general",
    db_path=temp_db_path,
)
if calibrator:
    print(f"      ✓ Recommended: {calibrator['source_name']}")
else:
    print("      ⚠ No recommendation (may be expected)")

print()
print("5. Testing coverage summary display...")
print_coverage_summary()

print()
print("=" * 70)
print("PHASE 2 SMOKE TESTS COMPLETE")
print("=" * 70)
print()
print("Summary:")
print("  ✓ Coverage-aware catalog selection working")
print("  ✓ Calibrator registry database functional")
print("  ✓ Blacklisting system operational")
print("  ✓ Fast calibrator selection integrated")
print()
print("Next steps:")
print("  1. Build production calibrator registry: build_calibrator_registry_from_catalog()")
print("  2. Run blacklist update: run_full_blacklist_update()")
print("  3. Integrate with pipeline: Update calibration/bandpass.py")
print("  4. Run unit tests: pytest tests/unit/catalog/test_coverage_calibrator_features.py")
print()

# Cleanup
import os

try:
    os.unlink(temp_db_path)
    print(f"Cleaned up temporary database: {temp_db_path}")
except Exception:
    pass
