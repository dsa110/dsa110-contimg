"""
Pytest configuration and shared fixtures.

This module handles the CASA C++ runtime error that occurs during Python
shutdown when casatools has been imported. The error:

    casatools::get_state() called after shutdown initiated

occurs because CASA's C++ backend tries to access internal state during
Python's atexit sequence. We work around this by:

1. Tracking when CASA modules are loaded during test execution
2. Using os._exit(0) after tests pass to skip Python's normal shutdown

This approach ensures tests pass cleanly without the spurious C++ error.
"""

import gc
import os
import sys
import pytest
from typing import Generator

from fastapi.testclient import TestClient

from dsa110_contimg.api.app import create_app


# Track whether CASA C++ code was ever loaded during the test session.
# This flag persists across all tests and is checked at session end.
_casa_cpp_loaded = False


def _check_casa_loaded():
    """Check if CASA C++ modules are currently loaded in sys.modules."""
    return any('casatools' in m or '__casac__' in m for m in sys.modules)


def pytest_runtest_call(item):
    """Called when running a test function.
    
    Check if CASA modules are loaded after each test call, since tests
    may import them inside patch.dict contexts.
    """
    global _casa_cpp_loaded
    if not _casa_cpp_loaded and _check_casa_loaded():
        _casa_cpp_loaded = True
        print(f"\n[DEBUG] CASA loaded during: {item.name}", file=sys.stderr)


def pytest_runtest_teardown(item, nextitem):
    """Called after each test completes.
    
    Double-check for CASA modules that may have been imported during the test.
    """
    global _casa_cpp_loaded
    if not _casa_cpp_loaded and _check_casa_loaded():
        _casa_cpp_loaded = True


def _cleanup_casa():
    """Clean up CASA modules from sys.modules.
    
    This helps reduce the chance of C++ destructor issues, though the
    C++ code may still be loaded in memory.
    """
    gc.collect()
    
    casa_modules = [m for m in list(sys.modules.keys()) if 'casa' in m.lower()]
    
    for mod_name in reversed(sorted(casa_modules)):
        if mod_name in sys.modules:
            try:
                del sys.modules[mod_name]
            except (KeyError, TypeError):
                pass
    
    gc.collect()


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Called after all tests finish, before returning exit status.
    
    If CASA C++ code was loaded during any test and all tests passed,
    use os._exit(0) to skip Python's normal shutdown sequence and avoid
    the C++ runtime error.
    
    Note: trylast=True ensures this runs after pytest-cov and other plugins
    have completed their sessionfinish hooks.
    """
    global _casa_cpp_loaded
    
    _cleanup_casa()
    
    if exitstatus == 0 and _casa_cpp_loaded:
        # Flush output streams before exiting to ensure all output is visible
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Skip Python's normal shutdown to avoid CASA C++ destructor issues
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
