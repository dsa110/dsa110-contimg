"""
GPU Monitoring Module.

Provides real-time GPU monitoring, metrics collection, and alerting
for the DSA-110 continuum imaging pipeline.

Features:
- Real-time GPU utilization, memory, temperature monitoring
- Historical metrics storage for trend analysis
- Alerting on high utilization/temperature
- CuPy and pynvml support
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


class GPUHealthStatus(str, Enum):
    """GPU health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNAVAILABLE = "unavailable"


@dataclass
class GPUMetricSample:
    """Single sample of GPU metrics."""

    timestamp: float
    gpu_id: int
    memory_used_gb: float
    memory_total_gb: float
    memory_utilization_pct: float
    gpu_utilization_pct: float
    temperature_c: Optional[float] = None
    power_draw_w: Optional[float] = None
    power_limit_w: Optional[float] = None


@dataclass
class GPUAlertThresholds:
    """Thresholds for GPU alerts."""

    memory_warning_pct: float = 80.0
    memory_critical_pct: float = 95.0
    utilization_warning_pct: float = 90.0
    utilization_critical_pct: float = 98.0
    temperature_warning_c: float = 75.0
    temperature_critical_c: float = 85.0


@dataclass
class GPUAlert:
    """GPU alert event."""

    timestamp: float
    gpu_id: int
    alert_type: str  # memory, utilization, temperature
    severity: str  # warning, critical
    message: str
    value: float
    threshold: float


@dataclass
class GPUDevice:
    """GPU device information and state."""

    id: int
    name: str
    uuid: Optional[str] = None
    compute_capability: Optional[str] = None
    driver_version: Optional[str] = None
    cuda_version: Optional[str] = None
    memory_total_gb: float = 0.0
    current_metrics: Optional[GPUMetricSample] = None
    health_status: GPUHealthStatus = GPUHealthStatus.UNAVAILABLE
    # Historical metrics - rolling window
    history: Deque[GPUMetricSample] = field(
        default_factory=lambda: deque(maxlen=3600)  # 1 hour at 1 sample/sec
    )


class GPUMonitor:
    """
    GPU Monitor for real-time metrics collection and alerting.

    Supports both pynvml (preferred) and CuPy for GPU monitoring.
    """

    def __init__(
        self,
        thresholds: Optional[GPUAlertThresholds] = None,
        history_size: int = 3600,
        alert_callback: Optional[Callable[[GPUAlert], None]] = None,
    ):
        self.thresholds = thresholds or GPUAlertThresholds()
        self.history_size = history_size
        self.alert_callback = alert_callback
        self.devices: Dict[int, GPUDevice] = {}
        self.alerts: Deque[GPUAlert] = deque(maxlen=1000)
        self._initialized = False
        self._use_pynvml = False
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    def initialize(self) -> bool:
        """Initialize GPU monitoring. Returns True if GPUs are available."""
        if self._initialized:
            return bool(self.devices)

        # Try pynvml first (more detailed metrics)
        try:
            import pynvml

            pynvml.nvmlInit()
            self._use_pynvml = True

            n_gpus = pynvml.nvmlDeviceGetCount()
            driver_version = pynvml.nvmlSystemGetDriverVersion()
            if isinstance(driver_version, bytes):
                driver_version = driver_version.decode()

            for i in range(n_gpus):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode()

                uuid = pynvml.nvmlDeviceGetUUID(handle)
                if isinstance(uuid, bytes):
                    uuid = uuid.decode()

                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)

                # Get compute capability
                try:
                    major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
                    cc = f"{major}.{minor}"
                except pynvml.NVMLError:
                    cc = None

                self.devices[i] = GPUDevice(
                    id=i,
                    name=name,
                    uuid=uuid,
                    compute_capability=cc,
                    driver_version=driver_version,
                    memory_total_gb=round(mem.total / 1e9, 2),
                    history=deque(maxlen=self.history_size),
                )

            pynvml.nvmlShutdown()
            self._initialized = True
            logger.info(f"GPU monitor initialized with pynvml: {n_gpus} GPUs found")
            return True

        except (ImportError, Exception) as exc:
            logger.debug(f"pynvml not available: {exc}")

        # Fall back to CuPy
        try:
            import cupy as cp

            n_gpus = cp.cuda.runtime.getDeviceCount()

            for i in range(n_gpus):
                props = cp.cuda.runtime.getDeviceProperties(i)
                name = props["name"]
                if isinstance(name, bytes):
                    name = name.decode()

                with cp.cuda.Device(i):
                    mem_info = cp.cuda.Device(i).mem_info

                cc = f"{props['major']}.{props['minor']}"

                self.devices[i] = GPUDevice(
                    id=i,
                    name=name,
                    compute_capability=cc,
                    memory_total_gb=round(mem_info[1] / 1e9, 2),
                    history=deque(maxlen=self.history_size),
                )

            self._initialized = True
            logger.info(f"GPU monitor initialized with CuPy: {n_gpus} GPUs found")
            return True

        except (ImportError, Exception) as exc:
            logger.warning(f"No GPU monitoring available: {exc}")
            self._initialized = True
            return False

    def _sample_metrics_pynvml(self) -> List[GPUMetricSample]:
        """Sample GPU metrics using pynvml."""
        import pynvml

        pynvml.nvmlInit()
        samples = []
        timestamp = time.time()

        try:
            for gpu_id in self.devices:
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)

                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except pynvml.NVMLError:
                    temp = None

                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # mW to W
                except pynvml.NVMLError:
                    power = None

                try:
                    power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000
                except pynvml.NVMLError:
                    power_limit = None

                sample = GPUMetricSample(
                    timestamp=timestamp,
                    gpu_id=gpu_id,
                    memory_used_gb=round(mem.used / 1e9, 3),
                    memory_total_gb=round(mem.total / 1e9, 3),
                    memory_utilization_pct=round(100 * mem.used / mem.total, 1),
                    gpu_utilization_pct=float(util.gpu),
                    temperature_c=temp,
                    power_draw_w=round(power, 1) if power else None,
                    power_limit_w=round(power_limit, 1) if power_limit else None,
                )
                samples.append(sample)

        finally:
            pynvml.nvmlShutdown()

        return samples

    def _sample_metrics_cupy(self) -> List[GPUMetricSample]:
        """Sample GPU metrics using CuPy (limited metrics)."""
        import cupy as cp

        samples = []
        timestamp = time.time()

        for gpu_id in self.devices:
            with cp.cuda.Device(gpu_id):
                mem_info = cp.cuda.Device(gpu_id).mem_info
                mem_free, mem_total = mem_info
                mem_used = mem_total - mem_free

                sample = GPUMetricSample(
                    timestamp=timestamp,
                    gpu_id=gpu_id,
                    memory_used_gb=round(mem_used / 1e9, 3),
                    memory_total_gb=round(mem_total / 1e9, 3),
                    memory_utilization_pct=round(100 * mem_used / mem_total, 1),
                    gpu_utilization_pct=0.0,  # Not available via CuPy
                )
                samples.append(sample)

        return samples

    def sample_metrics(self) -> List[GPUMetricSample]:
        """Sample current GPU metrics."""
        if not self._initialized:
            self.initialize()

        if not self.devices:
            return []

        try:
            if self._use_pynvml:
                return self._sample_metrics_pynvml()
            else:
                return self._sample_metrics_cupy()
        except Exception as exc:
            logger.warning(f"Failed to sample GPU metrics: {exc}")
            return []

    def _check_alerts(self, sample: GPUMetricSample) -> List[GPUAlert]:
        """Check sample against thresholds and generate alerts."""
        alerts = []
        t = self.thresholds

        # Memory alerts
        if sample.memory_utilization_pct >= t.memory_critical_pct:
            alerts.append(
                GPUAlert(
                    timestamp=sample.timestamp,
                    gpu_id=sample.gpu_id,
                    alert_type="memory",
                    severity="critical",
                    message=f"GPU {sample.gpu_id} memory critical: {sample.memory_utilization_pct:.1f}%",
                    value=sample.memory_utilization_pct,
                    threshold=t.memory_critical_pct,
                )
            )
        elif sample.memory_utilization_pct >= t.memory_warning_pct:
            alerts.append(
                GPUAlert(
                    timestamp=sample.timestamp,
                    gpu_id=sample.gpu_id,
                    alert_type="memory",
                    severity="warning",
                    message=f"GPU {sample.gpu_id} memory warning: {sample.memory_utilization_pct:.1f}%",
                    value=sample.memory_utilization_pct,
                    threshold=t.memory_warning_pct,
                )
            )

        # Utilization alerts
        if sample.gpu_utilization_pct >= t.utilization_critical_pct:
            alerts.append(
                GPUAlert(
                    timestamp=sample.timestamp,
                    gpu_id=sample.gpu_id,
                    alert_type="utilization",
                    severity="critical",
                    message=f"GPU {sample.gpu_id} utilization critical: {sample.gpu_utilization_pct:.1f}%",
                    value=sample.gpu_utilization_pct,
                    threshold=t.utilization_critical_pct,
                )
            )
        elif sample.gpu_utilization_pct >= t.utilization_warning_pct:
            alerts.append(
                GPUAlert(
                    timestamp=sample.timestamp,
                    gpu_id=sample.gpu_id,
                    alert_type="utilization",
                    severity="warning",
                    message=f"GPU {sample.gpu_id} utilization warning: {sample.gpu_utilization_pct:.1f}%",
                    value=sample.gpu_utilization_pct,
                    threshold=t.utilization_warning_pct,
                )
            )

        # Temperature alerts
        if sample.temperature_c is not None:
            if sample.temperature_c >= t.temperature_critical_c:
                alerts.append(
                    GPUAlert(
                        timestamp=sample.timestamp,
                        gpu_id=sample.gpu_id,
                        alert_type="temperature",
                        severity="critical",
                        message=f"GPU {sample.gpu_id} temperature critical: {sample.temperature_c}°C",
                        value=sample.temperature_c,
                        threshold=t.temperature_critical_c,
                    )
                )
            elif sample.temperature_c >= t.temperature_warning_c:
                alerts.append(
                    GPUAlert(
                        timestamp=sample.timestamp,
                        gpu_id=sample.gpu_id,
                        alert_type="temperature",
                        severity="warning",
                        message=f"GPU {sample.gpu_id} temperature warning: {sample.temperature_c}°C",
                        value=sample.temperature_c,
                        threshold=t.temperature_warning_c,
                    )
                )

        return alerts

    def _determine_health_status(self, sample: GPUMetricSample) -> GPUHealthStatus:
        """Determine overall health status from sample."""
        t = self.thresholds

        # Check for critical conditions
        if sample.memory_utilization_pct >= t.memory_critical_pct:
            return GPUHealthStatus.CRITICAL
        if sample.gpu_utilization_pct >= t.utilization_critical_pct:
            return GPUHealthStatus.CRITICAL
        if sample.temperature_c and sample.temperature_c >= t.temperature_critical_c:
            return GPUHealthStatus.CRITICAL

        # Check for warning conditions
        if sample.memory_utilization_pct >= t.memory_warning_pct:
            return GPUHealthStatus.WARNING
        if sample.gpu_utilization_pct >= t.utilization_warning_pct:
            return GPUHealthStatus.WARNING
        if sample.temperature_c and sample.temperature_c >= t.temperature_warning_c:
            return GPUHealthStatus.WARNING

        return GPUHealthStatus.HEALTHY

    def update(self) -> Dict[str, Any]:
        """
        Update GPU metrics, check alerts, and return current state.

        Returns dict with:
        - samples: Current metric samples
        - alerts: Any new alerts generated
        - devices: Updated device states
        """
        samples = self.sample_metrics()
        new_alerts = []

        for sample in samples:
            device = self.devices.get(sample.gpu_id)
            if device:
                device.current_metrics = sample
                device.history.append(sample)
                device.health_status = self._determine_health_status(sample)

                # Check for alerts
                alerts = self._check_alerts(sample)
                for alert in alerts:
                    self.alerts.append(alert)
                    new_alerts.append(alert)
                    if self.alert_callback:
                        try:
                            self.alert_callback(alert)
                        except Exception as exc:
                            logger.warning(f"Alert callback failed: {exc}")

        return {
            "samples": samples,
            "alerts": new_alerts,
            "devices": self.devices,
        }

    async def start_monitoring(self, interval: float = 1.0):
        """Start background monitoring task."""
        if self._monitoring:
            return

        self._monitoring = True

        async def monitor_loop():
            while self._monitoring:
                try:
                    self.update()
                except Exception as exc:
                    logger.warning(f"Monitor update failed: {exc}")
                await asyncio.sleep(interval)

        self._monitor_task = asyncio.create_task(monitor_loop())
        logger.info(f"GPU monitoring started with {interval}s interval")

    async def stop_monitoring(self):
        """Stop background monitoring task."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        logger.info("GPU monitoring stopped")

    def get_device_summary(self, gpu_id: int) -> Optional[Dict[str, Any]]:
        """Get summary for a specific GPU."""
        device = self.devices.get(gpu_id)
        if not device:
            return None

        metrics = device.current_metrics
        return {
            "id": device.id,
            "name": device.name,
            "uuid": device.uuid,
            "compute_capability": device.compute_capability,
            "driver_version": device.driver_version,
            "memory_total_gb": device.memory_total_gb,
            "health_status": device.health_status.value,
            "current_metrics": {
                "timestamp": metrics.timestamp if metrics else None,
                "memory_used_gb": metrics.memory_used_gb if metrics else None,
                "memory_utilization_pct": (metrics.memory_utilization_pct if metrics else None),
                "gpu_utilization_pct": (metrics.gpu_utilization_pct if metrics else None),
                "temperature_c": metrics.temperature_c if metrics else None,
                "power_draw_w": metrics.power_draw_w if metrics else None,
            }
            if metrics
            else None,
            "history_samples": len(device.history),
        }

    def get_all_summaries(self) -> Dict[str, Any]:
        """Get summaries for all GPUs."""
        if not self._initialized:
            self.initialize()

        return {
            "available": bool(self.devices),
            "gpu_count": len(self.devices),
            "monitoring_backend": "pynvml" if self._use_pynvml else "cupy",
            "devices": [self.get_device_summary(gpu_id) for gpu_id in sorted(self.devices)],
            "thresholds": {
                "memory_warning_pct": self.thresholds.memory_warning_pct,
                "memory_critical_pct": self.thresholds.memory_critical_pct,
                "utilization_warning_pct": self.thresholds.utilization_warning_pct,
                "utilization_critical_pct": self.thresholds.utilization_critical_pct,
                "temperature_warning_c": self.thresholds.temperature_warning_c,
                "temperature_critical_c": self.thresholds.temperature_critical_c,
            },
        }

    def get_recent_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        alerts = list(self.alerts)[-limit:]
        return [
            {
                "timestamp": alert.timestamp,
                "timestamp_iso": datetime.fromtimestamp(alert.timestamp).isoformat(),
                "gpu_id": alert.gpu_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "value": alert.value,
                "threshold": alert.threshold,
            }
            for alert in reversed(alerts)
        ]

    def get_history(self, gpu_id: int, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get historical metrics for a GPU."""
        device = self.devices.get(gpu_id)
        if not device:
            return []

        cutoff = time.time() - (minutes * 60)
        history = [
            {
                "timestamp": sample.timestamp,
                "timestamp_iso": datetime.fromtimestamp(sample.timestamp).isoformat(),
                "memory_used_gb": sample.memory_used_gb,
                "memory_utilization_pct": sample.memory_utilization_pct,
                "gpu_utilization_pct": sample.gpu_utilization_pct,
                "temperature_c": sample.temperature_c,
                "power_draw_w": sample.power_draw_w,
            }
            for sample in device.history
            if sample.timestamp >= cutoff
        ]
        return history


# Global monitor instance
_gpu_monitor: Optional[GPUMonitor] = None


def get_gpu_monitor() -> GPUMonitor:
    """Get or create the global GPU monitor instance."""
    global _gpu_monitor
    if _gpu_monitor is None:
        _gpu_monitor = GPUMonitor()
        _gpu_monitor.initialize()
    return _gpu_monitor


def reset_gpu_monitor():
    """Reset the global GPU monitor (for testing)."""
    global _gpu_monitor
    if _gpu_monitor:
        asyncio.create_task(_gpu_monitor.stop_monitoring())
    _gpu_monitor = None
