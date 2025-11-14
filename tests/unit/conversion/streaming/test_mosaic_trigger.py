"""Unit tests for mosaic creation trigger in streaming converter.

Tests the mosaic creation trigger functionality with focus on:
- Fast execution (mocked orchestrator)
- Accurate targeting of trigger logic
- Error handling and edge cases
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.conversion.streaming.streaming_converter import (
    trigger_group_mosaic_creation,
)


class TestTriggerGroupMosaicCreation:
    """Test mosaic creation trigger logic."""

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator")
    def test_successful_mosaic_creation(self, mock_orch_class, tmp_path):
        """Test successful mosaic creation from group."""
        mock_orch = MagicMock()
        mock_orch._form_group_from_ms_paths.return_value = True
        mock_orch._process_group_workflow.return_value = "/stage/mosaics/mosaic_test.fits"
        mock_orch_class.return_value = mock_orch

        ms_paths = [f"/stage/ms/2025-11-12T10:{i:02d}:00.ms" for i in range(10)]
        products_db = tmp_path / "products.sqlite3"
        mock_args = MagicMock()

        result = trigger_group_mosaic_creation(ms_paths, products_db, mock_args)

        assert result == "/stage/mosaics/mosaic_test.fits"
        mock_orch._form_group_from_ms_paths.assert_called_once()
        mock_orch._process_group_workflow.assert_called_once()

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator")
    def test_group_formation_failure(self, mock_orch_class, tmp_path):
        """Test handling of group formation failure."""
        mock_orch = MagicMock()
        mock_orch._form_group_from_ms_paths.return_value = False
        mock_orch_class.return_value = mock_orch

        ms_paths = [f"/stage/ms/2025-11-12T10:{i:02d}:00.ms" for i in range(10)]
        products_db = tmp_path / "products.sqlite3"
        mock_args = MagicMock()

        result = trigger_group_mosaic_creation(ms_paths, products_db, mock_args)

        assert result is None
        mock_orch._form_group_from_ms_paths.assert_called_once()
        mock_orch._process_group_workflow.assert_not_called()

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator")
    def test_mosaic_workflow_failure(self, mock_orch_class, tmp_path):
        """Test handling of mosaic workflow failure."""
        mock_orch = MagicMock()
        mock_orch._form_group_from_ms_paths.return_value = True
        mock_orch._process_group_workflow.return_value = None
        mock_orch_class.return_value = mock_orch

        ms_paths = [f"/stage/ms/2025-11-12T10:{i:02d}:00.ms" for i in range(10)]
        products_db = tmp_path / "products.sqlite3"
        mock_args = MagicMock()

        result = trigger_group_mosaic_creation(ms_paths, products_db, mock_args)

        assert result is None
        mock_orch._form_group_from_ms_paths.assert_called_once()
        mock_orch._process_group_workflow.assert_called_once()

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator")
    def test_group_id_generation_from_timestamp(self, mock_orch_class, tmp_path):
        """Test group ID generation from MS timestamp."""
        mock_orch = MagicMock()
        mock_orch._form_group_from_ms_paths.return_value = True
        mock_orch._process_group_workflow.return_value = "/stage/mosaics/mosaic.fits"
        mock_orch_class.return_value = mock_orch

        # MS paths with timestamp in filename
        ms_paths = [f"/stage/ms/2025-11-12T10:{i:02d}:00.ms" for i in range(10)]
        products_db = tmp_path / "products.sqlite3"
        mock_args = MagicMock()

        result = trigger_group_mosaic_creation(ms_paths, products_db, mock_args)

        assert result is not None
        # Verify group_id was generated from timestamp
        call_args = mock_orch._form_group_from_ms_paths.call_args
        assert call_args[0][1].startswith("mosaic_2025-11-12")

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator")
    def test_group_id_fallback_to_hash(self, mock_orch_class, tmp_path):
        """Test group ID fallback to hash when timestamp not found."""
        mock_orch = MagicMock()
        mock_orch._form_group_from_ms_paths.return_value = True
        mock_orch._process_group_workflow.return_value = "/stage/mosaics/mosaic.fits"
        mock_orch_class.return_value = mock_orch

        # MS paths without timestamp in filename
        ms_paths = [f"/stage/ms/ms_{i}.ms" for i in range(10)]
        products_db = tmp_path / "products.sqlite3"
        mock_args = MagicMock()

        result = trigger_group_mosaic_creation(ms_paths, products_db, mock_args)

        assert result is not None
        # Verify group_id was generated from hash
        call_args = mock_orch._form_group_from_ms_paths.call_args
        assert call_args[0][1].startswith("mosaic_")

    @patch("dsa110_contimg.mosaic.orchestrator.MosaicOrchestrator")
    def test_exception_handling(self, mock_orch_class, tmp_path):
        """Test exception handling in mosaic creation."""
        mock_orch = MagicMock()
        mock_orch._form_group_from_ms_paths.side_effect = Exception("Test error")
        mock_orch_class.return_value = mock_orch

        ms_paths = [f"/stage/ms/2025-11-12T10:{i:02d}:00.ms" for i in range(10)]
        products_db = tmp_path / "products.sqlite3"
        mock_args = MagicMock()

        result = trigger_group_mosaic_creation(ms_paths, products_db, mock_args)

        assert result is None
