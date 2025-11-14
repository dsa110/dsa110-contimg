"""Unit tests for publishing CLI commands.

Focus: Fast tests for CLI commands with mocked database operations.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.database.cli import (
    cmd_list,
    cmd_publish,
    cmd_retry,
    cmd_status,
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    import sqlite3

    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))

    # Create data_registry table
    conn.execute(
        """
        CREATE TABLE data_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_type TEXT NOT NULL,
            data_id TEXT NOT NULL UNIQUE,
            base_path TEXT,
            status TEXT NOT NULL,
            stage_path TEXT NOT NULL,
            published_path TEXT,
            created_at REAL NOT NULL,
            published_at REAL,
            publish_mode TEXT,
            publish_attempts INTEGER DEFAULT 0,
            publish_error TEXT,
            auto_publish INTEGER DEFAULT 0
        )
        """
    )

    # Insert test data
    import time

    now = time.time()
    conn.execute(
        """
        INSERT INTO data_registry
        (data_type, data_id, status, stage_path, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("mosaic", "mosaic_staging_001", "staging", "/stage/mosaics/mosaic_001.fits", now),
    )

    conn.execute(
        """
        INSERT INTO data_registry
        (data_type, data_id, status, stage_path, published_path, created_at, published_at, publish_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "mosaic",
            "mosaic_published_001",
            "published",
            "/stage/mosaics/mosaic_002.fits",
            "/data/products/mosaics/mosaic_002.fits",
            now,
            now,
            "manual",
        ),
    )

    conn.commit()
    yield conn, db_path
    conn.close()
    db_path.unlink(missing_ok=True)


class TestCmdPublish:
    """Test cmd_publish function."""

    @patch("dsa110_contimg.database.cli.publish_data_manual")
    @patch("dsa110_contimg.database.cli.get_data")
    def test_cmd_publish_success(self, mock_get_data, mock_publish, temp_db, capsys):
        """Test successful publish command."""
        conn, db_path = temp_db

        # Mock data record
        mock_record = MagicMock()
        mock_record.status = "staging"
        mock_get_data.return_value = mock_record

        # Mock published record
        mock_published = MagicMock()
        mock_published.status = "published"
        mock_published.published_path = "/data/products/mosaics/mosaic_001.fits"
        mock_get_data.side_effect = [mock_record, mock_published]

        mock_publish.return_value = True

        args = MagicMock()
        args.db = str(db_path)
        args.data_id = "mosaic_staging_001"
        args.products_base = None

        result = cmd_publish(args)

        assert result == 0
        mock_publish.assert_called_once()

        # Check output
        captured = capsys.readouterr()
        assert "published" in captured.out.lower()

    @patch("dsa110_contimg.database.cli.get_data")
    def test_cmd_publish_not_found(self, mock_get_data, temp_db):
        """Test publish command with non-existent data_id."""
        conn, db_path = temp_db

        mock_get_data.return_value = None

        args = MagicMock()
        args.db = str(db_path)
        args.data_id = "nonexistent"
        args.products_base = None

        result = cmd_publish(args)
        assert result == 1

    @patch("dsa110_contimg.database.cli.get_data")
    def test_cmd_publish_already_published(self, mock_get_data, temp_db, capsys):
        """Test publish command for already published data."""
        conn, db_path = temp_db

        mock_record = MagicMock()
        mock_record.status = "published"
        mock_get_data.return_value = mock_record

        args = MagicMock()
        args.db = str(db_path)
        args.data_id = "mosaic_published_001"
        args.products_base = None

        result = cmd_publish(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "already published" in captured.out.lower()


class TestCmdStatus:
    """Test cmd_status function."""

    @patch("dsa110_contimg.database.cli.get_data")
    def test_cmd_status_success(self, mock_get_data, temp_db, capsys):
        """Test status command."""
        conn, db_path = temp_db

        mock_record = MagicMock()
        mock_record.data_id = "mosaic_staging_001"
        mock_record.data_type = "mosaic"
        mock_record.status = "staging"
        mock_record.stage_path = "/stage/mosaics/mosaic_001.fits"
        mock_record.published_path = None
        mock_record.created_at = 1234567890.0
        mock_record.published_at = None
        mock_record.publish_mode = None
        mock_record.publish_attempts = 0
        mock_record.publish_error = None
        mock_get_data.return_value = mock_record

        args = MagicMock()
        args.db = str(db_path)
        args.data_id = "mosaic_staging_001"

        result = cmd_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "mosaic_staging_001" in captured.out
        assert "staging" in captured.out

    @patch("dsa110_contimg.database.cli.get_data")
    def test_cmd_status_not_found(self, mock_get_data, temp_db):
        """Test status command with non-existent data_id."""
        conn, db_path = temp_db

        mock_get_data.return_value = None

        args = MagicMock()
        args.db = str(db_path)
        args.data_id = "nonexistent"

        result = cmd_status(args)
        assert result == 1


class TestCmdRetry:
    """Test cmd_retry function."""

    @patch("dsa110_contimg.database.cli.trigger_auto_publish")
    @patch("dsa110_contimg.database.cli.get_data")
    def test_cmd_retry_success(self, mock_get_data, mock_trigger, temp_db, capsys):
        """Test retry command."""
        conn, db_path = temp_db

        mock_record = MagicMock()
        mock_record.status = "staging"
        mock_get_data.side_effect = [mock_record, mock_record]

        mock_trigger.return_value = True

        args = MagicMock()
        args.db = str(db_path)
        args.data_id = "mosaic_staging_001"

        result = cmd_retry(args)

        assert result == 0
        mock_trigger.assert_called_once()

    @patch("dsa110_contimg.database.cli.get_data")
    def test_cmd_retry_already_published(self, mock_get_data, temp_db, capsys):
        """Test retry command for already published data."""
        conn, db_path = temp_db

        mock_record = MagicMock()
        mock_record.status = "published"
        mock_get_data.return_value = mock_record

        args = MagicMock()
        args.db = str(db_path)
        args.data_id = "mosaic_published_001"

        result = cmd_retry(args)
        assert result == 0


class TestCmdList:
    """Test cmd_list function."""

    @patch("dsa110_contimg.database.cli.list_data")
    def test_cmd_list_success(self, mock_list, temp_db, capsys):
        """Test list command."""
        conn, db_path = temp_db

        mock_record1 = MagicMock()
        mock_record1.data_id = "mosaic_staging_001"
        mock_record1.data_type = "mosaic"
        mock_record1.status = "staging"
        mock_record1.stage_path = "/stage/mosaics/mosaic_001.fits"
        mock_record1.published_path = None
        mock_record1.created_at = 1234567890.0
        mock_record1.published_at = None

        mock_record2 = MagicMock()
        mock_record2.data_id = "mosaic_published_001"
        mock_record2.data_type = "mosaic"
        mock_record2.status = "published"
        mock_record2.stage_path = "/stage/mosaics/mosaic_002.fits"
        mock_record2.published_path = "/data/products/mosaics/mosaic_002.fits"
        mock_record2.created_at = 1234567890.0
        mock_record2.published_at = 1234567890.0

        mock_list.return_value = [mock_record1, mock_record2]

        args = MagicMock()
        args.db = str(db_path)
        args.data_type = None
        args.status = None
        args.json = False

        result = cmd_list(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "mosaic_staging_001" in captured.out
        assert "mosaic_published_001" in captured.out

    @patch("dsa110_contimg.database.cli.list_data")
    def test_cmd_list_json(self, mock_list, temp_db, capsys):
        """Test list command with JSON output."""
        conn, db_path = temp_db

        mock_record = MagicMock()
        mock_record.data_id = "mosaic_staging_001"
        mock_record.data_type = "mosaic"
        mock_record.status = "staging"
        mock_record.stage_path = "/stage/mosaics/mosaic_001.fits"
        mock_record.published_path = None
        mock_record.created_at = 1234567890.0
        mock_record.published_at = None

        mock_list.return_value = [mock_record]

        args = MagicMock()
        args.db = str(db_path)
        args.data_type = None
        args.status = None
        args.json = True

        result = cmd_list(args)

        assert result == 0
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert len(data) == 1
        assert data[0]["data_id"] == "mosaic_staging_001"
