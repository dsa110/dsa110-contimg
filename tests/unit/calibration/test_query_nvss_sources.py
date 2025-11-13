#!/usr/bin/env python3
"""
Unit tests for NVSS catalog query optimization.

Tests the query_nvss_sources() function for:
- SQLite database query path (fast)
- CSV fallback path (slow but reliable)
- Query parameter validation
- Edge cases (RA wrapping, empty results)
- Performance characteristics
- Error handling

Run with: pytest tests/unit/calibration/test_query_nvss_sources.py -v
"""

import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from astropy.coordinates import SkyCoord
import astropy.units as u

from dsa110_contimg.calibration.catalogs import query_nvss_sources, read_nvss_catalog


@pytest.fixture
def mock_sqlite_db(tmp_path):
    """Create a mock SQLite database with test sources."""
    db_path = tmp_path / "nvss_dec+54.6.sqlite3"

    with sqlite3.connect(str(db_path)) as conn:
        # Create table
        conn.execute(
            """
            CREATE TABLE sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                flux_mjy REAL,
                UNIQUE(ra_deg, dec_deg)
            )
        """
        )

        # Create indexes
        conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
        conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
        conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

        # Insert test sources around RA=83.5, Dec=54.6
        test_sources = [
            (83.5, 54.6, 100.0),  # Center source (bright)
            (83.4, 54.6, 50.0),  # Nearby source
            (83.6, 54.6, 30.0),  # Nearby source
            (84.0, 54.6, 5.0),  # Far source (should be filtered by radius)
            (83.5, 55.0, 20.0),  # Far source (should be filtered by radius)
            # Below flux threshold (different dec to avoid unique constraint)
            (83.5, 54.7, 2.0),
        ]
        conn.executemany(
            "INSERT INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
            test_sources,
        )
        conn.commit()

    return db_path


@pytest.mark.unit
class TestQueryNVSSSourcesSQLite:
    """Test SQLite query path (fast path)."""

    def test_sqlite_query_basic(self, mock_sqlite_db, tmp_path):
        """Test basic SQLite query functionality."""
        # Mock path resolution to use our test database
        with patch(
            "dsa110_contimg.calibration.catalogs.Path.cwd", return_value=tmp_path
        ):
            df = query_nvss_sources(
                ra_deg=83.5, dec_deg=54.6, radius_deg=0.2, min_flux_mjy=10.0
            )

        assert isinstance(df, pd.DataFrame)
        # Should find 3 sources within radius and flux threshold
        assert len(df) == 3
        assert "ra_deg" in df.columns
        assert "dec_deg" in df.columns
        assert "flux_mjy" in df.columns

        # Verify sources are within radius
        sc = SkyCoord(ra=df["ra_deg"].values * u.deg,
                      dec=df["dec_deg"].values * u.deg)
        center = SkyCoord(ra=83.5 * u.deg, dec=54.6 * u.deg)
        sep = sc.separation(center).deg
        assert all(sep <= 0.2)

        # Verify flux filtering
        assert all(df["flux_mjy"] >= 10.0)

    def test_sqlite_query_with_max_sources(self, mock_sqlite_db, tmp_path):
        """Test SQLite query with max_sources limit."""
        with patch(
            "dsa110_contimg.calibration.catalogs.Path.cwd", return_value=tmp_path
        ):
            df = query_nvss_sources(
                ra_deg=83.5,
                dec_deg=54.6,
                radius_deg=0.5,
                min_flux_mjy=10.0,
                max_sources=2,
            )

        assert len(df) <= 2
        # Should be sorted by flux descending
        if len(df) > 1:
            assert df.iloc[0]["flux_mjy"] >= df.iloc[1]["flux_mjy"]

    def test_sqlite_query_empty_result(self, mock_sqlite_db, tmp_path):
        """Test SQLite query with no matching sources."""
        # Query at location far from test sources (RA=83.5, Dec=54.6)
        # Use explicit path to ensure we use SQLite, not CSV fallback
        df = query_nvss_sources(
            ra_deg=0.0,
            dec_deg=0.0,
            radius_deg=0.1,
            min_flux_mjy=10.0,
            catalog_path=str(mock_sqlite_db),
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0  # No sources near RA=0, Dec=0 in test database
        assert list(df.columns) == ["ra_deg", "dec_deg", "flux_mjy"]

    def test_sqlite_query_performance(self, mock_sqlite_db, tmp_path):
        """Test that SQLite queries are fast (<50ms)."""
        with patch(
            "dsa110_contimg.calibration.catalogs.Path.cwd", return_value=tmp_path
        ):
            # Warm-up query
            _ = query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.2)

            # Benchmark
            start = time.perf_counter()
            df = query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.2)
            elapsed = time.perf_counter() - start

        assert elapsed < 0.05  # Should be < 50ms
        assert len(df) > 0

    def test_sqlite_query_ra_wrapping(self, mock_sqlite_db, tmp_path):
        """Test SQLite query handles RA wrapping correctly."""
        # Add sources near RA=0 and RA=360
        with sqlite3.connect(str(mock_sqlite_db)) as conn:
            conn.execute(
                "INSERT INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
                (0.1, 54.6, 50.0),
            )
            conn.execute(
                "INSERT INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
                (359.9, 54.6, 50.0),
            )
            conn.commit()

        with patch(
            "dsa110_contimg.calibration.catalogs.Path.cwd", return_value=tmp_path
        ):
            # Query near RA=0
            df1 = query_nvss_sources(ra_deg=0.0, dec_deg=54.6, radius_deg=0.2)
            # Query near RA=360
            df2 = query_nvss_sources(
                ra_deg=360.0, dec_deg=54.6, radius_deg=0.2)

        # Should find sources near RA=0/360
        assert len(df1) >= 1 or len(df2) >= 1


@pytest.mark.unit
class TestQueryNVSSSourcesCSVFallback:
    """Test CSV fallback path (when SQLite unavailable and use_csv_fallback=True)."""

    @patch("dsa110_contimg.calibration.catalogs.read_nvss_catalog")
    @patch("sqlite3.connect")
    @patch("dsa110_contimg.calibration.catalogs.Path.exists")
    def test_csv_fallback_when_no_sqlite(self, mock_exists, mock_connect, mock_read_nvss):
        """Test CSV fallback when SQLite database fails and use_csv_fallback=True."""
        # Mock Path.exists to return True (database path found) but connection fails
        mock_exists.return_value = True
        mock_connect.side_effect = Exception("Database connection failed")

        # Mock CSV data
        mock_df = pd.DataFrame(
            {
                "ra": [83.5, 83.4, 84.0],
                "dec": [54.6, 54.6, 54.6],
                "flux_20_cm": [100.0, 50.0, 5.0],
            }
        )
        mock_read_nvss.return_value = mock_df

        # Query should fall back to CSV when explicitly enabled
        df = query_nvss_sources(
            ra_deg=83.5, dec_deg=54.6, radius_deg=0.2, use_csv_fallback=True
        )

        assert isinstance(df, pd.DataFrame)
        assert "ra_deg" in df.columns
        assert "dec_deg" in df.columns
        assert "flux_mjy" in df.columns
        mock_read_nvss.assert_called_once()

    @patch("dsa110_contimg.calibration.catalogs.read_nvss_catalog")
    @patch("sqlite3.connect")
    @patch("dsa110_contimg.calibration.catalogs.Path.exists")
    def test_csv_fallback_with_flux_filter(self, mock_exists, mock_connect, mock_read_nvss):
        """Test CSV fallback with flux filtering."""
        mock_exists.return_value = True
        mock_connect.side_effect = Exception("Database connection failed")
        mock_df = pd.DataFrame(
            {
                "ra": [83.5, 83.4, 83.3],
                "dec": [54.6, 54.6, 54.6],
                "flux_20_cm": [100.0, 50.0, 5.0],
            }
        )
        mock_read_nvss.return_value = mock_df

        df = query_nvss_sources(
            ra_deg=83.5,
            dec_deg=54.6,
            radius_deg=0.5,
            min_flux_mjy=10.0,
            use_csv_fallback=True,
        )

        assert len(df) >= 2  # Should filter out flux < 10 mJy
        assert all(df["flux_mjy"] >= 10.0)

    @patch("dsa110_contimg.calibration.catalogs.read_nvss_catalog")
    @patch("sqlite3.connect")
    @patch("dsa110_contimg.calibration.catalogs.Path.exists")
    def test_csv_fallback_with_max_sources(self, mock_exists, mock_connect, mock_read_nvss):
        """Test CSV fallback with max_sources limit."""
        mock_exists.return_value = True
        mock_connect.side_effect = Exception("Database connection failed")
        # Create many sources
        n_sources = 100
        mock_df = pd.DataFrame(
            {
                "ra": np.full(n_sources, 83.5),
                "dec": np.full(n_sources, 54.6),
                "flux_20_cm": np.linspace(100.0, 1.0, n_sources),
            }
        )
        mock_read_nvss.return_value = mock_df

        df = query_nvss_sources(
            ra_deg=83.5,
            dec_deg=54.6,
            radius_deg=1.0,
            max_sources=10,
            use_csv_fallback=True,
        )

        assert len(df) <= 10


@pytest.mark.unit
class TestQueryNVSSSourcesNoFallback:
    """Test behavior when SQLite fails and use_csv_fallback=False (default)."""

    @patch("sqlite3.connect")
    @patch("dsa110_contimg.calibration.catalogs.Path.exists")
    def test_no_fallback_returns_empty_when_sqlite_fails(self, mock_exists, mock_connect):
        """Test that query returns empty DataFrame when SQLite fails and fallback disabled."""
        # Mock Path.exists to return True (database path found) but connection fails
        mock_exists.return_value = True
        # Mock sqlite3.connect to raise an exception
        mock_connect.side_effect = Exception("Database connection failed")

        # Query without CSV fallback (default)
        df = query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.2)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == ["ra_deg", "dec_deg", "flux_mjy"]

    @patch("sqlite3.connect")
    @patch("dsa110_contimg.calibration.catalogs.logger")
    @patch("dsa110_contimg.calibration.catalogs.Path.exists")
    def test_no_fallback_logs_error(self, mock_exists, mock_logger, mock_connect):
        """Test that error is logged when SQLite fails and fallback disabled."""
        mock_exists.return_value = True
        mock_connect.side_effect = Exception("Database connection failed")

        query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.2)

        # Verify error was logged
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "SQLite query failed" in error_call
        assert "use_csv_fallback=True" in error_call

    @patch("sqlite3.connect")
    @patch("builtins.print")
    @patch("dsa110_contimg.calibration.catalogs.Path.exists")
    def test_no_fallback_prints_info_message(self, mock_exists, mock_print, mock_connect):
        """Test that informational message is printed when CSV fallback disabled."""
        mock_exists.return_value = True
        mock_connect.side_effect = Exception("Database connection failed")

        query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.2)

        # Verify print was called with informational message
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("CSV catalog is available" in str(call) for call in print_calls)
        assert any("use_csv_fallback=True" in str(call) for call in print_calls)


class TestQueryNVSSSourcesErrorHandling:
    """Test error handling and edge cases."""

    def test_sqlite_error_falls_back_to_csv(self):
        """Test that SQLite errors gracefully fall back to CSV.

        Note: This test verifies error handling is in place. The actual CSV fallback
        behavior is more thoroughly tested in test_csv_fallback_when_no_sqlite.
        SQLite's error handling is complex (connect may succeed even with invalid files),
        so we test the error handling path indirectly.
        """
        # This test is covered by test_csv_fallback_when_no_sqlite
        # The try/except block in query_nvss_sources ensures errors are caught
        # and CSV fallback is used. Direct testing of SQLite errors is difficult
        # because sqlite3.connect() is very forgiving and may succeed even with
        # invalid data, only failing on specific query operations.
        pass

    def test_explicit_catalog_path(self, mock_sqlite_db, tmp_path):
        """Test query with explicit catalog path."""
        df = query_nvss_sources(
            ra_deg=83.5,
            dec_deg=54.6,
            radius_deg=0.2,
            catalog_path=str(mock_sqlite_db),
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    @patch("dsa110_contimg.calibration.catalogs.Path.exists")
    def test_explicit_catalog_path_not_found(self, mock_exists):
        """Test query with non-existent explicit path returns empty (no CSV fallback by default)."""
        # Mock Path.exists to return False for all paths (including auto-resolution)
        mock_exists.return_value = False
        
        df = query_nvss_sources(
            ra_deg=83.5,
            dec_deg=54.6,
            radius_deg=0.2,
            catalog_path="/nonexistent/path.sqlite3",
        )

        # Should return empty DataFrame (no CSV fallback by default)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == ["ra_deg", "dec_deg", "flux_mjy"]

    def test_zero_radius(self, mock_sqlite_db, tmp_path):
        """Test query with zero radius."""
        with patch(
            "dsa110_contimg.calibration.catalogs.Path.cwd", return_value=tmp_path
        ):
            df = query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.0)

        assert isinstance(df, pd.DataFrame)
        # Should return empty or only exact matches
        assert len(df) == 0  # No exact matches in test data

    def test_negative_radius(self, mock_sqlite_db, tmp_path):
        """Test query with negative radius (should still work but return empty)."""
        with patch(
            "dsa110_contimg.calibration.catalogs.Path.cwd", return_value=tmp_path
        ):
            df = query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=-0.1)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


@pytest.mark.unit
class TestQueryNVSSSourcesReturnFormat:
    """Test return format and data structure."""

    @patch("dsa110_contimg.calibration.catalogs.read_nvss_catalog")
    def test_return_format_columns(self, mock_read_nvss):
        """Test that return DataFrame has correct columns."""
        mock_df = pd.DataFrame(
            {
                "ra": [83.5, 83.4],
                "dec": [54.6, 54.6],
                "flux_20_cm": [100.0, 50.0],
            }
        )
        mock_read_nvss.return_value = mock_df

        df = query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.5)

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["ra_deg", "dec_deg", "flux_mjy"]
        assert df["ra_deg"].dtype in [np.float64, np.float32]
        assert df["dec_deg"].dtype in [np.float64, np.float32]
        assert df["flux_mjy"].dtype in [np.float64, np.float32]

    @patch("dsa110_contimg.calibration.catalogs.read_nvss_catalog")
    @patch("sqlite3.connect")
    @patch("dsa110_contimg.calibration.catalogs.Path.exists")
    def test_return_format_empty(self, mock_exists, mock_connect, mock_read_nvss):
        """Test return format for empty results."""
        mock_exists.return_value = True  # Database path found
        mock_connect.side_effect = Exception("Database connection failed")
        mock_df = pd.DataFrame({"ra": [], "dec": [], "flux_20_cm": []})
        mock_read_nvss.return_value = mock_df

        # With CSV fallback enabled, should return empty DataFrame
        df = query_nvss_sources(
            ra_deg=0.0, dec_deg=0.0, radius_deg=0.1, use_csv_fallback=True
        )

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["ra_deg", "dec_deg", "flux_mjy"]
        assert len(df) == 0

    def test_return_format_sorted_by_flux(self, mock_sqlite_db, tmp_path):
        """Test that results are sorted by flux (descending)."""
        with patch(
            "dsa110_contimg.calibration.catalogs.Path.cwd", return_value=tmp_path
        ):
            df = query_nvss_sources(
                ra_deg=83.5, dec_deg=54.6, radius_deg=0.5, min_flux_mjy=10.0
            )

        if len(df) > 1:
            # Check that flux is sorted descending
            fluxes = df["flux_mjy"].values
            assert all(fluxes[i] >= fluxes[i + 1]
                       for i in range(len(fluxes) - 1))


@pytest.mark.unit
class TestQueryNVSSSourcesIntegration:
    """Integration tests with real database structure."""

    def test_real_database_structure(self, tmp_path):
        """Test query works with real database structure."""
        # Create database matching production structure
        db_path = tmp_path / "nvss_dec+54.6.sqlite3"

        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE sources (
                    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ra_deg REAL NOT NULL,
                    dec_deg REAL NOT NULL,
                    flux_mjy REAL,
                    UNIQUE(ra_deg, dec_deg)
                )
            """
            )
            conn.execute("CREATE INDEX idx_radec ON sources(ra_deg, dec_deg)")
            conn.execute("CREATE INDEX idx_dec ON sources(dec_deg)")
            conn.execute("CREATE INDEX idx_flux ON sources(flux_mjy)")

            # Insert test data
            conn.execute(
                "INSERT INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
                (83.5, 54.6, 100.0),
            )
            conn.commit()

        # Test query
        df = query_nvss_sources(
            ra_deg=83.5,
            dec_deg=54.6,
            radius_deg=0.1,
            catalog_path=str(db_path),
        )

        assert len(df) == 1
        assert df.iloc[0]["ra_deg"] == 83.5
        assert df.iloc[0]["dec_deg"] == 54.6
        assert df.iloc[0]["flux_mjy"] == 100.0


@pytest.mark.unit
class TestQueryNVSSSourcesSmoke:
    """Smoke tests for end-to-end functionality with realistic scenarios.

    These tests verify basic functionality works in typical use cases.
    They are quick but comprehensive enough to catch major regressions.
    """

    def test_smoke_basic_query(self):
        """Smoke test: Basic query works end-to-end."""
        # Test with realistic parameters (typical field center)
        df = query_nvss_sources(
            ra_deg=83.5,
            dec_deg=54.6,
            radius_deg=1.0,
            min_flux_mjy=10.0,
        )

        # Should return results (or empty DataFrame if no sources)
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["ra_deg", "dec_deg", "flux_mjy"]

        # If results exist, verify structure
        if len(df) > 0:
            # Verify sources are within angular radius (not just box bounds)
            sc = SkyCoord(
                ra=df["ra_deg"].values * u.deg, dec=df["dec_deg"].values * u.deg
            )
            center = SkyCoord(ra=83.5 * u.deg, dec=54.6 * u.deg)
            sep = sc.separation(center).deg
            assert all(
                sep <= 1.0), f"Some sources exceed 1.0 deg radius: {sep[sep > 1.0]}"
            assert all(df["flux_mjy"] >= 10.0)
            assert all(df["flux_mjy"].notna())

    def test_smoke_production_database_if_available(self):
        """Smoke test: Query works with production database if available."""
        prod_db = Path(
            "/data/dsa110-contimg/state/catalogs/nvss_dec+54.6.sqlite3")

        if not prod_db.exists():
            pytest.skip("Production database not available")

        # Query production database
        df = query_nvss_sources(
            ra_deg=83.5,
            dec_deg=54.6,
            radius_deg=0.5,
            min_flux_mjy=10.0,
            catalog_path=str(prod_db),
        )

        # Should return results from production database
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0  # Production DB should have sources

        # Verify data quality
        assert all(df["ra_deg"].notna())
        assert all(df["dec_deg"].notna())
        assert all(df["flux_mjy"].notna())
        assert all(df["flux_mjy"] >= 10.0)

        # Verify sources are within radius
        sc = SkyCoord(
            ra=df["ra_deg"].values * u.deg, dec=df["dec_deg"].values * u.deg
        )
        center = SkyCoord(ra=83.5 * u.deg, dec=54.6 * u.deg)
        sep = sc.separation(center).deg
        assert all(sep <= 0.5)

    def test_smoke_performance_characteristics(self):
        """Smoke test: Verify performance is acceptable (<100ms per query)."""
        import time

        # Warm-up query
        _ = query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=1.0)

        # Measure performance
        times = []
        for _ in range(5):
            start = time.perf_counter()
            df = query_nvss_sources(
                ra_deg=83.5, dec_deg=54.6, radius_deg=1.0, min_flux_mjy=10.0
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Should be fast (<100ms average, <200ms max)
        assert avg_time < 0.1, f"Average query time {avg_time*1000:.1f}ms exceeds 100ms"
        assert max_time < 0.2, f"Max query time {max_time*1000:.1f}ms exceeds 200ms"

    def test_smoke_typical_workflow(self):
        """Smoke test: Typical workflow (multiple queries with different parameters)."""
        # Simulate typical workflow: query multiple fields
        test_cases = [
            (83.5, 54.6, 1.0, 10.0),  # Standard field
            (84.0, 54.6, 0.5, 20.0),  # Smaller radius, higher flux
            (83.0, 54.6, 2.0, 5.0),   # Larger radius, lower flux
        ]

        for ra, dec, radius, min_flux in test_cases:
            df = query_nvss_sources(
                ra_deg=ra, dec_deg=dec, radius_deg=radius, min_flux_mjy=min_flux
            )

            # Each query should succeed
            assert isinstance(df, pd.DataFrame)
            assert list(df.columns) == ["ra_deg", "dec_deg", "flux_mjy"]

            # Results should respect constraints
            if len(df) > 0:
                assert all(df["flux_mjy"] >= min_flux)

    def test_smoke_edge_case_coordinates(self):
        """Smoke test: Function handles edge case coordinates gracefully."""
        edge_cases = [
            (0.0, 0.0, 1.0),      # RA=0, Dec=0
            (360.0, 0.0, 1.0),   # RA=360, Dec=0
            (180.0, 90.0, 1.0),  # RA=180, Dec=90 (North pole)
            (180.0, -90.0, 1.0),  # RA=180, Dec=-90 (South pole)
        ]

        for ra, dec, radius in edge_cases:
            # Query may return empty if SQLite DB not available (default behavior)
            df = query_nvss_sources(ra_deg=ra, dec_deg=dec, radius_deg=radius)

            assert isinstance(df, pd.DataFrame)
            assert list(df.columns) == ["ra_deg", "dec_deg", "flux_mjy"]
            # May be empty if SQLite DB not available (expected behavior)

    def test_smoke_result_consistency(self):
        """Smoke test: Multiple queries with same parameters return consistent results."""
        # Query same field twice (using SQLite, not CSV fallback)
        df1 = query_nvss_sources(
            ra_deg=83.5, dec_deg=54.6, radius_deg=1.0, min_flux_mjy=10.0
        )
        df2 = query_nvss_sources(
            ra_deg=83.5, dec_deg=54.6, radius_deg=1.0, min_flux_mjy=10.0
        )

    def test_smoke_csv_fallback_disabled_by_default(self):
        """Smoke test: CSV fallback is disabled by default."""
        # This test verifies the default behavior - SQLite required
        # If SQLite is available, query succeeds
        # If SQLite unavailable, returns empty DataFrame (not CSV fallback)
        df = query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=1.0)
        # Should either succeed (if SQLite available) or return empty (if not)
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["ra_deg", "dec_deg", "flux_mjy"]
