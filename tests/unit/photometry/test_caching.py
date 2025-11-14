"""Unit tests for variability statistics caching.

Focus: Fast tests for caching system.
Task 3.1: Caching Variability Statistics
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from dsa110_contimg.photometry.caching import (
    CacheStats,
    get_cached_variability_stats,
    invalidate_cache,
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


class TestVariabilityCaching:
    """Test suite for variability statistics caching."""

    def test_cache_hit(self, temp_products_db):
        """Test cache hit scenario."""
        if get_cached_variability_stats is None:
            pytest.skip("get_cached_variability_stats not yet implemented")

        # Arrange: Add source to database
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
             sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("CACHE001", 120.0, 45.0, 10, 50.0, 5.0, 3.5, time.time()),
        )
        conn.commit()
        conn.close()

        # Act: Get cached stats
        stats = get_cached_variability_stats("CACHE001", temp_products_db)

        # Assert: Should return cached stats
        assert stats is not None, "Should return cached stats"
        assert stats["source_id"] == "CACHE001"
        assert stats["mean_flux_mjy"] == 50.0

    def test_cache_miss(self, temp_products_db):
        """Test cache miss scenario."""
        if get_cached_variability_stats is None:
            pytest.skip("get_cached_variability_stats not yet implemented")

        # Arrange: Source not in database
        source_id = "MISS001"

        # Act: Get cached stats
        stats = get_cached_variability_stats(source_id, temp_products_db)

        # Assert: Should return None or empty dict
        assert stats is None or stats == {}, "Cache miss should return None/empty"

    def test_cache_invalidation(self, temp_products_db):
        """Test cache invalidation."""
        if invalidate_cache is None:
            pytest.skip("invalidate_cache not yet implemented")

        # Arrange: Add source to cache
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
             sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("INVALIDATE001", 120.0, 45.0, 10, 50.0, 5.0, 3.5, time.time()),
        )
        conn.commit()
        conn.close()

        # Act: Invalidate cache
        invalidate_cache("INVALIDATE001", temp_products_db)

        # Assert: Cache should be invalidated
        # (Behavior depends on implementation - might remove or mark as stale)
        stats = get_cached_variability_stats("INVALIDATE001", temp_products_db)
        # Should either be None or require recomputation
        assert stats is None or stats.get("stale", False), "Cache should be invalidated"

    def test_cache_ttl_expiration(self, temp_products_db):
        """Test TTL expiration."""
        if get_cached_variability_stats is None:
            pytest.skip("get_cached_variability_stats not yet implemented")

        # Arrange: Add source with old timestamp
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        old_time = time.time() - 3600  # 1 hour ago
        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
             sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("TTL001", 120.0, 45.0, 10, 50.0, 5.0, 3.5, old_time),
        )
        conn.commit()
        conn.close()

        # Act: Get cached stats with short TTL
        stats = get_cached_variability_stats("TTL001", temp_products_db, ttl_seconds=300)

        # Assert: Should be expired (return None or stale)
        assert stats is None or stats.get("stale", False), "Expired cache should be stale"

    def test_cache_stats(self, temp_products_db):
        """Test cache statistics."""
        if CacheStats is None:
            pytest.skip("CacheStats not yet implemented")

        # Arrange: Use cache multiple times
        for i in range(5):
            get_cached_variability_stats(f"STATS{i:03d}", temp_products_db)

        # Act: Get cache stats
        stats = CacheStats.get_stats()

        # Assert: Should have stats
        assert stats is not None, "Should return cache statistics"
        assert "hits" in stats or "misses" in stats, "Should track hits/misses"

    def test_cache_performance(self, temp_products_db):
        """Performance test for caching."""
        if get_cached_variability_stats is None:
            pytest.skip("get_cached_variability_stats not yet implemented")

        # Arrange: Add source to cache
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO variability_stats 
            (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
             sigma_deviation, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("PERF001", 120.0, 45.0, 10, 50.0, 5.0, 3.5, time.time()),
        )
        conn.commit()
        conn.close()

        # Act: Measure cache access time
        start_time = time.time()
        for _ in range(100):
            get_cached_variability_stats("PERF001", temp_products_db)
        elapsed = time.time() - start_time

        # Assert: Should be fast (< 1ms per access)
        avg_time = elapsed / 100
        assert avg_time < 0.001, f"Cache access should be < 1ms, got {avg_time:.4f}s"

    def test_cache_smoke(self, temp_products_db):
        """End-to-end smoke test."""
        if get_cached_variability_stats is None:
            pytest.skip("get_cached_variability_stats not yet implemented")

        # Arrange: Add multiple sources
        conn = sqlite3.connect(temp_products_db)
        cursor = conn.cursor()
        for i in range(10):
            cursor.execute(
                """
                INSERT INTO variability_stats 
                (source_id, ra_deg, dec_deg, n_obs, mean_flux_mjy, std_flux_mjy, 
                 sigma_deviation, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (f"SMOKE{i:03d}", 120.0 + i, 45.0, 10, 50.0, 5.0, 3.5, time.time()),
            )
        conn.commit()
        conn.close()

        # Act: Get cached stats for all sources
        results = []
        for i in range(10):
            stats = get_cached_variability_stats(f"SMOKE{i:03d}", temp_products_db)
            results.append(stats)

        # Assert: All should be cached
        assert all(r is not None for r in results), "All sources should be cached"
