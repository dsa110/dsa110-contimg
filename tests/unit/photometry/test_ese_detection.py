"""Unit tests for ESE detection functionality.

Focus: Fast tests for ESE candidate detection with mocked dependencies.
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from dsa110_contimg.photometry.ese_detection import detect_ese_candidates


@pytest.fixture
def temp_products_db(tmp_path):
    """Create temporary products database with required tables."""
    db_path = tmp_path / "products.sqlite3"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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

    # Create photometry table (for recompute test)
    cursor.execute(
        """
        CREATE TABLE photometry (
            source_id TEXT,
            ra_deg REAL,
            dec_deg REAL,
            nvss_flux_mjy REAL,
            peak_jyb REAL,
            peak_err_jyb REAL,
            measured_at REAL,
            mjd REAL
        )
        """
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_variability_stats(temp_products_db):
    """Add sample variability statistics to database."""
    conn = sqlite3.connect(temp_products_db)
    cursor = conn.cursor()

    # Add sources with different sigma deviations
    sources = [
        ("source_001", 120.0, 45.0, 100.0, 10, 50.0, 5.0, 45.0,
         55.0, 2.5, 6.5, None, time.time(), 60000.0, time.time()),
        ("source_002", 121.0, 46.0, 150.0, 15, 75.0, 3.0, 70.0,
         80.0, 1.8, 4.2, None, time.time(), 60001.0, time.time()),
        ("source_003", 122.0, 47.0, 200.0, 20, 100.0, 8.0, 90.0,
         110.0, 3.2, 7.8, None, time.time(), 60002.0, time.time()),
    ]

    cursor.executemany(
        """
        INSERT INTO variability_stats 
        (source_id, ra_deg, dec_deg, nvss_flux_mjy, n_obs, mean_flux_mjy, 
         std_flux_mjy, min_flux_mjy, max_flux_mjy, chi2_nu, sigma_deviation,
         eta_metric, last_measured_at, last_mjd, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        sources,
    )

    conn.commit()
    conn.close()


class TestDetectESECandidates:
    """Test detect_ese_candidates function."""

    def test_detect_ese_candidates_all_sources(self, temp_products_db, sample_variability_stats):
        """Test detecting ESE candidates from all sources."""
        candidates = detect_ese_candidates(
            products_db=temp_products_db,
            min_sigma=5.0,
            source_id=None,
            recompute=False,
        )

        # Should detect source_001 (6.5) and source_003 (7.8), but not source_002 (4.2)
        assert len(candidates) == 2
        source_ids = {c["source_id"] for c in candidates}
        assert "source_001" in source_ids
        assert "source_003" in source_ids
        assert "source_002" not in source_ids

        # Verify candidate details
        for cand in candidates:
            assert "source_id" in cand
            assert "significance" in cand
            assert cand["significance"] >= 5.0
            assert "ra_deg" in cand
            assert "dec_deg" in cand

    def test_detect_ese_candidates_specific_source(self, temp_products_db, sample_variability_stats):
        """Test detecting ESE candidate for specific source."""
        candidates = detect_ese_candidates(
            products_db=temp_products_db,
            min_sigma=5.0,
            source_id="source_001",
            recompute=False,
        )

        assert len(candidates) == 1
        assert candidates[0]["source_id"] == "source_001"
        assert candidates[0]["significance"] == 6.5

    def test_detect_ese_candidates_higher_threshold(self, temp_products_db, sample_variability_stats):
        """Test with higher sigma threshold."""
        candidates = detect_ese_candidates(
            products_db=temp_products_db,
            min_sigma=7.0,
            source_id=None,
            recompute=False,
        )

        # Should only detect source_003 (7.8)
        assert len(candidates) == 1
        assert candidates[0]["source_id"] == "source_003"

    def test_detect_ese_candidates_no_matches(self, temp_products_db, sample_variability_stats):
        """Test with threshold too high."""
        candidates = detect_ese_candidates(
            products_db=temp_products_db,
            min_sigma=10.0,
            source_id=None,
            recompute=False,
        )

        assert len(candidates) == 0

    def test_detect_ese_candidates_updates_existing(self, temp_products_db, sample_variability_stats):
        """Test that existing candidates are updated if significance increases."""
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()

        # Pre-flag source_001 with lower significance
        cursor.execute(
            """
            INSERT INTO ese_candidates 
            (source_id, flagged_at, flagged_by, significance, flag_type, status)
            VALUES (?, ?, 'auto', ?, 'auto', 'active')
            """,
            ("source_001", time.time(), 5.5),
        )
        conn.commit()
        conn.close()

        # Run detection - should update existing candidate
        candidates = detect_ese_candidates(
            products_db=temp_products_db,
            min_sigma=5.0,
            source_id="source_001",
            recompute=False,
        )

        assert len(candidates) == 1
        assert candidates[0]["significance"] == 6.5

        # Verify update in database
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT significance FROM ese_candidates WHERE source_id = ?",
            ("source_001",),
        )
        row = cursor.fetchone()
        assert row[0] == 6.5
        conn.close()

    def test_detect_ese_candidates_missing_database(self, tmp_path):
        """Test handling of missing database."""
        missing_db = tmp_path / "missing.sqlite3"
        candidates = detect_ese_candidates(
            products_db=missing_db,
            min_sigma=5.0,
        )

        assert len(candidates) == 0

    def test_detect_ese_candidates_missing_tables(self, tmp_path):
        """Test handling of missing tables."""
        db_path = tmp_path / "empty.sqlite3"
        conn = sqlite3.connect(db_path)
        conn.close()

        candidates = detect_ese_candidates(
            products_db=db_path,
            min_sigma=5.0,
        )

        assert len(candidates) == 0

    @patch("dsa110_contimg.photometry.ese_detection._recompute_variability_stats")
    def test_detect_ese_candidates_recompute(self, mock_recompute, temp_products_db, sample_variability_stats):
        """Test recompute flag triggers variability stats recomputation."""
        candidates = detect_ese_candidates(
            products_db=temp_products_db,
            min_sigma=5.0,
            recompute=True,
        )

        mock_recompute.assert_called_once()
        assert len(candidates) == 2

    def test_detect_ese_candidates_empty_database(self, temp_products_db):
        """Test with empty variability_stats table."""
        candidates = detect_ese_candidates(
            products_db=temp_products_db,
            min_sigma=5.0,
        )

        assert len(candidates) == 0
