#!/usr/bin/env python3
"""
Direct test of SkyView functionality without requiring API to be running.
Tests database queries, image path resolution, and FITS conversion logic.
"""

import sys
import os
from pathlib import Path
import sqlite3
from typing import Optional, List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.api.image_utils import get_fits_path, is_casa_image
from dsa110_contimg.api.data_access import _connect

PRODUCTS_DB = Path(os.getenv("PIPELINE_PRODUCTS_DB", "/data/dsa110-contimg/state/products.sqlite3"))


def test_database_images() -> Dict:
    """Test database image queries."""
    print("=" * 60)
    print("1. Database Image Queries")
    print("=" * 60)
    
    if not PRODUCTS_DB.exists():
        print(f"  ✗ Database not found: {PRODUCTS_DB}")
        return {"status": "error", "message": "Database not found"}
    
    try:
        with _connect(PRODUCTS_DB) as conn:
            # Get all images
            cur = conn.execute("""
                SELECT id, path, type, pbcor, ms_path, created_at, 
                       beam_major_arcsec, noise_jy
                FROM images
                ORDER BY id
                LIMIT 10
            """)
            rows = cur.fetchall()
            
            print(f"  ✓ Found {len(rows)} images in database")
            
            results = []
            for row in rows:
                image_info = {
                    "id": row["id"],
                    "path": row["path"],
                    "type": row["type"],
                    "pbcor": bool(row["pbcor"]) if row["pbcor"] is not None else None,
                    "ms_path": row["ms_path"],
                    "exists": Path(row["path"]).exists(),
                }
                results.append(image_info)
                
                status = "✓" if image_info["exists"] else "✗"
                print(f"  {status} ID={image_info['id']}: {Path(image_info['path']).name}")
                print(f"      Type: {image_info['type']}, PBcor: {image_info['pbcor']}")
                print(f"      Exists: {image_info['exists']}")
            
            return {"status": "success", "images": results, "count": len(rows)}
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def test_image_path_resolution() -> Dict:
    """Test image path resolution and FITS conversion logic."""
    print("\n" + "=" * 60)
    print("2. Image Path Resolution & FITS Conversion")
    print("=" * 60)
    
    if not PRODUCTS_DB.exists():
        print("  ⚠ Skipping - database not found")
        return {"status": "skipped"}
    
    try:
        with _connect(PRODUCTS_DB) as conn:
            cur = conn.execute("SELECT id, path FROM images LIMIT 5")
            rows = cur.fetchall()
            
            if not rows:
                print("  ⚠ No images to test")
                return {"status": "no_images"}
            
            results = []
            for row in rows:
                image_id = row["id"]
                image_path = row["path"]
                
                print(f"\n  Testing image ID={image_id}:")
                print(f"    Path: {image_path}")
                
                # Check if path exists
                path_obj = Path(image_path)
                exists = path_obj.exists()
                is_dir = path_obj.is_dir()
                is_fits = image_path.endswith('.fits')
                is_casa = is_casa_image(image_path) if is_dir else False
                
                print(f"    Exists: {exists}")
                print(f"    Is directory: {is_dir}")
                print(f"    Is FITS: {is_fits}")
                print(f"    Is CASA: {is_casa}")
                
                # Test FITS path resolution
                fits_path = get_fits_path(image_path)
                fits_exists = Path(fits_path).exists() if fits_path else False
                
                print(f"    FITS path: {fits_path or 'None'}")
                print(f"    FITS exists: {fits_exists}")
                
                # Check for .fits extension
                if image_path.endswith('.fits'):
                    expected_fits = image_path
                else:
                    expected_fits = image_path + '.fits'
                
                results.append({
                    "id": image_id,
                    "path": image_path,
                    "exists": exists,
                    "is_casa": is_casa,
                    "is_fits": is_fits,
                    "fits_path": fits_path,
                    "fits_exists": fits_exists,
                    "expected_fits": expected_fits,
                })
            
            return {"status": "success", "results": results}
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def test_api_endpoint_logic() -> Dict:
    """Test the logic that would be used by API endpoints."""
    print("\n" + "=" * 60)
    print("3. API Endpoint Logic Simulation")
    print("=" * 60)
    
    if not PRODUCTS_DB.exists():
        print("  ⚠ Skipping - database not found")
        return {"status": "skipped"}
    
    try:
        with _connect(PRODUCTS_DB) as conn:
            # Simulate /api/images endpoint
            print("\n  Simulating GET /api/images:")
            
            # Test with filters
            filters = [
                {},
                {"image_type": "5min"},
                {"pbcor": True},
                {"limit": 3},
            ]
            
            for i, filter_params in enumerate(filters, 1):
                where_clauses = []
                params = []
                
                if "image_type" in filter_params:
                    where_clauses.append("type = ?")
                    params.append(filter_params["image_type"])
                
                if "pbcor" in filter_params:
                    where_clauses.append("pbcor = ?")
                    params.append(1 if filter_params["pbcor"] else 0)
                
                where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
                limit = filter_params.get("limit", 10)
                
                query = f"SELECT COUNT(*) as total FROM images{where_sql}"
                total = conn.execute(query, params).fetchone()["total"]
                
                query = f"SELECT id, path, type FROM images{where_sql} LIMIT ?"
                params.append(limit)
                items = conn.execute(query, params).fetchall()
                
                print(f"    Filter {i} {filter_params}: {len(items)}/{total} images")
            
            # Simulate /api/images/{id}/fits endpoint
            print("\n  Simulating GET /api/images/{id}/fits:")
            
            cur = conn.execute("SELECT id, path FROM images LIMIT 3")
            rows = cur.fetchall()
            
            for row in rows:
                image_id = row["id"]
                image_path = row["path"]
                
                # This is what the API endpoint does
                fits_path = get_fits_path(image_path)
                
                if fits_path and Path(fits_path).exists():
                    status = "✓"
                    message = f"FITS file available: {Path(fits_path).name}"
                else:
                    status = "✗"
                    message = "FITS file not found (conversion may be needed)"
                
                print(f"    {status} Image {image_id}: {message}")
            
            return {"status": "success"}
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def main():
    """Run all direct tests."""
    print("\n" + "=" * 60)
    print("SkyView Direct Functionality Test")
    print("=" * 60)
    print(f"Products DB: {PRODUCTS_DB}")
    print()
    
    # Run tests
    db_result = test_database_images()
    path_result = test_image_path_resolution()
    api_result = test_api_endpoint_logic()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    print(f"\nDatabase Queries: {'✓' if db_result.get('status') == 'success' else '✗'}")
    if db_result.get('status') == 'success':
        existing = sum(1 for img in db_result.get('images', []) if img.get('exists'))
        total = len(db_result.get('images', []))
        print(f"  Images with valid paths: {existing}/{total}")
    
    print(f"\nPath Resolution: {'✓' if path_result.get('status') == 'success' else '✗'}")
    if path_result.get('status') == 'success':
        results = path_result.get('results', [])
        fits_available = sum(1 for r in results if r.get('fits_exists'))
        print(f"  FITS files available: {fits_available}/{len(results)}")
    
    print(f"\nAPI Logic: {'✓' if api_result.get('status') == 'success' else '✗'}")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("Recommendations")
    print("=" * 60)
    
    if db_result.get('status') == 'success':
        images = db_result.get('images', [])
        missing = [img for img in images if not img.get('exists')]
        if missing:
            print(f"  • {len(missing)} image paths in database do not exist on filesystem")
            print("    Update database with correct paths or ensure images are accessible")
    
    if path_result.get('status') == 'success':
        results = path_result.get('results', [])
        needs_conversion = [r for r in results if r.get('is_casa') and not r.get('fits_exists')]
        if needs_conversion:
            print(f"  • {len(needs_conversion)} CASA images need FITS conversion")
            print("    Conversion will happen on-demand when accessed via API")
    
    print("\n  • To test full functionality, start API container:")
    print("    cd ops/docker && docker-compose up -d api")
    print("  • Then access SkyView page at: http://localhost:5173/skyview")
    print()


if __name__ == "__main__":
    main()

