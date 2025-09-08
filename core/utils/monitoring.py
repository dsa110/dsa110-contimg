# core/utils/monitoring.py
"""
Monitoring and metrics utilities for DSA-110 pipeline.

This module provides health checks, performance metrics, and monitoring
capabilities for the pipeline services and components.
"""

import time
import psutil
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import os


@dataclass
class HealthStatus:
    """Health status information for a service or component."""
    name: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    timestamp: datetime
    details: Dict[str, Any]
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class PerformanceMetrics:
    """Performance metrics for pipeline operations."""
    operation: str
    duration_seconds: float
    timestamp: datetime
    success: bool
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class PipelineMetrics:
    """
    Centralized metrics collection for the pipeline.
    """
    
    def __init__(self, metrics_file: Optional[str] = None):
        self.metrics_file = metrics_file or "pipeline_metrics.json"
        self.metrics_history: List[PerformanceMetrics] = []
        self.logger = logging.getLogger(__name__)
    
    def record_block_processing(self, block_id: str, success: bool, 
                              processing_time: float, ms_count: int, 
                              image_count: int, **kwargs):
        """Record metrics for block processing."""
        metrics = PerformanceMetrics(
            operation="block_processing",
            duration_seconds=processing_time,
            timestamp=datetime.now(),
            success=success,
            metadata={
                'block_id': block_id,
                'ms_count': ms_count,
                'image_count': image_count,
                **kwargs
            }
        )
        
        self.metrics_history.append(metrics)
        self._save_metrics()
        
        self.logger.info(
            f"Block processing metrics recorded",
            block_id=block_id,
            success=success,
            processing_time=processing_time,
            ms_count=ms_count,
            image_count=image_count
        )
    
    def record_stage_processing(self, stage: str, duration: float, 
                              success: bool, **kwargs):
        """Record metrics for individual stage processing."""
        metrics = PerformanceMetrics(
            operation=f"stage_{stage}",
            duration_seconds=duration,
            timestamp=datetime.now(),
            success=success,
            metadata={'stage': stage, **kwargs}
        )
        
        self.metrics_history.append(metrics)
        self._save_metrics()
    
    def get_recent_metrics(self, hours: int = 24) -> List[PerformanceMetrics]:
        """Get metrics from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_success_rate(self, hours: int = 24) -> float:
        """Calculate success rate for the last N hours."""
        recent_metrics = self.get_recent_metrics(hours)
        if not recent_metrics:
            return 0.0
        
        successful = sum(1 for m in recent_metrics if m.success)
        return successful / len(recent_metrics)
    
    def get_average_processing_time(self, hours: int = 24) -> float:
        """Calculate average processing time for the last N hours."""
        recent_metrics = self.get_recent_metrics(hours)
        if not recent_metrics:
            return 0.0
        
        total_time = sum(m.duration_seconds for m in recent_metrics)
        return total_time / len(recent_metrics)
    
    def _save_metrics(self):
        """Save metrics to file (keep only last 1000 entries)."""
        # Keep only the most recent 1000 metrics to prevent file from growing too large
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump([m.to_dict() for m in self.metrics_history], f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")


class HealthChecker:
    """
    Health checking utilities for pipeline components.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_system_health(self) -> HealthStatus:
        """Check overall system health."""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Determine overall status
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 95:
                status = 'unhealthy'
            elif cpu_percent > 70 or memory_percent > 70 or disk_percent > 85:
                status = 'degraded'
            else:
                status = 'healthy'
            
            return HealthStatus(
                name="system",
                status=status,
                timestamp=datetime.now(),
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_free_gb': disk.free / (1024**3)
                }
            )
            
        except Exception as e:
            return HealthStatus(
                name="system",
                status="unhealthy",
                timestamp=datetime.now(),
                details={},
                error_message=str(e)
            )
    
    def check_directory_health(self, directory: str) -> HealthStatus:
        """Check if a directory is accessible and has sufficient space."""
        try:
            if not os.path.exists(directory):
                return HealthStatus(
                    name=f"directory_{os.path.basename(directory)}",
                    status="unhealthy",
                    timestamp=datetime.now(),
                    details={'path': directory},
                    error_message="Directory does not exist"
                )
            
            if not os.access(directory, os.R_OK | os.W_OK):
                return HealthStatus(
                    name=f"directory_{os.path.basename(directory)}",
                    status="unhealthy",
                    timestamp=datetime.now(),
                    details={'path': directory},
                    error_message="Directory not readable/writable"
                )
            
            # Check disk space
            disk = psutil.disk_usage(directory)
            disk_percent = (disk.used / disk.total) * 100
            
            if disk_percent > 95:
                status = 'unhealthy'
            elif disk_percent > 85:
                status = 'degraded'
            else:
                status = 'healthy'
            
            return HealthStatus(
                name=f"directory_{os.path.basename(directory)}",
                status=status,
                timestamp=datetime.now(),
                details={
                    'path': directory,
                    'disk_percent': disk_percent,
                    'free_space_gb': disk.free / (1024**3)
                }
            )
            
        except Exception as e:
            return HealthStatus(
                name=f"directory_{os.path.basename(directory)}",
                status="unhealthy",
                timestamp=datetime.now(),
                details={'path': directory},
                error_message=str(e)
            )
    
    def check_file_health(self, file_path: str) -> HealthStatus:
        """Check if a file exists and is accessible."""
        try:
            if not os.path.exists(file_path):
                return HealthStatus(
                    name=f"file_{os.path.basename(file_path)}",
                    status="unhealthy",
                    timestamp=datetime.now(),
                    details={'path': file_path},
                    error_message="File does not exist"
                )
            
            if not os.access(file_path, os.R_OK):
                return HealthStatus(
                    name=f"file_{os.path.basename(file_path)}",
                    status="unhealthy",
                    timestamp=datetime.now(),
                    details={'path': file_path},
                    error_message="File not readable"
                )
            
            # Check file size and modification time
            stat = os.stat(file_path)
            file_size_mb = stat.st_size / (1024**2)
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            age_hours = (datetime.now() - mod_time).total_seconds() / 3600
            
            return HealthStatus(
                name=f"file_{os.path.basename(file_path)}",
                status="healthy",
                timestamp=datetime.now(),
                details={
                    'path': file_path,
                    'size_mb': file_size_mb,
                    'age_hours': age_hours,
                    'modified': mod_time.isoformat()
                }
            )
            
        except Exception as e:
            return HealthStatus(
                name=f"file_{os.path.basename(file_path)}",
                status="unhealthy",
                timestamp=datetime.now(),
                details={'path': file_path},
                error_message=str(e)
            )
    
    def check_all_health(self, config: Dict[str, Any]) -> List[HealthStatus]:
        """Check health of all pipeline components."""
        health_checks = []
        
        # System health
        health_checks.append(self.check_system_health())
        
        # Check all configured directories
        paths_config = config.get('paths', {})
        for key, path in paths_config.items():
            if key.endswith('_dir') and path:
                health_checks.append(self.check_directory_health(path))
        
        return health_checks
