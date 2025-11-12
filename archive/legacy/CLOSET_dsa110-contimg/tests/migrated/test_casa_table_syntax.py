#!/usr/bin/env python3
"""
Test CASA Table Creation Syntax

This script tests different CASA table creation approaches to find the correct syntax.
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

def test_casa_table_creation():
    """Test different CASA table creation approaches."""
    try:
        logger.info("🚀 Testing CASA Table Creation Syntax")
        
        # Import CASA
        from casatools import table
        
        # Test 1: Minimal table creation
        logger.info("🔧 Test 1: Minimal table creation")
        test_table_path = "test_minimal.table"
        
        if os.path.exists(test_table_path):
            import shutil
            shutil.rmtree(test_table_path)
        
        # Create minimal table descriptor
        tabledesc = {
            'ANTENNA1': {'TYPE': 'INT'},
            'ANTENNA2': {'TYPE': 'INT'},
            'TIME': {'TYPE': 'DOUBLE'},
            'DATA': {'TYPE': 'COMPLEX', 'NDIM': 2, 'SHAPE': [4, 2]}
        }
        
        try:
            tb = table()
            tb.create(
                tablename=test_table_path,
                tabledesc=tabledesc,
                nrow=10
            )
            
            # Add some test data
            tb.putcol('ANTENNA1', np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
            tb.putcol('ANTENNA2', np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 0]))
            tb.putcol('TIME', np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]))
            tb.putcol('DATA', np.ones((10, 4, 2), dtype=complex))
            
            tb.close()
            logger.info("✅ Test 1: Minimal table creation successful")
            
        except Exception as e:
            logger.error(f"❌ Test 1 failed: {e}")
            return False
        
        # Test 2: MS-style table creation
        logger.info("🔧 Test 2: MS-style table creation")
        test_ms_path = "test_ms.ms"
        
        if os.path.exists(test_ms_path):
            import shutil
            shutil.rmtree(test_ms_path)
        
        # Create MS directory
        os.makedirs(test_ms_path, exist_ok=True)
        main_table_path = os.path.join(test_ms_path, "MAIN")
        
        # MS-style table descriptor
        ms_tabledesc = {
            'ANTENNA1': {'TYPE': 'INT', 'NDIM': 0},
            'ANTENNA2': {'TYPE': 'INT', 'NDIM': 0},
            'ARRAY_ID': {'TYPE': 'INT', 'NDIM': 0},
            'DATA_DESC_ID': {'TYPE': 'INT', 'NDIM': 0},
            'EXPOSURE': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'FEED1': {'TYPE': 'INT', 'NDIM': 0},
            'FEED2': {'TYPE': 'INT', 'NDIM': 0},
            'FIELD_ID': {'TYPE': 'INT', 'NDIM': 0},
            'FLAG': {'TYPE': 'BOOL', 'NDIM': 2, 'SHAPE': [4, 2]},
            'FLAG_CATEGORY': {'TYPE': 'BOOL', 'NDIM': 3, 'SHAPE': [1, 4, 2]},
            'FLAG_ROW': {'TYPE': 'BOOL', 'NDIM': 0},
            'INTERVAL': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'OBSERVATION_ID': {'TYPE': 'INT', 'NDIM': 0},
            'PROCESSOR_ID': {'TYPE': 'INT', 'NDIM': 0},
            'SCAN_NUMBER': {'TYPE': 'INT', 'NDIM': 0},
            'SIGMA': {'TYPE': 'FLOAT', 'NDIM': 1, 'SHAPE': [2]},
            'STATE_ID': {'TYPE': 'INT', 'NDIM': 0},
            'TIME': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'TIME_CENTROID': {'TYPE': 'DOUBLE', 'NDIM': 0},
            'UVW': {'TYPE': 'DOUBLE', 'NDIM': 1, 'SHAPE': [3]},
            'WEIGHT': {'TYPE': 'FLOAT', 'NDIM': 1, 'SHAPE': [2]},
            'DATA': {'TYPE': 'COMPLEX', 'NDIM': 2, 'SHAPE': [4, 2]}
        }
        
        try:
            tb = table()
            tb.create(
                tablename=main_table_path,
                tabledesc=ms_tabledesc,
                nrow=10
            )
            
            # Add some test data
            tb.putcol('ANTENNA1', np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
            tb.putcol('ANTENNA2', np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 0]))
            tb.putcol('ARRAY_ID', np.zeros(10, dtype=int))
            tb.putcol('DATA_DESC_ID', np.zeros(10, dtype=int))
            tb.putcol('EXPOSURE', np.ones(10, dtype=float))
            tb.putcol('FEED1', np.zeros(10, dtype=int))
            tb.putcol('FEED2', np.zeros(10, dtype=int))
            tb.putcol('FIELD_ID', np.zeros(10, dtype=int))
            tb.putcol('FLAG', np.zeros((10, 4, 2), dtype=bool))
            tb.putcol('FLAG_CATEGORY', np.zeros((10, 1, 4, 2), dtype=bool))
            tb.putcol('FLAG_ROW', np.zeros(10, dtype=bool))
            tb.putcol('INTERVAL', np.ones(10, dtype=float))
            tb.putcol('OBSERVATION_ID', np.zeros(10, dtype=int))
            tb.putcol('PROCESSOR_ID', np.zeros(10, dtype=int))
            tb.putcol('SCAN_NUMBER', np.ones(10, dtype=int))
            tb.putcol('SIGMA', np.ones((10, 2), dtype=float))
            tb.putcol('STATE_ID', np.zeros(10, dtype=int))
            tb.putcol('TIME', np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]))
            tb.putcol('TIME_CENTROID', np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]))
            tb.putcol('UVW', np.random.random((10, 3)))
            tb.putcol('WEIGHT', np.ones((10, 2), dtype=float))
            tb.putcol('DATA', np.ones((10, 4, 2), dtype=complex))
            
            tb.close()
            logger.info("✅ Test 2: MS-style table creation successful")
            
        except Exception as e:
            logger.error(f"❌ Test 2 failed: {e}")
            return False
        
        # Test 3: Check if we can read the created tables
        logger.info("🔧 Test 3: Reading created tables")
        
        try:
            # Read minimal table
            tb = table(test_table_path)
            n_rows = tb.nrows()
            colnames = tb.colnames()
            logger.info(f"✅ Minimal table: {n_rows} rows, {len(colnames)} columns")
            tb.close()
            
            # Read MS table
            tb = table(main_table_path)
            n_rows = tb.nrows()
            colnames = tb.colnames()
            logger.info(f"✅ MS table: {n_rows} rows, {len(colnames)} columns")
            tb.close()
            
        except Exception as e:
            logger.error(f"❌ Test 3 failed: {e}")
            return False
        
        logger.info("🎉 All CASA table creation tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_casa_table_creation()
    if success:
        print("✅ CASA table creation syntax is working!")
    else:
        print("❌ CASA table creation syntax needs fixing!")
