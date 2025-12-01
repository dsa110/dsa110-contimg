"""
Base classes for pipeline stages.

A pipeline stage is a unit of work that transforms a PipelineContext into
a new PipelineContext with additional outputs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple

from dsa110_contimg.pipeline.context import PipelineContext


class StageStatus(Enum):
    """Status of a pipeline stage execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionMode(Enum):
    """Execution mode for a pipeline stage."""

    DIRECT = "direct"  # In-process execution (default, faster)
    SUBPROCESS = "subprocess"  # Isolated subprocess (for memory safety)
    REMOTE = "remote"  # Distributed execution (future)


class PipelineStage(ABC):
    """Base class for all pipeline stages.

    A stage transforms a PipelineContext by executing work and returning
    an updated context with new outputs.

    Example:
        class ConversionStage(PipelineStage):
            def execute(self, context: PipelineContext) -> PipelineContext:
                ms_path = convert_uvh5_to_ms(context.inputs["input_path"])
                return context.with_output("ms_path", ms_path)

            def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
                if "input_path" not in context.inputs:
                    return False, "input_path required"
                return True, None
    """

    execution_mode: ExecutionMode = ExecutionMode.DIRECT

    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute stage and return updated context.

        Args:
            context: Input context with configuration and inputs

        Returns:
            Updated context with new outputs

        Raises:
            Exception: If stage execution fails
        """
        ...

    @abstractmethod
    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for stage execution.

        Args:
            context: Context to validate

        Returns:
            Tuple of (is_valid, error_message). If is_valid is False,
            error_message should explain why validation failed.
        """
        ...

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup resources after execution (optional).

        This method is called after stage execution (success or failure)
        to perform any necessary cleanup. On failure, this should clean up
        any partial outputs to prevent accumulation of corrupted files.

        Args:
            context: Context used during execution
        """
        pass

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate stage outputs after execution (optional).

        This method is called after successful execution to validate that
        outputs are correct and complete before proceeding to next stage.

        Args:
            context: Context with outputs to validate

        Returns:
            Tuple of (is_valid, error_message). If is_valid is False,
            error_message should explain what validation failed.
        """
        return True, None

    def get_name(self) -> str:
        """Get stage name for logging and tracking.

        Returns:
            Stage name (defaults to class name)
        """
        return self.__class__.__name__
