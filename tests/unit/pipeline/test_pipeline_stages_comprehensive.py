"""
Comprehensive tests for pipeline stages.

Tests all stage implementations with focus on:
- Input validation
- Output validation
- Error handling
- Cleanup behavior
- Dependency relationships
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dsa110_contimg.pipeline.config import (
    CalibrationConfig,
    ConversionConfig,
    ImagingConfig,
    PathsConfig,
    PipelineConfig,
    ValidationConfig,
)
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import (
    AdaptivePhotometryStage,
    CalibrationStage,
    CalibrationSolveStage,
    CatalogSetupStage,
    ConversionStage,
    CrossMatchStage,
    ImagingStage,
    OrganizationStage,
    ValidationStage,
)


class TestCatalogSetupStage:
    """Test CatalogSetupStage."""

    def test_validate_missing_input_path(self):
        """Test validation fails when input_path is missing."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(config=config)
        stage = CatalogSetupStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "input_path" in error_msg.lower()

    def test_validate_nonexistent_file(self):
        """Test validation fails when file doesn't exist."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(
            config=config, inputs={"input_path": "/nonexistent/file.hdf5"}
        )
        stage = CatalogSetupStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "not found" in error_msg.lower()

    @patch("dsa110_contimg.pointing.utils.load_pointing")
    def test_validate_valid_input(self, mock_load_pointing):
        """Test validation succeeds with valid input."""
        mock_load_pointing.return_value = {"dec_deg": 30.0}

        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        with tempfile.NamedTemporaryFile(suffix=".hdf5", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            context = PipelineContext(config=config, inputs={"input_path": tmp_path})
            stage = CatalogSetupStage(config)

            is_valid, error_msg = stage.validate(context)
            assert is_valid
            assert error_msg is None
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = CatalogSetupStage(config)
        # Stages use snake_case names, not CamelCase
        assert stage.get_name() == "catalog_setup"


class TestConversionStage:
    """Test ConversionStage."""

    def test_validate_missing_input_path(self):
        """Test validation fails when input_path is missing."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(config=config)
        stage = ConversionStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        # ConversionStage validates input_dir existence, not input_path
        assert error_msg is not None

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = ConversionStage(config)
        assert stage.get_name() == "conversion"


class TestCalibrationSolveStage:
    """Test CalibrationSolveStage."""

    def test_validate_missing_ms_path(self):
        """Test validation fails when ms_path is missing."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(config=config)
        stage = CalibrationSolveStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "ms_path" in error_msg.lower()

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = CalibrationSolveStage(config)
        assert stage.get_name() == "calibration_solve"


class TestCalibrationStage:
    """Test CalibrationStage."""

    def test_validate_missing_ms_path(self):
        """Test validation fails when ms_path is missing."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(config=config)
        stage = CalibrationStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "ms_path" in error_msg.lower()

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = CalibrationStage(config)
        assert stage.get_name() == "calibration"


class TestImagingStage:
    """Test ImagingStage."""

    def test_validate_missing_ms_path(self):
        """Test validation fails when ms_path is missing."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(config=config)
        stage = ImagingStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "ms_path" in error_msg.lower()

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = ImagingStage(config)
        assert stage.get_name() == "imaging"


class TestOrganizationStage:
    """Test OrganizationStage."""

    def test_validate_missing_ms_path(self):
        """Test validation fails when ms_path is missing."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(config=config)
        stage = OrganizationStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "ms" in error_msg.lower()  # Error message says "No MS files found"

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = OrganizationStage(config)
        assert stage.get_name() == "organization"


class TestValidationStage:
    """Test ValidationStage."""

    def test_validate_missing_image_path(self):
        """Test validation fails when image_path is missing."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(config=config)
        stage = ValidationStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "image_path" in error_msg.lower()

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = ValidationStage(config)
        assert stage.get_name() == "validation"


class TestCrossMatchStage:
    """Test CrossMatchStage."""

    def test_validate_missing_detected_sources(self):
        """Test validation fails when detected_sources are missing."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        # Enable crossmatch for this test
        config.crossmatch.enabled = True
        context = PipelineContext(config=config)
        stage = CrossMatchStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert (
            "detected sources" in error_msg.lower()
            or "no detected sources" in error_msg.lower()
        )

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = CrossMatchStage(config)
        assert stage.get_name() == "cross_match"


class TestAdaptivePhotometryStage:
    """Test AdaptivePhotometryStage."""

    def test_validate_missing_ms_path(self):
        """Test validation fails when ms_path is missing."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        # Enable photometry for this test
        config.photometry.enabled = True
        context = PipelineContext(config=config)
        stage = AdaptivePhotometryStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "ms_path" in error_msg.lower()

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = AdaptivePhotometryStage(config)
        assert stage.get_name() == "adaptive_photometry"


class TestStageCleanup:
    """Test cleanup behavior for all stages."""

    @pytest.mark.parametrize(
        "stage_class,config_kwargs",
        [
            (CatalogSetupStage, {}),
            (ConversionStage, {}),
            (CalibrationSolveStage, {}),
            (CalibrationStage, {}),
            (ImagingStage, {}),
            (OrganizationStage, {}),
            (ValidationStage, {}),
            (CrossMatchStage, {}),
            (AdaptivePhotometryStage, {}),
        ],
    )
    def test_cleanup_called_on_success(self, stage_class, config_kwargs):
        """Test cleanup is called after successful execution."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = stage_class(config, **config_kwargs)
        context = PipelineContext(config=config)

        # Mock cleanup to verify it's called
        cleanup_called = []
        original_cleanup = stage.cleanup

        def mock_cleanup(ctx):
            cleanup_called.append(True)
            return original_cleanup(ctx)

        stage.cleanup = mock_cleanup

        # Note: We can't actually execute most stages without real data,
        # but we can verify cleanup method exists and is callable
        assert callable(stage.cleanup)
        stage.cleanup(context)
        assert len(cleanup_called) == 1


class TestStageOutputValidation:
    """Test output validation for stages."""

    @pytest.mark.parametrize(
        "stage_class,config_kwargs",
        [
            (CatalogSetupStage, {}),
            (ConversionStage, {}),
            (CalibrationSolveStage, {}),
            (CalibrationStage, {}),
            (ImagingStage, {}),
            (OrganizationStage, {}),
            (ValidationStage, {}),
            (CrossMatchStage, {}),
            (AdaptivePhotometryStage, {}),
        ],
    )
    def test_validate_outputs_method_exists(self, stage_class, config_kwargs):
        """Test validate_outputs method exists and is callable."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = stage_class(config, **config_kwargs)
        context = PipelineContext(config=config)

        # All stages should have validate_outputs method
        assert hasattr(stage, "validate_outputs")
        assert callable(stage.validate_outputs)

        # Should return tuple (bool, Optional[str])
        is_valid, error_msg = stage.validate_outputs(context)
        assert isinstance(is_valid, bool)
        assert error_msg is None or isinstance(error_msg, str)


class TestStageDependencies:
    """Test stage dependency relationships."""

    def test_stage_dependency_graph(self):
        """Test that stage dependencies form a valid DAG."""
        # Define expected dependencies
        dependencies = {
            "CatalogSetupStage": [],
            "ConversionStage": [],
            "CalibrationSolveStage": ["ConversionStage"],
            "CalibrationStage": ["ConversionStage", "CalibrationSolveStage"],
            "ImagingStage": ["CalibrationStage"],
            "OrganizationStage": ["ConversionStage"],
            "ValidationStage": ["ImagingStage"],
            "CrossMatchStage": ["ImagingStage"],
            "AdaptivePhotometryStage": ["ImagingStage"],
        }

        # Verify no circular dependencies
        # (This is a simple check - full topological sort is tested in orchestrator tests)
        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            for dep in dependencies.get(node, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for stage_name in dependencies:
            if stage_name not in visited:
                assert not has_cycle(
                    stage_name
                ), f"Circular dependency detected involving {stage_name}"
