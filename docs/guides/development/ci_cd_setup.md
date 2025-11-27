# CI/CD Setup Documentation

This document describes the CI/CD pipeline configuration and workflows.

## Overview

The project uses GitHub Actions for continuous integration and deployment. All
workflows use the casa6 conda environment for Python operations.

## Workflow Files

### Core Workflows

1. **pre-commit.yml**: Runs pre-commit hooks (Python + Frontend)
2. **pr-checks.yml**: Comprehensive PR checks (tests, linting, coverage)
3. **validation-tests.yml**: Unit and integration tests
4. **docs-minimal.yml**: Builds and deploys documentation

### Additional Workflows

- `codeql-analysis.yml`: Security analysis
- `e2e-tests.yml`: End-to-end tests
- `frontend-integration-tests.yml`: Frontend tests
- `prettier-check.yml`: Code formatting checks
- `environment-validation.yml`: Environment validation

## Workflow Details

### Pre-commit Workflow

**File**: `.github/workflows/pre-commit.yml`

**Purpose**: Validates code quality before merge

**Triggers**:

- Pull requests (on Python/JS/TS/JSON/YAML/MD changes)
- Pushes to main/develop

**Steps**:

1. Sets up casa6 conda environment
2. Runs Python hooks (black, isort, pylint)
3. Runs frontend hooks (prettier, eslint)

### PR Checks Workflow

**File**: `.github/workflows/pr-checks.yml`

**Purpose**: Comprehensive quality checks for pull requests

**Triggers**:

- Pull requests (on code/test changes)
- Pushes to main/develop

**Jobs**:

#### 1. Python Checks

- Linting (flake8)
- Type checking (mypy)
- Security scanning (bandit)
- Unit tests with coverage
- Coverage threshold validation (60% minimum)

#### 2. Frontend Checks

- Linting (ESLint)
- Type checking (TypeScript)
- Unit tests with coverage

#### 3. Integration Checks

- Integration tests (non-slow tests)

### Validation Tests Workflow

**File**: `.github/workflows/validation-tests.yml`

**Purpose**: Runs comprehensive test suite

**Triggers**:

- Pull requests
- Pushes to main/dev
- Scheduled (daily at 02:00 UTC)
- Manual dispatch

**Jobs**:

- Fast tests (impacted/fail-fast)
- Unit tests (mocked)
- Integration tests
- Validation tests

## Casa6 Environment Setup

All Python workflows use the casa6 conda environment:

```yaml
- name: Set up Miniforge
  uses: conda-incubator/setup-miniforge@v3
  with:
    miniforge-version: latest
    activate-environment: casa6
    python-version: "3.11"

- name: Create casa6 conda environment
  run: |
    conda env create -f env/environment.yml
    conda activate casa6
```

## Coverage Requirements

### Overall Coverage

- **Minimum**: 60% (configured in `pytest.ini` and `pyproject.toml`)
- **Enforced**: In PR checks workflow

### Critical Modules

These modules should aim for 80% coverage:

- `src/dsa110_contimg/api/routes.py`
- `src/dsa110_contimg/database/data_registry.py`
- `src/dsa110_contimg/pipeline/stages_impl.py`
- `src/dsa110_contimg/api/websocket_manager.py`

## Running Workflows Locally

### Using Act (GitHub Actions Local Runner)

```bash
# Install act
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# List workflows
act -l

# Run specific workflow
act pull_request -W .github/workflows/pr-checks.yml

# Run with casa6 environment (requires Docker)
act pull_request --container-architecture linux/amd64
```

### Manual Local Testing

```bash
# Run the same commands as CI
conda activate casa6

# Run linting
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
mypy src/ --ignore-missing-imports --no-strict-optional
bandit -r src/ -f json --skip B101,B601

# Run tests with coverage
pytest tests/unit/ --cov=src --cov-report=xml --cov-fail-under=60
```

## Workflow Status

View workflow status:

- GitHub Actions tab: `https://github.com/dsa110/dsa110-contimg/actions`
- PR checks: Visible in pull request status checks

## Troubleshooting

### Workflow Fails: "Conda environment not found"

**Solution**: Ensure `env/environment.yml` exists and is valid:

```bash
# Validate environment file
conda env create -f env/environment.yml --dry-run
```

### Workflow Fails: "Coverage below threshold"

**Solution**: Increase test coverage:

```bash
# Check current coverage
pytest tests/unit/ --cov=src --cov-report=term

# Aim for 60% overall, 80% for critical modules
```

### Workflow Fails: "Linting errors"

**Solution**: Fix linting issues locally:

```bash
conda activate casa6

# Auto-fix formatting
black src/
isort src/

# Check linting
flake8 src/
pylint src/
```

### Workflow Times Out

**Solution**:

- Split large test suites into separate jobs
- Use test parallelization (`pytest-xdist`)
- Mark slow tests with `@pytest.mark.slow`

## Best Practices

1. **Run checks locally first**: Don't rely only on CI
2. **Fix issues before pushing**: Address linting/type errors locally
3. **Monitor coverage**: Keep coverage above thresholds
4. **Review workflow logs**: Check detailed logs for failures
5. **Keep workflows fast**: Optimize slow workflows

## Related Documentation

- Environment Setup
- [Pre-commit Setup](PRE_COMMIT_SETUP.md)
- [Testing Guide](../qa/PIPELINE_TESTING_GUIDE.md)
