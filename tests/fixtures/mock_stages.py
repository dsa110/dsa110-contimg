"""
Mock pipeline stages for testing.
"""

from typing import Optional, Tuple

from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import PipelineStage


class MockStage(PipelineStage):
    """Mock stage for testing orchestrator logic.
    
    Can be configured to succeed, fail, or fail a certain number of times
    before succeeding (for testing retry policies).
    """
    
    def __init__(
        self,
        name: str,
        should_fail: bool = False,
        fail_count: int = 0,
        delay: float = 0.0,
    ):
        """Initialize mock stage.
        
        Args:
            name: Stage name
            should_fail: If True, stage will always fail
            fail_count: Number of times to fail before succeeding (for retry tests)
            delay: Artificial delay in seconds (for performance tests)
        """
        self.name = name
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.delay = delay
        self._call_count = 0
        self.executed = False
        self.validated = False
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute mock stage."""
        import time
        
        self._call_count += 1
        self.executed = True
        
        if self.delay > 0:
            time.sleep(self.delay)
        
        # Fail if configured to fail, or if we haven't exceeded fail_count
        if self.should_fail or self._call_count <= self.fail_count:
            raise ValueError(f"Mock failure in {self.name} (attempt {self._call_count})")
        
        return context.with_output(f"{self.name}_output", f"value_{self.name}")
    
    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate mock stage."""
        self.validated = True
        return True, None
    
    def get_name(self) -> str:
        """Get stage name."""
        return self.name


class FailingValidationStage(PipelineStage):
    """Mock stage that fails validation."""
    
    def __init__(self, name: str, error_message: str = "Validation failed"):
        self.name = name
        self.error_message = error_message
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute stage (should not be called if validation fails)."""
        return context
    
    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Fail validation."""
        return False, self.error_message
    
    def get_name(self) -> str:
        """Get stage name."""
        return self.name


class SlowStage(MockStage):
    """Mock stage that takes a long time to execute."""
    
    def __init__(self, name: str, duration: float = 1.0):
        super().__init__(name, delay=duration)

