"""Unit tests for multi-frequency analysis.

Focus: Fast tests for multi-frequency ESE detection.
Task 4.1: Multi-Frequency Analysis
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

from dsa110_contimg.photometry.multi_frequency import (
    analyze_frequency_correlation,
    detect_ese_multi_frequency,
    calculate_composite_significance,
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
            frequency_mhz REAL,
            n_obs INTEGER DEFAULT 0,
            mean_flux_mjy REAL,
            std_flux_mjy REAL,
            sigma_deviation REAL,
            updated_at REAL NOT NULL
        )
        """
    )
    
    conn.commit()
    conn.close()
    return db_path


class TestMultiFrequencyAnalysis:
    """Test suite for multi-frequency analysis."""

    def test_frequency_correlation_correlated(self, temp_products_db):
        """Test frequency correlation detection."""
        if analyze_frequency_correlation is None:
            pytest.skip("analyze_frequency_correlation not yet implemented")
        
        # Arrange: Add variability at multiple frequencies
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        frequencies = [1400.0, 1500.0, 1600.0]
        source_id = "FREQ001"
        
        for freq in frequencies:
            cursor.execute(
                """
                INSERT INTO variability_stats 
                (source_id, ra_deg, dec_deg, frequency_mhz, n_obs, mean_flux_mjy, 
                 std_flux_mjy, sigma_deviation, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"{source_id}_{freq:.0f}", 120.0, 45.0, freq, 10, 50.0, 5.0, 4.0, time.time())
            )
        conn.commit()
        conn.close()
        
        # Act: Analyze frequency correlation
        correlation = analyze_frequency_correlation(source_id, frequencies, temp_products_db)
        
        # Assert: Should detect correlation
        assert correlation['strength'] > 0.5, "Should detect frequency correlation"
        assert correlation['is_correlated'], "Should be marked as correlated"

    def test_frequency_correlation_not_correlated(self, temp_products_db):
        """Test no frequency correlation."""
        if analyze_frequency_correlation is None:
            pytest.skip("analyze_frequency_correlation not yet implemented")
        
        # Arrange: Variability at one frequency only
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        frequencies = [1400.0, 1500.0, 1600.0]
        source_id = "FREQ002"
        
        # Only one frequency has variability
        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, frequency_mhz, n_obs, mean_flux_mjy, 
             std_flux_mjy, sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (f"{source_id}_1400", 120.0, 45.0, 1400.0, 10, 50.0, 5.0, 4.0, time.time())
        )
        # Other frequencies have no variability
        for freq in [1500.0, 1600.0]:
            cursor.execute(
                """
                INSERT INTO variability_stats 
                (source_id, ra_deg, dec_deg, frequency_mhz, n_obs, mean_flux_mjy, 
                 std_flux_mjy, sigma_deviation, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"{source_id}_{freq:.0f}", 120.0, 45.0, freq, 10, 50.0, 1.0, 0.5, time.time())
            )
        conn.commit()
        conn.close()
        
        # Act: Analyze frequency correlation
        correlation = analyze_frequency_correlation(source_id, frequencies, temp_products_db)
        
        # Assert: Should not detect correlation
        assert not correlation['is_correlated'], "Should not detect correlation"

    def test_composite_significance_with_correlation(self):
        """Test composite significance calculation."""
        if calculate_composite_significance is None:
            pytest.skip("calculate_composite_significance not yet implemented")
        
        # Arrange: Base significance and correlation
        base_significance = 5.0
        correlation_strength = 0.8
        
        # Act: Calculate composite significance
        composite = calculate_composite_significance(base_significance, correlation_strength)
        
        # Assert: Should include correlation boost
        # Expected: 5.0 * (1.0 + 0.8 * 0.3) = 5.0 * 1.24 = 6.2
        expected = base_significance * (1.0 + correlation_strength * 0.3)
        assert abs(composite - expected) < 0.01, \
            f"Expected ≈ {expected}, got {composite}"

    def test_detect_ese_multi_frequency(self, temp_products_db):
        """Test multi-frequency ESE detection."""
        if detect_ese_multi_frequency is None:
            pytest.skip("detect_ese_multi_frequency not yet implemented")
        
        # Arrange: Add source with multi-frequency data
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "MULTIFREQ001"
        frequencies = [1400.0, 1500.0, 1600.0]
        
        for freq in frequencies:
            cursor.execute(
                """
                INSERT INTO variability_stats 
                (source_id, ra_deg, dec_deg, frequency_mhz, n_obs, mean_flux_mjy, 
                 std_flux_mjy, sigma_deviation, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"{source_id}_{freq:.0f}", 120.0, 45.0, freq, 10, 50.0, 5.0, 4.0, time.time())
            )
        conn.commit()
        conn.close()
        
        # Act: Detect ESE with multi-frequency
        result = detect_ese_multi_frequency(source_id, frequencies, temp_products_db, min_sigma=3.0)
        
        # Assert: Should return detection result
        assert result is not None, "Should return detection result"
        assert 'significance' in result, "Result should include significance"
        assert 'correlation' in result, "Result should include correlation analysis"

    def test_missing_frequencies(self, temp_products_db):
        """Test handling of missing frequencies."""
        if detect_ese_multi_frequency is None:
            pytest.skip("detect_ese_multi_frequency not yet implemented")
        
        # Arrange: Some frequencies missing
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "MISSFREQ001"
        
        # Only one frequency available
        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, frequency_mhz, n_obs, mean_flux_mjy, 
             std_flux_mjy, sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (f"{source_id}_1400", 120.0, 45.0, 1400.0, 10, 50.0, 5.0, 4.0, time.time())
        )
        conn.commit()
        conn.close()
        
        # Act: Detect with multiple frequencies (some missing)
        frequencies = [1400.0, 1500.0, 1600.0]
        result = detect_ese_multi_frequency(source_id, frequencies, temp_products_db, min_sigma=3.0)
        
        # Assert: Should handle gracefully
        assert result is not None, "Should handle missing frequencies"

    def test_single_frequency(self, temp_products_db):
        """Test single frequency handling."""
        if detect_ese_multi_frequency is None:
            pytest.skip("detect_ese_multi_frequency not yet implemented")
        
        # Arrange: Single frequency
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "SINGLEFREQ001"
        
        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, frequency_mhz, n_obs, mean_flux_mjy, 
             std_flux_mjy, sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (f"{source_id}_1400", 120.0, 45.0, 1400.0, 10, 50.0, 5.0, 4.0, time.time())
        )
        conn.commit()
        conn.close()
        
        # Act: Detect with single frequency
        result = detect_ese_multi_frequency(source_id, [1400.0], temp_products_db, min_sigma=3.0)
        
        # Assert: Should fall back to single-frequency analysis
        assert result is not None, "Should handle single frequency"

    def test_multi_frequency_smoke(self, temp_products_db):
        """End-to-end smoke test."""
        if detect_ese_multi_frequency is None:
            pytest.skip("detect_ese_multi_frequency not yet implemented")
        
        # Arrange: Add source with multi-frequency data
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_id = "SMOKEFREQ001"
        frequencies = [1400.0, 1500.0, 1600.0]
        
        for freq in frequencies:
            cursor.execute(
                """
                INSERT INTO variability_stats 
                (source_id, ra_deg, dec_deg, frequency_mhz, n_obs, mean_flux_mjy, 
                 std_flux_mjy, sigma_deviation, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"{source_id}_{freq:.0f}", 120.0, 45.0, freq, 10, 50.0, 5.0, 4.0, time.time())
            )
        conn.commit()
        conn.close()
        
        # Act: Detect ESE with multi-frequency
        result = detect_ese_multi_frequency(source_id, frequencies, temp_products_db, min_sigma=3.0)
        
        # Assert: Should return valid result
        assert result is not None, "Should return detection result"
        assert 'significance' in result, "Result should include significance"

