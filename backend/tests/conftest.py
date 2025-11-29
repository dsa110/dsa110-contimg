"""
Pytest configuration and shared fixtures.
"""

import atexit
import gc
import os
import signal
import sys
import pytest
from typing import Generator

from fastapi.testclient import TestClient

from dsa110_contimg.api.app import create_app


# Track whether CASA C++ code was ever loaded during the test session
_casa_cpp_loaded = False


def _cleanup_casa():
    """Clean up CASA modules to prevent C++ runtime errors on shutdown.
    
    CASA's C++ backend throws 'casatools::get_state() called after 
    shutdown initiated' if casatools tries to access state during 
    Python's atexit shutdown sequence. 
    """
    global _casa_cpp_loaded
    
    # Force garbage collection to release object references
    gc.collect()
    
    # Get all CASA-related modules
    casa_modules = [m for m in list(sys.modules.keys()) if 'casa' in m.lower()]
    
    # Check if casatools C++ code was loaded (look for __casac__ modules)
    if any('__casac__' in m or 'casatools' in m for m in casa_modules):
        _casa_cpp_loaded = True
    
    if not casa_modules:
        return
    
    # Clear all CASA modules from sys.modules
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
    shutdown sequence.
    """
    global _casa_cpp_loaded
    
    # Clean up CASA modules - this also sets _casa_cpp_loaded flag
    _cleanup_casa()
    
    # If CASA C++ code was loaded and tests passed, use os._exit() to avoid
    # the C++ runtime error during Python's normal shutdown sequence.
    if exitstatus == 0 and _casa_cpp_loaded:
        os._exit(0)


@pytest.fixture(scope="session")
def app():
    """Create application instance for testing."""
    return create_app()


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Create a test client for the API."""
    with TestClient(app) as client:
        yield client
