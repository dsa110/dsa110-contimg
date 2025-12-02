"""
Unit tests for the calibration pipeline and jobs.

Tests calibration job execution, pipeline orchestration, and integration.
"""

from __future__ import annotations

import sqlite3

import pytest

from dsa110_contimg.calibration.jobs import (
    CalibrationApplyJob,
    CalibrationJobConfig,
    CalibrationSolveJob,
    CalibrationValidateJob,
    _ensure_calibration_tables,
)
from dsa110_contimg.calibration.pipeline import (
    CalibrationPipeline,
    CalibrationPipelineConfig,
    CalibrationResult,
    CalibrationStatus,
    StreamingCalibrationPipeline,
)


class TestCalibrationJobConfig:
    """Tests for CalibrationJobConfig dataclass."""

    def test_config_creation(self, tmp_path):
        """Test creating a CalibrationJobConfig."""
        config = CalibrationJobConfig(
            database_path=tmp_path / "test.db",
            caltable_dir=tmp_path / "caltables",
        )

        assert config.database_path == tmp_path / "test.db"
        assert config.caltable_dir == tmp_path / "caltables"
        assert config.catalog_path is None

    def test_config_with_catalog(self, tmp_path):
        """Test config with catalog path."""
        config = CalibrationJobConfig(
            database_path=tmp_path / "test.db",
            caltable_dir=tmp_path / "caltables",
            catalog_path=tmp_path / "calibrators.csv",
        )

        assert config.catalog_path == tmp_path / "calibrators.csv"


class TestEnsureCalibrationTables:
    """Tests for database table creation."""

    def test_creates_tables(self, tmp_path):
        """Test that calibration tables are created."""
        db_path = tmp_path / "test.db"

        with sqlite3.connect(str(db_path)) as conn:
            _ensure_calibration_tables(conn)

            # Check tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            assert "calibration_solves" in tables
            assert "calibration_applications" in tables

    def test_table_schema(self, tmp_path):
        """Test calibration_solves table has expected columns."""
        db_path = tmp_path / "test.db"

        with sqlite3.connect(str(db_path)) as conn:
            _ensure_calibration_tables(conn)

            # Check columns in calibration_solves
            cursor = conn.execute("PRAGMA table_info(calibration_solves)")
            columns = {row[1] for row in cursor.fetchall()}

            expected = {
                "id", "ms_path", "calibrator_field", "refant",
                "status", "k_table_path", "bp_table_path", "g_table_path",
                "created_at", "completed_at", "error", "metadata_json",
            }
            assert expected.issubset(columns)

    def test_idempotent(self, tmp_path):
        """Test that calling twice doesn't error."""
        db_path = tmp_path / "test.db"

        with sqlite3.connect(str(db_path)) as conn:
            _ensure_calibration_tables(conn)
            _ensure_calibration_tables(conn)  # Should not raise


class TestCalibrationSolveJob:
    """Tests for CalibrationSolveJob."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration."""
        return CalibrationJobConfig(
            database_path=tmp_path / "test.db",
            caltable_dir=tmp_path / "caltables",
        )

    @pytest.fixture
    def mock_ms(self, tmp_path):
        """Create a mock MS directory."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()
        return ms_path

    def test_job_type(self):
        """Test job type is set correctly."""
        job = CalibrationSolveJob()
        assert job.job_type == "calibration_solve"

    def test_validate_no_config(self):
        """Test validation fails without config."""
        job = CalibrationSolveJob(ms_path="/data/test.ms")

        is_valid, error = job.validate()

        assert not is_valid
        assert "configuration" in error.lower()

    def test_validate_no_ms_path(self, config):
        """Test validation fails without MS path."""
        job = CalibrationSolveJob(config=config)

        is_valid, error = job.validate()

        assert not is_valid
        assert "ms path" in error.lower()

    def test_validate_ms_not_found(self, config):
        """Test validation fails when MS doesn't exist."""
        job = CalibrationSolveJob(
            config=config,
            ms_path="/nonexistent/test.ms",
        )

        is_valid, error = job.validate()

        assert not is_valid
        assert "not found" in error.lower()

    def test_validate_success(self, config, mock_ms):
        """Test validation succeeds with valid config."""
        job = CalibrationSolveJob(
            config=config,
            ms_path=str(mock_ms),
        )

        is_valid, error = job.validate()

        assert is_valid
        assert error is None


class TestCalibrationApplyJob:
    """Tests for CalibrationApplyJob."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration."""
        return CalibrationJobConfig(
            database_path=tmp_path / "test.db",
            caltable_dir=tmp_path / "caltables",
        )

    def test_job_type(self):
        """Test job type is set correctly."""
        job = CalibrationApplyJob()
        assert job.job_type == "calibration_apply"

    def test_validate_no_config(self):
        """Test validation fails without config."""
        job = CalibrationApplyJob(
            target_ms_path="/data/test.ms",
            target_field="0",
            solve_id=1,
        )

        is_valid, error = job.validate()

        assert not is_valid
        assert "configuration" in error.lower()

    def test_validate_no_target_ms(self, config):
        """Test validation fails without target MS."""
        job = CalibrationApplyJob(
            config=config,
            target_field="0",
            solve_id=1,
        )

        is_valid, error = job.validate()

        assert not is_valid

    def test_validate_no_solve_id(self, config, tmp_path):
        """Test validation fails without solve_id."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        job = CalibrationApplyJob(
            config=config,
            target_ms_path=str(ms_path),
            target_field="0",
        )

        is_valid, error = job.validate()

        assert not is_valid
        assert "solve_id" in error.lower()


class TestCalibrationValidateJob:
    """Tests for CalibrationValidateJob."""

    def test_job_type(self):
        """Test job type is set correctly."""
        job = CalibrationValidateJob()
        assert job.job_type == "calibration_validate"


class TestCalibrationPipelineConfig:
    """Tests for CalibrationPipelineConfig dataclass."""

    def test_config_creation(self, tmp_path):
        """Test creating a CalibrationPipelineConfig."""
        config = CalibrationPipelineConfig(
            database_path=tmp_path / "test.db",
            caltable_dir=tmp_path / "caltables",
        )

        assert config.database_path == tmp_path / "test.db"
        assert config.caltable_dir == tmp_path / "caltables"
        assert config.do_k_calibration is False
        assert config.default_refant is None

    def test_config_with_all_options(self, tmp_path):
        """Test config with all options."""
        config = CalibrationPipelineConfig(
            database_path=tmp_path / "test.db",
            caltable_dir=tmp_path / "caltables",
            catalog_path=tmp_path / "calibrators.csv",
            default_refant="ea01,ea02,ea03",
            do_k_calibration=True,
        )

        assert config.default_refant == "ea01,ea02,ea03"
        assert config.do_k_calibration is True


class TestCalibrationResult:
    """Tests for CalibrationResult dataclass."""

    def test_success_result(self):
        """Test creating a success result."""
        result = CalibrationResult(
            success=True,
            solve_id=1,
            application_id=1,
            validation_passed=True,
            gaintables=["/data/K.cal", "/data/BP.cal", "/data/G.cal"],
            message="Calibration completed successfully",
        )

        assert result.success
        assert len(result.gaintables) == 3
        assert result.validation_passed

    def test_failure_result(self):
        """Test creating a failure result."""
        result = CalibrationResult(
            success=False,
            message="Calibration failed",
            errors=["No calibrator found in field"],
        )

        assert not result.success
        assert len(result.errors) == 1


class TestCalibrationStatus:
    """Tests for CalibrationStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert CalibrationStatus.PENDING.value == "pending"
        assert CalibrationStatus.RUNNING.value == "running"
        assert CalibrationStatus.COMPLETED.value == "completed"
        assert CalibrationStatus.FAILED.value == "failed"
        assert CalibrationStatus.VALIDATION_FAILED.value == "validation_failed"


class TestCalibrationPipeline:
    """Tests for CalibrationPipeline class."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration."""
        return CalibrationPipelineConfig(
            database_path=tmp_path / "test.db",
            caltable_dir=tmp_path / "caltables",
        )

    def test_pipeline_name(self, config):
        """Test pipeline name is set correctly."""
        assert CalibrationPipeline.pipeline_name == "calibration"

    def test_pipeline_initialization(self, config):
        """Test pipeline initialization."""
        pipeline = CalibrationPipeline(
            config=config,
            ms_path="/data/test.ms",
            target_field="0",
        )

        assert pipeline.ms_path == "/data/test.ms"
        assert pipeline.target_field == "0"
        assert pipeline.do_k is False  # Default

    def test_pipeline_with_k_calibration(self, config):
        """Test pipeline with K calibration enabled."""
        config.do_k_calibration = True

        pipeline = CalibrationPipeline(
            config=config,
            ms_path="/data/test.ms",
            target_field="0",
        )

        assert pipeline.do_k is True

    def test_pipeline_override_do_k(self, config):
        """Test pipeline can override do_k from config."""
        config.do_k_calibration = True

        pipeline = CalibrationPipeline(
            config=config,
            ms_path="/data/test.ms",
            target_field="0",
            do_k=False,  # Override
        )

        assert pipeline.do_k is False

    def test_pipeline_skip_apply(self, config):
        """Test pipeline with skip_apply option."""
        pipeline = CalibrationPipeline(
            config=config,
            ms_path="/data/test.ms",
            target_field="0",
            skip_apply=True,
        )

        assert pipeline.skip_apply is True

    def test_pipeline_build_creates_jobs(self, config):
        """Test that build() creates expected jobs."""
        pipeline = CalibrationPipeline(
            config=config,
            ms_path="/data/test.ms",
            target_field="0",
        )

        pipeline.build()

        # Should have solve, apply, validate jobs
        assert "solve" in pipeline.jobs
        assert "apply" in pipeline.jobs
        assert "validate" in pipeline.jobs

    def test_pipeline_build_skip_apply(self, config):
        """Test build() with skip_apply creates fewer jobs."""
        pipeline = CalibrationPipeline(
            config=config,
            ms_path="/data/test.ms",
            target_field="0",
            skip_apply=True,
        )

        pipeline.build()

        # Should only have solve and validate
        assert "solve" in pipeline.jobs
        assert "apply" not in pipeline.jobs
        assert "validate" in pipeline.jobs


class TestStreamingCalibrationPipeline:
    """Tests for StreamingCalibrationPipeline class."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration."""
        return CalibrationPipelineConfig(
            database_path=tmp_path / "test.db",
            caltable_dir=tmp_path / "caltables",
        )

    def test_pipeline_name(self):
        """Test pipeline name is set correctly."""
        assert StreamingCalibrationPipeline.pipeline_name == "streaming_calibration"

    def test_pipeline_initialization(self, config):
        """Test pipeline initialization."""
        pipeline = StreamingCalibrationPipeline(
            config=config,
            ms_path="/data/cal.ms",
        )

        assert pipeline.ms_path == "/data/cal.ms"

    def test_pipeline_build_creates_jobs(self, config):
        """Test that build() creates expected jobs."""
        pipeline = StreamingCalibrationPipeline(
            config=config,
            ms_path="/data/cal.ms",
        )

        pipeline.build()

        # Should have solve and validate jobs (no apply)
        assert "solve" in pipeline.jobs
        assert "apply" not in pipeline.jobs
        assert "validate" in pipeline.jobs
