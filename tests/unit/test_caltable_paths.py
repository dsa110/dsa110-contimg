#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for calibration table path construction and validation.

Tests the caltable_paths module functions for:
- Expected caltable path construction
- Caltable existence validation
- SPW handling
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.calibration.caltable_paths import (
    get_expected_caltables,
    validate_caltables_exist,
    _get_n_spws_from_ms,
)


class TestGetExpectedCaltables:
    """Test expected caltable path construction."""

    def test_basic_path_construction(self, tmp_path):
        """Test basic caltable path construction."""
        ms_path = tmp_path / "test_obs.ms"
        ms_path.mkdir()
        
        expected = get_expected_caltables(str(ms_path))
        
        assert "K" in expected
        assert "B" in expected
        assert "G" in expected
        assert "all" in expected
        
        assert len(expected["K"]) == 1
        assert len(expected["G"]) == 1
        assert expected["K"][0] == str(tmp_path / "test_obs.K")
        assert expected["G"][0] == str(tmp_path / "test_obs.G")

    def test_custom_caltable_dir(self, tmp_path):
        """Test caltable path construction with custom directory."""
        ms_path = tmp_path / "ms" / "test_obs.ms"
        ms_path.mkdir(parents=True)
        caltable_dir = tmp_path / "caltables"
        caltable_dir.mkdir()
        
        expected = get_expected_caltables(
            str(ms_path),
            caltable_dir=str(caltable_dir)
        )
        
        assert expected["K"][0] == str(caltable_dir / "test_obs.K")
        assert expected["G"][0] == str(caltable_dir / "test_obs.G")

    def test_caltype_filtering(self, tmp_path):
        """Test filtering by caltable type."""
        ms_path = tmp_path / "test_obs.ms"
        ms_path.mkdir()
        
        expected_k = get_expected_caltables(str(ms_path), caltype="K")
        assert len(expected_k["K"]) == 1
        assert len(expected_k["B"]) == 0
        assert len(expected_k["G"]) == 0
        
        expected_g = get_expected_caltables(str(ms_path), caltype="G")
        assert len(expected_g["K"]) == 0
        assert len(expected_g["G"]) == 1

    @patch('dsa110_contimg.calibration.caltable_paths._get_n_spws_from_ms')
    def test_bandpass_tables(self, mock_get_spws, tmp_path):
        """Test bandpass table construction with multiple SPWs."""
        ms_path = tmp_path / "test_obs.ms"
        ms_path.mkdir()
        
        mock_get_spws.return_value = 3
        
        expected = get_expected_caltables(str(ms_path))
        
        assert len(expected["B"]) == 3
        assert str(tmp_path / "test_obs.B0") in expected["B"]
        assert str(tmp_path / "test_obs.B1") in expected["B"]
        assert str(tmp_path / "test_obs.B2") in expected["B"]

    def test_spwmap_handling(self, tmp_path):
        """Test SPW mapping for bandpass tables."""
        ms_path = tmp_path / "test_obs.ms"
        ms_path.mkdir()
        
        spwmap = {0: 0, 1: 0, 2: 1}  # SPWs 0,1 -> BP0, SPW 2 -> BP1
        
        expected = get_expected_caltables(str(ms_path), spwmap=spwmap)
        
        # Should have 2 unique BP tables (indices 0 and 1)
        assert len(expected["B"]) == 2
        assert str(tmp_path / "test_obs.B0") in expected["B"]
        assert str(tmp_path / "test_obs.B1") in expected["B"]


class TestValidateCaltablesExist:
    """Test caltable existence validation."""

    def test_all_tables_exist(self, tmp_path):
        """Test validation when all tables exist."""
        ms_path = tmp_path / "test_obs.ms"
        ms_path.mkdir()
        
        # Create expected caltables
        (tmp_path / "test_obs.K").mkdir()
        (tmp_path / "test_obs.B0").mkdir()
        (tmp_path / "test_obs.B1").mkdir()
        (tmp_path / "test_obs.G").mkdir()
        
        existing, missing = validate_caltables_exist(str(ms_path))
        
        assert len(missing["all"]) == 0
        assert len(existing["all"]) == 4
        assert len(existing["K"]) == 1
        assert len(existing["B"]) == 2
        assert len(existing["G"]) == 1

    def test_some_tables_missing(self, tmp_path):
        """Test validation when some tables are missing."""
        ms_path = tmp_path / "test_obs.ms"
        ms_path.mkdir()
        
        # Create only some caltables
        (tmp_path / "test_obs.K").mkdir()
        (tmp_path / "test_obs.B0").mkdir()
        # Missing B1 and G
        
        existing, missing = validate_caltables_exist(str(ms_path))
        
        assert len(existing["all"]) == 2
        assert len(missing["all"]) == 2
        assert len(missing["B"]) == 1
        assert len(missing["G"]) == 1

    def test_raise_on_missing(self, tmp_path):
        """Test raise_on_missing parameter."""
        ms_path = tmp_path / "test_obs.ms"
        ms_path.mkdir()
        
        # Don't create any caltables
        
        with pytest.raises(FileNotFoundError):
            validate_caltables_exist(
                str(ms_path),
                raise_on_missing=True
            )

    def test_custom_caltable_dir(self, tmp_path):
        """Test validation with custom caltable directory."""
        ms_path = tmp_path / "ms" / "test_obs.ms"
        ms_path.mkdir(parents=True)
        caltable_dir = tmp_path / "caltables"
        caltable_dir.mkdir()
        
        # Create caltables in custom directory
        (caltable_dir / "test_obs.K").mkdir()
        (caltable_dir / "test_obs.G").mkdir()
        
        existing, missing = validate_caltables_exist(
            str(ms_path),
            caltable_dir=str(caltable_dir)
        )
        
        assert len(existing["K"]) == 1
        assert existing["K"][0] == str(caltable_dir / "test_obs.K")


class TestGetNSpwsFromMS:
    """Test SPW count extraction from MS."""

    @patch('dsa110_contimg.calibration.caltable_paths.table')
    def test_get_spw_count(self, mock_table):
        """Test getting SPW count from MS."""
        mock_spw_table = MagicMock()
        mock_spw_table.__len__.return_value = 4
        mock_table.return_value.__enter__.return_value = mock_spw_table
        
        n_spws = _get_n_spws_from_ms("/path/to/test.ms")
        
        assert n_spws == 4

    @patch('dsa110_contimg.calibration.caltable_paths.table')
    def test_get_spw_count_error_handling(self, mock_table):
        """Test error handling when SPW table cannot be read."""
        mock_table.side_effect = Exception("Table not found")
        
        n_spws = _get_n_spws_from_ms("/path/to/test.ms")
        
        # Should default to 1 SPW on error
        assert n_spws == 1

