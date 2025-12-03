#!/usr/bin/env python3
"""
Resource Limiting Utilities for DSA-110 Testing

This module provides safeguards to prevent runaway memory/CPU usage
from crashing the system. Use these wrappers for any computationally
intensive testing or benchmarking.

USAGE:
------
    from resource_limits import (
        set_memory_limit,
        set_cpu_time_limit,
        ResourceLimitedRunner,
        safe_run,
    )
    
    # Simple: limit memory to 4GB
    set_memory_limit(4)
    
    # Or use context manager with all limits
    with ResourceLimitedRunner(max_memory_gb=4, max_cpu_seconds=60):
        run_expensive_computation()
    
    # Or run in subprocess with hard kill
    result = safe_run(my_function, args, max_memory_gb=2, timeout_seconds=30)

WHAT HAPPENED:
--------------
On Dec 2, 2025, a validation test created arrays for 96 antennas × 768 channels
which consumed all system RAM, caused disk disconnection, and required a reboot.

This module prevents that from ever happening again.
"""

import gc
import os
import resource
import signal
import sys
import multiprocessing
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, Tuple

# =============================================================================
# Constants - Conservative defaults for shared systems
# =============================================================================

# Default limits (conservative for shared systems)
DEFAULT_MAX_MEMORY_GB = 4.0      # 4 GB - safe for most systems
DEFAULT_MAX_CPU_SECONDS = 120   # 2 minutes
DEFAULT_MAX_WALL_SECONDS = 300  # 5 minutes

# Hard limits (never exceed these)
HARD_MAX_MEMORY_GB = 8.0        # Never allocate more than 8GB
HARD_MAX_CPU_SECONDS = 600      # Never run more than 10 min CPU
HARD_MAX_WALL_SECONDS = 900     # Never run more than 15 min wall clock


# =============================================================================
# Low-level resource limits (Linux only)
# =============================================================================

def set_memory_limit(max_gb: float = DEFAULT_MAX_MEMORY_GB, gpu_safe: bool = False) -> None:
    """Set hard memory limit for current process.
    
    Uses Linux rlimit to prevent memory allocation beyond limit.
    Process will receive MemoryError if limit is exceeded.
    
    Args:
        max_gb: Maximum memory in gigabytes (default: 4GB)
        gpu_safe: If True, skip RLIMIT_AS to allow GPU memory mapping.
                  RLIMIT_AS affects CUDA memory allocation because it limits
                  the total virtual address space which includes GPU memory maps.
    """
    if gpu_safe:
        print(f"✓ Memory limit: {max_gb:.1f} GB (soft - GPU safe mode)")
        return  # Skip RLIMIT_AS to allow CUDA to work
        
    # Enforce hard limit
    max_gb = min(max_gb, HARD_MAX_MEMORY_GB)
    max_bytes = int(max_gb * 1024 * 1024 * 1024)
    
    try:
        # RLIMIT_AS limits total address space (virtual memory)
        # WARNING: This breaks CUDA/GPU operations because CUDA uses
        # memory-mapped regions for GPU memory.
        resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))
        print(f"✓ Memory limit set: {max_gb:.1f} GB")
    except (ValueError, resource.error) as e:
        print(f"⚠ Could not set memory limit: {e}")


def set_cpu_time_limit(max_seconds: int = DEFAULT_MAX_CPU_SECONDS) -> None:
    """Set CPU time limit for current process.
    
    Process will receive SIGXCPU if CPU time exceeds limit.
    
    Args:
        max_seconds: Maximum CPU seconds (default: 120)
    """
    max_seconds = min(max_seconds, HARD_MAX_CPU_SECONDS)
    
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (max_seconds, max_seconds))
        print(f"✓ CPU time limit set: {max_seconds}s")
    except (ValueError, resource.error) as e:
        print(f"⚠ Could not set CPU limit: {e}")


def get_current_memory_gb() -> float:
    """Get current memory usage in GB."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / (1024 ** 3)
    except ImportError:
        # Fallback using /proc
        try:
            with open('/proc/self/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
        except:
            pass
    return 0.0


def check_available_memory() -> Tuple[float, float]:
    """Check available system memory.
    
    Returns:
        Tuple of (available_gb, total_gb)
    """
    try:
        import psutil
        mem = psutil.virtual_memory()
        return mem.available / (1024 ** 3), mem.total / (1024 ** 3)
    except ImportError:
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                total = available = 0
                for line in lines:
                    if line.startswith('MemTotal:'):
                        total = int(line.split()[1]) / (1024 ** 2)
                    elif line.startswith('MemAvailable:'):
                        available = int(line.split()[1]) / (1024 ** 2)
                return available, total
        except:
            return 0.0, 0.0


# =============================================================================
# Timeout handling
# =============================================================================

class TimeoutError(Exception):
    """Raised when operation times out."""
    pass


@contextmanager
def timeout(seconds: int, message: str = "Operation timed out"):
    """Context manager for wall-clock timeout.
    
    Args:
        seconds: Maximum wall-clock seconds
        message: Error message if timeout occurs
        
    Raises:
        TimeoutError: If operation exceeds timeout
    """
    def handler(signum, frame):
        raise TimeoutError(f"{message} (exceeded {seconds}s)")
    
    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


# =============================================================================
# Resource-limited context manager
# =============================================================================

@dataclass
class ResourceLimits:
    """Configuration for resource limits."""
    max_memory_gb: float = DEFAULT_MAX_MEMORY_GB
    max_cpu_seconds: int = DEFAULT_MAX_CPU_SECONDS
    max_wall_seconds: int = DEFAULT_MAX_WALL_SECONDS
    check_available_first: bool = True
    min_available_gb: float = 2.0  # Require at least 2GB free before starting


class ResourceLimitedRunner:
    """Context manager that enforces resource limits.
    
    Example:
        with ResourceLimitedRunner(max_memory_gb=4, max_wall_seconds=60):
            run_expensive_operation()
    """
    
    def __init__(
        self,
        max_memory_gb: float = DEFAULT_MAX_MEMORY_GB,
        max_cpu_seconds: int = DEFAULT_MAX_CPU_SECONDS,
        max_wall_seconds: int = DEFAULT_MAX_WALL_SECONDS,
        check_available_first: bool = True,
        min_available_gb: float = 2.0,
        gpu_safe: bool = False,
    ):
        """Initialize resource limiter.
        
        Args:
            max_memory_gb: Maximum memory in GB
            max_cpu_seconds: Maximum CPU time in seconds
            max_wall_seconds: Maximum wall clock time in seconds
            check_available_first: Whether to check available memory before starting
            min_available_gb: Minimum available memory required to start
            gpu_safe: If True, skip RLIMIT_AS to allow GPU operations.
                     RLIMIT_AS breaks CUDA because it limits virtual address space.
        """
        self.limits = ResourceLimits(
            max_memory_gb=min(max_memory_gb, HARD_MAX_MEMORY_GB),
            max_cpu_seconds=min(max_cpu_seconds, HARD_MAX_CPU_SECONDS),
            max_wall_seconds=min(max_wall_seconds, HARD_MAX_WALL_SECONDS),
            check_available_first=check_available_first,
            min_available_gb=min_available_gb,
        )
        self.gpu_safe = gpu_safe
        self._old_alarm_handler = None
    
    def __enter__(self):
        # Check available memory first
        if self.limits.check_available_first:
            available, total = check_available_memory()
            print(f"System memory: {available:.1f} GB available / {total:.1f} GB total")
            
            if available < self.limits.min_available_gb:
                raise MemoryError(
                    f"Insufficient memory: {available:.1f} GB available, "
                    f"need at least {self.limits.min_available_gb:.1f} GB"
                )
            
            # Don't request more than what's available
            effective_limit = min(self.limits.max_memory_gb, available * 0.8)
            if effective_limit < self.limits.max_memory_gb:
                print(f"⚠ Reducing memory limit to {effective_limit:.1f} GB (80% of available)")
                self.limits.max_memory_gb = effective_limit
        
        # Set resource limits
        set_memory_limit(self.limits.max_memory_gb, gpu_safe=self.gpu_safe)
        set_cpu_time_limit(self.limits.max_cpu_seconds)
        
        # Set wall-clock alarm
        def alarm_handler(signum, frame):
            raise TimeoutError(f"Wall-clock timeout exceeded ({self.limits.max_wall_seconds}s)")
        
        self._old_alarm_handler = signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(self.limits.max_wall_seconds)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clear alarm
        signal.alarm(0)
        if self._old_alarm_handler:
            signal.signal(signal.SIGALRM, self._old_alarm_handler)
        
        # Force garbage collection
        gc.collect()
        
        # Log final memory usage
        current = get_current_memory_gb()
        print(f"Final memory usage: {current:.2f} GB")
        
        return False  # Don't suppress exceptions


# =============================================================================
# Subprocess-based safe execution (ultimate protection)
# =============================================================================

def _run_in_subprocess(func: Callable, args: tuple, kwargs: dict, 
                       result_queue: multiprocessing.Queue,
                       max_memory_gb: float, max_cpu_seconds: int):
    """Worker function that runs in subprocess with limits."""
    try:
        # Set limits in subprocess
        set_memory_limit(max_memory_gb)
        set_cpu_time_limit(max_cpu_seconds)
        
        # Run the function
        result = func(*args, **kwargs)
        result_queue.put(('success', result))
    except Exception as e:
        result_queue.put(('error', str(e)))


def safe_run(
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    max_memory_gb: float = DEFAULT_MAX_MEMORY_GB,
    max_cpu_seconds: int = DEFAULT_MAX_CPU_SECONDS,
    timeout_seconds: int = DEFAULT_MAX_WALL_SECONDS,
) -> Any:
    """Run function in subprocess with hard resource limits.
    
    This is the SAFEST option - if the subprocess goes crazy, we can
    kill it without affecting the parent process.
    
    Args:
        func: Function to run
        args: Positional arguments
        kwargs: Keyword arguments
        max_memory_gb: Memory limit in GB
        max_cpu_seconds: CPU time limit
        timeout_seconds: Wall-clock timeout
        
    Returns:
        Function result
        
    Raises:
        TimeoutError: If function times out
        MemoryError: If function exceeds memory limit
        Exception: Any exception from the function
    """
    if kwargs is None:
        kwargs = {}
    
    # Enforce hard limits
    max_memory_gb = min(max_memory_gb, HARD_MAX_MEMORY_GB)
    max_cpu_seconds = min(max_cpu_seconds, HARD_MAX_CPU_SECONDS)
    timeout_seconds = min(timeout_seconds, HARD_MAX_WALL_SECONDS)
    
    result_queue = multiprocessing.Queue()
    
    process = multiprocessing.Process(
        target=_run_in_subprocess,
        args=(func, args, kwargs, result_queue, max_memory_gb, max_cpu_seconds)
    )
    
    process.start()
    process.join(timeout=timeout_seconds)
    
    if process.is_alive():
        # Kill the runaway process
        process.terminate()
        process.join(timeout=5)
        if process.is_alive():
            process.kill()  # Force kill
            process.join()
        raise TimeoutError(f"Function timed out after {timeout_seconds}s (killed)")
    
    if result_queue.empty():
        raise RuntimeError("Subprocess died without returning result (likely OOM killed)")
    
    status, result = result_queue.get()
    
    if status == 'error':
        raise RuntimeError(f"Subprocess error: {result}")
    
    return result


# =============================================================================
# Decorator for resource-limited functions
# =============================================================================

def resource_limited(
    max_memory_gb: float = DEFAULT_MAX_MEMORY_GB,
    max_cpu_seconds: int = DEFAULT_MAX_CPU_SECONDS,
    max_wall_seconds: int = DEFAULT_MAX_WALL_SECONDS,
    use_subprocess: bool = False,
):
    """Decorator to apply resource limits to a function.
    
    Args:
        max_memory_gb: Memory limit
        max_cpu_seconds: CPU time limit
        max_wall_seconds: Wall-clock timeout
        use_subprocess: If True, run in subprocess for hard isolation
        
    Example:
        @resource_limited(max_memory_gb=2, max_wall_seconds=30)
        def my_expensive_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if use_subprocess:
                return safe_run(
                    func, args, kwargs,
                    max_memory_gb=max_memory_gb,
                    max_cpu_seconds=max_cpu_seconds,
                    timeout_seconds=max_wall_seconds,
                )
            else:
                with ResourceLimitedRunner(
                    max_memory_gb=max_memory_gb,
                    max_cpu_seconds=max_cpu_seconds,
                    max_wall_seconds=max_wall_seconds,
                ):
                    return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Memory estimation utilities
# =============================================================================

def estimate_array_memory_gb(
    shape: tuple,
    dtype: str = 'complex128',
) -> float:
    """Estimate memory for a numpy array.
    
    Args:
        shape: Array shape tuple
        dtype: Numpy dtype string
        
    Returns:
        Estimated memory in GB
    """
    import numpy as np
    
    dtype_obj = np.dtype(dtype)
    n_elements = 1
    for dim in shape:
        n_elements *= dim
    
    bytes_needed = n_elements * dtype_obj.itemsize
    gb_needed = bytes_needed / (1024 ** 3)
    
    return gb_needed


def check_array_fits(
    shape: tuple,
    dtype: str = 'complex128',
    n_copies: int = 2,
    safety_factor: float = 1.5,
) -> Tuple[bool, str]:
    """Check if array(s) will fit in available memory.
    
    Args:
        shape: Array shape
        dtype: Numpy dtype
        n_copies: Number of copies needed (default 2 for operations)
        safety_factor: Additional safety margin
        
    Returns:
        Tuple of (fits: bool, message: str)
    """
    array_gb = estimate_array_memory_gb(shape, dtype)
    total_needed = array_gb * n_copies * safety_factor
    
    available, total = check_available_memory()
    current_usage = get_current_memory_gb()
    
    fits = total_needed < (available - 1.0)  # Keep 1GB free
    
    message = (
        f"Array {shape} ({dtype}): {array_gb:.2f} GB\n"
        f"Total needed ({n_copies} copies × {safety_factor} safety): {total_needed:.2f} GB\n"
        f"Available: {available:.2f} GB (using {current_usage:.2f} GB)"
    )
    
    if not fits:
        message += f"\n⚠ WILL NOT FIT - reduce size or dtype!"
    
    return fits, message


def suggest_safe_array_size(
    n_dims: int = 2,
    dtype: str = 'complex128',
    max_memory_gb: float = 2.0,
) -> int:
    """Suggest safe array dimension for given memory budget.
    
    Args:
        n_dims: Number of dimensions (assumes square)
        dtype: Numpy dtype
        max_memory_gb: Maximum memory to use
        
    Returns:
        Suggested dimension size
    """
    import numpy as np
    
    dtype_obj = np.dtype(dtype)
    bytes_per_element = dtype_obj.itemsize
    
    max_bytes = max_memory_gb * (1024 ** 3)
    max_elements = max_bytes / bytes_per_element
    
    dim_size = int(max_elements ** (1.0 / n_dims))
    
    return dim_size


# =============================================================================
# Quick self-test
# =============================================================================

def _self_test():
    """Run self-test of resource limits."""
    print("=" * 60)
    print("Resource Limits Self-Test")
    print("=" * 60)
    
    # Check system memory
    available, total = check_available_memory()
    print(f"\nSystem memory: {available:.1f} GB available / {total:.1f} GB total")
    print(f"Current usage: {get_current_memory_gb():.2f} GB")
    
    # Test array size estimation
    print("\n--- Array Size Estimation ---")
    test_shapes = [
        (1000, 1000),
        (4096, 4096),
        (96, 768, 10),  # DSA-110 like
        (4560, 768, 10),  # With baselines
    ]
    
    for shape in test_shapes:
        fits, msg = check_array_fits(shape, 'complex128', n_copies=3)
        status = "✓" if fits else "✗"
        print(f"\n{status} Shape {shape}:")
        print(f"   {msg.replace(chr(10), chr(10) + '   ')}")
    
    # Suggest safe sizes
    print("\n--- Safe Array Sizes (2GB budget) ---")
    print(f"2D complex128: {suggest_safe_array_size(2, 'complex128', 2.0)}")
    print(f"2D complex64:  {suggest_safe_array_size(2, 'complex64', 2.0)}")
    print(f"3D complex128: {suggest_safe_array_size(3, 'complex128', 2.0)}")
    
    # Test timeout
    print("\n--- Timeout Test (2s limit) ---")
    try:
        with timeout(2, "Test timeout"):
            import time
            time.sleep(1)
            print("✓ Completed within timeout")
    except TimeoutError as e:
        print(f"✗ {e}")
    
    print("\n" + "=" * 60)
    print("Self-test complete!")
    print("=" * 60)


if __name__ == "__main__":
    _self_test()
