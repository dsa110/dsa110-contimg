"""
Pipeline state machine with transaction safety.

This module provides state management for MS (Measurement Set) processing
through the DSA-110 continuum imaging pipeline. It tracks the processing
state of each MS file, enables checkpoint/resume for long-running operations,
and provides retry logic for failed operations.

States:
    PENDING: Queued for processing
    CONVERTING: Being converted from UVH5 to MS format
    CONVERTED: Conversion complete, ready for RFI flagging
    FLAGGING_RFI: GPU RFI detection running
    SOLVING_CAL: Calibration gains being solved
    APPLYING_CAL: Gains being applied to visibilities
    IMAGING: GPU gridding and FFT to produce images
    DONE: Successfully completed all processing
    FAILED: Processing failed (can retry)
    ERROR: Permanent error (requires manual intervention)

Usage:
    from dsa110_contimg.database.state_machine import (
        MSStateMachine, MSState, StateTransitionError
    )

    sm = MSStateMachine()

    # Start processing
    sm.transition("/path/to/file.ms", MSState.CONVERTING)

    # After conversion succeeds
    sm.transition("/path/to/file.ms", MSState.CONVERTED)

    # Check current state
    state = sm.get_state("/path/to/file.ms")

    # Handle failure with retry
    try:
        process_ms(ms_path)
    except Exception as e:
        sm.mark_failed(ms_path, e)
        if sm.can_retry(ms_path):
            sm.reset_for_retry(ms_path)

Configuration:
    - Uses unified pipeline.sqlite3 database
    - Max retries configurable (default: 3)
    - Checkpoint data stored as JSON for resume capability
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from .session import get_db_path

logger = logging.getLogger(__name__)


# =============================================================================
# State Definitions
# =============================================================================


class MSState(Enum):
    """MS processing states.

    The state machine enforces valid transitions between these states.
    See MSStateMachine.TRANSITIONS for the state transition graph.
    """

    PENDING = "pending"
    CONVERTING = "converting"
    CONVERTED = "converted"
    FLAGGING_RFI = "flagging_rfi"
    SOLVING_CAL = "solving_cal"
    APPLYING_CAL = "applying_cal"
    IMAGING = "imaging"
    DONE = "done"
    FAILED = "failed"
    ERROR = "error"

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (no outgoing transitions except to ERROR)."""
        return self in (MSState.DONE, MSState.ERROR)

    def is_processing(self) -> bool:
        """Check if this state represents active processing."""
        return self in (
            MSState.CONVERTING,
            MSState.FLAGGING_RFI,
            MSState.SOLVING_CAL,
            MSState.APPLYING_CAL,
            MSState.IMAGING,
        )

    def is_recoverable(self) -> bool:
        """Check if this state can be recovered from via retry."""
        return self in (MSState.FAILED, MSState.PENDING)


# =============================================================================
# Exceptions
# =============================================================================


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(
        self,
        ms_path: str,
        current_state: MSState,
        requested_state: MSState,
        valid_transitions: List[MSState],
    ):
        self.ms_path = ms_path
        self.current_state = current_state
        self.requested_state = requested_state
        self.valid_transitions = valid_transitions

        valid_str = ", ".join(s.value for s in valid_transitions) if valid_transitions else "none"
        super().__init__(
            f"Invalid state transition for {ms_path}: "
            f"{current_state.value} → {requested_state.value}. "
            f"Valid transitions from {current_state.value}: [{valid_str}]"
        )


class StateNotFoundError(Exception):
    """Raised when querying state for an untracked MS path."""

    def __init__(self, ms_path: str):
        self.ms_path = ms_path
        super().__init__(f"No state tracking record found for: {ms_path}")


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class StateRecord:
    """Record of MS processing state.

    Attributes:
        ms_path: Path to the MS file being tracked
        current_state: Current processing state
        previous_state: State before the last transition
        transition_time: Unix timestamp of last state transition
        retry_count: Number of retry attempts after failure
        error_message: Error message if in FAILED or ERROR state
        checkpoint_data: JSON-serializable checkpoint for resume
        created_at: Unix timestamp when tracking started
    """

    ms_path: str
    current_state: MSState
    previous_state: Optional[MSState] = None
    transition_time: float = 0.0
    retry_count: int = 0
    error_message: Optional[str] = None
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

    @classmethod
    def from_row(cls, row: Tuple) -> StateRecord:
        """Create StateRecord from database row.

        Args:
            row: Tuple of (ms_path, current_state, previous_state,
                          transition_time, retry_count, error_message,
                          checkpoint_data, created_at)

        Returns:
            StateRecord instance
        """
        (
            ms_path,
            current_state_str,
            previous_state_str,
            transition_time,
            retry_count,
            error_message,
            checkpoint_json,
            created_at,
        ) = row

        return cls(
            ms_path=ms_path,
            current_state=MSState(current_state_str),
            previous_state=MSState(previous_state_str) if previous_state_str else None,
            transition_time=transition_time or 0.0,
            retry_count=retry_count or 0,
            error_message=error_message,
            checkpoint_data=json.loads(checkpoint_json) if checkpoint_json else {},
            created_at=created_at or 0.0,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ms_path": self.ms_path,
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "transition_time": self.transition_time,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "checkpoint_data": self.checkpoint_data,
            "created_at": self.created_at,
        }


@dataclass
class TransitionResult:
    """Result of a state transition.

    Attributes:
        success: Whether the transition succeeded
        ms_path: Path to the MS file
        old_state: State before transition
        new_state: State after transition (or attempted state if failed)
        timestamp: Unix timestamp of transition
        error: Error message if transition failed
    """

    success: bool
    ms_path: str
    old_state: MSState
    new_state: MSState
    timestamp: float
    error: Optional[str] = None


# =============================================================================
# State Machine
# =============================================================================


class MSStateMachine:
    """Manage MS processing state with transaction safety.

    The state machine tracks the processing state of each MS file through
    the pipeline, enforces valid state transitions, and provides checkpoint/
    resume capability for long-running operations.

    State Transition Graph:

        PENDING ─────────────┬───────────────────────────────────┐
            │                │                                   │
            ▼                ▼                                   │
        CONVERTING ──► CONVERTED ──► FLAGGING_RFI               │
            │                │           │  │                    │
            │                │           │  └──► SOLVING_CAL ────┤
            │                │           │           │           │
            │                │           └──────────┐│           │
            │                │                      ▼▼           │
            ▼                ▼                  APPLYING_CAL ────┤
         FAILED ◄────────────┴─────────────────────│             │
            │                                      ▼             │
            │                                   IMAGING ─────────┤
            │                                      │             │
            ▼                                      ▼             ▼
          ERROR ◄──────────────────────────────  DONE ◄─────────┘

    Attributes:
        db_path: Path to SQLite database for state persistence
        max_retries: Maximum retry attempts before ERROR state
    """

    # Valid state transitions
    TRANSITIONS: Dict[MSState, List[MSState]] = {
        MSState.PENDING: [MSState.CONVERTING, MSState.FAILED],
        MSState.CONVERTING: [MSState.CONVERTED, MSState.FAILED],
        MSState.CONVERTED: [MSState.FLAGGING_RFI, MSState.FAILED],
        MSState.FLAGGING_RFI: [
            MSState.SOLVING_CAL,  # If using fresh calibration
            MSState.APPLYING_CAL,  # If using existing calibration
            MSState.FAILED,
        ],
        MSState.SOLVING_CAL: [MSState.APPLYING_CAL, MSState.DONE, MSState.FAILED],
        MSState.APPLYING_CAL: [MSState.IMAGING, MSState.FAILED],
        MSState.IMAGING: [MSState.DONE, MSState.FAILED],
        MSState.DONE: [],  # Terminal state
        MSState.FAILED: [MSState.PENDING, MSState.ERROR],  # Retry or escalate
        MSState.ERROR: [],  # Terminal state - requires manual intervention
    }

    # Schema for ms_state table
    SCHEMA = """
        CREATE TABLE IF NOT EXISTS ms_state (
            ms_path TEXT PRIMARY KEY,
            current_state TEXT NOT NULL,
            previous_state TEXT,
            transition_time REAL NOT NULL,
            retry_count INTEGER DEFAULT 0,
            error_message TEXT,
            checkpoint_data TEXT,
            created_at REAL NOT NULL
        )
    """

    # Index for efficient state queries
    INDEX_STATE = """
        CREATE INDEX IF NOT EXISTS idx_ms_state_current
        ON ms_state(current_state)
    """

    INDEX_TIME = """
        CREATE INDEX IF NOT EXISTS idx_ms_state_transition_time
        ON ms_state(transition_time)
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_retries: int = 3,
    ):
        """Initialize state machine.

        Args:
            db_path: Path to SQLite database. If None, uses pipeline.sqlite3.
            max_retries: Maximum retry attempts before transitioning to ERROR.
        """
        self.db_path = db_path or get_db_path("pipeline")
        self.max_retries = max_retries
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create database schema if not exists."""
        # Ensure parent directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute(self.SCHEMA)
            conn.execute(self.INDEX_STATE)
            conn.execute(self.INDEX_TIME)
            conn.commit()

        logger.debug("State machine schema initialized at %s", self.db_path)

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with proper configuration.

        Yields:
            SQLite connection configured for WAL mode and proper timeout.
        """
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            isolation_level=None,  # Autocommit mode, we manage transactions
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # State Queries
    # -------------------------------------------------------------------------

    def get_state(self, ms_path: str) -> MSState:
        """Get current state for an MS path.

        Args:
            ms_path: Path to MS file

        Returns:
            Current MSState, or PENDING if not tracked
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT current_state FROM ms_state WHERE ms_path = ?",
                (ms_path,),
            )
            row = cursor.fetchone()

        return MSState(row["current_state"]) if row else MSState.PENDING

    def get_record(self, ms_path: str) -> Optional[StateRecord]:
        """Get full state record for an MS path.

        Args:
            ms_path: Path to MS file

        Returns:
            StateRecord if tracked, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT ms_path, current_state, previous_state, transition_time,
                       retry_count, error_message, checkpoint_data, created_at
                FROM ms_state WHERE ms_path = ?
                """,
                (ms_path,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return StateRecord.from_row(tuple(row))

    def is_tracked(self, ms_path: str) -> bool:
        """Check if an MS path is being tracked.

        Args:
            ms_path: Path to MS file

        Returns:
            True if tracking record exists
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM ms_state WHERE ms_path = ?",
                (ms_path,),
            )
            return cursor.fetchone() is not None

    def list_by_state(
        self,
        state: MSState,
        limit: int = 100,
        offset: int = 0,
    ) -> List[StateRecord]:
        """List all MS files in a given state.

        Args:
            state: State to filter by
            limit: Maximum records to return
            offset: Pagination offset

        Returns:
            List of StateRecord instances
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT ms_path, current_state, previous_state, transition_time,
                       retry_count, error_message, checkpoint_data, created_at
                FROM ms_state
                WHERE current_state = ?
                ORDER BY transition_time DESC
                LIMIT ? OFFSET ?
                """,
                (state.value, limit, offset),
            )
            rows = cursor.fetchall()

        return [StateRecord.from_row(tuple(row)) for row in rows]

    def list_processing(self, limit: int = 100) -> List[StateRecord]:
        """List all MS files currently being processed.

        Args:
            limit: Maximum records to return

        Returns:
            List of StateRecord instances for MS files in processing states
        """
        processing_states = [s.value for s in MSState if s.is_processing()]
        placeholders = ",".join("?" * len(processing_states))

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT ms_path, current_state, previous_state, transition_time,
                       retry_count, error_message, checkpoint_data, created_at
                FROM ms_state
                WHERE current_state IN ({placeholders})
                ORDER BY transition_time DESC
                LIMIT ?
                """,
                (*processing_states, limit),
            )
            rows = cursor.fetchall()

        return [StateRecord.from_row(tuple(row)) for row in rows]

    def list_failed(self, limit: int = 100) -> List[StateRecord]:
        """List all MS files in FAILED state (eligible for retry).

        Args:
            limit: Maximum records to return

        Returns:
            List of StateRecord instances for failed MS files
        """
        return self.list_by_state(MSState.FAILED, limit=limit)

    def count_by_state(self) -> Dict[MSState, int]:
        """Count MS files in each state.

        Returns:
            Dictionary mapping MSState to count
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT current_state, COUNT(*) as count
                FROM ms_state
                GROUP BY current_state
                """
            )
            rows = cursor.fetchall()

        counts = {state: 0 for state in MSState}
        for row in rows:
            state = MSState(row["current_state"])
            counts[state] = row["count"]

        return counts

    # -------------------------------------------------------------------------
    # State Transitions
    # -------------------------------------------------------------------------

    def transition(
        self,
        ms_path: str,
        new_state: MSState,
        *,
        error_message: Optional[str] = None,
        checkpoint: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> TransitionResult:
        """Transition MS to a new state.

        Args:
            ms_path: Path to MS file
            new_state: Target state
            error_message: Error message (for FAILED/ERROR transitions)
            checkpoint: Checkpoint data for resume capability
            validate: If True, validate the transition is allowed

        Returns:
            TransitionResult with details of the transition

        Raises:
            StateTransitionError: If validate=True and transition is invalid
        """
        current = self.get_state(ms_path)
        now = time.time()

        # Validate transition
        if validate:
            valid_targets = self.TRANSITIONS.get(current, [])
            if new_state not in valid_targets:
                raise StateTransitionError(ms_path, current, new_state, valid_targets)

        # Serialize checkpoint
        checkpoint_json = json.dumps(checkpoint) if checkpoint else None

        with self._get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                # Check if record exists
                cursor = conn.execute(
                    "SELECT created_at FROM ms_state WHERE ms_path = ?",
                    (ms_path,),
                )
                existing = cursor.fetchone()

                if existing:
                    # Update existing record
                    conn.execute(
                        """
                        UPDATE ms_state SET
                            previous_state = current_state,
                            current_state = ?,
                            transition_time = ?,
                            error_message = ?,
                            checkpoint_data = COALESCE(?, checkpoint_data)
                        WHERE ms_path = ?
                        """,
                        (new_state.value, now, error_message, checkpoint_json, ms_path),
                    )
                else:
                    # Insert new record
                    conn.execute(
                        """
                        INSERT INTO ms_state
                        (ms_path, current_state, previous_state, transition_time,
                         retry_count, error_message, checkpoint_data, created_at)
                        VALUES (?, ?, ?, ?, 0, ?, ?, ?)
                        """,
                        (
                            ms_path,
                            new_state.value,
                            current.value,
                            now,
                            error_message,
                            checkpoint_json,
                            now,
                        ),
                    )

                conn.execute("COMMIT")

            except sqlite3.Error:
                conn.execute("ROLLBACK")
                raise

        logger.info(
            "State transition: %s: %s → %s",
            Path(ms_path).name,
            current.value,
            new_state.value,
        )

        return TransitionResult(
            success=True,
            ms_path=ms_path,
            old_state=current,
            new_state=new_state,
            timestamp=now,
        )

    def mark_failed(
        self,
        ms_path: str,
        error: Exception,
        checkpoint: Optional[Dict[str, Any]] = None,
    ) -> TransitionResult:
        """Mark MS as failed with error details.

        Args:
            ms_path: Path to MS file
            error: Exception that caused the failure
            checkpoint: Optional checkpoint data for resume

        Returns:
            TransitionResult
        """
        error_message = f"{type(error).__name__}: {error}"
        return self.transition(
            ms_path,
            MSState.FAILED,
            error_message=error_message,
            checkpoint=checkpoint,
        )

    def mark_done(self, ms_path: str) -> TransitionResult:
        """Mark MS as successfully completed.

        Args:
            ms_path: Path to MS file

        Returns:
            TransitionResult
        """
        return self.transition(ms_path, MSState.DONE)

    # -------------------------------------------------------------------------
    # Retry Logic
    # -------------------------------------------------------------------------

    def can_retry(self, ms_path: str, max_retries: Optional[int] = None) -> bool:
        """Check if MS can be retried.

        Args:
            ms_path: Path to MS file
            max_retries: Override default max_retries

        Returns:
            True if retry is allowed
        """
        max_allowed = max_retries if max_retries is not None else self.max_retries

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT retry_count, current_state FROM ms_state WHERE ms_path = ?",
                (ms_path,),
            )
            row = cursor.fetchone()

        if not row:
            return True  # New MS can always be started

        current_state = MSState(row["current_state"])
        retry_count = row["retry_count"]

        # Can't retry if already in ERROR state or if max retries exceeded
        return current_state != MSState.ERROR and retry_count < max_allowed

    def reset_for_retry(self, ms_path: str) -> TransitionResult:
        """Reset failed MS for retry.

        Increments retry count and transitions back to PENDING.

        Args:
            ms_path: Path to MS file

        Returns:
            TransitionResult

        Raises:
            StateTransitionError: If MS cannot be retried
        """
        if not self.can_retry(ms_path):
            record = self.get_record(ms_path)
            if record:
                raise StateTransitionError(
                    ms_path,
                    record.current_state,
                    MSState.PENDING,
                    [],  # No valid transitions
                )
            raise StateNotFoundError(ms_path)

        now = time.time()

        with self._get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                # Get current state for logging
                cursor = conn.execute(
                    "SELECT current_state, retry_count FROM ms_state WHERE ms_path = ?",
                    (ms_path,),
                )
                row = cursor.fetchone()

                if row:
                    old_state = MSState(row["current_state"])
                    new_retry_count = row["retry_count"] + 1

                    conn.execute(
                        """
                        UPDATE ms_state SET
                            previous_state = current_state,
                            current_state = ?,
                            transition_time = ?,
                            retry_count = ?,
                            error_message = NULL
                        WHERE ms_path = ?
                        """,
                        (MSState.PENDING.value, now, new_retry_count, ms_path),
                    )
                else:
                    old_state = MSState.PENDING
                    conn.execute(
                        """
                        INSERT INTO ms_state
                        (ms_path, current_state, previous_state, transition_time,
                         retry_count, error_message, checkpoint_data, created_at)
                        VALUES (?, ?, NULL, ?, 1, NULL, NULL, ?)
                        """,
                        (ms_path, MSState.PENDING.value, now, now),
                    )

                conn.execute("COMMIT")

            except sqlite3.Error:
                conn.execute("ROLLBACK")
                raise

        logger.info(
            "Reset for retry: %s: %s → PENDING (attempt %d)",
            Path(ms_path).name,
            old_state.value,
            new_retry_count if row else 1,
        )

        return TransitionResult(
            success=True,
            ms_path=ms_path,
            old_state=old_state,
            new_state=MSState.PENDING,
            timestamp=now,
        )

    def escalate_to_error(self, ms_path: str, reason: str) -> TransitionResult:
        """Escalate failed MS to permanent ERROR state.

        Args:
            ms_path: Path to MS file
            reason: Reason for escalation

        Returns:
            TransitionResult
        """
        return self.transition(
            ms_path,
            MSState.ERROR,
            error_message=f"Escalated to ERROR: {reason}",
        )

    # -------------------------------------------------------------------------
    # Checkpoint/Resume
    # -------------------------------------------------------------------------

    def save_checkpoint(
        self,
        ms_path: str,
        checkpoint: Dict[str, Any],
    ) -> None:
        """Save checkpoint data for an MS without changing state.

        Args:
            ms_path: Path to MS file
            checkpoint: Checkpoint data to save
        """
        checkpoint_json = json.dumps(checkpoint)

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE ms_state SET checkpoint_data = ?
                WHERE ms_path = ?
                """,
                (checkpoint_json, ms_path),
            )
            conn.commit()

        logger.debug("Saved checkpoint for %s", Path(ms_path).name)

    def get_checkpoint(self, ms_path: str) -> Optional[Dict[str, Any]]:
        """Get checkpoint data for an MS.

        Args:
            ms_path: Path to MS file

        Returns:
            Checkpoint dictionary, or None if no checkpoint
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT checkpoint_data FROM ms_state WHERE ms_path = ?",
                (ms_path,),
            )
            row = cursor.fetchone()

        if not row or not row["checkpoint_data"]:
            return None

        return json.loads(row["checkpoint_data"])

    def clear_checkpoint(self, ms_path: str) -> None:
        """Clear checkpoint data for an MS.

        Args:
            ms_path: Path to MS file
        """
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE ms_state SET checkpoint_data = NULL WHERE ms_path = ?",
                (ms_path,),
            )
            conn.commit()

    # -------------------------------------------------------------------------
    # Cleanup and Maintenance
    # -------------------------------------------------------------------------

    def cleanup_old_records(
        self,
        max_age_days: int = 30,
        terminal_only: bool = True,
    ) -> int:
        """Remove old state records.

        Args:
            max_age_days: Maximum age in days for records to keep
            terminal_only: If True, only remove DONE/ERROR records

        Returns:
            Number of records deleted
        """
        cutoff = time.time() - (max_age_days * 86400)

        if terminal_only:
            terminal_states = [MSState.DONE.value, MSState.ERROR.value]
            placeholders = ",".join("?" * len(terminal_states))
            query = f"""
                DELETE FROM ms_state
                WHERE transition_time < ? AND current_state IN ({placeholders})
            """
            params = (cutoff, *terminal_states)
        else:
            query = "DELETE FROM ms_state WHERE transition_time < ?"
            params = (cutoff,)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            logger.info("Cleaned up %d old state records", deleted)

        return deleted

    def reset_stale_processing(
        self,
        max_processing_hours: float = 24.0,
    ) -> List[str]:
        """Reset MS files stuck in processing states.

        If an MS has been in a processing state for too long (e.g., worker
        crashed), reset it to FAILED so it can be retried.

        Args:
            max_processing_hours: Maximum hours an MS can be in processing state

        Returns:
            List of MS paths that were reset
        """
        cutoff = time.time() - (max_processing_hours * 3600)
        processing_states = [s.value for s in MSState if s.is_processing()]
        placeholders = ",".join("?" * len(processing_states))

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT ms_path FROM ms_state
                WHERE current_state IN ({placeholders})
                AND transition_time < ?
                """,
                (*processing_states, cutoff),
            )
            stale_paths = [row["ms_path"] for row in cursor.fetchall()]

        reset_paths = []
        for ms_path in stale_paths:
            try:
                self.transition(
                    ms_path,
                    MSState.FAILED,
                    error_message=f"Stale processing state reset after {max_processing_hours}h",
                    validate=False,  # Force transition
                )
                reset_paths.append(ms_path)
            except (sqlite3.Error, StateTransitionError) as err:
                logger.warning("Failed to reset stale MS %s: %s", ms_path, err)

        if reset_paths:
            logger.warning(
                "Reset %d stale processing jobs: %s",
                len(reset_paths),
                [Path(p).name for p in reset_paths],
            )

        return reset_paths


# =============================================================================
# Context Manager for Pipeline Stages
# =============================================================================


@contextmanager
def state_transition_context(
    state_machine: MSStateMachine,
    ms_path: str,
    processing_state: MSState,
    success_state: MSState,
    checkpoint_callback: Optional[callable] = None,
) -> Generator[Dict[str, Any], None, None]:
    """Context manager for state-tracked processing.

    Automatically transitions to processing_state on entry, success_state
    on successful exit, and FAILED on exception.

    Args:
        state_machine: MSStateMachine instance
        ms_path: Path to MS being processed
        processing_state: State to enter during processing
        success_state: State to transition to on success
        checkpoint_callback: Optional callback to get checkpoint data on failure

    Yields:
        Context dict that can be used to store checkpoint data

    Example:
        sm = MSStateMachine()

        with state_transition_context(
            sm, ms_path,
            MSState.CONVERTING,
            MSState.CONVERTED
        ) as ctx:
            # Do conversion work
            ctx["rows_processed"] = 1000  # Store checkpoint data
            convert_uvh5_to_ms(input_path, ms_path)

        # If successful, MS is now in CONVERTED state
        # If exception raised, MS is in FAILED state with checkpoint
    """
    context: Dict[str, Any] = {}

    # Transition to processing state
    state_machine.transition(ms_path, processing_state)

    try:
        yield context

        # Success - transition to success state
        state_machine.transition(ms_path, success_state)

    except BaseException as exc:
        # Failure - get checkpoint data and transition to FAILED
        # Using BaseException to catch all exceptions including KeyboardInterrupt
        # so we can properly record state before re-raising
        checkpoint = context.copy()
        if checkpoint_callback:
            try:
                checkpoint.update(checkpoint_callback())
            except (TypeError, ValueError, RuntimeError):
                pass  # Don't fail on checkpoint collection

        state_machine.mark_failed(ms_path, exc, checkpoint=checkpoint)
        raise


# =============================================================================
# Convenience Functions
# =============================================================================


_default_state_machine: Optional[MSStateMachine] = None


def get_state_machine() -> MSStateMachine:
    """Get or create the default state machine instance.

    Returns:
        Singleton MSStateMachine instance
    """
    global _default_state_machine
    if _default_state_machine is None:
        _default_state_machine = MSStateMachine()
    return _default_state_machine


def close_state_machine() -> None:
    """Close the default state machine instance."""
    global _default_state_machine
    _default_state_machine = None
