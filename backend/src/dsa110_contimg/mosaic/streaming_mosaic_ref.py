"""
Streaming Mosaic Manager.

This module provides the high-level orchestration for the streaming
continuum imaging pipeline. It manages the flow of data from UVH5
files to final mosaic images.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import (
    CalibrationSolveStage,
    CalibrationStage,
    ConversionStage,
    ImagingStage,
)

logger = logging.getLogger(__name__)


class StreamingMosaicManager:
    """Manages the streaming mosaic pipeline.

    This class orchestrates the execution of pipeline stages for
    incoming data. It monitors the input directory for new files
    and triggers processing.

    Args:
        config: Pipeline configuration
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.running = False
        self.processed_files: Set[Path] = set()

        # Local queue for managing task concurrency
        self._processing_tasks: Set[asyncio.Task] = set()
        self._max_concurrent = 4

    async def start(self):
        """Start the mosaic manager."""
        self.running = True
        logger.info("Starting StreamingMosaicManager")

        while self.running:
            await self._process_cycle()
            await asyncio.sleep(self.config.monitor_interval)

    async def stop(self):
        """Stop the mosaic manager."""
        self.running = False
        logger.info("Stopping StreamingMosaicManager")

        # Wait for active tasks?
        if self._processing_tasks:
            await asyncio.gather(*self._processing_tasks, return_exceptions=True)

    async def _process_cycle(self):
        """Run one processing cycle."""
        # 1. Discover new files
        new_files = self._discover_files()

        for file_path in new_files:
            # Respect concurrency limit
            if len(self._processing_tasks) >= self._max_concurrent:
                # Wait for at least one task to finish
                done, pending = await asyncio.wait(
                    self._processing_tasks, return_when=asyncio.FIRST_COMPLETED
                )
                self._processing_tasks = pending

            # Spawn processing task
            task = asyncio.create_task(self._process_file(file_path))
            self._processing_tasks.add(task)
            task.add_done_callback(self._processing_tasks.discard)

            self.processed_files.add(file_path)

    def _discover_files(self) -> List[Path]:
        """Discover new files in input directory."""
        input_dir = Path(self.config.paths.input_dir)
        pattern = "*.hdf5"  # or whatever the format is

        found = []
        for p in input_dir.glob(pattern):
            if p not in self.processed_files:
                found.append(p)

        return sorted(found)

    async def _process_file(self, file_path: Path):
        """Process a single file through the pipeline.

        Current implementation runs stages locally in sequence.
        """
        logger.info(f"Processing file: {file_path}")

        try:
            # Stage 1: Conversion
            ms_path = await self._run_conversion(file_path)

            # Stage 2: Calibration Solve
            cal_tables = await self._run_calibration_solve(ms_path)

            # Stage 3: Calibration Apply
            cal_ms_path = await self._run_calibration_apply(ms_path, cal_tables)

            # Stage 4: Imaging
            image_path = await self._run_imaging(cal_ms_path)

            logger.info(f"Finished processing {file_path} -> {image_path}")

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}", exc_info=True)

    async def _run_conversion(self, uvh5_path: Path) -> Path:
        # ... local execution logic ...
        stage = ConversionStage(self.config)
        context = PipelineContext(self.config, inputs={"input_path": str(uvh5_path)})
        result = await asyncio.to_thread(stage.execute, context)
        return Path(result.outputs["ms_path"])

    # ... other local run methods ...
