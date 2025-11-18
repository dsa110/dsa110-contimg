"""Unit tests for calibration provenance helper functions.

Focus: Fast tests for CASA version detection, command building,
and quality metrics extraction.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from dsa110_contimg.calibration.calibration import (
    _build_command_string,
    _extract_quality_metrics,
    _get_casa_version,
)


@pytest.mark.unit
def test_get_casa_version_returns_string():
    """Test _get_casa_version returns a string version."""
    # Test with real CASA environment (if available)
    version = _get_casa_version()
    # Should return either a version string or None
    assert version is None or isinstance(version, str)
    if version:
        # Should be in format like "6.7.2" or "6.7.2.32"
        assert "." in version
        parts = version.split(".")
        assert len(parts) >= 2
        assert all(part.isdigit() for part in parts)


@pytest.mark.unit
def test_get_casa_version_handles_list_format():
    """Test _get_casa_version converts list format to string."""
    # Mock casatools to return list format
    mock_module = MagicMock()
    mock_module.version.return_value = [6, 7, 2, 32]

    # Patch the import inside the function

    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "casatools":
            return mock_module
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        version = _get_casa_version()
        assert version == "6.7.2.32"


@pytest.mark.unit
def test_get_casa_version_handles_tuple_format():
    """Test _get_casa_version converts tuple format to string."""
    mock_module = MagicMock()
    mock_module.version.return_value = (6, 7, 2)

    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "casatools":
            return mock_module
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        version = _get_casa_version()
        assert version == "6.7.2"


@pytest.mark.unit
def test_get_casa_version_fallback_env():
    """Test _get_casa_version falls back to environment variable."""
    # The function checks hasattr, so we need to make version raise AttributeError
    # when accessed, not when checking hasattr
    mock_module = MagicMock()
    # hasattr will return True, but calling version() will raise AttributeError
    del mock_module.version

    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name in ("casatools", "casatasks"):
            return mock_module
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        import os

        with patch.dict(os.environ, {"CASA_VERSION": "6.4.0"}, clear=False):
            # Need to patch os.environ in the calibration module's namespace
            with patch("dsa110_contimg.calibration.calibration.os.environ", os.environ):
                version = _get_casa_version()
                assert version == "6.4.0"


@pytest.mark.unit
def test_get_casa_version_handles_exceptions():
    """Test _get_casa_version handles exceptions gracefully."""
    mock_module = MagicMock()
    mock_module.version.side_effect = Exception("Error")

    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name in ("casatools", "casatasks"):
            return mock_module
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        import os

        with patch.dict(os.environ, {}, clear=True):
            version = _get_casa_version()
            assert version is None


@pytest.mark.unit
def test_build_command_string_simple():
    """Test _build_command_string builds simple command."""
    kwargs = {"vis": "test.ms", "caltable": "test.cal", "field": "0"}
    cmd = _build_command_string("gaincal", kwargs)
    assert cmd.startswith("gaincal(")
    assert "vis='test.ms'" in cmd
    assert "caltable='test.cal'" in cmd
    assert "field='0'" in cmd


@pytest.mark.unit
def test_build_command_string_filters_none():
    """Test _build_command_string filters out None values."""
    kwargs = {"vis": "test.ms", "caltable": "test.cal", "field": None, "refant": "103"}
    cmd = _build_command_string("gaincal", kwargs)
    assert "field" not in cmd
    assert "refant='103'" in cmd


@pytest.mark.unit
def test_build_command_string_handles_lists():
    """Test _build_command_string handles list values."""
    kwargs = {"vis": "test.ms", "gaintable": ["table1.cal", "table2.cal"]}
    cmd = _build_command_string("applycal", kwargs)
    assert "gaintable=" in cmd
    # Should convert list to string representation
    assert "table1" in cmd or "table2" in cmd


@pytest.mark.unit
def test_build_command_string_sorted_params():
    """Test _build_command_string sorts parameters alphabetically."""
    kwargs = {"vis": "test.ms", "caltable": "test.cal", "field": "0", "refant": "103"}
    cmd = _build_command_string("gaincal", kwargs)
    # Parameters should be sorted
    parts = cmd.split("(")[1].rstrip(")").split(", ")
    param_names = [p.split("=")[0] for p in parts]
    assert param_names == sorted(param_names)


@pytest.mark.unit
def test_extract_quality_metrics_nonexistent_table(tmp_path):
    """Test _extract_quality_metrics handles nonexistent table."""
    caltable_path = tmp_path / "nonexistent.cal"
    metrics = _extract_quality_metrics(str(caltable_path))
    assert metrics is None


@pytest.mark.unit
def test_extract_quality_metrics_mock_table():
    """Test _extract_quality_metrics extracts metrics from mock table."""
    # Create mock table with required columns
    mock_table = MagicMock()
    mock_table.nrows.return_value = 100
    mock_table.colnames.return_value = [
        "FLAG",
        "SNR",
        "ANTENNA1",
        "SPECTRAL_WINDOW_ID",
    ]

    # Mock FLAG column (100 solutions, 10 flagged)
    flags = np.zeros((100, 2, 1), dtype=bool)
    flags[:10] = True  # 10 flagged

    # Mock SNR column
    snr = np.random.randn(100, 2, 1) * 5 + 10  # Mean ~10, some variation
    snr[0, 0, 0] = np.nan  # One NaN

    # Mock ANTENNA1 (10 unique antennas)
    antennas = np.array([i % 10 for i in range(100)])

    # Mock SPECTRAL_WINDOW_ID (2 unique SPWs)
    spw_ids = np.array([i % 2 for i in range(100)])

    # Configure getcol to return appropriate data based on column name
    def getcol_side_effect(col):
        if col == "FLAG":
            return flags
        elif col == "SNR":
            return snr
        elif col == "ANTENNA1":
            return antennas
        elif col == "SPECTRAL_WINDOW_ID":
            return spw_ids
        return None

    mock_table.getcol.side_effect = getcol_side_effect

    with patch("dsa110_contimg.calibration.calibration.table") as mock_table_func:
        mock_table_func.return_value.__enter__.return_value = mock_table
        mock_table_func.return_value.__exit__.return_value = None

        metrics = _extract_quality_metrics("/test/path.cal")

        assert metrics is not None
        assert metrics["n_solutions"] == 100
        assert "flagged_fraction" in metrics
        assert metrics["flagged_fraction"] == pytest.approx(0.1, abs=0.01)  # 10/100
        assert "snr_mean" in metrics
        assert "snr_median" in metrics
        assert "snr_min" in metrics
        assert "snr_max" in metrics
        assert metrics["n_antennas"] == 10
        assert metrics["n_spws"] == 2


@pytest.mark.unit
def test_extract_quality_metrics_empty_table():
    """Test _extract_quality_metrics handles empty table."""
    mock_table = MagicMock()
    mock_table.nrows.return_value = 0
    mock_table.colnames.return_value = []

    with patch("dsa110_contimg.calibration.calibration.table") as mock_table_func:
        mock_table_func.return_value.__enter__.return_value = mock_table
        mock_table_func.return_value.__exit__.return_value = None

        metrics = _extract_quality_metrics("/test/path.cal")

        assert metrics is not None
        assert metrics["n_solutions"] == 0


@pytest.mark.unit
def test_extract_quality_metrics_minimal_columns():
    """Test _extract_quality_metrics works with minimal columns."""
    mock_table = MagicMock()
    mock_table.nrows.return_value = 50
    mock_table.colnames.return_value = ["ANTENNA1"]  # Only antenna column

    antennas = np.array([i % 5 for i in range(50)])

    def getcol_side_effect(col):
        if col == "ANTENNA1":
            return antennas
        return None

    mock_table.getcol.side_effect = getcol_side_effect

    with patch("dsa110_contimg.calibration.calibration.table") as mock_table_func:
        mock_table_func.return_value.__enter__.return_value = mock_table
        mock_table_func.return_value.__exit__.return_value = None

        metrics = _extract_quality_metrics("/test/path.cal")

        assert metrics is not None
        assert metrics["n_solutions"] == 50
        assert metrics["n_antennas"] == 5
        assert "snr_mean" not in metrics  # No SNR column
        assert "flagged_fraction" not in metrics  # No FLAG column


@pytest.mark.unit
def test_extract_quality_metrics_handles_exception():
    """Test _extract_quality_metrics handles exceptions gracefully."""
    with patch("dsa110_contimg.calibration.calibration.table") as mock_table_func:
        mock_table_func.side_effect = Exception("Table read error")

        metrics = _extract_quality_metrics("/test/path.cal")

        assert metrics is None
