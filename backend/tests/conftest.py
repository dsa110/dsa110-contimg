"""
Pytest configuration and shared fixtures.
"""

import atexit
import gc
import sys
import pytest
from typing import Generator

from fastapi.testclient import TestClient

from dsa110_contimg.api.app import create_app


def _cleanup_casa_modules():
    """Clean up CASA modules to prevent C++ runtime errors on shutdown.
    
    CASA's C++ backend can throw 'casatools::get_state() called after 
    shutdown initiated' if Python's garbage collector destroys CASA objects
    in the wrong order during interpreter shutdown. By explicitly removing
    CASA module references and forcing garbage collection before the 
    interpreter exits, we ensure proper cleanup order.
    """
    # Force garbage collection first to release any CASA object references
    gc.collect()
    
    # Remove all CASA-related modules from sys.modules
    # This must happen before Python's final cleanup phase
    casa_modules = [m for m in list(sys.modules.keys()) if 'casa' in m.lower()]
    for mod_name in reversed(sorted(casa_modules)):
        try:
            mod = sys.modules.get(mod_name)
            if mod is not None:
                # Clear module dict to release references
                if hasattr(mod, '__dict__'):
                    mod.__dict__.clear()
            del sys.modules[mod_name]
        except (KeyError, AttributeError, TypeError):
            pass
    
    # Force another GC pass to clean up the cleared modules
    gc.collect()


# Register cleanup to run at interpreter exit (before C++ destructors)
atexit.register(_cleanup_casa_modules)


@pytest.fixture(scope="session")
def app():
    """Create application instance for testing."""
    return create_app()


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Create a test client for the API."""
    with TestClient(app) as client:
        yield client
