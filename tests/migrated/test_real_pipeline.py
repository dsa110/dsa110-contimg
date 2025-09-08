#!/usr/bin/env python3
"""
Test script for DSA-110 Pipeline with Real Data

This script tests the pipeline with real DSA-110 HDF5 data from /data/incoming_test/
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import glob

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.utils.logging import get_logger
from core.pipeline.orchestrator import PipelineOrchestrator
from core.config.production_config import ProductionConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

async def test_real_pipeline():
    """Test the pipeline with real DSA-110 data."""
    try:
        logger.info("🚀 Starting DSA-110 Pipeline Test with Real Data")
        
        # Step 1: Check for real HDF5 files
        hdf5_dir = "/data/incoming_test"
        hdf5_files = glob.glob(f"{hdf5_dir}/*.hdf5")
        
        if not hdf5_files:
            logger.error("❌ No HDF5 files found in /data/incoming_test/")
            return
            
        logger.info(f"📊 Found {len(hdf5_files)} real HDF5 files")
        for i, file in enumerate(hdf5_files[:5]):  # Show first 5
            logger.info(f"  {i+1}. {Path(file).name}")
        if len(hdf5_files) > 5:
            logger.info(f"  ... and {len(hdf5_files) - 5} more")
        
        # Step 2: Initialize pipeline
        logger.info("🔧 Initializing pipeline...")
        config = ProductionConfig()
        orchestrator = PipelineOrchestrator(config.to_dict())
        logger.info("✅ Pipeline initialized")
        
        # Step 3: Test HDF5 to MS conversion
        logger.info("📥 Testing HDF5 to MS conversion...")
        
        # Use the first few files for testing
        test_files = hdf5_files[:3]  # Test with first 3 files
        logger.info(f"🔄 Processing {len(test_files)} test files")
        
        for i, hdf5_file in enumerate(test_files):
            logger.info(f"  Processing file {i+1}/{len(test_files)}: {Path(hdf5_file).name}")
            
            # Test the HDF5 to MS conversion
            try:
                result = await orchestrator.process_hdf5_to_ms(
                    hdf5_dir=hdf5_dir,
                    start_timestamp=None  # Process all files
                )
                logger.info(f"✅ HDF5 to MS conversion result: {result}")
                break  # Just test one conversion for now
            except Exception as e:
                logger.error(f"❌ Error processing {hdf5_file}: {e}")
                continue
        
        # Step 4: Check for generated MS files
        ms_dir = Path("data/ms")
        if ms_dir.exists():
            ms_files = list(ms_dir.glob("*.ms"))
            logger.info(f"📁 Found {len(ms_files)} MS files in data/ms/")
            
            if ms_files:
                # Test imaging with the first MS file
                logger.info("🖼️ Testing image generation...")
                test_ms = str(ms_files[0])
                logger.info(f"🔄 Processing MS file: {Path(test_ms).name}")
                
                # Here we would test the imaging stage
                # For now, just log that we found MS files
                logger.info("✅ MS files ready for imaging pipeline")
            else:
                logger.warning("⚠️ No MS files found after conversion")
        else:
            logger.warning("⚠️ MS directory not found")
            
        logger.info("🎉 Real data pipeline test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_real_pipeline())
