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
