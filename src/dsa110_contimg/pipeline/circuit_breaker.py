"""Circuit breaker pattern for resilient service calls.

Provides circuit breaker functionality to prevent cascading failures.
Uses circuitbreaker library if available, falls back to simple implementation.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


try:
    from circuitbreaker import circuit

    CIRCUITBREAKER_AVAILABLE = True
except ImportError:
    CIRCUITBREAKER_AVAILABLE = False


class SimpleCircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.success_count = 0

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Call function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time >= self.recovery_timeout
            ):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. "
                    f"Will retry after {self.recovery_timeout} seconds."
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 1:  # Single success closes circuit
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: type[Exception] = Exception,
):
    """Decorator for circuit breaker pattern.

    Usage:
        @circuit_breaker(failure_threshold=5, recovery_timeout=60)
        def my_function():
            # Function implementation
            pass
    """
    if CIRCUITBREAKER_AVAILABLE:
        # Use library decorator
        return circuit(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
        )
    else:
        # Use simple implementation
        breaker = SimpleCircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
        )

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args: Any, **kwargs: Any) -> T:
                return breaker.call(func, *args, **kwargs)

            return wrapper

        return decorator


# Pre-configured circuit breakers for common operations

ese_detection_circuit_breaker = SimpleCircuitBreaker(
    failure_threshold=5, recovery_timeout=60.0, expected_exception=RuntimeError
)

calibration_solve_circuit_breaker = SimpleCircuitBreaker(
    failure_threshold=3,
    recovery_timeout=300.0,  # 5 minutes for calibration
    expected_exception=RuntimeError,
)

photometry_circuit_breaker = SimpleCircuitBreaker(
    failure_threshold=10, recovery_timeout=30.0, expected_exception=IOError
)
