"""Integration test for the /api/mosaics endpoint."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure backend/src is on the path for API imports
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = REPO_ROOT / "src"
TESTS_PATH = REPO_ROOT / "tests"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
if str(TESTS_PATH) not in sys.path:
    sys.path.insert(0, str(TESTS_PATH))

from utils.mosaic_db import create_products_db_with_mosaic

from dsa110_contimg.api import create_app
from dsa110_contimg.api.config import ApiConfig

try:
    import astropy  # noqa: F401

    _HAS_ASTROPY = True
except Exception:
    _HAS_ASTROPY = False


@pytest.mark.skipif(not _HAS_ASTROPY, reason="astropy required for MJD conversion")
def test_mosaics_endpoint_returns_db_rows(tmp_path):
    """Ensure /api/mosaics returns mosaics stored in the products DB."""
    products_db = create_products_db_with_mosaic(tmp_path)
    registry_db = tmp_path / "cal_registry.sqlite3"
    queue_db = tmp_path / "ingest.sqlite3"
    registry_db.touch()
    queue_db.touch()

    cfg = ApiConfig(
        registry_db=registry_db,
        queue_db=queue_db,
        products_db=products_db,
        expected_subbands=16,
    )

    app = create_app(cfg)
    client = TestClient(app)

    resp = client.get("/api/mosaics?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["limit"] == 5
    assert len(data["mosaics"]) == 1
    mosaic = data["mosaics"][0]
    assert mosaic["name"] == "test_mosaic"
    assert mosaic["status"] == "completed"
    assert mosaic["path"].endswith("test_mosaic.fits")
