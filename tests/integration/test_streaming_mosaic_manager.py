"""Integration tests for StreamingMosaicManager methods.

Tests the core workflow methods with mocked CASA/WSClean dependencies:
- solve_calibration_for_group
- apply_calibration_to_group
- image_group
- create_mosaic

These tests verify the orchestration logic and database state management
without requiring actual CASA/WSClean execution.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from astropy.time import Time

from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.database.registry import ensure_db as ensure_cal_db
from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager


@pytest.fixture
def temp_products_db(tmp_path):
    """Create a temporary products database for testing."""
    db_path = tmp_path / "test_products.sqlite3"
    conn = ensure_products_db(db_path)
    
    # Ensure mosaic_groups table exists
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS mosaic_groups (
            group_id TEXT PRIMARY KEY,
            mosaic_id TEXT,
            ms_paths TEXT NOT NULL,
            calibration_ms_path TEXT,
            bpcal_solved INTEGER DEFAULT 0,
            gaincal_solved INTEGER DEFAULT 0,
            status TEXT DEFAULT 'registered',
            stage TEXT DEFAULT 'registered',
            cal_applied INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def temp_registry_db(tmp_path):
    """Create a temporary calibration registry database for testing."""
    db_path = tmp_path / "test_registry.sqlite3"
    conn = ensure_cal_db(db_path)
    conn.close()
    return db_path


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for MS, images, and mosaics."""
    ms_dir = tmp_path / "ms"
    images_dir = tmp_path / "images"
    mosaics_dir = tmp_path / "mosaics"
    ms_dir.mkdir()
    images_dir.mkdir()
    mosaics_dir.mkdir()
    return {
        "ms_dir": ms_dir,
        "images_dir": images_dir,
        "mosaics_dir": mosaics_dir,
    }


@pytest.fixture
def mosaic_manager(temp_products_db, temp_registry_db, temp_dirs):
    """Create a StreamingMosaicManager instance for testing."""
    return StreamingMosaicManager(
        products_db_path=temp_products_db,
        registry_db_path=temp_registry_db,
        ms_output_dir=temp_dirs["ms_dir"],
        images_dir=temp_dirs["images_dir"],
        mosaic_output_dir=temp_dirs["mosaics_dir"],
    )


@pytest.fixture
def mock_ms_files(tmp_path, temp_dirs):
    """Create mock MS file directories for testing."""
    ms_files = []
    base_time = Time("2024-01-15T12:00:00", format="isot", scale="utc")
    
    for i in range(3):  # Create 3 MS files
        ms_time = base_time + i * 0.00347  # ~5 minutes apart
        ms_name = f"test_{ms_time.mjd:.6f}.ms"
        ms_path = temp_dirs["ms_dir"] / ms_name
        ms_path.mkdir()
        # Create minimal MS structure
        (ms_path / "table.dat").touch()
        ms_files.append(str(ms_path))
    
    return ms_files


@pytest.fixture
def registered_group(mosaic_manager, mock_ms_files):
    """Register a test group in the database."""
    group_id = "test_group_001"
    ms_paths_str = ",".join(mock_ms_files)
    
    cursor = mosaic_manager.products_db.cursor()
    cursor.execute(
        """
        INSERT INTO mosaic_groups (group_id, ms_paths, status, stage)
        VALUES (?, ?, ?, ?)
        """,
        (group_id, ms_paths_str, "registered", "registered"),
    )
    mosaic_manager.products_db.commit()
    
    return group_id


@pytest.mark.integration
def test_solve_calibration_for_group_success(mosaic_manager, registered_group, mock_ms_files, tmp_path):
    """Test solve_calibration_for_group successfully solves calibration."""
    # Create a mock calibration MS
    cal_ms_path = tmp_path / "cal.ms"
    cal_ms_path.mkdir()
    (cal_ms_path / "table.dat").touch()
    
    # Register a bandpass calibrator for the test
    mosaic_manager.register_bandpass_calibrator(
        calibrator_name="0834+555",
        ra_deg=129.0,
        dec_deg=-30.0,
        dec_tolerance=5.0,
    )
    
    # Mock casacore.tables - need to patch where it's imported inside the function
    mock_table = MagicMock()
    mock_table.getkeyword.return_value = [
        {"REFERENCE_DIR": [[0.0, -0.523599]]}  # ~-30 deg Dec
    ]
    mock_table.close.return_value = None
    
    # Create a mock casatables module
    mock_casatables_module = MagicMock()
    mock_casatables_module.table = MagicMock(return_value=mock_table)
    
    # Mock the calibration solving functions
    with patch("dsa110_contimg.mosaic.streaming_mosaic.solve_bandpass") as mock_bp, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.solve_gains") as mock_gains, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.extract_ms_time_range") as mock_extract, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.select_bandpass_from_catalog") as mock_select, \
         patch("casacore.tables", mock_casatables_module):
        
        # Mock time extraction
        mock_extract.return_value = (None, None, 60000.0)  # MJD
        
        # Mock bandpass selection - returns (field_sel_str, indices, weighted_flux, calibrator_info, peak_field_idx)
        import numpy as np
        mock_select.return_value = (
            "0",  # field_sel_str
            [0],  # field_indices
            np.array([1.0]),  # weighted_flux_per_field
            ("0834+555", 129.0, -30.0, 1.0),  # calibrator_info: (name, ra_deg, dec_deg, flux_jy)
            0,  # peak_field_idx
        )
        
        # Mock successful calibration solving
        mock_bp.return_value = (True, "/test/bp.table")
        mock_gains.return_value = (True, ["/test/gp.table", "/test/2g.table"])
        
        # Mock registry check to return empty (no existing tables)
        with patch.object(mosaic_manager, "check_registry_for_calibration", return_value={"BP": [], "GP": [], "2G": []}):
            bpcal_solved, gaincal_solved, error_msg = mosaic_manager.solve_calibration_for_group(
                registered_group, str(cal_ms_path)
            )
        
        assert bpcal_solved is True
        assert gaincal_solved is True
        assert error_msg is None
        assert mock_bp.called
        assert mock_gains.called


@pytest.mark.integration
def test_solve_calibration_for_group_existing_tables(mosaic_manager, registered_group, tmp_path):
    """Test solve_calibration_for_group uses existing tables from registry."""
    # Create mock calibration tables (as directories for CASA tables)
    bp_table = tmp_path / "bp.table"
    gp_table = tmp_path / "gp.table"
    g2_table = tmp_path / "2g.table"
    bp_table.mkdir()
    (bp_table / "table.dat").touch()
    gp_table.mkdir()
    (gp_table / "table.dat").touch()
    g2_table.mkdir()
    (g2_table / "table.dat").touch()
    
    cal_ms_path = tmp_path / "cal.ms"
    cal_ms_path.mkdir()
    (cal_ms_path / "table.dat").touch()
    
    with patch("dsa110_contimg.mosaic.streaming_mosaic.extract_ms_time_range") as mock_extract:
        mock_extract.return_value = (None, None, 60000.0)
        
        # Mock registry to return existing tables
        with patch.object(
            mosaic_manager,
            "check_registry_for_calibration",
            return_value={
                "BP": [str(bp_table)],
                "GP": [str(gp_table)],
                "2G": [str(g2_table)],
            },
        ):
            bpcal_solved, gaincal_solved, error_msg = mosaic_manager.solve_calibration_for_group(
                registered_group, str(cal_ms_path)
            )
        
        # Should return True without solving (tables exist)
        assert bpcal_solved is True
        assert gaincal_solved is True
        assert error_msg is None


@pytest.mark.integration
def test_solve_calibration_for_group_bp_only(mosaic_manager, registered_group, tmp_path):
    """Test solve_calibration_for_group when only BP is solved."""
    cal_ms_path = tmp_path / "cal.ms"
    cal_ms_path.mkdir()
    (cal_ms_path / "table.dat").touch()
    
    # Register a bandpass calibrator
    mosaic_manager.register_bandpass_calibrator(
        calibrator_name="0834+555",
        ra_deg=129.0,
        dec_deg=-30.0,
        dec_tolerance=5.0,
    )
    
    # Mock casacore.tables - need to patch where it's imported inside the function
    mock_table = MagicMock()
    mock_table.getkeyword.return_value = [
        {"REFERENCE_DIR": [[0.0, -0.523599]]}  # ~-30 deg Dec
    ]
    mock_table.close.return_value = None
    
    # Create a mock casatables module
    mock_casatables_module = MagicMock()
    mock_casatables_module.table = MagicMock(return_value=mock_table)
    
    with patch("dsa110_contimg.mosaic.streaming_mosaic.solve_bandpass") as mock_bp, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.solve_gains") as mock_gains, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.extract_ms_time_range") as mock_extract, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.select_bandpass_from_catalog") as mock_select, \
         patch("casacore.tables", mock_casatables_module):
        
        mock_extract.return_value = (None, None, 60000.0)
        import numpy as np
        mock_select.return_value = (
            "0",  # field_sel_str
            [0],  # field_indices
            np.array([1.0]),  # weighted_flux_per_field
            ("0834+555", 129.0, -30.0, 1.0),  # calibrator_info: (name, ra_deg, dec_deg, flux_jy)
            0,  # peak_field_idx
        )
        mock_bp.return_value = (True, "/test/bp.table")
        mock_gains.return_value = (False, None)  # Gains fail
        
        with patch.object(mosaic_manager, "check_registry_for_calibration", return_value={"BP": [], "GP": [], "2G": []}):
            bpcal_solved, gaincal_solved, error_msg = mosaic_manager.solve_calibration_for_group(
                registered_group, str(cal_ms_path)
            )
        
        assert bpcal_solved is True
        assert gaincal_solved is False
        assert error_msg is None  # Partial success is acceptable


@pytest.mark.integration
def test_apply_calibration_to_group_success(mosaic_manager, registered_group, mock_ms_files, tmp_path):
    """Test apply_calibration_to_group successfully applies calibration."""
    # Create mock calibration tables
    bp_table = tmp_path / "bp.table"
    gp_table = tmp_path / "gp.table"
    g2_table = tmp_path / "2g.table"
    bp_table.mkdir()
    (bp_table / "table.dat").touch()
    gp_table.mkdir()
    (gp_table / "table.dat").touch()
    g2_table.mkdir()
    (g2_table / "table.dat").touch()
    
    # Mock applycal function
    with patch("dsa110_contimg.mosaic.streaming_mosaic.apply_to_target") as mock_apply, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.extract_ms_time_range") as mock_extract, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.get_active_applylist") as mock_get_applylist:
        
        # Mock time extraction for each MS - use a callable to avoid StopIteration
        def extract_side_effect(ms_path):
            # Return different times for each MS
            idx = mock_ms_files.index(ms_path) if ms_path in mock_ms_files else 0
            return (None, None, 60000.0 + idx * 0.00347)
        
        mock_extract.side_effect = extract_side_effect
        
        # Mock registry to return calibration tables
        mock_get_applylist.return_value = [str(bp_table), str(gp_table), str(g2_table)]
        
        # Mock successful application
        mock_apply.return_value = True
        
        result = mosaic_manager.apply_calibration_to_group(registered_group)
        
        assert result is True
        assert mock_apply.call_count == len(mock_ms_files)
        
        # Verify database state updated
        cursor = mosaic_manager.products_db.cursor()
        cursor.execute(
            "SELECT cal_applied, stage FROM mosaic_groups WHERE group_id = ?",
            (registered_group,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1  # cal_applied = True
        assert row[1] == "calibrated"


@pytest.mark.integration
def test_apply_calibration_to_group_already_applied(mosaic_manager, registered_group):
    """Test apply_calibration_to_group skips when already applied."""
    # Set database state to already calibrated
    cursor = mosaic_manager.products_db.cursor()
    cursor.execute(
        "UPDATE mosaic_groups SET cal_applied = 1, stage = 'calibrated' WHERE group_id = ?",
        (registered_group,),
    )
    mosaic_manager.products_db.commit()
    
    with patch("dsa110_contimg.mosaic.streaming_mosaic.apply_to_target") as mock_apply:
        result = mosaic_manager.apply_calibration_to_group(registered_group)
        
        assert result is True
        assert not mock_apply.called  # Should skip application


@pytest.mark.integration
def test_image_group_success(mosaic_manager, registered_group, mock_ms_files, temp_dirs):
    """Test image_group successfully images all MS files."""
    # Set group to calibrated state
    cursor = mosaic_manager.products_db.cursor()
    cursor.execute(
        "UPDATE mosaic_groups SET stage = 'calibrated' WHERE group_id = ?",
        (registered_group,),
    )
    mosaic_manager.products_db.commit()
    
    # Mock image_ms function
    with patch("dsa110_contimg.mosaic.streaming_mosaic.image_ms") as mock_image:
        # Mock successful imaging - create mock output files
        def create_mock_images(*args, **kwargs):
            imagename = kwargs.get("imagename", args[0] if args else "test")
            img_path = Path(imagename)
            img_path.parent.mkdir(parents=True, exist_ok=True)
            # Create mock FITS output
            fits_path = temp_dirs["images_dir"] / f"{img_path.name}-image-pb.fits"
            fits_path.parent.mkdir(parents=True, exist_ok=True)
            fits_path.touch()
            return str(fits_path)
        
        mock_image.side_effect = create_mock_images
        
        result = mosaic_manager.image_group(registered_group)
        
        assert result is True
        assert mock_image.call_count == len(mock_ms_files)
        
        # Verify database state updated
        cursor = mosaic_manager.products_db.cursor()
        cursor.execute(
            "SELECT stage FROM mosaic_groups WHERE group_id = ?",
            (registered_group,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "imaged"


@pytest.mark.integration
def test_image_group_already_imaged(mosaic_manager, registered_group, mock_ms_files, temp_dirs):
    """Test image_group skips when images already exist."""
    # Set database state to imaged
    cursor = mosaic_manager.products_db.cursor()
    cursor.execute(
        "UPDATE mosaic_groups SET stage = 'imaged' WHERE group_id = ?",
        (registered_group,),
    )
    mosaic_manager.products_db.commit()
    
    # Create mock image files
    from dsa110_contimg.utils.naming import construct_image_basename
    
    for ms_path in mock_ms_files:
        img_basename = construct_image_basename(Path(ms_path))
        imgroot = temp_dirs["images_dir"] / img_basename.replace(".img", "")
        (imgroot.parent / f"{imgroot.name}-image-pb.fits").touch()
    
    with patch("dsa110_contimg.mosaic.streaming_mosaic.image_ms") as mock_image:
        result = mosaic_manager.image_group(registered_group)
        
        assert result is True
        assert not mock_image.called  # Should skip imaging


@pytest.mark.integration
def test_create_mosaic_success(mosaic_manager, registered_group, mock_ms_files, temp_dirs):
    """Test create_mosaic successfully creates mosaic from images."""
    # Set group to imaged state
    cursor = mosaic_manager.products_db.cursor()
    cursor.execute(
        "UPDATE mosaic_groups SET stage = 'imaged' WHERE group_id = ?",
        (registered_group,),
    )
    
    # Ensure ms_index table exists and populate it
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ms_index (
            path TEXT PRIMARY KEY,
            imagename TEXT
        )
        """
    )
    
    # Create mock image files and register them in ms_index
    from dsa110_contimg.utils.naming import construct_image_basename
    
    image_paths = []
    for ms_path in mock_ms_files:
        img_basename = construct_image_basename(Path(ms_path))
        imgroot = temp_dirs["images_dir"] / img_basename.replace(".img", "")
        fits_path = imgroot.parent / f"{imgroot.name}-image-pb.fits"
        fits_path.parent.mkdir(parents=True, exist_ok=True)
        fits_path.touch()
        image_paths.append(str(fits_path))
        
        # Register in ms_index
        cursor.execute(
            "INSERT OR REPLACE INTO ms_index (path, imagename) VALUES (?, ?)",
            (ms_path, str(fits_path)),
        )
    
    mosaic_manager.products_db.commit()
    
    # Mock mosaic creation
    with patch("dsa110_contimg.mosaic.cli._build_weighted_mosaic") as mock_create, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.validate_tiles_consistency") as mock_validate:
        
        # Mock validation to return success
        mock_validate.return_value = (True, [], {})
        
        mosaic_path = str(temp_dirs["mosaics_dir"] / "test_mosaic.image")
        mock_create.return_value = None  # Function doesn't return value
        
        # Create the mosaic file (FITS format preferred)
        fits_path = mosaic_path.replace(".image", ".fits")
        Path(fits_path).touch()
        
        result = mosaic_manager.create_mosaic(registered_group)
        
        assert result == fits_path  # Should return FITS path
        assert mock_create.called
        assert mock_validate.called
        
        # Verify database state updated
        cursor = mosaic_manager.products_db.cursor()
        cursor.execute(
            "SELECT mosaic_id, stage FROM mosaic_groups WHERE group_id = ?",
            (registered_group,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] is not None  # mosaic_id set
        assert row[1] == "mosaicked"


@pytest.mark.integration
def test_create_mosaic_insufficient_images(mosaic_manager, registered_group):
    """Test create_mosaic fails with insufficient images."""
    # Set group to imaged state but don't create image files
    cursor = mosaic_manager.products_db.cursor()
    cursor.execute(
        "UPDATE mosaic_groups SET stage = 'imaged' WHERE group_id = ?",
        (registered_group,),
    )
    mosaic_manager.products_db.commit()
    
    result = mosaic_manager.create_mosaic(registered_group)
    
    assert result is None


@pytest.mark.integration
def test_full_workflow_integration(mosaic_manager, registered_group, mock_ms_files, tmp_path, temp_dirs):
    """Test full workflow: calibration -> imaging -> mosaic creation."""
    # Step 1: Solve calibration
    cal_ms_path = tmp_path / "cal.ms"
    cal_ms_path.mkdir()
    (cal_ms_path / "table.dat").touch()
    
    bp_table = tmp_path / "bp.table"
    gp_table = tmp_path / "gp.table"
    g2_table = tmp_path / "2g.table"
    bp_table.mkdir()
    gp_table.mkdir()
    g2_table.mkdir()
    
    with patch("dsa110_contimg.mosaic.streaming_mosaic.solve_bandpass") as mock_bp, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.solve_gains") as mock_gains, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.extract_ms_time_range") as mock_extract, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.apply_to_target") as mock_apply, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.get_active_applylist") as mock_get_applylist, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.image_ms") as mock_image, \
         patch("dsa110_contimg.mosaic.cli._build_weighted_mosaic") as mock_create, \
         patch("dsa110_contimg.mosaic.streaming_mosaic.validate_tiles_consistency") as mock_validate:
        
        # Mock calibration solving
        mock_extract.return_value = (None, None, 60000.0)
        mock_bp.return_value = (True, str(bp_table))
        mock_gains.return_value = (True, [str(gp_table), str(g2_table)])
        
        with patch.object(mosaic_manager, "check_registry_for_calibration", return_value={"BP": [], "GP": [], "2G": []}):
            bpcal_solved, gaincal_solved, _ = mosaic_manager.solve_calibration_for_group(
                registered_group, str(cal_ms_path)
            )
        
        assert bpcal_solved and gaincal_solved
        
        # Step 2: Apply calibration
        mock_get_applylist.return_value = [str(bp_table), str(gp_table), str(g2_table)]
        mock_apply.return_value = True
        mock_extract.side_effect = [(None, None, 60000.0 + i * 0.00347) for i in range(len(mock_ms_files))]
        
        apply_result = mosaic_manager.apply_calibration_to_group(registered_group)
        assert apply_result is True
        
        # Step 3: Image group
        def create_mock_images(*args, **kwargs):
            imagename = kwargs.get("imagename", args[0] if args else "test")
            fits_path = temp_dirs["images_dir"] / f"{Path(imagename).name}-image-pb.fits"
            fits_path.parent.mkdir(parents=True, exist_ok=True)
            fits_path.touch()
            return str(fits_path)
        
        mock_image.side_effect = create_mock_images
        image_result = mosaic_manager.image_group(registered_group)
        assert image_result is True
        
        # Step 4: Create mosaic
        mock_validate.return_value = (True, [], {})
        
        mosaic_path = str(temp_dirs["mosaics_dir"] / "test_mosaic.image")
        mock_create.return_value = None
        
        # Create the mosaic file (FITS format preferred)
        fits_path = mosaic_path.replace(".image", ".fits")
        Path(fits_path).touch()
        
        mosaic_result = mosaic_manager.create_mosaic(registered_group)
        assert mosaic_result == fits_path
        
        # Verify final database state
        cursor = mosaic_manager.products_db.cursor()
        cursor.execute(
            "SELECT bpcal_solved, gaincal_solved, cal_applied, stage FROM mosaic_groups WHERE group_id = ?",
            (registered_group,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1  # bpcal_solved
        assert row[1] == 1  # gaincal_solved
        assert row[2] == 1  # cal_applied
        assert row[3] == "mosaicked"  # stage

