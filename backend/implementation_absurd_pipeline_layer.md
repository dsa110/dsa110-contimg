## **Implementation Plan: Pipeline Layer on ABSURD**

### **Phase 1: Core Pipeline Framework** (Week 1-2)

#### **New Files to Create**

```
backend/src/dsa110_contimg/pipeline/
├── __init__.py
├── base.py              # Pipeline, Job base classes
├── executor.py          # Pipeline → ABSURD task spawning
├── scheduler.py         # Cron-like scheduling daemon
└── registry.py          # Pipeline registration and discovery
```

---

### **1.1: Base Classes (`base.py`)**

```python
# backend/src/dsa110_contimg/pipeline/base.py
"""
Pipeline framework: Declarative job orchestration on top of ABSURD
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

class JobResult:
    """Result of job execution"""
    def __init__(self, success: bool, outputs: Dict[str, Any], message: str = ""):
        self.success = success
        self.outputs = outputs
        self.message = message

    @classmethod
    def success(cls, outputs: Dict[str, Any] = None, message: str = ""):
        return cls(True, outputs or {}, message)

    @classmethod
    def failure(cls, message: str):
        return cls(False, {}, message)


@dataclass
class Job(ABC):
    """
    Base class for pipeline jobs

    Each job becomes an ABSURD task when executed via Pipeline.
    Subclasses implement execute() with their business logic.
    """
    job_type: str = field(init=False)  # Set by subclass

    @abstractmethod
    def execute(self) -> JobResult:
        """
        Execute job logic

        Returns:
            JobResult with success status and output parameters
        """
        pass

    def to_absurd_params(self) -> Dict[str, Any]:
        """
        Convert job parameters to ABSURD task params

        Override if you need custom serialization
        """
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }


class RetryPolicy(Enum):
    """Retry behavior for failed jobs"""
    NONE = "none"           # Don't retry
    FIXED = "fixed"         # Fixed backoff
    EXPONENTIAL = "exponential"  # Exponential backoff


@dataclass
class JobConfig:
    """Configuration for a job in a pipeline"""
    job_class: type  # Job subclass
    job_id: str      # Unique ID within pipeline
    params: Dict[str, Any]  # Parameters (can reference other jobs via ${job_id.output_key})
    dependencies: List[str] = field(default_factory=list)  # List of job_ids
    priority: int = 0
    timeout_seconds: Optional[int] = None


class Pipeline(ABC):
    """
    Base class for declarative pipelines

    Subclasses define job graphs that get compiled to ABSURD task chains.

    Example:
        class NightlyMosaicPipeline(Pipeline):
            pipeline_name = "nightly_mosaic"
            schedule = "0 3 * * *"

            def __init__(self, config):
                super().__init__(config)
                self.add_job(MosaicPlanningJob, 'plan', {...})
                self.add_job(MosaicBuildJob, 'build', {...}, dependencies=['plan'])
    """

    # Class-level config (override in subclasses)
    pipeline_name: str = None
    schedule: Optional[str] = None  # Cron syntax

    def __init__(self, config):
        self.config = config
        self.jobs: List[JobConfig] = []
        self._retry_policy = RetryPolicy.EXPONENTIAL
        self._max_retries = 3
        self._notifications = []

    def add_job(
        self,
        job_class: type,
        job_id: str,
        params: Dict[str, Any],
        dependencies: List[str] = None,
        priority: int = 0,
        timeout_seconds: Optional[int] = None
    ):
        """Add a job to the pipeline"""
        self.jobs.append(JobConfig(
            job_class=job_class,
            job_id=job_id,
            params=params,
            dependencies=dependencies or [],
            priority=priority,
            timeout_seconds=timeout_seconds
        ))

    def set_retry_policy(
        self,
        max_retries: int = 3,
        backoff: str = "exponential"
    ):
        """Configure retry behavior for all jobs"""
        self._max_retries = max_retries
        self._retry_policy = RetryPolicy(backoff)

    def add_notification(
        self,
        on_failure: str,  # job_id to watch
        channels: List[str],  # ['email', 'slack', etc.]
        recipients: List[str]
    ):
        """Add notification on job failure"""
        self._notifications.append({
            'job_id': on_failure,
            'channels': channels,
            'recipients': recipients
        })

    @abstractmethod
    def build(self):
        """
        Define the job graph

        Called during __init__ to construct the pipeline.
        Subclasses should call add_job() here.
        """
        pass
```

---

### **1.2: Pipeline Executor (`executor.py`)**

This is where we bridge Pipeline → ABSURD:

```python
# backend/src/dsa110_contimg/pipeline/executor.py
"""
Execute pipelines by spawning ABSURD tasks
"""
import asyncio
import re
from typing import Dict, Any, List
from pathlib import Path

from dsa110_contimg.absurd import AbsurdClient
from dsa110_contimg.pipeline.base import Pipeline, JobConfig
from dsa110_contimg.database import Database


class PipelineExecutor:
    """
    Compiles Pipeline job graphs into ABSURD task chains
    """

    def __init__(self, db_path: Path):
        self.db = Database(db_path)
        self.client: AbsurdClient = None

    async def connect(self):
        """Initialize ABSURD client"""
        self.client = AbsurdClient.from_env()
        await self.client.connect()

    async def close(self):
        """Close ABSURD client"""
        if self.client:
            await self.client.close()

    async def execute(self, pipeline: Pipeline) -> str:
        """
        Execute a pipeline by spawning ABSURD tasks

        Args:
            pipeline: Pipeline instance to execute

        Returns:
            execution_id: Unique ID for this pipeline run
        """
        if not self.client:
            await self.connect()

        # Generate execution ID
        import time
        execution_id = f"{pipeline.pipeline_name}_{int(time.time())}"

        # Record in database
        self.db.execute(
            """
            INSERT INTO pipeline_executions
                (execution_id, pipeline_name, status, started_at)
            VALUES (?, ?, 'running', ?)
            """,
            (execution_id, pipeline.pipeline_name, time.time())
        )

        # Spawn ABSURD tasks for each job
        task_map = {}  # job_id -> ABSURD task_id

        for job_config in pipeline.jobs:
            # Resolve dependencies
            depends_on = []
            for dep_job_id in job_config.dependencies:
                if dep_job_id not in task_map:
                    raise ValueError(
                        f"Job {job_config.job_id} depends on {dep_job_id} "
                        f"which hasn't been defined yet"
                    )
                depends_on.append(task_map[dep_job_id])

            # Resolve parameter references (${other_job.output_key})
            resolved_params = self._resolve_params(
                job_config.params,
                execution_id
            )

            # Add execution context
            resolved_params['_execution_id'] = execution_id
            resolved_params['_job_id'] = job_config.job_id
            resolved_params['_pipeline_name'] = pipeline.pipeline_name

            # Spawn ABSURD task
            task_id = await self.client.spawn(
                task_type=job_config.job_class.job_type,
                params=resolved_params,
                depends_on=depends_on,
                priority=job_config.priority,
                queue_name=f"{pipeline.pipeline_name}-queue"
            )

            task_map[job_config.job_id] = task_id

            # Record job in database
            self.db.execute(
                """
                INSERT INTO pipeline_jobs
                    (execution_id, job_id, absurd_task_id, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (execution_id, job_config.job_id, task_id, time.time())
            )

        return execution_id

    def _resolve_params(
        self,
        params: Dict[str, Any],
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Resolve parameter references like ${plan.plan_id}

        For now, just pass through - ABSURD worker will resolve
        when task executes (after dependencies complete)
        """
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith('${'):
                # Mark as deferred resolution
                resolved[key] = {
                    '_deferred': True,
                    '_expression': value,
                    '_execution_id': execution_id
                }
            else:
                resolved[key] = value
        return resolved

    async def get_status(self, execution_id: str) -> Dict[str, Any]:
        """Get pipeline execution status"""
        # Query pipeline status from database
        execution = self.db.query(
            "SELECT * FROM pipeline_executions WHERE execution_id = ?",
            (execution_id,)
        )[0]

        # Get job statuses
        jobs = self.db.query(
            "SELECT * FROM pipeline_jobs WHERE execution_id = ? ORDER BY created_at",
            (execution_id,)
        )

        # Check ABSURD task statuses
        for job in jobs:
            task = await self.client.get_task(job['absurd_task_id'])
            job['absurd_status'] = task['status']

        return {
            'execution_id': execution_id,
            'pipeline_name': execution['pipeline_name'],
            'status': execution['status'],
            'started_at': execution['started_at'],
            'jobs': jobs
        }
```

---

### **1.3: Scheduler (`scheduler.py`)**

Cron-like daemon that triggers pipelines on schedule:

```python
# backend/src/dsa110_contimg/pipeline/scheduler.py
"""
Pipeline scheduler: triggers pipelines based on cron schedules
"""
import asyncio
import time
from pathlib import Path
from typing import Dict, Type
from croniter import croniter
from datetime import datetime

from dsa110_contimg.pipeline.base import Pipeline
from dsa110_contimg.pipeline.executor import PipelineExecutor
from dsa110_contimg.database import Database


class PipelineScheduler:
    """
    Daemon that monitors schedules and triggers pipelines

    Usage:
        scheduler = PipelineScheduler(db_path)
        scheduler.register(NightlyMosaicPipeline)
        await scheduler.start()  # Runs forever
    """

    def __init__(self, db_path: Path, config):
        self.db_path = db_path
        self.config = config
        self.executor = PipelineExecutor(db_path)
        self.pipelines: Dict[str, Type[Pipeline]] = {}
        self._running = False

    def register(self, pipeline_class: Type[Pipeline]):
        """Register a pipeline for scheduling"""
        if not pipeline_class.schedule:
            raise ValueError(
                f"{pipeline_class.__name__} has no schedule defined"
            )

        self.pipelines[pipeline_class.pipeline_name] = pipeline_class
        print(f"Registered {pipeline_class.pipeline_name} "
              f"with schedule: {pipeline_class.schedule}")

    async def start(self):
        """Start scheduler (blocking)"""
        self._running = True
        await self.executor.connect()

        # Track next execution time for each pipeline
        next_run = {}
        for name, pipeline_class in self.pipelines.items():
            cron = croniter(pipeline_class.schedule, datetime.now())
            next_run[name] = cron.get_next(datetime)

        print("Pipeline scheduler started")

        try:
            while self._running:
                now = datetime.now()

                # Check if any pipelines are due
                for name, pipeline_class in self.pipelines.items():
                    if now >= next_run[name]:
                        print(f"Triggering {name} at {now}")

                        try:
                            # Instantiate and execute pipeline
                            pipeline = pipeline_class(self.config)
                            execution_id = await self.executor.execute(pipeline)
                            print(f"Started {name}: {execution_id}")
                        except Exception as e:
                            print(f"Failed to start {name}: {e}")

                        # Calculate next run
                        cron = croniter(pipeline_class.schedule, now)
                        next_run[name] = cron.get_next(datetime)
                        print(f"Next {name} at {next_run[name]}")

                # Sleep until next check (every minute)
                await asyncio.sleep(60)

        finally:
            await self.executor.close()

    def stop(self):
        """Stop scheduler"""
        self._running = False
```

---

### **1.4: Database Schema Extension**

Add to unified `pipeline.sqlite3`:

```sql
-- Pipeline execution tracking
CREATE TABLE IF NOT EXISTS pipeline_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT UNIQUE NOT NULL,
    pipeline_name TEXT NOT NULL,
    status TEXT NOT NULL,  -- running, completed, failed
    started_at REAL NOT NULL,
    completed_at REAL,
    error TEXT
);

CREATE INDEX idx_pipeline_executions_name ON pipeline_executions(pipeline_name);
CREATE INDEX idx_pipeline_executions_started ON pipeline_executions(started_at);

-- Individual job tracking within pipeline
CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    absurd_task_id TEXT NOT NULL,
    status TEXT NOT NULL,  -- pending, running, completed, failed
    created_at REAL NOT NULL,
    completed_at REAL,
    outputs TEXT,  -- JSON
    error TEXT,
    FOREIGN KEY(execution_id) REFERENCES pipeline_executions(execution_id)
);

CREATE INDEX idx_pipeline_jobs_execution ON pipeline_jobs(execution_id);
CREATE INDEX idx_pipeline_jobs_task ON pipeline_jobs(absurd_task_id);
```

---

### **Phase 2: Mosaicking Implementation** (Week 3-4)

Now implement mosaicking using the Pipeline framework:

```python
# backend/src/dsa110_contimg/mosaic/jobs.py
"""
Mosaicking jobs for Pipeline framework
"""
from dataclasses import dataclass
from pathlib import Path
import json
import time

from dsa110_contimg.pipeline.base import Job, JobResult
from dsa110_contimg.database import Database
from dsa110_contimg.mosaic.tiers import TIER_CONFIGS, MosaicTier
from dsa110_contimg.mosaic.builder import build_mosaic
from dsa110_contimg.mosaic.qa import run_qa_checks


@dataclass
class MosaicPlanningJob(Job):
    """Select images for mosaicking"""
    job_type = "mosaic_planning"

    start_time: int
    end_time: int
    tier: str
    mosaic_name: str

    def execute(self) -> JobResult:
        db = Database("state/db/pipeline.sqlite3")

        tier_enum = MosaicTier(self.tier)
        tier_config = TIER_CONFIGS[tier_enum]

        # Query images in time range
        query = """
            SELECT id, path, rms_jy, ra_deg, dec_deg
            FROM images
            WHERE created_at BETWEEN ? AND ?
              AND rms_jy < ?
            ORDER BY rms_jy ASC
            LIMIT ?
        """

        images = db.query(
            query,
            (self.start_time, self.end_time,
             tier_config.rms_threshold_jy, tier_config.max_images)
        )

        if len(images) == 0:
            return JobResult.failure("No images found in time range")

        # Calculate coverage
        coverage = {
            'ra_min': min(img['ra_deg'] for img in images),
            'ra_max': max(img['ra_deg'] for img in images),
            'dec_min': min(img['dec_deg'] for img in images),
            'dec_max': max(img['dec_deg'] for img in images),
        }

        # Insert plan
        image_ids = [img['id'] for img in images]
        plan_id = db.execute(
            """
            INSERT INTO mosaic_plans
                (name, tier, start_time, end_time, image_ids, n_images,
                 ra_min_deg, ra_max_deg, dec_min_deg, dec_max_deg,
                 created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (self.mosaic_name, self.tier, self.start_time, self.end_time,
             json.dumps(image_ids), len(images),
             coverage['ra_min'], coverage['ra_max'],
             coverage['dec_min'], coverage['dec_max'],
             int(time.time()))
        )

        return JobResult.success(
            outputs={'plan_id': plan_id, 'n_images': len(images)},
            message=f"Selected {len(images)} images"
        )


@dataclass
class MosaicBuildJob(Job):
    """Build mosaic from plan"""
    job_type = "mosaic_build"

    plan_id: int  # From planning job

    def execute(self) -> JobResult:
        db = Database("state/db/pipeline.sqlite3")

        # Get plan details
        plan = db.query(
            "SELECT * FROM mosaic_plans WHERE id = ?",
            (self.plan_id,)
        )[0]

        # Update status
        db.execute(
            "UPDATE mosaic_plans SET status = 'building' WHERE id = ?",
            (self.plan_id,)
        )

        # Get image paths
        image_ids = json.loads(plan['image_ids'])
        placeholders = ','.join('?' * len(image_ids))
        images = db.query(
            f"SELECT path FROM images WHERE id IN ({placeholders})",
            tuple(image_ids)
        )
        image_paths = [Path(img['path']) for img in images]

        # Get tier config
        tier_config = TIER_CONFIGS[MosaicTier(plan['tier'])]

        # Build mosaic
        output_path = Path(f"/data/mosaics/{plan['name']}.fits")

        try:
            result = build_mosaic(
                image_paths=image_paths,
                output_path=output_path,
                alignment_order=tier_config.alignment_order,
                timeout_minutes=tier_config.timeout_minutes
            )
        except Exception as e:
            db.execute(
                "UPDATE mosaic_plans SET status = 'failed' WHERE id = ?",
                (self.plan_id,)
            )
            return JobResult.failure(f"Build failed: {e}")

        # Register mosaic
        mosaic_id = db.execute(
            """
            INSERT INTO mosaics
                (plan_id, path, tier, n_images, median_rms_jy, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (self.plan_id, str(output_path), plan['tier'],
             len(image_paths), result.median_rms, int(time.time()))
        )

        db.execute(
            "UPDATE mosaic_plans SET status = 'completed' WHERE id = ?",
            (self.plan_id,)
        )

        return JobResult.success(
            outputs={'mosaic_id': mosaic_id, 'mosaic_path': str(output_path)},
            message=f"Built mosaic: {output_path}"
        )


@dataclass
class MosaicQAJob(Job):
    """Run QA on completed mosaic"""
    job_type = "mosaic_qa"

    mosaic_id: int  # From build job

    def execute(self) -> JobResult:
        db = Database("state/db/pipeline.sqlite3")

        # Get mosaic details
        mosaic = db.query(
            "SELECT * FROM mosaics WHERE id = ?",
            (self.mosaic_id,)
        )[0]

        # Run QA
        qa_result = run_qa_checks(
            mosaic_path=Path(mosaic['path']),
            tier=mosaic['tier']
        )

        # Determine status
        if qa_result.critical_failures:
            qa_status = 'FAIL'
        elif qa_result.warnings:
            qa_status = 'WARN'
        else:
            qa_status = 'PASS'

        # Store QA results
        db.execute(
            """
            INSERT INTO mosaic_qa
                (mosaic_id, astrometry_rms_arcsec, n_reference_stars,
                 median_noise_jy, dynamic_range, has_artifacts,
                 artifact_score, passed, warnings, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (self.mosaic_id, qa_result.astrometry_rms, qa_result.n_stars,
             qa_result.median_noise, qa_result.dynamic_range,
             qa_result.has_artifacts, qa_result.artifact_score,
             qa_status == 'PASS', json.dumps(qa_result.warnings),
             int(time.time()))
        )

        # Update mosaic
        db.execute(
            """
            UPDATE mosaics
            SET qa_status = ?, qa_details = ?
            WHERE id = ?
            """,
            (qa_status, json.dumps(qa_result.to_dict()), self.mosaic_id)
        )

        return JobResult.success(
            outputs={'qa_status': qa_status},
            message=f"QA complete: {qa_status}"
        )
```

---

### **Pipeline Definition:**

```python
# backend/src/dsa110_contimg/mosaic/pipeline.py
"""
Mosaicking pipelines
"""
import time
from dsa110_contimg.pipeline.base import Pipeline
from dsa110_contimg.mosaic.jobs import (
    MosaicPlanningJob, MosaicBuildJob, MosaicQAJob
)


class NightlyMosaicPipeline(Pipeline):
    """
    Nightly science-tier mosaic

    Runs at 03:00 UTC, processes previous 24 hours
    """
    pipeline_name = "nightly_mosaic"
    schedule = "0 3 * * *"

    def __init__(self, config):
        super().__init__(config)
        self.build()

    def build(self):
        end_time = int(time.time())
        start_time = end_time - 86400  # 24 hours ago

        # Planning job
        self.add_job(
            MosaicPlanningJob,
            job_id='plan',
            params={
                'start_time': start_time,
                'end_time': end_time,
                'tier': 'science',
                'mosaic_name': f'nightly_{time.strftime("%Y%m%d")}'
            }
        )

        # Build job (depends on planning)
        self.add_job(
            MosaicBuildJob,
            job_id='build',
            params={'plan_id': '${plan.plan_id}'},
            dependencies=['plan']
        )

        # QA job (depends on build)
        self.add_job(
            MosaicQAJob,
            job_id='qa',
            params={'mosaic_id': '${build.mosaic_id}'},
            dependencies=['build']
        )

        # Retry policy
        self.set_retry_policy(max_retries=2, backoff='exponential')

        # Notifications
        self.add_notification(
            on_failure='qa',
            channels=['email'],
            recipients=['observer@dsa110.org']
        )


class OnDemandMosaicPipeline(Pipeline):
    """User-requested mosaic via API"""
    pipeline_name = "on_demand_mosaic"
    schedule = None  # Event-driven, not scheduled

    def __init__(self, config, request_params):
        self.request_params = request_params
        super().__init__(config)
        self.build()

    def build(self):
        # Same three jobs, parameterized by request
        self.add_job(
            MosaicPlanningJob,
            job_id='plan',
            params={
                'start_time': self.request_params['start_time'],
                'end_time': self.request_params['end_time'],
                'tier': self.request_params.get('tier', 'science'),
                'mosaic_name': self.request_params['name']
            }
        )

        self.add_job(
            MosaicBuildJob,
            job_id='build',
            params={'plan_id': '${plan.plan_id}'},
            dependencies=['plan']
        )

        self.add_job(
            MosaicQAJob,
            job_id='qa',
            params={'mosaic_id': '${build.mosaic_id}'},
            dependencies=['build']
        )
```

---

### **Scheduler Daemon:**

```python
# backend/src/dsa110_contimg/pipeline/scheduler_main.py
"""
Main entry point for pipeline scheduler daemon
"""
import asyncio
from pathlib import Path

from dsa110_contimg.pipeline.scheduler import PipelineScheduler
from dsa110_contimg.mosaic.pipeline import NightlyMosaicPipeline
from dsa110_contimg.config import get_settings


async def main():
    settings = get_settings()

    scheduler = PipelineScheduler(
        db_path=Path(settings.database.unified_db),
        config=settings
    )

    # Register pipelines
    scheduler.register(NightlyMosaicPipeline)
    # scheduler.register(HousekeepingPipeline)  # Future

    # Start (blocks forever)
    await scheduler.start()


if __name__ == "__main__":
    asyncio.run(main())
```

---

### **ABSURD Adapter Extension**

Extend ABSURD's task executor to handle Pipeline jobs:

```python
# backend/src/dsa110_contimg/absurd/adapter.py
# Add to existing file

from dsa110_contimg.mosaic.jobs import (
    MosaicPlanningJob, MosaicBuildJob, MosaicQAJob
)

# Register job types
PIPELINE_JOB_REGISTRY = {
    'mosaic_planning': MosaicPlanningJob,
    'mosaic_build': MosaicBuildJob,
    'mosaic_qa': MosaicQAJob,
}

async def execute_pipeline_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a pipeline job task

    Called by ABSURD worker when task is claimed
    """
    task_type = task['task_type']
    params = task['params']

    # Get job class
    job_class = PIPELINE_JOB_REGISTRY.get(task_type)
    if not job_class:
        raise ValueError(f"Unknown task type: {task_type}")

    # Resolve deferred parameters (${plan.plan_id})
    resolved_params = await _resolve_deferred_params(params, task)

    # Instantiate and execute job
    job = job_class(**resolved_params)
    result = job.execute()

    # Store outputs in database for downstream jobs
    if result.success:
        db = Database("state/db/pipeline.sqlite3")
        db.execute(
            """
            UPDATE pipeline_jobs
            SET status = 'completed', outputs = ?, completed_at = ?
            WHERE absurd_task_id = ?
            """,
            (json.dumps(result.outputs), time.time(), task['id'])
        )

    return {'success': result.success, 'outputs': result.outputs}
```

---

## **Deployment**

### **Start Scheduler:**

```bash
# Single process that triggers scheduled pipelines
python -m dsa110_contimg.pipeline.scheduler_main
```

### **Start ABSURD Workers:**

```bash
# Workers execute the actual jobs
python -m dsa110_contimg.absurd
```

### **Or Use Systemd:**

```ini
# /etc/systemd/system/dsa110-scheduler.service
[Service]
ExecStart=/opt/miniforge/envs/casa6/bin/python \
  -m dsa110_contimg.pipeline.scheduler_main

# /etc/systemd/system/dsa110-workers.service
[Service]
ExecStart=/opt/miniforge/envs/casa6/bin/python \
  -m dsa110_contimg.absurd
```

---

## **Summary: What You Get**

1. ✅ **Declarative pipelines:** Clean Python classes, not scattered cron/scripts
2. ✅ **ABSURD-backed:** Leverages proven task queue infrastructure
3. ✅ **Unified database:** Pipeline state in `pipeline.sqlite3` alongside everything else
4. ✅ **Job dependencies:** Automatic ordering via `dependencies=['plan']`
5. ✅ **Retry logic:** Built into ABSURD, configured per pipeline
6. ✅ **Testable:** Can unit test `Pipeline.build()` and individual `Job.execute()`
7. ✅ **Scheduled execution:** Cron-like syntax, managed in code
8. ✅ **API integration:** Easy to trigger pipelines via FastAPI

This gives you the best of Option A: builds the high-level Pipeline layer while leveraging ABSURD's low-level task queue robustness.

Want me to proceed with drafting the PR description for this implementation?
