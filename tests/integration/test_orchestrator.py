"""
Integration tests for PipelineOrchestrator.

Tests orchestrator behavior with multiple stages, dependencies, and error handling.
"""

import pytest

from dsa110_contimg.pipeline import (
    PipelineOrchestrator,
    StageDefinition,
    PipelineContext,
    PipelineStatus,
    StageStatus,
)
from tests.fixtures.mock_stages import MockStage, FailingValidationStage


class TestOrchestratorExecution:
    """Test orchestrator execution flow."""
    
    def test_linear_execution(self, test_context):
        """Test simple linear stage execution."""
        stages = [
            StageDefinition("stage1", MockStage("stage1"), []),
            StageDefinition("stage2", MockStage("stage2"), ["stage1"]),
            StageDefinition("stage3", MockStage("stage3"), ["stage2"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(test_context)
        
        assert result.status == PipelineStatus.COMPLETED
        assert "stage1_output" in result.context.outputs
        assert "stage2_output" in result.context.outputs
        assert "stage3_output" in result.context.outputs
        assert result.stage_results["stage1"].status == StageStatus.COMPLETED
        assert result.stage_results["stage2"].status == StageStatus.COMPLETED
        assert result.stage_results["stage3"].status == StageStatus.COMPLETED
    
    def test_parallel_stages(self, test_context):
        """Test parallel stage execution (stages with same dependencies)."""
        stages = [
            StageDefinition("stage1", MockStage("stage1"), []),
            StageDefinition("stage2a", MockStage("stage2a"), ["stage1"]),
            StageDefinition("stage2b", MockStage("stage2b"), ["stage1"]),
            StageDefinition("stage3", MockStage("stage3"), ["stage2a", "stage2b"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(test_context)
        
        assert result.status == PipelineStatus.COMPLETED
        # Both stage2a and stage2b should complete before stage3
        assert "stage2a_output" in result.context.outputs
        assert "stage2b_output" in result.context.outputs
        assert "stage3_output" in result.context.outputs
    
    def test_dependency_ordering(self, test_context):
        """Test that stages execute in correct order despite definition order."""
        # Define stages out of order
        stages = [
            StageDefinition("stage3", MockStage("stage3"), ["stage2"]),
            StageDefinition("stage1", MockStage("stage1"), []),
            StageDefinition("stage2", MockStage("stage2"), ["stage1"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(test_context)
        
        assert result.status == PipelineStatus.COMPLETED
        # Verify execution order (should be 1, 2, 3)
        execution_order = list(result.stage_results.keys())
        assert execution_order == ["stage1", "stage2", "stage3"]


class TestOrchestratorErrorHandling:
    """Test orchestrator error handling."""
    
    def test_stage_failure_stops_pipeline(self, test_context):
        """Test that stage failure stops pipeline execution."""
        stages = [
            StageDefinition("stage1", MockStage("stage1"), []),
            StageDefinition("stage2", MockStage("stage2", should_fail=True), ["stage1"]),
            StageDefinition("stage3", MockStage("stage3"), ["stage2"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(test_context)
        
        assert result.status == PipelineStatus.FAILED
        assert result.stage_results["stage1"].status == StageStatus.COMPLETED
        assert result.stage_results["stage2"].status == StageStatus.FAILED
        assert "stage3" not in result.stage_results  # Should not execute
    
    def test_validation_failure(self, test_context):
        """Test that validation failure prevents execution."""
        stages = [
            StageDefinition(
                "stage1",
                FailingValidationStage("stage1", "Invalid input"),
                []
            ),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(test_context)
        
        assert result.status == PipelineStatus.FAILED
        assert result.stage_results["stage1"].status == StageStatus.FAILED
        assert result.stage_results["stage1"].error is not None
    
    def test_prerequisite_failure_skips_stage(self, test_context):
        """Test that failed prerequisites cause stage to be skipped."""
        from dsa110_contimg.pipeline import RetryPolicy, RetryStrategy
        
        # Use retry policy that allows continuation to test skip behavior
        stages = [
            StageDefinition(
                "stage1",
                MockStage("stage1", should_fail=True),
                [],
                retry_policy=RetryPolicy(continue_on_failure=True, max_attempts=1)
            ),
            StageDefinition("stage2", MockStage("stage2"), ["stage1"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(test_context)
        
        assert result.status == PipelineStatus.PARTIAL
        assert result.stage_results["stage1"].status == StageStatus.FAILED
        assert result.stage_results["stage2"].status == StageStatus.SKIPPED


class TestOrchestratorRetry:
    """Test orchestrator retry behavior."""
    
    def test_retry_on_failure(self, test_context):
        """Test that retry policy retries failed stages."""
        from dsa110_contimg.pipeline import RetryPolicy, RetryStrategy
        
        # Stage fails twice then succeeds
        stage = MockStage("retry_stage", should_fail=False, fail_count=2)
        retry_policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.IMMEDIATE,
        )
        
        stages = [
            StageDefinition("retry_stage", stage, [], retry_policy=retry_policy),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(test_context)
        
        assert result.status == PipelineStatus.COMPLETED
        assert result.stage_results["retry_stage"].attempt == 3
        assert "retry_stage_output" in result.context.outputs
    
    def test_max_retries_exceeded(self, test_context):
        """Test that exceeding max retries causes failure."""
        from dsa110_contimg.pipeline import RetryPolicy, RetryStrategy
        
        # Stage always fails
        stage = MockStage("failing_stage", should_fail=True)
        retry_policy = RetryPolicy(
            max_attempts=2,
            strategy=RetryStrategy.IMMEDIATE,
        )
        
        stages = [
            StageDefinition("failing_stage", stage, [], retry_policy=retry_policy),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(test_context)
        
        assert result.status == PipelineStatus.FAILED
        assert result.stage_results["failing_stage"].attempt == 2


class TestOrchestratorContext:
    """Test context passing through stages."""
    
    def test_context_immutability(self, test_context):
        """Test that context is immutable (new contexts created)."""
        stages = [
            StageDefinition("stage1", MockStage("stage1"), []),
            StageDefinition("stage2", MockStage("stage2"), ["stage1"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(test_context)
        
        # Original context should be unchanged
        assert test_context.outputs == {}
        # New context should have outputs
        assert len(result.context.outputs) > 0
    
    def test_output_propagation(self, test_context):
        """Test that outputs from one stage are available to next."""
        stages = [
            StageDefinition("stage1", MockStage("stage1"), []),
            StageDefinition("stage2", MockStage("stage2"), ["stage1"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(test_context)
        
        # Both outputs should be present
        assert "stage1_output" in result.context.outputs
        assert "stage2_output" in result.context.outputs


class TestOrchestratorCircularDependency:
    """Test circular dependency detection."""
    
    def test_circular_dependency_detection(self, test_context):
        """Test that circular dependencies are detected."""
        stages = [
            StageDefinition("stage1", MockStage("stage1"), ["stage2"]),
            StageDefinition("stage2", MockStage("stage2"), ["stage1"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        
        with pytest.raises(ValueError, match="Circular dependency"):
            orchestrator.execute(test_context)
    
    def test_self_dependency(self, test_context):
        """Test that self-dependencies are detected."""
        stages = [
            StageDefinition("stage1", MockStage("stage1"), ["stage1"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        
        with pytest.raises(ValueError, match="Circular dependency"):
            orchestrator.execute(test_context)

