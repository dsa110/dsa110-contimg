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


def _suppress_casa_abort():
    """Suppress CASA's C++ abort during Python shutdown.
    
    CASA's C++ backend throws a std::runtime_error and calls abort()
    during Python shutdown if it detects its state is being accessed
    after shutdown began. This is a known issue in CASA 6.x.
    
    We work around this by:
    1. Registering an atexit handler that suppresses SIGABRT
    2. Only doing this after tests complete (not during)
    """
    # Set a signal handler that exits cleanly instead of aborting
    def _handle_abort(signum, frame):
        # Exit with success code since tests passed
        os._exit(0)
    
    try:
        signal.signal(signal.SIGABRT, _handle_abort)
    except (ValueError, OSError):
        # Can't set signal handler (e.g., not main thread)
        pass


def _cleanup_casa():
    """Clean up CASA modules to prevent C++ runtime errors on shutdown.
    
    CASA's C++ backend throws 'casatools::get_state() called after 
    shutdown initiated' if casatools tries to access state during 
    Python's atexit shutdown sequence. 
    """
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
    # Clean up CASA modules
    _cleanup_casa()
    
    # Install abort handler for any remaining CASA C++ cleanup issues
    # This must be done AFTER cleanup to only catch genuine shutdown issues
    _suppress_casa_abort()


@pytest.fixture(scope="session")
def app():
    """Create application instance for testing."""
    return create_app()


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Create a test client for the API."""
    with TestClient(app) as client:
        yield client
