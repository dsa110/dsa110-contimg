"""
Pytest configuration and shared fixtures.
"""

import gc
import sys
import pytest
from typing import Generator

from fastapi.testclient import TestClient

from dsa110_contimg.api.app import create_app


def _cleanup_casa():
    """Clean up CASA modules to prevent C++ runtime errors on shutdown.
    
    CASA's C++ backend throws 'casatools::get_state() called after 
    shutdown initiated' if casatools tries to access state during 
    Python's atexit shutdown sequence. The fix is to remove all CASA
    modules from sys.modules BEFORE Python's shutdown begins.
    
    IMPORTANT: Do NOT call casatools.ctsys.shutdown() - that triggers
    the error immediately if any CASA code runs afterward.
    """
    # Force garbage collection first to release object references
    gc.collect()
    
    # Get all CASA-related modules
    casa_modules = [m for m in list(sys.modules.keys()) if 'casa' in m.lower()]
    if not casa_modules:
        return
    
    # Clear all CASA modules from sys.modules
    # Sort reversed so nested modules are removed before parent modules
    for mod_name in reversed(sorted(casa_modules)):
        if mod_name in sys.modules:
            try:
                del sys.modules[mod_name]
            except (KeyError, TypeError):
                pass
    
    gc.collect()


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished, right before returning exit status.
    
    This hook runs after all tests complete but before Python starts its
    shutdown sequence, making it the ideal place to clean up CASA.
    """
    print("\n=== pytest_sessionfinish: Starting CASA cleanup ===", file=sys.stderr)
    _cleanup_casa()
    print("=== pytest_sessionfinish: CASA cleanup complete ===", file=sys.stderr)


@pytest.fixture(scope="session")
def app():
    """Create application instance for testing."""
    return create_app()


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Create a test client for the API."""
    with TestClient(app) as client:
        yield client
