"""Unit tests for query_rax_sources function with use_csv_fallback parameter."""

import sqlite3
from unittest.mock import patch

import pandas as pd
import pytest

from dsa110_contimg.calibration.catalogs import query_rax_sources


@pytest.fixture
def mock_sqlite_db(tmp_path):
    """Create a temporary SQLite database with test RAX data."""
    db_path = tmp_path / "rax_dec+54.6.sqlite3"

    test_sources = [
        (83.5, 54.6, 100.0),
        (83.4, 54.6, 50.0),
        (83.3, 54.6, 25.0),
        (84.0, 54.6, 10.0),
    ]

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
        conn.executemany(
            "INSERT INTO sources(ra_deg, dec_deg, flux_mjy) VALUES(?, ?, ?)",
            test_sources,
        )
        conn.commit()

    return db_path


@pytest.mark.unit
class TestQueryRAXSourcesSQLite:
    """Test SQLite query path for RAX sources."""

    def test_sqlite_query_basic(self, mock_sqlite_db, tmp_path):
        """Test basic SQLite query for RAX sources."""
        # Use explicit catalog path to ensure we use the mock database
        df = query_rax_sources(
            ra_deg=83.5, dec_deg=54.6, radius_deg=0.2, catalog_path=str(mock_sqlite_db)
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 1
        assert "ra_deg" in df.columns
        assert "dec_deg" in df.columns
        assert "flux_mjy" in df.columns


@pytest.mark.unit
class TestQueryRAXSourcesCSVFallback:
    """Test CSV fallback path for RAX sources when use_csv_fallback=True."""

    @patch("dsa110_contimg.calibration.catalogs.read_rax_catalog")
    @patch("sqlite3.connect")
    @patch("dsa110_contimg.calibration.catalogs.Path.exists")
    def test_csv_fallback_when_sqlite_fails(self, mock_exists, mock_connect, mock_read_rax):
        """Test CSV fallback when SQLite fails and use_csv_fallback=True."""
        mock_exists.return_value = True
        mock_connect.side_effect = Exception("Database connection failed")

        mock_df = pd.DataFrame(
            {
                "ra": [83.5, 83.4],
                "dec": [54.6, 54.6],
                "flux": [100.0, 50.0],
            }
        )
        mock_read_rax.return_value = mock_df

        df = query_rax_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.2, use_csv_fallback=True)

        assert isinstance(df, pd.DataFrame)
        assert "ra_deg" in df.columns
        assert "dec_deg" in df.columns
        assert "flux_mjy" in df.columns


@pytest.mark.unit
class TestQueryRAXSourcesNoFallback:
    """Test behavior when SQLite fails and use_csv_fallback=False (default)."""

    @patch("sqlite3.connect")
    @patch("dsa110_contimg.calibration.catalogs.Path.exists")
    def test_no_fallback_returns_empty(self, mock_exists, mock_connect):
        """Test that query returns empty DataFrame when SQLite fails and fallback disabled."""
        mock_exists.return_value = True
        mock_connect.side_effect = Exception("Database connection failed")

        df = query_rax_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.2)

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

        query_rax_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.2)

        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "SQLite query failed" in error_call
        assert "use_csv_fallback=True" in error_call
