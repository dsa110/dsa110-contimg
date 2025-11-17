# Frontend Testing with Docker

**Date:** 2025-11-14

## Quick Start

### Option 1: Use Test Script (Easiest)

```bash
cd frontend

# Run tests once
./test.sh

# Run tests in watch mode (auto-reruns on file changes)
./test.sh watch

# Run tests with UI
./test.sh ui

# Run tests with coverage
./test.sh coverage
```

### Option 2: Use Docker Directly

```bash
cd frontend

# Build image (first time only)
docker build -t dsa110-frontend-test -f Dockerfile.dev .

# Run tests
docker run --rm -v "$PWD:/app" -v /app/node_modules dsa110-frontend-test npm test

# Run tests in watch mode
docker run --rm -it -v "$PWD:/app" -v /app/node_modules dsa110-frontend-test npm test -- --watch
```

### Option 3: Use Conda Environment (if Node 22+ available)

```bash
# Activate casa6 conda environment (has Node 22.6.0)
conda activate casa6

# Install dependencies
cd frontend
npm install

# Run tests
npm test
```

## Benefits of Docker Approach

✅ **No Node version conflicts** - Uses Node 22 in Docker  
✅ **Consistent environment** - Same setup everywhere  
✅ **Isolated dependencies** - Doesn't affect host system  
✅ **Easy CI/CD** - Same commands work in CI pipelines

## Writing Tests

When you find a bug, write a test first:

```typescript
// In useSelectionState.test.ts
it("should handle unchecking checkbox", () => {
  const result = computeSelectedMS(
    [], // paths (empty after uncheck)
    ["/data/ms1.ms"], // prevList (had one selected)
    "/data/ms1.ms" // currentSelectedMS
  );
  expect(result).toBe(""); // Should be empty
});
```

Then fix the code and verify the test passes.

## Troubleshooting

**Docker not found:**

```bash
# Check Docker is installed
docker --version

# If not installed, use conda environment instead
conda activate casa6
node --version  # Should be 22.6.0
```

**Tests fail:**

```bash
# Rebuild Docker image
docker build --no-cache -t dsa110-frontend-test -f Dockerfile.dev .

# Or check if dependencies are installed correctly
docker run --rm -v "$PWD:/app" dsa110-frontend-test npm ci
```

**Port conflicts:**

```bash
# Change port in test.sh if 51204 is in use
# Or use different port:
docker run --rm -it -v "$PWD:/app" -v /app/node_modules -p 3000:51204 dsa110-frontend-test npm test -- --ui
```
