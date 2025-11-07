"""
Shared pytest fixtures for pipeline tests.
"""

import tempfile
from pathlib import Path

import pytest

from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.state import InMemoryStateRepository, SQLiteStateRepository


@pytest.fixture
def test_config():
    """Standard test configuration."""
    return PipelineConfig(
        paths=PathsConfig(
            input_dir=Path("/test/input"),
            output_dir=Path("/test/output"),
        )
    )


@pytest.fixture
def test_context(test_config):
    """Standard test context."""
    return PipelineContext(
        config=test_config,
        job_id=1,
        inputs={
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-01T01:00:00",
        }
    )


@pytest.fixture
def in_memory_repo():
    """In-memory state repository for fast tests."""
    return InMemoryStateRepository()


@pytest.fixture
def sqlite_repo(tmp_path):
    """SQLite state repository with temporary database."""
    db_path = tmp_path / "test.db"
    repo = SQLiteStateRepository(db_path)
    yield repo
    repo.close()


@pytest.fixture
def context_with_repo(test_context, in_memory_repo):
    """Context with in-memory state repository."""
    return PipelineContext(
        config=test_context.config,
        job_id=test_context.job_id,
        inputs=test_context.inputs,
        outputs=test_context.outputs,
        metadata=test_context.metadata,
        state_repository=in_memory_repo,
    )


@pytest.fixture
def temp_dir():
    """Temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

