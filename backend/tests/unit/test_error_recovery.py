"""
Unit tests for error recovery module.

Tests:
- RetryPolicy configuration and backoff calculation
- ErrorRecoveryManager retry logic
- DeadLetterQueue operations
- CheckpointManager persistence
- Decorators (@with_retry, @with_retry_sync)
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dsa110_contimg.pipeline.error_recovery import (
    AGGRESSIVE_RETRY_POLICY,
    QUICK_RETRY_POLICY,
    STANDARD_RETRY_POLICY,
    BackoffStrategy,
    Checkpoint,
    CheckpointManager,
    DeadLetterEntry,
    DeadLetterQueue,
    DeadLetterReason,
    ErrorRecoveryManager,
    RetryAttempt,
    RetryOutcome,
    RetryPolicy,
    RetryResult,
    execute_with_retry_sync,
    with_retry,
    with_retry_sync,
)


# =============================================================================
# RetryPolicy Tests
# =============================================================================


class TestRetryPolicy:
    """Tests for RetryPolicy configuration."""

    def test_default_policy(self):
        """Test default policy values."""
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.backoff_strategy == BackoffStrategy.EXPONENTIAL
        assert policy.backoff_factor == 2.0
        assert policy.jitter == 0.1

    def test_custom_policy(self):
        """Test custom policy configuration."""
        policy = RetryPolicy(
            max_retries=5,
            base_delay=0.5,
            max_delay=120.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            backoff_factor=1.5,
            jitter=0.2,
        )
        assert policy.max_retries == 5
        assert policy.base_delay == 0.5
        assert policy.max_delay == 120.0
        assert policy.backoff_strategy == BackoffStrategy.LINEAR

    def test_predefined_policies(self):
        """Test predefined policy configurations."""
        assert QUICK_RETRY_POLICY.max_retries == 2
        assert QUICK_RETRY_POLICY.max_delay == 5.0

        assert STANDARD_RETRY_POLICY.max_retries == 3
        assert STANDARD_RETRY_POLICY.max_delay == 60.0

        assert AGGRESSIVE_RETRY_POLICY.max_retries == 5
        assert AGGRESSIVE_RETRY_POLICY.max_delay == 300.0


class TestBackoffCalculation:
    """Tests for backoff delay calculation."""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        policy = RetryPolicy(
            base_delay=1.0,
            backoff_factor=2.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            jitter=0.0,  # Disable jitter for predictable test
        )

        assert policy.calculate_delay(0) == 1.0  # 1 * 2^0
        assert policy.calculate_delay(1) == 2.0  # 1 * 2^1
        assert policy.calculate_delay(2) == 4.0  # 1 * 2^2
        assert policy.calculate_delay(3) == 8.0  # 1 * 2^3

    def test_linear_backoff(self):
        """Test linear backoff calculation."""
        policy = RetryPolicy(
            base_delay=1.0,
            backoff_factor=2.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            jitter=0.0,
        )

        assert policy.calculate_delay(0) == 1.0  # 1 * (1 + 0*2)
        assert policy.calculate_delay(1) == 3.0  # 1 * (1 + 1*2)
        assert policy.calculate_delay(2) == 5.0  # 1 * (1 + 2*2)

    def test_constant_backoff(self):
        """Test constant backoff calculation."""
        policy = RetryPolicy(
            base_delay=2.0,
            backoff_strategy=BackoffStrategy.CONSTANT,
            jitter=0.0,
        )

        assert policy.calculate_delay(0) == 2.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(5) == 2.0

    def test_fibonacci_backoff(self):
        """Test Fibonacci backoff calculation."""
        policy = RetryPolicy(
            base_delay=1.0,
            backoff_strategy=BackoffStrategy.FIBONACCI,
            jitter=0.0,
        )

        # Fibonacci: 1, 1, 2, 3, 5, 8, 13...
        # fib(n+2) for attempt n: fib(2)=1, fib(3)=2, fib(4)=3
        assert policy.calculate_delay(0) == 1.0  # fib(2)
        assert policy.calculate_delay(1) == 2.0  # fib(3)
        assert policy.calculate_delay(2) == 3.0  # fib(4)
        assert policy.calculate_delay(3) == 5.0  # fib(5)

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        policy = RetryPolicy(
            base_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            jitter=0.0,
        )

        # 2^10 = 1024, should be capped at 10
        assert policy.calculate_delay(10) == 10.0

    def test_jitter_applied(self):
        """Test that jitter adds randomness to delay."""
        policy = RetryPolicy(
            base_delay=10.0,
            backoff_strategy=BackoffStrategy.CONSTANT,
            jitter=0.5,  # 50% jitter
        )

        delays = [policy.calculate_delay(0) for _ in range(10)]
        # With 50% jitter on base 10, delays should be in range [5, 15]
        assert all(5.0 <= d <= 15.0 for d in delays)
        # Should have some variation
        assert len(set(round(d, 1) for d in delays)) > 1


# =============================================================================
# RetryResult Tests
# =============================================================================


class TestRetryResult:
    """Tests for RetryResult data class."""

    def test_successful_result(self):
        """Test successful result properties."""
        result = RetryResult(
            success=True,
            result="test_value",
            attempts=[
                RetryAttempt(
                    attempt_number=1,
                    started_at=100.0,
                    ended_at=101.0,
                    success=True,
                )
            ],
            total_duration=1.0,
        )

        assert result.success
        assert result.outcome == RetryOutcome.SUCCESS
        assert result.attempt_count == 1
        assert result.result == "test_value"

    def test_exhausted_result(self):
        """Test exhausted retries result."""
        result = RetryResult(
            success=False,
            attempts=[
                RetryAttempt(1, 100.0, 101.0, False, "error1"),
                RetryAttempt(2, 102.0, 103.0, False, "error2"),
                RetryAttempt(3, 104.0, 105.0, False, "error3"),
            ],
            final_error="error3",
            final_error_type="RuntimeError",
            total_duration=5.0,
        )

        assert not result.success
        assert result.outcome == RetryOutcome.EXHAUSTED
        assert result.attempt_count == 3
        assert result.final_error == "error3"

    def test_non_retryable_result(self):
        """Test non-retryable error result."""
        result = RetryResult(
            success=False,
            attempts=[RetryAttempt(1, 100.0, 101.0, False, "error")],
            final_error="error",
            final_error_type="non_retryable_TypeError",
        )

        assert result.outcome == RetryOutcome.NON_RETRYABLE

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = RetryResult(
            success=True,
            result="value",
            attempts=[RetryAttempt(1, 100.0, 101.0, True)],
            total_duration=1.0,
        )

        d = result.to_dict()
        assert d["success"] is True
        assert d["outcome"] == "success"
        assert d["attempt_count"] == 1
        assert len(d["attempts"]) == 1


# =============================================================================
# ErrorRecoveryManager Tests
# =============================================================================


class TestErrorRecoveryManager:
    """Tests for ErrorRecoveryManager."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test successful execution on first attempt."""
        manager = ErrorRecoveryManager()

        async def success_func():
            return "result"

        result = await manager.execute_with_retry(success_func)

        assert result.success
        assert result.result == "result"
        assert result.attempt_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry after initial failure."""
        policy = RetryPolicy(max_retries=3, base_delay=0.01, jitter=0)
        manager = ErrorRecoveryManager(policy)

        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError(f"Failure {call_count}")
            return "success"

        result = await manager.execute_with_retry(fail_then_succeed)

        assert result.success
        assert result.result == "success"
        assert result.attempt_count == 3
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Test all retries exhausted."""
        policy = RetryPolicy(max_retries=2, base_delay=0.01, jitter=0)
        manager = ErrorRecoveryManager(policy)

        async def always_fail():
            raise RuntimeError("Always fails")

        result = await manager.execute_with_retry(always_fail)

        assert not result.success
        assert result.attempt_count == 3  # 1 initial + 2 retries
        assert "Always fails" in result.final_error

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test that non-retryable exceptions stop immediately."""
        policy = RetryPolicy(
            max_retries=5,
            base_delay=0.01,
            retryable_exceptions=(RuntimeError,),  # Only RuntimeError is retryable
        )
        manager = ErrorRecoveryManager(policy)

        async def raise_type_error():
            raise TypeError("Not retryable")

        result = await manager.execute_with_retry(raise_type_error)

        assert not result.success
        assert result.attempt_count == 1  # Should stop after first attempt
        assert "non_retryable" in result.final_error_type

    @pytest.mark.asyncio
    async def test_alert_callback_on_failure(self):
        """Test alert callback is called on exhausted retries."""
        alert_mock = AsyncMock()
        policy = RetryPolicy(max_retries=1, base_delay=0.01, jitter=0)
        manager = ErrorRecoveryManager(policy, alert_callback=alert_mock)

        async def fail():
            raise RuntimeError("Test error")

        await manager.execute_with_retry(fail, operation_name="test_op")

        alert_mock.assert_called_once()
        call_args = alert_mock.call_args[0]
        assert "critical" in call_args[0] or "warning" in call_args[0]
        assert "test_op" in call_args[1]

    @pytest.mark.asyncio
    async def test_metrics_callback(self):
        """Test metrics callback is called."""
        metrics_mock = MagicMock()
        manager = ErrorRecoveryManager(metrics_callback=metrics_mock)

        async def success():
            return "ok"

        await manager.execute_with_retry(success, operation_name="test_op")

        metrics_mock.assert_called_once()
        call_args = metrics_mock.call_args[0]
        assert call_args[0] == "test_op"
        assert isinstance(call_args[1], RetryResult)


class TestSyncRetry:
    """Tests for synchronous retry function."""

    def test_sync_retry_success(self):
        """Test sync retry with success."""

        def success_func():
            return "result"

        result = execute_with_retry_sync(success_func)
        assert result.success
        assert result.result == "result"

    def test_sync_retry_with_retries(self):
        """Test sync retry with failures then success."""
        policy = RetryPolicy(max_retries=3, base_delay=0.01, jitter=0)
        call_count = 0

        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Fail")
            return "ok"

        result = execute_with_retry_sync(fail_twice, policy=policy)
        assert result.success
        assert result.attempt_count == 3


# =============================================================================
# Decorator Tests
# =============================================================================


class TestRetryDecorators:
    """Tests for retry decorators."""

    @pytest.mark.asyncio
    async def test_with_retry_success(self):
        """Test @with_retry decorator with success."""

        @with_retry(max_retries=2, base_delay=0.01)
        async def decorated():
            return "success"

        result = await decorated()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_with_retry_raises_after_exhaustion(self):
        """Test @with_retry raises RuntimeError after exhaustion."""

        @with_retry(max_retries=1, base_delay=0.01)
        async def always_fail():
            raise ValueError("Fail")

        with pytest.raises(RuntimeError, match="All .* attempts failed"):
            await always_fail()

    def test_with_retry_sync_success(self):
        """Test @with_retry_sync decorator."""

        @with_retry_sync(max_retries=2, base_delay=0.01)
        def decorated():
            return "sync_result"

        result = decorated()
        assert result == "sync_result"


# =============================================================================
# DeadLetterQueue Tests
# =============================================================================


class TestDeadLetterQueue:
    """Tests for DeadLetterQueue."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database for testing."""
        return str(tmp_path / "test_dlq.db")

    @pytest.mark.asyncio
    async def test_add_entry(self, temp_db):
        """Test adding entry to DLQ."""
        dlq = DeadLetterQueue(db_path=temp_db)

        entry_id = await dlq.add(
            ms_path="/data/test.ms",
            reason=DeadLetterReason.RETRIES_EXHAUSTED,
            error_message="Test error",
            error_type="RuntimeError",
            attempt_count=3,
        )

        assert entry_id > 0

    @pytest.mark.asyncio
    async def test_get_unresolved(self, temp_db):
        """Test retrieving unresolved entries."""
        dlq = DeadLetterQueue(db_path=temp_db)

        await dlq.add(
            ms_path="/data/test1.ms",
            reason=DeadLetterReason.RETRIES_EXHAUSTED,
            error_message="Error 1",
        )
        await dlq.add(
            ms_path="/data/test2.ms",
            reason=DeadLetterReason.NON_RETRYABLE_ERROR,
            error_message="Error 2",
        )

        entries = dlq.get_unresolved()
        assert len(entries) == 2
        assert all(isinstance(e, DeadLetterEntry) for e in entries)

    @pytest.mark.asyncio
    async def test_filter_by_reason(self, temp_db):
        """Test filtering by reason."""
        dlq = DeadLetterQueue(db_path=temp_db)

        await dlq.add("/data/a.ms", DeadLetterReason.RETRIES_EXHAUSTED, "err")
        await dlq.add("/data/b.ms", DeadLetterReason.TIMEOUT, "err")

        entries = dlq.get_unresolved(reason=DeadLetterReason.TIMEOUT)
        assert len(entries) == 1
        assert entries[0].reason == DeadLetterReason.TIMEOUT

    @pytest.mark.asyncio
    async def test_resolve_entry(self, temp_db):
        """Test resolving a DLQ entry."""
        dlq = DeadLetterQueue(db_path=temp_db)

        entry_id = await dlq.add(
            ms_path="/data/test.ms",
            reason=DeadLetterReason.RETRIES_EXHAUSTED,
            error_message="Test error",
        )

        success = dlq.resolve(entry_id, resolved_by="test_user", resolution_notes="Fixed")
        assert success

        entries = dlq.get_unresolved()
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, temp_db):
        """Test getting DLQ statistics."""
        dlq = DeadLetterQueue(db_path=temp_db)

        await dlq.add("/data/a.ms", DeadLetterReason.RETRIES_EXHAUSTED, "err")
        await dlq.add("/data/b.ms", DeadLetterReason.RETRIES_EXHAUSTED, "err")
        await dlq.add("/data/c.ms", DeadLetterReason.TIMEOUT, "err")

        stats = dlq.get_stats()
        assert stats["unresolved_count"] == 3
        assert stats["by_reason"]["retries_exhausted"] == 2
        assert stats["by_reason"]["timeout"] == 1

    @pytest.mark.asyncio
    async def test_requeue(self, temp_db):
        """Test requeue functionality."""
        dlq = DeadLetterQueue(db_path=temp_db)

        entry_id = await dlq.add(
            ms_path="/data/test.ms",
            reason=DeadLetterReason.RETRIES_EXHAUSTED,
            error_message="Error",
            checkpoint_data={"step": 5, "progress": 0.5},
            metadata={"source": "test"},
        )

        requeue_data = dlq.requeue(entry_id)
        assert requeue_data is not None
        assert requeue_data["ms_path"] == "/data/test.ms"
        assert requeue_data["checkpoint_data"]["step"] == 5

    @pytest.mark.asyncio
    async def test_alert_callback_on_add(self, temp_db):
        """Test alert callback when adding to DLQ."""
        alert_mock = AsyncMock()
        dlq = DeadLetterQueue(db_path=temp_db, alert_callback=alert_mock)

        await dlq.add(
            ms_path="/data/test.ms",
            reason=DeadLetterReason.RETRIES_EXHAUSTED,
            error_message="Critical error",
        )

        alert_mock.assert_called_once()


# =============================================================================
# Checkpoint Tests
# =============================================================================


class TestCheckpoint:
    """Tests for Checkpoint data class."""

    def test_checkpoint_creation(self):
        """Test checkpoint creation."""
        cp = Checkpoint(
            ms_path="/data/test.ms",
            stage="imaging",
            progress=0.5,
            data={"rows_processed": 1000},
        )

        assert cp.ms_path == "/data/test.ms"
        assert cp.stage == "imaging"
        assert cp.progress == 0.5
        assert cp.data["rows_processed"] == 1000

    def test_to_dict_from_dict(self):
        """Test checkpoint serialization."""
        cp = Checkpoint(
            ms_path="/data/test.ms",
            stage="calibration",
            progress=0.75,
            data={"gains_solved": True},
        )

        d = cp.to_dict()
        restored = Checkpoint.from_dict(d)

        assert restored.ms_path == cp.ms_path
        assert restored.stage == cp.stage
        assert restored.progress == cp.progress
        assert restored.data == cp.data


class TestCheckpointManager:
    """Tests for CheckpointManager."""

    def test_save_and_load_without_state_machine(self):
        """Test manager without state machine (no-op)."""
        manager = CheckpointManager()

        cp = Checkpoint("/data/test.ms", "imaging", 0.5)
        manager.save(cp)  # Should not raise

        loaded = manager.load("/data/test.ms")
        assert loaded is None  # No persistence

    def test_checkpoint_context_success(self):
        """Test checkpoint context manager on success."""
        manager = CheckpointManager()

        with manager.checkpoint_context("/data/test.ms", "imaging") as ctx:
            ctx.data["processed"] = True
            # Success path - no exception

    def test_checkpoint_context_failure(self):
        """Test checkpoint context manager on failure."""
        manager = CheckpointManager()

        with pytest.raises(ValueError):
            with manager.checkpoint_context("/data/test.ms", "imaging") as ctx:
                ctx.data["step"] = 5
                raise ValueError("Processing failed")


# =============================================================================
# DeadLetterEntry Tests
# =============================================================================


class TestDeadLetterEntry:
    """Tests for DeadLetterEntry data class."""

    def test_to_dict(self):
        """Test serialization."""
        entry = DeadLetterEntry(
            id=1,
            ms_path="/data/test.ms",
            reason=DeadLetterReason.RETRIES_EXHAUSTED,
            error_message="Error",
            error_type="RuntimeError",
            attempt_count=3,
            last_attempt_at=time.time(),
            created_at=time.time(),
            checkpoint_data={"step": 5},
            metadata={"source": "test"},
        )

        d = entry.to_dict()
        assert d["id"] == 1
        assert d["reason"] == "retries_exhausted"
        assert d["checkpoint_data"]["step"] == 5
