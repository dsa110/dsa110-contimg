"""
Pipeline context for passing data between stages.

The PipelineContext is an immutable data structure that carries configuration,
inputs, outputs, and metadata through the pipeline execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from dsa110_contimg.pipeline.config import PipelineConfig


@dataclass(frozen=True)
class PipelineContext:
    """Immutable context passed between pipeline stages.

    The context is immutable to prevent accidental mutations. Use `with_output()`
    to create new contexts with additional outputs.

    Attributes:
        config: Pipeline configuration
        job_id: Optional job ID for tracking
        inputs: Stage inputs (e.g., time ranges, file paths)
        outputs: Stage outputs (e.g., created MS paths, image paths)
        metadata: Additional metadata (e.g., execution timestamps, metrics)
        state_repository: Optional state repository for persistence
    """

    config: PipelineConfig
    job_id: Optional[int] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    state_repository: Optional[Any] = None  # StateRepository, but avoid circular import

    def with_output(self, key: str, value: Any) -> PipelineContext:
        """Return new context with added output.

        Args:
            key: Output key
            value: Output value

        Returns:
            New PipelineContext with the output added
        """
        new_outputs = {**self.outputs, key: value}
        return PipelineContext(
            config=self.config,
            job_id=self.job_id,
            inputs=self.inputs,
            outputs=new_outputs,
            metadata=self.metadata,
            state_repository=self.state_repository,
        )

    def with_outputs(self, outputs: Dict[str, Any]) -> PipelineContext:
        """Return new context with multiple outputs added.

        Args:
            outputs: Dictionary of outputs to add

        Returns:
            New PipelineContext with the outputs merged
        """
        new_outputs = {**self.outputs, **outputs}
        return PipelineContext(
            config=self.config,
            job_id=self.job_id,
            inputs=self.inputs,
            outputs=new_outputs,
            metadata=self.metadata,
            state_repository=self.state_repository,
        )

    def with_metadata(self, key: str, value: Any) -> PipelineContext:
        """Return new context with added metadata.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            New PipelineContext with the metadata added
        """
        new_metadata = {**self.metadata, key: value}
        return PipelineContext(
            config=self.config,
            job_id=self.job_id,
            inputs=self.inputs,
            outputs=self.outputs,
            metadata=new_metadata,
            state_repository=self.state_repository,
        )
