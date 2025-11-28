"""Tests for the diagnostics auto-fix service templates."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Optional dependency used by fetch_mosaics_recent for time conversion
try:
    import astropy  # type: ignore  # noqa: F401

    _HAS_ASTROPY = True
except Exception:
    _HAS_ASTROPY = False

# Ensure backend/src is on the path for dsa110_contimg imports
# REPO_ROOT is /data/dsa110-contimg (parents[4] from backend/tests/unit/diagnostics/)
REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_PATH = REPO_ROOT / "backend" / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
# Also add scripts/ops so diagnostics can be imported
SCRIPTS_OPS_PATH = REPO_ROOT / "scripts" / "ops"
if str(SCRIPTS_OPS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_OPS_PATH))

from dsa110_contimg.api.data_access import fetch_mosaics_recent
from diagnostics.auto_fix_services import MISSING_ENDPOINTS
from tests.utils.mosaic_db import create_products_db_with_mosaic


def test_mosaics_template_uses_database_listing():
    """Template should call fetch_mosaics_recent (no TODO placeholders)."""
    template = MISSING_ENDPOINTS["/api/mosaics"]
    assert "fetch_mosaics_recent" in template
    assert "TODO" not in template


@pytest.mark.skipif(not _HAS_ASTROPY, reason="astropy required for MJD conversion")
def test_fetch_mosaics_recent_reads_from_db(tmp_path):
    """fetch_mosaics_recent should surface mosaics stored in the products DB."""
    db_path = create_products_db_with_mosaic(tmp_path)

    mosaics, total = fetch_mosaics_recent(db_path, limit=5)

    assert total == 1
    assert len(mosaics) == 1
    m = mosaics[0]
    assert m["name"] == "test_mosaic"
    assert m["path"].endswith("test_mosaic.fits")
    assert m["status"] == "completed"
    assert m["start_time"] is not None
    assert m["end_time"] is not None
