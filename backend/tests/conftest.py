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


def _check_casa_loaded():
    """Check if CASA C++ modules are currently loaded."""
    return any('casatools' in m or '__casac__' in m for m in sys.modules)


def pytest_runtest_call(item):
    """Called to run the test function.
    
    We use this hook to check if CASA gets loaded during any test.
    """
    global _casa_cpp_loaded
    if not _casa_cpp_loaded and _check_casa_loaded():
        _casa_cpp_loaded = True


def pytest_runtest_teardown(item, nextitem):
    """Called after each test.
    
    Check if CASA was loaded during the test.
    """
    global _casa_cpp_loaded
    if not _casa_cpp_loaded and _check_casa_loaded():
        _casa_cpp_loaded = True


def _cleanup_casa():
    """Clean up CASA modules to prevent C++ runtime errors on shutdown."""
    # Force garbage collection to release object references
    gc.collect()
    
    # Get all CASA-related modules
    casa_modules = [m for m in list(sys.modules.keys()) if 'casa' in m.lower()]
    
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
    
    # Clean up any remaining CASA modules
    _cleanup_casa()
    
    # If CASA C++ code was loaded during any test and tests passed,
    # use os._exit() to avoid the C++ runtime error during Python's
    # normal shutdown sequence.
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
