"""Task Scheduling Module for Absurd Workflow Manager.

This module provides cron-like scheduling capabilities for recurring tasks.
Scheduled tasks are stored in a dedicated table and processed by a scheduler
daemon that spawns actual tasks when their schedule triggers.

Features:
- Cron expression support (minute, hour, day, month, weekday)
- Timezone-aware scheduling
- Enable/disable schedules without deletion
- Last run tracking and next run calculation
- Integration with existing Absurd task spawning
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import asyncpg
except ImportError:
    asyncpg = None

logger = logging.getLogger(__name__)


class ScheduleState(str, Enum):
    """Scheduled task states."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass
class ScheduledTask:
    """Represents a scheduled task definition."""

    schedule_id: str
    name: str
    queue_name: str
    task_name: str
    cron_expression: str
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout_sec: Optional[int] = None
    max_retries: int = 3
    state: ScheduleState = ScheduleState.ACTIVE
    timezone: str = "UTC"
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    description: Optional[str] = None


def parse_cron_field(field_value: str, min_val: int, max_val: int) -> List[int]:
    """Parse a single cron field into a list of valid values.

    Supports:
    - * (any value)
    - */n (every n values)
    - n (specific value)
    - n-m (range)
    - n,m,o (list)
    """
    if field_value == "*":
        return list(range(min_val, max_val + 1))

    values = set()

    for part in field_value.split(","):
        part = part.strip()

        if "/" in part:
            # Step value (*/5 or 1-30/5)
            base, step = part.split("/")
            step = int(step)

            if base == "*":
                start, end = min_val, max_val
            elif "-" in base:
                start, end = map(int, base.split("-"))
            else:
                start = int(base)
                end = max_val

            for v in range(start, end + 1, step):
                if min_val <= v <= max_val:
                    values.add(v)

        elif "-" in part:
            # Range (1-5)
            start, end = map(int, part.split("-"))
            for v in range(start, end + 1):
                if min_val <= v <= max_val:
                    values.add(v)

        else:
            # Single value
            v = int(part)
            if min_val <= v <= max_val:
                values.add(v)

    return sorted(values)


def parse_cron_expression(expression: str) -> Dict[str, List[int]]:
    """Parse a cron expression into component fields.

    Format: minute hour day_of_month month day_of_week

    Example: "0 */2 * * 1-5" = every 2 hours on weekdays

    Returns dict with keys: minute, hour, day, month, weekday
    """
    parts = expression.strip().split()

    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: expected 5 fields, got {len(parts)}")

    return {
        "minute": parse_cron_field(parts[0], 0, 59),
        "hour": parse_cron_field(parts[1], 0, 23),
        "day": parse_cron_field(parts[2], 1, 31),
        "month": parse_cron_field(parts[3], 1, 12),
        "weekday": parse_cron_field(parts[4], 0, 6),  # 0=Sunday
    }


def calculate_next_run(cron_expression: str, from_time: Optional[datetime] = None) -> datetime:
    """Calculate the next run time for a cron expression.

    Args:
        cron_expression: Standard 5-field cron expression
        from_time: Starting point for calculation (default: now)

    Returns:
        Next datetime when the schedule should trigger
    """
    if from_time is None:
        from_time = datetime.utcnow()

    fields = parse_cron_expression(cron_expression)

    # Start from the next minute
    current = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)

    # Search up to 2 years ahead
    max_iterations = 525600  # minutes in a year * 2

    for _ in range(max_iterations):
        # Check if current time matches all fields
        if (
            current.minute in fields["minute"]
            and current.hour in fields["hour"]
            and current.day in fields["day"]
            and current.month in fields["month"]
            and current.weekday() in fields["weekday"]
        ):
            return current

        # Advance by one minute
        current += timedelta(minutes=1)

    raise ValueError(f"Could not find next run time within 2 years for: {cron_expression}")


class TaskScheduler:
    """Scheduler daemon for managing and triggering scheduled tasks.

    The scheduler:
    1. Periodically checks for schedules whose next_run_at has passed
    2. Spawns actual tasks for triggered schedules
    3. Updates last_run_at and calculates next_run_at
    4. Handles errors gracefully without stopping the scheduler
    """

    def __init__(
        self,
        pool: Optional["asyncpg.Pool"] = None,
        check_interval: float = 60.0,  # Check every minute
    ):
        """Initialize the scheduler.

        Args:
            pool: PostgreSQL connection pool
            check_interval: Seconds between schedule checks
        """
        self.pool = pool
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the scheduler daemon."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Task scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler daemon."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Task scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._process_due_schedules()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")

            await asyncio.sleep(self.check_interval)

    async def _process_due_schedules(self) -> None:
        """Find and process all schedules that are due to run."""
        if not self.pool:
            return

        now = datetime.utcnow()

        async with self.pool.acquire() as conn:
            # Find all active schedules where next_run_at <= now
            due_schedules = await conn.fetch(
                """
                SELECT 
                    schedule_id, name, queue_name, task_name,
                    cron_expression, params, priority, timeout_sec,
                    max_retries, timezone
                FROM absurd.scheduled_tasks
                WHERE state = 'active'
                  AND next_run_at <= $1
                ORDER BY next_run_at
            """,
                now,
            )

            for schedule in due_schedules:
                try:
                    # Spawn the actual task
                    task_id = await conn.fetchval(
                        """
                        SELECT absurd.spawn_task(
                            $1::TEXT,
                            $2::TEXT,
                            $3::JSONB,
                            $4::INTEGER,
                            $5::INTEGER,
                            $6::INTEGER
                        )
                    """,
                        schedule["queue_name"],
                        schedule["task_name"],
                        schedule["params"],
                        schedule["priority"],
                        schedule["timeout_sec"],
                        schedule["max_retries"],
                    )

                    # Calculate next run time
                    next_run = calculate_next_run(schedule["cron_expression"], now)

                    # Update the schedule
                    await conn.execute(
                        """
                        UPDATE absurd.scheduled_tasks
                        SET last_run_at = $1,
                            next_run_at = $2,
                            updated_at = $1
                        WHERE schedule_id = $3
                    """,
                        now,
                        next_run,
                        schedule["schedule_id"],
                    )

                    logger.info(
                        f"Spawned task {task_id} for schedule '{schedule['name']}', "
                        f"next run at {next_run}"
                    )

                except Exception as e:
                    logger.error(f"Failed to process schedule '{schedule['name']}': {e}")


# SQL migration for scheduled tasks table
SCHEDULED_TASKS_SCHEMA = """
-- =============================================================================
-- Scheduled Tasks Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS absurd.scheduled_tasks (
    schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    
    -- Task definition
    queue_name TEXT NOT NULL,
    task_name TEXT NOT NULL,
    params JSONB NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 0,
    timeout_sec INTEGER,
    max_retries INTEGER NOT NULL DEFAULT 3,
    
    -- Schedule configuration
    cron_expression TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    state TEXT NOT NULL DEFAULT 'active'
        CHECK (state IN ('active', 'paused', 'disabled')),
    
    -- Tracking
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for scheduled tasks
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_state 
    ON absurd.scheduled_tasks(state);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run 
    ON absurd.scheduled_tasks(next_run_at) WHERE state = 'active';
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_queue 
    ON absurd.scheduled_tasks(queue_name);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON absurd.scheduled_tasks TO PUBLIC;

COMMENT ON TABLE absurd.scheduled_tasks IS 'Cron-like scheduled task definitions';
"""


async def ensure_scheduled_tasks_table(pool: "asyncpg.Pool") -> None:
    """Ensure the scheduled_tasks table exists.

    Args:
        pool: PostgreSQL connection pool
    """
    async with pool.acquire() as conn:
        await conn.execute(SCHEDULED_TASKS_SCHEMA)
    logger.info("Scheduled tasks table ready")


async def create_schedule(
    pool: "asyncpg.Pool",
    name: str,
    queue_name: str,
    task_name: str,
    cron_expression: str,
    params: Optional[Dict[str, Any]] = None,
    priority: int = 0,
    timeout_sec: Optional[int] = None,
    max_retries: int = 3,
    timezone: str = "UTC",
    description: Optional[str] = None,
) -> ScheduledTask:
    """Create a new scheduled task.

    Args:
        pool: PostgreSQL connection pool
        name: Unique schedule name
        queue_name: Target queue for spawned tasks
        task_name: Task type name
        cron_expression: 5-field cron expression
        params: Task parameters
        priority: Task priority (higher = more important)
        timeout_sec: Task timeout
        max_retries: Maximum retry attempts
        timezone: Schedule timezone
        description: Optional description

    Returns:
        Created ScheduledTask
    """
    # Validate cron expression
    parse_cron_expression(cron_expression)

    # Calculate initial next_run_at
    next_run = calculate_next_run(cron_expression)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO absurd.scheduled_tasks (
                name, description, queue_name, task_name, params,
                priority, timeout_sec, max_retries, cron_expression,
                timezone, next_run_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING *
        """,
            name,
            description,
            queue_name,
            task_name,
            params or {},
            priority,
            timeout_sec,
            max_retries,
            cron_expression,
            timezone,
            next_run,
        )

    return _row_to_scheduled_task(row)


async def get_schedule(pool: "asyncpg.Pool", name: str) -> Optional[ScheduledTask]:
    """Get a scheduled task by name."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM absurd.scheduled_tasks WHERE name = $1
        """,
            name,
        )

    return _row_to_scheduled_task(row) if row else None


async def list_schedules(
    pool: "asyncpg.Pool",
    queue_name: Optional[str] = None,
    state: Optional[ScheduleState] = None,
) -> List[ScheduledTask]:
    """List scheduled tasks with optional filters."""
    conditions = []
    params = []

    if queue_name:
        conditions.append(f"queue_name = ${len(params) + 1}")
        params.append(queue_name)

    if state:
        conditions.append(f"state = ${len(params) + 1}")
        params.append(state.value)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT * FROM absurd.scheduled_tasks
            {where_clause}
            ORDER BY name
        """,
            *params,
        )

    return [_row_to_scheduled_task(row) for row in rows]


async def update_schedule(
    pool: "asyncpg.Pool",
    name: str,
    cron_expression: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    state: Optional[ScheduleState] = None,
    priority: Optional[int] = None,
    description: Optional[str] = None,
) -> Optional[ScheduledTask]:
    """Update a scheduled task."""
    updates = ["updated_at = NOW()"]
    values = []

    if cron_expression is not None:
        parse_cron_expression(cron_expression)  # Validate
        values.append(cron_expression)
        updates.append(f"cron_expression = ${len(values)}")
        # Recalculate next_run_at
        next_run = calculate_next_run(cron_expression)
        values.append(next_run)
        updates.append(f"next_run_at = ${len(values)}")

    if params is not None:
        values.append(params)
        updates.append(f"params = ${len(values)}")

    if state is not None:
        values.append(state.value)
        updates.append(f"state = ${len(values)}")

    if priority is not None:
        values.append(priority)
        updates.append(f"priority = ${len(values)}")

    if description is not None:
        values.append(description)
        updates.append(f"description = ${len(values)}")

    values.append(name)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE absurd.scheduled_tasks
            SET {', '.join(updates)}
            WHERE name = ${len(values)}
            RETURNING *
        """,
            *values,
        )

    return _row_to_scheduled_task(row) if row else None


async def delete_schedule(pool: "asyncpg.Pool", name: str) -> bool:
    """Delete a scheduled task."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM absurd.scheduled_tasks WHERE name = $1
        """,
            name,
        )

    return result == "DELETE 1"


async def trigger_schedule_now(pool: "asyncpg.Pool", name: str) -> Optional[str]:
    """Manually trigger a scheduled task immediately.

    Returns:
        The task_id of the spawned task, or None if schedule not found
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT queue_name, task_name, params, priority, timeout_sec, max_retries
            FROM absurd.scheduled_tasks WHERE name = $1
        """,
            name,
        )

        if not row:
            return None

        task_id = await conn.fetchval(
            """
            SELECT absurd.spawn_task(
                $1::TEXT, $2::TEXT, $3::JSONB,
                $4::INTEGER, $5::INTEGER, $6::INTEGER
            )
        """,
            row["queue_name"],
            row["task_name"],
            row["params"],
            row["priority"],
            row["timeout_sec"],
            row["max_retries"],
        )

        # Update last_run_at
        await conn.execute(
            """
            UPDATE absurd.scheduled_tasks
            SET last_run_at = NOW(), updated_at = NOW()
            WHERE name = $1
        """,
            name,
        )

        return str(task_id)


def _row_to_scheduled_task(row) -> ScheduledTask:
    """Convert a database row to ScheduledTask."""
    return ScheduledTask(
        schedule_id=str(row["schedule_id"]),
        name=row["name"],
        queue_name=row["queue_name"],
        task_name=row["task_name"],
        cron_expression=row["cron_expression"],
        params=dict(row["params"]) if row["params"] else {},
        priority=row["priority"],
        timeout_sec=row["timeout_sec"],
        max_retries=row["max_retries"],
        state=ScheduleState(row["state"]),
        timezone=row["timezone"],
        last_run_at=row["last_run_at"],
        next_run_at=row["next_run_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        description=row["description"],
    )
