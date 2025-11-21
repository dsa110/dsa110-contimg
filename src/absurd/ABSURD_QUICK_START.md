# Absurd Quick Start Guide

## First Steps to Implement Absurd

Follow these steps in order to get Absurd up and running quickly.

## Step 1: Database Setup (5 minutes)

### Option A: Use Setup Script (Recommended)

```bash
cd /data/dsa110-contimg/src
./scripts/setup_absurd.sh
```

The script will:

- Check PostgreSQL availability
- Create database if needed
- Install Absurd schema
- Create initial queue
- Generate connection string

### Option B: Manual Setup

```bash
# 1. Create database
createdb dsa110_absurd

# 2. Install schema
psql -d dsa110_absurd -f /home/ubuntu/proj/absurd/sql/absurd.sql

# 3. Create queue
psql -d dsa110_absurd -c "SELECT absurd.create_queue('dsa110-pipeline');"

# 4. Verify
psql -d dsa110_absurd -c "SELECT * FROM absurd.queues;"
```

## Step 2: Install Python Dependencies (2 minutes)

```bash
cd /data/dsa110-contimg/src

# Add asyncpg to requirements
echo "asyncpg>=0.29.0" >> requirements.txt

# Or install directly
pip install asyncpg>=0.29.0
```

## Step 3: Create Python Client (10 minutes)

Create the basic client structure:

```bash
mkdir -p dsa110_contimg/absurd
touch dsa110_contimg/absurd/__init__.py
```

Create `dsa110_contimg/absurd/client.py` (see `ABSURD_IMPLEMENTATION_ROADMAP.md`
Step 1.3 for full code)

## Step 4: Test Basic Integration (5 minutes)

Create `scripts/test_absurd_basic.py`:

```python
#!/usr/bin/env python3
"""Basic test of Absurd integration."""
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dsa110_contimg.absurd.client import AbsurdClient

async def main():
    database_url = os.getenv(
        "ABSURD_DATABASE_URL",
        "postgresql://postgres:postgres@localhost/dsa110_absurd"
    )

    print(f"Connecting to: {database_url}")
    client = AbsurdClient(database_url)

    try:
        await client.connect()
        print("✓ Connected to Absurd database")

        # Spawn a test task
        task_id = await client.spawn_task(
            queue_name="dsa110-pipeline",
            task_name="test-task",
            params={"message": "Hello from Absurd!"}
        )

        print(f"✓ Spawned task: {task_id}")

        # Get task details
        task = await client.get_task("dsa110-pipeline", task_id)
        print(f"✓ Task status: {task['state']}")
        print(f"✓ Task name: {task['task_name']}")

        print("\n✅ Basic integration test passed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

Run test:

```bash
export ABSURD_DATABASE_URL="postgresql://user:pass@localhost/dsa110_absurd"
python scripts/test_absurd_basic.py
```

## Step 5: Add Configuration (5 minutes)

Add to `dsa110_contimg/pipeline/config.py`:

```python
# In PipelineConfig class
absurd_enabled: bool = Field(default=False)
absurd_database_url: Optional[str] = Field(default=None)
absurd_queue_name: str = Field(default="dsa110-pipeline")

# In from_env method
absurd_enabled = os.getenv("ABSURD_ENABLED", "false").lower() == "true"
absurd_database_url = os.getenv("ABSURD_DATABASE_URL")
absurd_queue_name = os.getenv("ABSURD_QUEUE_NAME", "dsa110-pipeline")
```

## Step 6: Test Task Spawning (5 minutes)

Create a simple script to spawn a pipeline task:

```python
# scripts/test_spawn_pipeline_task.py
import asyncio
import os
from dsa110_contimg.absurd.client import AbsurdClient

async def main():
    client = AbsurdClient(os.getenv("ABSURD_DATABASE_URL"))
    await client.connect()

    try:
        task_id = await client.spawn_task(
            queue_name="dsa110-pipeline",
            task_name="dsa110-pipeline",
            params={
                "input_path": "/data/incoming/test.hdf5",
                "output_dir": "/stage/dsa110-contimg/ms"
            }
        )
        print(f"Task spawned: {task_id}")
        print(f"View in Habitat: http://localhost:7890/tasks/{task_id}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 7: Verify with Habitat UI (Optional, 5 minutes)

If you want to see tasks in Habitat UI:

```bash
cd /home/ubuntu/proj/absurd/habitat
make build
./bin/habitat run -db-name dsa110_absurd -listen :7890
```

Then visit: http://localhost:7890

## Next Steps

Once basic integration works:

1. **Create Worker** (see `ABSURD_IMPLEMENTATION_ROADMAP.md` Step 2.2)
2. **Add API Endpoints** (see `ABSURD_IMPLEMENTATION_ROADMAP.md` Step 3.1)
3. **Integrate with Pipeline** (see `ABSURD_IMPLEMENTATION_ROADMAP.md` Step 2.3)
4. **Add UI Components** (see `ABSURD_USER_INTERACTION_GUIDE.md`)

## Troubleshooting

### Database Connection Failed

- Verify PostgreSQL is running: `pg_isready`
- Check connection string format
- Verify database exists: `psql -l | grep dsa110_absurd`

### Schema Not Found

- Verify schema installed: `psql -d dsa110_absurd -c "\dn"`
- Reinstall schema:
  `psql -d dsa110_absurd -f /home/ubuntu/proj/absurd/sql/absurd.sql`

### Queue Not Found

- Verify queue created:
  `psql -d dsa110_absurd -c "SELECT * FROM absurd.queues;"`
- Create queue:
  `psql -d dsa110_absurd -c "SELECT absurd.create_queue('dsa110-pipeline');"`

### Import Errors

- Verify Python path includes `src` directory
- Check `dsa110_contimg/absurd/__init__.py` exists
- Verify `asyncpg` is installed: `pip list | grep asyncpg`

## Success Checklist

- [ ] Database created and schema installed
- [ ] Queue created successfully
- [ ] Python client can connect
- [ ] Can spawn test task
- [ ] Can query task status
- [ ] (Optional) Can view in Habitat UI

## Time Estimate

- Step 1: 5 minutes
- Step 2: 2 minutes
- Step 3: 10 minutes
- Step 4: 5 minutes
- Step 5: 5 minutes
- Step 6: 5 minutes
- Step 7: 5 minutes (optional)

**Total: ~30-40 minutes** for basic integration

## Getting Help

- See `ABSURD_IMPLEMENTATION_ROADMAP.md` for detailed steps
- See `ABSURD_USER_INTERACTION_GUIDE.md` for UI integration
- See `HABITAT_UI_INTEGRATION.md` for UI integration details
