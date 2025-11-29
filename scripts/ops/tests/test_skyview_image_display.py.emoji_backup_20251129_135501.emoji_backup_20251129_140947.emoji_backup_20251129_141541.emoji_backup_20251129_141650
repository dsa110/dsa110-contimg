#!/opt/miniforge/envs/casa6/bin/python
"""
Test script to verify image display functionality in SkyView.
Tests the full flow: database -> API endpoint -> FITS file serving -> JS9 compatibility
"""

import os
import sys
from pathlib import Path

import requests
from astropy.io import fits

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.api.data_access import _connect

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8010/api")
PRODUCTS_DB = Path(os.getenv("PIPELINE_PRODUCTS_DB", "/data/dsa110-contimg/state/db/products.sqlite3"))


def test_fits_endpoint(image_id: int):
    """Test the /api/images/{id}/fits endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing FITS Endpoint for Image ID {image_id}")
    print(f"{'='*60}")
    
    url = f"{API_BASE_URL}/images/{image_id}/fits"
    
    try:
        # Test HEAD request first
        response = requests.head(url, timeout=10)
        print(f"HEAD request status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"Content-Length: {response.headers.get('content-length', 'N/A')} bytes")
        
        if response.status_code != 200:
            print(f"  ✗ HEAD request failed: {response.status_code}")
            if response.status_code == 404:
                print(f"     Response: {response.text[:200]}")
            return False
        
        # Test GET request (download first 1KB to verify it's FITS)
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()
        
        # Read first 1KB to verify it's a FITS file
        first_chunk = next(response.iter_content(1024))
        
        # Check FITS header (should start with 'SIMPLE')
        if first_chunk.startswith(b'SIMPLE'):
            print(f"  ✓ Valid FITS file (starts with 'SIMPLE')")
        else:
            print(f"  ⚠ First bytes: {first_chunk[:80]}")
            print(f"     May not be a valid FITS file")
        
        # Get full file size
        content_length = response.headers.get('content-length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            print(f"  ✓ File size: {size_mb:.2f} MB")
        
        # Try to open with astropy to verify it's valid
        response.rewind = False
        temp_file = Path("/tmp/test_skyview_fits.fits")
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        try:
            with fits.open(temp_file) as hdul:
                print(f"  ✓ Valid FITS file (astropy can open it)")
                print(f"     HDUs: {len(hdul)}")
                if len(hdul) > 0:
                    hdu = hdul[0]
                    if hasattr(hdu, 'data') and hdu.data is not None:
                        print(f"     Data shape: {hdu.data.shape}")
                        print(f"     Data type: {hdu.data.dtype}")
        except Exception as e:
            print(f"  ✗ astropy failed to open FITS: {e}")
            return False
        finally:
            if temp_file.exists():
                temp_file.unlink()
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Connection error: API not reachable at {API_BASE_URL}")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"  ✗ HTTP error: {e}")
        if hasattr(e.response, 'text'):
            print(f"     Response: {e.response.text[:200]}")
        return False
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_paths():
    """Test that image paths in database point to valid files."""
    print(f"\n{'='*60}")
    print("Testing Image Paths in Database")
    print(f"{'='*60}")
    
    if not PRODUCTS_DB.exists():
        print(f"  ✗ Database not found: {PRODUCTS_DB}")
        return []
    
    try:
        with _connect(PRODUCTS_DB) as conn:
            cur = conn.execute("SELECT id, path FROM images LIMIT 5")
            rows = cur.fetchall()
            
            valid_images = []
            for row in rows:
                image_id = row["id"]
                image_path = row["path"]
                exists = Path(image_path).exists()
                
                status = "✓" if exists else "✗"
                print(f"  {status} ID={image_id}: {Path(image_path).name}")
                print(f"      Path exists: {exists}")
                
                if exists:
                    # Check if it's a FITS file
                    is_fits = image_path.endswith('.fits')
                    print(f"      Is FITS: {is_fits}")
                    
                    if is_fits:
                        # Quick check if it's valid FITS
                        try:
                            with fits.open(image_path, memmap=False) as hdul:
                                print(f"      Valid FITS: ✓")
                                valid_images.append(image_id)
                        except Exception as e:
                            print(f"      Valid FITS: ✗ ({e})")
            
            return valid_images
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return []


def main():
    """Run all image display tests."""
    print("\n" + "="*60)
    print("SkyView Image Display Test Suite")
    print("="*60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Products DB: {PRODUCTS_DB}")
    
    # Test 1: Check image paths
    valid_image_ids = test_image_paths()
    
    if not valid_image_ids:
        print("\n⚠ No valid images found in database")
        print("  Run: python scripts/create_synthetic_images.py")
        return 1
    
    # Test 2: Test FITS endpoint for each valid image
    print(f"\n{'='*60}")
    print("Testing FITS Endpoint")
    print(f"{'='*60}")
    
    results = []
    for image_id in valid_image_ids[:3]:  # Test first 3
        success = test_fits_endpoint(image_id)
        results.append((image_id, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nFITS Endpoint Tests: {passed}/{total} passed")
    for image_id, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  Image ID {image_id}: {status}")
    
    if passed == total:
        print("\n✓ All tests passed! Images should display in SkyView.")
        print("\nTo verify in browser:")
        print("  1. Navigate to: http://localhost:5173/skyview")
        print("  2. Select an image from the ImageBrowser")
        print("  3. Verify JS9 displays the image")
    else:
        print("\n✗ Some tests failed. Check API logs and file paths.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

