# DSA-110 Developer Guide

**For developers contributing to the DSA-110 Continuum Imaging Pipeline.**

!!! note "Version"
Last updated: Phase 4 completion (complexity reduction)

---

## Quick Start for Developers

### Prerequisites

- **Conda Environment**: `casa6` with Python 3.11
- **CASA 6.7**: via casatools, casatasks, casacore
- **Node.js 22+**: for frontend development
- **Git**: with hooks configured

### First-Time Setup

```bash
# 1. Clone the repository
cd /data
git clone git@github.com:dsa110/dsa110-contimg.git
cd dsa110-contimg

# 2. Run setup script (sets up hooks, verifies environment)
./scripts/ops/dev/setup-dev.sh

# 3. Verify your setup
./scripts/ops/quality/check-environment.sh

# 4. Activate the environment
conda activate casa6
```

### Critical Rule: Always Use casa6 Python

```bash
# ❌ WRONG - uses system Python
python script.py

# ✅ CORRECT - uses casa6 environment
conda activate casa6
python script.py

# ✅ ALSO CORRECT - explicit path
/opt/miniforge/envs/casa6/bin/python script.py

# ✅ WRAPPER - automatic environment
./scripts/ops/utils/run-python.sh script.py
```

---

## Repository Structure

```
dsa110-contimg/
├── backend/                 # Python pipeline package
│   ├── src/dsa110_contimg/  # Main Python package
│   │   ├── api/             # REST API (FastAPI)
│   │   ├── conversion/      # UVH5 → MS conversion
│   │   ├── calibration/     # CASA calibration
│   │   ├── imaging/         # Imaging (WSClean, tclean)
│   │   ├── database/        # Database operations
│   │   ├── catalog/         # Source catalogs
│   │   ├── photometry/      # Source detection
│   │   ├── pipeline/        # Pipeline orchestration
│   │   └── utils/           # Shared utilities
│   └── tests/               # Test suite
├── frontend/                # React dashboard
│   ├── src/                 # Source code
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom hooks
│   │   └── api/             # API client
│   └── e2e/                 # E2E tests (Playwright)
├── docs/                    # Documentation
├── ops/                     # Operations (systemd, Docker)
├── config/                  # Configuration files
├── scripts/                 # Utility scripts
└── state/                   # Runtime state (databases, logs)
```

---

## Backend Development

### Package Structure

The main Python package is at `backend/src/dsa110_contimg/`:

| Module         | Purpose                             |
| -------------- | ----------------------------------- |
| `api/`         | REST API with FastAPI (fully async) |
| `conversion/`  | UVH5 → MS conversion                |
| `calibration/` | CASA calibration routines           |
| `imaging/`     | Imaging with WSClean/tclean         |
| `database/`    | SQLite database operations          |
| `catalog/`     | Source catalog management           |
| `photometry/`  | Source detection and photometry     |
| `pipeline/`    | Pipeline stage orchestration        |
| `utils/`       | Shared utilities                    |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Routes Layer                      │
│              (routes/*.py - HTTP handlers)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Services Layer                            │
│         (services/*.py - Business logic)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Repositories Layer                          │
│       (async_repositories.py - aiosqlite)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               Database Abstraction Layer                     │
│            (db_adapters/ - SQLite adapters)                 │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
UVH5 Files → conversion/ → Measurement Sets → calibration/ → Calibrated MS
                                                    ↓
                                              imaging/ → Images
                                                    ↓
                                          photometry/ → Sources
                                                    ↓
                                           catalog/ → Catalog
```

### Key Design Patterns

#### 1. Protocol-Based Interfaces

Repository interfaces use Python `Protocol`:

```python
from typing import Protocol

class ImageRepositoryProtocol(Protocol):
    async def get_by_id(self, image_id: str) -> Optional[ImageRecord]: ...
    async def list_all(self, limit: int, offset: int) -> List[ImageRecord]: ...
```

#### 2. Dependency Injection

FastAPI's `Depends()` for clean DI:

```python
from fastapi import Depends

async def get_async_image_service(
    repo: AsyncImageRepository = Depends(get_async_image_repository)
) -> AsyncImageService:
    return AsyncImageService(repo)

@router.get("/{image_id}")
async def get_image(
    image_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    return await service.get_image(image_id)
```

#### 3. Custom Exception Hierarchy

All API errors extend `DSA110APIError`:

```python
class DSA110APIError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

class RecordNotFoundError(DSA110APIError):
    status_code = 404
    error_code = "NOT_FOUND"

class ValidationError(DSA110APIError):
    status_code = 400
    error_code = "VALIDATION_ERROR"
```

### Running the Backend

```bash
conda activate casa6
cd /data/dsa110-contimg/backend

# Start API server (development)
uvicorn dsa110_contimg.api.app:app --reload --host 0.0.0.0 --port 8000

# Or use the VS Code task
# "Backend: Start API Server"
```

---

## Frontend Development

### Quick Start

```bash
cd /data/dsa110-contimg/frontend

# 1. Install dependencies
npm install

# 2. Start dev server (http://localhost:3000)
npm run dev

# 3. Run tests in watch mode
npm test

# 4. Start Storybook (http://localhost:6006)
npm run storybook
```

### Directory Structure

```
frontend/src/
├── pages/           # Page components (routes)
├── components/
│   ├── common/      # Reusable UI components
│   └── {feature}/   # Feature-specific components
├── hooks/           # Custom React hooks
├── api/             # API client & data fetching
├── types/           # TypeScript types
└── utils/           # Utility functions
```

### Component Organization

Each component follows this pattern:

```
src/components/example/
├── ExampleComponent.tsx       # Main component
├── ExampleComponent.test.tsx  # Unit tests (Vitest)
├── ExampleComponent.stories.tsx  # Storybook stories
└── index.ts                   # Barrel exports
```

### Key Libraries

| Library      | Purpose                 |
| ------------ | ----------------------- |
| React Query  | Server state management |
| React Router | Client-side routing     |
| Zustand      | Client state management |
| Tailwind CSS | Utility-first CSS       |
| Vitest       | Unit testing            |
| Playwright   | E2E testing             |
| Storybook    | Component development   |

### Working with the API

```tsx
import { useImages, useSources } from '@/hooks/useQueries';

function MyComponent() {
  const { data, isLoading, error } = useImages();
  if (isLoading) return <Loading />;
  if (error) return <Error message={error.message} />;
  return <ImageList images={data} />;
}
```

### Building for Production

```bash
# Build on scratch SSD (faster I/O)
npm run build:scratch

# Or standard build
npm run build
```

---

## Testing Strategy

### Test Categories

| Type            | Purpose             | Speed | Location             |
| --------------- | ------------------- | ----- | -------------------- |
| **Contract**    | Verify interfaces   | Fast  | `tests/contract/`    |
| **Unit**        | Test isolated logic | Fast  | `tests/unit/`        |
| **Integration** | End-to-end flow     | Slow  | `tests/integration/` |

### Contract Tests (Recommended)

Contract tests verify actual behavior with real data and minimal mocking:

```python
class TestConversionContracts:
    """Verify MS output format."""

    def test_ms_directory_structure(self, synthetic_ms_path):
        """MS has required CASA tables."""
        assert (synthetic_ms_path / "ANTENNA").exists()
        assert (synthetic_ms_path / "SPECTRAL_WINDOW").exists()
        assert (synthetic_ms_path / "MAIN").exists()

    def test_antenna_positions_itrf(self, synthetic_ms_path):
        """Antenna positions are in ITRF coordinates."""
        with table(str(synthetic_ms_path / "ANTENNA")) as t:
            positions = t.getcol("POSITION")
            assert positions.shape[1] == 3  # X, Y, Z
```

### Running Tests

```bash
conda activate casa6
cd /data/dsa110-contimg/backend

# IMPORTANT: Use 'python -m pytest' to ensure casa6's pytest is used
# (not ~/.local/bin/pytest which may be linked to system Python)

# Run all contract tests
python -m pytest tests/contract/ -v

# Run unit tests
python -m pytest tests/unit/ -v

# Run specific test file
python -m pytest tests/contract/test_conversion_contracts.py -v

# With coverage
python -m pytest tests/contract/ --cov=src/dsa110_contimg --cov-report=term-missing

# Suppress pyuvdata deprecation warnings
python -m pytest tests/contract/ -v -W ignore::DeprecationWarning
```

### Frontend Testing

```bash
cd /data/dsa110-contimg/frontend

# Run unit tests
npm test

# Run tests for specific file
npm test -- src/components/common/Card.test.tsx

# Run E2E tests
npm run test:e2e

# Run Playwright in UI mode
npx playwright test --ui
```

### Test Fixtures

Common fixtures in `tests/conftest.py`:

- `synthetic_ms_path`: Generated MS for conversion testing
- `synthetic_fits_path`: Generated FITS for imaging testing
- `test_pipeline_db`: Clean database instance
- `api_client`: FastAPI TestClient for API testing

### Current Test Status

- **163 contract tests** across 6 files
- **35 conversion tests** passing
- **72% code coverage** on API package
- All tests run with casa6 environment

---

## Code Quality

### Linting

```bash
# Backend (Python)
cd backend
ruff check src/

# Frontend (TypeScript/JavaScript)
cd frontend
npm run lint
npm run lint:fix  # Auto-fix issues
```

### Type Checking

```bash
# Backend
mypy src/dsa110_contimg/

# Frontend
npm run typecheck
```

### Formatting

```bash
# Backend
ruff format src/

# Frontend
npm run lint:fix
```

---

## Environment Configuration

### Environment Variables

| Variable            | Default                     | Description             |
| ------------------- | --------------------------- | ----------------------- |
| `DSA110_DB_BACKEND` | `sqlite`                    | Database backend        |
| `PRODUCTS_DB_PATH`  | `state/db/products.sqlite3` | Products database       |
| `PIPELINE_DB`       | `state/db/pipeline.sqlite3` | Pipeline state database |
| `REDIS_URL`         | `redis://localhost:6379/0`  | Redis connection        |
| `DSA110_LOG_LEVEL`  | `INFO`                      | Logging level           |
| `DSA110_QUEUE_NAME` | `dsa110-pipeline`           | RQ queue name           |

### Storage Paths

| Mount       | Type     | Purpose                           |
| ----------- | -------- | --------------------------------- |
| `/data/`    | HDD      | Source code, databases (slow I/O) |
| `/stage/`   | NVMe SSD | Output MS files, working data     |
| `/scratch/` | NVMe SSD | Temporary files, builds           |
| `/dev/shm/` | tmpfs    | In-memory staging                 |

**Important**: Avoid I/O-intensive operations on `/data/`. Use `/scratch/` or `/stage/` for builds and processing.

---

## Database Development

### Unified Pipeline Database

The pipeline uses a unified SQLite database at `state/db/pipeline.sqlite3`:

```python
from dsa110_contimg.database.session import get_session

with get_session() as session:
    # Query products
    products = session.query(MSIndex).filter_by(calibrated=True).all()
```

### Key Tables

| Table                 | Purpose                  |
| --------------------- | ------------------------ |
| `ms_index`            | Measurement Set registry |
| `images`              | Image products           |
| `calibration_tables`  | Caltable registry        |
| `ingest_queue`        | Streaming queue state    |
| `performance_metrics` | Processing timing        |

### Migrations

```bash
cd backend
alembic upgrade head           # Apply all migrations
alembic revision --autogenerate -m "description"  # Create migration
```

---

## Adding New Features

### 1. New API Endpoint

```python
# backend/src/dsa110_contimg/api/routes/new_feature.py
from fastapi import APIRouter, Depends
from ..schemas import NewFeatureResponse
from ..services.new_feature_service import NewFeatureService

router = APIRouter(prefix="/new-feature", tags=["new-feature"])

@router.get("/{item_id}", response_model=NewFeatureResponse)
async def get_item(
    item_id: str,
    service: NewFeatureService = Depends(get_new_feature_service),
):
    return await service.get_item(item_id)
```

Register in `app.py`:

```python
from .routes import new_feature
app.include_router(new_feature.router, prefix="/api/v1")
```

### 2. New React Component

```tsx
// frontend/src/components/new-feature/NewComponent.tsx
import React from 'react';

interface NewComponentProps {
  title: string;
}

export function NewComponent({ title }: NewComponentProps) {
  return <div className="p-4 bg-white rounded shadow">{title}</div>;
}
```

Add tests:

```tsx
// NewComponent.test.tsx
import { render, screen } from '@testing-library/react';
import { NewComponent } from './NewComponent';

describe('NewComponent', () => {
  it('renders title', () => {
    render(<NewComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
```

Add Storybook story:

```tsx
// NewComponent.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { NewComponent } from './NewComponent';

const meta: Meta<typeof NewComponent> = {
  component: NewComponent,
};

export default meta;
type Story = StoryObj<typeof NewComponent>;

export const Default: Story = {
  args: {
    title: 'Example Title',
  },
};
```

### 3. New Pipeline Stage

```python
# backend/src/dsa110_contimg/pipeline/stages_impl.py
from .base import PipelineStage

class NewProcessingStage(PipelineStage):
    """New processing stage."""

    name = "new_processing"

    async def execute(self, context: PipelineContext) -> StageResult:
        # Implementation
        return StageResult(success=True, artifacts={"output": path})
```

---

## Debugging Tips

### 1. Check Logs

```bash
# Pipeline logs
tail -f /data/dsa110-contimg/state/logs/pipeline.log

# API logs
tail -f /data/dsa110-contimg/state/logs/api.log

# Streaming converter logs
journalctl -u contimg-stream -f
```

### 2. Database Inspection

```bash
# Pipeline database
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3
> .tables
> SELECT * FROM ms_index LIMIT 5;

# Check queue status
> SELECT group_id, state, processing_stage FROM ingest_queue ORDER BY received_at DESC LIMIT 10;
```

### 3. Interactive Development

```bash
conda activate casa6
cd /data/dsa110-contimg/backend

# IPython with package available
python -c "from dsa110_contimg.conversion import ..."

# Test specific function
python -c "
from dsa110_contimg.utils import FastMeta
with FastMeta('/data/incoming/test.hdf5') as meta:
    print(meta.freq_array)
"
```

### 4. VS Code Tasks

Use the provided VS Code tasks for common operations:

- **Backend: Run Tests** - Run pytest
- **Backend: Start API Server** - Start development server
- **Frontend: Dev Server** - Start React dev server
- **Health Check** - Verify all services running

---

## Contributing Workflow

### 1. Create a Branch

```bash
git checkout master-dev
git pull origin master-dev
git checkout -b feature/my-new-feature
```

### 2. Make Changes

- Follow existing code patterns
- Add tests for new functionality
- Update documentation if needed

### 3. Run Tests

```bash
# Backend
cd backend
python -m pytest tests/contract/ tests/unit/ -v

# Frontend
cd frontend
npm test
npm run lint
```

### 4. Commit

```bash
git add .
git commit -m "feat: add new feature description"
```

### 5. Push and Create PR

```bash
git push origin feature/my-new-feature
# Create PR on GitHub targeting master-dev
```

---

## Common Pitfalls

| Pitfall                       | Solution                                          |
| ----------------------------- | ------------------------------------------------- |
| Wrong Python environment      | Always `conda activate casa6` first               |
| Slow I/O on `/data/`          | Use `/scratch/` or `/stage/` for builds           |
| Tests using wrong pytest      | Use `python -m pytest` not bare `pytest`          |
| Missing antenna positions     | Use `antpos_local.get_itrf()`                     |
| Processing single subbands    | Must group by timestamp first (16 subbands/group) |
| pyuvdata deprecation warnings | Use `Nants_telescope` not `Nants_data`            |

---

## Resources

- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Storybook**: `http://localhost:6006` (Component library)
- **Backend Architecture**: `backend/docs/ARCHITECTURE.md`
- **System Context**: `docs/SYSTEM_CONTEXT.md`

---

## Getting Help

1. Search documentation with DocSearch:

   ```bash
   python -m dsa110_contimg.docsearch.cli search "your question"
   ```

2. Check existing tests for usage patterns

3. Browse Storybook for component examples

4. Review the architecture docs for design decisions
