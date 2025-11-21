"""Performance optimization utilities for calibration.

Provides parallel processing and memory management for large-scale calibration operations.
"""

import logging
import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


def get_optimal_workers(n_tasks: int, max_workers: Optional[int] = None) -> int:
    """Determine optimal number of worker processes/threads.

    Args:
        n_tasks: Number of tasks to process
        max_workers: Maximum number of workers (default: CPU count)

    Returns:
        Optimal number of workers
    """
    cpu_count = mp.cpu_count()

    if max_workers is None:
        max_workers = cpu_count

    # Don't use more workers than tasks
    optimal = min(n_tasks, max_workers, cpu_count)

    # For I/O-bound tasks (like CASA operations), can use more workers
    # For CPU-bound tasks, limit to CPU count
    return max(1, optimal)


def parallel_process_spws(
    ms_path: str,
    process_func: Callable[[str, int], Any],
    spw_list: Optional[List[int]] = None,
    max_workers: Optional[int] = None,
    use_threads: bool = False,
) -> List[Any]:
    """Process multiple SPWs in parallel.

    Args:
        ms_path: Path to Measurement Set
        process_func: Function to call for each SPW: func(ms_path, spw_id) -> result
        spw_list: List of SPW IDs to process (None = auto-detect)
        max_workers: Maximum number of parallel workers
        use_threads: Use threads instead of processes (for I/O-bound tasks)

    Returns:
        List of results from process_func
    """
    # Ensure CASAPATH is set before importing CASA modules
    from dsa110_contimg.utils.casa_init import ensure_casa_path

    ensure_casa_path()

    import casacore.tables as casatables

    table = casatables.table

    # Auto-detect SPWs if not provided
    if spw_list is None:
        with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True, ack=False) as spw_tb:
            spw_list = list(range(spw_tb.nrows()))

    if not spw_list:
        logger.warning("No SPWs to process")
        return []

    n_workers = get_optimal_workers(len(spw_list), max_workers)
    logger.info(f"Processing {len(spw_list)} SPW(s) with {n_workers} worker(s)")

    executor_class = ThreadPoolExecutor if use_threads else ProcessPoolExecutor

    results = []
    with executor_class(max_workers=n_workers) as executor:
        # Submit all tasks
        future_to_spw = {
            executor.submit(process_func, ms_path, spw_id): spw_id for spw_id in spw_list
        }

        # Collect results as they complete
        for future in as_completed(future_to_spw):
            spw_id = future_to_spw[future]
            try:
                result = future.result()
                results.append((spw_id, result))
                logger.debug(f"Completed SPW {spw_id}")
            except Exception as e:
                logger.error(f"SPW {spw_id} processing failed: {e}")
                raise

    # Sort results by SPW ID
    results.sort(key=lambda x: x[0])
    return [result for _, result in results]


def parallel_process_antennas(
    ms_path: str,
    process_func: Callable[[str, int], Any],
    antenna_list: Optional[List[int]] = None,
    max_workers: Optional[int] = None,
    use_threads: bool = True,  # Default to threads for antenna processing
) -> List[Any]:
    """Process multiple antennas in parallel.

    Args:
        ms_path: Path to Measurement Set
        process_func: Function to call for each antenna: func(ms_path, ant_id) -> result
        antenna_list: List of antenna IDs to process (None = auto-detect)
        max_workers: Maximum number of parallel workers
        use_threads: Use threads instead of processes (default: True for I/O-bound)

    Returns:
        List of results from process_func
    """
    import casacore.tables as casatables

    table = casatables.table

    # Auto-detect antennas if not provided
    if antenna_list is None:
        with table(f"{ms_path}::ANTENNA", readonly=True, ack=False) as ant_tb:
            antenna_list = list(range(ant_tb.nrows()))

    if not antenna_list:
        logger.warning("No antennas to process")
        return []

    n_workers = get_optimal_workers(len(antenna_list), max_workers)
    logger.info(f"Processing {len(antenna_list)} antenna(s) with {n_workers} worker(s)")

    executor_class = ThreadPoolExecutor if use_threads else ProcessPoolExecutor

    results = []
    with executor_class(max_workers=n_workers) as executor:
        # Submit all tasks
        future_to_ant = {
            executor.submit(process_func, ms_path, ant_id): ant_id for ant_id in antenna_list
        }

        # Collect results as they complete
        for future in as_completed(future_to_ant):
            ant_id = future_to_ant[future]
            try:
                result = future.result()
                results.append((ant_id, result))
                logger.debug(f"Completed antenna {ant_id}")
            except Exception as e:
                logger.error(f"Antenna {ant_id} processing failed: {e}")
                raise

    # Sort results by antenna ID
    results.sort(key=lambda x: x[0])
    return [result for _, result in results]


def optimize_memory_usage():
    """Optimize memory usage for calibration operations.

    Sets environment variables and provides memory management utilities.
    """
    import gc

    # Set CASA memory limits if available
    casa_memory_limit_gb = os.environ.get("CASA_MEMORY_LIMIT_GB", "16")
    os.environ["CASA_MEMORY_LIMIT_GB"] = str(casa_memory_limit_gb)

    # Force garbage collection
    gc.collect()

    logger.debug(f"Memory optimization applied (CASA limit: {casa_memory_limit_gb} GB)")


def chunk_processing(
    items: List[Any],
    chunk_size: int,
    process_chunk: Callable[[List[Any]], Any],
    max_workers: Optional[int] = None,
) -> List[Any]:
    """Process a large list in chunks with parallel processing.

    Useful for processing large datasets that don't fit in memory.

    Args:
        items: List of items to process
        chunk_size: Number of items per chunk
        process_chunk: Function to process a chunk: func(chunk) -> result
        max_workers: Maximum number of parallel workers

    Returns:
        List of results from process_chunk
    """
    if not items:
        return []

    # Split into chunks
    chunks = [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]
    logger.info(f"Processing {len(items)} items in {len(chunks)} chunk(s) of size {chunk_size}")

    n_workers = get_optimal_workers(len(chunks), max_workers)

    results = []
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        future_to_chunk = {
            executor.submit(process_chunk, chunk): i for i, chunk in enumerate(chunks)
        }

        for future in as_completed(future_to_chunk):
            chunk_idx = future_to_chunk[future]
            try:
                result = future.result()
                results.append((chunk_idx, result))
                logger.debug(f"Completed chunk {chunk_idx + 1}/{len(chunks)}")
            except Exception as e:
                logger.error(f"Chunk {chunk_idx} processing failed: {e}")
                raise

    # Sort results by chunk index and flatten
    results.sort(key=lambda x: x[0])
    return [result for _, result in results]


def estimate_memory_requirements(ms_path: str) -> dict:
    """Estimate memory requirements for calibration operations.

    Args:
        ms_path: Path to Measurement Set

    Returns:
        Dictionary with memory estimates (in GB)
    """
    import casacore.tables as casatables
    import numpy as np

    table = casatables.table

    try:
        with table(ms_path, readonly=True, ack=False) as tb:
            n_rows = tb.nrows()
            colnames = tb.colnames()

            # Estimate from DATA column
            if "DATA" in colnames:
                data_shape = tb.getcol("DATA", startrow=0, nrow=1).shape
                # Complex float64 = 16 bytes per value
                bytes_per_row = np.prod(data_shape) * 16
            else:
                bytes_per_row = 1024  # Fallback estimate

            total_bytes = n_rows * bytes_per_row
            total_gb = total_bytes / (1024**3)

            # Calibration typically needs 2-3x the MS size
            calibration_gb = total_gb * 2.5

            return {
                "ms_size_gb": total_gb,
                "estimated_calibration_memory_gb": calibration_gb,
                "recommended_memory_gb": max(8, calibration_gb * 1.2),  # 20% overhead
            }
    except Exception as e:
        logger.warning(f"Could not estimate memory requirements: {e}")
        return {
            "ms_size_gb": None,
            "estimated_calibration_memory_gb": None,
            "recommended_memory_gb": 16,  # Safe default
        }
