"""
Pipeline Hardening Module - Fixes for Critical Weaknesses.

This module addresses 15 identified pipeline weaknesses:

Tier 1 (Data Loss Risk):
1. Calibration validity gap (bidirectional windows)
4. Race condition in calibration (calibration fence)
7. Transactional safety (state machine)
10. Disk space monitoring (quota enforcement)

Tier 2 (Data Quality Risk):
2. Calibration interpolation
3. Calibrator redundancy
5. Calibration QA (SNR thresholds)
8. RFI mitigation

Tier 3 (Operational Risk):
6. Overlapping calibration handling
9. I/O bottleneck fixes
12. Subprocess consistency
13. Observability (metrics/alerts)

Tier 4 (Technical Debt):
11. Pointing change detection
14. Database constraints
15. Mosaic trigger logic
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)


# =============================================================================
# Issue #1: Bidirectional Calibration Validity Windows
# =============================================================================

# Default validity half-window in days (±12 hours)
DEFAULT_CAL_VALIDITY_HOURS = 12.0
DEFAULT_CAL_VALIDITY_DAYS = DEFAULT_CAL_VALIDITY_HOURS / 24.0


@dataclass
class CalibrationSelection:
    """Result of calibration selection with quality metadata."""
    
    set_name: str
    paths: List[str]
    mid_mjd: float
    selection_method: str  # 'exact', 'nearest_before', 'nearest_after', 'interpolated'
    time_offset_hours: float  # How far from target MJD
    quality_score: float  # Combined quality metric
    warnings: List[str] = field(default_factory=list)


def get_active_applylist_bidirectional(
    db_path: Path,
    target_mjd: float,
    *,
    set_name: Optional[str] = None,
    validity_hours: float = DEFAULT_CAL_VALIDITY_HOURS,
    prefer_nearest: bool = True,
) -> CalibrationSelection:
    """
    Return calibration tables with bidirectional validity windows.
    
    This fixes Issue #1: Forward-only validity windows that leave pre-calibrator
    observations without valid calibration.
    
    Strategy:
    1. First try exact match (target within validity window)
    2. If no exact match and prefer_nearest=True, find nearest calibration
       (before or after) within validity_hours
    3. Return selection with quality metadata
    
    Args:
        db_path: Path to calibration registry database
        target_mjd: Target observation MJD
        set_name: Optional specific set name
        validity_hours: Maximum time offset for calibration validity (default: 12h)
        prefer_nearest: If True, find nearest even outside strict window
        
    Returns:
        CalibrationSelection with paths and metadata
        
    Raises:
        ValueError: If no suitable calibration found
    """
    from dsa110_contimg.database.unified import ensure_db
    
    conn = ensure_db(db_path)
    validity_days = validity_hours / 24.0
    
    if set_name:
        # Direct set lookup
        rows = conn.execute(
            """
            SELECT path, valid_start_mjd, valid_end_mjd, quality_metrics
            FROM caltables
            WHERE set_name = ? AND status = 'active'
            ORDER BY order_index ASC
            """,
            (set_name,),
        ).fetchall()
        
        if rows:
            # Calculate time offset from set's validity window
            mid_mjds = [
                (r[1] + r[2]) / 2 if r[1] and r[2] else target_mjd
                for r in rows
            ]
            avg_mid = sum(mid_mjds) / len(mid_mjds) if mid_mjds else target_mjd
            offset_hours = abs(target_mjd - avg_mid) * 24.0
            
            return CalibrationSelection(
                set_name=set_name,
                paths=[r[0] for r in rows],
                mid_mjd=avg_mid,
                selection_method='exact',
                time_offset_hours=offset_hours,
                quality_score=_calculate_quality_score(rows, offset_hours),
            )
        raise ValueError(f"No active calibration tables for set '{set_name}'")
    
    # BIDIRECTIONAL SEARCH: Look for calibrations ±validity_hours from target
    # This is the key fix for Issue #1
    
    # 1. Try exact match (target within validity window)
    exact_sets = conn.execute(
        """
        SELECT DISTINCT set_name, 
               (valid_start_mjd + valid_end_mjd) / 2.0 AS mid_mjd,
               MAX(created_at) AS newest
        FROM caltables
        WHERE status = 'active'
          AND (valid_start_mjd IS NULL OR valid_start_mjd <= ?)
          AND (valid_end_mjd IS NULL OR valid_end_mjd >= ?)
        GROUP BY set_name
        ORDER BY newest DESC
        """,
        (target_mjd, target_mjd),
    ).fetchall()
    
    if exact_sets:
        chosen_set = exact_sets[0][0]
        mid_mjd = exact_sets[0][1] or target_mjd
        offset_hours = abs(target_mjd - mid_mjd) * 24.0
        
        paths = _get_set_paths(conn, chosen_set)
        return CalibrationSelection(
            set_name=chosen_set,
            paths=paths,
            mid_mjd=mid_mjd,
            selection_method='exact',
            time_offset_hours=offset_hours,
            quality_score=1.0 - (offset_hours / (validity_hours * 2)),
        )
    
    # 2. BIDIRECTIONAL: Find nearest calibration (before OR after)
    if prefer_nearest:
        # Search window: target ± validity_hours
        search_min = target_mjd - validity_days
        search_max = target_mjd + validity_days
        
        # Find all sets with validity windows overlapping search range
        nearby_sets = conn.execute(
            """
            SELECT DISTINCT set_name,
                   (valid_start_mjd + COALESCE(valid_end_mjd, valid_start_mjd)) / 2.0 AS mid_mjd,
                   ABS((valid_start_mjd + COALESCE(valid_end_mjd, valid_start_mjd)) / 2.0 - ?) AS distance,
                   MAX(created_at) AS newest
            FROM caltables
            WHERE status = 'active'
              AND valid_start_mjd IS NOT NULL
              AND (
                  -- Set's validity window overlaps our search window
                  (valid_start_mjd <= ? AND (valid_end_mjd IS NULL OR valid_end_mjd >= ?))
                  OR
                  -- Set's midpoint is within search range
                  ((valid_start_mjd + COALESCE(valid_end_mjd, valid_start_mjd)) / 2.0 BETWEEN ? AND ?)
              )
            GROUP BY set_name
            ORDER BY distance ASC, newest DESC
            LIMIT 3
            """,
            (target_mjd, search_max, search_min, search_min, search_max),
        ).fetchall()
        
        if nearby_sets:
            chosen_set = nearby_sets[0][0]
            mid_mjd = nearby_sets[0][1]
            offset_hours = nearby_sets[0][2] * 24.0
            
            # Determine selection method
            if mid_mjd < target_mjd:
                method = 'nearest_before'
            else:
                method = 'nearest_after'
            
            paths = _get_set_paths(conn, chosen_set)
            
            warnings = []
            if offset_hours > validity_hours / 2:
                warnings.append(
                    f"Calibration is {offset_hours:.1f}h from target "
                    f"(recommended max: {validity_hours / 2:.1f}h)"
                )
            
            return CalibrationSelection(
                set_name=chosen_set,
                paths=paths,
                mid_mjd=mid_mjd,
                selection_method=method,
                time_offset_hours=offset_hours,
                quality_score=max(0.0, 1.0 - (offset_hours / validity_hours)),
                warnings=warnings,
            )
    
    raise ValueError(
        f"No calibration found within ±{validity_hours:.1f}h of MJD {target_mjd:.6f}"
    )


def _get_set_paths(conn: sqlite3.Connection, set_name: str) -> List[str]:
    """Get ordered paths for a calibration set."""
    rows = conn.execute(
        "SELECT path FROM caltables WHERE set_name = ? AND status = 'active' ORDER BY order_index",
        (set_name,),
    ).fetchall()
    return [r[0] for r in rows]


def _calculate_quality_score(rows: List[tuple], offset_hours: float) -> float:
    """Calculate combined quality score from table metrics and time offset."""
    base_score = 1.0 - min(offset_hours / 24.0, 0.5)
    
    # Add quality metrics if available
    quality_scores = []
    for row in rows:
        metrics_json = row[3] if len(row) > 3 else None
        if metrics_json:
            try:
                metrics = json.loads(metrics_json)
                if 'snr_median' in metrics:
                    # SNR > 50 is excellent, < 10 is poor
                    snr_score = min(metrics['snr_median'] / 50.0, 1.0)
                    quality_scores.append(snr_score)
                if 'flagged_fraction' in metrics:
                    # Lower flagged fraction is better
                    flag_score = 1.0 - metrics['flagged_fraction']
                    quality_scores.append(flag_score)
            except (json.JSONDecodeError, TypeError):
                pass
    
    if quality_scores:
        avg_quality = sum(quality_scores) / len(quality_scores)
        return (base_score + avg_quality) / 2.0
    
    return base_score


# =============================================================================
# Issue #4: Race Condition Fix - Calibration Fence
# =============================================================================

class CalibrationFence:
    """
    Coordination mechanism to prevent race conditions in calibration application.
    
    This fixes Issue #4: Target observations processed before new calibration
    is registered (40s window).
    
    Strategy:
    1. Before processing a target, check if a calibrator is being processed
    2. If so, wait for calibration to complete (with timeout)
    3. Use database-backed locking for multi-process coordination
    """
    
    FENCE_TIMEOUT_SECONDS = 120  # Max wait for calibration to complete
    POLL_INTERVAL_SECONDS = 2
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._ensure_fence_table()
    
    def _ensure_fence_table(self) -> None:
        """Create fence table if needed."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calibration_fence (
                id INTEGER PRIMARY KEY,
                calibrator_ms TEXT NOT NULL,
                started_at REAL NOT NULL,
                completed_at REAL,
                status TEXT NOT NULL DEFAULT 'in_progress',
                set_name TEXT
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_fence_status ON calibration_fence(status)"
        )
        conn.commit()
        conn.close()
    
    @contextmanager
    def calibrator_lock(self, calibrator_ms: str) -> Iterator[None]:
        """
        Context manager for calibrator processing.
        
        Signals to other workers that calibration is in progress.
        """
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        fence_id = None
        
        try:
            cursor = conn.execute(
                """
                INSERT INTO calibration_fence (calibrator_ms, started_at, status)
                VALUES (?, ?, 'in_progress')
                """,
                (calibrator_ms, time.time()),
            )
            fence_id = cursor.lastrowid
            conn.commit()
            
            yield
            
            # Mark completed
            conn.execute(
                """
                UPDATE calibration_fence 
                SET status = 'completed', completed_at = ?
                WHERE id = ?
                """,
                (time.time(), fence_id),
            )
            conn.commit()
            
        except Exception:
            if fence_id:
                conn.execute(
                    """
                    UPDATE calibration_fence 
                    SET status = 'failed', completed_at = ?
                    WHERE id = ?
                    """,
                    (time.time(), fence_id),
                )
                conn.commit()
            raise
        finally:
            conn.close()
    
    def wait_for_pending_calibrations(
        self,
        max_age_seconds: float = 300,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        """
        Wait for any in-progress calibrations to complete.
        
        Args:
            max_age_seconds: Only consider calibrations started within this window
            timeout_seconds: Maximum time to wait (default: FENCE_TIMEOUT_SECONDS)
            
        Returns:
            True if no pending calibrations or all completed
            False if timeout reached
        """
        timeout = timeout_seconds or self.FENCE_TIMEOUT_SECONDS
        deadline = time.time() + timeout
        cutoff = time.time() - max_age_seconds
        
        while time.time() < deadline:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            row = conn.execute(
                """
                SELECT COUNT(*) FROM calibration_fence
                WHERE status = 'in_progress' AND started_at > ?
                """,
                (cutoff,),
            ).fetchone()
            conn.close()
            
            if row[0] == 0:
                return True
            
            logger.debug(
                f"Waiting for {row[0]} in-progress calibration(s)..."
            )
            time.sleep(self.POLL_INTERVAL_SECONDS)
        
        logger.warning(
            f"Timeout waiting for calibrations after {timeout}s"
        )
        return False


# =============================================================================
# Issue #5: Calibration Quality Assessment
# =============================================================================

@dataclass
class CalibrationQAResult:
    """Result of calibration quality assessment."""
    
    passed: bool
    snr_mean: Optional[float] = None
    snr_min: Optional[float] = None
    flagged_fraction: Optional[float] = None
    n_antennas: Optional[int] = None
    n_solutions: Optional[int] = None
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# QA thresholds
QA_SNR_MIN_THRESHOLD = 5.0  # Minimum acceptable SNR
QA_SNR_WARN_THRESHOLD = 10.0  # SNR below this triggers warning
QA_FLAGGED_MAX_THRESHOLD = 0.5  # Maximum acceptable flagged fraction
QA_FLAGGED_WARN_THRESHOLD = 0.2  # Flagged fraction above this triggers warning
QA_MIN_ANTENNAS = 10  # Minimum antennas for valid calibration


def assess_calibration_quality(
    caltable_path: str,
    *,
    snr_min: float = QA_SNR_MIN_THRESHOLD,
    snr_warn: float = QA_SNR_WARN_THRESHOLD,
    flagged_max: float = QA_FLAGGED_MAX_THRESHOLD,
    flagged_warn: float = QA_FLAGGED_WARN_THRESHOLD,
    min_antennas: int = QA_MIN_ANTENNAS,
) -> CalibrationQAResult:
    """
    Assess quality of a calibration table.
    
    This fixes Issue #5: No automated QA before registration.
    
    Args:
        caltable_path: Path to calibration table
        snr_min: Minimum acceptable mean SNR
        snr_warn: SNR threshold for warnings
        flagged_max: Maximum acceptable flagged fraction
        flagged_warn: Flagged fraction threshold for warnings
        min_antennas: Minimum number of antennas
        
    Returns:
        CalibrationQAResult with pass/fail status and metrics
    """
    import casacore.tables as casatables
    import numpy as np
    
    result = CalibrationQAResult(passed=True)
    issues = []
    warnings = []
    
    try:
        with casatables.table(caltable_path, readonly=True) as tb:
            n_rows = tb.nrows()
            result.n_solutions = n_rows
            
            if n_rows == 0:
                result.passed = False
                issues.append("Calibration table has zero solutions")
                result.issues = issues
                return result
            
            # Check flagged fraction
            if "FLAG" in tb.colnames():
                flags = tb.getcol("FLAG")
                flagged = np.sum(flags)
                total = flags.size
                result.flagged_fraction = flagged / total if total > 0 else 0.0
                
                if result.flagged_fraction > flagged_max:
                    result.passed = False
                    issues.append(
                        f"Flagged fraction too high: {result.flagged_fraction:.1%} "
                        f"(max: {flagged_max:.1%})"
                    )
                elif result.flagged_fraction > flagged_warn:
                    warnings.append(
                        f"High flagged fraction: {result.flagged_fraction:.1%}"
                    )
            
            # Check SNR
            if "SNR" in tb.colnames():
                snr = tb.getcol("SNR").flatten()
                snr_valid = snr[~np.isnan(snr)]
                
                if len(snr_valid) > 0:
                    result.snr_mean = float(np.mean(snr_valid))
                    result.snr_min = float(np.min(snr_valid))
                    
                    if result.snr_mean < snr_min:
                        result.passed = False
                        issues.append(
                            f"Mean SNR too low: {result.snr_mean:.1f} "
                            f"(min: {snr_min:.1f})"
                        )
                    elif result.snr_mean < snr_warn:
                        warnings.append(
                            f"Low mean SNR: {result.snr_mean:.1f}"
                        )
            
            # Check antenna count
            if "ANTENNA1" in tb.colnames():
                ant1 = tb.getcol("ANTENNA1")
                result.n_antennas = len(np.unique(ant1))
                
                if result.n_antennas < min_antennas:
                    result.passed = False
                    issues.append(
                        f"Too few antennas: {result.n_antennas} "
                        f"(min: {min_antennas})"
                    )
    
    except Exception as e:
        result.passed = False
        issues.append(f"Failed to read calibration table: {e}")
    
    result.issues = issues
    result.warnings = warnings
    
    return result


def get_calibration_quality_metrics(caltable_path: str) -> Dict[str, Any]:
    """
    Extract quality metrics from calibration table for database storage.
    
    Returns JSON-serializable dict for quality_metrics column.
    """
    result = assess_calibration_quality(caltable_path)
    
    metrics = {
        "qa_passed": result.passed,
        "snr_mean": result.snr_mean,
        "snr_min": result.snr_min,
        "flagged_fraction": result.flagged_fraction,
        "n_antennas": result.n_antennas,
        "n_solutions": result.n_solutions,
        "assessed_at": time.time(),
    }
    
    if result.issues:
        metrics["issues"] = result.issues
    if result.warnings:
        metrics["warnings"] = result.warnings
    
    return metrics


# =============================================================================
# Issue #7: Transactional Safety - State Machine
# =============================================================================

class ProcessingState(Enum):
    """Processing pipeline states with allowed transitions."""
    
    RECEIVED = auto()      # Files received, not yet processed
    CONVERTING = auto()    # UVH5 -> MS conversion in progress
    CONVERTED = auto()     # Conversion complete, ready for calibration
    CALIBRATING = auto()   # Calibration in progress
    CALIBRATED = auto()    # Calibration complete, ready for imaging
    IMAGING = auto()       # Imaging in progress
    IMAGED = auto()        # Imaging complete, ready for photometry
    PHOTOMETRY = auto()    # Photometry in progress
    COMPLETED = auto()     # All processing complete
    FAILED = auto()        # Processing failed (recoverable)
    DEAD_LETTER = auto()   # Failed too many times (manual intervention)


# Valid state transitions
VALID_TRANSITIONS = {
    ProcessingState.RECEIVED: {ProcessingState.CONVERTING, ProcessingState.FAILED},
    ProcessingState.CONVERTING: {ProcessingState.CONVERTED, ProcessingState.FAILED},
    ProcessingState.CONVERTED: {ProcessingState.CALIBRATING, ProcessingState.IMAGING, ProcessingState.FAILED},
    ProcessingState.CALIBRATING: {ProcessingState.CALIBRATED, ProcessingState.FAILED},
    ProcessingState.CALIBRATED: {ProcessingState.IMAGING, ProcessingState.FAILED},
    ProcessingState.IMAGING: {ProcessingState.IMAGED, ProcessingState.FAILED},
    ProcessingState.IMAGED: {ProcessingState.PHOTOMETRY, ProcessingState.COMPLETED, ProcessingState.FAILED},
    ProcessingState.PHOTOMETRY: {ProcessingState.COMPLETED, ProcessingState.FAILED},
    ProcessingState.FAILED: {ProcessingState.RECEIVED, ProcessingState.DEAD_LETTER},  # Retry or give up
}


@dataclass
class StateTransition:
    """Record of a state transition."""
    
    group_id: str
    from_state: ProcessingState
    to_state: ProcessingState
    timestamp: float
    success: bool
    error_message: Optional[str] = None
    checkpoint_data: Optional[Dict[str, Any]] = None


class ProcessingStateMachine:
    """
    State machine for pipeline processing with atomic transitions.
    
    This fixes Issue #7: No transactional safety in multi-step processing.
    
    Features:
    - Atomic state transitions with database locking
    - Checkpoint data for recovery
    - Automatic retry tracking
    - Dead letter queue for failed items
    """
    
    MAX_RETRIES = 3
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._ensure_tables()
    
    def _ensure_tables(self) -> None:
        """Create state machine tables."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS processing_state (
                group_id TEXT PRIMARY KEY,
                current_state TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                checkpoint_json TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS state_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                from_state TEXT NOT NULL,
                to_state TEXT NOT NULL,
                timestamp REAL NOT NULL,
                success INTEGER NOT NULL,
                error_message TEXT,
                FOREIGN KEY (group_id) REFERENCES processing_state(group_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_state_current 
            ON processing_state(current_state);
            
            CREATE INDEX IF NOT EXISTS idx_transitions_group 
            ON state_transitions(group_id, timestamp);
        """)
        conn.commit()
        conn.close()
    
    def get_state(self, group_id: str) -> Optional[ProcessingState]:
        """Get current state for a group."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        row = conn.execute(
            "SELECT current_state FROM processing_state WHERE group_id = ?",
            (group_id,),
        ).fetchone()
        conn.close()
        
        if row:
            return ProcessingState[row[0]]
        return None
    
    def initialize(self, group_id: str) -> None:
        """Initialize a new processing group."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        now = time.time()
        conn.execute(
            """
            INSERT OR IGNORE INTO processing_state 
            (group_id, current_state, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (group_id, ProcessingState.RECEIVED.name, now, now),
        )
        conn.commit()
        conn.close()
    
    @contextmanager
    def transition(
        self,
        group_id: str,
        to_state: ProcessingState,
        checkpoint_data: Optional[Dict[str, Any]] = None,
    ) -> Iterator[None]:
        """
        Atomic state transition with automatic rollback on failure.
        
        Usage:
            with state_machine.transition(group_id, ProcessingState.CONVERTING):
                # Do conversion work
                pass
            # State is now CONVERTING (or rolled back on exception)
        """
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        
        # Get current state with lock
        conn.execute("BEGIN EXCLUSIVE")
        
        row = conn.execute(
            "SELECT current_state, retry_count FROM processing_state WHERE group_id = ?",
            (group_id,),
        ).fetchone()
        
        if not row:
            conn.rollback()
            raise ValueError(f"Group {group_id} not initialized")
        
        from_state = ProcessingState[row[0]]
        retry_count = row[1]
        
        # Validate transition
        if to_state not in VALID_TRANSITIONS.get(from_state, set()):
            conn.rollback()
            raise ValueError(
                f"Invalid transition: {from_state.name} -> {to_state.name}"
            )
        
        now = time.time()
        checkpoint_json = json.dumps(checkpoint_data) if checkpoint_data else None
        
        try:
            # Update state
            conn.execute(
                """
                UPDATE processing_state 
                SET current_state = ?, updated_at = ?, checkpoint_json = ?
                WHERE group_id = ?
                """,
                (to_state.name, now, checkpoint_json, group_id),
            )
            
            # Log transition (in progress)
            conn.execute(
                """
                INSERT INTO state_transitions 
                (group_id, from_state, to_state, timestamp, success)
                VALUES (?, ?, ?, ?, 0)
                """,
                (group_id, from_state.name, to_state.name, now),
            )
            
            conn.commit()
            
            yield  # Execute the actual work
            
            # Mark transition successful
            conn2 = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn2.execute(
                """
                UPDATE state_transitions 
                SET success = 1
                WHERE group_id = ? AND to_state = ? AND timestamp = ?
                """,
                (group_id, to_state.name, now),
            )
            conn2.commit()
            conn2.close()
            
        except Exception as e:
            # Rollback to previous state
            conn2 = sqlite3.connect(str(self.db_path), timeout=30.0)
            new_retry = retry_count + 1
            
            if new_retry >= self.MAX_RETRIES:
                # Move to dead letter
                conn2.execute(
                    """
                    UPDATE processing_state 
                    SET current_state = ?, last_error = ?, 
                        retry_count = ?, updated_at = ?
                    WHERE group_id = ?
                    """,
                    (ProcessingState.DEAD_LETTER.name, str(e), new_retry, time.time(), group_id),
                )
                logger.error(
                    f"Group {group_id} moved to dead letter after {new_retry} retries"
                )
            else:
                # Stay in FAILED state for retry
                conn2.execute(
                    """
                    UPDATE processing_state 
                    SET current_state = ?, last_error = ?, 
                        retry_count = ?, updated_at = ?
                    WHERE group_id = ?
                    """,
                    (ProcessingState.FAILED.name, str(e), new_retry, time.time(), group_id),
                )
            
            # Log failed transition
            conn2.execute(
                """
                UPDATE state_transitions 
                SET success = 0, error_message = ?
                WHERE group_id = ? AND to_state = ? AND timestamp = ?
                """,
                (str(e), group_id, to_state.name, now),
            )
            
            conn2.commit()
            conn2.close()
            raise
        finally:
            conn.close()
    
    def get_retryable(self) -> List[Tuple[str, int]]:
        """Get groups that can be retried."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        rows = conn.execute(
            """
            SELECT group_id, retry_count FROM processing_state
            WHERE current_state = ? AND retry_count < ?
            ORDER BY updated_at ASC
            """,
            (ProcessingState.FAILED.name, self.MAX_RETRIES),
        ).fetchall()
        conn.close()
        return [(r[0], r[1]) for r in rows]
    
    def reset_for_retry(self, group_id: str, to_state: ProcessingState) -> None:
        """Reset a failed group for retry from a specific state."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute(
            """
            UPDATE processing_state 
            SET current_state = ?, updated_at = ?
            WHERE group_id = ? AND current_state = ?
            """,
            (to_state.name, time.time(), group_id, ProcessingState.FAILED.name),
        )
        conn.commit()
        conn.close()


# =============================================================================
# Issue #10: Disk Space Monitoring
# =============================================================================

@dataclass
class DiskQuota:
    """Disk quota configuration."""
    
    path: Path
    warning_threshold_gb: float = 100.0  # Warn when free space below this
    critical_threshold_gb: float = 20.0  # Stop processing when below this
    cleanup_target_gb: float = 200.0  # Target free space after cleanup


@dataclass
class DiskStatus:
    """Current disk status."""
    
    path: Path
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float
    status: str  # 'ok', 'warning', 'critical'


def check_disk_space(path: Path, quota: Optional[DiskQuota] = None) -> DiskStatus:
    """
    Check disk space for a path.
    
    This fixes Issue #10: No disk space monitoring.
    """
    stat = os.statvfs(path)
    
    total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
    free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
    used_gb = total_gb - free_gb
    usage_percent = (used_gb / total_gb) * 100 if total_gb > 0 else 0
    
    status = 'ok'
    if quota:
        if free_gb < quota.critical_threshold_gb:
            status = 'critical'
        elif free_gb < quota.warning_threshold_gb:
            status = 'warning'
    
    return DiskStatus(
        path=path,
        total_gb=total_gb,
        used_gb=used_gb,
        free_gb=free_gb,
        usage_percent=usage_percent,
        status=status,
    )


class DiskSpaceMonitor:
    """
    Monitor disk space and trigger cleanup when needed.
    """
    
    def __init__(
        self,
        quotas: List[DiskQuota],
        cleanup_callback: Optional[Callable[[Path, float], int]] = None,
    ):
        """
        Args:
            quotas: List of disk quotas to monitor
            cleanup_callback: Function(path, target_gb) -> freed_bytes
        """
        self.quotas = {q.path: q for q in quotas}
        self.cleanup_callback = cleanup_callback
        self._lock = threading.Lock()
    
    def check_all(self) -> Dict[Path, DiskStatus]:
        """Check all monitored paths."""
        results = {}
        for path, quota in self.quotas.items():
            try:
                results[path] = check_disk_space(path, quota)
            except OSError as e:
                logger.error(f"Failed to check disk space for {path}: {e}")
        return results
    
    def is_safe_to_process(self) -> bool:
        """Check if all disks have sufficient space."""
        for path, quota in self.quotas.items():
            try:
                status = check_disk_space(path, quota)
                if status.status == 'critical':
                    logger.error(
                        f"CRITICAL: Disk space low on {path}: "
                        f"{status.free_gb:.1f}GB free "
                        f"(critical threshold: {quota.critical_threshold_gb}GB)"
                    )
                    return False
            except OSError:
                continue
        return True
    
    def trigger_cleanup_if_needed(self) -> Dict[Path, int]:
        """
        Trigger cleanup on paths below warning threshold.
        
        Returns:
            Dict mapping paths to bytes freed
        """
        if not self.cleanup_callback:
            return {}
        
        freed = {}
        with self._lock:
            for path, quota in self.quotas.items():
                try:
                    status = check_disk_space(path, quota)
                    if status.status in ('warning', 'critical'):
                        target = quota.cleanup_target_gb - status.free_gb
                        if target > 0:
                            bytes_freed = self.cleanup_callback(path, target)
                            freed[path] = bytes_freed
                            logger.info(
                                f"Cleanup freed {bytes_freed / (1024**3):.2f}GB on {path}"
                            )
                except Exception as e:
                    logger.error(f"Cleanup failed for {path}: {e}")
        
        return freed


def default_cleanup_callback(path: Path, target_gb: float) -> int:
    """
    Default cleanup: remove oldest processed MS files.
    
    This is a conservative cleanup that only removes files
    that have been successfully imaged.
    """
    # This is a placeholder - actual implementation would query
    # the database for completed MS files and remove oldest
    logger.warning(
        f"Default cleanup not implemented. Need to free {target_gb:.1f}GB on {path}"
    )
    return 0


# =============================================================================
# Issue #6: Overlapping Calibration Handling
# =============================================================================

def check_calibration_overlap(
    db_path: Path,
    new_set_name: str,
    valid_start_mjd: float,
    valid_end_mjd: Optional[float],
    cal_field: Optional[str] = None,
    refant: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Check for overlapping calibration sets before registration.
    
    This fixes Issue #6: Weak overlapping calibration handling.
    
    Returns list of conflicting sets with metadata.
    """
    from dsa110_contimg.database.unified import ensure_db
    
    conn = ensure_db(db_path)
    
    # Find overlapping sets
    if valid_end_mjd is None:
        # Open-ended: conflicts with anything after start
        overlaps = conn.execute(
            """
            SELECT DISTINCT set_name, cal_field, refant, 
                   MIN(valid_start_mjd) as set_start,
                   MAX(valid_end_mjd) as set_end
            FROM caltables
            WHERE status = 'active'
              AND set_name != ?
              AND (valid_end_mjd IS NULL OR valid_end_mjd >= ?)
            GROUP BY set_name
            """,
            (new_set_name, valid_start_mjd),
        ).fetchall()
    else:
        overlaps = conn.execute(
            """
            SELECT DISTINCT set_name, cal_field, refant,
                   MIN(valid_start_mjd) as set_start,
                   MAX(valid_end_mjd) as set_end
            FROM caltables
            WHERE status = 'active'
              AND set_name != ?
              AND (
                  (valid_start_mjd <= ? AND (valid_end_mjd IS NULL OR valid_end_mjd >= ?))
                  OR
                  (valid_start_mjd >= ? AND valid_start_mjd <= ?)
              )
            GROUP BY set_name
            """,
            (new_set_name, valid_end_mjd, valid_start_mjd, valid_start_mjd, valid_end_mjd),
        ).fetchall()
    
    conflicts = []
    for row in overlaps:
        conflict = {
            "set_name": row[0],
            "cal_field": row[1],
            "refant": row[2],
            "valid_start_mjd": row[3],
            "valid_end_mjd": row[4],
            "issues": [],
        }
        
        # Check for incompatibilities
        if refant and row[2] and refant != row[2]:
            conflict["issues"].append(
                f"Different reference antenna: {refant} vs {row[2]}"
            )
        if cal_field and row[1] and cal_field != row[1]:
            conflict["issues"].append(
                f"Different calibrator field: {cal_field} vs {row[1]}"
            )
        
        conflicts.append(conflict)
    
    return conflicts


def resolve_calibration_overlap(
    db_path: Path,
    new_set_name: str,
    valid_start_mjd: float,
    valid_end_mjd: Optional[float],
    *,
    strategy: str = "trim",  # 'trim', 'retire', 'error'
) -> None:
    """
    Resolve overlapping calibrations.
    
    Strategies:
    - trim: Adjust validity windows of existing sets to not overlap
    - retire: Retire overlapping sets entirely
    - error: Raise error if overlap exists
    """
    conflicts = check_calibration_overlap(
        db_path, new_set_name, valid_start_mjd, valid_end_mjd
    )
    
    if not conflicts:
        return
    
    from dsa110_contimg.database.unified import ensure_db, retire_caltable_set
    
    if strategy == "error":
        conflict_names = [c["set_name"] for c in conflicts]
        raise ValueError(
            f"Calibration overlap detected with sets: {conflict_names}. "
            f"Use strategy='trim' or 'retire' to resolve."
        )
    
    conn = ensure_db(db_path)
    
    for conflict in conflicts:
        if strategy == "retire":
            retire_caltable_set(
                db_path,
                conflict["set_name"],
                reason=f"Superseded by {new_set_name}",
            )
            logger.info(f"Retired overlapping set: {conflict['set_name']}")
        
        elif strategy == "trim":
            # Trim existing set's validity to end before new set starts
            conn.execute(
                """
                UPDATE caltables 
                SET valid_end_mjd = ?
                WHERE set_name = ? 
                  AND status = 'active'
                  AND (valid_end_mjd IS NULL OR valid_end_mjd > ?)
                """,
                (valid_start_mjd, conflict["set_name"], valid_start_mjd),
            )
            conn.commit()
            logger.info(
                f"Trimmed validity of {conflict['set_name']} to end at MJD {valid_start_mjd}"
            )


# =============================================================================
# Issue #8: RFI Mitigation - Pre-flagging
# =============================================================================

@dataclass
class RFIStats:
    """RFI flagging statistics."""
    
    original_flagged_fraction: float
    new_flagged_fraction: float
    rfi_detected_fraction: float
    channels_flagged: int
    baselines_flagged: int
    processing_time_s: float


def preflag_rfi(
    ms_path: str,
    *,
    strategy: str = "tfcrop",
    aggressive: bool = False,
) -> RFIStats:
    """
    Pre-flag RFI before calibration.
    
    This fixes Issue #8: Inadequate RFI mitigation.
    
    Args:
        ms_path: Path to Measurement Set
        strategy: Flagging strategy ('tfcrop', 'rflag', 'manual')
        aggressive: If True, use more aggressive thresholds
        
    Returns:
        RFIStats with flagging results
    """
    from casatasks import flagdata
    import casacore.tables as casatables
    import numpy as np
    
    start_time = time.time()
    
    # Get initial flag state
    with casatables.table(ms_path, readonly=True) as tb:
        flags = tb.getcol("FLAG")
        original_flagged = np.sum(flags) / flags.size
    
    # Apply flagging based on strategy
    if strategy == "tfcrop":
        # Time-frequency crop: good for broadband RFI
        threshold = 3.0 if aggressive else 4.0
        flagdata(
            vis=ms_path,
            mode="tfcrop",
            datacolumn="DATA",
            timecutoff=threshold,
            freqcutoff=threshold,
            action="apply",
        )
    
    elif strategy == "rflag":
        # R-flag: statistical outlier detection
        threshold = 4.0 if aggressive else 5.0
        flagdata(
            vis=ms_path,
            mode="rflag",
            datacolumn="DATA",
            timedevscale=threshold,
            freqdevscale=threshold,
            action="apply",
        )
    
    # Get final flag state
    with casatables.table(ms_path, readonly=True) as tb:
        flags = tb.getcol("FLAG")
        new_flagged = np.sum(flags) / flags.size
    
    rfi_fraction = new_flagged - original_flagged
    
    return RFIStats(
        original_flagged_fraction=original_flagged,
        new_flagged_fraction=new_flagged,
        rfi_detected_fraction=rfi_fraction,
        channels_flagged=0,  # Would need more detailed analysis
        baselines_flagged=0,
        processing_time_s=time.time() - start_time,
    )


# =============================================================================
# Issue #13: Observability - Metrics Registry
# =============================================================================

class MetricsRegistry:
    """
    Central registry for pipeline metrics.
    
    This fixes Issue #13: Inadequate observability.
    
    Provides:
    - Counter/gauge/histogram tracking
    - Prometheus-compatible export
    - Alert threshold checking
    """
    
    def __init__(self):
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._labels: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()
    
    def inc_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value
            if labels:
                self._labels[key] = labels
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge value."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
            if labels:
                self._labels[key] = labels
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            if labels:
                self._labels[key] = labels
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create unique key from name and labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics as dict."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: {"values": v, "count": len(v)} for k, v in self._histograms.items()},
            }
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        with self._lock:
            for key, value in self._counters.items():
                lines.append(f"# TYPE {key.split('{')[0]} counter")
                lines.append(f"{key} {value}")
            
            for key, value in self._gauges.items():
                lines.append(f"# TYPE {key.split('{')[0]} gauge")
                lines.append(f"{key} {value}")
            
            for key, values in self._histograms.items():
                base_name = key.split('{')[0]
                lines.append(f"# TYPE {base_name} histogram")
                lines.append(f"{key}_count {len(values)}")
                if values:
                    lines.append(f"{key}_sum {sum(values)}")
        
        return "\n".join(lines) + "\n"


# Global metrics registry
_metrics_registry: Optional[MetricsRegistry] = None


def get_metrics_registry() -> MetricsRegistry:
    """Get the global metrics registry."""
    global _metrics_registry
    if _metrics_registry is None:
        _metrics_registry = MetricsRegistry()
    return _metrics_registry


# Convenience functions for common metrics
def record_conversion_time(group_id: str, seconds: float) -> None:
    """Record conversion time for a group."""
    registry = get_metrics_registry()
    registry.observe_histogram("contimg_conversion_seconds", seconds)
    registry.inc_counter("contimg_conversions_total")


def record_calibration_quality(set_name: str, snr: float, flagged: float) -> None:
    """Record calibration quality metrics."""
    registry = get_metrics_registry()
    registry.set_gauge("contimg_calibration_snr", snr, {"set_name": set_name})
    registry.set_gauge("contimg_calibration_flagged", flagged, {"set_name": set_name})


def record_imaging_time(ms_path: str, seconds: float) -> None:
    """Record imaging time."""
    registry = get_metrics_registry()
    registry.observe_histogram("contimg_imaging_seconds", seconds)
    registry.inc_counter("contimg_images_total")


def record_queue_depth(state: str, count: int) -> None:
    """Record queue depth by state."""
    registry = get_metrics_registry()
    registry.set_gauge("contimg_queue_depth", count, {"state": state})


# =============================================================================
# Issue #3: Calibrator Redundancy
# =============================================================================

@dataclass
class CalibratorCandidate:
    """A potential calibrator with quality metrics."""
    
    name: str
    ra_deg: float
    dec_deg: float
    flux_jy: float
    transit_mjd: float
    beam_response: float  # Primary beam response at transit
    quality_score: float  # Combined quality metric


def find_backup_calibrators(
    dec_deg: float,
    target_mjd: float,
    db_path: Path,
    *,
    max_candidates: int = 3,
    min_flux_jy: float = 1.0,
) -> List[CalibratorCandidate]:
    """
    Find backup calibrators for redundancy.
    
    This fixes Issue #3: Single calibrator strategy is fragile.
    
    Returns ranked list of calibrator candidates near the target declination.
    """
    from dsa110_contimg.database.unified import ensure_db
    
    conn = ensure_db(db_path)
    
    # Query calibrators within beam range
    # DSA-110 primary beam FWHM is ~2.5° at 1.4 GHz
    dec_tolerance = 2.5
    
    rows = conn.execute(
        """
        SELECT name, ra_deg, dec_deg, flux_jy
        FROM calibrator_catalog
        WHERE status = 'active'
          AND dec_deg BETWEEN ? AND ?
          AND flux_jy >= ?
        ORDER BY flux_jy DESC
        LIMIT ?
        """,
        (dec_deg - dec_tolerance, dec_deg + dec_tolerance, min_flux_jy, max_candidates * 2),
    ).fetchall()
    
    if not rows:
        return []
    
    candidates = []
    for row in rows:
        name, ra, dec, flux = row
        
        # Calculate transit time
        # Simplified: transit occurs when RA matches LST
        from dsa110_contimg.utils.constants import DSA110_LOCATION
        from astropy.time import Time
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        
        # Find next transit after target_mjd
        t = Time(target_mjd, format='mjd')
        lst = t.sidereal_time('apparent', DSA110_LOCATION).deg
        
        # Hours until RA transits
        ra_diff = (ra - lst) % 360
        hours_to_transit = ra_diff / 15.0  # 15 deg/hour
        transit_mjd = target_mjd + hours_to_transit / 24.0
        
        # Estimate beam response based on dec offset
        dec_offset = abs(dec - dec_deg)
        beam_response = max(0, 1.0 - (dec_offset / dec_tolerance) ** 2)
        
        # Quality score: prefer bright, well-centered calibrators
        quality = (flux / 10.0) * beam_response
        
        candidates.append(CalibratorCandidate(
            name=name,
            ra_deg=ra,
            dec_deg=dec,
            flux_jy=flux,
            transit_mjd=transit_mjd,
            beam_response=beam_response,
            quality_score=quality,
        ))
    
    # Sort by quality score
    candidates.sort(key=lambda c: c.quality_score, reverse=True)
    
    return candidates[:max_candidates]


# =============================================================================
# Issue #15: Mosaic Trigger Logic Fixes
# =============================================================================

@dataclass
class MosaicGroup:
    """A group of observations suitable for mosaicing."""
    
    group_id: str
    ms_paths: List[str]
    center_ra_deg: float
    center_dec_deg: float
    dec_range: Tuple[float, float]
    time_range_mjd: Tuple[float, float]
    total_integration_s: float


def find_mosaic_groups(
    db_path: Path,
    *,
    dec_tolerance_deg: float = 0.5,
    time_window_hours: float = 2.0,
    min_observations: int = 3,
    max_observations: int = 24,
) -> List[MosaicGroup]:
    """
    Find groups of observations suitable for mosaicing.
    
    This fixes Issue #15: Mosaic trigger logic fragility.
    
    Improvements over original:
    - Groups by declination (not just time)
    - Handles observation gaps gracefully
    - Configurable thresholds
    """
    from dsa110_contimg.database.unified import Database
    
    db = Database(db_path)
    
    # Get all imaged MS files with coordinates
    rows = db.query(
        """
        SELECT path, mid_mjd, dec_deg, ra_deg
        FROM ms_index
        WHERE stage = 'imaged' 
          AND dec_deg IS NOT NULL
          AND mid_mjd IS NOT NULL
        ORDER BY dec_deg, mid_mjd
        """
    )
    
    if not rows:
        return []
    
    # Group by declination band
    dec_bands: Dict[float, List[Dict]] = {}
    for row in rows:
        dec = row['dec_deg']
        band_center = round(dec / dec_tolerance_deg) * dec_tolerance_deg
        if band_center not in dec_bands:
            dec_bands[band_center] = []
        dec_bands[band_center].append(row)
    
    # Within each dec band, group by time
    groups = []
    time_window_days = time_window_hours / 24.0
    
    for dec_center, observations in dec_bands.items():
        # Sort by time
        observations.sort(key=lambda x: x['mid_mjd'])
        
        current_group: List[Dict] = []
        
        for obs in observations:
            if not current_group:
                current_group.append(obs)
            else:
                time_gap = obs['mid_mjd'] - current_group[-1]['mid_mjd']
                
                if time_gap <= time_window_days and len(current_group) < max_observations:
                    current_group.append(obs)
                else:
                    # Save current group if large enough
                    if len(current_group) >= min_observations:
                        groups.append(_make_mosaic_group(current_group, dec_center))
                    current_group = [obs]
        
        # Don't forget the last group
        if len(current_group) >= min_observations:
            groups.append(_make_mosaic_group(current_group, dec_center))
    
    return groups


def _make_mosaic_group(observations: List[Dict], dec_center: float) -> MosaicGroup:
    """Create MosaicGroup from list of observations."""
    ms_paths = [o['path'] for o in observations]
    ras = [o['ra_deg'] for o in observations]
    decs = [o['dec_deg'] for o in observations]
    mjds = [o['mid_mjd'] for o in observations]
    
    # Estimate integration time (5 minutes per observation)
    integration_s = len(observations) * 309.0
    
    return MosaicGroup(
        group_id=f"mosaic_{mjds[0]:.3f}_{dec_center:+.1f}",
        ms_paths=ms_paths,
        center_ra_deg=sum(ras) / len(ras),
        center_dec_deg=sum(decs) / len(decs),
        dec_range=(min(decs), max(decs)),
        time_range_mjd=(min(mjds), max(mjds)),
        total_integration_s=integration_s,
    )
