# Docker Setup for Playwright Python Tests

## Quick Start

```bash
# Build and run all tests
./scripts/run-playwright-python-tests.sh

# Or use docker compose directly
docker compose -f docker/docker-compose.playwright-python.yml --profile playwright-python run --rm playwright-python-tests
```

## What Was Created

1. **Dockerfile** (`docker/Dockerfile.playwright-python`):
   - Python 3.11 base image
   - All system dependencies for Playwright
   - Playwright Python and browsers installed
   - Ready to run tests

2. **Docker Compose** (`docker/docker-compose.playwright-python.yml`):
   - Service definition for test container
   - Volume mounts for tests and source code
   - Environment variable configuration
   - Network configuration (host mode for accessing services)

3. **Test Runner Script** (`scripts/run-playwright-python-tests.sh`):
   - Convenience script for running tests
   - Handles building, starting services, running tests
   - Copies test results to host

## Usage

### Basic Usage

```bash
# Run all tests
./scripts/run-playwright-python-tests.sh

# Run specific test
./scripts/run-playwright-python-tests.sh --command "pytest tests/e2e/frontend/test_dashboard.py -v"
```

### With Services

```bash
# Start services, run tests, stop services
./scripts/run-playwright-python-tests.sh --up --down

# Or start services manually
docker compose up -d api dashboard-dev
./scripts/run-playwright-python-tests.sh
docker compose down
```

## Configuration

The Docker setup uses:

- **Host network mode**: Accesses services on `localhost` or
  `host.docker.internal`
- **Environment variables**: Configurable via docker-compose or script
- **Volume mounts**: Tests and source code are mounted (not copied)

## Test Results

Results are saved to:

- Container: `/app/test-results/`
- Host: `test-results/playwright-python/` (copied automatically)

## Advantages

✅ **No browser installation issues** - Browsers installed in container ✅
**Consistent environment** - Same setup everywhere ✅ **Easy CI/CD** - Works the
same locally and in CI ✅ **Isolated** - Doesn't affect host system

## See Also

- [Playwright Python Docker Guide](../../../docs/how-to/playwright-python-docker.md)
- [Run All Frontend Tests](../../../docs/how-to/run-all-frontend-tests.md)
