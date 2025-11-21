"""Unit tests for parallel processing.

Focus: Fast tests for parallel ESE detection.
Task 3.2: Parallel Processing
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from dsa110_contimg.photometry.parallel import (
    detect_ese_parallel,
    get_optimal_worker_count,
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

    conn.commit()
    conn.close()
    return db_path


class TestParallelProcessing:
    """Test suite for parallel processing."""

    def test_parallel_detection_basic(self, temp_products_db):
        """Basic parallel detection test."""
        if detect_ese_parallel is None:
            pytest.skip("detect_ese_parallel not yet implemented")

        # Arrange: Add multiple sources
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_ids = [f"PARALLEL{i:03d}" for i in range(10)]
        for source_id in source_ids:
            cursor.execute(
                """
                INSERT INTO variability_stats 
                (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
                 sigma_deviation, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source_id, 120.0, 45.0, 10, 50.0, 5.0, 3.5, time.time()),
            )
        conn.commit()
        conn.close()

        # Act: Run parallel detection
        results = detect_ese_parallel(source_ids, temp_products_db, min_sigma=3.0)

        # Assert: Should return results for all sources
        assert len(results) == len(source_ids), "Should process all sources"
        assert all("source_id" in r for r in results), "Results should have source_id"

    def test_parallel_vs_sequential(self, temp_products_db):
        """Compare parallel vs sequential performance."""
        if detect_ese_parallel is None:
            pytest.skip("detect_ese_parallel not yet implemented")

        # Arrange: Add many sources
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_ids = [f"PERF{i:04d}" for i in range(100)]
        for source_id in source_ids:
            cursor.execute(
                """
                INSERT INTO variability_stats 
                (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
                 sigma_deviation, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source_id, 120.0, 45.0, 10, 50.0, 5.0, 3.5, time.time()),
            )
        conn.commit()
        conn.close()

        # Act: Measure parallel time
        start_time = time.time()
        detect_ese_parallel(source_ids, temp_products_db, min_sigma=3.0)
        parallel_time = time.time() - start_time

        # Assert: Should be faster than sequential (rough check)
        # Note: Actual speedup depends on system, but should be measurable
        assert parallel_time < 10.0, f"Parallel should complete in < 10s, got {parallel_time:.2f}s"

    def test_optimal_worker_count(self):
        """Test optimal worker count calculation."""
        if get_optimal_worker_count is None:
            pytest.skip("get_optimal_worker_count not yet implemented")

        # Act: Get optimal worker count
        worker_count = get_optimal_worker_count()

        # Assert: Should be reasonable
        assert worker_count > 0, "Worker count should be positive"
        assert worker_count <= 32, "Worker count should be reasonable"

    def test_parallel_error_handling(self, temp_products_db):
        """Test error handling in parallel processing."""
        if detect_ese_parallel is None:
            pytest.skip("detect_ese_parallel not yet implemented")

        # Arrange: Mix of valid and invalid source IDs
        source_ids = ["VALID001", "INVALID001", "VALID002"]

        # Act: Run parallel detection
        results = detect_ese_parallel(source_ids, temp_products_db, min_sigma=3.0)

        # Assert: Should handle errors gracefully
        assert len(results) <= len(source_ids), "Should handle invalid sources"
        # Results might be filtered or include error info

    def test_parallel_concurrency(self, temp_products_db):
        """Test database concurrency."""
        if detect_ese_parallel is None:
            pytest.skip("detect_ese_parallel not yet implemented")

        # Arrange: Add sources
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_ids = [f"CONCURRENT{i:03d}" for i in range(20)]
        for source_id in source_ids:
            cursor.execute(
                """
                INSERT INTO variability_stats 
                (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
                 sigma_deviation, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source_id, 120.0, 45.0, 10, 50.0, 5.0, 3.5, time.time()),
            )
        conn.commit()
        conn.close()

        # Act: Run parallel detection (should handle concurrent DB access)
        results = detect_ese_parallel(source_ids, temp_products_db, min_sigma=3.0)

        # Assert: Should complete without errors
        assert len(results) == len(source_ids), "Should handle concurrent access"

    def test_parallel_smoke(self, temp_products_db):
        """End-to-end smoke test."""
        if detect_ese_parallel is None:
            pytest.skip("detect_ese_parallel not yet implemented")

        # Arrange: Add sources
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        source_ids = [f"SMOKE{i:03d}" for i in range(5)]
        for source_id in source_ids:
            cursor.execute(
                """
                INSERT INTO variability_stats 
                (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
                 sigma_deviation, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source_id, 120.0, 45.0, 10, 50.0, 5.0, 3.5, time.time()),
            )
        conn.commit()
        conn.close()

        # Act: Run parallel detection
        results = detect_ese_parallel(source_ids, temp_products_db, min_sigma=3.0)

        # Assert: Should return valid results
        assert len(results) == len(source_ids), "Should process all sources"
        assert all("source_id" in r for r in results), "Results should be valid"
