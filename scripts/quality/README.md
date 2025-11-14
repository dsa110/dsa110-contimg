# Quality Assurance Scripts

Scripts for code quality, validation, and error detection.

## Quick Start

```bash
# Run all quality checks
./quality/check-code-quality.sh

# Run error detection
./quality/auto-error-detection.sh

# Auto-fix common issues
./quality/auto-fix-common-issues.sh
```

## Error Detection

- **`auto-error-detection.sh`** - Comprehensive error detection
- **`auto-error-detection-env.sh`** - Environment-specific error detection
- **`auto-error-detection-universal.sh`** - Universal error detection
- **`error-detector-example.sh`** - Example error detector usage
- **`ensure-error-detection.sh`** - Ensure error detection is enabled

See `README-error-detection.md` for detailed documentation.

## Code Quality

- **`check-code-quality.sh`** - Run code quality checks
- **`auto-fix-code-quality.sh`** - Auto-fix code quality issues
- **`auto-fix-gotchas.sh`** - Fix common gotchas
- **`anti-pattern-review.sh`** - Review anti-patterns

## Validation

- **`validate-test-organization.py`** - Validate test organization
- **`validate-port-config.py`** - Validate port configuration
- **`validate-docker-ports.sh`** - Validate Docker port usage
- **`validate-startup-ports.sh`** - Validate startup port configuration
- **`validate-environment.sh`** - Validate development environment
- **`validate-output-handling.sh`** - Validate output handling

## Pre-commit Hooks

- **`pre-commit-output-suppression.sh`** - Check output suppression
- **`pre-commit-output-suppression-strict.sh`** - Strict output suppression
  check

## Auditing

- **`audit-output-suppression.sh`** - Audit output suppression usage
- **`maintenance-audit-output-suppression.sh`** - Maintenance audit

## Common Workflows

### Before Committing

```bash
./quality/check-code-quality.sh
./quality/auto-fix-common-issues.sh
```

### Continuous Integration

```bash
./quality/auto-error-detection.sh
./quality/validate-test-organization.py
```
