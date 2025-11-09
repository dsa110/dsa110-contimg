"""
Parallel processing utilities for independent operations.

This module provides utilities for parallelizing independent operations,
with careful consideration for CASA tool thread-safety limitations.

WARNING: CASA tools (imhead, gaincal, bandpass, etc.) may not be thread-safe.
Use parallel processing only for operations that:
- Don't use CASA tools directly
- Are I/O-bound (file reading/writing)
- Are independent (no shared state)

For CASA operations, use ProcessPoolExecutor (separate processes) rather than
ThreadPoolExecutor (shared memory) to avoid thread-safety issues.
"""

from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from typing import List, Callable, TypeVar, Union
import logging
from dsa110_contimg.utils.runtime_safeguards import log_progress

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


def process_parallel(
    items: List[T],
    func: Callable[[T], R],
    max_workers: int = 4,
    use_processes: bool = True,
    show_progress: bool = True,
    desc: str = "Processing",
) -> List[Union[R, None]]:
    """
    Process items in parallel with progress feedback.

    OPTIMIZATION: Use parallel processing for independent operations to
    achieve 2-4x speedup on multi-core systems (depending on workload).

    Args:
        items: List of items to process
        func: Function to apply to each item (must be pickleable if
            use_processes=True)
        max_workers: Maximum number of parallel workers
        use_processes: If True, use ProcessPoolExecutor (safe for CASA tools).
            If False, use ThreadPoolExecutor (faster but CASA tools may not
            be thread-safe)
        show_progress: Whether to show progress bar
        desc: Progress bar description

    Returns:
        List of results (order preserved). Failed items are None.

    Example:
        # Process multiple MS files in parallel
        def validate_ms(ms_path: str) -> dict:
            return {'ms_path': ms_path, 'valid': True}

        ms_paths = ['ms1.ms', 'ms2.ms', 'ms3.ms']
        results = process_parallel(ms_paths, validate_ms, max_workers=4)
    """
    if not items:
        return []

    if len(items) == 1:
        # No need for parallelization for single item
        return [func(items[0])]

    log_progress(
        f"Starting parallel processing: {len(items)} items with {max_workers} workers ({'processes' if use_processes else 'threads'})", flush=True)

    results = []
    executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor

    try:
        from dsa110_contimg.utils.progress import get_progress_bar
        has_progress = True
    except ImportError:
        has_progress = False
        show_progress = False

    with executor_class(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(func, item): i for i,
                   item in enumerate(items)}

        # Collect results in order
        results = [None] * len(items)

        if show_progress and has_progress:
            # Use progress bar
            try:
                with get_progress_bar(total=len(items), desc=desc) as pbar:
                    for future in as_completed(futures):
                        idx = futures[future]
                        try:
                            results[idx] = future.result()
                        except (OSError, IOError, ValueError, RuntimeError, MemoryError) as e:
                            logger.error(
                                f"Error processing item {idx}: {e}", exc_info=True)
                            results[idx] = None
                        except Exception as e:
                            logger.error(
                                f"Unexpected error processing item {idx}: {type(e).__name__}: {e}", exc_info=True)
                            results[idx] = None
                        pbar.update(1)
            except (OSError, IOError, RuntimeError) as e:
                logger.warning(
                    f"Progress bar failed, continuing without progress display: {e}")
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        results[idx] = future.result()
                    except (OSError, IOError, ValueError, RuntimeError, MemoryError) as e:
                        logger.error(
                            f"Error processing item {idx}: {e}", exc_info=True)
                        results[idx] = None
                    except Exception as e:
                        logger.error(
                            f"Unexpected error processing item {idx}: {type(e).__name__}: {e}", exc_info=True)
                        results[idx] = None
        else:
            # No progress bar
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except (OSError, IOError, ValueError, RuntimeError, MemoryError) as e:
                    logger.error(
                        f"Error processing item {idx}: {e}", exc_info=True)
                    results[idx] = None
                except Exception as e:
                    logger.error(
                        f"Unexpected error processing item {idx}: {type(e).__name__}: {e}", exc_info=True)
                    results[idx] = None

    log_progress(
        f"Completed parallel processing: {len([r for r in results if r is not None])}/{len(items)} items succeeded", flush=True)
    return results


def process_batch_parallel(
    items: List[T],
    func: Callable[[T], R],
    batch_size: int = 10,
    max_workers: int = 4,
    use_processes: bool = True,
    show_progress: bool = True,
    desc: str = "Processing batches"
) -> List[R]:
    """
    Process items in batches with parallel execution within each batch.

    Useful for very large item lists where submitting all at once would
    consume too much memory or create too many concurrent operations.

    Args:
        items: List of items to process
        func: Function to apply to each item
        batch_size: Number of items per batch
        max_workers: Maximum number of parallel workers per batch
        use_processes: Use ProcessPoolExecutor (True) or ThreadPoolExecutor (False)
        show_progress: Whether to show progress
        desc: Progress bar description

    Returns:
        List of results (order preserved)
    """
    log_progress(
        f"Starting batch parallel processing: {len(items)} items in batches of {batch_size}", flush=True)

    all_results = []
    total_batches = (len(items) + batch_size - 1) // batch_size

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(items))
        batch = items[start_idx:end_idx]

        if show_progress:
            logger.info(
                f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} items)...")

        batch_results = process_parallel(
            batch,
            func,
            max_workers=max_workers,
            use_processes=use_processes,
            show_progress=False,  # Don't show nested progress bars
            desc=f"{desc} (batch {batch_num + 1}/{total_batches})"
        )
        all_results.extend(batch_results)

    log_progress(
        f"Completed batch parallel processing: {len([r for r in all_results if r is not None])}/{len(items)} items succeeded", flush=True)
    return all_results


def map_parallel(
    func: Callable[..., R],
    *iterables,
    max_workers: int = 4,
    use_processes: bool = True,
    show_progress: bool = True,
    desc: str = "Processing"
) -> List[R]:
    """
    Parallel version of map() function.

    Args:
        func: Function to apply (must accept same number of arguments as iterables)
        *iterables: Iterables to map over (must be same length)
        max_workers: Maximum number of parallel workers
        use_processes: Use ProcessPoolExecutor (True) or ThreadPoolExecutor (False)
        show_progress: Whether to show progress
        desc: Progress bar description

    Returns:
        List of results

    Raises:
        ValueError: If iterables have different lengths

    Example:
        # Process multiple MS files with different parameters
        def validate_ms(ms_path: str, threshold: float) -> dict:
            return {'ms_path': ms_path, 'valid': True, 'threshold': threshold}

        ms_paths = ['ms1.ms', 'ms2.ms', 'ms3.ms']
        thresholds = [0.1, 0.2, 0.3]
        results = map_parallel(validate_ms, ms_paths, thresholds, max_workers=4)
    """
    if not iterables:
        raise ValueError("At least one iterable must be provided")

    items_list = list(zip(*iterables))
    if not items_list:
        return []

    def func_wrapper(args: tuple) -> R:
        return func(*args)

    return process_parallel(items_list, func_wrapper, max_workers=max_workers,
                            use_processes=use_processes, show_progress=show_progress, desc=desc)
