"""
Unit tests for OrganizationStage.

Tests the file organization pipeline stage including:
- Input validation (ms_path/ms_paths existence)
- File movement to organized directories
- Database path updates
- Calibrator vs science classification
- Error handling for missing files
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.pipeline.config import (
    PathsConfig,
    PipelineConfig,
)
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import OrganizationStage


class TestOrganizationStageValidation:
    """Test OrganizationStage validation."""

    def test_validate_missing_ms_path(self):
        """Test validation fails when no MS files in context."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(config=config)
        stage = OrganizationStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "no ms" in error_msg.lower()

    def test_validate_output_dir_not_exists(self):
        """Test validation fails when output directory doesn't exist."""
        config = PipelineConfig(
            paths=PathsConfig(
                input_dir=Path("/input"),
                output_dir=Path("/nonexistent/output"),
            )
        )
        context = PipelineContext(
            config=config,
            outputs={"ms_path": "/some/file.ms"},
        )
        stage = OrganizationStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "does not exist" in error_msg.lower()

    def test_validate_with_ms_path(self):
        """Test validation succeeds with ms_path and existing output dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            # Create a products_db file to satisfy validation
            products_db = output_dir / "products.sqlite3"
            products_db.touch()

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                    products_db=products_db,
                )
            )
            context = PipelineContext(
                config=config,
                outputs={"ms_path": "/some/file.ms"},
            )
            stage = OrganizationStage(config)

            is_valid, error_msg = stage.validate(context)
            assert is_valid
            assert error_msg is None

    def test_validate_with_ms_paths(self):
        """Test validation succeeds with ms_paths list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            # Create a products_db file to satisfy validation
            products_db = output_dir / "products.sqlite3"
            products_db.touch()

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                    products_db=products_db,
                )
            )
            context = PipelineContext(
                config=config,
                outputs={"ms_paths": ["/some/file1.ms", "/some/file2.ms"]},
            )
            stage = OrganizationStage(config)

            is_valid, error_msg = stage.validate(context)
            assert is_valid
            assert error_msg is None

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        stage = OrganizationStage(config)
        assert stage.get_name() == "organization"


class TestOrganizationStageExecution:
    """Test OrganizationStage execution."""

    def test_execute_no_ms_files(self):
        """Test execution with empty ms_paths returns unchanged context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                )
            )
            context = PipelineContext(
                config=config,
                outputs={"ms_paths": []},
            )
            stage = OrganizationStage(config)

            result = stage.execute(context)

            # Context unchanged when no files
            assert result.outputs.get("ms_paths") == [] or "ms_paths" not in result.outputs

    @patch("dsa110_contimg.pipeline.stages_impl.determine_ms_type")
    @patch("dsa110_contimg.pipeline.stages_impl.organize_ms_file")
    def test_execute_organizes_science_ms(self, mock_organize, mock_determine_type):
        """Test execution organizes science MS files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            products_db = output_dir / "products.sqlite3"
            products_db.touch()

            # Create a fake MS directory
            ms_path = output_dir / "test.ms"
            ms_path.mkdir()
            (ms_path / "table.dat").touch()

            organized_path = output_dir / "science" / "2025-01-01" / "test.ms"

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                    products_db=products_db,
                )
            )

            # Mock: science MS (not calibrator, not failed)
            mock_determine_type.return_value = (False, False)
            mock_organize.return_value = organized_path

            context = PipelineContext(
                config=config,
                outputs={"ms_path": str(ms_path)},
            )
            stage = OrganizationStage(config)

            result = stage.execute(context)

            mock_determine_type.assert_called_once()
            mock_organize.assert_called_once()
            assert result.outputs["ms_path"] == str(organized_path)

    @patch("dsa110_contimg.pipeline.stages_impl.determine_ms_type")
    @patch("dsa110_contimg.pipeline.stages_impl.organize_ms_file")
    def test_execute_organizes_calibrator_ms(self, mock_organize, mock_determine_type):
        """Test execution organizes calibrator MS files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            products_db = output_dir / "products.sqlite3"
            products_db.touch()

            # Create a fake MS directory
            ms_path = output_dir / "3C286.ms"
            ms_path.mkdir()

            organized_path = output_dir / "calibrators" / "2025-01-01" / "3C286.ms"

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                    products_db=products_db,
                )
            )

            # Mock: calibrator MS
            mock_determine_type.return_value = (True, False)
            mock_organize.return_value = organized_path

            context = PipelineContext(
                config=config,
                outputs={"ms_path": str(ms_path)},
            )
            stage = OrganizationStage(config)

            result = stage.execute(context)

            # Verify calibrator flag passed
            call_kwargs = mock_organize.call_args[1]
            assert call_kwargs["is_calibrator"] is True
            assert call_kwargs["is_failed"] is False

    def test_execute_handles_nonexistent_ms(self):
        """Test execution handles non-existent MS files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                )
            )

            # MS file doesn't exist
            context = PipelineContext(
                config=config,
                outputs={"ms_path": "/nonexistent/file.ms"},
            )
            stage = OrganizationStage(config)

            result = stage.execute(context)

            # Should return original path when file doesn't exist
            assert "/nonexistent/file.ms" in result.outputs.get("ms_paths", [])

    @patch("dsa110_contimg.pipeline.stages_impl.determine_ms_type")
    def test_execute_without_products_db(self, mock_determine_type):
        """Test execution works without products database (fallback path)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create a fake MS directory
            ms_path = output_dir / "test.ms"
            ms_path.mkdir()
            (ms_path / "table.dat").touch()

            # Don't create products_db - test fallback behavior
            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                    # products_db not specified
                )
            )

            mock_determine_type.return_value = (False, False)

            context = PipelineContext(
                config=config,
                outputs={"ms_path": str(ms_path)},
            )
            stage = OrganizationStage(config)

            with patch(
                "dsa110_contimg.pipeline.stages_impl.get_organized_ms_path"
            ) as mock_get_path:
                organized_path = output_dir / "science" / "2025-01-01" / "test.ms"
                organized_path.parent.mkdir(parents=True, exist_ok=True)
                mock_get_path.return_value = organized_path

                # This uses the fallback path without products_db
                result = stage.execute(context)

                # Should still attempt organization
                mock_get_path.assert_called_once()


class TestOrganizationStageOutputValidation:
    """Test output validation for OrganizationStage."""

    def test_validate_outputs_no_paths(self):
        """Test output validation fails when no paths."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(config=config)
        stage = OrganizationStage(config)

        is_valid, error_msg = stage.validate_outputs(context)
        assert not is_valid
        assert "no organized" in error_msg.lower()

    def test_validate_outputs_file_not_exists(self):
        """Test output validation fails when file doesn't exist."""
        config = PipelineConfig(
            paths=PathsConfig(input_dir=Path("/input"), output_dir=Path("/output"))
        )
        context = PipelineContext(
            config=config,
            outputs={"ms_paths": ["/nonexistent/organized.ms"]},
        )
        stage = OrganizationStage(config)

        is_valid, error_msg = stage.validate_outputs(context)
        assert not is_valid
        assert "does not exist" in error_msg.lower()

    def test_validate_outputs_success(self):
        """Test output validation succeeds with existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            organized_ms = output_dir / "science" / "2025-01-01" / "test.ms"
            organized_ms.mkdir(parents=True)

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                )
            )
            context = PipelineContext(
                config=config,
                outputs={"ms_paths": [str(organized_ms)]},
            )
            stage = OrganizationStage(config)

            is_valid, error_msg = stage.validate_outputs(context)
            assert is_valid
            assert error_msg is None


class TestOrganizationStageMultipleFiles:
    """Test OrganizationStage with multiple MS files."""

    @patch("dsa110_contimg.pipeline.stages_impl.determine_ms_type")
    @patch("dsa110_contimg.pipeline.stages_impl.organize_ms_file")
    def test_execute_multiple_ms_files(self, mock_organize, mock_determine_type):
        """Test execution organizes multiple MS files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            products_db = output_dir / "products.sqlite3"
            products_db.touch()

            # Create fake MS directories
            ms1 = output_dir / "obs1.ms"
            ms2 = output_dir / "obs2.ms"
            ms1.mkdir()
            ms2.mkdir()

            organized1 = output_dir / "science" / "2025-01-01" / "obs1.ms"
            organized2 = output_dir / "science" / "2025-01-01" / "obs2.ms"

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                    products_db=products_db,
                )
            )

            mock_determine_type.return_value = (False, False)
            mock_organize.side_effect = [organized1, organized2]

            context = PipelineContext(
                config=config,
                outputs={"ms_paths": [str(ms1), str(ms2)]},
            )
            stage = OrganizationStage(config)

            result = stage.execute(context)

            assert len(result.outputs["ms_paths"]) == 2
            assert str(organized1) in result.outputs["ms_paths"]
            assert str(organized2) in result.outputs["ms_paths"]

    @patch("dsa110_contimg.pipeline.stages_impl.determine_ms_type")
    @patch("dsa110_contimg.pipeline.stages_impl.organize_ms_file")
    def test_execute_mixed_calibrator_science(self, mock_organize, mock_determine_type):
        """Test execution handles mixed calibrator and science files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            products_db = output_dir / "products.sqlite3"
            products_db.touch()

            # Create fake MS directories
            cal_ms = output_dir / "3C286.ms"
            sci_ms = output_dir / "target.ms"
            cal_ms.mkdir()
            sci_ms.mkdir()

            organized_cal = output_dir / "calibrators" / "2025-01-01" / "3C286.ms"
            organized_sci = output_dir / "science" / "2025-01-01" / "target.ms"

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                    products_db=products_db,
                )
            )

            # First call: calibrator, second call: science
            mock_determine_type.side_effect = [(True, False), (False, False)]
            mock_organize.side_effect = [organized_cal, organized_sci]

            context = PipelineContext(
                config=config,
                outputs={"ms_paths": [str(cal_ms), str(sci_ms)]},
            )
            stage = OrganizationStage(config)

            result = stage.execute(context)

            assert len(result.outputs["ms_paths"]) == 2
            # Verify both paths organized
            assert str(organized_cal) in result.outputs["ms_paths"]
            assert str(organized_sci) in result.outputs["ms_paths"]


class TestOrganizationStageErrorHandling:
    """Test error handling in OrganizationStage."""

    @patch("dsa110_contimg.pipeline.stages_impl.determine_ms_type")
    @patch("dsa110_contimg.pipeline.stages_impl.organize_ms_file")
    def test_execute_handles_organize_error(self, mock_organize, mock_determine_type):
        """Test execution handles errors during organization gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            products_db = output_dir / "products.sqlite3"
            products_db.touch()

            ms_path = output_dir / "test.ms"
            ms_path.mkdir()

            config = PipelineConfig(
                paths=PathsConfig(
                    input_dir=Path("/input"),
                    output_dir=output_dir,
                    products_db=products_db,
                )
            )

            mock_determine_type.return_value = (False, False)
            mock_organize.side_effect = Exception("Organization failed")

            context = PipelineContext(
                config=config,
                outputs={"ms_path": str(ms_path)},
            )
            stage = OrganizationStage(config)

            # Should not raise, but return original path
            result = stage.execute(context)

            # When organization fails, we expect original path in output
            # The stage catches exceptions and logs them, returning original path
            assert str(ms_path) in result.outputs.get("ms_paths", [str(ms_path)])
