# mypy: disable-error-code="import-not-found,import-untyped"
"""
Unit tests for Absurd pipeline adapter.

Tests task routing and execution with mocked pipeline stages.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # type: ignore[import-not-found]

from dsa110_contimg.absurd.adapter import execute_pipeline_task  # type: ignore[import-not-found]

# --- execute_pipeline_task Routing Tests ---


class TestTaskRouting:
    """Tests for task routing in execute_pipeline_task."""

    @pytest.mark.asyncio
    async def test_unknown_task_raises_value_error(self):
        """Unknown task name should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown task name"):
            await execute_pipeline_task("unknown-task", {})

    @pytest.mark.asyncio
    async def test_convert_task_routes_correctly(self):
        """convert-uvh5-to-ms should route to execute_conversion."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_conversion", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"status": "success"}
            result = await execute_pipeline_task("convert-uvh5-to-ms", {"config": {}, "inputs": {}})
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_calibration_solve_routes_correctly(self):
        """calibration-solve should route to execute_calibration_solve."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_calibration_solve", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"status": "success"}
            result = await execute_pipeline_task("calibration-solve", {"config": {}, "inputs": {}})
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_calibration_apply_routes_correctly(self):
        """calibration-apply should route to execute_calibration_apply."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_calibration_apply", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"status": "success"}
            result = await execute_pipeline_task("calibration-apply", {"config": {}, "inputs": {}})
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_imaging_routes_correctly(self):
        """imaging should route to execute_imaging."""
        with patch("dsa110_contimg.absurd.adapter.execute_imaging", new_callable=AsyncMock) as mock:
            mock.return_value = {"status": "success"}
            result = await execute_pipeline_task("imaging", {"config": {}, "inputs": {}})
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_routes_correctly(self):
        """validation should route to execute_validation."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_validation", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"status": "success"}
            result = await execute_pipeline_task("validation", {"config": {}, "inputs": {}})
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_crossmatch_routes_correctly(self):
        """crossmatch should route to execute_crossmatch."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_crossmatch", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"status": "success"}
            result = await execute_pipeline_task("crossmatch", {"config": {}, "inputs": {}})
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_photometry_routes_correctly(self):
        """photometry should route to execute_photometry."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_photometry", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"status": "success"}
            result = await execute_pipeline_task("photometry", {"config": {}, "inputs": {}})
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_catalog_setup_routes_correctly(self):
        """catalog-setup should route to execute_catalog_setup."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_catalog_setup", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"status": "success"}
            result = await execute_pipeline_task("catalog-setup", {"config": {}, "inputs": {}})
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_organize_files_routes_correctly(self):
        """organize-files should route to execute_organize_files."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_organize_files", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"status": "success"}
            result = await execute_pipeline_task("organize-files", {"config": {}, "inputs": {}})
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_housekeeping_routes_correctly(self):
        """housekeeping should route to execute_housekeeping."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_housekeeping", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {"status": "success"}
            result = await execute_pipeline_task("housekeeping", {"config": {}, "inputs": {}})
            mock.assert_called_once()


# --- Task Result Tests ---


class TestTaskResults:
    """Tests for task result structure."""

    @pytest.mark.asyncio
    async def test_success_result_structure(self):
        """Successful task should return proper structure."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_conversion", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {
                "status": "success",
                "outputs": {"ms_path": "/data/obs.ms"},
                "message": "Done",
            }
            result = await execute_pipeline_task("convert-uvh5-to-ms", {"config": {}, "inputs": {}})

            assert result["status"] == "success"
            assert "outputs" in result
            assert "message" in result

    @pytest.mark.asyncio
    async def test_error_result_structure(self):
        """Failed task should return error structure."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_conversion", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {
                "status": "error",
                "message": "Missing input",
                "errors": ["No input_path"],
            }
            result = await execute_pipeline_task("convert-uvh5-to-ms", {"config": {}, "inputs": {}})

            assert result["status"] == "error"
            assert "message" in result
            assert "errors" in result


# --- Integration with Config Loading Tests ---


class TestConfigLoading:
    """Tests for config loading in task executors."""

    @pytest.mark.asyncio
    async def test_missing_required_inputs_returns_error(self):
        """Missing required inputs should return error status."""
        # Test conversion without required inputs
        with patch("dsa110_contimg.absurd.adapter._load_config") as mock_load:
            mock_load.return_value = MagicMock()

            from dsa110_contimg.absurd.adapter import execute_conversion

            result = await execute_conversion({"config": {}, "inputs": {}})

            assert result["status"] == "error"
            assert "Missing" in result["message"] or "missing" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_validation_failure_returns_error(self):
        """Validation failure should return error status."""
        with patch("dsa110_contimg.absurd.adapter._load_config") as mock_load:
            mock_config = MagicMock()
            mock_load.return_value = mock_config

            with patch("dsa110_contimg.absurd.adapter.PipelineContext") as mock_context_cls:
                with patch("dsa110_contimg.absurd.adapter.ConversionStage") as mock_stage_cls:
                    mock_stage = MagicMock()
                    mock_stage.validate.return_value = (False, "Missing input file")
                    mock_stage_cls.return_value = mock_stage

                    from dsa110_contimg.absurd.adapter import execute_conversion

                    result = await execute_conversion(
                        {
                            "config": {},
                            "inputs": {
                                "input_path": "/data/obs.hdf5",
                                "start_time": "2025-01-01T00:00:00",
                                "end_time": "2025-01-01T01:00:00",
                            },
                        }
                    )

                    assert result["status"] == "error"
                    assert "Validation failed" in result["message"]


# --- Housekeeping Task Tests ---


class TestHousekeepingTask:
    """Tests for housekeeping task execution."""

    @pytest.mark.asyncio
    async def test_housekeeping_with_cleanup_days(self):
        """Housekeeping should handle cleanup_days parameter."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_housekeeping", new_callable=AsyncMock
        ) as mock:
            mock.return_value = {
                "status": "success",
                "outputs": {"cleaned_files": 10, "freed_bytes": 1024 * 1024 * 100},
                "message": "Cleaned 10 files",
            }
            result = await execute_pipeline_task(
                "housekeeping",
                {"config": {}, "inputs": {"cleanup_days": 7}},
            )

            assert result["status"] == "success"
            mock.assert_called_once()
            call_params = mock.call_args[0][0]
            assert call_params["inputs"]["cleanup_days"] == 7
