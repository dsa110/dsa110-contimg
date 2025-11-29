#!/usr/bin/env python
# mypy: disable-error-code="import-not-found,import-untyped"
"""
Smoke tests for Absurd mosaic and task chaining features.

Tests:
1. Task chaining imports and structure
2. Housekeeping function structure
3. Streaming bridge initialization
4. DLQ API router registration
5. WebSocket event wiring
"""

import sys
from pathlib import Path

import pytest  # type: ignore[import-not-found]

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))  # noqa: E402


@pytest.mark.smoke
class TestMosaicImports:
    """Verify mosaic and chaining imports work correctly."""

    def test_task_chain_imports(self):
        """Test TaskChain and chain imports."""
        from dsa110_contimg.absurd import (
            CALIBRATOR_CHAIN,
            QUICK_IMAGING_CHAIN,
            STANDARD_PIPELINE_CHAIN,
            TARGET_CHAIN,
            TaskChain,
            execute_chained_task,
        )

        assert TaskChain is not None
        assert STANDARD_PIPELINE_CHAIN is not None
        assert QUICK_IMAGING_CHAIN is not None
        assert CALIBRATOR_CHAIN is not None
        assert TARGET_CHAIN is not None
        assert callable(execute_chained_task)
        print("✓ Task chaining imports successful")

    def test_housekeeping_import(self):
        """Test housekeeping function import."""
        from dsa110_contimg.absurd import execute_housekeeping

        assert callable(execute_housekeeping)
        print("✓ Housekeeping import successful")

    def test_streaming_bridge_import(self):
        """Test AbsurdStreamingBridge import."""
        from dsa110_contimg.absurd import AbsurdStreamingBridge

        assert AbsurdStreamingBridge is not None
        print("✓ Streaming bridge import successful")

    def test_websocket_manager_import(self):
        """Test WebSocket manager and worker integration imports."""
        from dsa110_contimg.absurd import set_websocket_manager
        from dsa110_contimg.absurd.worker import emit_queue_stats_update, emit_task_update

        assert callable(set_websocket_manager)
        assert callable(emit_task_update)
        assert callable(emit_queue_stats_update)
        print("✓ WebSocket manager imports successful")


@pytest.mark.smoke
class TestChainStructure:
    """Verify chain structure is correct."""

    def test_standard_chain_order(self):
        """Test STANDARD_PIPELINE_CHAIN has correct task order."""
        from dsa110_contimg.absurd import STANDARD_PIPELINE_CHAIN

        tasks = STANDARD_PIPELINE_CHAIN.tasks

        # Verify key tasks exist
        assert "convert-uvh5-to-ms" in tasks
        assert "calibration-solve" in tasks
        assert "calibration-apply" in tasks
        assert "imaging" in tasks

        # Verify order
        conv_idx = tasks.index("convert-uvh5-to-ms")
        solve_idx = tasks.index("calibration-solve")
        assert conv_idx < solve_idx
        assert solve_idx < tasks.index("calibration-apply")
        assert tasks.index("calibration-apply") < tasks.index("imaging")
        print("✓ Standard chain order verified")

    def test_quick_imaging_chain_skips_solve(self):
        """Test QUICK_IMAGING_CHAIN skips calibration-solve."""
        from dsa110_contimg.absurd import QUICK_IMAGING_CHAIN

        tasks = QUICK_IMAGING_CHAIN.tasks

        assert "convert-uvh5-to-ms" in tasks
        assert "calibration-apply" in tasks
        assert "imaging" in tasks
        assert "calibration-solve" not in tasks
        print("✓ Quick imaging chain verified (skips solve)")


@pytest.mark.smoke
class TestStreamingBridge:
    """Verify streaming bridge can be instantiated."""

    def test_bridge_instantiation(self):
        """Test AbsurdStreamingBridge can be instantiated."""
        from unittest.mock import MagicMock

        from dsa110_contimg.absurd import AbsurdStreamingBridge

        mock_client = MagicMock()
        bridge = AbsurdStreamingBridge(
            absurd_client=mock_client,
            queue_name="test-queue",
        )

        assert bridge.client == mock_client
        assert bridge.queue_name == "test-queue"
        print("✓ Streaming bridge instantiation successful")


@pytest.mark.smoke
class TestDLQRouter:
    """Verify DLQ router is correctly structured."""

    def test_dlq_router_exists(self):
        """Test DLQ router module exists and has endpoints."""
        from dsa110_contimg.api.routers.dlq import router

        assert router is not None

        # Check router has routes
        routes = [route.path for route in router.routes]

        assert "/items" in routes or any("/items" in r for r in routes)
        assert "/stats" in routes or any("/stats" in r for r in routes)
        print("✓ DLQ router exists with expected endpoints")

    def test_dlq_models_exist(self):
        """Test DLQ Pydantic models exist."""
        from dsa110_contimg.api.routers.dlq import (
            DLQActionRequest,
            DLQItemResponse,
            DLQListResponse,
            DLQRetryRequest,
            DLQStatsResponse,
        )

        assert DLQItemResponse is not None
        assert DLQListResponse is not None
        assert DLQStatsResponse is not None
        assert DLQActionRequest is not None
        assert DLQRetryRequest is not None
        print("✓ DLQ models exist")


@pytest.mark.smoke
class TestDeadLetterQueue:
    """Verify DeadLetterQueue has required methods."""

    def test_dlq_has_required_methods(self):
        """Test DeadLetterQueue has all required methods."""
        from dsa110_contimg.pipeline.dead_letter_queue import DeadLetterQueue

        dlq_methods = dir(DeadLetterQueue)

        # Required methods
        assert "get_by_id" in dlq_methods
        assert "delete" in dlq_methods
        assert "resolve" in dlq_methods
        assert "get_stats" in dlq_methods

        # Existing methods
        assert "add" in dlq_methods
        assert "get_pending" in dlq_methods
        assert "mark_retrying" in dlq_methods
        assert "mark_failed" in dlq_methods
        print("✓ DeadLetterQueue has all required methods")


@pytest.mark.smoke
class TestMosaicIntegration:
    """Integration-level smoke tests."""

    def test_absurd_package_exports(self):
        """Test all chaining exports from absurd package."""
        from dsa110_contimg import absurd

        # Verify __all__ exports
        exports = absurd.__all__

        chaining_exports = [
            "AbsurdStreamingBridge",
            "TaskChain",
            "execute_chained_task",
            "execute_housekeeping",
            "set_websocket_manager",
            "STANDARD_PIPELINE_CHAIN",
            "QUICK_IMAGING_CHAIN",
            "CALIBRATOR_CHAIN",
            "TARGET_CHAIN",
        ]

        for export in chaining_exports:
            assert export in exports, f"Missing export: {export}"

        print(f"✓ All {len(chaining_exports)} chaining exports present")

    def test_task_chain_dataclass(self):
        """Test TaskChain is a proper dataclass."""
        from dataclasses import is_dataclass

        from dsa110_contimg.absurd import TaskChain

        assert is_dataclass(TaskChain)

        # Create instance
        chain = TaskChain(
            name="test",
            tasks=["a", "b", "c"],
        )

        assert chain.name == "test"
        assert len(chain.tasks) == 3
        print("✓ TaskChain is a valid dataclass")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "smoke"])
