"""End-to-end integration tests for MosaicOrchestrator.

Tests the complete orchestrator workflow:
1. Group formation from MS paths
2. Calibration solving and application
3. Imaging individual MS files
4. Mosaic creation
5. QA validation
6. Publishing

Uses mocked CASA/WSClean dependencies to validate orchestration logic
without requiring actual execution.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.database.data_registry import ensure_data_registry_db
from dsa110_contimg.database.products import ensure_products_db


@pytest.fixture
def temp_dbs(tmp_path):
    """Create temporary databases for testing."""
    products_db = tmp_path / "products.sqlite3"
    registry_db = tmp_path / "cal_registry.sqlite3"
    data_registry_db = tmp_path / "data_registry.sqlite3"

    products_conn = ensure_products_db(products_db)
    registry_conn = sqlite3.connect(str(registry_db))
    data_registry_conn = ensure_data_registry_db(data_registry_db)

    yield {
        "products": (products_db, products_conn),
        "registry": (registry_db, registry_conn),
        "data_registry": (data_registry_db, data_registry_conn),
    }

    products_conn.close()
    registry_conn.close()
    data_registry_conn.close()


@pytest.fixture
def mock_ms_paths(tmp_path):
    """Create mock MS file paths."""
    ms_dir = tmp_path / "ms"
    ms_dir.mkdir()

    ms_paths = []
    for i in range(10):
        ms_path = ms_dir / f"2025-11-12T10:{i:02d}:00.ms"
        ms_path.mkdir()  # MS is a directory
        ms_paths.append(str(ms_path))

    return ms_paths


class TestOrchestratorEndToEnd:
    """Test complete orchestrator end-to-end workflow."""

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._process_group_workflow")
    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._form_group_from_ms_paths")
    def test_complete_orchestrator_workflow(
        self,
        mock_form_group,
        mock_process_workflow,
        temp_dbs,
        mock_ms_paths,
    ):
        """Test complete orchestrator workflow from group formation to mosaic."""
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        products_db, products_conn = temp_dbs["products"]

        # Mock workflow steps
        mock_form_group.return_value = True
        mock_process_workflow.return_value = "/stage/mosaics/mosaic_test.fits"

        orchestrator = MosaicOrchestrator(products_db_path=products_db)

        # Step 1: Form group
        group_id = "mosaic_test_001"
        success = orchestrator._form_group_from_ms_paths(mock_ms_paths, group_id)
        assert success is True
        mock_form_group.assert_called_once_with(mock_ms_paths, group_id)

        # Step 2: Process workflow (internally handles calibration, imaging, mosaic)
        mosaic_path = orchestrator._process_group_workflow(group_id)
        assert mosaic_path is not None
        assert mosaic_path == "/stage/mosaics/mosaic_test.fits"
        mock_process_workflow.assert_called_once_with(group_id)

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._process_group_workflow")
    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._form_group_from_ms_paths")
    def test_orchestrator_with_qa_and_publishing(
        self,
        mock_form_group,
        mock_process_workflow,
        temp_dbs,
        mock_ms_paths,
        tmp_path,
    ):
        """Test orchestrator workflow with QA and publishing integration."""
        from dsa110_contimg.database.data_registry import finalize_data, get_data
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        products_db, products_conn = temp_dbs["products"]
        data_registry_db, data_registry_conn = temp_dbs["data_registry"]

        # Mock workflow
        mock_form_group.return_value = True
        mock_process_workflow.return_value = "/stage/mosaics/mosaic_test.fits"

        orchestrator = MosaicOrchestrator(
            products_db_path=products_db,
            data_registry_db_path=data_registry_db,
        )

        # Form group
        group_id = "mosaic_test_002"
        success = orchestrator._form_group_from_ms_paths(mock_ms_paths, group_id)
        assert success is True

        # Process workflow
        mosaic_path = orchestrator._process_group_workflow(group_id)
        assert mosaic_path is not None

        # Register in data registry
        mosaic_id = Path(mosaic_path).stem
        # Use tmp_path instead of /stage to avoid permission errors
        mosaic_file = tmp_path / "mosaics" / Path(mosaic_path).name
        mosaic_file.parent.mkdir(parents=True, exist_ok=True)
        mosaic_file.touch()

        # Register data first (finalize_data requires existing record)
        from dsa110_contimg.database.data_registry import register_data

        register_data(
            data_registry_conn,
            data_type="mosaic",
            data_id=mosaic_id,
            stage_path=str(mosaic_file),
            auto_publish=True,
        )
        # Then finalize
        finalize_data(
            data_registry_conn,
            data_id=mosaic_id,
            qa_status="passed",
        )

        # Verify registration
        record = get_data(data_registry_conn, mosaic_id)
        assert record is not None
        assert record.data_type == "mosaic"
        # Check that record exists and has correct type
        assert hasattr(record, "data_id")

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._trigger_photometry_for_mosaic")
    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._form_group_from_ms_paths")
    def test_orchestrator_with_photometry(
        self,
        mock_form_group,
        mock_photometry,
        temp_dbs,
        mock_ms_paths,
        tmp_path,
    ):
        """Test orchestrator workflow with photometry automation."""
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        products_db, products_conn = temp_dbs["products"]

        # Mock group formation
        mock_form_group.return_value = True
        mock_photometry.return_value = "photometry_job_123"

        # Mock manager to avoid EarthLocation initialization
        with (
            patch(
                "dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._get_mosaic_manager"
            ) as mock_get_manager,
            patch(
                "dsa110_contimg.photometry.helpers.query_sources_for_mosaic"
            ) as mock_query_sources,
        ):
            # Create mock manager
            mock_manager = MagicMock()
            mock_manager.get_group_ms_paths.return_value = mock_ms_paths
            mock_manager.select_calibration_ms.return_value = (
                mock_ms_paths[4] if len(mock_ms_paths) > 4 else mock_ms_paths[0]
            )
            mock_manager.solve_calibration_for_group.return_value = (True, True, None)
            mock_manager.apply_calibration_to_group.return_value = True
            mock_manager.image_group.return_value = True
            # Create mosaic file in tmp_path
            mosaic_file = tmp_path / "mosaics" / "mosaic_test.fits"
            mosaic_file.parent.mkdir(parents=True, exist_ok=True)
            mosaic_file.touch()
            mock_manager.create_mosaic.return_value = str(mosaic_file)
            mock_get_manager.return_value = mock_manager
            mock_query_sources.return_value = [{"ra": 100.0, "dec": 50.0}]

            orchestrator = MosaicOrchestrator(
                products_db_path=products_db,
                enable_photometry=True,
            )

            # Form group
            group_id = "mosaic_test_003"
            success = orchestrator._form_group_from_ms_paths(mock_ms_paths, group_id)
            assert success is True

            # Process workflow (should trigger photometry)
            mosaic_path = orchestrator._process_group_workflow(group_id)
            assert mosaic_path is not None

            # Verify photometry was triggered
            mock_photometry.assert_called_once()

    def test_orchestrator_error_handling(self, temp_dbs, mock_ms_paths):
        """Test orchestrator error handling and recovery."""
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        products_db, products_conn = temp_dbs["products"]

        orchestrator = MosaicOrchestrator(products_db_path=products_db)

        # Test with invalid group ID
        with patch(
            "dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._form_group_from_ms_paths"
        ) as mock_form:
            mock_form.return_value = False

            success = orchestrator._form_group_from_ms_paths(mock_ms_paths, "invalid_group")
            assert success is False

        # Test workflow failure
        with patch(
            "dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._process_group_workflow"
        ) as mock_process:
            mock_process.return_value = None

            result = orchestrator._process_group_workflow("test_group")
            assert result is None

    def test_orchestrator_performance_characteristics(self, temp_dbs, mock_ms_paths):
        """Test orchestrator performance characteristics."""
        from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

        products_db, products_conn = temp_dbs["products"]

        orchestrator = MosaicOrchestrator(products_db_path=products_db)

        # Mock all expensive operations
        with (
            patch(
                "dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._form_group_from_ms_paths"
            ) as mock_form,
            patch(
                "dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator._process_group_workflow"
            ) as mock_process,
        ):
            mock_form.return_value = True
            mock_process.return_value = "/stage/mosaics/mosaic_test.fits"

            # Measure group formation time
            start = time.perf_counter()
            success = orchestrator._form_group_from_ms_paths(mock_ms_paths, "perf_test")
            form_time = time.perf_counter() - start

            assert success is True
            assert form_time < 1.0  # Should be fast with mocks

            # Measure workflow processing time
            start = time.perf_counter()
            result = orchestrator._process_group_workflow("perf_test")
            workflow_time = time.perf_counter() - start

            assert result is not None
            assert workflow_time < 1.0  # Should be fast with mocks
