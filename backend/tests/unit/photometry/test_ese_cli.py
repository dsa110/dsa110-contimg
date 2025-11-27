"""Unit tests for ESE detection CLI command.

Focus: Fast tests for CLI subcommand with mocked dependencies.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from dsa110_contimg.photometry.cli import cmd_ese_detect


@pytest.fixture
def temp_products_db(tmp_path):
    """Create temporary products database."""
    db_path = tmp_path / "products.sqlite3"
    db_path.touch()
    return db_path


class TestESEDetectCLI:
    """Test ese-detect CLI command."""

    @patch("dsa110_contimg.photometry.cli.detect_ese_candidates")
    def test_cmd_ese_detect_success(self, mock_detect, temp_products_db, capsys):
        """Test successful ESE detection via CLI."""
        mock_detect.return_value = [
            {
                "source_id": "source_001",
                "ra_deg": 120.0,
                "dec_deg": 45.0,
                "significance": 6.5,
                "nvss_flux_mjy": 100.0,
                "mean_flux_mjy": 50.0,
                "std_flux_mjy": 5.0,
                "chi2_nu": 2.5,
                "n_obs": 10,
                "last_mjd": 60000.0,
            }
        ]

        class Args:
            products_db = str(temp_products_db)
            min_sigma = 5.0
            source_id = None
            recompute = False

        result = cmd_ese_detect(Args())

        assert result == 0
        # CLI now also passes use_composite_scoring parameter
        mock_detect.assert_called_once()
        call_kwargs = mock_detect.call_args.kwargs
        assert call_kwargs["products_db"] == temp_products_db
        assert call_kwargs["min_sigma"] == 5.0
        assert call_kwargs["source_id"] is None
        assert call_kwargs["recompute"] is False

        # Check JSON output
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["candidates_found"] == 1
        assert len(output["candidates"]) == 1
        assert output["min_sigma"] == 5.0

    @patch("dsa110_contimg.photometry.cli.detect_ese_candidates")
    def test_cmd_ese_detect_with_source_id(self, mock_detect, temp_products_db, capsys):
        """Test ESE detection with specific source ID."""
        mock_detect.return_value = []

        class Args:
            products_db = str(temp_products_db)
            min_sigma = 5.0
            source_id = "source_001"
            recompute = False

        result = cmd_ese_detect(Args())

        assert result == 0
        mock_detect.assert_called_once_with(
            products_db=temp_products_db,
            min_sigma=5.0,
            source_id="source_001",
            recompute=False,
        )

    @patch("dsa110_contimg.photometry.cli.detect_ese_candidates")
    def test_cmd_ese_detect_with_recompute(self, mock_detect, temp_products_db, capsys):
        """Test ESE detection with recompute flag."""
        mock_detect.return_value = []

        class Args:
            products_db = str(temp_products_db)
            min_sigma = 5.0
            source_id = None
            recompute = True

        result = cmd_ese_detect(Args())

        assert result == 0
        mock_detect.assert_called_once_with(
            products_db=temp_products_db,
            min_sigma=5.0,
            source_id=None,
            recompute=True,
        )

    def test_cmd_ese_detect_missing_database(self, tmp_path, capsys):
        """Test handling of missing database."""
        missing_db = tmp_path / "missing.sqlite3"

        class Args:
            products_db = str(missing_db)
            min_sigma = 5.0
            source_id = None
            recompute = False

        result = cmd_ese_detect(Args())

        assert result == 1
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "error" in output

    @patch("dsa110_contimg.photometry.cli.detect_ese_candidates")
    def test_cmd_ese_detect_exception(self, mock_detect, temp_products_db, capsys):
        """Test handling of exceptions."""
        mock_detect.side_effect = Exception("Test error")

        class Args:
            products_db = str(temp_products_db)
            min_sigma = 5.0
            source_id = None
            recompute = False

        result = cmd_ese_detect(Args())

        assert result == 1
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "error" in output
        assert "Test error" in output["error"]
