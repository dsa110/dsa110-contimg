# Integration Test Optimization Guide

## Shared Fixtures

Use the fixtures in `tests/integration/conftest.py`:

- `shared_temp_dir` - Session-scoped temporary directory (reused across tests)
- `clean_test_dir` - Function-scoped clean directory for each test
- `casa6_python` - Verifies casa6 Python is being used

## Example: Optimized Integration Test

```python
import pytest
from pathlib import Path

@pytest.mark.integration
@pytest.mark.synthetic
def test_example(clean_test_dir, casa6_python):
    """Example using shared fixtures."""
    # Use clean_test_dir instead of tmp_path for faster execution
    output_file = clean_test_dir / "output.fits"

    # Test code here...
    assert output_file.exists()
```

## Parallel Execution

### Install pytest-xdist

```bash
conda activate casa6
pip install pytest-xdist
```

### Run tests in parallel

```bash
# Auto-detect CPU cores
pytest tests/integration -n auto

# Specify worker count
pytest tests/integration -n 4

# Run only fast integration tests
pytest tests/integration -m "integration and not slow" -n auto
```

## Test Markers

Use markers to categorize tests:

- `@pytest.mark.integration` - Integration test
- `@pytest.mark.slow` - Slow test (>1 second)
- `@pytest.mark.synthetic` - Uses synthetic data
- `@pytest.mark.casa` - Requires CASA tools

## Selective Test Execution

```bash
# Run only fast integration tests
pytest -m "integration and not slow"

# Run only synthetic data tests
pytest -m "synthetic"

# Run specific test file
pytest tests/integration/test_orchestrator.py -n auto
```

## Performance Tips

1. **Use session-scoped fixtures** for expensive setup
2. **Use in-memory repositories** instead of file-based when possible
3. **Mock external dependencies** (APIs, file I/O)
4. **Run tests in parallel** with pytest-xdist
5. **Use selective markers** to run only necessary tests
