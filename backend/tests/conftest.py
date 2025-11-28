"""
Pytest configuration and shared fixtures.
"""

import pytest
from typing import Generator

from fastapi.testclient import TestClient

from dsa110_contimg.api.app import create_app


@pytest.fixture(scope="session")
def app():
    """Create application instance for testing."""
    return create_app()


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Create a test client for the API."""
    with TestClient(app) as client:
        yield client
