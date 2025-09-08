#!/usr/bin/env python3
"""
Test CASA Table Imports

This script checks what's available in the CASA table module.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_casa_table_imports():
    """Test what's available in CASA table module."""
    try:
        logger.info("🚀 Testing CASA Table Imports")
        
        # Import CASA table
        from casatools import table
        logger.info("✅ Successfully imported table from casatools")
        
        # Check what's available in casatools
        import casatools
        logger.info(f"Available in casatools: {dir(casatools)}")
        
        # Check what's available in table
        tb = table()
        logger.info(f"Available in table: {dir(tb)}")
        
        # Check table methods
        methods = [method for method in dir(tb) if not method.startswith('_')]
        logger.info(f"Table methods: {methods}")
        
        # Check if there are any table creation examples
        logger.info("🔧 Checking for table creation examples...")
        
        # Try to find table creation methods
        if hasattr(tb, 'create'):
            logger.info("✅ table.create method exists")
            # Check create method signature
            import inspect
            sig = inspect.signature(tb.create)
            logger.info(f"create method signature: {sig}")
        
        if hasattr(tb, 'addrows'):
            logger.info("✅ table.addrows method exists")
        
        if hasattr(tb, 'putcol'):
            logger.info("✅ table.putcol method exists")
        
        if hasattr(tb, 'putcell'):
            logger.info("✅ table.putcell method exists")
        
        # Check if there are any table descriptor classes
        logger.info("🔧 Checking for table descriptor classes...")
        
        # Try to import from different locations
        try:
            from casatools import tabledesc
            logger.info("✅ tabledesc available in casatools")
        except ImportError:
            logger.info("❌ tabledesc not available in casatools")
        
        try:
            from casatools import tablecolumn
            logger.info("✅ tablecolumn available in casatools")
        except ImportError:
            logger.info("❌ tablecolumn not available in casatools")
        
        try:
            from casatools.table import tabledesc
            logger.info("✅ tabledesc available in casatools.table")
        except ImportError:
            logger.info("❌ tabledesc not available in casatools.table")
        
        try:
            from casatools.table import tablecolumn
            logger.info("✅ tablecolumn available in casatools.table")
        except ImportError:
            logger.info("❌ tablecolumn not available in casatools.table")
        
        # Check if there are any other table-related modules
        try:
            import casatools.table
            logger.info(f"Available in casatools.table: {dir(casatools.table)}")
        except Exception as e:
            logger.info(f"❌ Error accessing casatools.table: {e}")
        
        logger.info("🎉 CASA table import test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_casa_table_imports()
    if success:
        print("✅ CASA table import test completed!")
    else:
        print("❌ CASA table import test failed!")
