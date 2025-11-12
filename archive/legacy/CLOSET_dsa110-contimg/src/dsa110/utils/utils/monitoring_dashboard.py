# core/utils/monitoring_dashboard.py
"""
Monitoring dashboard for the DSA-110 pipeline.

This module provides a web-based monitoring dashboard for viewing
pipeline health, performance metrics, and system status.
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import webbrowser
import tempfile

from .logging import get_logger
from .health_monitoring import health_monitor, HealthStatus
from .error_recovery import error_recovery_manager

logger = get_logger(__name__)


@dataclass
class DashboardConfig:
    """Configuration for the monitoring dashboard."""
    port: int = 8080
    host: str = "localhost"
    auto_refresh: int = 30  # seconds
    max_history: int = 1000
    enable_alerts: bool = True


class MonitoringDashboard:
    """
    Web-based monitoring dashboard for the pipeline.
    
    Provides real-time monitoring of pipeline health, performance,
    and system metrics through a web interface.
    """
    
    def __init__(self, config: Optional[DashboardConfig] = None):
        """
        Initialize monitoring dashboard.
        
        Args:
            config: Dashboard configuration
        """
        self.config = config or DashboardConfig()
        self.dashboard_data = {
            'pipeline_stages': [
                'data_ingestion',
                'calibration', 
                'imaging',
                'mosaicking',
                'photometry'
            ],
            'system_metrics': {},
            'health_status': {},
            'error_recovery': {},
            'alerts': [],
            'last_updated': None
        }
        self.alert_history = []
        self.metric_history = []
    
    async def update_dashboard_data(self):
        """Update all dashboard data."""
        try:
            # Update health status
            health_results = await health_monitor.run_all_health_checks()
            self.dashboard_data['health_status'] = {
                name: {
                    'status': result.status.value,
                    'response_time': result.response_time,
                    'error_message': result.error_message,
                    'timestamp': result.timestamp.isoformat()
                }
                for name, result in health_results.items()
            }
            
            # Update system metrics
            health_summary = health_monitor.get_health_summary()
            self.dashboard_data['system_metrics'] = health_summary.get('system_metrics', {})
            
            # Update error recovery status
            recovery_status = error_recovery_manager.get_health_status()
            self.dashboard_data['error_recovery'] = recovery_status
            
            # Update alerts
            self.dashboard_data['alerts'] = health_summary.get('alerts', [])
            
            # Store alert history
            for alert in self.dashboard_data['alerts']:
                alert['timestamp'] = datetime.now().isoformat()
                self.alert_history.append(alert)
            
            # Keep only recent alerts
            if len(self.alert_history) > self.config.max_history:
                self.alert_history = self.alert_history[-self.config.max_history:]
            
            # Update timestamp
            self.dashboard_data['last_updated'] = datetime.now().isoformat()
            
            logger.debug("Dashboard data updated")
            
        except Exception as e:
            logger.error(f"Failed to update dashboard data: {e}")
    
    def generate_html_dashboard(self) -> str:
        """
        Generate HTML dashboard.
        
        Returns:
            HTML content for the dashboard
        """
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DSA-110 Pipeline Monitoring Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .status-healthy {{ background-color: #4CAF50; }}
        .status-degraded {{ background-color: #FF9800; }}
        .status-unhealthy {{ background-color: #F44336; }}
        .status-unknown {{ background-color: #9E9E9E; }}
        .metric {{
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }}
        .metric-label {{
            font-weight: 500;
            color: #555;
        }}
        .metric-value {{
            font-weight: bold;
            color: #333;
        }}
        .alert {{
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 4px solid;
        }}
        .alert-warning {{
            background-color: #fff3cd;
            border-color: #ffc107;
            color: #856404;
        }}
        .alert-critical {{
            background-color: #f8d7da;
            border-color: #dc3545;
            color: #721c24;
        }}
        .pipeline-stage {{
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #ddd;
        }}
        .refresh-info {{
            text-align: center;
            color: #666;
            font-size: 0.9em;
            margin-top: 20px;
        }}
        .auto-refresh {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
    </style>
    <script>
        // Auto-refresh functionality
        let refreshInterval;
        
        function startAutoRefresh() {{
            refreshInterval = setInterval(() => {{
                location.reload();
            }}, {self.config.auto_refresh * 1000});
        }}
        
        function stopAutoRefresh() {{
            if (refreshInterval) {{
                clearInterval(refreshInterval);
            }}
        }}
        
        // Start auto-refresh on page load
        window.onload = function() {{
            startAutoRefresh();
        }};
        
        // Stop auto-refresh when page is hidden
        document.addEventListener('visibilitychange', function() {{
            if (document.hidden) {{
                stopAutoRefresh();
            }} else {{
                startAutoRefresh();
            }}
        }});
    </script>
</head>
<body>
    <div class="header">
        <h1>🔭 DSA-110 Pipeline Monitoring Dashboard</h1>
        <p>Real-time monitoring of continuum imaging pipeline</p>
    </div>
    
    <div class="auto-refresh">
        <label>
            <input type="checkbox" checked onchange="if(this.checked) startAutoRefresh(); else stopAutoRefresh();">
            Auto-refresh ({self.config.auto_refresh}s)
        </label>
    </div>
    
    <div class="dashboard-grid">
        {self._generate_health_status_card()}
        {self._generate_system_metrics_card()}
        {self._generate_pipeline_stages_card()}
        {self._generate_error_recovery_card()}
    </div>
    
    <div class="card">
        <h3>🚨 Alerts</h3>
        {self._generate_alerts_section()}
    </div>
    
    <div class="refresh-info">
        Last updated: {self.dashboard_data.get('last_updated', 'Never')}
    </div>
</body>
</html>
        """
        return html_content
    
    def _generate_health_status_card(self) -> str:
        """Generate health status card HTML."""
        overall_status = health_monitor.get_overall_health_status()
        status_class = f"status-{overall_status.value}"
        
        health_items = []
        for name, status_data in self.dashboard_data.get('health_status', {}).items():
            status_class_item = f"status-{status_data['status']}"
            health_items.append(f"""
                <div class="metric">
                    <span class="metric-label">
                        <span class="status-indicator {status_class_item}"></span>
                        {name.replace('_', ' ').title()}
                    </span>
                    <span class="metric-value">{status_data['response_time']:.2f}s</span>
                </div>
            """)
        
        return f"""
        <div class="card">
            <h3>🏥 Health Status</h3>
            <div class="metric">
                <span class="metric-label">
                    <span class="status-indicator {status_class}"></span>
                    Overall Status
                </span>
                <span class="metric-value">{overall_status.value.title()}</span>
            </div>
            {''.join(health_items)}
        </div>
        """
    
    def _generate_system_metrics_card(self) -> str:
        """Generate system metrics card HTML."""
        metrics = self.dashboard_data.get('system_metrics', {})
        
        metrics_html = []
        if metrics:
            metrics_html.extend([
                f'<div class="metric"><span class="metric-label">CPU Usage</span><span class="metric-value">{metrics.get("cpu_percent", 0):.1f}%</span></div>',
                f'<div class="metric"><span class="metric-label">Memory Usage</span><span class="metric-value">{metrics.get("memory_percent", 0):.1f}%</span></div>',
                f'<div class="metric"><span class="metric-label">Memory Used</span><span class="metric-value">{metrics.get("memory_used_gb", 0):.1f} GB</span></div>',
                f'<div class="metric"><span class="metric-label">Disk Usage</span><span class="metric-value">{metrics.get("disk_percent", 0):.1f}%</span></div>',
                f'<div class="metric"><span class="metric-label">Disk Used</span><span class="metric-value">{metrics.get("disk_used_gb", 0):.1f} GB</span></div>',
                f'<div class="metric"><span class="metric-label">Process Memory</span><span class="metric-value">{metrics.get("process_memory_mb", 0):.1f} MB</span></div>'
            ])
        else:
            metrics_html.append('<div class="metric"><span class="metric-label">No metrics available</span></div>')
        
        return f"""
        <div class="card">
            <h3>💻 System Metrics</h3>
            {''.join(metrics_html)}
        </div>
        """
    
    def _generate_pipeline_stages_card(self) -> str:
        """Generate pipeline stages card HTML."""
        stages_html = []
        for stage in self.dashboard_data.get('pipeline_stages', []):
            # Get health status for this stage
            stage_status = self.dashboard_data.get('health_status', {}).get(stage, {})
            status = stage_status.get('status', 'unknown')
            status_class = f"status-{status}"
            
            stages_html.append(f"""
                <div class="pipeline-stage">
                    <span class="status-indicator {status_class}"></span>
                    <strong>{stage.replace('_', ' ').title()}</strong>
                    <span style="float: right;">{status.title()}</span>
                </div>
            """)
        
        return f"""
        <div class="card">
            <h3>🔄 Pipeline Stages</h3>
            {''.join(stages_html)}
        </div>
        """
    
    def _generate_error_recovery_card(self) -> str:
        """Generate error recovery card HTML."""
        recovery_data = self.dashboard_data.get('error_recovery', {})
        
        if not recovery_data:
            return """
            <div class="card">
                <h3>🛡️ Error Recovery</h3>
                <div class="metric">
                    <span class="metric-label">No recovery data available</span>
                </div>
            </div>
            """
        
        return f"""
        <div class="card">
            <h3>🛡️ Error Recovery</h3>
            <div class="metric">
                <span class="metric-label">Total Operations</span>
                <span class="metric-value">{recovery_data.get('recovery_stats', {}).get('total_operations', 0)}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Successful</span>
                <span class="metric-value">{recovery_data.get('recovery_stats', {}).get('successful_operations', 0)}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Failed</span>
                <span class="metric-value">{recovery_data.get('recovery_stats', {}).get('failed_operations', 0)}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Circuit Breaker Trips</span>
                <span class="metric-value">{recovery_data.get('recovery_stats', {}).get('circuit_breaker_trips', 0)}</span>
            </div>
        </div>
        """
    
    def _generate_alerts_section(self) -> str:
        """Generate alerts section HTML."""
        alerts = self.dashboard_data.get('alerts', [])
        
        if not alerts:
            return '<p>No active alerts</p>'
        
        alerts_html = []
        for alert in alerts[-10:]:  # Show last 10 alerts
            severity_class = f"alert-{alert.get('severity', 'warning')}"
            alerts_html.append(f"""
                <div class="alert {severity_class}">
                    <strong>{alert.get('type', 'Unknown').replace('_', ' ').title()}</strong>
                    <br>{alert.get('message', 'No message')}
                    <br><small>Component: {alert.get('component', 'System')} | Time: {alert.get('timestamp', 'Unknown')}</small>
                </div>
            """)
        
        return ''.join(alerts_html)
    
    async def start_dashboard(self, open_browser: bool = True):
        """
        Start the monitoring dashboard.
        
        Args:
            open_browser: Whether to open the dashboard in a browser
        """
        try:
            # Update initial data
            await self.update_dashboard_data()
            
            # Generate HTML
            html_content = self.generate_html_dashboard()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_file = f.name
            
            # Open in browser
            if open_browser:
                webbrowser.open(f'file://{temp_file}')
                logger.info(f"Dashboard opened in browser: {temp_file}")
            else:
                logger.info(f"Dashboard saved to: {temp_file}")
            
            # Start auto-update loop
            while True:
                await asyncio.sleep(self.config.auto_refresh)
                await self.update_dashboard_data()
                
                # Regenerate and save HTML
                html_content = self.generate_html_dashboard()
                with open(temp_file, 'w') as f:
                    f.write(html_content)
                
                logger.debug("Dashboard updated")
                
        except KeyboardInterrupt:
            logger.info("Dashboard stopped by user")
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def save_dashboard_data(self, filepath: str):
        """
        Save dashboard data to file.
        
        Args:
            filepath: Path to save data file
        """
        data = {
            'dashboard_data': self.dashboard_data,
            'alert_history': self.alert_history,
            'metric_history': self.metric_history,
            'config': {
                'port': self.config.port,
                'host': self.config.host,
                'auto_refresh': self.config.auto_refresh,
                'max_history': self.config.max_history,
                'enable_alerts': self.config.enable_alerts
            }
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Dashboard data saved to {filepath}")
    
    def load_dashboard_data(self, filepath: str):
        """
        Load dashboard data from file.
        
        Args:
            filepath: Path to data file
        """
        if not os.path.exists(filepath):
            logger.warning(f"Dashboard data file not found: {filepath}")
            return
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.dashboard_data = data.get('dashboard_data', {})
            self.alert_history = data.get('alert_history', [])
            self.metric_history = data.get('metric_history', [])
            
            # Update config
            config_data = data.get('config', {})
            self.config.port = config_data.get('port', self.config.port)
            self.config.host = config_data.get('host', self.config.host)
            self.config.auto_refresh = config_data.get('auto_refresh', self.config.auto_refresh)
            self.config.max_history = config_data.get('max_history', self.config.max_history)
            self.config.enable_alerts = config_data.get('enable_alerts', self.config.enable_alerts)
            
            logger.info(f"Dashboard data loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load dashboard data: {e}")


# Global dashboard instance
monitoring_dashboard = MonitoringDashboard()
