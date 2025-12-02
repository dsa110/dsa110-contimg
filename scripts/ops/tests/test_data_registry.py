#!/opt/miniforge/envs/casa6/bin/python
"""Test script for data registry functionality."""
import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from dsa110_contimg.database.data_config import PRODUCTS_BASE, STAGE_BASE
from dsa110_contimg.database.data_registry import (ensure_data_registry_db,
                                                   finalize_data, get_data,
                                                   get_data_lineage, link_data,
                                                   list_data, register_data)


def test_data_registry():
    """Test basic data registry operations."""
    print("=== Testing Data Registry ===\n")
    
    # Use temp database for testing
    import tempfile
    db_path = Path(tempfile.mktemp(suffix='.db'))
    
    try:
        # 1. Create database
        print("1. Creating database...")
        conn = ensure_data_registry_db(db_path)
        print("   :check: Database created\n")
        
        # 2. Register test data
        print("2. Registering test data...")
        ms_id = register_data(
            conn,
            data_type='ms',
            data_id='test_ms_001',
            stage_path=str(STAGE_BASE / 'ms' / 'test_ms_001.ms'),
            metadata={'test': True, 'frequency': 1.4},
            auto_publish=True,
        )
        print(f"   :check: Registered MS: {ms_id}\n")
        
        image_id = register_data(
            conn,
            data_type='image',
            data_id='test_image_001',
            stage_path=str(STAGE_BASE / 'images' / 'test_image_001.fits'),
            metadata={'ms_id': ms_id, 'beam': 5.0},
            auto_publish=True,
        )
        print(f"   :check: Registered Image: {image_id}\n")
        
        # 3. Link data
        print("3. Linking data...")
        link_data(conn, ms_id, image_id, 'derived_from')
        print("   :check: Linked MS -> Image\n")
        
        # 4. Retrieve data
        print("4. Retrieving data...")
        ms_record = get_data(conn, ms_id)
        if ms_record:
            print(f"   :check: Retrieved MS: {ms_record.data_id}, status={ms_record.status}")
        else:
            print("   :cross: Failed to retrieve MS")
            return False
        
        # 5. List data
        print("\n5. Listing data...")
        all_data = list_data(conn)
        print(f"   :check: Found {len(all_data)} data instances")
        for d in all_data:
            print(f"     - {d.data_type}: {d.data_id} ({d.status})")
        
        # 6. Get lineage
        print("\n6. Getting lineage...")
        lineage = get_data_lineage(conn, image_id)
        print(f"   :check: Lineage for {image_id}:")
        print(f"     Parents: {lineage['parents']}")
        print(f"     Children: {lineage['children']}")
        
        # 7. Finalize data
        print("\n7. Finalizing data...")
        finalized = finalize_data(
            conn,
            image_id,
            qa_status='passed',
            validation_status='validated',
        )
        print(f"   :check: Finalized: {finalized}")
        
        # Check if auto-published
        updated = get_data(conn, image_id)
        if updated and updated.status == 'published':
            print(f"   :check: Auto-published to: {updated.published_path}")
        else:
            print(f"   :warning: Status: {updated.status if updated else 'unknown'}")
        
        print("\n=== All Tests Passed ===")
        return True
        
    except Exception as e:
        print(f"\n:cross: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if db_path.exists():
            db_path.unlink()

if __name__ == '__main__':
    success = test_data_registry()
    sys.exit(0 if success else 1)
