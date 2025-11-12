#!/usr/bin/env python3
"""
Simple MS Creation Test

This script tests simple MS creation to debug data shape issues.
"""

import os
import sys
import logging
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_simple_ms_creation():
    """Test simple MS creation with minimal data."""
    try:
        logger.info("🚀 Testing Simple MS Creation")
        
        # Import CASA
        from casatools import table
        
        # Test 1: Very simple table
        logger.info("🔧 Test 1: Very simple table")
        test_table_path = "test_simple.table"
        
        if os.path.exists(test_table_path):
            import shutil
            shutil.rmtree(test_table_path)
        
        # Very simple table descriptor
        tabledesc = {
            'ANTENNA1': {'valueType': 'int', 'ndim': 0, 'option': 0},
            'ANTENNA2': {'valueType': 'int', 'ndim': 0, 'option': 0},
            'TIME': {'valueType': 'double', 'ndim': 0, 'option': 0},
            'DATA': {'valueType': 'complex', 'ndim': 2, 'option': 0, 'shape': [4, 2]}
        }
        
        try:
            tb = table()
            tb.create(
                tablename=test_table_path,
                tabledesc=tabledesc,
                nrow=10
            )
            
            # Add simple test data
            tb.putcol('ANTENNA1', np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
            tb.putcol('ANTENNA2', np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 0]))
            tb.putcol('TIME', np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]))
            tb.putcol('DATA', np.ones((10, 4, 2), dtype=complex))
            
            tb.close()
            logger.info("✅ Test 1: Very simple table successful")
            
        except Exception as e:
            logger.error(f"❌ Test 1 failed: {e}")
            return False
        
        # Test 2: Test with HDF5-like data shapes
        logger.info("🔧 Test 2: HDF5-like data shapes")
        test_table_path2 = "test_hdf5_shapes.table"
        
        if os.path.exists(test_table_path2):
            import shutil
            shutil.rmtree(test_table_path2)
        
        # HDF5-like table descriptor
        tabledesc2 = {
            'ANTENNA1': {'valueType': 'int', 'ndim': 0, 'option': 0},
            'ANTENNA2': {'valueType': 'int', 'ndim': 0, 'option': 0},
            'TIME': {'valueType': 'double', 'ndim': 0, 'option': 0},
            'UVW': {'valueType': 'double', 'ndim': 1, 'option': 0, 'shape': [3]},
            'FLAG': {'valueType': 'boolean', 'ndim': 2, 'option': 0, 'shape': [4, 2]},
            'WEIGHT': {'valueType': 'float', 'ndim': 1, 'option': 0, 'shape': [2]},
            'DATA': {'valueType': 'complex', 'ndim': 2, 'option': 0, 'shape': [4, 2]}
        }
        
        try:
            tb = table()
            tb.create(
                tablename=test_table_path2,
                tabledesc=tabledesc2,
                nrow=10
            )
            
            # Add HDF5-like test data
            tb.putcol('ANTENNA1', np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
            tb.putcol('ANTENNA2', np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 0]))
            tb.putcol('TIME', np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]))
            tb.putcol('UVW', np.random.random((10, 3)))
            tb.putcol('FLAG', np.zeros((10, 4, 2), dtype=bool))
            tb.putcol('WEIGHT', np.ones((10, 2), dtype=float))
            tb.putcol('DATA', np.ones((10, 4, 2), dtype=complex))
            
            tb.close()
            logger.info("✅ Test 2: HDF5-like data shapes successful")
            
        except Exception as e:
            logger.error(f"❌ Test 2 failed: {e}")
            return False
        
        # Test 3: Test with actual HDF5 data shapes
        logger.info("🔧 Test 3: Actual HDF5 data shapes")
        test_table_path3 = "test_actual_hdf5.table"
        
        if os.path.exists(test_table_path3):
            import shutil
            shutil.rmtree(test_table_path3)
        
        # Actual HDF5 data shapes
        n_freqs = 48
        n_pols = 2
        n_rows = 100  # Smaller for testing
        
        tabledesc3 = {
            'ANTENNA1': {'valueType': 'int', 'ndim': 0, 'option': 0},
            'ANTENNA2': {'valueType': 'int', 'ndim': 0, 'option': 0},
            'TIME': {'valueType': 'double', 'ndim': 0, 'option': 0},
            'UVW': {'valueType': 'double', 'ndim': 1, 'option': 0, 'shape': [3]},
            'FLAG': {'valueType': 'boolean', 'ndim': 2, 'option': 0, 'shape': [n_freqs, n_pols]},
            'WEIGHT': {'valueType': 'float', 'ndim': 1, 'option': 0, 'shape': [n_pols]},
            'DATA': {'valueType': 'complex', 'ndim': 2, 'option': 0, 'shape': [n_freqs, n_pols]}
        }
        
        try:
            tb = table()
            tb.create(
                tablename=test_table_path3,
                tabledesc=tabledesc3,
                nrow=n_rows
            )
            
            # Add actual HDF5-like test data
            tb.putcol('ANTENNA1', np.random.randint(0, 10, n_rows))
            tb.putcol('ANTENNA2', np.random.randint(0, 10, n_rows))
            tb.putcol('TIME', np.random.random(n_rows))
            tb.putcol('UVW', np.random.random((n_rows, 3)))
            tb.putcol('FLAG', np.zeros((n_rows, n_freqs, n_pols), dtype=bool))
            tb.putcol('WEIGHT', np.ones((n_rows, n_pols), dtype=float))
            tb.putcol('DATA', np.ones((n_rows, n_freqs, n_pols), dtype=complex))
            
            tb.close()
            logger.info("✅ Test 3: Actual HDF5 data shapes successful")
            
        except Exception as e:
            logger.error(f"❌ Test 3 failed: {e}")
            return False
        
        logger.info("🎉 All simple MS creation tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_simple_ms_creation()
    if success:
        print("✅ Simple MS creation is working!")
    else:
        print("❌ Simple MS creation needs fixing!")