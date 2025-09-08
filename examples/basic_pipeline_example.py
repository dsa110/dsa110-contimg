#!/usr/bin/env python3
"""
Basic pipeline example for DSA-110 continuum imaging.

This example demonstrates how to use the new unified pipeline architecture
for processing MS files through the complete pipeline.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.pipeline import PipelineOrchestrator, ProcessingBlock
from core.utils.logging import setup_logging, get_logger
from core.utils.config_loader import load_pipeline_config
from core.data_ingestion.ms_creation import MSCreationManager
from astropy.time import Time

logger = get_logger(__name__)


async def create_test_data(config):
    """Create test MS files for the example."""
    logger.info("Creating test MS files...")
    
    ms_manager = MSCreationManager(config)
    
    # Create test MS files
    test_ms_files = []
    for i in range(3):
        ms_path = f"test_data/ms_stage1/drift_20230101T000000_{i:02d}.ms"
        os.makedirs(os.path.dirname(ms_path), exist_ok=True)
        
        start_time = Time('2023-01-01T00:00:00', format='isot', scale='utc')
        end_time = Time('2023-01-01T00:05:00', format='isot', scale='utc')
        
        success = await ms_manager.create_test_ms(
            ms_path, start_time, end_time,
            n_antennas=5, n_frequencies=16, n_times=10
        )
        
        if success:
            test_ms_files.append(ms_path)
            logger.info(f"Created test MS: {ms_path}")
        else:
            logger.error(f"Failed to create test MS: {ms_path}")
    
    return test_ms_files


async def run_pipeline_example():
    """Run a basic pipeline example."""
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_pipeline_config(environment="development")
        
        # Set up logging
        setup_logging(config['paths']['log_dir'], 'example', logging.INFO)
        
        # Create test data
        test_ms_files = await create_test_data(config)
        
        if not test_ms_files:
            logger.error("No test MS files created")
            return
        
        # Initialize orchestrator
        logger.info("Initializing pipeline orchestrator...")
        orchestrator = PipelineOrchestrator(config)
        
        # Create a processing block
        block_end_time = Time('2023-01-01T00:15:00', format='isot', scale='utc')
        block = orchestrator.create_processing_block(block_end_time, test_ms_files)
        
        logger.info(f"Created processing block: {block.block_id}")
        logger.info(f"Block time range: {block.start_time.iso} to {block.end_time.iso}")
        logger.info(f"MS files: {len(block.ms_files)}")
        
        # Process the block
        logger.info("Processing block...")
        result = await orchestrator.process_block(block)
        
        # Report results
        if result.success:
            logger.info("✅ Block processing completed successfully!")
            logger.info(f"Processing time: {result.processing_time:.1f} seconds")
            logger.info(f"Output files: {list(result.output_files.keys())}")
        else:
            logger.error("❌ Block processing failed!")
            logger.error(f"Errors: {result.errors}")
        
        return result
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


async def run_batch_processing_example():
    """Run a batch processing example."""
    try:
        # Load configuration
        logger.info("Loading configuration for batch processing...")
        config = load_pipeline_config(environment="development")
        
        # Set up logging
        setup_logging(config['paths']['log_dir'], 'batch_example', logging.INFO)
        
        # Create test data
        test_ms_files = await create_test_data(config)
        
        if not test_ms_files:
            logger.error("No test MS files created")
            return
        
        # Initialize orchestrator
        logger.info("Initializing pipeline orchestrator...")
        orchestrator = PipelineOrchestrator(config)
        
        # Find blocks for batch processing
        logger.info("Finding MS blocks for batch processing...")
        blocks_dict = orchestrator.find_ms_blocks_for_batch(
            start_time_iso='2023-01-01T00:00:00',
            end_time_iso='2023-01-01T00:30:00'
        )
        
        if not blocks_dict:
            logger.warning("No MS blocks found for batch processing")
            return
        
        logger.info(f"Found {len(blocks_dict)} blocks for processing")
        
        # Process blocks
        successful_blocks = 0
        total_blocks = len(blocks_dict)
        
        for block_end_time, ms_files in blocks_dict.items():
            try:
                block = orchestrator.create_processing_block(block_end_time, ms_files)
                logger.info(f"Processing block: {block.block_id}")
                
                result = await orchestrator.process_block(block)
                
                if result.success:
                    successful_blocks += 1
                    logger.info(f"✅ Block {block.block_id} processed successfully")
                else:
                    logger.error(f"❌ Block {block.block_id} failed: {result.errors}")
                
            except Exception as e:
                logger.error(f"Exception processing block: {e}")
        
        # Report batch results
        logger.info(f"Batch processing completed: {successful_blocks}/{total_blocks} blocks successful")
        
    except Exception as e:
        logger.error(f"Batch example failed: {e}")
        raise


def main():
    """Main entry point for the example."""
    import argparse
    
    parser = argparse.ArgumentParser(description='DSA-110 Pipeline Example')
    parser.add_argument('--mode', choices=['single', 'batch'], default='single',
                       help='Example mode to run')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'single':
            asyncio.run(run_pipeline_example())
        elif args.mode == 'batch':
            asyncio.run(run_batch_processing_example())
        
        print("Example completed successfully!")
        
    except Exception as e:
        print(f"Example failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
