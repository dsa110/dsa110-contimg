#!/opt/miniforge/envs/casa6/bin/python
"""
Test script for SkyView functionality.
Tests the /api/images endpoint and /api/images/{id}/fits endpoint.
"""

import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8010/api")
PRODUCTS_DB = Path(os.getenv("PIPELINE_PRODUCTS_DB", "/data/dsa110-contimg/state/db/products.sqlite3"))


def check_database() -> dict:
    """Check if database exists and has images."""
    print("=" * 60)
    print("1. Database Check")
    print("=" * 60)
    
    if not PRODUCTS_DB.exists():
        print(f"  ✗ Database not found: {PRODUCTS_DB}")
        return {"exists": False, "image_count": 0}
    
    print(f"  ✓ Database found: {PRODUCTS_DB}")
    
    try:
        conn = sqlite3.connect(PRODUCTS_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Check if images table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='images'")
        if not cur.fetchone():
            print("  ✗ 'images' table does not exist")
            conn.close()
            return {"exists": True, "table_exists": False, "image_count": 0}
        
        print("  ✓ 'images' table exists")
        
        # Count images
        cur.execute("SELECT COUNT(*) as count FROM images")
        count = cur.fetchone()["count"]
        print(f"  ✓ Found {count} images in database")
        
        # Get sample image
        if count > 0:
            cur.execute("SELECT id, path, type FROM images LIMIT 1")
            sample = cur.fetchone()
            if sample:
                print(f"  ✓ Sample image: ID={sample['id']}, Path={sample['path']}, Type={sample['type']}")
        
        conn.close()
        return {"exists": True, "table_exists": True, "image_count": count}
    except Exception as e:
        print(f"  ✗ Error querying database: {e}")
        return {"exists": True, "error": str(e)}


def test_images_endpoint() -> dict:
    """Test the /api/images endpoint."""
    print("\n" + "=" * 60)
    print("2. Testing /api/images Endpoint")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/images", params={"limit": 10})
        response.raise_for_status()
        data = response.json()
        
        print(f"  ✓ Status: {response.status_code}")
        print(f"  ✓ Total images: {data.get('total', 0)}")
        print(f"  ✓ Items returned: {len(data.get('items', []))}")
        
        if data.get('items'):
            first = data['items'][0]
            print(f"  ✓ First image: ID={first.get('id')}, Type={first.get('type')}")
        
        return {"status": "success", "total": data.get('total', 0), "items": len(data.get('items', []))}
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Connection error: API not reachable at {API_BASE_URL}")
        print("     Make sure the API container is running")
        return {"status": "connection_error"}
    except requests.exceptions.HTTPError as e:
        print(f"  ✗ HTTP error: {e}")
        return {"status": "http_error", "error": str(e)}
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return {"status": "error", "error": str(e)}


def test_image_fits_endpoint(image_id: Optional[int] = None) -> dict:
    """Test the /api/images/{id}/fits endpoint."""
    print("\n" + "=" * 60)
    print("3. Testing /api/images/{id}/fits Endpoint")
    print("=" * 60)
    
    # Get an image ID if not provided
    if image_id is None:
        try:
            response = requests.get(f"{API_BASE_URL}/images", params={"limit": 1})
            response.raise_for_status()
            data = response.json()
            if not data.get('items'):
                print("  ⚠ No images available to test FITS endpoint")
                return {"status": "no_images"}
            image_id = data['items'][0]['id']
            print(f"  Using image ID: {image_id}")
        except Exception as e:
            print(f"  ✗ Could not get image ID: {e}")
            return {"status": "error", "error": str(e)}
    
    try:
        response = requests.get(f"{API_BASE_URL}/images/{image_id}/fits", stream=True)
        
        if response.status_code == 404:
            print(f"  ⚠ Image {image_id} not found or FITS file unavailable")
            print(f"     Response: {response.text[:200]}")
            return {"status": "not_found"}
        
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        print(f"  ✓ Status: {response.status_code}")
        print(f"  ✓ Content-Type: {content_type}")
        
        # Check if it's actually a FITS file (starts with 'SIMPLE' or has FITS-like headers)
        if response.status_code == 200:
            # Read first few bytes to verify it's FITS
            first_bytes = response.content[:80]
            if first_bytes.startswith(b'SIMPLE'):
                print("  ✓ Valid FITS file (starts with 'SIMPLE')")
            else:
                print(f"  ⚠ Response may not be a valid FITS file (first 80 bytes: {first_bytes[:40]})")
            
            # Check size
            content_length = response.headers.get('content-length')
            if content_length:
                size_kb = int(content_length) / 1024
                print(f"  ✓ File size: {size_kb:.2f} KB")
        
        return {"status": "success", "content_type": content_type}
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Connection error: API not reachable at {API_BASE_URL}")
        return {"status": "connection_error"}
    except requests.exceptions.HTTPError as e:
        print(f"  ✗ HTTP error: {e}")
        if hasattr(e.response, 'text'):
            print(f"     Response: {e.response.text[:200]}")
        return {"status": "http_error", "error": str(e)}
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return {"status": "error", "error": str(e)}


def test_image_filters() -> dict:
    """Test filtering options for /api/images endpoint."""
    print("\n" + "=" * 60)
    print("4. Testing Image Filters")
    print("=" * 60)
    
    filters = [
        {"limit": 5, "offset": 0},
        {"limit": 10, "image_type": "image"},
        {"limit": 10, "pbcor": True},
        {"limit": 10, "pbcor": False},
    ]
    
    results = []
    for i, params in enumerate(filters, 1):
        try:
            response = requests.get(f"{API_BASE_URL}/images", params=params)
            response.raise_for_status()
            data = response.json()
            print(f"  ✓ Filter {i} ({params}): {len(data.get('items', []))} items")
            results.append({"filter": params, "count": len(data.get('items', []))})
        except Exception as e:
            print(f"  ✗ Filter {i} failed: {e}")
            results.append({"filter": params, "error": str(e)})
    
    return {"status": "success", "results": results}


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SkyView Functionality Test Suite")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Products DB: {PRODUCTS_DB}")
    print()
    
    # Run tests
    db_result = check_database()
    images_result = test_images_endpoint()
    fits_result = None
    filters_result = None
    
    if images_result.get("status") == "success" and images_result.get("total", 0) > 0:
        fits_result = test_image_fits_endpoint()
        filters_result = test_image_filters()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    print(f"\nDatabase:")
    print(f"  Exists: {'✓' if db_result.get('exists') else '✗'}")
    if db_result.get('exists'):
        print(f"  Images: {db_result.get('image_count', 0)}")
    
    print(f"\nAPI Endpoints:")
    print(f"  /api/images: {'✓' if images_result.get('status') == 'success' else '✗'}")
    if fits_result:
        print(f"  /api/images/{{id}}/fits: {'✓' if fits_result.get('status') == 'success' else '✗'}")
    if filters_result:
        print(f"  Image filters: {'✓' if filters_result.get('status') == 'success' else '✗'}")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("Recommendations")
    print("=" * 60)
    
    if not db_result.get('exists'):
        print("  • Initialize the products database: python scripts/init_databases.py")
        print("  • Create mock data: python scripts/create_mock_dashboard_data.py")
    
    if images_result.get('status') == 'connection_error':
        print("  • Start the API container: cd ops/docker && docker-compose up -d api")
    
    if db_result.get('image_count', 0) == 0:
        print("  • Add images to the database (run pipeline or create mock data)")
    
    if fits_result and fits_result.get('status') == 'not_found':
        print("  • Ensure image paths in database point to valid CASA images or FITS files")
        print("  • Verify CASA is available for on-demand conversion")
    
    print()


if __name__ == "__main__":
    main()

