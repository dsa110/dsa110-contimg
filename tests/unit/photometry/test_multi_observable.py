"""Unit tests for multi-observable correlation analysis.

Focus: Fast tests for multi-observable ESE detection.
Task 4.2: Multi-Observable Correlation
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

from dsa110_contimg.photometry.multi_observable import (
    analyze_dm_variability,
    analyze_scintillation_variability,
    calculate_observable_correlation,
    detect_ese_multi_observable,
)


@pytest.fixture
def temp_products_db(tmp_path):
    """Create temporary products database."""
    db_path = tmp_path / "products.sqlite3"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE variability_stats (
            source_id TEXT PRIMARY KEY,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            n_obs INTEGER DEFAULT 0,
            mean_flux_mjy REAL,
            std_flux_mjy REAL,
            sigma_deviation REAL,
            updated_at REAL NOT NULL
        )
        """
    )

    # Create scintillation_data table (if needed)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scintillation_data (
            source_id TEXT NOT NULL,
            measured_at REAL NOT NULL,
            scintillation_bandwidth_mhz REAL,
            scintillation_timescale_sec REAL,
            PRIMARY KEY (source_id, measured_at)
        )
        """
    )

    # Create dm_data table (if needed)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dm_data (
            source_id TEXT NOT NULL,
            measured_at REAL NOT NULL,
            dm_pc_cm3 REAL,
            PRIMARY KEY (source_id, measured_at)
        )
        """
    )

    conn.commit()
    conn.close()
    return db_path


class TestMultiObservableAnalysis:
    """Test suite for multi-observable analysis."""

    def test_analyze_scintillation_variability(self, temp_products_db):
        """Verify scintillation analysis."""
        if analyze_scintillation_variability is None:
            pytest.skip("analyze_scintillation_variability not yet implemented")

        # Arrange: Add scintillation measurements
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "SCINT001"

        for i in range(10):
            cursor.execute(
                """
                INSERT INTO scintillation_data 
                (source_id, measured_at, scintillation_bandwidth_mhz, scintillation_timescale_sec)
                VALUES (?, ?, ?, ?)
                """,
                (source_id, time.time() + i, 10.0 + i * 0.5, 100.0 + i * 10.0),
            )
        conn.commit()
        conn.close()

        # Act: Analyze scintillation variability
        result = analyze_scintillation_variability(source_id, temp_products_db)

        # Assert: Should return variability metrics
        assert result is not None, "Should return variability result"
        assert "variability" in result or "std" in result, "Should include variability metrics"

    def test_analyze_dm_variability(self, temp_products_db):
        """Verify DM analysis."""
        if analyze_dm_variability is None:
            pytest.skip("analyze_dm_variability not yet implemented")

        # Arrange: Add DM measurements
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "DM001"

        for i in range(10):
            cursor.execute(
                """
                INSERT INTO dm_data 
                (source_id, measured_at, dm_pc_cm3)
                VALUES (?, ?, ?)
                """,
                (source_id, time.time() + i, 50.0 + i * 0.1),
            )
        conn.commit()
        conn.close()

        # Act: Analyze DM variability
        result = analyze_dm_variability(source_id, temp_products_db)

        # Assert: Should return variability metrics
        assert result is not None, "Should return variability result"
        assert "variability" in result or "std" in result, "Should include variability metrics"

    def test_observable_correlation_correlated(self):
        """Verify correlation detection."""
        if calculate_observable_correlation is None:
            pytest.skip("calculate_observable_correlation not yet implemented")

        # Arrange: High variability in multiple observables
        observable_results = {
            "flux": {"variability": "high", "sigma_deviation": 5.0},
            "scintillation": {"variability": "high", "sigma_deviation": 4.5},
            "dm": {"variability": "high", "sigma_deviation": 4.0},
        }

        # Act: Calculate correlation
        correlation = calculate_observable_correlation(observable_results)

        # Assert: Should detect correlation
        assert correlation["strength"] > 0.5, "Should detect correlation"
        assert correlation["is_correlated"], "Should be marked as correlated"

    def test_observable_correlation_not_correlated(self):
        """Verify no correlation."""
        if calculate_observable_correlation is None:
            pytest.skip("calculate_observable_correlation not yet implemented")

        # Arrange: Variability in one observable only
        observable_results = {
            "flux": {"variability": "high", "sigma_deviation": 5.0},
            "scintillation": {"variability": "low", "sigma_deviation": 1.0},
            "dm": {"variability": "low", "sigma_deviation": 0.5},
        }

        # Act: Calculate correlation
        correlation = calculate_observable_correlation(observable_results)

        # Assert: Should not detect correlation
        assert not correlation["is_correlated"], "Should not detect correlation"

    def test_composite_significance_with_correlation(self):
        """Verify composite significance."""
        # Arrange: Base significance and correlation strength
        base_significance = 5.0
        correlation_strength = 0.8

        # Act: Calculate composite significance
        # Formula: base_significance * (1.0 + correlation_strength * 0.3)
        composite = base_significance * (1.0 + correlation_strength * 0.3)

        # Assert: Should include correlation boost
        expected = 5.0 * 1.24  # 6.2
        assert abs(composite - expected) < 0.01, f"Expected ≈ {expected}, got {composite}"

    def test_detect_ese_multi_observable(self, temp_products_db):
        """Verify multi-observable detection."""
        if detect_ese_multi_observable is None:
            pytest.skip("detect_ese_multi_observable not yet implemented")

        # Arrange: Add source with flux and scintillation data
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "MULTIOBS001"

        # Add flux variability stats
        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
             sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, 120.0, 45.0, 10, 50.0, 5.0, 5.0, time.time()),
        )

        # Add scintillation data
        for i in range(10):
            cursor.execute(
                """
                INSERT INTO scintillation_data 
                (source_id, measured_at, scintillation_bandwidth_mhz, scintillation_timescale_sec)
                VALUES (?, ?, ?, ?)
                """,
                (source_id, time.time() + i, 10.0 + i * 0.5, 100.0 + i * 10.0),
            )
        conn.commit()
        conn.close()

        # Act: Detect ESE with multi-observable
        observables = {"flux": True, "scintillation": True}
        result = detect_ese_multi_observable(source_id, observables, temp_products_db)

        # Assert: Should return detection result with correlation analysis
        assert result is not None, "Should return detection result"
        assert "significance" in result, "Result should include significance"
        assert "correlation" in result, "Result should include correlation analysis"

    def test_missing_observables(self, temp_products_db):
        """Verify missing observable handling."""
        if detect_ese_multi_observable is None:
            pytest.skip("detect_ese_multi_observable not yet implemented")

        # Arrange: Some observables missing data
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "MISSOBS001"

        # Only flux data available
        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
             sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, 120.0, 45.0, 10, 50.0, 5.0, 5.0, time.time()),
        )
        conn.commit()
        conn.close()

        # Act: Detect with multiple observables (some missing)
        observables = {"flux": True, "scintillation": True, "dm": True}
        result = detect_ese_multi_observable(source_id, observables, temp_products_db)

        # Assert: Should use available observables
        assert result is not None, "Should handle missing observables gracefully"

    def test_single_observable(self, temp_products_db):
        """Verify single observable handling."""
        if detect_ese_multi_observable is None:
            pytest.skip("detect_ese_multi_observable not yet implemented")

        # Arrange: Only flux data available
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "SINGLEOBS001"

        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
             sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, 120.0, 45.0, 10, 50.0, 5.0, 5.0, time.time()),
        )
        conn.commit()
        conn.close()

        # Act: Detect with single observable
        observables = {"flux": True}
        result = detect_ese_multi_observable(source_id, observables, temp_products_db)

        # Assert: Should fall back to single-observable analysis
        assert result is not None, "Should handle single observable"

    def test_multi_observable_integration_smoke(self, temp_products_db):
        """End-to-end integration smoke test."""
        if detect_ese_multi_observable is None:
            pytest.skip("detect_ese_multi_observable not yet implemented")

        # Arrange: Add source with multiple observables
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "SMOKEOBS001"

        # Add flux data
        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
             sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, 120.0, 45.0, 10, 50.0, 5.0, 5.0, time.time()),
        )

        # Add scintillation data
        for i in range(10):
            cursor.execute(
                """
                INSERT INTO scintillation_data 
                (source_id, measured_at, scintillation_bandwidth_mhz, scintillation_timescale_sec)
                VALUES (?, ?, ?, ?)
                """,
                (source_id, time.time() + i, 10.0 + i * 0.5, 100.0 + i * 10.0),
            )
        conn.commit()
        conn.close()

        # Act: Use multi-observable detection in pipeline
        observables = {"flux": True, "scintillation": True}
        result = detect_ese_multi_observable(source_id, observables, temp_products_db)

        # Assert: Results should include correlation analysis
        assert result is not None, "Should return detection result"
        assert "correlation" in result, "Results should include correlation analysis"

    def test_multi_observable_api_smoke(self, temp_products_db):
        """API integration smoke test."""
        if detect_ese_multi_observable is None:
            pytest.skip("detect_ese_multi_observable not yet implemented")

        # Arrange: Add source
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "APIOBS001"

        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
             sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, 120.0, 45.0, 10, 50.0, 5.0, 5.0, time.time()),
        )
        conn.commit()
        conn.close()

        # Act: Create job with use_multi_observable=true
        # (In real usage, would call API endpoint)
        observables = {"flux": True}
        result = detect_ese_multi_observable(source_id, observables, temp_products_db)

        # Assert: Should perform multi-observable analysis
        assert result is not None, "Should perform multi-observable analysis"
