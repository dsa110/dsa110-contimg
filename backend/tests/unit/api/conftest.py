"""Pytest configuration for API unit tests.

Sets environment variables before any imports to prevent expensive operations
during test collection (e.g., scanning large directories).
"""

import os

# Set SKIP_INCOMING_SCAN before any imports that might trigger file system operations
# This prevents scanning /data/incoming/ which has 80k+ files
os.environ["SKIP_INCOMING_SCAN"] = "true"

# Also set other environment variables that might cause issues during import
os.environ.setdefault("PIPELINE_STATE_DIR", "/tmp/test_state")
os.environ.setdefault("PIPELINE_QUEUE_DB", "/tmp/test_state/ingest.sqlite3")
os.environ.setdefault("PIPELINE_PRODUCTS_DB", "/tmp/test_state/products.sqlite3")
os.environ.setdefault("CAL_REGISTRY_DB", "/tmp/test_state/cal_registry.sqlite3")
