#!/usr/bin/env python3
"""
Test script to verify the fix for TypeError in catalog/query.py.

Tests that round() works correctly with both scalar and numpy array inputs.
"""

import sys
from pathlib import Path

# Add src to path BEFORE importing dsa110_contimg modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
from dsa110_contimg.catalog.query import resolve_catalog_path

print("Testing catalog/query.py TypeError fix...")
print("=" * 70)

# Test 1: Scalar input (should work)
print("\nTest 1: Scalar input")
try:
    result = resolve_catalog_path("nvss", dec_strip=45.5)
    print("✓ Scalar input handled correctly")
except TypeError as e:
    print(f"✗ Scalar input failed: {e}")
except FileNotFoundError:
    print(
        "✓ Scalar input handled correctly (FileNotFoundError expected - no catalog file)"
    )
except Exception as e:
    print(f"✗ Unexpected error: {e}")

# Test 2: NumPy array input (the bug case)
print("\nTest 2: NumPy array input (1D)")
try:
    dec_array = np.array([45.5])
    result = resolve_catalog_path("nvss", dec_strip=dec_array)
    print("✓ NumPy array (1D) input handled correctly")
except TypeError as e:
    print(f"✗ NumPy array (1D) input failed: {e}")
except FileNotFoundError:
    print(
        "✓ NumPy array (1D) input handled correctly (FileNotFoundError expected - no catalog file)"
    )
except Exception as e:
    print(f"✗ Unexpected error: {e}")

# Test 3: NumPy array input (2D, should extract first element)
print("\nTest 3: NumPy array input (2D)")
try:
    dec_array_2d = np.array([[45.5], [46.0]])
    result = resolve_catalog_path("nvss", dec_strip=dec_array_2d)
    print("✓ NumPy array (2D) input handled correctly")
except TypeError as e:
    print(f"✗ NumPy array (2D) input failed: {e}")
except FileNotFoundError:
    print(
        "✓ NumPy array (2D) input handled correctly (FileNotFoundError expected - no catalog file)"
    )
except Exception as e:
    print(f"✗ Unexpected error: {e}")

# Test 4: NumPy scalar (0D array)
print("\nTest 4: NumPy scalar (0D array)")
try:
    dec_scalar = np.array(45.5)  # 0D array
    result = resolve_catalog_path("nvss", dec_strip=dec_scalar)
    print("✓ NumPy scalar (0D) input handled correctly")
except TypeError as e:
    print(f"✗ NumPy scalar (0D) input failed: {e}")
except FileNotFoundError:
    print(
        "✓ NumPy scalar (0D) input handled correctly (FileNotFoundError expected - no catalog file)"
    )
except Exception as e:
    print(f"✗ Unexpected error: {e}")

print("\n" + "=" * 70)
print("All tests completed!")
print("\nNote: FileNotFoundError is expected since we don't have catalog files.")
print("The important thing is that TypeError is NOT raised.")
