"""Smoke tests for calibration provenance tracking integration.

Focus: Fast end-to-end tests verifying provenance tracking works
correctly when integrated with calibration functions.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.calibration.calibration import (
    _track_calibration_provenance,
    _validate_solve_success,
)
from dsa110_contimg.database.provenance import (
    get_caltable_provenance,
    query_caltables_by_source,
    track_calibration_provenance,
)
from dsa110_contimg.database.registry import CalTableRow, ensure_db, register_set


@pytest.fixture
def temp_registry_db(tmp_path):
    """Create a temporary calibration registry database for testing."""
    db_path = tmp_path / "test_cal_registry.sqlite3"
    conn = ensure_db(db_path)
    conn.close()
    return db_path


@pytest.fixture
def mock_caltable_path(tmp_path):
    """Create a mock calibration table path."""
    caltable_dir = tmp_path / "caltables"
    caltable_dir.mkdir()
    caltable_path = caltable_dir / "test_kcal"
    # Create a dummy file to simulate caltable existence
    caltable_path.mkdir()
    return str(caltable_path)


@pytest.mark.unit
def test_provenance_tracking_workflow_smoke(temp_registry_db, mock_caltable_path):
    """Smoke test: Verify complete provenance tracking workflow."""
    ms_path = "/test/input.ms"
    
    # Step 1: Register caltable without provenance
    row = CalTableRow(
        set_name="test_set",
        path=mock_caltable_path,
        table_type="K",
        order_index=10,
        cal_field="0",
        refant="103",
        valid_start_mjd=60000.0,
        valid_end_mjd=60001.0,
        status="active",
    )
    register_set(temp_registry_db, "test_set", [row])
    
    # Step 2: Track provenance
    track_calibration_provenance(
        registry_db=temp_registry_db,
        ms_path=ms_path,
        caltable_path=mock_caltable_path,
        params={"field": "0", "refant": "103", "gaintype": "K"},
        metrics={"snr_mean": 10.5, "n_solutions": 100},
        solver_command="gaincal(vis='/test/input.ms', ...)",
        solver_version="6.7.2",
    )
    
    # Step 3: Verify provenance was stored
    caltable = get_caltable_provenance(temp_registry_db, mock_caltable_path)
    assert caltable is not None
    assert caltable.source_ms_path == ms_path
    assert caltable.solver_version == "6.7.2"
    assert caltable.solver_params == {"field": "0", "refant": "103", "gaintype": "K"}
    assert caltable.quality_metrics == {"snr_mean": 10.5, "n_solutions": 100}
    
    # Step 4: Query by source
    results = query_caltables_by_source(temp_registry_db, ms_path)
    assert len(results) == 1
    assert results[0].path == mock_caltable_path


@pytest.mark.unit
def test_provenance_tracking_non_blocking(temp_registry_db, mock_caltable_path):
    """Smoke test: Verify provenance tracking failures don't break calibration."""
    # Simulate provenance tracking failure (invalid registry path)
    invalid_db = Path("/nonexistent/path/registry.sqlite3")
    
    # Should not raise exception
    try:
        _track_calibration_provenance(
            ms_path="/test/input.ms",
            caltable_path=mock_caltable_path,
            task_name="gaincal",
            params={"field": "0"},
            registry_db=str(invalid_db),
        )
    except Exception:
        pytest.fail("Provenance tracking should not raise exceptions")


@pytest.mark.unit
def test_provenance_tracking_with_validate_solve_success(
    temp_registry_db, mock_caltable_path
):
    """Smoke test: Verify provenance tracking integrates with validation."""
    # Mock table for validation
    mock_table = MagicMock()
    mock_table.nrows.return_value = 100
    mock_table.colnames.return_value = ["ANTENNA1", "FLAG"]
    antennas = [103] * 100
    flags = [[[False]]] * 100
    mock_table.getcol.side_effect = lambda col: (
        antennas if col == "ANTENNA1" else flags if col == "FLAG" else None
    )
    
    with patch("dsa110_contimg.calibration.calibration.table") as mock_table_func:
        mock_table_func.return_value.__enter__.return_value = mock_table
        mock_table_func.return_value.__exit__.return_value = None
        
        # Register caltable first
        row = CalTableRow(
            set_name="test_set",
            path=mock_caltable_path,
            table_type="K",
            order_index=10,
            cal_field="0",
            refant="103",
            valid_start_mjd=60000.0,
            valid_end_mjd=60001.0,
            status="active",
        )
        register_set(temp_registry_db, "test_set", [row])
        
        # Validate solve success (should not raise)
        _validate_solve_success(mock_caltable_path, refant="103")
        
        # Track provenance after validation
        _track_calibration_provenance(
            ms_path="/test/input.ms",
            caltable_path=mock_caltable_path,
            task_name="gaincal",
            params={"field": "0", "refant": "103"},
            registry_db=str(temp_registry_db),
        )
        
        # Verify provenance was tracked
        caltable = get_caltable_provenance(temp_registry_db, mock_caltable_path)
        assert caltable is not None
        assert caltable.source_ms_path == "/test/input.ms"


@pytest.mark.unit
def test_provenance_multiple_caltables_same_source(temp_registry_db, tmp_path):
    """Smoke test: Verify provenance tracking for multiple caltables from same MS."""
    ms_path = "/test/input.ms"
    caltable_dir = tmp_path / "caltables"
    caltable_dir.mkdir()
    
    # Create multiple mock caltables
    kcal_path = str(caltable_dir / "test_kcal")
    bpcal_path = str(caltable_dir / "test_bpcal")
    gpcal_path = str(caltable_dir / "test_gpcal")
    
    for path in [kcal_path, bpcal_path, gpcal_path]:
        Path(path).mkdir()
    
    # Register all caltables
    rows = [
        CalTableRow(
            set_name="test_set",
            path=kcal_path,
            table_type="K",
            order_index=10,
            cal_field="0",
            refant="103",
            valid_start_mjd=60000.0,
            valid_end_mjd=60001.0,
            status="active",
        ),
        CalTableRow(
            set_name="test_set",
            path=bpcal_path,
            table_type="BP",
            order_index=30,
            cal_field="0",
            refant="103",
            valid_start_mjd=60000.0,
            valid_end_mjd=60001.0,
            status="active",
        ),
        CalTableRow(
            set_name="test_set",
            path=gpcal_path,
            table_type="GP",
            order_index=50,
            cal_field="0",
            refant="103",
            valid_start_mjd=60000.0,
            valid_end_mjd=60001.0,
            status="active",
        ),
    ]
    register_set(temp_registry_db, "test_set", rows)
    
    # Track provenance for all
    for path, task_name in [
        (kcal_path, "gaincal"),
        (bpcal_path, "bandpass"),
        (gpcal_path, "gaincal"),
    ]:
        track_calibration_provenance(
            registry_db=temp_registry_db,
            ms_path=ms_path,
            caltable_path=path,
            params={"field": "0"},
            solver_command=f"{task_name}(...)",
            solver_version="6.7.2",
        )
    
    # Query by source - should get all three
    results = query_caltables_by_source(temp_registry_db, ms_path)
    assert len(results) == 3
    assert {r.path for r in results} == {kcal_path, bpcal_path, gpcal_path}
    assert all(r.source_ms_path == ms_path for r in results)


@pytest.mark.unit
def test_provenance_impact_analysis_smoke(temp_registry_db, tmp_path):
    """Smoke test: Verify impact analysis finds affected MS paths."""
    ms1_path = "/test/input1.ms"
    ms2_path = "/test/input2.ms"
    
    caltable_dir = tmp_path / "caltables"
    caltable_dir.mkdir()
    
    cal1_path = str(caltable_dir / "cal1")
    cal2_path = str(caltable_dir / "cal2")
    cal3_path = str(caltable_dir / "cal3")
    
    for path in [cal1_path, cal2_path, cal3_path]:
        Path(path).mkdir()
    
    # Register and track provenance
    rows = [
        CalTableRow(
            set_name="set1",
            path=cal1_path,
            table_type="K",
            order_index=10,
            cal_field="0",
            refant="103",
            valid_start_mjd=60000.0,
            valid_end_mjd=60001.0,
            status="active",
            source_ms_path=ms1_path,
        ),
        CalTableRow(
            set_name="set1",
            path=cal2_path,
            table_type="BP",
            order_index=30,
            cal_field="0",
            refant="103",
            valid_start_mjd=60000.0,
            valid_end_mjd=60001.0,
            status="active",
            source_ms_path=ms1_path,
        ),
        CalTableRow(
            set_name="set2",
            path=cal3_path,
            table_type="K",
            order_index=10,
            cal_field="1",
            refant="103",
            valid_start_mjd=60000.0,
            valid_end_mjd=60001.0,
            status="active",
            source_ms_path=ms2_path,
        ),
    ]
    register_set(temp_registry_db, "set1", rows[:2])
    register_set(temp_registry_db, "set2", rows[2:])
    
    # Analyze impact of first two caltables
    from dsa110_contimg.database.provenance import impact_analysis
    
    affected = impact_analysis(temp_registry_db, [cal1_path, cal2_path])
    assert len(affected) == 1
    assert ms1_path in affected
    assert ms2_path not in affected


@pytest.mark.unit
def test_provenance_registry_db_path_resolution(temp_registry_db, mock_caltable_path):
    """Smoke test: Verify registry DB path resolution works correctly."""
    ms_path = "/test/input.ms"
    
    # Register caltable
    row = CalTableRow(
        set_name="test_set",
        path=mock_caltable_path,
        table_type="K",
        order_index=10,
        cal_field="0",
        refant="103",
        valid_start_mjd=60000.0,
        valid_end_mjd=60001.0,
        status="active",
    )
    register_set(temp_registry_db, "test_set", [row])
    
    # Track provenance without explicit registry_db (should use default)
    # This tests the path resolution logic in _track_calibration_provenance
    with patch.dict(os.environ, {"CAL_REGISTRY_DB": str(temp_registry_db)}):
        _track_calibration_provenance(
            ms_path=ms_path,
            caltable_path=mock_caltable_path,
            task_name="gaincal",
            params={"field": "0"},
            registry_db=None,  # Should use environment variable
        )
        
        # Verify provenance was tracked
        caltable = get_caltable_provenance(temp_registry_db, mock_caltable_path)
        assert caltable is not None
        assert caltable.source_ms_path == ms_path


@pytest.mark.unit
def test_provenance_quality_metrics_extraction_smoke(
    temp_registry_db, mock_caltable_path
):
    """Smoke test: Verify quality metrics are extracted and stored."""
    import numpy as np
    
    # Mock table with quality metrics
    mock_table = MagicMock()
    mock_table.nrows.return_value = 100
    mock_table.colnames.return_value = ["FLAG", "SNR", "ANTENNA1", "SPECTRAL_WINDOW_ID"]
    
    flags = np.zeros((100, 2, 1), dtype=bool)
    flags[:10] = True  # 10% flagged
    snr = np.random.randn(100, 2, 1) * 2 + 10  # Mean ~10
    antennas = np.array([i % 10 for i in range(100)])
    spw_ids = np.array([0] * 100)
    
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
    
    # Register caltable
    row = CalTableRow(
        set_name="test_set",
        path=mock_caltable_path,
        table_type="K",
        order_index=10,
        cal_field="0",
        refant="103",
        valid_start_mjd=60000.0,
        valid_end_mjd=60001.0,
        status="active",
    )
    register_set(temp_registry_db, "test_set", [row])
    
    with patch("dsa110_contimg.calibration.calibration.table") as mock_table_func:
        mock_table_func.return_value.__enter__.return_value = mock_table
        mock_table_func.return_value.__exit__.return_value = None
        
        # Track provenance (should extract quality metrics)
        _track_calibration_provenance(
            ms_path="/test/input.ms",
            caltable_path=mock_caltable_path,
            task_name="gaincal",
            params={"field": "0"},
            registry_db=str(temp_registry_db),
        )
        
        # Verify quality metrics were stored
        caltable = get_caltable_provenance(temp_registry_db, mock_caltable_path)
        assert caltable is not None
        assert caltable.quality_metrics is not None
        assert "n_solutions" in caltable.quality_metrics
        assert caltable.quality_metrics["n_solutions"] == 100
        assert "flagged_fraction" in caltable.quality_metrics
        assert "snr_mean" in caltable.quality_metrics
        assert "n_antennas" in caltable.quality_metrics
        assert caltable.quality_metrics["n_antennas"] == 10

