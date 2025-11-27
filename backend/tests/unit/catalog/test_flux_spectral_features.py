"""Unit tests for flux monitoring and spectral index features.

Tests Proposal #6: Flux Calibration Monitoring & Alerts
Tests Proposal #1: Spectral Index Mapping
"""

import sqlite3
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

# Add source directory to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "src" / "dsa110_contimg" / "src")
)

from dsa110_contimg.catalog.flux_monitoring import (
    calculate_flux_trends,
    check_flux_stability,
    create_flux_monitoring_tables,
    record_calibration_measurement,
    run_flux_monitoring_check,
)
from dsa110_contimg.catalog.spectral_index import (
    calculate_and_store_from_catalogs,
    calculate_spectral_index,
    create_spectral_indices_table,
    fit_spectral_index_multifreq,
    get_spectral_index_for_source,
    get_spectral_index_statistics,
    query_spectral_indices,
)


class TestFluxMonitoring:
    """Test flux calibration monitoring system."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    def test_create_tables(self, temp_db):
        """Test table creation."""
        assert create_flux_monitoring_tables(temp_db)

        # Verify tables exist
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()

        assert "calibration_monitoring" in tables
        assert "flux_monitoring_alerts" in tables

    def test_record_measurement(self, temp_db):
        """Test recording calibration measurements."""
        create_flux_monitoring_tables(temp_db)

        measurement_id = record_calibration_measurement(
            calibrator_name="3C286",
            ms_path="/path/to/test.ms",
            observed_flux_jy=7.5,
            catalog_flux_jy=7.4,
            frequency_ghz=1.4,
            mjd=59000.0,
            timestamp_iso="2020-05-23T12:00:00",
            phase_rms_deg=10.0,
            amp_rms=0.05,
            flagged_fraction=0.1,
            db_path=temp_db,
        )

        assert measurement_id is not None

        # Verify stored
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT * FROM calibration_monitoring WHERE id=?", (measurement_id,))
        row = cur.fetchone()
        conn.close()

        assert row is not None
        assert row[1] == "3C286"  # calibrator_name
        assert abs(row[3] - 7.5) < 0.01  # observed_flux_jy
        assert abs(row[4] - 7.4) < 0.01  # catalog_flux_jy
        assert abs(row[5] - (7.5 / 7.4)) < 0.01  # flux_ratio

    def test_flux_trends(self, temp_db):
        """Test flux trend calculation."""
        create_flux_monitoring_tables(temp_db)

        # Record series of measurements with drift
        current_mjd = time.time() / 86400.0 + 40587.0
        for i in range(10):
            mjd = current_mjd - (9 - i) / 24.0  # Every hour for 10 hours
            # Simulate 30% drift from 1.0 to 1.3
            flux_ratio = 1.0 + 0.03 * i
            record_calibration_measurement(
                calibrator_name="3C286",
                ms_path=f"/path/test_{i}.ms",
                observed_flux_jy=7.4 * flux_ratio,
                catalog_flux_jy=7.4,
                frequency_ghz=1.4,
                mjd=mjd,
                db_path=temp_db,
            )

        # Calculate trends
        trends = calculate_flux_trends(
            calibrator_name="3C286", time_window_days=1.0, db_path=temp_db
        )

        assert "3C286" in trends
        stats = trends["3C286"]

        assert stats["n_measurements"] == 10
        assert abs(stats["mean_ratio"] - 1.135) < 0.1  # Mean around 1.135
        assert stats["drift_percent"] > 20.0  # Should show significant drift

    def test_stability_check(self, temp_db):
        """Test flux stability checking."""
        create_flux_monitoring_tables(temp_db)

        # Record stable measurements
        current_mjd = time.time() / 86400.0 + 40587.0
        for i in range(10):
            mjd = current_mjd - (9 - i) / 24.0
            # Stable within 5%
            flux_ratio = 1.0 + 0.01 * (i % 2)
            record_calibration_measurement(
                calibrator_name="3C48",
                ms_path=f"/path/stable_{i}.ms",
                observed_flux_jy=16.2 * flux_ratio,
                catalog_flux_jy=16.2,
                frequency_ghz=1.4,
                mjd=mjd,
                db_path=temp_db,
            )

        # Check stability - should be stable
        all_stable, issues = check_flux_stability(
            drift_threshold_percent=20.0, time_window_days=1.0, min_measurements=3, db_path=temp_db
        )

        assert all_stable
        assert len(issues) == 0

    def test_stability_alert(self, temp_db):
        """Test alerting on unstable calibration."""
        create_flux_monitoring_tables(temp_db)

        # Record measurements with large drift
        current_mjd = time.time() / 86400.0 + 40587.0
        for i in range(10):
            mjd = current_mjd - (9 - i) / 24.0
            # 40% drift
            flux_ratio = 1.0 + 0.04 * i
            record_calibration_measurement(
                calibrator_name="3C147",
                ms_path=f"/path/drift_{i}.ms",
                observed_flux_jy=22.4 * flux_ratio,
                catalog_flux_jy=22.4,
                frequency_ghz=1.4,
                mjd=mjd,
                db_path=temp_db,
            )

        # Check stability - should detect issue
        all_stable, issues = run_flux_monitoring_check(
            drift_threshold_percent=20.0,
            time_window_days=1.0,
            min_measurements=3,
            create_alerts=True,
            db_path=temp_db,
        )

        assert not all_stable
        assert len(issues) == 1
        assert issues[0]["calibrator_name"] == "3C147"
        assert issues[0]["drift_percent"] > 30.0

        # Verify alert created
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM flux_monitoring_alerts")
        alert_count = cur.fetchone()[0]
        conn.close()

        assert alert_count == 1


class TestSpectralIndex:
    """Test spectral index calculation system."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    def test_create_table(self, temp_db):
        """Test spectral indices table creation."""
        assert create_spectral_indices_table(temp_db)

        # Verify table exists
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()

        assert "spectral_indices" in tables

    def test_calculate_spectral_index(self):
        """Test spectral index calculation."""
        # Typical steep-spectrum source: α = -0.7
        # S_ν ∝ ν^(-0.7)
        # S(1.4 GHz) = 100 mJy, S(3 GHz) = 100 * (3/1.4)^(-0.7) ≈ 58.7 mJy

        freq1_ghz = 1.4
        freq2_ghz = 3.0
        flux1_mjy = 100.0
        target_alpha = -0.7
        flux2_mjy = flux1_mjy * (freq2_ghz / freq1_ghz) ** target_alpha

        alpha, alpha_err = calculate_spectral_index(
            freq1_ghz=freq1_ghz,
            freq2_ghz=freq2_ghz,
            flux1_mjy=flux1_mjy,
            flux2_mjy=flux2_mjy,
            flux1_err_mjy=5.0,
            flux2_err_mjy=3.0,
        )

        assert not np.isnan(alpha)
        assert abs(alpha - target_alpha) < 0.05  # Should be close to -0.7
        assert alpha_err is not None
        assert alpha_err > 0

    def test_flat_spectrum(self):
        """Test flat-spectrum source (α ≈ 0)."""
        alpha, _ = calculate_spectral_index(
            freq1_ghz=1.4, freq2_ghz=3.0, flux1_mjy=100.0, flux2_mjy=100.0
        )

        assert not np.isnan(alpha)
        assert abs(alpha) < 0.1  # Should be close to 0

    def test_inverted_spectrum(self):
        """Test inverted-spectrum source (α > 0)."""
        # Inverted spectrum: α = +0.5
        # S(3 GHz) > S(1.4 GHz)
        alpha, _ = calculate_spectral_index(
            freq1_ghz=1.4, freq2_ghz=3.0, flux1_mjy=100.0, flux2_mjy=155.6
        )

        assert not np.isnan(alpha)
        assert alpha > 0.4  # Positive spectral index

    def test_multifrequency_fit(self):
        """Test spectral index fit with multiple frequencies."""
        # Simulate data with α = -0.8
        freqs = [0.888, 1.4, 3.0, 10.0]
        s0 = 200.0  # Flux at 1 GHz
        true_alpha = -0.8
        fluxes = [s0 * (f / 1.0) ** true_alpha for f in freqs]

        alpha, alpha_err, quality = fit_spectral_index_multifreq(freqs, fluxes)

        assert not np.isnan(alpha)
        assert abs(alpha - true_alpha) < 0.05
        assert quality in ["good", "fair"]
        assert alpha_err < 0.1  # Should have good fit

    def test_store_and_query(self, temp_db):
        """Test storing and querying spectral indices."""
        create_spectral_indices_table(temp_db)

        # Store spectral index
        from dsa110_contimg.catalog.spectral_index import store_spectral_index

        record_id = store_spectral_index(
            source_id="J123456+654321",
            ra_deg=188.64,
            dec_deg=65.72,
            spectral_index=-0.7,
            freq1_ghz=1.4,
            freq2_ghz=3.0,
            flux1_mjy=100.0,
            flux2_mjy=64.5,
            catalog1="NVSS",
            catalog2="VLASS",
            spectral_index_err=0.05,
            flux1_err_mjy=5.0,
            flux2_err_mjy=3.0,
            match_separation_arcsec=1.5,
            fit_quality="good",
            db_path=temp_db,
        )

        assert record_id is not None

        # Query by source ID
        result = get_spectral_index_for_source("J123456+654321", db_path=temp_db)
        assert result is not None
        assert abs(result["spectral_index"] - (-0.7)) < 0.01
        assert result["fit_quality"] == "good"

    def test_cone_search(self, temp_db):
        """Test spatial cone search for spectral indices."""
        create_spectral_indices_table(temp_db)

        from dsa110_contimg.catalog.spectral_index import store_spectral_index

        # Store several sources
        for i in range(5):
            ra = 180.0 + i * 0.1
            dec = 45.0 + i * 0.1
            store_spectral_index(
                source_id=f"J{ra:.2f}+{dec:.2f}",
                ra_deg=ra,
                dec_deg=dec,
                spectral_index=-0.7 - i * 0.1,
                freq1_ghz=1.4,
                freq2_ghz=3.0,
                flux1_mjy=100.0,
                flux2_mjy=60.0,
                catalog1="NVSS",
                catalog2="VLASS",
                db_path=temp_db,
            )

        # Cone search around first source
        results = query_spectral_indices(
            ra_deg=180.0, dec_deg=45.0, radius_deg=0.2, db_path=temp_db
        )

        assert len(results) >= 1  # Should find at least the first source

    def test_calculate_from_catalogs(self, temp_db):
        """Test calculating spectral indices from multiple catalogs."""
        create_spectral_indices_table(temp_db)

        # Simulate multi-catalog matches
        catalog_fluxes = {
            "RACS": (0.888, 250.0, 12.0),  # 888 MHz
            "NVSS": (1.4, 150.0, 7.0),  # 1.4 GHz
            "VLASS": (3.0, 80.0, 4.0),  # 3 GHz
        }

        record_ids = calculate_and_store_from_catalogs(
            source_id="J120000+450000",
            ra_deg=180.0,
            dec_deg=45.0,
            catalog_fluxes=catalog_fluxes,
            db_path=temp_db,
        )

        # Should create 3 pairwise combinations: RACS-NVSS, RACS-VLASS, NVSS-VLASS
        assert len(record_ids) == 3

        # Verify stored
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM spectral_indices WHERE source_id=?", ("J120000+450000",))
        count = cur.fetchone()[0]
        conn.close()

        assert count == 3

    def test_statistics(self, temp_db):
        """Test spectral index statistics."""
        create_spectral_indices_table(temp_db)

        from dsa110_contimg.catalog.spectral_index import store_spectral_index

        # Store sources with different spectral types
        test_cases = [
            ("steep1", -0.9, "good"),  # Steep spectrum
            ("steep2", -0.8, "good"),
            ("typical", -0.7, "fair"),  # Typical
            ("flat", -0.2, "good"),  # Flat spectrum
            ("inverted", +0.6, "poor"),  # Inverted spectrum
        ]

        for source_id, alpha, quality in test_cases:
            store_spectral_index(
                source_id=source_id,
                ra_deg=180.0,
                dec_deg=45.0,
                spectral_index=alpha,
                freq1_ghz=1.4,
                freq2_ghz=3.0,
                flux1_mjy=100.0,
                flux2_mjy=100.0,
                catalog1="NVSS",
                catalog2="VLASS",
                fit_quality=quality,
                db_path=temp_db,
            )

        stats = get_spectral_index_statistics(db_path=temp_db)

        assert stats["total_count"] == 5
        assert stats["steep_spectrum_count"] >= 2  # steep1, steep2
        assert stats["flat_spectrum_count"] >= 1  # flat
        assert stats["inverted_spectrum_count"] >= 1  # inverted
        assert "good" in stats["by_quality"]
        assert stats["by_quality"]["good"] >= 2
