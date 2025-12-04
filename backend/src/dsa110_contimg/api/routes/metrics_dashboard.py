"""
Prometheus Metrics Dashboard API routes.

Provides dashboard summaries, metric queries, and history data
for the frontend metrics panels.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


# ============================================================================
# Pydantic Models
# ============================================================================


class MetricDataPoint(BaseModel):
    """Single data point in a time series."""

    timestamp: int  # Unix timestamp in seconds
    value: float


class MetricSeries(BaseModel):
    """A time series of metric values."""

    metric: str
    labels: Dict[str, str] = Field(default_factory=dict)
    values: List[MetricDataPoint] = Field(default_factory=list)


class PrometheusQueryResult(BaseModel):
    """Result from a Prometheus query."""

    query: str
    resultType: str  # vector, matrix, scalar, string
    data: List[MetricSeries] = Field(default_factory=list)


class SystemMetric(BaseModel):
    """A system metric with current value and history."""

    id: str
    name: str
    description: str
    unit: str
    current: float
    trend: str  # up, down, stable
    trendPercent: float
    status: str  # healthy, warning, critical
    history: List[MetricDataPoint] = Field(default_factory=list)


class ResourceMetrics(BaseModel):
    """System resource metrics."""

    cpu_percent: float
    memory_percent: float
    disk_io_mbps: float
    network_io_mbps: float


class PipelineMetrics(BaseModel):
    """Pipeline processing metrics."""

    jobs_per_hour: float
    avg_job_duration_sec: float
    success_rate_percent: float
    queue_depth: int
    active_workers: int
    total_workers: int


class MetricsDashboard(BaseModel):
    """Complete metrics dashboard data."""

    resources: ResourceMetrics
    pipeline: PipelineMetrics
    metrics: List[SystemMetric] = Field(default_factory=list)
    updated_at: str


# ============================================================================
# Helper Functions
# ============================================================================


def get_prometheus_url() -> Optional[str]:
    """Get Prometheus URL from environment."""
    return os.environ.get("PROMETHEUS_URL", "http://localhost:9090")


def query_prometheus(query: str) -> Optional[Dict[str, Any]]:
    """
    Execute a Prometheus query.

    Returns None if Prometheus is not available.
    """
    import urllib.request
    import urllib.parse
    import json

    prometheus_url = get_prometheus_url()
    if not prometheus_url:
        return None

    try:
        url = f"{prometheus_url}/api/v1/query?query={urllib.parse.quote(query)}"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "success":
                return data.get("data", {})
    except Exception as e:
        logger.debug(f"Prometheus query failed: {e}")
        return None

    return None


def query_prometheus_range(
    query: str, start: int, end: int, step: int
) -> Optional[Dict[str, Any]]:
    """
    Execute a Prometheus range query.

    Returns None if Prometheus is not available.
    """
    import urllib.request
    import urllib.parse
    import json

    prometheus_url = get_prometheus_url()
    if not prometheus_url:
        return None

    try:
        params = urllib.parse.urlencode({
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        })
        url = f"{prometheus_url}/api/v1/query_range?{params}"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "success":
                return data.get("data", {})
    except Exception as e:
        logger.debug(f"Prometheus range query failed: {e}")
        return None

    return None


def get_system_metrics() -> Dict[str, float]:
    """
    Get current system metrics using psutil or fallback values.
    """
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory().percent
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        # Calculate I/O rates (simplified - would need time delta in production)
        disk_mbps = (disk_io.read_bytes + disk_io.write_bytes) / (1024 * 1024) if disk_io else 0
        net_mbps = (net_io.bytes_recv + net_io.bytes_sent) / (1024 * 1024) if net_io else 0

        return {
            "cpu_percent": cpu,
            "memory_percent": memory,
            "disk_io_mbps": min(disk_mbps, 1000),  # Cap at reasonable value
            "network_io_mbps": min(net_mbps, 1000),
        }
    except ImportError:
        # psutil not available, return placeholder values
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_io_mbps": 0.0,
            "network_io_mbps": 0.0,
        }


def get_pipeline_metrics() -> Dict[str, Any]:
    """
    Get pipeline metrics from database or queue system.
    """
    import sqlite3
    from pathlib import Path

    db_path = Path(
        os.environ.get("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
    )

    metrics = {
        "jobs_per_hour": 0.0,
        "avg_job_duration_sec": 0.0,
        "success_rate_percent": 100.0,
        "queue_depth": 0,
        "active_workers": 0,
        "total_workers": 0,
    }

    if not db_path.exists():
        return metrics

    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row

        # Check if jobs table exists
        table_check = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
        ).fetchone()

        if table_check:
            # Jobs per hour (last hour)
            hour_ago = int(time.time()) - 3600
            result = conn.execute(
                """
                SELECT COUNT(*) as count FROM jobs
                WHERE completed_at > datetime(?, 'unixepoch')
                """,
                (hour_ago,),
            ).fetchone()
            if result:
                metrics["jobs_per_hour"] = float(result["count"])

            # Average job duration (last 24 hours)
            day_ago = int(time.time()) - 86400
            result = conn.execute(
                """
                SELECT AVG(
                    CAST((julianday(completed_at) - julianday(started_at)) * 86400 AS REAL)
                ) as avg_duration
                FROM jobs
                WHERE completed_at > datetime(?, 'unixepoch')
                  AND started_at IS NOT NULL
                  AND completed_at IS NOT NULL
                """,
                (day_ago,),
            ).fetchone()
            if result and result["avg_duration"]:
                metrics["avg_job_duration_sec"] = float(result["avg_duration"])

            # Success rate (last 24 hours)
            result = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success
                FROM jobs
                WHERE completed_at > datetime(?, 'unixepoch')
                """,
                (day_ago,),
            ).fetchone()
            if result and result["total"] > 0:
                metrics["success_rate_percent"] = (
                    float(result["success"]) / float(result["total"]) * 100
                )

        conn.close()
    except Exception as e:
        logger.debug(f"Failed to get pipeline metrics: {e}")

    # Try to get worker info from ABSURD/Redis
    try:
        import redis as redis_module

        redis_url = os.environ.get("DSA110_REDIS_URL", "redis://localhost:6379")
        r = redis_module.from_url(redis_url, socket_timeout=2)

        # Get queue depth
        queue_len = r.llen("absurd:queue:default")
        metrics["queue_depth"] = queue_len or 0

        # Get worker count
        workers = r.hgetall("absurd:workers")
        if workers:
            metrics["total_workers"] = len(workers)
            # Count active workers (heartbeat within last 60 seconds)
            now = time.time()
            active = 0
            for worker_data in workers.values():
                try:
                    import json
                    data = json.loads(worker_data)
                    if now - data.get("last_heartbeat", 0) < 60:
                        active += 1
                except Exception:
                    pass
            metrics["active_workers"] = active
    except Exception as e:
        logger.debug(f"Failed to get worker metrics: {e}")

    return metrics


def calculate_trend(current: float, history: List[MetricDataPoint]) -> tuple[str, float]:
    """Calculate trend direction and percentage from history."""
    if not history or len(history) < 2:
        return "stable", 0.0

    # Compare current to average of first half of history
    first_half = history[: len(history) // 2]
    if not first_half:
        return "stable", 0.0

    avg_old = sum(p.value for p in first_half) / len(first_half)
    if avg_old == 0:
        return "stable", 0.0

    change_percent = ((current - avg_old) / avg_old) * 100

    if change_percent > 5:
        return "up", change_percent
    elif change_percent < -5:
        return "down", abs(change_percent)
    else:
        return "stable", abs(change_percent)


def get_metric_status(value: float, warning_threshold: float, critical_threshold: float) -> str:
    """Determine metric status based on thresholds."""
    if value >= critical_threshold:
        return "critical"
    elif value >= warning_threshold:
        return "warning"
    return "healthy"


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/dashboard", response_model=MetricsDashboard)
async def get_metrics_dashboard() -> MetricsDashboard:
    """
    Get the complete metrics dashboard summary.

    Returns current system metrics, pipeline metrics, and key indicators
    with their status and trends.
    """
    now = datetime.utcnow().isoformat() + "Z"

    # Get system metrics
    sys_metrics = get_system_metrics()
    resources = ResourceMetrics(
        cpu_percent=sys_metrics["cpu_percent"],
        memory_percent=sys_metrics["memory_percent"],
        disk_io_mbps=sys_metrics["disk_io_mbps"],
        network_io_mbps=sys_metrics["network_io_mbps"],
    )

    # Get pipeline metrics
    pipe_metrics = get_pipeline_metrics()
    pipeline = PipelineMetrics(
        jobs_per_hour=pipe_metrics["jobs_per_hour"],
        avg_job_duration_sec=pipe_metrics["avg_job_duration_sec"],
        success_rate_percent=pipe_metrics["success_rate_percent"],
        queue_depth=pipe_metrics["queue_depth"],
        active_workers=pipe_metrics["active_workers"],
        total_workers=pipe_metrics["total_workers"],
    )

    # Build detailed metrics list
    timestamp = int(time.time())
    metrics = [
        SystemMetric(
            id="cpu",
            name="CPU Usage",
            description="System CPU utilization",
            unit="%",
            current=sys_metrics["cpu_percent"],
            trend="stable",
            trendPercent=0.0,
            status=get_metric_status(sys_metrics["cpu_percent"], 70, 90),
            history=[MetricDataPoint(timestamp=timestamp, value=sys_metrics["cpu_percent"])],
        ),
        SystemMetric(
            id="memory",
            name="Memory Usage",
            description="System memory utilization",
            unit="%",
            current=sys_metrics["memory_percent"],
            trend="stable",
            trendPercent=0.0,
            status=get_metric_status(sys_metrics["memory_percent"], 80, 95),
            history=[MetricDataPoint(timestamp=timestamp, value=sys_metrics["memory_percent"])],
        ),
        SystemMetric(
            id="jobs_per_hour",
            name="Jobs/Hour",
            description="Pipeline jobs completed per hour",
            unit="jobs",
            current=pipe_metrics["jobs_per_hour"],
            trend="stable",
            trendPercent=0.0,
            status="healthy",
            history=[MetricDataPoint(timestamp=timestamp, value=pipe_metrics["jobs_per_hour"])],
        ),
        SystemMetric(
            id="success_rate",
            name="Success Rate",
            description="Pipeline job success rate",
            unit="%",
            current=pipe_metrics["success_rate_percent"],
            trend="stable",
            trendPercent=0.0,
            status=get_metric_status(100 - pipe_metrics["success_rate_percent"], 5, 20),
            history=[MetricDataPoint(timestamp=timestamp, value=pipe_metrics["success_rate_percent"])],
        ),
        SystemMetric(
            id="queue_depth",
            name="Queue Depth",
            description="Number of pending jobs in queue",
            unit="jobs",
            current=float(pipe_metrics["queue_depth"]),
            trend="stable",
            trendPercent=0.0,
            status=get_metric_status(pipe_metrics["queue_depth"], 100, 500),
            history=[MetricDataPoint(timestamp=timestamp, value=float(pipe_metrics["queue_depth"]))],
        ),
    ]

    return MetricsDashboard(
        resources=resources,
        pipeline=pipeline,
        metrics=metrics,
        updated_at=now,
    )


@router.get("/query", response_model=PrometheusQueryResult)
async def query_metrics(
    query: str = Query(..., description="Prometheus query expression"),
    start: Optional[int] = Query(None, description="Start timestamp (unix)"),
    end: Optional[int] = Query(None, description="End timestamp (unix)"),
    step: Optional[int] = Query(None, description="Step in seconds"),
) -> PrometheusQueryResult:
    """
    Execute a Prometheus query.

    If start/end/step are provided, executes a range query.
    Otherwise executes an instant query.
    """
    if start and end:
        # Range query
        step = step or 60  # Default 1 minute step
        result = query_prometheus_range(query, start, end, step)

        if result:
            series = []
            for item in result.get("result", []):
                metric_name = item.get("metric", {}).get("__name__", "unknown")
                labels = {k: v for k, v in item.get("metric", {}).items() if k != "__name__"}
                values = [
                    MetricDataPoint(timestamp=int(v[0]), value=float(v[1]))
                    for v in item.get("values", [])
                ]
                series.append(MetricSeries(metric=metric_name, labels=labels, values=values))

            return PrometheusQueryResult(
                query=query,
                resultType=result.get("resultType", "matrix"),
                data=series,
            )
    else:
        # Instant query
        result = query_prometheus(query)

        if result:
            series = []
            for item in result.get("result", []):
                metric_name = item.get("metric", {}).get("__name__", "unknown")
                labels = {k: v for k, v in item.get("metric", {}).items() if k != "__name__"}
                value = item.get("value", [0, "0"])
                values = [MetricDataPoint(timestamp=int(value[0]), value=float(value[1]))]
                series.append(MetricSeries(metric=metric_name, labels=labels, values=values))

            return PrometheusQueryResult(
                query=query,
                resultType=result.get("resultType", "vector"),
                data=series,
            )

    # No Prometheus available, return empty result
    return PrometheusQueryResult(query=query, resultType="vector", data=[])


@router.get("/{metric_id}/history", response_model=SystemMetric)
async def get_metric_history(
    metric_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of history"),
) -> SystemMetric:
    """
    Get historical data for a specific metric.
    """
    # Define metric configurations
    metric_configs = {
        "cpu": {
            "name": "CPU Usage",
            "description": "System CPU utilization",
            "unit": "%",
            "prom_query": "avg(rate(node_cpu_seconds_total{mode!='idle'}[5m])) * 100",
            "warning": 70,
            "critical": 90,
        },
        "memory": {
            "name": "Memory Usage",
            "description": "System memory utilization",
            "unit": "%",
            "prom_query": "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100",
            "warning": 80,
            "critical": 95,
        },
        "disk": {
            "name": "Disk Usage",
            "description": "Primary disk utilization",
            "unit": "%",
            "prom_query": "(1 - node_filesystem_avail_bytes{mountpoint='/'} / node_filesystem_size_bytes{mountpoint='/'}) * 100",
            "warning": 80,
            "critical": 90,
        },
        "jobs_per_hour": {
            "name": "Jobs/Hour",
            "description": "Pipeline jobs completed per hour",
            "unit": "jobs",
            "prom_query": "sum(rate(pipeline_jobs_completed_total[1h])) * 3600",
            "warning": 0,
            "critical": 0,
        },
        "success_rate": {
            "name": "Success Rate",
            "description": "Pipeline job success rate",
            "unit": "%",
            "prom_query": "sum(rate(pipeline_jobs_completed_total{status='success'}[1h])) / sum(rate(pipeline_jobs_completed_total[1h])) * 100",
            "warning": 95,
            "critical": 80,
        },
        "queue_depth": {
            "name": "Queue Depth",
            "description": "Number of pending jobs in queue",
            "unit": "jobs",
            "prom_query": "absurd_queue_depth",
            "warning": 100,
            "critical": 500,
        },
    }

    config = metric_configs.get(metric_id)
    if not config:
        # Return a generic metric
        config = {
            "name": metric_id,
            "description": f"Metric: {metric_id}",
            "unit": "",
            "prom_query": metric_id,
            "warning": 70,
            "critical": 90,
        }

    # Try to get historical data from Prometheus
    now = int(time.time())
    start = now - (hours * 3600)
    step = max(60, hours * 60 // 100)  # Aim for ~100 data points

    history: List[MetricDataPoint] = []
    current = 0.0

    result = query_prometheus_range(config["prom_query"], start, now, step)
    if result and result.get("result"):
        for item in result.get("result", []):
            for ts, val in item.get("values", []):
                history.append(MetricDataPoint(timestamp=int(ts), value=float(val)))
        if history:
            current = history[-1].value

    # If no Prometheus data, use current system metrics for some metrics
    if not history:
        sys_metrics = get_system_metrics()
        pipe_metrics = get_pipeline_metrics()

        metric_values = {
            "cpu": sys_metrics.get("cpu_percent", 0),
            "memory": sys_metrics.get("memory_percent", 0),
            "jobs_per_hour": pipe_metrics.get("jobs_per_hour", 0),
            "success_rate": pipe_metrics.get("success_rate_percent", 100),
            "queue_depth": pipe_metrics.get("queue_depth", 0),
        }
        current = metric_values.get(metric_id, 0)
        history = [MetricDataPoint(timestamp=now, value=current)]

    trend, trend_percent = calculate_trend(current, history)
    status = get_metric_status(current, config["warning"], config["critical"])

    return SystemMetric(
        id=metric_id,
        name=config["name"],
        description=config["description"],
        unit=config["unit"],
        current=current,
        trend=trend,
        trendPercent=trend_percent,
        status=status,
        history=history,
    )
