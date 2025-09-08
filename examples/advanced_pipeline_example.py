#!/usr/bin/env python3
"""
Advanced pipeline example demonstrating all Phase 3 features.

This example shows how to use the enhanced pipeline orchestrator with
advanced error recovery, distributed state management, message queuing,
and monitoring capabilities.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.pipeline.enhanced_orchestrator import EnhancedPipelineOrchestrator
from core.utils.logging import setup_logging, get_logger
from core.utils.config_loader import load_pipeline_config
from core.utils.error_recovery import get_error_recovery_manager
from core.utils.distributed_state import initialize_distributed_state
from core.messaging.message_queue import initialize_message_queues
from core.data_ingestion.ms_creation import MSCreationManager
from monitoring.advanced_monitoring import AdvancedMonitor, MonitoringDashboard
from astropy.time import Time

logger = get_logger(__name__)


async def setup_advanced_infrastructure():
    """Set up the advanced infrastructure components."""
    logger.info("Setting up advanced infrastructure...")
    
    try:
        # Initialize distributed state management
        await initialize_distributed_state(
            redis_url="redis://localhost:6379",
            namespace="dsa110_pipeline_demo"
        )
        logger.info("✅ Distributed state management initialized")
        
        # Initialize message queues
        await initialize_message_queues(
            redis_url="redis://localhost:6379",
            namespace="dsa110_pipeline_demo"
        )
        logger.info("✅ Message queues initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to setup advanced infrastructure: {e}")
        logger.info("Note: Make sure Redis is running on localhost:6379")
        return False


async def create_test_data(config):
    """Create test MS files for the advanced example."""
    logger.info("Creating test MS files for advanced example...")
    
    ms_manager = MSCreationManager(config)
    test_ms_files = []
    
    # Create more test MS files for advanced processing
    for i in range(5):
        ms_path = f"test_data/ms_stage1/drift_20230101T000000_{i:02d}.ms"
        os.makedirs(os.path.dirname(ms_path), exist_ok=True)
        
        start_time = Time('2023-01-01T00:00:00', format='isot', scale='utc')
        end_time = Time('2023-01-01T00:05:00', format='isot', scale='utc')
        
        success = await ms_manager.create_test_ms(
            ms_path, start_time, end_time,
            n_antennas=8, n_frequencies=32, n_times=20
        )
        
        if success:
            test_ms_files.append(ms_path)
            logger.info(f"✅ Created test MS: {ms_path}")
        else:
            logger.error(f"❌ Failed to create test MS: {ms_path}")
    
    return test_ms_files


async def run_advanced_monitoring_example():
    """Run an example with advanced monitoring."""
    logger.info("=== Advanced Monitoring Example ===")
    
    try:
        # Load configuration
        config = load_pipeline_config(environment="development")
        
        # Set up logging
        setup_logging(config['paths']['log_dir'], 'advanced_monitoring', logging.INFO)
        
        # Initialize enhanced orchestrator
        orchestrator = EnhancedPipelineOrchestrator(config)
        await orchestrator.initialize_advanced_features()
        
        # Create test data
        test_ms_files = await create_test_data(config)
        
        if not test_ms_files:
            logger.error("No test MS files created")
            return
        
        # Create processing block
        block_end_time = Time('2023-01-01T00:25:00', format='isot', scale='utc')
        block = orchestrator.create_processing_block(block_end_time, test_ms_files)
        
        logger.info(f"Created processing block: {block.block_id}")
        
        # Process block with advanced recovery
        logger.info("Processing block with advanced error recovery...")
        result = await orchestrator.process_block_with_recovery(block)
        
        # Report results
        if result.success:
            logger.info("✅ Advanced processing completed successfully!")
            logger.info(f"Processing time: {result.processing_time:.1f} seconds")
            logger.info(f"Stage results: {list(result.stage_results.keys())}")
        else:
            logger.error("❌ Advanced processing failed!")
            logger.error(f"Errors: {result.errors}")
        
        # Get processing status
        status = await orchestrator.get_processing_status(block.block_id)
        if status:
            logger.info(f"Block status: {status['state']}")
        
        # Get error recovery status
        recovery_status = await orchestrator.get_error_recovery_status()
        logger.info(f"Circuit breaker status: {list(recovery_status['circuit_breakers'].keys())}")
        
        # Clean up
        await orchestrator.cleanup_advanced_features()
        
        return result
        
    except Exception as e:
        logger.error(f"Advanced monitoring example failed: {e}")
        raise


async def run_distributed_processing_example():
    """Run an example with distributed processing."""
    logger.info("=== Distributed Processing Example ===")
    
    try:
        # Load configuration
        config = load_pipeline_config(environment="development")
        
        # Set up logging
        setup_logging(config['paths']['log_dir'], 'distributed_processing', logging.INFO)
        
        # Initialize enhanced orchestrator
        orchestrator = EnhancedPipelineOrchestrator(config)
        await orchestrator.initialize_advanced_features()
        
        # Create test data
        test_ms_files = await create_test_data(config)
        
        if not test_ms_files:
            logger.error("No test MS files created")
            return
        
        # Process multiple blocks concurrently
        logger.info("Processing multiple blocks concurrently...")
        
        blocks = []
        for i in range(3):
            block_end_time = Time(f'2023-01-01T00:{15+i*5:02d}:00', format='isot', scale='utc')
            block = orchestrator.create_processing_block(block_end_time, test_ms_files[:3])
            blocks.append(block)
        
        # Process blocks concurrently
        tasks = []
        for block in blocks:
            task = asyncio.create_task(orchestrator.process_block_with_recovery(block))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Report results
        successful_blocks = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Block {i+1} failed with exception: {result}")
            elif result.success:
                successful_blocks += 1
                logger.info(f"✅ Block {i+1} completed successfully")
            else:
                logger.error(f"❌ Block {i+1} failed: {result.errors}")
        
        logger.info(f"Distributed processing completed: {successful_blocks}/{len(blocks)} blocks successful")
        
        # Get all processing statuses
        all_statuses = await orchestrator.get_all_processing_statuses()
        logger.info(f"Total blocks processed: {len(all_statuses)}")
        
        # Get service statuses
        service_statuses = await orchestrator.get_service_statuses()
        logger.info(f"Service statuses: {list(service_statuses.keys())}")
        
        # Clean up
        await orchestrator.cleanup_advanced_features()
        
        return results
        
    except Exception as e:
        logger.error(f"Distributed processing example failed: {e}")
        raise


async def run_monitoring_dashboard_example():
    """Run an example with the monitoring dashboard."""
    logger.info("=== Monitoring Dashboard Example ===")
    
    try:
        # Load configuration
        config = load_pipeline_config(environment="development")
        
        # Set up logging
        setup_logging(config['paths']['log_dir'], 'monitoring_dashboard', logging.INFO)
        
        # Initialize enhanced orchestrator
        orchestrator = EnhancedPipelineOrchestrator(config)
        await orchestrator.initialize_advanced_features()
        
        # Initialize advanced monitor
        message_queue = await orchestrator.message_queue_manager.get_queue("monitor")
        monitor = AdvancedMonitor(message_queue)
        
        # Add some threshold rules
        from monitoring.advanced_monitoring import ThresholdRule, AlertLevel
        
        # Add threshold rule for processing time
        processing_time_rule = ThresholdRule(
            name="high_processing_time",
            metric_name="block_processing_time",
            operator=">",
            threshold_value=300.0,  # 5 minutes
            alert_level=AlertLevel.WARNING,
            duration=60
        )
        await monitor.add_threshold_rule(processing_time_rule)
        
        # Add threshold rule for failure rate
        failure_rate_rule = ThresholdRule(
            name="high_failure_rate",
            metric_name="block_failure_rate",
            operator=">",
            threshold_value=0.5,  # 50%
            alert_level=AlertLevel.ERROR,
            duration=120
        )
        await monitor.add_threshold_rule(failure_rate_rule)
        
        # Start monitoring
        monitor_task = asyncio.create_task(monitor.start())
        
        # Initialize dashboard
        dashboard = MonitoringDashboard(monitor, port=8080)
        dashboard_task = asyncio.create_task(dashboard.start())
        
        logger.info("✅ Monitoring dashboard started on http://localhost:8080")
        logger.info("Press Ctrl+C to stop...")
        
        # Create test data and process some blocks
        test_ms_files = await create_test_data(config)
        
        if test_ms_files:
            # Process a few blocks to generate metrics
            for i in range(2):
                block_end_time = Time(f'2023-01-01T00:{10+i*5:02d}:00', format='isot', scale='utc')
                block = orchestrator.create_processing_block(block_end_time, test_ms_files[:2])
                
                # Record some metrics
                await monitor.record_metric("block_processing_time", 120.0 + i*50)
                await monitor.record_metric("block_failure_rate", 0.1 + i*0.2)
                
                # Process block
                result = await orchestrator.process_block_with_recovery(block)
                
                # Record processing result
                await monitor.record_metric("block_processing_time", result.processing_time)
                await monitor.record_metric("block_success", 1.0 if result.success else 0.0)
                
                logger.info(f"Processed block {i+1}, recorded metrics")
        
        # Wait for user to stop
        try:
            await asyncio.sleep(60)  # Run for 1 minute
        except KeyboardInterrupt:
            logger.info("Stopping monitoring dashboard...")
        
        # Stop monitoring
        await monitor.stop()
        monitor_task.cancel()
        dashboard_task.cancel()
        
        # Clean up
        await orchestrator.cleanup_advanced_features()
        
        logger.info("✅ Monitoring dashboard example completed")
        
    except Exception as e:
        logger.error(f"Monitoring dashboard example failed: {e}")
        raise


async def main():
    """Main entry point for the advanced example."""
    import argparse
    
    parser = argparse.ArgumentParser(description='DSA-110 Advanced Pipeline Example')
    parser.add_argument('--example', choices=['monitoring', 'distributed', 'dashboard'], 
                       default='monitoring', help='Example to run')
    
    args = parser.parse_args()
    
    # Set up advanced infrastructure
    infrastructure_ready = await setup_advanced_infrastructure()
    
    if not infrastructure_ready:
        logger.error("❌ Advanced infrastructure not available")
        logger.info("Please ensure Redis is running on localhost:6379")
        sys.exit(1)
    
    try:
        if args.example == 'monitoring':
            await run_advanced_monitoring_example()
        elif args.example == 'distributed':
            await run_distributed_processing_example()
        elif args.example == 'dashboard':
            await run_monitoring_dashboard_example()
        
        print("✅ Advanced example completed successfully!")
        
    except Exception as e:
        print(f"❌ Advanced example failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
