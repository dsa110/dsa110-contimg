# CI/CD E2E Test Integration

## Overview

This document describes how to integrate Docker-based E2E tests into CI/CD pipelines.

---

## GitHub Actions

### Workflow File

Created: `.github/workflows/e2e-tests.yml`

### Features

- ✅ Runs on push/PR to main/develop branches
- ✅ Only triggers when frontend or E2E test files change
- ✅ Starts frontend dev server automatically
- ✅ Runs E2E tests in Docker
- ✅ Uploads test reports as artifacts
- ✅ Cleans up server on completion

### Usage

The workflow runs automatically when:
- Code is pushed to `main` or `develop` branches
- PRs are opened targeting `main` or `develop`
- Files in `frontend/` or `tests/e2e/` are modified

### Manual Trigger

```bash
# Via GitHub UI: Actions tab → E2E Tests → Run workflow
```

---

## GitLab CI

### Configuration

Created: `.gitlab-ci.yml.e2e`

### Features

- ✅ Uses Docker-in-Docker (DinD)
- ✅ Starts frontend dev server automatically
- ✅ Runs E2E tests in Docker
- ✅ Saves test reports as artifacts
- ✅ Only runs when relevant files change

### Integration

Add to your existing `.gitlab-ci.yml`:

```yaml
include:
  - local: '.gitlab-ci.yml.e2e'
```

Or copy the `e2e-tests` job directly into your `.gitlab-ci.yml`.

---

## Jenkins

### Pipeline Script

```groovy
pipeline {
    agent any
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Install Dependencies') {
            steps {
                dir('frontend') {
                    sh 'npm ci'
                }
            }
        }
        
        stage('Start Frontend Server') {
            steps {
                dir('frontend') {
                    sh 'npm run dev > /tmp/frontend-dev.log 2>&1 &'
                    sh 'echo $! > /tmp/frontend-dev.pid'
                    sh '''
                        timeout 60 bash -c '
                            until curl -f http://localhost:5173 > /dev/null 2>&1; do
                                sleep 2
                            done
                        ' || exit 1
                    '''
                }
            }
        }
        
        stage('Run E2E Tests') {
            environment {
                BASE_URL = 'http://localhost:5173'
            }
            steps {
                dir('frontend') {
                    sh 'docker compose -f docker-compose.test.yml --profile e2e run --rm frontend-e2e'
                }
            }
        }
        
        stage('Cleanup') {
            steps {
                sh 'kill $(cat /tmp/frontend-dev.pid) || true'
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'frontend/playwright-report/**/*', fingerprint: true
            archiveArtifacts artifacts: 'frontend/test-results/**/*', fingerprint: true
        }
    }
}
```

---

## Local Development

### Quick Test Run

```bash
# Terminal 1: Start frontend server
cd frontend
npm run dev

# Terminal 2: Run E2E tests
make frontend-test-e2e-docker
```

### With Docker Compose (All-in-One)

```bash
cd frontend

# Start frontend server
docker compose -f docker-compose.test.yml run --rm -d \
  --service-ports frontend-dev

# Wait for server
sleep 10

# Run E2E tests
docker compose -f docker-compose.test.yml --profile e2e run --rm frontend-e2e

# Stop frontend server
docker compose -f docker-compose.test.yml stop frontend-dev
```

---

## Environment Variables

### Required

- `BASE_URL`: Frontend server URL (default: `http://localhost:5173`)

### Optional

- `CI`: Set to `true` in CI environments (enables retries)
- `PLAYWRIGHT_BROWSERS_PATH`: Browser cache path (default: `/ms-playwright`)

---

## Test Reports

### HTML Report

After test execution:

```bash
# View report
cd frontend
npx playwright show-report
```

### CI Artifacts

- **GitHub Actions**: Uploaded to Actions artifacts
- **GitLab CI**: Saved as job artifacts
- **Jenkins**: Archived in build artifacts

---

## Troubleshooting

### Frontend Server Not Starting

```bash
# Check logs
cat /tmp/frontend-dev.log

# Check if port is in use
lsof -i :5173

# Kill existing process
kill $(lsof -t -i:5173)
```

### Tests Can't Connect to Frontend

```bash
# Verify server is running
curl http://localhost:5173

# Check BASE_URL environment variable
echo $BASE_URL

# Update playwright.config.ts baseURL if needed
```

### Docker Issues

```bash
# Rebuild image
cd frontend
docker compose -f docker-compose.test.yml build frontend-e2e

# Check Docker daemon
docker info
```

---

## Performance Considerations

### Parallel Execution

Playwright runs tests in parallel by default:
- **Local**: 4 workers
- **CI**: 2 workers (configurable in `playwright.config.ts`)

### Test Timeout

Default timeout: 30 seconds per test
- Adjustable in `playwright.config.ts`
- CI environments may need longer timeouts

### Resource Usage

- Frontend dev server: ~200-500 MB RAM
- Docker container: ~500 MB RAM
- Total: ~1 GB RAM recommended

---

## Best Practices

1. **Run E2E tests on PRs** - Catch issues before merge
2. **Use test retries in CI** - Handle flaky tests
3. **Archive test reports** - Debug failures easily
4. **Monitor test duration** - Optimize slow tests
5. **Use test tags** - Run specific test suites

---

## Next Steps

1. ✅ GitHub Actions workflow created
2. ✅ GitLab CI configuration created
3. ✅ Jenkins pipeline example provided
4. ⏭️ Add to existing CI/CD pipelines
5. ⏭️ Configure test notifications
6. ⏭️ Set up test result dashboards

---

## Related Documentation

- [Docker E2E Setup](e2e_testing_docker.md)
- [Test Optimization Summary](test_optimization_summary.md)
- [Casa6 Test Execution](casa6_test_execution.md)

