"""
Integration test configuration.

This conftest.py must be loaded BEFORE the test modules to ensure
environment variables are set before the API module is imported.
"""
import os

# Allow TestClient IP access for integration tests
# TestClient uses 'testclient' as the client host, which must be whitelisted
# This must be set BEFORE the API module is imported anywhere
if "DSA110_ALLOWED_IPS" not in os.environ:
    os.environ["DSA110_ALLOWED_IPS"] = (
        "127.0.0.1,::1,testclient,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    )
