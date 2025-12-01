# Scripts

Utility scripts for the DSA-110 Continuum Imaging Pipeline.

## Directory Structure

### `ops/` - Operations & Runtime

Scripts for running and monitoring the API server in production/development.

| Script            | Description                                        |
| ----------------- | -------------------------------------------------- |
| `run_api.py`      | **Primary entry point** - Start the FastAPI server |
| `run_api.sh`      | Shell wrapper for run_api.py                       |
| `health_check.py` | Check API health and database connectivity         |
| `ensure_port.py`  | Ensure the API port is available before starting   |
| `migrate.py`      | Database migration management with Alembic         |

**Quick Start:**

```bash
# Start the API server
python scripts/ops/run_api.py

# Or use uvicorn directly
python -m uvicorn dsa110_contimg.api.app:app --host 0.0.0.0 --port 8000

# Database migrations
python scripts/ops/migrate.py status    # Show current status
python scripts/ops/migrate.py upgrade   # Apply pending migrations
python scripts/ops/migrate.py history   # Show migration history
python scripts/ops/migrate.py create "Add new column"  # Create migration
```

### `dev/` - Development Tools

Scripts for development, documentation generation, and one-time fixes.

| Script                     | Description                           |
| -------------------------- | ------------------------------------- |
| `render_mermaid_to_svg.py` | Render Mermaid diagrams to SVG        |
| `fix_schemas.py`           | One-time schema migration/fix utility |

> **Note:** For directory structure diagrams, use the root-level script:
> `python scripts/generate_structure_diagram.py`

### `testing/` - Test Utilities

Scripts for manual testing and validation.

| Script                  | Description                           |
| ----------------------- | ------------------------------------- |
| `test_api_endpoints.sh` | Manually test API endpoints with curl |

**Note:** Automated tests are in `tests/` directory. Use `pytest tests/` for
unit/integration tests.
