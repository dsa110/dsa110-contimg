# Quick Reference Card - Critical Commands

## Python Environment

```bash
# Always use casa6
/opt/miniforge/envs/casa6/bin/python -m pytest
```

## Error Detection Setup

```bash
source /data/dsa110-contimg/scripts/agent-setup.sh
```

## Running Tests

```bash
# Use wrapper (handles everything)
./scripts/run-tests.sh unit
./scripts/run-tests.sh integration
./scripts/run-tests.sh smoke

# Categories: smoke, unit, integration, science, e2e, all
```

## Adding New Tests

```bash
# Use template generator
python scripts/test-template.py <type> <module> <feature>

# Then validate
./scripts/validate-test-organization.py --staged-only
```

## Pre-commit Issues

```bash
# Fix Git lock file
./scripts/fix-git-lock.sh

# Check what's blocking
git commit  # Will show pre-commit errors
```

## Common Fixes

### "file not found: 2>&1"

→ Use `./scripts/pytest-safe.sh` or `./scripts/run-tests.sh`

### "Permission denied: casacore/data"

→ Ensure using casa6 Python, not system Python

### "Commit blocked by pre-commit hook"

→ Fix test organization or formatting issues shown

### "Tests failing silently"

→ Source error detection: `source scripts/agent-setup.sh`

## Critical Paths

- Code: `/data/dsa110-contimg/`
- Data: `/stage/dsa110-contimg/` (SSD) or `/data/dsa110-contimg/` (HDD)
- Docs: `docs/` (see `docs/DOCUMENTATION_QUICK_REFERENCE.md`)

## Emergency Docs

- Full warnings: `docs/how-to/CRITICAL_HANDOVER_WARNINGS.md`
- Python env: `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md`
- Test org: `docs/concepts/TEST_ORGANIZATION.md`
