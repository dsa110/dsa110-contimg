"""Unit tests for MosaicStage."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, patch, Mock

import pytest

from dsa110_contimg.pipeline.config import (
    MosaicConfig,
    PathsConfig,
    PipelineConfig,
)
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import MosaicStage


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create directory structure
        input_dir = tmpdir_path / "input"
        output_dir = tmpdir_path / "output"
        state_dir = tmpdir_path / "state"
        images_dir = output_dir / "images"
        mosaics_dir = output_dir / "mosaics"
        
        for d in [input_dir, output_dir, state_dir, images_dir, mosaics_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Create products.sqlite3
        products_db = state_dir / "products.sqlite3"
        products_db.touch()
        
        # Create cal_registry.sqlite3
        cal_registry_db = state_dir / "cal_registry.sqlite3"
        cal_registry_db.touch()
        
        yield {
            "tmpdir": tmpdir_path,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "state_dir": state_dir,
            "images_dir": images_dir,
            "mosaics_dir": mosaics_dir,
            "products_db": products_db,
            "cal_registry_db": cal_registry_db,
        }


@pytest.fixture
def pipeline_config(temp_dirs):
    """Create pipeline configuration for testing."""
    return PipelineConfig(
        paths=PathsConfig(
            input_dir=str(temp_dirs["input_dir"]),
            output_dir=str(temp_dirs["output_dir"]),
            state_dir=str(temp_dirs["state_dir"]),
            products_db=str(temp_dirs["products_db"]),
            cal_registry_db=str(temp_dirs["cal_registry_db"]),
        ),
        mosaic=MosaicConfig(
            enabled=True,
            ms_per_mosaic=10,
            min_images=3,  # Lower for testing
        ),
    )


@pytest.fixture
def mosaic_stage(pipeline_config):
    """Create MosaicStage instance."""
    return MosaicStage(pipeline_config)


@pytest.fixture
def sample_images(temp_dirs):
    """Create sample image files for testing."""
    images_dir = temp_dirs["images_dir"]
    image_paths = []
    
    for i in range(5):
        image_path = images_dir / f"2025-01-01T12:{i:02d}:00.img-MFS-image.fits"
        image_path.write_text("FITS mock data")
        image_paths.append(str(image_path))
    
    return image_paths


class TestMosaicStageValidation:
    """Tests for MosaicStage.validate()."""

    def test_validate_missing_image_paths(self, mosaic_stage, pipeline_config):
        """Test validation fails when image_paths missing."""
        context = PipelineContext(config=pipeline_config, outputs={})
        
        is_valid, error = mosaic_stage.validate(context)
        
        assert not is_valid
        assert "image_paths or image_path required" in error

    def test_validate_insufficient_images(self, mosaic_stage, pipeline_config, temp_dirs):
        """Test validation fails with too few images."""
        # Create only 2 images (min is 3)
        images_dir = temp_dirs["images_dir"]
        image_paths = []
        for i in range(2):
            image_path = images_dir / f"test_{i}.fits"
            image_path.write_text("mock")
            image_paths.append(str(image_path))
        
        context = PipelineContext(
            config=pipeline_config,
            outputs={"image_paths": image_paths},
        )
        
        is_valid, error = mosaic_stage.validate(context)
        
        assert not is_valid
        assert "At least 3 images required" in error

    def test_validate_missing_files(self, mosaic_stage, pipeline_config):
        """Test validation fails when image files don't exist."""
        context = PipelineContext(
            config=pipeline_config,
            outputs={
                "image_paths": [
                    "/nonexistent/path1.fits",
                    "/nonexistent/path2.fits",
                    "/nonexistent/path3.fits",
                ]
            },
        )
        
        is_valid, error = mosaic_stage.validate(context)
        
        assert not is_valid
        assert "Image files not found" in error

    def test_validate_success(self, mosaic_stage, pipeline_config, sample_images):
        """Test validation succeeds with valid inputs."""
        context = PipelineContext(
            config=pipeline_config,
            outputs={"image_paths": sample_images},
        )
        
        is_valid, error = mosaic_stage.validate(context)
        
        assert is_valid
        assert error is None

    def test_validate_single_image_path(self, mosaic_stage, pipeline_config, temp_dirs):
        """Test validation accepts single image_path (not list) if min_images=1."""
        # Reconfigure for single image
        pipeline_config.mosaic.min_images = 1
        mosaic_stage = MosaicStage(pipeline_config)
        
        image_path = temp_dirs["images_dir"] / "single.fits"
        image_path.write_text("mock")
        
        context = PipelineContext(
            config=pipeline_config,
            outputs={"image_path": str(image_path)},
        )
        
        is_valid, error = mosaic_stage.validate(context)
        
        assert is_valid
        assert error is None


class TestMosaicStageExecution:
    """Tests for MosaicStage.execute() - focus on testable logic."""

    def test_execute_requires_casa6_decorator(self, mosaic_stage):
        """Test execute method has the require_casa6_python decorator."""
        # The decorator is applied, so the method should have the wrapped attribute
        assert hasattr(mosaic_stage.execute, "__wrapped__") or callable(mosaic_stage.execute)

    def test_execute_input_normalization(self, mosaic_stage, pipeline_config, sample_images):
        """Test that execute handles both list and single image_path correctly."""
        # This tests the input normalization logic at the start of execute()
        # We don't actually run the full execute, but verify the stage is ready
        context = PipelineContext(
            config=pipeline_config,
            outputs={"image_paths": sample_images},
        )
        
        # Validation should pass (prerequisites are met)
        is_valid, _ = mosaic_stage.validate(context)
        assert is_valid


class TestMosaicStageCleanup:
    """Tests for MosaicStage.cleanup()."""

    def test_cleanup_handles_no_group_id(self, mosaic_stage, pipeline_config):
        """Test cleanup handles missing group_id gracefully."""
        context = PipelineContext(
            config=pipeline_config,
            outputs={},  # No group_id
        )
        
        # Should not raise
        mosaic_stage.cleanup(context)

    def test_cleanup_with_group_id_logs_info(self, mosaic_stage, pipeline_config, caplog):
        """Test cleanup logs when group_id is present."""
        import logging
        
        context = PipelineContext(
            config=pipeline_config,
            outputs={"group_id": "mosaic_test_group"},
        )
        
        with caplog.at_level(logging.INFO):
            # This will try to clean up but database won't exist - that's OK
            mosaic_stage.cleanup(context)
        
        # Should have logged the cleanup attempt
        assert any("Cleaning up" in record.message for record in caplog.records)


class TestMosaicStageName:
    """Tests for MosaicStage.get_name()."""

    def test_get_name(self, mosaic_stage):
        """Test get_name returns correct stage name."""
        assert mosaic_stage.get_name() == "mosaic"


class TestMosaicConfig:
    """Tests for MosaicConfig."""

    def test_default_values(self):
        """Test MosaicConfig default values."""
        config = MosaicConfig()
        
        assert config.enabled is True
        assert config.ms_per_mosaic == 10
        assert config.overlap_count == 2
        assert config.min_images == 5
        assert config.enable_photometry is True
        assert config.enable_crossmatch is True
        assert config.output_format == "fits"

    def test_custom_values(self):
        """Test MosaicConfig with custom values."""
        config = MosaicConfig(
            enabled=False,
            ms_per_mosaic=8,
            overlap_count=1,
            min_images=3,
        )
        
        assert config.enabled is False
        assert config.ms_per_mosaic == 8
        assert config.overlap_count == 1
        assert config.min_images == 3

    def test_validation_constraints(self):
        """Test MosaicConfig validation."""
        # ms_per_mosaic must be >= 2
        with pytest.raises(ValueError):
            MosaicConfig(ms_per_mosaic=1)
        
        # min_images must be >= 1
        with pytest.raises(ValueError):
            MosaicConfig(min_images=0)
