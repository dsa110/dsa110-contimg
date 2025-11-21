# Test Organization Strategy

## Test Taxonomy

Tests are organized by **purpose** and **scope**, not just by module. This
ensures:

- Fast feedback loops (run fast tests first)
- Clear test purposes (know what each test validates)
- Efficient CI/CD (run appropriate tests at each stage)

## Test Categories

### 1. Unit Tests (`tests/unit/`)

**Purpose:** Test individual components in isolation with mocked dependencies.

**Characteristics:**

- Fast (< 1 second per test typically)
- No external dependencies (databases, filesystems, network)
- Use mocks/stubs for all external interactions
- Test single functions, classes, or small modules
- Should run on every code change

**Organization:** By module/component

```
tests/unit/
  ├── api/           # API endpoint tests
  ├── calibration/   # Calibration algorithm tests
  ├── catalog/       # Catalog query/access tests
  ├── conversion/    # Data conversion tests
  ├── database/      # Database schema/query tests
  ├── imaging/       # Imaging algorithm tests
  ├── mosaic/        # Mosaic creation tests
  ├── photometry/    # Photometry measurement tests
  ├── pipeline/      # Pipeline stage/context tests
  ├── qa/            # QA validation tests
  ├── simulation/    # Synthetic data generation tests
  └── visualization/ # Visualization/plotting tests
```

### 2. Integration Tests (`tests/integration/`)

**Purpose:** Test how multiple components work together.

**Characteristics:**

- Moderate speed (seconds to minutes)
- May use real databases, filesystems
- Test component interactions and workflows
- May require test fixtures/data
- Run on PRs and before releases

**Organization:** By workflow/system

```
tests/integration/
  ├── test_calibration_workflow.py      # Full calibration pipeline
  ├── test_end_to_end_batch_workflow.py # Batch processing workflows
  ├── test_orchestrator.py              # Pipeline orchestration
  ├── test_stage_interactions.py        # Stage chaining
  ├── test_streaming_mosaic_manager.py  # Streaming mosaic creation
  ├── test_streaming_photometry.py      # Streaming photometry
  └── ...
```

### 3. Smoke Tests (`tests/smoke/`)

**Purpose:** Quick sanity checks to verify basic functionality.

**Characteristics:**

- Very fast (< 10 seconds total)
- Minimal setup required
- Test critical paths only
- Run on every commit
- Should never be skipped

**Organization:** By critical path

```
tests/smoke/
  ├── test_imports.py              # All modules importable
  ├── test_api_health.py           # API endpoints respond
  ├── test_database_connectivity.py # Database accessible
  └── test_basic_workflows.py      # Core workflows functional
```

### 4. Science/Validation Tests (`tests/science/`)

**Purpose:** Validate scientific correctness and algorithm accuracy.

**Characteristics:**

- May be slow (minutes)
- May require real observational data
- Test scientific algorithms, not just code correctness
- Validate against known results
- Run before releases and on scientific validation

**Organization:** By validation type

```
tests/science/
  ├── test_calibration_scientific_validation.py  # Calibration accuracy
  ├── test_calibration_integration_validation.py # End-to-end calibration
  ├── test_casa_compliance.py                    # CASA standard compliance
  └── ...
```

### 5. End-to-End Tests (`tests/e2e/`)

**Purpose:** Test complete workflows from input to output.

**Characteristics:**

- Slowest tests (minutes to hours)
- May require synthetic or real data
- Test full pipeline execution
- Validate complete data products
- Run on scheduled basis or before major releases

**Organization:** By workflow type

```
tests/e2e/
  ├── test_full_imaging_pipeline.py    # Complete imaging workflow
  ├── test_full_calibration_pipeline.py # Complete calibration workflow
  └── ...
```

## Test Markers

All tests should be marked appropriately:

```python
@pytest.mark.unit          # Unit test (fast, isolated)
@pytest.mark.integration   # Integration test
@pytest.mark.smoke         # Smoke test (critical path)
@pytest.mark.science       # Science validation test
@pytest.mark.e2e          # End-to-end test
@pytest.mark.slow         # Slow test (> 1 minute)
@pytest.mark.casa         # Requires CASA environment
```

## Running Tests

### Quick Development Cycle

```bash
# Run only fast unit tests
pytest -m "unit and not slow" -x

# Run smoke tests
pytest -m smoke -x
```

### Pre-Commit

```bash
# Run unit + smoke tests
pytest -m "unit or smoke" -x
```

### PR Validation

```bash
# Run unit + integration tests
pytest -m "unit or integration" -x
```

### Full Validation

```bash
# Run all tests
pytest tests/
```

## Migration Strategy

1. **Phase 1:** Organize existing tests into proper categories
2. **Phase 2:** Add appropriate markers to all tests
3. **Phase 3:** Create smoke test suite
4. **Phase 4:** Document test purposes and requirements

## File Naming Conventions

- Unit tests: `test_<module>_<feature>.py`
- Integration tests: `test_<workflow>_<component>.py`
- Smoke tests: `test_<critical_path>.py`
- Science tests: `test_<validation_type>_<algorithm>.py`

## Principles

1. **Fast feedback:** Fast tests run first, slow tests run later
2. **Clear purpose:** Test name and location indicate what it tests
3. **Isolation:** Unit tests don't depend on external resources
4. **Completeness:** Integration tests cover real workflows
5. **Maintainability:** Easy to find and update related tests
