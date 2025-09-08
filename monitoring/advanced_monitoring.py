# monitoring/advanced_monitoring.py
"""
Advanced monitoring and alerting system for DSA-110 pipeline.

This module provides real-time monitoring, alerting, and dashboard capabilities
for the pipeline with support for metrics collection, threshold monitoring,
and automated alerting.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import statistics

from core.utils.logging import get_logger
from core.utils.monitoring import HealthStatus, PerformanceMetrics
from core.messaging.message_queue import MessageQueue, MessageType, MessagePriority

logger = get_logger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Alert:
    """An alert with metadata."""
    id: str
    level: AlertLevel
    title: str
    message: str
    source: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'level': self.level.value,
            'title': self.title,
            'message': self.message,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            level=AlertLevel(data['level']),
            title=data['title'],
            message=data['message'],
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            resolved=data.get('resolved', False),
            resolved_at=datetime.fromisoformat(data['resolved_at']) if data.get('resolved_at') else None,
            metadata=data.get('metadata', {})
        )


@dataclass
class Metric:
    """A metric with metadata."""
    name: str
    value: Union[float, int]
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = None
    unit: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'value': self.value,
            'metric_type': self.metric_type.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags,
            'unit': self.unit
        }


@dataclass
class ThresholdRule:
    """A threshold rule for alerting."""
    name: str
    metric_name: str
    operator: str  # '>', '<', '>=', '<=', '==', '!='
    threshold_value: float
    alert_level: AlertLevel
    duration: int  # Duration in seconds before alerting
    enabled: bool = True
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if the threshold is exceeded."""
        if not self.enabled:
            return False
        
        if self.operator == '>':
            return value > self.threshold_value
        elif self.operator == '<':
            return value < self.threshold_value
        elif self.operator == '>=':
            return value >= self.threshold_value
        elif self.operator == '<=':
            return value <= self.threshold_value
        elif self.operator == '==':
            return value == self.threshold_value
        elif self.operator == '!=':
            return value != self.threshold_value
        
        return False


class AdvancedMonitor:
    """
    Advanced monitoring system with real-time metrics, alerting, and dashboards.
    
    Provides comprehensive monitoring capabilities including:
    - Real-time metrics collection
    - Threshold-based alerting
    - Health status monitoring
    - Performance tracking
    - Alert management
    """
    
    def __init__(self, message_queue: Optional[MessageQueue] = None):
        """
        Initialize the advanced monitor.
        
        Args:
            message_queue: Optional message queue for distributed monitoring
        """
        self.message_queue = message_queue
        self.metrics: Dict[str, List[Metric]] = {}
        self.alerts: Dict[str, Alert] = {}
        self.threshold_rules: Dict[str, ThresholdRule] = {}
        self.health_checks: Dict[str, HealthStatus] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self.running = False
        
        logger.info("Advanced monitor initialized")
    
    async def start(self):
        """Start the monitoring system."""
        if self.running:
            logger.warning("Monitor is already running")
            return
        
        self.running = True
        logger.info("Started advanced monitoring system")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._metrics_processor()),
            asyncio.create_task(self._threshold_monitor()),
            asyncio.create_task(self._health_monitor()),
            asyncio.create_task(self._alert_processor())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in monitoring tasks: {e}")
        finally:
            self.running = False
    
    async def stop(self):
        """Stop the monitoring system."""
        self.running = False
        logger.info("Stopped advanced monitoring system")
    
    async def record_metric(self, name: str, value: Union[float, int],
                          metric_type: MetricType = MetricType.GAUGE,
                          tags: Dict[str, str] = None, unit: Optional[str] = None):
        """
        Record a metric.
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            tags: Optional tags
            unit: Optional unit
        """
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            tags=tags or {},
            unit=unit
        )
        
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append(metric)
        
        # Keep only recent metrics (last 1000 per metric)
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
        
        logger.debug(f"Recorded metric: {name} = {value}")
    
    async def add_threshold_rule(self, rule: ThresholdRule):
        """
        Add a threshold rule for alerting.
        
        Args:
            rule: Threshold rule
        """
        self.threshold_rules[rule.name] = rule
        logger.info(f"Added threshold rule: {rule.name}")
    
    async def remove_threshold_rule(self, rule_name: str):
        """
        Remove a threshold rule.
        
        Args:
            rule_name: Name of the rule to remove
        """
        if rule_name in self.threshold_rules:
            del self.threshold_rules[rule_name]
            logger.info(f"Removed threshold rule: {rule_name}")
    
    async def create_alert(self, level: AlertLevel, title: str, message: str,
                          source: str, metadata: Dict[str, Any] = None) -> Alert:
        """
        Create a new alert.
        
        Args:
            level: Alert level
            title: Alert title
            message: Alert message
            source: Alert source
            metadata: Optional metadata
            
        Returns:
            Created alert
        """
        alert = Alert(
            id=f"alert_{int(time.time())}_{len(self.alerts)}",
            level=level,
            title=title,
            message=message,
            source=source,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.alerts[alert.id] = alert
        
        # Send alert via message queue if available
        if self.message_queue:
            await self.message_queue.publish(
                "alerts",
                self.message_queue.create_message(
                    MessageType.ERROR_NOTIFICATION,
                    alert.to_dict(),
                    "monitor",
                    priority=MessagePriority.HIGH
                )
            )
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        logger.warning(f"Created alert: {title} ({level.value})")
        return alert
    
    async def resolve_alert(self, alert_id: str):
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert ID
        """
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            self.alerts[alert_id].resolved_at = datetime.now()
            logger.info(f"Resolved alert: {alert_id}")
    
    async def add_alert_callback(self, callback: Callable[[Alert], None]):
        """
        Add an alert callback.
        
        Args:
            callback: Callback function
        """
        self.alert_callbacks.append(callback)
        logger.info("Added alert callback")
    
    async def update_health_status(self, name: str, status: HealthStatus):
        """
        Update health status.
        
        Args:
            name: Health check name
            status: Health status
        """
        self.health_checks[name] = status
        logger.debug(f"Updated health status: {name} = {status.status}")
    
    async def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get metrics summary for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Metrics summary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        summary = {}
        for metric_name, metrics in self.metrics.items():
            recent_metrics = [
                m for m in metrics
                if m.timestamp >= cutoff_time
            ]
            
            if recent_metrics:
                values = [m.value for m in recent_metrics]
                summary[metric_name] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'unit': recent_metrics[0].unit
                }
        
        return summary
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get health status summary."""
        healthy_count = sum(1 for hc in self.health_checks.values() if hc.status == 'healthy')
        degraded_count = sum(1 for hc in self.health_checks.values() if hc.status == 'degraded')
        unhealthy_count = sum(1 for hc in self.health_checks.values() if hc.status == 'unhealthy')
        
        return {
            'total_checks': len(self.health_checks),
            'healthy': healthy_count,
            'degraded': degraded_count,
            'unhealthy': unhealthy_count,
            'health_checks': {name: hc.to_dict() for name, hc in self.health_checks.items()}
        }
    
    async def _metrics_processor(self):
        """Background task to process metrics."""
        while self.running:
            try:
                # Process metrics (e.g., aggregation, cleanup)
                await asyncio.sleep(60)  # Process every minute
            except Exception as e:
                logger.error(f"Error in metrics processor: {e}")
                await asyncio.sleep(10)
    
    async def _threshold_monitor(self):
        """Background task to monitor thresholds."""
        while self.running:
            try:
                # Check threshold rules
                for rule_name, rule in self.threshold_rules.items():
                    if rule.metric_name in self.metrics:
                        recent_metrics = self.metrics[rule.metric_name][-10:]  # Last 10 values
                        if recent_metrics:
                            latest_value = recent_metrics[-1].value
                            
                            if rule.evaluate(latest_value):
                                await self.create_alert(
                                    rule.alert_level,
                                    f"Threshold exceeded: {rule.name}",
                                    f"Metric {rule.metric_name} = {latest_value} {rule.operator} {rule.threshold_value}",
                                    "threshold_monitor",
                                    {
                                        'rule_name': rule.name,
                                        'metric_name': rule.metric_name,
                                        'value': latest_value,
                                        'threshold': rule.threshold_value,
                                        'operator': rule.operator
                                    }
                                )
                
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in threshold monitor: {e}")
                await asyncio.sleep(10)
    
    async def _health_monitor(self):
        """Background task to monitor health status."""
        while self.running:
            try:
                # Check for unhealthy services
                for name, health_status in self.health_checks.items():
                    if health_status.status == 'unhealthy':
                        # Check if we already have an alert for this
                        existing_alerts = [
                            alert for alert in self.alerts.values()
                            if (not alert.resolved and 
                                alert.source == 'health_monitor' and
                                alert.metadata.get('service_name') == name)
                        ]
                        
                        if not existing_alerts:
                            await self.create_alert(
                                AlertLevel.ERROR,
                                f"Service unhealthy: {name}",
                                f"Service {name} is in unhealthy state: {health_status.error_message}",
                                "health_monitor",
                                {'service_name': name, 'health_status': health_status.to_dict()}
                            )
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(10)
    
    async def _alert_processor(self):
        """Background task to process alerts."""
        while self.running:
            try:
                # Process alerts (e.g., cleanup old resolved alerts)
                cutoff_time = datetime.now() - timedelta(hours=24)
                old_alerts = [
                    alert_id for alert_id, alert in self.alerts.items()
                    if alert.resolved and alert.resolved_at and alert.resolved_at < cutoff_time
                ]
                
                for alert_id in old_alerts:
                    del self.alerts[alert_id]
                
                if old_alerts:
                    logger.info(f"Cleaned up {len(old_alerts)} old alerts")
                
                await asyncio.sleep(3600)  # Cleanup every hour
            except Exception as e:
                logger.error(f"Error in alert processor: {e}")
                await asyncio.sleep(60)


class MonitoringDashboard:
    """
    Monitoring dashboard for real-time pipeline monitoring.
    
    Provides a web-based dashboard for monitoring pipeline status,
    metrics, alerts, and health checks.
    """
    
    def __init__(self, monitor: AdvancedMonitor, port: int = 8080):
        """
        Initialize the monitoring dashboard.
        
        Args:
            monitor: Advanced monitor instance
            port: Dashboard port
        """
        self.monitor = monitor
        self.port = port
        self.app = None
        
        logger.info(f"Monitoring dashboard initialized on port {port}")
    
    async def start(self):
        """Start the monitoring dashboard."""
        try:
            from aiohttp import web, web_request
            import aiohttp_cors
            
            self.app = web.Application()
            cors = aiohttp_cors.setup(self.app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
            
            # Add routes
            self.app.router.add_get('/api/health', self._health_handler)
            self.app.router.add_get('/api/metrics', self._metrics_handler)
            self.app.router.add_get('/api/alerts', self._alerts_handler)
            self.app.router.add_get('/api/dashboard', self._dashboard_handler)
            
            # Add CORS to all routes
            for route in list(self.app.router.routes()):
                cors.add(route)
            
            # Start server
            runner = web.AppRunner(self.app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', self.port)
            await site.start()
            
            logger.info(f"Monitoring dashboard started on http://0.0.0.0:{self.port}")
            
        except ImportError:
            logger.error("aiohttp not available. Install with: pip install aiohttp aiohttp-cors")
            raise
        except Exception as e:
            logger.error(f"Failed to start monitoring dashboard: {e}")
            raise
    
    async def _health_handler(self, request: web_request.Request):
        """Handle health status requests."""
        try:
            health_summary = await self.monitor.get_health_summary()
            return web.json_response(health_summary)
        except Exception as e:
            logger.error(f"Error in health handler: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _metrics_handler(self, request: web_request.Request):
        """Handle metrics requests."""
        try:
            hours = int(request.query.get('hours', 24))
            metrics_summary = await self.monitor.get_metrics_summary(hours)
            return web.json_response(metrics_summary)
        except Exception as e:
            logger.error(f"Error in metrics handler: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _alerts_handler(self, request: web_request.Request):
        """Handle alerts requests."""
        try:
            active_alerts = await self.monitor.get_active_alerts()
            return web.json_response([alert.to_dict() for alert in active_alerts])
        except Exception as e:
            logger.error(f"Error in alerts handler: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _dashboard_handler(self, request: web_request.Request):
        """Handle dashboard requests."""
        try:
            # Return simple HTML dashboard
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>DSA-110 Pipeline Monitor</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .metric { margin: 10px 0; padding: 10px; border: 1px solid #ccc; }
                    .alert { margin: 10px 0; padding: 10px; border-radius: 5px; }
                    .alert.error { background-color: #ffebee; border-left: 4px solid #f44336; }
                    .alert.warning { background-color: #fff3e0; border-left: 4px solid #ff9800; }
                    .alert.info { background-color: #e3f2fd; border-left: 4px solid #2196f3; }
                </style>
            </head>
            <body>
                <h1>DSA-110 Pipeline Monitor</h1>
                <div id="content">
                    <p>Loading...</p>
                </div>
                <script>
                    async function loadDashboard() {
                        try {
                            const [health, metrics, alerts] = await Promise.all([
                                fetch('/api/health').then(r => r.json()),
                                fetch('/api/metrics').then(r => r.json()),
                                fetch('/api/alerts').then(r => r.json())
                            ]);
                            
                            let html = '<h2>Health Status</h2>';
                            html += `<p>Total: ${health.total_checks}, Healthy: ${health.healthy}, Degraded: ${health.degraded}, Unhealthy: ${health.unhealthy}</p>`;
                            
                            html += '<h2>Active Alerts</h2>';
                            if (alerts.length === 0) {
                                html += '<p>No active alerts</p>';
                            } else {
                                alerts.forEach(alert => {
                                    html += `<div class="alert ${alert.level}">
                                        <strong>${alert.title}</strong><br>
                                        ${alert.message}<br>
                                        <small>${new Date(alert.timestamp).toLocaleString()}</small>
                                    </div>`;
                                });
                            }
                            
                            html += '<h2>Metrics</h2>';
                            Object.keys(metrics).forEach(metric => {
                                const data = metrics[metric];
                                html += `<div class="metric">
                                    <strong>${metric}</strong><br>
                                    Count: ${data.count}, Mean: ${data.mean.toFixed(2)}, Min: ${data.min}, Max: ${data.max}
                                </div>`;
                            });
                            
                            document.getElementById('content').innerHTML = html;
                        } catch (error) {
                            document.getElementById('content').innerHTML = '<p>Error loading dashboard: ' + error.message + '</p>';
                        }
                    }
                    
                    loadDashboard();
                    setInterval(loadDashboard, 30000); // Refresh every 30 seconds
                </script>
            </body>
            </html>
            """
            return web.Response(text=html, content_type='text/html')
        except Exception as e:
            logger.error(f"Error in dashboard handler: {e}")
            return web.json_response({'error': str(e)}, status=500)