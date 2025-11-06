"""
Retry policies and failure handling for pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class RetryStrategy(Enum):
    """Retry strategy for failed stages."""
    
    NONE = "none"
    EXPONENTIAL_BACKOFF = "exponential"
    FIXED_INTERVAL = "fixed"
    IMMEDIATE = "immediate"


@dataclass
class RetryPolicy:
    """Retry policy for stage execution.
    
    Example:
        policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay=1.0,
            max_delay=60.0,
        )
    """
    
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    initial_delay: float = 1.0
    max_delay: float = 60.0
    retryable_errors: Optional[Callable[[Exception], bool]] = None
    continue_on_failure: bool = False  # Continue pipeline even if stage fails
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if should retry after error.
        
        Args:
            attempt: Current attempt number (1-indexed)
            error: Exception that occurred
            
        Returns:
            True if should retry
        """
        if attempt >= self.max_attempts:
            return False
        
        if self.retryable_errors and not self.retryable_errors(error):
            return False
        
        return True
    
    def get_delay(self, attempt: int) -> float:
        """Get delay before retry.
        
        Args:
            attempt: Current attempt number (1-indexed)
            
        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.initial_delay * (2 ** (attempt - 1))
            return min(delay, self.max_delay)
        elif self.strategy == RetryStrategy.FIXED_INTERVAL:
            return self.initial_delay
        elif self.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        else:  # NONE
            return 0.0
    
    def should_continue(self) -> bool:
        """Determine if pipeline should continue after stage failure.
        
        Returns:
            True if pipeline should continue
        """
        return self.continue_on_failure

