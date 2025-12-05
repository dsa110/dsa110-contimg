"""
Execution module for unified task execution.

This module provides the Executor abstraction that enables consistent
execution of conversion tasks in both in-process and subprocess modes.

Part of Issue #11: Subprocess vs In-Process Execution Consistency.

Main exports:
    - ExecutionTask: Task specification dataclass
    - ExecutionResult: Result dataclass with success/failure info
    - ErrorCode: Standardized error codes
    - Executor: Abstract base class for executors
    - InProcessExecutor: Execute in current process
    - SubprocessExecutor: Execute in isolated subprocess
    - get_executor: Factory function

    - ResourceManager: Resource limit management
    - resource_limits: Context manager for limits

    - validate_execution_task: Validate task parameters
    - ValidationResult: Validation outcome
    - ValidationError: Exception for validation failures

Example:
    from dsa110_contimg.execution import (
        ExecutionTask, get_executor, ErrorCode
    )

    task = ExecutionTask(
        group_id="2025-06-01T12:00:00",
        input_dir=Path("/data/incoming"),
        output_dir=Path("/stage/ms"),
        start_time=datetime(2025, 6, 1, 12, 0),
        end_time=datetime(2025, 6, 1, 13, 0),
    )

    executor = get_executor("in-process")
    result = executor.run(task)

    if result.success:
        print(f"Converted: {result.final_paths}")
    else:
        print(f"Error {result.error_code}: {result.message}")
"""

from dsa110_contimg.execution.errors import (
    ErrorCode,
    ExecutionError,
    ValidationError,
    map_exception_to_error_code,
    map_return_code_to_error_code,
)
from dsa110_contimg.execution.executor import (
    Executor,
    InProcessExecutor,
    SubprocessExecutor,
    get_executor,
)
from dsa110_contimg.execution.resources import (
    ResourceManager,
    ResourceSnapshot,
    get_recommended_limits,
    resource_limits,
)
from dsa110_contimg.execution.task import (
    ExecutionMetrics,
    ExecutionResult,
    ExecutionTask,
    ResourceLimits,
)
from dsa110_contimg.execution.validate import (
    ValidationResult,
    validate_execution_task,
)

# Import adapter functions LAST to avoid circular imports
# (adapter.py imports ExecutionTask and get_executor from this module)
from dsa110_contimg.execution.adapter import (  # noqa: E402, I001
    convert_group_inprocess,
    convert_group_subprocess,
    convert_group_unified,
    create_task_from_group,
    execute_conversion,
)

__all__ = [
    # Task and Result
    "ExecutionTask",
    "ExecutionResult",
    "ExecutionMetrics",
    "ResourceLimits",
    # Error handling
    "ErrorCode",
    "ExecutionError",
    "ValidationError",
    "map_exception_to_error_code",
    "map_return_code_to_error_code",
    # Executors
    "Executor",
    "InProcessExecutor",
    "SubprocessExecutor",
    "get_executor",
    # Resource management
    "ResourceManager",
    "ResourceSnapshot",
    "resource_limits",
    "get_recommended_limits",
    # Validation
    "validate_execution_task",
    "ValidationResult",
    # Adapter functions
    "convert_group_unified",
    "convert_group_inprocess",
    "convert_group_subprocess",
    "create_task_from_group",
    "execute_conversion",
]
