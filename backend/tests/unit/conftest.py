"""
Unit test configuration and fixtures.

Provides properly configured test clients with database fixtures for unit tests
that need to interact with API routes.
"""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from tests.fixtures import (
    create_test_database_environment,
    create_test_products_db,
    create_test_cal_registry_db,
)


@pytest.fixture
def client():
    """Create a test client with properly configured test databases.
    
    This fixture creates temporary SQLite databases with sample data,
    configures the API to use them, and returns a TestClient.
    
    The databases are cleaned up automatically when the fixture exits.
    """
    with create_test_database_environment() as db_paths:
        products_db = str(db_paths["products"])
        cal_db = str(db_paths["cal_registry"])
        
        # Set environment variables before creating the app
        env_patches = {
            "PIPELINE_PRODUCTS_DB": products_db,
            "PIPELINE_CAL_REGISTRY_DB": cal_db,
            "DSA110_AUTH_DISABLED": "true",
            "DSA110_ALLOWED_IPS": "127.0.0.1,::1,testclient",
        }
        
        with patch.dict(os.environ, env_patches):
            # Clear cached configs
            try:
                from dsa110_contimg.api.config import get_config
                get_config.cache_clear()
            except (ImportError, AttributeError):
                pass
            
            # Reset database engines
            try:
                from dsa110_contimg.database.session import reset_engines
                reset_engines()
            except (ImportError, AttributeError):
                pass
            
            # Patch IP check and create app
            with patch("dsa110_contimg.api.app.is_ip_allowed", return_value=True):
                from dsa110_contimg.api.app import create_app
                app = create_app()
                yield TestClient(app)
