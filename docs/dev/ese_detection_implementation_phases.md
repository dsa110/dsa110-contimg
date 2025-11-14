# ESE Detection Improvements - Implementation Phases

## Date: 2025-11-12

This document divides the comprehensive ESE detection improvements into logical
implementation phases. Each phase builds upon previous phases and can be
implemented independently.

**Reference**: See `ese_detection_comprehensive_improvements.md` for detailed
technical specifications.

---

## Phase Overview

| Phase       | Name                     | Focus                                   | Duration  | Dependencies     |
| ----------- | ------------------------ | --------------------------------------- | --------- | ---------------- |
| **Phase 1** | Foundation & Quality     | Code quality, testing, shared utilities | 1-2 weeks | None             |
| **Phase 2** | Detection Enhancement    | Multi-metric scoring, threshold presets | 1-2 weeks | Phase 1          |
| **Phase 3** | Performance Optimization | Caching, parallel processing            | 1-2 weeks | Phase 1          |
| **Phase 4** | Advanced Analysis        | Multi-frequency, multi-observable       | 2-3 weeks | Phase 2, Phase 3 |

**Total Estimated Duration**: 5-9 weeks (depending on team size and priorities)

---

## General Implementation Guidelines

### Before Starting Any Task

1. **Read the Comprehensive Specification**
   - Review `ese_detection_comprehensive_improvements.md` for detailed technical
     specifications
   - Understand the scientific rationale and mathematical definitions
   - Review existing code to understand current implementation

2. **Set Up Development Environment**
   - Ensure `casa6` Python environment is active:
     `/opt/miniforge/envs/casa6/bin/python`
   - Verify all dependencies installed:
     `pip list | grep -E "(numpy|pandas|astropy|sqlite3)"`
   - Run existing tests to ensure baseline:
     `/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/ -v`

3. **Create Feature Branch**
   - Branch naming: `feature/ese-improvements-phase{N}-task{M}`
   - Example: `feature/ese-improvements-phase1-task1.1`

### During Implementation

1. **Follow Task Breakdown Order**
   - Complete subtasks in the order listed
   - Each subtask should be independently testable
   - Commit after each major subtask completion

2. **Write Tests First (TDD Approach)**
   - Write test cases before implementation when possible
   - Tests serve as specification
   - Run tests frequently during development

3. **Verify Integration Points**
   - Check all integration points listed in task
   - Use `grep` to find all usages before modifying
   - Test integration points after changes

4. **Document as You Go**
   - Update docstrings immediately
   - Add comments for complex logic
   - Update architecture docs if structure changes

### Code Quality Standards

1. **Type Hints**: All functions must have complete type hints
2. **Docstrings**: Use Google-style docstrings with Args, Returns, Raises,
   Examples
3. **Error Handling**: Use specific exceptions, informative error messages
4. **Testing**: Aim for 100% coverage for new code, >90% for modified code
5. **Style**: Follow existing codebase style (use `black` formatter if
   available)

### Unit and Smoke Testing Strategy

**Objective**: Develop comprehensive unit and smoke tests with emphasis on speed
and efficiency.

**Principles**:

- **Speed**: Unit tests should complete in < 1 second each, full suite in < 30
  seconds
- **Isolation**: Each test is independent, no shared state
- **Targeted**: Tests validate specific functionality, not integration
- **Fast Failure**: Detect and report failures immediately
- **Minimal Overhead**: Use mocks/fixtures instead of real I/O when possible

**Test Categories**:

1. **Unit Tests** (`tests/unit/`):
   - Test individual functions/methods in isolation
   - Use mocks for external dependencies (database, file I/O, network)
   - Fast execution (< 100ms per test)
   - High coverage (> 95% for new code)

2. **Smoke Tests** (`tests/smoke/` or `tests/unit/*_smoke.py`):
   - Test critical paths end-to-end
   - Use minimal real dependencies (test database, test files)
   - Verify system works at basic level
   - Fast execution (< 5 seconds per test)

**Test Checklist** (for each new feature):

- [ ] Unit tests for core functionality (3-7 test cases)
- [ ] Unit tests for edge cases (empty input, None values, boundary conditions)
- [ ] Unit tests for error handling (invalid input, exceptions)
- [ ] Smoke test for critical path (end-to-end basic flow)
- [ ] All tests pass independently
- [ ] Test execution time < 30 seconds total
- [ ] Coverage > 95% for new code

**Test Design Guidelines**:

1. **Before Writing Tests**:
   - Identify the specific functionality to test
   - Determine expected behavior and edge cases
   - Plan test data (use fixtures for reusability)
   - Consider what to mock (database, file I/O, external APIs)

2. **Test Structure**:

   ```python
   def test_feature_name():
       """Test description - what it validates."""
       # Arrange: Set up test data
       # Act: Execute function
       # Assert: Verify results
   ```

3. **Error Handling in Tests**:
   - Use `pytest.raises()` for expected exceptions
   - Verify exception messages are informative
   - Test error recovery paths

4. **Validation After Writing**:
   - Run test individually: `pytest tests/unit/path/to/test.py::test_name -v`
   - Run full suite: `pytest tests/unit/ -v --tb=short`
   - Check coverage: `pytest --cov=module --cov-report=term-missing`
   - Fix any failures immediately

**Performance Targets**:

- Unit test: < 100ms per test
- Smoke test: < 5 seconds per test
- Full unit suite: < 30 seconds
- Full smoke suite: < 2 minutes

### Verification Checklist (Before PR)

- [ ] **Unit Tests**:
  - [ ] All unit tests pass: `pytest tests/unit/photometry/ -v --tb=short`
  - [ ] Unit tests complete in < 30 seconds total
  - [ ] Individual unit tests < 100ms each
- [ ] **Smoke Tests**:
  - [ ] All smoke tests pass: `pytest tests/unit/photometry/ -k smoke -v`
  - [ ] Smoke tests complete in < 2 minutes total
  - [ ] Individual smoke tests < 5 seconds each
- [ ] **Test Coverage**:
  - [ ] Coverage meets requirements:
        `pytest --cov=... --cov-report=term-missing`
  - [ ] New code coverage > 95%
  - [ ] Modified code coverage > 90%
- [ ] **Fast Failure**:
  - [ ] Tests stop on first failure: `pytest -x -v`
  - [ ] Error messages are informative
- [ ] **Code Quality**:
  - [ ] Code follows style guidelines
  - [ ] All acceptance criteria met
  - [ ] Integration points verified
  - [ ] Documentation updated
  - [ ] No regressions introduced

### Common Pitfalls to Avoid

1. **Modifying Multiple Files Simultaneously**: Make one logical change at a
   time
2. **Skipping Tests**: Always write tests, even for "simple" changes
3. **Ignoring Edge Cases**: Edge cases are where bugs hide
4. **Breaking Backward Compatibility**: Ensure existing APIs still work
5. **Incomplete Documentation**: Future you will thank present you

---

## Phase 1: Foundation & Quality

**Duration**: 1-2 weeks  
**Priority**: Critical (foundation for all other improvements)  
**Dependencies**: None

### Objectives

1. Establish code quality standards and shared utilities
2. Create comprehensive test suite for validation
3. Fix inconsistencies and improve maintainability
4. Ensure statistical correctness

### Tasks

#### 1.1 Extract Shared Sigma Deviation Function

**Effort**: 2-3 days  
**File Locations**:

- Implementation: `src/dsa110_contimg/photometry/variability.py`
- Tests: `tests/unit/photometry/test_variability.py`
- Integration points:
  - `src/dsa110_contimg/photometry/ese_pipeline.py` (line ~150-200)
  - `src/dsa110_contimg/photometry/ese_detection.py` (line ~200-250)

**Task Breakdown**:

1. **Create Function Signature** (30 min)
   - [ ] Add function to `src/dsa110_contimg/photometry/variability.py`
   - [ ] Function signature:
         `def calculate_sigma_deviation(fluxes: np.ndarray, mean_flux: Optional[float] = None, std_flux: Optional[float] = None) -> float:`
   - [ ] Reference implementation: See
         `ese_detection_comprehensive_improvements.md` Section 1.1

2. **Implement Core Logic** (2 hours)
   - [ ] Input validation:
     - [ ] Empty array raises `ValueError`
     - [ ] NaN/Inf values filtered out
     - [ ] Minimum 2 measurements required (return 0.0 if < 2)
   - [ ] Calculate mean/std if not provided (use `np.mean`, `np.std` with
         `ddof=1`)
   - [ ] Handle zero variance case (return 0.0)
   - [ ] Calculate max deviation:
         `max(abs(max_flux - mean_flux), abs(min_flux - mean_flux)) / std_flux`

3. **Add Documentation** (1 hour)
   - [ ] Docstring includes:
     - [ ] Mathematical definition:
           `σ_dev = max(|max(flux) - μ|, |min(flux) - μ|) / σ`
     - [ ] Parameter descriptions with types
     - [ ] Return value description
     - [ ] Edge case behavior (empty, NaN, zero variance)
     - [ ] At least 3 usage examples

4. **Write Unit Tests** (3-4 hours)
   - [ ] Test file: `tests/unit/photometry/test_variability.py`
   - [ ] Test class: `TestCalculateSigmaDeviation`
   - [ ] **Unit Test Checklist**:
     - [ ] Core functionality tests (3-7 cases)
     - [ ] Edge case tests (empty, None, boundaries)
     - [ ] Error handling tests (invalid input, exceptions)
     - [ ] Smoke test for integration
   - [ ] **Required Unit Test Cases**:
     - [ ] `test_basic_calculation()` - Verify against manual calculation
       - [ ] Input: `fluxes = [1.0, 2.0, 3.0, 4.0, 5.0]`
       - [ ] Expected: ≈ 1.414 (manual calculation)
       - [ ] Execution time: < 10ms
     - [ ] `test_symmetric_deviations()` - Both positive and negative deviations
       - [ ] Input: Symmetric distribution around mean
       - [ ] Expected: Maximum deviation captured correctly
       - [ ] Execution time: < 10ms
     - [ ] `test_zero_variance()` - Returns 0.0 for identical values
       - [ ] Input: `fluxes = [1.0, 1.0, 1.0]`
       - [ ] Expected: 0.0
       - [ ] Execution time: < 5ms
     - [ ] `test_single_measurement()` - Returns 0.0 for single value
       - [ ] Input: `fluxes = [1.0]`
       - [ ] Expected: 0.0 (need multiple measurements)
       - [ ] Execution time: < 5ms
     - [ ] `test_negative_fluxes()` - Handles negative values correctly
       - [ ] Input: `fluxes = [-1.0, 0.0, 1.0]`
       - [ ] Expected: Valid sigma deviation > 0
       - [ ] Execution time: < 10ms
     - [ ] `test_nan_handling()` - Filters NaN values
       - [ ] Input: `fluxes = [1.0, 2.0, np.nan, 4.0, 5.0]`
       - [ ] Expected: NaN filtered, valid result
       - [ ] Execution time: < 10ms
     - [ ] `test_precomputed_statistics()` - Works with provided mean/std
       - [ ] Input: Pre-computed mean=3.0, std=1.414
       - [ ] Expected: Same result as auto-computed
       - [ ] Execution time: < 5ms
     - [ ] `test_edge_case_large_deviations()` - Handles extreme outliers
       - [ ] Input: `fluxes = [1.0, 2.0, 3.0, 4.0, 100.0]`
       - [ ] Expected: Large sigma deviation detected
       - [ ] Execution time: < 10ms
     - [ ] `test_empty_array()` - Raises ValueError for empty input
       - [ ] Input: `fluxes = []`
       - [ ] Expected: `ValueError` raised
       - [ ] Execution time: < 5ms
     - [ ] `test_all_nan()` - Raises ValueError for all NaN
       - [ ] Input: `fluxes = [np.nan, np.nan, np.nan]`
       - [ ] Expected: `ValueError` raised
       - [ ] Execution time: < 5ms
   - [ ] **Smoke Test**:
     - [ ] `test_sigma_deviation_smoke()` - End-to-end integration test
       - [ ] Use function in context of ESE detection
       - [ ] Verify integration with `ese_pipeline.py` and `ese_detection.py`
       - [ ] Execution time: < 100ms
   - [ ] Test coverage target: 100% for this function
   - [ ] Total test execution time: < 100ms for all unit tests

5. **Update Integration Points** (2 hours)
   - [ ] Update `ese_pipeline.py`:
     - [ ] Find inline sigma deviation calculation (search for
           `sigma_deviation =`)
     - [ ] Replace with:
           `from dsa110_contimg.photometry.variability import calculate_sigma_deviation`
     - [ ] Replace calculation with function call
     - [ ] Verify no other sigma deviation calculations remain
   - [ ] Update `ese_detection.py`:
     - [ ] Find `_recompute_variability_stats()` function
     - [ ] Replace inline calculation with function call
     - [ ] Verify consistency

6. **Verification Steps** (1 hour)
   - [ ] **Run Unit Tests**:
     - [ ] Run new unit tests:
           `/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_variability.py::TestCalculateSigmaDeviation -v --tb=short`
     - [ ] Verify execution time:
           `pytest tests/unit/photometry/test_variability.py::TestCalculateSigmaDeviation --durations=0`
     - [ ] All tests should complete in < 100ms total
   - [ ] **Run Smoke Test**:
     - [ ] Run smoke test:
           `/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_variability.py::test_sigma_deviation_smoke -v`
     - [ ] Verify smoke test completes in < 100ms
   - [ ] **Run Existing Tests** (regression check):
     - [ ] `/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/ -v --tb=short`
     - [ ] All existing tests should still pass
   - [ ] **Test Coverage**:
     - [ ] `/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_variability.py --cov=dsa110_contimg/photometry/variability --cov-report=term-missing`
     - [ ] Verify 100% coverage for `calculate_sigma_deviation`
   - [ ] **Manual Verification**:
     - [ ] Test with known values: `fluxes = [1.0, 2.0, 3.0, 4.0, 5.0]` →
           expected ≈ 1.414
     - [ ] Test with zero variance: `fluxes = [1.0, 1.0, 1.0]` → expected 0.0
   - [ ] **Code Quality Checks**:
     - [ ] Check code duplication:
           `grep -r "sigma_deviation.*=" src/dsa110_contimg/photometry/` should
           only show function definition
     - [ ] Check for inline calculations:
           `grep -r "abs.*max_flux.*mean_flux" src/dsa110_contimg/photometry/`
           should only show function definition
   - [ ] **Fast Failure Validation**:
     - [ ] Run tests with `-x` flag to stop on first failure:
           `pytest tests/unit/photometry/test_variability.py -x`
     - [ ] Verify immediate failure detection

7. **Update Documentation** (30 min)
   - [ ] Add function to API documentation if applicable
   - [ ] Update `ese_detection_architecture.md` if it references sigma deviation
         calculation
   - [ ] Add note in CHANGELOG or implementation summary

**Deliverables Checklist**:

- [ ] Function implemented in `src/dsa110_contimg/photometry/variability.py`
- [ ] Tests in `tests/unit/photometry/test_variability.py` (8+ test cases)
- [ ] `ese_pipeline.py` updated (no inline calculations)
- [ ] `ese_detection.py` updated (no inline calculations)
- [ ] All tests passing (existing + new)
- [ ] Code review completed
- [ ] Documentation updated

**Acceptance Criteria** (All Must Pass):

- [ ] **Single Source of Truth**:
      `grep -r "sigma_deviation.*=" src/dsa110_contimg/photometry/` returns only
      function definition
- [ ] **Test Coverage**:
      `pytest --cov=dsa110_contimg/photometry/variability --cov-report=term-missing`
      shows 100% coverage for `calculate_sigma_deviation`
- [ ] **Existing Tests Pass**: All existing tests in `tests/unit/photometry/`
      pass without modification
- [ ] **Edge Cases Covered**: Tests cover empty array, NaN, zero variance,
      single measurement, negative values
- [ ] **Mathematical Correctness**: Manual calculation matches function output
      for known test cases
- [ ] **No Regressions**: ESE detection produces identical results before/after
      refactoring (run detection on test database)

**Code Review Checklist**:

- [ ] Function signature matches specification
- [ ] Input validation handles all edge cases
- [ ] Docstring is complete and accurate
- [ ] Tests cover all edge cases
- [ ] Integration points updated correctly
- [ ] No code duplication remains
- [ ] Type hints are correct
- [ ] Error messages are informative

**Rollback Procedure** (If Issues Found):

1. Revert changes to `variability.py`
2. Revert changes to `ese_pipeline.py` and `ese_detection.py`
3. Run tests to verify original behavior restored
4. Document issues found for next attempt

#### 1.2 Comprehensive Validation Test Suite

**Effort**: 3-4 days  
**File Locations**:

- Test suite: `tests/unit/photometry/test_ese_validation.py`
- Test fixtures: `tests/conftest.py`
- Test utilities: `tests/utils/test_helpers.py` (create if doesn't exist)
- Reference data: `tests/data/test_photometry/` (create if needed)

**Task Breakdown**:

1. **Create Test Infrastructure** (4 hours)
   - [ ] Create `tests/utils/test_helpers.py`:
     - [ ] `create_test_photometry_data()` - Generate standardized test data
     - [ ] `create_known_ese_pattern()` - Generate ESE-like variability pattern
     - [ ] `create_test_database()` - Create temporary SQLite database
     - [ ] `add_photometry_measurements()` - Helper to add measurements to DB
   - [ ] Update `tests/conftest.py`:
     - [ ] `@pytest.fixture` for test database
     - [ ] `@pytest.fixture` for test photometry data
     - [ ] `@pytest.fixture` for known ESE pattern
   - [ ] Reference: See `ese_detection_comprehensive_improvements.md` Section
         1.2

2. **Unit Tests for Variability Metrics** (6-8 hours)
   - [ ] Test file: `tests/unit/photometry/test_ese_validation.py`
   - [ ] Test class: `TestVariabilityMetrics`
   - [ ] **Unit Test Checklist**:
     - [ ] Core functionality tests for each metric (3-5 cases each)
     - [ ] Edge case tests (empty, None, boundaries)
     - [ ] Error handling tests (invalid input, exceptions)
     - [ ] Smoke test for end-to-end validation
   - [ ] **Chi-squared tests**:
     - [ ] `test_chi_squared_calculation()` - Manual calculation vs function
       - [ ] Input: `fluxes = [1.0, 2.0, 3.0, 4.0, 5.0]`, `errors = [0.1] * 5`
       - [ ] Expected: `χ² = Σ((obs - expected)² / σ²)`, `χ²_ν = χ² / (N - 1)`
       - [ ] Verify against manual calculation
       - [ ] Execution time: < 10ms
     - [ ] `test_chi_squared_zero_variance()` - Zero variance case
       - [ ] Input: All fluxes identical
       - [ ] Expected: `χ²_ν ≈ 0.0`
       - [ ] Execution time: < 5ms
     - [ ] `test_chi_squared_missing_errors()` - Handle missing errors
       - [ ] Input: Some errors are None or NaN
       - [ ] Expected: Handles gracefully
       - [ ] Execution time: < 10ms
   - [ ] **Eta metric tests**:
     - [ ] `test_eta_metric_against_vast_tools()` - Compare with VAST Tools
           reference
       - [ ] No variability: `fluxes = [1.0, 1.0, 1.0]`,
             `errors = [0.1, 0.1, 0.1]` → `eta ≈ 0.0`
       - [ ] Variability: `fluxes = [1.0, 2.0, 3.0]`, `errors = [0.1, 0.1, 0.1]`
             → `eta ≈ 0.6667`
       - [ ] Tolerance: `abs(calculated - expected) < 0.01`
       - [ ] Execution time: < 20ms
     - [ ] `test_eta_metric_edge_cases()` - Edge cases
       - [ ] Single measurement, zero variance, negative fluxes
       - [ ] Execution time: < 15ms
   - [ ] **V metric tests**:
     - [ ] `test_v_metric_calculation()` - Verify V metric calculation
       - [ ] Test with known input/output pairs
       - [ ] Execution time: < 10ms
     - [ ] `test_v_metric_edge_cases()` - Edge cases
       - [ ] Execution time: < 10ms
   - [ ] **VS metric tests**:
     - [ ] `test_vs_metric_calculation()` - Verify VS (two-epoch) metric
       - [ ] Input: Two measurements: `flux_a, flux_b, flux_err_a, flux_err_b`
       - [ ] Expected: Valid VS metric calculation
       - [ ] Execution time: < 10ms
     - [ ] `test_vs_metric_zero_error()` - Handle zero error case
       - [ ] Execution time: < 5ms
   - [ ] **Total unit test execution time**: < 200ms for all metric tests

3. **Integration Tests** (4-5 hours)
   - [ ] Test class: `TestESEDetectionPipeline`
   - [ ] **Smoke Test Checklist**:
     - [ ] Critical path end-to-end test
     - [ ] Uses minimal real dependencies (test database)
     - [ ] Fast execution (< 2 seconds)
     - [ ] Verifies basic system functionality
   - [ ] **End-to-end smoke test**:
     - [ ] `test_end_to_end_detection_smoke()`:
       - [ ] Create test database (in-memory or temp file)
       - [ ] Add photometry with known ESE pattern:
             `fluxes = [1.0, 1.1, 1.2, 1.3, 5.0]` (large jump)
       - [ ] Run `detect_ese_candidates(db_path, min_sigma=3.0)`
       - [ ] Verify: 1 candidate found, `source_id == "TEST001"`,
             `significance > 3.0`
       - [ ] Execution time: < 1 second
   - [ ] **Consistency smoke test**:
     - [ ] `test_consistency_automatic_vs_manual_smoke()`:
       - [ ] Add measurements to test database
       - [ ] Run automatic detection: `auto_detect_ese_for_new_measurements()`
       - [ ] Run manual detection: `detect_ese_candidates()`
       - [ ] Verify: Same number of candidates, same significance values
       - [ ] Tolerance: `abs(auto_significance - manual_significance) < 0.01`
       - [ ] Execution time: < 1 second
   - [ ] **Total smoke test execution time**: < 2 seconds

4. **Edge Case Tests** (3-4 hours)
   - [ ] Test class: `TestEdgeCases`
   - [ ] **Single measurement**: `test_single_measurement()`
     - [ ] Input: `fluxes = [1.0]`, `errors = [0.1]`
     - [ ] Expected: Handles gracefully, no candidates (need multiple
           measurements)
     - [ ] Verify: No exceptions raised, returns empty list
   - [ ] **Zero variance**: `test_zero_variance()`
     - [ ] Input: `fluxes = [1.0, 1.0, 1.0, 1.0]`,
           `errors = [0.1, 0.1, 0.1, 0.1]`
     - [ ] Expected: No detection (no variability)
     - [ ] Verify: `len(candidates) == 0`
   - [ ] **Missing errors**: `test_missing_errors()`
     - [ ] Input: Some measurements with `None` or `NaN` errors
     - [ ] Expected: Handles gracefully, skips chi-squared calculation
     - [ ] Verify: No exceptions, detection still works
   - [ ] **Negative fluxes**: `test_negative_fluxes()`
     - [ ] Input: `fluxes = [-1.0, 0.0, 1.0]`
     - [ ] Expected: Variability still detectable
     - [ ] Verify: Detection works correctly
   - [ ] **Extreme outliers**: `test_extreme_outliers()`
     - [ ] Input: `fluxes = [1.0, 2.0, 3.0, 4.0, 100.0]`
     - [ ] Expected: Detects but doesn't crash
     - [ ] Verify: Detection works, significance > threshold

5. **Performance Tests** (2-3 hours)
   - [ ] Test class: `TestPerformance`
   - [ ] **Large source count**: `test_large_source_count()`
     - [ ] Create database with 10,000 sources
     - [ ] Measure detection time
     - [ ] Expected: Completes in < 60 seconds
     - [ ] Verify: `detection_time < 60.0`
   - [ ] **Incremental updates**: `test_incremental_updates()`
     - [ ] Add measurements incrementally
     - [ ] Measure time for each update
     - [ ] Expected: Only affected sources recomputed
     - [ ] Verify: Update time scales with number of new measurements, not total
           sources

6. **Test Documentation** (1 hour)
   - [ ] Document test structure in test file docstrings
   - [ ] Add comments explaining test cases
   - [ ] Document expected behaviors for edge cases

**Deliverables Checklist**:

- [ ] `tests/utils/test_helpers.py` created with helper functions
- [ ] `tests/conftest.py` updated with fixtures
- [ ] `tests/unit/photometry/test_ese_validation.py` created with all test
      classes
- [ ] All tests passing:
      `/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_validation.py -v`
- [ ] Test coverage report:
      `pytest --cov=dsa110_contimg/photometry --cov-report=html`
- [ ] Test documentation complete

**Acceptance Criteria** (All Must Pass):

- [ ] **Test Coverage**:
      `pytest --cov=dsa110_contimg/photometry --cov-report=term-missing` shows >
      90% coverage for variability calculations
- [ ] **All Tests Pass**: All tests in `test_ese_validation.py` pass
- [ ] **Edge Cases**: All edge cases handled gracefully (no crashes, appropriate
      behavior)
- [ ] **Performance**: Large source count test completes in < 60 seconds
- [ ] **Documentation**: Tests serve as executable documentation (clear names,
      docstrings, comments)
- [ ] **Consistency**: Automatic and manual detection produce identical results
      (within tolerance)

**Code Review Checklist**:

- [ ] Test structure follows pytest conventions
- [ ] Test names are descriptive
- [ ] Test data is realistic
- [ ] Edge cases are comprehensive
- [ ] Performance tests have reasonable thresholds
- [ ] Helper functions are reusable
- [ ] Fixtures are properly scoped
- [ ] Tests are independent (no shared state)

**Verification Commands**:

```bash
# Run all unit tests (should complete in < 200ms)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_validation.py::TestVariabilityMetrics -v --tb=short --durations=0

# Run smoke tests (should complete in < 2 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_validation.py -k smoke -v --tb=short --durations=0

# Run all validation tests (unit + smoke + integration)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_validation.py -v --tb=short

# Check test coverage
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_validation.py --cov=dsa110_contimg/photometry --cov-report=term-missing

# Run specific test class
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_validation.py::TestVariabilityMetrics -v

# Run edge case tests
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_validation.py::TestEdgeCases -v --tb=short

# Run performance tests (may take longer, but should be < 60 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_validation.py::TestPerformance -v --durations=0

# Fast failure mode (stop on first failure)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_validation.py -x -v
```

### Phase 1 Summary

**Key Outcomes**:

- Code quality improved (DRY principle, single source of truth)
- Comprehensive test coverage ensures correctness
- Foundation established for future improvements
- Statistical calculations validated

**Risks & Mitigation**:

- Risk: Breaking existing functionality during refactoring
- Mitigation: Comprehensive test suite catches regressions early

**Success Metrics**:

- Zero code duplication for sigma deviation
- Test coverage > 90%
- All existing functionality preserved
- Documentation complete

---

## Phase 2: Detection Enhancement

**Duration**: 1-2 weeks  
**Priority**: High (improves detection quality)  
**Dependencies**: Phase 1

### Objectives

1. Implement multi-metric scoring for robust detection
2. Add configurable threshold presets for different use cases
3. Improve candidate ranking and prioritization
4. Enhance detection confidence assessment

### Tasks

#### 2.1 Multi-Metric Scoring System

**Effort**: 4-5 days  
**File Locations**:

- Implementation: `src/dsa110_contimg/photometry/scoring.py` (new file)
- Configuration: `config/ese_detection.yaml` (create if doesn't exist)
- Integration points:
  - `src/dsa110_contimg/photometry/ese_detection.py` (update
    `detect_ese_candidates()`)
  - `src/dsa110_contimg/api/models.py` (update `ESEDetectJobParams`)
  - `src/dsa110_contimg/photometry/cli.py` (update CLI)
- Tests: `tests/unit/photometry/test_scoring.py` (new file)

**Task Breakdown**:

1. **Design Scoring Algorithm** (4 hours)
   - [ ] Review comprehensive improvements doc Section 2.1 for algorithm design
   - [ ] Define default weights:
     - [ ] `sigma_deviation`: 1.0 (primary metric)
     - [ ] `chi2_nu`: 0.5 (secondary metric)
     - [ ] `eta_metric`: 0.3 (tertiary metric)
     - [ ] `n_obs_penalty`: 0.2 (observation count factor)
   - [ ] Design normalization:
     - [ ] Chi-squared: normalize by dividing by 5.0 (chi2_nu > 5.0 gives full
           boost)
     - [ ] Eta: normalize by dividing by 0.5 (eta > 0.5 gives full boost)
     - [ ] Observation penalty: `(5 - n_obs) / 5.0` for n_obs < 5
   - [ ] Design confidence levels:
     - [ ] `high`: composite_score >= 7.0
     - [ ] `medium`: composite_score >= 5.0
     - [ ] `low`: composite_score >= 3.0
     - [ ] `very_low`: composite_score < 3.0

2. **Implement Scoring Function** (6-8 hours)
   - [ ] Create `src/dsa110_contimg/photometry/scoring.py`
   - [ ] Function signature:
         `def calculate_ese_composite_score(sigma_deviation: float, chi2_nu: Optional[float], eta_metric: Optional[float], n_obs: int, weights: Optional[dict] = None) -> dict:`
   - [ ] Implement base score: `sigma_deviation * weights["sigma_deviation"]`
   - [ ] Implement chi-squared contribution:
     - [ ] If `chi2_nu > 2.0`: `min(chi2_nu / 5.0, 1.0) * weights["chi2_nu"]`
     - [ ] Else: 0.0
   - [ ] Implement eta contribution:
     - [ ] If `eta_metric > 0.1`:
           `min(eta_metric / 0.5, 1.0) * weights["eta_metric"]`
     - [ ] Else: 0.0
   - [ ] Implement observation penalty:
     - [ ] If `n_obs < 5`: `(5 - n_obs) / 5.0 * weights["n_obs_penalty"]`
     - [ ] Else if `n_obs < 10`:
           `(10 - n_obs) / 10.0 * weights["n_obs_penalty"] * 0.5`
     - [ ] Else: 0.0
   - [ ] Calculate composite score:
         `base_score + chi2_contribution + eta_contribution - obs_penalty`
   - [ ] Determine confidence level based on composite score
   - [ ] Generate human-readable explanation string
   - [ ] Return dict with: `score`, `components`, `confidence`, `explanation`

3. **Create Configuration System** (2-3 hours)
   - [ ] Create `config/ese_detection.yaml`:
     ```yaml
     ese_detection:
       scoring:
         method: "composite" # or "sigma_only"
         composite_weights:
           sigma_deviation: 1.0
           chi2_nu: 0.5
           eta_metric: 0.3
           n_obs_penalty: 0.2
         thresholds:
           conservative: 7.0
           moderate: 5.5
           sensitive: 4.0
     ```
   - [ ] Create config loader function: `load_ese_config() -> dict`
   - [ ] Add config validation

4. **Integrate with Detection Pipeline** (4-5 hours)
   - [ ] Update `detect_ese_candidates()` in `ese_detection.py`:
     - [ ] Add parameter: `use_composite_score: bool = True`
     - [ ] Add parameter: `score_threshold: Optional[float] = None`
     - [ ] If `use_composite_score`:
       - [ ] Calculate composite score for each candidate
       - [ ] Use `score_threshold` or fall back to `min_sigma`
       - [ ] Add `composite_score`, `confidence`, `score_components` to result
     - [ ] Maintain backward compatibility (default behavior unchanged)
   - [ ] Update API model `ESEDetectJobParams`:
     - [ ] Add `use_composite_score: bool = True`
     - [ ] Add `score_threshold: Optional[float] = None`
   - [ ] Update CLI in `photometry/cli.py`:
     - [ ] Add `--use-composite-score` flag (default: True)
     - [ ] Add `--score-threshold` option
     - [ ] Update help text

5. **Create Validation Framework** (3-4 hours)
   - [ ] Create `scripts/validate_scoring_weights.py`:
     - [ ] Load known ESE candidates from database
     - [ ] Load non-ESE sources
     - [ ] Calculate scores for both groups
     - [ ] Analyze separation (ROC curve, precision/recall)
     - [ ] Suggest weight adjustments
   - [ ] Run validation on test dataset
   - [ ] Tune weights based on results
   - [ ] Document tuning process

6. **Write Comprehensive Tests** (4-5 hours)
   - [ ] Test file: `tests/unit/photometry/test_scoring.py`
   - [ ] Test class: `TestCalculateESECompositeScore`
   - [ ] **Unit Test Checklist**:
     - [ ] Core functionality tests (3-7 cases)
     - [ ] Edge case tests (None values, boundary conditions)
     - [ ] Error handling tests (invalid input, exceptions)
     - [ ] Smoke test for integration
   - [ ] **Unit tests** (execution time target: < 150ms total):
     - [ ] `test_basic_scoring()` - Verify basic score calculation
       - [ ] Input:
             `sigma_deviation=6.5, chi2_nu=3.2, eta_metric=0.15, n_obs=10`
       - [ ] Expected: Valid composite score > 6.0
       - [ ] Execution time: < 10ms
     - [ ] `test_chi2_contribution()` - Verify chi-squared boost
       - [ ] Input: `chi2_nu=5.0` (should give full boost)
       - [ ] Expected: Chi-squared contribution = `0.5 * weights["chi2_nu"]`
       - [ ] Execution time: < 5ms
     - [ ] `test_eta_contribution()` - Verify eta boost
       - [ ] Input: `eta_metric=0.5` (should give full boost)
       - [ ] Expected: Eta contribution = `0.3 * weights["eta_metric"]`
       - [ ] Execution time: < 5ms
     - [ ] `test_obs_penalty()` - Verify observation count penalty
       - [ ] Input: `n_obs=3` (should penalize)
       - [ ] Expected: Penalty applied correctly
       - [ ] Execution time: < 5ms
     - [ ] `test_confidence_levels()` - Verify confidence assignment
       - [ ] Test all confidence levels: high (>=7.0), medium (>=5.0), low
             (>=3.0), very_low (<3.0)
       - [ ] Execution time: < 15ms
     - [ ] `test_custom_weights()` - Verify custom weight support
       - [ ] Input: Custom weights dict
       - [ ] Expected: Uses custom weights instead of defaults
       - [ ] Execution time: < 10ms
     - [ ] `test_missing_metrics()` - Verify handling of None chi2/eta
       - [ ] Input: `chi2_nu=None, eta_metric=None`
       - [ ] Expected: Handles gracefully, only uses sigma deviation
       - [ ] Execution time: < 5ms
     - [ ] `test_edge_case_zero_obs()` - Handle zero observations
       - [ ] Input: `n_obs=0`
       - [ ] Expected: Handles gracefully
       - [ ] Execution time: < 5ms
   - [ ] **Smoke tests** (execution time target: < 1 second):
     - [ ] `test_scoring_smoke()` - End-to-end integration test
       - [ ] Use scoring in context of detection pipeline
       - [ ] Verify integration with `detect_ese_candidates()`
       - [ ] Execution time: < 500ms
     - [ ] `test_backward_compatibility_smoke()` - Verify old behavior still
           works
       - [ ] Test with `use_composite_score=False`
       - [ ] Expected: Identical results to current behavior
       - [ ] Execution time: < 500ms
   - [ ] **Validation tests** (execution time target: < 2 seconds):
     - [ ] `test_known_ese_scoring()` - Known ESEs get high scores
       - [ ] Load known ESE from test database
       - [ ] Expected: Composite score >= 5.0
       - [ ] Execution time: < 1 second
     - [ ] `test_non_ese_scoring()` - Non-ESEs get low scores
       - [ ] Load non-ESE source from test database
       - [ ] Expected: Composite score < 3.0
       - [ ] Execution time: < 1 second
   - [ ] **Total test execution time**: < 4 seconds (unit + smoke + validation)

**Deliverables Checklist**:

- [ ] `scoring.py` created with `calculate_ese_composite_score()` function
- [ ] `config/ese_detection.yaml` created with default weights
- [ ] `detect_ese_candidates()` updated with scoring support
- [ ] API models updated (`ESEDetectJobParams`)
- [ ] CLI updated with scoring flags
- [ ] Validation framework script created
- [ ] Test suite created (`test_scoring.py`)
- [ ] Documentation updated

**Acceptance Criteria** (All Must Pass):

- [ ] **Functionality**: Composite scoring produces scores > single metric for
      ESE candidates
- [ ] **Validation**: Weights tuned based on known ESE candidates (ROC AUC >
      0.8)
- [ ] **Backward Compatibility**: `use_composite_score=False` produces identical
      results to current behavior
- [ ] **Test Coverage**: `pytest --cov=dsa110_contimg/photometry/scoring`
      shows > 95% coverage
- [ ] **API Integration**: API endpoints accept and use scoring parameters
- [ ] **CLI Integration**: CLI accepts scoring flags and produces correct output
- [ ] **Documentation**: Scoring algorithm documented with examples

**Code Review Checklist**:

- [ ] Scoring algorithm matches specification
- [ ] Weights are configurable
- [ ] Confidence levels are clearly defined
- [ ] Explanation strings are informative
- [ ] Backward compatibility maintained
- [ ] Error handling for edge cases
- [ ] Type hints complete
- [ ] Docstrings comprehensive

**Verification Commands**:

```bash
# Run unit tests (should complete in < 150ms)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_scoring.py::TestCalculateESECompositeScore -v --tb=short --durations=0

# Run smoke tests (should complete in < 1 second)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_scoring.py -k smoke -v --tb=short --durations=0

# Run all scoring tests (unit + smoke + validation, should complete in < 4 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_scoring.py -v --tb=short --durations=0

# Test integration with detection pipeline
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_ese_detection.py -k scoring -v --tb=short

# Check test coverage
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_scoring.py --cov=dsa110_contimg/photometry/scoring --cov-report=term-missing

# Fast failure mode (stop on first failure)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_scoring.py -x -v

# Validate weights (separate script)
/opt/miniforge/envs/casa6/bin/python scripts/validate_scoring_weights.py

# Test API endpoint (requires API server running)
curl -X POST http://localhost:8000/api/jobs/ese-detect \
  -H "Content-Type: application/json" \
  -d '{"params": {"use_composite_score": true, "score_threshold": 5.5}}'

# Test CLI
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.photometry.cli ese-detect \
  --use-composite-score --score-threshold 5.5
```

**Performance Benchmarks**:

- Scoring function should complete in < 1ms per candidate
- Integration should add < 5% overhead to detection pipeline
- Memory usage should be minimal (no large data structures)

#### 2.2 Configurable Threshold Presets

**Effort**: 2-3 days  
**File Locations**:

- Implementation: `src/dsa110_contimg/photometry/thresholds.py` (new file)
- Integration points:
  - `src/dsa110_contimg/api/models.py` (update `ESEDetectJobParams`)
  - `src/dsa110_contimg/api/routes.py` (update endpoint handlers)
  - `src/dsa110_contimg/photometry/cli.py` (update CLI)
- Tests: `tests/unit/photometry/test_thresholds.py` (new file)
- Documentation: `docs/how-to/ese_threshold_selection.md` (new file)

**Task Breakdown**:

1. **Design Preset System** (2-3 hours)
   - [ ] Review comprehensive improvements doc Section 2.2 for preset design
   - [ ] Define preset categories:
     - [ ] `conservative`: 5.0σ (false positive rate ~0.00006%)
     - [ ] `moderate`: 4.0σ (false positive rate ~0.006%)
     - [ ] `sensitive`: 3.0σ (false positive rate ~0.3%)
     - [ ] `very_sensitive`: 2.5σ (false positive rate ~1.2%)
   - [ ] Calculate false positive rates for each preset
   - [ ] Document use cases:
     - [ ] Conservative: Production monitoring, automated alerts
     - [ ] Moderate: Follow-up analysis, detailed investigation
     - [ ] Sensitive: Initial screening, exploratory analysis
     - [ ] Very sensitive: Research exploration

2. **Implement `ESEThresholdPreset` Class** (3-4 hours)
   - [ ] Create `src/dsa110_contimg/photometry/thresholds.py`
   - [ ] Class structure:

     ```python
     class ESEThresholdPreset:
         PRESETS = {
             "conservative": {
                 "sigma_threshold": 5.0,
                 "description": "...",
                 "false_positive_rate": 0.00006,
                 "use_cases": [...]
             },
             # ... other presets
         }

         @classmethod
         def get_threshold(cls, preset: str, custom: Optional[float] = None) -> float:
             """Get threshold value from preset or custom value."""

         @classmethod
         def get_preset_info(cls, preset: str) -> dict:
             """Get information about a preset."""
     ```

   - [ ] Implement `get_threshold()`:
     - [ ] Validate preset name
     - [ ] Return custom value if provided (overrides preset)
     - [ ] Return preset threshold if valid preset
     - [ ] Raise `ValueError` if preset not found
   - [ ] Implement `get_preset_info()`:
     - [ ] Return preset metadata dict
     - [ ] Raise `ValueError` if preset not found
   - [ ] Add type hints and docstrings

3. **Integrate with API** (2-3 hours)
   - [ ] Update `ESEDetectJobParams` in `api/models.py`:
     - [ ] Add `threshold_preset: str = Field("conservative", ...)`
     - [ ] Add `min_sigma: Optional[float] = Field(None, ...)` (optional
           override)
     - [ ] Add validator: `@validator("threshold_preset")` to check valid
           presets
     - [ ] Add method: `def get_threshold(self) -> float:`
   - [ ] Update endpoint handlers in `api/routes.py`:
     - [ ] Update `create_ese_detect_job()` to use `params.get_threshold()`
     - [ ] Update `create_batch_ese_detect_job_endpoint()` similarly
   - [ ] Update response models to include preset info if needed

4. **Integrate with CLI** (2 hours)
   - [ ] Update `photometry/cli.py`:
     - [ ] Add `--threshold-preset` argument:
       - [ ] Choices:
             `["conservative", "moderate", "sensitive", "very_sensitive"]`
       - [ ] Default: `"conservative"`
       - [ ] Help text: "Threshold preset (conservative, moderate, sensitive,
             very_sensitive)"
     - [ ] Keep `--min-sigma` as optional override
     - [ ] Update `cmd_ese_detect()`:
       - [ ] Import `ESEThresholdPreset`
       - [ ] Get threshold:
             `threshold = ESEThresholdPreset.get_threshold(args.threshold_preset, args.min_sigma)`
       - [ ] Pass threshold to `detect_ese_candidates()`

5. **Create Documentation** (2 hours)
   - [ ] Create `docs/how-to/ese_threshold_selection.md`:
     - [ ] Threshold selection guide
     - [ ] Use case examples for each preset
     - [ ] False positive rate analysis
     - [ ] When to use custom thresholds
   - [ ] Update API documentation if applicable

6. **Write Comprehensive Tests** (3-4 hours)
   - [ ] Test file: `tests/unit/photometry/test_thresholds.py`
   - [ ] Test class: `TestESEThresholdPreset`
   - [ ] **Unit Test Checklist**:
     - [ ] Core functionality tests (3-7 cases)
     - [ ] Edge case tests (invalid preset, None values, boundary conditions)
     - [ ] Error handling tests (invalid input, exceptions)
     - [ ] Smoke test for integration
   - [ ] **Unit tests** (execution time target: < 100ms total):
     - [ ] `test_get_threshold_conservative()` - Verify conservative preset
       - [ ] Input: `preset="conservative"`
       - [ ] Expected: `5.0`
       - [ ] Execution time: < 5ms
     - [ ] `test_get_threshold_moderate()` - Verify moderate preset
       - [ ] Input: `preset="moderate"`
       - [ ] Expected: `4.0`
       - [ ] Execution time: < 5ms
     - [ ] `test_get_threshold_sensitive()` - Verify sensitive preset
       - [ ] Input: `preset="sensitive"`
       - [ ] Expected: `3.0`
       - [ ] Execution time: < 5ms
     - [ ] `test_get_threshold_very_sensitive()` - Verify very_sensitive preset
       - [ ] Input: `preset="very_sensitive"`
       - [ ] Expected: `2.5`
       - [ ] Execution time: < 5ms
     - [ ] `test_get_threshold_custom_override()` - Verify custom override
       - [ ] Input: `preset="conservative", custom=6.0`
       - [ ] Expected: `6.0` (custom overrides preset)
       - [ ] Execution time: < 5ms
     - [ ] `test_get_threshold_invalid_preset()` - Verify error handling
       - [ ] Input: `preset="invalid"`
       - [ ] Expected: `ValueError` raised
       - [ ] Execution time: < 5ms
     - [ ] `test_get_preset_info()` - Verify preset info retrieval
       - [ ] Input: `preset="conservative"`
       - [ ] Expected: Dict with metadata (sigma_threshold, description, etc.)
       - [ ] Execution time: < 5ms
     - [ ] `test_get_preset_info_invalid()` - Verify error for invalid preset
       - [ ] Input: `preset="invalid"`
       - [ ] Expected: `ValueError` raised
       - [ ] Execution time: < 5ms
     - [ ] `test_all_presets_available()` - Verify all presets exist
       - [ ] Check all four presets are in `PRESETS` dict
       - [ ] Execution time: < 10ms
   - [ ] **Smoke tests** (execution time target: < 1 second):
     - [ ] `test_threshold_preset_api_smoke()` - API integration test
       - [ ] Create job with `threshold_preset="moderate"`
       - [ ] Verify threshold used is 4.0
       - [ ] Execution time: < 500ms
     - [ ] `test_threshold_preset_cli_smoke()` - CLI integration test
       - [ ] Run CLI with `--threshold-preset sensitive`
       - [ ] Verify threshold used is 3.0
       - [ ] Execution time: < 500ms
     - [ ] `test_custom_override_smoke()` - Custom override integration
       - [ ] Test API with `threshold_preset="conservative"` and `min_sigma=6.0`
       - [ ] Verify threshold used is 6.0 (custom overrides)
       - [ ] Execution time: < 500ms
   - [ ] **Total test execution time**: < 1.5 seconds (unit + smoke)

**Deliverables Checklist**:

- [ ] `thresholds.py` created with `ESEThresholdPreset` class
- [ ] API models updated (`ESEDetectJobParams`)
- [ ] API endpoints updated (use preset system)
- [ ] CLI updated with `--threshold-preset` argument
- [ ] Documentation created (`ese_threshold_selection.md`)
- [ ] Test suite created (`test_thresholds.py`)
- [ ] All tests passing

**Acceptance Criteria** (All Must Pass):

- [ ] **Four Presets Available**: All four presets (conservative, moderate,
      sensitive, very_sensitive) work correctly
- [ ] **Custom Override**: Custom thresholds override presets when provided
- [ ] **API Integration**: API endpoints accept and use `threshold_preset`
      parameter
- [ ] **CLI Integration**: CLI accepts `--threshold-preset` argument and uses it
      correctly
- [ ] **Error Handling**: Invalid preset names raise `ValueError` with
      informative message
- [ ] **Test Coverage**: `pytest --cov=dsa110_contimg/photometry/thresholds`
      shows > 95% coverage
- [ ] **Documentation**: Threshold selection guide is clear and complete

**Code Review Checklist**:

- [ ] Preset definitions match specification (thresholds, descriptions, use
      cases)
- [ ] `get_threshold()` handles custom override correctly
- [ ] Error messages are informative
- [ ] Type hints are complete
- [ ] Docstrings are comprehensive
- [ ] API integration maintains backward compatibility
- [ ] CLI integration provides clear help text

**Verification Commands**:

```bash
# Run unit tests (should complete in < 100ms)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_thresholds.py::TestESEThresholdPreset -v --tb=short --durations=0

# Run smoke tests (should complete in < 1 second)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_thresholds.py -k smoke -v --tb=short --durations=0

# Run all threshold tests (unit + smoke, should complete in < 1.5 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_thresholds.py -v --tb=short --durations=0

# Check test coverage
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_thresholds.py --cov=dsa110_contimg/photometry/thresholds --cov-report=term-missing

# Fast failure mode (stop on first failure)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_thresholds.py -x -v

# Test API endpoint (requires API server running)
curl -X POST http://localhost:8000/api/jobs/ese-detect \
  -H "Content-Type: application/json" \
  -d '{"params": {"threshold_preset": "moderate"}}'

# Test CLI
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.photometry.cli ese-detect \
  --threshold-preset sensitive --min-sigma 3.5
```

**Performance Benchmarks**:

- Threshold retrieval should complete in < 1ms per call
- No performance impact on detection pipeline (threshold is retrieved once per
  job)
- Memory usage minimal (presets are class-level constants)

### Phase 2 Summary

**Key Outcomes**:

- More robust detection through multi-metric scoring
- Flexible threshold configuration for different use cases
- Better candidate ranking and prioritization
- Improved detection confidence assessment

**Risks & Mitigation**:

- Risk: Scoring weights may need tuning based on real data
- Mitigation: Validation framework allows iterative tuning
- Risk: Presets may not match all use cases
- Mitigation: Custom thresholds always available as override

**Success Metrics**:

- Composite scoring reduces false positives while maintaining sensitivity
- Presets cover common use cases
- API and CLI fully support new features
- Documentation complete

---

## Phase 3: Performance Optimization

**Duration**: 1-2 weeks  
**Priority**: High (enables scalability)  
**Dependencies**: Phase 1

### Objectives

1. Implement caching system for variability statistics
2. Add parallel processing for batch operations
3. Improve scalability for large source catalogs
4. Optimize database queries and operations

### Tasks

#### 3.1 Caching Variability Statistics

**Effort**: 3-4 days  
**File Locations**:

- Implementation: `src/dsa110_contimg/photometry/caching.py` (new file)
- Integration points:
  - `src/dsa110_contimg/photometry/ese_pipeline.py` (update
    `update_variability_stats_for_source()`)
  - `src/dsa110_contimg/photometry/ese_detection.py` (update
    `_recompute_variability_stats()`)
- Tests: `tests/unit/photometry/test_caching.py` (new file)
- Configuration: `config/ese_detection.yaml` (add caching section)

**Task Breakdown**:

1. **Design Cache Architecture** (3-4 hours)
   - [ ] Review comprehensive improvements doc Section 3.1 for cache design
   - [ ] Cache key generation strategy:
     - [ ] Key format: `f"{source_id}:{photometry_timestamp}"`
     - [ ] Use MD5 hash for key: `hashlib.md5(key_data.encode()).hexdigest()`
   - [ ] Cache invalidation strategy:
     - [ ] Time-based: TTL (default 3600 seconds)
     - [ ] Event-based: Invalidate on photometry updates
     - [ ] Timestamp-based: Compare photometry timestamps
   - [ ] Cache backend selection:
     - [ ] Memory backend (default, in-memory dict)
     - [ ] Redis backend (optional, for distributed systems)
     - [ ] File backend (optional, for persistence)

2. **Implement `VariabilityStatsCache` Data Class** (2-3 hours)
   - [ ] Create `@dataclass` in `caching.py`:

     ```python
     @dataclass
     class VariabilityStatsCache:
         source_id: str
         stats: dict
         cache_timestamp: float
         photometry_timestamp: float
         cache_key: str

         def is_valid(self, max_age_seconds: float = 3600) -> bool:
             """Check if cache entry is still valid."""

         def matches_photometry(self, current_photometry_timestamp: float) -> bool:
             """Check if cache matches current photometry state."""
     ```

   - [ ] Implement `is_valid()`:
     - [ ] Check age: `time.time() - self.cache_timestamp < max_age_seconds`
     - [ ] Return boolean
   - [ ] Implement `matches_photometry()`:
     - [ ] Compare timestamps:
           `abs(self.photometry_timestamp - current_photometry_timestamp) < 1.0`
     - [ ] Return boolean

3. **Implement `VariabilityStatsCacheManager` Class** (4-5 hours)
   - [ ] Create class in `caching.py`:

     ```python
     class VariabilityStatsCacheManager:
         def __init__(self, cache_backend: str = "memory", max_size: int = 10000, default_ttl: float = 3600.0):
             """Initialize cache manager."""

         def get_cache_key(self, source_id: str, photometry_timestamp: float) -> str:
             """Generate cache key."""

         def get(self, source_id: str, current_photometry_timestamp: float) -> Optional[dict]:
             """Get cached statistics if available and valid."""

         def set(self, source_id: str, stats: dict, photometry_timestamp: float):
             """Cache statistics."""

         def invalidate(self, source_id: str):
             """Invalidate cache for a source."""
     ```

   - [ ] Implement memory backend:
     - [ ] Use dict: `self.cache: Dict[str, VariabilityStatsCache] = {}`
     - [ ] Implement LRU eviction when at capacity
   - [ ] Implement Redis backend (optional):
     - [ ] Use `redis.Redis()` connection
     - [ ] Serialize cache entries to JSON
   - [ ] Implement file backend (optional):
     - [ ] Store in `/tmp/ese_cache/` directory
     - [ ] Use pickle or JSON for serialization

4. **Integrate with Variability Stats Computation** (3-4 hours)
   - [ ] Update `update_variability_stats_for_source()` in `ese_pipeline.py`:
     - [ ] Get cache manager: `cache_manager = get_cache_manager()`
     - [ ] Check cache:
           `cached_stats = cache_manager.get(source_id, current_photometry_timestamp)`
     - [ ] If cache hit: Return cached stats, skip computation
     - [ ] If cache miss: Compute stats, cache results
   - [ ] Update `_recompute_variability_stats()` in `ese_detection.py`:
     - [ ] Similar cache integration
     - [ ] Invalidate cache before recomputation if needed
   - [ ] Add cache hit/miss logging:
     - [ ] Log cache hits: `logger.debug(f"Cache hit for {source_id}")`
     - [ ] Log cache misses: `logger.debug(f"Cache miss for {source_id}")`

5. **Add Configuration** (1-2 hours)
   - [ ] Update `config/ese_detection.yaml`:
     ```yaml
     ese_detection:
       caching:
         backend: "memory" # or "redis", "file"
         max_size: 10000
         default_ttl: 3600.0 # seconds
         redis_host: "localhost" # if using Redis
         redis_port: 6379
     ```
   - [ ] Create config loader: `load_cache_config() -> dict`

6. **Write Comprehensive Tests** (4-5 hours)
   - [ ] Test file: `tests/unit/photometry/test_caching.py`
   - [ ] Test class: `TestVariabilityStatsCacheManager`
   - [ ] **Unit Test Checklist**:
     - [ ] Core functionality tests (3-7 cases)
     - [ ] Edge case tests (empty cache, expired entries, invalid keys)
     - [ ] Error handling tests (invalid input, exceptions)
     - [ ] Smoke test for integration
   - [ ] **Unit tests** (execution time target: < 200ms total):
     - [ ] `test_cache_hit()` - Verify cache hit behavior
       - [ ] Set cache entry
       - [ ] Get same entry
       - [ ] Expected: Returns cached stats
       - [ ] Execution time: < 10ms
     - [ ] `test_cache_miss()` - Verify cache miss behavior
       - [ ] Get non-existent entry
       - [ ] Expected: Returns None
       - [ ] Execution time: < 5ms
     - [ ] `test_cache_invalidation()` - Verify invalidation
       - [ ] Set cache entry
       - [ ] Invalidate source
       - [ ] Get entry
       - [ ] Expected: Returns None (invalidated)
       - [ ] Execution time: < 10ms
     - [ ] `test_cache_expiration()` - Verify TTL expiration
       - [ ] Set cache entry with short TTL
       - [ ] Wait for expiration
       - [ ] Get entry
       - [ ] Expected: Returns None (expired)
       - [ ] Execution time: < 50ms (includes wait)
     - [ ] `test_cache_eviction()` - Verify LRU eviction
       - [ ] Fill cache to capacity
       - [ ] Add new entry
       - [ ] Expected: Oldest entry evicted
       - [ ] Execution time: < 20ms
     - [ ] `test_photometry_timestamp_mismatch()` - Verify timestamp validation
       - [ ] Set cache entry with old timestamp
       - [ ] Get with new timestamp
       - [ ] Expected: Returns None (timestamp mismatch)
       - [ ] Execution time: < 10ms
     - [ ] `test_cache_key_generation()` - Verify key generation
       - [ ] Generate keys for same source/different timestamps
       - [ ] Expected: Different keys
       - [ ] Execution time: < 5ms
     - [ ] `test_multiple_backends()` - Verify backend switching
       - [ ] Test memory backend
       - [ ] Test file backend (if implemented)
       - [ ] Expected: Both work correctly
       - [ ] Execution time: < 30ms
   - [ ] **Smoke tests** (execution time target: < 2 seconds):
     - [ ] `test_caching_integration_smoke()` - End-to-end integration
       - [ ] Use cache in variability stats computation
       - [ ] Verify cache hit on second call
       - [ ] Execution time: < 1 second
     - [ ] `test_cache_performance_smoke()` - Performance validation
       - [ ] Compare cached vs non-cached computation time
       - [ ] Expected: Cached is 10-100x faster
       - [ ] Execution time: < 1 second
   - [ ] **Performance tests** (execution time target: < 5 seconds):
     - [ ] `test_cache_hit_rate()` - Measure hit rate
       - [ ] Run 1000 operations with 80% cache hits
       - [ ] Expected: Hit rate > 75%
       - [ ] Execution time: < 2 seconds
   - [ ] **Total test execution time**: < 8 seconds (unit + smoke + performance)

7. **Add Monitoring** (1-2 hours)
   - [ ] Add cache metrics:
     - [ ] `cache_hits`: Counter
     - [ ] `cache_misses`: Counter
     - [ ] `cache_hit_rate`: Gauge (hits / (hits + misses))
     - [ ] `cache_size`: Gauge (current cache size)
   - [ ] Integrate with existing monitoring system

**Deliverables Checklist**:

- [ ] `caching.py` created with `VariabilityStatsCache` and
      `VariabilityStatsCacheManager`
- [ ] Cache integration in variability stats computation
- [ ] Configuration system updated
- [ ] Test suite created (`test_caching.py`)
- [ ] Monitoring/metrics added
- [ ] All tests passing

**Acceptance Criteria** (All Must Pass):

- [ ] **Cache Hit Rate**: Cache hit rate > 80% for stable sources (measured in
      tests)
- [ ] **Performance**: 10-100x speedup for cached sources (measured in smoke
      tests)
- [ ] **Cache Invalidation**: Cache invalidation works correctly (tested)
- [ ] **Memory Usage**: Memory usage within limits (max_size enforced)
- [ ] **Test Coverage**: `pytest --cov=dsa110_contimg/photometry/caching`
      shows > 95% coverage
- [ ] **Backward Compatibility**: System works without cache (cache disabled)

**Code Review Checklist**:

- [ ] Cache key generation is deterministic
- [ ] Cache invalidation handles all cases
- [ ] LRU eviction works correctly
- [ ] Memory backend is thread-safe (if needed)
- [ ] Error handling for cache failures
- [ ] Type hints complete
- [ ] Docstrings comprehensive

**Verification Commands**:

```bash
# Run unit tests (should complete in < 200ms)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_caching.py::TestVariabilityStatsCacheManager -v --tb=short --durations=0

# Run smoke tests (should complete in < 2 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_caching.py -k smoke -v --tb=short --durations=0

# Run performance tests (should complete in < 5 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_caching.py -k performance -v --durations=0

# Run all caching tests (unit + smoke + performance, should complete in < 8 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_caching.py -v --tb=short --durations=0

# Check test coverage
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_caching.py --cov=dsa110_contimg/photometry/caching --cov-report=term-missing

# Fast failure mode (stop on first failure)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_caching.py -x -v
```

**Performance Benchmarks**:

- Cache hit: < 1ms per lookup
- Cache miss: < 2ms per lookup (includes computation)
- Cache set: < 1ms per entry
- Cache invalidation: < 1ms per source
- Memory overhead: < 1KB per cached entry

#### 3.2 Parallel Processing

**Effort**: 3-4 days  
**File Locations**:

- Implementation: `src/dsa110_contimg/photometry/parallel.py` (new file)
- Integration points:
  - `src/dsa110_contimg/photometry/ese_detection.py` (update
    `detect_ese_candidates()`)
  - `src/dsa110_contimg/api/job_adapters.py` (update
    `run_batch_ese_detect_job()`)
- Tests: `tests/unit/photometry/test_parallel.py` (new file)
- Configuration: `config/ese_detection.yaml` (add parallel section)

**Task Breakdown**:

1. **Design Parallel Processing Architecture** (3-4 hours)
   - [ ] Review comprehensive improvements doc Section 3.2 for parallel design
   - [ ] Worker pool sizing strategy:
     - [ ] Default: `min(cpu_count(), len(source_ids), 8)` (cap at 8 workers)
     - [ ] Configurable via config file
   - [ ] Batch size optimization:
     - [ ] Default: 100 sources per batch
     - [ ] Adjust based on source count and worker count
   - [ ] Database concurrency handling:
     - [ ] Enable WAL mode: `PRAGMA journal_mode=WAL`
     - [ ] Connection per worker (no shared connections)
     - [ ] Timeout: 30 seconds per connection

2. **Implement Batch Processing Functions** (4-5 hours)
   - [ ] Create `src/dsa110_contimg/photometry/parallel.py`
   - [ ] Function:
         `process_source_batch(source_ids: List[str], products_db: Path, batch_size: int = 100) -> List[dict]`:
     - [ ] Split source_ids into batches
     - [ ] Create worker pool
     - [ ] Process batches in parallel
     - [ ] Collect results
     - [ ] Return flattened results
   - [ ] Function:
         `process_single_batch(source_ids: List[str], products_db: Path) -> List[dict]`:
     - [ ] Create database connection for this worker
     - [ ] Process each source_id
     - [ ] Return results
   - [ ] Worker initialization:
     - [ ] Create connection per worker
     - [ ] Set up error handling
     - [ ] Set up logging

3. **Handle Database Concurrency** (2-3 hours)
   - [ ] Enable WAL mode:
     - [ ] Check if WAL mode enabled: `PRAGMA journal_mode`
     - [ ] Enable if not: `PRAGMA journal_mode=WAL`
   - [ ] Connection pooling per worker:
     - [ ] Each worker gets its own connection
     - [ ] No shared connections between workers
   - [ ] Lock handling:
     - [ ] Use SQLite's built-in locking (WAL mode handles this)
     - [ ] Handle `sqlite3.OperationalError` for locked database
     - [ ] Retry logic with exponential backoff

4. **Integrate with Detection Pipeline** (3-4 hours)
   - [ ] Update `detect_ese_candidates()` in `ese_detection.py`:
     - [ ] Add parameter: `use_parallel: bool = True`
     - [ ] Add parameter: `max_workers: Optional[int] = None`
     - [ ] If `use_parallel` and multiple sources:
       - [ ] Use `process_source_batch()` for parallel processing
     - [ ] Else: Use sequential processing (backward compatible)
   - [ ] Update `run_batch_ese_detect_job()` in `job_adapters.py`:
     - [ ] Use parallel processing for batch jobs
     - [ ] Update progress tracking for parallel execution
   - [ ] Add parallel processing flag to API/CLI if needed

5. **Add Configuration** (1-2 hours)
   - [ ] Update `config/ese_detection.yaml`:
     ```yaml
     ese_detection:
       parallel:
         enabled: true
         max_workers: null # null = auto-detect (min(cpu_count(), 8))
         batch_size: 100
         connection_timeout: 30.0 # seconds
     ```
   - [ ] Create config loader: `load_parallel_config() -> dict`

6. **Write Comprehensive Tests** (4-5 hours)
   - [ ] Test file: `tests/unit/photometry/test_parallel.py`
   - [ ] Test class: `TestParallelProcessing`
   - [ ] **Unit Test Checklist**:
     - [ ] Core functionality tests (3-7 cases)
     - [ ] Edge case tests (empty list, single source, large batches)
     - [ ] Error handling tests (database errors, worker failures)
     - [ ] Smoke test for integration
   - [ ] **Unit tests** (execution time target: < 300ms total):
     - [ ] `test_process_single_batch()` - Verify single batch processing
       - [ ] Input: List of 10 source_ids
       - [ ] Expected: All sources processed correctly
       - [ ] Execution time: < 50ms
     - [ ] `test_process_source_batch_parallel()` - Verify parallel processing
       - [ ] Input: List of 100 source_ids, 4 workers
       - [ ] Expected: All sources processed, results correct
       - [ ] Execution time: < 200ms
     - [ ] `test_worker_pool_sizing()` - Verify worker count calculation
       - [ ] Test with different CPU counts and source counts
       - [ ] Expected: Worker count capped appropriately
       - [ ] Execution time: < 10ms
     - [ ] `test_batch_size_optimization()` - Verify batch splitting
       - [ ] Input: 250 sources, batch_size=100
       - [ ] Expected: 3 batches (100, 100, 50)
       - [ ] Execution time: < 5ms
     - [ ] `test_database_concurrency()` - Verify WAL mode and concurrency
       - [ ] Enable WAL mode
       - [ ] Process multiple sources concurrently
       - [ ] Expected: No database locks, all succeed
       - [ ] Execution time: < 100ms
     - [ ] `test_error_handling()` - Verify error handling
       - [ ] Simulate worker failure
       - [ ] Expected: Other workers continue, errors logged
       - [ ] Execution time: < 50ms
     - [ ] `test_empty_source_list()` - Verify empty input handling
       - [ ] Input: Empty list
       - [ ] Expected: Returns empty list, no errors
       - [ ] Execution time: < 5ms
     - [ ] `test_single_source()` - Verify single source handling
       - [ ] Input: Single source_id
       - [ ] Expected: Processes correctly (may use sequential)
       - [ ] Execution time: < 20ms
   - [ ] **Smoke tests** (execution time target: < 3 seconds):
     - [ ] `test_parallel_integration_smoke()` - End-to-end integration
       - [ ] Use parallel processing in detection pipeline
       - [ ] Verify results match sequential processing
       - [ ] Execution time: < 2 seconds
     - [ ] `test_parallel_performance_smoke()` - Performance validation
       - [ ] Compare parallel vs sequential processing time
       - [ ] Expected: Parallel is faster (near-linear speedup)
       - [ ] Execution time: < 1 second
   - [ ] **Concurrency tests** (execution time target: < 5 seconds):
     - [ ] `test_no_race_conditions()` - Verify no race conditions
       - [ ] Process same sources concurrently multiple times
       - [ ] Expected: Consistent results, no corruption
       - [ ] Execution time: < 2 seconds
     - [ ] `test_database_locking()` - Verify database locking works
       - [ ] Concurrent writes to same database
       - [ ] Expected: No deadlocks, all succeed
       - [ ] Execution time: < 3 seconds
   - [ ] **Performance tests** (execution time target: < 10 seconds):
     - [ ] `test_speedup_scaling()` - Measure speedup vs worker count
       - [ ] Test with 1, 2, 4, 8 workers
       - [ ] Expected: Near-linear speedup up to CPU count
       - [ ] Execution time: < 5 seconds
     - [ ] `test_large_source_count()` - Test with large number of sources
       - [ ] Process 10,000 sources
       - [ ] Expected: Completes efficiently, no memory issues
       - [ ] Execution time: < 5 seconds
   - [ ] **Total test execution time**: < 20 seconds (unit + smoke +
         concurrency + performance)

7. **Add Monitoring** (1-2 hours)
   - [ ] Add parallel processing metrics:
     - [ ] `parallel_workers`: Gauge (current worker count)
     - [ ] `parallel_batches_processed`: Counter
     - [ ] `parallel_processing_time`: Histogram
     - [ ] `parallel_speedup`: Gauge (speedup vs sequential)
   - [ ] Integrate with existing monitoring system

**Deliverables Checklist**:

- [ ] `parallel.py` created with parallel processing functions
- [ ] Database concurrency handling (WAL mode, connection pooling)
- [ ] Integration with detection pipeline
- [ ] Configuration system updated
- [ ] Test suite created (`test_parallel.py`)
- [ ] Monitoring/metrics added
- [ ] All tests passing

**Acceptance Criteria** (All Must Pass):

- [ ] **Speedup**: Near-linear speedup up to CPU count (measured in performance
      tests)
- [ ] **Scalability**: Handles 100K+ sources efficiently (tested with large
      source count)
- [ ] **Correctness**: No race conditions or data corruption (tested in
      concurrency tests)
- [ ] **Configurability**: Worker count configurable (tested)
- [ ] **Backward Compatibility**: Sequential processing still works (tested)
- [ ] **Test Coverage**: `pytest --cov=dsa110_contimg/photometry/parallel`
      shows > 95% coverage

**Code Review Checklist**:

- [ ] Worker pool sizing is correct
- [ ] Database connections are properly managed (no leaks)
- [ ] Error handling for worker failures
- [ ] No race conditions in shared state
- [ ] WAL mode is properly enabled
- [ ] Type hints complete
- [ ] Docstrings comprehensive

**Verification Commands**:

```bash
# Run unit tests (should complete in < 300ms)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_parallel.py::TestParallelProcessing -v --tb=short --durations=0

# Run smoke tests (should complete in < 3 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_parallel.py -k smoke -v --tb=short --durations=0

# Run concurrency tests (should complete in < 5 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_parallel.py -k concurrency -v --tb=short --durations=0

# Run performance tests (should complete in < 10 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_parallel.py -k performance -v --durations=0

# Run all parallel tests (unit + smoke + concurrency + performance, should complete in < 20 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_parallel.py -v --tb=short --durations=0

# Check test coverage
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_parallel.py --cov=dsa110_contimg/photometry/parallel --cov-report=term-missing

# Fast failure mode (stop on first failure)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_parallel.py -x -v
```

**Performance Benchmarks**:

- Parallel processing: Near-linear speedup up to CPU count
- Batch processing: < 100ms per batch of 100 sources
- Database operations: No significant overhead from WAL mode
- Memory usage: < 10MB per worker

### Phase 3 Summary

**Key Outcomes**:

- Significant performance improvements (10-100x speedup with caching)
- Scalability for large source catalogs (100K+ sources)
- Efficient resource utilization
- Production-ready performance

**Risks & Mitigation**:

- Risk: Cache invalidation bugs causing stale data
- Mitigation: Comprehensive tests and timestamp-based validation
- Risk: Database concurrency issues
- Mitigation: WAL mode and proper locking

**Success Metrics**:

- Cache hit rate > 80%
- 10-100x speedup for cached operations
- Near-linear parallel speedup
- Handles 100K+ sources efficiently

---

## Phase 4: Advanced Analysis

**Duration**: 2-3 weeks  
**Priority**: Medium (enhances scientific capabilities)  
**Dependencies**: Phase 2, Phase 3

### Objectives

1. Implement multi-frequency analysis for ESE detection
2. Add multi-observable correlation analysis
3. Enhance detection confidence through correlation
4. Support advanced scientific use cases

### Tasks

#### 4.1 Multi-Frequency Analysis

**Effort**: 5-6 days  
**File Locations**:

- Implementation: `src/dsa110_contimg/photometry/multi_frequency.py` (new file)
- Database schema: `src/dsa110_contimg/database/schema_evolution.py` (add
  migrations)
- Integration points:
  - `src/dsa110_contimg/photometry/ese_detection.py` (add multi-frequency
    option)
  - `src/dsa110_contimg/api/models.py` (update job params)
  - `src/dsa110_contimg/photometry/cli.py` (add multi-frequency flag)
- Tests: `tests/unit/photometry/test_multi_frequency.py` (new file)
- Documentation: `docs/concepts/multi_frequency_analysis.md` (new file)

**Task Breakdown**:

1. **Design Multi-Frequency Analysis Architecture** (4-5 hours)
   - [ ] Review comprehensive improvements doc Section 4.1 for design
   - [ ] Frequency correlation algorithm:
     - [ ] Calculate variability at each frequency
     - [ ] Check for correlation across frequencies
     - [ ] Boost significance if correlated
   - [ ] Composite significance calculation:
     - [ ] Base significance from max frequency
     - [ ] Correlation boost: `1.0 + correlation_strength * 0.5`
     - [ ] Final: `base_significance * correlation_boost`
   - [ ] Database schema extensions:
     - [ ] Add `frequency_mhz` column to `photometry` table
     - [ ] Create `variability_stats_multi_freq` table
     - [ ] Indexes: `(source_id, frequency_mhz)`, `(source_id, measured_at)`

2. **Extend Database Schema** (2-3 hours)
   - [ ] Update `schema_evolution.py`:
     - [ ] Migration: `ALTER TABLE photometry ADD COLUMN frequency_mhz REAL`
     - [ ] Create table: `variability_stats_multi_freq`
       ```sql
       CREATE TABLE IF NOT EXISTS variability_stats_multi_freq (
           source_id TEXT NOT NULL,
           frequency_mhz REAL NOT NULL,
           sigma_deviation REAL,
           mean_flux_mjy REAL,
           std_flux_mjy REAL,
           n_obs INTEGER,
           PRIMARY KEY (source_id, frequency_mhz)
       )
       ```
     - [ ] Create indexes:
       - [ ] `CREATE INDEX idx_photometry_frequency ON photometry(source_id, frequency_mhz, measured_at)`
       - [ ] `CREATE INDEX idx_variability_multi_freq ON variability_stats_multi_freq(source_id, frequency_mhz)`

3. **Implement Frequency Correlation Analysis** (5-6 hours)
   - [ ] Create `src/dsa110_contimg/photometry/multi_frequency.py`
   - [ ] Function:
         `detect_ese_multi_frequency(source_id: str, frequencies: List[float], products_db: Path) -> dict`:
     - [ ] Get flux measurements at each frequency
     - [ ] Compute variability at each frequency
     - [ ] Analyze frequency correlation
     - [ ] Calculate composite significance
     - [ ] Return detection result
   - [ ] Function:
         `analyze_frequency_correlation(variability_by_freq: dict, frequencies: List[float]) -> dict`:
     - [ ] Extract sigma deviations for each frequency
     - [ ] Calculate correlation strength
     - [ ] Determine if correlated
     - [ ] Return correlation analysis

4. **Update Photometry Pipeline** (2-3 hours)
   - [ ] Update photometry storage to include frequency:
     - [ ] Store `frequency_mhz` when available
     - [ ] Update `photometry_insert()` function
   - [ ] Compute frequency-specific variability stats:
     - [ ] Group by frequency
     - [ ] Compute stats per frequency
     - [ ] Store in `variability_stats_multi_freq` table

5. **Integrate with Detection Pipeline** (3-4 hours)
   - [ ] Update `detect_ese_candidates()` in `ese_detection.py`:
     - [ ] Add parameter: `use_multi_frequency: bool = False`
     - [ ] Add parameter: `frequencies: Optional[List[float]] = None`
     - [ ] If `use_multi_frequency`:
       - [ ] Use `detect_ese_multi_frequency()`
       - [ ] Include correlation analysis in results
   - [ ] Update API models:
     - [ ] Add `use_multi_frequency` and `frequencies` to `ESEDetectJobParams`
   - [ ] Update CLI:
     - [ ] Add `--multi-frequency` flag
     - [ ] Add `--frequencies` argument (comma-separated)

6. **Write Comprehensive Tests** (5-6 hours)
   - [ ] Test file: `tests/unit/photometry/test_multi_frequency.py`
   - [ ] Test class: `TestMultiFrequencyAnalysis`
   - [ ] **Unit Test Checklist**:
     - [ ] Core functionality tests (3-7 cases)
     - [ ] Edge case tests (single frequency, missing frequencies, no
           correlation)
     - [ ] Error handling tests (invalid input, exceptions)
     - [ ] Smoke test for integration
   - [ ] **Unit tests** (execution time target: < 300ms total):
     - [ ] `test_frequency_correlation_correlated()` - Verify correlation
           detection
       - [ ] Input: High variability at multiple frequencies
       - [ ] Expected: Correlation detected, strength > 0.5
       - [ ] Execution time: < 50ms
     - [ ] `test_frequency_correlation_not_correlated()` - Verify no correlation
       - [ ] Input: Variability at one frequency only
       - [ ] Expected: No correlation detected
       - [ ] Execution time: < 30ms
     - [ ] `test_composite_significance_calculation()` - Verify composite
           significance
       - [ ] Input: Base significance 5.0, correlation strength 0.8
       - [ ] Expected: Composite significance ≈ 7.0 (5.0 \* 1.4)
       - [ ] Execution time: < 20ms
     - [ ] `test_detect_ese_multi_frequency()` - Verify multi-frequency
           detection
       - [ ] Input: Source with measurements at 3 frequencies
       - [ ] Expected: Detection result with frequency analysis
       - [ ] Execution time: < 100ms
     - [ ] `test_single_frequency()` - Verify single frequency handling
       - [ ] Input: Only one frequency available
       - [ ] Expected: Falls back to single-frequency analysis
       - [ ] Execution time: < 30ms
     - [ ] `test_missing_frequencies()` - Verify missing frequency handling
       - [ ] Input: Some frequencies missing measurements
       - [ ] Expected: Uses available frequencies, handles gracefully
       - [ ] Execution time: < 50ms
     - [ ] `test_database_schema()` - Verify schema extensions
       - [ ] Check `frequency_mhz` column exists
       - [ ] Check `variability_stats_multi_freq` table exists
       - [ ] Check indexes exist
       - [ ] Execution time: < 20ms
   - [ ] **Smoke tests** (execution time target: < 3 seconds):
     - [ ] `test_multi_frequency_integration_smoke()` - End-to-end integration
       - [ ] Use multi-frequency detection in pipeline
       - [ ] Verify results include correlation analysis
       - [ ] Execution time: < 2 seconds
     - [ ] `test_multi_frequency_api_smoke()` - API integration
       - [ ] Create job with `use_multi_frequency=true`
       - [ ] Verify multi-frequency analysis performed
       - [ ] Execution time: < 1 second
   - [ ] **Total test execution time**: < 4 seconds (unit + smoke)

7. **Create Documentation** (2-3 hours)
   - [ ] Create `docs/concepts/multi_frequency_analysis.md`:
     - [ ] Multi-frequency analysis guide
     - [ ] Scientific rationale (plasma lensing, frequency-dependent effects)
     - [ ] Use case examples
     - [ ] API/CLI usage examples
   - [ ] Update API documentation

**Deliverables Checklist**:

- [ ] `multi_frequency.py` created with analysis functions
- [ ] Database schema extended (migrations added)
- [ ] Integration with detection pipeline
- [ ] Updated API models and CLI
- [ ] Test suite created (`test_multi_frequency.py`)
- [ ] Documentation created
- [ ] All tests passing

**Acceptance Criteria** (All Must Pass):

- [ ] **Frequency Correlation**: Frequency correlation correctly identified
      (tested)
- [ ] **Composite Significance**: Composite significance calculated correctly
      (tested)
- [ ] **Database Schema**: Database schema supports multi-frequency data
      (tested)
- [ ] **API Integration**: API endpoints support multi-frequency analysis
      (tested)
- [ ] **CLI Integration**: CLI supports multi-frequency analysis (tested)
- [ ] **Test Coverage**:
      `pytest --cov=dsa110_contimg/photometry/multi_frequency` shows > 95%
      coverage

**Code Review Checklist**:

- [ ] Frequency correlation algorithm is correct
- [ ] Composite significance calculation matches specification
- [ ] Database migrations are reversible
- [ ] Error handling for missing frequencies
- [ ] Type hints complete
- [ ] Docstrings comprehensive

**Verification Commands**:

```bash
# Run unit tests (should complete in < 300ms)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_multi_frequency.py::TestMultiFrequencyAnalysis -v --tb=short --durations=0

# Run smoke tests (should complete in < 3 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_multi_frequency.py -k smoke -v --tb=short --durations=0

# Run all multi-frequency tests (unit + smoke, should complete in < 4 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_multi_frequency.py -v --tb=short --durations=0

# Check test coverage
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_multi_frequency.py --cov=dsa110_contimg/photometry/multi_frequency --cov-report=term-missing

# Fast failure mode (stop on first failure)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_multi_frequency.py -x -v

# Test API endpoint (requires API server running)
curl -X POST http://localhost:8000/api/jobs/ese-detect \
  -H "Content-Type: application/json" \
  -d '{"params": {"use_multi_frequency": true, "frequencies": [1000.0, 1500.0, 2000.0]}}'

# Test CLI
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.photometry.cli ese-detect \
  --multi-frequency --frequencies 1000.0,1500.0,2000.0
```

**Performance Benchmarks**:

- Multi-frequency detection: < 100ms per source (with 3 frequencies)
- Frequency correlation analysis: < 10ms per analysis
- Database queries: < 50ms per frequency query

#### 4.2 Multi-Observable Correlation

**Effort**: 5-6 days  
**File Locations**:

- Implementation: `src/dsa110_contimg/photometry/multi_observable.py` (new file)
- Database schema: `src/dsa110_contimg/database/schema_evolution.py` (add tables
  if needed)
- Integration points:
  - `src/dsa110_contimg/photometry/ese_detection.py` (add multi-observable
    option)
  - `src/dsa110_contimg/api/models.py` (update job params)
  - `src/dsa110_contimg/photometry/cli.py` (add multi-observable flag)
- Tests: `tests/unit/photometry/test_multi_observable.py` (new file)
- Documentation: `docs/concepts/multi_observable_analysis.md` (new file)

**Task Breakdown**:

1. **Design Multi-Observable Analysis Architecture** (4-5 hours)
   - [ ] Review comprehensive improvements doc Section 4.2 for design
   - [ ] Observable types:
     - [ ] Flux density (existing)
     - [ ] Scintillation bandwidth (new)
     - [ ] Dispersion measure (DM, for pulsars, new)
     - [ ] Scintillation timescale (new)
   - [ ] Correlation algorithm:
     - [ ] Analyze variability in each observable
     - [ ] Check for temporal correlation
     - [ ] Calculate correlation strength
   - [ ] Composite significance calculation:
     - [ ] Base significance from flux (primary)
     - [ ] Correlation boost: `1.0 + correlation_strength * 0.3`
     - [ ] Final: `base_significance * correlation_boost`

2. **Implement Observable Analysis Functions** (5-6 hours)
   - [ ] Create `src/dsa110_contimg/photometry/multi_observable.py`
   - [ ] Function: `analyze_flux_variability()` (update existing or create
         wrapper):
     - [ ] Use existing flux variability analysis
     - [ ] Return variability metrics
   - [ ] Function:
         `analyze_scintillation_variability(source_id: str, products_db: Path) -> dict`:
     - [ ] Get scintillation bandwidth measurements
     - [ ] Calculate variability metrics
     - [ ] Return variability result
   - [ ] Function:
         `analyze_dm_variability(source_id: str, products_db: Path) -> dict`:
     - [ ] Get DM measurements (for pulsars)
     - [ ] Calculate variability metrics
     - [ ] Return variability result
   - [ ] Function:
         `analyze_scintillation_timescale(source_id: str, products_db: Path) -> dict`:
     - [ ] Get scintillation timescale measurements
     - [ ] Calculate variability metrics
     - [ ] Return variability result

3. **Implement Correlation Analysis** (4-5 hours)
   - [ ] Function:
         `calculate_observable_correlation(observable_results: dict) -> dict`:
     - [ ] Extract variability indicators from each observable
     - [ ] Check for temporal correlation
     - [ ] Calculate correlation strength (0.0 to 1.0)
     - [ ] Determine if correlated (strength > 0.5)
     - [ ] Return correlation analysis
   - [ ] Correlation strength calculation:
     - [ ] Count observables with high variability
     - [ ] Check temporal alignment
     - [ ] Calculate strength: `high_variability_count / total_observables`

4. **Integrate with Detection Pipeline** (3-4 hours)
   - [ ] Function:
         `detect_ese_multi_observable(source_id: str, observables: dict, products_db: Path) -> dict`:
     - [ ] Analyze each observable
     - [ ] Calculate correlation
     - [ ] Compute composite significance
     - [ ] Return detection result
   - [ ] Update `detect_ese_candidates()` in `ese_detection.py`:
     - [ ] Add parameter: `use_multi_observable: bool = False`
     - [ ] Add parameter: `observables: Optional[dict] = None`
     - [ ] If `use_multi_observable`:
       - [ ] Use `detect_ese_multi_observable()`
       - [ ] Include correlation analysis in results
   - [ ] Update API models:
     - [ ] Add `use_multi_observable` and `observables` to `ESEDetectJobParams`
   - [ ] Update CLI:
     - [ ] Add `--multi-observable` flag
     - [ ] Add `--observables` argument (comma-separated list)

5. **Extend Database Schema** (2-3 hours, if needed)
   - [ ] Create tables for scintillation data (if needed):
     ```sql
     CREATE TABLE IF NOT EXISTS scintillation_data (
         source_id TEXT NOT NULL,
         measured_at REAL NOT NULL,
         scintillation_bandwidth_mhz REAL,
         scintillation_timescale_sec REAL,
         PRIMARY KEY (source_id, measured_at)
     )
     ```
   - [ ] Create tables for DM data (if needed):
     ```sql
     CREATE TABLE IF NOT EXISTS dm_data (
         source_id TEXT NOT NULL,
         measured_at REAL NOT NULL,
         dm_pc_cm3 REAL,
         PRIMARY KEY (source_id, measured_at)
     )
     ```
   - [ ] Create indexes as needed

6. **Write Comprehensive Tests** (5-6 hours)
   - [ ] Test file: `tests/unit/photometry/test_multi_observable.py`
   - [ ] Test class: `TestMultiObservableAnalysis`
   - [ ] **Unit Test Checklist**:
     - [ ] Core functionality tests (3-7 cases)
     - [ ] Edge case tests (missing observables, single observable, no
           correlation)
     - [ ] Error handling tests (invalid input, exceptions)
     - [ ] Smoke test for integration
   - [ ] **Unit tests** (execution time target: < 400ms total):
     - [ ] `test_analyze_scintillation_variability()` - Verify scintillation
           analysis
       - [ ] Input: Scintillation bandwidth measurements
       - [ ] Expected: Variability metrics calculated
       - [ ] Execution time: < 50ms
     - [ ] `test_analyze_dm_variability()` - Verify DM analysis
       - [ ] Input: DM measurements
       - [ ] Expected: Variability metrics calculated
       - [ ] Execution time: < 50ms
     - [ ] `test_observable_correlation_correlated()` - Verify correlation
           detection
       - [ ] Input: High variability in multiple observables
       - [ ] Expected: Correlation detected, strength > 0.5
       - [ ] Execution time: < 50ms
     - [ ] `test_observable_correlation_not_correlated()` - Verify no
           correlation
       - [ ] Input: Variability in one observable only
       - [ ] Expected: No correlation detected
       - [ ] Execution time: < 30ms
     - [ ] `test_composite_significance_with_correlation()` - Verify composite
           significance
       - [ ] Input: Base significance 5.0, correlation strength 0.8
       - [ ] Expected: Composite significance ≈ 6.2 (5.0 \* 1.24)
       - [ ] Execution time: < 20ms
     - [ ] `test_detect_ese_multi_observable()` - Verify multi-observable
           detection
       - [ ] Input: Source with flux and scintillation data
       - [ ] Expected: Detection result with correlation analysis
       - [ ] Execution time: < 100ms
     - [ ] `test_missing_observables()` - Verify missing observable handling
       - [ ] Input: Some observables missing data
       - [ ] Expected: Uses available observables, handles gracefully
       - [ ] Execution time: < 50ms
     - [ ] `test_single_observable()` - Verify single observable handling
       - [ ] Input: Only flux data available
       - [ ] Expected: Falls back to single-observable analysis
       - [ ] Execution time: < 30ms
   - [ ] **Smoke tests** (execution time target: < 3 seconds):
     - [ ] `test_multi_observable_integration_smoke()` - End-to-end integration
       - [ ] Use multi-observable detection in pipeline
       - [ ] Verify results include correlation analysis
       - [ ] Execution time: < 2 seconds
     - [ ] `test_multi_observable_api_smoke()` - API integration
       - [ ] Create job with `use_multi_observable=true`
       - [ ] Verify multi-observable analysis performed
       - [ ] Execution time: < 1 second
   - [ ] **Total test execution time**: < 4 seconds (unit + smoke)

7. **Create Documentation** (2-3 hours)
   - [ ] Create `docs/concepts/multi_observable_analysis.md`:
     - [ ] Multi-observable analysis guide
     - [ ] Scientific rationale (flux, scintillation, DM correlations)
     - [ ] Use case examples
     - [ ] API/CLI usage examples
   - [ ] Update API documentation

**Deliverables Checklist**:

- [ ] `multi_observable.py` created with analysis functions
- [ ] Database schema extended (if needed)
- [ ] Integration with detection pipeline
- [ ] Updated API models and CLI
- [ ] Test suite created (`test_multi_observable.py`)
- [ ] Documentation created
- [ ] All tests passing

**Acceptance Criteria** (All Must Pass):

- [ ] **Multiple Observables**: Multiple observables analyzed correctly (tested)
- [ ] **Correlation**: Correlation correctly identified (tested)
- [ ] **Composite Significance**: Composite significance includes correlation
      boost (tested)
- [ ] **API Integration**: API endpoints support multi-observable analysis
      (tested)
- [ ] **CLI Integration**: CLI supports multi-observable analysis (tested)
- [ ] **Test Coverage**:
      `pytest --cov=dsa110_contimg/photometry/multi_observable` shows > 95%
      coverage

**Code Review Checklist**:

- [ ] Observable analysis functions are correct
- [ ] Correlation algorithm is sound
- [ ] Composite significance calculation matches specification
- [ ] Error handling for missing observables
- [ ] Type hints complete
- [ ] Docstrings comprehensive

**Verification Commands**:

```bash
# Run unit tests (should complete in < 400ms)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_multi_observable.py::TestMultiObservableAnalysis -v --tb=short --durations=0

# Run smoke tests (should complete in < 3 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_multi_observable.py -k smoke -v --tb=short --durations=0

# Run all multi-observable tests (unit + smoke, should complete in < 4 seconds)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_multi_observable.py -v --tb=short --durations=0

# Check test coverage
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_multi_observable.py --cov=dsa110_contimg/photometry/multi_observable --cov-report=term-missing

# Fast failure mode (stop on first failure)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/photometry/test_multi_observable.py -x -v

# Test API endpoint (requires API server running)
curl -X POST http://localhost:8000/api/jobs/ese-detect \
  -H "Content-Type: application/json" \
  -d '{"params": {"use_multi_observable": true, "observables": ["flux", "scintillation"]}}'

# Test CLI
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.photometry.cli ese-detect \
  --multi-observable --observables flux,scintillation
```

**Performance Benchmarks**:

- Multi-observable detection: < 150ms per source (with 2-3 observables)
- Observable correlation analysis: < 20ms per analysis
- Database queries: < 50ms per observable query

### Phase 4 Summary

**Key Outcomes**:

- Advanced scientific capabilities (multi-frequency, multi-observable)
- Enhanced detection confidence through correlation
- Support for complex ESE analysis scenarios
- Foundation for future research capabilities

**Risks & Mitigation**:

- Risk: Limited availability of multi-frequency/multi-observable data
- Mitigation: Graceful degradation when data unavailable
- Risk: Complex correlation algorithms may need tuning
- Mitigation: Validation framework and iterative improvement

**Success Metrics**:

- Multi-frequency correlation correctly identified
- Multi-observable correlation correctly identified
- Enhanced confidence for correlated variability
- Documentation complete

---

## Implementation Strategy

### Recommended Approach

1. **Sequential Phases**: Implement phases in order (1 → 2 → 3 → 4)
   - Each phase builds on previous phases
   - Dependencies clearly defined
   - Can validate each phase before moving to next

2. **Parallel Workstreams** (within phases):
   - Phase 1: Can work on 1.1 and 1.2 in parallel (different developers)
   - Phase 2: Can work on 2.1 and 2.2 in parallel
   - Phase 3: Can work on 3.1 and 3.2 in parallel
   - Phase 4: Sequential (4.2 depends on 4.1 concepts)

3. **Incremental Delivery**:
   - Each task delivers working, tested code
   - Can deploy improvements incrementally
   - No "big bang" releases

### Testing Strategy

- **Unit Tests**: Written alongside implementation
- **Integration Tests**: After each phase completion
- **Validation Tests**: After Phase 2 (scoring validation)
- **Performance Tests**: After Phase 3 (caching/parallel)
- **End-to-End Tests**: After Phase 4 (complete system)

### Documentation Strategy

- **Technical Documentation**: Updated during implementation
- **User Documentation**: Updated after each phase
- **API Documentation**: Updated as APIs change
- **Scientific Documentation**: Updated after Phase 4

### Deployment Strategy

- **Phase 1**: Internal testing, no user-facing changes
- **Phase 2**: Feature flags for new scoring/presets
- **Phase 3**: Gradual rollout of caching/parallel processing
- **Phase 4**: Optional features, available for advanced users

---

## Risk Management

### Technical Risks

| Risk                            | Impact | Probability | Mitigation                  |
| ------------------------------- | ------ | ----------- | --------------------------- |
| Breaking existing functionality | High   | Medium      | Comprehensive test suite    |
| Performance regressions         | Medium | Low         | Performance tests           |
| Cache invalidation bugs         | High   | Medium      | Timestamp validation, tests |
| Database concurrency issues     | High   | Medium      | WAL mode, proper locking    |
| Scoring weights need tuning     | Medium | High        | Validation framework        |

### Schedule Risks

| Risk                  | Impact | Probability | Mitigation                |
| --------------------- | ------ | ----------- | ------------------------- |
| Underestimated effort | Medium | Medium      | Buffer time in estimates  |
| Dependencies delayed  | Medium | Low         | Clear dependency tracking |
| Scope creep           | Medium | Medium      | Strict phase boundaries   |

---

## Success Criteria

### Phase 1 Success

- [ ] Zero code duplication for sigma deviation
- [ ] Test coverage > 90%
- [ ] All existing functionality preserved
- [ ] Documentation complete

### Phase 2 Success

- [ ] Composite scoring reduces false positives
- [ ] Presets cover common use cases
- [ ] API and CLI fully support new features
- [ ] Documentation complete

### Phase 3 Success

- [ ] Cache hit rate > 80%
- [ ] 10-100x speedup for cached operations
- [ ] Near-linear parallel speedup
- [ ] Handles 100K+ sources efficiently

### Phase 4 Success

- [ ] Multi-frequency correlation correctly identified
- [ ] Multi-observable correlation correctly identified
- [ ] Enhanced confidence for correlated variability
- [ ] Documentation complete

### Overall Success

- [ ] All phases completed
- [ ] Production-ready system
- [ ] Comprehensive documentation
- [ ] Validated against real data

---

## Next Steps

1. **Review and Approve**: Review this phased plan with stakeholders
2. **Prioritize**: Confirm phase order and priorities
3. **Resource Allocation**: Assign developers to phases
4. **Kickoff Phase 1**: Begin implementation of foundation phase
5. **Track Progress**: Use this document to track phase completion

---

## References

- **Comprehensive Improvements**: `ese_detection_comprehensive_improvements.md`
- **Current Implementation**: `ese_detection_implementation_summary.md`
- **Architecture**: `ese_detection_architecture.md`
- **User Guide**: `ese_detection_guide.md`

---

## Document Improvements Summary

This document has been enhanced with the following improvements to increase
implementation precision and quality:

### 1. **General Implementation Guidelines Section**

- Pre-implementation checklist (read specs, set up environment, create branch)
- During-implementation best practices (TDD, integration verification,
  documentation)
- Code quality standards (type hints, docstrings, error handling, testing,
  style)
- **Unit and Smoke Testing Strategy** (comprehensive testing guidelines)
- Pre-PR verification checklist (enhanced with unit/smoke test requirements)
- Common pitfalls to avoid

### 2. **Enhanced Task Breakdowns**

Each major task now includes:

- **File Locations**: Exact file paths for implementation, tests, and
  integration points
- **Task Breakdown**: Step-by-step subtasks with time estimates
- **Detailed Specifications**: Function signatures, algorithm details, expected
  behaviors
- **Deliverables Checklist**: Comprehensive list of all deliverables
- **Acceptance Criteria**: Measurable, testable criteria (all must pass)
- **Code Review Checklist**: Specific items for reviewers to check
- **Verification Commands**: Exact commands to run for verification
- **Performance Benchmarks**: Specific performance targets where applicable
- **Rollback Procedures**: Steps to revert if issues are found

### 3. **Specific Improvements by Task**

**Task 1.1 (Sigma Deviation)**:

- Exact function signature specification
- Detailed input validation requirements
- Specific test cases with expected outputs
- Verification commands using `grep` to check for code duplication
- Manual verification steps with known test values

**Task 1.2 (Validation Test Suite)**:

- Detailed test infrastructure requirements
- Specific test cases with input/output specifications
- Performance test thresholds (e.g., < 60 seconds for 10K sources)
- Test coverage targets (> 90%)
- Verification commands for different test categories

**Task 2.1 (Multi-Metric Scoring)**:

- Complete algorithm specification with formulas
- Default weight values and normalization strategies
- Confidence level thresholds
- Configuration file structure (YAML example)
- Integration points with exact function names and parameters
- Validation framework requirements
- Performance benchmarks (< 1ms per candidate, < 5% overhead)
- **Unit and smoke test requirements** with execution time targets

### 4. **Unit and Smoke Test Integration**

**Comprehensive Testing Strategy**:

- **Unit Test Guidelines**: Speed-focused (< 100ms per test, < 30 seconds total
  suite)
- **Smoke Test Guidelines**: Critical path validation (< 5 seconds per test, < 2
  minutes total)
- **Test Checklists**: Integrated into each task (3-7 core tests, edge cases,
  error handling, smoke test)
- **Execution Time Targets**: Specific targets for each test category
- **Fast Failure**: Immediate error detection with `-x` flag
- **Test Structure**: Arrange-Act-Assert pattern with clear documentation

**Integration Points**:

- Task 1.1: 10 unit tests + 1 smoke test (< 100ms total)
- Task 1.2: Unit tests for all metrics + smoke tests (< 200ms unit, < 2 seconds
  smoke)
- Task 2.1: 8 unit tests + 2 smoke tests + 2 validation tests (< 4 seconds
  total)
- Task 2.2: 9 unit tests + 3 smoke tests (< 1.5 seconds total)
- Task 3.1: 8 unit tests + 2 smoke tests + 1 performance test (< 8 seconds
  total)
- Task 3.2: 8 unit tests + 2 smoke tests + 2 concurrency tests + 2 performance
  tests (< 20 seconds total)
- Task 4.1: 7 unit tests + 2 smoke tests (< 4 seconds total)
- Task 4.2: 8 unit tests + 2 smoke tests (< 4 seconds total)
- All tasks include verification commands with execution time checks

### 5. **Benefits of These Improvements**

- **Reduced Ambiguity**: Exact file paths, function signatures, and expected
  behaviors eliminate guesswork
- **Faster Onboarding**: New developers can start immediately with clear
  specifications
- **Better Quality**: Comprehensive checklists ensure nothing is missed
- **Easier Verification**: Specific commands and criteria make validation
  straightforward
- **Risk Mitigation**: Rollback procedures and common pitfalls help avoid issues
- **Consistent Implementation**: Detailed specifications ensure consistent
  results across developers

### 6. **How to Use This Document**

1.  **Before Starting**: Read "General Implementation Guidelines" and "Unit and
    Smoke Testing Strategy" sections
2.  **For Each Task**: Follow the task breakdown in order, including unit/smoke
    test requirements
3.  **During Implementation**:
    - Write unit tests first (TDD approach)
    - Run tests frequently to catch issues early
    - Verify execution times meet targets
4.  **Before PR**:
    - Complete verification checklist (including unit/smoke test requirements)
    - Run all verification commands
    - Ensure test execution times meet targets
5.  **If Issues**: Follow rollback procedures and document problems

### 7. **Future Enhancements**

Additional improvements that could be made:

- Add more detailed examples for Phase 3 and Phase 4 tasks
- Include diagrams for complex algorithms
- Add troubleshooting guides for common issues
- Create implementation templates for common patterns
- Add progress tracking templates

---

**Last Updated**: 2025-11-12  
**Version**: 2.0 (Enhanced with detailed specifications)
