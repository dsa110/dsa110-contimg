"""
Streaming Converter for DSA-110 Continuum Imaging Pipeline.

Real-time daemon for processing incoming UVH5 subband files, with
SQLite-backed queue management, checkpoint recovery, and integrated
error handling.

Queue States:
    collecting → pending → in_progress → completed/failed

Usage:
    # Via systemd (production)
    sudo systemctl start contimg-stream.service
    
    # Manual (testing)
    python -m dsa110_contimg.conversion.streaming.streaming_converter \\
        --input-dir /data/incoming \\
        --output-dir /stage/dsa110-contimg/ms \\
        --queue-db /data/dsa110-contimg/state/ingest.sqlite3

Performance Tracking:
    Records load_time, phase_time, write_time per observation group
    in the performance_metrics table for later analysis.
"""

from __future__ import annotations

import os
import sqlite3
import time
import logging
import threading
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field, asdict

from dsa110_contimg.utils.antpos_local import get_itrf
from dsa110_contimg.conversion.strategies.writers import get_writer
from dsa110_contimg.database.hdf5_index import query_subband_groups
from dsa110_contimg.utils.exceptions import (
    ConversionError,
    DatabaseError,
    DatabaseLockError,
    QueueError,
    QueueStateTransitionError,
    wrap_exception,
    is_recoverable,
)
from dsa110_contimg.utils.logging_config import (
    setup_logging,
    log_context,
    log_exception,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Queue States
# =============================================================================

class QueueState:
    """Valid queue states for observation groups."""
    COLLECTING = "collecting"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

    # Valid state transitions
    TRANSITIONS = {
        COLLECTING: {PENDING, FAILED},
        PENDING: {IN_PROGRESS, FAILED},
        IN_PROGRESS: {COMPLETED, FAILED},
        COMPLETED: set(),  # Terminal state
        FAILED: {PENDING},  # Can retry
    }

    @classmethod
    def is_valid_transition(cls, from_state: str, to_state: str) -> bool:
        """Check if a state transition is valid."""
        return to_state in cls.TRANSITIONS.get(from_state, set())


# =============================================================================
# Performance Metrics
# =============================================================================

@dataclass
class ConversionMetrics:
    """Performance metrics for a conversion operation."""
    group_id: str
    load_time: float = 0.0
    phase_time: float = 0.0
    write_time: float = 0.0
    total_time: float = 0.0
    subband_count: int = 0
    output_size_bytes: int = 0
    recorded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# =============================================================================
# Streaming Converter
# =============================================================================

class StreamingConverter:
    """
    Real-time streaming converter for DSA-110 data.
    
    Monitors an input directory for new subband files, groups them by
    observation timestamp, and converts complete groups to Measurement Sets.
    
    Attributes:
        input_dir: Directory to watch for incoming HDF5 files
        output_dir: Directory for output Measurement Sets
        queue_db: Path to SQLite queue database
        registry_db: Path to calibration registry database
        scratch_dir: Directory for temporary files
        monitor_interval: Seconds between queue health checks
        max_retries: Maximum retry attempts for failed conversions
    """
    
    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        queue_db: str,
        registry_db: str,
        scratch_dir: str,
        monitor_interval: int = 60,
        max_retries: int = 3,
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.queue_db = queue_db
        self.registry_db = registry_db
        self.scratch_dir = scratch_dir
        self.monitor_interval = monitor_interval
        self.max_retries = max_retries
        self.running = True
        self._lock = threading.Lock()
        
        # Initialize logging
        setup_logging()
        
        logger.info(
            "StreamingConverter initialized",
            extra={
                "input_dir": input_dir,
                "output_dir": output_dir,
                "queue_db": queue_db,
                "monitor_interval": monitor_interval,
            }
        )
        
        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize queue database tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.queue_db, timeout=30)
            cursor = conn.cursor()
            
            # Create ingest queue table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ingest_queue (
                    group_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL DEFAULT 'collecting',
                    subband_count INTEGER DEFAULT 0,
                    received_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    error_type TEXT,
                    processing_stage TEXT
                )
            """)
            
            # Create performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT NOT NULL,
                    load_time REAL,
                    phase_time REAL,
                    write_time REAL,
                    total_time REAL,
                    subband_count INTEGER,
                    output_size_bytes INTEGER,
                    recorded_at TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("Queue database initialized", extra={"queue_db": self.queue_db})
            
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to initialize queue database: {e}",
                db_name="ingest",
                db_path=self.queue_db,
                operation="init",
                original_exception=e,
            ) from e

    def start(self) -> None:
        """Start the streaming converter."""
        logger.info("Starting StreamingConverter")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_queue, daemon=True)
        monitor_thread.start()
        
        # Main processing loop
        self._process_stream()

    def stop(self) -> None:
        """Stop the streaming converter gracefully."""
        logger.info("Stopping StreamingConverter")
        self.running = False

    def _process_stream(self) -> None:
        """Main loop: process pending items from the queue."""
        while self.running:
            try:
                # Get next pending group
                group_id = self._get_next_pending()
                
                if group_id:
                    self._process_group(group_id)
                else:
                    # No pending work, wait before checking again
                    time.sleep(5)
                    
            except DatabaseLockError as e:
                # Database locked, wait and retry
                logger.warning(
                    f"Database locked, waiting to retry: {e}",
                    extra=e.context,
                )
                time.sleep(10)
                
            except Exception as e:
                # Unexpected error, log and continue
                logger.error(
                    f"Unexpected error in process loop: {e}",
                    exc_info=True,
                )
                time.sleep(30)

    def _process_group(self, group_id: str) -> None:
        """
        Process a single observation group.
        
        Updates queue state throughout processing and records metrics.
        """
        with log_context(group_id=group_id, pipeline_stage="streaming"):
            start_time = time.time()
            metrics = ConversionMetrics(group_id=group_id)
            
            try:
                # Update state to in_progress
                self._update_queue_state(
                    group_id,
                    QueueState.PENDING,
                    QueueState.IN_PROGRESS,
                    processing_stage="starting",
                )
                
                # Get file list for this group
                files = self._get_group_files(group_id)
                metrics.subband_count = len(files)
                
                logger.info(
                    f"Processing group {group_id} with {len(files)} subbands",
                    extra={"subband_count": len(files), "file_list": files}
                )
                
                # Perform conversion
                self._convert_group(group_id, files, metrics)
                
                # Mark as completed
                metrics.total_time = time.time() - start_time
                self._update_queue_state(
                    group_id,
                    QueueState.IN_PROGRESS,
                    QueueState.COMPLETED,
                    processing_stage="completed",
                )
                
                # Record metrics
                self._record_metrics(metrics)
                
                logger.info(
                    f"Successfully processed group {group_id} in {metrics.total_time:.2f}s",
                    extra=metrics.to_dict(),
                )
                
            except ConversionError as e:
                self._handle_conversion_error(group_id, e, start_time)
                
            except Exception as e:
                wrapped = wrap_exception(
                    e,
                    ConversionError,
                    f"Unexpected error processing group: {e}",
                    group_id=group_id,
                )
                self._handle_conversion_error(group_id, wrapped, start_time)

    def _convert_group(
        self,
        group_id: str,
        files: list[str],
        metrics: ConversionMetrics,
    ) -> None:
        """Perform the actual conversion of a group."""
        import pyuvdata
        from dsa110_contimg.utils import FastMeta
        
        # Load and combine subbands
        self._update_queue_state(
            group_id,
            QueueState.IN_PROGRESS,
            QueueState.IN_PROGRESS,
            processing_stage="loading",
        )
        
        load_start = time.time()
        uvdata = pyuvdata.UVData()
        
        for i, file_path in enumerate(sorted(files)):
            try:
                with FastMeta(file_path) as meta:
                    _ = meta.time_array  # Validate
                    
                subband = pyuvdata.UVData()
                subband.read(file_path, strict_uvw_antpos_check=False)
                
                if i == 0:
                    uvdata = subband
                else:
                    uvdata += subband
                    
            except Exception as e:
                raise ConversionError(
                    f"Failed to load subband {file_path}: {e}",
                    input_path=file_path,
                    group_id=group_id,
                    original_exception=e,
                ) from e
        
        metrics.load_time = time.time() - load_start
        
        # Phase visibilities
        self._update_queue_state(
            group_id,
            QueueState.IN_PROGRESS,
            QueueState.IN_PROGRESS,
            processing_stage="phasing",
        )
        
        phase_start = time.time()
        # Phasing would happen here
        metrics.phase_time = time.time() - phase_start
        
        # Write Measurement Set
        self._update_queue_state(
            group_id,
            QueueState.IN_PROGRESS,
            QueueState.IN_PROGRESS,
            processing_stage="writing",
        )
        
        write_start = time.time()
        output_path = os.path.join(self.output_dir, f"{group_id}.ms")
        
        try:
            writer_cls = get_writer('parallel-subband')
            writer = writer_cls(uvdata, output_path)
            writer.write()
            
            # Record output size
            if os.path.exists(output_path):
                metrics.output_size_bytes = self._get_dir_size(output_path)
                
        except Exception as e:
            raise ConversionError(
                f"Failed to write MS {output_path}: {e}",
                output_path=output_path,
                group_id=group_id,
                original_exception=e,
            ) from e
        
        metrics.write_time = time.time() - write_start

    def _handle_conversion_error(
        self,
        group_id: str,
        error: ConversionError,
        start_time: float,
    ) -> None:
        """Handle a conversion error by updating queue and logging."""
        log_exception(logger, error, group_id=group_id)
        
        # Get current retry count
        retry_count = self._get_retry_count(group_id)
        
        if retry_count < self.max_retries and is_recoverable(error):
            # Mark as pending for retry
            logger.warning(
                f"Marking group {group_id} for retry ({retry_count + 1}/{self.max_retries})",
                extra={"retry_count": retry_count + 1}
            )
            self._update_queue_state(
                group_id,
                QueueState.IN_PROGRESS,
                QueueState.PENDING,
                error_message=str(error),
                error_type=type(error).__name__,
                retry_count=retry_count + 1,
            )
        else:
            # Mark as failed (permanent)
            logger.error(
                f"Marking group {group_id} as permanently failed",
                extra={
                    "retry_count": retry_count,
                    "max_retries": self.max_retries,
                    "recoverable": is_recoverable(error),
                }
            )
            self._update_queue_state(
                group_id,
                QueueState.IN_PROGRESS,
                QueueState.FAILED,
                error_message=str(error),
                error_type=type(error).__name__,
            )

    def _update_queue_state(
        self,
        group_id: str,
        from_state: str,
        to_state: str,
        processing_stage: str = "",
        error_message: str = "",
        error_type: str = "",
        retry_count: Optional[int] = None,
    ) -> None:
        """Update queue state with validation."""
        # Skip validation for same-state updates (progress tracking)
        if from_state != to_state and not QueueState.is_valid_transition(from_state, to_state):
            raise QueueStateTransitionError(
                group_id=group_id,
                current_state=from_state,
                target_state=to_state,
                reason="Invalid state transition",
            )
        
        try:
            conn = sqlite3.connect(self.queue_db, timeout=30)
            cursor = conn.cursor()
            
            now = datetime.utcnow().isoformat()
            updates = ["state = ?", "processing_stage = ?"]
            params = [to_state, processing_stage]
            
            if to_state == QueueState.IN_PROGRESS and from_state == QueueState.PENDING:
                updates.append("started_at = ?")
                params.append(now)
            
            if to_state in (QueueState.COMPLETED, QueueState.FAILED):
                updates.append("completed_at = ?")
                params.append(now)
            
            if error_message:
                updates.append("error_message = ?")
                params.append(error_message)
            
            if error_type:
                updates.append("error_type = ?")
                params.append(error_type)
            
            if retry_count is not None:
                updates.append("retry_count = ?")
                params.append(retry_count)
            
            params.append(group_id)
            
            cursor.execute(
                f"UPDATE ingest_queue SET {', '.join(updates)} WHERE group_id = ?",
                params
            )
            
            conn.commit()
            conn.close()
            
            logger.debug(
                f"Queue state updated: {from_state} -> {to_state}",
                extra={
                    "group_id": group_id,
                    "from_state": from_state,
                    "to_state": to_state,
                    "processing_stage": processing_stage,
                }
            )
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                raise DatabaseLockError(
                    db_name="ingest",
                    original_exception=e,
                ) from e
            raise DatabaseError(
                f"Failed to update queue state: {e}",
                db_name="ingest",
                db_path=self.queue_db,
                operation="update",
                table_name="ingest_queue",
                original_exception=e,
            ) from e

    def _get_next_pending(self) -> Optional[str]:
        """Get the next pending group from the queue."""
        try:
            conn = sqlite3.connect(self.queue_db, timeout=30)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT group_id FROM ingest_queue
                WHERE state = ?
                ORDER BY received_at ASC
                LIMIT 1
            """, (QueueState.PENDING,))
            
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else None
            
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to query pending queue: {e}",
                db_name="ingest",
                db_path=self.queue_db,
                operation="query",
                table_name="ingest_queue",
                original_exception=e,
            ) from e

    def _get_group_files(self, group_id: str) -> list[str]:
        """Get the list of files for a group (stub implementation)."""
        # This would query the HDF5 index database
        return []

    def _get_retry_count(self, group_id: str) -> int:
        """Get current retry count for a group."""
        try:
            conn = sqlite3.connect(self.queue_db, timeout=30)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT retry_count FROM ingest_queue WHERE group_id = ?",
                (group_id,)
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else 0
        except sqlite3.Error:
            return 0

    def _record_metrics(self, metrics: ConversionMetrics) -> None:
        """Record performance metrics to database."""
        try:
            conn = sqlite3.connect(self.queue_db, timeout=30)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO performance_metrics
                (group_id, load_time, phase_time, write_time, total_time,
                 subband_count, output_size_bytes, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.group_id,
                metrics.load_time,
                metrics.phase_time,
                metrics.write_time,
                metrics.total_time,
                metrics.subband_count,
                metrics.output_size_bytes,
                metrics.recorded_at,
            ))
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            # Log but don't fail on metrics recording error
            logger.warning(
                f"Failed to record performance metrics: {e}",
                extra={"group_id": metrics.group_id}
            )

    def _get_dir_size(self, path: str) -> int:
        """Get total size of a directory in bytes."""
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total

    def _monitor_queue(self) -> None:
        """Monitor queue health in background thread."""
        while self.running:
            try:
                self._check_queue_status()
            except Exception as e:
                logger.warning(f"Queue monitoring error: {e}")
            
            time.sleep(self.monitor_interval)

    def _check_queue_status(self) -> None:
        """Check queue status and log metrics."""
        try:
            conn = sqlite3.connect(self.queue_db, timeout=30)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT state, COUNT(*) FROM ingest_queue GROUP BY state
            """)
            
            state_counts = dict(cursor.fetchall())
            conn.close()
            
            logger.info(
                "Queue status",
                extra={
                    "collecting": state_counts.get(QueueState.COLLECTING, 0),
                    "pending": state_counts.get(QueueState.PENDING, 0),
                    "in_progress": state_counts.get(QueueState.IN_PROGRESS, 0),
                    "completed": state_counts.get(QueueState.COMPLETED, 0),
                    "failed": state_counts.get(QueueState.FAILED, 0),
                }
            )
            
        except sqlite3.Error as e:
            logger.warning(f"Failed to check queue status: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="DSA-110 Streaming Converter")
    parser.add_argument("--input-dir", default="/data/incoming")
    parser.add_argument("--output-dir", default="/stage/dsa110-contimg/ms")
    parser.add_argument("--queue-db", default="/data/dsa110-contimg/state/ingest.sqlite3")
    parser.add_argument("--registry-db", default="/data/dsa110-contimg/state/cal_registry.sqlite3")
    parser.add_argument("--scratch-dir", default="/stage/dsa110-contimg/scratch")
    parser.add_argument("--monitor-interval", type=int, default=60)
    parser.add_argument("--max-retries", type=int, default=3)
    
    args = parser.parse_args()
    
    converter = StreamingConverter(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        queue_db=args.queue_db,
        registry_db=args.registry_db,
        scratch_dir=args.scratch_dir,
        monitor_interval=args.monitor_interval,
        max_retries=args.max_retries,
    )
    
    try:
        converter.start()
    except KeyboardInterrupt:
        converter.stop()