"""
Absurd durable task queue integration for DSA-110 pipeline.

This package provides integration with the Absurd workflow manager
for durable, fault-tolerant task execution.
"""

from .adapter import (
    CALIBRATOR_CHAIN,
    QUICK_IMAGING_CHAIN,
    STANDARD_PIPELINE_CHAIN,
    TARGET_CHAIN,
    AbsurdStreamingBridge,
    TaskChain,
    execute_chained_task,
    execute_housekeeping,
)
from .client import AbsurdClient
from .config import AbsurdConfig

# Dependencies module
from .dependencies import (
    DependencyState,
    TaskNode,
    WorkflowDAG,
    create_workflow,
    detect_cycles,
    ensure_dependencies_schema,
    get_ready_tasks,
    get_ready_workflow_tasks,
    get_workflow_dag,
    get_workflow_status,
    list_workflows,
    spawn_task_with_dependencies,
    topological_sort,
)

# Scheduling module
from .scheduling import (
    ScheduledTask,
    ScheduleState,
    TaskScheduler,
    calculate_next_run,
    create_schedule,
    delete_schedule,
    ensure_scheduled_tasks_table,
    get_schedule,
    list_schedules,
    parse_cron_expression,
    trigger_schedule_now,
    update_schedule,
)
from .worker import AbsurdWorker, set_websocket_manager

__all__ = [
    # Core client and worker
    "AbsurdClient",
    "AbsurdConfig",
    "AbsurdWorker",
    "AbsurdStreamingBridge",
    "TaskChain",
    "execute_chained_task",
    "execute_housekeeping",
    "set_websocket_manager",
    "STANDARD_PIPELINE_CHAIN",
    "QUICK_IMAGING_CHAIN",
    "CALIBRATOR_CHAIN",
    "TARGET_CHAIN",
    # Scheduling
    "TaskScheduler",
    "ScheduledTask",
    "ScheduleState",
    "parse_cron_expression",
    "calculate_next_run",
    "create_schedule",
    "get_schedule",
    "list_schedules",
    "update_schedule",
    "delete_schedule",
    "trigger_schedule_now",
    "ensure_scheduled_tasks_table",
    # Dependencies/DAG
    "WorkflowDAG",
    "TaskNode",
    "DependencyState",
    "detect_cycles",
    "topological_sort",
    "get_ready_tasks",
    "create_workflow",
    "spawn_task_with_dependencies",
    "get_workflow_dag",
    "get_workflow_status",
    "get_ready_workflow_tasks",
    "list_workflows",
    "ensure_dependencies_schema",
]
