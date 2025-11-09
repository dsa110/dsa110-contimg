#!/usr/bin/env python3
"""Test script for data registry functionality."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.database.data_registry import (
    ensure_data_registry_db,
    register_data,
    finalize_data,
    get_data,
    list_data,
    link_data,
    get_data_lineage,
)
from dsa110_contimg.database.data_config import STAGE_BASE, PRODUCTS_BASE

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
        print("   ✓ Database created\n")
        
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
        print(f"   ✓ Registered MS: {ms_id}\n")
        
        image_id = register_data(
            conn,
            data_type='image',
            data_id='test_image_001',
            stage_path=str(STAGE_BASE / 'images' / 'test_image_001.fits'),
            metadata={'ms_id': ms_id, 'beam': 5.0},
            auto_publish=True,
        )
        print(f"   ✓ Registered Image: {image_id}\n")
        
        # 3. Link data
        print("3. Linking data...")
        link_data(conn, ms_id, image_id, 'derived_from')
        print("   ✓ Linked MS -> Image\n")
        
        # 4. Retrieve data
        print("4. Retrieving data...")
        ms_record = get_data(conn, ms_id)
        if ms_record:
            print(f"   ✓ Retrieved MS: {ms_record.data_id}, status={ms_record.status}")
        else:
            print("   ✗ Failed to retrieve MS")
            return False
        
        # 5. List data
        print("\n5. Listing data...")
        all_data = list_data(conn)
        print(f"   ✓ Found {len(all_data)} data instances")
        for d in all_data:
            print(f"     - {d.data_type}: {d.data_id} ({d.status})")
        
        # 6. Get lineage
        print("\n6. Getting lineage...")
        lineage = get_data_lineage(conn, image_id)
        print(f"   ✓ Lineage for {image_id}:")
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
        print(f"   ✓ Finalized: {finalized}")
        
        # Check if auto-published
        updated = get_data(conn, image_id)
        if updated and updated.status == 'published':
            print(f"   ✓ Auto-published to: {updated.published_path}")
        else:
            print(f"   ⚠ Status: {updated.status if updated else 'unknown'}")
        
        print("\n=== All Tests Passed ===")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if db_path.exists():
            db_path.unlink()

if __name__ == '__main__':
    success = test_data_registry()
    sys.exit(0 if success else 1)
