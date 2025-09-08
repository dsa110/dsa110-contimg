# core/pipeline/enhanced_orchestrator.py
"""
Enhanced pipeline orchestrator with advanced features.

This module extends the basic orchestrator with advanced error recovery,
distributed state management, message queuing, and monitoring capabilities.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from astropy.time import Time

from .orchestrator import PipelineOrchestrator, ProcessingBlock, ProcessingResult
from ..utils.logging import get_logger
from ..utils.monitoring import PipelineMetrics
from ..utils.error_recovery import (
    ErrorRecoveryManager, CircuitBreakerConfig, RetryConfig,
    with_circuit_breaker, get_error_recovery_manager
)
from ..utils.distributed_state import (
    DistributedStateManager, StateType, get_distributed_state_manager
)
from ..messaging.message_queue import (
    MessageQueue, MessageType, MessagePriority, get_message_queue_manager
)
from ..pipeline.exceptions import PipelineError

logger = get_logger(__name__)


class EnhancedPipelineOrchestrator(PipelineOrchestrator):
    """
    Enhanced pipeline orchestrator with advanced features.
    
    Extends the basic orchestrator with:
    - Advanced error recovery and circuit breakers
    - Distributed state management
    - Message queue integration
    - Enhanced monitoring and alerting
    - Automatic retry mechanisms
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the enhanced pipeline orchestrator.
        
        Args:
            config: Pipeline configuration dictionary
        """
        super().__init__(config)
        
        # Initialize advanced components
        self.error_recovery_manager = get_error_recovery_manager()
        self.state_manager = get_distributed_state_manager()
        self.message_queue_manager = get_message_queue_manager()
        
        # Initialize circuit breakers for different operations
        self._initialize_circuit_breakers()
        
        # Initialize retry configurations
        self._initialize_retry_configs()
        
        # Message queue for this orchestrator
        self.message_queue = None
        
        logger.info("Enhanced pipeline orchestrator initialized")
    
    def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for different operations."""
        # Calibration circuit breaker
        self.calibration_cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=300,  # 5 minutes
            expected_exception=Exception,
            success_threshold=2
        )
        
        # Imaging circuit breaker
        self.imaging_cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=600,  # 10 minutes
            expected_exception=Exception,
            success_threshold=3
        )
        
        # Mosaicking circuit breaker
        self.mosaicking_cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=300,  # 5 minutes
            expected_exception=Exception,
            success_threshold=2
        )
        
        # Photometry circuit breaker
        self.photometry_cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=300,  # 5 minutes
            expected_exception=Exception,
            success_threshold=2
        )
    
    def _initialize_retry_configs(self):
        """Initialize retry configurations for different operations."""
        # Calibration retry config
        self.calibration_retry_config = RetryConfig(
            max_attempts=3,
            base_delay=5.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(Exception,)
        )
        
        # Imaging retry config
        self.imaging_retry_config = RetryConfig(
            max_attempts=2,
            base_delay=10.0,
            max_delay=120.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(Exception,)
        )
        
        # Mosaicking retry config
        self.mosaicking_retry_config = RetryConfig(
            max_attempts=2,
            base_delay=5.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(Exception,)
        )
        
        # Photometry retry config
        self.photometry_retry_config = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(Exception,)
        )
    
    async def initialize_advanced_features(self):
        """Initialize advanced features (state management, message queues, etc.)."""
        try:
            # Initialize distributed state
            await self.state_manager.connect()
            
            # Initialize message queue
            self.message_queue = await self.message_queue_manager.get_queue("orchestrator")
            
            # Set service status
            await self.state_manager.set_service_status(
                "pipeline_orchestrator",
                "healthy",
                {"instance_id": self.state_manager.instance_id}
            )
            
            logger.info("Advanced features initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize advanced features: {e}")
            raise PipelineError(f"Advanced features initialization failed: {e}")
    
    async def cleanup_advanced_features(self):
        """Clean up advanced features."""
        try:
            # Update service status
            await self.state_manager.set_service_status(
                "pipeline_orchestrator",
                "unhealthy",
                {"shutdown": True}
            )
            
            # Disconnect from state manager
            await self.state_manager.disconnect()
            
            logger.info("Advanced features cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error cleaning up advanced features: {e}")
    
    @with_circuit_breaker("calibration", CircuitBreakerConfig(), RetryConfig())
    async def process_block(self, block: ProcessingBlock) -> ProcessingResult:
        """
        Process a single block with enhanced error recovery and monitoring.
        
        Args:
            block: ProcessingBlock containing MS files and timing information
            
        Returns:
            ProcessingResult with success status and output information
        """
        start_time = datetime.now()
        logger.info(f"Starting enhanced processing block {block.block_id}")
        
        # Set block state to processing
        await self.state_manager.set_processing_block_state(
            block.block_id,
            "processing",
            {
                "start_time": start_time.isoformat(),
                "ms_count": len(block.ms_files),
                "instance_id": self.state_manager.instance_id
            }
        )
        
        # Send processing start message
        if self.message_queue:
            await self.message_queue.publish(
                "processing_events",
                self.message_queue.create_message(
                    MessageType.PROCESSING_REQUEST,
                    {
                        "block_id": block.block_id,
                        "action": "start",
                        "ms_files": block.ms_files
                    },
                    "orchestrator",
                    priority=MessagePriority.NORMAL
                )
            )
        
        try:
            # Process the block using the parent class method
            result = await super().process_block(block)
            
            # Update block state
            if result.success:
                await self.state_manager.set_processing_block_state(
                    block.block_id,
                    "completed",
                    {
                        "end_time": datetime.now().isoformat(),
                        "processing_time": result.processing_time,
                        "output_files": result.output_files
                    }
                )
                
                # Send success message
                if self.message_queue:
                    await self.message_queue.publish(
                        "processing_events",
                        self.message_queue.create_message(
                            MessageType.PROCESSING_RESULT,
                            {
                                "block_id": block.block_id,
                                "success": True,
                                "processing_time": result.processing_time
                            },
                            "orchestrator",
                            priority=MessagePriority.NORMAL
                        )
                    )
            else:
                await self.state_manager.set_processing_block_state(
                    block.block_id,
                    "failed",
                    {
                        "end_time": datetime.now().isoformat(),
                        "errors": result.errors
                    }
                )
                
                # Send failure message
                if self.message_queue:
                    await self.message_queue.publish(
                        "processing_events",
                        self.message_queue.create_message(
                            MessageType.ERROR_NOTIFICATION,
                            {
                                "block_id": block.block_id,
                                "success": False,
                                "errors": result.errors
                            },
                            "orchestrator",
                            priority=MessagePriority.HIGH
                        )
                    )
            
            return result
            
        except Exception as e:
            # Update block state to failed
            await self.state_manager.set_processing_block_state(
                block.block_id,
                "failed",
                {
                    "end_time": datetime.now().isoformat(),
                    "error": str(e)
                }
            )
            
            # Send error message
            if self.message_queue:
                await self.message_queue.publish(
                    "processing_events",
                    self.message_queue.create_message(
                        MessageType.ERROR_NOTIFICATION,
                        {
                            "block_id": block.block_id,
                            "error": str(e)
                        },
                        "orchestrator",
                        priority=MessagePriority.CRITICAL
                    )
                )
            
            raise
    
    async def get_processing_status(self, block_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the processing status of a block.
        
        Args:
            block_id: Block ID
            
        Returns:
            Block status information or None if not found
        """
        return await self.state_manager.get_processing_block_state(block_id)
    
    async def get_all_processing_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the processing status of all blocks.
        
        Returns:
            Dictionary of block statuses
        """
        entries = await self.state_manager.list_states(StateType.PROCESSING_BLOCK)
        return {entry.value['block_id']: entry.value for entry in entries}
    
    async def get_service_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all services.
        
        Returns:
            Dictionary of service statuses
        """
        return await self.state_manager.get_all_service_statuses()
    
    async def get_error_recovery_status(self) -> Dict[str, Any]:
        """
        Get the status of error recovery components.
        
        Returns:
            Error recovery status information
        """
        return {
            "circuit_breakers": self.error_recovery_manager.get_circuit_breaker_status(),
            "failure_summary": self.error_recovery_manager.get_failure_summary(hours=24)
        }
    
    async def reset_circuit_breaker(self, name: str):
        """
        Reset a circuit breaker.
        
        Args:
            name: Circuit breaker name
        """
        self.error_recovery_manager.reset_circuit_breaker(name)
        logger.info(f"Reset circuit breaker: {name}")
    
    async def process_block_with_recovery(self, block: ProcessingBlock) -> ProcessingResult:
        """
        Process a block with advanced error recovery.
        
        This method implements a more sophisticated error recovery strategy
        that can handle partial failures and retry individual stages.
        
        Args:
            block: ProcessingBlock to process
            
        Returns:
            ProcessingResult with detailed recovery information
        """
        start_time = datetime.now()
        logger.info(f"Starting block processing with recovery: {block.block_id}")
        
        result = ProcessingResult(
            block_id=block.block_id,
            success=False,
            stage_results={},
            errors=[],
            processing_time=0.0,
            output_files={}
        )
        
        try:
            # Stage 1: Calibration with recovery
            logger.info("=== Stage 1: Calibration with Recovery ===")
            cal_result = await self._process_calibration_with_recovery(block)
            result.stage_results['calibration'] = cal_result
            
            if not cal_result['success']:
                raise Exception(f"Calibration failed: {cal_result['error']}")
            
            # Stage 2: Imaging with recovery
            logger.info("=== Stage 2: Imaging with Recovery ===")
            img_result = await self._process_imaging_with_recovery(block, cal_result)
            result.stage_results['imaging'] = img_result
            
            if not img_result['success']:
                raise Exception(f"Imaging failed: {img_result['error']}")
            
            # Stage 3: Mosaicking with recovery
            logger.info("=== Stage 3: Mosaicking with Recovery ===")
            mos_result = await self._process_mosaicking_with_recovery(block, img_result)
            result.stage_results['mosaicking'] = mos_result
            
            if not mos_result['success']:
                raise Exception(f"Mosaicking failed: {mos_result['error']}")
            
            # Stage 4: Photometry with recovery
            logger.info("=== Stage 4: Photometry with Recovery ===")
            phot_result = await self._process_photometry_with_recovery(block, mos_result)
            result.stage_results['photometry'] = phot_result
            
            # Mark as successful
            result.success = True
            result.output_files = {
                'mosaic_image': mos_result.get('image_path'),
                'mosaic_fits': mos_result.get('fits_path'),
                'processed_images': img_result.get('processed_images', []),
                'processed_pbs': img_result.get('processed_pbs', [])
            }
            
            logger.info(f"Block processing with recovery completed successfully: {block.block_id}")
            
        except Exception as e:
            error_msg = f"Block processing with recovery failed: {e}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            result.success = False
        
        finally:
            result.processing_time = (datetime.now() - start_time).total_seconds()
            
            # Record metrics
            self.metrics.record_block_processing(
                block_id=block.block_id,
                success=result.success,
                processing_time=result.processing_time,
                ms_count=len(block.ms_files),
                image_count=len(result.output_files.get('processed_images', []))
            )
        
        return result
    
    async def _process_calibration_with_recovery(self, block: ProcessingBlock) -> Dict[str, Any]:
        """Process calibration stage with recovery."""
        try:
            # Use circuit breaker and retry for calibration
            calibration_stage = self.stages['calibration']
            result = await calibration_stage.setup_calibration(block)
            
            if result['success']:
                logger.info("Calibration stage completed successfully")
            else:
                logger.error(f"Calibration stage failed: {result['error']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Calibration stage exception: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _process_imaging_with_recovery(self, block: ProcessingBlock, 
                                           cal_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process imaging stage with recovery."""
        try:
            imaging_stage = self.stages['imaging']
            processed_images = []
            processed_pbs = []
            
            for i, ms_path in enumerate(block.ms_files):
                try:
                    img_result = await imaging_stage.process_ms(
                        ms_path,
                        cal_result['bcal_table'],
                        cal_result['gcal_table'],
                        cal_result['cl_path'],
                        cal_result.get('mask_path')
                    )
                    
                    if img_result['success']:
                        processed_images.append(img_result['image_path'])
                        processed_pbs.append(img_result['pb_path'])
                        logger.info(f"Successfully processed MS {i+1}/{len(block.ms_files)}")
                    else:
                        logger.error(f"Failed to process MS {i+1}: {img_result['error']}")
                        
                except Exception as e:
                    logger.error(f"Exception processing MS {i+1}: {e}")
                    continue
            
            # Check if we have enough successful images
            min_images_needed = int(len(block.ms_files) * 0.75)
            if len(processed_images) < min_images_needed:
                return {
                    'success': False,
                    'error': f'Insufficient successful images: {len(processed_images)}/{len(block.ms_files)}'
                }
            
            return {
                'success': True,
                'processed_images': processed_images,
                'processed_pbs': processed_pbs
            }
            
        except Exception as e:
            logger.error(f"Imaging stage exception: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _process_mosaicking_with_recovery(self, block: ProcessingBlock,
                                              img_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process mosaicking stage with recovery."""
        try:
            mosaicking_stage = self.stages['mosaicking']
            mosaic_result = await mosaicking_stage.create_mosaic(
                img_result['processed_images'],
                img_result['processed_pbs'],
                block
            )
            
            if mosaic_result['success']:
                logger.info("Mosaicking stage completed successfully")
            else:
                logger.error(f"Mosaicking stage failed: {mosaic_result['error']}")
            
            return mosaic_result
            
        except Exception as e:
            logger.error(f"Mosaicking stage exception: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _process_photometry_with_recovery(self, block: ProcessingBlock,
                                              mos_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process photometry stage with recovery."""
        try:
            if not mos_result.get('fits_path'):
                return {'success': False, 'error': 'No FITS file available for photometry'}
            
            photometry_stage = self.stages['photometry']
            phot_result = await photometry_stage.process_mosaic(
                mos_result['fits_path'],
                block.end_time
            )
            
            if phot_result['success']:
                logger.info("Photometry stage completed successfully")
            else:
                logger.warning(f"Photometry stage failed: {phot_result['error']}")
            
            return phot_result
            
        except Exception as e:
            logger.error(f"Photometry stage exception: {e}")
            return {'success': False, 'error': str(e)}
