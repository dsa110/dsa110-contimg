#!/opt/miniforge/envs/casa6/bin/python
"""Initialize all pipeline databases with required schemas."""

import sqlite3
import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from dsa110_contimg.conversion.streaming import QueueDB
from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.database.registry import ensure_db as ensure_registry_db
from dsa110_contimg.database.schema_evolution import evolve_all_schemas


def init_all(state_dir: Path = Path("/data/dsa110-contimg/state")):
    """Initialize all databases."""
    print("=== Initializing DSA-110 Pipeline Databases ===\n")
    
    state_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Ingest Queue DB (via QueueDB class)
    queue_db = state_dir / "ingest.sqlite3"
    print(f"Initializing ingest queue: {queue_db}")
    try:
        queue = QueueDB(queue_db, expected_subbands=16, chunk_duration_minutes=5.0)
        queue.close()
        print("  :check: Ingest queue initialized\n")
    except Exception as e:
        print(f"  :cross: Failed: {e}\n")
        return False
    
    # 2. Registry DB
    registry_db = state_dir / "cal_registry.sqlite3"
    print(f"Initializing calibration registry: {registry_db}")
    try:
        ensure_registry_db(registry_db)
        print("  :check: Registry initialized\n")
    except Exception as e:
        print(f"  :cross: Failed: {e}\n")
        return False
    
    # 3. Products DB
    products_db = state_dir / "products.sqlite3"
    print(f"Initializing products: {products_db}")
    try:
        ensure_products_db(products_db)
        print("  :check: Products initialized\n")
    except Exception as e:
        print(f"  :cross: Failed: {e}\n")
        return False
    
    # 4. Evolve schemas to add any missing columns/tables
    print("Evolving database schemas...")
    evolve_all_schemas(state_dir, verbose=True)
    
    print("\n=== Database Initialization Complete ===")
    return True


if __name__ == "__main__":
    state_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/data/dsa110-contimg/state")
    success = init_all(state_dir)
    sys.exit(0 if success else 1)

