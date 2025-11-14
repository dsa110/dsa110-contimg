"""Smoke tests for ESE detection end-to-end flow.

Focus: Quick validation that all components work together.
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path

import pytest

from dsa110_contimg.photometry.ese_detection import detect_ese_candidates


@pytest.fixture
def smoke_test_db(tmp_path):
    """Create complete test database for smoke tests."""
    db_path = tmp_path / "smoke_test.sqlite3"
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

    # Add test data
    now = time.time()
    test_sources = [
        (
            "smoke_source_001",
            120.0,
            45.0,
            100.0,
            10,
            50.0,
            5.0,
            45.0,
            55.0,
            2.5,
            6.5,
            None,
            now,
            60000.0,
            now,
        ),
        (
            "smoke_source_002",
            121.0,
            46.0,
            150.0,
            15,
            75.0,
            3.0,
            70.0,
            80.0,
            1.8,
            4.2,
            None,
            now,
            60001.0,
            now,
        ),
        (
            "smoke_source_003",
            122.0,
            47.0,
            200.0,
            20,
            100.0,
            8.0,
            90.0,
            110.0,
            3.2,
            7.8,
            None,
            now,
            60002.0,
            now,
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO variability_stats 
        (source_id, ra_deg, dec_deg, nvss_flux_mjy, n_obs, mean_flux_mjy, 
         std_flux_mjy, min_flux_mjy, max_flux_mjy, chi2_nu, sigma_deviation,
         last_measured_at, last_mjd, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        test_sources,
    )

    conn.commit()
    conn.close()
    return db_path


class TestESEDetectionSmoke:
    """Smoke tests for ESE detection end-to-end."""

    def test_smoke_detect_all_sources(self, smoke_test_db):
        """Smoke test: Detect ESE candidates from all sources."""
        candidates = detect_ese_candidates(
            products_db=smoke_test_db,
            min_sigma=5.0,
            source_id=None,
            recompute=False,
        )

        # Should detect 2 sources (6.5 and 7.8 sigma)
        assert len(candidates) == 2
        source_ids = {c["source_id"] for c in candidates}
        assert "smoke_source_001" in source_ids
        assert "smoke_source_003" in source_ids

    def test_smoke_detect_specific_source(self, smoke_test_db):
        """Smoke test: Detect ESE candidate for specific source."""
        candidates = detect_ese_candidates(
            products_db=smoke_test_db,
            min_sigma=5.0,
            source_id="smoke_source_001",
            recompute=False,
        )

        assert len(candidates) == 1
        assert candidates[0]["source_id"] == "smoke_source_001"
        assert candidates[0]["significance"] == 6.5

    def test_smoke_detect_verify_database(self, smoke_test_db):
        """Smoke test: Verify candidates are stored in database."""
        candidates = detect_ese_candidates(
            products_db=smoke_test_db,
            min_sigma=5.0,
            recompute=False,
        )

        # Verify database records
        conn = sqlite3.connect(smoke_test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ese_candidates WHERE status = 'active'")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 2
        assert len(candidates) == count

    def test_smoke_detect_idempotent(self, smoke_test_db):
        """Smoke test: Running detection twice doesn't create duplicates."""
        # First run
        candidates1 = detect_ese_candidates(
            products_db=smoke_test_db,
            min_sigma=5.0,
            recompute=False,
        )

        # Second run
        candidates2 = detect_ese_candidates(
            products_db=smoke_test_db,
            min_sigma=5.0,
            recompute=False,
        )

        # Should have same candidates (no duplicates)
        assert len(candidates1) == len(candidates2) == 2

        # Verify no duplicate database records
        conn = sqlite3.connect(smoke_test_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM ese_candidates 
            WHERE status = 'active' AND source_id IN ('smoke_source_001', 'smoke_source_003')
            """
        )
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 2  # One per source, not duplicates
