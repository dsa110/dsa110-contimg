# Development Setup TODO List

## Current Phase: Foundation Setup

### Step 1: Create the environment.yml file for casa6 dependencies
- [ ] Create `environment.yml` in project root
- [ ] Document casa6 conda environment dependencies
- [ ] Include Python version (3.11 in casa6 conda environment)
- [ ] Include CASA dependencies
- [ ] Include development tools:
  - [ ] pytest, pytest-cov, pytest-asyncio, pytest-mock
  - [ ] black, flake8, mypy, pylint
  - [ ] bandit, safety (security)
  - [ ] alembic (database migrations)
- [ ] Test environment.yml can be used to recreate environment
- [ ] Document installation instructions

### Step 2: Set up pre-commit hooks with casa6 paths
- [ ] Create `.pre-commit-config.yaml` in project root
- [ ] Configure black hook to use casa6 Python path
- [ ] Configure flake8 hook to use casa6 Python path
- [ ] Configure mypy hook to use casa6 Python path
- [ ] Configure bandit hook to use casa6 Python path
- [ ] Add frontend hooks (eslint, prettier)
- [ ] Install pre-commit: `pip install pre-commit` (in casa6 or system)
- [ ] Install hooks: `pre-commit install`
- [ ] Test hooks work correctly
- [ ] Update documentation with pre-commit setup instructions

### Step 3: Start implementing Phase 1 (testing infrastructure, CI/CD basics)
- [ ] **3.1: Testing Infrastructure**
  - [ ] Install pytest in casa6: `conda install -c conda-forge pytest pytest-cov pytest-asyncio pytest-mock`
  - [ ] Create `tests/unit/` directory structure
  - [ ] Create test fixtures and factories
  - [ ] Set up test database configuration
  - [ ] Write unit tests for critical modules:
    - [ ] `data_registry.py`
    - [ ] `pipeline/stages_impl.py`
    - [ ] `api/routes.py`
    - [ ] `websocket_manager.py`
  - [ ] Set up pytest-cov for coverage reporting
  - [ ] Configure coverage thresholds (80% critical, 60% overall)
  - [ ] Update Makefile to use `$(CASA6_PYTHON)` for test commands
  - [ ] Verify tests run successfully

- [ ] **3.2: CI/CD Basics**
  - [ ] Create `.github/workflows/` directory
  - [ ] Create `.github/workflows/pre-commit.yml` (using casa6 Python)
  - [ ] Create `.github/workflows/pr-checks.yml` (using casa6 Python)
  - [ ] Configure automated testing on PR (all Python steps use casa6)
  - [ ] Set up code coverage checks (using casa6 Python)
  - [ ] Ensure CI environment has casa6 conda environment available
  - [ ] Test CI workflows locally (using act or similar)
  - [ ] Document CI/CD setup

## Future Phases

### Phase 2: Quality & Monitoring
- [ ] Complete unit test coverage (using casa6 Python)
- [ ] Set up error tracking (Sentry)
- [ ] Set up monitoring
- [ ] Fix E2E tests
- [ ] Update all scripts/Makefile to use casa6 Python

### Phase 3: Security & Database
- [ ] Set up database migrations (Alembic in casa6)
- [ ] Configure security scanning (bandit in casa6)
- [ ] Audit and harden security
- [ ] Set up backups
- [ ] Create environment.yml for casa6 dependencies

### Phase 4: Documentation & Polish
- [ ] Complete documentation (including casa6 requirements)
- [ ] Performance testing (using casa6 Python)
- [ ] Advanced monitoring
- [ ] Disaster recovery planning
- [ ] Verify all tools work with casa6 environment

## Notes

- All Python operations MUST use `/opt/miniforge/envs/casa6/bin/python`
- Makefile already defines `CASA6_PYTHON` variable
- See `docs/CASA6_ENVIRONMENT_GUIDE.md` for detailed casa6 setup instructions
- See `docs/DEVELOPMENT_ROADMAP.md` for comprehensive strategy
- See `docs/IMPLEMENTATION_CHECKLIST.md` for detailed checklist

## Progress Tracking

- **Total Steps**: 3 main steps
- **Completed**: 0
- **In Progress**: 0
- **Remaining**: 3

Last Updated: 2025-11-09

