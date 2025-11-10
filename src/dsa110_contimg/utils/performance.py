"""
Performance metrics and monitoring utilities.

This module provides utilities for tracking and analyzing performance metrics
across the DSA-110 continuum imaging pipeline. Use the `track_performance`
decorator to automatically track execution time for operations.

Example:
    ```python
    from dsa110_contimg.utils.performance import track_performance

    @track_performance("subband_loading")
    def load_subbands(file_list):
        # ... loading logic ...
        return uv_data

    # Later, get performance statistics
    from dsa110_contimg.utils.performance import get_performance_stats
    stats = get_performance_stats()
    print(f"Average subband loading time: {stats['subband_loading']['mean']:.2f}s")
    ```
"""

import time
from functools import wraps
from typing import Dict, List, Any, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Global performance metrics storage
_performance_metrics: Dict[str, List[float]] = {}


def track_performance(operation_name: str, log_result: bool = False):
    """
    Decorator to track operation performance.

    Tracks execution time for decorated functions and stores metrics
    in a global dictionary. Metrics can be retrieved later using
    `get_performance_stats()`.

    Args:
        operation_name: Name to identify this operation in metrics
        log_result: If True, log the execution time after each call

    Returns:
        Decorated function that tracks performance

    Example:
        ```python
        @track_performance("ms_validation")
        def validate_ms(ms_path: str) -> bool:
            # ... validation logic ...
            return True
        ```
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                _performance_metrics.setdefault(operation_name, []).append(elapsed)

                if log_result:
                    logger.debug(
                        f"Performance: {operation_name} took {elapsed:.3f}s "
                        f"(args: {len(args)} positional, {len(kwargs)} keyword)"
                    )

                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                error_name = f"{operation_name}_error"
                _performance_metrics.setdefault(error_name, []).append(elapsed)

                if log_result:
                    logger.debug(
                        f"Performance: {operation_name} failed after {elapsed:.3f}s: {e}"
                    )

                raise

        return wrapper

    return decorator


def get_performance_stats(
    operation_name: Optional[str] = None,
) -> Dict[str, Dict[str, float]]:
    """
    Get performance statistics for tracked operations.

    Args:
        operation_name: If provided, return stats only for this operation.
                      If None, return stats for all operations.

    Returns:
        Dictionary mapping operation names to statistics dictionaries:
        - 'mean': Average execution time (seconds)
        - 'median': Median execution time (seconds)
        - 'min': Minimum execution time (seconds)
        - 'max': Maximum execution time (seconds)
        - 'std': Standard deviation (seconds)
        - 'count': Number of measurements

    Example:
        ```python
        stats = get_performance_stats()
        print(stats['subband_loading']['mean'])  # Average time
        print(stats['subband_loading']['count'])  # Number of calls
        ```
    """
    stats = {}

    operations = (
        [operation_name] if operation_name else list(_performance_metrics.keys())
    )

    for op in operations:
        if op not in _performance_metrics:
            continue

        times = _performance_metrics[op]
        if not times:
            continue

        stats[op] = {
            "mean": float(np.mean(times)),
            "median": float(np.median(times)),
            "min": float(np.min(times)),
            "max": float(np.max(times)),
            "std": float(np.std(times)),
            "count": len(times),
        }

    return stats


def clear_performance_metrics(operation_name: Optional[str] = None) -> None:
    """
    Clear performance metrics.

    Args:
        operation_name: If provided, clear only this operation's metrics.
                      If None, clear all metrics.

    Example:
        ```python
        # Clear all metrics
        clear_performance_metrics()

        # Clear only subband_loading metrics
        clear_performance_metrics("subband_loading")
        ```
    """
    if operation_name:
        if operation_name in _performance_metrics:
            del _performance_metrics[operation_name]
    else:
        _performance_metrics.clear()


def get_performance_summary() -> str:
    """
    Get a human-readable summary of performance metrics.

    Returns:
        Multi-line string with formatted performance statistics

    Example:
        ```python
        print(get_performance_summary())
        # Output:
        # subband_loading: mean=2.34s, median=2.30s, min=1.95s, max=3.12s (count=10)
        # ms_validation: mean=0.15s, median=0.14s, min=0.12s, max=0.18s (count=20)
        ```
    """
    stats = get_performance_stats()

    if not stats:
        return "No performance metrics recorded yet."

    lines = []
    for op, op_stats in sorted(stats.items()):
        lines.append(
            f"{op}: "
            f"mean={op_stats['mean']:.3f}s, "
            f"median={op_stats['median']:.3f}s, "
            f"min={op_stats['min']:.3f}s, "
            f"max={op_stats['max']:.3f}s "
            f"(count={op_stats['count']})"
        )

    return "\n".join(lines)
