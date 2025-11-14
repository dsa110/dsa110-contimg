# Adding New Tests - Organization Guide

## Quick Reference

When adding a new test file, follow these steps:

### 1. Determine Test Type

**Unit Test** (`tests/unit/<module>/`)

- Tests single component in isolation
- Uses mocks for all dependencies
- Fast (< 1 second per test)
- Example: `tests/unit/api/test_new_endpoint.py`

**Integration Test** (`tests/integration/`)

- Tests component interactions
- May use real databases/filesystems
- Moderate speed (seconds to minutes)
- Example: `tests/integration/test_new_workflow.py`

**Smoke Test** (`tests/smoke/`)

- Quick sanity checks
- Critical path only
- Very fast (< 10 seconds total)
- Example: `tests/smoke/test_basic_functionality.py`

**Science Test** (`tests/science/`)

- Algorithm validation
- Scientific correctness
- May require real data
- Example: `tests/science/test_algorithm_accuracy.py`

### 2. Choose Location

```
tests/
├── smoke/              # Quick sanity checks
├── unit/               # Unit tests (by module)
│   ├── api/
│   ├── calibration/
│   ├── catalog/
│   ├── conversion/
│   ├── database/
│   ├── imaging/
│   ├── mosaic/
│   ├── photometry/
│   ├── pipeline/
│   ├── qa/
│   ├── simulation/
│   └── visualization/
├── integration/        # Integration tests
├── science/           # Science validation
└── e2e/              # End-to-end tests
```

### 3. Add Required Marker

**Every test file MUST have the appropriate pytest marker:**

```python
import pytest

@pytest.mark.unit  # or integration, smoke, science, e2e
def test_my_feature():
    ...
```

**For class-based tests:**

```python
import pytest

@pytest.mark.unit
class TestMyFeature:
    def test_something(self):
        ...
```

### 4. File Naming

- Unit: `test_<module>_<feature>.py`
- Integration: `test_<workflow>_<component>.py`
- Smoke: `test_<critical_path>.py`

### 5. Validation

Before committing, run:

```bash
# Validate test organization
./scripts/validate-test-organization.py

# Or use the enforcer
./scripts/test-organization-enforcer.sh check
```

## Automated Enforcement

The test organization is **automatically enforced**:

1. **Pre-commit hook** - Validates staged test files before commit
2. **CI/CD integration** - Validates all tests in CI pipeline
3. **Validation script** - Can be run manually:
   `scripts/validate-test-organization.py`

## Common Mistakes to Avoid

❌ **Wrong:** Test in `tests/` root ✅ **Right:** Test in appropriate
subdirectory

❌ **Wrong:** Missing pytest marker ✅ **Right:** Always include
`@pytest.mark.unit` (or appropriate marker)

❌ **Wrong:** Unit test in `tests/integration/` ✅ **Right:** Unit test in
`tests/unit/<module>/`

❌ **Wrong:** Integration test without marker ✅ **Right:** Integration test
with `@pytest.mark.integration`

## Examples

### Example 1: New API Endpoint Test

```python
# File: tests/unit/api/test_new_endpoint.py
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
def test_new_endpoint_success():
    """Test new API endpoint."""
    # ... test code ...
```

### Example 2: New Integration Test

```python
# File: tests/integration/test_new_workflow.py
import pytest

@pytest.mark.integration
class TestNewWorkflow:
    def test_workflow_completes(self):
        """Test complete workflow."""
        # ... test code ...
```

### Example 3: New Smoke Test

```python
# File: tests/smoke/test_critical_path.py
import pytest

@pytest.mark.smoke
def test_critical_imports():
    """Quick check that critical modules import."""
    # ... test code ...
```

## Need Help?

- See `docs/concepts/TEST_ORGANIZATION.md` for complete taxonomy
- See `tests/README.md` for test suite overview
- Run `./scripts/test-organization-enforcer.sh` for validation
