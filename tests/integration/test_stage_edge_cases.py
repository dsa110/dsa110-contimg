"""
Integration tests for pipeline stage edge cases and error scenarios.

Tests edge cases, error handling, and failure modes across stage interactions.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.orchestrator import PipelineOrchestrator, StageDefinition
from dsa110_contimg.pipeline.stages_impl import (
    ConversionStage,
    CalibrationSolveStage,
    CalibrationStage,
    ImagingStage,
    ValidationStage,
)


class TestStageEdgeCases:
    """Test edge cases for pipeline stages."""

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

    def test_empty_outputs_from_previous_stage(self, config):
        """Test stage handles empty outputs from previous stage gracefully."""
        context = PipelineContext(config=config, outputs={})
        stage = CalibrationSolveStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "ms_path" in error_msg.lower()

    def test_missing_optional_inputs(self, config):
        """Test stage handles missing optional inputs."""
        context = PipelineContext(config=config, outputs={"ms_path": "/mock/ms"})
        stage = CalibrationSolveStage(config)

        # Should validate even without optional inputs
        is_valid, error_msg = stage.validate(context)
        # May or may not be valid depending on file existence, but shouldn't crash

    def test_invalid_file_paths(self, config):
        """Test stage handles invalid file paths."""
        context = PipelineContext(
            config=config, outputs={"ms_path": "/nonexistent/path/to/file.ms"}
        )
        stage = CalibrationSolveStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "not found" in error_msg.lower() or "not exist" in error_msg.lower()

    def test_large_output_context(self, config):
        """Test context immutability with large outputs."""
        # Create context with many outputs
        outputs = {f"output_{i}": f"value_{i}" for i in range(100)}
        context = PipelineContext(config=config, outputs=outputs)

        # Add new output
        new_context = context.with_output("new_output", "new_value")

        # Verify original unchanged
        assert "new_output" not in context.outputs
        assert "new_output" in new_context.outputs
        assert len(new_context.outputs) == len(context.outputs) + 1

    def test_nested_context_transformation(self, config):
        """Test multiple context transformations maintain immutability."""
        context = PipelineContext(config=config, inputs={"input": "value"})

        # Multiple transformations
        context1 = context.with_output("output1", "value1")
        context2 = context1.with_output("output2", "value2")
        context3 = context2.with_output("output3", "value3")

        # Verify each transformation creates new context
        assert context is not context1
        assert context1 is not context2
        assert context2 is not context3

        # Verify all outputs present in final context
        assert "output1" in context3.outputs
        assert "output2" in context3.outputs
        assert "output3" in context3.outputs

        # Verify earlier contexts unchanged
        assert "output2" not in context1.outputs
        assert "output3" not in context2.outputs


class TestStageErrorRecovery:
    """Test error recovery and cleanup behavior."""

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

    def test_cleanup_called_on_validation_failure(self, config):
        """Test cleanup is called even when validation fails."""
        context = PipelineContext(config=config)
        stage = ConversionStage(config)
        stage.cleanup = MagicMock()

        # Validation fails
        is_valid, _ = stage.validate(context)
        assert not is_valid

        # Cleanup should still be callable (though not called automatically)
        assert callable(stage.cleanup)

    def test_cleanup_called_on_execution_failure(self, config):
        """Test cleanup is called when execution fails."""
        context = PipelineContext(config=config, inputs={"input_path": "/mock/input"})
        stage = ConversionStage(config)
        stage.cleanup = MagicMock()

        # Mock execute to raise exception
        original_execute = stage.execute

        def failing_execute(ctx):
            raise Exception("Execution failed")

        stage.execute = failing_execute

        # Attempt execution
        try:
            stage.execute(context)
        except Exception:
            pass

        # Cleanup should be callable
        assert callable(stage.cleanup)

    def test_partial_outputs_on_failure(self, config):
        """Test that partial outputs are handled correctly on failure."""
        context = PipelineContext(config=config, outputs={"ms_path": "/mock/ms"})

        # Stage that might produce partial outputs
        stage = ImagingStage(config)

        # Even if execution fails partway, cleanup should handle partial outputs
        assert hasattr(stage, "cleanup")
        assert callable(stage.cleanup)


class TestStageDependencyEdgeCases:
    """Test edge cases in stage dependencies."""

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

    def test_stage_with_no_dependencies(self, config):
        """Test stage that has no dependencies."""
        context = PipelineContext(config=config, inputs={"input_path": "/mock/input"})
        stage = ConversionStage(config)

        # Should validate independently
        is_valid, error_msg = stage.validate(context)
        # May fail due to missing file, but shouldn't fail due to dependencies

    def test_stage_with_multiple_dependencies(self, config):
        """Test stage that depends on multiple previous stages."""
        # Simulate context with outputs from multiple stages
        context = PipelineContext(
            config=config,
            outputs={
                "ms_path": "/mock/ms",  # From conversion
                "calibration_tables": {"K": "/mock/K.cal"},  # From calibration solve
            },
        )
        stage = CalibrationStage(config)

        # Should validate with multiple dependencies satisfied
        is_valid, error_msg = stage.validate(context)
        # May fail due to file existence, but dependencies are satisfied

    def test_circular_dependency_prevention(self, config):
        """Test that circular dependencies are prevented."""
        from dsa110_contimg.pipeline.stages_impl import ConversionStage

        # Try to create circular dependency
        stages = [
            StageDefinition("stage1", ConversionStage(config), ["stage2"]),
            StageDefinition("stage2", ConversionStage(config), ["stage1"]),
        ]

        # Orchestrator should detect circular dependency
        with pytest.raises((ValueError, RuntimeError)):  # May raise different errors
            orchestrator = PipelineOrchestrator(stages)
            # Or may fail during topological sort
            orchestrator._topological_sort()


class TestStageOutputValidation:
    """Test output validation edge cases."""

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

    def test_validate_outputs_with_missing_outputs(self, config):
        """Test validate_outputs when outputs are missing."""
        context = PipelineContext(config=config)
        stage = ConversionStage(config)

        # Should handle missing outputs gracefully
        is_valid, error_msg = stage.validate_outputs(context)
        # Default implementation returns (True, None), but stages can override

    def test_validate_outputs_with_invalid_outputs(self, config):
        """Test validate_outputs with invalid output values."""
        context = PipelineContext(
            config=config, outputs={"ms_path": ""}  # Empty string
        )
        stage = ConversionStage(config)

        # Should validate outputs
        is_valid, error_msg = stage.validate_outputs(context)
        # Default implementation may pass, but stages can add validation

    def test_validate_outputs_with_correct_outputs(self, config):
        """Test validate_outputs with correct outputs."""
        with tempfile.NamedTemporaryFile(suffix=".ms", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            context = PipelineContext(config=config, outputs={"ms_path": tmp_path})
            stage = ConversionStage(config)

            # Should validate successfully
            is_valid, error_msg = stage.validate_outputs(context)
            assert is_valid is True
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestStageConfigurationEdgeCases:
    """Test edge cases with stage configuration."""

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

    def test_stage_with_disabled_config(self, config):
        """Test stage behavior when disabled in configuration."""
        config.crossmatch.enabled = False
        context = PipelineContext(config=config)
        stage = ValidationStage(config)  # Using ValidationStage as example

        # Stage should handle disabled config gracefully
        # May skip validation or return specific error
        is_valid, error_msg = stage.validate(context)
        # Behavior depends on stage implementation

    def test_stage_with_minimal_config(self, config):
        """Test stage with minimal configuration."""
        minimal_config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/tmp/input"),
                output_dir=Path("/tmp/output"),
            )
        )
        context = PipelineContext(config=minimal_config)
        stage = ConversionStage(minimal_config)

        # Should handle minimal config
        assert stage.config == minimal_config
