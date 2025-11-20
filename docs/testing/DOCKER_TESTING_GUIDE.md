# Docker-Based Testing Guide

## Overview

This guide explains how to run E2E tests using Docker, which is required for
Ubuntu 18.x systems where npm/npx compatibility issues exist.

## Why Docker?

- **Ubuntu 18.x Compatibility**: Node.js 22+ is not available natively on Ubuntu
  18.x
- **Isolated Environment**: Tests run in a consistent environment
- **Easy Setup**: No need to manage Node.js versions locally
- **CI/CD Ready**: Same environment for local and CI testing

## Architecture

```
┌─────────────────────────────────────────┐
│  Host System (Ubuntu 18.x)              │
│  ┌───────────────────────────────────┐  │
│  │  Docker Container                 │  │
│  │  - Node.js 22 Alpine              │  │
│  │  - Playwright                     │  │
│  │  - Chromium                        │  │
│  │                                    │  │
│  │  Tests connect to:                │  │
│  │  - Frontend: host.docker.internal │  │
│  │  - Backend: host.docker.internal  │  │
│  └───────────────────────────────────┘  │
│                                          │
│  Services (running on host):             │
│  - Frontend: localhost:5173             │
│  - Backend: localhost:8010              │
└─────────────────────────────────────────┘
```

## Setup

### 1. Install Docker

```bash
# Ubuntu 18.x
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes
# Verify installation
docker --version
docker-compose --version
```

### 2. Build Test Image

```bash
# Build the test Docker image
docker build -f docker/Dockerfile.test -t dsa110-test:latest .
```

### 3. Start Services

Ensure frontend and backend are running:

```bash
# Option 1: Run services manually
# Frontend: cd frontend && npm run dev
# Backend: python -m dsa110_contimg.api.main

# Option 2: Use Docker Compose (if configured)
./scripts/run-tests-docker.sh up
```

## Running Tests

### Method 1: Simple Docker Script

```bash
# Run all tests
./scripts/run-tests.sh docker-e2e

# Run specific test suite
./scripts/run-tests.sh docker-e2e -- --grep "Navigation"

# Run with specific browser
./scripts/run-tests.sh docker-e2e -- --project=chromium
```

### Method 2: Docker Compose (Isolated)

```bash
# Run all tests (starts services automatically)
./scripts/run-tests-docker.sh up

# Run specific tests
./scripts/run-tests-docker.sh up -- --grep "Navigation"

# Run in UI mode
./scripts/run-tests-docker.sh ui

# Run in debug mode
./scripts/run-tests-docker.sh shell
# Then inside container: npx playwright test --debug
```

### Method 3: Direct Docker Commands

```bash
# Run tests
docker run --rm \
  --network host \
  --add-host=host.docker.internal:host-gateway \
  -v "$(pwd)/test-results:/app/test-results" \
  -v "$(pwd)/playwright-report:/app/playwright-report" \
  -e BASE_URL="http://localhost:5173" \
  -e API_URL="http://localhost:8010" \
  dsa110-test:latest \
  npx playwright test

# Run specific tests
docker run --rm \
  --network host \
  --add-host=host.docker.internal:host-gateway \
  -v "$(pwd)/test-results:/app/test-results" \
  -e BASE_URL="http://localhost:5173" \
  dsa110-test:latest \
  npx playwright test --grep "Navigation"

# Run in UI mode
docker run --rm -it \
  --network host \
  -p 9323:9323 \
  --add-host=host.docker.internal:host-gateway \
  -v "$(pwd)/test-results:/app/test-results" \
  -e BASE_URL="http://localhost:5173" \
  dsa110-test:latest \
  npx playwright test --ui --host 0.0.0.0
```

## Configuration

### Environment Variables

Tests use these environment variables (set via `-e` flag or `.env` file):

- `BASE_URL`: Frontend URL (default: `http://localhost:5173`)
- `API_URL`: Backend API URL (default: `http://localhost:8010`)
- `CI`: Set to `true` in CI environments

### Network Configuration

Tests use `host.docker.internal` to access services running on the host:

- **Host Network Mode**: `--network host` allows direct access
- **Host Gateway**: `--add-host=host.docker.internal:host-gateway` maps host IP

### Volume Mounts

- `test-results/`: Test output (screenshots, videos, traces)
- `playwright-report/`: HTML test report
- Source code: Mounted for live code changes (optional)

## Troubleshooting

### Services Not Accessible

**Problem**: Tests can't connect to frontend/backend

**Solutions**:

1. Verify services are running:

   ```bash
   curl http://localhost:5173
   curl http://localhost:8010/api/health
   ```

2. Use `host.docker.internal` in Docker:

   ```bash
   docker run --add-host=host.docker.internal:host-gateway ...
   ```

3. Use host network mode:
   ```bash
   docker run --network host ...
   ```

### Permission Denied

**Problem**: Docker permission errors

**Solution**:

```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

### Chromium Not Found

**Problem**: Playwright can't find Chromium

**Solution**:

```bash
# Rebuild image with browsers
docker build -f docker/Dockerfile.test -t dsa110-test:latest .
# Or install in container
docker run --rm dsa110-test:latest npx playwright install chromium
```

### Test Timeouts

**Problem**: Tests timeout waiting for services

**Solutions**:

1. Increase timeout in `playwright.config.ts`
2. Wait for services before running tests:
   ```bash
   # Wait for frontend
   until curl -f http://localhost:5173; do sleep 1; done
   # Wait for backend
   until curl -f http://localhost:8010/api/health; do sleep 1; done
   ```

### Out of Memory

**Problem**: Container runs out of memory

**Solution**:

```bash
# Increase Docker memory limit
docker run --memory="2g" ...
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start services
        run: |
          # Start backend
          docker-compose up -d api
          # Start frontend
          cd frontend && npm run dev &

      - name: Build test image
        run: docker build -f docker/Dockerfile.test -t dsa110-test:latest .

      - name: Run tests
        run: |
          docker run --rm \
            --network host \
            -v "$(pwd)/test-results:/app/test-results" \
            -e BASE_URL="http://localhost:5173" \
            -e API_URL="http://localhost:8010" \
            -e CI=true \
            dsa110-test:latest \
            npx playwright test

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

## Best Practices

1. **Rebuild Image Regularly**: Update dependencies and browsers
2. **Use Volumes**: Mount test-results for easy access
3. **Network Configuration**: Use host network for simplicity
4. **Environment Variables**: Set BASE_URL and API_URL explicitly
5. **Clean Up**: Remove containers after tests: `docker run --rm`
6. **Cache Layers**: Use multi-stage builds for faster rebuilds

## Advanced Usage

### Interactive Shell

```bash
# Open shell in test container
./scripts/run-tests-docker.sh shell

# Or directly
docker run -it --rm --network host \
  -v "$(pwd):/app" \
  dsa110-test:latest sh
```

### Debugging Failed Tests

```bash
# Run with trace
docker run --rm --network host \
  -v "$(pwd)/test-results:/app/test-results" \
  dsa110-test:latest \
  npx playwright test --trace on

# View trace
npx playwright show-trace test-results/trace.zip
```

### Custom Test Configuration

```bash
# Run with custom config
docker run --rm --network host \
  -v "$(pwd)/playwright.config.ts:/app/playwright.config.ts" \
  dsa110-test:latest \
  npx playwright test --config=playwright.config.ts
```

## Performance Tips

1. **Parallel Execution**: Tests run in parallel by default
2. **Browser Reuse**: Use `--project=chromium` for faster runs
3. **Selective Testing**: Use `--grep` to run specific tests
4. **Cache Dependencies**: Reuse Docker image layers

## Resources

- [Docker Documentation](https://docs.docker.com/)
- [Playwright Docker Guide](https://playwright.dev/docs/docker)
- [Test Plan](./COMPREHENSIVE_TESTING_PLAN.md)
- E2E Test Guide: `../tests/e2e/README.md` (external file)
