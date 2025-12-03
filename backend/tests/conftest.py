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

Additionally, CASA writes log files (casa-YYYYMMDD-HHMMSS.log) to the current
working directory. We redirect these to a centralized logs directory to prevent
test runs from polluting the workspace root.
"""

import gc
import os
import sys
import pytest
import importlib
from pathlib import Path
from typing import Generator, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# --- CASA Log Redirection ---
# CASA writes log files to CWD. Redirect to centralized logs directory
# BEFORE any CASA modules are imported (which happens during test collection).
_CASA_LOG_DIR = Path("/data/dsa110-contimg/state/logs/casa")
_ORIGINAL_CWD = os.getcwd()

try:
    _CASA_LOG_DIR.mkdir(parents=True, exist_ok=True)
    os.chdir(_CASA_LOG_DIR)
except (OSError, PermissionError):
    # Best effort - if we can't change to the log dir, logs will go to CWD
    pass


def pytest_configure(config):
    """
    Clear config caches at test session start.
    
    This ensures environment variables set in CI are respected by clearing
    any cached configurations from module import time.
    """
    # Allow TestClient IP access for integration tests
    # TestClient uses 'testclient' as the client host, which must be whitelisted
    # This must be set BEFORE the API module is imported
    os.environ.setdefault(
        "DSA110_ALLOWED_IPS",
        "127.0.0.1,::1,testclient,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    )
    
    # Clear API config cache if already imported
    try:
        from dsa110_contimg.api.config import get_config
        get_config.cache_clear()
    except ImportError:
        pass
    
    # Reset database session engines to pick up new paths
    try:
        from dsa110_contimg.database.session import reset_engines
        reset_engines()
    except ImportError:
        pass
    
    # Force reload of repositories module to pick up new config
    # (it caches DEFAULT_DB_PATH at import time)
    # Only reload if both parent and child modules are already loaded
    if "dsa110_contimg.api" in sys.modules and "dsa110_contimg.api.repositories" in sys.modules:
        importlib.reload(sys.modules["dsa110_contimg.api.repositories"])


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


# Store exit status for use in pytest_unconfigure
_pytest_exit_status = None


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Called after all tests finish, before returning exit status.
    
    Record exit status and clean up CASA modules. The actual os._exit()
    call is deferred to pytest_unconfigure to allow terminal summary to print.
    """
    global _pytest_exit_status
    _pytest_exit_status = exitstatus
    _cleanup_casa()


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    """Called after all other pytest activities are complete.
    
    If CASA C++ code was loaded during tests and all tests passed,
    use os._exit(0) to skip Python's normal shutdown sequence and avoid
    the C++ runtime error.
    """
    global _casa_cpp_loaded, _pytest_exit_status
    
    if _pytest_exit_status == 0 and _casa_cpp_loaded:
        # Flush output streams before exiting
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Skip Python's normal shutdown to avoid CASA C++ destructor issues
        os._exit(0)


@pytest.fixture(scope="session")
def app():
    """Create application instance for testing."""
    from dsa110_contimg.api.app import create_app
    return create_app()


@pytest.fixture(scope="session")
def client(app) -> "Generator[TestClient, None, None]":
    """Create a test client for the API."""
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        yield client
