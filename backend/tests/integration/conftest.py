"""
Shared fixtures for integration tests.

This module provides session-scoped fixtures for expensive setup operations
that can be reused across multiple integration tests.
"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture(scope="session")
def shared_temp_dir():
    """
    Create a temporary directory that persists for the entire test session.
    This avoids creating/deleting directories for each test.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="dsa110_integration_"))
    yield temp_dir
    # Cleanup after all tests complete
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def casa6_python():
    """
    Verify casa6 Python environment is being used.
    Raises error if not using casa6.
    """
    import sys

    casa6_path = "/opt/miniforge/envs/casa6/bin/python"
    if sys.executable != casa6_path:
        pytest.skip(f"Requires casa6 Python environment. Current: {sys.executable}")
    return sys.executable


@pytest.fixture(scope="function")
def clean_test_dir(shared_temp_dir):
    """
    Create a clean subdirectory for each test function.
    Uses session-scoped temp dir but creates unique subdirs.
    """
    import uuid

    test_dir = shared_temp_dir / f"test_{uuid.uuid4().hex[:8]}"
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    # Cleanup test-specific directory
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def temp_work_dir(tmp_path: Path) -> Path:
    """Create a temporary work directory for test output files."""
    work_dir = tmp_path / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


@pytest.fixture
def test_config():
    """Provide a minimal pipeline config for integration tests."""
    from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig

    return PipelineConfig(
        paths=PathsConfig(
            input_dir="/tmp/test_input",
            output_dir="/tmp/test_output",
        )
    )


@pytest.fixture
def context_with_repo(test_config, tmp_path):
    """Provide a PipelineContext with a mock state repository."""
    from unittest.mock import MagicMock
    from dsa110_contimg.pipeline.context import PipelineContext

    mock_repo = MagicMock()
    mock_repo.get_state.return_value = {}

    return PipelineContext(
        config=test_config,
        job_id="test-job-123",
        inputs={},
        outputs={},
        metadata={},
        state_repository=mock_repo,
    )


@pytest.fixture
def mock_table_factory():
    """Factory for creating mock casacore table objects."""
    from unittest.mock import MagicMock
    import numpy as np

    def _factory(path, readonly=True):
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=None)

        if "FIELD" in str(path):
            ctx.getcol.return_value = np.array([[[np.radians(120.0), np.radians(45.0)]]])
            ctx.colnames.return_value = ["PHASE_DIR"]
            ctx.nrows.return_value = 1
        elif "SPECTRAL_WINDOW" in str(path):
            ctx.getcol.return_value = np.array([[1.4e9]])
            ctx.colnames.return_value = ["CHAN_FREQ"]
            ctx.nrows.return_value = 1
        else:
            ctx.colnames.return_value = [
                "DATA",
                "CORRECTED_DATA",
                "FLAG",
                "ANTENNA1",
                "ANTENNA2",
                "TIME",
                "UVW",
            ]
            ctx.nrows.return_value = 1000
            ctx.getcol.return_value = np.random.random((1000, 1, 4)) + 1j * np.random.random(
                (1000, 1, 4)
            )
        return ctx

    return _factory
