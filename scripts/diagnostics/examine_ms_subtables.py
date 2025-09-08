#!/usr/bin/env python3
"""
Examine MS Subtables Structure

This script examines the subtables of an existing MS file to understand the structure.
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

def examine_ms_subtables():
    """Examine MS subtables to understand the structure."""
    try:
        logger.info("🚀 Examining MS Subtables Structure")
        
        # Import CASA
        from casatools import table
        
        # Find an existing MS file
        ms_path = "/data/jfaber/dsa110-contimg/ms_stage1/2025-09-05T03:23:14.ms"
        
        if not os.path.exists(ms_path):
            logger.error(f"❌ MS file not found: {ms_path}")
            return False
        
        logger.info(f"📁 Examining MS file: {ms_path}")
        
        # Check subtables
        subtable_names = ['ANTENNA', 'SPECTRAL_WINDOW', 'POLARIZATION', 'FIELD', 'OBSERVATION', 'SOURCE', 'HISTORY']
        
        for subtable_name in subtable_names:
            subtable_path = os.path.join(ms_path, subtable_name)
            if os.path.exists(subtable_path):
                try:
                    logger.info(f"🔧 Examining {subtable_name} table:")
                    stb = table(subtable_path)
                    n_rows = stb.nrows()
                    colnames = stb.colnames()
                    logger.info(f"  ✅ {subtable_name}: {n_rows} rows, {len(colnames)} columns")
                    logger.info(f"  Column names: {colnames}")
                    
                    # Get column descriptions for first few columns
                    logger.info(f"  Column descriptions:")
                    for col in colnames[:3]:  # First 3 columns
                        try:
                            desc = stb.getcoldesc(col)
                            logger.info(f"    {col}: {desc}")
                        except Exception as e:
                            logger.warning(f"    {col}: Error getting description - {e}")
                    
                    # Get sample data for first few columns
                    logger.info(f"  Sample data:")
                    for col in colnames[:3]:  # First 3 columns
                        try:
                            sample = stb.getcol(col, 0, min(3, n_rows))
                            logger.info(f"    {col}: {sample}")
                        except Exception as e:
                            logger.warning(f"    {col}: Error getting sample - {e}")
                    
                    stb.close()
                    logger.info("")
                    
                except Exception as e:
                    logger.warning(f"  ❌ {subtable_name}: Error - {e}")
            else:
                logger.info(f"  ❌ {subtable_name}: Not found")
        
        logger.info("🎉 MS subtables examination completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Examination failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = examine_ms_subtables()
    if success:
        print("✅ MS subtables examination completed!")
    else:
        print("❌ MS subtables examination failed!")
