# core/utils/error_recovery.py
"""
Advanced error handling and recovery utilities for the DSA-110 pipeline.

This module provides circuit breakers, retry mechanisms, failure analysis,
and recovery strategies for robust pipeline operation.
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any, Optional, Callable, List, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os

from .logging import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: float = 60.0      # Seconds before trying half-open
    success_threshold: int = 3          # Successes needed to close from half-open
    timeout: float = 30.0               # Request timeout in seconds


@dataclass
class RetryConfig:
    """Configuration for retry mechanism."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple[type, ...] = (Exception,)


class CircuitBreaker:
    """
    Circuit breaker implementation for service protection.
    
    Prevents cascading failures by opening the circuit when
    a service is failing and allowing it to recover.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the circuit breaker
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.failure_history = []
        
    def can_execute(self) -> bool:
        """
        Check if requests can be executed.
        
        Returns:
            True if circuit is closed or half-open, False if open
        """
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                time.time() - self.last_failure_time > self.config.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record a successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self, exception: Exception):
        """
        Record a failed operation.
        
        Args:
            exception: The exception that caused the failure
        """
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        # Record failure in history
        self.failure_history.append({
            'timestamp': datetime.now().isoformat(),
            'exception': str(exception),
            'failure_count': self.failure_count
        })
        
        # Keep only recent failures
        if len(self.failure_history) > 100:
            self.failure_history = self.failure_history[-50:]
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} transitioning to OPEN after {self.failure_count} failures")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} transitioning to OPEN from HALF_OPEN")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get circuit breaker statistics.
        
        Returns:
            Dictionary containing circuit breaker statistics
        """
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time,
            'recent_failures': len([f for f in self.failure_history 
                                  if datetime.fromisoformat(f['timestamp']) > 
                                  datetime.now() - timedelta(hours=1)])
        }


class RetryManager:
    """
    Advanced retry mechanism with exponential backoff and jitter.
    
    Provides configurable retry logic with various backoff strategies
    and retryable exception handling.
    """
    
    def __init__(self, config: RetryConfig):
        """
        Initialize retry manager.
        
        Args:
            config: Retry configuration
        """
        self.config = config
        self.retry_stats = {
            'total_attempts': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'retry_histories': []
        }
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: Last exception if all retries failed
        """
        last_exception = None
        retry_history = []
        
        for attempt in range(self.config.max_retries + 1):
            try:
                self.retry_stats['total_attempts'] += 1
                retry_history.append({
                    'attempt': attempt + 1,
                    'timestamp': datetime.now().isoformat(),
                    'success': False
                })
                
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                retry_history[-1]['success'] = True
                self.retry_stats['successful_retries'] += 1
                
                if attempt > 0:
                    logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                last_exception = e
                retry_history[-1]['exception'] = str(e)
                
                # Check if exception is retryable
                if not isinstance(e, self.config.retryable_exceptions):
                    logger.error(f"Non-retryable exception in {func.__name__}: {e}")
                    break
                
                # Check if we have retries left
                if attempt >= self.config.max_retries:
                    logger.error(f"All retries exhausted for {func.__name__}: {e}")
                    break
                
                # Calculate delay with exponential backoff and jitter
                delay = self._calculate_delay(attempt)
                logger.warning(f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1}/{self.config.max_retries + 1}): {e}")
                
                await asyncio.sleep(delay)
        
        # Record failed retry
        self.retry_stats['failed_retries'] += 1
        self.retry_stats['retry_histories'].append({
            'function': func.__name__,
            'attempts': retry_history,
            'final_exception': str(last_exception)
        })
        
        # Keep only recent histories
        if len(self.retry_stats['retry_histories']) > 100:
            self.retry_stats['retry_histories'] = self.retry_stats['retry_histories'][-50:]
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter = random.uniform(0, delay * 0.1)
            delay += jitter
        
        return delay
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get retry statistics.
        
        Returns:
            Dictionary containing retry statistics
        """
        return self.retry_stats.copy()


class FailureAnalyzer:
    """
    Analyzes failure patterns and provides recovery recommendations.
    
    Tracks failure patterns, identifies common causes, and suggests
    recovery strategies.
    """
    
    def __init__(self):
        """Initialize failure analyzer."""
        self.failure_patterns = {}
        self.recovery_strategies = {
            'timeout': ['increase_timeout', 'reduce_load'],
            'memory': ['increase_memory', 'reduce_batch_size'],
            'network': ['retry_with_backoff', 'check_connectivity'],
            'permission': ['check_permissions', 'verify_credentials'],
            'resource': ['check_resources', 'scale_up']
        }
    
    def analyze_failure(self, stage: str, exception: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a failure and provide recommendations.
        
        Args:
            stage: Pipeline stage where failure occurred
            exception: The exception that occurred
            context: Additional context about the failure
            
        Returns:
            Dictionary containing analysis and recommendations
        """
        failure_type = self._classify_failure(exception)
        timestamp = datetime.now().isoformat()
        
        # Record failure pattern
        if stage not in self.failure_patterns:
            self.failure_patterns[stage] = []
        
        self.failure_patterns[stage].append({
            'timestamp': timestamp,
            'failure_type': failure_type,
            'exception': str(exception),
            'context': context
        })
        
        # Keep only recent patterns
        if len(self.failure_patterns[stage]) > 1000:
            self.failure_patterns[stage] = self.failure_patterns[stage][-500:]
        
        # Analyze patterns
        recent_failures = [f for f in self.failure_patterns[stage] 
                          if datetime.fromisoformat(f['timestamp']) > 
                          datetime.now() - timedelta(hours=1)]
        
        analysis = {
            'stage': stage,
            'failure_type': failure_type,
            'timestamp': timestamp,
            'recent_failure_count': len(recent_failures),
            'recommendations': self.recovery_strategies.get(failure_type, ['investigate_further']),
            'pattern_analysis': self._analyze_patterns(stage, recent_failures)
        }
        
        return analysis
    
    def _classify_failure(self, exception: Exception) -> str:
        """
        Classify failure type based on exception.
        
        Args:
            exception: The exception to classify
            
        Returns:
            Failure type string
        """
        exception_str = str(exception).lower()
        
        if 'timeout' in exception_str or 'timed out' in exception_str:
            return 'timeout'
        elif 'memory' in exception_str or 'out of memory' in exception_str:
            return 'memory'
        elif 'network' in exception_str or 'connection' in exception_str:
            return 'network'
        elif 'permission' in exception_str or 'access denied' in exception_str:
            return 'permission'
        elif 'resource' in exception_str or 'not found' in exception_str:
            return 'resource'
        else:
            return 'unknown'
    
    def _analyze_patterns(self, stage: str, recent_failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze failure patterns for a stage.
        
        Args:
            stage: Pipeline stage
            recent_failures: List of recent failures
            
        Returns:
            Pattern analysis results
        """
        if not recent_failures:
            return {'trend': 'stable', 'frequency': 0}
        
        # Count failure types
        failure_types = {}
        for failure in recent_failures:
            failure_type = failure['failure_type']
            failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
        
        # Calculate frequency
        frequency = len(recent_failures) / 60  # failures per minute
        
        # Determine trend
        if frequency > 1.0:
            trend = 'increasing'
        elif frequency > 0.1:
            trend = 'stable'
        else:
            trend = 'decreasing'
        
        return {
            'trend': trend,
            'frequency': frequency,
            'failure_types': failure_types,
            'most_common_type': max(failure_types.items(), key=lambda x: x[1])[0] if failure_types else None
        }
    
    def get_recovery_recommendations(self, stage: str) -> List[str]:
        """
        Get recovery recommendations for a stage.
        
        Args:
            stage: Pipeline stage
            
        Returns:
            List of recovery recommendations
        """
        if stage not in self.failure_patterns:
            return ['no_failures_recorded']
        
        recent_failures = [f for f in self.failure_patterns[stage] 
                          if datetime.fromisoformat(f['timestamp']) > 
                          datetime.now() - timedelta(hours=1)]
        
        if not recent_failures:
            return ['no_recent_failures']
        
        # Get most common failure type
        failure_types = {}
        for failure in recent_failures:
            failure_type = failure['failure_type']
            failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
        
        most_common_type = max(failure_types.items(), key=lambda x: x[1])[0] if failure_types else 'unknown'
        
        return self.recovery_strategies.get(most_common_type, ['investigate_further'])
    
    def get_failure_summary(self) -> Dict[str, Any]:
        """
        Get overall failure summary.
        
        Returns:
            Dictionary containing failure summary
        """
        summary = {}
        
        for stage, failures in self.failure_patterns.items():
            recent_failures = [f for f in failures 
                              if datetime.fromisoformat(f['timestamp']) > 
                              datetime.now() - timedelta(hours=24)]
            
            summary[stage] = {
                'total_failures': len(failures),
                'recent_failures': len(recent_failures),
                'pattern_analysis': self._analyze_patterns(stage, recent_failures),
                'recommendations': self.get_recovery_recommendations(stage)
            }
        
        return summary


class ErrorRecoveryManager:
    """
    Central error recovery manager for the pipeline.
    
    Coordinates circuit breakers, retry mechanisms, and failure analysis
    across all pipeline stages.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize error recovery manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.circuit_breakers = {}
        self.retry_managers = {}
        self.failure_analyzer = FailureAnalyzer()
        self.recovery_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'circuit_breaker_trips': 0,
            'retry_operations': 0
        }
    
    def get_circuit_breaker(self, stage: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for a stage.
        
        Args:
            stage: Pipeline stage name
            
        Returns:
            Circuit breaker instance
        """
        if stage not in self.circuit_breakers:
            cb_config = CircuitBreakerConfig(
                failure_threshold=self.config.get('circuit_breaker', {}).get('failure_threshold', 5),
                recovery_timeout=self.config.get('circuit_breaker', {}).get('recovery_timeout', 60.0),
                success_threshold=self.config.get('circuit_breaker', {}).get('success_threshold', 3),
                timeout=self.config.get('circuit_breaker', {}).get('timeout', 30.0)
            )
            self.circuit_breakers[stage] = CircuitBreaker(stage, cb_config)
        
        return self.circuit_breakers[stage]
    
    def get_retry_manager(self, stage: str) -> RetryManager:
        """
        Get or create retry manager for a stage.
        
        Args:
            stage: Pipeline stage name
            
        Returns:
            Retry manager instance
        """
        if stage not in self.retry_managers:
            retry_config = RetryConfig(
                max_retries=self.config.get('retry', {}).get('max_retries', 3),
                base_delay=self.config.get('retry', {}).get('base_delay', 1.0),
                max_delay=self.config.get('retry', {}).get('max_delay', 60.0),
                exponential_base=self.config.get('retry', {}).get('exponential_base', 2.0),
                jitter=self.config.get('retry', {}).get('jitter', True)
            )
            self.retry_managers[stage] = RetryManager(retry_config)
        
        return self.retry_managers[stage]
    
    async def execute_with_recovery(self, stage: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with full error recovery.
        
        Args:
            stage: Pipeline stage name
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all recovery mechanisms fail
        """
        self.recovery_stats['total_operations'] += 1
        
        # Check circuit breaker
        circuit_breaker = self.get_circuit_breaker(stage)
        if not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker {stage} is OPEN, failing fast")
            self.recovery_stats['circuit_breaker_trips'] += 1
            raise Exception(f"Circuit breaker {stage} is OPEN")
        
        try:
            # Execute with retry
            retry_manager = self.get_retry_manager(stage)
            result = await retry_manager.execute_with_retry(func, *args, **kwargs)
            
            # Record success
            circuit_breaker.record_success()
            self.recovery_stats['successful_operations'] += 1
            
            return result
            
        except Exception as e:
            # Record failure
            circuit_breaker.record_failure(e)
            self.recovery_stats['failed_operations'] += 1
            
            # Analyze failure
            analysis = self.failure_analyzer.analyze_failure(stage, e, {
                'function': func.__name__,
                'args': str(args)[:100],  # Truncate for logging
                'kwargs': str(kwargs)[:100]
            })
            
            logger.error(f"Operation failed in stage {stage}: {e}")
            logger.error(f"Failure analysis: {analysis}")
            
            raise e
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of the recovery system.
        
        Returns:
            Dictionary containing health status
        """
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'recovery_stats': self.recovery_stats.copy(),
            'circuit_breakers': {},
            'retry_managers': {},
            'failure_summary': self.failure_analyzer.get_failure_summary()
        }
        
        # Add circuit breaker status
        for stage, cb in self.circuit_breakers.items():
            health_status['circuit_breakers'][stage] = cb.get_stats()
        
        # Add retry manager status
        for stage, rm in self.retry_managers.items():
            health_status['retry_managers'][stage] = rm.get_stats()
        
        return health_status
    
    def save_recovery_state(self, filepath: str):
        """
        Save recovery state to file.
        
        Args:
            filepath: Path to save state file
        """
        state = {
            'timestamp': datetime.now().isoformat(),
            'circuit_breakers': {stage: cb.get_stats() for stage, cb in self.circuit_breakers.items()},
            'retry_managers': {stage: rm.get_stats() for stage, rm in self.retry_managers.items()},
            'failure_patterns': self.failure_analyzer.failure_patterns,
            'recovery_stats': self.recovery_stats
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Recovery state saved to {filepath}")
    
    def load_recovery_state(self, filepath: str):
        """
        Load recovery state from file.
        
        Args:
            filepath: Path to state file
        """
        if not os.path.exists(filepath):
            logger.warning(f"Recovery state file not found: {filepath}")
            return
        
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            # Restore failure patterns
            self.failure_analyzer.failure_patterns = state.get('failure_patterns', {})
            
            # Restore recovery stats
            self.recovery_stats.update(state.get('recovery_stats', {}))
            
            logger.info(f"Recovery state loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load recovery state: {e}")


# Global error recovery manager instance
error_recovery_manager = ErrorRecoveryManager()


def with_circuit_breaker(service_name: str, 
                        circuit_config: CircuitBreakerConfig = None,
                        retry_config: RetryConfig = None):
    """
    Decorator to add circuit breaker and retry functionality to functions.
    
    Args:
        service_name: Name of the service for circuit breaker
        circuit_config: Circuit breaker configuration
        retry_config: Retry configuration
        
    Returns:
        Decorated function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get circuit breaker for service
            circuit_breaker = error_recovery_manager.get_circuit_breaker(service_name)
            
            # Configure circuit breaker if provided
            if circuit_config:
                circuit_breaker.configure(circuit_config)
            
            # Get retry manager
            retry_manager = error_recovery_manager.get_retry_manager()
            
            # Configure retry manager if provided
            if retry_config:
                retry_manager.configure(retry_config)
            
            # Execute with circuit breaker and retry
            return await retry_manager.execute_with_retry(
                lambda: circuit_breaker.execute(func, *args, **kwargs)
            )
        
        return wrapper
    return decorator


def get_error_recovery_manager() -> ErrorRecoveryManager:
    """
    Get the global error recovery manager instance.
    
    Returns:
        ErrorRecoveryManager instance
    """
    return error_recovery_manager