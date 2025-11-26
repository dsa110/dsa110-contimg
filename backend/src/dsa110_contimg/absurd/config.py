"""
Absurd workflow manager configuration.

Provides configuration for connecting to and using the Absurd durable
task queue.
"""

import os
from dataclasses import dataclass


@dataclass
class AbsurdConfig:
    """Configuration for Absurd workflow manager.

    Attributes:
        enabled: Whether Absurd is enabled
        database_url: PostgreSQL connection URL
        queue_name: Name of the Absurd queue to use
        worker_concurrency: Number of concurrent tasks per worker
        worker_poll_interval_sec: How often to poll for new tasks (seconds)
        task_timeout_sec: Default task execution timeout (seconds)
        max_retries: Maximum number of task retry attempts
        dead_letter_enabled: Whether to route exhausted tasks to a DLQ
        dead_letter_queue_name: Queue name used for dead letter tasks
    """

    enabled: bool = False
    database_url: str = "postgresql://postgres:postgres@localhost/dsa110_absurd"
    queue_name: str = "dsa110-pipeline"
    worker_concurrency: int = 4
    worker_poll_interval_sec: float = 1.0
    task_timeout_sec: int = 3600  # 1 hour default
    max_retries: int = 3
    dead_letter_enabled: bool = True
    dead_letter_queue_name: str = "dsa110-pipeline-dlq"

    @classmethod
    def from_env(cls) -> "AbsurdConfig":
        """Load Absurd configuration from environment variables.

        Environment variables:
            ABSURD_ENABLED: Enable Absurd (default: false)
            ABSURD_DATABASE_URL: PostgreSQL connection URL
            ABSURD_QUEUE_NAME: Queue name (default: dsa110-pipeline)
            ABSURD_WORKER_CONCURRENCY: Worker concurrency (default: 4)
            ABSURD_WORKER_POLL_INTERVAL: Poll interval (default: 1.0)
            ABSURD_TASK_TIMEOUT: Task timeout in seconds (default: 3600)
            ABSURD_MAX_RETRIES: Maximum retry attempts (default: 3)
            ABSURD_DLQ_ENABLED: Enable dead letter routing (default: true)
            ABSURD_DLQ_QUEUE_NAME: Dead letter queue name (default: <queue_name>-dlq)

        Returns:
            AbsurdConfig instance with values from environment
        """
        queue_name = os.getenv("ABSURD_QUEUE_NAME", "dsa110-pipeline")
        return cls(
            enabled=os.getenv("ABSURD_ENABLED", "false").lower() in ("true", "1", "yes"),
            database_url=os.getenv(
                "ABSURD_DATABASE_URL",
                "postgresql://postgres:postgres@localhost/dsa110_absurd",
            ),
            queue_name=queue_name,
            worker_concurrency=int(os.getenv("ABSURD_WORKER_CONCURRENCY", "4")),
            worker_poll_interval_sec=float(os.getenv("ABSURD_WORKER_POLL_INTERVAL", "1.0")),
            task_timeout_sec=int(os.getenv("ABSURD_TASK_TIMEOUT", "3600")),
            max_retries=int(os.getenv("ABSURD_MAX_RETRIES", "3")),
            dead_letter_enabled=os.getenv("ABSURD_DLQ_ENABLED", "true").lower()
            in ("true", "1", "yes"),
            dead_letter_queue_name=os.getenv("ABSURD_DLQ_QUEUE_NAME", f"{queue_name}-dlq"),
        )

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If configuration values are invalid
        """
        if self.enabled and not self.database_url:
            raise ValueError("ABSURD_DATABASE_URL must be set when Absurd is enabled")

        if self.worker_concurrency < 1:
            raise ValueError(f"worker_concurrency must be >= 1, " f"got {self.worker_concurrency}")

        if self.worker_poll_interval_sec <= 0:
            raise ValueError(
                f"worker_poll_interval_sec must be > 0, " f"got {self.worker_poll_interval_sec}"
            )

        if self.task_timeout_sec < 1:
            raise ValueError(f"task_timeout_sec must be >= 1, " f"got {self.task_timeout_sec}")

        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")

        if self.dead_letter_enabled and not self.dead_letter_queue_name:
            raise ValueError("dead_letter_queue_name must be set when DLQ is enabled")
