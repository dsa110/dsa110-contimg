# Fast, Targeted Testing

Speed up feedback when iterating on the pipeline by running only the most
relevant tests first, and failing fast.

## Prerequisites

- Always use CASA6 Python for local runs: `/opt/miniforge/envs/casa6/bin/python`
- Set `PYTHONPATH` to include `src/` or use `make` targets which do this for
  you.

## Quick Options

- Smoke (ultra-fast):

```
make test-smoke
```

- Fast unit subset (fail-fast):

```
make test-fast
```

- Impacted tests only (map changes → tests):

```
# Default compares to HEAD~1
bash scripts/test-impacted.sh

# Compare against a specific base
bash scripts/test-impacted.sh origin/main

# Or via make (uses BASE_REF if set)
BASE_REF=origin/main make test-impacted
```

## What They Run

- `test-smoke`: a tiny, representative suite (a few quick files) for sub‑minute
  feedback.
- `test-fast`: unit tests only; excludes `slow`, `integration`, and `casa`
  markers; uses `-q -x --maxfail=1`; also excludes heavier paths by keyword
  (`imaging|masking|nvss`) and disables plugin autoload.
- `test-impacted.sh`: detects changed files and runs only matching tests:
  - `pipeline/` → orchestrator + core pipeline tests
  - `imaging/` → mocked imaging tests
  - `qa/` → simple report/plot tests
  - `catalog/`, `calibration/`, `conversion/` → mapped tests that import the
    touched modules
  - If no match, falls back to `tests/unit` fast subset

## Notes

- Integration tests require `TEST_WITH_SYNTHETIC_DATA=1` plus CASA6/pyuvdata;
  they are excluded by default.
- By policy, local testing should use CASA6; CI may use system Python for
  certain unit tests.
- For faster startup, we disable auto‑loading of third‑party pytest plugins in
  the fast/smoke targets (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`).
