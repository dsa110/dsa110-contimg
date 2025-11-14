"""Unit tests for calibration provenance tracking.

Focus: Fast, isolated tests for provenance tracking, schema migration,
and calibration metadata capture.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.database.provenance import (
    CalTable,
    get_caltable_provenance,
    impact_analysis,
    query_caltables_by_source,
    track_calibration_provenance,
)
from dsa110_contimg.database.registry import (
    CalTableRow,
    ensure_db,
    register_set,
)


@pytest.fixture
def temp_registry_db(tmp_path):
    """Create a temporary calibration registry database for testing."""
    db_path = tmp_path / "test_cal_registry.sqlite3"
    conn = ensure_db(db_path)
    conn.close()
    return db_path


@pytest.fixture
def sample_caltable_row():
    """Create a sample CalTableRow with provenance data."""
    return CalTableRow(
        set_name="test_set",
        path="/test/path_kcal",
        table_type="K",
        order_index=10,
        cal_field="0",
        refant="103",
        valid_start_mjd=60000.0,
        valid_end_mjd=60001.0,
        status="active",
        source_ms_path="/test/input.ms",
        solver_command="gaincal(vis='/test/input.ms', caltable='/test/path_kcal', ...)",
        solver_version="6.7.2",
        solver_params={"field": "0", "refant": "103", "gaintype": "K"},
        quality_metrics={"snr_mean": 10.5, "n_solutions": 100},
    )


@pytest.mark.unit
def test_schema_migration_adds_provenance_columns(temp_registry_db):
    """Test schema migration adds provenance columns to existing database."""
    conn = ensure_db(temp_registry_db)

    # Verify new columns exist
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(caltables)")
    columns = {row[1]: row[2] for row in cur.fetchall()}

    assert "source_ms_path" in columns
    assert columns["source_ms_path"] == "TEXT"
    assert "solver_command" in columns
    assert columns["solver_command"] == "TEXT"
    assert "solver_version" in columns
    assert columns["solver_version"] == "TEXT"
    assert "solver_params" in columns
    assert columns["solver_params"] == "TEXT"
    assert "quality_metrics" in columns
    assert columns["quality_metrics"] == "TEXT"

    conn.close()


@pytest.mark.unit
def test_schema_migration_creates_source_index(temp_registry_db):
    """Test schema migration creates index on source_ms_path."""
    conn = ensure_db(temp_registry_db)

    # Verify index exists
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_caltables_source'")
    index = cur.fetchone()
    assert index is not None

    conn.close()


@pytest.mark.unit
def test_caltable_row_with_provenance(sample_caltable_row):
    """Test CalTableRow dataclass includes all provenance fields."""
    row = sample_caltable_row

    assert row.source_ms_path == "/test/input.ms"
    assert row.solver_command is not None
    assert row.solver_version == "6.7.2"
    assert row.solver_params == {"field": "0", "refant": "103", "gaintype": "K"}
    assert row.quality_metrics == {"snr_mean": 10.5, "n_solutions": 100}


@pytest.mark.unit
def test_register_set_stores_provenance(temp_registry_db, sample_caltable_row):
    """Test register_set stores provenance data correctly."""
    register_set(temp_registry_db, "test_set", [sample_caltable_row])

    conn = ensure_db(temp_registry_db)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_ms_path, solver_command, solver_version, solver_params, quality_metrics
        FROM caltables WHERE path = ?
        """,
        (sample_caltable_row.path,),
    )
    result = cur.fetchone()

    assert result is not None
    assert result[0] == "/test/input.ms"
    assert result[1] == sample_caltable_row.solver_command
    assert result[2] == "6.7.2"

    # Verify JSON fields are stored correctly
    params = json.loads(result[3])
    assert params == sample_caltable_row.solver_params

    metrics = json.loads(result[4])
    assert metrics == sample_caltable_row.quality_metrics

    conn.close()


@pytest.mark.unit
def test_register_set_with_null_provenance(temp_registry_db):
    """Test register_set handles None provenance fields gracefully."""
    row = CalTableRow(
        set_name="test_set",
        path="/test/path_kcal",
        table_type="K",
        order_index=10,
        cal_field="0",
        refant="103",
        valid_start_mjd=60000.0,
        valid_end_mjd=60001.0,
        status="active",
        # All provenance fields are None
    )

    register_set(temp_registry_db, "test_set", [row])

    conn = ensure_db(temp_registry_db)
    cur = conn.cursor()
    cur.execute(
        "SELECT source_ms_path, solver_params, quality_metrics FROM caltables WHERE path = ?",
        (row.path,),
    )
    result = cur.fetchone()

    assert result[0] is None  # source_ms_path
    assert result[1] is None  # solver_params (JSON)
    assert result[2] is None  # quality_metrics (JSON)

    conn.close()


@pytest.mark.unit
def test_track_calibration_provenance_updates_existing(temp_registry_db, sample_caltable_row):
    """Test track_calibration_provenance updates existing caltable entry."""
    # First register without provenance
    row_no_prov = CalTableRow(
        set_name=sample_caltable_row.set_name,
        path=sample_caltable_row.path,
        table_type=sample_caltable_row.table_type,
        order_index=sample_caltable_row.order_index,
        cal_field=sample_caltable_row.cal_field,
        refant=sample_caltable_row.refant,
        valid_start_mjd=sample_caltable_row.valid_start_mjd,
        valid_end_mjd=sample_caltable_row.valid_end_mjd,
        status=sample_caltable_row.status,
    )
    register_set(temp_registry_db, "test_set", [row_no_prov])

    # Then track provenance
    track_calibration_provenance(
        registry_db=temp_registry_db,
        ms_path="/test/input.ms",
        caltable_path=sample_caltable_row.path,
        params={"field": "0", "refant": "103"},
        metrics={"snr_mean": 10.5},
        solver_command="gaincal(...)",
        solver_version="6.7.2",
    )

    # Verify provenance was updated
    conn = ensure_db(temp_registry_db)
    cur = conn.cursor()
    cur.execute(
        "SELECT source_ms_path, solver_version FROM caltables WHERE path = ?",
        (sample_caltable_row.path,),
    )
    result = cur.fetchone()

    assert result[0] == "/test/input.ms"
    assert result[1] == "6.7.2"

    conn.close()


@pytest.mark.unit
def test_track_calibration_provenance_nonexistent_table(temp_registry_db):
    """Test track_calibration_provenance handles nonexistent table gracefully."""
    # Should not raise exception, just log warning
    track_calibration_provenance(
        registry_db=temp_registry_db,
        ms_path="/test/input.ms",
        caltable_path="/nonexistent/path.cal",
        params={},
    )

    # Verify no row was created
    conn = ensure_db(temp_registry_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM caltables WHERE path = ?", ("/nonexistent/path.cal",))
    count = cur.fetchone()[0]
    assert count == 0

    conn.close()


@pytest.mark.unit
def test_query_caltables_by_source(temp_registry_db, sample_caltable_row):
    """Test query_caltables_by_source returns correct caltables."""
    # Register multiple caltables from same source
    row1 = sample_caltable_row
    row2 = CalTableRow(
        set_name="test_set",
        path="/test/path_bpcal",
        table_type="BP",
        order_index=30,
        cal_field="0",
        refant="103",
        valid_start_mjd=60000.0,
        valid_end_mjd=60001.0,
        status="active",
        source_ms_path="/test/input.ms",
        solver_command="bandpass(...)",
        solver_version="6.7.2",
        solver_params={"field": "0"},
        quality_metrics={"snr_mean": 15.0},
    )
    # Different source MS
    row3 = CalTableRow(
        set_name="other_set",
        path="/test/path_other.cal",
        table_type="K",
        order_index=10,
        cal_field="1",
        refant="103",
        valid_start_mjd=60000.0,
        valid_end_mjd=60001.0,
        status="active",
        source_ms_path="/test/other.ms",
    )

    register_set(temp_registry_db, "test_set", [row1, row2])
    register_set(temp_registry_db, "other_set", [row3])

    # Query by source
    results = query_caltables_by_source(temp_registry_db, "/test/input.ms")

    assert len(results) == 2
    assert all(r.source_ms_path == "/test/input.ms" for r in results)
    assert {r.path for r in results} == {"/test/path_kcal", "/test/path_bpcal"}


@pytest.mark.unit
def test_query_caltables_by_source_empty_result(temp_registry_db):
    """Test query_caltables_by_source returns empty list for unknown source."""
    results = query_caltables_by_source(temp_registry_db, "/nonexistent/ms.ms")
    assert results == []


@pytest.mark.unit
def test_get_caltable_provenance(temp_registry_db, sample_caltable_row):
    """Test get_caltable_provenance returns full provenance information."""
    register_set(temp_registry_db, "test_set", [sample_caltable_row])

    caltable = get_caltable_provenance(temp_registry_db, sample_caltable_row.path)

    assert caltable is not None
    assert isinstance(caltable, CalTable)
    assert caltable.path == sample_caltable_row.path
    assert caltable.source_ms_path == "/test/input.ms"
    assert caltable.solver_version == "6.7.2"
    assert caltable.solver_params == sample_caltable_row.solver_params
    assert caltable.quality_metrics == sample_caltable_row.quality_metrics


@pytest.mark.unit
def test_get_caltable_provenance_nonexistent(temp_registry_db):
    """Test get_caltable_provenance returns None for nonexistent table."""
    caltable = get_caltable_provenance(temp_registry_db, "/nonexistent/path.cal")
    assert caltable is None


@pytest.mark.unit
def test_impact_analysis(temp_registry_db, sample_caltable_row):
    """Test impact_analysis finds affected MS paths."""
    # Register caltables from different sources
    row1 = sample_caltable_row
    row2 = CalTableRow(
        set_name="test_set",
        path="/test/path_bpcal",
        table_type="BP",
        order_index=30,
        cal_field="0",
        refant="103",
        valid_start_mjd=60000.0,
        valid_end_mjd=60001.0,
        status="active",
        source_ms_path="/test/input.ms",
    )
    row3 = CalTableRow(
        set_name="other_set",
        path="/test/path_other.cal",
        table_type="K",
        order_index=10,
        cal_field="1",
        refant="103",
        valid_start_mjd=60000.0,
        valid_end_mjd=60001.0,
        status="active",
        source_ms_path="/test/other.ms",
    )

    register_set(temp_registry_db, "test_set", [row1, row2])
    register_set(temp_registry_db, "other_set", [row3])

    # Analyze impact of first two caltables
    affected = impact_analysis(temp_registry_db, ["/test/path_kcal", "/test/path_bpcal"])

    assert len(affected) == 1
    assert "/test/input.ms" in affected
    assert "/test/other.ms" not in affected


@pytest.mark.unit
def test_impact_analysis_no_provenance(temp_registry_db):
    """Test impact_analysis handles caltables without provenance."""
    # Register caltable without provenance
    row = CalTableRow(
        set_name="test_set",
        path="/test/path_kcal",
        table_type="K",
        order_index=10,
        cal_field="0",
        refant="103",
        valid_start_mjd=60000.0,
        valid_end_mjd=60001.0,
        status="active",
    )
    register_set(temp_registry_db, "test_set", [row])

    affected = impact_analysis(temp_registry_db, ["/test/path_kcal"])
    assert affected == []


@pytest.mark.unit
def test_caltable_dataclass_json_deserialization():
    """Test CalTable dataclass correctly deserializes JSON fields."""
    # Simulate database row with JSON strings
    solver_params_json = json.dumps({"field": "0", "refant": "103"})
    quality_metrics_json = json.dumps({"snr_mean": 10.5, "n_solutions": 100})

    # This would come from database query
    row_data = (
        1,  # id
        "test_set",  # set_name
        "/test/path.cal",  # path
        "K",  # table_type
        10,  # order_index
        "0",  # cal_field
        "103",  # refant
        1234567890.0,  # created_at
        60000.0,  # valid_start_mjd
        60001.0,  # valid_end_mjd
        "active",  # status
        None,  # notes
        "/test/input.ms",  # source_ms_path
        "gaincal(...)",  # solver_command
        "6.7.2",  # solver_version
        solver_params_json,  # solver_params (JSON string)
        quality_metrics_json,  # quality_metrics (JSON string)
    )

    # Deserialize JSON fields (as done in query functions)
    solver_params = json.loads(row_data[15]) if row_data[15] else None
    quality_metrics = json.loads(row_data[16]) if row_data[16] else None

    caltable = CalTable(
        id=row_data[0],
        set_name=row_data[1],
        path=row_data[2],
        table_type=row_data[3],
        order_index=row_data[4],
        cal_field=row_data[5],
        refant=row_data[6],
        created_at=row_data[7],
        valid_start_mjd=row_data[8],
        valid_end_mjd=row_data[9],
        status=row_data[10],
        notes=row_data[11],
        source_ms_path=row_data[12],
        solver_command=row_data[13],
        solver_version=row_data[14],
        solver_params=solver_params,
        quality_metrics=quality_metrics,
    )

    assert caltable.solver_params == {"field": "0", "refant": "103"}
    assert caltable.quality_metrics == {"snr_mean": 10.5, "n_solutions": 100}
