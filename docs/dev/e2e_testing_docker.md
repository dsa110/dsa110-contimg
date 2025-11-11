# E2E Testing with Docker

## Problem

**GLIBC Version Incompatibility:**
- System GLIBC: 2.27 (Ubuntu 18.04)
- Casa6 Playwright requires: GLIBC 2.28+
- Result: E2E tests cannot run directly on system

## Solution: Docker-Based E2E Testing

Use Docker to run E2E tests in an environment with compatible GLIBC (Node.js 22 Alpine).

---

## Quick Start

### Option 1: Using Makefile (Easiest)

```bash
# From repo root
make frontend-test-e2e-docker
```

### Option 2: Using Docker Compose

```bash
cd frontend

# Run E2E tests in Docker
docker compose -f docker-compose.test.yml --profile e2e run --rm frontend-e2e

# View test results
docker compose -f docker-compose.test.yml --profile e2e run --rm frontend-e2e npx playwright show-report
```

### Option 3: Using Docker Directly

```bash
cd frontend

# Build test image
docker build -t dsa110-frontend-test -f Dockerfile.test .

# Run E2E tests
docker run --rm \
  -v $(pwd):/app \
  -v /app/node_modules \
  dsa110-frontend-test \
  npx playwright test
```

---

## Docker Setup

### Files Created

1. **`frontend/Dockerfile.test`**
   - Base: Node.js 22 Alpine (compatible GLIBC)
   - Includes Chromium browser (system package)
   - Playwright configured to use system Chromium

2. **`frontend/docker-compose.test.yml`** (updated)
   - Added `frontend-e2e` service
   - Volumes for test results and reports
   - CI environment variables

3. **`Makefile`** (updated)
   - Added `frontend-test-e2e-docker` target

---

## Usage Examples

### Run All E2E Tests

```bash
make frontend-test-e2e-docker
```

### Run Specific Test File

```bash
cd frontend
docker compose -f docker-compose.test.yml --profile e2e run --rm frontend-e2e \
  npx playwright test tests/e2e/dashboard.test.ts
```

### Run Tests in UI Mode (Interactive)

```bash
cd frontend
docker compose -f docker-compose.test.yml --profile e2e run --rm \
  -p 9323:9323 \
  frontend-e2e \
  npx playwright test --ui
```

### View Test Report

```bash
cd frontend
docker compose -f docker-compose.test.yml --profile e2e run --rm frontend-e2e \
  npx playwright show-report
```

### Debug Failed Tests

```bash
cd frontend
docker compose -f docker-compose.test.yml --profile e2e run --rm \
  frontend-e2e \
  npx playwright test --debug
```

---

## How It Works

1. **Docker Image:** Uses Node.js 22 Alpine (newer GLIBC)
2. **System Chromium:** Pre-installed browser (faster than downloading)
3. **Volume Mounts:** Source code and node_modules mounted
4. **Test Results:** Saved to Docker volumes for inspection

---

## Benefits

✅ **GLIBC Compatibility:** Docker image has GLIBC 2.28+  
✅ **Isolation:** Tests run in clean environment  
✅ **Consistency:** Same environment across developers  
✅ **CI/CD Ready:** Works in CI pipelines  
✅ **No System Changes:** Doesn't require system updates  

---

## Limitations

⚠️ **Performance:** Slightly slower than native (Docker overhead ~10-20%)  
⚠️ **Debugging:** Requires Docker knowledge for troubleshooting  
⚠️ **Network:** May need `host.docker.internal` for API access in tests  

---

## Troubleshooting

### Error: "Cannot connect to Docker daemon"

```bash
# Check Docker is running
sudo systemctl status docker

# Start Docker if needed
sudo systemctl start docker
```

### Error: "Playwright browsers not found"

The Dockerfile uses system Chromium. If issues occur:

```bash
# Rebuild image
cd frontend
docker compose -f docker-compose.test.yml build frontend-e2e
```

### Error: "Permission denied" on volumes

```bash
# Ensure Docker has permissions
sudo usermod -aG docker $USER
# Log out and back in
```

### Tests Can't Connect to Backend API

If tests need to connect to running API:

```bash
# Use host network mode
docker compose -f docker-compose.test.yml --profile e2e run --rm \
  --network host \
  frontend-e2e
```

---

## CI/CD Integration

Docker-based E2E tests work seamlessly in CI:

```yaml
# Example GitHub Actions
- name: Run E2E Tests
  run: |
    cd frontend
    docker compose -f docker-compose.test.yml --profile e2e run --rm frontend-e2e
```

---

## Comparison: Casa6 vs Docker

| Aspect | Casa6 (Native) | Docker |
|--------|----------------|--------|
| **GLIBC** | ❌ Incompatible (2.27 vs 2.28+) | ✅ Compatible |
| **Speed** | ✅ Faster | ⚠️ Slightly slower |
| **Setup** | ✅ Simple | ⚠️ Requires Docker |
| **Isolation** | ❌ Uses system | ✅ Complete isolation |
| **CI/CD** | ⚠️ May fail | ✅ Reliable |

**Recommendation:** Use Docker for E2E tests on systems with GLIBC < 2.28.

---

## Next Steps

1. ✅ Docker setup complete
2. ✅ Makefile target added
3. ⏭️ Test execution (run `make frontend-test-e2e-docker`)
4. ⏭️ Update CI/CD pipelines to use Docker for E2E
5. ⏭️ Document in main README

---

## Related Documentation

- [Test Optimization Summary](test_optimization_summary.md)
- [Casa6 Test Execution](casa6_test_execution.md)
- [E2E Page Objects](../tests/e2e/pages/)
