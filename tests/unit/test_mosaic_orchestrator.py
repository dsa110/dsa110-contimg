"""Unit tests for mosaic orchestrator functionality.

Tests for:
- find_earliest_incomplete_window with Dec extraction
- _trigger_hdf5_conversion (mocked)
- ensure_ms_files_in_window conversion triggering
- create_mosaic_default_behavior workflow (mocked)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from astropy.time import Time

from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator


@pytest.fixture
def temp_products_db(tmp_path):
    """Create a temporary products database for testing."""
    from dsa110_contimg.database.products import ensure_products_db

    db_path = tmp_path / "test_products.sqlite3"
    conn = ensure_products_db(db_path)

    # Ensure pointing columns exist
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(ms_index)")
    cols = {r[1] for r in cur.fetchall()}
    if "ra_deg" not in cols:
        cur.execute("ALTER TABLE ms_index ADD COLUMN ra_deg REAL")
    if "dec_deg" not in cols:
        cur.execute("ALTER TABLE ms_index ADD COLUMN dec_deg REAL")

    # Insert test MS files with pointing
    ms_paths = [
        "/test/ms/2024-01-01T00:00:00.ms",
        "/test/ms/2024-01-01T00:05:00.ms",
        "/test/ms/2024-01-01T00:10:00.ms",
    ]
    mjds = [60000.0, 60000.00347, 60000.00694]  # ~5 min apart

    for ms_path, mjd in zip(ms_paths, mjds):
        cur.execute(
            """
            INSERT INTO ms_index (path, start_mjd, end_mjd, mid_mjd, status, dec_deg, ra_deg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ms_path, mjd, mjd + 0.00347, mjd + 0.00174, "converted", -30.0, 150.0),
        )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def temp_data_registry_db(tmp_path):
    """Create a temporary data registry database for testing."""
    from dsa110_contimg.database.data_registry import ensure_data_registry_db

    db_path = tmp_path / "test_registry.sqlite3"
    conn = ensure_data_registry_db(db_path)
    conn.close()
    return db_path


@pytest.fixture
def orchestrator(temp_products_db, temp_data_registry_db, tmp_path):
    """Create a MosaicOrchestrator instance for testing."""
    ms_output_dir = tmp_path / "ms_output"
    mosaic_output_dir = tmp_path / "mosaic_output"
    ms_output_dir.mkdir()
    mosaic_output_dir.mkdir()

    return MosaicOrchestrator(
        products_db_path=temp_products_db,
        data_registry_db_path=temp_data_registry_db,
        ms_output_dir=ms_output_dir,
        mosaic_output_dir=mosaic_output_dir,
    )


@pytest.mark.unit
def test_find_earliest_incomplete_window_extracts_dec(orchestrator):
    """Test find_earliest_incomplete_window extracts Dec from ms_index."""
    with patch.object(orchestrator, "_get_mosaic_manager") as mock_get_manager:
        # Mock mosaic manager
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        # Mock BP calibrator lookup
        mock_manager.get_bandpass_calibrator_for_dec.return_value = {
            "name": "0834+555",
            "dec_deg": -30.0,
        }

        # Mock transit calculation
        mock_manager.calculate_calibrator_transit.return_value = Time(
            60000.0 + 0.5, format="mjd"
        )

        result = orchestrator.find_earliest_incomplete_window()

        assert result is not None
        assert "dec_deg" in result
        assert abs(result["dec_deg"] - (-30.0)) < 1e-6
        assert "bp_calibrator" in result
        assert result["bp_calibrator"] == "0834+555"
        assert "start_time" in result
        assert "end_time" in result


@pytest.mark.unit
def test_find_earliest_incomplete_window_no_dec(orchestrator):
    """Test find_earliest_incomplete_window handles missing Dec gracefully."""
    # Clear Dec from ms_index
    conn = orchestrator.products_db
    conn.execute("UPDATE ms_index SET dec_deg = NULL")
    conn.commit()

    result = orchestrator.find_earliest_incomplete_window()

    # Should return None when Dec cannot be determined
    assert result is None


@pytest.mark.unit
def test_find_earliest_incomplete_window_no_bp_calibrator(orchestrator):
    """Test find_earliest_incomplete_window handles missing BP calibrator."""
    with patch.object(orchestrator, "_get_mosaic_manager") as mock_get_manager:
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        # Return None (no calibrator found)
        mock_manager.get_bandpass_calibrator_for_dec.return_value = None

        result = orchestrator.find_earliest_incomplete_window()

        # Should return None when no BP calibrator found
        assert result is None


@pytest.mark.unit
def test_trigger_hdf5_conversion_success(orchestrator):
    """Test _trigger_hdf5_conversion successfully triggers conversion."""
    start_time = Time("2024-01-01T00:00:00", scale="utc")
    end_time = Time("2024-01-01T00:50:00", scale="utc")

    with patch(
        "dsa110_contimg.conversion.strategies.hdf5_orchestrator.convert_subband_groups_to_ms"
    ) as mock_convert:
        mock_convert.return_value = None  # Success

        result = orchestrator._trigger_hdf5_conversion(start_time, end_time)

        assert result is True
        mock_convert.assert_called_once()


@pytest.mark.unit
def test_trigger_hdf5_conversion_failure(orchestrator):
    """Test _trigger_hdf5_conversion handles conversion failure."""
    start_time = Time("2024-01-01T00:00:00", scale="utc")
    end_time = Time("2024-01-01T00:50:00", scale="utc")

    with patch(
        "dsa110_contimg.conversion.strategies.hdf5_orchestrator.convert_subband_groups_to_ms"
    ) as mock_convert:
        mock_convert.side_effect = Exception("Conversion failed")

        result = orchestrator._trigger_hdf5_conversion(start_time, end_time)

        assert result is False


@pytest.mark.unit
def test_ensure_ms_files_in_window_existing_files(orchestrator):
    """Test ensure_ms_files_in_window returns existing MS files."""
    start_time = Time(60000.0, format="mjd")
    end_time = Time(60000.1, format="mjd")
    required_count = 3

    ms_paths = orchestrator.ensure_ms_files_in_window(
        start_time, end_time, required_count
    )

    assert len(ms_paths) == 3
    assert all(p.startswith("/test/ms/") for p in ms_paths)


@pytest.mark.unit
def test_ensure_ms_files_in_window_triggers_conversion(orchestrator):
    """Test ensure_ms_files_in_window triggers conversion when files missing."""
    start_time = Time(60001.0, format="mjd")  # Future time, no MS files
    end_time = Time(60001.1, format="mjd")
    required_count = 3

    with patch.object(orchestrator, "_trigger_hdf5_conversion") as mock_trigger, patch(
        "time.sleep"
    ):  # Skip sleep
        mock_trigger.return_value = True

        ms_paths = orchestrator.ensure_ms_files_in_window(
            start_time, end_time, required_count
        )

        # Should have called conversion trigger
        mock_trigger.assert_called_once_with(start_time, end_time)


@pytest.mark.unit
def test_create_mosaic_default_behavior_workflow(orchestrator):
    """Test create_mosaic_default_behavior orchestrates full workflow."""
    with patch.object(
        orchestrator, "find_earliest_incomplete_window"
    ) as mock_find, patch.object(
        orchestrator, "ensure_ms_files_in_window"
    ) as mock_ensure, patch.object(
        orchestrator, "_form_group_from_ms_paths"
    ) as mock_form, patch.object(
        orchestrator, "_process_group_workflow"
    ) as mock_process, patch.object(
        orchestrator, "wait_for_published"
    ) as mock_wait:
        # Setup mocks
        mock_find.return_value = {
            "start_time": Time(60000.0, format="mjd"),
            "end_time": Time(60000.0347, format="mjd"),
            "dec_deg": -30.0,
            "bp_calibrator": "0834+555",
            "transit_time": Time(60000.5, format="mjd"),
            "ms_count": 3,
        }
        mock_ensure.return_value = ["/test/ms1.ms", "/test/ms2.ms", "/test/ms3.ms"]
        mock_form.return_value = True
        mock_process.return_value = "/test/mosaic.fits"
        mock_wait.return_value = "/data/mosaic.fits"

        result = orchestrator.create_mosaic_default_behavior(
            timespan_minutes=15, wait_for_published=True
        )

        assert result == "/data/mosaic.fits"
        mock_find.assert_called_once()
        mock_ensure.assert_called_once()
        mock_form.assert_called_once()
        mock_process.assert_called_once()
        mock_wait.assert_called_once()


@pytest.mark.unit
def test_create_mosaic_default_behavior_no_window(orchestrator):
    """Test create_mosaic_default_behavior handles no window found."""
    with patch.object(orchestrator, "find_earliest_incomplete_window") as mock_find:
        mock_find.return_value = None

        result = orchestrator.create_mosaic_default_behavior()

        assert result is None


@pytest.mark.unit
def test_create_mosaic_default_behavior_insufficient_ms(orchestrator):
    """Test create_mosaic_default_behavior handles insufficient MS files."""
    with patch.object(
        orchestrator, "find_earliest_incomplete_window"
    ) as mock_find, patch.object(
        orchestrator, "ensure_ms_files_in_window"
    ) as mock_ensure:
        mock_find.return_value = {
            "start_time": Time(60000.0, format="mjd"),
            "end_time": Time(60000.0347, format="mjd"),
            "dec_deg": -30.0,
            "bp_calibrator": "0834+555",
            "ms_count": 1,  # Insufficient
        }
        mock_ensure.return_value = ["/test/ms1.ms"]  # Only 1 MS

        result = orchestrator.create_mosaic_default_behavior(timespan_minutes=15)

        # Should return None when insufficient MS files (< 3)
        assert result is None
