"""
DSA-110 Streaming Converter Module.

This module provides a streaming data ingest and processing pipeline for
DSA-110 continuum imaging. It watches for incoming HDF5 subband files,
groups them by observation time, and processes complete groups through
conversion, calibration, imaging, and mosaic stages.

Architecture:
    - queue.py: SubbandQueue - SQLite-backed queue for tracking subband arrivals
    - watcher.py: StreamingWatcher - Watchdog-based filesystem monitoring
    - stages/: Pipeline stages for each processing step
    - worker.py: StreamingWorker - Orchestrates stages for queued groups

Usage:
    from dsa110_contimg.conversion.streaming import (
        SubbandQueue,
        StreamingWatcher,
        StreamingWorker,
    )
    
    # Create queue
    queue = SubbandQueue(db_path, expected_subbands=16)
    
    # Start watcher
    watcher = StreamingWatcher(input_dir, queue)
    watcher.start()
    
    # Process groups
    worker = StreamingWorker(queue, output_dir)
    worker.run()

The module maintains backwards compatibility with the original streaming_converter.py
interface through re-exports.
"""

from __future__ import annotations

# Re-export from queue module
from .queue import SubbandQueue

# Re-export from watcher module  
from .watcher import StreamingWatcher

# Re-export from worker module
from .worker import StreamingWorker

# Stage exports
from .stages import (
    ConversionStage,
    CalibrationStage,
    ImagingStage,
    PhotometryStage,
    MosaicStage,
)

# CLI module
from .cli import main as run_streaming_pipeline, StreamingPipeline

__all__ = [
    # Core components
    "SubbandQueue",
    "StreamingWatcher", 
    "StreamingWorker",
    # Pipeline stages
    "ConversionStage",
    "CalibrationStage",
    "ImagingStage",
    "PhotometryStage",
    "MosaicStage",
    # CLI
    "run_streaming_pipeline",
    "StreamingPipeline",
]
