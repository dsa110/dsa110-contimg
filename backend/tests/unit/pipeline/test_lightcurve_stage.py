"""Unit tests for LightCurveStage."""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from dsa110_contimg.pipeline.config import (
    LightCurveConfig,
    PathsConfig,
    PipelineConfig,
)
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import LightCurveStage


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create directory structure
        output_dir = tmpdir_path / "output"
        state_dir = tmpdir_path / "state"
        mosaics_dir = output_dir / "mosaics"

        for d in [output_dir, state_dir, mosaics_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Create products database with photometry table
        products_db_path = state_dir / "products.sqlite3"
        conn = sqlite3.connect(products_db_path)
        conn.execute(
            """
            CREATE TABLE photometry (
                id INTEGER PRIMARY KEY,
                source_id TEXT,
                ra_deg REAL,
                dec_deg REAL,
                mjd REAL,
                flux_jy REAL,
                flux_err_jy REAL,
                normalized_flux_jy REAL,
                normalized_flux_err_jy REAL,
                nvss_flux_mjy REAL,
                mosaic_path TEXT,
                image_path TEXT
            )
            """
        )
        conn.commit()
        conn.close()

        # Create cal_registry database
        cal_registry_db = state_dir / "cal_registry.sqlite3"
        cal_registry_db.touch()

        yield {
            "tmpdir": tmpdir_path,
            "output_dir": output_dir,
            "state_dir": state_dir,
            "mosaics_dir": mosaics_dir,
            "products_db": products_db_path,
            "cal_registry_db": cal_registry_db,
        }


@pytest.fixture
def pipeline_config(temp_dirs):
    """Create pipeline configuration for testing."""
    return PipelineConfig(
        paths=PathsConfig(
            input_dir=str(temp_dirs["output_dir"]),
            output_dir=str(temp_dirs["output_dir"]),
            state_dir=str(temp_dirs["state_dir"]),
            products_db=str(temp_dirs["products_db"]),
            cal_registry_db=str(temp_dirs["cal_registry_db"]),
        ),
        light_curve=LightCurveConfig(
            enabled=True,
            min_epochs=3,
            eta_threshold=2.0,
            v_threshold=0.1,
            sigma_threshold=3.0,
        ),
    )


@pytest.fixture
def lightcurve_stage(pipeline_config):
    """Create LightCurveStage instance."""
    return LightCurveStage(pipeline_config)


@pytest.fixture
def sample_photometry(temp_dirs):
    """Insert sample photometry data into database."""
    conn = sqlite3.connect(temp_dirs["products_db"])

    # Insert data for 3 sources with varying variability
    sources = [
        # Non-variable source (consistent flux)
        {
            "source_id": "NVSS_J120000+300000",
            "ra_deg": 180.0,
            "dec_deg": 30.0,
            "fluxes": [0.100, 0.101, 0.099, 0.100, 0.102],
            "flux_errs": [0.005, 0.005, 0.005, 0.005, 0.005],
            "nvss_flux_mjy": 100.0,
        },
        # Variable source (high variability)
        {
            "source_id": "NVSS_J120100+300100",
            "ra_deg": 180.25,
            "dec_deg": 30.03,
            "fluxes": [0.100, 0.200, 0.150, 0.300, 0.120],
            "flux_errs": [0.010, 0.010, 0.010, 0.010, 0.010],
            "nvss_flux_mjy": 150.0,
        },
        # ESE candidate (one extreme outlier - needs many baseline points for 3σ detection)
        {
            "source_id": "NVSS_J120200+300200",
            "ra_deg": 180.5,
            "dec_deg": 30.06,
            # 19 baseline + 1 spike = 20 epochs, giving σ-deviation > 4
            "fluxes": [0.100] * 19 + [1.000],  # 10x spike on 20th epoch
            "flux_errs": [0.005] * 20,
            "nvss_flux_mjy": 100.0,
        },
    ]

    base_mjd = 60000.0
    for source in sources:
        for i, (flux, err) in enumerate(zip(source["fluxes"], source["flux_errs"])):
            conn.execute(
                """
                INSERT INTO photometry
                (source_id, ra_deg, dec_deg, mjd, flux_jy, flux_err_jy,
                 normalized_flux_jy, normalized_flux_err_jy, nvss_flux_mjy, mosaic_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source["source_id"],
                    source["ra_deg"],
                    source["dec_deg"],
                    base_mjd + i,
                    flux,
                    err,
                    flux,  # normalized = raw for simplicity
                    err,
                    source["nvss_flux_mjy"],
                    "/data/mosaics/test.fits",
                ),
            )

    conn.commit()
    conn.close()

    return sources


class TestLightCurveStageValidation:
    """Tests for LightCurveStage.validate()."""

    def test_validate_missing_products_db(self, pipeline_config, temp_dirs):
        """Test validation fails when products database missing."""
        # Remove the database
        Path(temp_dirs["products_db"]).unlink()

        stage = LightCurveStage(pipeline_config)
        context = PipelineContext(config=pipeline_config, outputs={})

        is_valid, error = stage.validate(context)

        assert not is_valid
        assert "Products database not found" in error

    def test_validate_success_no_source_ids(self, lightcurve_stage, pipeline_config):
        """Test validation succeeds without source_ids (will process all)."""
        context = PipelineContext(config=pipeline_config, outputs={})

        is_valid, error = lightcurve_stage.validate(context)

        assert is_valid
        assert error is None

    def test_validate_success_with_source_ids(self, lightcurve_stage, pipeline_config):
        """Test validation succeeds with source_ids provided."""
        context = PipelineContext(
            config=pipeline_config,
            outputs={"source_ids": ["NVSS_J120000+300000", "NVSS_J120100+300100"]},
        )

        is_valid, error = lightcurve_stage.validate(context)

        assert is_valid
        assert error is None

    def test_validate_success_with_mosaic_path(self, lightcurve_stage, pipeline_config):
        """Test validation succeeds with mosaic_path provided."""
        context = PipelineContext(
            config=pipeline_config,
            outputs={"mosaic_path": "/data/mosaics/test.fits"},
        )

        is_valid, error = lightcurve_stage.validate(context)

        assert is_valid
        assert error is None


class TestLightCurveStageExecution:
    """Tests for LightCurveStage.execute() - focus on testable logic."""

    def test_execute_no_sources_found(self, lightcurve_stage, pipeline_config):
        """Test execute handles empty database gracefully."""
        context = PipelineContext(config=pipeline_config, outputs={})

        result = lightcurve_stage.execute(context)

        assert result.outputs["variable_sources"] == []
        assert result.outputs["ese_candidates"] == []
        assert result.outputs["metrics_updated"] == 0

    def test_execute_computes_metrics(
        self, lightcurve_stage, pipeline_config, sample_photometry
    ):
        """Test execute computes metrics for sources with sufficient epochs."""
        context = PipelineContext(config=pipeline_config, outputs={})

        result = lightcurve_stage.execute(context)

        # Should have processed all 3 sources (each has 5 epochs >= min_epochs=3)
        assert result.outputs["metrics_updated"] == 3

        # Variable source should be flagged
        assert "NVSS_J120100+300100" in result.outputs["variable_sources"]

        # ESE candidate should be flagged (5x spike exceeds sigma_threshold=3)
        assert "NVSS_J120200+300200" in result.outputs["ese_candidates"]

    def test_execute_respects_source_ids(
        self, lightcurve_stage, pipeline_config, sample_photometry
    ):
        """Test execute only processes specified source_ids."""
        context = PipelineContext(
            config=pipeline_config,
            outputs={"source_ids": ["NVSS_J120000+300000"]},  # Only non-variable
        )

        result = lightcurve_stage.execute(context)

        # Should only process the one specified source
        assert result.outputs["metrics_updated"] == 1
        assert result.outputs["variable_sources"] == []
        assert result.outputs["ese_candidates"] == []


class TestLightCurveStageCleanup:
    """Tests for LightCurveStage.cleanup()."""

    def test_cleanup_does_nothing(self, lightcurve_stage, pipeline_config):
        """Test cleanup handles gracefully (no cleanup needed for light curves)."""
        context = PipelineContext(config=pipeline_config, outputs={})

        # Should not raise
        lightcurve_stage.cleanup(context)


class TestLightCurveStageName:
    """Tests for LightCurveStage.get_name()."""

    def test_get_name(self, lightcurve_stage):
        """Test get_name returns correct stage name."""
        assert lightcurve_stage.get_name() == "light_curve"


class TestLightCurveConfig:
    """Tests for LightCurveConfig."""

    def test_default_values(self):
        """Test LightCurveConfig default values."""
        config = LightCurveConfig()

        assert config.enabled is True
        assert config.min_epochs == 3
        assert config.eta_threshold == 2.0
        assert config.v_threshold == 0.1
        assert config.sigma_threshold == 3.0
        assert config.use_normalized_flux is True
        assert config.update_database is True
        assert config.trigger_alerts is True

    def test_custom_values(self):
        """Test LightCurveConfig with custom values."""
        config = LightCurveConfig(
            enabled=False,
            min_epochs=5,
            eta_threshold=1.5,
            v_threshold=0.2,
            sigma_threshold=4.0,
        )

        assert config.enabled is False
        assert config.min_epochs == 5
        assert config.eta_threshold == 1.5
        assert config.v_threshold == 0.2
        assert config.sigma_threshold == 4.0

    def test_validation_constraints(self):
        """Test LightCurveConfig validation."""
        # min_epochs must be >= 2
        with pytest.raises(ValueError):
            LightCurveConfig(min_epochs=1)

        # sigma_threshold must be >= 1.0
        with pytest.raises(ValueError):
            LightCurveConfig(sigma_threshold=0.5)

        # v_threshold must be <= 1.0
        with pytest.raises(ValueError):
            LightCurveConfig(v_threshold=1.5)


class TestLightCurveMetricsComputation:
    """Tests for internal metrics computation methods."""

    def test_compute_source_metrics(
        self, lightcurve_stage, pipeline_config, sample_photometry, temp_dirs
    ):
        """Test _compute_source_metrics returns correct structure."""
        import sqlite3

        conn = sqlite3.connect(temp_dirs["products_db"])

        metrics = lightcurve_stage._compute_source_metrics(
            conn,
            "NVSS_J120000+300000",
            use_normalized=True,
            min_epochs=3,
        )

        assert metrics is not None
        assert "eta" in metrics
        assert "v" in metrics
        assert "sigma_deviation" in metrics
        assert "chi2_nu" in metrics
        assert "n_epochs" in metrics
        assert metrics["n_epochs"] == 5

        conn.close()

    def test_compute_source_metrics_insufficient_epochs(
        self, lightcurve_stage, pipeline_config, temp_dirs
    ):
        """Test _compute_source_metrics returns None for insufficient data."""
        import sqlite3

        conn = sqlite3.connect(temp_dirs["products_db"])

        # Insert only 2 epochs (below min_epochs=3)
        conn.execute(
            """
            INSERT INTO photometry
            (source_id, ra_deg, dec_deg, mjd, flux_jy, flux_err_jy,
             normalized_flux_jy, normalized_flux_err_jy, nvss_flux_mjy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("TEST_SPARSE", 0.0, 0.0, 60000.0, 0.1, 0.01, 0.1, 0.01, 100.0),
        )
        conn.execute(
            """
            INSERT INTO photometry
            (source_id, ra_deg, dec_deg, mjd, flux_jy, flux_err_jy,
             normalized_flux_jy, normalized_flux_err_jy, nvss_flux_mjy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("TEST_SPARSE", 0.0, 0.0, 60001.0, 0.1, 0.01, 0.1, 0.01, 100.0),
        )
        conn.commit()

        metrics = lightcurve_stage._compute_source_metrics(
            conn,
            "TEST_SPARSE",
            use_normalized=True,
            min_epochs=3,
        )

        assert metrics is None

        conn.close()
