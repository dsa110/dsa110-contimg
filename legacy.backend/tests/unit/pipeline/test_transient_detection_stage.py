"""
Unit tests for TransientDetectionStage.

Tests the transient detection pipeline stage including:
- Input validation (detected_sources, enabled/disabled)
- Transient detection logic (new, variable, fading sources)
- Alert generation
- Edge cases (no sources, no baseline matches)
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dsa110_contimg.pipeline.config import (
    PathsConfig,
    PipelineConfig,
    TransientDetectionConfig,
)
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import TransientDetectionStage


class TestTransientDetectionStageValidation:
    """Test TransientDetectionStage validation."""

    def test_validate_stage_disabled(self):
        """Test validation fails when stage is disabled."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
            transient_detection=TransientDetectionConfig(enabled=False),
        )
        context = PipelineContext(config=config)
        stage = TransientDetectionStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "disabled" in error_msg.lower()

    def test_validate_missing_detected_sources(self):
        """Test validation fails when detected_sources is missing."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
            transient_detection=TransientDetectionConfig(enabled=True),
        )
        context = PipelineContext(config=config)
        stage = TransientDetectionStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "detected sources" in error_msg.lower()

    def test_validate_with_detected_sources(self):
        """Test validation succeeds with detected_sources."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
            transient_detection=TransientDetectionConfig(enabled=True),
        )
        detected_sources = pd.DataFrame({
            "ra_deg": [180.0, 180.1],
            "dec_deg": [30.0, 30.1],
            "flux_mjy": [10.0, 20.0],
        })
        context = PipelineContext(
            config=config,
            outputs={"detected_sources": detected_sources},
        )
        stage = TransientDetectionStage(config)

        is_valid, error_msg = stage.validate(context)
        assert is_valid
        assert error_msg is None

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
        )
        stage = TransientDetectionStage(config)
        assert stage.get_name() == "transient_detection"


class TestTransientDetectionStageExecution:
    """Test TransientDetectionStage execution."""

    @patch("dsa110_contimg.catalog.query.query_sources")
    @patch("dsa110_contimg.catalog.transient_detection.detect_transients")
    @patch("dsa110_contimg.catalog.transient_detection.create_transient_detection_tables")
    @patch("dsa110_contimg.catalog.transient_detection.store_transient_candidates")
    @patch("dsa110_contimg.catalog.transient_detection.generate_transient_alerts")
    def test_execute_with_transients_found(
        self,
        mock_generate_alerts,
        mock_store_candidates,
        mock_create_tables,
        mock_detect_transients,
        mock_query_sources,
    ):
        """Test execution when transients are found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=Path("/output"),
                    state_dir=state_dir,
                ),
                transient_detection=TransientDetectionConfig(
                    enabled=True,
                    baseline_catalog="NVSS",
                ),
            )

            detected_sources = pd.DataFrame({
                "ra_deg": [180.0, 180.1, 180.2],
                "dec_deg": [30.0, 30.1, 30.2],
                "flux_mjy": [10.0, 20.0, 30.0],
                "flux_err_mjy": [1.0, 2.0, 3.0],
            })

            # Mock baseline catalog response
            mock_query_sources.return_value = pd.DataFrame({
                "ra_deg": [180.0],
                "dec_deg": [30.0],
                "flux_mjy": [5.0],  # Different flux = variable
            })

            # Mock transient detection results
            new_source = {"ra_deg": 180.2, "dec_deg": 30.2, "type": "new"}
            variable_source = {"ra_deg": 180.0, "dec_deg": 30.0, "type": "variable"}
            mock_detect_transients.return_value = (
                [new_source],  # new sources
                [variable_source],  # variable sources
                [],  # fading sources
            )

            mock_store_candidates.return_value = [1, 2]  # candidate IDs
            mock_generate_alerts.return_value = [101]  # alert IDs

            context = PipelineContext(
                config=config,
                outputs={"detected_sources": detected_sources},
            )
            stage = TransientDetectionStage(config)

            result = stage.execute(context)

            # Verify results
            assert "transient_results" in result.outputs
            results = result.outputs["transient_results"]
            assert results["n_new"] == 1
            assert results["n_variable"] == 1
            assert results["n_fading"] == 0
            assert results["candidate_ids"] == [1, 2]
            assert result.outputs["alert_ids"] == [101]

            # Verify mocks called correctly
            mock_create_tables.assert_called_once()
            mock_query_sources.assert_called_once()
            mock_detect_transients.assert_called_once()
            mock_store_candidates.assert_called_once()
            mock_generate_alerts.assert_called_once()

    def test_execute_stage_disabled(self):
        """Test execution returns early when disabled."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
            transient_detection=TransientDetectionConfig(enabled=False),
        )
        context = PipelineContext(config=config)
        stage = TransientDetectionStage(config)

        result = stage.execute(context)

        assert result.outputs.get("transient_status") == "disabled"

    @patch("dsa110_contimg.catalog.transient_detection.create_transient_detection_tables")
    def test_execute_no_detected_sources(self, mock_create_tables):
        """Test execution with empty detected sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=Path("/output"),
                    state_dir=state_dir,
                ),
                transient_detection=TransientDetectionConfig(enabled=True),
            )

            # Empty detected sources
            detected_sources = pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

            context = PipelineContext(
                config=config,
                outputs={"detected_sources": detected_sources},
            )
            stage = TransientDetectionStage(config)

            result = stage.execute(context)

            assert result.outputs.get("transient_status") == "skipped_no_sources"


class TestTransientDetectionStageEdgeCases:
    """Test edge cases for TransientDetectionStage."""

    @patch("dsa110_contimg.catalog.query.query_sources")
    @patch("dsa110_contimg.catalog.transient_detection.detect_transients")
    @patch("dsa110_contimg.catalog.transient_detection.create_transient_detection_tables")
    @patch("dsa110_contimg.catalog.transient_detection.store_transient_candidates")
    @patch("dsa110_contimg.catalog.transient_detection.generate_transient_alerts")
    def test_execute_no_baseline_sources(
        self,
        mock_generate_alerts,
        mock_store_candidates,
        mock_create_tables,
        mock_detect_transients,
        mock_query_sources,
    ):
        """Test execution when baseline catalog returns no sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=Path("/output"),
                    state_dir=state_dir,
                ),
                transient_detection=TransientDetectionConfig(enabled=True),
            )

            detected_sources = pd.DataFrame({
                "ra_deg": [180.0],
                "dec_deg": [30.0],
                "flux_mjy": [10.0],
            })

            # No baseline sources found
            mock_query_sources.return_value = None

            # All detected sources are "new"
            mock_detect_transients.return_value = (
                [{"ra_deg": 180.0, "dec_deg": 30.0, "type": "new"}],
                [],
                [],
            )
            mock_store_candidates.return_value = [1]
            mock_generate_alerts.return_value = []

            context = PipelineContext(
                config=config,
                outputs={"detected_sources": detected_sources},
            )
            stage = TransientDetectionStage(config)

            result = stage.execute(context)

            assert "transient_results" in result.outputs
            assert result.outputs["transient_results"]["n_new"] == 1

    @patch("dsa110_contimg.catalog.query.query_sources")
    @patch("dsa110_contimg.catalog.transient_detection.detect_transients")
    @patch("dsa110_contimg.catalog.transient_detection.create_transient_detection_tables")
    @patch("dsa110_contimg.catalog.transient_detection.store_transient_candidates")
    @patch("dsa110_contimg.catalog.transient_detection.generate_transient_alerts")
    def test_execute_with_mosaic_id(
        self,
        mock_generate_alerts,
        mock_store_candidates,
        mock_create_tables,
        mock_detect_transients,
        mock_query_sources,
    ):
        """Test execution passes mosaic_id to storage function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=Path("/output"),
                    state_dir=state_dir,
                ),
                transient_detection=TransientDetectionConfig(enabled=True),
            )

            detected_sources = pd.DataFrame({
                "ra_deg": [180.0],
                "dec_deg": [30.0],
                "flux_mjy": [10.0],
            })

            mock_query_sources.return_value = pd.DataFrame()
            mock_detect_transients.return_value = ([], [], [])
            mock_store_candidates.return_value = []
            mock_generate_alerts.return_value = []

            context = PipelineContext(
                config=config,
                outputs={
                    "detected_sources": detected_sources,
                    "mosaic_id": 42,
                },
            )
            stage = TransientDetectionStage(config)

            stage.execute(context)

            # Verify mosaic_id was passed
            call_kwargs = mock_store_candidates.call_args
            assert call_kwargs[1]["mosaic_id"] == 42

    def test_cleanup_does_nothing(self):
        """Test cleanup is a no-op (no resources to clean)."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output")),
        )
        context = PipelineContext(config=config)
        stage = TransientDetectionStage(config)

        # Should not raise
        stage.cleanup(context)


class TestTransientDetectionThresholds:
    """Test threshold configuration for TransientDetectionStage."""

    @patch("dsa110_contimg.catalog.query.query_sources")
    @patch("dsa110_contimg.catalog.transient_detection.detect_transients")
    @patch("dsa110_contimg.catalog.transient_detection.create_transient_detection_tables")
    @patch("dsa110_contimg.catalog.transient_detection.store_transient_candidates")
    @patch("dsa110_contimg.catalog.transient_detection.generate_transient_alerts")
    def test_thresholds_passed_to_detector(
        self,
        mock_generate_alerts,
        mock_store_candidates,
        mock_create_tables,
        mock_detect_transients,
        mock_query_sources,
    ):
        """Test that configured thresholds are passed to detect_transients."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=Path("/output"),
                    state_dir=state_dir,
                ),
                transient_detection=TransientDetectionConfig(
                    enabled=True,
                    detection_threshold_sigma=5.0,
                    variability_threshold_sigma=4.0,
                    match_radius_arcsec=10.0,
                    baseline_catalog="FIRST",
                ),
            )

            detected_sources = pd.DataFrame({
                "ra_deg": [180.0],
                "dec_deg": [30.0],
                "flux_mjy": [10.0],
            })

            mock_query_sources.return_value = pd.DataFrame()
            mock_detect_transients.return_value = ([], [], [])
            mock_store_candidates.return_value = []
            mock_generate_alerts.return_value = []

            context = PipelineContext(
                config=config,
                outputs={"detected_sources": detected_sources},
            )
            stage = TransientDetectionStage(config)

            stage.execute(context)

            # Verify thresholds passed correctly
            call_kwargs = mock_detect_transients.call_args[1]
            assert call_kwargs["detection_threshold_sigma"] == 5.0
            assert call_kwargs["variability_threshold"] == 4.0
            assert call_kwargs["match_radius_arcsec"] == 10.0
            assert call_kwargs["baseline_catalog"] == "FIRST"
