# Quick Start: Testing Guide

## For Ubuntu 18.x Systems (Docker Required)

### 1. Install Docker

```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER
# Log out and back in
```

### 2. Start Services

```bash
# Start backend (in one terminal)
cd /data/dsa110-contimg
python -m dsa110_contimg.api.main

# Start frontend (in another terminal)
cd /data/dsa110-contimg/frontend
npm run dev
```

### 3. Run Tests

```bash
# Quick test run
./scripts/run-tests.sh docker-e2e

# Or with Docker Compose (isolated)
./scripts/run-tests-docker.sh up
```

## Test Execution Options

### Simple Docker Script
```bash
# All tests
./scripts/run-tests.sh docker-e2e

# Specific tests
./scripts/run-tests.sh docker-e2e -- --grep "Navigation"

# Manual test guide
./scripts/run-tests.sh manual
```

### Docker Compose (Isolated Environment)
```bash
# Run all tests (starts services automatically)
./scripts/run-tests-docker.sh up

# Run in UI mode
./scripts/run-tests-docker.sh ui

# Run specific tests
./scripts/run-tests-docker.sh up -- --grep "Control"

# Clean up
./scripts/run-tests-docker.sh clean
```

## View Results

```bash
# HTML report
open playwright-report/index.html

# Test results
ls test-results/
```

## Common Issues

### Services Not Accessible
```bash
# Check services are running
curl http://localhost:5173
curl http://localhost:8010/api/health
```

### Permission Denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

### Build Fails
```bash
# Rebuild test image
docker build -f docker/Dockerfile.test -t dsa110-test:latest .
```

## Next Steps

- **Full Test Plan**: See [COMPREHENSIVE_TESTING_PLAN.md](./COMPREHENSIVE_TESTING_PLAN.md)
- **Docker Details**: See [DOCKER_TESTING_GUIDE.md](./DOCKER_TESTING_GUIDE.md)
- **E2E Tests**: See [tests/e2e/README.md](../tests/e2e/README.md)

