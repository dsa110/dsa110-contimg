#!/usr/bin/env python3
"""
Test CASA TAQL Approach

This script tests using CASA tableutil.defaulttaql for table creation.
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

def test_casa_taql_approach():
    """Test CASA table creation using TAQL approach."""
    try:
        logger.info("🚀 Testing CASA TAQL Approach")
        
        # Import CASA
        from casatools import table, tableutil
        
        # Test 1: Simple table using TAQL
        logger.info("🔧 Test 1: Simple table using TAQL")
        test_table_path = "test_taql_simple.table"
        
        if os.path.exists(test_table_path):
            import shutil
            shutil.rmtree(test_table_path)
        
        try:
            # Create table using TAQL
            tb = table()
            td = tableutil.defaulttaql('CREATE TABLE MAIN (DATA COMPLEX, TIME DOUBLE, ANTENNA1 INT, ANTENNA2 INT, UVW DOUBLE[3])')
            tb.create(test_table_path, td)
            
            # Add some test data
            tb.addrows(10)
            tb.putcol('ANTENNA1', np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
            tb.putcol('ANTENNA2', np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 0]))
            tb.putcol('TIME', np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]))
            tb.putcol('UVW', np.random.random((10, 3)))
            tb.putcol('DATA', np.ones((10, 1, 1), dtype=complex))
            
            tb.close()
            logger.info("✅ Test 1: Simple TAQL table successful")
            
        except Exception as e:
            logger.error(f"❌ Test 1 failed: {e}")
            return False
        
        # Test 2: MS-like table using TAQL
        logger.info("🔧 Test 2: MS-like table using TAQL")
        test_ms_path = "test_taql_ms.ms"
        
        if os.path.exists(test_ms_path):
            import shutil
            shutil.rmtree(test_ms_path)
        
        try:
            # Create MS directory
            os.makedirs(test_ms_path, exist_ok=True)
            main_table_path = os.path.join(test_ms_path, "MAIN")
            
            # Create main table using TAQL
            tb = table()
            td = tableutil.defaulttaql('CREATE TABLE MAIN (DATA COMPLEX, TIME DOUBLE, ANTENNA1 INT, ANTENNA2 INT, UVW DOUBLE[3], FLAG BOOLEAN, WEIGHT FLOAT)')
            tb.create(main_table_path, td)
            
            # Add some test data
            tb.addrows(10)
            tb.putcol('ANTENNA1', np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
            tb.putcol('ANTENNA2', np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 0]))
            tb.putcol('TIME', np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]))
            tb.putcol('UVW', np.random.random((10, 3)))
            tb.putcol('FLAG', np.zeros(10, dtype=bool))
            tb.putcol('WEIGHT', np.ones(10, dtype=float))
            tb.putcol('DATA', np.ones((10, 1, 1), dtype=complex))
            
            tb.close()
            logger.info("✅ Test 2: MS-like TAQL table successful")
            
        except Exception as e:
            logger.error(f"❌ Test 2 failed: {e}")
            return False
        
        # Test 3: Check if we can read the created tables
        logger.info("🔧 Test 3: Reading created tables")
        
        try:
            # Read simple table
            tb = table(test_table_path)
            n_rows = tb.nrows()
            colnames = tb.colnames()
            logger.info(f"✅ Simple table: {n_rows} rows, {len(colnames)} columns")
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
        
        logger.info("🎉 All CASA TAQL tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_casa_taql_approach()
    if success:
        print("✅ CASA TAQL approach is working!")
    else:
        print("❌ CASA TAQL approach needs fixing!")
