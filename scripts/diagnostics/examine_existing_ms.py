#!/usr/bin/env python3
"""
Examine Existing MS Structure

This script examines an existing MS file to understand the correct table structure.
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

def examine_existing_ms():
    """Examine an existing MS file to understand the structure."""
    try:
        logger.info("🚀 Examining Existing MS Structure")
        
        # Import CASA
        from casatools import table
        
        # Find an existing MS file
        ms_path = "/data/jfaber/dsa110-contimg/ms_stage1/2025-09-05T03:23:14.ms"
        
        if not os.path.exists(ms_path):
            logger.error(f"❌ MS file not found: {ms_path}")
            return False
        
        logger.info(f"📁 Examining MS file: {ms_path}")
        
        # Open the main table
        main_table_path = os.path.join(ms_path, "MAIN")
        tb = table(main_table_path)
        
        # Get table information
        n_rows = tb.nrows()
        colnames = tb.colnames()
        logger.info(f"✅ Main table: {n_rows} rows, {len(colnames)} columns")
        logger.info(f"Column names: {colnames}")
        
        # Get column descriptions
        logger.info("🔧 Column descriptions:")
        for col in colnames:
            try:
                desc = tb.getcoldesc(col)
                logger.info(f"  {col}: {desc}")
            except Exception as e:
                logger.warning(f"  {col}: Error getting description - {e}")
        
        # Get a sample of data
        logger.info("🔧 Sample data:")
        for col in colnames[:5]:  # First 5 columns
            try:
                sample = tb.getcol(col, 0, min(5, n_rows))
                logger.info(f"  {col}: {sample}")
            except Exception as e:
                logger.warning(f"  {col}: Error getting sample - {e}")
        
        tb.close()
        
        # Check subtables
        logger.info("🔧 Checking subtables:")
        subtable_names = ['ANTENNA', 'SPECTRAL_WINDOW', 'POLARIZATION', 'FIELD', 'OBSERVATION', 'SOURCE', 'HISTORY']
        
        for subtable_name in subtable_names:
            subtable_path = os.path.join(ms_path, subtable_name)
            if os.path.exists(subtable_path):
                try:
                    stb = table(subtable_path)
                    n_rows = stb.nrows()
                    colnames = stb.colnames()
                    logger.info(f"  ✅ {subtable_name}: {n_rows} rows, {len(colnames)} columns")
                    stb.close()
                except Exception as e:
                    logger.warning(f"  ❌ {subtable_name}: Error - {e}")
            else:
                logger.info(f"  ❌ {subtable_name}: Not found")
        
        logger.info("🎉 MS examination completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Examination failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = examine_existing_ms()
    if success:
        print("✅ MS examination completed!")
    else:
        print("❌ MS examination failed!")
