"""
Event-driven handlers for pipeline orchestration.

This module provides handlers that react to events and trigger pipelines.
It enables reactive workflows like:
- ESE detection → Deep mosaic pipeline
- Data ingestion → Streaming calibration
- QA failure → Alert notification

Usage:
    from dsa110_contimg.pipeline.handlers import setup_event_handlers

    # During application startup
    config = AppConfig(...)
    executor = PipelineExecutor(db_path=config.database_path)
    setup_event_handlers(executor, config)

    # Now events will automatically trigger pipelines
    emitter = EventEmitter.get_instance()
    emitter.emit(EventType.ESE_DETECTED, {...})  # Triggers deep mosaic
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .events import Event, EventEmitter, EventType

logger = logging.getLogger(__name__)


@dataclass
class HandlerConfig:
    """Configuration for event handlers.

    Attributes:
        database_path: Path to the unified database
        mosaic_dir: Directory for output mosaics
        caltable_dir: Directory for calibration tables
        enable_ese_mosaic: Enable automatic mosaic on ESE detection
        enable_streaming_cal: Enable automatic calibration on data ingestion
        ese_deep_lookback_hours: Hours to look back for deep mosaic
    """

    database_path: Path
    mosaic_dir: Path
    caltable_dir: Path
    enable_ese_mosaic: bool = True
    enable_streaming_cal: bool = True
    ese_deep_lookback_hours: int = 168  # 7 days


def setup_event_handlers(
    executor: Any,  # PipelineExecutor
    config: HandlerConfig,
) -> list[Callable[[], None]]:
    """Set up all event handlers for pipeline orchestration.

    Call this once during application startup to wire event handlers
    to pipeline triggers.

    Args:
        executor: PipelineExecutor instance for triggering pipelines
        config: Handler configuration

    Returns:
        List of unsubscribe functions (call to remove handlers)
    """
    emitter = EventEmitter.get_instance()
    unsubscribers = []

    # ESE Detection → Deep Mosaic Pipeline
    if config.enable_ese_mosaic:
        handler = ESEMosaicHandler(executor, config)
        unsub = emitter.subscribe_async(EventType.ESE_DETECTED, handler.on_ese_detected)
        unsubscribers.append(unsub)
        logger.info("Registered ESE detection → deep mosaic handler")

    # Data Ingestion → Streaming Calibration
    if config.enable_streaming_cal:
        handler = StreamingCalHandler(executor, config)
        unsub = emitter.subscribe_async(
            EventType.DATA_INGESTED, handler.on_data_ingested
        )
        unsubscribers.append(unsub)
        logger.info("Registered data ingestion → streaming calibration handler")

    # QA Failure → Alert Notification
    qa_handler = QAAlertHandler(config)
    unsub = emitter.subscribe(EventType.MOSAIC_QA_FAILED, qa_handler.on_qa_failed)
    unsubscribers.append(unsub)
    logger.info("Registered QA failure → alert handler")

    return unsubscribers


class ESEMosaicHandler:
    """Handler that triggers deep mosaic pipeline on ESE detection.

    When an Extreme Scattering Event (ESE) is detected, this handler
    triggers a targeted deep mosaic centered on the source location
    using a configurable lookback period of archival data.
    """

    def __init__(self, executor: Any, config: HandlerConfig):
        """Initialize handler.

        Args:
            executor: PipelineExecutor for triggering pipelines
            config: Handler configuration
        """
        self.executor = executor
        self.config = config

    async def on_ese_detected(self, event: Event) -> None:
        """Handle ESE detection event.

        Triggers a targeted deep mosaic pipeline centered on the
        detected source location.

        Args:
            event: ESE detection event with source coordinates
        """
        source_name = event.data.get("source_name", "unknown")
        ra = event.data.get("ra")
        dec = event.data.get("dec")
        snr = event.data.get("detection_snr", 0)

        logger.info(
            f"ESE detection received: {source_name} at RA={ra}, Dec={dec} (SNR={snr})"
        )

        if ra is None or dec is None:
            logger.warning(
                f"ESE detection missing coordinates, skipping mosaic trigger"
            )
            return

        try:
            # Import here to avoid circular imports
            from dsa110_contimg.mosaic.pipeline import (
                MosaicPipelineConfig,
                OnDemandMosaicPipeline,
            )

            # Configure deep mosaic
            now = datetime.now(timezone.utc)
            end_time = int(now.timestamp())
            start_time = end_time - (self.config.ese_deep_lookback_hours * 3600)

            mosaic_config = MosaicPipelineConfig(
                database_path=self.config.database_path,
                mosaic_dir=self.config.mosaic_dir,
            )

            # Create targeted deep mosaic pipeline
            mosaic_name = f"ese_{source_name}_{now.strftime('%Y%m%d_%H%M%S')}"
            pipeline = OnDemandMosaicPipeline(
                config=mosaic_config,
                name=mosaic_name,
                start_time=start_time,
                end_time=end_time,
                tier="deep",
                center_ra=ra,
                center_dec=dec,
            )

            # Execute pipeline
            execution_id = await self.executor.execute(pipeline)
            logger.info(
                f"Triggered deep mosaic for ESE {source_name}: {execution_id}"
            )

            # Emit pipeline started event
            emitter = EventEmitter.get_instance()
            emitter.emit(
                EventType.PIPELINE_STARTED,
                {
                    "pipeline_name": "on_demand_mosaic",
                    "execution_id": execution_id,
                    "trigger": "ese_detection",
                    "source_name": source_name,
                },
                source="ese_mosaic_handler",
                correlation_id=event.event_id,
            )

        except Exception as e:
            logger.exception(f"Failed to trigger deep mosaic for ESE {source_name}: {e}")


class StreamingCalHandler:
    """Handler that triggers streaming calibration on data ingestion.

    When new MS data is ingested and contains calibrator data, this
    handler triggers automatic calibration solving to produce fresh
    calibration tables.
    """

    def __init__(self, executor: Any, config: HandlerConfig):
        """Initialize handler.

        Args:
            executor: PipelineExecutor for triggering pipelines
            config: Handler configuration
        """
        self.executor = executor
        self.config = config

    async def on_data_ingested(self, event: Event) -> None:
        """Handle data ingestion event.

        If the ingested data contains calibrator data, triggers
        streaming calibration pipeline.

        Args:
            event: Data ingestion event
        """
        ms_path = event.data.get("ms_path")
        has_calibrator = event.data.get("has_calibrator", False)

        if not ms_path:
            logger.warning("Data ingestion event missing ms_path")
            return

        if not has_calibrator:
            logger.debug(f"No calibrator in {ms_path}, skipping calibration")
            return

        logger.info(f"Calibrator data detected in {ms_path}, triggering calibration")

        try:
            # Import here to avoid circular imports
            from dsa110_contimg.calibration.pipeline import (
                CalibrationPipelineConfig,
                StreamingCalibrationPipeline,
            )

            cal_config = CalibrationPipelineConfig(
                database_path=self.config.database_path,
                caltable_dir=self.config.caltable_dir,
            )

            # Create streaming calibration pipeline
            pipeline = StreamingCalibrationPipeline(
                config=cal_config,
                ms_path=ms_path,
            )

            # Execute pipeline
            execution_id = await self.executor.execute(pipeline)
            logger.info(
                f"Triggered streaming calibration for {ms_path}: {execution_id}"
            )

        except Exception as e:
            logger.exception(f"Failed to trigger streaming calibration for {ms_path}: {e}")


class QAAlertHandler:
    """Handler that sends alerts on QA failures.

    When mosaic or calibration QA fails, this handler sends
    alerts via configured notification channels.
    """

    def __init__(self, config: HandlerConfig):
        """Initialize handler.

        Args:
            config: Handler configuration
        """
        self.config = config

    def on_qa_failed(self, event: Event) -> None:
        """Handle QA failure event.

        Sends alert notification via Slack/webhook.

        Args:
            event: QA failure event
        """
        validation_type = event.data.get("validation_type", "unknown")
        warnings = event.data.get("warnings", [])
        ms_path = event.data.get("ms_path", "unknown")

        logger.warning(
            f"QA failure for {validation_type}: {ms_path} ({len(warnings)} warnings)"
        )

        try:
            from dsa110_contimg.monitoring.alerting import (
                Alert,
                AlertManager,
                AlertSeverity,
                AlertState,
            )
            import os
            import time

            # Create alert
            alert = Alert(
                rule_name=f"qa_failure_{validation_type}",
                severity=AlertSeverity.WARNING,
                state=AlertState.FIRING,
                message=f"QA validation failed for {validation_type}: {ms_path}\nWarnings: {', '.join(warnings[:5])}",
                fired_at=time.time(),
                labels={
                    "validation_type": validation_type,
                    "ms_path": ms_path,
                },
            )

            # Send via AlertManager
            slack_webhook = os.environ.get("SLACK_WEBHOOK_URL") or os.environ.get(
                "DSA110_SLACK_WEBHOOK"
            )
            if slack_webhook:
                manager = AlertManager(slack_webhook=slack_webhook)
                asyncio.run(manager.send_notifications([alert]))
                logger.info(f"Sent QA failure alert to Slack")

        except Exception as e:
            logger.error(f"Failed to send QA failure alert: {e}")


# =============================================================================
# Convenience function to check for calibrator in MS
# =============================================================================


def check_ms_for_calibrator(ms_path: str, radius_deg: float = 2.0) -> bool:
    """Check if an MS contains calibrator data.

    Utility function for data ingestion pipelines to determine if
    automatic calibration should be triggered.

    Args:
        ms_path: Path to Measurement Set
        radius_deg: Search radius for calibrator matching

    Returns:
        True if calibrator data is present
    """
    try:
        from dsa110_contimg.calibration.streaming import has_calibrator

        return has_calibrator(ms_path, radius_deg=radius_deg)
    except Exception as e:
        logger.warning(f"Failed to check for calibrator in {ms_path}: {e}")
        return False


def emit_data_ingested(
    ms_path: str,
    check_calibrator: bool = True,
    **extra_data: Any,
) -> Event:
    """Emit a data ingestion event.

    Convenience function for emitting DATA_INGESTED events with
    optional automatic calibrator detection.

    Args:
        ms_path: Path to the ingested MS
        check_calibrator: If True, check for calibrator automatically
        **extra_data: Additional event data

    Returns:
        The emitted Event
    """
    emitter = EventEmitter.get_instance()

    has_cal = False
    if check_calibrator:
        has_cal = check_ms_for_calibrator(ms_path)

    return emitter.emit(
        EventType.DATA_INGESTED,
        {
            "ms_path": ms_path,
            "has_calibrator": has_cal,
            **extra_data,
        },
        source="data_ingestion",
    )
