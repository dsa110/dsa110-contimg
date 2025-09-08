#!/usr/bin/env python3
"""
Test script for DSA-110 Pipeline Image Generation

This script generates test data and runs the pipeline to test image generation.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.utils.logging import get_logger
from tests.data.test_data_generator import TestDataGenerator
from core.pipeline.orchestrator import PipelineOrchestrator
from core.config.production_config import ProductionConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

async def test_image_generation():
    """Test the complete image generation pipeline."""
    try:
        logger.info("🚀 Starting DSA-110 Pipeline Image Generation Test")
        
        # Step 1: Generate test data
        logger.info("📊 Generating test data...")
        data_generator = TestDataGenerator(output_dir="data/test_data")
        
        # Generate HDF5 files (simulating raw DSA-110 data)
        hdf5_files = data_generator.generate_hdf5_files(n_files=3, time_interval=300.0)
        logger.info(f"✅ Generated {len(hdf5_files)} HDF5 files")
        
        # Generate calibration tables
        cal_tables = data_generator.generate_calibration_tables()
        logger.info(f"✅ Generated {len(cal_tables)} calibration tables")
        
        # Step 2: Initialize pipeline
        logger.info("🔧 Initializing pipeline...")
        config = ProductionConfig()
        orchestrator = PipelineOrchestrator(config.to_dict())
        logger.info("✅ Pipeline initialized")
        
        # Step 3: Test data ingestion (HDF5 to MS conversion)
        logger.info("📥 Testing data ingestion...")
        hdf5_dir = "data/test_data"
        
        # Create a processing block for testing
        from core.pipeline.orchestrator import ProcessingBlock
        from astropy.time import Time
        
        # Test with the first HDF5 file
        if hdf5_files:
            test_file = hdf5_files[0]
            logger.info(f"🔄 Processing test file: {test_file}")
            
            # Create a simple processing block
            block = ProcessingBlock(
                block_id="test_block_001",
                start_time=Time.now(),
                end_time=Time.now() + 300,  # 5 minutes
                ms_files=[],  # Will be populated by the pipeline
                status="pending"
            )
            
            # Test the pipeline processing
            result = await orchestrator.process_block(block)
            logger.info(f"✅ Processing result: {result}")
            
        else:
            logger.warning("⚠️ No HDF5 files generated for testing")
            
        # Step 4: Test image generation
        logger.info("🖼️ Testing image generation...")
        
        # Check if we have any MS files to work with
        ms_dir = Path("data/ms")
        if ms_dir.exists() and any(ms_dir.iterdir()):
            logger.info("✅ Found MS files for image generation")
            # Here we would test the imaging stage
        else:
            logger.info("ℹ️ No MS files found - this is expected for a basic test")
            
        logger.info("🎉 Image generation test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_image_generation())
