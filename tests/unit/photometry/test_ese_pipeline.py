"""Unit tests for automated ESE detection pipeline.

Focus: Fast tests for automatic ESE detection after photometry measurements.
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from dsa110_contimg.photometry.ese_pipeline import (
    auto_detect_ese_after_photometry,
    auto_detect_ese_for_new_measurements,
    update_variability_stats_for_source,
)


@pytest.fixture
def temp_products_db(tmp_path):
    """Create temporary products database with required tables."""
    db_path = tmp_path / "products.sqlite3"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create photometry table
    cursor.execute(
        """
        CREATE TABLE photometry (
            image_path TEXT,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            nvss_flux_mjy REAL,
            peak_jyb REAL NOT NULL,
            peak_err_jyb REAL,
            measured_at REAL NOT NULL,
            source_id TEXT,
            mjd REAL
        )
        """
    )

    # Create variability_stats table
    cursor.execute(
        """
        CREATE TABLE variability_stats (
            source_id TEXT PRIMARY KEY,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            nvss_flux_mjy REAL,
            n_obs INTEGER DEFAULT 0,
            mean_flux_mjy REAL,
            std_flux_mjy REAL,
            min_flux_mjy REAL,
            max_flux_mjy REAL,
            chi2_nu REAL,
            sigma_deviation REAL,
            eta_metric REAL,
            last_measured_at REAL,
            last_mjd REAL,
            updated_at REAL NOT NULL
        )
        """
    )

    # Create ese_candidates table
    cursor.execute(
        """
        CREATE TABLE ese_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            flagged_at REAL NOT NULL,
            flagged_by TEXT DEFAULT 'auto',
            significance REAL NOT NULL,
            flag_type TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'active',
            investigated_at REAL,
            dismissed_at REAL,
            FOREIGN KEY (source_id) REFERENCES variability_stats(source_id)
        )
        """
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_photometry_data(temp_products_db):
    """Add sample photometry measurements."""
    conn = sqlite3.connect(temp_products_db)
    cursor = conn.cursor()

    source_id = "J120000+450000"
    now = time.time()
    mjd_base = 60000.0

    # Add multiple measurements for same source (showing variability)
    measurements = [
        ("image1.fits", 120.0, 45.0, 100.0, 0.05, 0.002, now - 86400 * 5, source_id, mjd_base - 5),
        ("image2.fits", 120.0, 45.0, 100.0, 0.06, 0.002, now - 86400 * 4, source_id, mjd_base - 4),
        ("image3.fits", 120.0, 45.0, 100.0, 0.07, 0.002, now - 86400 * 3, source_id, mjd_base - 3),
        ("image4.fits", 120.0, 45.0, 100.0, 0.08, 0.002, now - 86400 * 2, source_id, mjd_base - 2),
        (
            "image5.fits",
            120.0,
            45.0,
            100.0,
            0.12,
            0.002,
            now - 86400 * 1,
            source_id,
            mjd_base - 1,
        ),  # High flux
    ]

    cursor.executemany(
        """
        INSERT INTO photometry 
        (image_path, ra_deg, dec_deg, nvss_flux_mjy, peak_jyb, peak_err_jyb, measured_at, source_id, mjd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        measurements,
    )

    conn.commit()
    conn.close()


class TestUpdateVariabilityStatsForSource:
    """Test update_variability_stats_for_source function."""

    def test_update_stats_success(self, temp_products_db, sample_photometry_data):
        """Test updating variability stats for a source."""
        conn = sqlite3.connect(temp_products_db)
        source_id = "J120000+450000"

        result = update_variability_stats_for_source(conn, source_id)

        assert result is True

        # Verify stats were inserted
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM variability_stats WHERE source_id = ?", (source_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[5] == 5  # n_obs
        assert row[9] > 0  # sigma_deviation (should be > 0 due to variability)

        conn.close()

    def test_update_stats_no_photometry(self, temp_products_db):
        """Test updating stats when no photometry data exists."""
        conn = sqlite3.connect(temp_products_db)
        source_id = "J999999+999999"

        result = update_variability_stats_for_source(conn, source_id)

        assert result is False
        conn.close()

    def test_update_stats_idempotent(self, temp_products_db, sample_photometry_data):
        """Test that updating stats multiple times is idempotent."""
        conn = sqlite3.connect(temp_products_db)
        source_id = "J120000+450000"

        # First update
        result1 = update_variability_stats_for_source(conn, source_id)
        conn.commit()
        assert result1 is True

        # Get first sigma_deviation
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sigma_deviation FROM variability_stats WHERE source_id = ?",
            (source_id,),
        )
        sigma1 = cursor.fetchone()[0]

        # Second update (should update, not duplicate)
        result2 = update_variability_stats_for_source(conn, source_id)
        conn.commit()
        assert result2 is True

        # Verify only one record exists
        cursor.execute("SELECT COUNT(*) FROM variability_stats WHERE source_id = ?", (source_id,))
        count = cursor.fetchone()[0]
        assert count == 1

        conn.close()


class TestAutoDetectESEForNewMeasurements:
    """Test auto_detect_ese_for_new_measurements function."""

    def test_auto_detect_no_candidate(self, temp_products_db, sample_photometry_data):
        """Test auto-detection when source doesn't qualify as ESE candidate."""
        source_id = "J120000+450000"

        candidate = auto_detect_ese_for_new_measurements(
            products_db=temp_products_db,
            source_id=source_id,
            min_sigma=10.0,  # High threshold
        )

        assert candidate is None

    def test_auto_detect_with_candidate(self, temp_products_db, sample_photometry_data):
        """Test auto-detection when source qualifies as ESE candidate."""
        source_id = "J120000+450000"

        # First update stats
        conn = sqlite3.connect(temp_products_db)
        update_variability_stats_for_source(conn, source_id)
        conn.commit()

        # Manually set high sigma_deviation to trigger detection
        conn.execute(
            """
            UPDATE variability_stats 
            SET sigma_deviation = 6.5 
            WHERE source_id = ?
            """,
            (source_id,),
        )
        conn.commit()
        conn.close()

        candidate = auto_detect_ese_for_new_measurements(
            products_db=temp_products_db,
            source_id=source_id,
            min_sigma=5.0,
        )

        assert candidate is not None
        assert candidate["source_id"] == source_id
        assert candidate["significance"] >= 5.0

    def test_auto_detect_missing_source(self, temp_products_db):
        """Test auto-detection for non-existent source."""
        candidate = auto_detect_ese_for_new_measurements(
            products_db=temp_products_db,
            source_id="J999999+999999",
            min_sigma=5.0,
        )

        assert candidate is None


class TestAutoDetectESEAfterPhotometry:
    """Test auto_detect_ese_after_photometry function."""

    def test_auto_detect_all_sources(self, temp_products_db, sample_photometry_data):
        """Test auto-detection for all sources."""
        candidates = auto_detect_ese_after_photometry(
            products_db=temp_products_db,
            source_ids=None,
            min_sigma=5.0,
            update_variability_stats=True,
        )

        # Should process all sources with photometry data
        assert isinstance(candidates, list)

    def test_auto_detect_specific_sources(self, temp_products_db, sample_photometry_data):
        """Test auto-detection for specific source IDs."""
        source_ids = ["J120000+450000"]

        candidates = auto_detect_ese_after_photometry(
            products_db=temp_products_db,
            source_ids=source_ids,
            min_sigma=5.0,
            update_variability_stats=True,
        )

        assert isinstance(candidates, list)

    def test_auto_detect_without_update_stats(self, temp_products_db, sample_photometry_data):
        """Test auto-detection without updating variability stats."""
        # Pre-populate variability stats
        conn = sqlite3.connect(temp_products_db)
        update_variability_stats_for_source(conn, "J120000+450000")
        conn.commit()
        conn.close()

        candidates = auto_detect_ese_after_photometry(
            products_db=temp_products_db,
            source_ids=None,
            min_sigma=5.0,
            update_variability_stats=False,
        )

        assert isinstance(candidates, list)

    def test_auto_detect_missing_database(self, tmp_path):
        """Test handling of missing database."""
        missing_db = tmp_path / "missing.sqlite3"

        candidates = auto_detect_ese_after_photometry(
            products_db=missing_db,
            min_sigma=5.0,
        )

        assert candidates == []
