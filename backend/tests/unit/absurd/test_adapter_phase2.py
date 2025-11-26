# mypy: disable-error-code="import-not-found,import-untyped"
"""
Unit tests for Absurd adapter Phase 2 features.

Tests task chaining, housekeeping, and streaming bridge functionality.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest  # type: ignore[import-not-found]

# ============================================================================
# Task Chaining Tests
# ============================================================================


@pytest.mark.unit
class TestTaskChain:
    """Tests for TaskChain dataclass and pre-defined chains."""

    def test_task_chain_creation(self):
        """Test creating a TaskChain."""
        from dsa110_contimg.absurd.adapter import TaskChain  # type: ignore[import-not-found]

        chain = TaskChain(
            name="test-chain",
            tasks=["task1", "task2", "task3"],
        )

        assert chain.name == "test-chain"
        assert len(chain.tasks) == 3
        assert chain.tasks[0] == "task1"

    def test_standard_pipeline_chain(self):
        """Test STANDARD_PIPELINE_CHAIN has correct tasks."""
        from dsa110_contimg.absurd.adapter import STANDARD_PIPELINE_CHAIN

        assert STANDARD_PIPELINE_CHAIN.name == "standard-pipeline"
        assert "convert-uvh5-to-ms" in STANDARD_PIPELINE_CHAIN.tasks
        assert "calibration-solve" in STANDARD_PIPELINE_CHAIN.tasks
        assert "calibration-apply" in STANDARD_PIPELINE_CHAIN.tasks
        assert "imaging" in STANDARD_PIPELINE_CHAIN.tasks
        # Verify order
        conv_idx = STANDARD_PIPELINE_CHAIN.tasks.index("convert-uvh5-to-ms")
        solve_idx = STANDARD_PIPELINE_CHAIN.tasks.index("calibration-solve")
        assert conv_idx < solve_idx

    def test_quick_imaging_chain(self):
        """Test QUICK_IMAGING_CHAIN has correct tasks."""
        from dsa110_contimg.absurd.adapter import QUICK_IMAGING_CHAIN

        assert QUICK_IMAGING_CHAIN.name == "quick-imaging"
        assert "convert-uvh5-to-ms" in QUICK_IMAGING_CHAIN.tasks
        assert "calibration-apply" in QUICK_IMAGING_CHAIN.tasks
        assert "imaging" in QUICK_IMAGING_CHAIN.tasks
        # Should NOT have calibration-solve
        assert "calibration-solve" not in QUICK_IMAGING_CHAIN.tasks

    def test_calibrator_chain(self):
        """Test CALIBRATOR_CHAIN has correct tasks."""
        from dsa110_contimg.absurd.adapter import CALIBRATOR_CHAIN

        assert "calibrator" in CALIBRATOR_CHAIN.name.lower()
        assert "convert-uvh5-to-ms" in CALIBRATOR_CHAIN.tasks
        assert "calibration-solve" in CALIBRATOR_CHAIN.tasks

    def test_target_chain(self):
        """Test TARGET_CHAIN has correct tasks."""
        from dsa110_contimg.absurd.adapter import TARGET_CHAIN

        assert "target" in TARGET_CHAIN.name.lower()
        assert "convert-uvh5-to-ms" in TARGET_CHAIN.tasks
        assert "photometry" in TARGET_CHAIN.tasks

    def test_get_next_task(self):
        """Test get_next_task method."""
        from dsa110_contimg.absurd.adapter import TaskChain

        chain = TaskChain(
            name="test",
            tasks=["task1", "task2", "task3"],
        )

        assert chain.get_next_task("task1") == "task2"
        assert chain.get_next_task("task2") == "task3"
        assert chain.get_next_task("task3") is None
        assert chain.get_next_task("unknown") is None


@pytest.mark.unit
class TestExecuteChainedTask:
    """Tests for execute_chained_task function."""

    @pytest.mark.asyncio
    async def test_spawn_follow_up_task(self):
        """Test that follow-up task is spawned after completion."""
        from dsa110_contimg.absurd.adapter import execute_chained_task

        spawn_callback = AsyncMock(return_value="follow-up-task-id")

        # Mock execute_pipeline_task to return success
        with patch(
            "dsa110_contimg.absurd.adapter.execute_pipeline_task",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {
                "status": "success",
                "outputs": {"ms_path": "/test.ms"},
            }

            result = await execute_chained_task(
                task_name="convert-uvh5-to-ms",
                params={"config": None, "inputs": {}},
                chain_name="standard-pipeline",
                spawn_callback=spawn_callback,
            )

            assert result["status"] == "success"
            # Follow-up task should be spawned
            spawn_callback.assert_called_once()
            # Result should include chain info
            assert "chain_next_task" in result

    @pytest.mark.asyncio
    async def test_no_follow_up_for_last_task(self):
        """Test that no follow-up is spawned for the last task."""
        from dsa110_contimg.absurd.adapter import execute_chained_task

        spawn_callback = AsyncMock()

        with patch(
            "dsa110_contimg.absurd.adapter.execute_pipeline_task",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success", "outputs": {}}

            result = await execute_chained_task(
                task_name="photometry",  # Last task in standard chain
                params={"config": None, "inputs": {}},
                chain_name="standard-pipeline",
                spawn_callback=spawn_callback,
            )

            assert result["status"] == "success"
            # No follow-up should be spawned for last task
            spawn_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_follow_up_on_failure(self):
        """Test that no follow-up is spawned when task fails."""
        from dsa110_contimg.absurd.adapter import execute_chained_task

        spawn_callback = AsyncMock()

        with patch(
            "dsa110_contimg.absurd.adapter.execute_pipeline_task",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {
                "status": "error",
                "errors": ["Something failed"],
            }

            result = await execute_chained_task(
                task_name="convert-uvh5-to-ms",
                params={"config": None, "inputs": {}},
                chain_name="standard-pipeline",
                spawn_callback=spawn_callback,
            )

            assert result["status"] == "error"
            # No follow-up should be spawned on failure
            spawn_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_chain_no_spawn(self):
        """Test that no follow-up is spawned when chain_name is None."""
        from dsa110_contimg.absurd.adapter import execute_chained_task

        spawn_callback = AsyncMock()

        with patch(
            "dsa110_contimg.absurd.adapter.execute_pipeline_task",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"status": "success", "outputs": {}}

            result = await execute_chained_task(
                task_name="convert-uvh5-to-ms",
                params={"config": None, "inputs": {}},
                chain_name=None,  # No chain
                spawn_callback=spawn_callback,
            )

            assert result["status"] == "success"
            # No follow-up for no chain
            spawn_callback.assert_not_called()


# ============================================================================
# Housekeeping Tests
# ============================================================================


@pytest.mark.unit
class TestExecuteHousekeeping:
    """Tests for execute_housekeeping function."""

    @pytest.mark.asyncio
    async def test_housekeeping_success(self):
        """Test successful housekeeping execution."""
        from dsa110_contimg.absurd.adapter import execute_housekeeping

        with (
            patch(
                "dsa110_contimg.absurd.adapter._load_config",
                return_value=Mock(),
            ),
            patch(
                "dsa110_contimg.absurd.adapter._clean_scratch_directories",
                new_callable=AsyncMock,
                return_value={"dirs_cleaned": 5, "bytes_freed": 1024},
            ),
            patch(
                "dsa110_contimg.absurd.adapter._recover_stuck_groups",
                new_callable=AsyncMock,
                return_value=2,
            ),
            patch(
                "dsa110_contimg.absurd.adapter._prune_completed_tasks",
                new_callable=AsyncMock,
                return_value=10,
            ),
        ):
            result = await execute_housekeeping(
                params={
                    "config": None,
                    "inputs": {"clean_scratch": True, "recover_stuck": True},
                }
            )

            assert result["status"] == "success"
            assert result["outputs"]["scratch_dirs_cleaned"] == 5
            assert result["outputs"]["stuck_groups_recovered"] == 2

    @pytest.mark.asyncio
    async def test_housekeeping_failure(self):
        """Test housekeeping handles errors gracefully."""
        from dsa110_contimg.absurd.adapter import execute_housekeeping

        with patch(
            "dsa110_contimg.absurd.adapter._load_config",
            side_effect=Exception("Config load failed"),
        ):
            result = await execute_housekeeping(params={"config": None})

            assert result["status"] == "error"
            assert "Config load failed" in result["message"]


# ============================================================================
# Streaming Bridge Tests
# ============================================================================


@pytest.mark.unit
class TestAbsurdStreamingBridge:
    """Tests for AbsurdStreamingBridge class."""

    @pytest.mark.asyncio
    async def test_submit_group(self):
        """Test submitting a subband group."""
        from dsa110_contimg.absurd.adapter import AbsurdStreamingBridge

        mock_client = AsyncMock()
        mock_client.spawn_task = AsyncMock(return_value="task-123")

        bridge = AbsurdStreamingBridge(
            absurd_client=mock_client,
            queue_name="test-queue",
        )

        task_id = await bridge.submit_group(
            group_id="2025-11-25T12:00:00",
            file_paths=[f"/data/incoming/2025-11-25T12:00:00_sb{i:02d}.hdf5" for i in range(16)],
        )

        assert task_id == "task-123"
        mock_client.spawn_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_calibrator_group_with_priority(self):
        """Test that priority is passed correctly for calibrator groups."""
        from dsa110_contimg.absurd.adapter import AbsurdStreamingBridge

        mock_client = AsyncMock()
        mock_client.spawn_task = AsyncMock(return_value="task-456")

        bridge = AbsurdStreamingBridge(
            absurd_client=mock_client,
            queue_name="test-queue",
        )

        await bridge.submit_group(
            group_id="2025-11-25T12:00:00",
            file_paths=["/data/incoming/test.hdf5"],
            is_calibrator=True,
            priority=20,  # Calibrators get higher priority
        )

        call_args = mock_client.spawn_task.call_args
        # Verify priority was passed correctly
        assert call_args.kwargs.get("priority") == 20
        # Verify chain_name is set to calibrator
        params = call_args.kwargs.get("params", {})
        assert params.get("chain_name") == "calibrator"

    def test_bridge_initialization(self):
        """Test bridge initialization with config."""
        from dsa110_contimg.absurd.adapter import AbsurdStreamingBridge

        mock_client = MagicMock()
        bridge = AbsurdStreamingBridge(
            absurd_client=mock_client,
            queue_name="my-queue",
        )

        assert bridge.client == mock_client
        assert bridge.queue_name == "my-queue"

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """Test that duplicate group submissions are skipped."""
        from dsa110_contimg.absurd.adapter import AbsurdStreamingBridge

        mock_client = AsyncMock()
        mock_client.spawn_task = AsyncMock(return_value="task-123")

        bridge = AbsurdStreamingBridge(
            absurd_client=mock_client,
            queue_name="test-queue",
        )

        # First submission
        task_id1 = await bridge.submit_group(
            group_id="2025-11-25T12:00:00",
            file_paths=["/data/incoming/test.hdf5"],
        )

        # Second submission of same group
        task_id2 = await bridge.submit_group(
            group_id="2025-11-25T12:00:00",
            file_paths=["/data/incoming/test.hdf5"],
        )

        assert task_id1 == "task-123"
        assert task_id2 is None  # Deduplicated
        mock_client.spawn_task.assert_called_once()  # Only one call
