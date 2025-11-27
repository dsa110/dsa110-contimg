# Test Coverage Improvement Plan

Based on the coverage analysis, this document outlines a prioritized plan to
improve test coverage from 19% to 80%+.

## Current Status

- **Overall Coverage:** 19% (420/2,170 statements)
- **Critical Gaps:** 11 modules below 50% coverage
- **Zero Coverage:** 3 modules (health.py, signals.py, timeout.py)

## Improvement Strategy

### Phase 1: Critical Infrastructure (Weeks 1-2)

**Goal:** Achieve 80%+ coverage for core pipeline infrastructure

#### 1.1 Pipeline Stages (`pipeline/stages_impl.py`)

- **Current:** 8% coverage (87/1,138 statements)
- **Target:** 80%+ coverage
- **Tasks:**
  - [ ] Create comprehensive unit tests for all 9 stage classes
  - [ ] Test `validate()` methods for all stages
  - [ ] Test `execute()` methods with mocked dependencies
  - [ ] Test `cleanup()` methods
  - [ ] Test `validate_outputs()` methods
  - [ ] Add edge case tests (missing inputs, invalid paths, etc.)
  - [ ] Add error handling tests

**Estimated Effort:** 40 hours **Priority:** Critical

#### 1.2 Pipeline Orchestrator (`pipeline/orchestrator.py`)

- **Current:** 26% coverage (42/162 statements)
- **Target:** 80%+ coverage
- **Tasks:**
  - [ ] Test dependency resolution
  - [ ] Test stage execution ordering
  - [ ] Test retry mechanisms
  - [ ] Test error handling and recovery
  - [ ] Test context propagation
  - [ ] Test parallel execution (if applicable)

**Estimated Effort:** 20 hours **Priority:** Critical

#### 1.3 Pipeline Configuration (`pipeline/config.py`)

- **Current:** 49% coverage (86/175 statements)
- **Target:** 80%+ coverage
- **Tasks:**
  - [ ] Test all configuration classes
  - [ ] Test validation logic
  - [ ] Test environment variable parsing
  - [ ] Test default values
  - [ ] Test path validation

**Estimated Effort:** 15 hours **Priority:** High

### Phase 2: Supporting Infrastructure (Weeks 3-4)

**Goal:** Achieve 60%+ coverage for supporting modules

#### 2.1 Zero Coverage Modules

- **`pipeline/health.py`** (0% coverage)
  - [ ] Add unit tests for health checks
  - [ ] Test monitoring functionality
  - [ ] Test diagnostic endpoints
- **`pipeline/signals.py`** (0% coverage)
  - [ ] Test signal handlers
  - [ ] Test event propagation
  - [ ] Test error handling

- **`pipeline/timeout.py`** (0% coverage)
  - [ ] Test timeout logic
  - [ ] Test timeout expiration
  - [ ] Test timeout cancellation

**Estimated Effort:** 20 hours **Priority:** Medium

#### 2.2 Low Coverage Modules

- **`pipeline/adapter.py`** (25% coverage)
- **`pipeline/resources.py`** (25% coverage)
- **`pipeline/workflows.py`** (32% coverage)
- **`pipeline/observability.py`** (36% coverage)
- **`pipeline/state.py`** (46% coverage)

**Estimated Effort:** 30 hours **Priority:** Medium

### Phase 3: Integration and Edge Cases (Weeks 5-6)

**Goal:** Improve integration test coverage and edge case handling

#### 3.1 Integration Tests

- [ ] Test full pipeline execution end-to-end
- [ ] Test stage interactions
- [ ] Test error propagation
- [ ] Test recovery scenarios

#### 3.2 Edge Cases

- [ ] Test with missing inputs
- [ ] Test with invalid configurations
- [ ] Test with large datasets
- [ ] Test with concurrent executions

**Estimated Effort:** 25 hours **Priority:** Medium

## Testing Best Practices

### Unit Testing

- Use `pytest` framework
- Mock external dependencies (CASA, file I/O)
- Test one thing per test
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

### Integration Testing

- Use real dependencies where possible
- Test stage interactions
- Test error handling
- Use fixtures for common setup

### Coverage Goals

- **Critical modules:** 80%+ coverage
- **Supporting modules:** 60%+ coverage
- **Overall:** 70%+ coverage

## Tools and Commands

### Generate Coverage Report

```bash
pytest --cov=src/dsa110_contimg --cov-report=term-missing --cov-report=html:tests/coverage_html tests/
```

### View HTML Coverage Report

```bash
# Open tests/coverage_html/index.html in browser
```

### Analyze Coverage Gaps

```bash
/opt/miniforge/envs/casa6/bin/python scripts/analyze_coverage.py
```

### Run Specific Test Suite

```bash
# Unit tests only
pytest tests/unit -m unit

# Integration tests only
pytest tests/integration -m integration

# Specific module
pytest tests/unit/test_pipeline_stages_comprehensive.py
```

## Success Metrics

- [ ] Overall coverage: 70%+
- [ ] Critical modules: 80%+
- [ ] Zero coverage modules eliminated
- [ ] All new code has tests
- [ ] CI/CD enforces coverage thresholds

## Related Documentation

- [Test Coverage Analysis](test_coverage_analysis.md)
- Testing Guide
- [Pipeline Stage Architecture](../architecture/pipeline/pipeline_stage_architecture.md)
