"""DAG-based Task Dependencies for Absurd Workflow Manager.

This module provides directed acyclic graph (DAG) support for task dependencies,
enabling complex workflow orchestration where tasks can depend on the completion
of other tasks.

Features:
- Task dependency declarations (depends_on field)
- Automatic dependency resolution
- Cycle detection to prevent deadlocks
- Parallel execution of independent tasks
- Dependency status tracking
- Workflow visualization data
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

try:
    import asyncpg
except ImportError:
    asyncpg = None

logger = logging.getLogger(__name__)


class DependencyState(str, Enum):
    """State of a task dependency."""

    PENDING = "pending"  # Waiting for dependency to complete
    SATISFIED = "satisfied"  # Dependency completed successfully
    FAILED = "failed"  # Dependency failed
    SKIPPED = "skipped"  # Dependency was cancelled/skipped


@dataclass
class TaskNode:
    """Represents a task in the dependency graph."""

    task_id: str
    task_name: str
    status: str
    depends_on: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    depth: int = 0  # Distance from root (no dependencies)


@dataclass
class WorkflowDAG:
    """Represents a complete workflow DAG."""

    workflow_id: str
    name: str
    tasks: Dict[str, TaskNode] = field(default_factory=dict)
    root_tasks: List[str] = field(default_factory=list)  # Tasks with no dependencies
    leaf_tasks: List[str] = field(default_factory=list)  # Tasks with no dependents
    total_depth: int = 0


def detect_cycles(dependencies: Dict[str, List[str]]) -> Optional[List[str]]:
    """Detect cycles in a dependency graph.

    Args:
        dependencies: Dict mapping task_id -> list of dependency task_ids

    Returns:
        List of task_ids forming a cycle, or None if no cycle exists
    """
    # Use DFS with coloring
    WHITE, GRAY, BLACK = 0, 1, 2
    color = defaultdict(lambda: WHITE)

    def dfs(node: str, path: List[str]) -> Optional[List[str]]:
        color[node] = GRAY

        for dep in dependencies.get(node, []):
            if color[dep] == GRAY:
                # Found a back edge - cycle detected
                cycle_start = path.index(dep) if dep in path else 0
                return path[cycle_start:] + [dep]
            elif color[dep] == WHITE:
                result = dfs(dep, path + [dep])
                if result:
                    return result

        color[node] = BLACK
        return None

    for node in dependencies:
        if color[node] == WHITE:
            result = dfs(node, [node])
            if result:
                return result

    return None


def topological_sort(dependencies: Dict[str, List[str]]) -> List[str]:
    """Perform topological sort on dependency graph.

    Args:
        dependencies: Dict mapping task_id -> list of dependency task_ids

    Returns:
        List of task_ids in topological order (dependencies first)

    Raises:
        ValueError if cycle detected
    """
    cycle = detect_cycles(dependencies)
    if cycle:
        raise ValueError(f"Dependency cycle detected: {' -> '.join(cycle)}")

    # Kahn's algorithm
    in_degree = defaultdict(int)
    all_nodes = set(dependencies.keys())

    for deps in dependencies.values():
        all_nodes.update(deps)
        for dep in deps:
            in_degree[dep] += 1

    # Start with nodes that have no incoming edges (root tasks)
    queue = [node for node in all_nodes if in_degree[node] == 0]
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)

        for other in all_nodes:
            if node in dependencies.get(other, []):
                in_degree[other] -= 1
                if in_degree[other] == 0:
                    queue.append(other)

    # Return in reverse order (dependencies before dependents)
    return result[::-1]


def get_ready_tasks(
    dependencies: Dict[str, List[str]],
    completed: Set[str],
    failed: Set[str],
    in_progress: Set[str],
) -> List[str]:
    """Get tasks that are ready to execute (all dependencies satisfied).

    Args:
        dependencies: Task dependency graph
        completed: Set of completed task_ids
        failed: Set of failed task_ids
        in_progress: Set of in-progress task_ids

    Returns:
        List of task_ids ready for execution
    """
    ready = []

    for task_id, deps in dependencies.items():
        if task_id in completed or task_id in failed or task_id in in_progress:
            continue

        # Check if all dependencies are satisfied
        all_satisfied = all(dep in completed for dep in deps)
        any_failed = any(dep in failed for dep in deps)

        if any_failed:
            # Mark this task as failed due to dependency failure
            failed.add(task_id)
        elif all_satisfied:
            ready.append(task_id)

    return ready


# SQL schema for task dependencies
DEPENDENCIES_SCHEMA = """
-- =============================================================================
-- Task Dependencies Support
-- =============================================================================

-- Add depends_on column to tasks if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'absurd'
        AND table_name = 'tasks'
        AND column_name = 'depends_on'
    ) THEN
        ALTER TABLE absurd.tasks
        ADD COLUMN depends_on UUID[] DEFAULT '{}';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'absurd'
        AND table_name = 'tasks'
        AND column_name = 'workflow_id'
    ) THEN
        ALTER TABLE absurd.tasks
        ADD COLUMN workflow_id UUID;
    END IF;
END $$;

-- Index for dependency lookups
CREATE INDEX IF NOT EXISTS idx_tasks_depends_on
    ON absurd.tasks USING GIN (depends_on);
CREATE INDEX IF NOT EXISTS idx_tasks_workflow_id
    ON absurd.tasks(workflow_id) WHERE workflow_id IS NOT NULL;

-- Workflows table for grouping related tasks
CREATE TABLE IF NOT EXISTS absurd.workflows (
    workflow_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    total_tasks INTEGER NOT NULL DEFAULT 0,
    completed_tasks INTEGER NOT NULL DEFAULT 0,
    failed_tasks INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_workflows_status
    ON absurd.workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_created_at
    ON absurd.workflows(created_at DESC);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON absurd.workflows TO PUBLIC;

-- Function to spawn a task with dependencies
CREATE OR REPLACE FUNCTION absurd.spawn_task_with_deps(
    p_queue_name TEXT,
    p_task_name TEXT,
    p_params JSONB,
    p_depends_on UUID[],
    p_workflow_id UUID DEFAULT NULL,
    p_priority INTEGER DEFAULT 0,
    p_timeout_sec INTEGER DEFAULT NULL,
    p_max_retries INTEGER DEFAULT 3
) RETURNS UUID AS $$
DECLARE
    v_task_id UUID;
    v_pending_deps INTEGER;
BEGIN
    -- Check if all dependencies exist
    SELECT COUNT(*)
    INTO v_pending_deps
    FROM unnest(p_depends_on) AS dep_id
    WHERE NOT EXISTS (
        SELECT 1 FROM absurd.tasks WHERE task_id = dep_id
    );

    IF v_pending_deps > 0 THEN
        RAISE EXCEPTION 'One or more dependency tasks do not exist';
    END IF;

    -- Check for unsatisfied dependencies
    SELECT COUNT(*)
    INTO v_pending_deps
    FROM absurd.tasks
    WHERE task_id = ANY(p_depends_on)
      AND status NOT IN ('completed');

    -- Insert task with appropriate status
    INSERT INTO absurd.tasks (
        queue_name,
        task_name,
        params,
        priority,
        timeout_sec,
        max_retries,
        depends_on,
        workflow_id,
        status
    ) VALUES (
        p_queue_name,
        p_task_name,
        p_params,
        p_priority,
        p_timeout_sec,
        p_max_retries,
        p_depends_on,
        p_workflow_id,
        CASE WHEN v_pending_deps > 0 THEN 'pending' ELSE 'pending' END
    ) RETURNING task_id INTO v_task_id;

    RETURN v_task_id;
END;
$$ LANGUAGE plpgsql;

-- Function to check and release blocked tasks
CREATE OR REPLACE FUNCTION absurd.check_blocked_tasks(
    p_completed_task_id UUID
) RETURNS INTEGER AS $$
DECLARE
    v_released INTEGER := 0;
    v_task RECORD;
BEGIN
    -- Find tasks waiting on the completed task
    FOR v_task IN
        SELECT task_id, depends_on
        FROM absurd.tasks
        WHERE p_completed_task_id = ANY(depends_on)
          AND status = 'pending'
    LOOP
        -- Check if all dependencies are now satisfied
        IF NOT EXISTS (
            SELECT 1
            FROM unnest(v_task.depends_on) AS dep_id
            WHERE NOT EXISTS (
                SELECT 1 FROM absurd.tasks
                WHERE task_id = dep_id AND status = 'completed'
            )
        ) THEN
            -- All dependencies satisfied - task is ready
            v_released := v_released + 1;
        END IF;
    END LOOP;

    RETURN v_released;
END;
$$ LANGUAGE plpgsql;

-- Update complete_task to check blocked tasks
CREATE OR REPLACE FUNCTION absurd.complete_task_with_deps(
    p_task_id UUID,
    p_result JSONB
) RETURNS TABLE (
    success BOOLEAN,
    released_tasks INTEGER
) AS $$
DECLARE
    v_success BOOLEAN;
    v_released INTEGER;
    v_workflow_id UUID;
BEGIN
    -- Complete the task normally
    SELECT absurd.complete_task(p_task_id, p_result) INTO v_success;

    IF v_success THEN
        -- Check for blocked tasks that can now proceed
        SELECT absurd.check_blocked_tasks(p_task_id) INTO v_released;

        -- Update workflow progress if applicable
        SELECT workflow_id INTO v_workflow_id
        FROM absurd.tasks WHERE task_id = p_task_id;

        IF v_workflow_id IS NOT NULL THEN
            UPDATE absurd.workflows
            SET completed_tasks = completed_tasks + 1,
                status = CASE
                    WHEN completed_tasks + 1 >= total_tasks THEN 'completed'
                    ELSE status
                END,
                completed_at = CASE
                    WHEN completed_tasks + 1 >= total_tasks THEN NOW()
                    ELSE completed_at
                END
            WHERE workflow_id = v_workflow_id;
        END IF;
    ELSE
        v_released := 0;
    END IF;

    RETURN QUERY SELECT v_success, v_released;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION absurd.spawn_task_with_deps IS
    'Create a task with dependencies on other tasks';
COMMENT ON FUNCTION absurd.check_blocked_tasks IS
    'Check and count tasks that can proceed after a task completes';
COMMENT ON FUNCTION absurd.complete_task_with_deps IS
    'Complete a task and check for blocked dependent tasks';
"""


async def ensure_dependencies_schema(pool: "asyncpg.Pool") -> None:
    """Ensure the dependencies schema extensions exist.

    Args:
        pool: PostgreSQL connection pool
    """
    async with pool.acquire() as conn:
        await conn.execute(DEPENDENCIES_SCHEMA)
    logger.info("Dependencies schema ready")


async def create_workflow(
    pool: "asyncpg.Pool",
    name: str,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a new workflow container.

    Args:
        pool: PostgreSQL connection pool
        name: Workflow name
        description: Optional description
        metadata: Optional metadata dict

    Returns:
        workflow_id as string
    """
    async with pool.acquire() as conn:
        workflow_id = await conn.fetchval(
            """
            INSERT INTO absurd.workflows (name, description, metadata)
            VALUES ($1, $2, $3)
            RETURNING workflow_id
        """,
            name,
            description,
            metadata or {},
        )

    return str(workflow_id)


async def spawn_task_with_dependencies(
    pool: "asyncpg.Pool",
    queue_name: str,
    task_name: str,
    params: Dict[str, Any],
    depends_on: Optional[List[str]] = None,
    workflow_id: Optional[str] = None,
    priority: int = 0,
    timeout_sec: Optional[int] = None,
    max_retries: int = 3,
) -> str:
    """Spawn a task with dependencies.

    Args:
        pool: PostgreSQL connection pool
        queue_name: Target queue
        task_name: Task type name
        params: Task parameters
        depends_on: List of task_ids this task depends on
        workflow_id: Optional workflow container
        priority: Task priority
        timeout_sec: Timeout in seconds
        max_retries: Max retry attempts

    Returns:
        task_id as string
    """
    # Convert string UUIDs to proper format for PostgreSQL
    dep_uuids = depends_on or []

    async with pool.acquire() as conn:
        task_id = await conn.fetchval(
            """
            SELECT absurd.spawn_task_with_deps(
                $1::TEXT, $2::TEXT, $3::JSONB, $4::UUID[],
                $5::UUID, $6::INTEGER, $7::INTEGER, $8::INTEGER
            )
        """,
            queue_name,
            task_name,
            params,
            dep_uuids,
            workflow_id,
            priority,
            timeout_sec,
            max_retries,
        )

        # Update workflow task count if applicable
        if workflow_id:
            await conn.execute(
                """
                UPDATE absurd.workflows
                SET total_tasks = total_tasks + 1
                WHERE workflow_id = $1
            """,
                workflow_id,
            )

    return str(task_id)


async def get_workflow_dag(pool: "asyncpg.Pool", workflow_id: str) -> WorkflowDAG:
    """Build a DAG representation of a workflow.

    Args:
        pool: PostgreSQL connection pool
        workflow_id: Workflow ID

    Returns:
        WorkflowDAG with task nodes and relationships
    """
    async with pool.acquire() as conn:
        # Get workflow info
        workflow = await conn.fetchrow(
            """
            SELECT name, description FROM absurd.workflows
            WHERE workflow_id = $1
        """,
            workflow_id,
        )

        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # Get all tasks in workflow
        tasks = await conn.fetch(
            """
            SELECT task_id, task_name, status, depends_on
            FROM absurd.tasks
            WHERE workflow_id = $1
            ORDER BY created_at
        """,
            workflow_id,
        )

    # Build DAG
    dag = WorkflowDAG(
        workflow_id=workflow_id,
        name=workflow["name"],
    )

    # First pass: create nodes
    for task in tasks:
        task_id = str(task["task_id"])
        deps = [str(d) for d in (task["depends_on"] or [])]

        dag.tasks[task_id] = TaskNode(
            task_id=task_id,
            task_name=task["task_name"],
            status=task["status"],
            depends_on=deps,
        )

    # Second pass: compute dependents and identify roots/leaves
    for task_id, node in dag.tasks.items():
        if not node.depends_on:
            dag.root_tasks.append(task_id)

        for dep_id in node.depends_on:
            if dep_id in dag.tasks:
                dag.tasks[dep_id].dependents.append(task_id)

    # Find leaf tasks (no dependents)
    for task_id, node in dag.tasks.items():
        if not node.dependents:
            dag.leaf_tasks.append(task_id)

    # Compute depths using BFS from roots
    visited = set()
    queue = [(tid, 0) for tid in dag.root_tasks]

    while queue:
        task_id, depth = queue.pop(0)
        if task_id in visited:
            continue
        visited.add(task_id)

        if task_id in dag.tasks:
            dag.tasks[task_id].depth = depth
            dag.total_depth = max(dag.total_depth, depth)

            for dep_id in dag.tasks[task_id].dependents:
                queue.append((dep_id, depth + 1))

    return dag


async def get_ready_workflow_tasks(
    pool: "asyncpg.Pool",
    workflow_id: str,
) -> List[str]:
    """Get tasks in a workflow that are ready to execute.

    Ready tasks have all dependencies completed and are in pending status.

    Args:
        pool: PostgreSQL connection pool
        workflow_id: Workflow ID

    Returns:
        List of ready task_ids
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.task_id
            FROM absurd.tasks t
            WHERE t.workflow_id = $1
              AND t.status = 'pending'
              AND NOT EXISTS (
                  SELECT 1
                  FROM unnest(t.depends_on) AS dep_id
                  WHERE NOT EXISTS (
                      SELECT 1 FROM absurd.tasks
                      WHERE task_id = dep_id AND status = 'completed'
                  )
              )
        """,
            workflow_id,
        )

    return [str(row["task_id"]) for row in rows]


async def get_workflow_status(
    pool: "asyncpg.Pool",
    workflow_id: str,
) -> Dict[str, Any]:
    """Get comprehensive workflow status.

    Args:
        pool: PostgreSQL connection pool
        workflow_id: Workflow ID

    Returns:
        Dict with workflow status and task breakdown
    """
    async with pool.acquire() as conn:
        workflow = await conn.fetchrow(
            """
            SELECT * FROM absurd.workflows WHERE workflow_id = $1
        """,
            workflow_id,
        )

        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # Get task status breakdown
        task_stats = await conn.fetchrow(
            """
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'claimed') as running,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed
            FROM absurd.tasks
            WHERE workflow_id = $1
        """,
            workflow_id,
        )

        # Get blocked tasks (waiting on dependencies)
        blocked = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM absurd.tasks t
            WHERE t.workflow_id = $1
              AND t.status = 'pending'
              AND array_length(t.depends_on, 1) > 0
              AND EXISTS (
                  SELECT 1
                  FROM unnest(t.depends_on) AS dep_id
                  WHERE EXISTS (
                      SELECT 1 FROM absurd.tasks
                      WHERE task_id = dep_id AND status NOT IN ('completed')
                  )
              )
        """,
            workflow_id,
        )

    return {
        "workflow_id": str(workflow["workflow_id"]),
        "name": workflow["name"],
        "description": workflow["description"],
        "status": workflow["status"],
        "created_at": workflow["created_at"].isoformat() if workflow["created_at"] else None,
        "started_at": workflow["started_at"].isoformat() if workflow["started_at"] else None,
        "completed_at": workflow["completed_at"].isoformat() if workflow["completed_at"] else None,
        "tasks": {
            "total": task_stats["total"],
            "pending": task_stats["pending"],
            "running": task_stats["running"],
            "completed": task_stats["completed"],
            "failed": task_stats["failed"],
            "blocked": blocked,
        },
        "progress": (
            task_stats["completed"] / task_stats["total"] * 100 if task_stats["total"] > 0 else 0
        ),
    }


async def list_workflows(
    pool: "asyncpg.Pool",
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List workflows with optional status filter.

    Args:
        pool: PostgreSQL connection pool
        status: Optional status filter
        limit: Maximum number of results

    Returns:
        List of workflow dicts
    """
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                """
                SELECT * FROM absurd.workflows
                WHERE status = $1
                ORDER BY created_at DESC
                LIMIT $2
            """,
                status,
                limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM absurd.workflows
                ORDER BY created_at DESC
                LIMIT $1
            """,
                limit,
            )

    return [
        {
            "workflow_id": str(row["workflow_id"]),
            "name": row["name"],
            "description": row["description"],
            "status": row["status"],
            "total_tasks": row["total_tasks"],
            "completed_tasks": row["completed_tasks"],
            "failed_tasks": row["failed_tasks"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
        }
        for row in rows
    ]
