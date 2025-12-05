#!/opt/miniforge/envs/casa6/bin/python
"""Initialize the unified pipeline database.

As of v0.10, all pipeline state is stored in a single unified database
(pipeline.sqlite3). This script ensures the database exists with all
required tables.

Usage:
    python scripts/ops/utils/init_databases.py
"""

import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from dsa110_contimg.database import ensure_pipeline_db


def init_all():
    """Initialize the unified pipeline database."""
    print("=== Initializing DSA-110 Pipeline Database ===\n")
    
    try:
        conn = ensure_pipeline_db()
        conn.close()
        print("  ✓ Unified pipeline database initialized\n")
    except Exception as e:
        print(f"  ✗ Failed: {e}\n")
        return False
    
    print("=== Database Initialization Complete ===")
    return True


if __name__ == "__main__":
    success = init_all()
    sys.exit(0 if success else 1)

