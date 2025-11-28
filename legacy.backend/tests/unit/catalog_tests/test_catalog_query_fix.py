#!/usr/bin/env python3
"""
Test to verify the fix for TypeError in catalog/query.py.

Tests that round() works correctly with both scalar and numpy array inputs.
"""

import numpy as np

from dsa110_contimg.catalog.query import resolve_catalog_path


class TestCatalogQueryTypeFix:
    """Tests for catalog query type handling."""

    def test_scalar_input(self):
        """Test that scalar input is handled correctly."""
        try:
            resolve_catalog_path("nvss", dec_strip=45.5)
        except FileNotFoundError:
            # FileNotFoundError is expected - no catalog file, but no TypeError
            pass

    def test_numpy_array_1d(self):
        """Test that 1D numpy array input is handled correctly."""
        dec_array = np.array([45.5])
        try:
            resolve_catalog_path("nvss", dec_strip=dec_array)
        except FileNotFoundError:
            # FileNotFoundError is expected - no catalog file, but no TypeError
            pass

    def test_numpy_array_2d(self):
        """Test that 2D numpy array input is handled correctly."""
        dec_array_2d = np.array([[45.5], [46.0]])
        try:
            resolve_catalog_path("nvss", dec_strip=dec_array_2d)
        except FileNotFoundError:
            # FileNotFoundError is expected - no catalog file, but no TypeError
            pass

    def test_numpy_scalar_0d(self):
        """Test that 0D numpy array (scalar) input is handled correctly."""
        dec_scalar = np.array(45.5)  # 0D array
        try:
            resolve_catalog_path("nvss", dec_strip=dec_scalar)
        except FileNotFoundError:
            # FileNotFoundError is expected - no catalog file, but no TypeError
            pass
