"""Unit tests for mosaic orchestrator functionality.

Tests for:
- find_earliest_incomplete_window with Dec extraction
- find_transit_centered_window (transit lookup, failures, edge cases)
- _trigger_hdf5_conversion (mocked)
- ensure_ms_files_in_window conversion triggering
- _form_group_from_ms_paths (group formation, error handling)
- wait_for_published (polling, timeouts, errors)
- create_mosaic_default_behavior workflow (mocked)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    # Ensure mosaic_groups table exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS mosaic_groups (
            group_id TEXT PRIMARY KEY,
            mosaic_id TEXT,
            ms_paths TEXT NOT NULL,
            calibration_ms_path TEXT,
            bpcal_solved INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            calibrated_at REAL,
            imaged_at REAL,
            mosaicked_at REAL,
            status TEXT DEFAULT 'pending',
            stage TEXT,
            cal_applied INTEGER DEFAULT 0
        )
        """
    )

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
    """Create a MosaicOrchestrator instance for testing.

    Optimized: CalibratorMSGenerator is already mocked at module import time
    to avoid ~9.6s import overhead. Tests that need calibrator service can
    override orchestrator.calibrator_service.
    """
    ms_output_dir = tmp_path / "ms_output"
    mosaic_output_dir = tmp_path / "mosaic_output"
    ms_output_dir.mkdir()
    mosaic_output_dir.mkdir()

    orch = MosaicOrchestrator(
        products_db_path=temp_products_db,
        data_registry_db_path=temp_data_registry_db,
        ms_output_dir=ms_output_dir,
        mosaic_output_dir=mosaic_output_dir,
    )
    # Set to None - tests can override if needed
    orch.calibrator_service = None
    return orch


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
        mock_manager.calculate_calibrator_transit.return_value = Time(60000.0 + 0.5, format="mjd")

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

    ms_paths = orchestrator.ensure_ms_files_in_window(start_time, end_time, required_count)

    assert len(ms_paths) == 3
    assert all(p.startswith("/test/ms/") for p in ms_paths)


@pytest.mark.unit
def test_ensure_ms_files_in_window_triggers_conversion(orchestrator):
    """Test ensure_ms_files_in_window triggers conversion when files missing."""
    start_time = Time(60001.0, format="mjd")  # Future time, no MS files
    end_time = Time(60001.1, format="mjd")
    required_count = 3

    with (
        patch.object(orchestrator, "_trigger_hdf5_conversion") as mock_trigger,
        patch("time.sleep"),
    ):  # Skip sleep
        mock_trigger.return_value = True

        orchestrator.ensure_ms_files_in_window(start_time, end_time, required_count)

        # Should have called conversion trigger
        mock_trigger.assert_called_once_with(start_time, end_time)


@pytest.mark.unit
def test_create_mosaic_default_behavior_workflow(orchestrator):
    """Test create_mosaic_default_behavior orchestrates full workflow."""
    with (
        patch.object(orchestrator, "find_earliest_incomplete_window") as mock_find,
        patch.object(orchestrator, "ensure_ms_files_in_window") as mock_ensure,
        patch.object(orchestrator, "_form_group_from_ms_paths") as mock_form,
        patch.object(orchestrator, "_process_group_workflow") as mock_process,
        patch.object(orchestrator, "wait_for_published") as mock_wait,
    ):
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
    with (
        patch.object(orchestrator, "find_earliest_incomplete_window") as mock_find,
        patch.object(orchestrator, "ensure_ms_files_in_window") as mock_ensure,
    ):
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


# ============================================================================
# Tests for find_transit_centered_window
# ============================================================================


@pytest.mark.unit
def test_find_transit_centered_window_success(orchestrator):
    """Test find_transit_centered_window successfully finds transit window."""
    calibrator_name = "0834+555"
    timespan_minutes = 50

    # Mock calibrator service
    mock_service = MagicMock()
    mock_service.list_available_transits.return_value = [
        {"transit_iso": "2024-01-15T12:00:00"},  # Most recent first
        {"transit_iso": "2024-01-14T12:00:00"},
        {"transit_iso": "2024-01-13T12:00:00"},  # Earliest (last in list)
    ]
    mock_service._load_radec.return_value = (150.0, -30.0)  # RA, Dec

    orchestrator.calibrator_service = mock_service

    result = orchestrator.find_transit_centered_window(calibrator_name, timespan_minutes)

    assert result is not None
    assert "transit_time" in result
    assert "start_time" in result
    assert "end_time" in result
    assert "dec_deg" in result
    assert "bp_calibrator" in result
    assert "ms_count" in result
    assert result["bp_calibrator"] == calibrator_name
    assert abs(result["dec_deg"] - (-30.0)) < 1e-6

    # Verify window is centered on transit (±25 minutes for 50-minute span)
    transit_time = result["transit_time"]
    start_time = result["start_time"]
    end_time = result["end_time"]
    assert abs((end_time - start_time).to_value("min") - timespan_minutes) < 0.1
    assert abs((transit_time - start_time).to_value("min") - timespan_minutes / 2) < 0.1

    mock_service.list_available_transits.assert_called_once_with(calibrator_name, max_days_back=60)
    mock_service._load_radec.assert_called_once_with(calibrator_name)


@pytest.mark.unit
def test_find_transit_centered_window_no_transits(orchestrator):
    """Test find_transit_centered_window handles no transits found."""
    calibrator_name = "0834+555"

    # Mock calibrator service returning empty list
    mock_service = MagicMock()
    mock_service.list_available_transits.return_value = []

    orchestrator.calibrator_service = mock_service

    result = orchestrator.find_transit_centered_window(calibrator_name)

    assert result is None
    mock_service.list_available_transits.assert_called_once()


@pytest.mark.unit
def test_find_transit_centered_window_no_calibrator_service(orchestrator):
    """Test find_transit_centered_window handles missing calibrator service."""
    orchestrator.calibrator_service = None

    result = orchestrator.find_transit_centered_window("0834+555")

    assert result is None


@pytest.mark.unit
def test_find_transit_centered_window_custom_timespan(orchestrator):
    """Test find_transit_centered_window with custom timespan."""
    calibrator_name = "0834+555"
    timespan_minutes = 15  # 3 MS files instead of 10

    mock_service = MagicMock()
    mock_service.list_available_transits.return_value = [{"transit_iso": "2024-01-13T12:00:00"}]
    mock_service._load_radec.return_value = (150.0, -30.0)

    orchestrator.calibrator_service = mock_service

    result = orchestrator.find_transit_centered_window(calibrator_name, timespan_minutes)

    assert result is not None
    # Verify window span matches custom timespan
    start_time = result["start_time"]
    end_time = result["end_time"]
    assert abs((end_time - start_time).to_value("min") - timespan_minutes) < 0.1


@pytest.mark.unit
def test_find_transit_centered_window_ms_count_query(orchestrator):
    """Test find_transit_centered_window queries MS count correctly."""
    calibrator_name = "0834+555"

    mock_service = MagicMock()
    mock_service.list_available_transits.return_value = [{"transit_iso": "2024-01-13T12:00:00"}]
    mock_service._load_radec.return_value = (150.0, -30.0)

    orchestrator.calibrator_service = mock_service

    result = orchestrator.find_transit_centered_window(calibrator_name)

    assert result is not None
    assert "ms_count" in result
    # Should query ms_index for files in window
    assert isinstance(result["ms_count"], int)


# ============================================================================
# Tests for _form_group_from_ms_paths
# ============================================================================


@pytest.mark.unit
def test_form_group_from_ms_paths_success(orchestrator, tmp_path):
    """Test _form_group_from_ms_paths successfully creates group."""
    # Create test MS files
    ms_dir = tmp_path / "ms_files"
    ms_dir.mkdir()
    ms_paths = [
        str(ms_dir / "ms1.ms"),
        str(ms_dir / "ms2.ms"),
        str(ms_dir / "ms3.ms"),
    ]
    for ms_path in ms_paths:
        Path(ms_path).touch()

    group_id = "test_group_123"

    # Mock mosaic manager
    with patch.object(orchestrator, "_get_mosaic_manager") as mock_get_manager:
        mock_manager = MagicMock()
        mock_manager.products_db = orchestrator.products_db
        mock_get_manager.return_value = mock_manager

        result = orchestrator._form_group_from_ms_paths(ms_paths, group_id)

        assert result is True
        mock_get_manager.assert_called_once()

        # Verify group was inserted into database
        cursor = orchestrator.products_db.cursor()
        cursor.execute(
            "SELECT group_id, ms_paths, status FROM mosaic_groups WHERE group_id = ?",
            (group_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == group_id
        assert row[2] == "pending"


@pytest.mark.unit
def test_form_group_from_ms_paths_missing_file(orchestrator, tmp_path):
    """Test _form_group_from_ms_paths handles missing MS file."""
    ms_dir = tmp_path / "ms_files"
    ms_dir.mkdir()
    ms_paths = [
        str(ms_dir / "ms1.ms"),  # Exists
        str(ms_dir / "ms2.ms"),  # Missing
        str(ms_dir / "ms3.ms"),  # Exists
    ]
    Path(ms_paths[0]).touch()
    Path(ms_paths[2]).touch()

    group_id = "test_group_456"

    with patch.object(orchestrator, "_get_mosaic_manager") as mock_get_manager:
        mock_manager = MagicMock()
        mock_manager.products_db = orchestrator.products_db
        mock_get_manager.return_value = mock_manager

        result = orchestrator._form_group_from_ms_paths(ms_paths, group_id)

        assert result is False
        # Group should not be created
        cursor = orchestrator.products_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM mosaic_groups WHERE group_id = ?", (group_id,))
        assert cursor.fetchone()[0] == 0


@pytest.mark.unit
def test_form_group_from_ms_paths_database_error(orchestrator, tmp_path):
    """Test _form_group_from_ms_paths handles database errors."""
    ms_dir = tmp_path / "ms_files"
    ms_dir.mkdir()
    ms_paths = [str(ms_dir / "ms1.ms")]
    Path(ms_paths[0]).touch()

    group_id = "test_group_789"

    with patch.object(orchestrator, "_get_mosaic_manager") as mock_get_manager:
        mock_manager = MagicMock()
        # Simulate database error
        mock_manager.products_db.execute.side_effect = sqlite3.OperationalError("database locked")
        mock_get_manager.return_value = mock_manager

        result = orchestrator._form_group_from_ms_paths(ms_paths, group_id)

        assert result is False


@pytest.mark.unit
def test_form_group_from_ms_paths_group_id_collision(orchestrator, tmp_path):
    """Test _form_group_from_ms_paths handles group ID collision (INSERT OR REPLACE)."""
    ms_dir = tmp_path / "ms_files"
    ms_dir.mkdir()
    ms_paths1 = [str(ms_dir / "ms1.ms")]
    ms_paths2 = [str(ms_dir / "ms2.ms")]
    Path(ms_paths1[0]).touch()
    Path(ms_paths2[0]).touch()

    group_id = "collision_group"

    with patch.object(orchestrator, "_get_mosaic_manager") as mock_get_manager:
        mock_manager = MagicMock()
        mock_manager.products_db = orchestrator.products_db
        mock_get_manager.return_value = mock_manager

        # Create first group
        result1 = orchestrator._form_group_from_ms_paths(ms_paths1, group_id)
        assert result1 is True

        # Create second group with same ID (should replace)
        result2 = orchestrator._form_group_from_ms_paths(ms_paths2, group_id)
        assert result2 is True

        # Verify only one group exists (replaced)
        cursor = orchestrator.products_db.cursor()
        cursor.execute("SELECT ms_paths FROM mosaic_groups WHERE group_id = ?", (group_id,))
        row = cursor.fetchone()
        assert row is not None
        # Should contain ms_paths2, not ms_paths1
        assert "ms2.ms" in row[0]
        assert "ms1.ms" not in row[0]


# ============================================================================
# Tests for wait_for_published
# ============================================================================


@pytest.mark.unit
def test_wait_for_published_success(orchestrator, tmp_path):
    """Test wait_for_published successfully detects published status."""
    mosaic_id = "test_mosaic_123"
    published_path = str(tmp_path / "published" / "mosaic.fits")
    Path(published_path).parent.mkdir(parents=True)
    Path(published_path).touch()

    # Mock data registry to return published status
    mock_instance = MagicMock()
    mock_instance.status = "published"
    mock_instance.published_path = published_path

    call_count = [0]

    def time_side_effect():
        call_count[0] += 1
        # First call: start_time (0.0)
        # Second call: loop condition check (0.0, allows entry)
        # If function doesn't return immediately, subsequent calls return increasing values
        # to allow loop to exit (but shouldn't be needed for success case)
        return 0.0 if call_count[0] <= 2 else 100.0

    with (
        patch("dsa110_contimg.mosaic.orchestrator.get_data") as mock_get_data,
        patch("dsa110_contimg.mosaic.orchestrator.time.sleep"),
        patch("dsa110_contimg.mosaic.orchestrator.time.time") as mock_time,
    ):
        mock_get_data.return_value = mock_instance
        mock_time.side_effect = time_side_effect

        result = orchestrator.wait_for_published(mosaic_id, poll_interval_seconds=0.1)

        assert result == published_path
        mock_get_data.assert_called()


@pytest.mark.unit
def test_wait_for_published_timeout(orchestrator):
    """Test wait_for_published times out when not published."""
    mosaic_id = "test_mosaic_timeout"

    # Mock data registry to return non-published status
    mock_instance = MagicMock()
    mock_instance.status = "staging"  # Not published

    call_count = [0]

    def time_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return 0.0  # Start time
        elif call_count[0] == 2:
            return 0.0  # First loop condition check (allows entry)
        else:
            # After sleep, loop condition check - return value > max_wait to exit
            return 25 * 3600  # Past timeout (exits loop)

    with (
        patch("dsa110_contimg.mosaic.orchestrator.get_data") as mock_get_data,
        patch("dsa110_contimg.mosaic.orchestrator.time.sleep"),
        patch("dsa110_contimg.mosaic.orchestrator.time.time") as mock_time,
    ):
        mock_get_data.return_value = mock_instance
        mock_time.side_effect = time_side_effect

        result = orchestrator.wait_for_published(
            mosaic_id, poll_interval_seconds=0.1, max_wait_hours=24.0
        )

        assert result is None


@pytest.mark.unit
def test_wait_for_published_file_not_found(orchestrator):
    """Test wait_for_published handles file not found scenario."""
    mosaic_id = "test_mosaic_no_file"

    # Mock data registry: status is published but file doesn't exist
    mock_instance = MagicMock()
    mock_instance.status = "published"
    mock_instance.published_path = "/nonexistent/path/mosaic.fits"

    call_count = [0]

    def time_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return 0.0  # Start time
        elif call_count[0] == 2:
            return 0.0  # First loop condition check (allows entry)
        else:
            # After sleep, loop condition check - return value > max_wait to exit
            # 0.001 hours = 3.6 seconds, so return > 3.6
            return 10.0  # Past timeout (exits loop)

    with (
        patch("dsa110_contimg.mosaic.orchestrator.get_data") as mock_get_data,
        patch("dsa110_contimg.mosaic.orchestrator.time.sleep"),
        patch("dsa110_contimg.mosaic.orchestrator.time.time") as mock_time,
    ):
        mock_get_data.return_value = mock_instance
        mock_time.side_effect = time_side_effect

        result = orchestrator.wait_for_published(
            mosaic_id, poll_interval_seconds=0.1, max_wait_hours=0.001
        )

        # Should timeout because file doesn't exist
        assert result is None


@pytest.mark.unit
def test_wait_for_published_no_registry_entry(orchestrator):
    """Test wait_for_published handles missing registry entry."""
    mosaic_id = "test_mosaic_no_entry"

    call_count = [0]

    def time_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return 0.0  # Start time
        elif call_count[0] == 2:
            return 0.0  # First loop condition check (allows entry)
        else:
            # After sleep, loop condition check - return value > max_wait to exit
            # 0.001 hours = 3.6 seconds, so return > 3.6
            return 10.0  # Past timeout (exits loop)

    with (
        patch("dsa110_contimg.mosaic.orchestrator.get_data") as mock_get_data,
        patch("dsa110_contimg.mosaic.orchestrator.time.sleep"),
        patch("dsa110_contimg.mosaic.orchestrator.time.time") as mock_time,
    ):
        mock_get_data.return_value = None  # No entry found
        mock_time.side_effect = time_side_effect

        result = orchestrator.wait_for_published(
            mosaic_id, poll_interval_seconds=0.1, max_wait_hours=0.001
        )

        assert result is None


@pytest.mark.unit
def test_wait_for_published_polling_interval(orchestrator, tmp_path):
    """Test wait_for_published respects polling interval."""
    mosaic_id = "test_mosaic_polling"
    published_path = str(tmp_path / "published" / "mosaic.fits")
    Path(published_path).parent.mkdir(parents=True)
    Path(published_path).touch()

    mock_instance = MagicMock()
    mock_instance.status = "staging"
    # Change to published on second call
    call_count = [0]

    def get_data_side_effect(*args):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_instance
        else:
            mock_instance.status = "published"
            mock_instance.published_path = published_path
            return mock_instance

    with (
        patch("dsa110_contimg.mosaic.orchestrator.get_data") as mock_get_data,
        patch("dsa110_contimg.mosaic.orchestrator.time.sleep") as mock_sleep,
        patch("dsa110_contimg.mosaic.orchestrator.time.time") as mock_time,
    ):
        mock_get_data.side_effect = get_data_side_effect
        # Simulate time progression
        # Start, after first poll, after second poll
        mock_time.side_effect = [0.0, 0.05, 0.1]

        result = orchestrator.wait_for_published(
            mosaic_id, poll_interval_seconds=0.05, max_wait_hours=1.0
        )

        assert result == published_path
        # Should have slept at least once
        assert mock_sleep.call_count >= 1
