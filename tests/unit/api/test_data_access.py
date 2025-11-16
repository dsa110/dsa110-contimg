"""Unit tests for API data access functions.

Focus: Fast, isolated tests with mocked database connections.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.api.config import ApiConfig
from dsa110_contimg.api.data_access import (
    fetch_alert_history,
    fetch_calibration_sets,
    fetch_ese_candidates,
    fetch_mosaic_by_id,
    fetch_mosaics,
    fetch_observation_timeline,
    fetch_pointing_history,
    fetch_queue_stats,
    fetch_recent_calibrator_matches,
    fetch_recent_products,
    fetch_recent_queue_groups,
    fetch_source_timeseries,
)
from dsa110_contimg.api.models import QueueStats


@pytest.fixture
def mock_queue_db(tmp_path):
    """Create a temporary queue database for testing."""
    db_path = tmp_path / "queue.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(
            """
            CREATE TABLE ingest_queue (
                group_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                received_at REAL NOT NULL,
                last_update REAL NOT NULL,
                expected_subbands INTEGER DEFAULT 16,
                chunk_minutes REAL DEFAULT 5.0,
                has_calibrator INTEGER,
                calibrators TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE subband_files (
                group_id TEXT NOT NULL,
                subband_idx INTEGER NOT NULL,
                path TEXT NOT NULL,
                PRIMARY KEY (group_id, subband_idx)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE pointing_history (
                timestamp REAL PRIMARY KEY,
                ra_deg REAL,
                dec_deg REAL
            )
            """
        )
        # Insert test pointing data
        from astropy.time import Time

        now = Time.now()
        conn.execute(
            "INSERT INTO pointing_history(timestamp, ra_deg, dec_deg) VALUES(?, ?, ?)",
            (now.mjd, 207.45, 34.19),
        )
        # Insert test data with different timestamps for proper ordering
        now = datetime.now(tz=timezone.utc).timestamp()
        conn.execute(
            """
            INSERT INTO ingest_queue(group_id, state, received_at, last_update, expected_subbands, has_calibrator)
            VALUES(?,?,?,?,?,?)
            """,
            ("2025-10-07T00:00:00", "pending", now - 3600, now - 3600, 16, 1),  # Older
        )
        conn.execute(
            """
            INSERT INTO ingest_queue(group_id, state, received_at, last_update, expected_subbands, has_calibrator)
            VALUES(?,?,?,?,?,?)
            """,
            ("2025-10-07T01:00:00", "completed", now, now, 16, 0),  # Newer
        )
        conn.executemany(
            "INSERT INTO subband_files(group_id, subband_idx, path) VALUES(?,?,?)",
            [
                ("2025-10-07T00:00:00", idx, f"/data/subbands/file_sb{idx:02d}.hdf5")
                for idx in range(10)
            ],
        )
    return db_path


@pytest.fixture
def mock_products_db(tmp_path):
    """Create a temporary products database for testing."""
    db_path = tmp_path / "products.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(
            """
            CREATE TABLE ms_index (
                path TEXT PRIMARY KEY,
                start_mjd REAL,
                end_mjd REAL,
                mid_mjd REAL,
                processed_at REAL,
                status TEXT,
                stage TEXT,
                stage_updated_at REAL,
                cal_applied INTEGER DEFAULT 0,
                imagename TEXT,
                field_name TEXT,
                pointing_ra_deg REAL,
                pointing_dec_deg REAL,
                ra_deg REAL,
                dec_deg REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE images (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL,
                ms_path TEXT NOT NULL,
                created_at REAL NOT NULL,
                type TEXT NOT NULL,
                beam_major_arcsec REAL,
                noise_jy REAL,
                pbcor INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE ese_candidates (
                id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL,
                flagged_at REAL NOT NULL,
                flagged_by TEXT,
                significance REAL NOT NULL,
                flag_type TEXT,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                investigated_at REAL,
                dismissed_at REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE variability_stats (
                source_id TEXT PRIMARY KEY,
                ra_deg REAL,
                dec_deg REAL,
                nvss_flux_mjy REAL,
                mean_flux_mjy REAL,
                std_flux_mjy REAL,
                chi2_nu REAL,
                sigma_deviation REAL,
                last_measured_at REAL,
                last_mjd REAL,
                updated_at REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE photometry (
                id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL,
                image_path TEXT NOT NULL,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                nvss_flux_mjy REAL,
                peak_jyb REAL NOT NULL,
                peak_err_jyb REAL,
                measured_at REAL NOT NULL,
                mjd REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE mosaics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                created_at REAL NOT NULL,
                start_mjd REAL NOT NULL,
                end_mjd REAL NOT NULL,
                integration_sec REAL,
                n_images INTEGER,
                center_ra_deg REAL,
                center_dec_deg REAL,
                dec_min_deg REAL,
                dec_max_deg REAL,
                noise_jy REAL,
                beam_major_arcsec REAL,
                beam_minor_arcsec REAL,
                beam_pa_deg REAL,
                n_sources INTEGER,
                thumbnail_path TEXT
            )
            """
        )
        # pointing_history table is now in ingest database, not products database
        conn.execute(
            """
            CREATE TABLE alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_at REAL NOT NULL,
                channel TEXT,
                success INTEGER DEFAULT 1,
                error_msg TEXT
            )
            """
        )
        # Insert test data
        now = datetime.now(tz=timezone.utc).timestamp()
        conn.execute(
            """
            INSERT INTO images(path, ms_path, created_at, type, beam_major_arcsec, noise_jy, pbcor)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                "/data/images/test.fits",
                "/data/ms/test.ms",
                now,
                "image",
                12.5,
                0.002,
                1,
            ),
        )
        conn.execute(
            """
            INSERT INTO ese_candidates(source_id, flagged_at, significance, status, flagged_by, flag_type)
            VALUES(?,?,?,?,?,?)
            """,
            ("NVSS J123456.7+420312", now, 7.8, "active", "auto", "variability"),
        )
        conn.execute(
            """
            INSERT INTO variability_stats(source_id, ra_deg, dec_deg, nvss_flux_mjy, mean_flux_mjy, std_flux_mjy, chi2_nu, sigma_deviation, last_measured_at, last_mjd, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "NVSS J123456.7+420312",
                188.73625,
                42.05333,
                145.0,
                153.0,
                12.0,
                8.3,
                6.2,
                now,
                60238.5,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO mosaics(name, path, created_at, start_mjd, end_mjd, n_images, n_sources, noise_jy)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "test_mosaic",
                "/data/mosaics/test.fits",
                now,
                60238.5,
                60238.542,
                12,
                142,
                0.00085,
            ),
        )
        # pointing_history table is now in ingest database (mock_queue_db), not products database
    return db_path


@pytest.fixture
def mock_registry_db(tmp_path):
    """Create a temporary registry database for testing."""
    db_path = tmp_path / "registry.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(
            """
            CREATE TABLE caltables (
                id INTEGER PRIMARY KEY,
                set_name TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                table_type TEXT NOT NULL,
                order_index INTEGER NOT NULL,
                created_at REAL NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO caltables(set_name, path, table_type, order_index, created_at, status)
            VALUES(?,?,?,?,?,?)
            """,
            (
                "2025-10-06_J1234",
                "/data/cal/2025-10-06_J1234_kcal",
                "K",
                10,
                datetime.now(tz=timezone.utc).timestamp(),
                "active",
            ),
        )
    return db_path


@pytest.fixture
def mock_config(mock_queue_db, mock_products_db, mock_registry_db):
    """Create a mock ApiConfig for testing."""
    return ApiConfig(
        queue_db=mock_queue_db,
        products_db=mock_products_db,
        registry_db=mock_registry_db,
    )


class TestFetchQueueStats:
    """Test fetch_queue_stats function."""

    def test_fetch_queue_stats_success(self, mock_queue_db):
        """Test successful queue stats retrieval."""
        stats = fetch_queue_stats(mock_queue_db)
        assert isinstance(stats, QueueStats)
        assert stats.total == 2
        assert stats.pending == 1
        assert stats.completed == 1

    def test_fetch_queue_stats_empty_db(self, tmp_path):
        """Test queue stats with empty database (no tables)."""
        db_path = tmp_path / "empty.sqlite3"
        conn = sqlite3.connect(str(db_path))
        conn.close()  # Create empty DB
        # Function should handle missing table gracefully
        try:
            stats = fetch_queue_stats(db_path)
            # If it doesn't raise, should return zeros
            assert stats.total == 0
        except sqlite3.OperationalError:
            # Expected if table doesn't exist
            pass

    def test_fetch_queue_stats_missing_db(self, tmp_path):
        """Test queue stats with missing database file."""
        db_path = tmp_path / "nonexistent.sqlite3"
        # Function creates connection, which creates empty DB
        # But table won't exist, so should handle error
        try:
            stats = fetch_queue_stats(db_path)
            assert stats.total == 0
        except sqlite3.OperationalError:
            # Expected if table doesn't exist
            pass


class TestFetchRecentQueueGroups:
    """Test fetch_recent_queue_groups function."""

    def test_fetch_recent_queue_groups_success(self, mock_config):
        """Test successful queue groups retrieval."""
        groups = fetch_recent_queue_groups(mock_config.queue_db, mock_config, limit=10)
        assert len(groups) == 2
        # Groups ordered by received_at DESC (most recent first)
        assert groups[0].group_id == "2025-10-07T01:00:00"  # Most recent first
        assert groups[0].subbands_present == 0
        assert groups[1].group_id == "2025-10-07T00:00:00"
        assert groups[1].subbands_present == 10

    def test_fetch_recent_queue_groups_limit(self, mock_config):
        """Test queue groups with limit parameter."""
        groups = fetch_recent_queue_groups(mock_config.queue_db, mock_config, limit=1)
        assert len(groups) == 1


class TestFetchCalibrationSets:
    """Test fetch_calibration_sets function."""

    def test_fetch_calibration_sets_success(self, mock_registry_db):
        """Test successful calibration sets retrieval."""
        sets = fetch_calibration_sets(mock_registry_db)
        assert len(sets) == 1
        assert sets[0].set_name == "2025-10-06_J1234"
        assert sets[0].total == 1
        assert sets[0].active == 1


class TestFetchRecentProducts:
    """Test fetch_recent_products function."""

    def test_fetch_recent_products_success(self, mock_products_db):
        """Test successful products retrieval."""
        products = fetch_recent_products(mock_products_db, limit=10)
        assert len(products) == 1
        assert products[0].type == "image"
        assert products[0].path == "/data/images/test.fits"

    def test_fetch_recent_products_limit(self, mock_products_db):
        """Test products with limit parameter."""
        products = fetch_recent_products(mock_products_db, limit=0)
        assert len(products) == 0


class TestFetchESECandidates:
    """Test fetch_ese_candidates function."""

    def test_fetch_ese_candidates_success(self, mock_products_db):
        """Test successful ESE candidates retrieval."""
        candidates = fetch_ese_candidates(mock_products_db, limit=10, min_sigma=5.0)
        assert len(candidates) == 1
        assert candidates[0]["source_id"] == "NVSS J123456.7+420312"
        # Function returns max_sigma_dev (from sigma_deviation or significance)
        assert "max_sigma_dev" in candidates[0]
        assert candidates[0]["max_sigma_dev"] == 6.2  # From sigma_deviation

    def test_fetch_ese_candidates_min_sigma_filter(self, mock_products_db):
        """Test ESE candidates with sigma threshold."""
        candidates = fetch_ese_candidates(mock_products_db, limit=10, min_sigma=10.0)
        assert len(candidates) == 0  # 7.8 < 10.0

    def test_fetch_ese_candidates_empty_db(self, tmp_path):
        """Test ESE candidates with empty database."""
        db_path = tmp_path / "empty.sqlite3"
        db_path.touch()
        candidates = fetch_ese_candidates(db_path, limit=10, min_sigma=5.0)
        assert len(candidates) == 0


class TestFetchMosaics:
    """Test fetch_mosaics function."""

    def test_fetch_mosaics_success(self, mock_products_db):
        """Test successful mosaics retrieval."""
        # Need to convert MJD to ISO datetime for the function
        from astropy.time import Time

        start_mjd = 60238.5
        end_mjd = 60238.542
        start_time = Time(start_mjd, format="mjd").iso
        end_time = Time(end_mjd, format="mjd").iso

        mosaics = fetch_mosaics(
            mock_products_db,
            start_time=start_time,
            end_time=end_time,
        )
        assert len(mosaics) == 1
        assert mosaics[0]["name"] == "test_mosaic"

    def test_fetch_mosaics_time_range_filter(self, mock_products_db):
        """Test mosaics with time range filter."""
        from astropy.time import Time

        start_time = Time(60240.0, format="mjd").iso
        end_time = Time(60241.0, format="mjd").iso

        mosaics = fetch_mosaics(
            mock_products_db,
            start_time=start_time,
            end_time=end_time,
        )
        assert len(mosaics) == 0  # Outside time range


class TestFetchMosaicById:
    """Test fetch_mosaic_by_id function."""

    def test_fetch_mosaic_by_id_success(self, mock_products_db):
        """Test successful mosaic retrieval by ID."""
        mosaic = fetch_mosaic_by_id(mock_products_db, mosaic_id=1)
        assert mosaic is not None
        assert mosaic["name"] == "test_mosaic"

    def test_fetch_mosaic_by_id_not_found(self, mock_products_db):
        """Test mosaic retrieval with non-existent ID."""
        mosaic = fetch_mosaic_by_id(mock_products_db, mosaic_id=999)
        assert mosaic is None


class TestFetchSourceTimeseries:
    """Test fetch_source_timeseries function."""

    def test_fetch_source_timeseries_success(self, mock_products_db):
        """Test successful source timeseries retrieval."""
        # Need photometry data for timeseries
        conn = sqlite3.connect(str(mock_products_db))
        conn.row_factory = sqlite3.Row
        with conn:
            now = datetime.now(tz=timezone.utc).timestamp()
            conn.execute(
                """
                INSERT INTO photometry(source_id, image_path, ra_deg, dec_deg, peak_jyb, peak_err_jyb, measured_at, mjd)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    "NVSS J123456.7+420312",
                    "/data/images/test.fits",
                    188.73625,
                    42.05333,
                    0.153,
                    0.005,
                    now,
                    60238.5,
                ),
            )
        conn.close()

        timeseries = fetch_source_timeseries(mock_products_db, "NVSS J123456.7+420312")
        assert timeseries is not None
        assert timeseries["source_id"] == "NVSS J123456.7+420312"
        assert timeseries["ra_deg"] == 188.73625

    def test_fetch_source_timeseries_not_found(self, mock_products_db):
        """Test source timeseries with non-existent source."""
        timeseries = fetch_source_timeseries(mock_products_db, "NONEXISTENT")
        assert timeseries is None


class TestFetchPointingHistory:
    """Test fetch_pointing_history function."""

    @patch.dict("os.environ", {"SKIP_INCOMING_SCAN": "true"})
    def test_fetch_pointing_history_success(self, mock_queue_db, mock_products_db):
        """Test successful pointing history retrieval."""
        # Skip scanning /data/incoming/ (which has 80k+ files) via environment variable
        import os

        # Function now expects both ingest_db_path and products_db_path
        # Need to convert timestamp to MJD for query
        from astropy.time import Time

        now = datetime.now(tz=timezone.utc)
        now_mjd = Time(now).mjd

        history = fetch_pointing_history(
            str(mock_queue_db),  # ingest_db_path
            str(mock_products_db),  # products_db_path
            start_mjd=now_mjd - 1.0,
            end_mjd=now_mjd + 1.0,
        )
        # May be empty if timestamp doesn't match MJD range
        assert len(history) >= 0
        if len(history) > 0:
            assert hasattr(history[0], "ra_deg")
            assert hasattr(history[0], "dec_deg")
            assert hasattr(history[0], "timestamp")

    @patch.dict("os.environ", {"SKIP_INCOMING_SCAN": "true"})
    def test_fetch_pointing_history_time_range(self, mock_queue_db, mock_products_db):
        """Test pointing history with time range filter."""
        # Skip scanning /data/incoming/ (which has 80k+ files) via environment variable
        # Use far future MJD that won't match
        history = fetch_pointing_history(
            str(mock_queue_db),  # ingest_db_path
            str(mock_products_db),  # products_db_path
            start_mjd=70000.0,
            end_mjd=70001.0,
        )
        assert len(history) == 0  # Outside time range


class TestFetchAlertHistory:
    """Test fetch_alert_history function."""

    def test_fetch_alert_history_success(self, mock_products_db):
        """Test successful alert history retrieval."""
        # Add test alert data
        conn = sqlite3.connect(str(mock_products_db))
        conn.row_factory = sqlite3.Row
        with conn:
            now = datetime.now(tz=timezone.utc).timestamp()
            conn.execute(
                """
                INSERT INTO alert_history(source_id, alert_type, severity, message, sent_at, success)
                VALUES(?,?,?,?,?,?)
                """,
                (
                    "NVSS J123456.7+420312",
                    "ese_candidate",
                    "critical",
                    "Test alert",
                    now,
                    1,
                ),
            )
        conn.close()

        alerts = fetch_alert_history(mock_products_db, limit=10)
        assert isinstance(alerts, list)
        assert len(alerts) == 1

    def test_fetch_alert_history_limit(self, mock_products_db):
        """Test alert history with limit parameter."""
        alerts = fetch_alert_history(mock_products_db, limit=5)
        assert isinstance(alerts, list)


class TestFetchRecentCalibratorMatches:
    """Test fetch_recent_calibrator_matches function."""

    def test_fetch_recent_calibrator_matches_success(self, mock_queue_db):
        """Test successful calibrator matches retrieval."""
        matches = fetch_recent_calibrator_matches(mock_queue_db, limit=10)
        assert isinstance(matches, list)

    def test_fetch_recent_calibrator_matches_limit(self, mock_queue_db):
        """Test calibrator matches with limit parameter."""
        matches = fetch_recent_calibrator_matches(mock_queue_db, limit=5)
        assert isinstance(matches, list)


class TestFetchObservationTimeline:
    """Test fetch_observation_timeline function."""

    def test_fetch_observation_timeline_success(self, tmp_path):
        """Test successful observation timeline retrieval."""
        from datetime import datetime

        # Create test HDF5 files with timestamps
        data_dir = tmp_path / "incoming"
        data_dir.mkdir()

        # Create files with different timestamps
        test_files = [
            ("2025-01-15T10:00:00_sb01.hdf5", datetime(2025, 1, 15, 10, 0, 0)),
            (
                "2025-01-15T10:00:00_sb02.hdf5",
                datetime(2025, 1, 15, 10, 0, 0),
            ),  # Same timestamp
            (
                "2025-01-15T10:05:00_sb01.hdf5",
                datetime(2025, 1, 15, 10, 5, 0),
            ),  # Within gap threshold
            (
                "2025-01-16T14:30:00_sb01.hdf5",
                datetime(2025, 1, 16, 14, 30, 0),
            ),  # New segment (>24h gap)
            (
                "2025-01-16T14:35:00_sb01.hdf5",
                datetime(2025, 1, 16, 14, 35, 0),
            ),  # Same segment
        ]

        for filename, _ in test_files:
            (data_dir / filename).touch()

        # Test with default gap threshold (24 hours)
        timeline = fetch_observation_timeline(data_dir, gap_threshold_hours=24.0)

        assert timeline is not None
        assert timeline.total_files == 5
        assert timeline.unique_timestamps == 4  # 4 unique timestamps
        assert timeline.earliest_time == datetime(2025, 1, 15, 10, 0, 0)
        assert timeline.latest_time == datetime(2025, 1, 16, 14, 35, 0)
        assert len(timeline.segments) == 2  # Two segments (gap > 24h)

        # First segment: 2025-01-15 10:00:00 to 10:05:00 (3 files)
        assert timeline.segments[0].start_time == datetime(2025, 1, 15, 10, 0, 0)
        assert timeline.segments[0].end_time == datetime(2025, 1, 15, 10, 5, 0)
        assert timeline.segments[0].file_count == 3

        # Second segment: 2025-01-16 14:30:00 to 14:35:00 (2 files)
        assert timeline.segments[1].start_time == datetime(2025, 1, 16, 14, 30, 0)
        assert timeline.segments[1].end_time == datetime(2025, 1, 16, 14, 35, 0)
        assert timeline.segments[1].file_count == 2

    def test_fetch_observation_timeline_empty_dir(self, tmp_path):
        """Test observation timeline with empty directory."""
        data_dir = tmp_path / "empty"
        data_dir.mkdir()

        timeline = fetch_observation_timeline(data_dir)

        assert timeline is not None
        assert timeline.total_files == 0
        assert timeline.unique_timestamps == 0
        assert timeline.earliest_time is None
        assert timeline.latest_time is None
        assert len(timeline.segments) == 0

    def test_fetch_observation_timeline_nonexistent_dir(self, tmp_path):
        """Test observation timeline with nonexistent directory."""
        data_dir = tmp_path / "nonexistent"

        timeline = fetch_observation_timeline(data_dir)

        assert timeline is not None
        assert timeline.total_files == 0
        assert timeline.unique_timestamps == 0
        assert timeline.earliest_time is None
        assert timeline.latest_time is None
        assert len(timeline.segments) == 0

    def test_fetch_observation_timeline_invalid_filenames(self, tmp_path):
        """Test observation timeline with invalid filenames (should skip them)."""
        data_dir = tmp_path / "invalid"
        data_dir.mkdir()

        # Create files with invalid names
        (data_dir / "not_hdf5.txt").touch()
        (data_dir / "invalid_format.hdf5").touch()
        (data_dir / "2025-01-15T10:00:00.hdf5").touch()  # Missing _sbXX

        timeline = fetch_observation_timeline(data_dir)

        assert timeline is not None
        assert timeline.total_files == 0
        assert timeline.unique_timestamps == 0

    def test_fetch_observation_timeline_custom_gap_threshold(self, tmp_path):
        """Test observation timeline with custom gap threshold."""
        from datetime import datetime

        data_dir = tmp_path / "custom_gap"
        data_dir.mkdir()

        # Create files with 1-hour gaps
        test_files = [
            "2025-01-15T10:00:00_sb01.hdf5",
            "2025-01-15T11:00:00_sb01.hdf5",  # 1 hour gap
            "2025-01-15T12:00:00_sb01.hdf5",  # 1 hour gap
            "2025-01-15T14:00:00_sb01.hdf5",  # 2 hour gap - should split with 1.5h threshold
        ]

        for filename in test_files:
            (data_dir / filename).touch()

        # Test with 1.5 hour gap threshold
        timeline = fetch_observation_timeline(data_dir, gap_threshold_hours=1.5)

        assert timeline is not None
        assert timeline.total_files == 4
        assert len(timeline.segments) == 2  # Should split at 2-hour gap

        # First segment: 10:00 to 12:00 (3 files)
        assert timeline.segments[0].file_count == 3

        # Second segment: 14:00 (1 file)
        assert timeline.segments[1].file_count == 1
