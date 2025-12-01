"""
Prometheus Metrics Exporter for DSA-110 Continuum Imaging Pipeline.

This module exports health check metrics in Prometheus format for
integration with Grafana dashboards and alerting.

Metrics exported:
- contimg_storage_files_on_disk: Number of HDF5 files on disk
- contimg_storage_files_indexed: Number of files indexed in database
- contimg_storage_sync_percentage: Percentage of files synchronized
- contimg_storage_orphaned_files: Files on disk but not in database
- contimg_storage_stale_records: Database records for missing files
- contimg_service_status: Service health status (1=running, 0=stopped, -1=error)
- contimg_service_response_time_ms: Service response time in milliseconds
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """A single metric value with labels."""
    name: str
    value: float
    labels: Dict[str, str] = None  # type: ignore
    help_text: str = ""
    metric_type: str = "gauge"
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


class PrometheusExporter:
    """Export metrics in Prometheus text format."""
    
    def __init__(self):
        self.metrics: List[MetricValue] = []
        self._last_collection_time: Optional[float] = None
        self._cache_ttl_seconds = 30  # Cache metrics for 30 seconds
    
    def clear(self):
        """Clear all metrics."""
        self.metrics = []
    
    def add_metric(self, metric: MetricValue):
        """Add a metric value directly."""
        self.metrics.append(metric)
    
    def add_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help_text: str = "",
    ):
        """Add a gauge metric."""
        self.metrics.append(MetricValue(
            name=name,
            value=value,
            labels=labels or {},
            help_text=help_text,
            metric_type="gauge",
        ))
    
    def add_counter(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help_text: str = "",
    ):
        """Add a counter metric."""
        self.metrics.append(MetricValue(
            name=name,
            value=value,
            labels=labels or {},
            help_text=help_text,
            metric_type="counter",
        ))
    
    def format_prometheus(self) -> str:
        """Format metrics in Prometheus text exposition format."""
        lines = []
        seen_metrics = set()
        
        for metric in self.metrics:
            # Add HELP and TYPE only once per metric name
            if metric.name not in seen_metrics:
                if metric.help_text:
                    lines.append(f"# HELP {metric.name} {metric.help_text}")
                lines.append(f"# TYPE {metric.name} {metric.metric_type}")
                seen_metrics.add(metric.name)
            
            # Format labels
            if metric.labels:
                label_str = ",".join(
                    f'{k}="{v}"' for k, v in sorted(metric.labels.items())
                )
                lines.append(f"{metric.name}{{{label_str}}} {metric.value}")
            else:
                lines.append(f"{metric.name} {metric.value}")
        
        return "\n".join(lines) + "\n"


async def collect_all_metrics(
    hdf5_db_path: str,
    incoming_dir: str,
    docker_containers: Optional[List[str]] = None,
    systemd_services: Optional[List[str]] = None,
) -> PrometheusExporter:
    """
    Collect all metrics for Prometheus export.
    
    Args:
        hdf5_db_path: Path to HDF5 index database
        incoming_dir: Path to HDF5 storage directory
        docker_containers: List of Docker container names to monitor
        systemd_services: List of systemd service names to monitor
    
    Returns:
        PrometheusExporter with all metrics
    """
    from dsa110_contimg.database.storage_validator import get_storage_metrics
    from dsa110_contimg.monitoring.service_health import (
        check_docker_container,
        check_systemd_service,
        ServiceStatus,
    )
    
    exporter = PrometheusExporter()
    collection_start = time.time()
    
    # Storage metrics
    try:
        storage = get_storage_metrics(hdf5_db_path, incoming_dir)
        
        exporter.add_gauge(
            "contimg_storage_files_on_disk",
            storage["files_on_disk"],
            help_text="Number of HDF5 files on disk",
        )
        exporter.add_gauge(
            "contimg_storage_files_indexed",
            storage["files_in_db_stored"],
            help_text="Number of files indexed in database as stored",
        )
        exporter.add_gauge(
            "contimg_storage_files_total",
            storage["files_in_db_total"],
            help_text="Total number of files in database index",
        )
        
        # Calculate sync percentage
        if storage["files_on_disk"] > 0:
            sync_pct = min(
                (storage["files_in_db_stored"] / storage["files_on_disk"]) * 100,
                100.0
            )
        else:
            sync_pct = 100.0 if storage["files_in_db_stored"] == 0 else 0.0
        
        exporter.add_gauge(
            "contimg_storage_sync_percentage",
            sync_pct,
            help_text="Percentage of files synchronized between disk and database",
        )
        exporter.add_gauge(
            "contimg_storage_synchronized",
            1.0 if storage["count_matches"] else 0.0,
            help_text="Whether storage is synchronized (1=yes, 0=no)",
        )
    except Exception as e:
        logger.error(f"Failed to collect storage metrics: {e}")
        exporter.add_gauge(
            "contimg_storage_collection_error",
            1.0,
            labels={"error": str(e)[:50]},
            help_text="Error collecting storage metrics",
        )
    
    # Docker container metrics
    if docker_containers:
        for container in docker_containers:
            try:
                result = check_docker_container(container)
                status_value = {
                    ServiceStatus.RUNNING: 1.0,
                    ServiceStatus.STOPPED: 0.0,
                    ServiceStatus.DEGRADED: 0.5,
                    ServiceStatus.ERROR: -1.0,
                    ServiceStatus.UNKNOWN: -2.0,
                }.get(result.status, -2.0)
                
                exporter.add_gauge(
                    "contimg_docker_container_status",
                    status_value,
                    labels={"container": container},
                    help_text="Docker container status (1=running, 0=stopped, -1=error)",
                )
                if result.response_time_ms is not None:
                    exporter.add_gauge(
                        "contimg_docker_container_check_duration_ms",
                        result.response_time_ms,
                        labels={"container": container},
                        help_text="Time to check container status in milliseconds",
                    )
            except Exception as e:
                logger.error(f"Failed to check container {container}: {e}")
    
    # Systemd service metrics
    if systemd_services:
        for service in systemd_services:
            try:
                result = check_systemd_service(service)
                status_value = {
                    ServiceStatus.RUNNING: 1.0,
                    ServiceStatus.STOPPED: 0.0,
                    ServiceStatus.DEGRADED: 0.5,
                    ServiceStatus.ERROR: -1.0,
                    ServiceStatus.UNKNOWN: -2.0,
                }.get(result.status, -2.0)
                
                exporter.add_gauge(
                    "contimg_systemd_service_status",
                    status_value,
                    labels={"service": service},
                    help_text="Systemd service status (1=running, 0=stopped, -1=error)",
                )
                if result.response_time_ms is not None:
                    exporter.add_gauge(
                        "contimg_systemd_service_check_duration_ms",
                        result.response_time_ms,
                        labels={"service": service},
                        help_text="Time to check service status in milliseconds",
                    )
            except Exception as e:
                logger.error(f"Failed to check service {service}: {e}")
    
    # Collection metadata
    collection_duration = (time.time() - collection_start) * 1000
    exporter.add_gauge(
        "contimg_metrics_collection_duration_ms",
        collection_duration,
        help_text="Time to collect all metrics in milliseconds",
    )
    exporter.add_gauge(
        "contimg_metrics_last_collection_timestamp",
        time.time(),
        help_text="Unix timestamp of last metrics collection",
    )
    
    return exporter
