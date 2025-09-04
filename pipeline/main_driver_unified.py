# pipeline/main_driver_unified.py
"""
Unified main driver for DSA-110 continuum imaging pipeline.

This module provides a unified interface for both batch processing
and service-based processing using the new orchestrator architecture.
"""

import os
import sys
import asyncio
import argparse
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from astropy.time import Time

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import PipelineOrchestrator, ProcessingBlock
from core.utils.logging import setup_logging, get_logger
from core.utils.monitoring import HealthChecker
from core.pipeline.exceptions import PipelineError, ConfigurationError

logger = get_logger(__name__)


class UnifiedPipelineDriver:
    """
    Unified driver for the DSA-110 pipeline.
    
    This class provides a single interface for both batch processing
    and service-based processing, eliminating code duplication.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the unified pipeline driver.
        
        Args:
            config_path: Path to the pipeline configuration file
        """
        self.config_path = config_path
        self.config = self._load_configuration()
        self.orchestrator = None
        self.health_checker = HealthChecker()
        
        # Set up logging
        log_dir = self.config.get('paths', {}).get('log_dir', 'logs')
        setup_logging(log_dir, 'pipeline', logging.INFO)
        
        logger.info("Unified pipeline driver initialized")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """
        Load pipeline configuration from file.
        
        Returns:
            Configuration dictionary
        """
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    async def initialize(self):
        """Initialize the pipeline orchestrator."""
        try:
            self.orchestrator = PipelineOrchestrator(self.config)
            logger.info("Pipeline orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise PipelineError(f"Orchestrator initialization failed: {e}")
    
    async def run_batch_processing(self, start_time_iso: Optional[str] = None,
                                 end_time_iso: Optional[str] = None,
                                 max_blocks: Optional[int] = None) -> Dict[str, Any]:
        """
        Run batch processing for a time range.
        
        Args:
            start_time_iso: ISO timestamp to start processing from
            end_time_iso: ISO timestamp to end processing at
            max_blocks: Maximum number of blocks to process
            
        Returns:
            Dictionary containing processing results
        """
        logger.info("Starting batch processing")
        
        try:
            if not self.orchestrator:
                await self.initialize()
            
            # Find MS blocks for processing
            blocks_dict = self.orchestrator.find_ms_blocks_for_batch(
                start_time_iso, end_time_iso
            )
            
            if not blocks_dict:
                logger.warning("No MS blocks found for processing")
                return {
                    'success': True,
                    'blocks_processed': 0,
                    'total_blocks': 0,
                    'errors': []
                }
            
            # Process blocks
            results = await self._process_blocks(blocks_dict, max_blocks)
            
            logger.info(f"Batch processing completed: {results['blocks_processed']}/{results['total_blocks']} blocks processed")
            return results
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'blocks_processed': 0,
                'total_blocks': 0
            }
    
    async def run_single_block(self, block_end_time_iso: str, ms_files: list) -> Dict[str, Any]:
        """
        Run processing for a single block.
        
        Args:
            block_end_time_iso: ISO timestamp for the block end time
            ms_files: List of MS file paths
            
        Returns:
            Dictionary containing processing results
        """
        logger.info(f"Processing single block ending at {block_end_time_iso}")
        
        try:
            if not self.orchestrator:
                await self.initialize()
            
            # Create processing block
            block_end_time = Time(block_end_time_iso)
            block = self.orchestrator.create_processing_block(block_end_time, ms_files)
            
            # Process the block
            result = await self.orchestrator.process_block(block)
            
            logger.info(f"Single block processing completed: {'success' if result.success else 'failed'}")
            return {
                'success': result.success,
                'block_id': result.block_id,
                'processing_time': result.processing_time,
                'errors': result.errors,
                'output_files': result.output_files
            }
            
        except Exception as e:
            logger.error(f"Single block processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'block_id': None,
                'processing_time': 0.0,
                'errors': [str(e)]
            }
    
    async def _process_blocks(self, blocks_dict: Dict[Time, list], 
                            max_blocks: Optional[int] = None) -> Dict[str, Any]:
        """
        Process multiple blocks.
        
        Args:
            blocks_dict: Dictionary mapping block end times to MS file lists
            max_blocks: Maximum number of blocks to process
            
        Returns:
            Dictionary containing processing results
        """
        total_blocks = len(blocks_dict)
        blocks_processed = 0
        successful_blocks = 0
        errors = []
        
        # Sort blocks by time
        sorted_blocks = sorted(blocks_dict.items(), key=lambda x: x[0])
        
        # Limit number of blocks if specified
        if max_blocks is not None:
            sorted_blocks = sorted_blocks[:max_blocks]
        
        logger.info(f"Processing {len(sorted_blocks)} blocks")
        
        for block_end_time, ms_files in sorted_blocks:
            try:
                # Create processing block
                block = self.orchestrator.create_processing_block(block_end_time, ms_files)
                
                # Process the block
                result = await self.orchestrator.process_block(block)
                
                blocks_processed += 1
                if result.success:
                    successful_blocks += 1
                    logger.info(f"Block {block.block_id} processed successfully")
                else:
                    logger.error(f"Block {block.block_id} failed: {result.errors}")
                    errors.extend(result.errors)
                
                # Check if we should continue
                if max_blocks is not None and blocks_processed >= max_blocks:
                    break
                    
            except Exception as e:
                error_msg = f"Exception processing block ending at {block_end_time.iso}: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                blocks_processed += 1
        
        return {
            'success': len(errors) == 0,
            'blocks_processed': blocks_processed,
            'successful_blocks': successful_blocks,
            'total_blocks': total_blocks,
            'errors': errors
        }
    
    async def run_health_check(self) -> Dict[str, Any]:
        """
        Run health checks on the pipeline.
        
        Returns:
            Dictionary containing health check results
        """
        logger.info("Running health checks")
        
        try:
            health_checks = self.health_checker.check_all_health(self.config)
            
            # Categorize results
            healthy_count = sum(1 for hc in health_checks if hc.status == 'healthy')
            degraded_count = sum(1 for hc in health_checks if hc.status == 'degraded')
            unhealthy_count = sum(1 for hc in health_checks if hc.status == 'unhealthy')
            
            overall_status = 'healthy'
            if unhealthy_count > 0:
                overall_status = 'unhealthy'
            elif degraded_count > 0:
                overall_status = 'degraded'
            
            logger.info(f"Health check completed: {healthy_count} healthy, {degraded_count} degraded, {unhealthy_count} unhealthy")
            
            return {
                'success': True,
                'overall_status': overall_status,
                'healthy_count': healthy_count,
                'degraded_count': degraded_count,
                'unhealthy_count': unhealthy_count,
                'health_checks': [hc.to_dict() for hc in health_checks]
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'overall_status': 'unknown'
            }


async def main():
    """Main entry point for the unified pipeline driver."""
    parser = argparse.ArgumentParser(description='DSA-110 Unified Pipeline Driver')
    parser.add_argument('--config', required=True, help='Path to configuration file')
    parser.add_argument('--mode', choices=['batch', 'single', 'health'], required=True,
                       help='Processing mode')
    parser.add_argument('--start-time', help='Start time for batch processing (ISO format)')
    parser.add_argument('--end-time', help='End time for batch processing (ISO format)')
    parser.add_argument('--block-end-time', help='Block end time for single block processing (ISO format)')
    parser.add_argument('--ms-files', nargs='+', help='MS files for single block processing')
    parser.add_argument('--max-blocks', type=int, help='Maximum number of blocks to process')
    
    args = parser.parse_args()
    
    try:
        # Initialize driver
        driver = UnifiedPipelineDriver(args.config)
        
        if args.mode == 'batch':
            # Batch processing
            result = await driver.run_batch_processing(
                start_time_iso=args.start_time,
                end_time_iso=args.end_time,
                max_blocks=args.max_blocks
            )
            
            if result['success']:
                print(f"Batch processing completed successfully: {result['blocks_processed']} blocks processed")
            else:
                print(f"Batch processing failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        
        elif args.mode == 'single':
            # Single block processing
            if not args.block_end_time or not args.ms_files:
                print("Error: --block-end-time and --ms-files are required for single block processing")
                sys.exit(1)
            
            result = await driver.run_single_block(args.block_end_time, args.ms_files)
            
            if result['success']:
                print(f"Single block processing completed successfully: {result['block_id']}")
            else:
                print(f"Single block processing failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        
        elif args.mode == 'health':
            # Health check
            result = await driver.run_health_check()
            
            if result['success']:
                print(f"Health check completed: {result['overall_status']}")
                print(f"Healthy: {result['healthy_count']}, Degraded: {result['degraded_count']}, Unhealthy: {result['unhealthy_count']}")
            else:
                print(f"Health check failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
