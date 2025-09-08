# core/utils/health_monitoring.py
"""
Health monitoring and health check utilities for the DSA-110 pipeline.

This module provides health check endpoints, monitoring capabilities,
and health status reporting for all pipeline components.
"""

import asyncio
import logging
import time
import psutil
import os
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json

from .logging import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check definition."""
    name: str
    check_func: Callable
    timeout: float = 30.0
    critical: bool = True
    description: str = ""


@dataclass
class HealthMetrics:
    """Health metrics for a component."""
    status: HealthStatus
    timestamp: datetime
    response_time: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


class HealthMonitor:
    """
    Health monitoring system for pipeline components.
    
    Provides health check execution, status tracking, and
    health reporting capabilities.
    """
    
    def __init__(self):
        """Initialize health monitor."""
        self.health_checks = {}
        self.health_history = {}
        self.metrics_history = {}
        self.alert_thresholds = {
            'response_time': 30.0,  # seconds
            'error_rate': 0.1,      # 10%
            'memory_usage': 0.9,    # 90%
            'disk_usage': 0.9       # 90%
        }
    
    def register_health_check(self, name: str, check_func: Callable, 
                            timeout: float = 30.0, critical: bool = True,
                            description: str = ""):
        """
        Register a health check.
        
        Args:
            name: Name of the health check
            check_func: Function to execute for health check
            timeout: Timeout in seconds
            critical: Whether this check is critical
            description: Description of the health check
        """
        self.health_checks[name] = HealthCheck(
            name=name,
            check_func=check_func,
            timeout=timeout,
            critical=critical,
            description=description
        )
        logger.info(f"Registered health check: {name}")
    
    async def run_health_check(self, name: str) -> HealthMetrics:
        """
        Run a specific health check.
        
        Args:
            name: Name of the health check
            
        Returns:
            Health metrics for the check
        """
        if name not in self.health_checks:
            return HealthMetrics(
                status=HealthStatus.UNKNOWN,
                timestamp=datetime.now(),
                response_time=0.0,
                error_message=f"Health check '{name}' not found"
            )
        
        check = self.health_checks[name]
        start_time = time.time()
        
        try:
            # Run health check with timeout
            result = await asyncio.wait_for(
                self._execute_check(check.check_func),
                timeout=check.timeout
            )
            
            response_time = time.time() - start_time
            status = HealthStatus.HEALTHY if result.get('healthy', False) else HealthStatus.UNHEALTHY
            
            metrics = HealthMetrics(
                status=status,
                timestamp=datetime.now(),
                response_time=response_time,
                metadata=result.get('metadata', {})
            )
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            metrics = HealthMetrics(
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.now(),
                response_time=response_time,
                error_message=f"Health check '{name}' timed out after {check.timeout}s"
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            metrics = HealthMetrics(
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.now(),
                response_time=response_time,
                error_message=f"Health check '{name}' failed: {str(e)}"
            )
        
        # Store metrics
        if name not in self.health_history:
            self.health_history[name] = []
        
        self.health_history[name].append(metrics)
        
        # Keep only recent history
        if len(self.health_history[name]) > 1000:
            self.health_history[name] = self.health_history[name][-500:]
        
        return metrics
    
    async def _execute_check(self, check_func: Callable) -> Dict[str, Any]:
        """
        Execute a health check function.
        
        Args:
            check_func: Health check function
            
        Returns:
            Health check result
        """
        if asyncio.iscoroutinefunction(check_func):
            return await check_func()
        else:
            return check_func()
    
    async def run_all_health_checks(self) -> Dict[str, HealthMetrics]:
        """
        Run all registered health checks.
        
        Returns:
            Dictionary of health check results
        """
        results = {}
        
        # Run checks concurrently
        tasks = []
        for name in self.health_checks:
            tasks.append(self.run_health_check(name))
        
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (name, result) in enumerate(zip(self.health_checks.keys(), check_results)):
            if isinstance(result, Exception):
                results[name] = HealthMetrics(
                    status=HealthStatus.UNHEALTHY,
                    timestamp=datetime.now(),
                    response_time=0.0,
                    error_message=f"Health check execution failed: {str(result)}"
                )
            else:
                results[name] = result
        
        return results
    
    def get_overall_health_status(self) -> HealthStatus:
        """
        Get overall health status based on all checks.
        
        Returns:
            Overall health status
        """
        if not self.health_history:
            return HealthStatus.UNKNOWN
        
        # Check recent health status for each component
        recent_threshold = datetime.now() - timedelta(minutes=5)
        
        for name, history in self.health_history.items():
            if not history:
                continue
            
            # Get most recent check
            latest_check = max(history, key=lambda x: x.timestamp)
            
            if latest_check.timestamp < recent_threshold:
                return HealthStatus.UNKNOWN
            
            check_def = self.health_checks.get(name)
            if check_def and check_def.critical and latest_check.status == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY
        
        # Check for degraded status
        for name, history in self.health_history.items():
            if not history:
                continue
            
            latest_check = max(history, key=lambda x: x.timestamp)
            if latest_check.status == HealthStatus.DEGRADED:
                return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive health summary.
        
        Returns:
            Dictionary containing health summary
        """
        overall_status = self.get_overall_health_status()
        
        summary = {
            'overall_status': overall_status.value,
            'timestamp': datetime.now().isoformat(),
            'components': {},
            'system_metrics': self._get_system_metrics(),
            'alerts': self._check_alerts()
        }
        
        # Add component health
        for name, history in self.health_history.items():
            if not history:
                continue
            
            latest_check = max(history, key=lambda x: x.timestamp)
            
            # Calculate error rate
            recent_checks = [h for h in history 
                           if h.timestamp > datetime.now() - timedelta(hours=1)]
            error_rate = sum(1 for h in recent_checks if h.status == HealthStatus.UNHEALTHY) / len(recent_checks) if recent_checks else 0
            
            # Calculate average response time
            avg_response_time = sum(h.response_time for h in recent_checks) / len(recent_checks) if recent_checks else 0
            
            summary['components'][name] = {
                'status': latest_check.status.value,
                'last_check': latest_check.timestamp.isoformat(),
                'response_time': latest_check.response_time,
                'avg_response_time': avg_response_time,
                'error_rate': error_rate,
                'error_message': latest_check.error_message,
                'metadata': latest_check.metadata or {}
            }
        
        return summary
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system-level metrics.
        
        Returns:
            Dictionary containing system metrics
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Process info
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_total_gb': memory.total / (1024**3),
                'memory_used_gb': memory.used / (1024**3),
                'memory_percent': memory.percent,
                'disk_total_gb': disk.total / (1024**3),
                'disk_used_gb': disk.used / (1024**3),
                'disk_percent': (disk.used / disk.total) * 100,
                'process_memory_mb': process_memory.rss / (1024**2),
                'process_cpu_percent': process.cpu_percent()
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    def _check_alerts(self) -> List[Dict[str, Any]]:
        """
        Check for alert conditions.
        
        Returns:
            List of alerts
        """
        alerts = []
        system_metrics = self._get_system_metrics()
        
        # Check system metrics
        if system_metrics.get('cpu_percent', 0) > 90:
            alerts.append({
                'type': 'high_cpu',
                'message': f"High CPU usage: {system_metrics.get('cpu_percent', 0):.1f}%",
                'severity': 'warning'
            })
        
        if system_metrics.get('memory_percent', 0) > self.alert_thresholds['memory_usage'] * 100:
            alerts.append({
                'type': 'high_memory',
                'message': f"High memory usage: {system_metrics.get('memory_percent', 0):.1f}%",
                'severity': 'critical'
            })
        
        if system_metrics.get('disk_percent', 0) > self.alert_thresholds['disk_usage'] * 100:
            alerts.append({
                'type': 'high_disk',
                'message': f"High disk usage: {system_metrics.get('disk_percent', 0):.1f}%",
                'severity': 'critical'
            })
        
        # Check component health
        for name, history in self.health_history.items():
            if not history:
                continue
            
            recent_checks = [h for h in history 
                           if h.timestamp > datetime.now() - timedelta(minutes=5)]
            
            if not recent_checks:
                continue
            
            latest_check = max(recent_checks, key=lambda x: x.timestamp)
            
            # Check response time
            if latest_check.response_time > self.alert_thresholds['response_time']:
                alerts.append({
                    'type': 'slow_response',
                    'component': name,
                    'message': f"Slow response time: {latest_check.response_time:.2f}s",
                    'severity': 'warning'
                })
            
            # Check error rate
            error_rate = sum(1 for h in recent_checks if h.status == HealthStatus.UNHEALTHY) / len(recent_checks)
            if error_rate > self.alert_thresholds['error_rate']:
                alerts.append({
                    'type': 'high_error_rate',
                    'component': name,
                    'message': f"High error rate: {error_rate:.1%}",
                    'severity': 'critical'
                })
        
        return alerts
    
    def save_health_state(self, filepath: str):
        """
        Save health state to file.
        
        Args:
            filepath: Path to save state file
        """
        state = {
            'timestamp': datetime.now().isoformat(),
            'health_history': {
                name: [
                    {
                        'status': h.status.value,
                        'timestamp': h.timestamp.isoformat(),
                        'response_time': h.response_time,
                        'error_message': h.error_message,
                        'metadata': h.metadata or {}
                    }
                    for h in history
                ]
                for name, history in self.health_history.items()
            },
            'alert_thresholds': self.alert_thresholds
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Health state saved to {filepath}")
    
    def load_health_state(self, filepath: str):
        """
        Load health state from file.
        
        Args:
            filepath: Path to state file
        """
        if not os.path.exists(filepath):
            logger.warning(f"Health state file not found: {filepath}")
            return
        
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            # Restore health history
            self.health_history = {}
            for name, history_data in state.get('health_history', {}).items():
                self.health_history[name] = [
                    HealthMetrics(
                        status=HealthStatus(h['status']),
                        timestamp=datetime.fromisoformat(h['timestamp']),
                        response_time=h['response_time'],
                        error_message=h.get('error_message'),
                        metadata=h.get('metadata', {})
                    )
                    for h in history_data
                ]
            
            # Restore alert thresholds
            self.alert_thresholds.update(state.get('alert_thresholds', {}))
            
            logger.info(f"Health state loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load health state: {e}")


# Predefined health check functions
async def check_disk_space(path: str = "/", min_free_gb: float = 10.0) -> Dict[str, Any]:
    """
    Check available disk space.
    
    Args:
        path: Path to check
        min_free_gb: Minimum free space in GB
        
    Returns:
        Health check result
    """
    try:
        disk_usage = psutil.disk_usage(path)
        free_gb = disk_usage.free / (1024**3)
        
        return {
            'healthy': free_gb >= min_free_gb,
            'metadata': {
                'free_gb': free_gb,
                'total_gb': disk_usage.total / (1024**3),
                'used_percent': (disk_usage.used / disk_usage.total) * 100
            }
        }
    except Exception as e:
        return {
            'healthy': False,
            'metadata': {'error': str(e)}
        }


async def check_memory_usage(max_percent: float = 90.0) -> Dict[str, Any]:
    """
    Check memory usage.
    
    Args:
        max_percent: Maximum memory usage percentage
        
    Returns:
        Health check result
    """
    try:
        memory = psutil.virtual_memory()
        
        return {
            'healthy': memory.percent <= max_percent,
            'metadata': {
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_total_gb': memory.total / (1024**3)
            }
        }
    except Exception as e:
        return {
            'healthy': False,
            'metadata': {'error': str(e)}
        }


async def check_file_accessibility(filepath: str) -> Dict[str, Any]:
    """
    Check if a file is accessible.
    
    Args:
        filepath: Path to file to check
        
    Returns:
        Health check result
    """
    try:
        accessible = os.path.exists(filepath) and os.access(filepath, os.R_OK)
        
        return {
            'healthy': accessible,
            'metadata': {
                'filepath': filepath,
                'exists': os.path.exists(filepath),
                'readable': os.access(filepath, os.R_OK) if os.path.exists(filepath) else False
            }
        }
    except Exception as e:
        return {
            'healthy': False,
            'metadata': {'error': str(e)}
        }


async def check_process_responsiveness(timeout: float = 5.0) -> Dict[str, Any]:
    """
    Check if the current process is responsive.
    
    Args:
        timeout: Timeout for responsiveness check
        
    Returns:
        Health check result
    """
    try:
        start_time = time.time()
        
        # Simple responsiveness test
        await asyncio.sleep(0.001)
        
        response_time = time.time() - start_time
        
        return {
            'healthy': response_time < timeout,
            'metadata': {
                'response_time': response_time,
                'timeout': timeout
            }
        }
    except Exception as e:
        return {
            'healthy': False,
            'metadata': {'error': str(e)}
        }


# Global health monitor instance
health_monitor = HealthMonitor()

# Register default health checks
health_monitor.register_health_check(
    'disk_space',
    lambda: check_disk_space(),
    timeout=10.0,
    critical=True,
    description="Check available disk space"
)

health_monitor.register_health_check(
    'memory_usage',
    lambda: check_memory_usage(),
    timeout=5.0,
    critical=True,
    description="Check memory usage"
)

health_monitor.register_health_check(
    'process_responsiveness',
    lambda: check_process_responsiveness(),
    timeout=10.0,
    critical=False,
    description="Check process responsiveness"
)
