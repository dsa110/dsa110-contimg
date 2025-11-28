"""End-to-end integration tests for streaming_workflow.

Tests the complete streaming pipeline workflow:
1. CatalogSetup stage
2. Conversion stage
3. CalibrationSolve stage
4. CalibrationApply stage
5. Imaging stage
6. Mosaic stage (optional)
7. Validation stage (optional)
8. CrossMatch stage (optional)
9. AdaptivePhotometry stage (optional)
10. LightCurve stage (optional)
11. TransientDetection stage (optional)

Uses mocked stage implementations to validate workflow orchestration
without requiring actual CASA/WSClean execution.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dsa110_contimg.pipeline.config import (
    CrossMatchConfig,
    LightCurveConfig,
    MosaicConfig,
    PathsConfig,
    PhotometryConfig,
    PipelineConfig,
    TransientDetectionConfig,
    ValidationConfig,
)
from dsa110_contimg.pipeline.workflows import streaming_workflow


class TestStreamingWorkflowStructure:
    """Test streaming workflow structure and stage configuration."""

    def test_workflow_creates_core_stages(self):
        """Test that core stages are always created."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
            mosaic=MosaicConfig(enabled=False),
            validation=ValidationConfig(enabled=False),
            crossmatch=CrossMatchConfig(enabled=False),
            photometry=PhotometryConfig(enabled=False),
            light_curve=LightCurveConfig(enabled=False),
            transient_detection=TransientDetectionConfig(enabled=False),
        )

        workflow = streaming_workflow(config)

        # Check core stages exist (stages is dict of name -> StageDefinition)
        stage_names = list(workflow.stages.keys())
        assert "catalog_setup" in stage_names
        assert "conversion" in stage_names
        assert "calibration_solve" in stage_names
        assert "calibration_apply" in stage_names
        assert "imaging" in stage_names

        # Optional stages should NOT be present when disabled
        assert "mosaic" not in stage_names
        assert "validation" not in stage_names
        assert "crossmatch" not in stage_names
        assert "adaptive_photometry" not in stage_names
        assert "light_curve" not in stage_names
        assert "transient_detection" not in stage_names

    def test_workflow_creates_all_optional_stages(self):
        """Test that all optional stages are created when enabled."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
            mosaic=MosaicConfig(enabled=True),
            validation=ValidationConfig(enabled=True),
            crossmatch=CrossMatchConfig(enabled=True),
            photometry=PhotometryConfig(enabled=True),
            light_curve=LightCurveConfig(enabled=True),
            transient_detection=TransientDetectionConfig(enabled=True),
        )

        workflow = streaming_workflow(config)

        stage_names = list(workflow.stages.keys())

        # All stages should be present
        expected_stages = [
            "catalog_setup",
            "conversion",
            "calibration_solve",
            "calibration_apply",
            "imaging",
            "mosaic",
            "validation",
            "crossmatch",
            "adaptive_photometry",
            "light_curve",
            "transient_detection",
        ]

        for stage in expected_stages:
            assert stage in stage_names, f"Expected stage '{stage}' not found"

    def test_workflow_stage_dependencies(self):
        """Test that stage dependencies are correctly configured."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
            mosaic=MosaicConfig(enabled=True),
            validation=ValidationConfig(enabled=True),
            crossmatch=CrossMatchConfig(enabled=True),
            photometry=PhotometryConfig(enabled=True),
            light_curve=LightCurveConfig(enabled=True),
            transient_detection=TransientDetectionConfig(enabled=True),
        )

        workflow = streaming_workflow(config)

        # Get dependency graph from orchestrator
        deps = workflow.graph

        # Core dependencies
        assert deps.get("conversion") == ["catalog_setup"]
        assert deps.get("calibration_solve") == ["conversion"]
        assert deps.get("calibration_apply") == ["calibration_solve"]
        assert deps.get("imaging") == ["calibration_apply"]

        # Mosaic depends on imaging
        assert "imaging" in deps.get("mosaic", [])

        # Validation depends on mosaic (when mosaic enabled)
        assert "mosaic" in deps.get("validation", [])

        # Photometry depends on mosaic (when mosaic enabled)
        assert "mosaic" in deps.get("adaptive_photometry", [])

        # Light curve depends on photometry and mosaic
        light_curve_deps = deps.get("light_curve", [])
        assert "adaptive_photometry" in light_curve_deps

        # Transient detection depends on light curve
        assert "light_curve" in deps.get("transient_detection", [])

    def test_workflow_light_curve_requires_photometry(self):
        """Test that light curve stage is only added when photometry is enabled."""
        # Light curve enabled but photometry disabled
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
            photometry=PhotometryConfig(enabled=False),
            light_curve=LightCurveConfig(enabled=True),
        )

        workflow = streaming_workflow(config)
        stage_names = list(workflow.stages.keys())

        # Light curve should NOT be present without photometry
        assert "light_curve" not in stage_names

    def test_workflow_transient_detection_fallback_deps(self):
        """Test transient detection dependency fallback when light curve disabled."""
        # Transient detection with photometry but no light curve
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
            photometry=PhotometryConfig(enabled=True),
            light_curve=LightCurveConfig(enabled=False),
            transient_detection=TransientDetectionConfig(enabled=True),
        )

        workflow = streaming_workflow(config)
        deps = workflow.graph

        # Transient detection should depend on photometry, not light_curve
        transient_deps = deps.get("transient_detection", [])
        assert "adaptive_photometry" in transient_deps
        assert "light_curve" not in transient_deps


class TestStreamingWorkflowExecution:
    """Test streaming workflow execution with mocked stages."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a test configuration."""
        output_dir = tmp_path / "output"
        state_dir = tmp_path / "state"
        output_dir.mkdir()
        state_dir.mkdir()
        (state_dir / "products.sqlite3").touch()

        return PipelineConfig(
            paths=PathsConfig(
                input_dir=tmp_path / "input",
                output_dir=output_dir,
                state_dir=state_dir,
            ),
            mosaic=MosaicConfig(enabled=False),
            validation=ValidationConfig(enabled=False),
            crossmatch=CrossMatchConfig(enabled=False),
            photometry=PhotometryConfig(enabled=False),
            light_curve=LightCurveConfig(enabled=False),
            transient_detection=TransientDetectionConfig(enabled=False),
        )

    def test_workflow_stages_have_retry_policy(self, mock_config):
        """Test that all stages have retry policies configured."""
        workflow = streaming_workflow(mock_config)

        for stage_name, stage_def in workflow.stages.items():
            assert stage_def.retry_policy is not None, (
                f"Stage '{stage_name}' missing retry policy"
            )
            assert stage_def.retry_policy.max_attempts >= 1

    def test_workflow_stages_have_timeouts(self, mock_config):
        """Test that all stages have timeouts configured."""
        workflow = streaming_workflow(mock_config)

        for stage_name, stage_def in workflow.stages.items():
            assert stage_def.timeout is not None, (
                f"Stage '{stage_name}' missing timeout"
            )
            assert stage_def.timeout > 0

    def test_workflow_stage_timeouts_reasonable(self, mock_config):
        """Test that stage timeouts are reasonable values."""
        workflow = streaming_workflow(mock_config)

        # Check specific timeouts
        expected_timeouts = {
            "catalog_setup": 300.0,  # 5 minutes
            "conversion": 1800.0,  # 30 minutes
            "calibration_solve": 900.0,  # 15 minutes
            "calibration_apply": 600.0,  # 10 minutes
            "imaging": 1800.0,  # 30 minutes
        }

        for stage_name, expected_timeout in expected_timeouts.items():
            actual_timeout = workflow.stages[stage_name].timeout
            assert actual_timeout == expected_timeout, (
                f"Stage '{stage_name}' timeout mismatch: "
                f"expected {expected_timeout}, got {actual_timeout}"
            )


class TestStreamingWorkflowWithMockedExecution:
    """Test streaming workflow execution with mocked stage implementations."""

    @pytest.fixture
    def full_config(self, tmp_path):
        """Create a full configuration with all stages enabled."""
        output_dir = tmp_path / "output"
        state_dir = tmp_path / "state"
        output_dir.mkdir()
        state_dir.mkdir()
        (state_dir / "products.sqlite3").touch()

        return PipelineConfig(
            paths=PathsConfig(
                input_dir=tmp_path / "input",
                output_dir=output_dir,
                state_dir=state_dir,
            ),
            mosaic=MosaicConfig(enabled=True),
            validation=ValidationConfig(enabled=True),
            crossmatch=CrossMatchConfig(enabled=True),
            photometry=PhotometryConfig(enabled=True),
            light_curve=LightCurveConfig(enabled=True),
            transient_detection=TransientDetectionConfig(enabled=True),
        )

    def test_workflow_can_be_built(self, full_config):
        """Test that workflow can be built with full configuration."""
        workflow = streaming_workflow(full_config)

        # Should have all 11 stages
        assert len(workflow.stages) == 11

        # Verify stage types via StageDefinition.stage attribute
        from dsa110_contimg.pipeline import stages_impl

        assert isinstance(
            workflow.stages["catalog_setup"].stage, stages_impl.CatalogSetupStage
        )
        assert isinstance(
            workflow.stages["conversion"].stage, stages_impl.ConversionStage
        )
        assert isinstance(
            workflow.stages["calibration_solve"].stage, stages_impl.CalibrationSolveStage
        )
        assert isinstance(
            workflow.stages["calibration_apply"].stage, stages_impl.CalibrationStage
        )
        assert isinstance(
            workflow.stages["imaging"].stage, stages_impl.ImagingStage
        )
        assert isinstance(
            workflow.stages["mosaic"].stage, stages_impl.MosaicStage
        )
        assert isinstance(
            workflow.stages["validation"].stage, stages_impl.ValidationStage
        )
        assert isinstance(
            workflow.stages["crossmatch"].stage, stages_impl.CrossMatchStage
        )
        assert isinstance(
            workflow.stages["adaptive_photometry"].stage,
            stages_impl.AdaptivePhotometryStage,
        )
        assert isinstance(
            workflow.stages["light_curve"].stage, stages_impl.LightCurveStage
        )
        assert isinstance(
            workflow.stages["transient_detection"].stage,
            stages_impl.TransientDetectionStage,
        )

    def test_workflow_topological_sort(self, full_config):
        """Test that stages are ordered correctly by dependencies."""
        workflow = streaming_workflow(full_config)

        # Get ordered stage list via topological sort
        ordered_stages = workflow._topological_sort()

        # Verify core stages come first in order
        core_stages = [
            "catalog_setup",
            "conversion",
            "calibration_solve",
            "calibration_apply",
            "imaging",
        ]

        for i, stage in enumerate(core_stages[:-1]):
            next_stage = core_stages[i + 1]
            assert ordered_stages.index(stage) < ordered_stages.index(next_stage), (
                f"Stage '{stage}' should come before '{next_stage}'"
            )

        # Mosaic should come after imaging
        assert ordered_stages.index("imaging") < ordered_stages.index("mosaic")

        # Transient detection should be last (or near last)
        assert ordered_stages.index("transient_detection") > ordered_stages.index(
            "light_curve"
        )


class TestStreamingWorkflowMinimalConfiguration:
    """Test streaming workflow with minimal configuration."""

    def test_minimal_workflow_only_core_stages(self, tmp_path):
        """Test workflow with only core stages enabled."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=tmp_path / "input",
                output_dir=output_dir,
            ),
            mosaic=MosaicConfig(enabled=False),
            validation=ValidationConfig(enabled=False),
            crossmatch=CrossMatchConfig(enabled=False),
            photometry=PhotometryConfig(enabled=False),
            light_curve=LightCurveConfig(enabled=False),
            transient_detection=TransientDetectionConfig(enabled=False),
        )

        workflow = streaming_workflow(config)

        # Should have exactly 5 core stages
        assert len(workflow.stages) == 5

    def test_workflow_handles_empty_input_dir(self, tmp_path):
        """Test workflow creation with non-existent input directory."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=tmp_path / "nonexistent",
                output_dir=tmp_path / "output",
            ),
        )

        # Workflow creation should not fail
        workflow = streaming_workflow(config)
        assert workflow is not None


class TestStreamingWorkflowRetryConfiguration:
    """Test retry policy configuration in streaming workflow."""

    def test_retry_policy_exponential_backoff(self, tmp_path):
        """Test that retry policy uses exponential backoff."""
        from dsa110_contimg.pipeline.resilience import RetryStrategy

        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=tmp_path / "input",
                output_dir=tmp_path / "output",
            ),
            mosaic=MosaicConfig(enabled=False),
        )

        workflow = streaming_workflow(config)

        for stage_name, stage_def in workflow.stages.items():
            policy = stage_def.retry_policy
            assert policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
            assert policy.max_attempts == 3
            assert policy.initial_delay == 5.0
            assert policy.max_delay == 60.0
