"""
Unit tests for the MS processing state machine.

Tests cover:
- MSState enum properties
- StateRecord dataclass
- MSStateMachine state queries and transitions
- Retry logic
- Checkpoint/resume functionality
- Error handling
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Generator

import pytest

from dsa110_contimg.database.state_machine import (
    MSState,
    MSStateMachine,
    StateRecord,
    StateTransitionError,
    close_state_machine,
    get_state_machine,
    state_transition_context,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Create a temporary database path."""
    return str(tmp_path / "test_state_machine.sqlite3")


@pytest.fixture
def state_machine(temp_db_path: str) -> Generator[MSStateMachine, None, None]:
    """Create a state machine with temporary database."""
    state_mach = MSStateMachine(db_path=temp_db_path)
    yield state_mach
    # Cleanup - close any connections


@pytest.fixture
def sample_ms_path() -> str:
    """Sample MS path for testing."""
    return "/data/dsa110/ms/test_observation.ms"


# =============================================================================
# MSState Enum Tests
# =============================================================================


class TestMSState:
    """Tests for MSState enum."""

    def test_state_values(self):
        """Test all expected state values exist."""
        expected_states = [
            "pending",
            "converting",
            "converted",
            "flagging_rfi",
            "solving_cal",
            "applying_cal",
            "imaging",
            "done",
            "failed",
            "error",
        ]
        for state_value in expected_states:
            assert MSState(state_value) is not None

    def test_is_terminal_done(self):
        """Test DONE is terminal."""
        assert MSState.DONE.is_terminal() is True

    def test_is_terminal_error(self):
        """Test ERROR is terminal."""
        assert MSState.ERROR.is_terminal() is True

    def test_is_terminal_pending(self):
        """Test PENDING is not terminal."""
        assert MSState.PENDING.is_terminal() is False

    def test_is_processing_converting(self):
        """Test CONVERTING is a processing state."""
        assert MSState.CONVERTING.is_processing() is True

    def test_is_processing_imaging(self):
        """Test IMAGING is a processing state."""
        assert MSState.IMAGING.is_processing() is True

    def test_is_processing_pending(self):
        """Test PENDING is not a processing state."""
        assert MSState.PENDING.is_processing() is False

    def test_is_processing_done(self):
        """Test DONE is not a processing state."""
        assert MSState.DONE.is_processing() is False

    def test_is_recoverable_failed(self):
        """Test FAILED is recoverable."""
        assert MSState.FAILED.is_recoverable() is True

    def test_is_recoverable_pending(self):
        """Test PENDING is recoverable."""
        assert MSState.PENDING.is_recoverable() is True

    def test_is_recoverable_error(self):
        """Test ERROR is not recoverable."""
        assert MSState.ERROR.is_recoverable() is False


# =============================================================================
# StateRecord Tests
# =============================================================================


class TestStateRecord:
    """Tests for StateRecord dataclass."""

    def test_create_state_record(self):
        """Test creating a StateRecord."""
        record = StateRecord(
            ms_path="/path/to/file.ms",
            current_state=MSState.CONVERTING,
        )
        assert record.ms_path == "/path/to/file.ms"
        assert record.current_state == MSState.CONVERTING
        assert record.previous_state is None
        assert record.retry_count == 0
        assert record.checkpoint_data == {}

    def test_from_row(self):
        """Test creating StateRecord from database row."""
        now = time.time()
        row = (
            "/path/to/file.ms",
            "converting",
            "pending",
            now,
            2,
            "Some error",
            '{"step": 100}',
            now - 3600,
        )
        record = StateRecord.from_row(row)

        assert record.ms_path == "/path/to/file.ms"
        assert record.current_state == MSState.CONVERTING
        assert record.previous_state == MSState.PENDING
        assert record.transition_time == now
        assert record.retry_count == 2
        assert record.error_message == "Some error"
        assert record.checkpoint_data == {"step": 100}

    def test_from_row_null_values(self):
        """Test creating StateRecord with null values."""
        now = time.time()
        row = (
            "/path/to/file.ms",
            "pending",
            None,  # No previous state
            now,
            0,
            None,  # No error
            None,  # No checkpoint
            now,
        )
        record = StateRecord.from_row(row)

        assert record.previous_state is None
        assert record.error_message is None
        assert record.checkpoint_data == {}

    def test_to_dict(self):
        """Test converting StateRecord to dict."""
        record = StateRecord(
            ms_path="/path/to/file.ms",
            current_state=MSState.IMAGING,
            previous_state=MSState.APPLYING_CAL,
            transition_time=1000.0,
            retry_count=1,
        )
        d = record.to_dict()

        assert d["ms_path"] == "/path/to/file.ms"
        assert d["current_state"] == "imaging"
        assert d["previous_state"] == "applying_cal"
        assert d["retry_count"] == 1


# =============================================================================
# StateTransitionError Tests
# =============================================================================


class TestStateTransitionError:
    """Tests for StateTransitionError exception."""

    def test_error_message(self):
        """Test error message formatting."""
        error = StateTransitionError(
            ms_path="/path/to/file.ms",
            current_state=MSState.PENDING,
            requested_state=MSState.IMAGING,
            valid_transitions=[MSState.CONVERTING, MSState.FAILED],
        )

        assert "/path/to/file.ms" in str(error)
        assert "pending" in str(error)
        assert "imaging" in str(error)
        assert "converting, failed" in str(error)

    def test_error_with_no_valid_transitions(self):
        """Test error message when no valid transitions."""
        error = StateTransitionError(
            ms_path="/path/to/file.ms",
            current_state=MSState.DONE,
            requested_state=MSState.IMAGING,
            valid_transitions=[],
        )

        assert "none" in str(error)


# =============================================================================
# MSStateMachine Basic Tests
# =============================================================================


class TestMSStateMachineBasic:
    """Basic tests for MSStateMachine."""

    def test_create_state_machine(self, temp_db_path: str):
        """Test creating a state machine."""
        sm = MSStateMachine(db_path=temp_db_path)
        assert sm.db_path == temp_db_path
        assert sm.max_retries == 3

    def test_create_with_custom_max_retries(self, temp_db_path: str):
        """Test creating state machine with custom max_retries."""
        sm = MSStateMachine(db_path=temp_db_path, max_retries=5)
        assert sm.max_retries == 5

    def test_schema_created(self, temp_db_path: str):
        """Test that schema is created on initialization."""
        MSStateMachine(db_path=temp_db_path)

        # Check table exists
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ms_state'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_get_state_untracked(self, state_machine: MSStateMachine, sample_ms_path: str):
        """Test getting state for untracked MS returns PENDING."""
        state = state_machine.get_state(sample_ms_path)
        assert state == MSState.PENDING

    def test_is_tracked_false(self, state_machine: MSStateMachine, sample_ms_path: str):
        """Test is_tracked returns False for untracked MS."""
        assert state_machine.is_tracked(sample_ms_path) is False


# =============================================================================
# State Transition Tests
# =============================================================================


class TestStateTransitions:
    """Tests for state transitions."""

    def test_valid_transition_pending_to_converting(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test valid transition from PENDING to CONVERTING."""
        result = state_machine.transition(sample_ms_path, MSState.CONVERTING)

        assert result.success is True
        assert result.old_state == MSState.PENDING
        assert result.new_state == MSState.CONVERTING
        assert state_machine.get_state(sample_ms_path) == MSState.CONVERTING

    def test_valid_transition_chain(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test valid transition chain through pipeline."""
        # PENDING -> CONVERTING -> CONVERTED -> FLAGGING_RFI -> APPLYING_CAL -> IMAGING -> DONE
        transitions = [
            MSState.CONVERTING,
            MSState.CONVERTED,
            MSState.FLAGGING_RFI,
            MSState.APPLYING_CAL,
            MSState.IMAGING,
            MSState.DONE,
        ]

        for target_state in transitions:
            result = state_machine.transition(sample_ms_path, target_state)
            assert result.success is True
            assert result.new_state == target_state

        assert state_machine.get_state(sample_ms_path) == MSState.DONE

    def test_invalid_transition_raises(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test invalid transition raises StateTransitionError."""
        with pytest.raises(StateTransitionError) as exc_info:
            state_machine.transition(sample_ms_path, MSState.IMAGING)

        assert sample_ms_path in str(exc_info.value)
        assert "pending" in str(exc_info.value)
        assert "imaging" in str(exc_info.value)

    def test_transition_with_error_message(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test transition with error message."""
        state_machine.transition(sample_ms_path, MSState.FAILED, error_message="Test error")

        record = state_machine.get_record(sample_ms_path)
        assert record is not None
        assert record.error_message == "Test error"

    def test_transition_with_checkpoint(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test transition with checkpoint data."""
        checkpoint = {"step": 50, "rows_processed": 1000}
        state_machine.transition(
            sample_ms_path, MSState.CONVERTING, checkpoint=checkpoint
        )

        saved_checkpoint = state_machine.get_checkpoint(sample_ms_path)
        assert saved_checkpoint == checkpoint

    def test_transition_preserves_previous_state(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test that transition preserves previous state."""
        state_machine.transition(sample_ms_path, MSState.CONVERTING)
        state_machine.transition(sample_ms_path, MSState.CONVERTED)

        record = state_machine.get_record(sample_ms_path)
        assert record is not None
        assert record.previous_state == MSState.CONVERTING

    def test_transition_without_validation(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test forced transition bypasses validation."""
        # Force an invalid transition
        result = state_machine.transition(
            sample_ms_path, MSState.DONE, validate=False
        )

        assert result.success is True
        assert state_machine.get_state(sample_ms_path) == MSState.DONE


# =============================================================================
# Mark Failed/Done Tests
# =============================================================================


class TestMarkFailedDone:
    """Tests for mark_failed and mark_done methods."""

    def test_mark_failed(self, state_machine: MSStateMachine, sample_ms_path: str):
        """Test marking MS as failed."""
        state_machine.transition(sample_ms_path, MSState.CONVERTING)

        error = ValueError("Test conversion error")
        result = state_machine.mark_failed(sample_ms_path, error)

        assert result.success is True
        assert result.new_state == MSState.FAILED

        record = state_machine.get_record(sample_ms_path)
        assert record is not None
        assert "ValueError" in record.error_message
        assert "Test conversion error" in record.error_message

    def test_mark_failed_with_checkpoint(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test marking failed with checkpoint data."""
        state_machine.transition(sample_ms_path, MSState.CONVERTING)

        error = RuntimeError("Processing failed")
        checkpoint = {"last_row": 500}
        state_machine.mark_failed(sample_ms_path, error, checkpoint=checkpoint)

        saved_checkpoint = state_machine.get_checkpoint(sample_ms_path)
        assert saved_checkpoint == checkpoint

    def test_mark_done(self, state_machine: MSStateMachine, sample_ms_path: str):
        """Test marking MS as done."""
        # Go through valid transitions to IMAGING
        state_machine.transition(sample_ms_path, MSState.CONVERTING)
        state_machine.transition(sample_ms_path, MSState.CONVERTED)
        state_machine.transition(sample_ms_path, MSState.FLAGGING_RFI)
        state_machine.transition(sample_ms_path, MSState.APPLYING_CAL)
        state_machine.transition(sample_ms_path, MSState.IMAGING)

        result = state_machine.mark_done(sample_ms_path)

        assert result.success is True
        assert result.new_state == MSState.DONE
        assert state_machine.get_state(sample_ms_path) == MSState.DONE


# =============================================================================
# Retry Logic Tests
# =============================================================================


class TestRetryLogic:
    """Tests for retry functionality."""

    def test_can_retry_failed_state(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test can_retry returns True for failed MS."""
        state_machine.transition(sample_ms_path, MSState.FAILED)
        assert state_machine.can_retry(sample_ms_path) is True

    def test_can_retry_new_ms(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test can_retry returns True for new MS."""
        assert state_machine.can_retry(sample_ms_path) is True

    def test_cannot_retry_error_state(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test can_retry returns False for ERROR state."""
        state_machine.transition(sample_ms_path, MSState.FAILED)
        state_machine.transition(sample_ms_path, MSState.ERROR)
        assert state_machine.can_retry(sample_ms_path) is False

    def test_reset_for_retry(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test reset_for_retry resets state and increments counter."""
        state_machine.transition(sample_ms_path, MSState.CONVERTING)
        state_machine.transition(sample_ms_path, MSState.FAILED)

        result = state_machine.reset_for_retry(sample_ms_path)

        assert result.success is True
        assert result.new_state == MSState.PENDING

        record = state_machine.get_record(sample_ms_path)
        assert record is not None
        assert record.retry_count == 1
        assert record.error_message is None

    def test_reset_for_retry_multiple(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test multiple retry resets increment counter."""
        state_mach = MSStateMachine(db_path=state_machine.db_path, max_retries=5)

        for _ in range(3):
            state_mach.transition(sample_ms_path, MSState.CONVERTING)
            state_mach.transition(sample_ms_path, MSState.FAILED)
            state_mach.reset_for_retry(sample_ms_path)

        record = state_mach.get_record(sample_ms_path)
        assert record is not None
        assert record.retry_count == 3

    def test_cannot_retry_after_max_retries(self, temp_db_path: str, sample_ms_path: str):
        """Test can_retry returns False after max retries exceeded."""
        state_mach = MSStateMachine(db_path=temp_db_path, max_retries=2)

        # Do 2 retries (max)
        for _ in range(2):
            state_mach.transition(sample_ms_path, MSState.CONVERTING)
            state_mach.transition(sample_ms_path, MSState.FAILED)
            state_mach.reset_for_retry(sample_ms_path)

        # Third failure
        state_mach.transition(sample_ms_path, MSState.CONVERTING)
        state_mach.transition(sample_ms_path, MSState.FAILED)

        assert state_mach.can_retry(sample_ms_path) is False

    def test_escalate_to_error(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test escalating to ERROR state."""
        state_machine.transition(sample_ms_path, MSState.FAILED)

        result = state_machine.escalate_to_error(sample_ms_path, "Max retries exceeded")

        assert result.success is True
        assert result.new_state == MSState.ERROR
        assert state_machine.can_retry(sample_ms_path) is False


# =============================================================================
# Checkpoint Tests
# =============================================================================


class TestCheckpoints:
    """Tests for checkpoint functionality."""

    def test_save_checkpoint(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test saving checkpoint data."""
        state_machine.transition(sample_ms_path, MSState.CONVERTING)

        checkpoint = {"row": 500, "phase": "visibility"}
        state_machine.save_checkpoint(sample_ms_path, checkpoint)

        saved = state_machine.get_checkpoint(sample_ms_path)
        assert saved == checkpoint

    def test_get_checkpoint_none(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test getting checkpoint when none exists."""
        state_machine.transition(sample_ms_path, MSState.CONVERTING)
        assert state_machine.get_checkpoint(sample_ms_path) is None

    def test_clear_checkpoint(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test clearing checkpoint data."""
        state_machine.transition(
            sample_ms_path, MSState.CONVERTING, checkpoint={"step": 1}
        )
        state_machine.clear_checkpoint(sample_ms_path)

        assert state_machine.get_checkpoint(sample_ms_path) is None


# =============================================================================
# List and Query Tests
# =============================================================================


class TestListQueries:
    """Tests for list and query methods."""

    def test_list_by_state(self, state_machine: MSStateMachine):
        """Test listing MS by state."""
        # Create MS in different states
        state_machine.transition("/path/1.ms", MSState.CONVERTING)
        state_machine.transition("/path/2.ms", MSState.CONVERTING)
        state_machine.transition("/path/3.ms", MSState.FAILED)

        converting = state_machine.list_by_state(MSState.CONVERTING)
        assert len(converting) == 2

        failed = state_machine.list_by_state(MSState.FAILED)
        assert len(failed) == 1

    def test_list_processing(self, state_machine: MSStateMachine):
        """Test listing processing MS."""
        state_machine.transition("/path/1.ms", MSState.CONVERTING)
        state_machine.transition("/path/2.ms", MSState.FAILED)
        state_machine.transition("/path/3.ms", MSState.CONVERTING)
        state_machine.transition("/path/3.ms", MSState.CONVERTED)
        state_machine.transition("/path/3.ms", MSState.FLAGGING_RFI)

        processing = state_machine.list_processing()
        assert len(processing) == 2  # CONVERTING and FLAGGING_RFI

    def test_list_failed(self, state_machine: MSStateMachine):
        """Test listing failed MS."""
        state_machine.transition("/path/1.ms", MSState.FAILED)
        state_machine.transition("/path/2.ms", MSState.FAILED)
        state_machine.transition("/path/3.ms", MSState.CONVERTING)

        failed = state_machine.list_failed()
        assert len(failed) == 2

    def test_count_by_state(self, state_machine: MSStateMachine):
        """Test counting MS by state."""
        state_machine.transition("/path/1.ms", MSState.CONVERTING)
        state_machine.transition("/path/2.ms", MSState.CONVERTING)
        state_machine.transition("/path/3.ms", MSState.FAILED)

        counts = state_machine.count_by_state()

        assert counts[MSState.CONVERTING] == 2
        assert counts[MSState.FAILED] == 1
        assert counts[MSState.DONE] == 0

    def test_get_record(self, state_machine: MSStateMachine, sample_ms_path: str):
        """Test getting full state record."""
        state_machine.transition(sample_ms_path, MSState.CONVERTING)

        record = state_machine.get_record(sample_ms_path)

        assert record is not None
        assert record.ms_path == sample_ms_path
        assert record.current_state == MSState.CONVERTING
        assert record.transition_time > 0

    def test_get_record_not_found(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test getting record for untracked MS returns None."""
        record = state_machine.get_record(sample_ms_path)
        assert record is None


# =============================================================================
# Cleanup Tests
# =============================================================================


class TestCleanup:
    """Tests for cleanup functionality."""

    def test_cleanup_old_records(self, state_machine: MSStateMachine):
        """Test cleaning up old terminal state records."""
        # Create some records
        state_machine.transition("/path/1.ms", MSState.CONVERTING)
        state_machine.transition("/path/1.ms", MSState.CONVERTED)
        state_machine.transition("/path/1.ms", MSState.FLAGGING_RFI)
        state_machine.transition("/path/1.ms", MSState.APPLYING_CAL)
        state_machine.transition("/path/1.ms", MSState.IMAGING)
        state_machine.transition("/path/1.ms", MSState.DONE)

        state_machine.transition("/path/2.ms", MSState.CONVERTING)  # Not terminal

        # Manually update transition_time to be old
        conn = sqlite3.connect(state_machine.db_path)
        old_time = time.time() - (40 * 86400)  # 40 days ago
        conn.execute(
            "UPDATE ms_state SET transition_time = ? WHERE ms_path = ?",
            (old_time, "/path/1.ms"),
        )
        conn.commit()
        conn.close()

        deleted = state_machine.cleanup_old_records(max_age_days=30)

        assert deleted == 1
        assert state_machine.get_record("/path/1.ms") is None
        assert state_machine.get_record("/path/2.ms") is not None

    def test_reset_stale_processing(self, state_machine: MSStateMachine):
        """Test resetting stale processing jobs."""
        state_machine.transition("/path/1.ms", MSState.CONVERTING)
        state_machine.transition("/path/2.ms", MSState.CONVERTING)

        # Make one stale
        conn = sqlite3.connect(state_machine.db_path)
        old_time = time.time() - (30 * 3600)  # 30 hours ago
        conn.execute(
            "UPDATE ms_state SET transition_time = ? WHERE ms_path = ?",
            (old_time, "/path/1.ms"),
        )
        conn.commit()
        conn.close()

        reset = state_machine.reset_stale_processing(max_processing_hours=24.0)

        assert len(reset) == 1
        assert "/path/1.ms" in reset
        assert state_machine.get_state("/path/1.ms") == MSState.FAILED
        assert state_machine.get_state("/path/2.ms") == MSState.CONVERTING


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestStateTransitionContext:
    """Tests for state_transition_context context manager."""

    def test_successful_context(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test successful context manager execution."""
        with state_transition_context(
            state_machine,
            sample_ms_path,
            MSState.CONVERTING,
            MSState.CONVERTED,
        ):
            # Verify we're in CONVERTING during processing
            assert state_machine.get_state(sample_ms_path) == MSState.CONVERTING

        # Verify we're in CONVERTED after success
        assert state_machine.get_state(sample_ms_path) == MSState.CONVERTED

    def test_failed_context(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test context manager on failure."""
        with pytest.raises(ValueError):
            with state_transition_context(
                state_machine,
                sample_ms_path,
                MSState.CONVERTING,
                MSState.CONVERTED,
            ):
                raise ValueError("Test error")

        # Verify we're in FAILED after exception
        assert state_machine.get_state(sample_ms_path) == MSState.FAILED

    def test_context_with_checkpoint_callback(
        self, state_machine: MSStateMachine, sample_ms_path: str
    ):
        """Test context manager with checkpoint callback on failure."""

        def checkpoint_cb():
            return {"extra_info": "from callback"}

        with pytest.raises(ValueError):
            with state_transition_context(
                state_machine,
                sample_ms_path,
                MSState.CONVERTING,
                MSState.CONVERTED,
                checkpoint_callback=checkpoint_cb,
            ) as ctx:
                ctx["step"] = 50
                raise ValueError("Test error")

        checkpoint = state_machine.get_checkpoint(sample_ms_path)
        assert checkpoint is not None
        assert checkpoint["step"] == 50
        assert checkpoint["extra_info"] == "from callback"


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Tests for singleton functions."""

    def test_get_state_machine_singleton(self):
        """Test get_state_machine returns singleton."""
        close_state_machine()  # Ensure clean state

        sm1 = get_state_machine()
        sm2 = get_state_machine()

        assert sm1 is sm2

        close_state_machine()

    def test_close_state_machine(self):
        """Test close_state_machine clears singleton."""
        close_state_machine()

        sm1 = get_state_machine()
        close_state_machine()
        sm2 = get_state_machine()

        # After close, a new instance should be created
        assert sm1 is not sm2

        close_state_machine()
