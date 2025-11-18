"""Unit tests for group detection logic in streaming converter.

Tests the group detection functionality with focus on:
- Fast execution (mocked database queries)
- Accurate targeting of group detection logic
- Edge case handling (incomplete groups, time windows)
"""

from pathlib import Path

from dsa110_contimg.conversion.streaming.streaming_converter import (
    check_for_complete_group,
)
from dsa110_contimg.database.products import ensure_products_db


class TestCheckForCompleteGroup:
    """Test group detection logic."""

    def test_complete_group_detection(self, tmp_path):
        """Test detection of complete group (10 MS files)."""
        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        # Insert 10 MS files within time window
        base_mjd = 60295.0
        ms_paths = []
        for i in range(10):
            ms_path = f"/stage/ms/2025-11-12T10:{i:02d}:00.ms"
            ms_paths.append(ms_path)
            mid_mjd = base_mjd + i * 5 / (24 * 60)  # 5 minutes apart
            conn.execute(
                """
                INSERT OR REPLACE INTO ms_index (path, mid_mjd, status, stage)
                VALUES (?, ?, ?, ?)
                """,
                (ms_path, mid_mjd, "done", "imaged"),
            )
        conn.commit()
        conn.close()

        # Check for complete group using middle MS
        # Use larger time window to include all 10 files (they span 45 minutes)
        result = check_for_complete_group(
            ms_paths[5], products_db.resolve(), time_window_minutes=50.0
        )

        assert result is not None
        assert len(result) == 10
        assert result == ms_paths

    def test_incomplete_group_returns_none(self, tmp_path):
        """Test that incomplete group (< 10 MS files) returns None."""
        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        # Insert only 5 MS files
        base_mjd = 60295.0
        ms_paths = []
        for i in range(5):
            ms_path = f"/stage/ms/2025-11-12T10:{i:02d}:00.ms"
            ms_paths.append(ms_path)
            mid_mjd = base_mjd + i * 5 / (24 * 60)
            conn.execute(
                """
                INSERT INTO ms_index (path, mid_mjd, status, stage)
                VALUES (?, ?, ?, ?)
                """,
                (ms_path, mid_mjd, "done", "imaged"),
            )
        conn.commit()
        conn.close()

        result = check_for_complete_group(ms_paths[2], products_db, time_window_minutes=25.0)

        assert result is None

    def test_only_imaged_ms_included(self, tmp_path):
        """Test that only imaged MS files are included in group."""
        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        base_mjd = 60295.0
        ms_paths = []
        for i in range(12):
            ms_path = f"/stage/ms/2025-11-12T10:{i:02d}:00.ms"
            ms_paths.append(ms_path)
            mid_mjd = base_mjd + i * 5 / (24 * 60)
            # Mix of imaged and non-imaged
            status = "done" if i < 10 else "pending"
            stage = "imaged" if i < 10 else "converted"
            conn.execute(
                """
                INSERT INTO ms_index (path, mid_mjd, status, stage)
                VALUES (?, ?, ?, ?)
                """,
                (ms_path, mid_mjd, status, stage),
            )
        conn.commit()
        conn.close()

        result = check_for_complete_group(
            ms_paths[5], products_db.resolve(), time_window_minutes=50.0
        )

        assert result is not None
        assert len(result) == 10
        # Should only include imaged MS files (first 10)
        assert all(Path(p).name.startswith("2025-11-12T10:0") for p in result)

    def test_time_window_boundary(self, tmp_path):
        """Test that time window correctly filters MS files."""
        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        base_mjd = 60295.0
        # Create MS files: 5 within window, 5 outside window
        ms_paths_in_window = []
        for i in range(5):
            ms_path = f"/stage/ms/in_window_{i}.ms"
            ms_paths_in_window.append(ms_path)
            mid_mjd = base_mjd + i * 5 / (24 * 60)
            conn.execute(
                """
                INSERT INTO ms_index (path, mid_mjd, status, stage)
                VALUES (?, ?, ?, ?)
                """,
                (ms_path, mid_mjd, "done", "imaged"),
            )

        # MS files outside window (30 minutes away)
        for i in range(5):
            ms_path = f"/stage/ms/out_window_{i}.ms"
            mid_mjd = base_mjd + (30 + i * 5) / (24 * 60)
            conn.execute(
                """
                INSERT INTO ms_index (path, mid_mjd, status, stage)
                VALUES (?, ?, ?, ?)
                """,
                (ms_path, mid_mjd, "done", "imaged"),
            )

        conn.commit()
        conn.close()

        result = check_for_complete_group(
            ms_paths_in_window[2], products_db, time_window_minutes=25.0
        )

        assert result is None  # Not enough files in window

    def test_missing_ms_returns_none(self, tmp_path):
        """Test that missing MS path returns None."""
        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)
        conn.close()

        result = check_for_complete_group(
            "/nonexistent/path.ms", products_db, time_window_minutes=25.0
        )

        assert result is None

    def test_null_mid_mjd_returns_none(self, tmp_path):
        """Test that MS with null mid_mjd returns None."""
        products_db = tmp_path / "products.sqlite3"
        conn = ensure_products_db(products_db)

        ms_path = "/stage/ms/test.ms"
        conn.execute(
            """
            INSERT INTO ms_index (path, mid_mjd, status, stage)
            VALUES (?, ?, ?, ?)
            """,
            (ms_path, None, "done", "imaged"),
        )
        conn.commit()
        conn.close()

        result = check_for_complete_group(ms_path, products_db, time_window_minutes=25.0)

        assert result is None
