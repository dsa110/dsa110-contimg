"""
Pipeline orchestrator with dependency resolution.

Executes pipeline stages in the correct order based on dependencies,
with support for retry policies, error handling, and observability.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.resilience import RetryPolicy
from dsa110_contimg.pipeline.stages import PipelineStage, StageStatus


class PipelineStatus(Enum):
    """Overall pipeline execution status."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some stages failed but pipeline continued


@dataclass
class StageResult:
    """Result of executing a single stage."""
    
    status: StageStatus
    context: PipelineContext
    error: Optional[Exception] = None
    duration_seconds: Optional[float] = None
    attempt: int = 1


@dataclass
class StageDefinition:
    """Definition of a pipeline stage with metadata."""
    
    name: str
    stage: PipelineStage
    dependencies: List[str]  # Names of prerequisite stages
    retry_policy: Optional[RetryPolicy] = None
    timeout: Optional[float] = None
    resource_requirements: Optional[Dict[str, Any]] = None


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    
    status: PipelineStatus
    context: PipelineContext
    stage_results: Dict[str, StageResult]
    total_duration_seconds: Optional[float] = None


class PipelineOrchestrator:
    """Orchestrates multi-stage pipeline with dependency resolution.
    
    Example:
        stages = [
            StageDefinition("convert", ConversionStage(), []),
            StageDefinition("calibrate", CalibrationStage(), ["convert"]),
            StageDefinition("image", ImagingStage(), ["calibrate"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(initial_context)
    """
    
    def __init__(self, stages: List[StageDefinition]):
        """Initialize orchestrator.
        
        Args:
            stages: List of stage definitions
        """
        self.stages = {s.name: s for s in stages}
        self.graph = self._build_dependency_graph()
    
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph from stage definitions.
        
        Returns:
            Dictionary mapping stage names to their dependencies
        """
        return {name: stage_def.dependencies for name, stage_def in self.stages.items()}
    
    def _topological_sort(self) -> List[str]:
        """Topologically sort stages by dependencies.
        
        Returns:
            List of stage names in execution order
        """
        # Kahn's algorithm for topological sort
        in_degree = {name: len(deps) for name, deps in self.graph.items()}
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # Reduce in-degree of dependent nodes
            for name, deps in self.graph.items():
                if node in deps:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)
        
        # Check for cycles
        if len(result) != len(self.stages):
            raise ValueError("Circular dependency detected in pipeline stages")
        
        return result
    
    def _prerequisites_met(self, stage_name: str, results: Dict[str, StageResult]) -> bool:
        """Check if prerequisites for a stage are met.
        
        Args:
            stage_name: Name of stage to check
            results: Results from previous stages
            
        Returns:
            True if all prerequisites are met
        """
        stage_def = self.stages[stage_name]
        
        for dep_name in stage_def.dependencies:
            if dep_name not in results:
                return False
            
            dep_result = results[dep_name]
            if dep_result.status != StageStatus.COMPLETED:
                return False
        
        return True
    
    def _execute_with_retry(
        self,
        stage_def: StageDefinition,
        context: PipelineContext,
        attempt: int = 1
    ) -> StageResult:
        """Execute stage with retry policy.
        
        Args:
            stage_def: Stage definition
            context: Pipeline context
            attempt: Current attempt number
            
        Returns:
            StageResult
        """
        import time
        
        start_time = time.time()
        
        try:
            # Validate prerequisites
            is_valid, error_msg = stage_def.stage.validate(context)
            if not is_valid:
                return StageResult(
                    status=StageStatus.FAILED,
                    context=context,
                    error=ValueError(error_msg),
                    duration_seconds=time.time() - start_time,
                    attempt=attempt,
                )
            
            # Execute stage
            result_context = stage_def.stage.execute(context)
            
            # Cleanup
            try:
                stage_def.stage.cleanup(result_context)
            except Exception as cleanup_error:
                # Log but don't fail on cleanup errors
                pass
            
            return StageResult(
                status=StageStatus.COMPLETED,
                context=result_context,
                duration_seconds=time.time() - start_time,
                attempt=attempt,
            )
        
        except Exception as e:
            duration = time.time() - start_time
            
            # Check if we should retry
            if stage_def.retry_policy and stage_def.retry_policy.should_retry(attempt, e):
                # Wait before retry
                delay = stage_def.retry_policy.get_delay(attempt)
                if delay > 0:
                    time.sleep(delay)
                
                # Retry
                return self._execute_with_retry(stage_def, context, attempt + 1)
            
            # No retry or max attempts reached
            return StageResult(
                status=StageStatus.FAILED,
                context=context,
                error=e,
                duration_seconds=duration,
                attempt=attempt,
            )
    
    def execute(self, initial_context: PipelineContext) -> PipelineResult:
        """Execute pipeline respecting dependencies.
        
        Args:
            initial_context: Initial pipeline context
            
        Returns:
            PipelineResult with execution results
        """
        import time
        
        start_time = time.time()
        execution_order = self._topological_sort()
        context = initial_context
        results: Dict[str, StageResult] = {}
        pipeline_status = PipelineStatus.RUNNING
        
        for stage_name in execution_order:
            stage_def = self.stages[stage_name]
            
            # Check if prerequisites met
            if not self._prerequisites_met(stage_name, results):
                results[stage_name] = StageResult(
                    status=StageStatus.SKIPPED,
                    context=context,
                )
                continue
            
            # Execute with retry policy
            result = self._execute_with_retry(stage_def, context)
            results[stage_name] = result
            
            # Update context with stage outputs
            if result.status == StageStatus.COMPLETED:
                context = result.context
            elif result.status == StageStatus.FAILED:
                # Handle failure based on retry policy
                if stage_def.retry_policy and stage_def.retry_policy.should_continue():
                    pipeline_status = PipelineStatus.PARTIAL
                    continue
                else:
                    pipeline_status = PipelineStatus.FAILED
                    break
        
        # Determine final status
        if pipeline_status == PipelineStatus.RUNNING:
            # Check if all stages completed
            all_completed = all(
                r.status == StageStatus.COMPLETED
                for r in results.values()
            )
            pipeline_status = PipelineStatus.COMPLETED if all_completed else PipelineStatus.PARTIAL
        
        return PipelineResult(
            status=pipeline_status,
            context=context,
            stage_results=results,
            total_duration_seconds=time.time() - start_time,
        )

