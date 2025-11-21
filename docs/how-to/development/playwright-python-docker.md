# Running Playwright Python Tests in Docker

This guide explains how to run Playwright Python E2E tests in a Docker
container, which solves browser installation issues on Ubuntu 18.04.

## Quick Start

### Option 1: Using the Convenience Script (Recommended)

```bash
# Run all tests (will build image if needed)
./scripts/run-playwright-python-tests.sh

# Rebuild image and run tests
./scripts/run-playwright-python-tests.sh --build

# Start services, run tests, then stop services
./scripts/run-playwright-python-tests.sh --up --down

# Run specific test file
./scripts/run-playwright-python-tests.sh --command "pytest tests/e2e/frontend/test_dashboard.py -v"

# Run in headed mode (see browser)
./scripts/run-playwright-python-tests.sh --headed
```

### Option 2: Using Docker Compose Directly

```bash
# Build the image
docker compose -f docker/docker-compose.playwright-python.yml --profile playwright-python build

# Run all tests
docker compose -f docker/docker-compose.playwright-python.yml --profile playwright-python run --rm playwright-python-tests

# Run specific test
docker compose -f docker/docker-compose.playwright-python.yml --profile playwright-python run --rm playwright-python-tests pytest tests/e2e/frontend/test_dashboard.py -v
```

## Prerequisites

1. **Docker and Docker Compose** installed
2. **Services Running** (or use `--up` flag):
   - Backend API: `http://api:8000` (or `http://localhost:8000`)
   - Frontend Production: `http://localhost:3210` (recommended for testing)
   - Frontend Dev Server: `http://localhost:5174` (Docker dev container)

### Port Assignments

Following the project's port assignment rules:

- **Port 3210**: Production dashboard (`dashboard` service)
- **Port 5174**: Development dashboard (`dashboard-dev` service, Docker)
- **Port 5173**: Vite dev server (inside container, mapped to 5174 on host)
- **Port 8000**: Backend API

See `docs/operations/PORT_ASSIGNMENTS_QUICK_REFERENCE.md` for complete port
assignments.

## Docker Setup

### Image Details

The Docker image (`Dockerfile.playwright-python`) includes:

- Python 3.11
- All test dependencies from `requirements-test.txt`
- Playwright Python
- Chromium browser (installed via Playwright)
- All system dependencies for browser automation

### Network Configuration

Tests run in the `dsa110-network` Docker network, allowing them to:

- Access the frontend at `http://dashboard-dev:5173`
- Access the API at `http://api:8000`

## Running Tests

### Run All Tests

```bash
./scripts/run-playwright-python-tests.sh
```

### Run Specific Test Suite

```bash
# Comprehensive test suite
./scripts/run-playwright-python-tests.sh --command "pytest tests/e2e/frontend/test_all_pages.py -v"

# Quick smoke tests
./scripts/run-playwright-python-tests.sh --command "pytest tests/e2e/frontend/test_page_smoke.py -v"

# Dashboard tests only
./scripts/run-playwright-python-tests.sh --command "pytest tests/e2e/frontend/test_dashboard.py -v"
```

### Run with Parallel Execution

```bash
# Auto-detect workers
./scripts/run-playwright-python-tests.sh --command "pytest tests/e2e/frontend/ -v -n auto"

# Specific worker count
./scripts/run-playwright-python-tests.sh --command "pytest tests/e2e/frontend/ -v -n 4"
```

### Run with Markers

```bash
# Only critical tests
./scripts/run-playwright-python-tests.sh --command "pytest tests/e2e/frontend/ -v -m 'e2e_critical'"

# Exclude slow tests
./scripts/run-playwright-python-tests.sh --command "pytest tests/e2e/frontend/ -v -m 'not e2e_slow'"
```

## Starting Services

### Option 1: Use Docker Compose (Recommended)

```bash
# Start API and frontend
docker compose up -d api dashboard-dev

# Run tests
./scripts/run-playwright-python-tests.sh

# Stop services when done
docker compose down
```

### Option 2: Use Script Flag

```bash
# Start services, run tests, stop services
./scripts/run-playwright-python-tests.sh --up --down
```

### Option 3: Services Already Running

If services are already running, just run:

```bash
./scripts/run-playwright-python-tests.sh
```

## Test Results

Test results are automatically copied to the host:

```
test-results/playwright-python/
├── report.html          # HTML test report
├── junit.xml            # JUnit XML for CI/CD
└── screenshots/         # Screenshots on failure (if enabled)
```

View the HTML report:

```bash
# Open in browser
xdg-open test-results/playwright-python/report.html
# Or on macOS
open test-results/playwright-python/report.html
```

## Environment Variables

You can set environment variables for the tests:

```bash
# Test against production dashboard (recommended)
FRONTEND_BASE_URL=http://localhost:3210 ./scripts/run-playwright-python-tests.sh

# Test against dev dashboard
FRONTEND_BASE_URL=http://localhost:5174 ./scripts/run-playwright-python-tests.sh

# Or set in docker-compose file or pass via -e flag
docker compose -f docker/docker-compose.playwright-python.yml \
    --profile playwright-python \
    run --rm \
    -e FRONTEND_BASE_URL=http://localhost:3210 \
    -e API_URL=http://localhost:8000 \
    -e PLAYWRIGHT_HEADLESS=false \
    playwright-python-tests
```

## Troubleshooting

### Services Not Accessible

If tests can't reach services:

1. **Check network**: Ensure services are on `dsa110-network`

   ```bash
   docker network inspect dsa110-network
   ```

2. **Check service names**: Use `dashboard-dev` and `api` (not `localhost`)

3. **Start services**: Use `--up` flag or start manually

4. **Verify ports**:
   - Production: `curl http://localhost:3210`
   - Dev: `curl http://localhost:5174`
   - API: `curl http://localhost:8000/api/status`

### Warnings and Errors

All known warnings have been resolved:

1. **Orphan containers warning**: Automatically cleaned up by the test script
2. **Benchmark warnings**: Suppressed in `pytest.ini` when using parallel
   execution
3. **Unknown marker warnings**: All markers registered in `tests/pytest.ini`

If you see warnings, check:

- `tests/pytest.ini` has all required markers
- `pytest.ini` has benchmark warning filters
- Test script runs `docker compose down --remove-orphans` before tests

### Browser Issues

If browser fails to launch:

1. **Check image build**: Rebuild with `--build` flag
2. **Check logs**: `docker compose logs playwright-python-tests`
3. **Try headed mode**: Use `--headed` flag to see what's happening

### Test Failures

1. **Check frontend is running**: `curl http://localhost:5173`
2. **Check API is running**: `curl http://localhost:8000/api/health`
3. **View test results**: Check `test-results/playwright-python/report.html`
4. **Run in headed mode**: `--headed` to see browser

### Permission Issues

If you get permission errors:

```bash
# Fix script permissions
chmod +x scripts/run-playwright-python-tests.sh

# Fix Docker permissions (if needed)
sudo usermod -aG docker $USER
# Then log out and back in
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Frontend E2E Tests (Python)

on: [push, pull_request]

jobs:
  frontend-e2e-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Compose
        run: |
          docker compose version

      - name: Start services
        run: |
          docker compose up -d api dashboard-dev
          sleep 10

      - name: Run E2E tests
        run: |
          ./scripts/run-playwright-python-tests.sh --build

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-python-results
          path: test-results/playwright-python/
```

## Advantages of Docker Approach

1. **No Browser Installation Issues**: Browsers are installed in the container
2. **Consistent Environment**: Same environment across all machines
3. **Isolation**: Tests don't affect host system
4. **Easy CI/CD**: Works the same locally and in CI
5. **Network Isolation**: Tests can access services via Docker network

## Comparison: Docker vs Local

| Aspect                  | Docker                       | Local                              |
| ----------------------- | ---------------------------- | ---------------------------------- |
| Browser Installation    | ✅ Automatic                 | ❌ Manual (issues on Ubuntu 18.04) |
| Environment Consistency | ✅ Same everywhere           | ❌ Varies by machine               |
| Setup Complexity        | ✅ One command               | ❌ Multiple steps                  |
| CI/CD Ready             | ✅ Yes                       | ⚠️ May need adjustments            |
| Debugging               | ⚠️ Requires Docker knowledge | ✅ Direct access                   |

## See Also

- [Playwright Python Frontend Testing Guide](playwright-python-frontend-testing.md)
- [Run All Frontend Tests](run-all-frontend-tests.md)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
