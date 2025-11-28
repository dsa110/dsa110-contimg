#!/usr/bin/env python
"""Smoke test for flux monitoring and spectral indices.

This script verifies that flux monitoring and spectral index features work correctly.
"""

import sqlite3
import sys
import tempfile
import time
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "dsa110_contimg" / "src"))

from dsa110_contimg.catalog.flux_monitoring import (
    calculate_flux_trends,
    check_flux_stability,
    create_flux_monitoring_tables,
    record_calibration_measurement,
)
from dsa110_contimg.catalog.spectral_index import (
    calculate_spectral_index,
    create_spectral_indices_table,
    store_spectral_index,
)


def test_flux_monitoring():
    """Test flux monitoring functionality."""
    print("Testing flux monitoring...")

    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = f.name

    try:
        # Create tables
        assert create_flux_monitoring_tables(db_path), "Failed to create tables"
        print("  ✓ Created flux monitoring tables")

        # Record measurements
        current_mjd = time.time() / 86400.0 + 40587.0
        for i in range(5):
            mjd = current_mjd - (4 - i) / 24.0
            record_calibration_measurement(
                calibrator_name="3C286",
                ms_path=f"/test/ms_{i}.ms",
                observed_flux_jy=7.4,
                catalog_flux_jy=7.4,
                frequency_ghz=1.4,
                mjd=mjd,
                db_path=db_path,
            )
        print(f"  ✓ Recorded 5 calibration measurements")

        # Calculate trends
        trends = calculate_flux_trends(
            calibrator_name="3C286", time_window_days=1.0, db_path=db_path
        )
        assert "3C286" in trends, "Trends not calculated"
        assert trends["3C286"]["n_measurements"] == 5
        print(f"  ✓ Calculated flux trends: {trends['3C286']['n_measurements']} measurements")

        # Check stability
        all_stable, issues = check_flux_stability(
            drift_threshold_percent=20.0, time_window_days=1.0, min_measurements=3, db_path=db_path
        )
        assert all_stable, "Should be stable with constant flux"
        print(f"  ✓ Stability check passed: {len(issues)} issues")

    finally:
        Path(db_path).unlink(missing_ok=True)

    print("✅ Flux monitoring tests passed!\n")


def test_spectral_indices():
    """Test spectral index functionality."""
    print("Testing spectral indices...")

    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = f.name

    try:
        # Create tables
        assert create_spectral_indices_table(db_path), "Failed to create table"
        print("  ✓ Created spectral_indices table")

        # Calculate spectral index (steep spectrum: α = -0.7)
        # For α=-0.7: S(1.4 GHz)=100 mJy => S(3.0 GHz)=58.65 mJy
        alpha, alpha_err = calculate_spectral_index(
            freq1_ghz=1.4,
            freq2_ghz=3.0,
            flux1_mjy=100.0,
            flux2_mjy=58.65,
            flux1_err_mjy=5.0,
            flux2_err_mjy=3.0,
        )
        assert abs(alpha - (-0.7)) < 0.05, f"Expected α ≈ -0.7, got {alpha}"
        print(f"  ✓ Calculated spectral index: α = {alpha:.3f} ± {alpha_err:.3f}")

        # Store spectral index
        record_id = store_spectral_index(
            source_id="J123456+654321",
            ra_deg=188.64,
            dec_deg=65.72,
            spectral_index=alpha,
            freq1_ghz=1.4,
            freq2_ghz=3.0,
            flux1_mjy=100.0,
            flux2_mjy=58.65,
            catalog1="NVSS",
            catalog2="VLASS",
            spectral_index_err=alpha_err,
            flux1_err_mjy=5.0,
            flux2_err_mjy=3.0,
            fit_quality="good",
            db_path=db_path,
        )
        assert record_id is not None
        print(f"  ✓ Stored spectral index (ID: {record_id})")

        # Verify stored
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM spectral_indices")
        count = cur.fetchone()[0]
        conn.close()
        assert count == 1
        print(f"  ✓ Verified database storage: {count} record")

    finally:
        Path(db_path).unlink(missing_ok=True)

    print("✅ Spectral index tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 SMOKE TESTS")
    print("Proposal #6: Flux Calibration Monitoring & Alerts")
    print("Proposal #1: Spectral Index Mapping")
    print("=" * 60)
    print()

    try:
        test_flux_monitoring()
        test_spectral_indices()

        print("=" * 60)
        print("✅ ALL PHASE 1 TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
