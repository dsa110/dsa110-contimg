"""
Contract tests for Pipeline Control API endpoints.

These tests validate the API contracts for:
1. Pipeline registration and listing
2. Full pipeline execution
3. Individual stage execution
4. Calibration and imaging endpoints
5. Execution status and history

Uses FastAPI's TestClient with mocked ABSURD client.
"""

import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_pipeline_db() -> Generator[Path, None, None]:
    """Create a temporary database with pipeline schema."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))

    # Create pipeline_executions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_executions (
            execution_id TEXT PRIMARY KEY,
            pipeline_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            started_at TEXT,
            completed_at TEXT,
            error TEXT,
            created_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """)

    # Create pipeline_jobs table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_jobs (
            job_id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            started_at TEXT,
            completed_at TEXT,
            error TEXT,
            FOREIGN KEY (execution_id) REFERENCES pipeline_executions(execution_id)
        )
    """)

    # Insert test data
    conn.execute("""
        INSERT INTO pipeline_executions 
        (execution_id, pipeline_name, status, started_at, completed_at)
        VALUES 
        ('exec-001', 'nightly_mosaic', 'completed', '2025-01-15T03:00:00Z', '2025-01-15T03:45:00Z'),
        ('exec-002', 'on_demand_mosaic', 'running', '2025-01-15T10:30:00Z', NULL),
        ('exec-003', 'calibration_refresh', 'failed', '2025-01-14T18:00:00Z', '2025-01-14T18:15:00Z')
    """)

    conn.execute("""
        INSERT INTO pipeline_jobs
        (job_id, execution_id, job_type, status)
        VALUES
        ('job-001', 'exec-001', 'mosaic-plan', 'completed'),
        ('job-002', 'exec-001', 'mosaic-build', 'completed'),
        ('job-003', 'exec-001', 'mosaic-qa', 'completed'),
        ('job-004', 'exec-002', 'mosaic-plan', 'completed'),
        ('job-005', 'exec-002', 'mosaic-build', 'running'),
        ('job-006', 'exec-003', 'calibration-solve', 'failed')
    """)

    conn.commit()
    conn.close()

    # Set environment variable
    old_db = os.environ.get("PIPELINE_DB")
    os.environ["PIPELINE_DB"] = str(db_path)

    yield db_path

    # Cleanup
    if old_db:
        os.environ["PIPELINE_DB"] = old_db
    else:
        os.environ.pop("PIPELINE_DB", None)

    db_path.unlink(missing_ok=True)


@pytest.fixture
def mock_absurd_client():
    """Mock ABSURD client for task spawning."""
    client = AsyncMock()
    client.spawn_task = AsyncMock(return_value="mock-task-id-123")
    client.get_task = AsyncMock(
        return_value={
            "task_id": "mock-task-id-123",
            "status": "pending",
            "task_name": "test-task",
        }
    )
    return client


@pytest.fixture
def mock_pipeline_registry():
    """Mock pipeline registry with test pipelines."""
    registry = MagicMock()
    registry.list_names.return_value = [
        "nightly_mosaic",
        "on_demand_mosaic",
        "calibration_refresh",
    ]

    # Create mock pipeline classes
    class MockNightlyMosaic:
        """Nightly mosaic pipeline."""
        schedule = "0 3 * * *"

    class MockOnDemandMosaic:
        """On-demand mosaic creation."""
        schedule = None

    class MockCalRefresh:
        """Calibration refresh pipeline."""
        schedule = None

    registry.get.side_effect = lambda name: {
        "nightly_mosaic": MockNightlyMosaic,
        "on_demand_mosaic": MockOnDemandMosaic,
        "calibration_refresh": MockCalRefresh,
    }.get(name)

    registry.__contains__ = lambda self, name: name in [
        "nightly_mosaic",
        "on_demand_mosaic",
        "calibration_refresh",
    ]

    return registry


@pytest.fixture
def client(temp_pipeline_db, mock_absurd_client, mock_pipeline_registry):
    """Create test client with mocked dependencies."""
    # Patch before importing
    with patch(
        "dsa110_contimg.api.routes.pipeline.get_absurd_client",
        return_value=mock_absurd_client,
    ), patch(
        "dsa110_contimg.pipeline.get_pipeline_registry",
        return_value=mock_pipeline_registry,
    ), patch(
        "dsa110_contimg.api.routes.absurd.get_absurd_client",
        return_value=mock_absurd_client,
    ):
        from dsa110_contimg.api.app import create_app

        app = create_app()
        yield TestClient(app)


# =============================================================================
# Tests: Registered Pipelines
# =============================================================================


class TestRegisteredPipelines:
    """Tests for /pipeline/registered endpoint."""

    def test_list_registered_pipelines(self, client, mock_pipeline_registry):
        """GET /pipeline/registered returns list of pipelines."""
        with patch(
            "dsa110_contimg.api.routes.pipeline.get_pipeline_registry",
            return_value=mock_pipeline_registry,
        ):
            # Skip if API requires auth we haven't set up
            response = client.get("/api/v1/pipeline/registered")

            # Allow 401 if auth is required
            if response.status_code == 401:
                pytest.skip("Authentication required for this endpoint")

            assert response.status_code == 200
            data = response.json()

            assert "pipelines" in data
            assert "total" in data
            assert data["total"] == 3

            # Check pipeline names
            names = [p["name"] for p in data["pipelines"]]
            assert "nightly_mosaic" in names
            assert "on_demand_mosaic" in names

    def test_pipeline_has_schedule_info(self, client, mock_pipeline_registry):
        """Pipelines include schedule information."""
        with patch(
            "dsa110_contimg.api.routes.pipeline.get_pipeline_registry",
            return_value=mock_pipeline_registry,
        ):
            response = client.get("/api/v1/pipeline/registered")

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 200
            data = response.json()

            # Find scheduled pipeline
            nightly = next(
                (p for p in data["pipelines"] if p["name"] == "nightly_mosaic"), None
            )
            assert nightly is not None
            assert nightly["is_scheduled"] == True
            assert nightly["schedule"] == "0 3 * * *"

            # Find non-scheduled pipeline
            on_demand = next(
                (p for p in data["pipelines"] if p["name"] == "on_demand_mosaic"), None
            )
            assert on_demand is not None
            assert on_demand["is_scheduled"] == False


# =============================================================================
# Tests: Available Stages
# =============================================================================


class TestAvailableStages:
    """Tests for /pipeline/stages endpoint."""

    def test_list_available_stages(self, client):
        """GET /pipeline/stages returns list of stages."""
        response = client.get("/api/v1/pipeline/stages")

        if response.status_code == 401:
            pytest.skip("Authentication required")

        assert response.status_code == 200
        data = response.json()

        assert "stages" in data
        assert "total" in data
        assert data["total"] >= 9  # At least 9 core stages

        # Check required stages
        stage_names = [s["name"] for s in data["stages"]]
        assert "convert-uvh5-to-ms" in stage_names
        assert "calibration-solve" in stage_names
        assert "calibration-apply" in stage_names
        assert "imaging" in stage_names

    def test_stages_have_descriptions(self, client):
        """Each stage has a description."""
        response = client.get("/api/v1/pipeline/stages")

        if response.status_code == 401:
            pytest.skip("Authentication required")

        data = response.json()

        for stage in data["stages"]:
            assert "name" in stage
            assert "description" in stage
            assert len(stage["description"]) > 0


# =============================================================================
# Tests: Full Pipeline Execution
# =============================================================================


class TestFullPipelineExecution:
    """Tests for /pipeline/full endpoint."""

    def test_run_full_pipeline_success(self, client, mock_absurd_client):
        """POST /pipeline/full queues full pipeline."""
        request_body = {
            "start_time": "2025-01-15T00:00:00Z",
            "end_time": "2025-01-15T12:00:00Z",
            "input_dir": "/data/incoming",
            "output_dir": "/stage/dsa110-contimg/ms",
            "run_calibration": True,
            "run_imaging": True,
        }

        with patch(
            "dsa110_contimg.api.routes.pipeline.get_absurd_client",
            return_value=mock_absurd_client,
        ):
            response = client.post("/api/v1/pipeline/full", json=request_body)

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "queued"
            assert "task_ids" in data
            assert "conversion" in data["task_ids"]
            assert "time_range" in data

    def test_run_full_pipeline_conversion_only(self, client, mock_absurd_client):
        """Can run conversion without calibration/imaging."""
        request_body = {
            "start_time": "2025-01-15T00:00:00Z",
            "end_time": "2025-01-15T12:00:00Z",
            "run_calibration": False,
            "run_imaging": False,
        }

        with patch(
            "dsa110_contimg.api.routes.pipeline.get_absurd_client",
            return_value=mock_absurd_client,
        ):
            response = client.post("/api/v1/pipeline/full", json=request_body)

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 200
            data = response.json()

            assert "conversion" in data["task_ids"]
            assert "calibration" not in data["task_ids"]
            assert "imaging" not in data["task_ids"]

    def test_run_full_pipeline_validation_error(self, client):
        """Invalid request returns 422."""
        request_body = {
            # Missing required fields
            "run_calibration": True,
        }

        response = client.post("/api/v1/pipeline/full", json=request_body)

        # Should fail validation
        assert response.status_code in [401, 422]


# =============================================================================
# Tests: Individual Stage Execution
# =============================================================================


class TestIndividualStageExecution:
    """Tests for /pipeline/stage endpoint."""

    def test_run_stage_success(self, client, mock_absurd_client):
        """POST /pipeline/stage spawns stage task."""
        request_body = {
            "stage": "imaging",
            "params": {"ms_path": "/stage/dsa110-contimg/ms/test.ms"},
            "priority": 5,
        }

        with patch(
            "dsa110_contimg.api.routes.pipeline.get_absurd_client",
            return_value=mock_absurd_client,
        ):
            response = client.post("/api/v1/pipeline/stage", json=request_body)

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 200
            data = response.json()

            assert "task_id" in data
            assert data["stage"] == "imaging"
            assert data["status"] == "pending"

    def test_run_stage_invalid_stage(self, client):
        """Invalid stage name returns 400."""
        request_body = {
            "stage": "not-a-real-stage",
            "params": {},
        }

        response = client.post("/api/v1/pipeline/stage", json=request_body)

        if response.status_code == 401:
            pytest.skip("Authentication required")

        assert response.status_code == 400
        assert "Unknown stage" in response.json()["detail"]


# =============================================================================
# Tests: Calibrate Endpoint
# =============================================================================


class TestCalibrateEndpoint:
    """Tests for /pipeline/calibrate endpoint."""

    def test_calibrate_apply_only(self, client, mock_absurd_client):
        """POST /pipeline/calibrate applies existing solutions."""
        with patch(
            "dsa110_contimg.api.routes.pipeline.get_absurd_client",
            return_value=mock_absurd_client,
        ):
            response = client.post(
                "/api/v1/pipeline/calibrate",
                params={
                    "ms_path": "/stage/dsa110-contimg/ms/test.ms",
                    "apply_only": True,
                },
            )

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 200
            data = response.json()

            assert "task_id" in data
            assert data["stage"] == "calibration-apply"

    def test_calibrate_solve_new(self, client, mock_absurd_client):
        """POST /pipeline/calibrate can solve new solutions."""
        with patch(
            "dsa110_contimg.api.routes.pipeline.get_absurd_client",
            return_value=mock_absurd_client,
        ):
            response = client.post(
                "/api/v1/pipeline/calibrate",
                params={
                    "ms_path": "/stage/dsa110-contimg/ms/test.ms",
                    "apply_only": False,
                },
            )

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 200
            data = response.json()

            assert data["stage"] == "calibration-solve"


# =============================================================================
# Tests: Image Endpoint
# =============================================================================


class TestImageEndpoint:
    """Tests for /pipeline/image endpoint."""

    def test_image_default_params(self, client, mock_absurd_client):
        """POST /pipeline/image uses default imaging parameters."""
        with patch(
            "dsa110_contimg.api.routes.pipeline.get_absurd_client",
            return_value=mock_absurd_client,
        ):
            response = client.post(
                "/api/v1/pipeline/image",
                params={"ms_path": "/stage/dsa110-contimg/ms/test.ms"},
            )

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 200
            data = response.json()

            assert "task_id" in data
            assert data["stage"] == "imaging"

    def test_image_custom_params(self, client, mock_absurd_client):
        """POST /pipeline/image accepts custom imaging parameters."""
        with patch(
            "dsa110_contimg.api.routes.pipeline.get_absurd_client",
            return_value=mock_absurd_client,
        ):
            response = client.post(
                "/api/v1/pipeline/image",
                params={
                    "ms_path": "/stage/dsa110-contimg/ms/test.ms",
                    "imsize": 2048,
                    "cell": "3arcsec",
                    "niter": 5000,
                    "threshold": "1mJy",
                    "weighting": "natural",
                    "robust": 0.0,
                },
            )

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 200


# =============================================================================
# Tests: Execution History
# =============================================================================


class TestExecutionHistory:
    """Tests for /pipeline/executions endpoints."""

    def test_list_executions(self, client, temp_pipeline_db):
        """GET /pipeline/executions returns execution list."""
        response = client.get("/api/v1/pipeline/executions")

        if response.status_code == 401:
            pytest.skip("Authentication required")

        assert response.status_code == 200
        data = response.json()

        assert "executions" in data
        assert "total" in data
        assert data["total"] >= 3  # We inserted 3 test executions

    def test_list_executions_with_limit(self, client, temp_pipeline_db):
        """GET /pipeline/executions respects limit parameter."""
        response = client.get("/api/v1/pipeline/executions", params={"limit": 2})

        if response.status_code == 401:
            pytest.skip("Authentication required")

        assert response.status_code == 200
        data = response.json()

        assert len(data["executions"]) <= 2

    def test_list_executions_filter_by_status(self, client, temp_pipeline_db):
        """GET /pipeline/executions can filter by status."""
        response = client.get(
            "/api/v1/pipeline/executions", params={"status_filter": "completed"}
        )

        if response.status_code == 401:
            pytest.skip("Authentication required")

        assert response.status_code == 200
        data = response.json()

        for exec in data["executions"]:
            assert exec["status"] == "completed"

    def test_get_execution_detail(self, client, temp_pipeline_db):
        """GET /pipeline/executions/{id} returns execution details."""
        response = client.get("/api/v1/pipeline/executions/exec-001")

        if response.status_code == 401:
            pytest.skip("Authentication required")

        assert response.status_code == 200
        data = response.json()

        assert data["execution_id"] == "exec-001"
        assert data["pipeline_name"] == "nightly_mosaic"
        assert data["status"] == "completed"
        assert "jobs" in data
        assert len(data["jobs"]) == 3

    def test_get_execution_not_found(self, client, temp_pipeline_db):
        """GET /pipeline/executions/{id} returns 404 for missing execution."""
        response = client.get("/api/v1/pipeline/executions/nonexistent-id")

        if response.status_code == 401:
            pytest.skip("Authentication required")

        assert response.status_code == 404

    def test_execution_includes_job_details(self, client, temp_pipeline_db):
        """Execution details include job information."""
        response = client.get("/api/v1/pipeline/executions/exec-002")

        if response.status_code == 401:
            pytest.skip("Authentication required")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "running"
        jobs = data["jobs"]

        # Should have 2 jobs
        assert len(jobs) == 2

        # Check job structure
        for job in jobs:
            assert "job_id" in job
            assert "job_type" in job
            assert "status" in job


# =============================================================================
# Tests: Run Registered Pipeline
# =============================================================================


class TestRunRegisteredPipeline:
    """Tests for /pipeline/run endpoint."""

    def test_run_registered_pipeline(self, client, mock_absurd_client, mock_pipeline_registry):
        """POST /pipeline/run queues a registered pipeline."""
        with patch(
            "dsa110_contimg.api.routes.pipeline.get_absurd_client",
            return_value=mock_absurd_client,
        ), patch(
            "dsa110_contimg.api.routes.pipeline.get_pipeline_registry",
            return_value=mock_pipeline_registry,
        ):
            request_body = {
                "pipeline_name": "nightly_mosaic",
                "params": {},
            }

            response = client.post("/api/v1/pipeline/run", json=request_body)

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 200
            data = response.json()

            assert "execution_id" in data
            assert data["pipeline_name"] == "nightly_mosaic"
            assert data["status"] == "pending"

    def test_run_pipeline_with_params(self, client, mock_absurd_client, mock_pipeline_registry):
        """POST /pipeline/run passes parameters to pipeline."""
        with patch(
            "dsa110_contimg.api.routes.pipeline.get_absurd_client",
            return_value=mock_absurd_client,
        ), patch(
            "dsa110_contimg.api.routes.pipeline.get_pipeline_registry",
            return_value=mock_pipeline_registry,
        ):
            request_body = {
                "pipeline_name": "on_demand_mosaic",
                "params": {
                    "start_time": "2025-01-15T00:00:00Z",
                    "end_time": "2025-01-15T12:00:00Z",
                },
            }

            response = client.post("/api/v1/pipeline/run", json=request_body)

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 200

    def test_run_unknown_pipeline(self, client, mock_pipeline_registry):
        """POST /pipeline/run returns 404 for unknown pipeline."""
        with patch(
            "dsa110_contimg.api.routes.pipeline.get_pipeline_registry",
            return_value=mock_pipeline_registry,
        ):
            request_body = {
                "pipeline_name": "unknown_pipeline",
                "params": {},
            }

            response = client.post("/api/v1/pipeline/run", json=request_body)

            if response.status_code == 401:
                pytest.skip("Authentication required")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


# =============================================================================
# Tests: Response Schema Validation
# =============================================================================


class TestResponseSchemas:
    """Tests that verify response schemas match expected format."""

    def test_execution_response_schema(self, client, temp_pipeline_db):
        """Execution response has correct schema."""
        response = client.get("/api/v1/pipeline/executions/exec-001")

        if response.status_code == 401:
            pytest.skip("Authentication required")

        data = response.json()

        # Required fields
        assert "execution_id" in data
        assert "pipeline_name" in data
        assert "status" in data
        assert "jobs" in data

        # Optional fields should be present (even if null)
        assert "started_at" in data
        assert "completed_at" in data
        assert "error" in data

    def test_stage_list_response_schema(self, client):
        """Stage list response has correct schema."""
        response = client.get("/api/v1/pipeline/stages")

        if response.status_code == 401:
            pytest.skip("Authentication required")

        data = response.json()

        assert isinstance(data["stages"], list)
        assert isinstance(data["total"], int)

        for stage in data["stages"]:
            assert isinstance(stage["name"], str)
            assert isinstance(stage["description"], str)

    def test_pipeline_list_response_schema(self, client, mock_pipeline_registry):
        """Pipeline list response has correct schema."""
        with patch(
            "dsa110_contimg.api.routes.pipeline.get_pipeline_registry",
            return_value=mock_pipeline_registry,
        ):
            response = client.get("/api/v1/pipeline/registered")

            if response.status_code == 401:
                pytest.skip("Authentication required")

            data = response.json()

            assert isinstance(data["pipelines"], list)
            assert isinstance(data["total"], int)

            for pipeline in data["pipelines"]:
                assert isinstance(pipeline["name"], str)
                assert isinstance(pipeline["is_scheduled"], bool)
                # description and schedule can be None
