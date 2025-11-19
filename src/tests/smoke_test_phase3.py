#!/usr/bin/env python3
"""Smoke tests for Phase 3: Transient Detection & Astrometric Calibration.

Quick validation of core Phase 3 functionality:
- Transient detection module imports
- Astrometric calibration module imports
- Database table creation
- Detection algorithm basic functionality
- Astrometric offset calculation
"""

import sys
import tempfile
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "dsa110_contimg" / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

import numpy as np
import pandas as pd


def test_imports():
    """Test that Phase 3 modules can be imported."""
    print("Testing imports...")

    try:
        from dsa110_contimg.catalog import transient_detection

        print("✓ transient_detection imported")
    except Exception as e:
        print(f"✗ Failed to import transient_detection: {e}")
        return False

    try:
        from dsa110_contimg.catalog import astrometric_calibration

        print("✓ astrometric_calibration imported")
    except Exception as e:
        print(f"✗ Failed to import astrometric_calibration: {e}")
        return False

    return True


def test_transient_detection_tables():
    """Test transient detection table creation."""
    print("\nTesting transient detection table creation...")

    from dsa110_contimg.catalog.transient_detection import create_transient_detection_tables

    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
        try:
            result = create_transient_detection_tables(tmp.name)
            if result:
                print("✓ Transient detection tables created")
                return True
            else:
                print("✗ Failed to create transient detection tables")
                return False
        except Exception as e:
            print(f"✗ Exception during table creation: {e}")
            return False


def test_astrometry_tables():
    """Test astrometry table creation."""
    print("\nTesting astrometry table creation...")

    from dsa110_contimg.catalog.astrometric_calibration import create_astrometry_tables

    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
        try:
            result = create_astrometry_tables(tmp.name)
            if result:
                print("✓ Astrometry tables created")
                return True
            else:
                print("✗ Failed to create astrometry tables")
                return False
        except Exception as e:
            print(f"✗ Exception during table creation: {e}")
            return False


def test_transient_detection_algorithm():
    """Test transient detection algorithm with synthetic data."""
    print("\nTesting transient detection algorithm...")

    from dsa110_contimg.catalog.transient_detection import detect_transients

    # Create synthetic observed sources
    # 1 new source, 1 brightening, 1 stable, 1 fading
    observed = pd.DataFrame(
        {
            "ra_deg": [180.0, 180.1, 180.2],
            "dec_deg": [30.0, 30.1, 30.2],
            "flux_mjy": [50.0, 100.0, 20.0],  # New, brightening, stable
            "flux_err_mjy": [5.0, 10.0, 2.0],
        }
    )

    # Baseline catalog
    baseline = pd.DataFrame(
        {
            "ra_deg": [180.1, 180.2, 180.3],
            "dec_deg": [30.1, 30.2, 30.3],
            "flux_mjy": [30.0, 20.0, 50.0],  # Will brighten, stable, will fade
        }
    )

    try:
        new_sources, variable_sources, fading_sources = detect_transients(
            observed,
            baseline,
            detection_threshold_sigma=3.0,
            variability_threshold=2.0,
            match_radius_arcsec=10.0,
        )

        print(f"  Detected {len(new_sources)} new sources")
        print(f"  Detected {len(variable_sources)} variable sources")
        print(f"  Detected {len(fading_sources)} fading sources")

        # Should find 1 new, 1 variable (brightening), 1 fading
        if len(new_sources) >= 1:
            print("✓ New source detection works")
        else:
            print("✗ New source detection failed")
            return False

        if len(variable_sources) >= 1:
            print("✓ Variable source detection works")
        else:
            print("✗ Variable source detection failed")
            return False

        if len(fading_sources) >= 1:
            print("✓ Fading source detection works")
        else:
            print("✗ Fading source detection failed")
            return False

        return True

    except Exception as e:
        print(f"✗ Exception during detection: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_astrometric_offset_calculation():
    """Test astrometric offset calculation with synthetic data."""
    print("\nTesting astrometric offset calculation...")

    from dsa110_contimg.catalog.astrometric_calibration import calculate_astrometric_offsets

    # Create synthetic sources with known offset
    # True offset: +100 mas in RA, -50 mas in Dec
    true_ra_offset_mas = 100.0  # mas
    true_dec_offset_mas = -50.0  # mas

    # Reference sources
    reference = pd.DataFrame(
        {
            "ra_deg": [180.0 + i * 0.01 for i in range(20)],
            "dec_deg": [30.0 + i * 0.01 for i in range(20)],
            "flux_mjy": [50.0] * 20,
        }
    )

    # Observed sources (with offset + small random noise)
    # Offset = observed - reference, so we ADD the offset to reference positions
    np.random.seed(42)
    dec_mean = reference["dec_deg"].mean()
    ra_offset_deg = true_ra_offset_mas / (3600.0 * 1000.0 * np.cos(np.radians(dec_mean)))
    dec_offset_deg = true_dec_offset_mas / (3600.0 * 1000.0)

    observed = pd.DataFrame(
        {
            "ra_deg": reference["ra_deg"] + ra_offset_deg + np.random.normal(0, 1e-6, 20),
            "dec_deg": reference["dec_deg"] + dec_offset_deg + np.random.normal(0, 1e-6, 20),
            "flux_mjy": [50.0] * 20,
        }
    )

    try:
        solution = calculate_astrometric_offsets(
            observed,
            reference,
            match_radius_arcsec=5.0,
            min_matches=10,
            flux_weight=False,
        )

        if solution is None:
            print("✗ No astrometric solution found")
            return False

        print(f"  Matches: {solution['n_matches']}")
        print(f"  RA offset: {solution['ra_offset_mas']:.1f} mas (true: 100 mas)")
        print(f"  Dec offset: {solution['dec_offset_mas']:.1f} mas (true: -50 mas)")
        print(f"  RMS residual: {solution['rms_residual_mas']:.1f} mas")

        # Check if recovered offsets are close to true values
        ra_error = abs(solution["ra_offset_mas"] - 100.0)
        dec_error = abs(solution["dec_offset_mas"] - (-50.0))

        if ra_error < 20.0 and dec_error < 20.0:
            print("✓ Astrometric offset calculation accurate")
            return True
        else:
            print(f"✗ Offset errors too large: RA={ra_error:.1f} mas, Dec={dec_error:.1f} mas")
            return False

    except Exception as e:
        print(f"✗ Exception during offset calculation: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_transient_storage():
    """Test storing transient candidates in database."""
    print("\nTesting transient candidate storage...")

    from dsa110_contimg.catalog.transient_detection import (
        create_transient_detection_tables,
        get_transient_candidates,
        store_transient_candidates,
    )

    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
        try:
            # Create tables
            create_transient_detection_tables(tmp.name)

            # Create test candidates
            candidates = [
                {
                    "ra_deg": 180.0,
                    "dec_deg": 30.0,
                    "flux_obs_mjy": 50.0,
                    "flux_baseline_mjy": None,
                    "significance_sigma": 7.5,
                    "detection_type": "new",
                },
                {
                    "ra_deg": 180.1,
                    "dec_deg": 30.1,
                    "flux_obs_mjy": 100.0,
                    "flux_baseline_mjy": 30.0,
                    "flux_ratio": 3.33,
                    "significance_sigma": 8.2,
                    "detection_type": "brightening",
                },
            ]

            # Store candidates
            candidate_ids = store_transient_candidates(
                candidates,
                baseline_catalog="NVSS",
                db_path=tmp.name,
            )

            if len(candidate_ids) != 2:
                print(f"✗ Expected 2 candidate IDs, got {len(candidate_ids)}")
                return False

            # Query back
            df = get_transient_candidates(min_significance=5.0, db_path=tmp.name)

            if len(df) != 2:
                print(f"✗ Expected 2 candidates in query, got {len(df)}")
                return False

            print("✓ Transient storage and retrieval works")
            return True

        except Exception as e:
            print(f"✗ Exception during storage test: {e}")
            import traceback

            traceback.print_exc()
            return False


def test_astrometry_storage():
    """Test storing astrometric solutions in database."""
    print("\nTesting astrometric solution storage...")

    from dsa110_contimg.catalog.astrometric_calibration import (
        create_astrometry_tables,
        get_recent_astrometric_solutions,
        store_astrometric_solution,
    )

    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
        try:
            # Create tables
            create_astrometry_tables(tmp.name)

            # Create test solution
            solution = {
                "n_matches": 15,
                "ra_offset_mas": 120.5,
                "dec_offset_mas": -45.2,
                "ra_offset_err_mas": 8.3,
                "dec_offset_err_mas": 7.1,
                "rms_residual_mas": 150.0,
                "matches": [
                    {
                        "ra_obs": 180.0,
                        "dec_obs": 30.0,
                        "ra_ref": 179.9999,
                        "dec_ref": 30.0001,
                        "ra_offset_mas": 120.0,
                        "dec_offset_mas": -50.0,
                        "separation_mas": 130.0,
                        "flux_obs": 50.0,
                        "flux_ref": 48.0,
                    }
                ],
            }

            # Store solution
            solution_id = store_astrometric_solution(
                solution,
                mosaic_id=1,
                reference_catalog="FIRST",
                db_path=tmp.name,
            )

            if solution_id is None:
                print("✗ Failed to store astrometric solution")
                return False

            # Query back
            df = get_recent_astrometric_solutions(limit=10, db_path=tmp.name)

            if len(df) != 1:
                print(f"✗ Expected 1 solution in query, got {len(df)}")
                return False

            print("✓ Astrometric solution storage and retrieval works")
            return True

        except Exception as e:
            print(f"✗ Exception during storage test: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("Phase 3 Smoke Tests: Transient Detection & Astrometry")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Transient Tables", test_transient_detection_tables),
        ("Astrometry Tables", test_astrometry_tables),
        ("Transient Detection", test_transient_detection_algorithm),
        ("Astrometric Offsets", test_astrometric_offset_calculation),
        ("Transient Storage", test_transient_storage),
        ("Astrometry Storage", test_astrometry_storage),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All Phase 3 smoke tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
