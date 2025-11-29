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
    """Clean up CASA to prevent C++ runtime errors on shutdown.
    
    CASA's C++ backend throws 'casatools::get_state() called after 
    shutdown initiated' if the internal gRPC service is still running
    when Python exits. We must remove the service before exit.
    """
    # Only clean up if casatools was actually imported
    if 'casatools' not in sys.modules:
        return
        
    try:
        casatools = sys.modules['casatools']
        # Remove the CASA gRPC service - this is the key fix
        reg = casatools.ctsys.registry()
        if reg and 'uri' in reg:
            casatools.ctsys.remove_service(reg['uri'])
    except Exception:
        pass
    
    # Force garbage collection to release CASA object references
    gc.collect()
    
    # Remove CASA modules from sys.modules
    casa_modules = [m for m in list(sys.modules.keys()) if 'casa' in m.lower()]
    for mod_name in reversed(sorted(casa_modules)):
        try:
            mod = sys.modules.get(mod_name)
            if mod is not None and hasattr(mod, '__dict__'):
                try:
                    mod.__dict__.clear()
                except (TypeError, RuntimeError):
                    pass
            del sys.modules[mod_name]
        except (KeyError, AttributeError, TypeError):
            pass
    
    gc.collect()


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished, right before returning exit status.
    
    This hook runs after all tests complete but before Python starts its
    shutdown sequence, making it the ideal place to clean up CASA.
    """
    _cleanup_casa()


@pytest.fixture(scope="session")
def app():
    """Create application instance for testing."""
    return create_app()


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Create a test client for the API."""
    with TestClient(app) as client:
        yield client
