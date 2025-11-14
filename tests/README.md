# Test Suite Organization

This directory contains the test suite for the DSA-110 Continuum Imaging
Pipeline.

## Test Taxonomy

Tests are organized by **purpose** and **scope** to enable efficient test
execution and clear test purposes.

See
[docs/concepts/TEST_ORGANIZATION.md](../../docs/concepts/TEST_ORGANIZATION.md)
for the complete test organization strategy.

## Directory Structure

```
tests/
├── smoke/              # Quick sanity checks (< 10s total)
├── unit/               # Unit tests (fast, isolated, mocked)
│   ├── api/           # API endpoint tests
│   ├── calibration/   # Calibration algorithm tests
│   ├── catalog/       # Catalog query/access tests
│   ├── conversion/    # Data conversion tests
│   ├── database/      # Database schema/query tests
│   ├── imaging/       # Imaging algorithm tests
│   ├── mosaic/        # Mosaic creation tests
│   ├── photometry/    # Photometry measurement tests
│   ├── pipeline/      # Pipeline stage/context tests
│   ├── qa/            # QA validation tests
│   ├── simulation/    # Synthetic data generation tests
│   └── visualization/ # Visualization/plotting tests
├── integration/        # Integration tests (component interactions)
├── science/           # Science validation tests (algorithm correctness)
└── e2e/               # End-to-end tests (full workflows)
```

## Running Tests

### Quick Development Cycle

```bash
# Run smoke tests (fastest)
./scripts/run-tests.sh smoke

# Run unit tests (fast)
./scripts/run-tests.sh unit

# Run quick tests (smoke + unit, no slow)
./scripts/run-tests.sh quick
```

### Pre-Commit

```bash
# Run smoke + unit tests
./scripts/run-tests.sh quick
```

### PR Validation

```bash
# Run unit + integration tests
./scripts/run-tests.sh unit
./scripts/run-tests.sh integration
```

### Full Validation

```bash
# Run all tests
./scripts/run-tests.sh all
```

## Test Markers

Tests should be marked with appropriate pytest markers:

- `@pytest.mark.unit` - Unit test (fast, isolated)
- `@pytest.mark.integration` - Integration test
- `@pytest.mark.smoke` - Smoke test (critical path)
- `@pytest.mark.science` - Science validation test
- `@pytest.mark.e2e` - End-to-end test
- `@pytest.mark.slow` - Slow test (> 1 minute)
- `@pytest.mark.casa` - Requires CASA environment

## Test Organization Principles

1. **Fast feedback:** Fast tests run first, slow tests run later
2. **Clear purpose:** Test name and location indicate what it tests
3. **Isolation:** Unit tests don't depend on external resources
4. **Completeness:** Integration tests cover real workflows
5. **Maintainability:** Easy to find and update related tests

## Adding New Tests

When adding a new test:

1. **Determine test type:**
   - Unit test: Tests single component in isolation → `tests/unit/<module>/`
   - Integration test: Tests component interactions → `tests/integration/`
   - Smoke test: Quick sanity check → `tests/smoke/`
   - Science test: Algorithm validation → `tests/science/`
   - E2E test: Full workflow → `tests/e2e/`

2. **Add appropriate markers:**

   ```python
   @pytest.mark.unit
   def test_my_feature():
       ...
   ```

3. **Follow naming conventions:**
   - Unit: `test_<module>_<feature>.py`
   - Integration: `test_<workflow>_<component>.py`
   - Smoke: `test_<critical_path>.py`

## Test Statistics

- **Unit tests:** ~98 files
- **Integration tests:** ~16 files
- **Smoke tests:** ~1 file
- **Science tests:** ~5 files
- **E2E tests:** ~0 files (workflows in integration/)
