"""
Unit tests for Absurd pipeline adapter.

Tests the task executor functions that wrap pipeline stages.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from dsa110_contimg.absurd.adapter import (
    execute_calibration_apply,
    execute_calibration_solve,
    execute_catalog_setup,
    execute_conversion,
    execute_crossmatch,
    execute_imaging,
    execute_organize_files,
    execute_photometry,
    execute_pipeline_task,
    execute_validation,
)


@pytest.mark.unit
class TestExecutePipelineTask:
    """Tests for the main task router."""

    @pytest.mark.asyncio
    async def test_route_convert_uvh5_to_ms(self):
        """Test routing to convert-uvh5-to-ms executor."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_conversion",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success"}

            params = {"config": Mock(), "inputs": {}}
            result = await execute_pipeline_task("convert-uvh5-to-ms", params)

            assert result["status"] == "success"
            mock_exec.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_route_calibration_solve(self):
        """Test routing to calibration-solve executor."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_calibration_solve",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success"}

            params = {"config": Mock(), "outputs": {"ms_path": "/test.ms"}}
            result = await execute_pipeline_task("calibration-solve", params)

            assert result["status"] == "success"
            mock_exec.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_route_calibration_apply(self):
        """Test routing to calibration-apply executor."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_calibration_apply",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success"}

            params = {
                "config": Mock(),
                "outputs": {
                    "ms_path": "/test.ms",
                    "calibration_tables": {},
                },
            }
            result = await execute_pipeline_task("calibration-apply", params)

            assert result["status"] == "success"
            mock_exec.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_route_imaging(self):
        """Test routing to imaging executor."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_imaging",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success"}

            params = {"config": Mock(), "outputs": {"ms_path": "/test.ms"}}
            result = await execute_pipeline_task("imaging", params)

            assert result["status"] == "success"
            mock_exec.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_route_validation(self):
        """Test routing to validation executor."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_validation",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success"}

            params = {"config": Mock(), "outputs": {"image_path": "/test.fits"}}
            result = await execute_pipeline_task("validation", params)

            assert result["status"] == "success"
            mock_exec.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_route_crossmatch(self):
        """Test routing to crossmatch executor."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_crossmatch",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success"}

            params = {"config": Mock(), "outputs": {"image_path": "/test.fits"}}
            result = await execute_pipeline_task("crossmatch", params)

            assert result["status"] == "success"
            mock_exec.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_route_photometry(self):
        """Test routing to photometry executor."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_photometry",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success"}

            params = {"config": Mock(), "outputs": {"ms_path": "/test.ms"}}
            result = await execute_pipeline_task("photometry", params)

            assert result["status"] == "success"
            mock_exec.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_route_catalog_setup(self):
        """Test routing to catalog-setup executor."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_catalog_setup",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success"}

            params = {"config": Mock(), "inputs": {"input_path": "/data/obs.hdf5"}}
            result = await execute_pipeline_task("catalog-setup", params)

            assert result["status"] == "success"
            mock_exec.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_route_organize_files(self):
        """Test routing to organize-files executor."""
        with patch(
            "dsa110_contimg.absurd.adapter.execute_organize_files",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success"}

            params = {"config": Mock(), "outputs": {"ms_path": "/data/raw/obs.ms"}}
            result = await execute_pipeline_task("organize-files", params)

            assert result["status"] == "success"
            mock_exec.assert_called_once_with(params)

    @pytest.mark.asyncio
    async def test_route_unknown_task(self):
        """Test routing with unknown task name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown task name"):
            await execute_pipeline_task("unknown-task", {})


@pytest.mark.unit
class TestExecuteConversion:
    """Tests for UVH5 to MS conversion executor."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful conversion."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {"ms_path": "/output/test.ms"}

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.ConversionStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute) as mock_thread,
        ):
            params = {
                "config": mock_config,
                "inputs": {
                    "input_path": "/data/obs.hdf5",
                    "start_time": "2025-01-01T00:00:00",
                    "end_time": "2025-01-01T01:00:00",
                },
            }

            result = await execute_conversion(params)

            assert result["status"] == "success"
            assert result["outputs"]["ms_path"] == "/output/test.ms"
            assert "Conversion completed" in result["message"]
            mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_inputs(self):
        """Test conversion with missing required inputs."""
        mock_config = Mock()

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            return_value=mock_config,
        ):
            params = {
                "config": mock_config,
                "inputs": {
                    "input_path": "/data/obs.hdf5",
                    # Missing start_time and end_time
                },
            }

            result = await execute_conversion(params)

            assert result["status"] == "error"
            assert "Missing required inputs" in result["message"]
            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Test conversion when stage validation fails."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (
            False,
            "Input file does not exist",
        )

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.ConversionStage",
                return_value=mock_stage,
            ),
        ):
            params = {
                "config": mock_config,
                "inputs": {
                    "input_path": "/data/obs.hdf5",
                    "start_time": "2025-01-01T00:00:00",
                    "end_time": "2025-01-01T01:00:00",
                },
            }

            result = await execute_conversion(params)

            assert result["status"] == "error"
            assert "Validation failed" in result["message"]
            assert "Input file does not exist" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_execution_exception(self):
        """Test conversion when execution raises exception."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.ConversionStage",
                return_value=mock_stage,
            ),
            patch(
                "asyncio.to_thread",
                side_effect=RuntimeError("CASA error"),
            ),
        ):
            params = {
                "config": mock_config,
                "inputs": {
                    "input_path": "/data/obs.hdf5",
                    "start_time": "2025-01-01T00:00:00",
                    "end_time": "2025-01-01T01:00:00",
                },
            }

            result = await execute_conversion(params)

            assert result["status"] == "error"
            assert "CASA error" in result["message"]


@pytest.mark.unit
class TestExecuteCalibrationSolve:
    """Tests for calibration solution solving executor."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful calibration solve."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {
            "calibration_tables": {
                "K": "/cal/K.cal",
                "BP": "/cal/BP.cal",
                "G": "/cal/G.cal",
            }
        }

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.CalibrationSolveStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute) as mock_thread,
        ):
            params = {
                "config": mock_config,
                "outputs": {"ms_path": "/data/test.ms"},
            }

            result = await execute_calibration_solve(params)

            assert result["status"] == "success"
            assert "K" in result["outputs"]["calibration_tables"]
            assert "BP" in result["outputs"]["calibration_tables"]
            assert "successfully" in result["message"]
            mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_ms_path(self):
        """Test calibration solve with missing ms_path."""
        mock_config = Mock()

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            return_value=mock_config,
        ):
            params = {"config": mock_config, "inputs": {}, "outputs": {}}

            result = await execute_calibration_solve(params)

            assert result["status"] == "error"
            assert "Missing required input: ms_path" in result["message"]

    @pytest.mark.asyncio
    async def test_ms_path_in_inputs(self):
        """Test calibration solve with ms_path in inputs."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {"calibration_tables": {"K": "/cal/K.cal"}}

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.CalibrationSolveStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute),
        ):
            # ms_path in inputs instead of outputs
            params = {
                "config": mock_config,
                "inputs": {"ms_path": "/data/test.ms"},
                "outputs": {},
            }

            result = await execute_calibration_solve(params)

            assert result["status"] == "success"


@pytest.mark.unit
class TestExecuteCalibrationApply:
    """Tests for calibration application executor."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful calibration apply."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {"ms_path": "/data/calibrated.ms"}

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.CalibrationStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute) as mock_thread,
        ):
            params = {
                "config": mock_config,
                "outputs": {
                    "ms_path": "/data/test.ms",
                    "calibration_tables": {
                        "K": "/cal/K.cal",
                        "BP": "/cal/BP.cal",
                    },
                },
            }

            result = await execute_calibration_apply(params)

            assert result["status"] == "success"
            assert result["outputs"]["ms_path"] == "/data/calibrated.ms"
            assert "successfully" in result["message"]
            mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_ms_path(self):
        """Test calibration apply with missing ms_path."""
        mock_config = Mock()

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            return_value=mock_config,
        ):
            params = {
                "config": mock_config,
                "outputs": {"calibration_tables": {"K": "/cal/K.cal"}},
            }

            result = await execute_calibration_apply(params)

            assert result["status"] == "error"
            assert "Missing required output: ms_path" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_calibration_tables(self):
        """Test calibration apply with missing calibration_tables."""
        mock_config = Mock()

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            return_value=mock_config,
        ):
            params = {"config": mock_config, "outputs": {"ms_path": "/data/test.ms"}}

            result = await execute_calibration_apply(params)

            assert result["status"] == "error"
            assert "Missing required output: calibration_tables" in result["message"]


@pytest.mark.unit
class TestExecuteImaging:
    """Tests for imaging executor."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful imaging."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {"image_path": "/output/image.fits"}

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.ImagingStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute) as mock_thread,
        ):
            params = {
                "config": mock_config,
                "outputs": {"ms_path": "/data/calibrated.ms"},
            }

            result = await execute_imaging(params)

            assert result["status"] == "success"
            assert result["outputs"]["image_path"] == "/output/image.fits"
            assert "successfully" in result["message"]
            mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_ms_path(self):
        """Test imaging with missing ms_path."""
        mock_config = Mock()

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            return_value=mock_config,
        ):
            params = {"config": mock_config, "outputs": {}}

            result = await execute_imaging(params)

            assert result["status"] == "error"
            assert "Missing required output: ms_path" in result["message"]

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Test imaging when stage validation fails."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (
            False,
            "MS file does not exist",
        )

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.ImagingStage",
                return_value=mock_stage,
            ),
        ):
            params = {
                "config": mock_config,
                "outputs": {"ms_path": "/data/calibrated.ms"},
            }

            result = await execute_imaging(params)

            assert result["status"] == "error"
            assert "Validation failed" in result["message"]


@pytest.mark.unit
class TestLoadConfig:
    """Tests for _load_config helper function."""

    def test_load_from_dict(self):
        """Test loading config from dict."""
        from dsa110_contimg.absurd.adapter import _load_config

        # Test that dict is passed through to PipelineConfig constructor
        # We can't easily mock PipelineConfig because isinstance() checks fail
        # So just verify it tries to create a PipelineConfig
        with pytest.raises(Exception):  # Will fail due to missing fields
            _load_config({"invalid": "config"})

    def test_load_from_none(self):
        """Test loading default config when param is None."""
        from dsa110_contimg.absurd.adapter import _load_config
        from dsa110_contimg.pipeline.config import PipelineConfig

        mock_config = Mock(spec=PipelineConfig)

        with patch.object(PipelineConfig, "from_env", return_value=mock_config):
            result = _load_config(None)
            assert result == mock_config

    def test_load_from_path(self):
        """Test loading config from YAML path."""
        from dsa110_contimg.absurd.adapter import _load_config
        from dsa110_contimg.pipeline.config import PipelineConfig

        mock_config = Mock(spec=PipelineConfig)

        with patch.object(PipelineConfig, "from_yaml", return_value=mock_config):
            result = _load_config("/path/to/config.yaml")
            assert result == mock_config

    def test_load_from_instance(self):
        """Test loading config from PipelineConfig instance."""
        from dsa110_contimg.absurd.adapter import _load_config
        from dsa110_contimg.pipeline.config import PipelineConfig

        mock_config = Mock(spec=PipelineConfig)
        result = _load_config(mock_config)
        assert result == mock_config

    def test_load_invalid_type(self):
        """Test loading config with invalid type raises ValueError."""
        from dsa110_contimg.absurd.adapter import _load_config

        with pytest.raises(ValueError, match="Invalid config parameter type"):
            _load_config(12345)  # Invalid type


@pytest.mark.unit
class TestExecuteValidation:
    """Tests for image validation executor."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful validation."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {
            "validation_results": {
                "status": "passed",
                "metrics": {"astrometry_rms": 0.5},
                "report_path": "/reports/validation.html",
            }
        }

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.ValidationStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute) as mock_thread,
        ):
            params = {
                "config": mock_config,
                "outputs": {"image_path": "/data/image.fits"},
            }

            result = await execute_validation(params)

            assert result["status"] == "success"
            assert "validation_results" in result["outputs"]
            assert result["outputs"]["validation_results"]["status"] == "passed"
            assert "passed" in result["message"]
            mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_image_path(self):
        """Test validation with missing image_path."""
        mock_config = Mock()

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            return_value=mock_config,
        ):
            params = {"config": mock_config, "outputs": {}}

            result = await execute_validation(params)

            assert result["status"] == "error"
            assert "Missing required output: image_path" in result["message"]

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Test validation when stage validation fails."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (
            False,
            "Validation stage is disabled",
        )

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.ValidationStage",
                return_value=mock_stage,
            ),
        ):
            params = {
                "config": mock_config,
                "outputs": {"image_path": "/data/image.fits"},
            }

            result = await execute_validation(params)

            assert result["status"] == "error"
            assert "Validation failed" in result["message"]


@pytest.mark.unit
class TestExecuteCrossmatch:
    """Tests for source cross-matching executor."""

    @pytest.mark.asyncio
    async def test_success_with_image_path(self):
        """Test successful cross-match with image_path."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {
            "crossmatch_results": {
                "matches": [{"source_id": 1, "catalog_id": 100}],
                "offsets": {"ra": 0.1, "dec": 0.2},
                "flux_scales": {"nvss": 1.05},
            }
        }

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.CrossMatchStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute) as mock_thread,
        ):
            params = {
                "config": mock_config,
                "outputs": {"image_path": "/data/image.fits"},
            }

            result = await execute_crossmatch(params)

            assert result["status"] == "success"
            assert "crossmatch_results" in result["outputs"]
            assert len(result["outputs"]["crossmatch_results"]["matches"]) == 1
            assert "1 matches" in result["message"]
            mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_with_detected_sources(self):
        """Test successful cross-match with detected_sources."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {
            "crossmatch_results": {
                "matches": [{"source_id": 1}, {"source_id": 2}],
            }
        }

        async def mock_execute(*args, **kwargs):
            return mock_context

        # Create a mock DataFrame
        import pandas as pd

        detected_sources = pd.DataFrame({"ra": [10.0, 20.0], "dec": [30.0, 40.0]})

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.CrossMatchStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute),
        ):
            params = {
                "config": mock_config,
                "outputs": {"detected_sources": detected_sources},
            }

            result = await execute_crossmatch(params)

            assert result["status"] == "success"
            assert "2 matches" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_required_outputs(self):
        """Test cross-match with missing required outputs."""
        mock_config = Mock()

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            return_value=mock_config,
        ):
            params = {"config": mock_config, "outputs": {}}

            result = await execute_crossmatch(params)

            assert result["status"] == "error"
            assert "Missing required output" in result["message"]


@pytest.mark.unit
class TestExecutePhotometry:
    """Tests for adaptive photometry executor."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful photometry."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)

        # Create mock photometry results
        import pandas as pd

        photometry_results = pd.DataFrame(
            {
                "source_id": [1, 2, 3],
                "flux": [10.5, 20.3, 15.7],
                "flux_err": [0.5, 1.2, 0.8],
            }
        )

        mock_context = Mock()
        mock_context.outputs = {"photometry_results": photometry_results}

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.AdaptivePhotometryStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute) as mock_thread,
        ):
            params = {
                "config": mock_config,
                "outputs": {
                    "ms_path": "/data/calibrated.ms",
                    "image_path": "/data/image.fits",
                },
            }

            result = await execute_photometry(params)

            assert result["status"] == "success"
            assert "photometry_results" in result["outputs"]
            assert len(result["outputs"]["photometry_results"]) == 3
            assert "3 sources" in result["message"]
            mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_without_image_path(self):
        """Test successful photometry without image_path."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)

        import pandas as pd

        photometry_results = pd.DataFrame({"source_id": [1], "flux": [10.5]})

        mock_context = Mock()
        mock_context.outputs = {"photometry_results": photometry_results}

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.AdaptivePhotometryStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute),
        ):
            params = {
                "config": mock_config,
                "outputs": {"ms_path": "/data/calibrated.ms"},
            }

            result = await execute_photometry(params)

            assert result["status"] == "success"
            assert "1 sources" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_ms_path(self):
        """Test photometry with missing ms_path."""
        mock_config = Mock()

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            return_value=mock_config,
        ):
            params = {"config": mock_config, "outputs": {}}

            result = await execute_photometry(params)

            assert result["status"] == "error"
            assert "Missing required output: ms_path" in result["message"]

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Test photometry when stage validation fails."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (False, "MS file not found")

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.AdaptivePhotometryStage",
                return_value=mock_stage,
            ),
        ):
            params = {
                "config": mock_config,
                "outputs": {"ms_path": "/data/calibrated.ms"},
            }

            result = await execute_photometry(params)

            assert result["status"] == "error"
            assert "Validation failed" in result["message"]


@pytest.mark.unit
class TestExecuteCatalogSetup:
    """Tests for catalog setup executor."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful catalog setup."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {"catalog_setup_status": "completed"}

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.CatalogSetupStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute) as mock_thread,
        ):
            params = {
                "config": mock_config,
                "inputs": {"input_path": "/data/observation.hdf5"},
            }

            result = await execute_catalog_setup(params)

            assert result["status"] == "success"
            assert "catalog_setup_status" in result["outputs"]
            assert result["outputs"]["catalog_setup_status"] == "completed"
            assert "completed" in result["message"]
            mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_input_path(self):
        """Test catalog setup with missing input_path."""
        mock_config = Mock()

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            return_value=mock_config,
        ):
            params = {"config": mock_config, "inputs": {}}

            result = await execute_catalog_setup(params)

            assert result["status"] == "error"
            assert "Missing required input: input_path" in result["message"]

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Test catalog setup when stage validation fails."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (False, "Input file not found")

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.CatalogSetupStage",
                return_value=mock_stage,
            ),
        ):
            params = {
                "config": mock_config,
                "inputs": {"input_path": "/data/observation.hdf5"},
            }

            result = await execute_catalog_setup(params)

            assert result["status"] == "error"
            assert "Validation failed" in result["message"]


@pytest.mark.unit
class TestExecuteOrganizeFiles:
    """Tests for file organization executor."""

    @pytest.mark.asyncio
    async def test_success_with_ms_path(self):
        """Test successful organization with ms_path."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {"ms_path": "/data/ms/science/2025-01-01/obs.ms"}

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.OrganizationStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute) as mock_thread,
        ):
            params = {
                "config": mock_config,
                "outputs": {"ms_path": "/data/raw/obs.ms"},
            }

            result = await execute_organize_files(params)

            assert result["status"] == "success"
            assert "ms_path" in result["outputs"]
            assert "science/2025-01-01" in result["outputs"]["ms_path"]
            assert "successfully" in result["message"]
            mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_with_ms_paths(self):
        """Test successful organization with ms_paths."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (True, None)
        mock_context = Mock()
        mock_context.outputs = {
            "ms_paths": [
                "/data/ms/science/2025-01-01/obs1.ms",
                "/data/ms/science/2025-01-01/obs2.ms",
            ]
        }

        async def mock_execute(*args, **kwargs):
            return mock_context

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.OrganizationStage",
                return_value=mock_stage,
            ),
            patch("asyncio.to_thread", side_effect=mock_execute),
        ):
            params = {
                "config": mock_config,
                "outputs": {"ms_paths": ["/data/raw/obs1.ms", "/data/raw/obs2.ms"]},
            }

            result = await execute_organize_files(params)

            assert result["status"] == "success"
            assert "ms_paths" in result["outputs"]
            assert len(result["outputs"]["ms_paths"]) == 2
            assert "2 files" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_required_outputs(self):
        """Test organization with missing required outputs."""
        mock_config = Mock()

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            return_value=mock_config,
        ):
            params = {"config": mock_config, "outputs": {}}

            result = await execute_organize_files(params)

            assert result["status"] == "error"
            assert "Missing required output" in result["message"]

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Test organization when stage validation fails."""
        mock_config = Mock()
        mock_stage = Mock()
        mock_stage.validate.return_value = (
            False,
            "MS base directory does not exist",
        )

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=mock_config,
            ),
            patch(
                "dsa110_contimg.absurd.adapter.OrganizationStage",
                return_value=mock_stage,
            ),
        ):
            params = {
                "config": mock_config,
                "outputs": {"ms_path": "/data/raw/obs.ms"},
            }

            result = await execute_organize_files(params)

            assert result["status"] == "error"
            assert "Validation failed" in result["message"]
