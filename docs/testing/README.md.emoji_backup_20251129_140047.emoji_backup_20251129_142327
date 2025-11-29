# Testing Documentation

## Overview

This directory contains comprehensive testing documentation and resources for
the DSA-110 Continuum Imaging Dashboard.

## Documentation Files

### [QUICK_START.md](./QUICK_START.md)

Quick reference for running tests on Ubuntu 18.x with Docker.

### [COMPREHENSIVE_TESTING_PLAN.md](./COMPREHENSIVE_TESTING_PLAN.md)

Complete manual test plan covering all clickable features and user interactions:

- Test cases organized by page/feature
- Expected behaviors and outcomes
- Test execution strategy
- Success criteria

### [DOCKER_TESTING_GUIDE.md](./DOCKER_TESTING_GUIDE.md)

Detailed guide for Docker-based testing:

- Docker setup and configuration
- Network configuration
- Troubleshooting
- CI/CD integration

### Test Execution

#### Automated Tests (E2E)

- **Location**: `tests/e2e/`
- **Framework**: Playwright
- **Run**: `./scripts/run-tests.sh e2e` or `npx playwright test`
- **Documentation**: See `tests/e2e/README.md`

#### Manual Tests

- **Location**: `docs/testing/COMPREHENSIVE_TESTING_PLAN.md`
- **Execution**: Follow test cases manually
- **Run**: `./scripts/run-tests.sh manual` (opens guide)

## Quick Start

### Prerequisites

#### Docker-Based Testing (Ubuntu 18.x - Recommended)

1. Docker installed and running
2. Frontend running on `http://localhost:5173` (or use docker-compose)
3. Backend API running on `http://localhost:8010` (or use docker-compose)
4. User added to docker group: `sudo usermod -aG docker $USER`

#### Local Testing (if Node.js 22+ available)

1. Node.js 22+ and npm installed
2. Frontend running on `http://localhost:5173`
3. Backend API running on `http://localhost:8010`
4. Playwright installed:
   `npm install -D @playwright/test && npx playwright install`

### Running Tests

#### Docker-Based (Ubuntu 18.x)

```bash
# Run all tests (E2E in Docker + show manual guide)
./scripts/run-tests.sh all

# Run only E2E tests in Docker
./scripts/run-tests.sh docker-e2e

# Run with Docker Compose (isolated environment)
./scripts/run-tests-docker.sh up

# Run in UI mode
./scripts/run-tests-docker.sh ui

# Show manual test guide
./scripts/run-tests.sh manual
```

#### Local Testing (if Node.js available)

```bash
# Run all tests (E2E + show manual guide)
./scripts/run-tests.sh all

# Run only E2E tests
npx playwright test

# Show manual test guide
./scripts/run-tests.sh manual
```

## Test Coverage

### Pages Tested

- ✅ Navigation Component
- ✅ Dashboard Page
- ✅ Control Page (Convert, Calibrate, Apply, Image tabs)
- ✅ Data Browser Page
- ✅ Data Detail Page
- ✅ Streaming Page
- ✅ Mosaic Gallery Page
- ✅ Source Monitoring Page
- ✅ Sky View Page

### Feature Categories

- ✅ Navigation and Routing
- ✅ Form Interactions
- ✅ Button Actions
- ✅ Table/List Interactions
- ✅ Modal/Dialog Interactions
- ✅ Tab Navigation
- ✅ API Integration
- ✅ Error Handling
- ✅ Accessibility
- ✅ Performance

## Test Statistics

### Manual Test Cases

- **Total Test Cases**: 200+
- **Coverage**: All clickable features and user interactions
- **Organization**: By page and feature

### Automated Tests

- **Test Suites**: 10+
- **Test Cases**: 50+
- **Browsers**: Chromium, Firefox, WebKit
- **Mobile**: Chrome Mobile, Safari Mobile

## Test Execution Workflow

1. **Pre-Test Setup**
   - Verify services are running
   - Check test data availability
   - Review test plan

2. **Test Execution**
   - Run automated E2E tests
   - Execute manual test cases
   - Document results

3. **Post-Test Analysis**
   - Review test results
   - Document failures
   - Create bug reports
   - Update test cases

## Maintenance

### Updating Test Cases

- Update test cases when features change
- Add tests for new features
- Remove obsolete tests
- Keep test data current

### Test Review Schedule

- **Weekly**: Review automated test results
- **Monthly**: Review manual test cases
- **Quarterly**: Comprehensive test plan review

## Best Practices

1. **Test Early and Often**: Run tests during development
2. **Maintain Test Data**: Keep test data up to date
3. **Document Changes**: Update tests when features change
4. **Review Failures**: Investigate and fix test failures promptly
5. **Coverage Goals**: Maintain high test coverage for critical paths

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Testing Best Practices](https://playwright.dev/docs/best-practices)
- [Test Plan](./COMPREHENSIVE_TESTING_PLAN.md)
- E2E Test Guide: `../tests/e2e/README.md` (external file)

## Support

For questions or issues with testing:

1. Review test documentation
2. Check test execution logs
3. Review Playwright documentation
4. Contact development team
