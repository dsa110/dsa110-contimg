#!/usr/bin/env python3
"""
Test CASA Table Creation Syntax - Fixed Version

This script tests the correct CASA table creation approach using tabledesc and tablecolumn.
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

def test_casa_table_creation_fixed():
    """Test the correct CASA table creation approach."""
    try:
        logger.info("🚀 Testing CASA Table Creation Syntax - Fixed Version")
        
        # Import CASA
        from casatools import table, tabledesc, tablecolumn
        
        # Test 1: Minimal table creation using tabledesc
        logger.info("🔧 Test 1: Minimal table creation using tabledesc")
        test_table_path = "test_minimal_fixed.table"
        
        if os.path.exists(test_table_path):
            import shutil
            shutil.rmtree(test_table_path)
        
        # Create table descriptor using tabledesc
        td = tabledesc()
        td.addcolumn(tablecolumn('ANTENNA1', 'int'))
        td.addcolumn(tablecolumn('ANTENNA2', 'int'))
        td.addcolumn(tablecolumn('TIME', 'double'))
        td.addcolumn(tablecolumn('DATA', 'complex', 2, [4, 2]))
        
        try:
            tb = table()
            tb.create(
                tablename=test_table_path,
                tabledesc=td,
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
        test_ms_path = "test_ms_fixed.ms"
        
        if os.path.exists(test_ms_path):
            import shutil
            shutil.rmtree(test_ms_path)
        
        # Create MS directory
        os.makedirs(test_ms_path, exist_ok=True)
        main_table_path = os.path.join(test_ms_path, "MAIN")
        
        # Create MS-style table descriptor
        ms_td = tabledesc()
        ms_td.addcolumn(tablecolumn('ANTENNA1', 'int'))
        ms_td.addcolumn(tablecolumn('ANTENNA2', 'int'))
        ms_td.addcolumn(tablecolumn('ARRAY_ID', 'int'))
        ms_td.addcolumn(tablecolumn('DATA_DESC_ID', 'int'))
        ms_td.addcolumn(tablecolumn('EXPOSURE', 'double'))
        ms_td.addcolumn(tablecolumn('FEED1', 'int'))
        ms_td.addcolumn(tablecolumn('FEED2', 'int'))
        ms_td.addcolumn(tablecolumn('FIELD_ID', 'int'))
        ms_td.addcolumn(tablecolumn('FLAG', 'bool', 2, [4, 2]))
        ms_td.addcolumn(tablecolumn('FLAG_CATEGORY', 'bool', 3, [1, 4, 2]))
        ms_td.addcolumn(tablecolumn('FLAG_ROW', 'bool'))
        ms_td.addcolumn(tablecolumn('INTERVAL', 'double'))
        ms_td.addcolumn(tablecolumn('OBSERVATION_ID', 'int'))
        ms_td.addcolumn(tablecolumn('PROCESSOR_ID', 'int'))
        ms_td.addcolumn(tablecolumn('SCAN_NUMBER', 'int'))
        ms_td.addcolumn(tablecolumn('SIGMA', 'float', 1, [2]))
        ms_td.addcolumn(tablecolumn('STATE_ID', 'int'))
        ms_td.addcolumn(tablecolumn('TIME', 'double'))
        ms_td.addcolumn(tablecolumn('TIME_CENTROID', 'double'))
        ms_td.addcolumn(tablecolumn('UVW', 'double', 1, [3]))
        ms_td.addcolumn(tablecolumn('WEIGHT', 'float', 1, [2]))
        ms_td.addcolumn(tablecolumn('DATA', 'complex', 2, [4, 2]))
        
        try:
            tb = table()
            tb.create(
                tablename=main_table_path,
                tabledesc=ms_td,
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
    success = test_casa_table_creation_fixed()
    if success:
        print("✅ CASA table creation syntax is working!")
    else:
        print("❌ CASA table creation syntax needs more fixing!")
