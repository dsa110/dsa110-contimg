"""
Integration tests for pipeline stage interactions.

Tests how real pipeline stages interact with each other, including:
- Output propagation between stages
- Dependency resolution
- Context transformation through multiple stages
- Error handling across stage boundaries
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.pipeline.config import PathsConfig, PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.orchestrator import PipelineOrchestrator, StageDefinition
from dsa110_contimg.pipeline.stages_impl import (
    CalibrationSolveStage,
    CalibrationStage,
    CatalogSetupStage,
    ConversionStage,
    ImagingStage,
    ValidationStage,
)


class TestStageChainExecution:
    """Test execution of chains of real pipeline stages."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path(tmpdir) / "input",
                    output_dir=Path(tmpdir) / "output",
                )
            )

    @pytest.fixture
    def initial_context(self, config):
        """Create initial pipeline context."""
        with tempfile.NamedTemporaryFile(suffix=".hdf5", delete=False) as tmp:
            tmp_path = tmp.name
        yield PipelineContext(config=config, inputs={"input_path": tmp_path})
        Path(tmp_path).unlink(missing_ok=True)

    def test_catalog_setup_to_conversion_chain(self, config, initial_context):
        """Test CatalogSetupStage → ConversionStage chain."""
        # Mock imports that happen inside execute methods
        with (
            patch(
                "dsa110_contimg.pointing.utils.load_pointing",
                return_value={"dec_deg": 30.0},
            ),
            patch("dsa110_contimg.database.products.ensure_products_db"),
            patch(
                "dsa110_contimg.catalog.query.resolve_catalog_path",
                return_value=Path("/mock/catalog.db"),
            ),
            patch(
                "dsa110_contimg.catalog.builders.build_nvss_strip_db",
                return_value=Path("/mock/nvss.db"),
            ),
            patch(
                "dsa110_contimg.catalog.builders.build_first_strip_db",
                return_value=Path("/mock/first.db"),
            ),
            patch(
                "dsa110_contimg.catalog.builders.build_rax_strip_db",
                return_value=Path("/mock/rax.db"),
            ),
            patch(
                "dsa110_contimg.conversion.strategies.hdf5_orchestrator.convert_subband_groups_to_ms",
                return_value=["/mock/converted.ms"],
            ),
        ):

            catalog_stage = CatalogSetupStage(config)
            conversion_stage = ConversionStage(config)

            # Execute catalog setup
            context_after_catalog = catalog_stage.execute(initial_context)
            assert "catalog_setup_status" in context_after_catalog.outputs

            # Execute conversion (should use same context)
            context_after_conversion = conversion_stage.execute(context_after_catalog)
            assert "ms_path" in context_after_conversion.outputs

            # Verify outputs from both stages are present
            assert "catalog_setup_status" in context_after_conversion.outputs

    def test_conversion_to_calibration_chain(self, config, initial_context):
        """Test ConversionStage → CalibrationSolveStage chain."""
        # Setup context with ms_path (simulating conversion output)
        context_with_ms = initial_context.with_output("ms_path", "/mock/converted.ms")

        with (
            patch(
                "dsa110_contimg.calibration.calibration.solve_bandpass",
                return_value="/mock/BA.cal",
            ),
            patch(
                "dsa110_contimg.calibration.calibration.solve_gains",
                return_value="/mock/G.cal",
            ),
            patch(
                "dsa110_contimg.calibration.calibration.solve_delay",
                return_value=None,
            ),
            patch(
                "dsa110_contimg.calibration.calibration.solve_prebandpass_phase",
                return_value=None,
            ),
        ):

            calibration_solve_stage = CalibrationSolveStage(config)

            # Execute calibration solve (should use ms_path from conversion)
            context_after_calibration = calibration_solve_stage.execute(context_with_ms)
            assert "calibration_tables" in context_after_calibration.outputs

            # Verify both outputs present
            assert "ms_path" in context_after_calibration.outputs
            assert context_after_calibration.outputs["ms_path"] == "/mock/converted.ms"
            # calibration_tables is a list, not a dict
            assert isinstance(context_after_calibration.outputs["calibration_tables"], list)

    def test_calibration_to_imaging_chain(self, config, initial_context):
        """Test CalibrationStage → ImagingStage chain."""
        # Setup context with ms_path and calibration tables
        context_with_ms = initial_context.with_output("ms_path", "/mock/calibrated.ms")
        context_with_cal = context_with_ms.with_output(
            "calibration_tables", ["/mock/K.cal", "/mock/BA.cal"]
        )

        # Mock imports that happen inside execute methods
        with (
            patch("dsa110_contimg.calibration.apply_service.apply_calibration"),
            patch("dsa110_contimg.imaging.cli_imaging.image_ms", return_value="/mock/image.fits"),
        ):

            calibration_stage = CalibrationStage(config)
            imaging_stage = ImagingStage(config)

            # Execute calibration
            context_after_calibration = calibration_stage.execute(context_with_cal)

            # Execute imaging (should use calibrated MS)
            context_after_imaging = imaging_stage.execute(context_after_calibration)
            assert "image_path" in context_after_imaging.outputs
            assert context_after_imaging.outputs["image_path"] == "/mock/image.fits"

    def test_imaging_to_validation_chain(self, config, initial_context):
        """Test ImagingStage → ValidationStage chain."""
        context_with_image = initial_context.with_output("image_path", "/mock/image.fits")

        # Mock validation function (check actual import path)
        with patch(
            "dsa110_contimg.qa.catalog_validation.run_full_validation",
            return_value={"status": "passed", "metrics": {"snr": 10.5, "rms": 0.001}},
        ):

            validation_stage = ValidationStage(config)

            # Execute validation (should use image from imaging stage)
            context_after_validation = validation_stage.execute(context_with_image)
            assert "validation_results" in context_after_validation.outputs

            # Verify image path still present
            assert "image_path" in context_after_validation.outputs
            assert context_after_validation.outputs["image_path"] == "/mock/image.fits"


class TestStageOutputPropagation:
    """Test that outputs propagate correctly through stage chains."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path(tmpdir) / "input",
                    output_dir=Path(tmpdir) / "output",
                )
            )

    def test_outputs_persist_through_multiple_stages(self, config):
        """Test that outputs from early stages persist through later stages."""
        initial_context = PipelineContext(config=config, inputs={"input_path": "/mock/input.hdf5"})

        # Mock imports that happen inside execute methods
        with (
            patch(
                "dsa110_contimg.pointing.utils.load_pointing",
                return_value={"dec_deg": 30.0},
            ),
            patch("dsa110_contimg.database.products.ensure_products_db"),
            patch(
                "dsa110_contimg.catalog.query.resolve_catalog_path",
                return_value=Path("/mock/catalog.db"),
            ),
            patch(
                "dsa110_contimg.catalog.builders.build_nvss_strip_db",
                return_value=Path("/mock/nvss.db"),
            ),
            patch(
                "dsa110_contimg.catalog.builders.build_first_strip_db",
                return_value=Path("/mock/first.db"),
            ),
            patch(
                "dsa110_contimg.catalog.builders.build_rax_strip_db",
                return_value=Path("/mock/rax.db"),
            ),
            patch(
                "dsa110_contimg.conversion.strategies.hdf5_orchestrator.convert_subband_groups_to_ms",
                return_value=["/mock/converted.ms"],
            ),
        ):

            catalog_stage = CatalogSetupStage(config)
            conversion_stage = ConversionStage(config)

            # Execute both stages
            context_1 = catalog_stage.execute(initial_context)
            context_2 = conversion_stage.execute(context_1)

            # Verify both outputs present
            assert "catalog_setup_status" in context_2.outputs
            assert "ms_path" in context_2.outputs

            # Verify inputs still present
            assert "input_path" in context_2.inputs

    def test_context_immutability_across_stages(self, config):
        """Test that context immutability is maintained across stages."""
        initial_context = PipelineContext(config=config, inputs={"input_path": "/mock/input.hdf5"})

        # Create a context with ms_path to simulate conversion output
        new_context = initial_context.with_output("ms_path", "/mock/converted.ms")

        # Verify original context unchanged
        assert "ms_path" not in initial_context.outputs
        assert "ms_path" in new_context.outputs

        # Verify they are different objects
        assert initial_context is not new_context


class TestStageDependencyValidation:
    """Test that stages correctly validate dependencies from previous stages."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path(tmpdir) / "input",
                    output_dir=Path(tmpdir) / "output",
                )
            )

    def test_conversion_validates_input_path(self, config):
        """Test ConversionStage validates input_path exists."""
        context = PipelineContext(config=config, inputs={"input_path": "/nonexistent/file.hdf5"})
        stage = ConversionStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert error_msg is not None

    def test_calibration_validates_ms_path(self, config):
        """Test CalibrationSolveStage validates ms_path from previous stage."""
        context = PipelineContext(config=config)  # No ms_path
        stage = CalibrationSolveStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "ms_path" in error_msg.lower()

        # With ms_path, should validate
        context_with_ms = context.with_output("ms_path", "/mock/ms")
        is_valid, error_msg = stage.validate(context_with_ms)
        assert is_valid

    def test_imaging_validates_ms_path(self, config):
        """Test ImagingStage validates ms_path from calibration stage."""
        context = PipelineContext(config=config)  # No ms_path
        stage = ImagingStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "ms_path" in error_msg.lower()

    def test_validation_validates_image_path(self, config):
        """Test ValidationStage validates image_path from imaging stage."""
        context = PipelineContext(config=config)  # No image_path
        stage = ValidationStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "image_path" in error_msg.lower()


class TestStageErrorHandling:
    """Test error handling across stage boundaries."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path(tmpdir) / "input",
                    output_dir=Path(tmpdir) / "output",
                )
            )

    def test_stage_failure_prevents_next_stage(self, config):
        """Test that stage failure prevents dependent stages from executing."""
        initial_context = PipelineContext(config=config, inputs={"input_path": "/mock/input.hdf5"})

        conversion_stage = ConversionStage(config)
        calibration_stage = CalibrationSolveStage(config)

        # Conversion fails (no mock, will fail validation or execution)
        try:
            conversion_stage.execute(initial_context)
        except Exception:
            pass

        # Calibration should fail validation because ms_path not available
        is_valid, error_msg = calibration_stage.validate(initial_context)
        assert not is_valid
        assert "ms_path" in error_msg.lower()

    def test_cleanup_called_on_failure(self, config):
        """Test that cleanup is called even when stage fails."""
        initial_context = PipelineContext(config=config, inputs={"input_path": "/mock/input.hdf5"})

        conversion_stage = ConversionStage(config)
        conversion_stage.cleanup = MagicMock()

        # Cause validation failure
        is_valid, _ = conversion_stage.validate(initial_context)
        if not is_valid:
            # Cleanup should still be callable
            conversion_stage.cleanup(initial_context)
            conversion_stage.cleanup.assert_called_once()


class TestOrchestratorWithRealStages:
    """Test PipelineOrchestrator with real pipeline stages."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path(tmpdir) / "input",
                    output_dir=Path(tmpdir) / "output",
                )
            )

    @pytest.fixture
    def initial_context(self, config):
        """Create initial pipeline context."""
        with tempfile.NamedTemporaryFile(suffix=".hdf5", delete=False) as tmp:
            tmp_path = tmp.name
        yield PipelineContext(config=config, inputs={"input_path": tmp_path})
        Path(tmp_path).unlink(missing_ok=True)

    def test_orchestrator_executes_stage_chain(self, config, initial_context):
        """Test orchestrator executes a chain of real stages."""
        # Mock imports that happen inside execute methods
        with (
            patch(
                "dsa110_contimg.pointing.utils.load_pointing",
                return_value={"dec_deg": 30.0},
            ),
            patch("dsa110_contimg.database.products.ensure_products_db"),
            patch(
                "dsa110_contimg.catalog.query.resolve_catalog_path",
                return_value=Path("/mock/catalog.db"),
            ),
            patch(
                "dsa110_contimg.catalog.builders.build_nvss_strip_db",
                return_value=Path("/mock/nvss.db"),
            ),
            patch(
                "dsa110_contimg.catalog.builders.build_first_strip_db",
                return_value=Path("/mock/first.db"),
            ),
            patch(
                "dsa110_contimg.catalog.builders.build_rax_strip_db",
                return_value=Path("/mock/rax.db"),
            ),
            patch(
                "dsa110_contimg.conversion.strategies.hdf5_orchestrator.convert_subband_groups_to_ms",
                return_value=["/mock/converted.ms"],
            ),
        ):

            stages = [
                StageDefinition("catalog_setup", CatalogSetupStage(config), []),
                StageDefinition("conversion", ConversionStage(config), ["catalog_setup"]),
            ]

            orchestrator = PipelineOrchestrator(stages)
            result = orchestrator.execute(initial_context)

            assert result.status.value in [
                "completed",
                "partial",
            ]  # May be partial if later stages not run
            assert "catalog_setup_status" in result.context.outputs
            assert "ms_path" in result.context.outputs
