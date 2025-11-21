"""
Absurd-enabled Streaming Mosaic Manager.

This module provides a version of StreamingMosaicManager that uses the Absurd
durable task queue for executing pipeline stages instead of local execution.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dsa110_contimg.absurd.client import AbsurdClient
from dsa110_contimg.absurd.config import AbsurdConfig
from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager
from dsa110_contimg.pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


class AbsurdStreamingMosaicManager(StreamingMosaicManager):
    """Streaming Mosaic Manager using Absurd for execution.

    This class overrides the synchronous execution methods of
    StreamingMosaicManager to offload work to the Absurd task queue.
    It maintains the high-level orchestration logic (grouping, overlap)
    while delegating heavy processing to workers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load Absurd config
        self.absurd_config = AbsurdConfig.from_env()
        self.client = AbsurdClient(self.absurd_config.database_url)
        self._connected = False

    async def ensure_connected(self):
        """Ensure Absurd client is connected."""
        if not self._connected:
            await self.client.connect()
            self._connected = True

    async def _wait_for_task(self, task_id: str, interval: float = 1.0) -> Dict[str, Any]:
        """Wait for an Absurd task to complete.

        Args:
            task_id: Task UUID string
            interval: Polling interval in seconds

        Returns:
            Task result dictionary

        Raises:
            RuntimeError: If task fails or is cancelled
        """
        while True:
            task = await self.client.get_task(task_id)
            if not task:
                raise RuntimeError(f"Task {task_id} vanished from queue")

            status = task["status"]
            if status == "completed":
                return task["result"]
            elif status == "failed":
                error = task.get("error", "Unknown error")
                raise RuntimeError(f"Task {task_id} failed: {error}")
            elif status == "cancelled":
                raise RuntimeError(f"Task {task_id} was cancelled")

            await asyncio.sleep(interval)

    # ----------------------------------------------------------------
    # Overridden Execution Methods (Async Wrappers)
    # ----------------------------------------------------------------
    # Note: The base class calls these synchronously.
    # We must change the Orchestration Logic to be Async to use these.
    # But the base class 'process_next_group' is synchronous.
    #
    # We have to override 'process_next_group' to make it async
    # or wrap these calls.
    # Since we want to make the whole system event-driven eventually,
    # rewriting the orchestration loop to be async is the right path.

    async def process_next_group_async(self, use_sliding_window: bool = True) -> bool:
        """Async version of process_next_group."""
        await self.ensure_connected()

        # Reuse the logic from base class but we can't call it directly
        # because it calls sync methods. We must copy-paste the high-level logic.
        # This is unfortunate but necessary unless we refactor base class.

        if use_sliding_window:
            group_id = self.check_for_sliding_window_group()
        else:
            group_id = self.check_for_new_group()

        if not group_id:
            return False

        logger.info(f"[Absurd] Processing group: {group_id}")

        # Get MS paths
        ms_paths = self.get_group_ms_paths(group_id)
        if len(ms_paths) < self.ms_per_group:
            logger.warning(f"Group {group_id} has only {len(ms_paths)} MS files")
            return False

        # Validate Dec and calibrator registration
        is_valid, dec_deg = self.validate_group_dec(ms_paths)
        if not is_valid:
            logger.error(f"Group {group_id} validation failed: no calibrator registered for Dec")
            return False

        # Get calibrator RA
        bp_cal = self.get_bandpass_calibrator_for_dec(dec_deg)
        calibrator_ra = bp_cal["ra_deg"] if bp_cal else None

        # Select calibration MS
        calibration_ms = self.select_calibration_ms(ms_paths, calibrator_ra=calibrator_ra)
        if not calibration_ms:
            logger.error(f"Could not select calibration MS for group {group_id}")
            return False

        # --- EXECUTION VIA ABSURD ---

        # 1. Calibration Solve
        try:
            bpcal_solved, gaincal_solved, error_msg = await self.solve_calibration_for_group_absurd(
                group_id, calibration_ms, bp_cal
            )
            if error_msg:
                logger.error(f"Calibration solving failed for group {group_id}: {error_msg}")
                return False
        except Exception as e:
            logger.error(f"Absurd task failed: {e}")
            return False

        # 2. Calibration Apply
        try:
            success = await self.apply_calibration_to_group_absurd(group_id)
            if not success:
                logger.error(f"Failed to apply calibration to group {group_id}")
                return False
        except Exception as e:
            logger.error(f"Absurd task failed: {e}")
            return False

        # 3. Image all MS
        try:
            success = await self.image_group_absurd(group_id)
            if not success:
                logger.error(f"Failed to image group {group_id}")
                return False
        except Exception as e:
            logger.error(f"Absurd task failed: {e}")
            return False

        # 4. Create mosaic
        # Currently create_mosaic is fast/local logic + cli call.
        # We can offload it too.
        try:
            mosaic_path = await self.create_mosaic_absurd(group_id)
            if not mosaic_path:
                logger.error(f"Failed to create mosaic for group {group_id}")
                return False
        except Exception as e:
            logger.error(f"Absurd task failed: {e}")
            return False

        logger.info(f"Successfully processed group {group_id}, mosaic: {mosaic_path}")
        return True

    # ----------------------------------------------------------------
    # Absurd Task Wrappers
    # ----------------------------------------------------------------

    async def solve_calibration_for_group_absurd(
        self, group_id: str, calibration_ms: str, bp_cal: Dict[str, Any]
    ) -> Tuple[bool, bool, Optional[str]]:
        """Run calibration solve via Absurd."""
        logger.info(f"Spawning calibration-solve task for {calibration_ms}")

        # Prepare params
        params = {
            "config": None,  # Use defaults/env
            "inputs": {
                "ms_path": calibration_ms,
                "calibrator_info": (
                    {
                        "name": bp_cal["name"],
                        "ra_deg": bp_cal["ra_deg"],
                        "dec_deg": bp_cal["dec_deg"],
                    }
                    if bp_cal
                    else None
                ),
            },
            "priority": 10,
        }

        task_id = await self.client.spawn_task(
            self.absurd_config.queue_name,
            "calibration-solve",
            params,
            priority=10,
            timeout_sec=self.absurd_config.task_timeout_sec,
        )

        logger.info(f"Task spawned: {task_id}")
        result = await self._wait_for_task(task_id)

        # Parse result
        outputs = result.get("outputs", {})
        cal_tables = outputs.get("calibration_tables", {})

        bp_solved = "BP" in cal_tables
        gain_solved = "G" in cal_tables or "GP" in cal_tables

        if not bp_solved and not gain_solved:
            return False, False, "Absurd task returned no tables"

        return bp_solved, gain_solved, None

    async def apply_calibration_to_group_absurd(self, group_id: str) -> bool:
        """Run calibration apply via Absurd for all MS in group."""
        ms_paths = self.get_group_ms_paths(group_id)

        # We need the calibration tables.
        # The base class logic assumes they are on disk at predicted paths.
        # Absurd worker wrote them to disk (shared storage).
        # So we can just iterate ms_paths and spawn tasks.

        tasks = []
        for ms_path in ms_paths:
            # We need to find the tables for this MS (or the group's tables)
            # Base class uses check_registry_for_calibration logic per MS.
            # We can reuse _get_calibration_table_prefix logic?
            # Actually, apply_calibration_to_group in base class iterates and calls `apply_calibration`.
            # We should spawn N tasks in parallel.

            # Simplified: The worker needs the cal table map.
            # We assume the worker (CalibrationStage) can find them if we pass the paths?
            # Or we pass the dict.

            # Base class `apply_calibration_to_group` calls `self.check_registry_for_calibration`.
            # We can do that here.

            # We need the mid_mjd for registry lookup
            # This requires local file access or DB access.
            # We have products_db.

            # Let's use a helper from base class if possible, or reimplement loop.
            # Base class:
            # for ms_path in ms_paths: ... get tables ... apply ...

            # I will replicate the loop logic here roughly
            try:
                from dsa110_contimg.utils.time_utils import extract_ms_time_range

                _, _, mid_mjd = extract_ms_time_range(ms_path)

                reg_tables = self.check_registry_for_calibration(mid_mjd)
                # Convert to flat dict
                cal_tables = {}
                for ttype, paths in reg_tables.items():
                    if paths:
                        cal_tables[ttype] = paths[0]

                if not cal_tables:
                    logger.warning(f"No cal tables for {ms_path}")
                    continue

                params = {
                    "config": None,
                    "outputs": {  # Use outputs to pass paths as expected by adapter
                        "ms_path": ms_path,
                        "calibration_tables": cal_tables,
                    },
                    "priority": 5,
                }

                task_id = await self.client.spawn_task(
                    self.absurd_config.queue_name, "calibration-apply", params
                )
                tasks.append(task_id)

            except Exception as e:
                logger.error(f"Failed to setup apply for {ms_path}: {e}")
                return False

        # Wait for all
        if not tasks:
            return False

        logger.info(f"Waiting for {len(tasks)} apply tasks...")
        for tid in tasks:
            await self._wait_for_task(tid)

        return True

    async def image_group_absurd(self, group_id: str) -> bool:
        """Run imaging via Absurd."""
        ms_paths = self.get_group_ms_paths(group_id)
        tasks = []

        for ms_path in ms_paths:
            params = {"config": None, "outputs": {"ms_path": ms_path}, "priority": 5}
            task_id = await self.client.spawn_task(self.absurd_config.queue_name, "imaging", params)
            tasks.append(task_id)

        logger.info(f"Waiting for {len(tasks)} imaging tasks...")
        for tid in tasks:
            await self._wait_for_task(tid)

        return True

    async def create_mosaic_absurd(self, group_id: str) -> Optional[str]:
        """Run mosaic creation via Absurd (Phase 3c, but we can do it)."""
        # If "create-mosaic" task exists in adapter? No, adapter has 'imaging'.
        # Adapter has 'organize-files', 'catalog-setup'.
        # It does NOT have 'create-mosaic'.
        # So we must run this LOCALLY for now (Hybrid approach).
        logger.info("Running mosaic creation locally (task executor pending)...")
        return self.create_mosaic(group_id)

    async def close(self):
        if self._connected:
            await self.client.close()
