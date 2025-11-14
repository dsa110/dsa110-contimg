# Agent Guide: Fast, Targeted Testing for DSA-110 Continuum Pipeline

This repo requires the CASA6 Python environment for all Python execution.

- Python: `/opt/miniforge/envs/casa6/bin/python` (never use `python`/`python3`)
- Quick sanity: `python tests/test_priority1_quick.py`

## Default Strategy

- Prefer unit tests with mocks; run the smallest relevant subset first.
- Fail fast: `-q -x --maxfail=1`, then rerun the single failing node.
- Avoid running notebooks or long end-to-end scripts by default.
- Use ripgrep for search: `rg -n "pattern" path/`.

Quick commands:

- `make test-smoke` — ultra-fast (few-file) smoke
- `make test-fast` — fast unit subset, fail-fast
- `make test-impacted` — only tests mapped from changed files (use `BASE_REF` to override base)

## Selecting Tests

1) Map changes to tests (example):

```
CHANGED=$(git diff --name-only HEAD~1)
for f in $CHANGED; do
  case "$f" in
    src/dsa110_contimg/imaging/*)      rg -l "dsa110_contimg\.imaging" tests | xargs -r /opt/miniforge/envs/casa6/bin/python -m pytest -q -x --maxfail=1 ;; 
    src/dsa110_contimg/pipeline/*)     /opt/miniforge/envs/casa6/bin/python -m pytest -q -x --maxfail=1 tests/integration/test_orchestrator.py tests/test_pipeline.py ;; 
    src/dsa110_contimg/qa/*)           /opt/miniforge/envs/casa6/bin/python -m pytest -q -x --maxfail=1 test_html_reports_simple.py test_validation_plots.py ;; 
    src/dsa110_contimg/catalog/*)      /opt/miniforge/envs/casa6/bin/python -m pytest -q -x --maxfail=1 tests/unit/test_catalog_validation.py ;; 
    *)                                 make test-unit ;;
  esac
done
```

2) Markers:

- Include: `unit`
- Exclude: `integration`, `slow`, `casa` (unless explicitly needed)

Examples:

```
make test-unit
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit -q -x -m "unit and not slow"
```

## Integration Tests

Only run when ALL are true:

- `TEST_WITH_SYNTHETIC_DATA=1`
- CASA6 Python available
- `pyuvdata` and `casacore` importable

Example:

```
TEST_WITH_SYNTHETIC_DATA=1 /opt/miniforge/envs/casa6/bin/python -m pytest -q -x tests/integration/test_orchestrator.py
```

## Safety and Fixtures

- Do not write to global `state/` in tests; use `tmp_path` or in-memory repos.
- Useful fixtures: `mock_table_factory`, `mock_casa_tasks`, `mock_wsclean_subprocess`, `in_memory_repo`, `sqlite_repo` (see `tests/conftest.py`).
- For pipeline config in tests, prefer direct `PipelineConfig(...)` or `from_dict` over `from_env(validate_paths=True)`.

## Common One-Liners

```
# Focused rerun of a single failing node
/opt/miniforge/envs/casa6/bin/python -m pytest -q tests/<file>::<ClassOrModule>::<test>

# Impacted tests for a specific module
MOD=src/dsa110_contimg/imaging/cli_imaging.py; rg -l "dsa110_contimg\.imaging.*cli_imaging" tests | xargs -r /opt/miniforge/envs/casa6/bin/python -m pytest -q -x --maxfail=1
```
